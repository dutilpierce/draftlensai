"""
Regression: langgraph_review_graph.chunk_document must call chunk_document_blocks.

A missing module-level import caused NameError at runtime after normalization.
"""

from __future__ import annotations

from pathlib import Path

from draftlens_api.domain.models import DocumentBlock
from draftlens_api.services.document_blocks import chunk_document_blocks


def _langgraph_source() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / "draftlens_api" / "engine" / "langgraph_review_graph.py").read_text(encoding="utf-8")


def test_langgraph_imports_chunk_document_blocks() -> None:
    src = _langgraph_source()
    assert "from draftlens_api.services.document_blocks import chunk_document_blocks" in src, (
        "langgraph_review_graph must import chunk_document_blocks at module scope"
    )
    assert "blocks = chunk_document_blocks(" in src


def test_chunk_document_stage_output_shape_matches_downstream() -> None:
    """Same helper the graph uses: list[DocumentBlock] with stable ids and char ranges."""
    text = "Intro.\n\n" + ("body word " * 80) + "\n\nOutro."
    blocks = chunk_document_blocks(text, max_chars=200)
    assert len(blocks) >= 1
    for b in blocks:
        DocumentBlock.model_validate(b.model_dump(mode="json"))
    assert blocks[0].char_start <= blocks[-1].char_start
