from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Final

END_GLOBAL_MARKER: Final[str] = "---END_GLOBAL---"

_PROMPT_FILENAMES: Final[dict[str, str]] = {
    "supervisor": "supervisor.md",
    "claude_author_intent_reviewer": "claude_author_intent_reviewer.md",
    "gpt_skeptical_reviewer": "gpt_skeptical_reviewer.md",
    "gemini_consistency_reviewer": "gemini_consistency_reviewer.md",
    "arbiter": "arbiter.md",
}

ALLOWED_PROMPT_STEMS: Final[frozenset[str]] = frozenset(_PROMPT_FILENAMES.keys())


def _env_prompts_dir() -> Path | None:
    raw = os.environ.get("DRAFTLENS_PROMPTS_DIR", "").strip()
    if not raw:
        return None
    p = Path(raw).expanduser()
    return p if p.is_dir() else None


def discover_prompts_dir() -> Path:
    """
    Locate the repository `prompts/` directory containing DraftLens markdown prompts.

    Resolution order:
    1. `DRAFTLENS_PROMPTS_DIR` if set and exists
    2. Walk parents from this package until `prompts/supervisor.md` exists
    """
    env = _env_prompts_dir()
    if env is not None:
        return env.resolve()

    here = Path(__file__).resolve()
    for d in [here.parent, *here.parents]:
        candidate = d / "prompts"
        if (candidate / "supervisor.md").is_file():
            return candidate.resolve()

    raise FileNotFoundError(
        "DraftLens prompts directory not found. Set DRAFTLENS_PROMPTS_DIR or add prompts/ at repository root."
    )


def _safe_join(root: Path, filename: str) -> Path:
    """Resolve `root/filename` and ensure the result stays under `root`."""
    root_r = root.resolve()
    target = (root_r / filename).resolve()
    try:
        target.relative_to(root_r)
    except ValueError as exc:
        raise ValueError("illegal_prompt_path") from exc
    return target


def load_prompt_raw(stem: str) -> str:
    """Load a prompt markdown file as UTF-8 text (full file)."""
    if stem not in ALLOWED_PROMPT_STEMS:
        raise KeyError(f"unknown_prompt:{stem}")
    root = discover_prompts_dir()
    path = _safe_join(root, _PROMPT_FILENAMES[stem])
    if not path.is_file():
        raise FileNotFoundError(f"missing_prompt_file:{path}")
    return path.read_text(encoding="utf-8")


def split_global_and_body(text: str) -> tuple[str, str]:
    """Split file into global rules (before marker) and body (after marker)."""
    if END_GLOBAL_MARKER not in text:
        return "", text.strip()
    head, tail = text.split(END_GLOBAL_MARKER, 1)
    return head.strip(), tail.strip()


def get_global_rules_markdown() -> str:
    """Return the shared global rules block (canonical: from supervisor.md)."""
    raw = load_prompt_raw("supervisor")
    global_part, _body = split_global_and_body(raw)
    if not global_part.strip():
        raise ValueError("supervisor_prompt_missing_global_rules")
    return global_part.strip()


def assert_all_prompts_share_global_block() -> str:
    """
    Verify every prompt file uses the same global-rules prefix as supervisor.md.

    Returns the sha256 hex digest of the canonical global block for diagnostics.
    """
    canonical = get_global_rules_markdown()
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    for stem in sorted(ALLOWED_PROMPT_STEMS):
        raw = load_prompt_raw(stem)
        g, _ = split_global_and_body(raw)
        if g.strip() != canonical:
            raise ValueError(f"global_rules_mismatch:{stem}")
    return digest


def load_prompt_body(stem: str) -> str:
    """Return markdown body after the global delimiter (role + contracts)."""
    raw = load_prompt_raw(stem)
    _g, body = split_global_and_body(raw)
    if not body.strip():
        raise ValueError(f"prompt_empty_body:{stem}")
    return body.strip()


def load_full_prompt(stem: str) -> str:
    """Return the entire prompt file (global + body), trimmed."""
    return load_prompt_raw(stem).strip()
