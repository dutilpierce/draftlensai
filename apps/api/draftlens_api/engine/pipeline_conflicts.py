from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from draftlens_api.domain.models import Issue, ReviewJobConfig
from draftlens_api.engine.material_discrepancy import (
    pair_material_discrepancy_reasons,
    should_count_pair_toward_material_discrepancy,
)


@dataclass
class ConflictCluster:
    cluster_id: str
    issues: list[Issue]
    reasons: list[str] = field(default_factory=list)

    def model_dump_issues(self) -> list[dict]:
        return [i.model_dump(mode="json") for i in self.issues]


def detect_conflicts(
    issues: list[Issue],
    *,
    material_severities: set[str] | None = None,
    severity_rank_gap_min: int = 1,
    do_not_change_corpus: str = "",
) -> list[ConflictCluster]:
    """
    Deterministic material cross-model discrepancy detection on a deduped issue ledger.

    Primary convergence metric: count of merged clusters here (each is at least one
    material pairwise discrepancy on an overlapping span).
    """
    clusters: list[ConflictCluster] = []
    n = len(issues)
    used: set[tuple[str, str]] = set()

    def pair_key(i: Issue, j: Issue) -> tuple[str, str]:
        a, b = sorted([i.issue_id, j.issue_id])
        return (a, b)

    for i in range(n):
        for j in range(i + 1, n):
            a, b = issues[i], issues[j]
            key = pair_key(a, b)
            if key in used:
                continue
            reasons = pair_material_discrepancy_reasons(
                a,
                b,
                severity_rank_gap_min=severity_rank_gap_min,
                do_not_change_corpus=do_not_change_corpus,
            )
            if not reasons:
                continue
            if not should_count_pair_toward_material_discrepancy(
                a, b, reasons, material_severities=material_severities
            ):
                continue
            used.add(key)
            clusters.append(
                ConflictCluster(
                    cluster_id=str(uuid.uuid4()),
                    issues=[a, b],
                    reasons=reasons,
                )
            )

    merged = _merge_overlapping_clusters(clusters)
    return merged


def material_discrepancy_detect_kwargs(cfg: ReviewJobConfig) -> dict[str, object]:
    """Shared kwargs for `detect_conflicts` across graph + iterative convergence."""
    ir = cfg.iterative_review
    return {
        "material_severities": set(ir.material_issue_severities),
        "severity_rank_gap_min": ir.severity_rank_gap_material_min,
        "do_not_change_corpus": (cfg.do_not_change or "").strip(),
    }


def _merge_overlapping_clusters(clusters: list[ConflictCluster]) -> list[ConflictCluster]:
    """Union clusters that share any issue_id."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for c in clusters:
        ids = [i.issue_id for i in c.issues]
        if len(ids) >= 2:
            for k in ids[1:]:
                union(ids[0], k)

    buckets: dict[str, ConflictCluster] = {}
    for c in clusters:
        root = find(c.issues[0].issue_id)
        if root not in buckets:
            buckets[root] = ConflictCluster(cluster_id=root, issues=[], reasons=[])
        seen_ids = {x.issue_id for x in buckets[root].issues}
        for it in c.issues:
            if it.issue_id not in seen_ids:
                buckets[root].issues.append(it)
                seen_ids.add(it.issue_id)
        for r in c.reasons:
            if r not in buckets[root].reasons:
                buckets[root].reasons.append(r)
    return list(buckets.values())
