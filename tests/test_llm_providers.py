"""Unified LLM provider registry, keystore, and proxy mapping."""

from __future__ import annotations

import json

import pytest

from arxiv_mcp import llm_providers
from arxiv_mcp.config import Settings


def _settings(tmp_path):
    return Settings(data_dir=tmp_path / "data")


def test_registry_shape():
    ids = [r["id"] for r in llm_providers.PROVIDERS]
    assert len(ids) == len(set(ids)) == 8
    for row in llm_providers.PROVIDERS:
        assert {"id", "label", "kind", "base_url", "chat_path", "models_path", "key_env", "curated"} <= set(row)
        assert row["kind"] in ("local", "cloud")
    clouds = [r for r in llm_providers.PROVIDERS if r["kind"] == "cloud"]
    assert {r["id"] for r in clouds} == {"openai", "anthropic", "deepseek", "openrouter", "meta"}
    for row in clouds:
        assert row["key_env"], row["id"]
        assert row["curated"], row["id"]


def test_deepseek_has_no_v1_prefix():
    row = llm_providers.require_provider("deepseek")
    assert row["base_url"] == "https://api.deepseek.com"
    assert row["chat_path"] == "/chat/completions"
    assert row["curated"][0] == "deepseek-v4-flash"


def test_meta_contributor_first():
    row = llm_providers.require_provider("meta")
    assert row["key_env"] == "MODEL_API_KEY"
    assert row["curated"][0] == "muse-spark-1.3-contributor"


def test_unknown_provider():
    with pytest.raises(ValueError, match="Unknown provider"):
        llm_providers.require_provider("nope")


def test_keystore_roundtrip_and_perms(tmp_path):
    settings = _settings(tmp_path)
    assert llm_providers.get_key("meta", settings) == ""
    llm_providers.save_key("meta", "sk-test", settings)
    assert llm_providers.get_key("meta", settings) == "sk-test"
    assert llm_providers.is_configured("meta", settings) is True
    assert llm_providers.keys_configured(settings)["meta"] is True
    assert llm_providers.delete_key("meta", settings) is True
    assert llm_providers.get_key("meta", settings) == ""
    assert llm_providers.delete_key("meta", settings) is False


def test_keystore_is_json_without_extra(tmp_path):
    settings = _settings(tmp_path)
    llm_providers.save_key("openai", "sk-x", settings)
    raw = json.loads(llm_providers.keystore_path(settings).read_text(encoding="utf-8"))
    assert raw == {"openai": "sk-x"}


def test_env_wins_over_keystore(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    llm_providers.save_key("openai", "sk-store", settings)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    assert llm_providers.get_key("openai", settings) == "sk-env"


def test_local_needs_no_key_but_not_configured_flag(tmp_path):
    settings = _settings(tmp_path)
    assert llm_providers.is_configured("ollama", settings) is True
    assert "ollama" not in llm_providers.keys_configured(settings)


def test_save_key_rejects_local_and_empty(tmp_path):
    settings = _settings(tmp_path)
    with pytest.raises(ValueError, match="no API key"):
        llm_providers.save_key("ollama", "x", settings)
    with pytest.raises(ValueError, match="Empty API key"):
        llm_providers.save_key("meta", "  ", settings)


def test_public_info_leaks_no_keys(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    llm_providers.save_key("meta", "sk-secret", settings)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-secret")
    blob = json.dumps(llm_providers.public_provider_info(settings))
    assert "sk-secret" not in blob
    assert "sk-env-secret" not in blob
    assert llm_providers.onboarding_state(settings)["clouds_configured"] == ["openai", "meta"]


def test_install_allowlist():
    with pytest.raises(ValueError, match="Allowed"):
        llm_providers.start_install("vllm")
    with pytest.raises(ValueError, match="Unknown install engine"):
        llm_providers.install_status("vllm")
    assert llm_providers.install_status("ollama")["state"] in ("idle", "running", "done", "error")


def test_anthropic_mapping():
    body = llm_providers._to_anthropic(
        "claude-sonnet-4-20250514",
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "yo"},
            {"role": "user", "content": "again"},
        ],
    )
    assert body["system"] == "sys"
    assert body["max_tokens"] == 1024
    assert [m["role"] for m in body["messages"]] == ["user", "assistant", "user"]
    text = llm_providers._from_anthropic({"content": [{"type": "text", "text": "a"}, {"type": "tool_use"}]})
    assert text == "a"
