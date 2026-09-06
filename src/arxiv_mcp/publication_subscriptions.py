"""Publication subscription credentials (NYT, WSJ, …) with loud expiry handling."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from arxiv_mcp.config import Settings, load_settings

log = logging.getLogger(__name__)

_STATUS_VALID = "valid"
_STATUS_EXPIRING_SOON = "expiring_soon"
_STATUS_EXPIRED = "expired"
_STATUS_NOT_CONFIGURED = "not_configured"
_STATUS_CREDENTIALS_INCOMPLETE = "credentials_incomplete"
_STATUS_COOKIE_MISSING = "cookie_missing"


@dataclass(frozen=True)
class PublicationDef:
    id: str
    name: str
    domains: tuple[str, ...]
    user_env: str
    password_env: str
    valid_till_env: str
    cookie_env: str


@dataclass
class PublicationCredentials:
    publication_id: str
    name: str
    user: str | None
    password: str | None
    valid_till: date | None
    cookie: str | None


def _repo_manifest_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "config" / "publication_subscriptions.json"
        if candidate.is_file():
            return candidate
    return here.parents[2] / "config" / "publication_subscriptions.json"


def load_publication_defs(settings: Settings | None = None) -> list[PublicationDef]:
    settings = settings or load_settings()
    paths: list[Path] = []
    if settings.publication_subscriptions_file:
        paths.append(Path(settings.publication_subscriptions_file))
    data_path = settings.resolved_data_dir() / "publication_subscriptions.json"
    if data_path.is_file():
        paths.append(data_path)
    paths.append(_repo_manifest_path())

    for path in paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, list):
            continue
        defs: list[PublicationDef] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            pid = str(item.get("id") or "").strip()
            if not pid:
                continue
            domains = tuple(d.strip().lower() for d in (item.get("domains") or []) if isinstance(d, str) and d.strip())
            defs.append(
                PublicationDef(
                    id=pid,
                    name=str(item.get("name") or pid),
                    domains=domains,
                    user_env=str(item.get("user_env") or f"ARXIV_MCP_PUB_{pid.upper()}_USER"),
                    password_env=str(item.get("password_env") or f"ARXIV_MCP_PUB_{pid.upper()}_PASSWORD"),
                    valid_till_env=str(item.get("valid_till_env") or f"ARXIV_MCP_PUB_{pid.upper()}_VALID_TILL"),
                    cookie_env=str(item.get("cookie_env") or f"ARXIV_MCP_PUB_{pid.upper()}_COOKIE"),
                )
            )
        if defs:
            return defs
    return []


def _parse_valid_till(raw: str | None) -> date | None:
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _env(name: str) -> str | None:
    val = os.environ.get(name, "").strip()
    return val or None


def load_credentials(defn: PublicationDef) -> PublicationCredentials:
    return PublicationCredentials(
        publication_id=defn.id,
        name=defn.name,
        user=_env(defn.user_env),
        password=_env(defn.password_env),
        valid_till=_parse_valid_till(_env(defn.valid_till_env)),
        cookie=_env(defn.cookie_env),
    )


def is_publication_configured(creds: PublicationCredentials) -> bool:
    return bool(creds.user or creds.password or creds.valid_till or creds.cookie)


def subscription_status(
    creds: PublicationCredentials,
    *,
    warn_days: int = 7,
    today: date | None = None,
) -> str:
    if not is_publication_configured(creds):
        return _STATUS_NOT_CONFIGURED
    if creds.valid_till is None:
        return _STATUS_CREDENTIALS_INCOMPLETE
    today = today or datetime.now(UTC).date()
    if creds.valid_till < today:
        return _STATUS_EXPIRED
    if (creds.valid_till - today).days <= max(0, warn_days):
        return _STATUS_EXPIRING_SOON
    if not creds.cookie:
        return _STATUS_COOKIE_MISSING
    return _STATUS_VALID


def resolve_publication(url: str, settings: Settings | None = None) -> PublicationDef | None:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return None
    for defn in load_publication_defs(settings):
        if host in defn.domains:
            return defn
        if host.startswith("www.") and host[4:] in defn.domains:
            return defn
    return None


def subscription_error_payload(
    creds: PublicationCredentials,
    status: str,
) -> dict[str, Any]:
    """Structured error - never silent when subscription is expired or unusable."""
    base: dict[str, Any] = {
        "subscription_error": status,
        "publication": creds.publication_id,
        "publication_name": creds.name,
        "valid_till": creds.valid_till.isoformat() if creds.valid_till else None,
        "silent_failure": False,
    }
    if status == _STATUS_EXPIRED:
        base["message"] = (
            f"{creds.name} subscription expired on {creds.valid_till}. "
            f"Renew and update {creds.publication_id.upper()} valid_till in .env - "
            "fetch blocked intentionally."
        )
        base["severity"] = "critical"
    elif status == _STATUS_CREDENTIALS_INCOMPLETE:
        base["message"] = (
            f"{creds.name}: set valid_till (YYYY-MM-DD) in .env - required so expired subs cannot fail silently."
        )
        base["severity"] = "error"
    elif status == _STATUS_COOKIE_MISSING:
        base["message"] = (
            f"{creds.name} subscription looks valid until {creds.valid_till} but "
            "subscriber cookie env is missing - export session cookie from browser."
        )
        base["severity"] = "error"
    elif status == _STATUS_EXPIRING_SOON:
        days = (creds.valid_till - datetime.now(UTC).date()).days if creds.valid_till else 0
        base["message"] = f"{creds.name} subscription expires in {days} day(s) ({creds.valid_till})."
        base["severity"] = "warning"
    else:
        base["message"] = f"{creds.name} subscription status: {status}"
    return base


def assert_subscription_usable(
    creds: PublicationCredentials,
    *,
    warn_days: int = 7,
) -> dict[str, Any] | None:
    """Return error dict if fetch must not proceed; None if OK to try auth fetch."""
    status = subscription_status(creds, warn_days=warn_days)
    if status == _STATUS_NOT_CONFIGURED:
        return None
    if status in (_STATUS_EXPIRED, _STATUS_CREDENTIALS_INCOMPLETE, _STATUS_COOKIE_MISSING):
        return subscription_error_payload(creds, status)
    return None


def list_subscription_statuses(settings: Settings | None = None) -> list[dict[str, Any]]:
    settings = settings or load_settings()
    warn = max(1, int(settings.publication_expiring_warn_days))
    rows: list[dict[str, Any]] = []
    for defn in load_publication_defs(settings):
        creds = load_credentials(defn)
        status = subscription_status(creds, warn_days=warn)
        rows.append(
            {
                "id": defn.id,
                "name": defn.name,
                "domains": list(defn.domains),
                "status": status,
                "valid_till": creds.valid_till.isoformat() if creds.valid_till else None,
                "has_user": bool(creds.user),
                "has_password": bool(creds.password),
                "has_cookie": bool(creds.cookie),
                "configured": is_publication_configured(creds),
                "env_keys": {
                    "user": defn.user_env,
                    "password": defn.password_env,
                    "valid_till": defn.valid_till_env,
                    "cookie": defn.cookie_env,
                },
                "usable": status == _STATUS_VALID,
                "expiring_soon": status == _STATUS_EXPIRING_SOON,
                "expired": status == _STATUS_EXPIRED,
            }
        )
    return rows


def expired_subscription_alerts(settings: Settings | None = None) -> list[dict[str, Any]]:
    from arxiv_mcp.readly_client import assert_readly_usable, readly_subscription_status

    settings = settings or load_settings()
    alerts: list[dict[str, Any]] = []
    readly_row = readly_subscription_status(settings)
    if readly_row.get("enabled"):
        readly_block = assert_readly_usable(settings)
        if readly_block is not None:
            alerts.append(
                {
                    "severity": readly_block.get("severity", "error"),
                    "code": readly_block.get("subscription_error", "readly_error").upper(),
                    "message": readly_block.get("message", "Readly subscription issue"),
                    "detail": {"publication": "readly", "valid_till": readly_row.get("valid_till")},
                }
            )
        elif readly_row.get("status") == "expiring_soon":
            alerts.append(
                {
                    "severity": "warning",
                    "code": "READLY_SUBSCRIPTION_EXPIRING",
                    "message": f"Readly subscription expires on {readly_row.get('valid_till')}",
                    "detail": {"publication": "readly"},
                }
            )
    for row in list_subscription_statuses(settings):
        if row["expired"]:
            alerts.append(
                {
                    "severity": "critical",
                    "code": "PUBLICATION_SUBSCRIPTION_EXPIRED",
                    "message": (
                        f"{row['name']} subscription expired ({row['valid_till']}) - "
                        "update .env valid_till after renewal"
                    ),
                    "detail": {"publication": row["id"], "valid_till": row["valid_till"]},
                }
            )
        elif row["status"] == _STATUS_CREDENTIALS_INCOMPLETE and row["configured"]:
            alerts.append(
                {
                    "severity": "error",
                    "code": "PUBLICATION_SUBSCRIPTION_INCOMPLETE",
                    "message": (f"{row['name']}: credentials present but valid_till missing in .env"),
                    "detail": {"publication": row["id"]},
                }
            )
        elif row["status"] == _STATUS_COOKIE_MISSING:
            alerts.append(
                {
                    "severity": "error",
                    "code": "PUBLICATION_COOKIE_MISSING",
                    "message": (f"{row['name']}: valid subscription dates set but cookie env empty"),
                    "detail": {"publication": row["id"], "valid_till": row["valid_till"]},
                }
            )
        elif row["expiring_soon"]:
            alerts.append(
                {
                    "severity": "warning",
                    "code": "PUBLICATION_SUBSCRIPTION_EXPIRING",
                    "message": f"{row['name']} subscription expires on {row['valid_till']}",
                    "detail": {"publication": row["id"], "valid_till": row["valid_till"]},
                }
            )
    return alerts
