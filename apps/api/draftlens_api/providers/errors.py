"""Provider-specific exceptions surfaced through `BaseLLMProvider` completion helpers."""


class GeminiJobRateLimitExhausted(RuntimeError):
    """Raised when Gemini returns 429 beyond the per-job retry budget."""


class GeminiServiceUnavailableExhausted(RuntimeError):
    """Raised when Gemini returns 503 (or similar) beyond the per-job transient-error budget."""


class GeminiSkippedUnavailable(RuntimeError):
    """Raised when Gemini is marked unavailable for the remainder of the job (after budget exhaustion)."""


class OpenAIJobRateLimitExhausted(RuntimeError):
    """Raised when OpenAI returns 429 beyond the per-job retry budget."""


class OpenAISkippedUnavailable(RuntimeError):
    """Raised when OpenAI is marked unavailable for the remainder of the job (after 429 budget exhaustion)."""
