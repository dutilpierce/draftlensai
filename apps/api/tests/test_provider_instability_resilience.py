"""OpenAI 429 and Gemini 503 resilience, job-level circuit breakers, and scheduling skips."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from draftlens_api.providers.errors import (
    GeminiServiceUnavailableExhausted,
    GeminiSkippedUnavailable,
    OpenAIJobRateLimitExhausted,
    OpenAISkippedUnavailable,
)
from draftlens_api.providers.gemini_adapter import GeminiProviderAdapter
from draftlens_api.providers.llm_job_runtime import LLMJobRuntime, attach_llm_job_runtime, reset_llm_job_runtime
from draftlens_api.providers.openai_adapter import OpenAIProviderAdapter


def test_openai_429_retries_then_returns_json() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] <= 2:
            return httpx.Response(429, json={"error": {"message": "rate limit"}})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"a":1}'}}]},
        )

    class _Client(httpx.AsyncClient):
        def __init__(self, *a, **kw):
            super().__init__(transport=httpx.MockTransport(handler), *a, **kw)

    async def inner() -> None:
        ad = OpenAIProviderAdapter("sk-test")
        rt = LLMJobRuntime(job_id="job-o1", openai_429_budget_remaining=8, openai_max_backoff_seconds=90.0)
        tok = attach_llm_job_runtime(rt)
        try:
            with (
                patch("draftlens_api.providers.openai_adapter.httpx.AsyncClient", _Client),
                patch("draftlens_api.providers.openai_adapter.asyncio.sleep", new_callable=AsyncMock),
            ):
                out = await ad._complete_once(model_id="gpt-4.1", system="sys", user="{}")
            assert '"a":1' in out or "a" in out
            assert calls["n"] == 3
            assert rt.openai_429_budget_remaining == 6
        finally:
            reset_llm_job_runtime(tok)

    asyncio.run(inner())


def test_openai_429_exhaustion_marks_unavailable_for_job() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "rate limit"}})

    class _Client(httpx.AsyncClient):
        def __init__(self, *a, **kw):
            super().__init__(transport=httpx.MockTransport(handler), *a, **kw)

    async def inner() -> None:
        ad = OpenAIProviderAdapter("sk-test")
        rt = LLMJobRuntime(job_id="job-o2", openai_429_budget_remaining=0)
        tok = attach_llm_job_runtime(rt)
        try:
            with (
                patch("draftlens_api.providers.openai_adapter.httpx.AsyncClient", _Client),
                patch("draftlens_api.providers.openai_adapter.asyncio.sleep", new_callable=AsyncMock),
            ):
                with pytest.raises(OpenAIJobRateLimitExhausted):
                    await ad._complete_once(model_id="gpt-4.1", system="s", user="{}")
            assert rt.openai_unavailable_for_job is True
            assert rt.openai_skip_reason == "OPENAI_RATE_LIMITED"
            with pytest.raises(OpenAISkippedUnavailable):
                await ad._complete_once(model_id="gpt-4.1", system="s", user="{}")
        finally:
            reset_llm_job_runtime(tok)

    asyncio.run(inner())


def test_gemini_503_retries_then_returns_json() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] <= 2:
            return httpx.Response(503, json={"error": {"message": "unavailable"}})
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": '{"summary":"s","risks":[],"questions_for_peers":[],"issues":[]}'}]
                        }
                    }
                ]
            },
        )

    class _Client(httpx.AsyncClient):
        def __init__(self, *a, **kw):
            super().__init__(transport=httpx.MockTransport(handler), *a, **kw)

    async def inner() -> None:
        ad = GeminiProviderAdapter("test-key")
        rt = LLMJobRuntime(job_id="job-g503", gemini_503_budget_remaining=8, gemini_max_backoff_seconds=90.0)
        tok = attach_llm_job_runtime(rt)
        try:
            with (
                patch("draftlens_api.providers.gemini_adapter.httpx.AsyncClient", _Client),
                patch("draftlens_api.providers.gemini_adapter.asyncio.sleep", new_callable=AsyncMock),
            ):
                out = await ad._complete_once(model_id="gemini-2.0-flash", system="sys", user="{}")
            assert "issues" in out
            assert calls["n"] == 3
            assert rt.gemini_503_budget_remaining == 6
        finally:
            reset_llm_job_runtime(tok)

    asyncio.run(inner())


def test_gemini_503_exhaustion_marks_unavailable_for_job() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"message": "unavailable"}})

    class _Client(httpx.AsyncClient):
        def __init__(self, *a, **kw):
            super().__init__(transport=httpx.MockTransport(handler), *a, **kw)

    async def inner() -> None:
        ad = GeminiProviderAdapter("test-key")
        rt = LLMJobRuntime(job_id="job-g503b", gemini_503_budget_remaining=0)
        tok = attach_llm_job_runtime(rt)
        try:
            with (
                patch("draftlens_api.providers.gemini_adapter.httpx.AsyncClient", _Client),
                patch("draftlens_api.providers.gemini_adapter.asyncio.sleep", new_callable=AsyncMock),
            ):
                with pytest.raises(GeminiServiceUnavailableExhausted):
                    await ad._complete_once(model_id="gemini-2.0-flash", system="s", user="{}")
            assert rt.gemini_unavailable_for_job is True
            assert rt.gemini_skip_reason == "GEMINI_SERVICE_UNAVAILABLE"
            with pytest.raises(GeminiSkippedUnavailable):
                await ad._complete_once(model_id="gemini-2.0-flash", system="s", user="{}")
        finally:
            reset_llm_job_runtime(tok)

    asyncio.run(inner())


def test_convergence_configured_role_count_skips_unavailable_openai_and_gemini() -> None:
    from types import SimpleNamespace

    from draftlens_api.engine.iterative_convergence import _convergence_configured_role_count

    class _Ad:
        configured = True

    class _Reg:
        def adapter(self, _rm: object) -> _Ad:
            return _Ad()

    assign = SimpleNamespace(
        author_intent=object(),
        skeptical_reviewer=object(),
        consistency_parser=object(),
    )
    rt = LLMJobRuntime(job_id="j-skip", openai_unavailable_for_job=True, gemini_unavailable_for_job=True)
    tok = attach_llm_job_runtime(rt)
    try:
        assert _convergence_configured_role_count(_Reg(), assign) == 1
    finally:
        reset_llm_job_runtime(tok)
