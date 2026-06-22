"""Shared async HTTP: User-Agent, retries, optional on-disk cache."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from arxiv_mcp.config import Settings, load_settings

log = logging.getLogger(__name__)

USER_AGENT = "arxiv-mcp/0.7 (research bot; +https://arxiv.org/help/policies)"


@dataclass
class HttpPayload:
    ok: bool
    status_code: int | None
    text: str | None
    content: bytes | None
    headers: dict[str, str]
    content_type: str | None
    error: dict[str, Any] | None
    from_cache: bool = False


def _cache_paths(settings: Settings, endpoint: str, url: str) -> tuple[Path, Path]:
    key = hashlib.sha256(f"{endpoint}\n{url}".encode()).hexdigest()[:32]
    base = settings.resolved_data_dir() / "http_cache" / endpoint
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{key}.body", base / f"{key}.meta.json"


def _read_cache(body_path: Path, meta_path: Path) -> HttpPayload | None:
    if not body_path.is_file() or not meta_path.is_file():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        raw = body_path.read_bytes()
        if meta.get("encoding") == "text":
            text = raw.decode(meta.get("charset", "utf-8"), errors="replace")
            content = None
        else:
            text = None
            content = raw
        return HttpPayload(
            ok=True,
            status_code=int(meta.get("status", 200)),
            text=text,
            content=content,
            headers=dict(meta.get("headers") or {}),
            content_type=meta.get("content_type"),
            error=None,
            from_cache=True,
        )
    except Exception:
        return None


def _write_cache(
    body_path: Path,
    meta_path: Path,
    *,
    status: int,
    raw: bytes,
    encoding: str,
    charset: str,
    headers: dict[str, str],
    content_type: str | None,
) -> None:
    try:
        body_path.write_bytes(raw)
        meta_path.write_text(
            json.dumps(
                {
                    "status": status,
                    "encoding": encoding,
                    "charset": charset,
                    "headers": headers,
                    "content_type": content_type,
                }
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        log.debug("HTTP cache write skipped: %s", exc)


def _retry_delay(settings: Settings, attempt: int, headers: httpx.Headers) -> float:
    raw = headers.get("Retry-After") or headers.get("retry-after")
    if raw is not None:
        try:
            return min(float(raw), settings.arxiv_backoff_max_seconds)
        except (TypeError, ValueError):
            pass
    base = min(
        settings.arxiv_backoff_base_seconds * (2**attempt),
        settings.arxiv_backoff_max_seconds,
    )
    return base + random.uniform(0, settings.arxiv_backoff_base_seconds)


def _failure_envelope(
    message: str,
    *,
    error_type: str,
    url: str,
    status: int | None = None,
    recovery_options: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "error": message,
        "error_type": error_type,
        "http_status": status,
        "url": url,
        "recovery_options": list(recovery_options or []),
    }


async def get_bytes(
    url: str,
    *,
    settings: Settings | None = None,
    timeout: float | None = None,
    follow_redirects: bool = True,
    use_cache: bool | None = None,
    cache_endpoint: str = "get",
    max_body_bytes: int | None = None,
) -> HttpPayload:
    """GET ``url`` with shared UA, async retry on 429/5xx, optional disk cache."""
    settings = settings or load_settings()
    cache_on = settings.http_cache_enabled if use_cache is None else use_cache
    http_timeout = timeout if timeout is not None else settings.arxiv_http_timeout_seconds
    max_attempts = max(1, settings.arxiv_max_retries + 1)
    headers_req = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
    }

    if cache_on:
        body_path, meta_path = _cache_paths(settings, cache_endpoint, url)
        cached = _read_cache(body_path, meta_path)
        if cached is not None:
            return cached

    last_status: int | None = None
    last_message = "HTTP request failed"

    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(
                follow_redirects=follow_redirects,
                timeout=http_timeout,
            ) as client:
                resp = await client.get(url, headers=headers_req)
            last_status = resp.status_code
            ctype = resp.headers.get("content-type")
            hdrs = {k: v for k, v in resp.headers.items()}

            if _is_transient_status(resp.status_code) and attempt < max_attempts - 1:
                await asyncio.sleep(_retry_delay(settings, attempt, resp.headers))
                continue

            if resp.status_code >= 400:
                return HttpPayload(
                    ok=False,
                    status_code=resp.status_code,
                    text=None,
                    content=None,
                    headers=hdrs,
                    content_type=ctype,
                    error=_failure_envelope(
                        f"HTTP {resp.status_code} when fetching {url}",
                        error_type="HTTPStatusError",
                        url=url,
                        status=resp.status_code,
                        recovery_options=[
                            "Retry after a short delay.",
                            "Increase ARXIV_MCP_ARXIV_HTTP_TIMEOUT_SECONDS if needed.",
                        ],
                    ),
                )

            raw = resp.content
            if max_body_bytes is not None and len(raw) > max_body_bytes:
                return HttpPayload(
                    ok=False,
                    status_code=resp.status_code,
                    text=None,
                    content=None,
                    headers=hdrs,
                    content_type=ctype,
                    error=_failure_envelope(
                        f"Response body exceeds {max_body_bytes} byte cap",
                        error_type="ResponseTooLarge",
                        url=url,
                        status=resp.status_code,
                        recovery_options=["Use a smaller resource or raise the cap."],
                    ),
                )

            if cache_on and resp.status_code == 200:
                body_path, meta_path = _cache_paths(settings, cache_endpoint, url)
                _write_cache(
                    body_path,
                    meta_path,
                    status=resp.status_code,
                    raw=raw,
                    encoding="bytes",
                    charset="utf-8",
                    headers=hdrs,
                    content_type=ctype,
                )

            return HttpPayload(
                ok=True,
                status_code=resp.status_code,
                text=None,
                content=raw,
                headers=hdrs,
                content_type=ctype,
                error=None,
            )
        except httpx.TimeoutException:
            last_message = f"Timeout fetching {url}"
            if attempt >= max_attempts - 1:
                break
            await asyncio.sleep(_retry_delay(settings, attempt, httpx.Headers({})))
        except httpx.RequestError as exc:
            last_message = f"Request failed: {exc}"
            if attempt >= max_attempts - 1:
                break
            await asyncio.sleep(_retry_delay(settings, attempt, httpx.Headers({})))

    err_type = "ArxivRateLimit" if last_status == 429 else "HTTPError"
    recovery = [
        "Retry after a short delay.",
        "Set ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY for Semantic Scholar endpoints.",
    ]
    if last_status == 429:
        recovery.insert(
            0,
            "Remote API rate-limited; auto-retried with backoff.",
        )
    return HttpPayload(
        ok=False,
        status_code=last_status,
        text=None,
        content=None,
        headers={},
        content_type=None,
        error=_failure_envelope(
            f"{last_message} (after {max_attempts} attempt(s))",
            error_type=err_type,
            url=url,
            status=last_status,
            recovery_options=recovery,
        ),
    )


def _is_transient_status(code: int) -> bool:
    return code == 429 or code >= 500


async def get_text(
    url: str,
    *,
    settings: Settings | None = None,
    timeout: float | None = None,
    follow_redirects: bool = True,
    use_cache: bool | None = None,
    cache_endpoint: str = "text",
    accept: str = "text/html,application/xhtml+xml,text/plain,*/*",
    extra_headers: dict[str, str] | None = None,
) -> HttpPayload:
    """GET text body (cached separately from binary responses)."""
    settings = settings or load_settings()
    cache_on = settings.http_cache_enabled if use_cache is None else use_cache
    http_timeout = timeout if timeout is not None else settings.arxiv_http_timeout_seconds
    max_attempts = max(1, settings.arxiv_max_retries + 1)
    headers_req = {"User-Agent": USER_AGENT, "Accept": accept}
    if extra_headers:
        headers_req.update(extra_headers)

    if cache_on:
        body_path, meta_path = _cache_paths(settings, cache_endpoint, url)
        cached = _read_cache(body_path, meta_path)
        if cached is not None:
            return cached

    last_status: int | None = None
    last_message = "HTTP request failed"

    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(
                follow_redirects=follow_redirects,
                timeout=http_timeout,
            ) as client:
                resp = await client.get(url, headers=headers_req)
            last_status = resp.status_code
            ctype = resp.headers.get("content-type")
            hdrs = {k: v for k, v in resp.headers.items()}

            if _is_transient_status(resp.status_code) and attempt < max_attempts - 1:
                await asyncio.sleep(_retry_delay(settings, attempt, resp.headers))
                continue

            if resp.status_code >= 400:
                return HttpPayload(
                    ok=False,
                    status_code=resp.status_code,
                    text=None,
                    content=None,
                    headers=hdrs,
                    content_type=ctype,
                    error=_failure_envelope(
                        f"HTTP {resp.status_code} when fetching {url}",
                        error_type="HTTPStatusError",
                        url=url,
                        status=resp.status_code,
                    ),
                )

            text = resp.text
            if cache_on and resp.status_code == 200:
                body_path, meta_path = _cache_paths(settings, cache_endpoint, url)
                _write_cache(
                    body_path,
                    meta_path,
                    status=resp.status_code,
                    raw=text.encode("utf-8"),
                    encoding="text",
                    charset="utf-8",
                    headers=hdrs,
                    content_type=ctype,
                )

            return HttpPayload(
                ok=True,
                status_code=resp.status_code,
                text=text,
                content=None,
                headers=hdrs,
                content_type=ctype,
                error=None,
            )
        except httpx.TimeoutException:
            last_message = f"Timeout fetching {url}"
            if attempt >= max_attempts - 1:
                break
            await asyncio.sleep(_retry_delay(settings, attempt, httpx.Headers({})))
        except httpx.RequestError as exc:
            last_message = f"Request failed: {exc}"
            if attempt >= max_attempts - 1:
                break
            await asyncio.sleep(_retry_delay(settings, attempt, httpx.Headers({})))

    return HttpPayload(
        ok=False,
        status_code=last_status,
        text=None,
        content=None,
        headers={},
        content_type=None,
        error=_failure_envelope(
            f"{last_message} (after {max_attempts} attempt(s))",
            error_type="ArxivRateLimit" if last_status == 429 else "HTTPError",
            url=url,
            status=last_status,
        ),
    )
