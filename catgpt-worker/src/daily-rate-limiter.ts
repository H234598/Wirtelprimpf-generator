import { DurableObject } from "cloudflare:workers";

export class DailyRateLimiter extends DurableObject<Env> {
  async reserve(_limit: number): Promise<boolean> {
    return false;
  }
}
