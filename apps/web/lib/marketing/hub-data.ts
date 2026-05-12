/**
 * Hub/list card copy — single source for index pages and cross-links.
 * Paths must match `app/(public)` routes and `PAGE_REGISTRY`.
 */

export type HubCard = {
  href: string;
  title: string;
  summary: string;
  /** One line: benefit or “why open this” */
  accent: string;
};

export const FEATURE_INDEX_ITEMS: HubCard[] = [
  {
    href: "/features/multi-model-review",
    title: "Multi-model review",
    summary: "Run complementary reviewers on the same manuscript (DOCX or PDF), then merge structured findings instead of chasing separate chats.",
    accent: "Best when one model’s blind spots are unacceptable for your draft.",
  },
  {
    href: "/features/review-mode",
    title: "Review mode",
    summary: "Issue ledger, digest, and exports—without silently rewriting your manuscript file.",
    accent: "Best when humans decide what becomes a redline.",
  },
  {
    href: "/features/fix-mode",
    title: "Fix mode",
    summary: "Proposed edits and corrected packages for workflows that expect change artifacts—still with human verification.",
    accent: "Best when you want machine drafts you can inspect in Word.",
  },
  {
    href: "/features/supporting-files",
    title: "Supporting files",
    summary: "Attach evidence (PDF, DOCX, text) so reviewers stay anchored to exhibits and policies. Pro capability.",
    accent: "Best for memos and agreements that cite external material.",
  },
  {
    href: "/features/do-not-change-locks",
    title: "Do-not-change locks",
    summary: "Tell reviewers which names, clauses, or figures must stay verbatim.",
    accent: "Best for contracts and regulated wording.",
  },
];

export type UseCaseCard = HubCard & { humanCheck: string };

export const USE_CASE_INDEX_ITEMS: UseCaseCard[] = [
  {
    href: "/use-cases/legal-document-review",
    title: "Legal document review",
    summary: "Stress-test memos and agreements for clarity and cross-references before partner review.",
    accent: "Structured disagreement—not a substitute for legal advice.",
    humanCheck: "Partners still decide what ships; privilege and filing rules stay yours.",
  },
  {
    href: "/use-cases/business-document-proofreading",
    title: "Business proofreading",
    summary: "Catch inconsistent metrics, tone drift, and weak transitions across long memos, decks-bound-as-DOCX, or PDF handoffs.",
    accent: "Multi-model pass for drafts that already went through a human outline.",
    humanCheck: "Executives and comms leads still own tone and politics.",
  },
  {
    href: "/use-cases/contract-redlining",
    title: "Contract redlining",
    summary: "Surface ambiguous obligations and risky cross references before circulation.",
    accent: "Pairs with locks for sensitive clauses.",
    humanCheck: "Counterparties and counsel still negotiate final language.",
  },
  {
    href: "/use-cases/long-document-proofreading",
    title: "Long documents",
    summary: "Block-aware review so models focus where the pipeline routes them—not endless scroll.",
    accent: "For manuscripts where attention spans are the bottleneck.",
    humanCheck: "Schedule a second pass for voice and stakeholder alignment.",
  },
  {
    href: "/use-cases/academic-paper-review",
    title: "Academic papers",
    summary: "Clarity and consistency checks when your institution allows tooling—integrity constraints first.",
    accent: "Voice preservation and citation hygiene—not a bypass for supervision.",
    humanCheck: "Venue rules, authorship, and integrity policies remain strictly human-led.",
  },
];

export type CompareCard = HubCard & { question: string };

export const COMPARE_INDEX_ITEMS: CompareCard[] = [
  {
    href: "/compare/draftlens-vs-grammarly",
    title: "DraftLens vs Grammarly",
    summary: "Finished DOCX or PDF review with structured outputs vs drafting-time writing assistance.",
    accent: "DraftLens: manuscript pipeline. Grammarly: interactive writing help.",
    question: "Are you polishing sentences live or reviewing a frozen draft seriously?",
  },
  {
    href: "/compare/draftlens-vs-chatgpt",
    title: "DraftLens vs ChatGPT",
    summary: "Jobs, stages, and exports instead of ad-hoc threads pasted from Word.",
    accent: "DraftLens: repeatable pipeline. ChatGPT: flexible conversation.",
    question: "Do you need auditability and merge logic across models?",
  },
  {
    href: "/compare/draftlens-vs-claude",
    title: "DraftLens vs Claude alone",
    summary: "Claude can be one reviewer inside DraftLens—value is orchestration, merge, and convergence controls.",
    accent: "Less about “which model” and more about operational guardrails.",
    question: "Are you already happy with one model but need packaging for DOCX or PDF teams?",
  },
  {
    href: "/compare/best-ai-proofreading-tools",
    title: "Choosing AI proofreading tools",
    summary: "A practical checklist: evidence boundaries, partial failures, exports—without fake scorecards.",
    accent: "Pick on workflow fit, not headline benchmarks you cannot reproduce.",
    question: "How will you evaluate tools for serious review, not toy sentences?",
  },
];

export type AcademyCard = HubCard & { reader: string; /** One line: concrete takeaway after reading */ outcome: string };

export const ACADEMY_INDEX_ITEMS: AcademyCard[] = [
  {
    href: "/academy/how-to-redline-a-word-document",
    title: "How to redline a Word document",
    summary: "Comment discipline, track changes hygiene, and separating formatting churn from substance.",
    accent: "Operators preparing drafts for AI review and partner markup.",
    reader: "Legal ops, paralegals, and deal teams.",
    outcome: "You will leave with a repeatable markup routine and a clean handoff into structured review.",
  },
  {
    href: "/academy/how-to-proofread-a-long-document",
    title: "How to proofread a long document",
    summary: "Chunking, terminology control, and scheduling passes for mechanics vs voice.",
    accent: "Editors and program managers wrangling long DOCX or PDF documents.",
    reader: "Technical and executive editors.",
    outcome: "You will know how to split a long DOCX or PDF into passes so nothing important slips through fatigue.",
  },
  {
    href: "/academy/how-to-preserve-voice-while-editing",
    title: "How to preserve voice while editing",
    summary: "Locks, paragraph-level review, and separating “must not change” from “may improve.”",
    accent: "Authors and ghostwriters protecting stance and rhythm.",
    reader: "Writers working with AI suggestions.",
    outcome: "You will be able to protect stance and rhythm while still accepting useful mechanical fixes.",
  },
];

export const RESEARCH_INDEX_ITEMS: HubCard[] = [
  {
    href: "/research/benchmark-methodology",
    title: "Benchmark methodology",
    summary: "Tasks, rubrics, adjudication, and disclosure rules before any leaderboard is credible.",
    accent: "How we think about evaluating document-review systems fairly.",
  },
  {
    href: "/research/ai-document-review-benchmark",
    title: "Benchmark framework",
    summary: "Scope for future comparative work—explicitly without fabricated vendor scores today.",
    accent: "What would be measured when real runs exist.",
  },
];
