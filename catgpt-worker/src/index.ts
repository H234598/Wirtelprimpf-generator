import { DailyRateLimiter } from "./daily-rate-limiter.ts";
import { isAllowedOrigin, isClientIpLiteral, parseChatRequest, type ChatRequest } from "./contracts.ts";
import { berlinDate, dailyClientKey } from "./identity.ts";
import { requestCatReply } from "./openai.ts";

export { DailyRateLimiter };

const MAX_BODY_BYTES = 16 * 1_024;

type ReplyRequester = (request: ChatRequest, env: Env) => Promise<string>;
type HandlerDependencies = {
  now?: () => Date;
  requestReply?: ReplyRequester;
};

class BodyTooLarge extends Error {}

function response(status: number, origin: string | null, headers?: HeadersInit, body: BodyInit | null = null): Response {
  const responseHeaders = new Headers(headers);
  responseHeaders.set("Cache-Control", "no-store");
  responseHeaders.set("Vary", "Origin");
  if (origin) {
    responseHeaders.set("Access-Control-Allow-Origin", origin);
    responseHeaders.set("Access-Control-Allow-Methods", "POST, OPTIONS");
    responseHeaders.set("Access-Control-Allow-Headers", "Content-Type");
  }
  return new Response(body, { status, headers: responseHeaders });
}

async function readBoundedJson(request: Request): Promise<unknown> {
  const declaredLength = request.headers.get("Content-Length");
  if (declaredLength && /^\d+$/.test(declaredLength) && Number(declaredLength) > MAX_BODY_BYTES) {
    throw new BodyTooLarge();
  }

  const reader = request.body?.getReader();
  if (!reader) return JSON.parse("");

  const chunks: Uint8Array[] = [];
  let size = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > MAX_BODY_BYTES) {
      try {
        await reader.cancel();
      } catch {
        // Response remains 413 even when the sender cannot be cancelled.
      }
      throw new BodyTooLarge();
    }
    chunks.push(value);
  }

  const body = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return JSON.parse(new TextDecoder("utf-8", { fatal: true, ignoreBOM: false }).decode(body));
}

function configuration(env: Env): { limit: number; namespace: DurableObjectNamespace<DailyRateLimiter> } | null {
  if (
    typeof env.EXTRA_ALLOWED_ORIGINS !== "string"
    || typeof env.HMAC_SECRET !== "string" || !env.HMAC_SECRET.trim()
    || typeof env.OPENAI_API_KEY !== "string" || !env.OPENAI_API_KEY.trim()
    || typeof env.OPENAI_MODEL !== "string" || !env.OPENAI_MODEL.trim()
    || typeof env.MAX_DAILY_REQUESTS !== "string" || !/^[1-9]\d*$/.test(env.MAX_DAILY_REQUESTS)
    || !env.DAILY_LIMITS
  ) return null;

  const limit = Number(env.MAX_DAILY_REQUESTS);
  const namespace = env.DAILY_LIMITS as DurableObjectNamespace<DailyRateLimiter>;
  if (
    !Number.isSafeInteger(limit)
    || typeof namespace.idFromName !== "function"
    || typeof namespace.get !== "function"
  ) return null;
  return { limit, namespace };
}

export function createHandler({
  now = () => new Date(),
  requestReply = requestCatReply,
}: HandlerDependencies = {}): (request: Request, env: Env) => Promise<Response> {
  return async (request, env) => {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");
    const extraOrigins = typeof env.EXTRA_ALLOWED_ORIGINS === "string" ? env.EXTRA_ALLOWED_ORIGINS : "";
    const corsOrigin = isAllowedOrigin(origin, extraOrigins) ? origin : null;
    if (url.pathname === "/" && (request.method === "GET" || request.method === "HEAD")) {
      return response(
        200,
        null,
        { "Content-Type": "text/plain; charset=utf-8" },
        "CatGPT Light API is online. Use POST /v1/chat.\n",
      );
    }
    if (url.pathname !== "/v1/chat") return response(404, corsOrigin);
    if (request.method !== "POST" && request.method !== "OPTIONS") {
      return response(405, corsOrigin, { Allow: "POST, OPTIONS" });
    }

    if (!corsOrigin) return response(403, null);
    if (request.method === "OPTIONS") return response(204, origin);
    if (String(env.LIGHT_ENABLED) !== "true") return response(503, origin);

    const config = configuration(env);
    if (!config) return response(503, origin);

    let chatRequest: ChatRequest;
    try {
      chatRequest = parseChatRequest(await readBoundedJson(request));
    } catch (error) {
      return response(error instanceof BodyTooLarge ? 413 : 400, origin);
    }

    const ip = request.headers.get("CF-Connecting-IP");
    if (!ip || !isClientIpLiteral(ip)) return response(400, origin);

    let reserved: boolean;
    try {
      const name = await dailyClientKey(ip, berlinDate(now()), env.HMAC_SECRET);
      const limiter = config.namespace.get(config.namespace.idFromName(name));
      reserved = await limiter.reserve(config.limit);
    } catch {
      return response(503, origin);
    }
    if (!reserved) return response(429, origin);

    try {
      const reply = await requestReply(chatRequest, env);
      const headers = new Headers({ "Content-Type": "application/json; charset=utf-8" });
      const successHeaders = response(200, origin, headers).headers;
      return new Response(JSON.stringify({ reply }), { status: 200, headers: successHeaders });
    } catch {
      return response(502, origin);
    }
  };
}

const handleRequest = createHandler();

export default {
  fetch: handleRequest,
} satisfies ExportedHandler<Env>;
