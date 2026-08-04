import { env, runDurableObjectAlarm } from "cloudflare:test";
import { expect, test } from "vitest";
import type { DailyRateLimiter } from "../src/daily-rate-limiter.ts";

const dailyLimits = env.DAILY_LIMITS as DurableObjectNamespace<DailyRateLimiter>;

test("rejects non-integer reservation limits", async () => {
  const stub = dailyLimits.get(dailyLimits.idFromName("invalid-limit-client-day"));

  expect(await stub.reserve(0.5)).toBe(false);
  expect(await stub.reserve(1)).toBe(true);
});

test("exactly fifty of fifty-one parallel reservations succeed", async () => {
  const stub = dailyLimits.get(dailyLimits.idFromName("client-day"));
  const results = await Promise.all(Array.from({ length: 51 }, () => stub.reserve(50)));

  expect(results.filter(Boolean)).toHaveLength(50);
  expect(await stub.reserve(50)).toBe(false);
});

test("alarm removes expired counter", async () => {
  const stub = dailyLimits.get(dailyLimits.idFromName("expiring-client-day"));

  expect(await stub.reserve(1)).toBe(true);
  expect(await stub.reserve(1)).toBe(false);
  await runDurableObjectAlarm(stub);
  expect(await stub.reserve(1)).toBe(true);
});
