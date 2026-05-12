/**
 * Run from apps/web: npm run validate-seo
 * Validates PAGE_REGISTRY, sitemap parity, and robots.txt source references sitemap.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import sitemap from "../app/sitemap";
import { INDEXABLE_PATHS, validateRegistry } from "../lib/seo/registry";
import { absoluteUrl } from "../lib/seo/site";

function main() {
  const reg = validateRegistry();
  if (!reg.ok) {
    console.error("[validate-seo] registry errors:\n" + reg.errors.join("\n"));
    process.exit(1);
  }

  const entries = sitemap();
  if (entries.length !== INDEXABLE_PATHS.length) {
    console.error(
      `[validate-seo] sitemap length ${entries.length} !== registry paths ${INDEXABLE_PATHS.length}`,
    );
    process.exit(1);
  }

  const urls = new Set(entries.map((e) => e.url));
  for (const path of INDEXABLE_PATHS) {
    const expected = absoluteUrl(path);
    if (!urls.has(expected)) {
      console.error(`[validate-seo] missing sitemap URL for ${path}: expected ${expected}`);
      process.exit(1);
    }
  }

  const robotsSrc = readFileSync(join(process.cwd(), "app", "robots.ts"), "utf8");
  if (!robotsSrc.includes("sitemap.xml")) {
    console.error("[validate-seo] app/robots.ts must reference sitemap.xml");
    process.exit(1);
  }

  console.log("[validate-seo] OK —", INDEXABLE_PATHS.length, "indexable URLs");
}

main();
