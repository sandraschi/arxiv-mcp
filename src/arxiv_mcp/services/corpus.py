"""Lightweight on-disk corpus for arXiv markdown snapshots."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from arxiv_mcp.config import Settings, load_settings


def _db_path(root: Path) -> Path:
    return root / "corpus.sqlite3"


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
    conn.commit()


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

    conn = sqlite3.connect(_db_path(root))
    try:
        _ensure_schema(conn)
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
        conn.commit()
    finally:
        conn.close()

    return {"arxiv_id": arxiv_id, "path": str(path), "bytes": path.stat().st_size}


def list_ingested(settings: Settings | None = None, *, limit: int = 50) -> list[dict[str, Any]]:
    settings = settings or load_settings()
    root = settings.resolved_data_dir()
    dbp = _db_path(root)
    if not dbp.is_file():
        return []
    conn = sqlite3.connect(dbp)
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
