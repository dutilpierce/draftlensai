# DraftLens

**Multi-model document review** — Next.js frontend, FastAPI backend, LangGraph pipeline, SQLite, Stripe (hosted Checkout + Customer Portal + webhooks).

## Source layout (essentials)

```
draftlens/
├── README.md
├── prompts/                    # Markdown prompt sources (reference)
│   ├── arbiter.md
│   ├── claude_author_intent_reviewer.md
│   ├── gemini_consistency_reviewer.md
│   ├── gpt_skeptical_reviewer.md
│   └── supervisor.md
├── apps/
│   ├── api/                    # FastAPI service
│   │   ├── pyproject.toml
│   │   ├── draftlens_api/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── db.py
│   │   │   ├── deps.py
│   │   │   ├── artifacts/
│   │   │   ├── domain/
│   │   │   ├── engine/         # LangGraph pipeline, dedupe, conflicts, debate, evidence
│   │   │   ├── evidence/
│   │   │   ├── persistence/
│   │   │   ├── policies/
│   │   │   ├── prompts/
│   │   │   ├── providers/
│   │   │   ├── routes/         # access, jobs, billing, disclaimers, health
│   │   │   ├── security/
│   │   │   ├── services/
│   │   │   ├── validation/
│   │   │   └── utils/
│   │   └── tests/              # pytest (unit + integration)
│   └── web/                    # Next.js app (single page journey)
│       ├── package.json
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── page.tsx        # sole core UI surface
│       │   └── globals.css
│       └── lib/
│           ├── api.ts
│           ├── pipelineStages.ts
│           └── sse.ts
└── .env.example                # (if present at repo root; else use apps/api/.env.example)
```

Dependency installs create `node_modules/`, `.venv/`, and build output (`.next/`) — omitted above.

## Install

**Backend** (`apps/api`):

```powershell
cd apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

**Frontend** (`apps/web`):

```powershell
cd apps\web
npm install
```

## Run commands

**API** (from `apps/api`, venv on):

```powershell
uvicorn draftlens_api.main:app --reload --host 127.0.0.1 --port 8000
```

**Web** (from `apps/web`):

```powershell
npm run dev
```

**Tests** (from `apps/api`):

```powershell
pytest tests/ -q
```

## Environment variables (exact names)

Copy from `.env.example` into `apps/api/.env` and `apps/web/.env.local` as applicable.

### API — `apps/api/.env`

| Variable | Required | Purpose |
|----------|----------|---------|
| `APP_SESSION_SECRET` | **Yes** (32+ chars) | Cookie signing (`DRAFTLENS_SECRET_KEY` alias) |
| `DRAFTLENS_ENVIRONMENT` | No | `development` recommended locally |
| `DRAFTLENS_DATA_DIR` | No | Data root (default `./data`) |
| `DRAFTLENS_DATABASE_URL` | No | SQLite URL (default `sqlite:///./data/draftlens.db`) |
| `OPENAI_API_KEY` | For OpenAI models | Chat Completions JSON |
| `ANTHROPIC_API_KEY` | For Anthropic models | Messages API |
| `GOOGLE_API_KEY` or `GEMINI_API_KEY` | For Gemini | `generativelanguage.googleapis.com` |

#### Gemini (third reviewer)

| Variable | Purpose |
|----------|---------|
| `DRAFTLENS_GEMINI_MODEL` | Override Gemini **API** model id for the consistency reviewer (e.g. `gemini-3.1-flash-lite` or `google/gemini-3.1-flash-lite`). Default routing uses Flash Lite in `MODEL_ROUTING_JSON` / app defaults. |
| `DRAFTLENS_GEMINI_FALLBACK_MODEL` | Optional fallback model id (no `google/` prefix) used only after empty candidates or 404 on the primary, same job. |
| `DRAFTLENS_GEMINI_MAX_429_RETRIES` | Per-job budget of Gemini HTTP 429 responses to absorb before **circuit-open** (no more Gemini calls that job). In `development`/`dev`/`local`/`test`, the effective budget is capped at **2** unless this env var is set explicitly. Production default from settings: **8**. |
| `DRAFTLENS_GEMINI_MAX_BACKOFF_SECONDS` | Max **single** sleep between 429 retries (exponential backoff is capped at this). In dev-like environments, capped at **5s** unless this env var is set explicitly. Production default: **90** (only used when not overridden). |
| `DRAFTLENS_DISABLE_GEMINI` | If `true`, Gemini is excluded for the job (`INTENTIONALLY_DISABLED`); not treated as a provider failure. |
| `DRAFTLENS_GEMINI_DISABLE_IN_DEV` | Same as above when `DRAFTLENS_ENVIRONMENT` is development-like. |

**Recommended local values:** `DRAFTLENS_GEMINI_MODEL=gemini-3.1-flash-lite`, `DRAFTLENS_GEMINI_MAX_429_RETRIES=2`, `DRAFTLENS_GEMINI_MAX_BACKOFF_SECONDS=5`, `DRAFTLENS_DISABLE_GEMINI=false`.

| `MODEL_ROUTING_JSON` or `DRAFTLENS_MODEL_ROUTING_JSON` | No | Per-agent model refs (`provider/model`) |
| `FREE_MONTHLY_PROOFS` | No | Free tier completed jobs / month (default `1`) |
| `FREE_MAX_PAGES` / `DRAFTLENS_FREE_MAX_PAGES` | No | Free page cap |
| `DRAFTLENS_PRO_MAX_PAGES` | No | Pro page cap |
| `PRO_FAIR_USE_DOCS_PER_MONTH` / `DRAFTLENS_PRO_MONTHLY_DOC_CAP` | No | Pro fair-use cap |
| `DRAFTLENS_FREE_MAX_REVIEW_BLOCKS` | No | Free chunk cap for large docs |
| `DRAFTLENS_PRO_MAX_REVIEW_BLOCKS` | No | Pro chunk cap (`0` = uncapped) |
| `DATA_RETENTION_HOURS_DEFAULT` / `DRAFTLENS_DEFAULT_RETENTION_HOURS` | No | Default retention window |
| `DATA_RETENTION_HOURS_SENSITIVE` / `DRAFTLENS_SENSITIVE_RETENTION_HOURS` | No | Sensitive-mode retention |
| `DRAFTLENS_RETENTION_SWEEP_SECONDS` | No | Background sweep interval |
| `STRIPE_SECRET_KEY` | For billing | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | For webhooks | `whsec_…` |
| `STRIPE_PRICE_ID_PRO_MONTHLY` | For Checkout | Recurring Price id |
| `NEXT_PUBLIC_APP_URL` / `DRAFTLENS_PUBLIC_APP_URL` | Recommended | Public origin for redirects |
| `STRIPE_SUCCESS_URL` / `STRIPE_CANCEL_URL` | No | Override Checkout return URLs |
| `DRAFTLENS_CORS_ORIGINS` | No | API CORS allowlist |

### Web — `apps/web/.env.local`

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | API base URL, e.g. `http://127.0.0.1:8000` |
| `NEXT_PUBLIC_APP_URL` | Browser origin for billing redirects when needed |

## Sample local end-to-end test flow

1. Set `APP_SESSION_SECRET`, at least **two** provider keys, and point `NEXT_PUBLIC_API_URL` at the API.
2. Start API (`uvicorn …`) and web (`npm run dev`).
3. Open the app → enter email → **Continue** (session + entitlements).
4. Drop a `.docx` → optionally open **Options** (context, review focus, do-not-change, supporting if Pro, sensitive mode).
5. Choose **Review** or **Fix** (Pro only for Fix) → **Run**.
6. Watch **Status** (SSE): multi-model review → bounded debate when conflicts exist → arbiter → render/export.
7. In **Summary**, confirm stats and **Download** links; confirm retention line when applicable.
8. **Pro:** `stripe listen --forward-to 127.0.0.1:8000/api/billing/webhook`, set `STRIPE_WEBHOOK_SECRET`, use **Upgrade** → complete Checkout → return with `?billing=success` → entitlements refresh; **Manage billing** opens Stripe Portal.

## Product checklist (MVP)

| Capability | Where |
|-------------|--------|
| Name + subtitle | `apps/web/app/layout.tsx` metadata; `page.tsx` header |
| Single core page | `apps/web/app/page.tsx` only |
| Two output modes | `review` · `fix` (API + UI) |
| Multiple providers | `draftlens_api/routing/model_registry.py` + adapters |
| Bounded cross-model debate | `engine/langgraph_review_graph.py` (`max_debate_rounds`) |
| Arbitration | Same graph + `engine/arbitration_engine.py` |
| Evidence-aware review | `evidence/`, `engine/pipeline_evidence.py`, graph nodes |
| Context field | Job form `context_text` |
| Do-not-change field | Job form `do_not_change` |
| Supporting files (Pro) | Entitlements + uploads |
| Subtle disclaimers | `artifacts/disclaimers.py` + `GET /api/disclaimers` + UI pulls copy |
| Stripe hosted Checkout + Portal | `routes/billing.py`, `services/billing_service.py` |
| Status streaming | `GET /api/jobs/{id}/events` (SSE) |
| Artifact downloads | `GET /api/jobs/{id}/artifacts/download` |
| Retention policy | `policies/central.py`, `services/retention_service.py`, job `retention_until` |
| Sensitive mode | Job flag + shorter retention |

## Known limitations (concise)

- Main manuscript is **DOCX-only** in v1.
- Supporting files are **evidence-only**; PDF is supported there, not as main.
- Native Word **Track Changes** is not guaranteed.
- No **team** workspaces or shared accounts.
- No **full auth** (email session cookie only).
- Pipeline needs **≥2 configured providers** for live quorum (`execute_review_pipeline`).

## v2 roadmap

- **Main PDF** as first-class review input (with clear edit/review semantics).
- **True auth** (passwordless SSO, orgs, sessions).
- **Annual billing** and plan variety beyond monthly Pro.
- **Coupons** and promotional pricing in Stripe.
- **Team plans** (seats, shared billing, admin roles).
- **Collaborative sharing** (links, comments, review handoff).
- **Evidence libraries** (reusable corpora, not just per-job uploads).
- **Deeper style guides** (voice, house style packs, terminology).
- **Usage analytics** (dashboards, exports, anomaly hints).

## License

Proprietary — DraftLens MVP scaffold.
