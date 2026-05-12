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
from draftlens_api.providers.errors import (
    GeminiJobRateLimitExhausted,
    GeminiServiceUnavailableExhausted,
    GeminiSkippedUnavailable,
)
from draftlens_api.providers.llm_job_runtime import get_llm_job_runtime

logger = logging.getLogger(__name__)


def _local_429_cap() -> int:
    """When no job runtime is attached, still allow a small number of 429 backoffs (tests / stray calls)."""
    raw = os.environ.get("DRAFTLENS_GEMINI_MAX_429_RETRIES", "").strip()
    if raw.isdigit():
        return max(1, int(raw))
    return 2


def _local_max_backoff_seconds() -> float:
    raw = os.environ.get("DRAFTLENS_GEMINI_MAX_BACKOFF_SECONDS", "").strip()
    if raw:
        try:
            return max(0.5, float(raw))
        except ValueError:
            pass
    return 5.0


def _local_503_cap() -> int:
    raw = os.environ.get("DRAFTLENS_GEMINI_MAX_503_RETRIES", "").strip()
    if raw.isdigit():
        return max(1, int(raw))
    return 2


class GeminiProviderAdapter(BaseLLMProvider):
    provider_key = "google"

    async def _generate_json_payload_once(self, *, model_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Single generateContent round-trip including 429 absorption for this model_id."""
        if not self._api_key:
            raise RuntimeError(f"gemini_not_configured — {MISSING_SINGLE_PROVIDER_ENV_HINT}")
        rt = get_llm_job_runtime()
        if rt and rt.gemini_disabled_intentionally:
            raise GeminiSkippedUnavailable("disabled_by_config")
        if rt and rt.gemini_unavailable_for_job:
            raise GeminiSkippedUnavailable(
                "disabled_by_config" if rt.gemini_disabled_intentionally else "GEMINI_SKIPPED_FOR_REMAINDER_OF_JOB"
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
        local_429_left = _local_429_cap()
        local_503_left = _local_503_cap() if not rt else 0
        attempt = 0
        attempt503 = 0
        current_payload = payload
        while True:
            if rt:
                now = time.monotonic()
                if rt.gemini_cooldown_until_monotonic > now:
                    await asyncio.sleep(rt.gemini_cooldown_until_monotonic - now + 0.02)
            async with httpx.AsyncClient(timeout=180.0) as client:
                r = await client.post(f"{url}?key={self._api_key}", json=current_payload)
            if r.status_code == 429:
                if rt:
                    rt.gemini_429_budget_remaining -= 1
                    if rt.gemini_429_budget_remaining < 0:
                        rt.gemini_unavailable_for_job = True
                        rt.gemini_skip_reason = "GEMINI_RATE_LIMITED"
                        raise GeminiJobRateLimitExhausted("gemini_429_budget_exhausted_for_job")
                else:
                    local_429_left -= 1
                    if local_429_left < 0:
                        raise GeminiJobRateLimitExhausted("gemini_429_local_cap_exceeded")
                cap = float(rt.gemini_max_backoff_seconds) if rt else _local_max_backoff_seconds()
                backoff = min(2**attempt * 0.5 + random.random() * 0.35, cap)
                if rt:
                    rt.gemini_cooldown_until_monotonic = max(
                        rt.gemini_cooldown_until_monotonic,
                        time.monotonic() + backoff,
                    )
                logger.warning(
                    "gemini_generateContent_429 model=%s backoff_s=%.2f cap_s=%.2f job_budget=%s",
                    model_id,
                    backoff,
                    cap,
                    rt.gemini_429_budget_remaining if rt else local_429_left,
                )
                await asyncio.sleep(backoff)
                attempt += 1
                continue

            if r.status_code == 503:
                if rt:
                    rt.gemini_503_budget_remaining -= 1
                    if rt.gemini_503_budget_remaining < 0:
                        rt.gemini_unavailable_for_job = True
                        rt.gemini_skip_reason = "GEMINI_SERVICE_UNAVAILABLE"
                        raise GeminiServiceUnavailableExhausted("gemini_503_budget_exhausted_for_job")
                    cap = float(rt.gemini_max_backoff_seconds)
                    budget_left = rt.gemini_503_budget_remaining
                else:
                    local_503_left -= 1
                    if local_503_left < 0:
                        raise GeminiServiceUnavailableExhausted("gemini_503_local_cap_exceeded")
                    cap = _local_max_backoff_seconds()
                    budget_left = local_503_left
                backoff = min(2**attempt503 * 0.5 + random.random() * 0.35, cap)
                if rt:
                    rt.gemini_cooldown_until_monotonic = max(
                        rt.gemini_cooldown_until_monotonic,
                        time.monotonic() + backoff,
                    )
                logger.warning(
                    "gemini_generateContent_503 model=%s backoff_s=%.2f cap_s=%.2f job_budget=%s",
                    model_id,
                    backoff,
                    cap,
                    budget_left,
                )
                await asyncio.sleep(backoff)
                attempt503 += 1
                continue

            if r.status_code == 400:
                logger.warning(
                    "gemini_generateContent_400 model=%s body=%s",
                    model_id,
                    (r.text or "")[:800],
                )
                current_payload = {
                    "contents": payload["contents"],
                    "generationConfig": {"temperature": 0.1},
                }
                async with httpx.AsyncClient(timeout=180.0) as client:
                    r = await client.post(f"{url}?key={self._api_key}", json=current_payload)

            r.raise_for_status()
            return r.json()

    async def _complete_once(self, *, model_id: str, system: str, user: str) -> str:
        rt = get_llm_job_runtime()
        combined = (
            (system or "").strip()
            + "\n\nRespond with a single JSON object only. No markdown fences.\n\n"
            + (user if isinstance(user, str) else str(user))
        )
        if not combined.strip():
            combined = '{"summary":"empty","risks":[],"questions_for_peers":[],"issues":[]}'
        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": combined}],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        chain = [model_id]
        fb = (rt.gemini_fallback_model_id.strip() if rt and rt.gemini_fallback_model_id else "") or ""
        if fb and fb != model_id:
            chain.append(fb)

        last_empty: RuntimeError | None = None
        for idx, mid in enumerate(chain):
            try:
                data = await self._generate_json_payload_once(model_id=mid, payload=payload)
            except GeminiJobRateLimitExhausted:
                raise
            except GeminiServiceUnavailableExhausted:
                raise
            except GeminiSkippedUnavailable:
                raise
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code if exc.response is not None else 0
                if code == 404 and idx + 1 < len(chain):
                    logger.warning(
                        "gemini_model_not_found model=%s trying_fallback=%s",
                        mid,
                        chain[idx + 1],
                    )
                    continue
                raise

            candidates = data.get("candidates") or []
            if not candidates:
                err = RuntimeError("gemini_empty_candidates")
                if idx + 1 < len(chain):
                    logger.warning(
                        "gemini_empty_candidates model=%s trying_fallback=%s",
                        mid,
                        chain[idx + 1],
                    )
                    last_empty = err
                    continue
                raise err

            parts_out = (candidates[0].get("content") or {}).get("parts") or []
            texts: list[str] = []
            for p in parts_out:
                if isinstance(p, dict) and isinstance(p.get("text"), str):
                    texts.append(p["text"])
            return "\n".join(texts)

        if last_empty:
            raise last_empty
        raise RuntimeError("gemini_exhausted_model_chain")
