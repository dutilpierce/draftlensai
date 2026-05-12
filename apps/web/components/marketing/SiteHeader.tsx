import Link from "next/link";
import { DraftLensLogo } from "@/components/brand/DraftLensLogo";

const nav = [
  { href: "/product", label: "Product" },
  { href: "/pricing", label: "Pricing" },
  { href: "/features", label: "Features" },
  { href: "/use-cases", label: "Use cases" },
  { href: "/compare", label: "Compare" },
  { href: "/academy", label: "Academy" },
  { href: "/research", label: "Research" },
] as const;

export default function SiteHeader() {
  return (
    <header className="border-b border-lineSubtle/75 bg-surface-card/90 backdrop-blur-sm">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div className="flex items-center gap-3">
          <Link href="/" className="focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink-800 rounded-sm">
            <DraftLensLogo size="sm" priority />
            <span className="sr-only">DraftLens home</span>
          </Link>
          <span className="hidden text-xs text-ink-400 sm:inline">Multi-model document review</span>
        </div>
        <nav aria-label="Primary" className="flex flex-wrap gap-x-4 gap-y-2 text-xs font-medium text-ink-600">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="hover:text-ink-950 underline decoration-transparent underline-offset-4 hover:decoration-ink-300"
            >
              {item.label}
            </Link>
          ))}
          <Link
            href="/app"
            className="rounded-full bg-ink-900 px-3 py-1 text-xs font-medium text-white hover:bg-ink-800"
          >
            Open app
          </Link>
        </nav>
      </div>
    </header>
  );
}
