import type { RegisteredPage } from "./types";

const WAVE1 = "2026-05-11";
const LEGAL_WAVE = "2026-05-13";

function p(def: RegisteredPage): RegisteredPage {
  return def;
}

/** Single source of truth for indexable public routes (paths without trailing slash). */
export const PAGE_REGISTRY: Record<string, RegisteredPage> = {
  "/": p({
    path: "/",
    title: "DraftLens — Multi-model document review for DOCX & PDF",
    description:
      "Run Claude, GPT, and Gemini reviewers on the same manuscript (DOCX or PDF), then converge on a single ledger. Review mode or fix mode — built for contracts, memos, and long documents.",
    h1: "Multi-model review that stays grounded in your document",
    canonicalPath: "/",
    breadcrumb: [{ name: "Home", href: "/" }],
    related: [
      { href: "/product", label: "Product overview" },
      { href: "/features", label: "All features" },
      { href: "/feedback", label: "Request a feature" },
      { href: "/app", label: "Open the app" },
    ],
    schemaProfile: "home",
    lastModified: WAVE1,
    primaryTopic: "AI document review software",
    secondaryTopics: ["multi-model LLM review", "DOCX proofreading", "PDF proofreading", "contract review workflow"],
  }),

  "/product": p({
    path: "/product",
    title: "Product — DraftLens multi-model document review",
    description:
      "What DraftLens does: tri-model structured review, optional convergence, review vs fix output, supporting evidence, and do-not-change locks — for manuscripts you upload as DOCX or PDF.",
    h1: "What DraftLens is built to do",
    canonicalPath: "/product",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Product", href: "/product" },
    ],
    related: [
      { href: "/pricing", label: "Pricing" },
      { href: "/features", label: "All features" },
      { href: "/methodology", label: "Methodology" },
    ],
    schemaProfile: "software",
    lastModified: WAVE1,
    primaryTopic: "DraftLens product overview",
    secondaryTopics: ["document review software", "DOCX", "PDF"],
  }),

  "/pricing": p({
    path: "/pricing",
    title: "Pricing — DraftLens Free and Pro",
    description:
      "DraftLens Free includes limited monthly runs; Pro unlocks fix mode, supporting files, and higher caps. Upload a DOCX or PDF from the app to see live entitlements.",
    h1: "Pricing that matches how teams review documents",
    canonicalPath: "/pricing",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Pricing", href: "/pricing" },
    ],
    related: [
      { href: "/product", label: "Product" },
      { href: "/app", label: "Run a review" },
      { href: "/feedback", label: "Feature requests" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "DraftLens pricing",
    secondaryTopics: ["subscription", "free tier"],
  }),

  "/about": p({
    path: "/about",
    title: "About — DraftLens",
    description:
      "DraftLens focuses on serious document review: multiple models, structured outputs, and clear partial-review behavior when consensus is not possible.",
    h1: "About DraftLens",
    canonicalPath: "/about",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "About", href: "/about" },
    ],
    related: [
      { href: "/methodology", label: "Methodology" },
      { href: "/editorial-policy", label: "Editorial policy" },
      { href: "/contact", label: "Contact" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "About DraftLens",
    secondaryTopics: ["company story", "document AI"],
  }),

  "/contact": p({
    path: "/contact",
    title: "Contact & support — DraftLens",
    description:
      "Reach DraftLens for product help, privacy and data requests, security reports, or billing questions. See also Privacy, Terms, and Data security.",
    h1: "Contact DraftLens",
    canonicalPath: "/contact",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Contact", href: "/contact" },
    ],
    related: [
      { href: "/privacy", label: "Privacy Policy" },
      { href: "/terms", label: "Terms of Service" },
      { href: "/data-security", label: "Data security" },
      { href: "/feedback", label: "Feature feedback" },
    ],
    schemaProfile: "standard",
    lastModified: LEGAL_WAVE,
    primaryTopic: "DraftLens contact and support",
    secondaryTopics: ["email support", "privacy requests", "security contact"],
  }),

  "/privacy": p({
    path: "/privacy",
    title: "Privacy Policy — DraftLens",
    description:
      "How DraftLens collects and uses account data, uploaded PDF and Word documents, AI model processing, Google Drive imports, Stripe billing, retention, and subprocessors—in plain English.",
    h1: "Privacy Policy",
    canonicalPath: "/privacy",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Privacy Policy", href: "/privacy" },
    ],
    related: [
      { href: "/terms", label: "Terms of Service" },
      { href: "/data-security", label: "Data security" },
      { href: "/contact", label: "Contact" },
    ],
    schemaProfile: "standard",
    lastModified: LEGAL_WAVE,
    primaryTopic: "DraftLens privacy policy",
    secondaryTopics: ["data collection", "AI providers", "document retention"],
  }),

  "/terms": p({
    path: "/terms",
    title: "Terms of Service — DraftLens",
    description:
      "Terms for using DraftLens AI document review and fix features: no professional advice, user responsibilities, cloud integrations, Stripe billing, acceptable use, warranties, and liability limits.",
    h1: "Terms of Service",
    canonicalPath: "/terms",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Terms of Service", href: "/terms" },
    ],
    related: [
      { href: "/privacy", label: "Privacy Policy" },
      { href: "/data-security", label: "Data security" },
      { href: "/contact", label: "Contact" },
    ],
    schemaProfile: "standard",
    lastModified: LEGAL_WAVE,
    primaryTopic: "DraftLens terms of service",
    secondaryTopics: ["user agreement", "acceptable use", "AI disclaimer"],
  }),

  "/data-security": p({
    path: "/data-security",
    title: "Data security & document handling — DraftLens",
    description:
      "Trust overview: how uploads are processed, what AI providers see, Google Drive scope, retention overview, sensitive documents, and what humans should verify—without overstating certifications.",
    h1: "Data security & document handling",
    canonicalPath: "/data-security",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Data security", href: "/data-security" },
    ],
    related: [
      { href: "/privacy", label: "Privacy Policy" },
      { href: "/terms", label: "Terms of Service" },
      { href: "/contact", label: "Contact" },
    ],
    schemaProfile: "standard",
    lastModified: LEGAL_WAVE,
    primaryTopic: "DraftLens data security",
    secondaryTopics: ["document handling", "AI processing transparency", "retention"],
  }),

  "/feedback": p({
    path: "/feedback",
    title: "Feedback & feature requests — DraftLens",
    description:
      "Tell us what to build next: missing features, confusing flows, or document types you want DraftLens to handle better. Optional email if you would like a reply.",
    h1: "Help shape DraftLens",
    canonicalPath: "/feedback",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Feedback", href: "/feedback" },
    ],
    related: [
      { href: "/product", label: "Product" },
      { href: "/features", label: "Features" },
      { href: "/contact", label: "Contact" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "DraftLens product feedback",
    secondaryTopics: ["feature request", "workflow input"],
  }),

  "/editorial-policy": p({
    path: "/editorial-policy",
    title: "Editorial policy — DraftLens Academy & research",
    description:
      "How DraftLens publishes academy and research content: accuracy, limitations, updates, and separation from the product UI. No fabricated benchmarks or credentials.",
    h1: "Editorial policy",
    canonicalPath: "/editorial-policy",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Editorial policy", href: "/editorial-policy" },
    ],
    related: [
      { href: "/methodology", label: "Methodology" },
      { href: "/research/benchmark-methodology", label: "Benchmark methodology" },
    ],
    schemaProfile: "article",
    lastModified: WAVE1,
    primaryTopic: "Editorial standards",
    secondaryTopics: ["E-E-A-T", "content governance"],
  }),

  "/features": p({
    path: "/features",
    title: "Features — DraftLens document review capabilities",
    description:
      "Explore how DraftLens handles multi-model review, review vs fix output, supporting evidence, and do-not-change locks—each as a focused capability for manuscripts you upload as DOCX or PDF.",
    h1: "Features",
    canonicalPath: "/features",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Features", href: "/features" },
    ],
    related: [
      { href: "/product", label: "Product overview" },
      { href: "/pricing", label: "Pricing" },
      { href: "/app", label: "Open the app" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "DraftLens features",
    secondaryTopics: ["multi-model review", "DOCX", "PDF", "review mode", "fix mode"],
  }),

  "/methodology": p({
    path: "/methodology",
    title: "Methodology — How DraftLens reviews documents",
    description:
      "How DraftLens structures reviewer output, merges findings, handles partial consensus, and applies convergence — written for technical readers and procurement.",
    h1: "Methodology",
    canonicalPath: "/methodology",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Methodology", href: "/methodology" },
    ],
    related: [
      { href: "/features", label: "All features" },
      { href: "/features/multi-model-review", label: "Multi-model review" },
      { href: "/research/benchmark-methodology", label: "Benchmark methodology" },
    ],
    schemaProfile: "article",
    lastModified: WAVE1,
    primaryTopic: "DraftLens methodology",
    secondaryTopics: ["structured review", "arbitration", "convergence"],
  }),

  "/features/multi-model-review": p({
    path: "/features/multi-model-review",
    title: "Multi-model review — DraftLens feature",
    description:
      "Why DraftLens runs multiple models on the same manuscript (DOCX or PDF): complementary failure modes, structured JSON outputs, and a merged issue ledger you can act on.",
    h1: "Multi-model review",
    canonicalPath: "/features/multi-model-review",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Features", href: "/features" },
      { name: "Multi-model review", href: "/features/multi-model-review" },
    ],
    related: [
      { href: "/features", label: "All features" },
      { href: "/use-cases/long-document-proofreading", label: "Long documents" },
      { href: "/compare/draftlens-vs-chatgpt", label: "vs. ChatGPT for documents" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "Multi-model document review",
    secondaryTopics: ["Claude GPT Gemini", "structured output"],
  }),

  "/features/review-mode": p({
    path: "/features/review-mode",
    title: "Review mode — findings without auto-editing the manuscript",
    description:
      "Review mode produces an issue ledger, digest, and exports for DOCX or PDF manuscripts so teams can decide what to change — ideal when you need judgment, not silent rewrites.",
    h1: "Review mode",
    canonicalPath: "/features/review-mode",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Features", href: "/features" },
      { name: "Review mode", href: "/features/review-mode" },
    ],
    related: [
      { href: "/features", label: "All features" },
      { href: "/features/fix-mode", label: "Fix mode" },
      { href: "/academy/how-to-proofread-a-long-document", label: "Proofreading long documents" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "Document review mode",
    secondaryTopics: ["issue ledger", "DOCX review", "PDF review"],
  }),

  "/features/fix-mode": p({
    path: "/features/fix-mode",
    title: "Fix mode — proposed edits with human verification",
    description:
      "Fix mode generates proposed edits and a corrected text path for Word (DOCX) workflows; PDF inputs follow the same review pipeline with export paths that match your verification process. DraftLens still expects human verification before filing or publishing.",
    h1: "Fix mode",
    canonicalPath: "/features/fix-mode",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Features", href: "/features" },
      { name: "Fix mode", href: "/features/fix-mode" },
    ],
    related: [
      { href: "/features", label: "All features" },
      { href: "/features/review-mode", label: "Review mode" },
      { href: "/pricing", label: "Pricing (Pro)" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "AI fix mode for documents",
    secondaryTopics: ["proposed edits", "DOCX", "PDF"],
  }),

  "/features/supporting-files": p({
    path: "/features/supporting-files",
    title: "Supporting files — evidence-aware review (Pro)",
    description:
      "Attach reference PDFs, DOCX, or text as supporting evidence. DraftLens treats the main manuscript you upload (DOCX or PDF) as the primary review target; supporting files inform review.",
    h1: "Supporting files",
    canonicalPath: "/features/supporting-files",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Features", href: "/features" },
      { name: "Supporting files", href: "/features/supporting-files" },
    ],
    related: [
      { href: "/features", label: "All features" },
      { href: "/use-cases/legal-document-review", label: "Legal workflows" },
      { href: "/pricing", label: "Pricing" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "Supporting evidence for document review",
    secondaryTopics: ["Pro feature", "PDF evidence"],
  }),

  "/features/do-not-change-locks": p({
    path: "/features/do-not-change-locks",
    title: "Do-not-change locks — preserve names, clauses, and numbers",
    description:
      "Tell reviewers which wording, parties, or figures must not be altered. DraftLens passes that intent into model context to reduce accidental edits.",
    h1: "Do-not-change locks",
    canonicalPath: "/features/do-not-change-locks",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Features", href: "/features" },
      { name: "Do-not-change locks", href: "/features/do-not-change-locks" },
    ],
    related: [
      { href: "/features", label: "All features" },
      { href: "/use-cases/contract-redlining", label: "Contract redlining" },
      { href: "/academy/how-to-preserve-voice-while-editing", label: "Preserve voice" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "Do not change document sections",
    secondaryTopics: ["constraints", "legal drafting"],
  }),

  "/use-cases/legal-document-review": p({
    path: "/use-cases/legal-document-review",
    title: "Legal document review with DraftLens",
    description:
      "Use DraftLens to stress-test memos, agreements, and client-facing drafts with multiple reviewers — then converge issues before partner review. Not legal advice.",
    h1: "Legal document review",
    canonicalPath: "/use-cases/legal-document-review",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Use cases", href: "/use-cases" },
      { name: "Legal", href: "/use-cases/legal-document-review" },
    ],
    related: [
      { href: "/use-cases/contract-redlining", label: "Contract redlining" },
      { href: "/academy/how-to-redline-a-word-document", label: "Redlining in Word (Academy)" },
      { href: "/features/supporting-files", label: "Supporting files" },
      { href: "/editorial-policy", label: "Editorial policy" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "Legal document AI review",
    secondaryTopics: ["contracts", "law firms"],
  }),

  "/use-cases/business-document-proofreading": p({
    path: "/use-cases/business-document-proofreading",
    title: "Business document proofreading with DraftLens",
    description:
      "Board memos, strategy docs, and customer-facing PDFs benefit from multi-model review: clarity, consistency, and risk flags without rewriting your voice.",
    h1: "Business document proofreading",
    canonicalPath: "/use-cases/business-document-proofreading",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Use cases", href: "/use-cases" },
      { name: "Business proofreading", href: "/use-cases/business-document-proofreading" },
    ],
    related: [
      { href: "/use-cases/long-document-proofreading", label: "Long documents" },
      { href: "/features/review-mode", label: "Review mode" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "Business proofreading software",
    secondaryTopics: ["memos", "enterprise"],
  }),

  "/use-cases/contract-redlining": p({
    path: "/use-cases/contract-redlining",
    title: "Contract redlining workflow support with DraftLens",
    description:
      "Surface inconsistencies, risky phrasing, and cross references before you circulate a redline. DraftLens outputs structured issues; humans decide what to change.",
    h1: "Contract redlining",
    canonicalPath: "/use-cases/contract-redlining",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Use cases", href: "/use-cases" },
      { name: "Contract redlining", href: "/use-cases/contract-redlining" },
    ],
    related: [
      { href: "/features/do-not-change-locks", label: "Do-not-change locks" },
      { href: "/academy/how-to-redline-a-word-document", label: "How to redline in Word" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "Contract redlining AI",
    secondaryTopics: ["MSA", "playbooks"],
  }),

  "/use-cases/long-document-proofreading": p({
    path: "/use-cases/long-document-proofreading",
    title: "Long document proofreading — structure and consistency",
    description:
      "Long DOCX or PDF files hide repetition, defined-term drift, and weak transitions. DraftLens reviews in blocks with caps so you get depth without unbounded token spend.",
    h1: "Long document proofreading",
    canonicalPath: "/use-cases/long-document-proofreading",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Use cases", href: "/use-cases" },
      { name: "Long documents", href: "/use-cases/long-document-proofreading" },
    ],
    related: [
      { href: "/features/multi-model-review", label: "Multi-model review" },
      { href: "/academy/how-to-proofread-a-long-document", label: "Academy guide" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "Long document proofreading",
    secondaryTopics: ["DOCX", "PDF", "book-length memos"],
  }),

  "/use-cases/academic-paper-review": p({
    path: "/use-cases/academic-paper-review",
    title: "Academic paper review — DraftLens use case",
    description:
      "Improve clarity and consistency in drafts while preserving scholarly voice. Always follow venue and integrity rules; DraftLens does not replace peer review or supervision.",
    h1: "Academic paper review",
    canonicalPath: "/use-cases/academic-paper-review",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Use cases", href: "/use-cases" },
      { name: "Academic papers", href: "/use-cases/academic-paper-review" },
    ],
    related: [
      { href: "/editorial-policy", label: "Editorial policy" },
      { href: "/features/do-not-change-locks", label: "Do-not-change locks" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "Academic writing review",
    secondaryTopics: ["scholarly voice", "integrity"],
  }),

  "/compare/draftlens-vs-grammarly": p({
    path: "/compare/draftlens-vs-grammarly",
    title: "DraftLens vs Grammarly — workflow comparison",
    description:
      "Grammarly excels at real-time writing assistance; DraftLens targets multi-model structured review of finished DOCX or PDF manuscripts with issue ledgers and optional fix packages.",
    h1: "DraftLens vs Grammarly",
    canonicalPath: "/compare/draftlens-vs-grammarly",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Compare", href: "/compare" },
      { name: "vs Grammarly", href: "/compare/draftlens-vs-grammarly" },
    ],
    related: [
      { href: "/compare/best-ai-proofreading-tools", label: "Best AI proofreading tools" },
      { href: "/features/review-mode", label: "Review mode" },
      { href: "/product", label: "Product" },
      { href: "/pricing", label: "Pricing" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "DraftLens vs Grammarly",
    secondaryTopics: ["comparison", "writing software"],
  }),

  "/compare/draftlens-vs-chatgpt": p({
    path: "/compare/draftlens-vs-chatgpt",
    title: "DraftLens vs ChatGPT for document review",
    description:
      "ChatGPT is a general assistant; DraftLens wraps multiple models in a review pipeline with structured JSON, merge logic, and exports aligned to DOCX or PDF manuscript workflows.",
    h1: "DraftLens vs ChatGPT",
    canonicalPath: "/compare/draftlens-vs-chatgpt",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Compare", href: "/compare" },
      { name: "vs ChatGPT", href: "/compare/draftlens-vs-chatgpt" },
    ],
    related: [
      { href: "/compare/draftlens-vs-claude", label: "vs Claude" },
      { href: "/features/multi-model-review", label: "Multi-model review" },
      { href: "/pricing", label: "Pricing" },
      { href: "/app", label: "Open the app" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "DraftLens vs ChatGPT for documents",
    secondaryTopics: ["LLM comparison", "DOCX", "PDF"],
  }),

  "/compare/draftlens-vs-claude": p({
    path: "/compare/draftlens-vs-claude",
    title: "DraftLens vs using Claude alone",
    description:
      "Claude is one of DraftLens’s reviewer models — not the whole system. DraftLens adds additional reviewers, merge/arbitration paths, and productized exports for DOCX and PDF pipelines.",
    h1: "DraftLens vs Claude alone",
    canonicalPath: "/compare/draftlens-vs-claude",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Compare", href: "/compare" },
      { name: "vs Claude", href: "/compare/draftlens-vs-claude" },
    ],
    related: [
      { href: "/compare/draftlens-vs-chatgpt", label: "vs ChatGPT" },
      { href: "/methodology", label: "Methodology" },
      { href: "/pricing", label: "Pricing" },
      { href: "/app", label: "Open the app" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "DraftLens vs Claude alone",
    secondaryTopics: ["Anthropic", "multi-model"],
  }),

  "/compare/best-ai-proofreading-tools": p({
    path: "/compare/best-ai-proofreading-tools",
    title: "Choosing AI proofreading tools for professional documents",
    description:
      "A practical lens: editor experience, manuscript workflows, model transparency, and export quality — without ranking vendors you have not independently benchmarked.",
    h1: "Choosing AI proofreading tools",
    canonicalPath: "/compare/best-ai-proofreading-tools",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Compare", href: "/compare" },
      { name: "Guide", href: "/compare/best-ai-proofreading-tools" },
    ],
    related: [
      { href: "/compare/draftlens-vs-grammarly", label: "vs Grammarly" },
      { href: "/product", label: "DraftLens product" },
      { href: "/research/benchmark-methodology", label: "Benchmark methodology" },
      { href: "/pricing", label: "Pricing" },
    ],
    schemaProfile: "article",
    lastModified: WAVE1,
    primaryTopic: "AI proofreading tools comparison",
    secondaryTopics: ["buyers guide", "software selection"],
  }),

  "/academy/how-to-redline-a-word-document": p({
    path: "/academy/how-to-redline-a-word-document",
    title: "How to redline a Word document — practical guide",
    description:
      "Definitions, track changes hygiene, comments vs. edits, and how to prep Word (DOCX) or exported PDF before multi-model review — written for operators, not hype.",
    h1: "How to redline a Word document",
    canonicalPath: "/academy/how-to-redline-a-word-document",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Academy", href: "/academy" },
      { name: "Redline in Word", href: "/academy/how-to-redline-a-word-document" },
    ],
    related: [
      { href: "/use-cases/contract-redlining", label: "Contract redlining" },
      { href: "/features/review-mode", label: "Review mode" },
      { href: "/features/do-not-change-locks", label: "Do-not-change locks" },
      { href: "/editorial-policy", label: "Editorial policy" },
    ],
    schemaProfile: "article",
    lastModified: WAVE1,
    primaryTopic: "Word document redlining",
    secondaryTopics: ["Microsoft Word", "track changes"],
  }),

  "/academy/how-to-proofread-a-long-document": p({
    path: "/academy/how-to-proofread-a-long-document",
    title: "How to proofread a long document",
    description:
      "Chunk the work, stabilize terminology, check cross references, and use tools responsibly. Includes how DraftLens fits into a long DOCX or PDF review pass.",
    h1: "How to proofread a long document",
    canonicalPath: "/academy/how-to-proofread-a-long-document",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Academy", href: "/academy" },
      { name: "Long document proofreading", href: "/academy/how-to-proofread-a-long-document" },
    ],
    related: [
      { href: "/use-cases/long-document-proofreading", label: "Use case" },
      { href: "/features/multi-model-review", label: "Multi-model review" },
      { href: "/academy/how-to-preserve-voice-while-editing", label: "Preserve voice" },
      { href: "/methodology", label: "Methodology" },
    ],
    schemaProfile: "article",
    lastModified: WAVE1,
    primaryTopic: "Long document proofreading",
    secondaryTopics: ["editing workflow", "DOCX", "PDF"],
  }),

  "/academy/how-to-preserve-voice-while-editing": p({
    path: "/academy/how-to-preserve-voice-while-editing",
    title: "How to preserve voice while editing",
    description:
      "Separate mechanical correctness from stylistic choices, lock sensitive phrasing, and review AI suggestions in context — especially for executive and legal voice.",
    h1: "How to preserve voice while editing",
    canonicalPath: "/academy/how-to-preserve-voice-while-editing",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Academy", href: "/academy" },
      { name: "Preserve voice", href: "/academy/how-to-preserve-voice-while-editing" },
    ],
    related: [
      { href: "/features/do-not-change-locks", label: "Do-not-change locks" },
      { href: "/features/review-mode", label: "Review mode" },
      { href: "/academy/how-to-proofread-a-long-document", label: "Proofread long documents" },
      { href: "/methodology", label: "Methodology" },
    ],
    schemaProfile: "article",
    lastModified: WAVE1,
    primaryTopic: "Preserve author voice editing",
    secondaryTopics: ["style", "constraints"],
  }),

  "/research": p({
    path: "/research",
    title: "Research — DraftLens document review evaluation",
    description:
      "Methodology notes and benchmark frameworks for evaluating multi-model document review — published without fabricated scores.",
    h1: "Research",
    canonicalPath: "/research",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Research", href: "/research" },
    ],
    related: [
      { href: "/research/benchmark-methodology", label: "Benchmark methodology" },
      { href: "/research/ai-document-review-benchmark", label: "Benchmark framework" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "DraftLens research",
    secondaryTopics: ["benchmark", "methodology"],
  }),

  "/research/benchmark-methodology": p({
    path: "/research/benchmark-methodology",
    title: "Document review benchmark methodology (DraftLens)",
    description:
      "How DraftLens thinks about evaluating multi-model document review: datasets, leakage controls, scoring rubrics, and human adjudication — a living framework, not a leaderboard.",
    h1: "Benchmark methodology",
    canonicalPath: "/research/benchmark-methodology",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Research", href: "/research" },
      { name: "Methodology", href: "/research/benchmark-methodology" },
    ],
    related: [
      { href: "/research/ai-document-review-benchmark", label: "Benchmark framework" },
      { href: "/compare/best-ai-proofreading-tools", label: "Choosing AI proofreading tools" },
      { href: "/editorial-policy", label: "Editorial policy" },
    ],
    schemaProfile: "article",
    lastModified: WAVE1,
    primaryTopic: "AI document review benchmark methodology",
    secondaryTopics: ["evaluation", "research"],
  }),

  "/use-cases": p({
    path: "/use-cases",
    title: "Use cases — DraftLens document review",
    description:
      "Explore how teams use DraftLens for legal drafts, business proofreading, contracts, long documents, and academic papers — always with human judgment in the loop.",
    h1: "Use cases",
    canonicalPath: "/use-cases",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Use cases", href: "/use-cases" },
    ],
    related: [
      { href: "/product", label: "Product" },
      { href: "/features/multi-model-review", label: "Multi-model review" },
      { href: "/academy", label: "Academy guides" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "DraftLens use cases",
    secondaryTopics: ["legal", "contracts", "academic"],
  }),

  "/compare": p({
    path: "/compare",
    title: "Compare — DraftLens vs other approaches",
    description:
      "Careful comparisons of workflow fit: DraftLens vs Grammarly, ChatGPT, or Claude-alone patterns — without fabricated scores or pricing claims.",
    h1: "Compare",
    canonicalPath: "/compare",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Compare", href: "/compare" },
    ],
    related: [
      { href: "/compare/best-ai-proofreading-tools", label: "Selection guide" },
      { href: "/product", label: "Product" },
      { href: "/methodology", label: "Methodology" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "DraftLens comparisons",
    secondaryTopics: ["Grammarly", "ChatGPT", "Claude"],
  }),

  "/academy": p({
    path: "/academy",
    title: "Academy — practical document review guides",
    description:
      "Operator-focused guides on redlining, long-document proofreading, and voice preservation — for DOCX or PDF manuscripts, aligned with how DraftLens thinks about review.",
    h1: "Academy",
    canonicalPath: "/academy",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Academy", href: "/academy" },
    ],
    related: [
      { href: "/editorial-policy", label: "Editorial policy" },
      { href: "/methodology", label: "Methodology" },
      { href: "/app", label: "Open the app" },
    ],
    schemaProfile: "standard",
    lastModified: WAVE1,
    primaryTopic: "Document review academy",
    secondaryTopics: ["Word", "proofreading", "voice"],
  }),

  "/research/ai-document-review-benchmark": p({
    path: "/research/ai-document-review-benchmark",
    title: "AI document review benchmark — framework (no vendor scores)",
    description:
      "A transparent framework for comparing document review systems: tasks, rubrics, and reporting rules. DraftLens does not publish numeric vendor rankings here without completed, disclosed runs.",
    h1: "AI document review benchmark framework",
    canonicalPath: "/research/ai-document-review-benchmark",
    breadcrumb: [
      { name: "Home", href: "/" },
      { name: "Research", href: "/research" },
      { name: "Benchmark framework", href: "/research/ai-document-review-benchmark" },
    ],
    related: [
      { href: "/research/benchmark-methodology", label: "Methodology detail" },
      { href: "/compare/best-ai-proofreading-tools", label: "Choosing AI proofreading tools" },
      { href: "/product", label: "Product" },
    ],
    schemaProfile: "article",
    lastModified: WAVE1,
    primaryTopic: "AI document review benchmark",
    secondaryTopics: ["framework", "research transparency"],
  }),
};

export const INDEXABLE_PATHS: string[] = Object.keys(PAGE_REGISTRY).sort();

export function getRegisteredPage(path: string): RegisteredPage | undefined {
  const key = path.endsWith("/") && path !== "/" ? path.slice(0, -1) : path;
  return PAGE_REGISTRY[key];
}

export function validateRegistry(): { ok: boolean; errors: string[] } {
  const errors: string[] = [];
  const titles = new Map<string, string[]>();
  const descs = new Map<string, string[]>();

  for (const [path, page] of Object.entries(PAGE_REGISTRY)) {
    if (path !== page.path) errors.push(`path key mismatch ${path} vs ${page.path}`);
    if (!page.title?.trim()) errors.push(`missing title: ${path}`);
    if (!page.description?.trim()) errors.push(`missing description: ${path}`);
    if (!page.h1?.trim()) errors.push(`missing h1: ${path}`);
    if (!page.canonicalPath?.trim()) errors.push(`missing canonicalPath: ${path}`);
    titles.set(page.title, [...(titles.get(page.title) ?? []), path]);
    descs.set(page.description, [...(descs.get(page.description) ?? []), path]);
  }
  for (const [title, paths] of titles) {
    if (paths.length > 1) errors.push(`duplicate title (${paths.join(", ")}): ${title}`);
  }
  for (const [d, paths] of descs) {
    if (paths.length > 1) errors.push(`duplicate description (${paths.join(", ")}): ${d.slice(0, 60)}…`);
  }
  return { ok: errors.length === 0, errors };
}
