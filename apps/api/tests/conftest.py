from __future__ import annotations

import json
import time
from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from typing import Any

import hashlib
import hmac
import pytest
from docx import Document
from fastapi.testclient import TestClient


@pytest.fixture
def api_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[TestClient, Path], None, None]:
    """Isolated SQLite DB + data dir; clears settings/engine caches between tests."""
    db_path = tmp_path / "test.db"
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("APP_SESSION_SECRET", "x" * 40)
    monkeypatch.setenv("DRAFTLENS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("DRAFTLENS_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("DRAFTLENS_ENVIRONMENT", "development")
    monkeypatch.setenv("FREE_MONTHLY_PROOFS", "1")
    monkeypatch.setenv("FREE_MAX_PAGES", "25")
    monkeypatch.setenv("DRAFTLENS_PRO_MAX_PAGES", "500")
    monkeypatch.setenv("PRO_FAIR_USE_DOCS_PER_MONTH", "200")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_testsecret")
    monkeypatch.setenv("STRIPE_PRICE_ID_PRO_MONTHLY", "price_test_123")

    from draftlens_api import config as cfg
    from draftlens_api import db as dbm

    cfg.get_settings.cache_clear()
    cfg.get_provider_env.cache_clear()
    dbm._engine = None
    dbm._SessionLocal = None

    from draftlens_api.db import init_db
    from draftlens_api.main import create_app

    init_db()
    app = create_app()

    with TestClient(app, raise_server_exceptions=True) as client:
        yield client, data_dir

    cfg.get_settings.cache_clear()
    cfg.get_provider_env.cache_clear()
    dbm._engine = None
    dbm._SessionLocal = None


def minimal_docx_bytes(*, paragraphs: list[str] | None = None) -> bytes:
    buf = BytesIO()
    doc = Document()
    for p in paragraphs or ["Hello DraftLens test paragraph. " * 5]:
        doc.add_paragraph(p)
    doc.save(buf)
    return buf.getvalue()


def stripe_signature_header(*, payload: bytes, secret: str) -> str:
    ts = int(time.time())
    signed_payload = f"{ts}.{payload.decode('utf-8')}"
    sig = hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def fake_pipeline_artifacts(
    *,
    paths_root: Path,
    job_id: str,
    output_mode: str,
    evidence_aware: bool = False,
) -> dict[str, Any]:
    """Minimal final_state for monkeypatched execute_review_pipeline."""
    from draftlens_api.services.paths import DataPaths

    paths = DataPaths(root=paths_root)
    art_dir = paths.job_artifacts(job_id)
    art_dir.mkdir(parents=True, exist_ok=True)

    reviewed = art_dir / "reviewed.docx"
    reviewed.write_bytes(minimal_docx_bytes())

    stats = art_dir / "pipeline_stats.json"
    stats.write_text(
        json.dumps(
            {
                "total_issues": 1,
                "stats_by_severity": {"minor": 1},
                "stats_by_category": {"grammar": 1},
                "unresolved_human_evidence": [],
                "consensus_reached": True,
                "full_three_reviewer_consensus_achieved": True,
                "partial_consensus_only": False,
                "evidence_aware": evidence_aware,
            }
        ),
        encoding="utf-8",
    )

    rows: list[dict[str, Any]] = [
        {"path": str(reviewed.resolve()), "name": "reviewed.docx", "media_type": "application/vnd.openxmlformats"},
        {"path": str(stats.resolve()), "name": "pipeline_stats.json", "media_type": "application/json"},
    ]

    if output_mode == "fix":
        corrected = art_dir / "corrected.docx"
        corrected.write_bytes(minimal_docx_bytes(paragraphs=["Corrected body."]))
        rows.append(
            {
                "path": str(corrected.resolve()),
                "name": "corrected.docx",
                "media_type": "application/vnd.openxmlformats",
            }
        )

    if evidence_aware:
        ev = art_dir / "evidence_snippets.md"
        ev.write_text("# Evidence-aware output\n\n- ranked excerpts referenced in review.\n", encoding="utf-8")
        rows.append({"path": str(ev.resolve()), "name": "evidence_snippets.md", "media_type": "text/markdown"})

    if output_mode == "review":
        from draftlens_api.domain.models import ArbitrationDecision

        arb = ArbitrationDecision(executive_summary="test seed", issues=[], proposed_edits=[], resolved_conflicts=[])
        body = "Hello DraftLens test paragraph. " * 3
        seed = {
            "version": 1,
            "source_job_id": job_id,
            "arbitration_decision": arb.model_dump(mode="json"),
            "blocks": [{"block_id": "b1", "char_start": 0, "char_end": len(body), "text": body}],
            "normalized_text": body,
            "main_text": "",
            "pages": 1,
            "parse_mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "reviewer_phase1": {"claude": {"ok": True}, "gpt": {"ok": True}, "gemini": {"ok": True}},
            "convergence_meta": {"convergence_status": "CONVERGENCE_REACHED"},
            "conflict_clusters": [],
            "issues_working": [],
        }
        seed_path = art_dir / "fix_seed_snapshot.json"
        seed_path.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rows.append(
            {"path": str(seed_path.resolve()), "name": "fix_seed_snapshot.json", "media_type": "application/json"}
        )

    return {"artifact_file_rows": rows}

