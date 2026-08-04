import { DurableObject } from "cloudflare:workers";

const RETENTION_MS = 48 * 60 * 60 * 1_000;

export class DailyRateLimiter extends DurableObject<Env> {
  async reserve(limit: number): Promise<boolean> {
    if (!Number.isSafeInteger(limit) || limit < 1) return false;

    const count = (await this.ctx.storage.get<number>("count")) ?? 0;
    if (count >= limit) return false;

    await this.ctx.storage.put("count", count + 1);
    if ((await this.ctx.storage.getAlarm()) === null) {
      await this.ctx.storage.setAlarm(Date.now() + RETENTION_MS);
    }
    return true;
  }

  async alarm(): Promise<void> {
    await this.ctx.storage.deleteAll();
  }
}
