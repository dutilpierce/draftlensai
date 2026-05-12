from __future__ import annotations

from draftlens_api.domain.enums import DocumentType
from draftlens_api.domain.models import ReviewJobConfig
from draftlens_api.prompts.loader import get_global_rules_markdown, load_full_prompt


def evidence_policy_block(*, has_supporting: bool) -> str:
    if has_supporting:
        return (
            "Evidence policy:\n"
            "- The MAIN document is the only editable target.\n"
            "- Supporting files are factual/reference evidence ONLY; never propose edits to them.\n"
            "- Use supporting excerpts to verify factual claims; if evidence is insufficient, prefer "
            "accuracy_posture in {unsupported, unverified} rather than asserting false.\n"
            "- Classify unsupported accuracy claims using accuracy_posture: "
            "false | unsupported | unverified | internally_inconsistent.\n"
        )
    return (
        "Evidence policy:\n"
        "- No supporting evidence was supplied.\n"
        "- Do NOT invent factual corrections or cite nonexistent sources.\n"
        "- For factual accuracy concerns without evidence, set accuracy_posture to unsupported or unverified.\n"
        "- Reserve false for clear internal contradictions within the main document itself.\n"
    )


def document_type_instructions(doc_type: DocumentType) -> str:
    mapping = {
        DocumentType.general: (
            "Document type: general. Balance tone preservation with clarity; moderate risk sensitivity. "
            "Prefer surgical edits over broad rewrites."
        ),
        DocumentType.legal: (
            "Document type: legal. Preserve defined terms, cross-references, and obligation language unless "
            "clearly erroneous; minimal paraphrase; flag definitional risk instead of rewriting."
        ),
        DocumentType.academic: (
            "Document type: academic. Treat citations, quotations, and empirical claims cautiously; "
            "do not invent sources; prefer notes where evidence is missing."
        ),
        DocumentType.business: (
            "Document type: business. Emphasize operational clarity, stakeholder-safe wording, and consistent "
            "terminology across sections."
        ),
        DocumentType.marketing: (
            "Document type: marketing. Preserve voice and differentiation; treat comparative or superlative "
            "claims as higher-risk; tighten wording without flattening brand tone."
        ),
    }
    return mapping.get(doc_type, mapping[DocumentType.general])


def review_focus_instructions(focus: str) -> str:
    f = (focus or "standard").lower()
    if f == "accuracy-heavy":
        return (
            "Review focus: accuracy-heavy. Weight factual grounding and evidence alignment higher in any tradeoffs; "
            "still avoid hallucinated fact fixes when evidence is missing."
        )
    if f == "formatting-heavy":
        return (
            "Review focus: formatting-heavy. Weight headings, numbering, style consistency, and mechanical structure higher."
        )
    if f == "adversarial":
        return (
            "Review focus: adversarial. Be maximally skeptical of leaps, risky implications, and missing support; "
            "still do not fabricate facts."
        )
    if f == "voice-preserving":
        return (
            "Review focus: voice-preserving. Prefer minimal surface edits; protect author voice; "
            "suggest fixes that preserve cadence and intent."
        )
    return "Review focus: standard. Balance clarity, correctness, tone, and structure."


def conflict_weighting_note(focus: str) -> str:
    f = (focus or "standard").lower()
    if f == "accuracy-heavy":
        return "Conflict weighting: elevate evidence and accuracy_posture disagreements."
    if f == "formatting-heavy":
        return "Conflict weighting: elevate formatting/structure disagreements."
    if f == "adversarial":
        return "Conflict weighting: elevate risk, logic, and unsupported-leap disagreements."
    if f == "voice-preserving":
        return "Conflict weighting: elevate meaning-changing rewrite vs preservation disagreements."
    return "Conflict weighting: neutral across categories."


def _runtime_context_block(cfg: ReviewJobConfig, *, has_supporting: bool) -> str:
    return (
        "## Runtime context (machine-appended)\n"
        f"{document_type_instructions(cfg.document_type)}\n\n"
        f"{review_focus_instructions(cfg.review_focus)}\n\n"
        f"{evidence_policy_block(has_supporting=has_supporting)}"
        "\nStructured intake: the user message is JSON with `document_blocks`; each item includes `text`, "
        "`relevant_evidence_excerpts`, and `evidence_note_for_block`. Ground factual assessments in excerpts when "
        "present; never treat user_context_text alone as external proof of facts.\n"
    )


def claude_system(cfg: ReviewJobConfig, *, has_supporting: bool) -> str:
    return load_full_prompt("claude_author_intent_reviewer") + "\n\n" + _runtime_context_block(
        cfg, has_supporting=has_supporting
    )


def gpt_system(cfg: ReviewJobConfig, *, has_supporting: bool) -> str:
    return load_full_prompt("gpt_skeptical_reviewer") + "\n\n" + _runtime_context_block(cfg, has_supporting=has_supporting)


def gemini_system(cfg: ReviewJobConfig, *, has_supporting: bool) -> str:
    return load_full_prompt("gemini_consistency_reviewer") + "\n\n" + _runtime_context_block(
        cfg, has_supporting=has_supporting
    )


def round2_system(agent_label: str) -> str:
    return (
        get_global_rules_markdown()
        + "\n\n"
        + f"## Round-2 dispute resolution — {agent_label}\n"
        "You will receive ONLY structured JSON per dispute: original block text, review context, do-not-change directives, "
        "ranked supporting evidence excerpts (if any), your_issues (your stake), peer_issues (structured peer objects), "
        "and each peer's rationale_summary and suggested_fix.\n"
        "Rules:\n"
        "- Do not request or infer hidden chain-of-thought from peers; reason only from the structured fields.\n"
        "- Respond with JSON ONLY: {votes: [{dispute_id, issue_id, stance, rationale_summary, revised_issue|null}] }.\n"
        "stance must be one of: defend | revise | withdraw.\n"
        "issue_id must identify YOUR issue from your_issues for that dispute (or empty string if you have no stake).\n"
        "If stance is revise, revised_issue must be a full issue object (same schema as Round-1 issues) and MUST "
        "preserve lineage_id from your prior issue when revising.\n"
        "If evidence is insufficient for factual adjudication, prefer withdraw or revise toward unsupported/unverified.\n"
    )


def arbiter_round3_system(cfg: ReviewJobConfig, output_mode: str, *, has_supporting: bool = False) -> str:
    mode_lines = (
        "Runtime output mode: fix. Include corrected_document_text (full revised plain text) when safe under do-not-change rules.\n"
        if output_mode == "fix"
        else "Runtime output mode: review. Include redline_html_fragment (HTML fragment) summarizing accepted changes when appropriate.\n"
    )
    fix_guard = ""
    if output_mode == "fix":
        fix_guard = (
            "\nFix-mode safeguards: prefer minimal edits; do not aggressively rewrite voice or structure. "
            "Honor do-not-change constraints; if a correction conflicts with a locked phrase, omit the automated "
            "edit and record the conflict for human resolution. Preserve substantive meaning over stylistic polish.\n"
        )
    evidence_first = ""
    if has_supporting:
        evidence_first = (
            "\nSupporting evidence was supplied: prefer factual resolutions that align with ranked evidence excerpts "
            "when they clearly apply; if excerpts are ambiguous, prefer conservative hedging (unsupported/unverified) "
            "over inventing facts.\n"
        )
    return (
        load_full_prompt("arbiter")
        + "\n\n## Runtime arbitration context (machine-appended)\n"
        + mode_lines
        + fix_guard
        + evidence_first
        + f"{conflict_weighting_note(cfg.review_focus)}\n\n"
        + f"{document_type_instructions(cfg.document_type)}\n"
    )


def supervisor_system() -> str:
    """Structured supervisor instructions (file-backed)."""
    return load_full_prompt("supervisor")
