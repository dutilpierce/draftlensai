"""Per-job LLM runtime (429/503 budgets, cooldowns) via ContextVar — set around graph execution."""

from __future__ import annotations

import os
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any

from draftlens_api.config import Settings

# Dataclass fallbacks when LLMJobRuntime is constructed without build_llm_job_runtime (tests).
_DEFAULT_GEMINI_429_BUDGET_PROD = 8
_DEFAULT_GEMINI_MAX_BACKOFF_PROD = 90.0
_DEFAULT_GEMINI_503_BUDGET_PROD = 8
# Development-like environments: tight per-error sleep cap (no long 90s stalls).
_DEFAULT_GEMINI_MAX_BACKOFF_DEV_CAP = 5.0
_DEFAULT_GEMINI_429_BUDGET_DEV_CAP = 2
_DEFAULT_GEMINI_503_BUDGET_DEV_CAP = 2

_DEFAULT_OPENAI_429_BUDGET_PROD = 8
_DEFAULT_OPENAI_MAX_BACKOFF_PROD = 90.0
_DEFAULT_OPENAI_429_BUDGET_DEV_CAP = 2
_DEFAULT_OPENAI_MAX_BACKOFF_DEV_CAP = 5.0


@dataclass
class LLMJobRuntime:
    job_id: str
    gemini_429_budget_remaining: int = field(default=_DEFAULT_GEMINI_429_BUDGET_PROD)
    gemini_503_budget_remaining: int = field(default=_DEFAULT_GEMINI_503_BUDGET_PROD)
    gemini_unavailable_for_job: bool = False
    gemini_cooldown_until_monotonic: float = 0.0
    """True when DRAFTLENS_DISABLE_GEMINI or DRAFTLENS_GEMINI_DISABLE_IN_DEV (dev) applied."""
    gemini_disabled_intentionally: bool = False
    """INTENTIONALLY_DISABLED | GEMINI_RATE_LIMITED | GEMINI_SERVICE_UNAVAILABLE | None"""
    gemini_skip_reason: str | None = None
    gemini_max_backoff_seconds: float = field(default=_DEFAULT_GEMINI_MAX_BACKOFF_PROD)
    """Raw Gemini API model id (no provider prefix) tried after primary fails empty/404 when set."""
    gemini_fallback_model_id: str | None = None

    openai_429_budget_remaining: int = field(default=_DEFAULT_OPENAI_429_BUDGET_PROD)
    openai_unavailable_for_job: bool = False
    openai_cooldown_until_monotonic: float = 0.0
    """OPENAI_RATE_LIMITED | None — set when 429 budget exhausts."""
    openai_skip_reason: str | None = None
    openai_max_backoff_seconds: float = field(default=_DEFAULT_OPENAI_MAX_BACKOFF_PROD)


_ctx: ContextVar[LLMJobRuntime | None] = ContextVar("draftlens_llm_job_runtime", default=None)


def get_llm_job_runtime() -> LLMJobRuntime | None:
    return _ctx.get()


def attach_llm_job_runtime(rt: LLMJobRuntime) -> Token[LLMJobRuntime | None]:
    return _ctx.set(rt)


def reset_llm_job_runtime(token: Token[LLMJobRuntime | None]) -> None:
    _ctx.reset(token)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def sync_provider_instability_into_meta(meta: dict[str, Any]) -> None:
    """
    Copy per-job provider dropout flags into convergence / pipeline meta for honest consensus labeling.

    Intentional Gemini disable is not treated as instability dropout.
    """
    rt = get_llm_job_runtime()
    if not rt:
        return
    dropout = False
    if rt.openai_unavailable_for_job:
        meta["openai_unavailable_for_job"] = True
        if rt.openai_skip_reason:
            meta["openai_skip_reason"] = rt.openai_skip_reason
        dropout = True
    if rt.gemini_unavailable_for_job and not rt.gemini_disabled_intentionally:
        meta["gemini_unavailable_after_failure"] = True
        if rt.gemini_skip_reason:
            meta["gemini_skip_reason_runtime"] = rt.gemini_skip_reason
        dropout = True
    if dropout:
        meta["provider_instability_dropout"] = True


def build_llm_job_runtime(job_id: str, settings: Settings) -> LLMJobRuntime:
    """
    Per-job runtime for provider rate limits, transient errors, and optional exclusion.

    Env (optional, override Settings):
    - DRAFTLENS_GEMINI_MAX_429_RETRIES — initial 429 absorption budget for this job.
    - DRAFTLENS_GEMINI_MAX_503_RETRIES — initial 503 absorption budget for this job.
    - DRAFTLENS_GEMINI_MAX_BACKOFF_SECONDS — cap per 429/503 backoff sleep.
    - DRAFTLENS_OPENAI_MAX_429_RETRIES — initial OpenAI 429 absorption budget for this job.
    - DRAFTLENS_OPENAI_MAX_BACKOFF_SECONDS — cap per OpenAI 429 backoff sleep.
    - DRAFTLENS_DISABLE_GEMINI — exclude Gemini for the job (intentional; not a failure).
    - DRAFTLENS_GEMINI_DISABLE_IN_DEV — same as above when environment is development-like.
    """
    env = (settings.environment or "").strip().lower()
    is_dev_like = env in ("development", "dev", "local", "test")

    budget_429 = settings.draftlens_gemini_max_429_retries
    if "DRAFTLENS_GEMINI_MAX_429_RETRIES" in os.environ and os.environ.get("DRAFTLENS_GEMINI_MAX_429_RETRIES", "").strip() != "":
        budget_429 = _env_int("DRAFTLENS_GEMINI_MAX_429_RETRIES", budget_429)
    elif is_dev_like:
        budget_429 = min(budget_429, _DEFAULT_GEMINI_429_BUDGET_DEV_CAP)

    budget_503 = settings.draftlens_gemini_max_503_retries
    if "DRAFTLENS_GEMINI_MAX_503_RETRIES" in os.environ and os.environ.get("DRAFTLENS_GEMINI_MAX_503_RETRIES", "").strip() != "":
        budget_503 = _env_int("DRAFTLENS_GEMINI_MAX_503_RETRIES", budget_503)
    elif is_dev_like:
        budget_503 = min(budget_503, _DEFAULT_GEMINI_503_BUDGET_DEV_CAP)

    max_backoff = float(settings.draftlens_gemini_max_backoff_seconds)
    if "DRAFTLENS_GEMINI_MAX_BACKOFF_SECONDS" in os.environ and os.environ.get(
        "DRAFTLENS_GEMINI_MAX_BACKOFF_SECONDS", ""
    ).strip() != "":
        max_backoff = _env_float("DRAFTLENS_GEMINI_MAX_BACKOFF_SECONDS", max_backoff)
    elif is_dev_like:
        max_backoff = min(max_backoff, _DEFAULT_GEMINI_MAX_BACKOFF_DEV_CAP)

    fb_raw = (settings.draftlens_gemini_fallback_model or "").strip()
    fb_id = None
    if fb_raw:
        fb_id = fb_raw.split("/", 1)[-1].strip()

    o_budget = settings.draftlens_openai_max_429_retries
    if "DRAFTLENS_OPENAI_MAX_429_RETRIES" in os.environ and os.environ.get("DRAFTLENS_OPENAI_MAX_429_RETRIES", "").strip() != "":
        o_budget = _env_int("DRAFTLENS_OPENAI_MAX_429_RETRIES", o_budget)
    elif is_dev_like:
        o_budget = min(o_budget, _DEFAULT_OPENAI_429_BUDGET_DEV_CAP)

    o_backoff = float(settings.draftlens_openai_max_backoff_seconds)
    if "DRAFTLENS_OPENAI_MAX_BACKOFF_SECONDS" in os.environ and os.environ.get("DRAFTLENS_OPENAI_MAX_BACKOFF_SECONDS", "").strip() != "":
        o_backoff = _env_float("DRAFTLENS_OPENAI_MAX_BACKOFF_SECONDS", o_backoff)
    elif is_dev_like:
        o_backoff = min(o_backoff, _DEFAULT_OPENAI_MAX_BACKOFF_DEV_CAP)

    rt = LLMJobRuntime(
        job_id=job_id,
        gemini_429_budget_remaining=max(1, budget_429),
        gemini_503_budget_remaining=max(1, budget_503),
        gemini_max_backoff_seconds=max(0.5, max_backoff),
        gemini_fallback_model_id=fb_id,
        openai_429_budget_remaining=max(1, o_budget),
        openai_max_backoff_seconds=max(0.5, o_backoff),
    )

    disable = settings.draftlens_disable_gemini or _env_truthy("DRAFTLENS_DISABLE_GEMINI")
    disable_in_dev = settings.draftlens_gemini_disable_in_dev or _env_truthy("DRAFTLENS_GEMINI_DISABLE_IN_DEV")
    if disable or (disable_in_dev and is_dev_like):
        rt.gemini_unavailable_for_job = True
        rt.gemini_disabled_intentionally = True
        rt.gemini_skip_reason = "INTENTIONALLY_DISABLED"

    return rt
