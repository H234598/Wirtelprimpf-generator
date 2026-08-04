import assert from "node:assert/strict";
import test from "node:test";

import { CATGPT_LIGHT_ENDPOINT } from "../src/lib/catgpt/config.ts";
import { LightReplyProvider } from "../src/lib/catgpt/light-provider.ts";
import type { ReplyProvider, ReplyRequest } from "../src/lib/catgpt/types.ts";

class FallbackProvider implements ReplyProvider {
  calls: ReplyRequest[] = [];
  async reply(request: ReplyRequest): Promise<string> {
    this.calls.push(request);
    return "statisches Miau";
  }
}

const request = {
  message: "Hallo",
  history: [{ role: "assistant", content: "Miau", secret: "nicht senden" }],
  secret: "nicht senden",
} as unknown as ReplyRequest;

test("Light sends one hardened POST containing only message and prior history", async () => {
  const fallback = new FallbackProvider();
  const calls: Array<{ input: string | URL | Request; init?: RequestInit }> = [];
  const fetcher = async (input: string | URL | Request, init?: RequestInit): Promise<Response> => {
    calls.push({ input, init });
    return Response.json({ reply: "  Licht-Miau  " });
  };
  const provider = new LightReplyProvider(CATGPT_LIGHT_ENDPOINT, fallback, { fetch: fetcher });

  assert.equal(await provider.reply(request), "Licht-Miau");
  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.input, CATGPT_LIGHT_ENDPOINT);
  assert.deepEqual(calls[0]?.init, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: '{"message":"Hallo","history":[{"role":"assistant","content":"Miau"}]}',
    cache: "no-store",
    credentials: "omit",
    redirect: "error",
    referrerPolicy: "no-referrer",
    signal: calls[0]?.init?.signal,
  });
  assert.ok(calls[0]?.init?.signal instanceof AbortSignal);
  assert.deepEqual(fallback.calls, []);
});

test("every Light failure silently falls back exactly once without retry", async (t) => {
  const failures: Array<[string, () => Promise<Response>]> = [
    ["fetch", async () => { throw new TypeError("offline"); }],
    ["HTTP", async () => new Response("nope", { status: 503 })],
    ["JSON", async () => new Response("not json", { status: 200 })],
    ["missing reply", async () => Response.json({ answer: "wrong field" })],
    ["non-string reply", async () => Response.json({ reply: 7 })],
    ["empty reply", async () => Response.json({ reply: "   " })],
  ];

  for (const [name, response] of failures) {
    await t.test(name, async () => {
      const fallback = new FallbackProvider();
      let fetchCalls = 0;
      const provider = new LightReplyProvider(CATGPT_LIGHT_ENDPOINT, fallback, {
        fetch: async () => { fetchCalls += 1; return response(); },
      });

      assert.equal(await provider.reply(request), "statisches Miau");
      assert.equal(fetchCalls, 1);
      assert.deepEqual(fallback.calls, [request]);
    });
  }
});

test("Light aborts after ten seconds and then falls back once", async () => {
  const fallback = new FallbackProvider();
  let timeoutDelay: number | undefined;
  let cleared = false;
  const provider = new LightReplyProvider(CATGPT_LIGHT_ENDPOINT, fallback, {
    fetch: async (_input, init) => {
      assert.equal(init?.signal?.aborted, true);
      throw init?.signal?.reason;
    },
    setTimeout: (callback, delay) => {
      timeoutDelay = delay;
      callback();
      return 1;
    },
    clearTimeout: () => { cleared = true; },
  });

  assert.equal(await provider.reply(request), "statisches Miau");
  assert.equal(timeoutDelay, 10_000);
  assert.equal(cleared, true);
  assert.deepEqual(fallback.calls, [request]);
});
