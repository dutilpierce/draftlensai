const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${p}`;
}

function appOrigin(): string {
  if (typeof window !== "undefined") return window.location.origin;
  return (process.env.NEXT_PUBLIC_APP_URL || "").replace(/\/$/, "") || "http://localhost:3000";
}

export function parseApiError(text: string): string {
  try {
    const j = JSON.parse(text) as { detail?: unknown };
    const d = j.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d))
      return (
        d
          .map((x: unknown) => (typeof x === "object" && x && "msg" in x ? String((x as { msg: string }).msg) : ""))
          .filter(Boolean)
          .join("; ") || text
      );
  } catch {
    /* ignore */
  }
  return text || "Request failed";
}

export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(apiUrl(path), {
    ...init,
    credentials: "include",
    headers,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(parseApiError(text));
  }
  return (await res.json()) as T;
}

export type MeResponse = {
  user_id: string;
  email: string;
  plan: "free" | "pro";
  access_tier: string;
  monthly_free_uses_remaining: number | null;
  free_proof_remaining_this_month: number | null;
  usage_count_current_month: number;
  fair_use_count_current_month: number | null;
  current_billing_status: string | null;
  subscription_current_period_end: string | null;
  pro_docs_used_this_month: number | null;
  pro_monthly_cap: number | null;
  supporting_files_allowed: boolean;
  fix_mode_allowed: boolean;
  max_pages: number;
};

export type AccessStartResponse = MeResponse & { ok: boolean };

export async function startAccess(email: string): Promise<AccessStartResponse> {
  return apiJson<AccessStartResponse>("/api/access/start", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function fetchMe(): Promise<MeResponse> {
  return apiJson<MeResponse>("/api/access/me", { method: "GET" });
}

export type DisclaimerBundle = {
  general: string;
  third_party_models: string;
  accuracy_context_note?: string | null;
  retention: string | null;
  no_model_training?: string | null;
  files_scheduled_for_deletion?: string | null;
  sensitive_mode: string | null;
  ui_run_area_note: string;
  ui_results_area_note: string;
  markdown_review_footer: string;
  markdown_fix_footer: string;
};

export async function fetchDisclaimers(params: {
  hasSupportingFiles: boolean;
  sensitiveMode: boolean;
}): Promise<DisclaimerBundle> {
  const q = new URLSearchParams({
    has_supporting_files: String(params.hasSupportingFiles),
    sensitive_mode: String(params.sensitiveMode),
  });
  return apiJson<DisclaimerBundle>(`/api/disclaimers?${q.toString()}`, { method: "GET" });
}

export type JobPipelineResult = {
  total_issues: number;
  stats_by_severity: Record<string, number>;
  stats_by_category: Record<string, number>;
  unresolved_human_evidence: Record<string, unknown>[];
  consensus_reached: boolean;
  reviewer_success_count?: number;
  reviewer_failure_count?: number;
  reviewer_full_consensus?: boolean;
  partial_quorum_used?: boolean;
  cycle_count_completed?: number;
  convergence_status?: string | null;
  convergence_failure_code?: string | null;
  consensus_mode?: string | null;
  intended_reviewer_count?: number | null;
  convergence_successful_reviewer_count?: number | null;
  required_full_consensus_count?: number | null;
  full_three_reviewer_consensus_achieved?: boolean;
  partial_consensus_only?: boolean;
  pairwise_material_discrepancy_count?: number | null;
  participation_coverage_deficit?: number | null;
  strict_three_reviewer_consensus?: boolean;
  fix_alignment_audit_passed?: boolean | null;
  fix_alignment_audit_errors?: string[] | null;
  max_cycles_reached?: boolean;
  unresolved_material_issue_count?: number;
  unresolved_nit_count?: number;
  unresolved_material_discrepancy_count?: number | null;
  newly_found_material_discrepancy_count?: number;
  resolved_material_discrepancy_count?: number;
  stopped_with_remaining_discrepancies?: boolean;
  stopped_due_to_max_cycles?: boolean;
  stopped_due_to_quorum_loss?: boolean;
  stopped_due_to_provider_unavailable?: boolean;
  stopped_due_to_fatal_arbiter_failure?: boolean;
  pdf_conversion_notes?: string[];
  unresolved_cluster_summaries?: { cluster_id?: string; reasons?: string[]; issues?: { title?: string }[] }[];
  artifact_pdf_flags?: Record<string, boolean>;
  artifact_tiers?: Record<string, string>;
};

export type JobSummary = {
  id: string;
  status: "queued" | "running" | "completed" | "failed";
  output_mode: "review" | "fix";
  review_focus: string;
  sensitive_mode: boolean;
  page_count: number;
  error_message?: string | null;
  artifacts: { name: string; path: string; media_type?: string | null; tier?: string }[];
  pipeline_result?: JobPipelineResult | null;
  created_at?: string | null;
  completed_at?: string | null;
  retention_until?: string | null;
  data_purged_at?: string | null;
  retention_notice?: string | null;
  post_review_fix_seed_job_id?: string | null;
  fix_generation_started_from_review?: boolean;
  apply_fixes_honesty_notice?: string | null;
  source_review_consensus_mode?: string | null;
  source_review_full_tri_consensus?: boolean | null;
  source_review_partial_consensus_only?: boolean | null;
};

export async function createJob(form: FormData): Promise<{ job: JobSummary }> {
  const res = await fetch(apiUrl("/api/jobs"), {
    method: "POST",
    body: form,
    credentials: "include",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(parseApiError(text));
  }
  return (await res.json()) as { job: JobSummary };
}

export async function fetchJob(jobId: string): Promise<JobSummary> {
  return apiJson<JobSummary>(`/api/jobs/${jobId}`, { method: "GET" });
}

export async function applyFixesFromReview(reviewJobId: string): Promise<{ job: JobSummary; source_review_job_id: string }> {
  return apiJson(`/api/jobs/${reviewJobId}/apply-fixes`, { method: "POST" });
}

export function artifactDownloadUrl(jobId: string, filename: string): string {
  const q = new URLSearchParams({ filename });
  return apiUrl(`/api/jobs/${jobId}/artifacts/download?${q.toString()}`);
}

export async function billingCheckout(urls?: { success_url?: string; cancel_url?: string }): Promise<{ url: string }> {
  const base = appOrigin();
  return apiJson<{ url: string }>("/api/billing/checkout", {
    method: "POST",
    body: JSON.stringify({
      success_url: urls?.success_url ?? `${base}/?billing=success`,
      cancel_url: urls?.cancel_url ?? `${base}/?billing=cancel`,
    }),
  });
}

export async function billingPortal(urls?: { return_url?: string }): Promise<{ url: string }> {
  const base = appOrigin();
  return apiJson<{ url: string }>("/api/billing/portal", {
    method: "POST",
    body: JSON.stringify({
      return_url: urls?.return_url ?? `${base}/`,
    }),
  });
}

export type CloudPublicConfig = {
  google_client_id: string | null;
  google_picker_api_key: string | null;
  /** Numeric GCP project number for Google Picker `setAppId` (optional; public). */
  google_cloud_project_number?: string | null;
  dropbox_app_key: string | null;
  microsoft_client_id: string | null;
  api_public_url: string;
};

export async function fetchCloudPublicConfig(): Promise<CloudPublicConfig> {
  const res = await fetch(apiUrl("/api/cloud/config"), { method: "GET" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(parseApiError(text));
  }
  return (await res.json()) as CloudPublicConfig;
}

export type CloudFileReference = {
  provider: "google_drive" | "dropbox" | "onedrive";
  provider_file_id: string;
  shared_link: string | null;
  download_url?: string | null;
  filename: string;
  mime_type: string;
  document_role: "main" | "supporting";
};

export type CloudImportResult = {
  import_handle: string;
  reference: CloudFileReference;
};

export type GoogleDriveFileMetadataResult = {
  id: string;
  name: string;
  mime_type: string;
  icon_link: string | null;
  thumbnail_link: string | null;
  web_view_link: string | null;
  size: string | null;
  modified_time: string | null;
};

export async function cloudGoogleDriveFileMetadata(body: {
  file_id: string;
  access_token: string;
}): Promise<GoogleDriveFileMetadataResult> {
  return apiJson<GoogleDriveFileMetadataResult>("/api/cloud/google-drive/metadata", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function cloudImport(body: {
  request: {
    provider: "google_drive" | "dropbox" | "onedrive";
    provider_file_id?: string;
    shared_link?: string | null;
    download_url?: string | null;
    filename: string;
    mime_type?: string | null;
    document_role: "main" | "supporting";
  };
  access_token?: string;
}): Promise<CloudImportResult> {
  return apiJson<CloudImportResult>("/api/cloud/import", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function cloudExport(body: {
  job_id: string;
  request: { provider: "google_drive" | "dropbox" | "onedrive"; artifact_name: string; parent_folder_id?: string | null };
  access_token: string;
}): Promise<{ provider: string; remote_file_id: string | null; web_view_link: string | null; message: string }> {
  return apiJson("/api/cloud/export", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function exchangeDropboxToken(body: {
  code: string;
  redirect_uri: string;
  code_verifier: string;
}): Promise<{ access_token: string }> {
  return apiJson("/api/cloud/oauth/dropbox/token", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function exchangeMicrosoftToken(body: {
  code: string;
  redirect_uri: string;
  code_verifier: string;
}): Promise<{ access_token: string }> {
  return apiJson("/api/cloud/oauth/microsoft/token", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
