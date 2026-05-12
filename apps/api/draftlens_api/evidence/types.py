from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class EvidenceChunk(BaseModel):
    """A searchable slice of normalized supporting text (reference-only; never edited)."""

    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_label: str
    source_suffix: str = ""
    text: str
    ordinal: int = 0
    extraction_quality: Literal["ok", "partial", "failed"] = "ok"


class EvidenceExcerpt(BaseModel):
    """One ranked snippet proposed for model context."""

    chunk_id: str
    source_label: str
    text: str
    score: float = Field(ge=0.0, le=1.0, description="Higher is more relevant (heuristic).")
    rank_method: Literal["fts_bm25", "lexical_jaccard", "none"] = "lexical_jaccard"


class EvidenceRankingResult(BaseModel):
    """Retrieval output for a single main-document block."""

    block_id: str
    excerpts: list[EvidenceExcerpt] = Field(default_factory=list)
    evidence_note: str = ""


class SupportingFileExtractionAudit(BaseModel):
    """Auditable extraction record for one supporting file (filesystem + parsing only)."""

    original_name: str
    storage_basename: str
    suffix: str
    status: Literal["ok", "partial", "failed"] = "ok"
    chars_extracted: int = 0
    chunks_emitted: int = 0
    pages_estimate: int | None = None
    error: str | None = None


class EvidenceIngestionAudit(BaseModel):
    """Written to disk per job for debugging; not exposed in product UI."""

    job_id: str
    files: list[SupportingFileExtractionAudit] = Field(default_factory=list)
    total_chunks: int = 0
    fts_index_built: bool = False
    fts_index_path: str | None = None
