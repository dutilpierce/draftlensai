import type { Metadata } from "next";
import type { RegisteredPage } from "./types";
import { absoluteUrl, getSiteUrl } from "./site";

function stripQueryAndHash(path: string): string {
  const [p] = path.split(/[?#]/);
  return p || "/";
}

/**
 * Builds Next.js Metadata with a single canonical URL (no query params).
 */
export function publicMetadata(page: RegisteredPage): Metadata {
  const canonicalPath = stripQueryAndHash(page.canonicalPath || page.path);
  const url = absoluteUrl(canonicalPath);
  const site = getSiteUrl();

  return {
    title: page.title,
    description: page.description,
    alternates: { canonical: url },
    openGraph: {
      type: page.schemaProfile === "article" ? "article" : "website",
      url,
      siteName: "DraftLens",
      title: page.title,
      description: page.description,
      locale: "en_US",
      ...(page.lastModified ? { publishedTime: page.lastModified } : {}),
    },
    twitter: {
      card: "summary_large_image",
      title: page.title,
      description: page.description,
    },
    robots: { index: true, follow: true },
    metadataBase: new URL(site),
  };
}
