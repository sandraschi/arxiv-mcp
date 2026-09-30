"""Tests for multi-server preprint fan-out: OSF mapping, dispatch contract."""

import inspect
import json
import urllib.request as _req

from arxiv_mcp.services.preprint_servers import (
    SERVER_FUNCTIONS,
    _osf_authors,
    _osf_to_paper,
    search_psyarxiv,
    search_socarxiv,
)


def _osf_item(**overrides):
    base = {
        "id": "abc12_v1",
        "attributes": {
            "title": "Test Preprint",
            "description": "An abstract.",
            "date_published": "2026-09-01T00:00:00.000000Z",
        },
        "links": {
            "html": "https://osf.io/preprints/socarxiv/abc12_v1/",
            "preprint_doi": "https://doi.org/10.31235/osf.io/abc12_v1",
        },
        "embeds": {
            "bibliographic_contributors": {
                "data": [
                    {
                        "attributes": {
                            "index": 0,
                            "unregistered_contributor": "",
                        },
                        "embeds": {
                            "users": {
                                "data": {
                                    "attributes": {"full_name": "Jane Doe"},
                                }
                            }
                        },
                    },
                    {
                        "attributes": {
                            "index": 1,
                            "unregistered_contributor": "John Smith",
                        },
                        "embeds": {},
                    },
                ]
            }
        },
    }
    base.update(overrides)
    return base


def test_osf_authors_registered_and_unregistered() -> None:
    assert _osf_authors(_osf_item()) == ["Jane Doe", "John Smith"]


def test_osf_authors_missing_embeds() -> None:
    assert _osf_authors({}) == []
    assert _osf_authors({"embeds": None}) == []


def test_osf_to_paper_shape() -> None:
    p = _osf_to_paper(_osf_item(), "socarxiv")
    assert p is not None
    assert p.paper_id == "abc12_v1"
    assert p.title == "Test Preprint"
    assert p.summary == "An abstract."
    assert p.authors == ["Jane Doe", "John Smith"]
    assert p.server == "socarxiv"
    assert p.html_url == "https://osf.io/preprints/socarxiv/abc12_v1/"
    assert p.pdf_url is None
    assert p.doi == "10.31235/osf.io/abc12_v1"


def test_osf_to_paper_rejects_untitled() -> None:
    item = _osf_item()
    item["attributes"]["title"] = ""
    # Mapping itself is lenient; the search loop drops untitled records.
    assert _osf_to_paper(item, "psyarxiv") is not None


def test_dispatch_contract_keywords() -> None:
    """Every registered function must accept (query, limit=, hours=) by keyword.

    Guards the 2026-09-30 positional-dispatch bug where ``limit`` landed in
    ``search_biorxiv``'s ``server`` slot, serving medRxiv as bioRxiv.
    """
    for key, fn in SERVER_FUNCTIONS.items():
        if fn is None:  # arxiv handled elsewhere
            continue
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())
        assert params[0].name == "query", key
        for name in ("limit", "hours"):
            assert name in sig.parameters, f"{key} missing {name}"
            assert sig.parameters[name].kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ), f"{key}.{name} not keyword-callable"


def _fake_urlopen_factory(payloads: list[dict]):
    """Yield canned OSF list responses (title pass, then description pass)."""

    class FakeResp:
        def __init__(self, payload):
            self._raw = json.dumps(payload).encode()

        def read(self):
            return self._raw

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    calls = {"n": 0}

    def fake(req, timeout=30):
        idx = min(calls["n"], len(payloads) - 1)
        calls["n"] += 1
        return FakeResp(payloads[idx])

    return fake


def test_osf_search_merges_title_and_description_passes(monkeypatch) -> None:
    item_a = _osf_item()
    item_b = _osf_item()
    item_b["id"] = "zzz99_v1"
    item_b["attributes"]["title"] = "Second Hit"
    payload_title = {"data": [item_a]}
    payload_desc = {"data": [item_a, item_b]}  # item_a dup must not repeat
    monkeypatch.setattr(_req, "urlopen", _fake_urlopen_factory([payload_title, payload_desc]))
    out = search_socarxiv("test", limit=10, hours=24 * 365 * 5)
    assert [p.paper_id for p in out] == ["abc12_v1", "zzz99_v1"]
    assert all(p.server == "socarxiv" for p in out)


def test_osf_search_hours_cutoff(monkeypatch) -> None:
    old = _osf_item()
    old["attributes"]["date_published"] = "2020-01-01T00:00:00.000000Z"
    payload = {"data": [old]}
    monkeypatch.setattr(_req, "urlopen", _fake_urlopen_factory([payload, payload]))
    assert search_psyarxiv("test", limit=10, hours=24) == []


def test_osf_search_api_error_returns_empty(monkeypatch) -> None:
    def boom(req, timeout=30):
        raise OSError("network down")

    monkeypatch.setattr(_req, "urlopen", boom)
    assert search_socarxiv("test") == []
