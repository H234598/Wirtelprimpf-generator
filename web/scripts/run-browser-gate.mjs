import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";


const patterns = {
  accessibility: "axe|lightbox opens progressively|reader supports reduced motion|keyboard entry points",
  comfort: "comfort state|storage failure|paper theme",
  downloads: "media actions",
  "error-states": "empty filters|failed media|quiet fallback",
  "full-story": "reader|chapter deep links",
  gallery: "gallery return|empty filters|no JavaScript",
  "gallery-filters": "empty filters",
  "gallery-return": "gallery return",
  homepage: "core routes",
  "image-detail": "core routes",
  lightbox: "lightbox",
  maintenance: "maintenance pages",
  "no-js": "no JavaScript|chapter deep links",
  reader: "reader|chapter deep links",
  responsive: "tablet and desktop layouts|320 pixel|mobile main navigation|P08 visual sample",
  seo: "seo routes",
  "story-library": "core routes|chapter deep links",
  "visual-sample": "P08 visual sample",
};

const gate = process.argv[2];
if (gate && !Object.hasOwn(patterns, gate)) {
  console.error(`unknown browser gate: ${gate}`);
  process.exit(2);
}

const playwright = join(process.cwd(), "node_modules", ".bin", process.platform === "win32" ? "playwright.cmd" : "playwright");
if (!existsSync(playwright)) {
  console.error("playwright binary is missing; run npm ci first");
  process.exit(2);
}

const args = ["test", "tests/browser"];
if (gate) args.push("--grep", patterns[gate]);
const result = spawnSync(playwright, args, { stdio: "inherit" });
process.exit(result.status ?? 1);
