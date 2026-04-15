"""On-disk corpus: ingested markdown, SQLite FTS5 chunks (depot RAG), favorites."""

from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from arxiv_mcp.config import Settings, load_settings

_CHUNK_SIZE = 1400
_CHUNK_OVERLAP = 180


def _db_path(root: Path) -> Path:
    return root / "corpus.sqlite3"


def _chunk_text(text: str, size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
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


def _index_paper_chunks(conn: sqlite3.Connection, arxiv_id: str, markdown: str) -> int:
    conn.execute("DELETE FROM chunks_fts WHERE arxiv_id = ?", (arxiv_id,))
    chunks = _chunk_text(markdown)
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
        cutoff_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=max_age_days)
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
                "title": titles.get(r["arxiv_id"], r["arxiv_id"]),
                "published": published.get(r["arxiv_id"], ""),
                "chunk_idx": r["chunk_idx"],
                "snippet": r["snippet"],
                "rank": r["rank"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def ingest_markdown(
    arxiv_id: str,
    title: str,
    markdown: str,
    *,
    source: str = "html",
    meta: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or load_settings()
    root = settings.resolved_data_dir()
    md_dir = root / "markdown"
    md_dir.mkdir(parents=True, exist_ok=True)
    safe = arxiv_id.replace("/", "_")
    path = md_dir / f"{safe}.md"
    path.write_text(markdown, encoding="utf-8")

    conn = _connect(root)
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
                json.dumps(meta or {}, ensure_ascii=False),
            ),
        )
        nchunks = _index_paper_chunks(conn, arxiv_id, markdown)
        conn.commit()
    finally:
        conn.close()

    return {
        "arxiv_id": arxiv_id,
        "path": str(path),
        "bytes": path.stat().st_size,
        "chunks": nchunks,
    }


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
            "title": row["title"],
            "markdown": text,
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
        return {"papers": 0, "favorites": 0, "chunks": 0, "data_dir": str(root)}
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
    return {"papers": p, "favorites": f, "chunks": c, "data_dir": str(root)}
