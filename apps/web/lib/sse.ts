import { apiUrl } from "./api";

export type SseEvent = {
  stage: string;
  message: string;
  detail: Record<string, unknown>;
  ts?: string | null;
};

function parseSseBlock(block: string): SseEvent | null {
  const lines = block.split("\n");
  for (const line of lines) {
    if (line.startsWith("data:")) {
      const raw = line.slice(5).trim();
      try {
        return JSON.parse(raw) as SseEvent;
      } catch {
        return { stage: "SSE_PARSE_ERROR", message: raw, detail: {} };
      }
    }
  }
  return null;
}

export async function* streamJobEvents(jobId: string, signal?: AbortSignal): AsyncGenerator<SseEvent> {
  const res = await fetch(apiUrl(`/api/jobs/${jobId}/events`), {
    method: "GET",
    headers: { Accept: "text/event-stream" },
    credentials: "include",
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`events_failed_${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      if (!part.trim()) continue;
      const ev = parseSseBlock(part);
      if (ev) yield ev;
    }
  }
}
