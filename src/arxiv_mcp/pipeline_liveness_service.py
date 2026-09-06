"""Pipeline liveness for the code-hunt / open-weight tracking loop."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from arxiv_mcp.config import Settings, load_settings

log = logging.getLogger(__name__)


async def check_pipeline_liveness(
    *,
    stale_hours: int = 48,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Alert when code-hunt digests are stale or aiwatcher push target is down."""
    settings = settings or load_settings()
    stale_hours = max(1, int(stale_hours))
    stale_seconds = stale_hours * 3600
    alerts: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    hunt_dir = settings.resolved_data_dir() / "codehunt"
    digests = sorted(
        hunt_dir.glob("digest_codehunt_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not digests:
        alerts.append(
            {
                "severity": "warning",
                "code": "CODEHUNT_NEVER_RUN",
                "message": ("No code-hunt digest on disk - run run_codehunt_scan_tool or install_codehunt_tasks.ps1"),
                "detail": {"digest_dir": str(hunt_dir)},
            }
        )
        checks.append({"name": "codehunt_last_digest", "ok": False, "age_hours": None})
    else:
        latest = digests[0]
        age_s = time.time() - latest.stat().st_mtime
        age_h = round(age_s / 3600, 1)
        ok = age_s <= stale_seconds
        checks.append(
            {
                "name": "codehunt_last_digest",
                "ok": ok,
                "age_hours": age_h,
                "path": str(latest),
            }
        )
        if not ok:
            alerts.append(
                {
                    "severity": "critical",
                    "code": "CODEHUNT_DIGEST_STALE",
                    "message": (
                        f"Last code-hunt digest is {age_h}h old (threshold {stale_hours}h) - scan loop may be dead"
                    ),
                    "detail": {"path": str(latest), "age_hours": age_h},
                }
            )

    base = (settings.aiwatcher_base_url or "").strip()
    if base:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{base.rstrip('/')}/api/health")
            ok = resp.status_code == 200
            checks.append(
                {
                    "name": "aiwatcher_health",
                    "ok": ok,
                    "url": base,
                    "status_code": resp.status_code,
                }
            )
            if not ok:
                alerts.append(
                    {
                        "severity": "critical",
                        "code": "AIWATCHER_UNHEALTHY",
                        "message": f"aiwatcher health check failed ({resp.status_code})",
                        "detail": {"url": base},
                    }
                )
        except httpx.HTTPError as exc:
            checks.append({"name": "aiwatcher_health", "ok": False, "url": base})
            alerts.append(
                {
                    "severity": "critical",
                    "code": "AIWATCHER_UNREACHABLE",
                    "message": f"Cannot reach aiwatcher at {base}: {exc}",
                    "detail": {"url": base},
                }
            )

    from arxiv_mcp.publication_subscriptions import expired_subscription_alerts
    from arxiv_mcp.readly_client import readly_enabled, readly_health

    pub_alerts = expired_subscription_alerts(settings)
    if pub_alerts:
        alerts.extend(pub_alerts)
        checks.append(
            {
                "name": "publication_subscriptions",
                "ok": not any(a.get("severity") == "critical" for a in pub_alerts),
                "count": len(pub_alerts),
            }
        )

    if readly_enabled(settings):
        readly_probe = await readly_health(settings)
        checks.append(
            {
                "name": "readly_mcp_health",
                "ok": readly_probe.get("ok") is True,
                "url": settings.readly_mcp_url,
            }
        )
        if not readly_probe.get("ok"):
            alerts.append(
                {
                    "severity": "warning",
                    "code": "READLY_MCP_UNREACHABLE",
                    "message": f"readly-mcp not reachable: {readly_probe.get('error')}",
                    "detail": {"url": settings.readly_mcp_url},
                }
            )

    healthy = len([a for a in alerts if a.get("severity") == "critical"]) == 0
    if alerts:
        for a in alerts:
            log.warning("Pipeline liveness [%s]: %s", a.get("code"), a.get("message"))

    return {
        "success": True,
        "healthy": healthy,
        "service": "arxiv-mcp",
        "stale_hours": stale_hours,
        "aiwatcher_base_url": base or None,
        "checks": checks,
        "alerts": alerts,
    }
