import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";


const css = readFileSync(join(process.cwd(), "src/styles/global.css"), "utf8");


test("visual contract keeps stable type, focus and motion rules", () => {
  assert.doesNotMatch(css, /font-size:\s*clamp\(/);
  assert.doesNotMatch(css, /letter-spacing:\s*-\s*[0-9]/);
  assert.match(css, /:focus-visible\s*\{/);
  assert.match(css, /prefers-reduced-motion/);
  assert.doesNotMatch(css, /radial-gradient\(/);
  assert.doesNotMatch(css, /@import[^;]*https?:/);
});
