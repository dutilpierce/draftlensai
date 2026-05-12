from __future__ import annotations

import re

from draftlens_api.domain.models import DocumentBlock
from draftlens_api.evidence.scoring import score_evidence_for_block
from draftlens_api.evidence.index_sqlite import EvidenceIndex
from draftlens_api.evidence.types import EvidenceChunk, EvidenceExcerpt, EvidenceRankingResult


def _query_tokens(text: str, *, max_tokens: int = 12) -> list[str]:
    found = re.findall(r"[a-z0-9]{4,}", text.lower())
    out: list[str] = []
    seen: set[str] = set()
    for t in found:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= max_tokens:
            break
    return out


def _fts_query_string(tokens: list[str]) -> str:
    parts: list[str] = []
    for t in tokens:
        safe = re.sub(r"[^a-z0-9_]", "", t)
        if len(safe) < 3:
            continue
        parts.append(safe)
    if not parts:
        return ""
    return " OR ".join(parts)


class EvidenceRetriever:
    """
    Lightweight relevance: FTS BM25 when available, else Jaccard overlap on chunks.
    """

    def __init__(
        self,
        *,
        chunks: list[EvidenceChunk],
        index: EvidenceIndex | None,
        has_supporting_files: bool,
        partial_file: bool,
    ) -> None:
        self._chunks = {c.chunk_id: c for c in chunks}
        self._chunks_list = chunks
        self._index = index
        self._has_supporting = has_supporting_files
        self._partial_file = partial_file

    def rank_for_block(
        self,
        block: DocumentBlock,
        *,
        top_k: int = 5,
        max_chars_each: int = 900,
    ) -> EvidenceRankingResult:
        if not self._has_supporting or not self._chunks_list:
            return EvidenceRankingResult(
                block_id=block.block_id,
                excerpts=[],
                evidence_note=(
                    "No supporting evidence files attached. For factual accuracy, use accuracy_posture "
                    "unsupported or unverified rather than asserting external facts as false."
                ),
            )

        tokens = _query_tokens(block.text)
        fts_hits: list[tuple[str, str, str, float]] = []
        if self._index and self._index.fts_enabled and tokens:
            q = _fts_query_string(tokens)
            if q:
                fts_hits = self._index.search(q, limit=max(32, top_k * 6))

        excerpts: list[EvidenceExcerpt] = []
        seen: set[str] = set()

        if fts_hits:
            for cid, lab, body, sc in fts_hits:
                if cid in seen:
                    continue
                seen.add(cid)
                clip = body.strip()
                if len(clip) > max_chars_each:
                    clip = clip[:max_chars_each] + "\n[excerpt truncated]"
                excerpts.append(
                    EvidenceExcerpt(
                        chunk_id=cid,
                        source_label=lab,
                        text=clip,
                        score=sc,
                        rank_method="fts_bm25",
                    )
                )
                if len(excerpts) >= top_k:
                    break

        if len(excerpts) < top_k:
            ranked: list[tuple[float, EvidenceChunk]] = []
            for ch in self._chunks_list:
                if ch.chunk_id in seen:
                    continue
                sc = score_evidence_for_block(block, ch.text)
                ranked.append((sc, ch))
            ranked.sort(key=lambda x: x[0], reverse=True)
            for sc, ch in ranked:
                if len(excerpts) >= top_k:
                    break
                clip = ch.text.strip()
                if len(clip) > max_chars_each:
                    clip = clip[:max_chars_each] + "\n[excerpt truncated]"
                excerpts.append(
                    EvidenceExcerpt(
                        chunk_id=ch.chunk_id,
                        source_label=ch.source_label,
                        text=clip,
                        score=max(0.0, min(1.0, sc)),
                        rank_method="lexical_jaccard",
                    )
                )

        note_parts: list[str] = []
        if self._partial_file:
            note_parts.append("Some supporting files had partial extraction; excerpts may be incomplete.")
        if not excerpts:
            note_parts.append(
                "No confident evidence overlap for this block; treat factual challenges as unverified unless "
                "internally provable from the main text."
            )
        elif not fts_hits and tokens:
            note_parts.append("Lexical overlap only (FTS sparse); treat excerpt relevance as moderate.")
        elif excerpts and all(e.rank_method == "lexical_jaccard" for e in excerpts):
            note_parts.append("Evidence ranking used lexical overlap (FTS unavailable or empty for this query).")

        return EvidenceRankingResult(
            block_id=block.block_id,
            excerpts=excerpts[:top_k],
            evidence_note=" ".join(note_parts).strip()
            or "Supporting evidence available; use excerpts only to verify or challenge factual claims.",
        )
