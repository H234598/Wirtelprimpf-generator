import assert from "node:assert/strict";
import test from "node:test";

import {
  clearSiteState,
  defaultSiteState,
  migrateSiteState,
  parseSiteState,
  readSiteState,
  serializeSiteState,
  writeSiteState,
} from "../src/lib/site-state.ts";
import { MAX_SITE_STATE_BYTES, SITE_STATE_KEY } from "../src/lib/site-state.schema.ts";


class MemoryStorage {
  readonly values = new Map<string, string>();
  getItem(key: string): string | null { return this.values.get(key) ?? null; }
  setItem(key: string, value: string): void { this.values.set(key, value); }
  removeItem(key: string): void { this.values.delete(key); }
}


test("site state round-trips only versioned comfort data", () => {
  const storage = new MemoryStorage();
  const state = defaultSiteState();
  state.theme = "paper";
  state.gallery.focus_id = "asset-1";
  state.progress["band-0001-teil-abcdef123456"] = { position: 3, anchor: "paragraph-1" };
  state.favorites = ["asset-1"];

  assert.equal(writeSiteState(storage, state), true);
  assert.equal(storage.values.has(SITE_STATE_KEY), true);
  assert.deepEqual(readSiteState(storage), state);
  assert.ok(new TextEncoder().encode(serializeSiteState(state)).byteLength < MAX_SITE_STATE_BYTES);
});


test("malformed, unknown-version and free-text state fail closed", () => {
  const storage = new MemoryStorage();
  storage.setItem(SITE_STATE_KEY, "not-json");
  assert.deepEqual(readSiteState(storage), defaultSiteState());
  storage.setItem(SITE_STATE_KEY, JSON.stringify({ schema_version: 99 }));
  assert.deepEqual(readSiteState(storage), defaultSiteState());

  const invalid = defaultSiteState();
  invalid.progress["user wrote this"] = { position: 1, anchor: null };
  assert.equal(writeSiteState(storage, invalid), false);
});


test("storage failures only remove the comfort feature", () => {
  const failing = {
    getItem(): string | null { throw new DOMException("blocked", "SecurityError"); },
    setItem(): void { throw new DOMException("blocked", "SecurityError"); },
    removeItem(): void { throw new DOMException("blocked", "SecurityError"); },
  };
  assert.deepEqual(readSiteState(failing), defaultSiteState());
  assert.equal(writeSiteState(failing, defaultSiteState()), false);
  assert.equal(clearSiteState(failing), false);
});


test("the state has a hard 64 KiB ceiling", () => {
  const state = defaultSiteState();
  for (let index = 0; index < 500; index += 1) {
    state.progress[`band-0001-teil-${index.toString(16).padStart(12, "0")}`] = {
      position: index,
      anchor: "a".repeat(200),
    };
  }
  assert.throws(() => serializeSiteState(state), /64 KiB/);
  assert.equal(writeSiteState(new MemoryStorage(), state), false);
});


test("aliases migrate stable chapter IDs without preserving the old key", () => {
  const oldId = "band-0001-teil-abcdef123456";
  const newId = "band-0001-teil-123456abcdef";
  const state = migrateSiteState({
    schema_version: 1,
    theme: "night",
    reading_view: "chapter",
    gallery: { typ: "all", seite: 1, jahr: null, focus_id: null, scroll_y: 0 },
    progress: { [oldId]: { position: 2, anchor: null } },
    favorites: [oldId],
  }, { [oldId]: newId });

  assert.deepEqual(state?.progress, { [newId]: { position: 2, anchor: null } });
  assert.deepEqual(state?.favorites, [newId]);
});


test("legacy theme is read only as a migration fallback", () => {
  const storage = new MemoryStorage();
  storage.setItem("wirtelprimpf-theme", "paper");
  assert.equal(readSiteState(storage).theme, "paper");
  assert.equal(parseSiteState(null).theme, "night");
});
