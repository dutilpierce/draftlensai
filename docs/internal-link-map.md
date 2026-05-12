# Internal link map (DraftLens)

Goal: every **indexable** URL in `PAGE_REGISTRY` receives contextual links from nav, footer, in-body `<a>` / `Link`, and the **Related** module in `PublicPageShell`.

## Global chrome

| Source | Targets |
|--------|---------|
| `SiteHeader` | `/product`, `/pricing`, `/features`, `/use-cases`, `/compare`, `/academy`, `/research`, **`/app`** (CTA) |
| `SiteFooter` | Product column: `/product`, `/features`, `/pricing`, `/methodology`, `/app` — Learn: `/use-cases`, `/academy`, `/compare`, `/research`, `/editorial-policy` — Company: `/about`, `/contact` |

## Cluster map (keyword families ↔ supporting pages)

### A — Brand + commercial core

| Money page | Supported by |
|------------|----------------|
| `/` | In-body → `/product`, `/features`, `/pricing`, `/use-cases`, `/compare`, `/app` |
| `/product` | Related → `/pricing`, `/features`, `/methodology` |
| `/pricing` | Related → `/product`, `/app` |
| `/methodology` | Cross-links to `/editorial-policy`, `/research/benchmark-methodology` (in copy + related where configured) |

### B — Features (multi-model spine)

| Page | Role |
|------|------|
| `/features` | Hub: `FeaturesHubBody` renders `FEATURE_INDEX_ITEMS` as `FeatureCard` links to all five detail URLs. |
| `/features/*` | Detail pages; breadcrumbs `Home → Features → …` (Features → `/features`). |

| Detail page | Typical links |
|---------------|---------------|
| `/features/multi-model-review` | Related registry + body links to comparisons / use cases |
| Other feature pages | Adjacent features, `/pricing`, `/use-cases/*` where relevant |

### C — Use cases (vertical intent)

| Hub `/use-cases` | Lists all five leaves + links back to `/product`, `/app` |
| Leaves | Each links to relevant **features**, **compare**, and **`/app`** |

### D — Compare (consideration)

| Hub `/compare` | Four comparison leaves + `/product` |
| Each compare page | `/pricing`, `/features/*`, `/academy/*`, honest “when DraftLens fits” |

### E — Academy (informational / citations)

| Hub `/academy` | Three articles + `/editorial-policy`, `/methodology` |
| Articles | Cross-link compare + features + `/research` where appropriate |

### F — Research + trust

| Hub `/research` | `/research/benchmark-methodology`, `/research/ai-document-review-benchmark`, `/editorial-policy` |
| Methodology + benchmark framework | Each other + `/product` |

## Orphan check

There is **no** indexable route in `PAGE_REGISTRY` without: (1) header/footer path, (2) `related` array on the `RegisteredPage`, and/or (3) inline links in `wave1-bodies.tsx`. New pages must repeat this pattern.
