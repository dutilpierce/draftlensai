import { HomeBody } from "@/components/marketing/wave1-bodies";
import { PublicPageShell } from "@/components/marketing/PublicPageShell";
import { publicMetadata } from "@/lib/seo/metadata-factory";
import { PAGE_REGISTRY } from "@/lib/seo/registry";

const page = PAGE_REGISTRY["/"]!;

export const metadata = publicMetadata(page);

export default function MarketingHomePage() {
  return (
    <PublicPageShell
      page={page}
      descriptionOverride={
        <div className="space-y-4">
          <p className="text-lg font-medium leading-snug text-ink-900 sm:text-xl">
            Multi-model review for serious <strong>DOCX</strong> or <strong>PDF</strong> manuscripts—structured findings,
            optional convergence, and clear partial review when models disagree.
          </p>
          <div className="rounded-2xl border border-lineSubtle/85 bg-surface-card-cool/80 p-5 shadow-sm sm:p-6">
            <p className="text-base leading-relaxed text-ink-600">{page.description}</p>
          </div>
        </div>
      }
    >
      <HomeBody />
    </PublicPageShell>
  );
}
