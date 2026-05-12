import { NextResponse } from "next/server";
import type { FeedbackSubmission } from "@/lib/feedback/types";

const MAX = { featureRequest: 4000, workflowType: 500, painPoint: 4000, email: 254 };

function trim(s: unknown, max: number): string {
  if (typeof s !== "string") return "";
  return s.trim().slice(0, max);
}

/**
 * Marketing feedback stub — safe default: accepts JSON, validates shape, optional outbound webhook.
 * Wire `FEEDBACK_WEBHOOK_URL` (e.g. Slack incoming webhook) or replace with DB/email without touching `/app`.
 */
export async function POST(req: Request) {
  let raw: unknown;
  try {
    raw = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "Expected JSON body." }, { status: 400 });
  }

  if (!raw || typeof raw !== "object") {
    return NextResponse.json({ ok: false, error: "Invalid payload." }, { status: 400 });
  }

  const b = raw as Record<string, unknown>;
  const featureRequest = trim(b.featureRequest, MAX.featureRequest);
  const workflowType = trim(b.workflowType, MAX.workflowType);
  const painPoint = trim(b.painPoint, MAX.painPoint);
  const email = trim(b.email, MAX.email);

  if (!featureRequest || featureRequest.length < 8) {
    return NextResponse.json(
      { ok: false, error: "Please describe the feature or outcome in a few more words." },
      { status: 400 },
    );
  }
  if (!workflowType || workflowType.length < 2) {
    return NextResponse.json(
      { ok: false, error: "Please add a short document or workflow label." },
      { status: 400 },
    );
  }
  if (!painPoint || painPoint.length < 8) {
    return NextResponse.json(
      { ok: false, error: "Please share what is getting in the way today." },
      { status: 400 },
    );
  }

  const payload: FeedbackSubmission = { featureRequest, workflowType, painPoint, email: email || undefined };

  const webhook = process.env.FEEDBACK_WEBHOOK_URL?.trim();
  if (webhook) {
    const text = [
      "*DraftLens marketing feedback*",
      `*Feature / outcome:* ${featureRequest}`,
      `*Workflow:* ${workflowType}`,
      `*Pain:* ${painPoint}`,
      email ? `*Contact:* ${email}` : "_No email provided_",
    ].join("\n");
    try {
      const r = await fetch(webhook, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!r.ok) {
        console.warn("[feedback] webhook non-OK", r.status);
      }
    } catch (e) {
      console.warn("[feedback] webhook failed", e);
    }
  } else if (process.env.NODE_ENV !== "production") {
    console.info("[feedback] submission (dev, no FEEDBACK_WEBHOOK_URL)", payload);
  }

  return NextResponse.json({ ok: true });
}
