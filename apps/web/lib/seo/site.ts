/**
 * Canonical site URL for metadata, sitemap, and JSON-LD.
 * Set NEXT_PUBLIC_SITE_URL in production (no trailing slash).
 */
export function getSiteUrl(): string {
  const raw = process.env.NEXT_PUBLIC_SITE_URL?.trim();
  if (raw) return raw.replace(/\/+$/, "");
  return "https://draftlens.app";
}

export function absoluteUrl(path: string): string {
  const base = getSiteUrl();
  if (!path || path === "/") return `${base}/`;
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}

export const BRAND = {
  name: "DraftLens",
  tagline: "Multi-model document review for serious drafts.",
  /** Absolute logo URL for JSON-LD; env overrides hosted asset. Defaults to `/brand/draftlens-logo.png`. */
  logoUrl: process.env.NEXT_PUBLIC_ORGANIZATION_LOGO_URL?.trim() || "",
  emailPlaceholder: process.env.NEXT_PUBLIC_CONTACT_EMAIL?.trim() || "",
} as const;

export function brandLogoAbsoluteUrl(): string {
  const env = process.env.NEXT_PUBLIC_ORGANIZATION_LOGO_URL?.trim();
  if (env) return env;
  return absoluteUrl("/brand/draftlens-logo.png");
}
