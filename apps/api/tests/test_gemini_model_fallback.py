"""Gemini adapter failover to DRAFTLENS_GEMINI_FALLBACK_MODEL."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import httpx

from draftlens_api.providers.gemini_adapter import GeminiProviderAdapter
from draftlens_api.providers.llm_job_runtime import LLMJobRuntime, attach_llm_job_runtime, reset_llm_job_runtime


def test_gemini_fallback_on_empty_candidates() -> None:
    calls = {"primary": 0, "fallback": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if "gemini-primary" in u:
            calls["primary"] += 1
            return httpx.Response(
                200,
                json={"candidates": []},
            )
        if "gemini-fallback" in u:
            calls["fallback"] += 1
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": '{"summary":"s","risks":[],"questions_for_peers":[],"issues":[]}'}
                                ]
                            }
                        }
                    ]
                },
            )
        return httpx.Response(404, json={"error": {"message": "unknown model"}})

    class _Client(httpx.AsyncClient):
        def __init__(self, *a, **kw):
            super().__init__(transport=httpx.MockTransport(handler), *a, **kw)

    async def inner() -> None:
        ad = GeminiProviderAdapter("test-key")
        rt = LLMJobRuntime(job_id="job-fb", gemini_fallback_model_id="gemini-fallback")
        tok = attach_llm_job_runtime(rt)
        try:
            with patch("draftlens_api.providers.gemini_adapter.httpx.AsyncClient", _Client):
                out = await ad._complete_once(model_id="gemini-primary", system="sys", user="{}")
            assert "issues" in out
            assert calls["primary"] == 1
            assert calls["fallback"] == 1
        finally:
            reset_llm_job_runtime(tok)

    asyncio.run(inner())
