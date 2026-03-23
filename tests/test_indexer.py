"""
Filebrowser — Testes do Indexador (indexer.py)

Testa _init_db, metadata CRUD, _delta_sync e build_index_local
com banco SQLite temporário e pastas de PDFs fake.
"""

import sqlite3
import time
from pathlib import Path

import pytest

from src.search.indexer import (
    _init_db,
    _delta_sync,
    save_metadata,
    get_metadata,
    get_all_pdfs,
    get_total_count,
    get_counts_by_source,
    build_index_local,
    clear_cloud_cache,
    insert_single_cloud_pdf,
)
from src.config.settings import AppConfig, SearchConfig


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Retorna um caminho de DB temporário."""
    return tmp_path / "test_index.db"


@pytest.fixture
def pdf_dir(tmp_path: Path) -> Path:
    """Cria uma pasta com PDFs fake para indexação."""
    docs = tmp_path / "documents"
    docs.mkdir()

    (docs / "relatorio.pdf").write_bytes(b"%PDF-1.4 fake")
    (docs / "notas.pdf").write_bytes(b"%PDF-1.4 fake2")
    (docs / "planilha.xlsx").write_bytes(b"not a pdf")

    sub = docs / "subdir"
    sub.mkdir()
    (sub / "deep_file.pdf").write_bytes(b"%PDF-1.4 deep")

    return docs


# ─── _init_db ────────────────────────────────────────────────────────────────


def test_init_db_creates_tables(db_path: Path):
    conn = _init_db(db_path)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = [t[0] for t in tables]
    assert "pdfs" in table_names
    assert "metadata" in table_names
    conn.close()


def test_init_db_idempotent(db_path: Path):
    """Chamar _init_db múltiplas vezes não deve falhar."""
    conn1 = _init_db(db_path)
    conn1.close()
    conn2 = _init_db(db_path)
    conn2.close()


# ─── Metadata ────────────────────────────────────────────────────────────────


def test_save_and_get_metadata(db_path: Path):
    save_metadata("test_key", "test_value", db_path)
    assert get_metadata("test_key", "", db_path) == "test_value"


def test_get_metadata_default(db_path: Path):
    """Chave inexistente retorna default."""
    _init_db(db_path).close()
    assert get_metadata("missing", "fallback", db_path) == "fallback"


def test_get_metadata_nonexistent_db(tmp_path: Path):
    """DB que não existe retorna default sem erro."""
    fake_db = tmp_path / "nope.db"
    assert get_metadata("key", "default", fake_db) == "default"


def test_save_metadata_overwrite(db_path: Path):
    save_metadata("key", "first", db_path)
    save_metadata("key", "second", db_path)
    assert get_metadata("key", "", db_path) == "second"


# ─── _delta_sync ─────────────────────────────────────────────────────────────


def test_delta_sync_insert(db_path: Path):
    """PDFs novos devem ser inseridos."""
    conn = _init_db(db_path)

    pdfs = [
        {"nome": "a.pdf", "caminho": "/docs/a.pdf", "diretorio": "/docs",
         "tamanho": 100, "modificado": time.time()},
        {"nome": "b.pdf", "caminho": "/docs/b.pdf", "diretorio": "/docs",
         "tamanho": 200, "modificado": time.time()},
    ]

    count = _delta_sync(conn, pdfs, "local")
    assert count == 2

    rows = conn.execute("SELECT COUNT(*) FROM pdfs WHERE fonte='local'").fetchone()
    assert rows[0] == 2
    conn.close()


def test_delta_sync_update(db_path: Path):
    """PDFs com mtime diferente devem ser atualizados."""
    conn = _init_db(db_path)

    old_time = time.time() - 100
    pdfs_v1 = [
        {"nome": "a.pdf", "caminho": "/docs/a.pdf", "diretorio": "/docs",
         "tamanho": 100, "modificado": old_time},
    ]
    _delta_sync(conn, pdfs_v1, "local")

    new_time = time.time()
    pdfs_v2 = [
        {"nome": "a.pdf", "caminho": "/docs/a.pdf", "diretorio": "/docs",
         "tamanho": 150, "modificado": new_time},
    ]
    _delta_sync(conn, pdfs_v2, "local")

    row = conn.execute("SELECT tamanho FROM pdfs WHERE caminho='/docs/a.pdf'").fetchone()
    assert row[0] == 150
    conn.close()


def test_delta_sync_delete(db_path: Path):
    """PDFs ausentes do scan devem ser removidos do cache."""
    conn = _init_db(db_path)

    pdfs = [
        {"nome": "a.pdf", "caminho": "/docs/a.pdf", "diretorio": "/docs",
         "tamanho": 100, "modificado": time.time()},
        {"nome": "b.pdf", "caminho": "/docs/b.pdf", "diretorio": "/docs",
         "tamanho": 200, "modificado": time.time()},
    ]
    _delta_sync(conn, pdfs, "local")

    # Segundo sync: b.pdf foi deletado
    pdfs_v2 = [pdfs[0]]
    _delta_sync(conn, pdfs_v2, "local")

    total = conn.execute("SELECT COUNT(*) FROM pdfs WHERE fonte='local'").fetchone()[0]
    assert total == 1

    row = conn.execute("SELECT nome FROM pdfs").fetchone()
    assert row[0] == "a.pdf"
    conn.close()


def test_delta_sync_no_change(db_path: Path):
    """PDFs sem alteração de mtime não devem ser atualizados."""
    conn = _init_db(db_path)

    mtime = time.time()
    pdfs = [
        {"nome": "a.pdf", "caminho": "/docs/a.pdf", "diretorio": "/docs",
         "tamanho": 100, "modificado": mtime},
    ]
    _delta_sync(conn, pdfs, "local")

    # Segundo sync com mesmo mtime
    _delta_sync(conn, pdfs, "local")

    total = conn.execute("SELECT COUNT(*) FROM pdfs WHERE fonte='local'").fetchone()[0]
    assert total == 1
    conn.close()


# ─── build_index_local ───────────────────────────────────────────────────────


def test_build_index_local(db_path: Path, pdf_dir: Path):
    """Indexação local deve encontrar os PDFs na pasta temporária."""
    config = AppConfig()
    config.busca = SearchConfig(
        diretorios=[str(pdf_dir)],
        profundidade_local=3,
        ignorar=[],
    )
    count = build_index_local(config, db_path=db_path)
    assert count >= 3  # relatorio.pdf, notas.pdf, deep_file.pdf


def test_build_index_local_ignores_non_pdf(db_path: Path, pdf_dir: Path):
    """Indexação deve ignorar arquivos que não são PDFs."""
    config = AppConfig()
    config.busca = SearchConfig(
        diretorios=[str(pdf_dir)],
        profundidade_local=3,
        ignorar=[],
    )
    build_index_local(config, db_path=db_path)
    pdfs = get_all_pdfs(db_path)
    names = [p["nome"] for p in pdfs]
    assert "planilha.xlsx" not in names


# ─── get_total_count / get_all_pdfs ──────────────────────────────────────────


def test_get_total_count_empty(tmp_path: Path):
    """DB inexistente retorna 0."""
    assert get_total_count(tmp_path / "nope.db") == 0


def test_get_all_pdfs_empty(tmp_path: Path):
    """DB inexistente retorna lista vazia."""
    assert get_all_pdfs(tmp_path / "nope.db") == []


# ─── get_counts_by_source ────────────────────────────────────────────────────


def test_get_counts_by_source(db_path: Path):
    conn = _init_db(db_path)
    pdfs_local = [
        {"nome": "a.pdf", "caminho": "/docs/a.pdf", "diretorio": "/docs",
         "tamanho": 100, "modificado": time.time()},
    ]
    _delta_sync(conn, pdfs_local, "local")
    conn.close()

    counts = get_counts_by_source(db_path)
    assert counts["local"] == 1
    assert counts["nuvem"] == 0


# ─── Cloud helpers ───────────────────────────────────────────────────────────


def test_insert_single_cloud_pdf(db_path: Path):
    _init_db(db_path).close()
    pdf = {
        "nome": "cloud.pdf",
        "caminho": "cloud://gdrive/cloud.pdf",
        "diretorio": "Nuvem: gdrive",
        "tamanho": 512,
        "modificado": time.time(),
    }
    insert_single_cloud_pdf(pdf, db_path)
    pdfs = get_all_pdfs(db_path)
    assert len(pdfs) == 1
    assert pdfs[0]["fonte"] == "nuvem"


def test_clear_cloud_cache(db_path: Path):
    _init_db(db_path).close()
    pdf = {
        "nome": "cloud.pdf",
        "caminho": "cloud://gdrive/cloud.pdf",
        "diretorio": "Nuvem: gdrive",
        "tamanho": 512,
        "modificado": time.time(),
    }
    insert_single_cloud_pdf(pdf, db_path)
    clear_cloud_cache(db_path)
    assert get_total_count(db_path) == 0
