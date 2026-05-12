import type { ReactNode } from "react";
import Link from "next/link";
import { DraftLensLogo } from "@/components/brand/DraftLensLogo";
import type { RegisteredPage } from "@/lib/seo/types";
import {
  JsonLd,
  articleJsonLd,
  breadcrumbJsonLd,
  organizationJsonLd,
  softwareApplicationJsonLd,
  websiteJsonLd,
} from "@/lib/seo/jsonld";

function Breadcrumbs({ items }: { items: { name: string; href: string }[] }) {
  return (
    <nav aria-label="Breadcrumb" className="text-xs text-ink-500">
      <ol className="flex flex-wrap items-center gap-1.5">
        {items.map((it, i) => (
          <li key={`${i}-${it.name}`} className="flex items-center gap-1.5">
            {i > 0 ? <span className="text-ink-300">/</span> : null}
            {i === items.length - 1 ? (
              <span className="font-medium text-ink-800">{it.name}</span>
            ) : (
              <Link href={it.href} className="hover:text-ink-900 underline decoration-line/80 underline-offset-2">
                {it.name}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

function RelatedPages({ links }: { links: { href: string; label: string }[] }) {
  if (!links.length) return null;
  return (
    <aside className="mt-16 rounded-2xl border border-lineWarm/80 bg-surface-card-warm/88 p-5 shadow-sm sm:p-6">
      <h2 className="text-[11px] font-medium uppercase tracking-[0.16em] text-ink-400">Related</h2>
      <ul className="mt-4 grid gap-2 sm:grid-cols-2">
        {links.map((l) => (
          <li key={l.href}>
            <Link
              href={l.href}
              className="text-sm font-medium text-ink-700 underline decoration-line/80 underline-offset-4 hover:text-ink-950"
            >
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </aside>
  );
}

export type PublicPageLayout = "canvas" | "reading";

export function PublicPageShell({
  page,
  children,
  layout = "canvas",
  /** When set, replaces the default registry description panel under the H1 (e.g. home hero). */
  descriptionOverride,
}: {
  page: RegisteredPage;
  children: ReactNode;
  layout?: PublicPageLayout;
  descriptionOverride?: ReactNode;
}) {
  const scripts: ReactNode[] = [];
  scripts.push(<JsonLd key="bc" data={breadcrumbJsonLd(page.breadcrumb)} />);

  if (page.schemaProfile === "home") {
    scripts.push(<JsonLd key="org" data={organizationJsonLd()} />);
    scripts.push(<JsonLd key="web" data={websiteJsonLd()} />);
  }
  if (page.schemaProfile === "software") {
    scripts.push(<JsonLd key="sw" data={softwareApplicationJsonLd()} />);
    scripts.push(<JsonLd key="org" data={organizationJsonLd()} />);
  }
  if (page.schemaProfile === "article") {
    scripts.push(
      <JsonLd
        key="art"
        data={articleJsonLd({
          headline: page.h1,
          description: page.description,
          path: page.path,
          datePublished: page.lastModified,
          dateModified: page.lastModified,
        })}
      />,
    );
    scripts.push(<JsonLd key="org" data={organizationJsonLd()} />);
  }
  if (page.schemaProfile === "standard") {
    scripts.push(<JsonLd key="org" data={organizationJsonLd()} />);
  }

  const maxW = layout === "reading" ? "max-w-3xl" : "max-w-5xl";

  return (
    <>
      {scripts}
      <article className={`mx-auto ${maxW} px-5 py-12 sm:px-6 sm:py-16`}>
        <Breadcrumbs items={page.breadcrumb} />
        <header className="mt-8 space-y-5">
          <DraftLensLogo size="sm" />
          <h1 className="text-3xl font-semibold tracking-tight text-ink-950 sm:text-[2.35rem] sm:leading-tight">{page.h1}</h1>
          {descriptionOverride ?? (
            <div className="rounded-2xl border border-lineSubtle/88 bg-surface-card-cool/82 p-5 shadow-sm sm:p-6">
              <p className="text-base leading-relaxed text-ink-600">{page.description}</p>
            </div>
          )}
          {page.lastModified ? <p className="text-xs text-ink-400">Last updated {page.lastModified}</p> : null}
        </header>
        <div className="mt-12 space-y-6 text-base leading-relaxed text-ink-700 [&_h2]:mt-0 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-ink-950 [&_h3]:mt-0 [&_h3]:text-lg [&_h3]:font-semibold [&_h3]:text-ink-900 [&_ul]:mt-3 [&_ul]:list-disc [&_ul]:pl-5 [&_li]:mt-1.5 [&_a]:text-ink-900 [&_a]:underline [&_a]:decoration-line [&_a]:underline-offset-4 [&_table]:mt-4 [&_table]:w-full [&_table]:text-sm [&_th]:border [&_th]:border-lineSubtle [&_th]:bg-surface-card-cool/90 [&_th]:px-3 [&_th]:py-2 [&_th]:text-left [&_td]:border [&_td]:border-lineSubtle [&_td]:px-3 [&_td]:py-2">
          {children}
        </div>
        <RelatedPages links={page.related} />
      </article>
    </>
  );
}
