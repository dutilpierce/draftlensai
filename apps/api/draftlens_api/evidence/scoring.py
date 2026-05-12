from __future__ import annotations

import re

from draftlens_api.domain.models import DocumentBlock


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]{3,}", text.lower()) if t}


def score_evidence_for_block(block: DocumentBlock, excerpt: str) -> float:
    """Lexical overlap score between a document block and an evidence excerpt."""
    bt = _tokenize(block.text)
    et = _tokenize(excerpt)
    if not bt or not et:
        return 0.0
    inter = len(bt & et)
    union = len(bt | et)
    return float(inter) / float(union) if union else 0.0
