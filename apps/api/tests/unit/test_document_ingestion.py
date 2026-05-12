from __future__ import annotations

from pathlib import Path

import pytest
from fpdf import FPDF

from draftlens_api.services.document_blocks import chunk_document_blocks
from draftlens_api.services.document_parsers import (
    UserFacingDocumentError,
    extract_supporting,
    normalize_supporting_file,
    parse_main_manuscript,
)
from tests.conftest import minimal_docx_bytes


def test_parse_main_docx_ok(tmp_path: Path) -> None:
    p = tmp_path / "m.docx"
    p.write_bytes(minimal_docx_bytes())
    r = parse_main_manuscript(p, "m.docx")
    assert r.source_format == "docx"
    assert r.pages >= 1
    assert "Hello" in r.text


def test_parse_main_pdf_blank_raises_user_facing(tmp_path: Path) -> None:
    from pypdf import PdfWriter

    p = tmp_path / "blank.pdf"
    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    with p.open("wb") as fh:
        w.write(fh)
    with pytest.raises(UserFacingDocumentError, match="no selectable text"):
        parse_main_manuscript(p, "blank.pdf")


def test_parse_main_pdf_with_selectable_text(tmp_path: Path) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    body = "Lorem ipsum dolor sit amet. " * 80
    pdf.multi_cell(0, 6, body)
    p = tmp_path / "filled.pdf"
    pdf.output(str(p))
    r = parse_main_manuscript(p, "filled.pdf")
    assert r.source_format == "pdf"
    assert r.pages >= 1
    assert "--- PDF page 1 ---" in r.text
    assert "Lorem ipsum" in r.text


def test_chunking_preserves_pdf_page_markers(tmp_path: Path) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, "Para one content here.\n\n" * 40)
    p = tmp_path / "p2.pdf"
    pdf.output(str(p))
    r = parse_main_manuscript(p, "p2.pdf")
    blocks = chunk_document_blocks(r.text, max_chars=2400)
    joined = "\n".join(b.text for b in blocks)
    assert "--- PDF page 1 ---" in joined


def test_normalize_supporting_doc_placeholder(tmp_path: Path) -> None:
    p = tmp_path / "legacy.doc"
    p.write_bytes(b"0\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\x00")  # OLE-like header fragment
    n = normalize_supporting_file(p, "legacy.doc")
    assert n.source_format == "doc"
    assert "not fully supported" in n.plain_text


def test_extract_supporting_doc_string(tmp_path: Path) -> None:
    p = tmp_path / "x.doc"
    p.write_bytes(b"x")
    s = extract_supporting(p, "x.doc")
    assert "not fully supported" in s


def test_main_pdf_mime_and_format(tmp_path: Path) -> None:
    p = tmp_path / "m.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, "Enough text for a full main manuscript body here. " * 60)
    pdf.output(str(p))
    r = parse_main_manuscript(p, "m.pdf")
    assert r.mime == "application/pdf"
    assert r.source_format == "pdf"
