"""HTTP resilience: arXiv API retry and structured failure envelopes."""

from __future__ import annotations

from unittest.mock import patch

from arxiv_mcp.config import Settings
from arxiv_mcp.http_policy import arxiv_retry


class _Resp429:
    status_code = 429

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}


class Http429(Exception):
    def __init__(self) -> None:
        self.response = _Resp429()


def test_arxiv_retry_429_then_success() -> None:
    settings = Settings(
        arxiv_max_retries=3,
        arxiv_backoff_base_seconds=0.01,
        arxiv_backoff_max_seconds=0.05,
    )
    calls = 0

    def fn() -> str:
        nonlocal calls
        calls += 1
        if calls < 2:
            raise Http429()
        return "payload"

    with patch("arxiv_mcp.http_policy.time.sleep", lambda _s: None):
        result = arxiv_retry(settings, fn)

    assert result == "payload"
    assert calls == 2


def test_arxiv_retry_persistent_429_returns_envelope() -> None:
    settings = Settings(
        arxiv_max_retries=2,
        arxiv_backoff_base_seconds=0.01,
        arxiv_backoff_max_seconds=0.05,
    )

    def fn() -> str:
        raise Http429()

    with patch("arxiv_mcp.http_policy.time.sleep", lambda _s: None):
        result = arxiv_retry(settings, fn)

    assert isinstance(result, dict)
    assert result["success"] is False
    assert result["error_type"] == "ArxivRateLimit"
    assert result.get("recovery_options")


def test_arxiv_retry_honors_retry_after() -> None:
    settings = Settings(
        arxiv_max_retries=2,
        arxiv_backoff_base_seconds=10.0,
        arxiv_backoff_max_seconds=30.0,
    )
    calls = 0
    slept: list[float] = []

    class RespRetryAfter:
        status_code = 429
        headers = {"Retry-After": "2"}

    class Err(Exception):
        def __init__(self) -> None:
            self.response = RespRetryAfter()

    def fn() -> str:
        nonlocal calls
        calls += 1
        if calls < 2:
            raise Err()
        return "ok"

    with patch("arxiv_mcp.http_policy.time.sleep", slept.append):
        assert arxiv_retry(settings, fn) == "ok"

    assert len(slept) == 1
    assert slept[0] <= 2.5 + settings.arxiv_backoff_base_seconds
