"""Code-hunt: mine recent arXiv papers for open-weight code/repo drops.

Many PRC research teams decouple the paper release from the code/weights drop,
often hosting first on Gitee/ModelScope before GitHub. This service scans recent
submissions in target categories, extracts repository links and "code coming
soon" promises from abstracts (and, for promising candidates, full text), tags
likely Chinese-lab affiliation, and persists findings to a local SQLite tracking
DB.

A re-poll pass re-checks promised/dead repo URLs for liveness. When a repo goes
live, the finding is pushed to aiwatcher-mcp (POST /api/fleet/ingest) as a
high-urgency fleet event so it surfaces ahead of the trending lists.

Pure stdlib + httpx; no new heavy deps. Storage lives under the arxiv-mcp data
dir at ``codehunt/tracking.sqlite3`` and digests at ``codehunt/digest_*.json``.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

import httpx

from arxiv_mcp.codehunt_affiliations import (
    affiliation_signal,
    affiliation_summary,
    classify_affiliations,
    load_affiliation_tables,
)
from arxiv_mcp.codehunt_media import probe_media_traction
from arxiv_mcp.codehunt_media_feeds import refresh_media_feed_cache
from arxiv_mcp.codehunt_watch_authors import classify_watch_authors, load_watch_authors
from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.services import papers

# ── Extraction patterns ──────────────────────────────────────────────────────

# Repository / weights hosts. Capture the canonical project URL.
_REPO_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("github", re.compile(r"https?://github\.com/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+", re.I)),
    ("gitee", re.compile(r"https?://gitee\.com/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+", re.I)),
    ("github_io", re.compile(r"https?://[A-Za-z0-9_.\-]+\.github\.io[A-Za-z0-9_./\-]*", re.I)),
    ("huggingface", re.compile(r"https?://huggingface\.co/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+", re.I)),
    ("modelscope", re.compile(r"https?://(?:www\.)?modelscope\.cn/[A-Za-z0-9_./\-]+", re.I)),
)

# "Code coming soon" style promises (no resolvable link yet).
_PROMISE_PATTERN = re.compile(
    r"\b("
    r"code(?:\s+and\s+(?:models?|weights?|data))?\s+(?:will\s+be|are|is)\s+"
    r"(?:made\s+)?(?:publicly\s+)?(?:available|released)"
    r"|(?:models?|weights?|checkpoints?)\s+will\s+be\s+(?:made\s+)?(?:publicly\s+)?released"
    r"|will\s+be\s+open[\s\-]?sourced"
    r"|code\s+(?:is|are)\s+coming\s+soon"
    r"|we\s+(?:will|plan\s+to)\s+release"
    r"|to\s+be\s+released"
    r"|code\s+available\s+(?:soon|upon)"
    r")\b",
    re.I,
)

# Trailing punctuation to strip from URLs captured mid-sentence.
_URL_TRIM = ".,);]}>\"'"

# Chinese-lab / company affiliation signals (lowercased substring match).
_CHINA_TERMS: tuple[str, ...] = (
    "tsinghua",
    "peking university",
    "zhejiang",
    "fudan",
    "nanjing university",
    "shanghai ai lab",
    "shanghai artificial intelligence lab",
    "harbin institute",
    "sun yat-sen",
    "beihang",
    "renmin university",
    "university of science and technology of china",
    "ustc",
    "casia",
    "chinese academy of sciences",
    "institute of automation",
    "alibaba",
    "qwen",
    "damo",
    "ant group",
    "tongyi",
    "tencent",
    "hunyuan",
    "wechat ai",
    "bytedance",
    "seed",
    "doubao",
    "baidu",
    "ernie",
    "deepseek",
    "moonshot",
    "kimi",
    "zhipu",
    "glm-",
    "01.ai",
    "yi-",
    "minimax",
    "stepfun",
    "step-",
    "baichuan",
    "internlm",
    "opengvlab",
    "sensetime",
    "megvii",
    "iflytek",
    "funasr",
    "modelscope",
    "huawei",
    "noah's ark",
    "noah ark",
    "xiaomi",
    "vivo",
    "oppo",
    "meituan",
    "kuaishou",
    "gitee.com",
    "modelscope.cn",
    "shenzhen",
    "hangzhou",
    "beijing",
)

# VLA / embodied robotics signals (title-focused; pairs with cs.RO in push policy).
_VLA_TERMS: tuple[str, ...] = (
    "wall-oss",
    "wall-x",
    "wall-wm",
    "wall wm",
    "x-vla",
    "xvla",
    "x-square",
    "vision-language-action",
    "vision language action",
    "vla model",
    "openvla",
    "lerobot",
    "dmuon",
    "embodied ai",
    "embodied manipulation",
    "robot manipulation",
)


def _vla_signal(finding: dict[str, Any]) -> bool:
    title = (finding.get("title") or "").lower()
    return any(term in title for term in _VLA_TERMS)


def _affiliation_min_tier(settings: Settings) -> str:
    tier = (settings.codehunt_affiliation_min_tier or "a").strip().lower()
    return tier if tier in ("a", "b") else "a"


def _should_push_finding(finding: dict[str, Any], settings: Settings) -> bool:
    """Push live drops: China, watch authors, tier-A/B affiliations, VLA, or priority cats."""
    if not settings.codehunt_china_only_push:
        return True
    if finding.get("china_signal"):
        return True
    if finding.get("watch_author_signal"):
        return True
    if finding.get("affiliation_signal"):
        return True
    if _vla_signal(finding):
        return True
    cats = set(finding.get("categories") or [])
    priority = set(settings.codehunt_priority_category_list())
    return bool(cats.intersection(priority))


def _classify_china(text: str) -> list[str]:
    """Return the distinct Chinese-affiliation terms found in ``text``."""
    low = text.lower()
    hits: list[str] = []
    for term in _CHINA_TERMS:
        if term in low and term not in hits:
            hits.append(term)
    return hits


def _extract_repo_links(text: str) -> list[dict[str, str]]:
    """Extract (host, url) repository/weights links, deduped, trimmed."""
    found: dict[str, dict[str, str]] = {}
    for host, pat in _REPO_PATTERNS:
        for m in pat.finditer(text):
            url = m.group(0).rstrip(_URL_TRIM)
            if url not in found:
                found[url] = {"host": host, "url": url}
    return list(found.values())


def _has_promise(text: str) -> bool:
    return bool(_PROMISE_PATTERN.search(text))


# ── Tracking DB ───────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS findings (
    paper_id      TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    categories    TEXT,
    published     TEXT,
    abs_url       TEXT,
    china_signal  INTEGER NOT NULL DEFAULT 0,
    china_terms   TEXT,
    watch_author_signal INTEGER NOT NULL DEFAULT 0,
    watch_authors TEXT,
    affiliation_signal INTEGER NOT NULL DEFAULT 0,
    affiliation_hits TEXT,
    media_signal INTEGER NOT NULL DEFAULT 0,
    media_hits TEXT,
    media_checked_at REAL,
    media_pushed INTEGER NOT NULL DEFAULT 0,
    repo_links    TEXT,
    status        TEXT NOT NULL DEFAULT 'none',  -- code_live | promised | none
    live_url      TEXT,
    first_seen    REAL NOT NULL,
    last_checked  REAL,
    pushed        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_findings_status ON findings(status);
"""


def _db_path(settings: Settings) -> Path:
    d = settings.resolved_data_dir() / "codehunt"
    d.mkdir(parents=True, exist_ok=True)
    return d / "tracking.sqlite3"


def _migrate_schema(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(findings)").fetchall()}
    if "watch_author_signal" not in cols:
        conn.execute("ALTER TABLE findings ADD COLUMN watch_author_signal INTEGER NOT NULL DEFAULT 0")
    if "watch_authors" not in cols:
        conn.execute("ALTER TABLE findings ADD COLUMN watch_authors TEXT")
    if "affiliation_signal" not in cols:
        conn.execute("ALTER TABLE findings ADD COLUMN affiliation_signal INTEGER NOT NULL DEFAULT 0")
    if "affiliation_hits" not in cols:
        conn.execute("ALTER TABLE findings ADD COLUMN affiliation_hits TEXT")
    if "media_signal" not in cols:
        conn.execute("ALTER TABLE findings ADD COLUMN media_signal INTEGER NOT NULL DEFAULT 0")
    if "media_hits" not in cols:
        conn.execute("ALTER TABLE findings ADD COLUMN media_hits TEXT")
    if "media_checked_at" not in cols:
        conn.execute("ALTER TABLE findings ADD COLUMN media_checked_at REAL")
    if "media_pushed" not in cols:
        conn.execute("ALTER TABLE findings ADD COLUMN media_pushed INTEGER NOT NULL DEFAULT 0")


def _connect(settings: Settings) -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(settings))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    _migrate_schema(conn)
    return conn


def _row_to_finding(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "paper_id": row["paper_id"],
        "title": row["title"],
        "categories": json.loads(row["categories"] or "[]"),
        "published": row["published"],
        "abs_url": row["abs_url"],
        "china_signal": bool(row["china_signal"]),
        "china_terms": json.loads(row["china_terms"] or "[]"),
        "watch_author_signal": bool(row["watch_author_signal"]) if "watch_author_signal" in row.keys() else False,
        "watch_authors": json.loads(row["watch_authors"] or "[]") if "watch_authors" in row.keys() else [],
        "affiliation_signal": bool(row["affiliation_signal"]) if "affiliation_signal" in row.keys() else False,
        "affiliation_hits": json.loads(row["affiliation_hits"] or "[]") if "affiliation_hits" in row.keys() else [],
        "media_signal": bool(row["media_signal"]) if "media_signal" in row.keys() else False,
        "media_hits": json.loads(row["media_hits"] or "[]") if "media_hits" in row.keys() else [],
        "media_checked_at": row["media_checked_at"] if "media_checked_at" in row.keys() else None,
        "media_pushed": bool(row["media_pushed"]) if "media_pushed" in row.keys() else False,
        "repo_links": json.loads(row["repo_links"] or "[]"),
        "status": row["status"],
        "live_url": row["live_url"],
        "first_seen": row["first_seen"],
        "last_checked": row["last_checked"],
        "pushed": bool(row["pushed"]),
    }


# ── Repo liveness + aiwatcher push ─────────────────────────────────────────────


async def _check_repo_live(client: httpx.AsyncClient, url: str) -> bool:
    """True if the repo/page resolves to a real page (2xx/3xx, not a 404 stub)."""
    try:
        resp = await client.get(url)
    except httpx.HTTPError:
        return False
    if resp.status_code >= 400:
        return False
    # GitHub returns 200 for its soft-404 page; guard against the obvious case.
    if "github.com" in url.lower() and "page not found" in resp.text[:4000].lower():
        return False
    return True


async def _push_to_aiwatcher(finding: dict[str, Any], settings: Settings) -> bool:
    """POST a live code-drop finding to aiwatcher /api/fleet/ingest."""
    base = (settings.aiwatcher_base_url or "").rstrip("/")
    if not base:
        return False
    headers = {"Content-Type": "application/json"}
    if settings.aiwatcher_api_key:
        headers["X-AIWatcher-Key"] = settings.aiwatcher_api_key
    cats = ", ".join(finding.get("categories") or [])
    terms = ", ".join(finding.get("china_terms") or [])
    watch = ", ".join(finding.get("watch_authors") or [])
    aff = affiliation_summary(finding.get("affiliation_hits") or [])
    summary = (
        f"Code/weights drop live for arXiv:{finding['paper_id']} ({cats}). "
        f"Repo: {finding.get('live_url') or ''}. "
        f"China signal: {terms or 'none'}. "
        f"Watch authors: {watch or 'none'}. Affiliations: {aff}. "
        f"Abstract: {finding['abs_url']}"
    )
    payload = {
        "title": f"[code-drop] {finding['title']}",
        "summary": summary,
        "source": "arxiv-codehunt",
        "url": finding.get("live_url") or finding["abs_url"],
        "urgency_hint": (
            9.0
            if finding.get("china_signal")
            else 8.5
            if finding.get("watch_author_signal")
            else 8.5
            if finding.get("affiliation_signal")
            else 8.5
            if _vla_signal(finding)
            else 8.5
            if set(finding.get("categories") or []).intersection(settings.codehunt_priority_category_list())
            else 7.5
        ),
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{base}/api/fleet/ingest", json=payload, headers=headers)
            return resp.status_code < 400
    except httpx.HTTPError:
        return False


# ── Scan ────────────────────────────────────────────────────────────────────


async def run_codehunt_scan(
    *,
    categories: list[str] | None = None,
    days: int = 3,
    limit_per_category: int = 50,
    fulltext_max_papers: int | None = None,
    push: bool = True,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Scan recent papers, extract repo links/promises, persist, optionally push.

    Args:
        categories: arXiv categories to scan (default from settings: cs.AI,cs.RO,cs.SD).
        days: rolling lookback window.
        limit_per_category: max papers pulled per category before dedupe.
        fulltext_max_papers: cap on papers to pull full text for when the abstract
            shows a promise but no resolvable link (default from settings).
        push: if True, push live China-signal drops to aiwatcher.
    """
    settings = settings or load_settings()
    cats = [c.strip() for c in (categories or settings.codehunt_category_list()) if c.strip()]
    hours = max(1, int(days)) * 24
    limit_per_category = min(max(limit_per_category, 1), 100)
    ft_budget = (
        settings.codehunt_fulltext_max_papers if fulltext_max_papers is None else max(0, int(fulltext_max_papers))
    )

    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for cat in cats:
        try:
            rows = await papers.list_category_latest(cat, limit=limit_per_category, hours=hours, settings=settings)
        except Exception as exc:
            errors.append({"category": cat, "error": str(exc), "error_type": type(exc).__name__})
            continue
        for p in rows:
            d = papers.paper_summary_to_dict(p)
            pid = d["paper_id"]
            if pid in seen:
                continue
            seen.add(pid)
            blob = " ".join([d.get("title") or "", d.get("summary") or "", " ".join(d.get("authors") or [])])
            candidates.append({"dict": d, "blob": blob, "cat": cat})

    candidates.sort(key=lambda c: c["dict"].get("published") or "", reverse=True)

    new_findings: list[dict[str, Any]] = []
    ft_used = 0

    with closing(_connect(settings)) as conn:
        for c in candidates:
            d = c["dict"]
            pid = d["paper_id"]
            blob = c["blob"]

            links = _extract_repo_links(blob)
            promised = _has_promise(blob)

            # Abstract had a promise but no link - spend full-text budget to confirm.
            if promised and not links and ft_used < ft_budget:
                ft_used += 1
                body = await _safe_fulltext(pid, settings)
                if body:
                    blob = blob + "\n" + body
                    links = _extract_repo_links(body)

            china_terms = _classify_china(blob)
            paper_authors = d.get("authors") or []
            watch_authors = classify_watch_authors(paper_authors, settings=settings)
            min_tier = _affiliation_min_tier(settings)  # type: ignore[arg-type]
            affiliation_hits = classify_affiliations(blob, settings=settings, min_tier=min_tier)
            aff_signal = affiliation_signal(affiliation_hits, min_tier=min_tier)
            if not links and not promised and not watch_authors and not aff_signal:
                continue  # not interesting

            if links or promised:
                status = "promised"  # links may exist but unverified until re-poll
            elif watch_authors:
                status = "watch_author"
            else:
                status = "watch_affiliation"
            row = {
                "paper_id": pid,
                "title": (d.get("title") or "")[:500],
                "categories": json.dumps(d.get("categories") or []),
                "published": d.get("published"),
                "abs_url": d.get("abs_url"),
                "china_signal": 1 if china_terms else 0,
                "china_terms": json.dumps(china_terms),
                "watch_author_signal": 1 if watch_authors else 0,
                "watch_authors": json.dumps(watch_authors),
                "affiliation_signal": 1 if aff_signal else 0,
                "affiliation_hits": json.dumps(affiliation_hits),
                "repo_links": json.dumps(links),
                "status": status,
                "first_seen": time.time(),
            }
            inserted = _upsert_finding(conn, row)
            if inserted:
                paper_cats = d.get("categories") or []
                new_findings.append(
                    {
                        "paper_id": pid,
                        "title": row["title"],
                        "categories": paper_cats,
                        "priority_category": bool(
                            set(paper_cats).intersection(settings.codehunt_priority_category_list())
                        ),
                        "china_signal": bool(china_terms),
                        "china_terms": china_terms,
                        "watch_author_signal": bool(watch_authors),
                        "watch_authors": watch_authors,
                        "affiliation_signal": aff_signal,
                        "affiliation_hits": affiliation_hits,
                        "repo_links": links,
                        "promised": promised,
                    }
                )
        conn.commit()

    digest = {
        "scanned_at": time.time(),
        "categories": cats,
        "days": days,
        "candidates_scanned": len(candidates),
        "new_findings": len(new_findings),
        "fulltext_fetched": ft_used,
        "findings": new_findings,
        "errors": errors,
    }
    digest_path = _write_digest(digest, settings)

    # New findings with links get an immediate liveness pass so live drops push now.
    repoll = await repoll_pending(push=push, settings=settings) if new_findings else None

    return {
        "success": True,
        "message": (
            f"Code-hunt: {len(new_findings)} new findings across {len(cats)} categories "
            f"({sum(1 for f in new_findings if f['china_signal'])} China-signal, "
            f"{sum(1 for f in new_findings if f.get('watch_author_signal'))} watch-author, "
            f"{sum(1 for f in new_findings if f.get('affiliation_signal'))} tier-affiliation)."
        ),
        "categories": cats,
        "days": days,
        "candidates_scanned": len(candidates),
        "new_findings": new_findings,
        "fulltext_fetched": ft_used,
        "digest_path": str(digest_path),
        "repoll": repoll,
        "errors": errors,
    }


def _upsert_finding(conn: sqlite3.Connection, row: dict[str, Any]) -> bool:
    """Insert a finding if new; return True only on first insert (preserve first_seen)."""
    cur = conn.execute("SELECT paper_id FROM findings WHERE paper_id = ?", (row["paper_id"],))
    has_links = bool(row.get("repo_links") and row["repo_links"] not in ("[]", ""))
    if cur.fetchone():
        conn.execute(
            "UPDATE findings SET repo_links = ?, china_signal = ?, china_terms = ?, "
            "watch_author_signal = ?, watch_authors = ?, "
            "affiliation_signal = ?, affiliation_hits = ?, "
            "status = CASE WHEN status IN ('watch_author', 'watch_affiliation') AND ? "
            "THEN 'promised' ELSE status END "
            "WHERE paper_id = ?",
            (
                row["repo_links"],
                row["china_signal"],
                row["china_terms"],
                row.get("watch_author_signal", 0),
                row.get("watch_authors", "[]"),
                row.get("affiliation_signal", 0),
                row.get("affiliation_hits", "[]"),
                1 if has_links else 0,
                row["paper_id"],
            ),
        )
        return False
    conn.execute(
        "INSERT INTO findings "
        "(paper_id, title, categories, published, abs_url, china_signal, china_terms, "
        " watch_author_signal, watch_authors, affiliation_signal, affiliation_hits, "
        " repo_links, status, first_seen) "
        "VALUES (:paper_id, :title, :categories, :published, :abs_url, :china_signal, "
        ":china_terms, :watch_author_signal, :watch_authors, :affiliation_signal, "
        ":affiliation_hits, :repo_links, :status, :first_seen)",
        row,
    )
    return True


async def _safe_fulltext(paper_id: str, settings: Settings) -> str:
    """Best-effort full-text markdown; empty string on any failure."""
    try:
        from arxiv_mcp.depot_service import resolve_fulltext_for_ingest

        res = await resolve_fulltext_for_ingest(paper_id, settings=settings)
        if res.get("success"):
            return str(res.get("markdown") or "")
    except Exception:
        return ""
    return ""


def _write_digest(digest: dict[str, Any], settings: Settings) -> Path:
    d = settings.resolved_data_dir() / "codehunt"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"digest_codehunt_{int(time.time())}.json"
    path.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ── Re-poll ───────────────────────────────────────────────────────────────────


async def repoll_pending(
    *,
    limit: int = 200,
    push: bool = True,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Re-check promised findings' repo links for liveness; push newly-live drops."""
    settings = settings or load_settings()
    with closing(_connect(settings)) as conn:
        rows = conn.execute(
            "SELECT * FROM findings WHERE status = 'promised' ORDER BY first_seen DESC LIMIT ?",
            (limit,),
        ).fetchall()
        pending = [_row_to_finding(r) for r in rows]

    checked = 0
    went_live: list[dict[str, Any]] = []
    pushed = 0

    async with httpx.AsyncClient(timeout=settings.codehunt_repo_timeout_seconds, follow_redirects=True) as client:
        for f in pending:
            links = f.get("repo_links") or []
            if not links:
                continue  # promise with no URL yet - nothing to poll
            checked += 1
            live_url = None
            for link in links:
                url = link.get("url") if isinstance(link, dict) else str(link)
                if url and await _check_repo_live(client, url):
                    live_url = url
                    break
            now = time.time()
            with closing(_connect(settings)) as conn:
                if live_url:
                    conn.execute(
                        "UPDATE findings SET status='code_live', live_url=?, last_checked=? WHERE paper_id=?",
                        (live_url, now, f["paper_id"]),
                    )
                else:
                    conn.execute(
                        "UPDATE findings SET last_checked=? WHERE paper_id=?",
                        (now, f["paper_id"]),
                    )
                conn.commit()
            if live_url:
                f["status"] = "code_live"
                f["live_url"] = live_url
                went_live.append(f)

    # Push live drops not yet pushed (respecting china-only setting).
    for f in went_live:
        if not _should_push_finding(f, settings):
            continue
        if push and await _push_to_aiwatcher(f, settings):
            pushed += 1
            with closing(_connect(settings)) as conn:
                conn.execute("UPDATE findings SET pushed=1 WHERE paper_id=?", (f["paper_id"],))
                conn.commit()

    return {
        "success": True,
        "pending_checked": checked,
        "went_live": [
            {
                "paper_id": f["paper_id"],
                "title": f["title"],
                "live_url": f["live_url"],
                "china_signal": f["china_signal"],
            }
            for f in went_live
        ],
        "pushed_to_aiwatcher": pushed,
    }


def _finding_quality_for_media(finding: dict[str, Any]) -> bool:
    return bool(
        finding.get("china_signal")
        or finding.get("watch_author_signal")
        or finding.get("affiliation_signal")
        or finding.get("status") == "code_live"
    )


async def _push_media_to_aiwatcher(
    finding: dict[str, Any],
    hits: list[dict[str, Any]],
    settings: Settings,
) -> bool:
    base = (settings.aiwatcher_base_url or "").rstrip("/")
    if not base or not hits:
        return False
    headers = {"Content-Type": "application/json"}
    if settings.aiwatcher_api_key:
        headers["X-AIWatcher-Key"] = settings.aiwatcher_api_key
    outlets = ", ".join(f"{h.get('source', '?')}:{(h.get('title') or '')[:60]}" for h in hits[:4])
    summary = (
        f"Media traction for arXiv:{finding['paper_id']} ({finding.get('title', '')[:120]}). "
        f"Hits ({len(hits)}): {outlets}. "
        f"Affiliations: {affiliation_summary(finding.get('affiliation_hits') or [])}. "
        f"Abstract: {finding.get('abs_url')}"
    )
    top_url = hits[0].get("url") or finding.get("abs_url")
    payload = {
        "title": f"[media-traction] {finding['title'][:200]}",
        "summary": summary,
        "source": "arxiv-codehunt-media",
        "url": top_url,
        "urgency_hint": 8.0 if finding.get("affiliation_signal") else 7.5,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{base}/api/fleet/ingest", json=payload, headers=headers)
            return resp.status_code < 400
    except httpx.HTTPError:
        return False


async def check_media_traction(
    *,
    limit: int = 40,
    push: bool = True,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Probe HN + Google News + tech RSS for papers ~1 week after arXiv publication."""
    settings = settings or load_settings()
    if not settings.codehunt_media_enabled:
        return {"success": True, "skipped": True, "reason": "codehunt_media_disabled"}

    feed_cache = await refresh_media_feed_cache(settings=settings)

    recheck_s = max(1, int(settings.codehunt_media_recheck_days)) * 86400
    cutoff = time.time() - recheck_s
    with closing(_connect(settings)) as conn:
        rows = conn.execute(
            "SELECT * FROM findings WHERE (media_checked_at IS NULL OR media_checked_at < ?) "
            "AND published IS NOT NULL "
            "ORDER BY published DESC LIMIT ?",
            (cutoff, limit),
        ).fetchall()
        candidates = [_row_to_finding(r) for r in rows]

    checked = 0
    with_traction: list[dict[str, Any]] = []
    pushed = 0
    skipped_young = 0

    for f in candidates:
        if not _finding_quality_for_media(f):
            continue
        result = await probe_media_traction(
            paper_id=f["paper_id"],
            title=f.get("title") or "",
            published=f.get("published"),
            settings=settings,
        )
        if result.get("skipped"):
            skipped_young += 1
            continue
        checked += 1
        hits = result.get("hits") or []
        now = time.time()
        media_sig = 1 if hits else 0
        with closing(_connect(settings)) as conn:
            conn.execute(
                "UPDATE findings SET media_signal=?, media_hits=?, media_checked_at=?, "
                "status = CASE WHEN ? AND status NOT IN ('code_live', 'promised') "
                "THEN 'media_traction' ELSE status END "
                "WHERE paper_id=?",
                (media_sig, json.dumps(hits), now, media_sig, f["paper_id"]),
            )
            conn.commit()
        f["media_hits"] = hits
        f["media_signal"] = bool(hits)
        if hits:
            with_traction.append({**f, "media_hits": hits})
            if push and not f.get("media_pushed") and await _push_media_to_aiwatcher(f, hits, settings):
                pushed += 1
                with closing(_connect(settings)) as conn:
                    conn.execute(
                        "UPDATE findings SET media_pushed=1 WHERE paper_id=?",
                        (f["paper_id"],),
                    )
                    conn.commit()

    return {
        "success": True,
        "candidates": len(candidates),
        "checked": checked,
        "skipped_too_young_or_old": skipped_young,
        "with_media_traction": [
            {
                "paper_id": f["paper_id"],
                "title": f.get("title"),
                "hits": f.get("media_hits"),
            }
            for f in with_traction
        ],
        "pushed_to_aiwatcher": pushed,
        "feed_cache": feed_cache,
        "fetch_policy": "aggregators_and_rss_metadata_only",
        "min_age_days": settings.codehunt_media_min_age_days,
        "max_age_days": settings.codehunt_media_max_age_days,
    }


def codehunt_stats(*, settings: Settings | None = None) -> dict[str, Any]:
    """Tracking DB summary for status cards / monitoring."""
    settings = settings or load_settings()
    with closing(_connect(settings)) as conn:
        total = conn.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
        by_status = {
            r[0]: r[1] for r in conn.execute("SELECT status, COUNT(*) FROM findings GROUP BY status").fetchall()
        }
        china = conn.execute("SELECT COUNT(*) FROM findings WHERE china_signal = 1").fetchone()[0]
        watch = conn.execute("SELECT COUNT(*) FROM findings WHERE watch_author_signal = 1").fetchone()[0]
        affiliation = conn.execute("SELECT COUNT(*) FROM findings WHERE affiliation_signal = 1").fetchone()[0]
        media = conn.execute("SELECT COUNT(*) FROM findings WHERE media_signal = 1").fetchone()[0]
        pushed = conn.execute("SELECT COUNT(*) FROM findings WHERE pushed = 1").fetchone()[0]
        media_pushed = conn.execute("SELECT COUNT(*) FROM findings WHERE media_pushed = 1").fetchone()[0]
        recent_live = [
            _row_to_finding(r)
            for r in conn.execute(
                "SELECT * FROM findings WHERE status='code_live' ORDER BY last_checked DESC LIMIT 20"
            ).fetchall()
        ]
    return {
        "total_findings": total,
        "by_status": by_status,
        "china_signal": china,
        "watch_author_signal": watch,
        "affiliation_signal": affiliation,
        "media_signal": media,
        "watch_authors_configured": len(load_watch_authors(settings)),
        "affiliation_terms_configured": sum(len(t) for t in load_affiliation_tables(settings)),
        "pushed_to_aiwatcher": pushed,
        "media_pushed_to_aiwatcher": media_pushed,
        "db_path": str(_db_path(settings)),
        "recent_live": recent_live,
    }
