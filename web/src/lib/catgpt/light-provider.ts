import type { CatGptLightEndpoint } from "./config.ts";
import { isValidChatContent, type ReplyProvider, type ReplyRequest } from "./types.ts";

type Fetcher = (input: string | URL | Request, init?: RequestInit) => Promise<Response>;

interface LightProviderDependencies {
  fetch?: Fetcher;
  setTimeout?: (callback: () => void, delay: number) => unknown;
  clearTimeout?: (handle: unknown) => void;
}

export class LightReplyProvider implements ReplyProvider {
  private readonly endpoint: CatGptLightEndpoint;
  private readonly fallback: ReplyProvider;
  private readonly fetcher: Fetcher;
  private readonly setTimer: (callback: () => void, delay: number) => unknown;
  private readonly clearTimer: (handle: unknown) => void;

  constructor(
    endpoint: CatGptLightEndpoint,
    fallback: ReplyProvider,
    dependencies: LightProviderDependencies = {},
  ) {
    this.endpoint = endpoint;
    this.fallback = fallback;
    this.fetcher = dependencies.fetch ?? globalThis.fetch;
    this.setTimer = dependencies.setTimeout ?? ((callback, delay) => globalThis.setTimeout(callback, delay));
    this.clearTimer = dependencies.clearTimeout ?? ((handle) => {
      globalThis.clearTimeout(handle as ReturnType<typeof globalThis.setTimeout>);
    });
  }

  async reply(request: ReplyRequest): Promise<string> {
    const controller = new AbortController();
    const timeout = this.setTimer(() => controller.abort(), 10_000);
    try {
      const response = await this.fetcher(this.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: request.message,
          history: request.history.map(({ role, content }) => ({ role, content })),
        }),
        cache: "no-store",
        credentials: "omit",
        redirect: "error",
        referrerPolicy: "no-referrer",
        signal: controller.signal,
      });
      if (!response.ok) throw new Error("CatGPT Light HTTP error");
      const body: unknown = await response.json();
      if (!body || typeof body !== "object" || typeof (body as Record<string, unknown>).reply !== "string") {
        throw new Error("CatGPT Light invalid reply");
      }
      const reply = ((body as Record<string, unknown>).reply as string).trim();
      if (!isValidChatContent(reply)) throw new Error("CatGPT Light invalid reply content");
      return reply;
    } catch {
      return this.fallback.reply(request);
    } finally {
      this.clearTimer(timeout);
    }
  }
}
