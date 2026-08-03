import assert from "node:assert/strict";
import test from "node:test";

import { STATIC_REPLIES } from "../src/lib/catgpt/static-replies.generated.ts";

const normalize = (value: string): string =>
  value.trim().normalize("NFC").toLocaleLowerCase("de-DE");

test("static CatGPT ships at least one thousand unique non-empty replies", () => {
  assert.ok(STATIC_REPLIES.length >= 1_000);
  assert.ok(STATIC_REPLIES.every((reply) => normalize(reply).length > 0));
  assert.equal(new Set(STATIC_REPLIES.map(normalize)).size, STATIC_REPLIES.length);
  for (const requiredSound of ["miau", "schnurr", "rrrrrr", "maooo"]) {
    assert.ok(STATIC_REPLIES.some((reply) => normalize(reply).includes(requiredSound)));
  }
});
