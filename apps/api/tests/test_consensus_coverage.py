"""Unit tests for tri-model vs partial consensus labeling."""

from __future__ import annotations

from draftlens_api.engine.consensus_coverage import reconcile_consensus_fields


def test_full_three_when_three_successes_and_zero_pairwise() -> None:
    meta: dict = {"convergence_status": "CONVERGENCE_REACHED"}
    reconcile_consensus_fields(
        meta,
        configured_slots=3,
        successful_count=3,
        pairwise_cluster_count=0,
        fix_mode=False,
        fix_clean=True,
        strict_three_reviewer_consensus=True,
    )
    assert meta["consensus_mode"] == "FULL_THREE_REVIEWER_CONSENSUS"
    assert meta["full_consensus_achieved"] is True
    assert meta["partial_consensus_only"] is False


def test_partial_when_two_successes_strict_downgrades_status() -> None:
    meta: dict = {"convergence_status": "CONVERGENCE_REACHED"}
    reconcile_consensus_fields(
        meta,
        configured_slots=3,
        successful_count=2,
        pairwise_cluster_count=0,
        fix_mode=False,
        fix_clean=True,
        strict_three_reviewer_consensus=True,
    )
    assert meta["consensus_mode"] == "PARTIAL_CONSENSUS"
    assert meta["full_consensus_achieved"] is False
    assert meta["partial_consensus_only"] is True
    assert meta["convergence_status"] == "PARTIAL_CONSENSUS"


def test_partial_when_two_successes_non_strict_keeps_convergence_label() -> None:
    meta: dict = {"convergence_status": "CONVERGENCE_REACHED"}
    reconcile_consensus_fields(
        meta,
        configured_slots=3,
        successful_count=2,
        pairwise_cluster_count=0,
        fix_mode=False,
        fix_clean=True,
        strict_three_reviewer_consensus=False,
    )
    assert meta["consensus_mode"] == "PARTIAL_CONSENSUS"
    assert meta["full_consensus_achieved"] is False
    assert meta["partial_consensus_only"] is True
    assert meta["convergence_status"] == "CONVERGENCE_REACHED"


def test_two_slot_panel_full_consensus() -> None:
    meta: dict = {"convergence_status": "SINGLE_PASS"}
    reconcile_consensus_fields(
        meta,
        configured_slots=2,
        successful_count=2,
        pairwise_cluster_count=0,
        fix_mode=False,
        fix_clean=True,
        strict_three_reviewer_consensus=True,
    )
    assert meta["consensus_mode"] == "TWO_REVIEWER_PANEL_COMPLETE"
    assert meta["full_consensus_achieved"] is True
    assert meta["convergence_status"] == "CONVERGENCE_REACHED"


def test_full_three_not_claimed_when_provider_instability_dropout() -> None:
    meta: dict = {"convergence_status": "CONVERGENCE_REACHED", "provider_instability_dropout": True}
    reconcile_consensus_fields(
        meta,
        configured_slots=3,
        successful_count=3,
        pairwise_cluster_count=0,
        fix_mode=False,
        fix_clean=True,
        strict_three_reviewer_consensus=False,
    )
    assert meta["consensus_mode"] == "PARTIAL_CONSENSUS"
    assert meta["full_consensus_achieved"] is False
    assert meta["partial_consensus_only"] is True
    assert meta["convergence_status"] == "PARTIAL_CONSENSUS"
    assert "consensus_honesty_note" in meta
