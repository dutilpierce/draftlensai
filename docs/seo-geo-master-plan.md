# DraftLens SEO + GEO master plan

This document describes the **implemented** production SEO and retrieval-friendly (GEO) architecture for DraftLens. It is scoped to the Next.js app in `apps/web`; the FastAPI service in `apps/api` is unchanged.

## Phase 0 — Audit summary

| Question | Finding |
|----------|---------|
| Where does the product live? | **`/app`** — client UI in `apps/web/app/app/page.tsx` (upload, jobs, billing controls). |
| Where is marketing? | **`/`** and routes under `apps/web/app/(public)/` — server-rendered pages with `PublicPageShell`. |
| Homepage role | **`/`** is the public marketing home; the tool is not the default route anymore. |
| Metadata / canonicals | Per-route `export const metadata` from `publicMetadata()` in `lib/seo/metadata-factory.ts`, driven by `PAGE_REGISTRY` in `lib/seo/registry.ts`. |
| Sitemap | `apps/web/app/sitemap.ts` — one entry per key in `PAGE_REGISTRY` (sorted `INDEXABLE_PATHS`). |
| Robots | `apps/web/app/robots.ts` — allows `/`, disallows `/app`, references `${getSiteUrl()}/sitemap.xml`. |
| JSON-LD | `lib/seo/jsonld.tsx` + `PublicPageShell` — `WebSite` + `Organization` on home; `SoftwareApplication` on `/product`; `Article` on academy/research article-profile pages; `BreadcrumbList` everywhere. |
| What is indexable? | All paths in `PAGE_REGISTRY` (30 Wave-1 marketing URLs). |
| What is noindex? | **`/app`** via `apps/web/app/app/layout.tsx` (`robots: { index: false, follow: true }`). Billing success is a query param on `/app`, not a separate route. |
| Reused vs replaced | Product logic preserved; former root `app/page.tsx` removed so `/` resolves only to `(public)/page.tsx`. |

## Information architecture

- **Marketing (indexable):** `(public)/**` — corporate, features, use cases, compare, academy, research hubs and leaves.
- **Product (noindex):** `app/**` — full DOCX workflow unchanged.

## Technical SEO stack (files)

| Concern | Location |
|---------|----------|
| Site URL + brand placeholders | `lib/seo/site.ts` (`getSiteUrl`, `absoluteUrl`, `BRAND`) |
| Typed page definitions | `lib/seo/types.ts`, `lib/seo/registry.ts` |
| Metadata factory | `lib/seo/metadata-factory.ts` |
| JSON-LD builders | `lib/seo/jsonld.tsx` |
| UI shell (H1, intro, breadcrumbs, related, JSON-LD) | `components/marketing/PublicPageShell.tsx` |
| Copy bodies | `components/marketing/wave1-bodies.tsx` |
| Global metadata + analytics hooks | `app/layout.tsx` |
| OG / Twitter default images | `app/opengraph-image.tsx`, `app/twitter-image.tsx` |
| Validation | `npm run validate-seo`, `npm run test:seo` |
| Lint (Next 16 has no `next lint` CLI) | `eslint.config.mjs`, `npm run lint` |

## Canonical and URL rules

- **Preferred origin:** `NEXT_PUBLIC_SITE_URL` (no trailing slash). Fallback in code: `https://draftlens.app` for local tooling only; production must set the env var.
- **Trailing slashes:** `next.config.ts` sets `trailingSlash: false`.
- **Query strings:** `publicMetadata()` uses `canonicalPath` without query or hash.

## GEO (retrieval-friendly content)

Implemented as **visible HTML structure**, not hidden meta tricks:

- Answer-first intros and definition-style openings in `wave1-bodies.tsx`.
- “Best for / limitations” style honesty on product, compare, and research pages.
- Research benchmark page is explicitly a **framework** page — no fabricated numeric vendor scores.

## Governance

- New indexable routes must add a `RegisteredPage` to `PAGE_REGISTRY` and a matching `app/(public)/.../page.tsx`.
- Run `npm run validate-seo` before release; CI can use `npm run verify:web` from the monorepo root.

## Human follow-ups

1. Set **`NEXT_PUBLIC_SITE_URL`** to the live canonical HTTPS origin.
2. Optionally set **`NEXT_PUBLIC_ORGANIZATION_LOGO_URL`**, **`NEXT_PUBLIC_CONTACT_EMAIL`**, **`GOOGLE_SITE_VERIFICATION`**, **`NEXT_PUBLIC_GA_MEASUREMENT_ID`** or **`NEXT_PUBLIC_GTM_ID`**.
3. Replace placeholder OG art if brand design finalizes.
4. Add real product screenshots under `apps/web/public/` when assets exist; reference them from bodies with descriptive `alt` text.
