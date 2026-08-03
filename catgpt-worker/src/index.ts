import { DailyRateLimiter } from "./daily-rate-limiter.ts";

export { DailyRateLimiter };

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname !== "/v1/chat") return new Response(null, { status: 404 });
    if (request.method !== "POST" && request.method !== "OPTIONS") {
      return new Response(null, { status: 405, headers: { Allow: "POST, OPTIONS" } });
    }
    if (String(env.LIGHT_ENABLED) !== "true") return new Response(null, { status: 503 });
    return new Response(null, { status: 501 });
  },
} satisfies ExportedHandler<Env>;
