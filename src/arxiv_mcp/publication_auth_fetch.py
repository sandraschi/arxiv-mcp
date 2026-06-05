"""Authenticated fetch for subscriber publications (cookie session)."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.publication_subscriptions import (
    PublicationCredentials,
    PublicationDef,
    assert_subscription_usable,
    load_credentials,
    resolve_publication,
)

log = logging.getLogger(__name__)

_FETCH_UA = (
    "arxiv-mcp-publication-reader/1.0 "
    "(licensed subscriber session; +https://arxiv.org/help/policies)"
)
_PAYWALL_MARKERS = re.compile(
    r"(subscribe to (continue|read)|sign in to continue|log\s*in to read|"
    r"you've reached your limit|register for free)",
    re.I,
)
_EXCERPT_CHARS = 480


def _looks_like_paywall(text: str) -> bool:
    if len(text.strip()) < 200:
        return True
    return bool(_PAYWALL_MARKERS.search(text[:4000]))


async def publication_auth_fetch(
    url: str,
    *,
    settings: Settings | None = None,
    publication: PublicationDef | None = None,
) -> dict[str, Any]:
    """Fetch URL with subscriber cookie when subscription is valid."""
    settings = settings or load_settings()
    defn = publication or resolve_publication(url, settings)
    if defn is None:
        return {"success": False, "error": "no_publication_match", "skipped": True}

    creds = load_credentials(defn)
    block = assert_subscription_usable(creds, warn_days=settings.publication_expiring_warn_days)
    if block is not None:
        return {"success": False, **block}

    cookie = creds.cookie or ""
    headers = {
        "User-Agent": _FETCH_UA,
        "Cookie": cookie,
        "Accept": "text/html,application/xhtml+xml",
    }
    timeout = float(settings.publication_fetch_timeout_seconds)

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers=headers,
        ) as client:
            resp = await client.get(url.strip())
    except httpx.HTTPError as exc:
        return {
            "success": False,
            "subscription_error": "fetch_failed",
            "publication": creds.publication_id,
            "message": f"{creds.name} authenticated fetch failed: {exc}",
            "silent_failure": False,
        }

    body = resp.text or ""
    if resp.status_code in (401, 403):
        return {
            "success": False,
            "subscription_error": "auth_rejected",
            "publication": creds.publication_id,
            "publication_name": creds.name,
            "http_status": resp.status_code,
            "message": (
                f"{creds.name} returned HTTP {resp.status_code} — "
                "cookie may be stale; re-export session cookie from browser."
            ),
            "silent_failure": False,
        }
    if resp.status_code >= 400:
        return {
            "success": False,
            "subscription_error": "http_error",
            "publication": creds.publication_id,
            "http_status": resp.status_code,
            "message": f"{creds.name} HTTP {resp.status_code}",
            "silent_failure": False,
        }
    if _looks_like_paywall(body):
        return {
            "success": False,
            "subscription_error": "paywall_detected",
            "publication": creds.publication_id,
            "publication_name": creds.name,
            "message": (
                f"{creds.name} still shows paywall/login — refresh "
                f"{creds.publication_id.upper()} cookie in .env"
            ),
            "silent_failure": False,
        }

    excerpt = re.sub(r"\s+", " ", body)[:_EXCERPT_CHARS]
    return {
        "success": True,
        "content": body,
        "excerpt": excerpt,
        "enriched": True,
        "enriched_via": "publication_auth",
        "publication": creds.publication_id,
        "publication_name": creds.name,
        "valid_till": creds.valid_till.isoformat() if creds.valid_till else None,
        "fetch_policy": "licensed_subscriber_cookie",
    }


async def try_publication_for_url(url: str, *, settings: Settings | None = None) -> dict[str, Any] | None:
    """Return fetch result if URL is a configured publication; None if unrelated."""
    settings = settings or load_settings()
    defn = resolve_publication(url, settings)
    if defn is None:
        return None
    creds = load_credentials(defn)
    from arxiv_mcp.publication_subscriptions import is_publication_configured, subscription_status

    if not is_publication_configured(creds):
        return None
    status = subscription_status(creds, warn_days=settings.publication_expiring_warn_days)
    if status in ("expired", "credentials_incomplete", "cookie_missing"):
        block = assert_subscription_usable(creds, warn_days=settings.publication_expiring_warn_days)
        return {"success": False, **(block or {})}
    return await publication_auth_fetch(url, settings=settings, publication=defn)
