"""Shared HTTP policy: User-Agent, arXiv API retry with backoff."""

from __future__ import annotations

import random
import time
from typing import Any, Callable, TypeVar

from arxiv_mcp.config import Settings
from arxiv_mcp.http import USER_AGENT

T = TypeVar("T")


class ArxivApiFailure(Exception):
    """Raised when arXiv API calls fail after retries (carries structured envelope)."""

    def __init__(self, envelope: dict[str, Any]):
        self.envelope = envelope
        super().__init__(envelope.get("error", "arXiv API error"))


def arxiv_tool_error(
    message: str,
    *,
    error_type: str = "ArxivRateLimit",
    recovery_options: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "message": f"arXiv API error: {message}",
        "error": message,
        "error_type": error_type,
        "recovery_options": list(recovery_options or []),
    }


def _status_code(exc: BaseException) -> int | None:
    resp = getattr(exc, "response", None)
    if resp is not None:
        return getattr(resp, "status_code", None)
    return getattr(exc, "status_code", None)


def _retry_after_seconds(exc: BaseException) -> float | None:
    resp = getattr(exc, "response", None)
    if resp is None:
        return None
    raw = None
    headers = getattr(resp, "headers", None)
    if headers is not None:
        raw = headers.get("Retry-After") or headers.get("retry-after")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, (LookupError, ValueError, ArxivApiFailure)):
        return False
    try:
        import arxiv

        if isinstance(exc, (arxiv.HTTPError, arxiv.UnexpectedEmptyPageError)):
            return True
    except ImportError:
        pass
    code = _status_code(exc)
    if code is not None and (code == 429 or code >= 500):
        return True
    name = type(exc).__name__.lower()
    if "timeout" in name or "connection" in name:
        return True
    mod = type(exc).__module__ or ""
    if mod.startswith("requests.") or mod.startswith("urllib"):
        return True
    return False


def apply_arxiv_user_agent(client: Any) -> None:
    """Set descriptive UA on the arxiv client's requests session."""
    try:
        session = client._session
        session.headers["User-Agent"] = USER_AGENT
    except Exception:
        pass


def arxiv_retry(settings: Settings, fn: Callable[[], T]) -> T | dict[str, Any]:
    """Run sync arXiv API work with exponential backoff; return tool_error dict on exhaustion."""
    max_attempts = max(1, settings.arxiv_max_retries + 1)
    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if isinstance(exc, LookupError):
                raise
            if not _is_transient(exc) or attempt >= max_attempts - 1:
                break
            ra = _retry_after_seconds(exc)
            if ra is not None:
                delay = min(ra, settings.arxiv_backoff_max_seconds)
            else:
                delay = min(
                    settings.arxiv_backoff_base_seconds * (2**attempt),
                    settings.arxiv_backoff_max_seconds,
                )
            delay += random.uniform(0, settings.arxiv_backoff_base_seconds)
            time.sleep(delay)

    code = _status_code(last_exc) if last_exc else None
    err_type = "ArxivRateLimit" if code == 429 else "ArxivHTTPError"
    delay_hint = int(settings.client_delay_seconds)
    return arxiv_tool_error(
        (
            f"arXiv API request failed after {max_attempts} attempt(s)"
            + (f" (last HTTP {code})" if code else "")
            + f": {last_exc}"
        ),
        error_type=err_type,
        recovery_options=[
            "arXiv is rate-limiting; auto-retries honor a courtesy delay between calls.",
            f"Wait ~{delay_hint}s and retry, or set ARXIV_MCP_CLIENT_DELAY_SECONDS higher (default 3.0).",
            "For metadata, try getPaper (HTML) if the API path keeps failing.",
        ],
    )
