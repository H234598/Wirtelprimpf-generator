import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const root = new URL("../src/", import.meta.url);
const layout = readFileSync(new URL("layouts/BaseLayout.astro", root), "utf8");
const settings = readFileSync(new URL("components/SettingsPanel.astro", root), "utf8");
const chat = readFileSync(new URL("components/CatGptWidget.astro", root), "utf8");
const styles = readFileSync(new URL("styles/global.css", root), "utf8");

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

test("base layout mounts an accessible static CatGPT on every page", () => {
  assert.match(layout, /import CatGptWidget/);
  assert.match(layout, /<CatGptWidget\s*\/>/);
  assert.match(layout, /connect-src 'none'/);
  assert.match(chat, /aria-controls="wirtelprimpf-catgpt"/);
  assert.match(chat, /role="dialog"/);
  assert.match(chat, /aria-live="polite"/);
  assert.match(chat, /maxlength="1000"/);
  assert.match(chat, /textContent/);
  assert.doesNotMatch(chat, /innerHTML/);
  assert.doesNotMatch(chat, /fetch\s*\(/);
});

test("CatGPT keeps its composer visible in short viewports", () => {
  assert.match(styles, /\.catgpt-window \{[^}]*display: flex;[^}]*flex-direction: column;/s);
  assert.match(styles, /\.catgpt-messages \{[^}]*min-height: 0;[^}]*flex: 1;/s);
  assert.doesNotMatch(styles, /\.catgpt-messages \{[^}]*max-height: 24rem;/s);
});
