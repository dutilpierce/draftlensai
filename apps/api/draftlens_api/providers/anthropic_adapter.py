from __future__ import annotations

import httpx

from draftlens_api.providers.base import BaseLLMProvider
from draftlens_api.providers.dev_hints import MISSING_SINGLE_PROVIDER_ENV_HINT


class AnthropicProviderAdapter(BaseLLMProvider):
    provider_key = "anthropic"

    async def _complete_once(self, *, model_id: str, system: str, user: str) -> str:
        if not self._api_key:
            raise RuntimeError(f"anthropic_not_configured — {MISSING_SINGLE_PROVIDER_ENV_HINT}")
        payload = {
            "model": model_id,
            "max_tokens": 8192,
            "temperature": 0.1,
            "system": system + "\n\nRespond with a single JSON object only. No markdown fences.",
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
        parts = data.get("content", [])
        texts: list[str] = []
        for p in parts:
            if isinstance(p, dict) and p.get("type") == "text":
                t = p.get("text")
                if isinstance(t, str):
                    texts.append(t)
        return "\n".join(texts)
