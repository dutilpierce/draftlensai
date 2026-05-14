import type { ReactNode } from "react";
import { FeedbackRequestSection } from "@/components/marketing/FeedbackRequestSection";
import {
  AcademyCard,
  ComparisonCard,
  CTASection,
  FeatureCard,
  IntroBlock,
  KeyPointsGrid,
  LinkRow,
  PricingCard,
  ProseColumn,
  SectionHeading,
  SectionShell,
  StepRow,
  SummaryCard,
  SummaryRow,
  UseCaseCard,
} from "@/components/marketing/MarketingUi";
import {
  ACADEMY_INDEX_ITEMS,
  COMPARE_INDEX_ITEMS,
  FEATURE_INDEX_ITEMS,
  RESEARCH_INDEX_ITEMS,
  USE_CASE_INDEX_ITEMS,
} from "@/lib/marketing/hub-data";

export function HomeBody() {
  return (
    <>
      <SectionShell tone="warm">
        <SectionHeading eyebrow="At a glance">What you get on the first pass</SectionHeading>
        <SummaryRow>
          <SummaryCard title="What it is">
            Multi-model review for <strong>DOCX</strong> or <strong>PDF</strong> with structured outputs, optional
            convergence, and clear partial review when models or limits disagree.
          </SummaryCard>
          <SummaryCard title="Who it is for">
            Teams that already care about voice, citations, and “do not change” clauses—and people who run recurring
            reviews and need step-by-step outputs they can export and defend.
          </SummaryCard>
          <SummaryCard title="Why it is different">
            Disagreement is first-class data: merged ledgers, explicit stages, and honest labeling instead of fake
            consensus.
          </SummaryCard>
        </SummaryRow>
      </SectionShell>

      <SectionShell tone="cool">
        <SectionHeading eyebrow="Flow">How it works</SectionHeading>
        <StepRow
          steps={[
            {
              step: "01",
              title: "Upload",
              text: "Bring a manuscript as DOCX or PDF. Optionally attach supporting evidence where your plan allows it.",
            },
            {
              step: "02",
              title: "Review or fix",
              text: "Choose review mode for judgment-first triage, or fix mode when you want proposed edits packaged for verification.",
            },
            {
              step: "03",
              title: "Download results",
              text: "Download structured findings and stage-aligned exports (DOCX, PDF, ledgers)—then continue in Word or your PDF workflow with humans in control.",
            },
          ]}
        />
      </SectionShell>

      <SectionShell tone="blush">
        <SectionHeading eyebrow="Detail">In practice</SectionHeading>
        <ProseColumn>
          <p>
            <strong>DraftLens</strong> runs complementary reviewer models (for example Claude, GPT, and Gemini) on the
            same manuscript, merges structured findings, and can iterate toward convergence when configured—so you get
            a defensible ledger instead of a single chat reply.
          </p>
          <h2 className="!mt-10 text-xl font-semibold text-ink-950">Who it is for</h2>
          <ul>
            <li>Teams that already care about voice, citations, and “do not change” clauses.</li>
            <li>People who coordinate reviews and need exports with clear step labels they can audit—not a black box.</li>
            <li>Workloads where partial consensus is honest: DraftLens labels partial reviews instead of pretending unanimity.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="sage">
        <SectionHeading eyebrow="Navigate">Where to go next</SectionHeading>
        <LinkRow
          links={[
            { href: "/product", label: "Product overview" },
            { href: "/features", label: "All features" },
            { href: "/pricing", label: "Pricing" },
            { href: "/use-cases", label: "Use cases" },
            { href: "/compare", label: "Comparisons" },
          ]}
        />
      </SectionShell>

      <FeedbackRequestSection />

      <SectionShell>
        <CTASection>
          <p className="text-base font-medium text-white">Ready to run a manuscript?</p>
          <p className="mt-2 text-sm text-white/85">
            Open the live app to upload a <strong>DOCX</strong> or <strong>PDF</strong>, see entitlements, and download
            results from a real job—not placeholder output.
          </p>
          <p className="mt-5">
            <a
              href="/app"
              className="inline-flex items-center justify-center rounded-full bg-white px-5 py-2 text-sm font-semibold text-ink-950 hover:bg-ink-100"
            >
              Open the app
            </a>
          </p>
        </CTASection>
      </SectionShell>
    </>
  );
}

export function ProductBody() {
  return (
    <>
      <IntroBlock kicker="What DraftLens is">
        <p>
          <strong>DOCX or PDF:</strong> upload a manuscript, run structured multi-model review, and download clear
          deliverables—a prioritized issue ledger, digest, and stage-aligned exports. Optional supporting evidence and
          do-not-change locks keep reviewers grounded and conservative where you need them.
        </p>
      </IntroBlock>

      <SectionShell tone="warm">
        <SectionHeading eyebrow="Surfaces">Core capabilities</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-3">
          <SummaryCard title="Review mode">
            Issues, digest, and downloads without silently rewriting your file.{" "}
            <a href="/features/review-mode">Read the feature page</a>.
          </SummaryCard>
          <SummaryCard title="Fix mode">
            Proposed edits and corrected packages for workflows that expect change artifacts.{" "}
            <a href="/features/fix-mode">Read the feature page</a>.
          </SummaryCard>
          <SummaryCard title="Multi-model pass">
            Complementary model behavior with merge and (when applicable) arbitration and bounded convergence.{" "}
            <a href="/features/multi-model-review">Read the feature page</a>.
          </SummaryCard>
        </div>
      </SectionShell>

      <SectionShell tone="cool">
        <SectionHeading eyebrow="Who it is for">Teams that get the most value</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Teams that need repeatable outputs every run—not one-off brilliant answers.</li>
            <li>Reviewers who care about disagreement being visible, not smoothed away.</li>
            <li>Authors and counsel who need locks and evidence boundaries to reduce accidental edits.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Trust">Honest limitations</SectionHeading>
        <ProseColumn>
          <p>
            Models can miss context, mis-rank severity, or disagree. DraftLens is designed to surface that disagreement as
            structured output — not to replace professional judgment, compliance review, or legal advice.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Next step">Try it</SectionHeading>
        <LinkRow
          links={[
            { href: "/pricing", label: "Pricing" },
            { href: "/use-cases", label: "Use cases" },
            { href: "/academy", label: "Academy guides" },
            { href: "/app", label: "Open the app" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function PricingBody() {
  return (
    <>
      <IntroBlock kicker="Source of truth">
        <p>
          Plans and caps ship with the product and may change; this page describes intent, not a legal quote. For the
          numbers that apply to your account right now, use the live app while signed in.
        </p>
      </IntroBlock>

      <SectionShell tone="blush">
        <div className="grid gap-5 lg:grid-cols-2">
        <PricingCard
          name="Free"
          badge="Start here"
          tint="warm"
          footnote="Limits apply on total runs per month and which modes are available—see the app for your current balance."
        >
          <ul className="list-disc space-y-2 pl-4">
            <li>Access to review-focused workflows within fair monthly caps.</li>
            <li>Designed for individuals and teams evaluating fit before upgrading.</li>
            <li>Upgrade path to Pro when you need fix mode, supporting files, or higher throughput.</li>
          </ul>
        </PricingCard>
        <PricingCard
          name="Pro"
          badge="For production review"
          tint="cool"
          footnote="Manage billing from the in-app portal when subscribed; entitlements always win over website copy."
        >
          <ul className="list-disc space-y-2 pl-4">
            <li>Fix mode and supporting evidence workflows where enabled for your deployment.</li>
            <li>Higher fair-use caps for teams running frequent manuscript reviews.</li>
            <li>Same structured pipeline—more room for the workloads that need artifacts daily.</li>
          </ul>
        </PricingCard>
      </div>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Choosing">How to decide</SectionHeading>
        <ProseColumn>
          <ul>
            <li>
              If you only need occasional triage on finished <strong>DOCX</strong> or <strong>PDF</strong>, start on Free
              and validate outputs against your QC checklist.
            </li>
            <li>
              If your workflow requires supporting evidence ingestion or fix packages, confirm those entitlements in-app
              before relying on them for deadlines.
            </li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <FeedbackRequestSection />

      <SectionShell>
        <SectionHeading eyebrow="Source of truth">How to see current numbers</SectionHeading>
        <ProseColumn>
          <p>
            Open <a href="/app">the app</a> while signed in — entitlements, remaining uses, and Pro status are shown next to
            the runner. For billing management, use the in-app portal when on a Pro plan.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Learn more">Product context</SectionHeading>
        <LinkRow
          links={[
            { href: "/product", label: "Product overview" },
            { href: "/features", label: "Features" },
            { href: "/compare/best-ai-proofreading-tools", label: "Choosing tools" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function AboutBody() {
  return (
    <>
      <IntroBlock>
        <p>
          DraftLens concentrates on one hard problem: making multi-model document review predictable — structured JSON,
          explicit stages, partial review when quorum or rate limits bite, and exports that fit DOCX- and PDF-centric
          teams.
        </p>
      </IntroBlock>
      <SectionShell>
        <SectionHeading>Principles</SectionHeading>
        <KeyPointsGrid
          items={[
            {
              title: "Inspectable pipelines",
              body: "Prefer explicit stages and downloads over opaque “agent magic.”",
            },
            {
              title: "Honest status",
              body: "Prefer accurate partial status over fake consensus.",
            },
            {
              title: "Manuscript fidelity",
              body: "Prefer locks and evidence boundaries over aggressive rewriting.",
            },
            {
              title: "Human authority",
              body: "Software assists review; professionals remain accountable for outcomes.",
            },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function ContactBody() {
  return (
    <>
      <IntroBlock kicker="How to reach us">
        <p>
          Use the addresses below for the type of request you have. Before publishing these in OAuth consoles or customer
          contracts, confirm the inboxes exist or forward—see{" "}
          <code className="rounded bg-ink-100 px-1">docs/trust-and-email-setup.md</code>.
        </p>
      </IntroBlock>

      <SectionShell tone="warm">
        <SectionHeading eyebrow="Email">Primary channels</SectionHeading>
        <ProseColumn>
          <ul>
            <li>
              <strong>Product & billing support:</strong>{" "}
              <a href="mailto:support@draftlensai.com">support@draftlensai.com</a>
            </li>
            <li>
              <strong>Privacy & data requests:</strong>{" "}
              <a href="mailto:privacy@draftlensai.com">privacy@draftlensai.com</a>
            </li>
            <li>
              <strong>Security reports:</strong>{" "}
              <a href="mailto:security@draftlensai.com">security@draftlensai.com</a>
            </li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="cool">
        <SectionHeading eyebrow="Self-serve">Feedback and policies</SectionHeading>
        <ProseColumn>
          <p>
            Feature ideas and UX notes: <a href="/feedback">Feedback</a>
          </p>
          <p>
            Trust and legal pages: <a href="/privacy">Privacy</a>, <a href="/terms">Terms</a>,{" "}
            <a href="/data-security">Data security</a>
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Schema">Marketing email env</SectionHeading>
        <ProseColumn>
          <p className="text-sm text-ink-500">
            Optional: set <code className="rounded bg-ink-100 px-1">NEXT_PUBLIC_CONTACT_EMAIL</code> to the address you
            want reflected in structured data (JSON-LD) for the public site—often the same as support.
          </p>
        </ProseColumn>
      </SectionShell>
    </>
  );
}

export function EditorialPolicyBody() {
  return (
    <>
      <ProseColumn>
        <p>
          Academy and research pages aim for practical accuracy and clear limits. We do not fabricate benchmark scores,
          customer identities, or “as seen in” claims.
        </p>
        <h2 className="!mt-10 text-xl font-semibold text-ink-950">Updates</h2>
        <p>
          When product behavior changes, editorial pages are revised or dated. Major methodology shifts are documented on{" "}
          <a href="/research/benchmark-methodology">benchmark methodology</a>.
        </p>
      </ProseColumn>
    </>
  );
}

export function MethodologyBody() {
  return (
    <>
      <IntroBlock kicker="What this page answers">
        <p>
          In plain terms: how DraftLens structures reviewer output, merges findings, routes conflict, and applies bounded
          convergence. Deeper technical detail for readers who need an inspectable story—not a black box.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Pipeline">Structured review path</SectionHeading>
        <ProseColumn>
          <p>
            DraftLens reviewers return structured payloads validated against schemas. Findings are deduplicated, material
            conflicts are clustered, and routing decides whether debate plus arbitration is appropriate or whether the
            ledger should be synthesized without an arbiter call when quorum or clusters do not justify it.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Convergence">When cycles run</SectionHeading>
        <ProseColumn>
          <p>
            When enabled, bounded convergence re-runs reviewers against targeted blocks and refreshes arbitration—with
            explicit stop reasons (for example quorum loss, rate limits, or clean thresholds in fix mode). It is designed
            to avoid infinite loops and to label partial completion honestly.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Related">Read next</SectionHeading>
        <LinkRow
          links={[
            { href: "/research/benchmark-methodology", label: "Benchmark methodology" },
            { href: "/features/multi-model-review", label: "Multi-model review" },
            { href: "/product", label: "Product overview" },
          ]}
        />
      </SectionShell>
    </>
  );
}

function featureSections(
  intro: ReactNode,
  sections: { title: string; body: ReactNode }[],
) {
  return (
    <>
      <IntroBlock>{intro}</IntroBlock>
      {sections.map((s) => (
        <SectionShell key={s.title}>
          <SectionHeading>{s.title}</SectionHeading>
          <ProseColumn>{s.body}</ProseColumn>
        </SectionShell>
      ))}
    </>
  );
}

export function FeatureMultiModelBody() {
  return featureSections(
    <>
      <p>
        Single-model chat can be brilliant and still blind to classes of errors. DraftLens runs multiple structured
        reviewers on the same manuscript (DOCX or PDF), merges findings, and can iterate toward convergence when
        configured—so disagreements
        become inspectable data instead of silent majority votes.
      </p>
      <p className="text-sm text-ink-500">
        This is not “more models for show.” It is a hedge against correlated mistakes when one vendor’s defaults miss
        a risk pattern another catches.
      </p>
    </>,
    [
      {
        title: "Why it exists",
        body: (
          <p>
            Serious review workflows need redundancy: different training distributions, different refusal behaviors, and
            different blind spots. Merge logic exists because humans should not have to diff three chat transcripts by
            hand.
          </p>
        ),
      },
      {
        title: "When it matters most",
        body: (
          <ul>
            <li>High-stakes memos and agreements where missing an ambiguity is costly.</li>
            <li>Long documents where a single pass cannot cover everything with equal depth.</li>
          </ul>
        ),
      },
      {
        title: "Where it can fail or be limited",
        body: (
          <ul>
            <li>All models can miss context outside the manuscript (unless you attach evidence appropriately).</li>
            <li>Rate limits or provider outages can reduce quorum—DraftLens should label partial status honestly.</li>
            <li>Convergence is bounded; some disagreements still end in human follow-up.</li>
          </ul>
        ),
      },
      {
        title: "What you should still verify",
        body: (
          <ul>
            <li>Severity mapping to your org’s rubric—do not ship based on model-severity alone.</li>
            <li>Citations, numbers, and dates against primary sources.</li>
            <li>Anything touching regulated language or parties—use locks and human eyes.</li>
          </ul>
        ),
      },
      {
        title: "Related",
        body: (
          <LinkRow
            links={[
              { href: "/use-cases/long-document-proofreading", label: "Long documents" },
              { href: "/compare/draftlens-vs-chatgpt", label: "vs ChatGPT for documents" },
              { href: "/methodology", label: "Methodology" },
            ]}
          />
        ),
      },
    ],
  );
}

export function FeatureReviewModeBody() {
  return featureSections(
    <>
      <p>
        Review mode is for teams that want <strong>judgment first</strong>: a prioritized issue ledger, digest, and
        downloads without silently rewriting the manuscript binary. Humans decide what becomes a tracked change in Word.
      </p>
    </>,
    [
      {
        title: "Why it exists",
        body: (
          <p>
            Many failures come from accidental rewrites: tone shifts, subtle obligation changes, or “helpful” edits that
            are wrong but hard to spot in a long file. Review mode keeps the manuscript stable while you triage structured
            findings.
          </p>
        ),
      },
      {
        title: "When it matters most",
        body: (
          <ul>
            <li>Legal and exec comms where nuance matters and partners still redline in Word.</li>
            <li>Any workflow where auditability of “what the software suggested” must be separable from the file.</li>
          </ul>
        ),
      },
      {
        title: "Where it can be limited",
        body: (
          <p>
            You still need humans to disposition issues, update the manuscript deliberately, and reconcile comments with
            counterparties. Review mode does not remove Word—it front-loads triage.
          </p>
        ),
      },
      {
        title: "Best for / not ideal for",
        body: (
          <ul>
            <li>
              <strong>Best for:</strong> triage-led review, exec-sensitive drafts, partner handoff workflows.
            </li>
            <li>
              <strong>Not ideal for:</strong> real-time typing assistance inside the editor (use a drafting copilot for
              that).
            </li>
          </ul>
        ),
      },
      {
        title: "Related",
        body: (
          <LinkRow
            links={[
              { href: "/features/fix-mode", label: "Fix mode (when you need change packages)" },
              { href: "/academy/how-to-redline-a-word-document", label: "Academy: redlining in Word" },
              { href: "/use-cases/business-document-proofreading", label: "Business proofreading" },
            ]}
          />
        ),
      },
    ],
  );
}

export function FeatureFixModeBody() {
  return featureSections(
    <>
      <p>
        Fix mode packages <strong>proposed edits and corrected outputs</strong> for teams that want machine-generated
        change artifacts—still expecting humans to verify before filing or publishing.
      </p>
      <p>
        Availability depends on plan and policy; see <a href="/pricing">pricing</a> and your in-app entitlements.
      </p>
    </>,
    [
      {
        title: "Why it exists",
        body: (
          <p>
            Some workflows want “show me the change” artifacts, not only issues. Fix mode is for that operational reality—
            with explicit expectation that acceptance criteria and verification steps live with your team.
          </p>
        ),
      },
      {
        title: "When it matters most",
        body: (
          <ul>
            <li>High-volume internal docs with clear style guides and repeatable edits.</li>
            <li>Teams that already review machine suggestions as a normal gate—not as a shortcut around QC.</li>
          </ul>
        ),
      },
      {
        title: "Where it can fail or be limited",
        body: (
          <ul>
            <li>Complex layout-heavy DOCX may not map 1:1 to every desired edit location; PDF layout can differ from Word.</li>
            <li>Meaning-changing suggestions can look “locally correct”—human judgment remains mandatory.</li>
          </ul>
        ),
      },
      {
        title: "What to verify manually",
        body: (
          <ul>
            <li>Any edit touching numbers, party names, dates, or cross references.</li>
            <li>Voice and stance in exec summaries and regulated disclaimers.</li>
          </ul>
        ),
      },
      {
        title: "Related",
        body: (
          <LinkRow
            links={[
              { href: "/features/review-mode", label: "Review mode" },
              { href: "/features/do-not-change-locks", label: "Do-not-change locks" },
              { href: "/use-cases/business-document-proofreading", label: "Business proofreading" },
            ]}
          />
        ),
      },
    ],
  );
}

export function FeatureSupportingFilesBody() {
  return featureSections(
    <>
      <p>
        Supporting files are ingested as <strong>evidence</strong> to inform review of the main manuscript (DOCX or PDF).
        They are not
        silently merged into the editable manuscript target in v1—reducing accidental edits to reference material.
      </p>
    </>,
    [
      {
        title: "Why it exists",
        body: (
          <p>
            Real review depends on exhibits, policies, prior agreements, and data rooms. Supporting files keep models
            grounded in what you provide—without turning every PDF page into an accidental edit surface.
          </p>
        ),
      },
      {
        title: "When it matters most",
        body: (
          <ul>
            <li>Memos and agreements that cite schedules, pricing tables, or prior clauses.</li>
            <li>Compliance drafts where “what we said elsewhere” is part of correctness.</li>
          </ul>
        ),
      },
      {
        title: "Operational limits",
        body: (
          <p>
            Large evidence sets increase retrieval complexity. Keep supporting packs tight, labeled, and limited to what
            reviewers truly need—quality beats volume.
          </p>
        ),
      },
      {
        title: "What you should still verify",
        body: (
          <ul>
            <li>That the evidence you attached is the correct version and scope for the question at hand.</li>
            <li>That sensitive material is appropriate to include under your org’s AI and confidentiality rules.</li>
          </ul>
        ),
      },
      {
        title: "Related",
        body: (
          <LinkRow
            links={[
              { href: "/use-cases/legal-document-review", label: "Legal document review" },
              { href: "/pricing", label: "Pricing (Pro)" },
              { href: "/product", label: "Product overview" },
            ]}
          />
        ),
      },
    ],
  );
}

export function FeatureDoNotChangeBody() {
  return featureSections(
    <>
      <p>
        Do-not-change fields are injected into reviewer context so models steer away from renaming parties, altering
        defined terms, or “cleaning up” numbers you need verbatim.
      </p>
      <p className="text-sm text-ink-500">
        Locks reduce risk; they do not guarantee zero suggestions touching adjacent text—human review still matters.
      </p>
    </>,
    [
      {
        title: "Why it exists",
        body: (
          <p>
            The fastest way to lose trust in AI review is an accidental party rename or a “small” numeric edit. Locks make
            non-negotiable strings explicit so reviewers spend attention where humans actually want discretion.
          </p>
        ),
      },
      {
        title: "When it matters most",
        body: (
          <ul>
            <li>Contracts and deal documents with sensitive proper nouns and financial figures.</li>
            <li>Regulated boilerplate that must remain character-stable even if surrounding prose improves.</li>
          </ul>
        ),
      },
      {
        title: "Where it can be limited",
        body: (
          <p>
            Adjacent wording may still change in ways that affect meaning near a locked span. Treat locks as strong
            guardrails, not a formal verification system.
          </p>
        ),
      },
      {
        title: "What to verify manually",
        body: (
          <ul>
            <li>That lock lists are complete (missing a lock is worse than having too many).</li>
            <li>That punctuation around locked spans still reads correctly after accepted nearby edits.</li>
          </ul>
        ),
      },
      {
        title: "Related",
        body: (
          <LinkRow
            links={[
              { href: "/academy/how-to-preserve-voice-while-editing", label: "Preserve voice while editing" },
              { href: "/use-cases/contract-redlining", label: "Contract redlining" },
              { href: "/features/review-mode", label: "Review mode" },
            ]}
          />
        ),
      },
    ],
  );
}

export function UseLegalBody() {
  return (
    <>
      <IntroBlock kicker="Who this is for">
        <p>
          Lawyers, paralegals, and deal teams preparing <strong>memos, client updates, and agreement drafts</strong> for
          partner or counterparty review—who want a disciplined pre-pass without confusing tooling for legal advice.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Problems">Typical review failures</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Cross references drift after late insertions (schedules, definitions, exhibits).</li>
            <li>Ambiguous obligations (“reasonable efforts”) without consistent qualifiers across sections.</li>
            <li>Inconsistent party labels and defined terms after partial edits from multiple authors.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Where AI helps">What models can do well</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Surface clarity risks and internal inconsistencies as structured findings.</li>
            <li>Stress-test phrasing against supporting evidence when you attach exhibits (Pro; policy-dependent).</li>
            <li>Provide a second pass on mechanics so humans spend time on judgment calls.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Human judgment">What stays with counsel</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Privilege, filing, regulatory interpretation, and negotiation strategy.</li>
            <li>Whether a clause is acceptable—software cannot sign for the firm.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="DraftLens fit">Where it sits in the workflow</SectionHeading>
        <ProseColumn>
          <p>
            Use <a href="/features/review-mode">review mode</a> for triage-led outputs, add{" "}
            <a href="/features/supporting-files">supporting files</a> when you need anchors to exhibits, and apply{" "}
            <a href="/features/do-not-change-locks">locks</a> for names, numbers, and non-negotiable clauses. Export
            artifacts into your existing Word redline process—see{" "}
            <a href="/academy/how-to-redline-a-word-document">Academy: redlining in Word</a>.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Verify">Before you rely on output</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Spot-check every “material” issue against source documents and playbooks.</li>
            <li>Reconcile defined terms after any automated pass—tools can miss subtle drift.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Next step">Continue</SectionHeading>
        <LinkRow
          links={[
            { href: "/use-cases/contract-redlining", label: "Contract redlining" },
            { href: "/features/do-not-change-locks", label: "Do-not-change locks" },
            { href: "/app", label: "Run a review" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function UseBusinessBody() {
  return (
    <>
      <IntroBlock kicker="Who this is for">
        <p>
          Chiefs of staff, strategy leads, and comms teams shipping <strong>board memos, QBRs, and exec narratives</strong>{" "}
          where consistency and credibility matter as much as polish.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Problems">What usually goes wrong</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Metrics and narrative disagree after last-minute cuts.</li>
            <li>Tone shifts between sections authored by different contributors.</li>
            <li>“Small” wording edits change emphasis (risk vs opportunity) without owners noticing.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Where AI helps">Where automation earns its keep</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Mechanical consistency and duplication detection across long DOCX or PDF documents.</li>
            <li>Second opinions from a different model family on the same structured checklist.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Human judgment">What humans still own</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Stakeholder politics, sequencing of announcements, and what can be said externally.</li>
            <li>Final tone calibration for leadership voice.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="DraftLens fit">Settings that matter</SectionHeading>
        <ProseColumn>
          <p>
            Start with <a href="/features/review-mode">review mode</a> on high-risk memos so leaders see issues—not silent
            rewrites. When your org has clear acceptance criteria for machine-generated edits, evaluate{" "}
            <a href="/features/fix-mode">fix mode</a> (plan-dependent) for packaged changes you can verify in Word.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Next step">Continue</SectionHeading>
        <LinkRow
          links={[
            { href: "/use-cases/long-document-proofreading", label: "Long-document proofreading" },
            { href: "/academy/how-to-proofread-a-long-document", label: "Academy: long document proofreading" },
            { href: "/pricing", label: "Pricing" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function UseContractBody() {
  return (
    <>
      <IntroBlock kicker="Who this is for">
        <p>
          In-house counsel, contract managers, and deal desks preparing drafts for <strong>internal approval or external
          circulation</strong>—before the negotiation line hardens.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Problems">Typical review problems</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Obligations scattered across articles and schedules with inconsistent qualifiers.</li>
            <li>Defined terms that drift (capitalization, singular/plural, “including” lists).</li>
            <li>Cross references that silently break when clauses move.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Where AI helps">Where models add leverage</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Structured pass for ambiguity and internal inconsistency as a triage layer.</li>
            <li>Highlighting risky phrasing candidates for human prioritization—not automatic rewrites.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Human judgment">What humans still decide</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Business tradeoffs, liability caps, and fallback positions.</li>
            <li>What becomes a redline to the counterparty—DraftLens outputs are inputs to that decision.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="DraftLens fit">Features that matter here</SectionHeading>
        <ProseColumn>
          <p>
            Pair <a href="/features/do-not-change-locks">do-not-change locks</a> with{" "}
            <a href="/features/review-mode">review mode</a> so sensitive clauses stay anchored while reviewers still flag
            nearby risks. Use <a href="/academy/how-to-redline-a-word-document">Academy: redlining in Word</a> to keep
            markup hygiene tight before circulation.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Next step">Continue</SectionHeading>
        <LinkRow
          links={[
            { href: "/use-cases/legal-document-review", label: "Legal document review" },
            { href: "/features/do-not-change-locks", label: "Do-not-change locks" },
            { href: "/app", label: "Run a review" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function UseLongDocBody() {
  return (
    <>
      <IntroBlock kicker="Who this is for">
        <p>
          Editors, PMOs, and technical leads responsible for{" "}
          <strong>reports, manuals, and long-form DOCX or PDF</strong> where
          fatigue—not lack of skill—causes misses.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Problems">What usually goes wrong</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Terminology drift between chapters written on different days.</li>
            <li>Numbering and figure references desync after merges from contributors.</li>
            <li>Important caveats live only in the middle of the document—where reviewers skim.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Where AI helps">Where automation helps</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Block-budgeted passes that focus compute where routing places risk.</li>
            <li>Second model family catches different mistakes than the first on the same structured checklist.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Human judgment">What humans still schedule</SectionHeading>
        <ProseColumn>
          <ul>
            <li>A dedicated voice and politics pass after mechanical review—still non-optional for high-stakes docs.</li>
            <li>Final sign-off on claims that depend on external facts not present in the file.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="DraftLens fit">Workflow placement</SectionHeading>
        <ProseColumn>
          <p>
            DraftLens is strongest when the manuscript is already structured enough to review in segments. Read{" "}
            <a href="/academy/how-to-proofread-a-long-document">Academy: proofreading long documents</a>, then run{" "}
            <a href="/features/multi-model-review">multi-model review</a> when you want disagreement surfaced—not
            smoothed away.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Checklist">Before finalizing</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Headings stable; lists and captions consistent.</li>
            <li>Do-not-change regions set for boilerplate and legal disclaimers where applicable.</li>
            <li>Human spot audit on any “critical” severity item regardless of model agreement.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Next step">Continue</SectionHeading>
        <LinkRow
          links={[
            { href: "/academy/how-to-proofread-a-long-document", label: "Academy guide" },
            { href: "/features/multi-model-review", label: "Multi-model review" },
            { href: "/app", label: "Run a review" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function UseAcademicBody() {
  return (
    <>
      <IntroBlock kicker="Who this is for">
        <p>
          Faculty, grad students, and research writers improving <strong>clarity and consistency</strong> in drafts—only
          where their institution and venue policies allow AI assistance, and always with integrity constraints first.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Problems">Typical review problems</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Argument repetition across sections after restructuring.</li>
            <li>Terminology inconsistency (methods, constructs) confusing reviewers.</li>
            <li>Over-smoothing that makes claims sound stronger than the evidence supports.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Where AI helps">Where tooling can help</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Mechanical clarity passes and consistency checks on your own draft.</li>
            <li>Flagging ambiguous sentences that human readers stumble on—without asserting novelty or correctness.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Human judgment">What AI must not replace</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Supervision, authorship, citation integrity, and venue compliance—strictly human-led.</li>
            <li>Novelty and contribution claims—never outsource to automation.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="DraftLens fit">Settings that matter</SectionHeading>
        <ProseColumn>
          <p>
            Prefer <a href="/features/review-mode">review mode</a> so you keep control of edits. Use{" "}
            <a href="/features/do-not-change-locks">locks</a> for quotations, definitions, and any text that must remain
            verbatim. Read <a href="/editorial-policy">editorial policy</a> for how DraftLens publishes guidance alongside
            the product—and <a href="/academy/how-to-preserve-voice-while-editing">Academy: preserve voice</a> for editing
            discipline.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Next step">Continue</SectionHeading>
        <LinkRow
          links={[
            { href: "/academy/how-to-preserve-voice-while-editing", label: "Preserve voice while editing" },
            { href: "/editorial-policy", label: "Editorial policy" },
            { href: "/app", label: "Run a review" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function CompareGrammarlyBody() {
  return (
    <>
      <IntroBlock kicker="Short answer">
        <p>
          If you need <strong>real-time writing help while you type</strong> across many apps, a drafting copilot is the
          right mental model. If you need{" "}
          <strong>serious review of a finished DOCX or PDF</strong> with structured outputs and
          multi-model disagreement on the record, DraftLens fits that second job—not the first.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Who each fits">Best for</SectionHeading>
        <KeyPointsGrid
          items={[
            {
              title: "Grammarly-class workflows",
              body: "Authors polishing sentences live; individuals; mixed surfaces (email, docs, web).",
            },
            {
              title: "DraftLens-class workflows",
              body: "Teams reviewing frozen manuscripts: memos, agreements, policies—where exports and traceability matter.",
            },
          ]}
        />
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Workflow">What changes with long documents</SectionHeading>
        <ProseColumn>
          <p>
            Drafting assistants optimize the <em>current cursor</em>. Manuscript review optimizes the <em>whole file</em>{" "}
            under budgets—different failure modes. Long DOCX or PDF work needs chunking, stable styles, and explicit “what changed and
            why” artifacts; DraftLens is built around job stages and downloads rather than inline suggestions.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Traceability">Review record</SectionHeading>
        <ProseColumn>
          <p>
            Chat-style writing help produces conversational history. DraftLens produces pipeline-oriented outputs (issues,
            digests, packages—depending on mode) intended for handoff into Word or PDF workflows. Neither replaces your sign-off
            checklist.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Decision">What to choose</SectionHeading>
        <ProseColumn>
          <ul>
            <li>
              <strong>Choose Grammarly-style tools</strong> when the draft is still forming and speed while typing matters
              most.
            </li>
            <li>
              <strong>Choose DraftLens</strong> when the document is “frozen enough” to review seriously and you want
              structured, multi-model triage with honest partial status when limits bite.
            </li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Related">Next steps</SectionHeading>
        <LinkRow
          links={[
            { href: "/features/review-mode", label: "Review mode" },
            { href: "/compare/best-ai-proofreading-tools", label: "Choosing AI proofreading tools" },
            { href: "/pricing", label: "Pricing" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function CompareChatgptBody() {
  return (
    <>
      <IntroBlock kicker="Short answer">
        <p>
          ChatGPT is excellent for <strong>exploration and drafting in conversation</strong>. DraftLens is purpose-built
          for <strong>repeatable manuscript review jobs</strong>: structured outputs, merge logic, explicit stages, and
          downloads aligned to document workflows (DOCX, PDF exports)—not an infinitely branching thread.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Who each fits">Who each option is best for</SectionHeading>
        <ProseColumn>
          <ul>
            <li>
              <strong>Chat-style assistants:</strong> individuals iterating quickly, one-off questions, flexible prompts.
            </li>
            <li>
              <strong>DraftLens:</strong> operators who need the same shape of output every run and teams that care about
              partial consensus being labeled honestly.
            </li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Long documents">What happens at scale</SectionHeading>
        <ProseColumn>
          <p>
            Pasting large DOCX or PDF fragments into chat windows loses structure, splits context, and makes regression testing
            hard. A job runner with blocks and budgets is a different shape of problem—built for files that do not fit
            comfortably in one prompt window.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Multiple reviewers">Why “more chats” is not the same as multi-model review</SectionHeading>
        <ProseColumn>
          <p>
            Running separate threads per model pushes merge work onto humans in the clipboard. DraftLens runs reviewers in
            a pipeline context and merges structured findings—so disagreements become data you can act on rather than
            conflicting paragraphs you reconcile by memory.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Tradeoffs">At a glance</SectionHeading>
        <ProseColumn>
          <table>
            <thead>
              <tr>
                <th>Topic</th>
                <th>Chat-style assistant</th>
                <th>DraftLens</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Primary unit</td>
                <td>Conversation session</td>
                <td>Job + manuscript file (DOCX or PDF)</td>
              </tr>
              <tr>
                <td>Models</td>
                <td>Often one thread per model / manual copy</td>
                <td>Multi-model pass by design</td>
              </tr>
              <tr>
                <td>Outputs</td>
                <td>Free-form assistant text</td>
                <td>Structured payloads + export-oriented artifacts</td>
              </tr>
              <tr>
                <td>Failure behavior</td>
                <td>User-managed (retry, re-prompt)</td>
                <td>Pipeline-visible partial status when quorum or limits bite</td>
              </tr>
            </tbody>
          </table>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Related">Next steps</SectionHeading>
        <LinkRow
          links={[
            { href: "/features/multi-model-review", label: "Multi-model review" },
            { href: "/methodology", label: "Methodology" },
            { href: "/product", label: "Product overview" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function CompareClaudeBody() {
  return (
    <>
      <IntroBlock kicker="Short answer">
        <p>
          Claude can be <strong>one reviewer inside DraftLens</strong>. The product value is not “pick this model instead
          of that one”—it is packaging: structured outputs, merge, arbitration when warranted, bounded convergence, and
          honest partial status when limits or quorum break.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Who each fits">When Claude alone is enough</SectionHeading>
        <ProseColumn>
          <ul>
            <li>You are an individual expert comfortable owning merge, severity, and export formatting manually.</li>
            <li>Your document is small enough to keep full context in one working session without operational drift.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="When DraftLens adds value">Where orchestration shows up</SectionHeading>
        <ProseColumn>
          <ul>
            <li>
              <strong>Multiple failure modes:</strong> different models catch different issues; merge logic matters more
              than any single model badge.
            </li>
            <li>
              <strong>Traceability:</strong> teams need repeatable artifacts, not screenshots of a good answer.
            </li>
            <li>
              <strong>Operational reality:</strong> rate limits and partial quorum should surface as status—not silent
              retries that pretend nothing happened.
            </li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Workflow">Document handoff (DOCX & PDF)</SectionHeading>
        <ProseColumn>
          <p>
            DraftLens is oriented to manuscript files (<strong>DOCX or PDF</strong>) and review modes your team can
            route into Word or PDF workflows. If you already like Claude’s judgment, DraftLens is the layer that makes that
            judgment comparable across runs and reviewers—without claiming it replaces your final read.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Related">Next steps</SectionHeading>
        <LinkRow
          links={[
            { href: "/compare/draftlens-vs-chatgpt", label: "vs ChatGPT for documents" },
            { href: "/features/multi-model-review", label: "Multi-model review" },
            { href: "/app", label: "Open the app" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function CompareBestToolsBody() {
  return (
    <>
      <IntroBlock kicker="Short answer">
        <p>
          Pick document AI tools on <strong>workflow fit and evidence</strong>: what the tool does to your file, what it
          promises when models disagree, and whether you can audit outputs—not on headline scores you cannot reproduce.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Evaluation">What to test before you buy</SectionHeading>
        <ProseColumn>
          <ol className="list-decimal space-y-3 pl-5">
            <li>
              <strong>Run your own DOCX or PDF</strong> (sanitized): not toy sentences—your headings, tables, defined terms.
            </li>
            <li>
              <strong>Force disagreement</strong>: pick a paragraph where reasonable reviewers could split; see if the
              tool surfaces conflict or smooths it away.
            </li>
            <li>
              <strong>Inspect exports</strong>: what do you hand to counsel or execs—structured issues, change packages, or
              only chat text?
            </li>
            <li>
              <strong>Stress partial failure</strong>: what happens when one provider is unavailable—honest labeling or
              silent downgrade?
            </li>
          </ol>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Why scores mislead">Benchmarks without disclosed harness detail</SectionHeading>
        <ProseColumn>
          <p>
            A single number rarely captures unsafe suggestion rate, evidence linkage quality, or how tools behave on long
            files. Read DraftLens research pages for what a credible benchmark would include—without fabricated rankings.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Related">Compare next</SectionHeading>
        <LinkRow
          links={[
            { href: "/compare/draftlens-vs-grammarly", label: "DraftLens vs Grammarly" },
            { href: "/compare/draftlens-vs-chatgpt", label: "DraftLens vs ChatGPT" },
            { href: "/research/benchmark-methodology", label: "Benchmark methodology" },
            { href: "/pricing", label: "Pricing" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function AcademyRedlineBody() {
  return (
    <>
      <IntroBlock kicker="Quick answer">
        <p>
          A good Word redline is a <strong>conversation you can audit</strong>: every change has intent, scope, and a
          clean separation between cosmetic formatting and substance. That discipline matters twice—once for humans,
          once before you add AI review on top.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Context">When this problem shows up</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Deal teams circulate a draft where comments duplicate, contradict, or bury the real asks.</li>
            <li>Track Changes noise (fonts, spacing) hides a material definition or obligation shift.</li>
            <li>You are about to run structured AI review and need the manuscript stable enough for consistent spans.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Watch for">Common mistakes</SectionHeading>
        <ProseColumn>
          <ul>
            <li>
              <strong>Drive-by comments</strong> without a proposed edit—fine for questions, expensive for execution.
            </li>
            <li>
              <strong>Global style “fixes”</strong> that create hundreds of low-value changes before substantive review.
            </li>
            <li>
              <strong>Implicit rewrites</strong> in comment text that never become tracked insertions—easy to miss at
              signing.
            </li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Manual workflow">How to handle it in Word first</SectionHeading>
        <ProseColumn>
          <ol className="list-decimal space-y-3 pl-5">
            <li>
              <strong>Freeze scope</strong>: decide what is in-round (definitions, economics, reps) vs out-of-round
              (formatting polish).
            </li>
            <li>
              <strong>Normalize the baseline</strong>: one heading hierarchy, consistent list numbering, stable styles—so
              later diffs map to intent.
            </li>
            <li>
              <strong>Use comments for questions, inserts for proposals</strong>: keep “why” in comments and “what
              changes” in tracked text where possible.
            </li>
            <li>
              <strong>Tag severity in your team’s language</strong> (blocking / material / cosmetic) so downstream
              readers triage faster.
            </li>
          </ol>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Product fit">How DraftLens helps</SectionHeading>
        <ProseColumn>
          <p>
            After the manuscript is stable, DraftLens can run structured reviewers on the same file and surface a
            merged issue ledger—useful when you want machine-assisted triage before partner markup.{" "}
            <a href="/features/review-mode">Review mode</a> keeps judgment-first outputs;{" "}
            <a href="/features/do-not-change-locks">do-not-change locks</a> carry your “must not drift” phrases into
            model context.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Limits">What DraftLens does not replace</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Negotiation strategy, privilege decisions, and regulatory interpretation.</li>
            <li>Counterparty-facing tone and relationship risk—still human-led.</li>
            <li>Final sign-off: models can miss context; treat outputs as inputs to your existing QC.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Checklist">Before you finalize</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Every blocking comment has an owner and a proposed resolution path.</li>
            <li>Defined terms and party names match your control list (locks help here).</li>
            <li>Cross-references resolve after insertions (schedules, exhibits, section xrefs).</li>
            <li>You have a second human read on anything labeled material—even if AI agreed.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Related">Next steps</SectionHeading>
        <LinkRow
          links={[
            { href: "/use-cases/contract-redlining", label: "Contract redlining workflow" },
            { href: "/features/do-not-change-locks", label: "Do-not-change locks" },
            { href: "/app", label: "Run a review in the app" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function AcademyLongBody() {
  return (
    <>
      <IntroBlock kicker="Quick answer">
        <p>
          Long proofreading fails when you try to do <strong>everything in one pass</strong>. Split the job: mechanics and
          consistency first, voice and politics second—then add AI where it helps without pretending one pass is enough.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Context">When this problem shows up</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Memos and reports where terminology drifts between sections written weeks apart.</li>
            <li>Executive summaries that contradict body detail because edits landed out of order.</li>
            <li>Appendices and tables that are correct in isolation but inconsistent with the narrative.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Watch for">Common mistakes</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Reading from page one to end in a single sitting—attention drops; errors cluster in the “boring” middle.</li>
            <li>Fixing sentences locally without updating dependent claims elsewhere.</li>
            <li>Letting formatting churn obscure real edits during team review.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Manual workflow">How to proofread manually (two-pass minimum)</SectionHeading>
        <ProseColumn>
          <p>
            <strong>Pass A — cold mechanics:</strong> spelling, grammar, numbering, captions, units, dates, xref labels.
            Work in short chunks (chapter, argument block, or time-boxed slices).
          </p>
          <p>
            <strong>Pass B — warm coherence:</strong> narrative arc, tone, stakeholder language, and “does this still
            claim what we intend after Pass A?”
          </p>
          <p className="text-sm text-ink-500">
            Keep a living terminology sheet (product names, banned phrases, capitalizations). One source of truth beats
            memory.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Product fit">How DraftLens helps</SectionHeading>
        <ProseColumn>
          <p>
            DraftLens reviews the manuscript in <strong>blocks with explicit budgets</strong> so models focus where the
            pipeline routes them—useful for long DOCX or PDF work where you want a second mechanical and consistency sweep. See{" "}
            <a href="/features/multi-model-review">multi-model review</a> and the{" "}
            <a href="/use-cases/long-document-proofreading">long-document use case</a> for workflow placement.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Limits">What DraftLens does not solve automatically</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Organizational politics, approval chains, and “who owns this paragraph.”</li>
            <li>Fact-finding beyond what is in the manuscript and attached evidence (when enabled).</li>
            <li>Final voice polish—schedule human time for Pass B even if Pass A was assisted.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Checklist">Before you finalize</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Defined terms and product names consistent across body, summary, and appendices.</li>
            <li>Figures and tables referenced in text still match after late edits.</li>
            <li>Any AI-surfaced issue has a human disposition (accept / edit / reject with rationale).</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Related">Next steps</SectionHeading>
        <LinkRow
          links={[
            { href: "/use-cases/long-document-proofreading", label: "Long-document use case" },
            { href: "/academy/how-to-preserve-voice-while-editing", label: "Preserve voice while editing" },
            { href: "/methodology", label: "How DraftLens structures review" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function AcademyVoiceBody() {
  return (
    <>
      <IntroBlock kicker="Quick answer">
        <p>
          Voice breaks when edits optimize <strong>local sentences</strong> but ignore stance, rhythm, and who the reader
          is. Protect voice by separating “must not change” strings from “may improve” regions—then review suggestions in
          full paragraphs, not isolated fragments.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Context">When this problem shows up</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Ghostwritten pieces where tightening reads “more professional” but loses personality.</li>
            <li>Founder letters and memos where hedging shifts change perceived conviction.</li>
            <li>Technical content where “clarity” edits flatten nuance that specialists rely on.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Watch for">Common mistakes</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Accepting a suggestion because it is shorter—not because it preserves intent.</li>
            <li>Editing line-by-line in track changes without re-reading the paragraph aloud (or silently) afterward.</li>
            <li>Letting models “harmonize tone” across sections that intentionally differ (exec summary vs legal caveat).</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Manual workflow">How to preserve voice manually</SectionHeading>
        <ProseColumn>
          <ol className="list-decimal space-y-3 pl-5">
            <li>
              <strong>Write a voice note</strong> in three bullets: audience, stance, taboos (words to avoid, tone
              ceiling/floor).
            </li>
            <li>
              <strong>Mark frozen phrases</strong> (titles, quotes, regulated lines) so editors do not “smooth” them.
            </li>
            <li>
              <strong>Batch mechanical fixes</strong> separate from rhetorical edits—different mindset, fewer accidents.
            </li>
            <li>
              <strong>Re-read for rhythm</strong> after mechanical passes; if it sounds anonymous, revert and tighten
              manually.
            </li>
          </ol>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Product fit">How DraftLens helps</SectionHeading>
        <ProseColumn>
          <p>
            <a href="/features/do-not-change-locks">Do-not-change locks</a> pass your frozen phrases into reviewer
            context. <a href="/features/review-mode">Review mode</a> keeps the manuscript file from being silently
            rewritten—so you decide what becomes a tracked change after you read the ledger.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Limits">What DraftLens does not decide</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Whether a sharper sentence is on-brand—that is author and approver judgment.</li>
            <li>Whether risk tolerance allows a more direct claim—policy and legal context win.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Checklist">Before you finalize</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Read every paragraph that saw heavy suggestion activity end-to-end—not only the diff.</li>
            <li>Compare opening and closing: stance should match; if not, fix narrative—not individual words.</li>
            <li>Spot-check quotes and attributed language character-for-character.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Related">Next steps</SectionHeading>
        <LinkRow
          links={[
            { href: "/features/do-not-change-locks", label: "Do-not-change locks" },
            { href: "/academy/how-to-proofread-a-long-document", label: "Proofread a long document" },
            { href: "/editorial-policy", label: "Editorial policy" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function ResearchMethodologyBody() {
  return (
    <>
      <IntroBlock kicker="What this page is for">
        <p>
          A credible document-review benchmark states tasks, datasets, rubrics, and adjudication rules up front—and
          reports failure modes and costs, not only headline accuracy. This page explains how DraftLens thinks about that
          design space <strong>without publishing comparative vendor scores</strong>.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Measurement">What should be measured</SectionHeading>
        <ProseColumn>
          <ul>
            <li>
              <strong>Task realism:</strong> whole-document behaviors (cross references, definitions) not isolated toy
              sentences.
            </li>
            <li>
              <strong>Severity calibration:</strong> material vs nit, and whether “helpful” edits are meaning-preserving.
            </li>
            <li>
              <strong>Evidence linkage:</strong> when claims require exhibits, does the system stay grounded or hallucinate
              anchors?
            </li>
            <li>
              <strong>Operational stress:</strong> long inputs, partial provider failures, and honest partial outputs.
            </li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Design">Why benchmark design matters</SectionHeading>
        <ProseColumn>
          <p>
            Raw scores become misleading when prompts leak, datasets overlap with training, or rubrics reward aggressive
            rewriting over conservative correctness. A serious methodology publishes enough detail that a third party could
            attempt to reproduce the harness—knowing reproduction may still differ in implementation details.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="DraftLens stance">How we think about methodology</SectionHeading>
        <ProseColumn>
          <p>
            DraftLens product behavior already emphasizes structured outputs, explicit stages, and honest partial status.
            Any external benchmark we publish should mirror those values: disclose what ran, what failed, and what humans
            adjudicated.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Future outputs">What may ship later (only with real runs)</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Task mix results with confidence intervals—not single-point leaderboards.</li>
            <li>Failure galleries: examples where models disagreed or where partial quorum applied.</li>
            <li>Open prompts and scoring notes sufficient for independent replication attempts.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Related">Read next</SectionHeading>
        <LinkRow
          links={[
            { href: "/research/ai-document-review-benchmark", label: "Benchmark framework" },
            { href: "/editorial-policy", label: "Editorial policy" },
            { href: "/methodology", label: "Product methodology" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function ResearchBenchmarkFrameworkBody() {
  return (
    <>
      <IntroBlock kicker="What exists today">
        <p>
          This page intentionally does <strong>not</strong> publish comparative vendor scores, win rates, or rankings. It
          defines what a fair benchmark would measure and how DraftLens will document results when real, completed runs
          exist.
        </p>
      </IntroBlock>

      <SectionShell>
        <SectionHeading eyebrow="Why raw scores mislead">What a headline number hides</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Prompt sensitivity: small wording changes can swing outcomes without changing real-world usefulness.</li>
            <li>Dataset leakage and memorization: models can appear “smart” on familiar text.</li>
            <li>Rubric gaming: optimizing for the scorer instead of the reader’s risk.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="What good would include">Benchmark components</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Document types spanning legal, policy, technical, and executive narrative styles.</li>
            <li>Human adjudication protocol for a sampled subset to keep automated rubrics honest.</li>
            <li>Reporting rules for partial runs, abstentions, and provider unavailability.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Limitations">Explicitly out of scope here</SectionHeading>
        <ProseColumn>
          <ul>
            <li>Fabricated win rates or unverifiable rankings.</li>
            <li>Undisclosed prompt sets presented as “neutral.”</li>
            <li>Claims of statistical significance without published sample design.</li>
          </ul>
        </ProseColumn>
      </SectionShell>

      <SectionShell>
        <SectionHeading eyebrow="Related">Continue</SectionHeading>
        <LinkRow
          links={[
            { href: "/research/benchmark-methodology", label: "Benchmark methodology" },
            { href: "/compare/best-ai-proofreading-tools", label: "Choosing AI proofreading tools" },
            { href: "/product", label: "Product overview" },
          ]}
        />
      </SectionShell>
    </>
  );
}

export function FeaturesHubBody() {
  return (
    <>
      <IntroBlock kicker="How to read these pages">
        <p>
          Each feature page explains what DraftLens does in production, why teams ask for it, where it breaks down, and
          what humans must still verify. Start with the capability you are evaluating—not the whole product at once.
        </p>
      </IntroBlock>

      <SectionShell tone="warm">
        <SectionHeading eyebrow="Capabilities">Features</SectionHeading>
        <p className="mb-6 max-w-3xl text-sm text-ink-500">
          Prefer <a href="/features/review-mode">review mode</a> when you want issues first; consider{" "}
          <a href="/features/fix-mode">fix mode</a> when your workflow expects change packages—subject to plan.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          {FEATURE_INDEX_ITEMS.map((f) => (
            <FeatureCard key={f.href} href={f.href} title={f.title} summary={f.summary} accent={f.accent} />
          ))}
        </div>
      </SectionShell>

      <SectionShell tone="cool">
        <SectionHeading eyebrow="Workflow">Where features show up together</SectionHeading>
        <LinkRow
          links={[
            { href: "/product", label: "Product overview" },
            { href: "/use-cases", label: "Use cases" },
            { href: "/methodology", label: "Methodology" },
          ]}
        />
      </SectionShell>

      <FeedbackRequestSection />
    </>
  );
}

export function UseCasesHubBody() {
  return (
    <>
      <IntroBlock kicker="How to use this section">
        <p>
          Pick the scenario closest to your workflow. Each use case explains typical failure modes, where AI can help,
          where humans must stay in charge, and which DraftLens features matter most—without pretending one paragraph fits
          every org.
        </p>
      </IntroBlock>

      <SectionShell tone="cool">
        <SectionHeading eyebrow="Scenarios">Use cases</SectionHeading>
        <div className="mt-2 grid gap-4 lg:grid-cols-2">
          {USE_CASE_INDEX_ITEMS.map((u) => (
            <UseCaseCard
              key={u.href}
              href={u.href}
              title={u.title}
              summary={u.summary}
              accent={u.accent}
              humanCheck={u.humanCheck}
            />
          ))}
        </div>
      </SectionShell>

      <SectionShell tone="warm">
        <SectionHeading eyebrow="Operators">If you are choosing for a team</SectionHeading>
        <ProseColumn>
          <p>
            Read <a href="/methodology">methodology</a> for how each run behaves end to end, then map your QC gates to{" "}
            <a href="/features/review-mode">review mode</a> vs <a href="/features/fix-mode">fix mode</a>. Legal-adjacent
            teams should skim <a href="/use-cases/legal-document-review">legal</a> and{" "}
            <a href="/use-cases/contract-redlining">contracts</a> even if your primary workload is “just memos.”
          </p>
        </ProseColumn>
      </SectionShell>

      <FeedbackRequestSection />
    </>
  );
}

export function CompareHubBody() {
  return (
    <>
      <IntroBlock kicker="How to use comparisons">
        <p>
          These pages help you decide <strong>workflow fit</strong>: drafting-time assistance vs manuscript-time review,
          chat flexibility vs structured job deliverables (reports, ledgers, downloads), single-model depth vs structured
          multi-model merge. They are not unverified feature matrices or pricing claims.
        </p>
      </IntroBlock>

      <SectionShell tone="warm">
        <SectionHeading eyebrow="Guides">Comparisons</SectionHeading>
        <div className="mt-2 grid gap-4 sm:grid-cols-2">
          {COMPARE_INDEX_ITEMS.map((c) => (
            <ComparisonCard
              key={c.href}
              href={c.href}
              title={c.title}
              question={c.question}
              summary={c.summary}
              accent={c.accent}
            />
          ))}
        </div>
      </SectionShell>

      <SectionShell tone="sage">
        <SectionHeading eyebrow="If you are deciding today">Practical path</SectionHeading>
        <ProseColumn>
          <ol className="list-decimal space-y-2 pl-5">
            <li>
              Read <a href="/compare/best-ai-proofreading-tools">Choosing AI proofreading tools</a> and run your own
              sample DOCX or PDF in the app.
            </li>
            <li>
              Map outputs to your QC: do you need structured issues, change packages, or conversation only?
            </li>
            <li>
              Check <a href="/pricing">pricing</a> for plan fit after you know which modes you will use.
            </li>
          </ol>
        </ProseColumn>
      </SectionShell>

      <FeedbackRequestSection />
    </>
  );
}

export function AcademyHubBody() {
  return (
    <>
      <IntroBlock kicker="What Academy is for">
        <p>
          Short, practical guides for people who actually ship DOCX or PDF: operators, reviewers, and authors. Each article is
          written so you can apply it in Word first—then decide where DraftLens fits as a second pass.
        </p>
      </IntroBlock>

      <SectionShell tone="warm">
        <SectionHeading eyebrow="How to use this section">Read in order—or jump to your bottleneck</SectionHeading>
        <ProseColumn>
          <ul>
            <li>
              <strong>Redlining</strong> when circulation and markup discipline are the risk (
              <a href="/academy/how-to-redline-a-word-document">guide</a>
              ).
            </li>
            <li>
              <strong>Long documents</strong> when fatigue and inconsistency dominate (
              <a href="/academy/how-to-proofread-a-long-document">guide</a>
              ).
            </li>
            <li>
              <strong>Voice</strong> when AI or human edits flatten stance (
              <a href="/academy/how-to-preserve-voice-while-editing">guide</a>
              ).
            </li>
          </ul>
          <p className="text-sm text-ink-500">
            Pair guides with{" "}
            <a href="/product" className="font-medium text-ink-800 underline-offset-2 hover:underline">
              product overview
            </a>{" "}
            and{" "}
            <a href="/methodology" className="font-medium text-ink-800 underline-offset-2 hover:underline">
              methodology
            </a>{" "}
            when you need pipeline context.
          </p>
        </ProseColumn>
      </SectionShell>

      <SectionShell tone="cool">
        <SectionHeading eyebrow="Articles">Guides</SectionHeading>
        <div className="grid gap-4 md:grid-cols-3">
          {ACADEMY_INDEX_ITEMS.map((a) => (
            <AcademyCard
              key={a.href}
              href={a.href}
              title={a.title}
              reader={a.reader}
              summary={a.summary}
              accent={a.accent}
              outcome={a.outcome}
            />
          ))}
        </div>
      </SectionShell>

      <SectionShell tone="sage">
        <SectionHeading eyebrow="Next step">Run a manuscript</SectionHeading>
        <ProseColumn>
          <p>
            When you are ready to layer structured multi-model review on top of a clean DOCX or PDF, open the app and upload
            your file—see{" "}
            <a href="/pricing" className="font-medium text-ink-800 underline-offset-2 hover:underline">
              pricing
            </a>{" "}
            for plan fit.
          </p>
          <LinkRow
            links={[
              { href: "/app", label: "Open the app" },
              { href: "/features/review-mode", label: "Review mode" },
              { href: "/use-cases/contract-redlining", label: "Contract redlining use case" },
            ]}
          />
        </ProseColumn>
      </SectionShell>
    </>
  );
}

export function ResearchHubBody() {
  return (
    <>
      <IntroBlock kicker="What you will find here">
        <p>
          Research on DraftLens is <strong>methodology-first</strong>: how to evaluate document-review systems fairly, what
          raw scores hide, and what we would publish only after real runs with disclosure. There are no fabricated
          leaderboards here.
        </p>
      </IntroBlock>

      <SectionShell tone="warm">
        <SectionHeading eyebrow="Topics">Research</SectionHeading>
        <div className="mt-2 grid gap-4 md:grid-cols-2">
          {RESEARCH_INDEX_ITEMS.map((r) => (
            <FeatureCard key={r.href} href={r.href} title={r.title} summary={r.summary} accent={r.accent} />
          ))}
        </div>
      </SectionShell>

      <SectionShell tone="cool">
        <SectionHeading eyebrow="Operators">If you are procuring or auditing</SectionHeading>
        <ProseColumn>
          <p>
            Start with <a href="/research/benchmark-methodology">benchmark methodology</a>, then read{" "}
            <a href="/editorial-policy">editorial policy</a> for how we separate research pages from product UI claims.
            When you need workflow guidance while evaluation is still underway, pair with{" "}
            <a href="/compare/best-ai-proofreading-tools">Choosing AI proofreading tools</a>.
          </p>
        </ProseColumn>
      </SectionShell>
    </>
  );
}
