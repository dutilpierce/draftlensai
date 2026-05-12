"""Deterministic JSON extraction and repair for reviewer / arbiter structured outputs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

# Explicit failure codes for reviewer runs (adapter + parse layer).
INVALID_JSON = "INVALID_JSON"
TRUNCATED_JSON = "TRUNCATED_JSON"
SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
EMPTY_RESPONSE = "EMPTY_RESPONSE"
PROVIDER_ERROR = "PROVIDER_ERROR"
RATE_LIMIT_EXHAUSTED = "RATE_LIMIT_EXHAUSTED"
GEMINI_RATE_LIMITED = "GEMINI_RATE_LIMITED"
GEMINI_UNAVAILABLE = "GEMINI_UNAVAILABLE"
GEMINI_DISABLED = "GEMINI_DISABLED"
GEMINI_SERVICE_UNAVAILABLE = "GEMINI_SERVICE_UNAVAILABLE"
OPENAI_RATE_LIMITED = "OPENAI_RATE_LIMITED"
OPENAI_UNAVAILABLE = "OPENAI_UNAVAILABLE"
# Job-level SSE / diagnostics when a provider is removed from scheduling for the remainder of the job.
PROVIDER_SKIPPED_FOR_REMAINDER_OF_JOB = "PROVIDER_SKIPPED_FOR_REMAINDER_OF_JOB"

_STRICT_TAIL = (
    "\n\nReturn valid JSON only matching the schema exactly. "
    "No prose. No markdown. No explanation."
)


def strip_code_fences(text: str) -> str:
    t = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", t, re.I)
    if m:
        return m.group(1).strip()
    return t


def extract_first_json_value(text: str) -> Any | None:
    """Extract first JSON object or array using raw_decode (handles trailing prose)."""
    s = strip_code_fences(text)
    if not s:
        return None
    dec = json.JSONDecoder()
    for opener, expect in (("{", dict), ("[", list)):
        idx = s.find(opener)
        if idx < 0:
            continue
        try:
            val, _end = dec.raw_decode(s[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(val, expect):
            return val
    return None


def _try_close_braces(text: str) -> str | None:
    """If JSON looks truncated, append closing brackets/braces."""
    t = strip_code_fences(text).strip()
    if not t:
        return None
    depth_obj = 0
    depth_arr = 0
    in_str = False
    esc = False
    for ch in t:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            depth_obj += 1
        elif ch == "}":
            depth_obj = max(0, depth_obj - 1)
        elif ch == "[":
            depth_arr += 1
        elif ch == "]":
            depth_arr = max(0, depth_arr - 1)
    if depth_obj == 0 and depth_arr == 0:
        return None
    suffix = "}" * depth_obj + "]" * depth_arr
    candidate = t + suffix
    try:
        json.loads(candidate)
        return candidate
    except json.JSONDecodeError:
        return None


def parse_json_with_repairs(raw: str) -> tuple[Any | None, str | None]:
    """
    Returns (parsed, error_code).
    Strips fences, extracts first JSON value, then one bracket-closing repair.
    """
    if raw is None or not str(raw).strip():
        return None, EMPTY_RESPONSE
    text = str(raw).strip()
    val = extract_first_json_value(text)
    if val is not None:
        return val, None
    closed = _try_close_braces(text)
    if closed:
        try:
            val2 = extract_first_json_value(closed)
            if val2 is not None:
                return val2, None
        except Exception:  # noqa: BLE001
            pass
        return None, TRUNCATED_JSON
    return None, INVALID_JSON


@dataclass(frozen=True)
class StructuredParseResult:
    payload: dict[str, Any] | None
    error_code: str | None
    repaired_truncation: bool = False


def parse_as_object(raw: str) -> StructuredParseResult:
    val, err = parse_json_with_repairs(raw)
    if val is None:
        return StructuredParseResult(None, err or INVALID_JSON)
    if isinstance(val, dict):
        return StructuredParseResult(val, None)
    if isinstance(val, list):
        return StructuredParseResult(None, SCHEMA_MISMATCH)
    return StructuredParseResult(None, INVALID_JSON)


def strict_json_user_suffix(original_user: str, parse_error: str) -> str:
    return (
        original_user
        + _STRICT_TAIL
        + "\n\nPrevious output was invalid. Parser error: "
        + parse_error[:400]
    )
