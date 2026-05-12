"""
Reviewer coverage vs material pairwise discrepancies.

Tri-model "gold" consensus requires three configured reviewer slots to all return
structured success on the latest counted pass, plus zero pairwise material clusters.
"""

from __future__ import annotations

from typing import Any

from draftlens_api.engine.arbitration_gate import count_structured_successes
from draftlens_api.providers.llm_job_runtime import sync_provider_instability_into_meta
from draftlens_api.routing.model_registry import ModelRegistry


def configured_reviewer_slots(registry: ModelRegistry, assign: Any) -> int:
    """How many of Claude / GPT / Gemini are configured (API keys present) for this job."""
    n = 0
    for rm in (assign.author_intent, assign.skeptical_reviewer, assign.consistency_parser):
        if registry.adapter(rm).configured:
            n += 1
    return n


def initial_successful_count(phase1: dict[str, Any] | None) -> int:
    return count_structured_successes(phase1)


def reconcile_consensus_fields(
    meta: dict[str, Any],
    *,
    configured_slots: int,
    successful_count: int,
    pairwise_cluster_count: int,
    fix_mode: bool,
    fix_clean: bool,
    strict_three_reviewer_consensus: bool,
) -> None:
    """
    Populate consensus_mode, full_consensus_achieved, partial_consensus_only, and
    align convergence_status with strict three-reviewer rules when requested.
    """
    sync_provider_instability_into_meta(meta)
    meta["intended_reviewer_count"] = configured_slots
    meta["required_full_consensus_count"] = configured_slots
    meta["successful_reviewer_count"] = successful_count
    meta["active_reviewer_count"] = successful_count
    meta["pairwise_material_discrepancy_count"] = pairwise_cluster_count
    meta["participation_coverage_deficit"] = max(0, configured_slots - successful_count)

    status = str(meta.get("convergence_status") or "")

    if status == "QUORUM_LOST":
        meta["consensus_mode"] = "QUORUM_LOST"
        meta["full_consensus_achieved"] = False
        meta["partial_consensus_only"] = True
        return

    if status == "PARTIAL_REVIEW_COMPLETE" and meta.get("stopped_due_to_provider_unavailable"):
        meta["consensus_mode"] = "PROVIDER_UNAVAILABLE"
        meta["full_consensus_achieved"] = False
        meta["partial_consensus_only"] = True
        return

    if status == "PARTIAL_REVIEW_COMPLETE":
        meta["consensus_mode"] = "CONSENSUS_INCOMPLETE"
        meta["full_consensus_achieved"] = False
        meta["partial_consensus_only"] = bool(configured_slots == 3 and successful_count < 3)
        return

    if status in ("MAX_CYCLES_REACHED", "HUMAN_FOLLOW_UP_REQUIRED"):
        meta["consensus_mode"] = "CONSENSUS_INCOMPLETE"
        meta["full_consensus_achieved"] = False
        meta["partial_consensus_only"] = bool(configured_slots == 3 and successful_count < 3)
        return

    if meta.get("stopped_due_to_fatal_arbiter_failure"):
        meta["consensus_mode"] = "CONSENSUS_INCOMPLETE"
        meta["full_consensus_achieved"] = False
        meta["partial_consensus_only"] = bool(configured_slots == 3 and successful_count < 3)
        return

    material_or_fix_blocking = pairwise_cluster_count > 0 or (fix_mode and not fix_clean)
    if material_or_fix_blocking:
        meta["consensus_mode"] = "CONSENSUS_INCOMPLETE"
        meta["full_consensus_achieved"] = False
        meta["partial_consensus_only"] = bool(configured_slots == 3 and successful_count < 3)
        return

    triple_slot = configured_slots == 3
    pairwise_clear = pairwise_cluster_count == 0 and (not fix_mode or fix_clean)

    if status == "PARTIAL_CONSENSUS" and triple_slot and successful_count < 3 and pairwise_clear:
        meta["consensus_mode"] = "PARTIAL_CONSENSUS"
        meta["partial_consensus_only"] = True
        meta["full_consensus_achieved"] = False
        return

    if triple_slot and successful_count < 3 and pairwise_clear:
        meta["consensus_mode"] = "PARTIAL_CONSENSUS"
        meta["partial_consensus_only"] = True
        meta["full_consensus_achieved"] = False
        if strict_three_reviewer_consensus:
            meta["convergence_status"] = "PARTIAL_CONSENSUS"
        return

    if not triple_slot and successful_count >= configured_slots and pairwise_clear:
        meta["consensus_mode"] = "TWO_REVIEWER_PANEL_COMPLETE"
        meta["partial_consensus_only"] = False
        meta["full_consensus_achieved"] = True
        if status not in ("QUORUM_LOST", "PARTIAL_REVIEW_COMPLETE", "MAX_CYCLES_REACHED", "HUMAN_FOLLOW_UP_REQUIRED"):
            meta["convergence_status"] = "CONVERGENCE_REACHED"
        return

    if triple_slot and successful_count == 3 and pairwise_clear:
        if meta.get("provider_instability_dropout"):
            meta["consensus_mode"] = "PARTIAL_CONSENSUS"
            meta["partial_consensus_only"] = True
            meta["full_consensus_achieved"] = False
            meta["consensus_honesty_note"] = (
                "Full three-reviewer consensus is not claimed: OpenAI and/or Gemini became unavailable "
                "(rate limit or transient service error) during this job."
            )
            if strict_three_reviewer_consensus:
                meta["convergence_status"] = "PARTIAL_CONSENSUS"
            elif status not in ("QUORUM_LOST", "PARTIAL_REVIEW_COMPLETE", "MAX_CYCLES_REACHED", "HUMAN_FOLLOW_UP_REQUIRED"):
                meta["convergence_status"] = "PARTIAL_CONSENSUS"
            return
        meta["consensus_mode"] = "FULL_THREE_REVIEWER_CONSENSUS"
        meta["partial_consensus_only"] = False
        meta["full_consensus_achieved"] = True
        if status not in ("QUORUM_LOST", "PARTIAL_REVIEW_COMPLETE", "MAX_CYCLES_REACHED", "HUMAN_FOLLOW_UP_REQUIRED"):
            meta["convergence_status"] = "CONVERGENCE_REACHED"
        return

    meta.setdefault("consensus_mode", "CONSENSUS_INCOMPLETE")
    meta["full_consensus_achieved"] = False
    meta["partial_consensus_only"] = bool(triple_slot and successful_count < 3)


def reconcile_single_pass_consensus(
    meta: dict[str, Any],
    *,
    configured_slots: int,
    phase1: dict[str, Any] | None,
    pairwise_cluster_count: int,
    fix_mode: bool,
    fix_clean: bool,
    strict_three_reviewer_consensus: bool,
) -> None:
    """When iterative convergence is disabled, still attach reviewer coverage + consensus_mode."""
    ok = initial_successful_count(phase1)
    reconcile_consensus_fields(
        meta,
        configured_slots=configured_slots,
        successful_count=ok,
        pairwise_cluster_count=pairwise_cluster_count,
        fix_mode=fix_mode,
        fix_clean=fix_clean,
        strict_three_reviewer_consensus=strict_three_reviewer_consensus,
    )
