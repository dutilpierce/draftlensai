import Link from "next/link";

/**
 * Single prominent, calm band for marketing pages — links to `/feedback` for structured input.
 * Keeps copy in HTML for crawlability; not a client island.
 */
export function FeedbackRequestSection() {
  return (
    <section
      id="feedback"
      aria-labelledby="feedback-heading"
      className="mt-14 scroll-mt-10 border-t border-lineWarm/65 pt-12 sm:mt-16 sm:pt-14"
    >
      <div className="rounded-2xl border border-lineSubtle/85 bg-surface-band-sage/35 px-6 py-8 shadow-sm sm:px-9 sm:py-10">
        <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-ink-400">Product input</p>
        <h2 id="feedback-heading" className="mt-2 text-xl font-semibold tracking-tight text-ink-950 sm:text-2xl">
          Need a feature? Tell us what&apos;s missing.
        </h2>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink-600 sm:text-[15px]">
          DraftLens is evolving quickly. Feature ideas, workflow pain points, and real document examples help us decide
          what ships next—whether something confused you, feels incomplete, or would make your review process calmer.
        </p>
        <p className="mt-3 max-w-2xl text-sm text-ink-500">
          Request a capability, describe a document type we should support better, or spell out what would make DraftLens
          more useful day to day. Optional contact if you&apos;d like a reply.
        </p>
        <div className="mt-7">
          <Link
            href="/feedback"
            className="inline-flex items-center justify-center rounded-full border border-ink-800/15 bg-ink-950 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-ink-900"
          >
            Share feedback or request a feature
          </Link>
        </div>
      </div>
    </section>
  );
}

/** Alias for discoverability in design docs / imports. */
export const FeatureRequestCTA = FeedbackRequestSection;
export const ProductFeedbackCard = FeedbackRequestSection;
