"""On-disk corpus: ingested markdown, SQLite FTS5 chunks (depot RAG), favorites."""

from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.sanitize import sanitize_text
from arxiv_mcp.services.epistemic_profile import build_epistemic_profile

_CHUNK_SIZE = 1400
_CHUNK_OVERLAP = 180
_RRF_K = 60


def _db_path(root: Path) -> Path:
    return root / "corpus.sqlite3"


def _chunk_text_sliding(text: str, size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    t = text.strip()
    if not t:
        return []
    out: list[str] = []
    i = 0
    n = len(t)
    while i < n:
        end = min(n, i + size)
        piece = t[i:end].strip()
        if piece:
            out.append(piece)
        if end >= n:
            break
        i = max(end - overlap, i + 1)
    return out


def _chunk_text(text: str, size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Prefer section boundaries (## headings) before sliding windows."""
    t = text.strip()
    if not t:
        return []
    sections = re.split(r"\n(?=##\s+)", t)
    if len(sections) <= 1:
        return _chunk_text_sliding(t, size=size, overlap=overlap)
    out: list[str] = []
    for section in sections:
        sec = section.strip()
        if not sec:
            continue
        if len(sec) <= size:
            out.append(sec)
        else:
            out.extend(_chunk_text_sliding(sec, size=size, overlap=overlap))
    return out



def _rrf_merge(
    ranked_lists: list[list[dict[str, Any]]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    scores: dict[tuple[str, int], float] = {}
    payloads: dict[tuple[str, int], dict[str, Any]] = {}
    for ranked in ranked_lists:
        for rank, hit in enumerate(ranked, start=1):
            key = (hit["arxiv_id"], int(hit["chunk_idx"]))
            scores[key] = scores.get(key, 0.0) + 1.0 / (_RRF_K + rank)
            payloads[key] = hit
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    out: list[dict[str, Any]] = []
    for key, score in ordered:
        hit = dict(payloads[key])
        hit["rank"] = score
        out.append(hit)
    return out


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS papers (
            arxiv_id TEXT PRIMARY KEY,
            title TEXT,
            ingested_at REAL,
            source TEXT,
            markdown_path TEXT,
            meta_json TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS favorites (
            arxiv_id TEXT PRIMARY KEY,
            title TEXT,
            note TEXT,
            created_at REAL
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            arxiv_id UNINDEXED,
            chunk_idx UNINDEXED,
            body,
            tokenize='porter unicode61'
        )
        """
    )
    conn.commit()


def _connect(root: Path) -> sqlite3.Connection:
    root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_db_path(root))
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _index_paper_chunks(
    conn: sqlite3.Connection,
    arxiv_id: str,
    markdown: str,
    *,
    precomputed_chunks: list[str] | None = None,
) -> int:
    conn.execute("DELETE FROM chunks_fts WHERE arxiv_id = ?", (arxiv_id,))
    chunks = precomputed_chunks if precomputed_chunks is not None else _chunk_text(markdown)
    for idx, body in enumerate(chunks):
        conn.execute(
            "INSERT INTO chunks_fts(arxiv_id, chunk_idx, body) VALUES (?,?,?)",
            (arxiv_id, idx, body),
        )
    return len(chunks)


def _fts_query_phrase(user_q: str) -> str:
    q = user_q.strip()
    if not q:
        return ""
    safe = q.replace('"', '""')
    return f'body: "{safe}"'


def _fts_query_or_terms(user_q: str) -> str:
    parts = [p for p in re.split(r"[^\w.\-]+", user_q.strip()) if len(p) > 1]
    if not parts:
        return ""
    bits: list[str] = []
    for p in parts[:12]:
        s = p.replace('"', '""')
        bits.append(f'body: "{s}"')
    return "(" + " OR ".join(bits) + ")"


def search_depot_fts(
    query: str,
    *,
    limit: int = 20,
    max_age_days: int | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Full-text search over ingested chunks (BM25-ranked).

    Args:
        query: Natural-language search query.
        limit: Maximum results to return.
        max_age_days: If set, exclude papers whose published date (from meta_json)
            is older than this many days. Useful for AI/ML topics where papers older
            than ~180 days may describe superseded systems. No filtering if None.
        settings: Optional settings override.
    """
    settings = settings or load_settings()
    root = settings.resolved_data_dir()
    dbp = _db_path(root)
    if not dbp.is_file():
        return []
    phrase = _fts_query_phrase(query)
    or_q = _fts_query_or_terms(query)
    tokens = [t for t in (phrase, or_q) if t]
    if not tokens:
        return []

    # Build published cutoff if requested
    cutoff_date: str | None = None
    if max_age_days is not None:
        import datetime
        cutoff_dt = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=max_age_days)
        cutoff_date = cutoff_dt.strftime("%Y-%m-%d")

    conn = sqlite3.connect(dbp)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_schema(conn)
        rows: list[sqlite3.Row] = []
        for token in tokens:
            try:
                if cutoff_date:
                    # JOIN to papers to filter by published date in meta_json.
                    # meta_json stores {"published": "YYYY-MM-DD", ...} or similar ISO string.
                    # We do a string prefix comparison — valid as long as dates are ISO-formatted.
                    rows = conn.execute(
                        """
                        SELECT c.arxiv_id, c.chunk_idx,
                               snippet(chunks_fts, 2, '<mark>', '</mark>', ' … ', 24) AS snippet,
                               bm25(chunks_fts) AS rank
                        FROM chunks_fts c
                        JOIN papers p ON p.arxiv_id = c.arxiv_id
                        WHERE chunks_fts MATCH ?
                          AND json_extract(p.meta_json, '$.published') >= ?
                        ORDER BY rank
                        LIMIT ?
                        """,
                        (token, cutoff_date, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT arxiv_id, chunk_idx,
                               snippet(chunks_fts, 2, '<mark>', '</mark>', ' … ', 24) AS snippet,
                               bm25(chunks_fts) AS rank
                        FROM chunks_fts
                        WHERE chunks_fts MATCH ?
                        ORDER BY rank
                        LIMIT ?
                        """,
                        (token, limit),
                    ).fetchall()
            except sqlite3.OperationalError:
                rows = []
            if rows:
                break
        titles: dict[str, str] = {}
        published: dict[str, str] = {}
        for r in rows:
            aid = r["arxiv_id"]
            if aid not in titles:
                tr = conn.execute(
                    "SELECT title, meta_json FROM papers WHERE arxiv_id = ?", (aid,)
                ).fetchone()
                titles[aid] = tr["title"] if tr else aid
                if tr and tr["meta_json"]:
                    try:
                        published[aid] = json.loads(tr["meta_json"]).get("published", "")
                    except (json.JSONDecodeError, TypeError):
                        published[aid] = ""
        return [
            {
                "arxiv_id": r["arxiv_id"],
                "title": sanitize_text(titles.get(r["arxiv_id"], r["arxiv_id"])),
                "published": published.get(r["arxiv_id"], ""),
                "chunk_idx": r["chunk_idx"],
                "snippet": sanitize_text(r["snippet"]),
                "rank": r["rank"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def search_depot_semantic(
    query: str,
    *,
    limit: int = 20,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    from arxiv_mcp.services.vector_rag import search_depot_semantic as _semantic

    return _semantic(query, limit=limit, settings=settings)


def search_depot_hybrid(
    query: str,
    *,
    limit: int = 20,
    max_age_days: int | None = None,
    settings: Settings | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Combine BM25 FTS and LanceDB vectors via reciprocal rank fusion."""
    fts = search_depot_fts(query, limit=max(limit * 2, 20), max_age_days=max_age_days, settings=settings)
    try:
        semantic = search_depot_semantic(query, limit=max(limit * 2, 20), settings=settings)
    except Exception:
        return fts[:limit], "sqlite_fts5"
    if not semantic:
        return fts[:limit], "sqlite_fts5" if fts else "hybrid_empty"
    merged = _rrf_merge([fts, semantic], limit=limit)
    for hit in merged:
        hit["engine"] = "hybrid_rrf"
    return merged, "hybrid_rrf"


def ingest_markdown(
    arxiv_id: str,
    title: str,
    markdown: str,
    *,
    source: str = "html",
    meta: dict[str, Any] | None = None,
    settings: Settings | None = None,
    precomputed_chunks: list[str] | None = None,
) -> dict[str, Any]:
    settings = settings or load_settings()
    root = settings.resolved_data_dir()
    md_dir = root / "markdown"
    md_dir.mkdir(parents=True, exist_ok=True)
    safe = arxiv_id.replace("/", "_")
    path = md_dir / f"{safe}.md"
    path.write_text(markdown, encoding="utf-8")

    meta_payload = dict(meta or {})
    cats = meta_payload.get("categories")
    if isinstance(cats, list) or markdown.strip():
        profile = build_epistemic_profile(
            markdown,
            categories=cats if isinstance(cats, list) else None,
            title=title,
        )
        meta_payload["epistemic_profile"] = profile
        meta_payload["epistemic_mode"] = profile["epistemic_mode"]

    conn = _connect(root)
    chunks: list[str] = []
    nchunks = 0
    try:
        conn.execute(
            """
            INSERT INTO papers (arxiv_id, title, ingested_at, source, markdown_path, meta_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(arxiv_id) DO UPDATE SET
              title=excluded.title,
              ingested_at=excluded.ingested_at,
              source=excluded.source,
              markdown_path=excluded.markdown_path,
              meta_json=excluded.meta_json
            """,
            (
                arxiv_id,
                title,
                time.time(),
                source,
                str(path),
                json.dumps(meta_payload, ensure_ascii=False),
            ),
        )
        chunks = precomputed_chunks if precomputed_chunks is not None else _chunk_text(markdown)
        nchunks = _index_paper_chunks(
            conn, arxiv_id, markdown, precomputed_chunks=chunks
        )
        conn.commit()
    finally:
        conn.close()

    vector_info: dict[str, Any] = {"vector_indexed": False}
    try:
        from arxiv_mcp.services.vector_rag import index_paper_vectors

        vector_info = index_paper_vectors(arxiv_id, title, chunks, settings=settings)
    except Exception as exc:
        vector_info = {"vector_indexed": False, "error": str(exc)}

    return {
        "arxiv_id": arxiv_id,
        "path": str(path),
        "bytes": path.stat().st_size,
        "chunks": nchunks,
        "source": source,
        "epistemic_mode": meta_payload.get("epistemic_mode"),
        "epistemic_profile": meta_payload.get("epistemic_profile"),
        **vector_info,
    }


def analyze_ingested_paper(arxiv_id: str, settings: Settings | None = None) -> dict[str, Any]:
    """Re-run epistemic profile on an already-ingested paper."""
    settings = settings or load_settings()
    row = get_paper_markdown(arxiv_id, settings=settings)
    if not row:
        return {"success": False, "error": "not_in_depot", "arxiv_id": arxiv_id}
    cats = row.get("meta", {}).get("categories")
    if not isinstance(cats, list):
        cats = None
    profile = build_epistemic_profile(row["markdown"], categories=cats, title=row["title"])
    meta = dict(row.get("meta") or {})
    meta["epistemic_profile"] = profile
    meta["epistemic_mode"] = profile["epistemic_mode"]

    root = settings.resolved_data_dir()
    conn = _connect(root)
    try:
        conn.execute(
            "UPDATE papers SET meta_json = ? WHERE arxiv_id = ?",
            (json.dumps(meta, ensure_ascii=False), arxiv_id),
        )
        conn.commit()
    finally:
        conn.close()
    return {"success": True, "arxiv_id": arxiv_id, "epistemic_profile": profile}


def persist_epistemic_profile(
    arxiv_id: str,
    profile: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or load_settings()
    root = settings.resolved_data_dir()
    conn = _connect(root)
    try:
        row = conn.execute(
            "SELECT meta_json FROM papers WHERE arxiv_id = ?",
            (arxiv_id,),
        ).fetchone()
        if not row:
            return {"success": False, "error": "not_in_depot", "arxiv_id": arxiv_id}
        meta = json.loads(row[0] or "{}")
        meta["epistemic_profile"] = profile
        meta["epistemic_mode"] = profile.get("epistemic_mode") or profile.get("primary_mode")
        conn.execute(
            "UPDATE papers SET meta_json = ? WHERE arxiv_id = ?",
            (json.dumps(meta, ensure_ascii=False), arxiv_id),
        )
        conn.commit()
    finally:
        conn.close()
    return {"success": True, "arxiv_id": arxiv_id, "epistemic_profile": profile}


def persist_readly_coverage(
    arxiv_id: str,
    coverage: list[dict[str, Any]],
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or load_settings()
    root = settings.resolved_data_dir()
    conn = _connect(root)
    try:
        row = conn.execute(
            "SELECT meta_json FROM papers WHERE arxiv_id = ?",
            (arxiv_id,),
        ).fetchone()
        if not row:
            return {"success": False, "error": "not_in_depot", "arxiv_id": arxiv_id}
        meta = json.loads(row[0] or "{}")
        meta["readly_coverage"] = coverage
        conn.execute(
            "UPDATE papers SET meta_json = ? WHERE arxiv_id = ?",
            (json.dumps(meta, ensure_ascii=False), arxiv_id),
        )
        conn.commit()
    finally:
        conn.close()
    return {"success": True, "arxiv_id": arxiv_id, "readly_coverage": coverage}


def _profile_matches_filters(
    profile: dict[str, Any] | None,
    *,
    primary_mode: str | None,
    needs_bench: bool | None,
    needs_telescope_or_instrument: bool | None,
    needs_formal_verification: bool | None,
    has_deep_claims: bool | None,
) -> bool:
    if not profile:
        if primary_mode is not None:
            return False
        if needs_bench is True or needs_telescope_or_instrument is True or needs_formal_verification is True:
            return False
        if has_deep_claims is True:
            return False
        return True
    if primary_mode and profile.get("primary_mode") != primary_mode:
        return False
    agg = profile.get("aggregate_needs") or {}
    if needs_bench is not None and bool(agg.get("needs_bench")) != needs_bench:
        return False
    if needs_telescope_or_instrument is not None and (
        bool(agg.get("needs_telescope_or_instrument")) != needs_telescope_or_instrument
    ):
        return False
    if needs_formal_verification is not None and (
        bool(agg.get("needs_formal_verification")) != needs_formal_verification
    ):
        return False
    claims = profile.get("claims") or []
    if has_deep_claims is True and not claims:
        return False
    if has_deep_claims is False and claims:
        return False
    return True


def list_ingested_filtered(
    settings: Settings | None = None,
    *,
    limit: int = 200,
    primary_mode: str | None = None,
    needs_bench: bool | None = None,
    needs_telescope_or_instrument: bool | None = None,
    needs_formal_verification: bool | None = None,
    has_deep_claims: bool | None = None,
) -> list[dict[str, Any]]:
    settings = settings or load_settings()
    root = settings.resolved_data_dir()
    dbp = _db_path(root)
    if not dbp.is_file():
        return []
    conn = sqlite3.connect(dbp)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_schema(conn)
        rows = conn.execute(
            "SELECT arxiv_id, title, ingested_at, source, meta_json FROM papers ORDER BY ingested_at DESC LIMIT ?",
            (limit * 4,),
        ).fetchall()
    finally:
        conn.close()
    out: list[dict[str, Any]] = []
    for r in rows:
        meta = json.loads(r["meta_json"] or "{}")
        profile = meta.get("epistemic_profile")
        if not _profile_matches_filters(
            profile,
            primary_mode=primary_mode,
            needs_bench=needs_bench,
            needs_telescope_or_instrument=needs_telescope_or_instrument,
            needs_formal_verification=needs_formal_verification,
            has_deep_claims=has_deep_claims,
        ):
            continue
        item = {
            "arxiv_id": r["arxiv_id"],
            "title": r["title"],
            "ingested_at": r["ingested_at"],
            "source": r["source"],
            "primary_mode": (profile or {}).get("primary_mode"),
            "claim_count": len((profile or {}).get("claims") or []),
            "aggregate_needs": (profile or {}).get("aggregate_needs"),
        }
        out.append(item)
        if len(out) >= limit:
            break
    return out


def get_paper_markdown(arxiv_id: str, settings: Settings | None = None) -> dict[str, Any] | None:
    settings = settings or load_settings()
    root = settings.resolved_data_dir()
    dbp = _db_path(root)
    if not dbp.is_file():
        return None
    conn = sqlite3.connect(dbp)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_schema(conn)
        row = conn.execute(
            "SELECT arxiv_id, title, markdown_path, meta_json, source, ingested_at FROM papers WHERE arxiv_id = ?",
            (arxiv_id,),
        ).fetchone()
        if not row:
            return None
        p = Path(row["markdown_path"])
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
        return {
            "arxiv_id": row["arxiv_id"],
            "title": sanitize_text(row["title"]),
            "markdown": sanitize_text(text),
            "meta": json.loads(row["meta_json"] or "{}"),
            "source": row["source"],
            "ingested_at": row["ingested_at"],
        }
    finally:
        conn.close()


def list_ingested(settings: Settings | None = None, *, limit: int = 50) -> list[dict[str, Any]]:
    settings = settings or load_settings()
    root = settings.resolved_data_dir()
    dbp = _db_path(root)
    if not dbp.is_file():
        return []
    conn = sqlite3.connect(dbp)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_schema(conn)
        rows = conn.execute(
            "SELECT arxiv_id, title, ingested_at, source FROM papers "
            "ORDER BY ingested_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [{"arxiv_id": r[0], "title": r[1], "ingested_at": r[2], "source": r[3]} for r in rows]


def add_favorite(
    arxiv_id: str,
    *,
    title: str | None = None,
    note: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or load_settings()
    root = settings.resolved_data_dir()
    conn = _connect(root)
    try:
        now = time.time()
        conn.execute(
            """
            INSERT INTO favorites (arxiv_id, title, note, created_at)
            VALUES (?,?,?,?)
            ON CONFLICT(arxiv_id) DO UPDATE SET
              title=COALESCE(excluded.title, favorites.title),
              note=COALESCE(excluded.note, favorites.note)
            """,
            (arxiv_id, title, note, now),
        )
        conn.commit()
    finally:
        conn.close()
    return {"arxiv_id": arxiv_id, "ok": True}


def remove_favorite(arxiv_id: str, settings: Settings | None = None) -> bool:
    settings = settings or load_settings()
    root = settings.resolved_data_dir()
    dbp = _db_path(root)
    if not dbp.is_file():
        return False
    conn = sqlite3.connect(dbp)
    try:
        _ensure_schema(conn)
        cur = conn.execute("DELETE FROM favorites WHERE arxiv_id = ?", (arxiv_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def list_favorites(settings: Settings | None = None, *, limit: int = 200) -> list[dict[str, Any]]:
    settings = settings or load_settings()
    root = settings.resolved_data_dir()
    dbp = _db_path(root)
    if not dbp.is_file():
        return []
    conn = sqlite3.connect(dbp)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_schema(conn)
        rows = conn.execute(
            "SELECT arxiv_id, title, note, created_at FROM favorites ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [{"arxiv_id": r[0], "title": r[1], "note": r[2], "created_at": r[3]} for r in rows]


def depot_stats(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or load_settings()
    root = settings.resolved_data_dir()
    dbp = _db_path(root)
    if not dbp.is_file():
        stats = {"papers": 0, "favorites": 0, "chunks": 0, "data_dir": str(root)}
    else:
        conn = sqlite3.connect(dbp)
        try:
            _ensure_schema(conn)
            p = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            f = conn.execute("SELECT COUNT(*) FROM favorites").fetchone()[0]
            try:
                c = conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0]
            except sqlite3.OperationalError:
                c = 0
        finally:
            conn.close()
        stats = {"papers": p, "favorites": f, "chunks": c, "data_dir": str(root)}
    try:
        from arxiv_mcp.services.vector_rag import vector_rag_status

        stats["rag"] = vector_rag_status(settings)
    except Exception as exc:
        stats["rag"] = {"available": False, "error": str(exc)}
    return stats
