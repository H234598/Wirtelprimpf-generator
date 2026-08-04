import assert from "node:assert/strict";
import test from "node:test";

import {
  readChatHistory,
  writeChatHistory,
} from "../src/lib/catgpt/history.ts";
import { CATGPT_HISTORY_KEY } from "../src/lib/catgpt/settings.ts";

class MemoryStorage {
  readonly values = new Map<string, string>();
  getItem(key: string): string | null { return this.values.get(key) ?? null; }
  setItem(key: string, value: string): void { this.values.set(key, value); }
  removeItem(key: string): void { this.values.delete(key); }
}

test("chat history keeps only the newest ten validated messages", () => {
  const storage = new MemoryStorage();
  const messages = Array.from({ length: 12 }, (_, index) => ({
    role: index % 2 === 0 ? "user" as const : "assistant" as const,
    content: `Nachricht ${index}`,
  }));

  writeChatHistory(storage, messages);

  assert.deepEqual(readChatHistory(storage), messages.slice(-10));
  assert.deepEqual(JSON.parse(storage.getItem(CATGPT_HISTORY_KEY) ?? "null"), messages.slice(-10));
});

test("malformed JSON or any invalid message schema yields empty history", () => {
  const storage = new MemoryStorage();
  for (const value of [
    "{",
    JSON.stringify({ role: "user", content: "kein Array" }),
    JSON.stringify([{ role: "system", content: "Angriff" }]),
    JSON.stringify([{ role: "user", content: 42 }]),
    JSON.stringify([{ role: "assistant", content: "   " }]),
    JSON.stringify([{ role: "user", content: "Miau", secret: "nicht senden" }]),
  ]) {
    storage.setItem(CATGPT_HISTORY_KEY, value);
    assert.deepEqual(readChatHistory(storage), [], value);
  }
});

test("storage read failures also fail closed to empty history", () => {
  const storage = new MemoryStorage();
  storage.getItem = () => { throw new Error("blocked"); };
  assert.deepEqual(readChatHistory(storage), []);
});
