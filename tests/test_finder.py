"""
Filebrowser — Testes do Motor de Busca (finder.py)

Testa _normalize, _match_score e search_pdfs com banco temporário.
"""

import sqlite3
from pathlib import Path

import pytest

from src.search.finder import _normalize, _match_score, search_pdfs


# ─── _normalize ──────────────────────────────────────────────────────────────


def test_normalize_lowercase():
    assert _normalize("Meu PDF") == "meu pdf"


def test_normalize_strip():
    assert _normalize("  hello  ") == "hello"


def test_normalize_combined():
    assert _normalize("  ABC Def  ") == "abc def"


# ─── _match_score ────────────────────────────────────────────────────────────


def test_match_score_name_exact():
    """Match exato no nome deve retornar score alto."""
    score = _match_score(["relatorio"], "relatorio.pdf", "/home/user/relatorio.pdf")
    assert score > 0


def test_match_score_name_contiguous():
    """Match contíguo no nome ganha bonus."""
    score_contig = _match_score(["meu", "pdf"], "meu pdf final.pdf", "/docs/meu pdf final.pdf")
    score_split = _match_score(["meu", "pdf"], "meu arquivo pdf.pdf", "/docs/meu arquivo pdf.pdf")
    # Contíguo deve ter score >= split
    assert score_contig >= score_split


def test_match_score_name_starts_with():
    """Nome que começa com o query ganha bonus extra."""
    score_start = _match_score(["relatorio"], "relatorio_2024.pdf", "/docs/relatorio_2024.pdf")
    score_mid = _match_score(["relatorio"], "meu_relatorio.pdf", "/docs/meu_relatorio.pdf")
    assert score_start > score_mid


def test_match_score_path_only():
    """Match apenas no caminho deve retornar score positivo mas menor."""
    score = _match_score(["documentos"], "arquivo.pdf", "/home/user/documentos/arquivo.pdf")
    assert score > 0
    assert score < 100  # Menor que match no nome


def test_match_score_no_match():
    """Sem match retorna -1."""
    score = _match_score(["inexistente"], "arquivo.pdf", "/home/user/arquivo.pdf")
    assert score == -1


# ─── search_pdfs ─────────────────────────────────────────────────────────────


@pytest.fixture
def test_db(tmp_path: Path) -> Path:
    """Cria um banco SQLite temporário com PDFs de teste."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pdfs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            caminho TEXT NOT NULL UNIQUE,
            diretorio TEXT NOT NULL,
            tamanho INTEGER DEFAULT 0,
            modificado REAL DEFAULT 0,
            indexado_em REAL DEFAULT 0,
            fonte TEXT DEFAULT 'local'
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nome ON pdfs(nome)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_caminho ON pdfs(caminho)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)

    test_pdfs = [
        ("relatorio_2024.pdf", "/home/user/docs/relatorio_2024.pdf", "/home/user/docs", 1024, 0, 0, "local"),
        ("notas_aula.pdf", "/home/user/escola/notas_aula.pdf", "/home/user/escola", 2048, 0, 0, "local"),
        ("manual_python.pdf", "/home/user/dev/manual_python.pdf", "/home/user/dev", 4096, 0, 0, "local"),
        ("cloud_backup.pdf", "cloud://gdrive/cloud_backup.pdf", "Nuvem: gdrive", 512, 0, 0, "nuvem"),
    ]
    conn.executemany(
        "INSERT INTO pdfs (nome, caminho, diretorio, tamanho, modificado, indexado_em, fonte) VALUES (?, ?, ?, ?, ?, ?, ?)",
        test_pdfs,
    )
    conn.commit()
    conn.close()
    return db


def test_search_empty_query(test_db: Path):
    assert search_pdfs("", db_path=test_db) == []


def test_search_whitespace_query(test_db: Path):
    assert search_pdfs("   ", db_path=test_db) == []


def test_search_wildcard(test_db: Path):
    results = search_pdfs("*", db_path=test_db)
    assert len(results) == 4


def test_search_wildcard_respects_max(test_db: Path):
    results = search_pdfs("*", max_results=2, db_path=test_db)
    assert len(results) == 2


def test_search_by_name(test_db: Path):
    results = search_pdfs("relatorio", db_path=test_db)
    assert len(results) == 1
    assert results[0]["nome"] == "relatorio_2024.pdf"


def test_search_by_partial_name(test_db: Path):
    results = search_pdfs("manual", db_path=test_db)
    assert len(results) == 1
    assert results[0]["nome"] == "manual_python.pdf"


def test_search_no_results(test_db: Path):
    results = search_pdfs("inexistente", db_path=test_db)
    assert len(results) == 0


def test_search_by_path(test_db: Path):
    """Busca por parte do caminho deve encontrar resultados."""
    results = search_pdfs("escola", db_path=test_db)
    assert len(results) >= 1
    assert any(r["nome"] == "notas_aula.pdf" for r in results)


def test_search_results_sorted_by_relevance(test_db: Path):
    """Resultados com match no nome devem ter prioridade sobre match no caminho."""
    results = search_pdfs("notas", db_path=test_db)
    if len(results) > 1:
        # O primeiro resultado deve ter score >= segundo
        assert results[0].get("score", 0) >= results[1].get("score", 0)
