import { expect, test, vi } from "vitest";
import { requestCatReply } from "../src/openai.ts";

const env = {
  OPENAI_API_KEY: "test-key",
  OPENAI_MODEL: "gpt-5.6-luna",
};

test("sends one bounded text-only Responses request with history before current message", async () => {
  const fetcher = vi.fn(async (_url: string, _init: RequestInit): Promise<Response> => Response.json({
    output: [
      {
        type: "message",
        role: "user",
        content: [{ type: "output_text", text: "not included" }],
      },
      {
        type: "message",
        role: "assistant",
        content: [
          { type: "output_text", text: "" },
          { type: "refusal", refusal: "not included" },
          { type: "output_text", text: "Miau" },
          { type: "output_text", text: "!" },
        ],
      },
    ],
  }));

  await expect(requestCatReply({
    history: [
      { role: "user", content: "Vorher" },
      { role: "assistant", content: "Schnurr" },
    ],
    message: "Jetzt",
  }, env, fetcher)).resolves.toBe("Miau!");

  expect(fetcher).toHaveBeenCalledTimes(1);
  const call = fetcher.mock.calls[0];
  if (!call) throw new Error("fetch call missing");
  const [url, init] = call;
  expect(url).toBe("https://api.openai.com/v1/responses");
  expect(init.method).toBe("POST");
  expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  expect(new Headers(init.headers).get("Authorization")).toBe("Bearer test-key");
  expect(JSON.parse(String(init.body))).toEqual({
    model: "gpt-5.6-luna",
    service_tier: "flex",
    instructions: expect.stringContaining("CatGPT"),
    input: [
      { role: "user", content: "Vorher" },
      { role: "assistant", content: "Schnurr" },
      { role: "user", content: "Jetzt" },
    ],
    max_output_tokens: 256,
    reasoning: { effort: "none" },
    store: false,
    text: { verbosity: "low" },
  });
  const body = JSON.parse(String(init.body)) as Record<string, unknown>;
  expect(body).not.toHaveProperty("tools");
  expect(body).not.toHaveProperty("tool_choice");
  expect(String(body.instructions)).toMatch(/Text|text/);
  expect(String(body.instructions)).toMatch(/keine|nicht/i);
});

test("rejects failed OpenAI responses without retrying", async () => {
  const fetcher = vi.fn(async () => new Response("upstream failed", { status: 502 }));

  await expect(requestCatReply({ message: "Miau", history: [] }, env, fetcher)).rejects.toThrow("502");
  expect(fetcher).toHaveBeenCalledTimes(1);
});

test("rejects empty or malformed OpenAI output without retrying", async () => {
  const emptyFetcher = vi.fn(async () => Response.json({ output: [] }));
  await expect(requestCatReply({ message: "Miau", history: [] }, env, emptyFetcher)).rejects.toThrow();
  expect(emptyFetcher).toHaveBeenCalledTimes(1);

  const malformedFetcher = vi.fn(async () => Response.json({ output: [{ type: "message", role: "assistant" }] }));
  await expect(requestCatReply({ message: "Miau", history: [] }, env, malformedFetcher)).rejects.toThrow();
  expect(malformedFetcher).toHaveBeenCalledTimes(1);
});

test("aborts the single request after eight seconds", async () => {
  vi.useFakeTimers();
  let signal: AbortSignal | undefined;
  const fetcher = vi.fn((_url: string, init?: RequestInit) => new Promise<Response>((_resolve, reject) => {
    signal = init?.signal ?? undefined;
    signal?.addEventListener("abort", () => reject(signal?.reason));
  }));

  const reply = requestCatReply({ message: "Miau", history: [] }, env, fetcher);
  const rejection = expect(reply).rejects.toThrow();
  expect(signal?.aborted).toBe(false);
  await vi.advanceTimersByTimeAsync(8_000);
  await rejection;
  expect(signal?.aborted).toBe(true);
  expect(fetcher).toHaveBeenCalledTimes(1);
  vi.useRealTimers();
});

test("keeps the timeout active while parsing an OpenAI response body", async () => {
  vi.useFakeTimers();
  try {
    let signal: AbortSignal | undefined;
    const fetcher = vi.fn(async (_url: string, init: RequestInit): Promise<Response> => {
      signal = init.signal ?? undefined;
      return {
        ok: true,
        json: () => new Promise((_resolve, reject) => {
          signal?.addEventListener("abort", () => reject(signal?.reason));
        }),
      } as Response;
    });

    const reply = requestCatReply({ message: "Miau", history: [] }, env, fetcher);
    const failure = reply.then(() => null, (error: unknown) => error);
    await vi.advanceTimersByTimeAsync(8_000);

    expect(signal?.aborted).toBe(true);
    expect(await failure).toBeInstanceOf(Error);
    expect(fetcher).toHaveBeenCalledTimes(1);
  } finally {
    vi.useRealTimers();
  }
});
