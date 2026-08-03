import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const root = new URL("../src/", import.meta.url);
const layout = readFileSync(new URL("layouts/BaseLayout.astro", root), "utf8");
const settings = readFileSync(new URL("components/SettingsPanel.astro", root), "utf8");

test("base layout replaces theme shortcut with accessible settings panel", () => {
  assert.match(layout, /import SettingsPanel/);
  assert.match(layout, /<SettingsPanel\s*\/>/);
  assert.doesNotMatch(layout, /data-theme-toggle/);
  assert.match(settings, /aria-controls="wirtelprimpf-settings"/);
  assert.match(settings, /role="dialog"/);
  assert.match(settings, /role="switch"/);
  assert.match(settings, /bald verfügbar/);
  assert.match(settings, /data-catgpt-mode[^>]*disabled/s);
});
