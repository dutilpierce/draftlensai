from __future__ import annotations

import asyncio
import json
import logging
import shutil
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from draftlens_api.config import get_settings
from draftlens_api.db import get_db_session, register_sse_subscriber, unregister_sse_subscriber
from draftlens_api.deps import get_db
from draftlens_api.domain.enums import DocumentType
from draftlens_api.domain.models import ReviewJobConfig
from draftlens_api.models.schemas import ArtifactInfo, JobPipelineResult, JobSummary, OutputMode, ReviewFocus
from draftlens_api.persistence.orm import Artifact, Job, JobStatusEventRow, SupportingFile, Upload, User
from draftlens_api.security.session import session_user_id_or_none
from draftlens_api.policies.central import CentralPolicyService
from draftlens_api.services.documents import UserFacingDocumentError, extract_main_document
from draftlens_api.services.entitlement_service import EntitlementService
from draftlens_api.services.job_runner import run_job
from draftlens_api.services.paths import DataPaths, main_upload_path, supporting_upload_path
from draftlens_api.validation.ingestion import (
    validate_main_file_size,
    validate_main_upload_filename,
    validate_supporting_file_byte_size,
    validate_supporting_file_list,
    validate_supporting_upload_filename,
)

from draftlens_api.cloud.staging import delete_staged, read_staged


def _upload_nonempty(f: UploadFile | None) -> bool:
    return bool(f and getattr(f, "filename", None) and str(f.filename).strip())


def _parse_supporting_cloud_handles(raw: str | None) -> list[str]:
    if not raw or not str(raw).strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid_supporting_cloud_handles") from exc
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="invalid_supporting_cloud_handles")
    return [str(x).strip() for x in data if str(x).strip()]


router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)


def _parse_bool(raw: str | None) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _optional_int(v) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _current_user(request: Request, db: Session) -> User:
    uid = session_user_id_or_none(request)
    if not uid:
        raise HTTPException(status_code=401, detail="not_signed_in")
    user = db.get(User, uid)
    if user is None:
        raise HTTPException(status_code=401, detail="not_signed_in")
    return user


def _load_pipeline_stats_from_disk(paths: DataPaths, job_id: str) -> dict:
    p = paths.job_artifacts(job_id) / "pipeline_stats.json"
    if not p.is_file():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _build_apply_fixes_honesty_notice(stats: dict, base_cfg: ReviewJobConfig) -> str | None:
    """User-visible caveat when downstream fix is seeded from partial or non–full-tri review."""
    if not stats:
        return None
    strict = bool(
        stats.get("strict_three_reviewer_consensus", base_cfg.iterative_review.strict_three_reviewer_consensus)
    )
    partial = bool(stats.get("partial_consensus_only"))
    full = bool(stats.get("full_three_reviewer_consensus_achieved"))
    if full and not partial:
        return None
    parts: list[str] = [
        "DraftLens will generate a corrected draft from this review’s finalized ledger, then run full Fix Mode "
        "validation (tri‑review, discrepancy handling, and a final alignment audit) before marking outputs complete."
    ]
    if partial or not full:
        parts.append(
            "The source review did not achieve full three‑reviewer agreement on every issue; "
            "treat the lineage and labels accordingly."
        )
    if strict and partial:
        parts.append("Strict three‑reviewer consensus was requested but the review ended with partial consensus only.")
    return " ".join(parts)


def _load_pipeline_result(artifacts: list[Artifact], settings) -> JobPipelineResult | None:
    root = DataPaths.from_settings(settings).root
    for a in artifacts:
        if a.name != "pipeline_stats.json" or not a.storage_path:
            continue
        p = Path(a.storage_path)
        if not p.is_absolute():
            p = root / p
        if not p.exists():
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        sev_raw = raw.get("stats_by_severity") or {}
        cat_raw = raw.get("stats_by_category") or {}
        if not isinstance(sev_raw, dict):
            sev_raw = {}
        if not isinstance(cat_raw, dict):
            cat_raw = {}

        def _intdict(d: dict) -> dict[str, int]:
            out: dict[str, int] = {}
            for k, v in d.items():
                try:
                    out[str(k)] = int(v)  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    continue
            return out

        sev = _intdict(sev_raw)
        cat = _intdict(cat_raw)
        uhe = raw.get("unresolved_human_evidence") or []
        if not isinstance(uhe, list):
            uhe = []
        total_issues = int(raw.get("total_issues", 0))
        if total_issues <= 0 and sev:
            total_issues = sum(sev.values())
        tiers_raw = raw.get("artifact_tiers") or {}
        tiers: dict[str, str] = {}
        if isinstance(tiers_raw, dict):
            for k, v in tiers_raw.items():
                if isinstance(k, str) and isinstance(v, str):
                    tiers[k] = v
        ferr_raw = raw.get("fix_alignment_audit_errors")
        if isinstance(ferr_raw, list):
            fix_alignment_audit_errors = [str(x) for x in ferr_raw if str(x).strip()]
        else:
            fix_alignment_audit_errors = None
        fap_raw = raw.get("fix_alignment_audit_passed")
        fix_alignment_audit_passed = fap_raw if isinstance(fap_raw, bool) else None
        if "reviewer_success_count" not in raw:
            reviewer_success_count = 3
            reviewer_failure_count = 0
            reviewer_full_consensus = True
            partial_quorum_used = False
        else:
            reviewer_success_count = int(raw.get("reviewer_success_count", 0))
            reviewer_failure_count = int(raw.get("reviewer_failure_count", 0))
            reviewer_full_consensus = bool(raw.get("reviewer_full_consensus", False))
            partial_quorum_used = bool(raw.get("partial_quorum_used", False))
        return JobPipelineResult(
            total_issues=total_issues,
            stats_by_severity=sev,
            stats_by_category=cat,
            unresolved_human_evidence=[x for x in uhe if isinstance(x, dict)],
            consensus_reached=bool(raw.get("consensus_reached", False)),
            reviewer_success_count=reviewer_success_count,
            reviewer_failure_count=reviewer_failure_count,
            reviewer_full_consensus=reviewer_full_consensus,
            partial_quorum_used=partial_quorum_used,
            cycle_count_completed=int(raw.get("cycle_count_completed", 1)),
            convergence_status=raw.get("convergence_status"),
            convergence_failure_code=raw.get("convergence_failure_code"),
            consensus_mode=raw.get("consensus_mode") if isinstance(raw.get("consensus_mode"), str) else None,
            intended_reviewer_count=_optional_int(raw.get("intended_reviewer_count")),
            convergence_successful_reviewer_count=_optional_int(raw.get("convergence_successful_reviewer_count")),
            required_full_consensus_count=_optional_int(raw.get("required_full_consensus_count")),
            full_three_reviewer_consensus_achieved=bool(raw.get("full_three_reviewer_consensus_achieved", False)),
            partial_consensus_only=bool(raw.get("partial_consensus_only", False)),
            pairwise_material_discrepancy_count=_optional_int(raw.get("pairwise_material_discrepancy_count")),
            participation_coverage_deficit=_optional_int(raw.get("participation_coverage_deficit")),
            strict_three_reviewer_consensus=bool(raw.get("strict_three_reviewer_consensus", True)),
            fix_alignment_audit_passed=fix_alignment_audit_passed,
            fix_alignment_audit_errors=fix_alignment_audit_errors,
            max_cycles_reached=bool(raw.get("max_cycles_reached", False)),
            unresolved_material_issue_count=int(raw.get("unresolved_material_issue_count", 0)),
            unresolved_nit_count=int(raw.get("unresolved_nit_count", 0)),
            unresolved_material_discrepancy_count=raw.get("unresolved_material_discrepancy_count"),
            newly_found_material_discrepancy_count=int(raw.get("newly_found_material_discrepancy_count", 0)),
            resolved_material_discrepancy_count=int(raw.get("resolved_material_discrepancy_count", 0)),
            stopped_with_remaining_discrepancies=bool(raw.get("stopped_with_remaining_discrepancies", False)),
            stopped_due_to_max_cycles=bool(raw.get("stopped_due_to_max_cycles", False)),
            stopped_due_to_quorum_loss=bool(raw.get("stopped_due_to_quorum_loss", False)),
            stopped_due_to_provider_unavailable=bool(raw.get("stopped_due_to_provider_unavailable", False)),
            stopped_due_to_fatal_arbiter_failure=bool(raw.get("stopped_due_to_fatal_arbiter_failure", False)),
            pdf_conversion_notes=[str(x) for x in raw.get("pdf_conversion_notes") or [] if str(x).strip()],
            unresolved_cluster_summaries=[x for x in (raw.get("unresolved_cluster_summaries") or []) if isinstance(x, dict)],
            artifact_pdf_flags={
                str(k): bool(v)
                for k, v in (raw.get("artifact_pdf_flags") or {}).items()
                if isinstance(k, str)
            },
            artifact_tiers=tiers,
        )
    return None


def _job_to_summary(db: Session, job: Job) -> JobSummary:
    settings = get_settings()
    arts = list(db.execute(select(Artifact).where(Artifact.job_id == job.id)).scalars().all())
    pipeline_result = None
    if job.status == "completed":
        pipeline_result = _load_pipeline_result(arts, settings)
    tiers = (pipeline_result.artifact_tiers if pipeline_result else {}) or {}
    artifacts = [
        ArtifactInfo(name=a.name, path=a.storage_path, media_type=a.mime, tier=tiers.get(a.name, "primary"))
        for a in arts
        if a.storage_path
    ]
    policy = CentralPolicyService(settings)
    retention_notice = None
    if job.data_purged_at is None and job.retention_until is not None:
        retention_notice = policy.job_retention_notice(sensitive_mode=bool(job.sensitive_mode))
    try:
        jc = ReviewJobConfig.model_validate(job.job_config or {})
    except Exception:
        jc = None
    return JobSummary(
        id=job.id,
        status=job.status,  # type: ignore[arg-type]
        output_mode=OutputMode(job.output_mode),
        review_focus=ReviewFocus(job.review_focus),
        sensitive_mode=bool(job.sensitive_mode),
        page_count=int(job.page_count or 0),
        error_message=job.error_message,
        artifacts=artifacts,
        created_at=job.created_at,
        completed_at=job.completed_at,
        pipeline_result=pipeline_result,
        retention_until=job.retention_until,
        data_purged_at=job.data_purged_at,
        retention_notice=retention_notice,
        post_review_fix_seed_job_id=jc.post_review_fix_seed_job_id if jc else None,
        fix_generation_started_from_review=bool(jc.fix_generation_started_from_review) if jc else False,
        apply_fixes_honesty_notice=jc.apply_fixes_honesty_notice if jc else None,
        source_review_consensus_mode=jc.source_review_consensus_mode if jc else None,
        source_review_full_tri_consensus=jc.source_review_full_tri_consensus if jc else None,
        source_review_partial_consensus_only=jc.source_review_partial_consensus_only if jc else None,
    )


@router.post("")
async def create_job(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    main_document: UploadFile | None = File(None),
    main_cloud_import_handle: str | None = Form(None),
    output_mode: str = Form(...),
    review_focus: str = Form("standard"),
    context_text: str | None = Form(None),
    do_not_change: str | None = Form(None),
    sensitive_mode: str | None = Form("false"),
    document_type: str | None = Form("general"),
    max_debate_rounds: int = Form(3),
    supporting_files: list[UploadFile] | None = File(None),
    supporting_cloud_import_handles: str | None = Form(None),
):
    settings = get_settings()
    user = _current_user(request, db)
    paths = DataPaths.from_settings(settings)
    paths.ensure_layout()

    try:
        mode = OutputMode(output_mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_output_mode") from exc

    try:
        focus = ReviewFocus(review_focus)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_review_focus") from exc

    try:
        doc_type = DocumentType((document_type or "general").lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_document_type") from exc

    if max_debate_rounds < 1 or max_debate_rounds > 5:
        raise HTTPException(status_code=400, detail="invalid_max_debate_rounds")

    sens = _parse_bool(sensitive_mode)
    support_list = supporting_files or []
    cloud_support_handles = _parse_supporting_cloud_handles(supporting_cloud_import_handles)

    has_main_upload = _upload_nonempty(main_document)
    main_handle = (main_cloud_import_handle or "").strip()
    if has_main_upload and main_handle:
        raise HTTPException(status_code=400, detail="main_document_ambiguous")
    if not has_main_upload and not main_handle:
        raise HTTPException(status_code=400, detail="main_document_required")

    total_supporting = len(support_list) + len(cloud_support_handles)
    validate_supporting_file_list(count=total_supporting)
    for f in support_list:
        validate_supporting_upload_filename(f.filename)

    if main_handle:
        try:
            main_blob, main_ref = read_staged(paths, user.id, main_handle)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="cloud_import_not_found") from exc
        except TimeoutError as exc:
            raise HTTPException(status_code=400, detail="cloud_import_expired") from exc
        filename = validate_main_upload_filename(main_ref.filename)
        main_mime = main_ref.mime_type or "application/octet-stream"
        main_bytes = main_blob.read_bytes()
        delete_staged(paths, user.id, main_handle)
    else:
        assert main_document is not None
        filename = validate_main_upload_filename(main_document.filename)
        main_mime = main_document.content_type or "application/octet-stream"
        main_bytes = await main_document.read()

    ent = EntitlementService(db, settings)
    policy = CentralPolicyService(settings)
    ent.assert_job_allowed(
        user=user,
        output_mode=mode.value,
        supporting_count=total_supporting,
        pages=None,
    )

    job_id = str(uuid.uuid4())
    retention_until = policy.retention_until(sensitive_mode=sens)
    limits = policy.document_review_limits(ent.tier_for_user(user))

    job_cfg = ReviewJobConfig(
        output_mode=mode.value,
        review_focus=focus.value,
        document_type=doc_type,
        max_debate_rounds=int(max_debate_rounds),
        context_text=context_text,
        do_not_change=do_not_change,
        sensitive_mode=sens,
        main_original_filename=filename,
        main_mime=main_mime,
        max_chars_per_block=limits.max_chars_per_block,
        max_blocks_for_review=limits.max_blocks_for_review,
        max_block_send_chars=limits.max_block_send_chars,
    )

    job = Job(
        id=job_id,
        user_id=user.id,
        status="queued",
        output_mode=mode.value,
        review_focus=focus.value,
        context_text=context_text,
        do_not_change=do_not_change,
        sensitive_mode=sens,
        page_count=0,
        retention_until=retention_until,
        working_root=str(paths.job_working(job_id)),
        job_config=job_cfg.model_dump(mode="json"),
    )
    db.add(job)
    db.flush()

    paths.job_working(job_id).mkdir(parents=True, exist_ok=True)

    main_path = main_upload_path(paths, job_id, filename)
    main_path.write_bytes(main_bytes)
    validate_main_file_size(main_path.stat().st_size)

    try:
        parsed = extract_main_document(main_path, filename)
    except UserFacingDocumentError as exc:
        shutil.rmtree(paths.job_working(job_id), ignore_errors=True)
        if main_path.exists():
            main_path.unlink()
        db.delete(job)
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError:
        shutil.rmtree(paths.job_working(job_id), ignore_errors=True)
        if main_path.exists():
            main_path.unlink()
        db.delete(job)
        db.commit()
        raise HTTPException(status_code=400, detail="invalid_main_document") from None

    ent.assert_job_allowed(
        user=user,
        output_mode=mode.value,
        supporting_count=total_supporting,
        pages=int(parsed.pages),
    )

    job.page_count = int(parsed.pages)

    rel_main = str(main_path.relative_to(paths.root))
    main_upload = Upload(
        id=str(uuid.uuid4()),
        job_id=job_id,
        kind="main",
        storage_path=rel_main,
        original_name=filename,
        mime=main_mime,
        byte_size=main_path.stat().st_size,
    )
    db.add(main_upload)

    supporting_batches: list[tuple[bytes, str, str]] = []
    for f in support_list:
        name = validate_supporting_upload_filename(f.filename)
        b = await f.read()
        supporting_batches.append((b, name, f.content_type or "application/octet-stream"))

    for h in cloud_support_handles:
        try:
            blob, ref = read_staged(paths, user.id, h)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="cloud_support_import_not_found") from exc
        except TimeoutError as exc:
            raise HTTPException(status_code=400, detail="cloud_import_expired") from exc
        name = validate_supporting_upload_filename(ref.filename)
        b = blob.read_bytes()
        delete_staged(paths, user.id, h)
        supporting_batches.append((b, name, ref.mime_type or "application/octet-stream"))

    for b, name, mime in supporting_batches:
        dest = supporting_upload_path(paths, job_id, name)
        dest.write_bytes(b)
        validate_supporting_file_byte_size(dest.stat().st_size)
        rel = str(dest.relative_to(paths.root))
        up = Upload(
            id=str(uuid.uuid4()),
            job_id=job_id,
            kind="supporting",
            storage_path=rel,
            original_name=name,
            mime=mime,
            byte_size=dest.stat().st_size,
        )
        db.add(up)
        db.flush()
        db.add(
            SupportingFile(
                id=str(uuid.uuid4()),
                job_id=job_id,
                upload_id=up.id,
                status="stored",
            )
        )

    db.commit()

    background_tasks.add_task(run_job, job.id, get_db_session)

    return {"job": _job_to_summary(db, job)}


@router.post("/{job_id}/apply-fixes")
async def apply_fixes_from_completed_review(
    job_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Create a derived Fix Mode job that hydrates from this job's `fix_seed_snapshot.json`
    (written when a Review job completes with a usable ledger).
    """
    user = _current_user(request, db)
    src = db.get(Job, job_id)
    if src is None or src.user_id != user.id:
        raise HTTPException(status_code=404, detail="job_not_found")
    if src.status != "completed":
        raise HTTPException(status_code=400, detail="apply_fixes_requires_completed_review")
    if src.output_mode != "review":
        raise HTTPException(status_code=400, detail="apply_fixes_requires_review_job")

    settings = get_settings()
    paths = DataPaths.from_settings(settings)
    paths.ensure_layout()

    seed_path = paths.job_artifacts(job_id) / "fix_seed_snapshot.json"
    if not seed_path.is_file():
        raise HTTPException(status_code=409, detail="apply_fixes_seed_missing_reprocess_review")

    stats = _load_pipeline_stats_from_disk(paths, job_id)
    base_cfg = ReviewJobConfig.model_validate(src.job_config or {})
    notice = _build_apply_fixes_honesty_notice(stats, base_cfg)

    ent = EntitlementService(db, settings)
    policy = CentralPolicyService(settings)
    supporting_ct = int(
        db.scalar(select(func.count()).select_from(Upload).where(Upload.job_id == job_id, Upload.kind == "supporting"))
        or 0
    )
    ent.assert_job_allowed(
        user=user,
        output_mode="fix",
        supporting_count=supporting_ct,
        pages=int(src.page_count or 0) or None,
    )

    new_id = str(uuid.uuid4())
    retention_until = policy.retention_until(sensitive_mode=bool(src.sensitive_mode))

    new_cfg = base_cfg.model_copy(
        update={
            "output_mode": "fix",
            "post_review_fix_seed_job_id": src.id,
            "fix_generation_started_from_review": True,
            "source_review_consensus_mode": stats.get("convergence_status") or stats.get("consensus_mode"),
            "source_review_full_tri_consensus": bool(stats.get("full_three_reviewer_consensus_achieved")),
            "source_review_partial_consensus_only": bool(stats.get("partial_consensus_only")),
            "apply_fixes_honesty_notice": notice,
        }
    )

    job = Job(
        id=new_id,
        user_id=user.id,
        status="queued",
        output_mode="fix",
        review_focus=src.review_focus,
        context_text=src.context_text,
        do_not_change=src.do_not_change,
        sensitive_mode=bool(src.sensitive_mode),
        page_count=int(src.page_count or 0),
        retention_until=retention_until,
        working_root=str(paths.job_working(new_id)),
        job_config=new_cfg.model_dump(mode="json"),
    )
    db.add(job)
    db.flush()

    paths.job_working(new_id).mkdir(parents=True, exist_ok=True)

    uploads = list(db.execute(select(Upload).where(Upload.job_id == src.id)).scalars().all())
    for up in uploads:
        src_abs = paths.root / up.storage_path
        if not src_abs.is_file():
            raise HTTPException(status_code=500, detail="apply_fixes_source_upload_missing")
        if up.kind == "main":
            dest = main_upload_path(paths, new_id, up.original_name)
        elif up.kind == "supporting":
            dest = supporting_upload_path(paths, new_id, up.original_name)
        else:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_abs, dest)
        rel = str(dest.relative_to(paths.root))
        if up.kind == "main":
            validate_main_file_size(dest.stat().st_size)
        else:
            validate_supporting_file_byte_size(dest.stat().st_size)
        new_up = Upload(
            id=str(uuid.uuid4()),
            job_id=new_id,
            kind=up.kind,
            storage_path=rel,
            original_name=up.original_name,
            mime=up.mime,
            byte_size=int(dest.stat().st_size),
        )
        db.add(new_up)
        db.flush()
        if up.kind == "supporting":
            db.add(
                SupportingFile(
                    id=str(uuid.uuid4()),
                    job_id=new_id,
                    upload_id=new_up.id,
                    status="stored",
                )
            )

    db.commit()
    background_tasks.add_task(run_job, new_id, get_db_session)

    job = db.get(Job, new_id)
    assert job is not None
    return {"job": _job_to_summary(db, job), "source_review_job_id": src.id}


@router.get("/{job_id}", response_model=JobSummary)
def get_job(job_id: str, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    job = db.get(Job, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="job_not_found")
    return _job_to_summary(db, job)


@router.get("/{job_id}/events")
async def job_events(job_id: str, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    job = db.get(Job, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="job_not_found")

    async def gen():
        queue: asyncio.Queue[dict] = asyncio.Queue()
        register_sse_subscriber(job_id, queue)
        try:
            stmt = (
                select(JobStatusEventRow)
                .where(JobStatusEventRow.job_id == job_id)
                .order_by(JobStatusEventRow.id.asc())
            )
            for ev in db.execute(stmt).scalars().all():
                payload = {
                    "stage": ev.stage,
                    "message": ev.message,
                    "detail": ev.detail or {},
                    "ts": ev.created_at.isoformat() if ev.created_at else None,
                }
                yield f"data: {json.dumps(payload)}\n\n"
            db.refresh(job)
            if job.status in {"completed", "failed"}:
                return
            while True:
                item = await queue.get()
                yield f"data: {json.dumps(item)}\n\n"
                if item.get("stage") in {"completed", "failed", "JOB_FAILED"}:
                    break
        finally:
            unregister_sse_subscriber(job_id, queue)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/{job_id}/artifacts")
def list_artifacts(job_id: str, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    job = db.get(Job, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="job_not_found")
    return {"artifacts": _job_to_summary(db, job).artifacts}


@router.get("/{job_id}/artifacts/download")
def download_artifact(
    job_id: str,
    request: Request,
    filename: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    user = _current_user(request, db)
    job = db.get(Job, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="job_not_found")
    safe_name = Path(filename).name
    art = db.execute(
        select(Artifact).where(Artifact.job_id == job_id, Artifact.name == safe_name)
    ).scalar_one_or_none()
    if art is None:
        raise HTTPException(status_code=404, detail="artifact_not_found")
    target = Path(art.storage_path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="artifact_not_found")
    return FileResponse(
        path=str(target),
        filename=safe_name,
        media_type=str(art.mime or "application/octet-stream"),
    )
