import Image from "next/image";

/** Canonical brand asset (source: user-provided PNG in `public/brand/`). */
export const BRAND_LOGO_SRC = "/brand/draftlens-logo.png";

/** Intrinsic size of `draftlens-logo.png` (2508×627); layout uses proportional display sizes. */
const ASPECT = 2508 / 627;

const sizeMap = {
  sm: { w: 200, h: Math.round(200 / ASPECT), className: "h-8 w-auto max-w-[min(220px,50vw)] sm:h-9" },
  md: { w: 240, h: Math.round(240 / ASPECT), className: "h-10 w-auto max-w-[min(260px,85vw)] sm:h-11" },
  lg: { w: 288, h: Math.round(288 / ASPECT), className: "h-11 w-auto max-w-[min(300px,90vw)] sm:h-12" },
} as const;

export type DraftLensLogoSize = keyof typeof sizeMap;

/**
 * Renders the official DraftLens horizontal logo (PNG).
 * `variant="mark"` uses the same asset at a compact size (no separate icon file).
 */
export function DraftLensLogo({
  variant = "full",
  size = "md",
  className = "",
  priority = false,
}: {
  variant?: "full" | "mark";
  size?: DraftLensLogoSize;
  className?: string;
  /** Set true for above-the-fold headers (LCP). */
  priority?: boolean;
}) {
  const key = variant === "mark" ? "sm" : size;
  const dim = sizeMap[key];
  return (
    <span className={`inline-flex items-center ${className}`}>
      <Image
        src={BRAND_LOGO_SRC}
        alt="DraftLens"
        width={dim.w}
        height={dim.h}
        className={dim.className}
        priority={priority}
        sizes={`${dim.w}px`}
      />
    </span>
  );
}
