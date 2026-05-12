from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from draftlens_api.providers.errors import (
    GeminiJobRateLimitExhausted,
    GeminiServiceUnavailableExhausted,
    GeminiSkippedUnavailable,
    OpenAIJobRateLimitExhausted,
    OpenAISkippedUnavailable,
)
from draftlens_api.providers.structured_output import (
    GEMINI_DISABLED,
    GEMINI_RATE_LIMITED,
    GEMINI_SERVICE_UNAVAILABLE,
    GEMINI_UNAVAILABLE,
    INVALID_JSON,
    OPENAI_RATE_LIMITED,
    OPENAI_UNAVAILABLE,
    PROVIDER_ERROR,
    RATE_LIMIT_EXHAUSTED,
    SCHEMA_MISMATCH,
    parse_as_object,
    strict_json_user_suffix,
)

logger = logging.getLogger(__name__)


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse first JSON object from model text (optionally inside a fenced block)."""
    pr = parse_as_object(text)
    if pr.payload is None:
        raise ValueError(pr.error_code or "json_parse_failed")
    return pr.payload


class BaseLLMProvider(ABC):
    """All providers must return JSON-only responses; parsing stays inside adapters."""

    provider_key: str

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    @abstractmethod
    async def _complete_once(self, *, model_id: str, system: str, user: str) -> str:
        """Provider-specific network call; returns raw assistant text."""

    async def complete_json_with_retry(
        self, *, model_id: str, system: str, user: str
    ) -> tuple[dict[str, Any] | None, str | None]:
        """
        Robust JSON object completion with one strict reprompt on parse failure.
        Returns (payload, error_code_or_message).
        """
        try:
            raw = await self._complete_once(model_id=model_id, system=system, user=user)
        except GeminiJobRateLimitExhausted as exc:
            logger.warning("%s completion rate-limited (job budget): %s", self.provider_key, exc)
            code = GEMINI_RATE_LIMITED if self.provider_key == "google" else RATE_LIMIT_EXHAUSTED
            return None, code
        except GeminiServiceUnavailableExhausted as exc:
            logger.warning("%s completion service unavailable (job budget): %s", self.provider_key, exc)
            return None, (GEMINI_SERVICE_UNAVAILABLE if self.provider_key == "google" else RATE_LIMIT_EXHAUSTED)
        except OpenAIJobRateLimitExhausted as exc:
            logger.warning("%s completion rate-limited (job budget): %s", self.provider_key, exc)
            return None, OPENAI_RATE_LIMITED
        except OpenAISkippedUnavailable as exc:
            logger.warning("%s completion skipped (unavailable for job): %s", self.provider_key, exc)
            return None, OPENAI_UNAVAILABLE
        except GeminiSkippedUnavailable as exc:
            logger.warning("%s completion skipped (unavailable for job): %s", self.provider_key, exc)
            if "disabled_by_config" in str(exc).lower():
                code = GEMINI_DISABLED
            else:
                code = GEMINI_UNAVAILABLE
            return None, code
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s completion failed: %s", self.provider_key, exc)
            return None, f"{PROVIDER_ERROR}:{exc}"

        pr = parse_as_object(raw)
        if pr.payload is not None:
            return pr.payload, None

        strict_user = strict_json_user_suffix(user, pr.error_code or INVALID_JSON)
        try:
            raw2 = await self._complete_once(
                model_id=model_id,
                system=system + "\n\nOutput must be a single JSON object only.",
                user=strict_user,
            )
        except GeminiJobRateLimitExhausted:
            code = GEMINI_RATE_LIMITED if self.provider_key == "google" else RATE_LIMIT_EXHAUSTED
            return None, code
        except GeminiServiceUnavailableExhausted:
            return None, (GEMINI_SERVICE_UNAVAILABLE if self.provider_key == "google" else RATE_LIMIT_EXHAUSTED)
        except OpenAIJobRateLimitExhausted:
            return None, OPENAI_RATE_LIMITED
        except OpenAISkippedUnavailable:
            return None, OPENAI_UNAVAILABLE
        except GeminiSkippedUnavailable as exc:
            return None, (GEMINI_DISABLED if "disabled_by_config" in str(exc).lower() else GEMINI_UNAVAILABLE)
        except Exception as exc:  # noqa: BLE001
            return None, f"{PROVIDER_ERROR}:{exc}"
        pr2 = parse_as_object(raw2)
        if pr2.payload is None:
            return None, pr2.error_code or INVALID_JSON
        return pr2.payload, None

    async def complete_reviewer_json(
        self,
        *,
        model_id: str,
        system: str,
        user: str,
        validate: Callable[[dict[str, Any]], Any],
    ) -> tuple[dict[str, Any] | None, str | None]:
        """
        Reviewer path: parse/repair, optional schema reprompt once, explicit error codes.
        """
        try:
            raw = await self._complete_once(model_id=model_id, system=system, user=user)
        except GeminiJobRateLimitExhausted as exc:
            logger.warning("%s reviewer rate-limited (job budget): %s", self.provider_key, exc)
            code = GEMINI_RATE_LIMITED if self.provider_key == "google" else RATE_LIMIT_EXHAUSTED
            return None, code
        except GeminiServiceUnavailableExhausted as exc:
            logger.warning("%s reviewer service unavailable (job budget): %s", self.provider_key, exc)
            return None, (GEMINI_SERVICE_UNAVAILABLE if self.provider_key == "google" else RATE_LIMIT_EXHAUSTED)
        except OpenAIJobRateLimitExhausted as exc:
            logger.warning("%s reviewer rate-limited (job budget): %s", self.provider_key, exc)
            return None, OPENAI_RATE_LIMITED
        except OpenAISkippedUnavailable as exc:
            logger.warning("%s reviewer skipped (unavailable for job): %s", self.provider_key, exc)
            return None, OPENAI_UNAVAILABLE
        except GeminiSkippedUnavailable as exc:
            logger.warning("%s reviewer skipped (unavailable for job): %s", self.provider_key, exc)
            return None, (GEMINI_DISABLED if "disabled_by_config" in str(exc).lower() else GEMINI_UNAVAILABLE)
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s reviewer provider error: %s", self.provider_key, exc)
            return None, PROVIDER_ERROR

        def _try_validate(payload: dict[str, Any]) -> str | None:
            try:
                validate(payload)
            except ValidationError as exc:
                return SCHEMA_MISMATCH + ":" + json.dumps(exc.errors()[:3], default=str)[:300]
            return None

        pr = parse_as_object(raw)
        payload = pr.payload
        err = pr.error_code

        if payload is not None:
            v_err = _try_validate(payload)
            if v_err is None:
                return payload, None
            err = v_err

        strict_user = strict_json_user_suffix(user, err or INVALID_JSON)
        try:
            raw2 = await self._complete_once(
                model_id=model_id,
                system=system + "\n\nOutput must be a single JSON object matching the schema.",
                user=strict_user,
            )
        except GeminiJobRateLimitExhausted:
            code = GEMINI_RATE_LIMITED if self.provider_key == "google" else RATE_LIMIT_EXHAUSTED
            return None, code
        except GeminiServiceUnavailableExhausted:
            return None, (GEMINI_SERVICE_UNAVAILABLE if self.provider_key == "google" else RATE_LIMIT_EXHAUSTED)
        except OpenAIJobRateLimitExhausted:
            return None, OPENAI_RATE_LIMITED
        except OpenAISkippedUnavailable:
            return None, OPENAI_UNAVAILABLE
        except GeminiSkippedUnavailable as exc:
            return None, (GEMINI_DISABLED if "disabled_by_config" in str(exc).lower() else GEMINI_UNAVAILABLE)
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s reviewer strict reprompt failed: %s", self.provider_key, exc)
            return None, PROVIDER_ERROR

        pr2 = parse_as_object(raw2)
        if pr2.payload is None:
            return None, pr2.error_code or INVALID_JSON
        v_err2 = _try_validate(pr2.payload)
        if v_err2 is not None:
            return None, SCHEMA_MISMATCH
        return pr2.payload, None

    async def complete_arbiter_json(
        self,
        *,
        model_id: str,
        system: str,
        user: str,
        validate: Callable[[dict[str, Any]], Any],
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Same hardened path as reviewers; keeps arbiter on the structured-output pipeline."""
        return await self.complete_reviewer_json(
            model_id=model_id, system=system, user=user, validate=validate
        )
