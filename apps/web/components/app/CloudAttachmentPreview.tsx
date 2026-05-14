"use client";

import { useState } from "react";

export type CloudAttachment = {
  handle: string;
  label: string;
  provider: "google_drive" | "dropbox" | "onedrive";
  filename: string;
  mimeType?: string | null;
  thumbnailUrl?: string | null;
  iconUrl?: string | null;
  webViewLink?: string | null;
};

function providerLabel(p: CloudAttachment["provider"]): string {
  if (p === "google_drive") return "Google Drive";
  if (p === "dropbox") return "Dropbox";
  return "OneDrive";
}

export type CloudFileKind = "pdf" | "docx" | "gdoc" | "text" | "doc" | "unknown";

export function cloudFileKind(mime: string | null | undefined, filename: string): CloudFileKind {
  const m = (mime || "").toLowerCase();
  const fn = filename.toLowerCase();
  if (m === "application/pdf" || fn.endsWith(".pdf")) return "pdf";
  if (m.includes("wordprocessingml") || fn.endsWith(".docx")) return "docx";
  if (m.includes("msword") || fn.endsWith(".doc")) return "doc";
  if (m === "application/vnd.google-apps.document") return "gdoc";
  if ((m.startsWith("text/") && m !== "text/html") || fn.endsWith(".txt") || fn.endsWith(".md")) return "text";
  return "unknown";
}

function KindBadge({ kind }: { kind: CloudFileKind }) {
  const map: Record<CloudFileKind, { short: string; className: string }> = {
    pdf: { short: "PDF", className: "bg-red-500/10 text-red-800 ring-red-500/15" },
    docx: { short: "DOCX", className: "bg-blue-500/10 text-blue-900 ring-blue-500/15" },
    gdoc: { short: "GDoc", className: "bg-indigo-500/10 text-indigo-900 ring-indigo-500/15" },
    text: { short: "Text", className: "bg-zinc-500/10 text-zinc-700 ring-zinc-400/20" },
    doc: { short: "DOC", className: "bg-blue-500/10 text-blue-900 ring-blue-500/15" },
    unknown: { short: "File", className: "bg-zinc-400/10 text-zinc-600 ring-zinc-300/25" },
  };
  const x = map[kind];
  return (
    <span className={`inline-flex shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-semibold tracking-wide ring-1 ${x.className}`}>
      {x.short}
    </span>
  );
}

function TypeLine({ mime, filename }: { mime: string | null | undefined; filename: string }) {
  const kind = cloudFileKind(mime, filename);
  const ext = filename.includes(".") ? filename.split(".").pop()?.toUpperCase() : "";
  const mimeShort = mime && mime.length < 44 ? mime : null;
  return (
    <div className="mt-0.5 flex flex-wrap items-center gap-2">
      <KindBadge kind={kind} />
      {mimeShort ? (
        <span className="truncate text-[10px] text-zinc-400">{mimeShort}</span>
      ) : ext && kind === "unknown" ? (
        <span className="text-[10px] text-zinc-400">{ext}</span>
      ) : null}
    </div>
  );
}

function ThumbnailOrFallback({
  thumbnailUrl,
  mime,
  filename,
}: {
  thumbnailUrl: string | null | undefined;
  mime: string | null | undefined;
  filename: string;
}) {
  const [broken, setBroken] = useState(false);
  const kind = cloudFileKind(mime, filename);
  const trimmed = (thumbnailUrl || "").trim();
  const showImg = Boolean(trimmed) && !broken;
  if (showImg) {
    return (
      <img
        src={trimmed}
        alt=""
        className="h-14 w-24 shrink-0 rounded-lg border border-zinc-200/80 bg-zinc-50 object-cover shadow-inner"
        onError={() => setBroken(true)}
      />
    );
  }
  return (
    <div className="flex h-14 w-24 shrink-0 flex-col items-center justify-center rounded-lg border border-dashed border-zinc-200/90 bg-gradient-to-br from-zinc-50 to-zinc-100/80 shadow-inner">
      <KindBadge kind={kind} />
    </div>
  );
}

export function MainCloudAttachmentCard(props: {
  attachment: CloudAttachment;
  running: boolean;
  onRemove: () => void;
  onChange: () => void;
}) {
  const { attachment, running, onRemove, onChange } = props;
  return (
    <div className="flex gap-3 rounded-2xl border border-zinc-200/85 bg-white/90 p-3 shadow-sm ring-1 ring-zinc-900/[0.03]">
      <ThumbnailOrFallback thumbnailUrl={attachment.thumbnailUrl} mime={attachment.mimeType} filename={attachment.filename} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-zinc-900" title={attachment.filename}>
          {attachment.filename}
        </p>
        <TypeLine mime={attachment.mimeType} filename={attachment.filename} />
        <p className="mt-1 text-[11px] text-zinc-500">{providerLabel(attachment.provider)}</p>
        <div className="mt-2 flex flex-wrap gap-3">
          <button
            type="button"
            disabled={running}
            className="text-[11px] font-medium text-zinc-600 underline decoration-zinc-300 underline-offset-2 hover:text-zinc-900 disabled:opacity-40"
            onClick={onChange}
          >
            Change
          </button>
          <button
            type="button"
            disabled={running}
            className="text-[11px] font-medium text-zinc-500 underline decoration-zinc-300 underline-offset-2 hover:text-zinc-800 disabled:opacity-40"
            onClick={onRemove}
          >
            Remove
          </button>
          {attachment.webViewLink && attachment.provider === "google_drive" ? (
            <a
              href={attachment.webViewLink}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[11px] font-medium text-zinc-600 underline decoration-zinc-300 underline-offset-2 hover:text-zinc-900"
            >
              Open in Drive
            </a>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function SupportingCloudAttachmentCard(props: {
  attachment: CloudAttachment;
  running: boolean;
  onRemove: () => void;
}) {
  const { attachment, running, onRemove } = props;
  return (
    <div className="flex gap-2.5 rounded-xl border border-zinc-200/80 bg-white/90 p-2.5 shadow-sm ring-1 ring-zinc-900/[0.02]">
      <ThumbnailOrFallback thumbnailUrl={attachment.thumbnailUrl} mime={attachment.mimeType} filename={attachment.filename} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[12px] font-medium text-zinc-900" title={attachment.filename}>
          {attachment.filename}
        </p>
        <TypeLine mime={attachment.mimeType} filename={attachment.filename} />
        <div className="mt-1 flex items-center justify-between gap-2">
          <span className="text-[10px] text-zinc-500">{providerLabel(attachment.provider)}</span>
          <button type="button" disabled={running} className="shrink-0 text-[11px] text-zinc-500 underline disabled:opacity-40" onClick={onRemove}>
            Remove
          </button>
        </div>
      </div>
    </div>
  );
}
