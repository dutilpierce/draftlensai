"""Best-effort PDF artifacts (never fails the job)."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _try_docx_to_pdf_windows(docx: Path, out_pdf: Path) -> bool:
    try:
        import docx2pdf  # type: ignore[import-untyped]
    except ImportError:
        return False
    try:
        docx2pdf.convert(str(docx), str(out_pdf))
        return out_pdf.is_file() and out_pdf.stat().st_size > 0
    except Exception as exc:  # noqa: BLE001
        logger.info("docx2pdf skipped: %s", exc)
        return False


def _try_libreoffice(docx: Path, out_dir: Path) -> Path | None:
    for cmd in ("soffice", "libreoffice"):
        try:
            subprocess.run(
                [cmd, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(docx)],
                check=True,
                timeout=120,
                capture_output=True,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError, OSError) as exc:
            logger.info("libreoffice convert skipped (%s): %s", cmd, exc)
            continue
        candidate = out_dir / (docx.stem + ".pdf")
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def convert_docx_to_pdf(docx: Path, out_pdf: Path) -> bool:
    """Return True if PDF written. Tries Word/docx2pdf on Windows, then LibreOffice on all platforms."""
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win") and _try_docx_to_pdf_windows(docx, out_pdf):
        return True
    lo = _try_libreoffice(docx, out_pdf.parent)
    if lo and lo != out_pdf:
        try:
            lo.replace(out_pdf)
            return True
        except OSError:
            pass
    elif lo:
        return True
    return False


def write_simple_issues_pdf(issues: list[dict[str, Any]], path: Path, *, title: str = "Issues") -> bool:
    """Lightweight PDF via fpdf2 when available."""
    try:
        from fpdf import FPDF  # type: ignore[import-untyped]
    except ImportError:
        logger.info("fpdf2 not installed; skipping issues PDF")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 5, title)
    pdf.ln(2)
    for i, it in enumerate(issues[:80], start=1):
        sev = str(it.get("severity", ""))
        cat = str(it.get("category", ""))
        tid = str(it.get("issue_id", ""))[:12]
        ttl = str(it.get("title", ""))[:120]
        snip = str(it.get("span_text", ""))[:180].replace("\n", " ")
        fix = str(it.get("suggested_fix", ""))[:220].replace("\n", " ")
        block = f"{i}. [{tid}] {sev}/{cat} — {ttl}"
        pdf.set_font("Helvetica", "B", 9)
        pdf.multi_cell(0, 4, block)
        pdf.set_font("Helvetica", size=8)
        pdf.multi_cell(0, 4, f"Snippet: {snip}")
        pdf.multi_cell(0, 4, f"Fix: {fix}")
        pdf.ln(1)
    try:
        pdf.output(str(path))
    except Exception as exc:  # noqa: BLE001
        logger.info("issues pdf write failed: %s", exc)
        return False
    return path.is_file()


def write_review_summary_pdf(
    *,
    path: Path,
    document_name: str,
    output_mode: str,
    reviewer_line: str,
    cycles: int,
    stats_sev: dict[str, int],
    stats_cat: dict[str, int],
    convergence_line: str,
    footer: str,
    consensus_coverage_lines: list[str] | None = None,
    extra_lines: list[str] | None = None,
) -> bool:
    try:
        from fpdf import FPDF  # type: ignore[import-untyped]
    except ImportError:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(0, 6, "DraftLens review summary")
    pdf.set_font("Helvetica", size=10)
    lines = [
        f"Document: {document_name}",
        f"Mode: {output_mode}",
        f"Reviewers: {reviewer_line}",
        f"Cycles completed: {cycles}",
        "",
        "Issues by severity:",
        ", ".join(f"{k}: {v}" for k, v in sorted(stats_sev.items())) or "(none)",
        "",
        "Issues by category:",
        ", ".join(f"{k}: {v}" for k, v in sorted(stats_cat.items())) or "(none)",
        "",
        f"Convergence: {convergence_line}",
        "",
    ]
    if consensus_coverage_lines:
        lines.extend(consensus_coverage_lines)
        lines.append("")
    if extra_lines:
        lines.extend(extra_lines)
        lines.append("")
    lines.append(footer)
    pdf.multi_cell(0, 5, "\n".join(lines))
    try:
        pdf.output(str(path))
        return path.is_file()
    except Exception as exc:  # noqa: BLE001
        logger.info("summary pdf failed: %s", exc)
        return False


def write_redline_pdf(
    issues: list[dict[str, Any]],
    path: Path,
    *,
    title: str = "DraftLens redline",
    document_name: str | None = None,
) -> bool:
    """User-facing redline summary as PDF (fpdf2)."""
    try:
        from fpdf import FPDF  # type: ignore[import-untyped]
    except ImportError:
        logger.info("fpdf2 not installed; skipping redline PDF")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = FPDF()
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(0, 6, title)
    pdf.ln(1)
    pdf.set_font("Helvetica", size=9)
    if document_name:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5, f"Document: {document_name}")
    pdf.ln(2)
    for i, it in enumerate(issues[:100], start=1):
        pdf.set_x(pdf.l_margin)
        sev = str(it.get("severity", ""))
        cat = str(it.get("category", ""))
        ttl = str(it.get("title", ""))[:200].replace("\n", " ")
        span = str(it.get("span_text", ""))[:260].replace("\n", " ")
        fix = str(it.get("suggested_fix", ""))[:260].replace("\n", " ")
        expl = str(it.get("explanation", "") or it.get("details", ""))[:400].replace("\n", " ")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 4, f"{i}. [{sev}/{cat}] {ttl}")
        pdf.set_font("Helvetica", size=8)
        if expl:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 4, f"Note: {expl}")
        pdf.set_x(pdf.l_margin)
        pdf.set_text_color(140, 30, 40)
        pdf.multi_cell(0, 4, f"Before: {span}")
        pdf.set_x(pdf.l_margin)
        pdf.set_text_color(20, 100, 40)
        pdf.multi_cell(0, 4, f"After: {fix}")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
    try:
        pdf.output(str(path))
    except Exception as exc:  # noqa: BLE001
        logger.info("redline pdf write failed: %s", exc)
        return False
    return path.is_file()


def write_reviewed_text_fallback_pdf(
    cleaned_plaintext: str,
    path: Path,
    *,
    document_name: str,
    doc_title: str = "DraftLens reviewed manuscript (text export)",
) -> bool:
    """Readable multi-page PDF when DOCX→PDF conversion is unavailable."""
    try:
        from fpdf import FPDF  # type: ignore[import-untyped]
    except ImportError:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = FPDF()
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(0, 6, doc_title)
    pdf.set_font("Helvetica", size=8)
    pdf.multi_cell(0, 4, f"Source file: {document_name}")
    pdf.multi_cell(
        0,
        4,
        "This PDF was generated from cleaned extracted text because native DOCX→PDF conversion "
        "was not available on this machine. Install Microsoft Word + docx2pdf, or LibreOffice, for print-accurate PDFs.",
    )
    pdf.ln(2)
    pdf.set_font("Helvetica", size=10)
    body = cleaned_plaintext.strip() or "(empty)"
    chunk = 4800
    for start in range(0, len(body), chunk):
        pdf.multi_cell(0, 5, body[start : start + chunk])
    try:
        pdf.output(str(path))
    except Exception as exc:  # noqa: BLE001
        logger.info("reviewed text fallback pdf failed: %s", exc)
        return False
    return path.is_file()


def write_change_log_pdf(rows: list[dict[str, Any]], path: Path) -> bool:
    try:
        from fpdf import FPDF  # type: ignore[import-untyped]
    except ImportError:
        return False
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 6, "Change log")
    pdf.ln(8)
    pdf.set_font("Helvetica", size=8)
    for i, ch in enumerate(rows[:60], start=1):
        pdf.multi_cell(0, 4, f"{i}. {ch.get('issue_id')}")
        pdf.multi_cell(0, 4, f"Original: {str(ch.get('original_snippet',''))[:400]}")
        pdf.multi_cell(0, 4, f"Revised: {str(ch.get('revised_snippet',''))[:400]}")
        pdf.multi_cell(0, 4, f"Rationale: {str(ch.get('rationale',''))[:400]}")
        pdf.ln(2)
    try:
        pdf.output(str(path))
        return path.is_file()
    except Exception as exc:  # noqa: BLE001
        logger.info("changelog pdf failed: %s", exc)
        return False
