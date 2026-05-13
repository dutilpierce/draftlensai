"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  artifactDownloadUrl,
  billingCheckout,
  billingPortal,
  cloudExport,
  cloudImport,
  createJob,
  applyFixesFromReview,
  exchangeDropboxToken,
  exchangeMicrosoftToken,
  fetchCloudPublicConfig,
  fetchDisclaimers,
  fetchJob,
  fetchMe,
  startAccess,
  type CloudPublicConfig,
  type DisclaimerBundle,
  type JobSummary,
  type MeResponse,
} from "@/lib/api";
import {
  getGoogleAccessToken,
  oauthRedirectUri,
  pickFromDropbox,
  pickFromGoogleDrive,
  pickFromOneDrive,
  startDropboxPkceOAuth,
  startMicrosoftPkceOAuth,
} from "@/lib/cloudStorage";
import { stageLabel } from "@/lib/pipelineStages";
import { aggregateReviewerChips } from "@/lib/reviewerChips";
import { streamJobEvents, type SseEvent } from "@/lib/sse";
import { DraftLensLogo } from "@/components/brand/DraftLensLogo";

const REVIEW_FOCUS = [
  { value: "standard", label: "Standard" },
  { value: "accuracy-heavy", label: "Accuracy-heavy" },
  { value: "formatting-heavy", label: "Formatting-heavy" },
  { value: "adversarial", label: "Adversarial" },
  { value: "voice-preserving", label: "Voice-preserving" },
] as const;

type Gate = "fix" | "supporting" | "quota" | "cap" | null;

function planBadge(me: MeResponse): string {
  if (me.plan === "pro") {
    return me.current_billing_status === "past_due" ? "Pro · billing" : "Pro";
  }
  const n = me.monthly_free_uses_remaining ?? me.free_proof_remaining_this_month ?? 0;
  return n > 0 ? `Free · ${n}` : "Free · 0";
}

function pickMainManuscript(file: File | null): File | null {
  if (!file) return null;
  const lower = file.name.toLowerCase();
  const extOk = lower.endsWith(".docx") || lower.endsWith(".pdf");
  const typeOk =
    file.type.includes("wordprocessingml") ||
    file.type === "application/pdf" ||
    file.type.includes("pdf");
  return extOk || typeOk ? file : null;
}

function num(v: unknown): number | null {
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  if (typeof v === "string" && v.trim() && !Number.isNaN(Number(v))) return Number(v);
  return null;
}

function debateSnapshot(log: SseEvent[]) {
  let before: number | null = null;
  let after: number | null = null;
  for (const ev of log) {
    if (ev.stage === "CROSS_MODEL_DEBATE_STARTED") {
      before = num(ev.detail?.conflict_groups);
    }
    if (ev.stage === "CROSS_MODEL_DEBATE_ROUND_COMPLETE") {
      const r = ev.detail?.round;
      const rem = num(ev.detail?.conflict_groups_remaining);
      if (r === "final" || r === "skipped") after = rem;
    }
  }
  return { before, after };
}

const HIDDEN_ARTIFACTS = new Set(["pipeline_stats.json", "pipeline_manifest.json"]);

function cloudSaveProviderLabel(p: "google_drive" | "dropbox" | "onedrive"): string {
  if (p === "google_drive") return "Google Drive";
  if (p === "dropbox") return "Dropbox";
  return "OneDrive";
}

function cloudSavedOpenLinkLabel(p: "google_drive" | "dropbox" | "onedrive"): string {
  if (p === "google_drive") return "Open in Google Drive";
  if (p === "dropbox") return "Open in Dropbox";
  return "Open in OneDrive";
}

export default function HomePage() {
  const [email, setEmail] = useState("");
  const [me, setMe] = useState<MeResponse | null>(null);
  const [meErr, setMeErr] = useState<string | null>(null);

  const [mainFile, setMainFile] = useState<File | null>(null);
  const [mainCloud, setMainCloud] = useState<{ handle: string; label: string } | null>(null);
  const [supporting, setSupporting] = useState<File[]>([]);
  const [supportingCloud, setSupportingCloud] = useState<{ handle: string; label: string }[]>([]);
  const [cloudCfg, setCloudCfg] = useState<CloudPublicConfig | null>(null);
  const [optOpen, setOptOpen] = useState(false);
  const [context, setContext] = useState("");
  const [reviewFocus, setReviewFocus] = useState("standard");
  const [doNotChange, setDoNotChange] = useState("");
  const [sensitive, setSensitive] = useState(false);
  const [outputMode, setOutputMode] = useState<"review" | "fix">("review");
  const [disclaimerCopy, setDisclaimerCopy] = useState<DisclaimerBundle | null>(null);

  const [log, setLog] = useState<SseEvent[]>([]);
  const [job, setJob] = useState<JobSummary | null>(null);
  const [formErr, setFormErr] = useState<string | null>(null);
  const [cloudSaveNotice, setCloudSaveNotice] = useState<{
    webUrl: string | null;
    artifact: string;
    provider: "google_drive" | "dropbox" | "onedrive";
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [gate, setGate] = useState<Gate>(null);
  const [drag, setDrag] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const mainInputRef = useRef<HTMLInputElement>(null);

  const refreshMe = useCallback(async () => {
    setMeErr(null);
    try {
      const m = await fetchMe();
      setMe(m);
      setEmail(m.email);
    } catch {
      setMe(null);
    }
  }, []);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const q = new URLSearchParams(window.location.search);
    if (q.get("billing") === "success") {
      void refreshMe().then(() => {
        window.history.replaceState({}, "", `${window.location.pathname}${window.location.hash}`);
      });
    }
  }, [refreshMe]);

  useEffect(() => {
    if (!me) {
      setDisclaimerCopy(null);
      return;
    }
    void fetchDisclaimers({
      hasSupportingFiles: supporting.length + supportingCloud.length > 0,
      sensitiveMode: sensitive,
    })
      .then(setDisclaimerCopy)
      .catch(() => setDisclaimerCopy(null));
  }, [me, supporting.length, supportingCloud.length, sensitive]);

  useEffect(() => {
    if (!me) {
      setCloudCfg(null);
      return;
    }
    void fetchCloudPublicConfig().then(setCloudCfg).catch(() => setCloudCfg(null));
  }, [me]);

  const runCloudExport = useCallback(
    async (jobId: string, artifactName: string, provider: "google_drive" | "dropbox" | "onedrive") => {
      const cfg = cloudCfg ?? (await fetchCloudPublicConfig().catch(() => null));
      if (!cfg) {
        setFormErr("Cloud is not configured on the server.");
        return;
      }
      setFormErr(null);
      setCloudSaveNotice(null);
      try {
        let token = "";
        if (provider === "google_drive") {
          if (!cfg.google_client_id) {
            setFormErr("Google Drive is not configured.");
            return;
          }
          token = await getGoogleAccessToken(cfg.google_client_id);
        } else if (provider === "dropbox") {
          token = sessionStorage.getItem("dl_dropbox_token") || "";
          if (!token && cfg.dropbox_app_key) {
            sessionStorage.setItem("dl_pending_export", JSON.stringify({ jobId, artifactName, provider }));
            startDropboxPkceOAuth(cfg.dropbox_app_key);
            return;
          }
        } else if (provider === "onedrive") {
          token = sessionStorage.getItem("dl_microsoft_token") || "";
          if (!token && cfg.microsoft_client_id) {
            sessionStorage.setItem("dl_pending_export", JSON.stringify({ jobId, artifactName, provider }));
            startMicrosoftPkceOAuth(cfg.microsoft_client_id);
            return;
          }
        }
        if (!token) {
          setFormErr("Sign in to this cloud provider first.");
          return;
        }
        const out = await cloudExport({
          job_id: jobId,
          request: { provider, artifact_name: artifactName },
          access_token: token,
        });
        setCloudSaveNotice({
          webUrl: out.web_view_link,
          artifact: artifactName,
          provider,
        });
      } catch (e) {
        setFormErr(e instanceof Error ? e.message : "Save to cloud failed");
      }
    },
    [cloudCfg],
  );

  useEffect(() => {
    if (typeof window === "undefined" || !me) return;
    const sp = new URLSearchParams(window.location.search);
    const code = sp.get("code");
    const state = sp.get("state");
    if (!code || !state?.startsWith("dl_oauth_")) return;
    const verifier = sessionStorage.getItem(state);
    const kind = sessionStorage.getItem("dl_oauth_kind");
    if (!verifier || !kind) return;

    let cancelled = false;
    void (async () => {
      try {
        const redirect = oauthRedirectUri();
        if (kind === "dropbox") {
          const { access_token } = await exchangeDropboxToken({
            code,
            redirect_uri: redirect,
            code_verifier: verifier,
          });
          if (!cancelled) sessionStorage.setItem("dl_dropbox_token", access_token);
        } else if (kind === "microsoft") {
          const { access_token } = await exchangeMicrosoftToken({
            code,
            redirect_uri: redirect,
            code_verifier: verifier,
          });
          if (!cancelled) sessionStorage.setItem("dl_microsoft_token", access_token);
        }
      } catch (e) {
        if (!cancelled) setFormErr(e instanceof Error ? e.message : "Cloud sign-in failed");
      } finally {
        if (cancelled) return;
        sessionStorage.removeItem(state);
        sessionStorage.removeItem("dl_oauth_kind");
        window.history.replaceState({}, "", `${window.location.pathname}${window.location.hash}`);
        const raw = sessionStorage.getItem("dl_pending_export");
        if (raw) {
          sessionStorage.removeItem("dl_pending_export");
          try {
            const pending = JSON.parse(raw) as {
              jobId: string;
              artifactName: string;
              provider: "google_drive" | "dropbox" | "onedrive";
            };
            await runCloudExport(pending.jobId, pending.artifactName, pending.provider);
          } catch {
            /* runCloudExport sets formErr */
          }
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [me, runCloudExport]);

  const canFix = me?.fix_mode_allowed === true;
  const canSupport = me?.supporting_files_allowed === true;
  const running = busy;

  const debateProgress = useMemo(() => debateSnapshot(log), [log]);
  const chips = useMemo(() => aggregateReviewerChips(log), [log]);

  const showAccuracyNote =
    supporting.length + supportingCloud.length === 0 &&
    reviewFocus === "accuracy-heavy" &&
    Boolean(disclaimerCopy?.accuracy_context_note);

  async function onContinue(e: React.FormEvent) {
    e.preventDefault();
    setMeErr(null);
    setBusy(true);
    try {
      const data = await startAccess(email.trim());
      const { ok: _ok, ...profile } = data;
      setMe(profile);
    } catch (err) {
      setMeErr(err instanceof Error ? err.message : "Session failed");
    } finally {
      setBusy(false);
    }
  }

  function setMode(m: "review" | "fix") {
    if (m === "fix" && !canFix) {
      setGate("fix");
      return;
    }
    setOutputMode(m);
  }

  function applyMainFile(f: File | null) {
    if (f) setMainCloud(null);
    const x = pickMainManuscript(f);
    setMainFile(x);
    if (f && !x) setFormErr("Use a .docx or .pdf file.");
    else if (x) setFormErr(null);
  }

  async function run() {
    setFormErr(null);
    setLog([]);
    setCloudSaveNotice(null);
    setJob(null);
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    if (!me) {
      setFormErr("Continue with email first.");
      return;
    }
    if (!mainFile && !mainCloud) {
      setFormErr("Add a manuscript (.docx or PDF).");
      return;
    }
    if (me.plan === "free") {
      const left = me.monthly_free_uses_remaining ?? me.free_proof_remaining_this_month ?? 0;
      if (left <= 0) {
        setGate("quota");
        return;
      }
    }
    if (me.plan === "pro" && me.pro_monthly_cap != null && (me.pro_docs_used_this_month ?? 0) >= me.pro_monthly_cap) {
      setGate("cap");
      return;
    }

    setBusy(true);
    try {
      const fd = new FormData();
      if (mainCloud) {
        fd.append("main_cloud_import_handle", mainCloud.handle);
      } else if (mainFile) {
        fd.append("main_document", mainFile);
      }
      fd.append("output_mode", outputMode);
      fd.append("review_focus", reviewFocus);
      if (context.trim()) fd.append("context_text", context.trim());
      if (doNotChange.trim()) fd.append("do_not_change", doNotChange.trim());
      fd.append("sensitive_mode", sensitive ? "true" : "false");
      for (const f of supporting) fd.append("supporting_files", f);
      if (supportingCloud.length > 0) {
        fd.append(
          "supporting_cloud_import_handles",
          JSON.stringify(supportingCloud.map((c) => c.handle)),
        );
      }

      const { job: created } = await createJob(fd);
      setJob(created);

      for await (const ev of streamJobEvents(created.id, abortRef.current.signal)) {
        setLog((prev) => [...prev, ev]);
        if (ev.stage === "completed" || ev.stage === "failed" || ev.stage === "JOB_FAILED") break;
      }

      const latest = await fetchJob(created.id);
      setJob(latest);
      await refreshMe();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Run failed";
      setFormErr(msg);
      if (msg.includes("fix_mode_requires_pro")) setGate("fix");
      else if (msg.includes("supporting_files_require_pro")) setGate("supporting");
      else if (msg.includes("free_monthly_limit_reached")) setGate("quota");
      else if (msg.includes("pro_monthly_cap_reached")) setGate("cap");
    } finally {
      setBusy(false);
    }
  }

  async function runApplyFixes() {
    if (!job || job.status !== "completed" || job.output_mode !== "review") return;
    if (!me) {
      setFormErr("Continue with email first.");
      return;
    }
    if (!job.artifacts.some((a) => a.name === "fix_seed_snapshot.json")) {
      setFormErr("Fix seed is missing; re-run review on the current DraftLens version.");
      return;
    }
    if (!canFix) {
      setGate("fix");
      return;
    }
    if (me.plan === "free") {
      const left = me.monthly_free_uses_remaining ?? me.free_proof_remaining_this_month ?? 0;
      if (left <= 0) {
        setGate("quota");
        return;
      }
    }
    if (me.plan === "pro" && me.pro_monthly_cap != null && (me.pro_docs_used_this_month ?? 0) >= me.pro_monthly_cap) {
      setGate("cap");
      return;
    }

    const reviewId = job.id;
    setFormErr(null);
    setLog([]);
    setCloudSaveNotice(null);
    setBusy(true);
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    try {
      const { job: created } = await applyFixesFromReview(reviewId);
      setJob(created);

      for await (const ev of streamJobEvents(created.id, abortRef.current.signal)) {
        setLog((prev) => [...prev, ev]);
        if (ev.stage === "completed" || ev.stage === "failed" || ev.stage === "JOB_FAILED") break;
      }

      const latest = await fetchJob(created.id);
      setJob(latest);
      await refreshMe();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Apply fixes failed";
      setFormErr(msg);
      if (msg.includes("fix_mode_requires_pro")) setGate("fix");
      else if (msg.includes("free_monthly_limit_reached")) setGate("quota");
      else if (msg.includes("pro_monthly_cap_reached")) setGate("cap");
      try {
        setJob(await fetchJob(reviewId));
      } catch {
        /* ignore */
      }
    } finally {
      setBusy(false);
    }
  }

  async function onRun(e: React.FormEvent) {
    e.preventDefault();
    await run();
  }

  async function importMainFromGoogle() {
    if (!cloudCfg?.google_client_id || !cloudCfg.google_picker_api_key) {
      setFormErr("Configure Google (DRAFTLENS_GOOGLE_CLIENT_ID and DRAFTLENS_GOOGLE_PICKER_API_KEY on the API).");
      return;
    }
    setFormErr(null);
    setBusy(true);
    try {
      const { pick, accessToken } = await pickFromGoogleDrive({
        clientId: cloudCfg.google_client_id,
        pickerApiKey: cloudCfg.google_picker_api_key,
      });
      const res = await cloudImport({
        request: {
          provider: "google_drive",
          provider_file_id: pick.id,
          filename: pick.name,
          mime_type: pick.mimeType ?? null,
          document_role: "main",
        },
        access_token: accessToken,
      });
      setMainFile(null);
      setMainCloud({ handle: res.import_handle, label: `${res.reference.filename} · Google Drive` });
    } catch (e) {
      if (e instanceof Error && e.message !== "cancelled") setFormErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function importMainFromDropbox() {
    if (!cloudCfg?.dropbox_app_key) {
      setFormErr("Configure Dropbox (DRAFTLENS_DROPBOX_APP_KEY on the API).");
      return;
    }
    setFormErr(null);
    setBusy(true);
    try {
      const { link, name } = await pickFromDropbox(cloudCfg.dropbox_app_key);
      const res = await cloudImport({
        request: {
          provider: "dropbox",
          provider_file_id: "",
          shared_link: link,
          filename: name,
          mime_type: null,
          document_role: "main",
        },
        access_token: "",
      });
      setMainFile(null);
      setMainCloud({ handle: res.import_handle, label: `${res.reference.filename} · Dropbox` });
    } catch (e) {
      if (e instanceof Error && e.message !== "cancelled") setFormErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function importMainFromOneDrive() {
    if (!cloudCfg?.microsoft_client_id) {
      setFormErr("Configure Microsoft (DRAFTLENS_MICROSOFT_CLIENT_ID on the API).");
      return;
    }
    setFormErr(null);
    setBusy(true);
    try {
      const pick = await pickFromOneDrive(cloudCfg.microsoft_client_id);
      if (!pick.downloadUrl) {
        setFormErr("OneDrive did not return a download link for this item. Try a different file or use local upload.");
        return;
      }
      const res = await cloudImport({
        request: {
          provider: "onedrive",
          provider_file_id: pick.id,
          shared_link: null,
          download_url: pick.downloadUrl,
          filename: pick.name,
          mime_type: null,
          document_role: "main",
        },
        access_token: "",
      });
      setMainFile(null);
      setMainCloud({ handle: res.import_handle, label: `${res.reference.filename} · OneDrive` });
    } catch (e) {
      if (e instanceof Error && e.message !== "cancelled") setFormErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function importSupportingFromGoogle() {
    if (!canSupport) {
      setGate("supporting");
      return;
    }
    if (!cloudCfg?.google_client_id || !cloudCfg.google_picker_api_key) {
      setFormErr("Configure Google picker on the API.");
      return;
    }
    setFormErr(null);
    setBusy(true);
    try {
      const { pick, accessToken } = await pickFromGoogleDrive({
        clientId: cloudCfg.google_client_id,
        pickerApiKey: cloudCfg.google_picker_api_key,
      });
      const res = await cloudImport({
        request: {
          provider: "google_drive",
          provider_file_id: pick.id,
          filename: pick.name,
          mime_type: pick.mimeType ?? null,
          document_role: "supporting",
        },
        access_token: accessToken,
      });
      setSupportingCloud((prev) => [...prev, { handle: res.import_handle, label: `${res.reference.filename} · Google Drive` }]);
    } catch (e) {
      if (e instanceof Error && e.message !== "cancelled") setFormErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function importSupportingFromDropbox() {
    if (!canSupport) {
      setGate("supporting");
      return;
    }
    if (!cloudCfg?.dropbox_app_key) {
      setFormErr("Configure Dropbox on the API.");
      return;
    }
    setFormErr(null);
    setBusy(true);
    try {
      const { link, name } = await pickFromDropbox(cloudCfg.dropbox_app_key);
      const res = await cloudImport({
        request: {
          provider: "dropbox",
          provider_file_id: "",
          shared_link: link,
          filename: name,
          mime_type: null,
          document_role: "supporting",
        },
        access_token: "",
      });
      setSupportingCloud((prev) => [...prev, { handle: res.import_handle, label: `${res.reference.filename} · Dropbox` }]);
    } catch (e) {
      if (e instanceof Error && e.message !== "cancelled") setFormErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function importSupportingFromOneDrive() {
    if (!canSupport) {
      setGate("supporting");
      return;
    }
    if (!cloudCfg?.microsoft_client_id) {
      setFormErr("Configure Microsoft on the API.");
      return;
    }
    setFormErr(null);
    setBusy(true);
    try {
      const pick = await pickFromOneDrive(cloudCfg.microsoft_client_id);
      if (!pick.downloadUrl) {
        setFormErr("OneDrive did not return a download link for this item.");
        return;
      }
      const res = await cloudImport({
        request: {
          provider: "onedrive",
          provider_file_id: pick.id,
          shared_link: null,
          download_url: pick.downloadUrl,
          filename: pick.name,
          mime_type: null,
          document_role: "supporting",
        },
        access_token: "",
      });
      setSupportingCloud((prev) => [...prev, { handle: res.import_handle, label: `${res.reference.filename} · OneDrive` }]);
    } catch (e) {
      if (e instanceof Error && e.message !== "cancelled") setFormErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  const pr = job?.pipeline_result;

  const artifactSplit = useMemo(() => {
    type Art = JobSummary["artifacts"][number];
    if (!job) return { primary: [] as Art[], advanced: [] as Art[] };
    const vis = job.artifacts.filter((a) => !HIDDEN_ARTIFACTS.has(a.name));
    const tiers = pr?.artifact_tiers ?? {};
    const tierOf = (name: string, a: Art) => tiers[name] ?? a.tier ?? "primary";
    const primaryRaw = vis.filter((a) => tierOf(a.name, a) !== "advanced");
    const primary = [...primaryRaw].sort((a, b) => {
      const apdf = a.name.toLowerCase().endsWith(".pdf") ? 0 : 1;
      const bpdf = b.name.toLowerCase().endsWith(".pdf") ? 0 : 1;
      if (apdf !== bpdf) return apdf - bpdf;
      return a.name.localeCompare(b.name);
    });
    return {
      primary,
      advanced: vis.filter((a) => tierOf(a.name, a) === "advanced"),
    };
  }, [job, pr?.artifact_tiers]);

  const progressPct = useMemo(() => {
    let best = 0;
    for (const ev of log) {
      const p = num(ev.detail?.progress_percent);
      if (p != null && p > best) best = p;
    }
    return best;
  }, [log]);

  const latestCycleNumber = useMemo(() => {
    for (let i = log.length - 1; i >= 0; i--) {
      const c = num(log[i]?.detail?.cycle_number);
      if (c != null) return c;
    }
    return null;
  }, [log]);

  const hasReviewFixSeed = useMemo(
    () => Boolean(job?.artifacts?.some((a) => a.name === "fix_seed_snapshot.json")),
    [job?.artifacts],
  );

  const showLongJobChrome = Boolean(busy && job && job.status !== "completed" && job.status !== "failed");

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!showLongJobChrome) return;
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [showLongJobChrome]);

  const liveStage = log.length ? log[log.length - 1] : null;

  return (
    <div className="min-h-full bg-[#faf9f7] text-zinc-900">
      {gate ? (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-zinc-200/80 bg-white/95 px-4 py-3 shadow-[0_-8px_30px_rgba(0,0,0,0.06)] backdrop-blur-sm">
          <div className="mx-auto flex max-w-lg flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-zinc-600">
              {gate === "fix" && "Fix mode is included with DraftLens Pro."}
              {gate === "supporting" && "Supporting files are a Pro feature."}
              {(gate === "quota" || gate === "cap") && "You've reached this month's limit."}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                className="rounded-full bg-zinc-900 px-4 py-1.5 text-xs font-medium text-white"
                onClick={async () => {
                  try {
                    const { url } = await billingCheckout();
                    window.location.href = url;
                  } catch {
                    setMeErr("Checkout unavailable");
                  }
                }}
              >
                Upgrade
              </button>
              <button type="button" className="text-xs text-zinc-500 underline" onClick={() => setGate(null)}>
                Not now
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <main className="mx-auto max-w-lg px-5 pb-28 pt-16 sm:px-6 sm:pt-20">
        <header className="mb-14 space-y-2">
          <DraftLensLogo size="md" />
          <p className="text-sm text-zinc-500">Multi-model document review</p>
        </header>

        <section className="space-y-10">
          {!me ? (
            <form onSubmit={onContinue} className="space-y-4">
              <label className="block">
                <span className="sr-only">Email</span>
                <input
                  type="email"
                  required
                  value={email}
                  disabled={running}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Work email"
                  className="w-full border-0 border-b border-zinc-300 bg-transparent py-2 text-sm outline-none ring-0 placeholder:text-zinc-400 focus:border-zinc-900 disabled:opacity-40"
                />
              </label>
              <button
                type="submit"
                disabled={running}
                className="text-sm font-medium text-zinc-900 underline decoration-zinc-300 underline-offset-4 hover:decoration-zinc-900 disabled:opacity-40"
              >
                Continue
              </button>
              {meErr ? <p className="text-xs text-red-600">{meErr}</p> : null}
            </form>
          ) : (
            <div className="space-y-10">
              {meErr ? <p className="text-xs text-red-600">{meErr}</p> : null}
              <div className="flex items-baseline justify-between gap-3">
                {me.plan === "pro" ? (
                  <button
                    type="button"
                    disabled={running}
                    onClick={async () => {
                      try {
                        const { url } = await billingPortal();
                        window.location.href = url;
                      } catch {
                        setMeErr("Billing unavailable");
                      }
                    }}
                    className="text-[11px] text-zinc-500 underline decoration-zinc-300 underline-offset-4 hover:text-zinc-800 disabled:opacity-40"
                  >
                    Manage billing
                  </button>
                ) : (
                  <span />
                )}
                <span className="rounded-full border border-zinc-200/80 bg-white px-2.5 py-0.5 text-[11px] font-medium text-zinc-500">
                  {planBadge(me)}
                </span>
              </div>

              <div
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") mainInputRef.current?.click();
                }}
                onDragEnter={(e) => {
                  e.preventDefault();
                  if (!running) setDrag(true);
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  if (!running) setDrag(true);
                }}
                onDragLeave={() => setDrag(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDrag(false);
                  if (running) return;
                  const f = e.dataTransfer.files?.[0];
                  applyMainFile(f ?? null);
                }}
                onClick={() => !running && mainInputRef.current?.click()}
                className={`flex min-h-[9.5rem] cursor-pointer flex-col justify-center rounded-2xl border px-5 py-6 shadow-sm ring-1 ring-zinc-900/[0.03] transition ${
                  drag ? "border-zinc-900 bg-white ring-zinc-900/10" : "border-zinc-200/90 bg-white/70 hover:border-zinc-300 hover:ring-zinc-900/[0.06]"
                } ${running ? "pointer-events-none opacity-50" : ""}`}
              >
                <input
                  ref={mainInputRef}
                  type="file"
                  accept=".docx,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/pdf"
                  className="hidden"
                  disabled={running}
                  onChange={(e) => applyMainFile(e.target.files?.[0] ?? null)}
                />
                <p className="text-sm text-zinc-800">
                  {mainCloud ? mainCloud.label : mainFile ? mainFile.name : "Drop manuscript or browse"}
                </p>
                <p className="mt-1 text-xs text-zinc-400">DOCX or PDF · up to {me.max_pages} pages</p>
                {cloudCfg?.google_client_id && cloudCfg?.google_picker_api_key ? (
                  <p className="mt-1 text-[11px] leading-relaxed text-zinc-400">
                    Google Docs files may be exported to Word before review.
                  </p>
                ) : null}
                {outputMode === "fix" &&
                (mainFile?.name ?? mainCloud?.label ?? "").toLowerCase().endsWith(".pdf") ? (
                  <p className="mt-1 text-[11px] text-zinc-400">
                    Fix mode outputs a new Word file from extracted text — not an edited PDF.
                  </p>
                ) : null}
              </div>

              {cloudCfg &&
              (cloudCfg.google_client_id ||
                cloudCfg.google_picker_api_key ||
                cloudCfg.dropbox_app_key ||
                cloudCfg.microsoft_client_id) ? (
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-zinc-500">
                  <span className="text-zinc-400">Or import from</span>
                  {cloudCfg.google_client_id && cloudCfg.google_picker_api_key ? (
                    <button
                      type="button"
                      disabled={running}
                      aria-label="Choose main manuscript from Google Drive"
                      onClick={(e) => {
                        e.stopPropagation();
                        void importMainFromGoogle();
                      }}
                      className="underline decoration-zinc-300 underline-offset-2 hover:text-zinc-800 disabled:opacity-40"
                    >
                      Choose from Google Drive
                    </button>
                  ) : null}
                  {cloudCfg.dropbox_app_key ? (
                    <button
                      type="button"
                      disabled={running}
                      onClick={(e) => {
                        e.stopPropagation();
                        void importMainFromDropbox();
                      }}
                      className="underline decoration-zinc-300 underline-offset-2 hover:text-zinc-800 disabled:opacity-40"
                    >
                      Dropbox
                    </button>
                  ) : null}
                  {cloudCfg.microsoft_client_id ? (
                    <button
                      type="button"
                      disabled={running}
                      onClick={(e) => {
                        e.stopPropagation();
                        void importMainFromOneDrive();
                      }}
                      className="underline decoration-zinc-300 underline-offset-2 hover:text-zinc-800 disabled:opacity-40"
                    >
                      OneDrive
                    </button>
                  ) : null}
                </div>
              ) : null}

              <div className="rounded-2xl border border-zinc-200/85 bg-white/55 px-3 py-2 shadow-sm ring-1 ring-zinc-900/[0.02]">
                <button
                  type="button"
                  disabled={running}
                  onClick={() => setOptOpen((o) => !o)}
                  className="flex w-full items-center justify-between py-1 text-left text-sm text-zinc-700 disabled:opacity-40"
                >
                  <span>Options</span>
                  <span className="text-zinc-400">{optOpen ? "−" : "+"}</span>
                </button>
                {optOpen ? (
                  <div className="mt-6 space-y-5 border-t border-zinc-100 pt-6">
                    <label className="block space-y-1.5">
                      <span className="text-xs text-zinc-500">Context</span>
                      <textarea
                        value={context}
                        disabled={running}
                        onChange={(e) => setContext(e.target.value)}
                        rows={3}
                        placeholder="Purpose, audience, tone, or areas to stress-test."
                        className="w-full resize-none rounded-xl border border-zinc-200/90 bg-white px-3 py-2 text-sm outline-none ring-zinc-900/10 focus:ring-1 disabled:opacity-40"
                      />
                    </label>
                    <label className="block space-y-1.5">
                      <span className="text-xs text-zinc-500">Review focus</span>
                      <select
                        value={reviewFocus}
                        disabled={running}
                        onChange={(e) => setReviewFocus(e.target.value)}
                        className="w-full rounded-xl border border-zinc-200/90 bg-white px-3 py-2 text-sm outline-none disabled:opacity-40"
                      >
                        {REVIEW_FOCUS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="block space-y-1.5">
                      <span className="text-xs text-zinc-500">Do-not-change</span>
                      <textarea
                        value={doNotChange}
                        disabled={running}
                        onChange={(e) => setDoNotChange(e.target.value)}
                        rows={2}
                        placeholder="Names, clauses, numbers, or wording to preserve."
                        className="w-full resize-none rounded-xl border border-zinc-200/90 bg-white px-3 py-2 text-sm outline-none disabled:opacity-40"
                      />
                    </label>
                    <label className={`block space-y-1.5 ${!canSupport ? "opacity-50" : ""}`}>
                      <span className="text-xs text-zinc-500">Supporting files</span>
                      <input
                        type="file"
                        multiple
                        accept=".docx,.pdf,.txt,.md,.doc"
                        disabled={running || !canSupport}
                        onChange={(e) => {
                          const files = e.target.files ? Array.from(e.target.files) : [];
                          if (!canSupport && files.length) {
                            e.target.value = "";
                            setGate("supporting");
                            return;
                          }
                          setSupporting(files);
                        }}
                        className="w-full text-xs file:mr-3 file:rounded-lg file:border-0 file:bg-zinc-900 file:px-3 file:py-2 file:text-xs file:text-white"
                      />
                      <p className="text-[11px] text-zinc-400">Evidence only · Pro</p>
                      <p className="mt-1 text-[11px] leading-relaxed text-zinc-400">
                        PDF, Word, or plain text—or add supporting files from Google Drive.
                      </p>
                      {supportingCloud.length > 0 ? (
                        <ul className="mt-2 space-y-1">
                          {supportingCloud.map((c) => (
                            <li key={c.handle} className="flex items-center justify-between text-[11px] text-zinc-600">
                              <span className="truncate pr-2">{c.label}</span>
                              <button
                                type="button"
                                disabled={running}
                                className="shrink-0 text-zinc-400 underline disabled:opacity-40"
                                onClick={() => setSupportingCloud((prev) => prev.filter((x) => x.handle !== c.handle))}
                              >
                                Remove
                              </button>
                            </li>
                          ))}
                        </ul>
                      ) : null}
                      {cloudCfg &&
                      (cloudCfg.google_client_id ||
                        cloudCfg.google_picker_api_key ||
                        cloudCfg.dropbox_app_key ||
                        cloudCfg.microsoft_client_id) ? (
                        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-zinc-500">
                          <span className="text-zinc-400">Add from</span>
                          {cloudCfg.google_client_id && cloudCfg.google_picker_api_key ? (
                            <button
                              type="button"
                              disabled={running || !canSupport}
                              aria-label="Add supporting files from Google Drive"
                              onClick={() => void importSupportingFromGoogle()}
                              className="underline decoration-zinc-300 underline-offset-2 hover:text-zinc-800 disabled:opacity-40"
                            >
                              Choose from Google Drive
                            </button>
                          ) : null}
                          {cloudCfg.dropbox_app_key ? (
                            <button
                              type="button"
                              disabled={running || !canSupport}
                              onClick={() => void importSupportingFromDropbox()}
                              className="underline decoration-zinc-300 underline-offset-2 hover:text-zinc-800 disabled:opacity-40"
                            >
                              Dropbox
                            </button>
                          ) : null}
                          {cloudCfg.microsoft_client_id ? (
                            <button
                              type="button"
                              disabled={running || !canSupport}
                              onClick={() => void importSupportingFromOneDrive()}
                              className="underline decoration-zinc-300 underline-offset-2 hover:text-zinc-800 disabled:opacity-40"
                            >
                              OneDrive
                            </button>
                          ) : null}
                        </div>
                      ) : null}
                    </label>
                    <label className="flex items-center gap-2 text-sm text-zinc-700">
                      <input
                        type="checkbox"
                        checked={sensitive}
                        disabled={running}
                        onChange={(e) => setSensitive(e.target.checked)}
                        className="rounded border-zinc-300"
                      />
                      <span className="text-xs">Sensitive mode — shorter retention.</span>
                    </label>
                  </div>
                ) : null}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  disabled={running}
                  onClick={() => setMode("review")}
                  className={`rounded-2xl py-3 text-sm font-medium transition ${
                    outputMode === "review" ? "bg-zinc-900 text-white" : "bg-white text-zinc-600 ring-1 ring-zinc-200/90"
                  } disabled:opacity-40`}
                >
                  Review
                </button>
                <button
                  type="button"
                  disabled={running}
                  onClick={() => setMode("fix")}
                  className={`rounded-2xl py-3 text-sm font-medium transition ${
                    outputMode === "fix" ? "bg-zinc-900 text-white" : "bg-white text-zinc-600 ring-1 ring-zinc-200/90"
                  } disabled:opacity-40`}
                >
                  Fix
                </button>
              </div>

              <form onSubmit={onRun} className="space-y-3">
                <button
                  type="submit"
                  disabled={running}
                  className="w-full rounded-2xl bg-zinc-900 py-3.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:opacity-40"
                >
                  {running ? "Running…" : "Run"}
                </button>
                <p className="text-center text-[11px] leading-relaxed text-zinc-400">
                  {disclaimerCopy?.general ?? "AI-assisted review. Please verify important facts and final wording."}
                </p>
                {formErr ? <p className="text-center text-xs text-red-600">{formErr}</p> : null}
              </form>
            </div>
          )}
        </section>

        <section className="mt-16 space-y-5 rounded-2xl border border-zinc-200/95 bg-white/80 p-5 shadow-sm ring-1 ring-zinc-900/[0.03] sm:p-6">
          <h2 className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-400">Status</h2>
          {showLongJobChrome ? (
            <div className="space-y-2 rounded-xl border border-zinc-200/90 bg-zinc-50/40 p-4 shadow-sm ring-1 ring-zinc-900/[0.02]">
              <p className="text-[11px] leading-relaxed text-zinc-500">
                DraftLens is still working. Please don&apos;t close or refresh this page. This step can take longer for
                larger documents; you can review results when processing completes.
              </p>
              <div className="mt-1 space-y-1.5">
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-200/90">
                  <div
                    className="h-full rounded-full bg-zinc-900 transition-[width] duration-300 ease-out"
                    style={{ width: `${Math.min(100, Math.max(1, progressPct || 1))}%` }}
                  />
                </div>
                <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-1 text-[11px] text-zinc-500">
                  <span className="min-w-0 flex-1 truncate text-zinc-700">
                    {liveStage
                      ? typeof liveStage.message === "string" && liveStage.message.trim()
                        ? liveStage.message.trim()
                        : stageLabel(liveStage.stage)
                      : "Starting…"}
                  </span>
                  <span className="flex shrink-0 items-center gap-2 tabular-nums text-zinc-600">
                    <span>{Math.min(100, progressPct || 0)}%</span>
                    {latestCycleNumber != null ? (
                      <span className="font-normal text-zinc-500">Cycle {latestCycleNumber}</span>
                    ) : null}
                  </span>
                </div>
              </div>
            </div>
          ) : null}
          {!showLongJobChrome && log.length > 0 ? (
            <div className="flex flex-wrap items-baseline justify-between gap-2 rounded-xl border border-zinc-200/85 bg-white/85 px-3 py-2.5 text-[11px] text-zinc-600 shadow-sm ring-1 ring-zinc-900/[0.02]">
              <span className="shrink-0 text-zinc-400">Latest</span>
              <span className="min-w-0 flex-1 truncate text-zinc-800">
                {liveStage
                  ? typeof liveStage.message === "string" && liveStage.message.trim()
                    ? liveStage.message.trim()
                    : stageLabel(liveStage.stage)
                  : "—"}
              </span>
              <span className="shrink-0 tabular-nums text-zinc-600">{Math.min(100, progressPct || 0)}%</span>
              {latestCycleNumber != null ? (
                <span className="shrink-0 text-zinc-500">Cycle {latestCycleNumber}</span>
              ) : null}
            </div>
          ) : null}
          {chips.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {chips.map((c) => (
                <span
                  key={c.key}
                  className="rounded-full bg-white px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-zinc-500 ring-1 ring-zinc-200/80"
                >
                  {c.label}
                </span>
              ))}
            </div>
          ) : null}
          {(debateProgress.before !== null || debateProgress.after !== null) && (
            <p className="text-[11px] text-zinc-500">
              Conflicts {debateProgress.before ?? "—"} → {debateProgress.after ?? "—"}
            </p>
          )}
          {log.length > 0 ? (
            <details className="rounded-xl border border-zinc-200/85 bg-white/70 text-xs text-zinc-600 shadow-sm ring-1 ring-zinc-900/[0.02]">
              <summary className="cursor-pointer select-none px-3 py-2.5 font-medium text-zinc-700 marker:text-zinc-400">
                View full process log ({log.length} {log.length === 1 ? "step" : "steps"})
              </summary>
              <ol className="max-h-52 space-y-2.5 overflow-y-auto border-t border-zinc-100 px-3 py-3 pl-6">
                {log.map((ev, i) => (
                  <li key={`${i}-${ev.stage}-${ev.ts ?? ""}`} className="relative text-xs leading-relaxed text-zinc-600">
                    <span className="font-medium text-zinc-800">{stageLabel(ev.stage)}</span>
                    {ev.message ? <span className="text-zinc-500"> · {ev.message}</span> : null}
                  </li>
                ))}
              </ol>
            </details>
          ) : !showLongJobChrome ? (
            <p className="text-xs text-zinc-400">Awaiting run.</p>
          ) : null}
        </section>

        <section className="mt-16 space-y-6 rounded-2xl border border-zinc-200/95 bg-white/80 p-5 shadow-sm ring-1 ring-zinc-900/[0.03] sm:p-6">
          <h2 className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-400">Summary</h2>
          {cloudSaveNotice ? (
            <div className="rounded-xl border border-emerald-200/80 bg-emerald-50/50 px-4 py-3 text-xs text-emerald-950 shadow-sm ring-1 ring-emerald-900/10">
              <p className="font-medium">Saved to {cloudSaveProviderLabel(cloudSaveNotice.provider)}</p>
              <p className="mt-0.5 text-emerald-900/90">{cloudSaveNotice.artifact}</p>
              {cloudSaveNotice.webUrl ? (
                <a
                  href={cloudSaveNotice.webUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-block font-medium text-emerald-900 underline decoration-emerald-300 underline-offset-2 hover:decoration-emerald-700"
                >
                  {cloudSavedOpenLinkLabel(cloudSaveNotice.provider)}
                </a>
              ) : (
                <p className="mt-2 text-emerald-800/90">Upload finished. Check your cloud folder if no link is shown.</p>
              )}
            </div>
          ) : null}
          {job ? (
            <div className="space-y-4 text-sm text-zinc-600">
              <p>
                <span className="text-zinc-400">Job</span>{" "}
                <span className="font-mono text-xs text-zinc-800">{job.id.slice(0, 8)}…</span>
                <span className="mx-2 text-zinc-300">·</span>
                <span className="text-zinc-800">{job.status}</span>
                <span className="mx-2 text-zinc-300">·</span>
                <span>{job.page_count} pp</span>
              </p>
              {job.retention_notice ? (
                <p className="text-[11px] leading-relaxed text-zinc-400">{job.retention_notice}</p>
              ) : null}
              {pr ? (
                <div className="space-y-3 rounded-2xl border border-zinc-200/90 bg-white/75 p-4 shadow-sm ring-1 ring-zinc-900/[0.03]">
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-zinc-700">Issues {pr.total_issues}</span>
                    {Object.entries(pr.stats_by_severity).map(([k, v]) => (
                      <span key={k} className="rounded-full bg-zinc-50 px-2 py-0.5 text-zinc-600">
                        {k} {v}
                      </span>
                    ))}
                  </div>
                  {Object.keys(pr.stats_by_category).length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(pr.stats_by_category).map(([k, v]) => (
                        <span key={k} className="text-[11px] text-zinc-500">
                          {k} {v}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  <p className="text-[11px] leading-relaxed text-zinc-600">
                    {pr.convergence_status === "PARTIAL_CONSENSUS" ? (
                      <>
                        <span className="font-medium text-zinc-800">Partial consensus reached</span>
                        {" — no material discrepancies among participating reviewers; "}
                        {"three-reviewer agreement was not obtained."}
                        {pr.stopped_due_to_provider_unavailable ? " · third reviewer unavailable for this job" : ""}
                      </>
                    ) : pr.convergence_status === "CONVERGENCE_REACHED" && pr.full_three_reviewer_consensus_achieved ? (
                      <>
                        <span className="font-medium text-zinc-800">Consensus reached across 3 reviewers</span>
                        {" — no material reviewer discrepancies remain."}
                      </>
                    ) : pr.convergence_status === "CONVERGENCE_REACHED" && pr.partial_consensus_only ? (
                      <>
                        <span className="font-medium text-zinc-800">Partial consensus reached</span>
                        {
                          " — convergence completed on participating reviewers, but full three-reviewer agreement was not achieved."
                        }
                      </>
                    ) : pr.convergence_status === "CONVERGENCE_REACHED" ? (
                      <>
                        <span className="font-medium text-zinc-800">Consensus reached</span>
                        {" — no material reviewer discrepancies remain on the configured reviewer panel."}
                      </>
                    ) : pr.stopped_with_remaining_discrepancies ? (
                      <>
                        <span className="font-medium text-zinc-800">Consensus incomplete</span>
                        {typeof pr.unresolved_material_discrepancy_count === "number"
                          ? ` · ${pr.unresolved_material_discrepancy_count} unresolved material discrepancy clusters`
                          : ""}
                        {pr.stopped_due_to_max_cycles ? " · stopped: max cycles" : ""}
                        {pr.stopped_due_to_quorum_loss ? " · stopped: reviewer quorum lost" : ""}
                        {pr.stopped_due_to_provider_unavailable ? " · stopped: provider unavailable" : ""}
                        {pr.stopped_due_to_fatal_arbiter_failure ? " · stopped: arbiter refresh failed" : ""}
                        {pr.convergence_failure_code === "THRASH_DETECTED" ? " · stopped: edit thrash" : ""}
                      </>
                    ) : pr.reviewer_full_consensus ?? pr.reviewer_success_count === 3 ? (
                      "Consensus reached across all three reviewer models."
                    ) : (
                      "Partial review — generated from available reviewers; consensus incomplete."
                    )}
                    {pr.pdf_conversion_notes && pr.pdf_conversion_notes.length > 0 ? (
                      <span className="mt-1 block text-zinc-500">{pr.pdf_conversion_notes.join(" · ")}</span>
                    ) : null}
                    {job.output_mode === "review" && pr.artifact_pdf_flags && Object.keys(pr.artifact_pdf_flags).length > 0 ? (
                      <span className="mt-1 block text-[11px] text-zinc-500">
                        Delivered PDFs:{" "}
                        {Object.entries(pr.artifact_pdf_flags)
                          .filter(([, v]) => v)
                          .map(([k]) => k)
                          .join(", ") || "none"}
                      </span>
                    ) : null}
                    {pr.max_cycles_reached && pr.stopped_due_to_max_cycles ? (
                      <span className="mt-1 block text-[11px] text-zinc-500">
                        Stopped at max convergence cycles
                        {typeof pr.unresolved_material_discrepancy_count === "number"
                          ? ` · ${pr.unresolved_material_discrepancy_count} open material discrepancy clusters`
                          : ""}
                      </span>
                    ) : null}
                    {pr.unresolved_cluster_summaries && pr.unresolved_cluster_summaries.length > 0 ? (
                      <span className="mt-1 block text-[11px] text-zinc-500">
                        Sample unresolved clusters:{" "}
                        {pr.unresolved_cluster_summaries
                          .slice(0, 4)
                          .map((c) => String(c.cluster_id ?? "—"))
                          .join(", ")}
                        {pr.unresolved_cluster_summaries.length > 4 ? "…" : ""}
                      </span>
                    ) : null}
                    {typeof pr.cycle_count_completed === "number" && pr.cycle_count_completed > 1 ? (
                      <span className="block pt-1 text-zinc-500">
                        Convergence cycles completed: {pr.cycle_count_completed}
                        {pr.convergence_status ? ` · ${pr.convergence_status}` : ""}
                      </span>
                    ) : null}
                    {job.output_mode === "fix" && pr && typeof pr.fix_alignment_audit_passed === "boolean" ? (
                      <span className="block pt-1 text-zinc-500">
                        {pr.fix_alignment_audit_passed
                          ? "Fix Mode: corrected document validated against the final ledger (alignment audit passed)."
                          : "Fix Mode: alignment audit did not pass — corrected output is a best-effort draft, not a fully validated fix."}
                      </span>
                    ) : null}
                    {pr.max_cycles_reached && job.output_mode === "fix" ? (
                      <span className="block pt-1 text-zinc-500">
                        Corrected draft generated — additional human review recommended
                        {typeof pr.unresolved_material_issue_count === "number"
                          ? ` · ${pr.unresolved_material_issue_count} material issues remain`
                          : ""}
                      </span>
                    ) : null}
                  </p>
                  <p className="text-[11px] text-zinc-500">
                    Human follow-up {pr.unresolved_human_evidence.length} · Evidence queue{" "}
                    <span className="text-zinc-800">{pr.consensus_reached ? "clear" : "open"}</span>
                  </p>
                </div>
              ) : null}
              {job.status === "completed" &&
              job.output_mode === "review" &&
              hasReviewFixSeed &&
              !job.error_message ? (
                <div className="rounded-2xl border border-zinc-200/85 bg-white/85 p-4 shadow-sm ring-1 ring-zinc-900/[0.03]">
                  {pr?.partial_consensus_only || pr?.full_three_reviewer_consensus_achieved === false ? (
                    <p className="mb-3 text-[11px] leading-relaxed text-zinc-500">
                      Review ended without full three‑reviewer agreement on every issue. You can still request a
                      corrected draft; Fix Mode will label results honestly and run full validation afterward.
                    </p>
                  ) : null}
                  <button
                    type="button"
                    disabled={running}
                    onClick={() => void runApplyFixes()}
                    className="w-full rounded-xl bg-zinc-900 py-2.5 text-xs font-medium text-white transition hover:bg-zinc-800 disabled:opacity-40"
                  >
                    Apply fixes
                  </button>
                  <p className="mt-2 text-center text-[10px] leading-relaxed text-zinc-400">
                    Builds a corrected document from this review, then runs tri‑review, discrepancy handling, and a
                    final alignment audit before outputs finalize.
                  </p>
                </div>
              ) : null}
              {job.output_mode === "fix" && job.apply_fixes_honesty_notice ? (
                <p className="text-[11px] leading-relaxed text-zinc-500">{job.apply_fixes_honesty_notice}</p>
              ) : null}
              {job.output_mode === "fix" && job.post_review_fix_seed_job_id ? (
                <p className="text-[11px] text-zinc-500">
                  Derived from review{" "}
                  <span className="font-mono text-zinc-700">{job.post_review_fix_seed_job_id.slice(0, 8)}…</span>
                </p>
              ) : null}
              {job.error_message ? (
                <div className="space-y-2">
                  <p className="text-xs text-red-700">{job.error_message}</p>
                  <button
                    type="button"
                    className="text-xs font-medium text-zinc-900 underline"
                    onClick={() => void run()}
                  >
                    Retry
                  </button>
                </div>
              ) : null}
            </div>
          ) : (
            <p className="text-xs text-zinc-400">Results appear when a run finishes.</p>
          )}

          {job && artifactSplit.primary.length > 0 ? (
            <div className="space-y-3">
              <div className="grid gap-2 sm:grid-cols-2">
                {artifactSplit.primary.map((a) => (
                  <div
                    key={a.name}
                    className="flex flex-col overflow-hidden rounded-2xl border border-zinc-200/90 bg-white shadow-sm ring-1 ring-zinc-900/[0.04] transition hover:ring-zinc-300"
                  >
                    <a
                      href={artifactDownloadUrl(job.id, a.name)}
                      className="flex flex-col p-4 text-sm text-zinc-800"
                    >
                      <span className="font-medium">{a.name}</span>
                      <span className="mt-2 text-[11px] text-zinc-400">Download</span>
                    </a>
                    {cloudCfg &&
                    (cloudCfg.google_client_id ||
                      cloudCfg.google_picker_api_key ||
                      cloudCfg.dropbox_app_key ||
                      cloudCfg.microsoft_client_id) &&
                    !a.name.endsWith(".json") ? (
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-zinc-100 px-4 py-2 text-[10px] text-zinc-500">
                        <span className="text-zinc-400">Save as new file</span>
                        {cloudCfg.google_client_id && cloudCfg.google_picker_api_key ? (
                          <button
                            type="button"
                            title="Save corrected output to Google Drive"
                            aria-label="Save corrected output to Google Drive"
                            className="underline decoration-zinc-300 underline-offset-2 hover:text-zinc-800"
                            onClick={() => void runCloudExport(job.id, a.name, "google_drive")}
                          >
                            Save to Drive
                          </button>
                        ) : null}
                        {cloudCfg.dropbox_app_key ? (
                          <button
                            type="button"
                            title="Save as a new file in Dropbox"
                            aria-label="Save as a new file in Dropbox"
                            className="underline decoration-zinc-300 underline-offset-2 hover:text-zinc-800"
                            onClick={() => void runCloudExport(job.id, a.name, "dropbox")}
                          >
                            Save to Dropbox
                          </button>
                        ) : null}
                        {cloudCfg.microsoft_client_id ? (
                          <button
                            type="button"
                            title="Save as a new file in OneDrive"
                            aria-label="Save as a new file in OneDrive"
                            className="underline decoration-zinc-300 underline-offset-2 hover:text-zinc-800"
                            onClick={() => void runCloudExport(job.id, a.name, "onedrive")}
                          >
                            Save to OneDrive
                          </button>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
              {artifactSplit.advanced.length > 0 ? (
                <details className="rounded-xl border border-zinc-200/85 bg-white/70 px-3 py-2 text-xs text-zinc-600 shadow-sm ring-1 ring-zinc-900/[0.02]">
                  <summary className="cursor-pointer select-none font-medium text-zinc-700">
                    Advanced artifacts
                  </summary>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {artifactSplit.advanced.map((a) => (
                      <a
                        key={a.name}
                        href={artifactDownloadUrl(job.id, a.name)}
                        className="flex flex-col rounded-xl bg-white p-3 text-xs text-zinc-800 ring-1 ring-zinc-200/80"
                      >
                        <span className="font-medium">{a.name}</span>
                        <span className="mt-1 text-[10px] text-zinc-400">Download</span>
                      </a>
                    ))}
                  </div>
                </details>
              ) : null}
            </div>
          ) : null}

          <p className="text-[11px] leading-relaxed text-zinc-400">
            {disclaimerCopy?.third_party_models ?? "Suggested edits may require human verification."}
          </p>
          {showAccuracyNote && disclaimerCopy?.accuracy_context_note ? (
            <p className="text-[11px] leading-relaxed text-zinc-400">{disclaimerCopy.accuracy_context_note}</p>
          ) : null}
        </section>
      </main>
    </div>
  );
}
