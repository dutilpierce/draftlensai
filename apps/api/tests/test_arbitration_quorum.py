from __future__ import annotations

from draftlens_api.engine.arbitration_gate import (
    build_arbiter_user_dict,
    count_structured_successes,
    has_arbitratable_conflict_clusters,
    post_detect_routing,
)


def test_post_detect_fail_when_zero_success() -> None:
    phase1 = {"claude": {"ok": False}, "gpt": {"ok": False}, "gemini": {"ok": False}}
    assert post_detect_routing(phase1, [{"issues": [{"x": 1}, {"x": 2}]}]) == "fail_no_reviewer_output"


def test_post_detect_synthesize_when_quorum_but_no_conflicts() -> None:
    phase1 = {"claude": {"ok": True}, "gpt": {"ok": True}, "gemini": {"ok": False}}
    assert post_detect_routing(phase1, []) == "synthesize_ledger_without_arbitration"


def test_post_detect_debate_when_quorum_and_conflicts() -> None:
    phase1 = {"claude": {"ok": True}, "gpt": {"ok": True}, "gemini": {"ok": True}}
    clusters = [{"issues": [{"a": 1}, {"b": 2}]}]
    assert post_detect_routing(phase1, clusters) == "cross_model_debate"


def test_post_detect_synthesize_when_only_one_success_even_with_clusters() -> None:
    phase1 = {"claude": {"ok": True}, "gpt": {"ok": False}, "gemini": {"ok": False}}
    clusters = [{"issues": [{"a": 1}, {"b": 2}]}]
    assert post_detect_routing(phase1, clusters) == "synthesize_ledger_without_arbitration"


def test_has_arbitratable_conflict_clusters_requires_two_issues() -> None:
    assert has_arbitratable_conflict_clusters([{"issues": [{"a": 1}]}]) is False
    assert has_arbitratable_conflict_clusters([{"issues": [{}, {}]}]) is True


def test_count_structured_successes() -> None:
    assert count_structured_successes({"claude": {"ok": True}, "gpt": {"ok": True}, "gemini": {}}) == 2


def test_build_arbiter_user_dict_truncates_issues() -> None:
    issues = [{"issue_id": str(i), "block_id": "b1"} for i in range(150)]
    d = build_arbiter_user_dict(
        conflict_clusters=[],
        round2_transcript=[],
        issues_working=issues,
        document_excerpt="x" * 50_000,
        output_mode="review",
        global_evidence_status="ok",
        evidence_arbitration_hints=[],
        max_issues=100,
    )
    assert len(d["issues_working"]) == 100
    assert len(d["document_excerpt"]) <= 18_000
