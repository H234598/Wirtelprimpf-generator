import assert from "node:assert/strict";
import test from "node:test";

import {
  CATGPT_LIGHT_ENDPOINT,
  resolveCatGptLightEndpoint,
} from "../src/lib/catgpt/config.ts";

test("only the byte-exact CatGPT Light endpoint enables network mode", () => {
  assert.equal(resolveCatGptLightEndpoint(CATGPT_LIGHT_ENDPOINT), CATGPT_LIGHT_ENDPOINT);

  for (const endpoint of [
    "https://attacker.example/v1/chat",
    "https://catgpt.evil.wirtelprimpf.telacore.org/v1/chat",
    "https://catgpt.wirtelprimpf.telacore.org:443/v1/chat",
    "https://user@catgpt.wirtelprimpf.telacore.org/v1/chat",
    "https://catgpt.wirtelprimpf.telacore.org/v1/chat?mode=light",
    "https://catgpt.wirtelprimpf.telacore.org/v1/chat#reply",
    "http://catgpt.wirtelprimpf.telacore.org/v1/chat",
    "https://catgpt.wirtelprimpf.telacore.org/v1/chat/",
    ` ${CATGPT_LIGHT_ENDPOINT}`,
    `${CATGPT_LIGHT_ENDPOINT} `,
    "",
    "not a URL",
  ]) {
    assert.equal(resolveCatGptLightEndpoint(endpoint), undefined, endpoint);
  }
  assert.equal(resolveCatGptLightEndpoint(undefined), undefined);
});
