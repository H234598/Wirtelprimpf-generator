import assert from "node:assert/strict";
import test from "node:test";

import { toggleFavorite } from "../src/scripts/favorites.ts";
import { saveReadingProgress, viewportProgress } from "../src/scripts/reading-progress.ts";
import { readSiteState } from "../src/lib/site-state.ts";


class MemoryStorage {
  readonly values = new Map<string, string>();
  getItem(key: string): string | null { return this.values.get(key) ?? null; }
  setItem(key: string, value: string): void { this.values.set(key, value); }
  removeItem(key: string): void { this.values.delete(key); }
}


test("reading progress is bounded and based on stable chapter IDs", () => {
  assert.equal(viewportProgress(0, 1000, 500), 0);
  assert.equal(viewportProgress(250, 1000, 500), 50);
  assert.equal(viewportProgress(9999, 1000, 500), 100);
  assert.equal(viewportProgress(0, 500, 500), 100);

  const storage = new MemoryStorage();
  const id = "band-0001-teil-abcdef123456";
  assert.equal(saveReadingProgress(storage, id, 55.4), true);
  assert.equal(readSiteState(storage).progress[id]?.position, 55);
  assert.equal(saveReadingProgress(storage, "free text", 55), false);
});


test("favorites remain local, bounded and independently toggleable", () => {
  const storage = new MemoryStorage();
  assert.equal(toggleFavorite(storage, "asset-1"), true);
  assert.equal(toggleFavorite(storage, "asset-1"), false);
  assert.equal(toggleFavorite(storage, "not valid!"), null);
  for (let index = 0; index < 101; index += 1) toggleFavorite(storage, `asset-${index}`);
  assert.equal(readSiteState(storage).favorites.length, 100);
  assert.equal(readSiteState(storage).favorites.includes("asset-0"), false);
});
