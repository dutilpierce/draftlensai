import { FeedbackForm } from "@/components/marketing/FeedbackForm";
import { IntroBlock } from "@/components/marketing/MarketingUi";

export function FeedbackPageBody() {
  return (
    <>
      <IntroBlock>
        <p>
          The product is moving quickly. Whether you need a new capability, clearer copy in the app, or support for a
          document type we have not prioritized yet, your specifics matter—real examples beat abstract wishlists.
        </p>
      </IntroBlock>

      <div className="mt-10 rounded-2xl border border-lineSubtle/85 bg-surface-card-warm/90 p-6 shadow-sm sm:p-8">
        <h2 className="text-lg font-semibold text-ink-950">Your note</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-600">
          A few fields keep things actionable for the team. Nothing here replaces security review or legal intake—use{" "}
          <a href="/contact">Contact</a> when that is what you need.
        </p>
        <div className="mt-8">
          <FeedbackForm />
        </div>
      </div>
    </>
  );
}
