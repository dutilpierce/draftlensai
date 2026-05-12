"""Shared caps for reviewer issue lists (per-block + global)."""

from __future__ import annotations

from collections import defaultdict

from draftlens_api.domain.models import Issue

MAX_ISSUES_PER_BLOCK = 6
MAX_ISSUES_GLOBAL = 36

_ORDER = ["critical", "major", "minor", "nit"]


def cap_reviewer_issues(issues: list[Issue]) -> list[Issue]:
    def sev_key(it: Issue) -> int:
        try:
            return _ORDER.index(it.severity.value)
        except ValueError:
            return 9

    sorted_issues = sorted(issues, key=sev_key)
    per_block: dict[str, int] = defaultdict(int)
    out: list[Issue] = []
    for it in sorted_issues:
        if per_block[it.block_id] >= MAX_ISSUES_PER_BLOCK:
            continue
        per_block[it.block_id] += 1
        out.append(it)
        if len(out) >= MAX_ISSUES_GLOBAL:
            break
    return out
