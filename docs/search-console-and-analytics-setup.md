# Google Search Console & analytics setup

## Search Console

1. **Add property** — Domain property (preferred) or URL-prefix property matching `NEXT_PUBLIC_SITE_URL` exactly.
2. **Verify**
   - **HTML tag:** set `GOOGLE_SITE_VERIFICATION` in the deployment environment. `apps/web/app/layout.tsx` passes it to Next `metadata.verification.google` when present.
   - Or verify via DNS / GA linkage per Google’s UI.
3. **Submit sitemap:** `https://<YOUR_DOMAIN>/sitemap.xml` (built from `app/sitemap.ts`).
4. **Request indexing (first 10 URLs)** — use URL Inspection → “Request indexing” after deploy:
   1. `https://<YOUR_DOMAIN>/`
   2. `https://<YOUR_DOMAIN>/product`
   3. `https://<YOUR_DOMAIN>/pricing`
   4. `https://<YOUR_DOMAIN>/features/multi-model-review`
   5. `https://<YOUR_DOMAIN>/use-cases`
   6. `https://<YOUR_DOMAIN>/compare`
   7. `https://<YOUR_DOMAIN>/academy`
   8. `https://<YOUR_DOMAIN>/research`
   9. `https://<YOUR_DOMAIN>/methodology`
   10. `https://<YOUR_DOMAIN>/compare/draftlens-vs-grammarly`

## Performance reports (weekly rhythm)

| Report | What to look for |
|--------|------------------|
| **Search results → Queries** | Impressions, clicks, CTR, position — sort by impressions to find demand. |
| **Pages** | Same metrics per URL — spot thin CTR on high-impression pages. |
| **Indexing → Pages** | Excluded vs indexed; fix soft-404s or accidental noindex. |

### Impressions but weak CTR

- Compare query intent in Search Console to the **title + description** on that URL (both come from `PAGE_REGISTRY`).
- Rewrite meta to match the dominant query phrasing **without** clickbait; keep H1 aligned with the title’s promise.

### Positions roughly 8–25 (“striking distance”)

- Expand the on-page answer in the first screen, add a concise FAQ-style **visible** section (no FAQ schema) if it genuinely helps users.
- Strengthen internal links from hubs (`/use-cases`, `/compare`, `/academy`) to that page.

### Updating titles / meta from data

1. Export top queries per page (last 28 days).
2. Group by intent (tool vs how-to vs vs-competitor).
3. Adjust **only** `title` and `description` in `lib/seo/registry.ts` for that path; re-run `npm run validate-seo`.

## Google Analytics 4 or GTM

- **GA4 only:** set `NEXT_PUBLIC_GA_MEASUREMENT_ID` — `app/layout.tsx` loads `gtag.js` when this is set and GTM is **not** set.
- **GTM:** set `NEXT_PUBLIC_GTM_ID` — takes precedence over direct GA4 snippet (avoid double-counting unless you configure GTM to forward to GA4 intentionally).
- Missing env vars **do not** break the build; scripts simply omit tags.

## Privacy / compliance note

Document your cookie/consent posture if you enable GTM with non-essential tags in the EU/UK; this repo does not ship a CMP.
