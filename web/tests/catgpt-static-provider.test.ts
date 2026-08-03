import assert from "node:assert/strict";
import test from "node:test";

import { StaticReplyProvider } from "../src/lib/catgpt/static-provider.ts";

test("shuffle bag emits every reply once and never repeats at bag boundaries", async () => {
  const provider = new StaticReplyProvider(["a", "b", "c"], () => 0);
  const replies: string[] = [];
  for (let index = 0; index < 9; index += 1) {
    replies.push(await provider.reply({ message: "ignoriert", history: [] }));
  }
  for (let start = 0; start < replies.length; start += 3) {
    assert.equal(new Set(replies.slice(start, start + 3)).size, 3);
  }
  for (let index = 1; index < replies.length; index += 1) {
    assert.notEqual(replies[index], replies[index - 1]);
  }
});

test("provider rejects catalogs that cannot avoid repetition", () => {
  assert.throws(() => new StaticReplyProvider(["miau"]), /at least two unique replies/);
});
