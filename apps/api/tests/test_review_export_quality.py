"""Review bundle export: no PDF markers in body, no issue table in reviewed.docx, strip helpers."""

from __future__ import annotations

from pathlib import Path

from docx import Document

from draftlens_api.artifacts import render as artifact_render


def test_strip_pdf_page_markers_removes_headers() -> None:
    raw = "--- PDF page 1 ---\n\nHello world.\n\n--- PDF page 2 ---\n\nNext part.\n"
    out = artifact_render.strip_pdf_page_markers_for_display(raw)
    assert "--- PDF page" not in out.lower()
    assert "Hello world." in out
    assert "Next part." in out


def test_reviewed_docx_plaintext_export_has_no_issue_table_heading(tmp_path: Path) -> None:
    issues = [
        {
            "issue_id": "i1",
            "block_id": "b1",
            "severity": "minor",
            "category": "grammar",
            "title": "Typo",
            "explanation": "x",
            "suggested_fix": "y",
            "confidence": 0.9,
            "source_agents": ["claude_reviewer"],
            "span_text": "Hello",
            "char_start": 0,
            "char_end": 5,
        }
    ]
    arb = {"executive_summary": "ok", "issues": issues}
    rows = artifact_render.write_review_bundle(
        artifacts_dir=tmp_path / "a",
        original_docx_path=None,
        document_text="Hello world.\n\nSecond paragraph.",
        arbiter_payload=arb,
        debate_digest="",
        main_source_format="pdf",
        main_original_filename="paper.pdf",
    )
    names = {r["name"] for r in rows}
    assert "reviewed.docx" in names
    doc_path = next(r["path"] for r in rows if r["name"] == "reviewed.docx")
    doc = Document(doc_path)
    full = "\n".join(p.text for p in doc.paragraphs)
    assert "DraftLens Issue Table" not in full
    assert "--- PDF page" not in full.lower()


def test_write_redline_pdf_smoke(tmp_path: Path) -> None:
    from draftlens_api.services import pdf_artifact_service

    issues = [
        {
            "issue_id": "a",
            "severity": "major",
            "category": "legal",
            "title": "Defined term",
            "span_text": "foo",
            "suggested_fix": "bar",
            "explanation": "needs clarity",
        }
    ]
    p = tmp_path / "redline.pdf"
    ok = pdf_artifact_service.write_redline_pdf(issues, p, document_name="t.docx")
    assert ok is True
    assert p.is_file() and p.stat().st_size > 40


def test_iterative_meta_includes_cluster_summaries() -> None:
    from draftlens_api.engine.iterative_convergence import _summarize_unresolved_clusters

    payload = [
        {
            "cluster_id": "c1",
            "reasons": ["severity_disagreement"],
            "issues": [{"title": "T1", "severity": "major", "category": "x"}],
        }
    ]
    s = _summarize_unresolved_clusters(payload)
    assert s[0]["cluster_id"] == "c1"
    assert "severity_disagreement" in s[0]["reasons"]
