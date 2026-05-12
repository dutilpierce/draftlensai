from __future__ import annotations

from fastapi import APIRouter, Query

from draftlens_api.artifacts.disclaimers import build_disclaimer_bundle

router = APIRouter(tags=["disclaimers"])


@router.get("/disclaimers")
def get_disclaimers(
    has_supporting_files: bool = Query(False, description="Whether the user attached supporting/source files."),
    sensitive_mode: bool = Query(False, description="Whether sensitive-mode retention applies."),
) -> dict:
    """Return disclaimer copy for UI nudges and to mirror artifact footers."""
    return build_disclaimer_bundle(
        sensitive_mode=sensitive_mode,
        has_supporting_files=has_supporting_files,
    ).model_dump(mode="json")
