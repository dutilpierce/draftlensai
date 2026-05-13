# Cloud file integration (DraftLens)

This document describes how the **Next.js** app (`apps/web`) and **FastAPI** API (`apps/api`) work together for **Google Drive**, **Dropbox**, and **OneDrive**. Secrets stay on the API; the browser only receives **public** identifiers from `GET /api/cloud/config`.

---

## Architecture (v1)

1. **Import**: Browser obtains a **short-lived access token** (or temporary download URL for OneDrive). The browser calls **`POST /api/cloud/import`** with the token and file pointer. The API downloads bytes from the provider, stages them server-side, and returns an **`import_handle`** referenced by the job form as `main_cloud_import_handle` / supporting handles.

2. **Export**: After a job completes, the browser calls **`POST /api/cloud/export`** with the same kind of token. The API reads the artifact from disk and uploads it as a **new** remote file (renamed using `export_filename` in `draftlens_api/cloud/transfer.py`).

3. **Google**: OAuth uses **Google Identity Services** (`getGoogleAccessToken` in `apps/web/lib/cloudStorage.ts`) with scope `drive.file`. File choice uses **Google Picker** (`pickFromGoogleDrive`) with `DocsView` + `ViewId.DOCUMENTS` and MIME filters for PDF, Word, Google Docs, and text.

4. **Dropbox / Microsoft**: Browser uses **PKCE** (`startDropboxPkceOAuth`, `startMicrosoftPkceOAuth`) with redirect **`{window.location.origin}/app`** — must match app registration exactly. Tokens are kept in `sessionStorage` for the session.

---

## HTTP endpoints (FastAPI)

All routes are mounted under the API’s `/api` prefix (see `draftlens_api/main.py`).

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/cloud/config` | None | Returns public picker/OAuth ids and `api_public_url`. |
| `POST` | `/api/cloud/import` | Session cookie | Stage a remote file; body: `CloudImportBody`. |
| `POST` | `/api/cloud/export` | Session cookie | Upload job artifact; body: `CloudExportBody`. |
| `POST` | `/api/cloud/oauth/dropbox/token` | Session cookie | Exchange Dropbox auth `code` for access token (PKCE). |
| `POST` | `/api/cloud/oauth/microsoft/token` | Session cookie | Exchange Microsoft auth `code` for access token (PKCE). |

### `GET /api/cloud/config` (response)

```json
{
  "google_client_id": "…apps.googleusercontent.com",
  "google_picker_api_key": "…",
  "dropbox_app_key": "…",
  "microsoft_client_id": "…",
  "api_public_url": "https://…"
}
```

Nulls are allowed for unused providers.

### `POST /api/cloud/import` (request)

- **`request`**: `CloudImportRequest` (`draftlens_api/cloud/models.py`)
  - `provider`: `google_drive` | `dropbox` | `onedrive`
  - `provider_file_id`: Drive/Graph id (Google Drive required)
  - `shared_link`: Dropbox preview link when not using path id
  - `download_url`: OneDrive temporary `@microsoft.graph.downloadUrl` when present
  - `filename`, `mime_type` (optional), `document_role`: `main` | `supporting`
- **`access_token`**: Required for Google Drive; optional when Dropbox link is public or OneDrive provides `download_url`.

### `POST /api/cloud/import` (response)

- `import_handle`: opaque string for multipart job submission
- `reference`: `CloudFileReference` (filename, mime, provider, `provider_file_id`, role)

### `POST /api/cloud/export` (request)

- `job_id`: completed job UUID
- `request.provider`: same enum as import
- `request.artifact_name`: e.g. `reviewed.docx`
- `request.parent_folder_id`: optional (Drive folder / Graph parent)
- `access_token`: user token for the provider

### `POST /api/cloud/export` (response)

- `provider`, `remote_file_id`, `web_view_link` (Drive and OneDrive may return a link), `message`

---

## Google Docs and MIME types

- **Native Google Docs** (`application/vnd.google-apps.document`): API **exports** to DOCX on download (`transfer._google_drive_download`).
- **PDF / Word in Drive**: downloaded with `alt=media`.
- **Spreadsheet** native files: exported to XLSX (supporting workflows only if your pipeline accepts them).

---

## Frontend modules

| File | Role |
|------|------|
| `apps/web/lib/cloudStorage.ts` | GIS token, Picker, Dropbox Chooser, OneDrive JS, PKCE helpers |
| `apps/web/lib/api.ts` | `fetchCloudPublicConfig`, `cloudImport`, `cloudExport`, token exchange |
| `apps/web/app/app/page.tsx` | UX: import buttons, `runCloudExport`, OAuth return handling on `/app` |

---

## Redirect URI reference (Dropbox / Microsoft)

Register exactly (no trailing slash issues):

| Environment | Redirect URI |
|-------------|----------------|
| Local | `http://localhost:3000/app` |
| Production | `https://www.draftlensai.com/app` |
| Preview | `https://<your-preview-host>/app` |

Same value is produced by `oauthRedirectUri()` in `cloudStorage.ts` (`window.location.origin + '/app'`).

---

## CORS and cookies

The browser sends `credentials: "include"` to the API. Ensure **`DRAFTLENS_CORS_ORIGINS`** includes your Next origin so session cookies on `POST /api/cloud/import` and `POST /api/cloud/export` succeed.

---

## Security notes

- Do **not** expose `DRAFTLENS_GOOGLE_CLIENT_SECRET`, Dropbox secret, or Microsoft secret to Next.js public env.
- User access tokens are sent only over **HTTPS** in production and are not persisted server-side in v1.
- Exported files are always **new** names (`original.reviewed.ext` pattern) — see `export_filename`.
