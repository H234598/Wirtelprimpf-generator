import { defineConfig } from "astro/config";

const defaultSite = "https://wirtelprimpf.telacore.org";
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
