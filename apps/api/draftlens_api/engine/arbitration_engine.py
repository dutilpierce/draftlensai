from __future__ import annotations

import uuid

from draftlens_api.domain.models import ArbitrationDecision, ConflictSet, ProposedEdit
from draftlens_api.providers.normalization import issues_from_payload
from draftlens_api.routing.agent_assignment import ResolvedModel
from draftlens_api.routing.model_registry import ModelRegistry


class ArbitrationEngine:
    """Final arbitration pass; consumes only normalized debate artifacts."""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    async def run(
        self,
        *,
        arbiter: ResolvedModel,
        debate_digest: str,
        conflicts: list[ConflictSet],
        document_excerpt: str,
        output_mode: str,
        do_not_change: str,
        context: str,
    ) -> ArbitrationDecision:
        adapter = self._registry.adapter(arbiter)
        system = (
            "You are the final arbiter for DraftLens. Return a single JSON object (no markdown) with keys: "
            "executive_summary (string), "
            "issues (array of objects with block_id, span_text, char_start, char_end, category, severity, "
            "title, explanation, evidence_basis, confidence, suggested_fix, preserve_voice_notes, source_agents array, status), "
            "proposed_edits (array of {block_id, before, after, rationale, source_agents}), "
            "resolved_conflicts (array of {topic, positions object, unresolved boolean}), "
        )
        if output_mode == "fix":
            system += "corrected_document_text (string, full revised plain text of the document). "
        else:
            system += "redline_html_fragment (string, HTML fragment only). "

        system += (
            "Categories must be one of: accuracy, logic, consistency, grammar, clarity, formatting, citation, tone, risk. "
            "Severities must be one of: critical, major, minor, nit. "
            "Respect do-not-change constraints unless there is a severe issue."
        )

        user = (
            f"Author context:\n{context or '(none)'}\n\n"
            f"Do-not-change list:\n{do_not_change or '(none)'}\n\n"
            f"Debate digest:\n{debate_digest}\n\n"
            f"Structured conflicts:\n{[c.model_dump() for c in conflicts]}\n\n"
            f"Document excerpt (truncated):\n{document_excerpt[:12000]}"
        )

        payload, err = await adapter.complete_json_with_retry(
            model_id=arbiter.model_id, system=system, user=user
        )
        if payload is None:
            raise RuntimeError(f"arbiter_failed:{err}")

        issues_raw = payload.get("issues") or []
        issues = issues_from_payload(issues_raw, default_block_id="doc-root", source_agent="arbiter")

        edits_raw = payload.get("proposed_edits") or []
        edits: list[ProposedEdit] = []
        if isinstance(edits_raw, list):
            for e in edits_raw:
                if not isinstance(e, dict):
                    continue
                edits.append(
                    ProposedEdit(
                        block_id=str(e.get("block_id", "doc-root")),
                        before=str(e.get("before", "")),
                        after=str(e.get("after", "")),
                        rationale=str(e.get("rationale", "")),
                        source_agents=[str(x) for x in e.get("source_agents", [])] or ["arbiter"],
                    )
                )

        resolved: list[ConflictSet] = []
        rc = payload.get("resolved_conflicts")
        if isinstance(rc, list):
            for item in rc:
                if not isinstance(item, dict):
                    continue
                pos = item.get("positions") or {}
                if not isinstance(pos, dict):
                    pos = {}
                resolved.append(
                    ConflictSet(
                        conflict_id=str(item.get("conflict_id") or uuid.uuid4()),
                        topic=str(item.get("topic", "")),
                        positions={str(k): str(v) for k, v in pos.items()},
                        unresolved=bool(item.get("unresolved", True)),
                    )
                )

        return ArbitrationDecision(
            executive_summary=str(payload.get("executive_summary", "")).strip() or "Arbitration complete.",
            resolved_conflicts=resolved or conflicts,
            issues=issues,
            proposed_edits=edits,
            corrected_document_text=payload.get("corrected_document_text"),
            redline_html_fragment=payload.get("redline_html_fragment"),
        )
