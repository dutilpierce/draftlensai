from __future__ import annotations

from pathlib import Path

from draftlens_api.domain.models import DocumentBlock
from draftlens_api.evidence.index_sqlite import EvidenceIndex
from draftlens_api.evidence.retriever import EvidenceRetriever
from draftlens_api.evidence.supporting_parser import SupportingFileParser
from draftlens_api.evidence.types import EvidenceChunk


def test_supporting_parser_txt_chunks(tmp_path: Path) -> None:
    p = tmp_path / "note.txt"
    p.write_text("alpha beta gamma.\n\n" + ("word " * 400), encoding="utf-8")
    pr = SupportingFileParser().parse(p, "note.txt")
    assert pr.chunks
    assert pr.audit.status in {"ok", "partial"}


def test_evidence_index_and_retriever_ranking(tmp_path: Path) -> None:
    chunks = [
        EvidenceChunk(
            chunk_id="c1",
            source_label="ref.pdf",
            text="The revenue for Q3 was forty two million dollars according to internal finance.",
            ordinal=0,
        ),
        EvidenceChunk(
            chunk_id="c2",
            source_label="ref.pdf",
            text="Unrelated narrative about office cats and coffee machines.",
            ordinal=1,
        ),
    ]
    db = tmp_path / "evidence.sqlite"
    idx = EvidenceIndex.build(db, chunks)
    retriever = EvidenceRetriever(
        chunks=chunks,
        index=idx,
        has_supporting_files=True,
        partial_file=False,
    )
    blk = DocumentBlock(block_id="b1", char_start=0, char_end=80, text="We claim Q3 revenue hit 42 million.")
    res = retriever.rank_for_block(blk, top_k=2)
    assert res.block_id == "b1"
    assert res.excerpts
    top = res.excerpts[0].text.lower()
    assert "revenue" in top or "million" in top
