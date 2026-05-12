from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from typing import Any

import httpx

from draftlens_api.providers.base import BaseLLMProvider
from draftlens_api.providers.dev_hints import MISSING_SINGLE_PROVIDER_ENV_HINT
from draftlens_api.providers.errors import OpenAIJobRateLimitExhausted, OpenAISkippedUnavailable
from draftlens_api.providers.llm_job_runtime import get_llm_job_runtime
from draftlens_api.providers.openai_params import openai_chat_temperature_params

logger = logging.getLogger(__name__)


def _local_openai_429_cap() -> int:
    """When no job runtime is attached, still allow a small number of 429 backoffs (tests / stray calls)."""
    raw = os.environ.get("DRAFTLENS_OPENAI_MAX_429_RETRIES", "").strip()
    if raw.isdigit():
        return max(1, int(raw))
    return 2


def _local_openai_max_backoff_seconds() -> float:
    raw = os.environ.get("DRAFTLENS_OPENAI_MAX_BACKOFF_SECONDS", "").strip()
    if raw:
        try:
            return max(0.5, float(raw))
        except ValueError:
            pass
    return 5.0


class OpenAIProviderAdapter(BaseLLMProvider):
    provider_key = "openai"

    async def _complete_once(self, *, model_id: str, system: str, user: str) -> str:
        if not self._api_key:
            raise RuntimeError(f"openai_not_configured — {MISSING_SINGLE_PROVIDER_ENV_HINT}")
        if not str(model_id).strip():
            raise RuntimeError("openai_missing_model_id")
        rt = get_llm_job_runtime()
        if rt and rt.openai_unavailable_for_job:
            raise OpenAISkippedUnavailable(rt.openai_skip_reason or "OPENAI_UNAVAILABLE_FOR_JOB")

        sys_c = (system or "").strip() or "You are a helpful assistant."
        usr_c = user if isinstance(user, str) else str(user)
        if not usr_c.strip():
            usr_c = "{}"
        payload: dict[str, Any] = {
            "model": str(model_id).strip(),
            "messages": [
                {"role": "system", "content": sys_c},
                {"role": "user", "content": usr_c},
            ],
            "response_format": {"type": "json_object"},
        }
        payload.update(openai_chat_temperature_params(model_id))
        headers = {"Authorization": f"Bearer {self._api_key}"}
        url = "https://api.openai.com/v1/chat/completions"

        local_429_left = _local_openai_429_cap()
        attempt = 0
        async with httpx.AsyncClient(timeout=180.0) as client:
            while True:
                if rt:
                    now = time.monotonic()
                    if rt.openai_cooldown_until_monotonic > now:
                        await asyncio.sleep(rt.openai_cooldown_until_monotonic - now + 0.02)
                r = await client.post(url, headers=headers, json=payload)
                if r.status_code == 429:
                    if rt:
                        rt.openai_429_budget_remaining -= 1
                        if rt.openai_429_budget_remaining < 0:
                            rt.openai_unavailable_for_job = True
                            rt.openai_skip_reason = "OPENAI_RATE_LIMITED"
                            raise OpenAIJobRateLimitExhausted("openai_429_budget_exhausted_for_job")
                    else:
                        local_429_left -= 1
                        if local_429_left < 0:
                            raise OpenAIJobRateLimitExhausted("openai_429_local_cap_exceeded")
                    cap = float(rt.openai_max_backoff_seconds) if rt else _local_openai_max_backoff_seconds()
                    backoff = min(2**attempt * 0.25 + random.random() * 0.35, cap)
                    if rt:
                        rt.openai_cooldown_until_monotonic = max(
                            rt.openai_cooldown_until_monotonic,
                            time.monotonic() + backoff,
                        )
                    logger.warning(
                        "openai_chat_completions_429 model=%s backoff_s=%.2f cap_s=%.2f job_budget=%s",
                        model_id,
                        backoff,
                        cap,
                        rt.openai_429_budget_remaining if rt else local_429_left,
                    )
                    await asyncio.sleep(backoff)
                    attempt += 1
                    continue

                if r.status_code == 400:
                    snippet = (r.text or "")[:800]
                    logger.warning(
                        "openai_chat_completions_400 model=%s response_format=json_object body=%s",
                        model_id,
                        snippet,
                    )
                    payload_retry = {k: v for k, v in payload.items() if k != "response_format"}
                    r = await client.post(url, headers=headers, json=payload_retry)

                r.raise_for_status()
                data = r.json()
                break

        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise RuntimeError("openai_unexpected_response")
        return content
