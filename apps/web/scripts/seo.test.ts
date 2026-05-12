/**
 * Run from apps/web: npm run test:seo
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import sitemap from "../app/sitemap";
import { INDEXABLE_PATHS, validateRegistry } from "../lib/seo/registry";
import { absoluteUrl } from "../lib/seo/site";

test("PAGE_REGISTRY passes validateRegistry()", () => {
  const r = validateRegistry();
  assert.ok(r.ok, r.errors.join("\n"));
});

test("sitemap lists exactly one URL per indexable path", () => {
  const entries = sitemap();
  assert.equal(entries.length, INDEXABLE_PATHS.length);
  const set = new Set(entries.map((e) => e.url));
  for (const path of INDEXABLE_PATHS) {
    assert.ok(set.has(absoluteUrl(path)), `missing ${path}`);
  }
});

test("robots.ts references sitemap and disallows /app", () => {
  const src = readFileSync(join(process.cwd(), "app", "robots.ts"), "utf8");
  assert.match(src, /sitemap\.xml/);
  assert.match(src, /\/app/);
});
