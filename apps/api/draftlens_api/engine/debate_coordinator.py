from __future__ import annotations

from draftlens_api.domain.models import AgentFinding, ConflictSet


class DebateCoordinator:
    """Turns independent reviewer outputs into a shared digest and lightweight conflict objects."""

    def build_digest(self, findings: list[AgentFinding]) -> str:
        parts: list[str] = []
        for f in findings:
            if f.unavailable:
                parts.append(f"## {f.agent_role} (unavailable)\nError: {f.error_code or 'unknown'}")
                continue
            parts.append(f"## {f.agent_role}\n{f.summary}")
            if f.risks:
                parts.append("Risks:\n- " + "\n- ".join(f.risks))
            if f.questions_for_peers:
                parts.append("Questions for peers:\n- " + "\n- ".join(f.questions_for_peers))
        return "\n\n".join(parts).strip()

    def build_conflicts(self, findings: list[AgentFinding]) -> list[ConflictSet]:
        """Heuristic: group issues that share span_text but differ in severity or category."""
        from draftlens_api.domain.enums import IssueSeverity

        buckets: dict[str, list] = {}
        for f in findings:
            if f.unavailable:
                continue
            for issue in f.issue_candidates:
                key = (issue.span_text or "").strip()[:240]
                if not key:
                    continue
                buckets.setdefault(key, []).append((f.agent_role, issue))

        conflicts: list[ConflictSet] = []
        for key, items in buckets.items():
            if len(items) < 2:
                continue
            sev = {str(it[1].severity.value) for it in items}
            if len(sev) < 2:
                continue
            positions = {role: f"{issue.severity.value}:{issue.category.value}" for role, issue in items}
            conflicts.append(
                ConflictSet(
                    topic=key[:200],
                    positions=positions,
                    unresolved=True,
                )
            )
        if not conflicts:
            # synthetic “process” conflict if reviewers disagree on counts of major issues
            majors = [
                sum(1 for i in f.issue_candidates if i.severity == IssueSeverity.major)
                for f in findings
                if not f.unavailable
            ]
            if majors and max(majors) - min(majors) >= 2:
                conflicts.append(
                    ConflictSet(
                        topic="Major issue density disagreement",
                        positions={
                            f.agent_role: str(
                                sum(1 for i in f.issue_candidates if i.severity == IssueSeverity.major)
                            )
                            for f in findings
                            if not f.unavailable
                        },
                        unresolved=True,
                    )
                )
        return conflicts
