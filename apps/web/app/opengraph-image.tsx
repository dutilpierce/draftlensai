import { readFileSync } from "fs";
import { join } from "path";
import { ImageResponse } from "next/og";

export const alt = "DraftLens — multi-model document review";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/** OG images read local assets; Node required for `fs`. */
export const runtime = "nodejs";

export default function OpenGraphImage() {
  const logoPath = join(process.cwd(), "public", "brand", "draftlens-logo.png");
  const logo = readFileSync(logoPath);
  const logoSrc = `data:image/png;base64,${logo.toString("base64")}`;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          justifyContent: "center",
          gap: 28,
          padding: 72,
          background: "linear-gradient(145deg, #fafafa 0%, #ececec 45%, #e4e4e4 100%)",
          color: "#12151b",
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- next/og ImageResponse requires img */}
        <img src={logoSrc} alt="" height={140} width={560} style={{ height: 140, width: "auto", maxWidth: 640 }} />
        <div style={{ fontSize: 28, color: "#3a4354", maxWidth: 920, lineHeight: 1.35 }}>
          Multi-model document review for DOCX & PDF — structured findings, review or fix mode.
        </div>
      </div>
    ),
    { ...size },
  );
}
