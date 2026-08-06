"""LanceDB semantic search over ingested paper chunks.

Optional deps: ``lancedb``, ``fastembed``, ``pyarrow``.
Lazy-loaded on first use; ingest still works without them (FTS5 only).

Fleet default embedding: ``BAAI/bge-small-en-v1.5`` via FastEmbed (384-dim).
Switching models requires ``reindex_depot_vectors``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.sanitize import sanitize_text

logger = logging.getLogger(__name__)

TABLE_NAME = "paper_chunks"
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


class VectorRAGUnavailable(Exception):
    """Raised when optional RAG dependencies are missing or indexing failed."""


def _lance_dir(settings: Settings | None = None) -> Path:
    settings = settings or load_settings()
    path = settings.resolved_data_dir() / "lancedb"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _fastembed_cache(settings: Settings) -> Path:
    cache = settings.resolved_data_dir() / "cache" / "fastembed"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def rag_deps_available() -> bool:
    try:
        import pyarrow as pa  # noqa: F401
        from fastembed import TextEmbedding  # noqa: F401

        import lancedb  # noqa: F401

        return True
    except ImportError:
        return False


_EMBEDDER = None
_EMBED_BATCH = 64


def _get_embedder(model_name: str, cache_dir: str):
    global _EMBEDDER, _EMBED_BATCH
    if _EMBEDDER is None:
        from arxiv_mcp.rag.fastembed_gpu import create_text_embedding, repo_root_from_here

        _EMBEDDER, device, _EMBED_BATCH = create_text_embedding(model_name, cache_dir, repo_root=repo_root_from_here())
        logger.info("[rag] Embed device: %s (batch %s)", device, _EMBED_BATCH)
    return _EMBEDDER


def _encode_texts(texts: list[str], model_name: str, settings: Settings | None = None) -> list[list[float]]:
    if not texts:
        return []
    settings = settings or load_settings()
    embedder = _get_embedder(model_name, str(_fastembed_cache(settings)))
    batch = _EMBED_BATCH
    out: list[list[float]] = []
    for start in range(0, len(texts), batch):
        chunk = texts[start : start + batch]
        out.extend([list(vec) for vec in embedder.embed(chunk)])
    return out


def _open_db(settings: Settings):
    import lancedb

    return lancedb.connect(str(_lance_dir(settings)))


def _open_table(settings: Settings):
    db = _open_db(settings)
    try:
        return db.open_table(TABLE_NAME)
    except Exception:
        return None


def vector_rag_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or load_settings()
    if not rag_deps_available():
        return {
            "available": False,
            "backend": "fastembed",
            "model": settings.embedding_model,
            "db_path": str(_lance_dir(settings)),
            "indexed_chunks": 0,
            "install_hint": "uv sync --extra rag",
        }
    table = _open_table(settings)
    count = 0
    if table is not None:
        try:
            count = int(table.count_rows())
        except Exception:
            count = 0
    return {
        "available": True,
        "enabled": settings.rag_enabled,
        "backend": "fastembed",
        "model": settings.embedding_model,
        "db_path": str(_lance_dir(settings)),
        "indexed_chunks": count,
        "reindex_required_after_model_change": True,
    }


def _delete_paper_vectors(arxiv_id: str, settings: Settings) -> None:
    table = _open_table(settings)
    if table is None:
        return
    safe_id = arxiv_id.replace("'", "''")
    try:
        table.delete(f"arxiv_id = '{safe_id}'")
    except Exception as exc:
        logger.warning("vector delete failed for %s: %s", arxiv_id, exc)


def index_paper_vectors(
    arxiv_id: str,
    title: str,
    chunks: list[str],
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Embed and upsert chunk rows for one paper."""
    settings = settings or load_settings()
    if not settings.rag_enabled:
        return {"vector_indexed": False, "reason": "rag_disabled"}
    if not rag_deps_available():
        return {"vector_indexed": False, "reason": "deps_missing", "install_hint": "uv sync --extra rag"}
    if not chunks:
        return {"vector_indexed": True, "chunks": 0}

    import pyarrow as pa

    _delete_paper_vectors(arxiv_id, settings)
    vectors = _encode_texts(chunks, settings.embedding_model, settings)
    rows: list[dict[str, Any]] = []
    for idx, (body, vector) in enumerate(zip(chunks, vectors, strict=True)):
        rows.append(
            {
                "chunk_id": f"{arxiv_id}:{idx}",
                "arxiv_id": arxiv_id,
                "chunk_idx": idx,
                "title": title,
                "body": body[:4000],
                "vector": vector,
            }
        )

    db = _open_db(settings)
    table = _open_table(settings)
    batch = pa.Table.from_pylist(rows)
    if table is None:
        db.create_table(TABLE_NAME, batch)
    else:
        table.add(batch)

    return {"vector_indexed": True, "chunks": len(rows), "model": settings.embedding_model, "backend": "fastembed"}


def search_depot_semantic(
    query: str,
    *,
    limit: int = 20,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    settings = settings or load_settings()
    if not settings.rag_enabled:
        raise VectorRAGUnavailable("Semantic search disabled (ARXIV_MCP_RAG_ENABLED=0)")
    if not rag_deps_available():
        raise VectorRAGUnavailable("Install RAG deps: uv sync --extra rag")

    table = _open_table(settings)
    if table is None:
        return []

    q = query.strip()
    if not q:
        return []

    qvec = _encode_texts([q], settings.embedding_model, settings)[0]
    raw = table.search(qvec).limit(limit).to_list()
    hits: list[dict[str, Any]] = []
    for row in raw:
        distance = float(row.get("_distance", 0.0))
        similarity = 1.0 / (1.0 + distance)
        body = str(row.get("body", ""))
        snippet = sanitize_text(body[:320] + ("…" if len(body) > 320 else ""))
        hits.append(
            {
                "arxiv_id": row.get("arxiv_id", ""),
                "title": sanitize_text(str(row.get("title", ""))),
                "chunk_idx": int(row.get("chunk_idx", 0)),
                "snippet": snippet,
                "rank": similarity,
                "distance": distance,
                "engine": "lancedb",
            }
        )
    return hits


def reindex_all_vectors(settings: Settings | None = None) -> dict[str, Any]:
    """Rebuild LanceDB index from SQLite corpus markdown files."""
    from arxiv_mcp.services.corpus import _chunk_text, get_paper_markdown, list_ingested

    settings = settings or load_settings()
    if not rag_deps_available():
        return {"success": False, "error": "deps_missing", "install_hint": "uv sync --extra rag"}

    db = _open_db(settings)
    try:
        db.drop_table(TABLE_NAME)
    except Exception as exc:
        logger.debug("drop_table skipped: %s", exc)

    papers = list_ingested(settings=settings, limit=10_000)
    indexed = 0
    chunks_total = 0
    for row in papers:
        detail = get_paper_markdown(row["arxiv_id"], settings=settings)
        if not detail or not detail.get("markdown"):
            continue
        chunks = _chunk_text(detail["markdown"])
        rec = index_paper_vectors(row["arxiv_id"], detail["title"], chunks, settings=settings)
        if rec.get("vector_indexed"):
            indexed += 1
            chunks_total += int(rec.get("chunks", 0))

    return {
        "success": True,
        "papers": indexed,
        "chunks": chunks_total,
        "model": settings.embedding_model,
        "backend": "fastembed",
    }
