from __future__ import annotations

import re

from draftlens_api.domain.models import DocumentBlock


def _paragraph_spans(full_text: str) -> list[tuple[int, int]]:
    """Non-overlapping spans covering the full string, split on blank-line boundaries."""
    if not full_text:
        return []
    spans: list[tuple[int, int]] = []
    start = 0
    for m in re.finditer(r"\n\s*\n+", full_text):
        if m.start() > start:
            spans.append((start, m.start()))
        start = m.end()
    if start < len(full_text):
        spans.append((start, len(full_text)))
    return spans or [(0, len(full_text))]


def _split_oversized(span: tuple[int, int], full_text: str, max_chars: int) -> list[tuple[int, int]]:
    s, e = span
    if e - s <= max_chars:
        return [span]
    out: list[tuple[int, int]] = []
    pos = s
    while pos < e:
        end = min(pos + max_chars, e)
        out.append((pos, end))
        pos = end
    return out


def chunk_document_blocks(
    full_text: str,
    *,
    max_chars: int = 2400,
    _min_merge_chars: int = 120,
) -> list[DocumentBlock]:
    """
    Paragraph/section-boundary-aware chunking with stable document order.
    Oversized paragraphs are hard-split at max_chars with exact char offsets preserved.
    """
    _ = _min_merge_chars  # reserved for future merge heuristics
    if not full_text.strip():
        return [DocumentBlock(block_id="b-0001", char_start=0, char_end=0, text="")]

    raw_spans = _paragraph_spans(full_text)
    expanded: list[tuple[int, int]] = []
    for sp in raw_spans:
        expanded.extend(_split_oversized(sp, full_text, max_chars))

    merged: list[tuple[int, int]] = []
    cur_s, cur_e = expanded[0]
    for s, e in expanded[1:]:
        if e - cur_s <= max_chars:
            cur_e = e
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))

    blocks: list[DocumentBlock] = []
    for i, (cs, ce) in enumerate(merged, start=1):
        text = full_text[cs:ce]
        blocks.append(DocumentBlock(block_id=f"b-{i:04d}", char_start=cs, char_end=ce, text=text))
    return blocks
