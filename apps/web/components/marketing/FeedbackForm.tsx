"use client";

import { useState, type FormEvent } from "react";

type Status = "idle" | "submitting" | "success" | "error";

export function FeedbackForm() {
  const [featureRequest, setFeatureRequest] = useState("");
  const [workflowType, setWorkflowType] = useState("");
  const [painPoint, setPainPoint] = useState("");
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setStatus("submitting");
    setMessage(null);
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          featureRequest,
          workflowType,
          painPoint,
          email: email.trim() || undefined,
        }),
      });
      const data = (await res.json().catch(() => ({}))) as { ok?: boolean; error?: string };
      if (!res.ok || !data.ok) {
        setStatus("error");
        setMessage(data.error ?? "Something went wrong. Please try again.");
        return;
      }
      setStatus("success");
      setMessage("Thank you. Your note is recorded—we read every submission.");
      setFeatureRequest("");
      setWorkflowType("");
      setPainPoint("");
      setEmail("");
    } catch {
      setStatus("error");
      setMessage("Network error. Check your connection and try again.");
    }
  }

  const disabled = status === "submitting" || status === "success";

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <div>
        <label htmlFor="fb-feature" className="block text-sm font-medium text-ink-900">
          What would you like DraftLens to do?
        </label>
        <p id="fb-feature-hint" className="mt-1 text-xs text-ink-500">
          New capability, integration, or output—be as concrete as you can.
        </p>
        <textarea
          id="fb-feature"
          name="featureRequest"
          required
          minLength={8}
          maxLength={4000}
          rows={4}
          value={featureRequest}
          onChange={(e) => setFeatureRequest(e.target.value)}
          disabled={disabled}
          aria-describedby="fb-feature-hint"
          className="mt-2 w-full rounded-xl border border-lineSubtle bg-surface-card/95 px-3 py-2.5 text-sm text-ink-900 shadow-sm outline-none ring-ink-900/10 placeholder:text-ink-400 focus:border-ink-400 focus:ring-2 disabled:opacity-60"
          placeholder="e.g. Export a partner-ready summary alongside the issue ledger…"
        />
      </div>

      <div>
        <label htmlFor="fb-workflow" className="block text-sm font-medium text-ink-900">
          Document or workflow type
        </label>
        <input
          id="fb-workflow"
          name="workflowType"
          type="text"
          required
          minLength={2}
          maxLength={500}
          value={workflowType}
          onChange={(e) => setWorkflowType(e.target.value)}
          disabled={disabled}
          className="mt-2 w-full rounded-xl border border-lineSubtle bg-surface-card/95 px-3 py-2.5 text-sm text-ink-900 shadow-sm outline-none ring-ink-900/10 placeholder:text-ink-400 focus:border-ink-400 focus:ring-2 disabled:opacity-60"
          placeholder="e.g. NDAs, grant proposals, policy memos, journal proofs…"
        />
      </div>

      <div>
        <label htmlFor="fb-pain" className="block text-sm font-medium text-ink-900">
          What&apos;s getting in the way today?
        </label>
        <p id="fb-pain-hint" className="mt-1 text-xs text-ink-500">
          Missing feature, confusing step, or a workflow DraftLens doesn&apos;t fit yet.
        </p>
        <textarea
          id="fb-pain"
          name="painPoint"
          required
          minLength={8}
          maxLength={4000}
          rows={4}
          value={painPoint}
          onChange={(e) => setPainPoint(e.target.value)}
          disabled={disabled}
          aria-describedby="fb-pain-hint"
          className="mt-2 w-full rounded-xl border border-lineSubtle bg-surface-card/95 px-3 py-2.5 text-sm text-ink-900 shadow-sm outline-none ring-ink-900/10 placeholder:text-ink-400 focus:border-ink-400 focus:ring-2 disabled:opacity-60"
          placeholder="Plain language is perfect—we’re not scoring writing style."
        />
      </div>

      <div>
        <label htmlFor="fb-email" className="block text-sm font-medium text-ink-900">
          Email <span className="font-normal text-ink-500">(optional)</span>
        </label>
        <p id="fb-email-hint" className="mt-1 text-xs text-ink-500">
          Only if you&apos;re open to a follow-up question—we won&apos;t add you to a list from this form alone.
        </p>
        <input
          id="fb-email"
          name="email"
          type="email"
          maxLength={254}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={disabled}
          aria-describedby="fb-email-hint"
          className="mt-2 w-full rounded-xl border border-lineSubtle bg-surface-card/95 px-3 py-2.5 text-sm text-ink-900 shadow-sm outline-none ring-ink-900/10 placeholder:text-ink-400 focus:border-ink-400 focus:ring-2 disabled:opacity-60"
          placeholder="you@company.com"
        />
      </div>

      {message ? (
        <p
          role="status"
          className={`text-sm ${status === "success" ? "text-ink-700" : "text-ink-800"}`}
        >
          {message}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={disabled}
          className="rounded-full bg-ink-950 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-ink-900 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {status === "submitting" ? "Sending…" : status === "success" ? "Sent" : "Send feedback"}
        </button>
        {status === "success" ? (
          <button
            type="button"
            className="text-sm font-medium text-ink-700 underline underline-offset-4"
            onClick={() => {
              setStatus("idle");
              setMessage(null);
            }}
          >
            Send another note
          </button>
        ) : null}
      </div>
    </form>
  );
}
