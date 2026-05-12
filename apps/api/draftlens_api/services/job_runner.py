from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from draftlens_api.config import get_provider_env, get_settings
from draftlens_api.db import broadcast_job_event, persist_job_event
from draftlens_api.domain.models import ReviewJobConfig
from draftlens_api.engine.langgraph_review_graph import execute_review_pipeline
from draftlens_api.engine.progress_weights import progress_percent_for_stage
from draftlens_api.persistence.orm import Artifact, Job, Upload, UsageEventRow
from draftlens_api.routing.model_registry import ModelRegistry
from draftlens_api.services.documents import extract_main_document
from draftlens_api.services.paths import DataPaths

logger = logging.getLogger(__name__)


def _clamp_iterative_for_dev(cfg: ReviewJobConfig, settings) -> ReviewJobConfig:
    env = (settings.environment or "").strip().lower()
    if env not in ("development", "dev", "local", "test"):
        return cfg
    ir = cfg.iterative_review
    updates: dict[str, int] = {}
    cap_r = settings.draftlens_convergence_max_cycles_review_cap
    cap_f = settings.draftlens_convergence_max_cycles_fix_cap
    if cap_r is not None:
        updates["max_cycles_review_mode"] = min(ir.max_cycles_review_mode, cap_r)
    if cap_f is not None:
        updates["max_cycles_fix_mode"] = min(ir.max_cycles_fix_mode, cap_f)
    if not updates:
        return cfg
    return cfg.model_copy(update={"iterative_review": ir.model_copy(update=updates)})


async def _emit_async(session_factory, job_id: str, stage: str, message: str, detail: dict | None = None):
    def _work():
        s = session_factory()
        try:
            persist_job_event(s, job_id, stage, message, detail)
            s.commit()
        finally:
            s.close()

    await asyncio.to_thread(_work)
    await broadcast_job_event(
        job_id,
        {
            "stage": stage,
            "message": message,
            "detail": detail or {},
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    )


async def run_job(job_id: str, session_factory) -> None:
    settings = get_settings()
    penv = get_provider_env()
    paths = DataPaths.from_settings(settings)
    paths.ensure_layout()

    def load_job() -> Job:
        s = session_factory()
        try:
            row = s.get(Job, job_id)
            if row is None:
                raise RuntimeError("job_missing")
            return row
        finally:
            s.close()

    job = await asyncio.to_thread(load_job)
    cfg_run = _clamp_iterative_for_dev(ReviewJobConfig.model_validate(job.job_config or {}), settings)
    post_review_hydrate = bool(cfg_run.post_review_fix_seed_job_id and cfg_run.output_mode == "fix")

    async def update_job(**fields):
        def _work():
            s = session_factory()
            try:
                row = s.get(Job, job_id)
                if row is None:
                    return
                for k, v in fields.items():
                    setattr(row, k, v)
                s.commit()
            finally:
                s.close()

        await asyncio.to_thread(_work)

    try:
        await _emit_async(
            session_factory,
            job_id,
            "UPLOAD_RECEIVED",
            "Main document received; preparing pipeline.",
            {"job_id": job_id, "progress_percent": 1},
        )
        if cfg_run.fix_generation_started_from_review and cfg_run.post_review_fix_seed_job_id:
            await _emit_async(
                session_factory,
                job_id,
                "APPLY_FIXES_STARTED",
                "Generating and validating a corrected document from your completed review.",
                {
                    "source_review_job_id": cfg_run.post_review_fix_seed_job_id,
                    "progress_percent": 3,
                },
            )

        def fetch_main_upload() -> tuple[Upload, Path]:
            s = session_factory()
            try:
                stmt = select(Upload).where(Upload.job_id == job_id, Upload.kind == "main")
                up = s.execute(stmt).scalar_one_or_none()
                if up is None:
                    raise RuntimeError("main_upload_missing")
                main_path = paths.root / up.storage_path
                return up, main_path
            finally:
                s.close()

        main_upload, main_path = await asyncio.to_thread(fetch_main_upload)

        if (
            cfg_run.fix_generation_started_from_review
            and cfg_run.post_review_fix_seed_job_id
            and int(job.page_count or 0) > 0
        ):
            pages = max(1, int(job.page_count))
        else:
            main_ex = extract_main_document(main_path, main_upload.original_name)
            _document_text, pages, _mime = main_ex.text, main_ex.pages, main_ex.mime
            if pages <= 0:
                pages = 1
        await update_job(page_count=pages, status="running")

        def list_supporting() -> list[tuple[Path, str]]:
            s = session_factory()
            try:
                stmt = select(Upload).where(Upload.job_id == job_id, Upload.kind == "supporting")
                rows = list(s.execute(stmt).scalars().all())
                out: list[tuple[Path, str]] = []
                for u in rows:
                    out.append((paths.root / u.storage_path, u.original_name))
                return out
            finally:
                s.close()

        supporting_pairs = await asyncio.to_thread(list_supporting)

        cfg = cfg_run

        registry = ModelRegistry.from_settings(settings, penv)

        async def emit(stage: str, message: str, detail: dict | None = None):
            d = dict(detail or {})
            if "progress_percent" not in d:
                inferred = progress_percent_for_stage(
                    stage,
                    output_mode=cfg.output_mode,
                    post_review_hydrate=post_review_hydrate,
                )
                if inferred is not None:
                    d["progress_percent"] = inferred
            await _emit_async(session_factory, job_id, stage, message, d)

        final_state = await execute_review_pipeline(
            job_id=job_id,
            main_path=main_path,
            supporting_pairs=supporting_pairs,
            job_config=cfg,
            paths=paths,
            registry=registry,
            emit=emit,
        )

        await _emit_async(session_factory, job_id, "EXPORT_COMPLETE", "Artifacts and stats packaged.", {})

        file_rows = list(final_state.get("artifact_file_rows") or [])

        if not file_rows:
            raise RuntimeError("artifact_render_missing")

        def _finalize():
            s = session_factory()
            try:
                row = s.get(Job, job_id)
                if row is None:
                    return
                row.status = "completed"
                row.error_message = None
                row.completed_at = datetime.now(timezone.utc)
                for item in file_rows:
                    p = Path(str(item["path"]))
                    sz = p.stat().st_size if p.exists() else None
                    art = Artifact(
                        id=str(uuid.uuid4()),
                        job_id=job_id,
                        name=str(item["name"]),
                        storage_path=str(p.resolve()),
                        mime=item.get("media_type"),
                        byte_size=sz,
                    )
                    s.add(art)
                ym = datetime.now(timezone.utc).strftime("%Y-%m")
                s.add(
                    UsageEventRow(
                        user_id=row.user_id,
                        job_id=job_id,
                        event_type="job_completed",
                        year_month=ym,
                        quantity=1,
                        meta={"output_mode": row.output_mode},
                    )
                )
                persist_job_event(s, job_id, "completed", "Outputs are ready to download.", None)
                s.commit()
            finally:
                s.close()

        await asyncio.to_thread(_finalize)
        await broadcast_job_event(
            job_id,
            {
                "stage": "completed",
                "message": "Outputs are ready to download.",
                "detail": {},
                "ts": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Job failed: %s", job_id)

        def _fail(err: BaseException):
            s = session_factory()
            try:
                row = s.get(Job, job_id)
                if row is None:
                    return
                row.status = "failed"
                row.error_message = str(err)
                ym = datetime.now(timezone.utc).strftime("%Y-%m")
                s.add(
                    UsageEventRow(
                        user_id=row.user_id,
                        job_id=job_id,
                        event_type="job_failed",
                        year_month=ym,
                        quantity=1,
                        meta={"error": str(err)},
                    )
                )
                persist_job_event(s, job_id, "JOB_FAILED", "Job failed.", {"error": str(err)})
                s.commit()
            finally:
                s.close()

        await asyncio.to_thread(_fail, exc)
        await broadcast_job_event(
            job_id,
            {
                "stage": "JOB_FAILED",
                "message": str(exc),
                "detail": {"error": str(exc)},
                "ts": datetime.now(timezone.utc).isoformat(),
            },
        )
