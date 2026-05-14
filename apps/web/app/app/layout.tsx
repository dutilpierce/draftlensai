import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import { DraftLensLogo } from "@/components/brand/DraftLensLogo";

export const metadata: Metadata = {
  title: "DraftLens App",
  robots: { index: false, follow: true },
};

export default function AppSectionLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-full">
      <div className="border-b border-line bg-white/90 px-5 py-3 sm:px-6">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <Link
            href="/"
            className="rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink-800"
          >
            <DraftLensLogo size="sm" priority />
            <span className="sr-only">DraftLens home page</span>
          </Link>
          <div className="text-right text-xs text-ink-500">
            <Link href="/" className="font-medium text-ink-800 underline-offset-4 hover:underline">
              ← Home page
            </Link>
            <span className="mx-2 text-ink-300">·</span>
            <span className="text-ink-400">App · not indexed for search</span>
          </div>
        </div>
      </div>
      {children}
      <div className="border-t border-line/80 bg-white/80 px-5 py-4 sm:px-6">
        <div className="mx-auto flex max-w-5xl flex-wrap justify-center gap-x-4 gap-y-2 text-center text-[11px] text-ink-500">
          <Link href="/privacy" className="hover:text-ink-900 underline-offset-4 hover:underline">
            Privacy
          </Link>
          <Link href="/terms" className="hover:text-ink-900 underline-offset-4 hover:underline">
            Terms
          </Link>
          <Link href="/data-security" className="hover:text-ink-900 underline-offset-4 hover:underline">
            Data security
          </Link>
          <Link href="/contact" className="hover:text-ink-900 underline-offset-4 hover:underline">
            Contact
          </Link>
        </div>
      </div>
    </div>
  );
}
