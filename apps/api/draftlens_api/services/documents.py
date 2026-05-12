"""Document extraction — re-exports unified parsers for main and supporting paths."""

from __future__ import annotations

from pathlib import Path

from draftlens_api.services.document_parsers import (
    MainExtractionResult,
    NormalizedDocument,
    ParsedPage,
    UserFacingDocumentError,
    extract_docx,
    extract_pdf,
    extract_plain,
    extract_supporting,
    normalize_supporting_file,
    parse_main_manuscript,
)

__all__ = [
    "MainExtractionResult",
    "NormalizedDocument",
    "ParsedPage",
    "UserFacingDocumentError",
    "extract_docx",
    "extract_main_document",
    "extract_pdf",
    "extract_plain",
    "extract_supporting",
    "normalize_supporting_file",
]


def extract_main_document(path: Path, filename: str) -> MainExtractionResult:
    return parse_main_manuscript(path, filename)
