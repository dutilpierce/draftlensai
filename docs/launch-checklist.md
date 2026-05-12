# Launch checklist — DraftLens web (SEO)

## Pre-deploy

- [ ] Set **`NEXT_PUBLIC_SITE_URL`** to the canonical HTTPS origin (no trailing slash).
- [ ] Confirm **`NEXT_PUBLIC_API_URL`** and Stripe keys for production.
- [ ] Optional: `NEXT_PUBLIC_ORGANIZATION_LOGO_URL`, `NEXT_PUBLIC_CONTACT_EMAIL`.
- [ ] Optional: `GOOGLE_SITE_VERIFICATION`, `NEXT_PUBLIC_GA_MEASUREMENT_ID` **or** `NEXT_PUBLIC_GTM_ID` (not both GA + GTM unless intentional).
- [ ] Run from `apps/web`: `npm run validate-seo`, `npm run test:seo`, `npm run lint`, `npm run build`.
- [ ] From monorepo root: `npm run verify:web` (validates SEO tests + lint + build).

## Post-deploy

- [ ] Fetch `https://<your-domain>/robots.txt` — contains `Sitemap:` pointing to `https://<your-domain>/sitemap.xml`.
- [ ] Fetch `https://<your-domain>/sitemap.xml` — 30 URLs, all marketing paths (no `/app`).
- [ ] Spot-check `/` and `/product` — single canonical `<link rel="canonical">`, unique `<title>`, one visible `<h1>`.
- [ ] Confirm `/app` — `X-Robots-Tag` or meta robots `noindex` (Next `metadata.robots` on `app/app/layout.tsx`).

## Search Console

- [ ] Add property, verify (meta tag via `GOOGLE_SITE_VERIFICATION` or DNS).
- [ ] Submit sitemap URL (see `search-console-and-analytics-setup.md`).
- [ ] Request indexing for the first 10 URLs listed there.

## SEO QA (Lighthouse / CWV sanity)

- [ ] **Lighthouse** (mobile): run on `/`, `/product`, one long article (`/academy/...`). Targets: reasonable Performance (marketing is static), Accessibility best-practice passes, SEO category 95+.
- [ ] **CLS**: no layout shift on font load (Geist is `next/font` — good).
- [ ] **LCP**: hero text path should be fast; OG images are generated statically.
- [ ] **Indexing:** URL Inspection tool on `/` and `/compare/draftlens-vs-grammarly` after deploy.

## Content integrity

- [ ] No page claims numeric benchmark winners (framework page only until real data).
- [ ] Compare pages: no invented competitor pricing or feature lists — only workflow tradeoffs.

## Operational

- [ ] If `next build` fails with missing `app/page.js` after deleting routes: delete `apps/web/.next` and rebuild (stale typegen).
