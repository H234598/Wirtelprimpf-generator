import { expect, test, vi } from "vitest";
import * as contracts from "../src/contracts.ts";
import worker, * as workerModule from "../src/index.ts";
import type { ChatRequest } from "../src/contracts.ts";

const allowedOrigin = "https://wirtelprimpf.telacore.org";
const validBody = JSON.stringify({ message: "Miau", history: [] });

type ReplyRequester = (request: ChatRequest, env: Env) => Promise<string>;
type Handler = (request: Request, env: Env) => Promise<Response>;
type HandlerFactory = (dependencies?: { now?: () => Date; requestReply?: ReplyRequester }) => Handler;

const missingHandler: Handler = async (request, env) => worker.fetch(request, env);
const createHandler = (workerModule as unknown as { createHandler?: HandlerFactory }).createHandler
  ?? (() => missingHandler);
const isClientIpLiteral = (contracts as unknown as { isClientIpLiteral?: (value: string) => boolean })
  .isClientIpLiteral ?? (() => false);

function makeEnv(options: {
  enabled?: string;
  limit?: string;
  reserve?: (limit: number) => Promise<boolean>;
  onName?: (name: string) => void;
  openAiKey?: string;
} = {}): Env {
  const reserve = options.reserve ?? (async () => true);
  const namespace = {
    idFromName(name: string) {
      options.onName?.(name);
      return { name };
    },
    get() {
      return { reserve };
    },
  };

  return {
    DAILY_LIMITS: namespace,
    EXTRA_ALLOWED_ORIGINS: "",
    HMAC_SECRET: "test-hmac-secret",
    LIGHT_ENABLED: options.enabled ?? "true",
    MAX_DAILY_REQUESTS: options.limit ?? "50",
    OPENAI_API_KEY: options.openAiKey ?? "test-openai-key",
    OPENAI_MODEL: "gpt-5.6-luna",
  } as unknown as Env;
}

function post(ip = "203.0.113.7", body: BodyInit | null = validBody, headers: HeadersInit = {}): Request {
  return new Request("https://worker.test/v1/chat", {
    method: "POST",
    headers: {
      "CF-Connecting-IP": ip,
      "Content-Type": "application/json",
      Origin: allowedOrigin,
      ...headers,
    },
    body,
  });
}

async function expectEmpty(response: Response, status: number): Promise<void> {
  expect(response.status).toBe(status);
  expect(await response.text()).toBe("");
  expect(response.headers.get("Cache-Control")).toBe("no-store");
}

test("strict client IP predicate accepts only canonical IPv4 and valid IPv6 literals", () => {
  for (const value of [
    "0.0.0.0",
    "203.0.113.7",
    "255.255.255.255",
    "::",
    "::1",
    "2001:db8::1",
    "2001:db8:0:1:1:1:192.0.2.1",
    "::ffff:192.0.2.128",
  ]) {
    expect(isClientIpLiteral(value), value).toBe(true);
  }

  for (const value of [
    "",
    "example.test",
    "203.0.113.7:443",
    "[2001:db8::1]",
    "fe80::1%eth0",
    "256.0.0.1",
    "01.2.3.4",
    "1.2.3",
    "2001:db8:1",
    "1:2:3:4:5:6:7:8:9",
    "2001:db8::1::2",
    "::ffff:192.0.2.999",
    "203.0.113.7, 198.51.100.2",
    " 203.0.113.7",
    "203.0.113.7 ",
    "203.0.113.7\t",
  ]) {
    expect(isClientIpLiteral(value), value).toBe(false);
  }
});

test("preserves path and method contracts before the origin gate", async () => {
  const handler = createHandler();
  const notFound = await handler(new Request("https://worker.test/other", {
    method: "POST",
    headers: { Origin: allowedOrigin },
  }), makeEnv());
  await expectEmpty(notFound, 404);
  expect(notFound.headers.get("Access-Control-Allow-Origin")).toBe(allowedOrigin);

  const methodNotAllowed = await handler(new Request("https://worker.test/v1/chat"), makeEnv());
  await expectEmpty(methodNotAllowed, 405);
  expect(methodNotAllowed.headers.get("Allow")).toBe("POST, OPTIONS");

  const allowedMethodNotAllowed = await handler(new Request("https://worker.test/v1/chat", {
    headers: { Origin: allowedOrigin },
  }), makeEnv());
  await expectEmpty(allowedMethodNotAllowed, 405);
  expect(allowedMethodNotAllowed.headers.get("Access-Control-Allow-Origin")).toBe(allowedOrigin);
});

test("rejects missing or denied origins and allows preflight only for an allowed origin", async () => {
  const handler = createHandler();
  await expectEmpty(await handler(post("203.0.113.7", validBody, { Origin: "" }), makeEnv()), 403);
  await expectEmpty(await handler(post("203.0.113.7", validBody, { Origin: "https://attacker.test" }), makeEnv()), 403);

  const deniedPreflight = await handler(new Request("https://worker.test/v1/chat", {
    method: "OPTIONS",
    headers: { Origin: "https://attacker.test" },
  }), makeEnv());
  await expectEmpty(deniedPreflight, 403);

  const preflight = await handler(new Request("https://worker.test/v1/chat", {
    method: "OPTIONS",
    headers: { Origin: allowedOrigin },
  }), makeEnv({ enabled: "false", openAiKey: "" }));
  expect(preflight.status).toBe(204);
  expect(preflight.headers.get("Access-Control-Allow-Origin")).toBe(allowedOrigin);
  expect(preflight.headers.get("Access-Control-Allow-Methods")).toBe("POST, OPTIONS");
  expect(preflight.headers.get("Access-Control-Allow-Headers")).toBe("Content-Type");
  expect(preflight.headers.get("Vary")).toBe("Origin");
  expect(preflight.headers.get("Cache-Control")).toBe("no-store");
});

test("fails closed for disabled or invalid configuration", async () => {
  const handler = createHandler();
  await expectEmpty(await handler(post(), makeEnv({ enabled: "false" })), 503);
  await expectEmpty(await handler(post(), makeEnv({ openAiKey: "" })), 503);
  await expectEmpty(await handler(post(), makeEnv({ limit: "50.5" })), 503);
});

test("rejects declared and streamed bodies over 16 KiB without calling dependencies", async () => {
  const requestReply = vi.fn<ReplyRequester>(async () => "Miau");
  const reserve = vi.fn(async () => true);
  const handler = createHandler({ requestReply });

  await expectEmpty(await handler(post("203.0.113.7", "{}", { "Content-Length": "16385" }), makeEnv({ reserve })), 413);

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new Uint8Array(10_000));
      controller.enqueue(new Uint8Array(6_385));
      controller.close();
    },
  });
  await expectEmpty(await handler(post("203.0.113.7", stream), makeEnv({ reserve })), 413);
  expect(reserve).not.toHaveBeenCalled();
  expect(requestReply).not.toHaveBeenCalled();
});

test("rejects malformed JSON and invalid chat payloads", async () => {
  const requestReply = vi.fn<ReplyRequester>(async () => "Miau");
  const reserve = vi.fn(async () => true);
  const handler = createHandler({ requestReply });

  await expectEmpty(await handler(post("203.0.113.7", "{"), makeEnv({ reserve })), 400);
  await expectEmpty(await handler(post("203.0.113.7", JSON.stringify({ message: "", history: [] })), makeEnv({ reserve })), 400);
  expect(reserve).not.toHaveBeenCalled();
  expect(requestReply).not.toHaveBeenCalled();
});

test.each([
  ["malformed", "999.0.0.1"],
  ["list", "203.0.113.7,198.51.100.2"],
  ["whitespace", "203.0.113.7\tbad"],
  ["missing", ""],
])("rejects %s client IP before reservation and upstream", async (_name, ip) => {
  const requestReply = vi.fn<ReplyRequester>(async () => "Miau");
  const reserve = vi.fn(async () => true);
  const handler = createHandler({ requestReply });

  await expectEmpty(await handler(post(ip), makeEnv({ reserve })), 400);
  expect(reserve).not.toHaveBeenCalled();
  expect(requestReply).not.toHaveBeenCalled();
});

test.each(["203.0.113.7", "2001:db8::7"])("reserves a hashed daily key before one upstream call for %s", async (ip) => {
  const events: string[] = [];
  let durableObjectName = "";
  const reserve = vi.fn(async (limit: number) => {
    events.push(`reserve:${limit}`);
    return true;
  });
  const requestReply = vi.fn<ReplyRequester>(async () => {
    events.push("upstream");
    return "Schnurr";
  });
  const handler = createHandler({
    now: () => new Date("2026-08-03T12:00:00Z"),
    requestReply,
  });
  const response = await handler(post(ip), makeEnv({ reserve, onName: (name) => { durableObjectName = name; } }));

  expect(response.status).toBe(200);
  await expect(response.json()).resolves.toEqual({ reply: "Schnurr" });
  expect(response.headers.get("Content-Type")).toContain("application/json");
  expect(response.headers.get("Access-Control-Allow-Origin")).toBe(allowedOrigin);
  expect(response.headers.get("Vary")).toBe("Origin");
  expect(response.headers.get("Cache-Control")).toBe("no-store");
  expect(events).toEqual(["reserve:50", "upstream"]);
  expect(requestReply).toHaveBeenCalledTimes(1);
  expect(durableObjectName).toMatch(/^[0-9a-f]{64}$/);
  expect(durableObjectName).not.toContain(ip);
});

test("returns 429 without upstream when reservation is denied", async () => {
  const requestReply = vi.fn<ReplyRequester>(async () => "Miau");
  const handler = createHandler({ requestReply });
  const response = await handler(post(), makeEnv({ reserve: async () => false }));

  await expectEmpty(response, 429);
  expect(response.headers.get("Access-Control-Allow-Origin")).toBe(allowedOrigin);
  expect(requestReply).not.toHaveBeenCalled();
});

test("maps one upstream failure to 502 and keeps its reservation consumed", async () => {
  let reservations = 0;
  const reserve = vi.fn(async (limit: number) => {
    if (reservations >= limit) return false;
    reservations += 1;
    return true;
  });
  const requestReply = vi.fn<ReplyRequester>(async () => {
    throw new Error("upstream failed");
  });
  const handler = createHandler({ requestReply });
  const env = makeEnv({ reserve });

  for (let attempt = 0; attempt < 50; attempt += 1) {
    await expectEmpty(await handler(post(), env), 502);
  }
  await expectEmpty(await handler(post(), env), 429);
  expect(reserve).toHaveBeenCalledTimes(51);
  expect(requestReply).toHaveBeenCalledTimes(50);
});
