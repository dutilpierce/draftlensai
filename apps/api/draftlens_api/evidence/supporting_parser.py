from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from draftlens_api.domain.models import EvidenceSource
from draftlens_api.evidence.types import EvidenceChunk, SupportingFileExtractionAudit
from draftlens_api.services.document_parsers import normalize_supporting_file


def _chunk_text(text: str, *, target: int = 1400, overlap: int = 200) -> list[str]:
    """Greedy windowing with overlap; keeps paragraphs together when possible."""
    t = text.strip()
    if not t:
        return []
    if len(t) <= target:
        return [t]
    paras = re.split(r"\n{2,}", t)
    chunks: list[str] = []
    buf = ""
    for p in paras:
        p = p.strip()
        if not p:
            continue
        cand = (buf + "\n\n" + p).strip() if buf else p
        if len(cand) <= target:
            buf = cand
            continue
        if buf:
            chunks.append(buf)
        if len(p) <= target:
            buf = p
        else:
            # hard-split long paragraph
            start = 0
            while start < len(p):
                end = min(start + target, len(p))
                piece = p[start:end].strip()
                if piece:
                    chunks.append(piece)
                start = max(end - overlap, start + 1)
            buf = ""
    if buf:
        chunks.append(buf)
    return chunks


@dataclass
class SupportingParseResult:
    chunks: list[EvidenceChunk]
    bundle_section: str
    sources: list[EvidenceSource]
    audit: SupportingFileExtractionAudit


class SupportingFileParser:
    """
    Text extraction for supporting evidence (DOCX, PDF, TXT, MD, DOC placeholder).
    Never treats evidence as editable manuscript; outputs normalized chunks only.
    """

    def parse(self, path: Path, original_name: str) -> SupportingParseResult:
        suffix = path.suffix.lower()
        basename = path.name
        status: str = "ok"
        err: str | None = None
        pages: int | None = None

        try:
            norm = normalize_supporting_file(path, original_name)
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            err = str(exc)
            placeholder = EvidenceChunk(
                chunk_id=str(uuid.uuid4()),
                source_label=original_name,
                source_suffix=suffix,
                text=f"(extraction failed: {err})",
                ordinal=0,
                extraction_quality="failed",
            )
            audit = SupportingFileExtractionAudit(
                original_name=original_name,
                storage_basename=basename,
                suffix=suffix,
                status="failed",
                chars_extracted=0,
                chunks_emitted=1,
                pages_estimate=pages,
                error=err,
            )
            src = EvidenceSource(
                label=original_name,
                excerpt=placeholder.text,
                kind="supporting",
            )
            return SupportingParseResult(
                chunks=[placeholder],
                bundle_section=f"### {original_name}\n{placeholder.text}",
                sources=[src],
                audit=audit,
            )

        pages = norm.page_count
        if norm.extraction_quality == "empty":
            status = "partial"
        elif norm.extraction_quality == "low_text":
            status = "partial"

        clipped = norm.plain_text.strip()
        if not clipped:
            status = "partial"
            clipped = "(no extractable text; file may be scanned or empty)"
        elif len(clipped) > 120_000:
            clipped = clipped[:120_000] + "\n\n[truncated at 120k chars]"

        raw_parts = _chunk_text(clipped)
        if not raw_parts:
            raw_parts = [clipped] if clipped else ["(empty)"]

        chunks: list[EvidenceChunk] = []
        sources: list[EvidenceSource] = []
        bundle_lines: list[str] = [f"### {original_name}"]
        exq = "ok" if status == "ok" else "partial"
        for i, part in enumerate(raw_parts):
            q: str = exq
            if not part.strip() or "(no extractable text" in part:
                q = "partial"
            ch = EvidenceChunk(
                chunk_id=str(uuid.uuid4()),
                source_label=original_name,
                source_suffix=suffix,
                text=part,
                ordinal=i,
                extraction_quality="partial" if q == "partial" else "ok",
            )
            chunks.append(ch)
            label = f"{original_name} · chunk {i + 1}/{len(raw_parts)}"
            sources.append(EvidenceSource(label=label, excerpt=part, kind="supporting"))
            bundle_lines.append(f"#### chunk:{i}\n{part}")
        final_status = status
        if final_status == "ok" and any(c.extraction_quality == "partial" for c in chunks):
            final_status = "partial"

        audit = SupportingFileExtractionAudit(
            original_name=original_name,
            storage_basename=basename,
            suffix=suffix,
            status="partial" if final_status == "partial" else "ok",
            chars_extracted=len(clipped),
            chunks_emitted=len(chunks),
            pages_estimate=pages,
            error=err,
        )
        return SupportingParseResult(
            chunks=chunks,
            bundle_section="\n".join(bundle_lines).strip(),
            sources=sources,
            audit=audit,
        )
