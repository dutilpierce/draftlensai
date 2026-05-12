from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from draftlens_api.prompts.loader import (
    ALLOWED_PROMPT_STEMS,
    assert_all_prompts_share_global_block,
    discover_prompts_dir,
    get_global_rules_markdown,
    load_full_prompt,
    load_prompt_raw,
    split_global_and_body,
)
from draftlens_api.prompts.schemas import (
    validate_arbiter_payload,
    validate_debate_round2_payload,
    validate_reviewer_payload,
    validate_supervisor_payload,
)


def test_discover_prompts_dir_finds_repo_prompts() -> None:
    root = discover_prompts_dir()
    assert (root / "supervisor.md").is_file()
    assert (root / "arbiter.md").is_file()


def test_load_all_prompts_nonempty() -> None:
    for stem in sorted(ALLOWED_PROMPT_STEMS):
        text = load_full_prompt(stem)
        assert len(text) > 200
        assert "strict JSON" in text.lower() or "json" in text.lower()


def test_global_rules_consistent_across_files() -> None:
    digest = assert_all_prompts_share_global_block()
    assert len(digest) == 64


def test_supervisor_has_required_sections() -> None:
    raw = load_prompt_raw("supervisor")
    assert "---END_GLOBAL---" in raw
    assert "Supervisor role" in raw
    assert "merged_issues" in raw


def test_env_override_prompts_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "prompts"
    fake.mkdir()
    # minimal valid tree: copy one real file as supervisor only is not enough for load_all
    real = discover_prompts_dir()
    for name in [
        "supervisor.md",
        "claude_author_intent_reviewer.md",
        "gpt_skeptical_reviewer.md",
        "gemini_consistency_reviewer.md",
        "arbiter.md",
    ]:
        (fake / name).write_text((real / name).read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setenv("DRAFTLENS_PROMPTS_DIR", str(fake))
    assert discover_prompts_dir().resolve() == fake.resolve()
    assert "strict JSON" in get_global_rules_markdown()


def test_unknown_prompt_rejected() -> None:
    with pytest.raises(KeyError):
        load_prompt_raw("etc_passwd")


def test_validate_reviewer_payload_minimal_ok() -> None:
    data = {
        "summary": "ok",
        "risks": [],
        "questions_for_peers": [],
        "issues": [
            {
                "block_id": "b-0001",
                "span_text": "x",
                "char_start": 0,
                "char_end": 1,
                "category": "clarity",
                "severity": "minor",
                "title": "t",
                "explanation": "e",
                "evidence_basis": "",
                "confidence": 0.5,
                "suggested_fix": "",
                "preserve_voice_notes": "",
                "source_agents": ["gpt_reviewer"],
                "status": "open",
            }
        ],
    }
    m = validate_reviewer_payload(data)
    assert m.summary == "ok"
    assert len(m.issues) == 1


def test_validate_reviewer_payload_rejects_bad_category() -> None:
    data = {
        "summary": "ok",
        "risks": [],
        "questions_for_peers": [],
        "issues": [
            {
                "block_id": "b-0001",
                "category": "not-a-category",
                "severity": "minor",
                "title": "t",
            }
        ],
    }
    with pytest.raises(ValidationError):
        validate_reviewer_payload(data)


def test_validate_arbiter_payload_ok() -> None:
    data = {
        "executive_summary": "done",
        "verdicts": [{"dispute_id": "d1", "verdict": "merge", "notes": "n", "merged_issue": None}],
        "issues": [],
        "proposed_edits": [],
        "resolved_conflicts": [],
        "redline_html_fragment": "<p></p>",
    }
    m = validate_arbiter_payload(data)
    assert m.verdicts[0].verdict == "merge"


def test_validate_debate_round2_payload_ok() -> None:
    data = {"votes": [{"dispute_id": "d", "issue_id": "i", "stance": "defend", "rationale_summary": "r"}]}
    m = validate_debate_round2_payload(data)
    assert m.votes[0].stance == "defend"


def test_validate_supervisor_payload_ok() -> None:
    data = {
        "executive_summary": "s",
        "merged_issues": [
            {
                "block_id": "b-0001",
                "span_text": "x",
                "char_start": 0,
                "char_end": 1,
                "category": "tone",
                "severity": "nit",
                "title": "t",
                "explanation": "e",
                "evidence_basis": "",
                "confidence": 0.6,
                "suggested_fix": "",
                "preserve_voice_notes": "",
                "source_agents": ["gemini_reviewer"],
                "status": "open",
            }
        ],
        "conflict_report": [{"cluster_id": "c1", "reasons": ["x"], "issue_ids": ["a", "b"]}],
        "stats_by_severity": {"critical": 0, "major": 0, "minor": 1, "nit": 0},
        "stats_by_category": {"tone": 1},
        "human_evidence_queue": [],
        "pipeline_notes": [],
    }
    m = validate_supervisor_payload(data)
    assert m.stats_by_category["tone"] == 1


def test_split_global_and_body() -> None:
    g, b = split_global_and_body("A\n---END_GLOBAL---\nB")
    assert "A" in g and "B" in b
