"""Gemini default model, env overrides, and dev vs prod runtime caps."""

from __future__ import annotations

import json

import pytest

from draftlens_api.config import _DEFAULT_MODEL_ROUTING, get_provider_env, get_settings
from draftlens_api.providers.llm_job_runtime import build_llm_job_runtime
from draftlens_api.routing.model_registry import ModelRegistry


def test_default_routing_gemini_reviewer_is_flash_lite() -> None:
    ref = _DEFAULT_MODEL_ROUTING["model_routing"]["consistency_parser_model"]
    assert ref == "google/gemini-3.1-flash-lite"


def test_model_registry_respects_draftlens_gemini_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_SESSION_SECRET", "x" * 40)
    monkeypatch.setenv("DRAFTLENS_GEMINI_MODEL", "gemini-custom-test")
    get_settings.cache_clear()
    try:
        reg = ModelRegistry.from_settings(get_settings(), get_provider_env())
        assert reg.assignment().consistency_parser.model_id == "gemini-custom-test"
    finally:
        get_settings.cache_clear()


def test_build_llm_job_runtime_dev_caps_retries_and_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_SESSION_SECRET", "x" * 40)
    monkeypatch.setenv("DRAFTLENS_ENVIRONMENT", "development")
    monkeypatch.delenv("DRAFTLENS_GEMINI_MAX_429_RETRIES", raising=False)
    monkeypatch.delenv("DRAFTLENS_GEMINI_MAX_503_RETRIES", raising=False)
    monkeypatch.delenv("DRAFTLENS_GEMINI_MAX_BACKOFF_SECONDS", raising=False)
    monkeypatch.delenv("DRAFTLENS_OPENAI_MAX_429_RETRIES", raising=False)
    monkeypatch.delenv("DRAFTLENS_OPENAI_MAX_BACKOFF_SECONDS", raising=False)
    get_settings.cache_clear()
    try:
        rt = build_llm_job_runtime("j-dev", get_settings())
        assert rt.gemini_429_budget_remaining == 2
        assert rt.gemini_503_budget_remaining == 2
        assert rt.gemini_max_backoff_seconds == 5.0
        assert rt.openai_429_budget_remaining == 2
        assert rt.openai_max_backoff_seconds == 5.0
    finally:
        get_settings.cache_clear()


def test_build_llm_job_runtime_production_uses_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_SESSION_SECRET", "x" * 40)
    monkeypatch.setenv("DRAFTLENS_ENVIRONMENT", "production")
    monkeypatch.delenv("DRAFTLENS_GEMINI_MAX_429_RETRIES", raising=False)
    monkeypatch.delenv("DRAFTLENS_GEMINI_MAX_503_RETRIES", raising=False)
    monkeypatch.delenv("DRAFTLENS_GEMINI_MAX_BACKOFF_SECONDS", raising=False)
    monkeypatch.delenv("DRAFTLENS_OPENAI_MAX_429_RETRIES", raising=False)
    monkeypatch.delenv("DRAFTLENS_OPENAI_MAX_BACKOFF_SECONDS", raising=False)
    get_settings.cache_clear()
    try:
        rt = build_llm_job_runtime("j-prod", get_settings())
        assert rt.gemini_429_budget_remaining == 8
        assert rt.gemini_503_budget_remaining == 8
        assert rt.gemini_max_backoff_seconds == 90.0
        assert rt.openai_429_budget_remaining == 8
        assert rt.openai_max_backoff_seconds == 90.0
    finally:
        get_settings.cache_clear()


def test_model_routing_json_can_override_gemini_until_env_model_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_SESSION_SECRET", "x" * 40)
    monkeypatch.delenv("DRAFTLENS_GEMINI_MODEL", raising=False)
    mr = {
        "model_routing": {
            **_DEFAULT_MODEL_ROUTING["model_routing"],
            "consistency_parser_model": "google/gemini-legacy-from-json",
        }
    }
    monkeypatch.setenv("MODEL_ROUTING_JSON", json.dumps(mr))
    get_settings.cache_clear()
    try:
        reg = ModelRegistry.from_settings(get_settings(), get_provider_env())
        assert reg.assignment().consistency_parser.model_id == "gemini-legacy-from-json"
    finally:
        get_settings.cache_clear()
