from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_MODEL_ROUTING: dict[str, Any] = {
    "model_routing": {
        "author_intent_model": "anthropic/claude-sonnet-4-6",
        "skeptical_reviewer_model": "openai/gpt-5.5",
        "consistency_parser_model": "google/gemini-3.1-flash-lite",
        "arbiter_model": "openai/gpt-5.5",
    }
}


class Settings(BaseSettings):
    """Application settings; env vars match deployment names with legacy fallbacks."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("DRAFTLENS_ENVIRONMENT", "ENVIRONMENT"),
    )

    app_session_secret: str = Field(
        ...,
        min_length=32,
        validation_alias=AliasChoices("APP_SESSION_SECRET", "DRAFTLENS_SECRET_KEY"),
    )
    cookie_name: str = Field(default="draftlens_session", validation_alias=AliasChoices("DRAFTLENS_COOKIE_NAME"))
    session_days: int = Field(default=30, validation_alias=AliasChoices("DRAFTLENS_SESSION_DAYS"))
    cors_origins: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("DRAFTLENS_CORS_ORIGINS"),
    )

    data_dir: str = Field(default="./data", validation_alias=AliasChoices("DRAFTLENS_DATA_DIR"))
    database_url: str = Field(
        default="sqlite:///./data/draftlens.db",
        validation_alias=AliasChoices("DRAFTLENS_DATABASE_URL"),
    )

    model_routing_json: str = Field(
        default=json.dumps(_DEFAULT_MODEL_ROUTING),
        validation_alias=AliasChoices("MODEL_ROUTING_JSON", "DRAFTLENS_MODEL_ROUTING_JSON"),
    )

    # Gemini rate limits & optional exclusion (see .env.example).
    draftlens_gemini_max_429_retries: int = Field(
        default=8,
        ge=1,
        le=50,
        validation_alias=AliasChoices("DRAFTLENS_GEMINI_MAX_429_RETRIES"),
    )
    draftlens_gemini_max_backoff_seconds: float = Field(
        default=90.0,
        ge=0.5,
        le=300.0,
        validation_alias=AliasChoices("DRAFTLENS_GEMINI_MAX_BACKOFF_SECONDS"),
    )
    draftlens_gemini_max_503_retries: int = Field(
        default=8,
        ge=1,
        le=50,
        validation_alias=AliasChoices("DRAFTLENS_GEMINI_MAX_503_RETRIES"),
    )
    draftlens_openai_max_429_retries: int = Field(
        default=8,
        ge=1,
        le=50,
        validation_alias=AliasChoices("DRAFTLENS_OPENAI_MAX_429_RETRIES"),
    )
    draftlens_openai_max_backoff_seconds: float = Field(
        default=90.0,
        ge=0.5,
        le=300.0,
        validation_alias=AliasChoices("DRAFTLENS_OPENAI_MAX_BACKOFF_SECONDS"),
    )
    draftlens_disable_gemini: bool = Field(
        default=False,
        validation_alias=AliasChoices("DRAFTLENS_DISABLE_GEMINI"),
    )
    draftlens_gemini_disable_in_dev: bool = Field(
        default=False,
        validation_alias=AliasChoices("DRAFTLENS_GEMINI_DISABLE_IN_DEV"),
    )
    draftlens_gemini_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DRAFTLENS_GEMINI_MODEL"),
    )
    draftlens_gemini_fallback_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DRAFTLENS_GEMINI_FALLBACK_MODEL"),
    )
    # When set, caps iterative convergence max cycles in development-like environments only.
    draftlens_convergence_max_cycles_review_cap: int | None = Field(
        default=None,
        ge=1,
        le=20,
        validation_alias=AliasChoices("DRAFTLENS_CONVERGENCE_MAX_CYCLES_REVIEW_CAP"),
    )
    draftlens_convergence_max_cycles_fix_cap: int | None = Field(
        default=None,
        ge=1,
        le=20,
        validation_alias=AliasChoices("DRAFTLENS_CONVERGENCE_MAX_CYCLES_FIX_CAP"),
    )

    data_retention_hours_default: int = Field(
        default=168,
        validation_alias=AliasChoices("DATA_RETENTION_HOURS_DEFAULT", "DRAFTLENS_DEFAULT_RETENTION_HOURS"),
    )
    data_retention_hours_sensitive: int = Field(
        default=24,
        validation_alias=AliasChoices("DATA_RETENTION_HOURS_SENSITIVE", "DRAFTLENS_SENSITIVE_RETENTION_HOURS"),
    )

    free_monthly_proofs: int = Field(default=1, validation_alias=AliasChoices("FREE_MONTHLY_PROOFS"))
    free_max_pages: int = Field(default=25, validation_alias=AliasChoices("FREE_MAX_PAGES", "DRAFTLENS_FREE_MAX_PAGES"))
    pro_fair_use_docs_per_month: int = Field(
        default=200,
        validation_alias=AliasChoices("PRO_FAIR_USE_DOCS_PER_MONTH", "DRAFTLENS_PRO_MONTHLY_DOC_CAP"),
    )
    pro_max_pages: int = Field(default=500, validation_alias=AliasChoices("DRAFTLENS_PRO_MAX_PAGES"))

    free_max_review_blocks: int = Field(
        default=48,
        validation_alias=AliasChoices("DRAFTLENS_FREE_MAX_REVIEW_BLOCKS", "FREE_MAX_REVIEW_BLOCKS"),
    )
    pro_max_review_blocks: int = Field(
        default=0,
        validation_alias=AliasChoices("DRAFTLENS_PRO_MAX_REVIEW_BLOCKS", "PRO_MAX_REVIEW_BLOCKS"),
    )

    retention_sweep_interval_seconds: int = Field(
        default=3600,
        validation_alias=AliasChoices("DRAFTLENS_RETENTION_SWEEP_SECONDS", "RETENTION_SWEEP_INTERVAL_SECONDS"),
    )

    next_public_app_url: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("NEXT_PUBLIC_APP_URL", "DRAFTLENS_PUBLIC_APP_URL"),
    )
    stripe_success_url: str = Field(
        default="http://localhost:3000/?billing=success",
        validation_alias=AliasChoices("STRIPE_SUCCESS_URL", "DRAFTLENS_STRIPE_SUCCESS_URL"),
    )
    stripe_cancel_url: str = Field(
        default="http://localhost:3000/?billing=cancel",
        validation_alias=AliasChoices("STRIPE_CANCEL_URL", "DRAFTLENS_STRIPE_CANCEL_URL"),
    )

    stripe_secret_key: str = Field(default="", validation_alias=AliasChoices("STRIPE_SECRET_KEY"))
    stripe_publishable_key: str = Field(default="", validation_alias=AliasChoices("STRIPE_PUBLISHABLE_KEY"))
    stripe_webhook_secret: str = Field(default="", validation_alias=AliasChoices("STRIPE_WEBHOOK_SECRET"))
    stripe_price_id_pro_monthly: str = Field(
        default="",
        validation_alias=AliasChoices("STRIPE_PRICE_ID_PRO_MONTHLY", "STRIPE_PRICE_ID_PRO", "DRAFTLENS_STRIPE_PRICE_ID_PRO"),
    )

    # --- Cloud storage (Google Drive / Dropbox / OneDrive) — secrets server-side only ---
    draftlens_api_public_url: str = Field(
        default="http://127.0.0.1:8000",
        validation_alias=AliasChoices("DRAFTLENS_API_PUBLIC_URL", "API_PUBLIC_URL"),
    )
    draftlens_cloud_google_client_id: str = Field(default="", validation_alias=AliasChoices("DRAFTLENS_GOOGLE_CLIENT_ID"))
    draftlens_cloud_google_client_secret: str = Field(
        default="", validation_alias=AliasChoices("DRAFTLENS_GOOGLE_CLIENT_SECRET")
    )
    draftlens_cloud_google_picker_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("DRAFTLENS_GOOGLE_PICKER_API_KEY", "GOOGLE_PICKER_API_KEY"),
    )
    # Numeric GCP project number for Google Picker setAppId (public; improves Picker integration when set).
    draftlens_cloud_google_project_number: str = Field(
        default="",
        validation_alias=AliasChoices("DRAFTLENS_GOOGLE_PROJECT_NUMBER", "GOOGLE_CLOUD_PROJECT_NUMBER"),
    )
    draftlens_cloud_dropbox_app_key: str = Field(default="", validation_alias=AliasChoices("DRAFTLENS_DROPBOX_APP_KEY"))
    draftlens_cloud_dropbox_app_secret: str = Field(
        default="", validation_alias=AliasChoices("DRAFTLENS_DROPBOX_APP_SECRET")
    )
    draftlens_cloud_microsoft_client_id: str = Field(
        default="", validation_alias=AliasChoices("DRAFTLENS_MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_ID")
    )
    draftlens_cloud_microsoft_client_secret: str = Field(
        default="", validation_alias=AliasChoices("DRAFTLENS_MICROSOFT_CLIENT_SECRET", "MICROSOFT_CLIENT_SECRET")
    )

    def model_routing(self) -> dict[str, Any]:
        try:
            data = json.loads(self.model_routing_json)
        except json.JSONDecodeError:
            data = _DEFAULT_MODEL_ROUTING
        return data.get("model_routing", data)


class ProviderEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = Field(default="", validation_alias=AliasChoices("OPENAI_API_KEY"))
    anthropic_api_key: str = Field(default="", validation_alias=AliasChoices("ANTHROPIC_API_KEY"))
    gemini_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_provider_env() -> ProviderEnv:
    return ProviderEnv()
