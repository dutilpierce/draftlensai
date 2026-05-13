# Google Drive setup for DraftLens

This checklist configures **Google Identity Services (GIS)** access tokens, the **Google Picker** UI, and **Drive API** calls used when users import files from Drive and save completed artifacts back as **new** files (no in-place editing of the original).

DraftLens uses scope **`https://www.googleapis.com/auth/drive.file`** (“Per-file access to files created or opened by the app”). Tokens are obtained in the browser; the API never stores refresh tokens for Google.

---

## 1. Google Cloud project

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Select an existing project or **Create project**.
3. Note the **Project ID** (for your own records).

---

## 2. Enable APIs

1. **APIs & Services → Library**.
2. Enable:
   - **Google Drive API**
   - **Google Picker API** (Picker UI)

---

## 3. OAuth consent screen

1. **APIs & Services → OAuth consent screen**.
2. Choose **External** (unless you are on a Workspace org-only internal app).
3. Fill **App name**, **User support email**, **Developer contact**.
4. **Scopes → Add or remove scopes** → add:
   - `https://www.googleapis.com/auth/drive.file`
5. If the app is in **Testing**, add every tester Google account under **Test users**.

---

## 4. OAuth 2.0 Client ID (Web application)

1. **APIs & Services → Credentials → Create credentials → OAuth client ID**.
2. Application type: **Web application**.
3. **Authorized JavaScript origins** — add every browser origin that will load `/app` (no path, no trailing slash):

| Environment | Example origin |
|-------------|----------------|
| Local Next.js | `http://localhost:3000` |
| Production | `https://www.draftlensai.com` |
| Apex (if used) | `https://draftlensai.com` |
| Vercel preview | `https://your-deployment.vercel.app` (add each stable preview URL you use, or a wildcard is **not** supported—add previews as needed) |

4. **Authorized redirect URIs** — for the current DraftLens Google flow (**GIS token client + Picker**), Google typically does **not** require redirect URIs the way a server authorization-code flow does. You may leave this list empty unless you add a future server-side OAuth flow.  
   - **Dropbox / Microsoft** in the same app use redirect `https://www.draftlensai.com/app` (and local `http://localhost:3000/app`) — those are documented in `docs/cloud-file-integration.md`, not Google GIS.

5. Save. Copy the **Client ID** (ends with `.apps.googleusercontent.com`).

---

## 5. API key (Picker “developer key”)

1. **Credentials → Create credentials → API key**.
2. **Restrict key** (recommended):
   - **Application restrictions**: HTTP referrers (web sites).
   - **Website restrictions** — add referrers matching your deployed app (path wildcards allowed):

```
https://www.draftlensai.com/*
https://draftlensai.com/*
https://*.vercel.app/*
http://localhost:3000/*
```

   - **API restrictions**: Restrict to **Google Picker API** (and ensure Drive API is allowed for the OAuth client usage; the key is mainly for Picker).

3. Copy the **API key** string.

---

## 6. Environment variables

### API (`apps/api/.env` or Vercel **server** env for the API service)

| Variable | Value |
|----------|--------|
| `DRAFTLENS_GOOGLE_CLIENT_ID` | Web client ID from §4 |
| `DRAFTLENS_GOOGLE_PICKER_API_KEY` | API key from §5 (alias `GOOGLE_PICKER_API_KEY` also supported in code) |
| `DRAFTLENS_GOOGLE_CLIENT_SECRET` | Optional today — not used by GIS + Picker in-repo; leave empty or store for future server OAuth |
| `DRAFTLENS_API_PUBLIC_URL` | Public base URL of this API, e.g. `https://api.draftlensai.com` or your Vercel API URL |
| `DRAFTLENS_CORS_ORIGINS` | Comma-separated list of web origins allowed to call the API with cookies, e.g. `https://www.draftlensai.com,https://draftlensai.com` |

No Google secrets are required in the **Next.js** bundle beyond what `/api/cloud/config` already exposes (`google_client_id`, `google_picker_api_key`).

### Web (`apps/web/.env.local` or Vercel **frontend** env)

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | Same origin you use in the browser to reach FastAPI, e.g. `https://api.draftlensai.com` |
| `NEXT_PUBLIC_APP_URL` | Canonical **browser** origin for the Next app (used for Dropbox/OneDrive redirects), e.g. `https://www.draftlensai.com` — for local dev: `http://localhost:3000` |

---

## 7. Production checklist (`https://www.draftlensai.com`)

- [ ] OAuth Web client: JavaScript origins include `https://www.draftlensai.com` (and apex if you redirect it).
- [ ] Picker API key: referrer `https://www.draftlensai.com/*`.
- [ ] API deployment: `DRAFTLENS_GOOGLE_CLIENT_ID`, `DRAFTLENS_GOOGLE_PICKER_API_KEY`, `DRAFTLENS_API_PUBLIC_URL`, `DRAFTLENS_CORS_ORIGINS` set.
- [ ] `GET https://<api>/api/cloud/config` returns non-null `google_client_id` and `google_picker_api_key`.

---

## 8. Vercel preview checklist

For each preview URL you actually use (example: `https://draftlens-git-feature-foo.vercel.app`):

- [ ] Add that origin to **Authorized JavaScript origins**.
- [ ] Add `https://draftlens-git-feature-foo.vercel.app/*` to the Picker API key referrer allowlist.

Wildcard `https://*.vercel.app/*` on the API key covers many previews in one rule.

---

## 9. How to test

1. Deploy or run locally with env vars set; restart API and web.
2. Sign in to the app with email (**Continue**).
3. Click **Choose from Google Drive** → consent once → pick a **PDF** or **Word** file (or a **Google Doc**, which the API exports to DOCX on import).
4. Run a job; when complete, use **Save to Drive** on an artifact → confirm a new file appears in Drive and the success link opens.

If the Picker opens but files are greyed out, check **Drive API** enabled and Picker **API key** restrictions. If GIS errors appear, check **JavaScript origins** and **drive.file** scope on the consent screen.
