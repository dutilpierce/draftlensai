from __future__ import annotations

import re
from typing import Iterable

from draftlens_api.domain.models import DocumentBlock, EvidenceSource
from draftlens_api.evidence.scoring import score_evidence_for_block


def rank_evidence_for_block(
    block: DocumentBlock,
    sources: Iterable[EvidenceSource],
    *,
    max_excerpts: int = 4,
    max_chars_each: int = 900,
) -> list[str]:
    """Return ranked supporting excerpts (reference-only) for a single block."""
    ranked: list[tuple[float, EvidenceSource]] = []
    for src in sources:
        if src.kind != "supporting":
            continue
        score = score_evidence_for_block(block, src.excerpt)
        ranked.append((score, src))
    ranked.sort(key=lambda x: x[0], reverse=True)
    out: list[str] = []
    for score, src in ranked[:max_excerpts]:
        clip = src.excerpt.strip()
        if len(clip) > max_chars_each:
            clip = clip[:max_chars_each] + "\n[excerpt truncated]"
        label = src.label.strip() or "supporting"
        out.append(f"[{label}] (relevance={score:.2f})\n{clip}")
    return out


def split_evidence_bundle(bundle: str) -> list[EvidenceSource]:
    """Parse bundled `### filename` sections into sources."""
    if not bundle.strip():
        return []
    parts = re.split(r"(?m)^###\s+", bundle.strip())
    sources: list[EvidenceSource] = []
    for chunk in parts:
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.splitlines()
        label = lines[0].strip() if lines else "supporting"
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else chunk
        sources.append(EvidenceSource(label=label, excerpt=body, kind="supporting"))
    return sources
