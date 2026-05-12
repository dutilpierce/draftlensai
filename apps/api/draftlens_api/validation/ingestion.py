from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

_ALLOWED_MAIN_SUFFIXES = frozenset({".docx", ".pdf"})
_ALLOWED_SUPPORTING_SUFFIXES = frozenset({".docx", ".pdf", ".txt", ".md", ".doc"})

# Defense-in-depth caps (multipart limits also apply at the ASGI server).
_MAX_SUPPORTING_FILES = 12
_MAX_SUPPORTING_FILE_BYTES = 25 * 1024 * 1024  # 25 MiB each
_MAX_MAIN_FILE_BYTES = 40 * 1024 * 1024  # 40 MiB


def validate_main_upload_filename(filename: str | None) -> str:
    name = Path(filename or "document").name
    suf = Path(name).suffix.lower()
    if suf not in _ALLOWED_MAIN_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=(
                "invalid_main_document_type — main manuscript must be .docx or .pdf. "
                "Classic .doc is not supported yet; save as .docx or export to PDF."
            ),
        )
    return name


def validate_supporting_upload_filename(filename: str | None) -> str:
    name = Path(filename or "supporting").name
    suf = Path(name).suffix.lower()
    if suf not in _ALLOWED_SUPPORTING_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=(
                "invalid_supporting_file_type — allowed evidence types: .docx, .pdf, .txt, .md, .doc. "
                "Supporting files are reference-only and are not edited in v1."
            ),
        )
    return name


def validate_supporting_file_list(*, count: int, byte_sizes: list[int] | None = None) -> None:
    if count > _MAX_SUPPORTING_FILES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"too_many_supporting_files — at most {_MAX_SUPPORTING_FILES} supporting evidence files "
                "are accepted per job."
            ),
        )
    if byte_sizes:
        for i, sz in enumerate(byte_sizes):
            if sz > _MAX_SUPPORTING_FILE_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"supporting_file_too_large — file #{i + 1} exceeds "
                        f"{_MAX_SUPPORTING_FILE_BYTES // (1024 * 1024)} MiB."
                    ),
                )


def validate_main_file_size(byte_size: int) -> None:
    if byte_size > _MAX_MAIN_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"main_document_too_large — main document exceeds {_MAX_MAIN_FILE_BYTES // (1024 * 1024)} MiB."
            ),
        )


def validate_supporting_file_byte_size(byte_size: int) -> None:
    if byte_size > _MAX_SUPPORTING_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"supporting_file_too_large — each supporting evidence file must be "
                f"at most {_MAX_SUPPORTING_FILE_BYTES // (1024 * 1024)} MiB."
            ),
        )
