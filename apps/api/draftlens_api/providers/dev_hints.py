"""Human-readable hints for local development (missing secrets, quorum, etc.)."""

MISSING_SINGLE_PROVIDER_ENV_HINT = (
    "Set the matching API key in apps/api/.env (see .env.example): "
    "OPENAI_API_KEY for OpenAI, ANTHROPIC_API_KEY for Anthropic, GOOGLE_API_KEY or GEMINI_API_KEY for Gemini."
)

MULTI_MODEL_QUORUM_HINT = (
    "DraftLens needs at least two configured model providers for review quorum. "
    "In apps/api/.env, set two or more of: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY."
)
