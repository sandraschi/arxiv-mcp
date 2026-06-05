"""Publication subscription credentials and expiry."""

from __future__ import annotations

import os
from datetime import date

import pytest

from arxiv_mcp.config import Settings
from arxiv_mcp.publication_auth_fetch import try_publication_for_url
from arxiv_mcp.publication_subscriptions import (
    assert_subscription_usable,
    expired_subscription_alerts,
    load_credentials,
    load_publication_defs,
    resolve_publication,
    subscription_status,
)


@pytest.fixture
def nyt_env(monkeypatch):
    monkeypatch.setenv("ARXIV_MCP_PUB_NYT_USER", "reader@example.com")
    monkeypatch.setenv("ARXIV_MCP_PUB_NYT_PASSWORD", "secret")
    monkeypatch.setenv("ARXIV_MCP_PUB_NYT_VALID_TILL", "2099-12-31")
    monkeypatch.setenv("ARXIV_MCP_PUB_NYT_COOKIE", "NYT-S=test")


def test_load_publication_defs_includes_nyt():
    defs = load_publication_defs()
    ids = {d.id for d in defs}
    assert "nyt" in ids


def test_resolve_nyt_domain():
    defn = resolve_publication("https://www.nytimes.com/2024/01/01/tech/ai.html")
    assert defn is not None
    assert defn.id == "nyt"


def test_expired_subscription_blocks_loudly(nyt_env, monkeypatch):
    monkeypatch.setenv("ARXIV_MCP_PUB_NYT_VALID_TILL", "2020-01-01")
    defs = load_publication_defs()
    nyt = next(d for d in defs if d.id == "nyt")
    creds = load_credentials(nyt)
    assert subscription_status(creds) == "expired"
    err = assert_subscription_usable(creds)
    assert err is not None
    assert err["subscription_error"] == "expired"
    assert err["silent_failure"] is False


def test_missing_valid_till_is_incomplete(nyt_env, monkeypatch):
    monkeypatch.delenv("ARXIV_MCP_PUB_NYT_VALID_TILL", raising=False)
    defs = load_publication_defs()
    nyt = next(d for d in defs if d.id == "nyt")
    creds = load_credentials(nyt)
    assert subscription_status(creds) == "credentials_incomplete"


def test_cookie_missing_when_valid_dates(nyt_env, monkeypatch):
    monkeypatch.delenv("ARXIV_MCP_PUB_NYT_COOKIE", raising=False)
    defs = load_publication_defs()
    nyt = next(d for d in defs if d.id == "nyt")
    creds = load_credentials(nyt)
    assert subscription_status(creds) == "cookie_missing"


def test_expired_alerts_critical(nyt_env, monkeypatch):
    monkeypatch.setenv("ARXIV_MCP_PUB_NYT_VALID_TILL", "2020-01-01")
    alerts = expired_subscription_alerts()
    codes = {a["code"] for a in alerts}
    assert "PUBLICATION_SUBSCRIPTION_EXPIRED" in codes


@pytest.mark.asyncio
async def test_try_publication_expired_returns_error_not_skip(nyt_env, monkeypatch):
    monkeypatch.setenv("ARXIV_MCP_PUB_NYT_VALID_TILL", "2020-01-01")
    out = await try_publication_for_url("https://www.nytimes.com/article.html")
    assert out is not None
    assert out.get("success") is False
    assert out.get("subscription_error") == "expired"
