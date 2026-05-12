/**
 * Aggregates MODEL_REVIEW_* SSE stages into one chip per logical provider.
 * A later failure must not overwrite an earlier successful pass (complete wins).
 */

export type ReviewerChip = { key: string; label: string };

type ProviderKey = "anthropic" | "openai" | "google";

function providerFromStage(stage: string): ProviderKey | null {
  if (stage.includes("_CLAUDE_")) return "anthropic";
  if (stage.includes("_GPT_")) return "openai";
  if (stage.includes("_GEMINI_")) return "google";
  return null;
}

type AggState = "running" | "failed" | "skipped" | "unavailable" | "complete";

export function aggregateReviewerChips(
  log: readonly { stage: string; detail?: Record<string, unknown> }[],
): ReviewerChip[] {
  const st = new Map<ProviderKey, AggState>();
  const lb = new Map<ProviderKey, string>();

  for (const ev of log) {
    const stage = ev.stage;
    if (!stage.startsWith("MODEL_REVIEW_")) continue;
    const p = providerFromStage(stage);
    if (!p) continue;
    const mid = typeof ev.detail?.model_id === "string" ? ev.detail.model_id : "";
    const short = mid.includes("/") ? mid.split("/").slice(-2).join("/") : mid;
    const ec = typeof ev.detail?.error_code === "string" ? ev.detail.error_code : "";

    if (stage.endsWith("_COMPLETE")) {
      st.set(p, "complete");
      lb.set(p, `${p} · ${short || "—"} · complete`);
      continue;
    }
    if (stage.endsWith("_FAILED")) {
      if (st.get(p) === "complete") continue;
      if (ec === "not_configured") {
        st.set(p, "skipped");
        lb.set(p, `${p} · skipped`);
      } else if (ec === "GEMINI_DISABLED") {
        st.set(p, "skipped");
        lb.set(p, `${p} · disabled`);
      } else if (ec === "GEMINI_UNAVAILABLE" || ec === "RATE_LIMIT_EXHAUSTED" || ec === "GEMINI_RATE_LIMITED") {
        st.set(p, "unavailable");
        lb.set(p, `${p} · unavailable`);
      } else if (ec === "GEMINI_SERVICE_UNAVAILABLE") {
        st.set(p, "unavailable");
        lb.set(p, `${p} · Gemini temporarily unavailable`);
      } else if (ec === "OPENAI_RATE_LIMITED") {
        st.set(p, "unavailable");
        lb.set(p, `${p} · GPT rate-limited`);
      } else if (ec === "OPENAI_UNAVAILABLE") {
        st.set(p, "unavailable");
        lb.set(p, `${p} · GPT unavailable for job`);
      } else {
        st.set(p, "failed");
        lb.set(p, `${p} · ${short || "—"} · failed`);
      }
      continue;
    }
    if (stage.endsWith("_STARTED")) {
      const cur = st.get(p);
      if (cur === "complete" || cur === "failed" || cur === "skipped" || cur === "unavailable") {
        continue;
      }
      st.set(p, "running");
      lb.set(p, `${p} · ${short || "—"} · running`);
    }
  }

  const order: ProviderKey[] = ["anthropic", "openai", "google"];
  return order.filter((k) => st.has(k)).map((k) => ({ key: k, label: lb.get(k)! }));
}
