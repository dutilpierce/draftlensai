"""Classify artifacts for default vs advanced downloads."""

from __future__ import annotations

PRIMARY_REVIEW = {
    "reviewed.pdf",
    "reviewed.docx",
    "redline.pdf",
    "review_summary.pdf",
    "issues.pdf",
}
PRIMARY_FIX = {
    "corrected.docx",
    "corrected.pdf",
    "change_log.pdf",
}
ADVANCED = {
    "redline.html",
    "issues.json",
    "changes.json",
    "issues.md",
    "review_summary.md",
    "change_log.md",
    "pipeline_stats.json",
    "pipeline_manifest.json",
}


def artifact_tier(name: str, *, output_mode: str) -> str:
    n = name.lower()
    if n in ADVANCED or n.endswith(".json") and n not in {"pipeline_stats.json"}:
        return "advanced"
    primary = PRIMARY_FIX if output_mode == "fix" else PRIMARY_REVIEW
    if n in primary:
        return "primary"
    if n.endswith(".pdf") or n.endswith(".docx"):
        return "primary"
    return "advanced"


def annotate_rows(rows: list[dict[str, str]], *, output_mode: str) -> list[dict[str, str]]:
    out = []
    for r in rows:
        name = str(r.get("name", ""))
        tier = artifact_tier(name, output_mode=output_mode)
        out.append({**r, "tier": tier})
    return out
