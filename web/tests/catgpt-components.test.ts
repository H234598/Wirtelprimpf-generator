import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { isValidChatContent } from "../src/lib/catgpt/types.ts";

const root = new URL("../src/", import.meta.url);
const layout = readFileSync(new URL("layouts/BaseLayout.astro", root), "utf8");
const settings = readFileSync(new URL("components/SettingsPanel.astro", root), "utf8");
const chat = readFileSync(new URL("components/CatGptWidget.astro", root), "utf8");
const styles = readFileSync(new URL("styles/global.css", root), "utf8");

test("base layout replaces theme shortcut with accessible settings panel", () => {
  assert.match(layout, /import SettingsPanel/);
  assert.match(layout, /<SettingsPanel\s+lightEndpoint=\{lightEndpoint\}\s*\/>/);
  assert.doesNotMatch(layout, /data-theme-toggle/);
  assert.match(settings, /aria-controls="wirtelprimpf-settings"/);
  assert.match(settings, /role="dialog"/);
  assert.match(settings, /role="switch"/);
  assert.match(settings, /bald verfügbar/);
  assert.match(settings, /disabled=\{!lightEndpoint\}/);
  assert.match(settings, /initializeCatGptMode\(\(\) => localStorage, lightAvailable\)/);
  assert.match(settings, /changeCatGptMode\(\s*\(\) => localStorage,\s*\(\) => sessionStorage/);
});

test("base layout gates Light once and passes the endpoint into both CatGPT components", () => {
  assert.match(layout, /resolveCatGptLightEndpoint\(import\.meta\.env\.PUBLIC_CATGPT_LIGHT_ENDPOINT\)/);
  assert.match(layout, /connect-src \$\{lightEndpoint/);
  assert.match(layout, /<SettingsPanel\s+lightEndpoint=\{lightEndpoint\}\s*\/>/);
  assert.match(layout, /import CatGptWidget/);
  assert.match(layout, /<CatGptWidget\s+lightEndpoint=\{lightEndpoint\}\s*\/>/);
  assert.match(chat, /aria-controls="wirtelprimpf-catgpt"/);
  assert.match(chat, /role="dialog"/);
  assert.match(chat, /aria-live="polite"/);
  assert.match(chat, /textContent/);
  assert.doesNotMatch(chat, /innerHTML/);
});

test("CatGPT composer accepts 1000 Unicode code points and rejects 1001", () => {
  assert.equal(isValidChatContent("🐈".repeat(1000)), true);
  assert.equal(isValidChatContent("🐈".repeat(1001)), false);
  assert.doesNotMatch(chat, /\smaxlength=/);
  assert.match(chat, /if \(!isValidChatContent\(message\)\)/);
  assert.match(chat, /setCustomValidity/);
  assert.match(chat, /reportValidity/);
});

test("CatGPT selects its provider and clears stale work on mode changes without exposing fallback", () => {
  assert.match(chat, /new LightReplyProvider\(lightEndpoint, staticProvider\)/);
  assert.match(chat, /readMode\(localStorage\)/);
  assert.match(chat, /readChatHistory\(\(\) => sessionStorage\)/);
  assert.match(chat, /writeChatHistory\(sessionStorage/);
  assert.match(chat, /generation \+= 1/);
  assert.match(chat, /finally\s*\{\s*if \(requestGeneration === generation\)/);
  assert.match(chat, /CATGPT_MODE_CHANGE_EVENT[\s\S]*replaceChildren/);
  assert.doesNotMatch(chat, /Fallback|Kontingent|fehlgeschlagen|Fehler:/i);
});

test("CatGPT keeps its composer visible in short viewports", () => {
  assert.match(styles, /\.catgpt-window \{[^}]*display: flex;[^}]*flex-direction: column;/s);
  assert.match(styles, /\.catgpt-messages \{[^}]*min-height: 0;[^}]*flex: 1;/s);
  assert.doesNotMatch(styles, /\.catgpt-messages \{[^}]*max-height: 24rem;/s);
});
