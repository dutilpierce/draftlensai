from __future__ import annotations

from draftlens_api.domain.models import DisclaimerBundle
from draftlens_api.policies.central import TrustCopy


def build_disclaimer_bundle(*, sensitive_mode: bool, has_supporting_files: bool) -> DisclaimerBundle:
    """Compose footers that depend on supporting evidence; other fields use DisclaimerBundle defaults."""
    trust = TrustCopy()
    accuracy = (
        "Accuracy checks are limited when no source files are provided."
        if not has_supporting_files
        else "When source files are provided, spot-check that excerpts support the flagged claims."
    )
    review_footer = (
        "_Not native Word Track Changes._ AI-assisted review — please verify important facts and final wording.\n\n"
        f"_{accuracy}_"
    )
    fix_footer = (
        "_No comments or highlights in corrected output._ Changes are generated automatically and should be "
        "reviewed before use.\n\n"
        f"_{accuracy}_"
    )
    sens = (
        "Sensitive mode is enabled: shorter on-disk retention applies; avoid pasting highly classified "
        "material unless your policy permits automated review."
        if sensitive_mode
        else None
    )
    retention_core = (
        "Files are processed for review and scheduled for deletion after the configured retention window. "
        "Artifacts remain available until that window expires."
    )
    return DisclaimerBundle(
        sensitive_mode=sens,
        accuracy_context_note=accuracy,
        markdown_review_footer=review_footer,
        markdown_fix_footer=fix_footer,
        retention=retention_core,
        no_model_training=trust.no_model_training,
        files_scheduled_for_deletion=trust.files_scheduled_for_deletion,
    )
