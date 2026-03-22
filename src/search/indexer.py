"""
Filebrowser — Indexador de PDFs

Varre os diretórios configurados e mantém um cache SQLite com os caminhos
dos arquivos PDF encontrados. Suporta indexação incremental delta e por fase
(locais primeiro, nuvem depois).
"""

import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from src.config.settings import AppConfig, CACHE_DIR, DB_PATH


def _init_db(db_path: Path) -> sqlite3.Connection:
    """Inicializa o banco de dados SQLite com as tabelas necessárias."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
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

    # Tabela de metadados para persistir informações entre sessões
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


# ─── Metadados ───────────────────────────────────────────────────────────────


def save_metadata(key: str, value: str, db_path: Path | None = None):
    """Salva um metadado no banco de dados."""
    path = db_path or DB_PATH
    conn = _init_db(path)
    conn.execute(
        "INSERT OR REPLACE INTO metadata (chave, valor) VALUES (?, ?)",
        (key, value),
    )
    conn.commit()
    conn.close()


def get_metadata(key: str, default: str = "", db_path: Path | None = None) -> str:
    """Lê um metadado do banco de dados."""
    path = db_path or DB_PATH
    if not path.exists():
        return default
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute(
            "SELECT valor FROM metadata WHERE chave = ?", (key,)
        ).fetchone()
        return row[0] if row else default
    finally:
        conn.close()


def get_counts_by_source(db_path: Path | None = None) -> dict[str, int]:
    """Retorna contagem de PDFs separada por fonte (local/nuvem)."""
    path = db_path or DB_PATH
    if not path.exists():
        return {"local": 0, "nuvem": 0}

    conn = sqlite3.connect(str(path))
    try:
        rows = conn.execute(
            "SELECT fonte, COUNT(*) FROM pdfs GROUP BY fonte"
        ).fetchall()
        counts = {"local": 0, "nuvem": 0}
        for fonte, count in rows:
            if fonte == "nuvem_nativa":
                counts["nuvem"] = counts.get("nuvem", 0) + count
            else:
                counts[fonte] = counts.get(fonte, 0) + count
        return counts
    finally:
        conn.close()


def get_last_indexed_at(db_path: Path | None = None) -> str:
    """Retorna timestamp formatado da última indexação."""
    ts = get_metadata("last_indexed_at", "", db_path)
    if not ts:
        return ""
    try:
        dt = datetime.fromtimestamp(float(ts))
        return dt.strftime("%d/%m %H:%M")
    except (ValueError, OSError):
        return ""


def get_last_cloud_count(db_path: Path | None = None) -> int:
    """Retorna a contagem da última indexação de nuvem bem-sucedida."""
    val = get_metadata("last_cloud_count", "0", db_path)
    try:
        return int(val)
    except ValueError:
        return 0


def _save_index_timestamp(conn: sqlite3.Connection):
    """Salva o timestamp da indexação atual."""
    conn.execute(
        "INSERT OR REPLACE INTO metadata (chave, valor) VALUES (?, ?)",
        ("last_indexed_at", str(time.time())),
    )
    conn.commit()


# ─── Scan de Diretórios ──────────────────────────────────────────────────────


def _scandir_recursive(base_path: str, max_depth: int, ignorar: set[str], current_depth: int = 0) -> list[dict]:
    """Varredura otimizada de baixo nível via iteradores MFT/Inode."""
    if current_depth > max_depth:
        return []
        
    pdfs = []
    try:
        with os.scandir(base_path) as it:
            for entry in it:
                if entry.name.startswith(".") or entry.name in ignorar:
                    continue
                    
                if entry.is_dir(follow_symlinks=False):
                    pdfs.extend(_scandir_recursive(entry.path, max_depth, ignorar, current_depth + 1))
                elif entry.is_file(follow_symlinks=False) and entry.name.lower().endswith('.pdf'):
                    try:
                        stat = entry.stat()
                        pdfs.append({
                            "nome": entry.name,
                            "caminho": entry.path,
                            "diretorio": base_path,
                            "tamanho": stat.st_size,
                            "modificado": stat.st_mtime,
                        })
                    except OSError:
                        pass
    except (PermissionError, OSError):
        pass
        
    return pdfs


from concurrent.futures import ThreadPoolExecutor, as_completed

def scan_directory_list(
    diretorios: list[Path],
    max_depth: int,
    ignorar: list[str],
    on_found: callable = None,
) -> list[dict]:
    """
    Varre uma lista de diretórios em paralelo usando ThreadPoolExecutor.
    """
    todas_pdfs = []
    ignorar_set = set(ignorar)
    
    max_workers = min(32, (os.cpu_count() or 1) * 4)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_scandir_recursive, str(d), max_depth, ignorar_set): d 
            for d in diretorios if d.exists()
        }
        
        for future in as_completed(futures):
            try:
                batch = future.result()
                todas_pdfs.extend(batch)
                if on_found and batch:
                    # Emite um relatório por lote resolvido
                    on_found(len(todas_pdfs), batch[-1])
            except Exception:
                pass

    return todas_pdfs


# ─── Indexação Delta ─────────────────────────────────────────────────────────


def _delta_sync(conn: sqlite3.Connection, pdfs: list[dict], fonte: str) -> int:
    """
    Sincronização delta: compara PDFs encontrados com o cache.
    - Novos: INSERT
    - Modificados (mtime diferente): UPDATE
    - Removidos (no cache mas não no scan): DELETE

    Retorna a quantidade final de PDFs dessa fonte.
    """
    agora = time.time()

    # Obter caminhos existentes no cache para esta fonte
    existing = {}
    rows = conn.execute(
        "SELECT caminho, modificado FROM pdfs WHERE fonte = ?", (fonte,)
    ).fetchall()
    for caminho, modificado in rows:
        existing[caminho] = modificado

    # Caminhos encontrados no scan atual
    found_paths = set()

    for pdf in pdfs:
        caminho = pdf["caminho"]
        found_paths.add(caminho)

        if caminho in existing:
            # Existe no cache — verificar se foi modificado
            if abs(pdf["modificado"] - existing[caminho]) > 1.0:
                # Modificado → UPDATE
                conn.execute(
                    """UPDATE pdfs SET nome=?, diretorio=?, tamanho=?,
                       modificado=?, indexado_em=? WHERE caminho=?""",
                    (pdf["nome"], pdf["diretorio"], pdf["tamanho"],
                     pdf["modificado"], agora, caminho),
                )
        else:
            # Novo → INSERT
            conn.execute(
                """INSERT OR REPLACE INTO pdfs
                   (nome, caminho, diretorio, tamanho, modificado, indexado_em, fonte)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (pdf["nome"], caminho, pdf["diretorio"], pdf["tamanho"],
                 pdf["modificado"], agora, fonte),
            )

    # Remover PDFs que não existem mais no sistema de arquivos
    removed = set(existing.keys()) - found_paths
    if removed:
        conn.executemany(
            "DELETE FROM pdfs WHERE caminho = ?",
            [(r,) for r in removed],
        )

    conn.commit()
    return len(pdfs)


def build_index_local(
    config: AppConfig,
    db_path: Path | None = None,
    on_found: callable = None,
) -> int:
    """
    Indexa as pastas LOCAIS usando delta sync (rápido).
    Retorna a quantidade de PDFs locais indexados.
    """
    path = db_path or DB_PATH
    conn = _init_db(path)

    pdfs_local = scan_directory_list(
        config.busca.diretorios_locais,
        config.busca.profundidade_local,
        config.busca.ignorar,
        on_found=on_found,
    )
    count_local = _delta_sync(conn, pdfs_local, "local")
    
    pdfs_nativa = scan_directory_list(
        config.busca.diretorios_nuvem_nativos_expandidos,
        config.busca.profundidade_local,
        config.busca.ignorar,
        on_found=on_found,
    )
    count_nativa = _delta_sync(conn, pdfs_nativa, "nuvem_nativa")
    
    _save_index_timestamp(conn)
    conn.close()
    return count_local + count_nativa


def scan_cloud(config: AppConfig, on_found: callable = None) -> list[dict]:
    """
    Varre instâncias de nuvem headless registradas usando `rclone lsjson` de forma assíncrona.
    Não depende de rclone mounte FUSE.
    """
    remotes = config.nuvem.remotes
    if not remotes:
        return []

    todas_pdfs = []
    ignorar_set = set(config.busca.ignorar)
    
    import json
    import subprocess
    
    def _fetch_remote(remote_name: str) -> list[dict]:
        pdfs = []
        try:
            cmd = [
                "rclone", "lsjson", f"{remote_name}:",
                "--include", "*.pdf",
                "--fast-list", "-R"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                items = json.loads(result.stdout)
                for item in items:
                    if item.get("IsDir"):
                        continue
                        
                    path_str = item.get("Path", "")
                    
                    # Checagem leve de paths ignorados
                    should_ign = False
                    for ign in ignorar_set:
                        if f"/{ign.lower()}/" in f"/{path_str.lower()}":
                            should_ign = True
                            break
                    if should_ign:
                        continue
                        
                    mtime = 0.0
                    modtime = item.get("ModTime", "")
                    if modtime:
                        try:
                            if modtime.endswith("Z"):
                                modtime = modtime[:-1] + "+00:00"
                            mtime = datetime.fromisoformat(modtime).timestamp()
                        except ValueError:
                            pass
                            
                    pdfs.append({
                        "nome": item.get("Name", ""),
                        "caminho": f"cloud://{remote_name}/{path_str}",
                        "diretorio": f"Nuvem: {remote_name}",
                        "tamanho": item.get("Size", 0),
                        "modificado": mtime,
                    })
        except Exception:
            pass
        return pdfs

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=max(1, len(remotes))) as executor:
        futures = {executor.submit(_fetch_remote, r): r for r in remotes.keys()}
        for future in as_completed(futures):
            try:
                batch = future.result()
                todas_pdfs.extend(batch)
                if on_found and batch:
                    on_found(len(todas_pdfs), batch[-1])
            except Exception:
                pass

    return todas_pdfs


def save_cloud_results(pdfs: list[dict], db_path: Path | None = None) -> int:
    """
    Salva os PDFs de nuvem no banco de dados usando delta sync.
    Chamado pelo UI após o scan concluir com sucesso.
    """
    path = db_path or DB_PATH
    conn = _init_db(path)
    count = _delta_sync(conn, pdfs, "nuvem")

    # Salvar contagem para referência de progresso futuro
    conn.execute(
        "INSERT OR REPLACE INTO metadata (chave, valor) VALUES (?, ?)",
        ("last_cloud_count", str(count)),
    )
    _save_index_timestamp(conn)
    conn.close()
    return count


def clear_cloud_cache(db_path: Path | None = None):
    """Limpa o cache de nuvem antes de iniciar novo scan."""
    path = db_path or DB_PATH
    conn = _init_db(path)
    conn.execute("DELETE FROM pdfs WHERE fonte = 'nuvem'")
    conn.commit()
    conn.close()


def insert_single_cloud_pdf(pdf: dict, db_path: Path | None = None):
    """
    Insere um único PDF de nuvem no banco de dados.
    Chamado incrementalmente durante o scan para persistência imediata.
    """
    path = db_path or DB_PATH
    conn = _init_db(path)
    agora = time.time()
    conn.execute(
        """INSERT OR REPLACE INTO pdfs
           (nome, caminho, diretorio, tamanho, modificado, indexado_em, fonte)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            pdf["nome"],
            pdf["caminho"],
            pdf["diretorio"],
            pdf["tamanho"],
            pdf["modificado"],
            agora,
            "nuvem",
        ),
    )
    conn.commit()
    conn.close()


def build_index_cloud(
    config: AppConfig,
    db_path: Path | None = None,
    timeout: int = 30,
    on_found: callable = None,
) -> int:
    """Atalho para compatibilidade. Retorna contagem ou -1 em timeout."""
    import threading
    result = {"pdfs": []}

    def _scan():
        result["pdfs"] = scan_cloud(config, on_found=on_found)
    t = threading.Thread(target=_scan, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        return -1
    return save_cloud_results(result["pdfs"], db_path)


def build_index(config: AppConfig, db_path: Path | None = None) -> int:
    """
    Constrói/atualiza o índice completo (local + nuvem).
    Atalho para compatibilidade. Retorna total de PDFs.
    """
    local = build_index_local(config, db_path)
    cloud = build_index_cloud(config, db_path)
    return local + cloud


def get_total_count(db_path: Path | None = None) -> int:
    """Retorna a contagem total de PDFs no índice."""
    path = db_path or DB_PATH
    if not path.exists():
        return 0
    conn = sqlite3.connect(str(path))
    count = conn.execute("SELECT COUNT(*) FROM pdfs").fetchone()[0]
    conn.close()
    return count


def get_all_pdfs(db_path: Path | None = None) -> list[dict]:
    """Retorna todos os PDFs do índice."""
    path = db_path or DB_PATH
    if not path.exists():
        return []

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT nome, caminho, diretorio, tamanho, fonte FROM pdfs ORDER BY nome"
    ).fetchall()
    conn.close()

    return [dict(row) for row in rows]
