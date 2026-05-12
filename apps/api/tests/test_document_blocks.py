from __future__ import annotations

from draftlens_api.services.document_blocks import chunk_document_blocks


def test_chunk_stable_order_and_paragraph_merge() -> None:
    text = "A short para.\n\n" + ("B word " * 200) + "\n\nFinal tail here."
    blocks = chunk_document_blocks(text, max_chars=600)
    assert blocks[0].char_start < blocks[-1].char_start
    joined = "".join(b.text for b in blocks)
    assert "A short" in joined and "Final tail" in joined
