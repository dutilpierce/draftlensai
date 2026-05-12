from __future__ import annotations

import logging
from dataclasses import dataclass

from draftlens_api.artifacts.disclaimers import build_disclaimer_bundle
from draftlens_api.domain.models import (
    AgentFinding,
    ArbitrationDecision,
    DocumentBlock,
    FinalLedger,
    RenderPlan,
    ReviewJobConfig,
)
from draftlens_api.engine.arbitration_engine import ArbitrationEngine
from draftlens_api.engine.debate_coordinator import DebateCoordinator
from draftlens_api.providers.normalization import agent_finding_from_payload
from draftlens_api.routing.agent_assignment import ResolvedModel
from draftlens_api.routing.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

REVIEWER_JSON_CONTRACT = (
    "Return a single JSON object with keys: "
    "summary (string), risks (array of strings), questions_for_peers (array of strings), "
    "issues (array of objects with block_id, span_text, char_start, char_end, category, severity, "
    "title, explanation, evidence_basis, confidence, suggested_fix, preserve_voice_notes, source_agents, status). "
    "Use only allowed categories and severities from the system instructions."
)


@dataclass
class ReviewContext:
    job_id: str
    job_config: ReviewJobConfig
    document_text: str
    blocks: list[DocumentBlock]
    evidence_bundle: str


class ReviewEngine:
    """Coordinates multi-model review, debate packaging, quorum checks, and arbitration."""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry
        self._debate = DebateCoordinator()
        self._arb = ArbitrationEngine(registry)

    async def execute(self, ctx: ReviewContext) -> tuple[FinalLedger, RenderPlan, ArbitrationDecision]:
        assign = self._registry.assignment()
        blocks_excerpt = "\n\n".join(f"[{b.block_id}]\n{b.text}" for b in ctx.blocks[:12])
        if len(ctx.blocks) > 12:
            blocks_excerpt += "\n\n[additional blocks omitted for prompt size]"

        base_user = (
            f"Review focus: {ctx.job_config.review_focus}\n"
            f"Sensitive mode: {ctx.job_config.sensitive_mode}\n"
            f"Output mode (informational): {ctx.job_config.output_mode}\n\n"
            f"Author-added context:\n{ctx.job_config.context_text or '(none)'}\n\n"
            f"Do-not-change list:\n{ctx.job_config.do_not_change or '(none)'}\n\n"
            f"Supporting evidence (reference only):\n{ctx.evidence_bundle or '(none)'}\n\n"
            f"Document blocks:\n{blocks_excerpt}"
        )

        reviewer_plan: list[tuple[str, str, ResolvedModel]] = [
            ("author_intent", "You capture author intent, structural risks, and missing context.", assign.author_intent),
            (
                "skeptical_reviewer",
                "You challenge assumptions and hunt for contradictions versus evidence and internal consistency.",
                assign.skeptical_reviewer,
            ),
            (
                "consistency_parser",
                "You focus on mechanical consistency, citations, numbering, and cross-block alignment.",
                assign.consistency_parser,
            ),
        ]

        prior_notes: list[str] = []
        findings: list[AgentFinding] = []

        for role, instruction, resolved in reviewer_plan:
            adapter = self._registry.adapter(resolved)
            system = (
                f"You are the {role} reviewer for DraftLens. {instruction}\n"
                f"{REVIEWER_JSON_CONTRACT}\n"
                "Severity must be critical|major|minor|nit. Category must be one of the allowed taxonomy values."
            )
            user = base_user
            if prior_notes:
                user += "\n\nPeer notes so far:\n" + "\n---\n".join(prior_notes)

            if not adapter.configured:
                findings.append(
                    AgentFinding(
                        agent_role=role,
                        summary="",
                        unavailable=True,
                        error_code=f"{resolved.provider}_not_configured",
                    )
                )
                prior_notes.append(f"{role}: unavailable ({resolved.provider} not configured)")
                continue

            payload, err = await adapter.complete_json_with_retry(
                model_id=resolved.model_id, system=system, user=user
            )
            if payload is None:
                findings.append(
                    AgentFinding(
                        agent_role=role,
                        summary="",
                        unavailable=True,
                        error_code=err or "unknown_error",
                    )
                )
                prior_notes.append(f"{role}: unavailable ({err})")
                continue

            finding = agent_finding_from_payload(payload, role=role)
            findings.append(finding)
            prior_notes.append(f"{role}: {finding.summary}")

        active = [f for f in findings if not f.unavailable]
        if len(active) < 2:
            raise RuntimeError(
                f"quorum_not_met: need>=2 active reviewers; got {len(active)}. "
                f"Unavailable={[f.agent_role for f in findings if f.unavailable]}"
            )

        arb_adapter = self._registry.adapter(assign.arbiter)
        if not arb_adapter.configured:
            raise RuntimeError("arbiter_not_configured")

        digest = self._debate.build_digest(findings)
        conflicts = self._debate.build_conflicts(findings)

        excerpt = ctx.document_text[:20000]
        decision = await self._arb.run(
            arbiter=assign.arbiter,
            debate_digest=digest,
            conflicts=conflicts,
            document_excerpt=excerpt,
            output_mode=ctx.job_config.output_mode,
            do_not_change=ctx.job_config.do_not_change or "",
            context=ctx.job_config.context_text or "",
        )

        disclaimers = build_disclaimer_bundle(
            sensitive_mode=ctx.job_config.sensitive_mode,
            has_supporting_files=bool((ctx.evidence_bundle or "").strip()),
        )

        ledger = FinalLedger(
            job_id=ctx.job_id,
            debate_digest=digest,
            participating_agents=[f.agent_role for f in findings if not f.unavailable] + ["arbiter"],
            unavailable_agents=[f.agent_role for f in findings if f.unavailable],
            quorum_met=True,
            arbitration=decision,
            disclaimers=disclaimers,
        )

        plan = RenderPlan(
            emit_corrected_docx=ctx.job_config.output_mode == "fix",
            emit_change_log_md=ctx.job_config.output_mode == "fix",
            emit_changes_json=ctx.job_config.output_mode == "fix",
        )

        return ledger, plan, decision
