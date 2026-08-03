import assert from "node:assert/strict";
import test from "node:test";

import {
  CATGPT_HISTORY_KEY,
  clearChatSession,
  readMode,
  readTheme,
  writeMode,
  writeTheme,
} from "../src/lib/catgpt/settings.ts";

class MemoryStorage {
  readonly values = new Map<string, string>();
  getItem(key: string): string | null { return this.values.get(key) ?? null; }
  setItem(key: string, value: string): void { this.values.set(key, value); }
  removeItem(key: string): void { this.values.delete(key); }
}

test("invalid or missing settings fail closed to night and static", () => {
  const storage = new MemoryStorage();
  assert.equal(readTheme(storage), "night");
  assert.equal(readMode(storage), "static");
  storage.setItem("wirtelprimpf-theme", "attacker");
  storage.setItem("wirtelprimpf-catgpt-mode", "agent");
  assert.equal(readTheme(storage), "night");
  assert.equal(readMode(storage), "static");
});

test("known settings persist and clearing a chat removes only session history", () => {
  const storage = new MemoryStorage();
  writeTheme(storage, "paper");
  writeMode(storage, "light");
  storage.setItem(CATGPT_HISTORY_KEY, "history");
  clearChatSession(storage);
  assert.equal(readTheme(storage), "paper");
  assert.equal(readMode(storage), "light");
  assert.equal(storage.getItem(CATGPT_HISTORY_KEY), null);
});
