"""
OpenAI Chat Completions request normalization (model-specific).

Unsupported parameters must be omitted entirely — sending defaults explicitly can still 400.
"""

from __future__ import annotations

import re
from typing import Any


def openai_model_supports_custom_temperature(model_id: str) -> bool:
    """
    True when `temperature` may be set to a non-default value on Chat Completions.

    gpt-5.x currently only accepts the API default (1); o-series reasoning models
    similarly reject custom sampling temperature on many deployments.
    """
    m = str(model_id).strip().lower()
    if not m:
        return True
    if "gpt-5" in m:
        return False
    if re.match(r"^o\d", m) or m.startswith("o1") or m.startswith("o3"):
        return False
    return True


def openai_chat_temperature_params(model_id: str) -> dict[str, Any]:
    """Fragment to merge into a chat/completions JSON body (empty dict = omit temperature)."""
    if openai_model_supports_custom_temperature(model_id):
        return {"temperature": 0.1}
    return {}
