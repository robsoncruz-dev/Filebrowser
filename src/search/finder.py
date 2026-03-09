"""
Filebrowser — Motor de Busca

Filtra os PDFs indexados com base no termo de busca digitado pelo usuário.
Suporta busca parcial case-insensitive e ordena por relevância.
"""

from pathlib import Path
from src.search.indexer import get_all_pdfs
from src.config.settings import DB_PATH


def _normalize(text: str) -> str:
    """Normaliza texto para comparação (lowercase, sem acentos básicos)."""
    return text.lower().strip()


def _match_score(query_parts: list[str], nome: str, caminho: str) -> int:
    """
    Calcula um score de relevância para ordenar os resultados.
    Quanto menor o score, mais relevante.

    Regras:
    - Match exato no nome do arquivo → score alto (prioridade)
    - Todas as partes do query presentes no nome → bom score
    - Match no caminho → score menor
    """
    nome_lower = nome.lower()
    caminho_lower = caminho.lower()

    # Verificar se todas as partes estão no nome
    all_in_name = all(part in nome_lower for part in query_parts)
    # Verificar se todas as partes estão no caminho completo
    all_in_path = all(part in caminho_lower for part in query_parts)

    if not all_in_name and not all_in_path:
        return -1  # Sem match

    score = 0

    if all_in_name:
        score += 100  # Priorizar match no nome

        # Bonus: query aparece como substring contígua no nome
        query_joined = " ".join(query_parts)
        if query_joined in nome_lower:
            score += 50

        # Bonus: nome começa com o query
        if nome_lower.startswith(query_parts[0]):
            score += 25

        # Penalizar nomes mais longos (preferir match mais "tight")
        score -= len(nome) // 10
    elif all_in_path:
        score += 30  # Match no caminho é menos relevante

    return score


def search_pdfs(
    query: str,
    max_results: int = 12,
    db_path: Path | None = None,
) -> list[dict]:
    """
    Busca PDFs que correspondem ao query.

    Args:
        query: Texto digitado pelo usuário.
        max_results: Número máximo de resultados.
        db_path: Caminho personalizado para o banco de dados.

    Returns:
        Lista de dicts com os PDFs encontrados, ordenados por relevância.
    """
    if not query or not query.strip():
        return []

    query = query.strip()

    # Wildcard: * mostra todos os PDFs indexados
    if query == "*":
        all_pdfs = get_all_pdfs(db_path or DB_PATH)
        return all_pdfs[:max_results]

    query_normalized = _normalize(query)
    query_parts = query_normalized.split()

    all_pdfs = get_all_pdfs(db_path or DB_PATH)
    scored_results = []

    for pdf in all_pdfs:
        score = _match_score(query_parts, pdf["nome"], pdf["caminho"])
        if score >= 0:
            pdf["score"] = score
            scored_results.append(pdf)

    # Ordenar por score (maior = mais relevante)
    scored_results.sort(key=lambda x: x["score"], reverse=True)

    return scored_results[:max_results]
