import { defineConfig } from "astro/config";

const profile = process.env.WIRTELPRIMPF_SITE_PROFILE === "archive" ? "archive" : "hub";
const defaultSite = profile === "hub"
  ? "https://wirtelprimpf.telacore.org"
  : "https://wirtelprimpf-0001.telacore.org";
const outputDir = process.env.WIRTELPRIMPF_OUTPUT_DIR;

export default defineConfig({
  output: "static",
  site: process.env.WIRTELPRIMPF_SITE_URL || defaultSite,
  ...(outputDir ? { outDir: outputDir } : {}),
  build: {
    assets: "_assets",
    inlineStylesheets: "auto"
  },
  vite: {
    build: {
      cssMinify: "lightningcss"
    }
  }
});
