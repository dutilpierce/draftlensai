import type { MetadataRoute } from "next";
import { INDEXABLE_PATHS, PAGE_REGISTRY } from "@/lib/seo/registry";
import { absoluteUrl } from "@/lib/seo/site";

export default function sitemap(): MetadataRoute.Sitemap {
  return INDEXABLE_PATHS.map((path) => {
    const page = PAGE_REGISTRY[path]!;
    return {
      url: absoluteUrl(path),
      lastModified: page.lastModified ? new Date(page.lastModified) : new Date(),
      changeFrequency: path.startsWith("/research") || path.startsWith("/academy") ? "monthly" : "weekly",
      priority: path === "/" ? 1 : path === "/product" || path === "/pricing" ? 0.9 : 0.7,
    };
  });
}
