import type { ReactNode } from "react";
import Link from "next/link";

/** Optional full-width (within article) band tint for long-page rhythm — keep sparse. */
export type SectionBandTone = "plain" | "warm" | "cool" | "sage" | "blush";

const SECTION_BAND: Record<Exclude<SectionBandTone, "plain">, string> = {
  warm: "bg-surface-band-warm",
  cool: "bg-surface-band-cool",
  sage: "bg-surface-band-sage",
  blush: "bg-surface-band-blush",
};

/** Vertical rhythm between major bands (hero, grids, deep copy). */
export function SectionShell({
  id,
  children,
  className = "",
  tone = "plain",
}: {
  id?: string;
  children: ReactNode;
  className?: string;
  /** Subtle inset band — alternates page warmth without heavy blocks. */
  tone?: SectionBandTone;
}) {
  const inner =
    tone === "plain" ? (
      children
    ) : (
      <div
        className={`${SECTION_BAND[tone]} -mx-5 rounded-2xl border border-line/70 px-5 py-7 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.45)] ring-1 ring-ink-900/[0.07] sm:-mx-6 sm:px-6 sm:py-8`}
      >
        {children}
      </div>
    );

  return (
    <section id={id} className={`mt-12 scroll-mt-8 first:mt-0 sm:mt-14 ${className}`.trim()}>
      {inner}
    </section>
  );
}

export function SectionHeading({
  children,
  eyebrow,
  as = "h2",
}: {
  children: ReactNode;
  eyebrow?: string;
  as?: "h2" | "h3";
}) {
  const Comp = as;
  return (
    <div className="mb-5 max-w-3xl">
      {eyebrow ? (
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-ink-400">{eyebrow}</p>
      ) : null}
      <Comp className="mt-1 text-xl font-semibold tracking-tight text-ink-950 sm:text-2xl">{children}</Comp>
    </div>
  );
}

/** Scan-friendly one-liner + optional children. */
export function IntroBlock({ kicker, children }: { kicker?: ReactNode; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-lineWarm bg-surface-card-warm/92 p-5 shadow-sm ring-1 ring-ink-900/[0.05] sm:p-6">
      {kicker ? <p className="text-sm font-medium text-ink-800">{kicker}</p> : null}
      <div className={kicker ? "mt-2 text-base leading-relaxed text-ink-600" : "text-base leading-relaxed text-ink-600"}>
        {children}
      </div>
    </div>
  );
}

/** Narrow column for long explanatory copy inside a wide shell. */
export function ProseColumn({ children }: { children: ReactNode }) {
  return <div className="max-w-3xl space-y-6 text-base leading-relaxed text-ink-700">{children}</div>;
}

export function SummaryRow({ children }: { children: ReactNode }) {
  return <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:gap-5">{children}</div>;
}

export function SummaryCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="min-w-0 flex-1 rounded-2xl border border-lineSubtle bg-surface-card-warm/93 px-4 py-4 shadow-sm ring-1 ring-ink-900/[0.05] sm:min-w-[200px] sm:px-5 sm:py-5">
      <h3 className="text-sm font-semibold text-ink-950">{title}</h3>
      <div className="mt-2 text-sm leading-relaxed text-ink-600">{children}</div>
    </div>
  );
}

export function FeatureCard({ href, title, summary, accent }: { href: string; title: string; summary: string; accent: string }) {
  return (
    <Link
      href={href}
      className="group flex flex-col rounded-2xl border border-lineSubtle bg-surface-card-cool/94 p-5 shadow-sm ring-1 ring-ink-900/[0.04] transition hover:border-ink-300/40 hover:bg-surface-card hover:shadow-card"
    >
      <h3 className="text-base font-semibold tracking-tight text-ink-950 group-hover:text-ink-900">{title}</h3>
      <p className="mt-2 flex-1 text-sm leading-relaxed text-ink-600">{summary}</p>
      <p className="mt-4 border-t border-lineWarm/75 pt-3 text-xs leading-relaxed text-ink-500">{accent}</p>
    </Link>
  );
}

export function UseCaseCard({
  href,
  title,
  summary,
  accent,
  humanCheck,
}: {
  href: string;
  title: string;
  summary: string;
  accent: string;
  humanCheck: string;
}) {
  return (
    <Link
      href={href}
      className="group flex flex-col rounded-2xl border border-lineSubtle bg-surface-card-cool/94 p-5 shadow-sm ring-1 ring-ink-900/[0.04] transition hover:border-ink-300/40 hover:bg-surface-card hover:shadow-card"
    >
      <h3 className="text-base font-semibold tracking-tight text-ink-950">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-ink-600">{summary}</p>
      <p className="mt-3 text-xs font-medium text-ink-700">{accent}</p>
      <p className="mt-3 border-t border-lineWarm/75 pt-3 text-xs leading-relaxed text-ink-500">
        <span className="text-ink-400">Human role: </span>
        {humanCheck}
      </p>
    </Link>
  );
}

export function ComparisonCard({
  href,
  title,
  question,
  summary,
  accent,
}: {
  href: string;
  title: string;
  question: string;
  summary: string;
  accent: string;
}) {
  return (
    <Link
      href={href}
      className="group flex flex-col rounded-2xl border border-lineSubtle bg-surface-card-cool/94 p-5 shadow-sm ring-1 ring-ink-900/[0.04] transition hover:border-ink-300/40 hover:bg-surface-card hover:shadow-card"
    >
      <h3 className="text-base font-semibold tracking-tight text-ink-950">{title}</h3>
      <p className="mt-2 text-xs italic text-ink-500">“{question}”</p>
      <p className="mt-3 text-sm leading-relaxed text-ink-600">{summary}</p>
      <p className="mt-4 border-t border-lineWarm/75 pt-3 text-xs leading-relaxed text-ink-500">{accent}</p>
    </Link>
  );
}

export function AcademyCard({
  href,
  title,
  reader,
  summary,
  accent,
  outcome,
}: {
  href: string;
  title: string;
  reader: string;
  summary: string;
  accent: string;
  outcome: string;
}) {
  return (
    <Link
      href={href}
      className="group flex flex-col rounded-2xl border border-lineSubtle bg-surface-card-cool/94 p-5 shadow-sm ring-1 ring-ink-900/[0.04] transition hover:border-ink-300/40 hover:bg-surface-card hover:shadow-card"
    >
      <h3 className="text-base font-semibold tracking-tight text-ink-950">{title}</h3>
      <p className="mt-1 text-xs text-ink-500">For {reader}</p>
      <p className="mt-3 flex-1 text-sm leading-relaxed text-ink-600">{summary}</p>
      <p className="mt-3 rounded-lg border border-lineSubtle/60 bg-surface-card-warm/90 px-3 py-2 text-xs leading-relaxed text-ink-700">
        <span className="font-medium text-ink-800">You will learn: </span>
        {outcome}
      </p>
      <p className="mt-4 border-t border-lineWarm/75 pt-3 text-xs text-ink-500">{accent}</p>
    </Link>
  );
}

export function MethodologyCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-lineSubtle bg-surface-card-warm/90 p-5 shadow-sm ring-1 ring-ink-900/[0.05] sm:p-6">
      <h3 className="text-sm font-semibold text-ink-950">{title}</h3>
      <div className="mt-3 text-sm leading-relaxed text-ink-600">{children}</div>
    </div>
  );
}

export function PricingCard({
  name,
  badge,
  children,
  footnote,
  tint = "neutral",
}: {
  name: string;
  badge?: string;
  children: ReactNode;
  footnote?: ReactNode;
  /** Slight warm/cool split between tiers — still restrained. */
  tint?: "neutral" | "warm" | "cool";
}) {
  const shell =
    tint === "warm"
      ? "border-lineWarm bg-surface-card-warm/95 ring-1 ring-ink-900/[0.05]"
      : tint === "cool"
        ? "border-lineSubtle bg-surface-card-cool/95 ring-1 ring-ink-900/[0.05]"
        : "border-line bg-surface-card/95 ring-1 ring-ink-900/[0.04]";

  return (
    <div className={`flex flex-col rounded-2xl border p-6 shadow-sm sm:p-7 ${shell}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-lg font-semibold text-ink-950">{name}</h3>
        {badge ? (
          <span className="rounded-full border border-lineSubtle/90 bg-surface-card-cool/80 px-2.5 py-0.5 text-[11px] font-medium text-ink-700">
            {badge}
          </span>
        ) : null}
      </div>
      <div className="mt-5 flex-1 space-y-3 text-sm leading-relaxed text-ink-600">{children}</div>
      {footnote ? <div className="mt-5 border-t border-lineWarm/70 pt-4 text-xs text-ink-500">{footnote}</div> : null}
    </div>
  );
}

export function KeyPointsGrid({ items }: { items: { title: string; body: ReactNode }[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {items.map((it) => (
        <div key={it.title} className="rounded-xl border border-lineSubtle bg-surface-card-warm/80 px-4 py-4 shadow-sm ring-1 ring-ink-900/[0.04]">
          <h3 className="text-sm font-semibold text-ink-900">{it.title}</h3>
          <div className="mt-2 text-sm leading-relaxed text-ink-600">{it.body}</div>
        </div>
      ))}
    </div>
  );
}

export function CTASection({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-ink-950 px-5 py-6 text-center shadow-sm sm:px-8 sm:py-8">
      <div className="mx-auto max-w-xl text-sm leading-relaxed text-white/90">{children}</div>
    </div>
  );
}

export function StepRow({
  steps,
}: {
  steps: { step: string; title: string; text: string }[];
}) {
  return (
    <ol className="grid gap-4 sm:grid-cols-3">
      {steps.map((s, i) => (
        <li
          key={s.step}
          className={`relative rounded-2xl border p-4 shadow-sm ring-1 ring-ink-900/[0.04] sm:p-5 ${
            i % 2 === 0 ? "border-lineSubtle bg-surface-card-warm/78" : "border-lineSubtle bg-surface-card-cool/72"
          }`}
        >
          <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400">{s.step}</span>
          <p className="mt-2 text-sm font-semibold text-ink-950">{s.title}</p>
          <p className="mt-2 text-sm leading-relaxed text-ink-600">{s.text}</p>
        </li>
      ))}
    </ol>
  );
}

export function LinkRow({ links }: { links: { href: string; label: string }[] }) {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
      {links.map((l) => (
        <li key={l.href}>
          <Link href={l.href} className="font-medium text-ink-800 underline decoration-line/70 underline-offset-4 hover:text-ink-950">
            {l.label}
          </Link>
        </li>
      ))}
    </ul>
  );
}
