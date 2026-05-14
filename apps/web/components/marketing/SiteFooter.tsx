import Link from "next/link";
import { DraftLensLogo } from "@/components/brand/DraftLensLogo";

const footerCols = [
  {
    title: "Product",
    links: [
      { href: "/product", label: "Overview" },
      { href: "/features", label: "Features" },
      { href: "/pricing", label: "Pricing" },
      { href: "/methodology", label: "Methodology" },
      { href: "/app", label: "Run a review" },
    ],
  },
  {
    title: "Learn",
    links: [
      { href: "/use-cases", label: "Use cases" },
      { href: "/academy", label: "Academy" },
      { href: "/compare", label: "Compare" },
      { href: "/research", label: "Research" },
      { href: "/editorial-policy", label: "Editorial policy" },
    ],
  },
  {
    title: "Trust",
    links: [
      { href: "/privacy", label: "Privacy" },
      { href: "/terms", label: "Terms" },
      { href: "/data-security", label: "Data security" },
    ],
  },
  {
    title: "Company",
    links: [
      { href: "/about", label: "About" },
      { href: "/contact", label: "Contact" },
      { href: "/feedback", label: "Feedback" },
    ],
  },
] as const;

export default function SiteFooter() {
  return (
    <footer className="border-t border-lineWarm/70 bg-surface-card-warm/92">
      <div className="mx-auto max-w-5xl px-5 pb-6 pt-12 sm:px-6">
        <Link
          href="/"
          className="inline-flex focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink-800 rounded-sm"
        >
          <DraftLensLogo size="sm" />
          <span className="sr-only">DraftLens home</span>
        </Link>
      </div>
      <div className="mx-auto grid max-w-5xl gap-8 px-5 pb-12 sm:grid-cols-2 lg:grid-cols-4 sm:px-6">
        {footerCols.map((col) => (
          <div key={col.title}>
            <h2 className="text-xs font-medium uppercase tracking-[0.16em] text-ink-400">{col.title}</h2>
            <ul className="mt-3 space-y-2">
              {col.links.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-sm text-ink-600 hover:text-ink-950 underline-offset-4 hover:underline">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-lineSubtle/80 py-4 text-center text-[11px] text-ink-400">
        © {new Date().getFullYear()} DraftLens · AI-assisted review — verify important facts before relying on results.
      </div>
    </footer>
  );
}
