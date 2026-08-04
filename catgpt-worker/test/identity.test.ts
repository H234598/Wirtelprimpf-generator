import { expect, test } from "vitest";
import { berlinDate, dailyClientKey } from "../src/identity.ts";

test("Berlin day handles summer and winter boundaries", () => {
  expect(berlinDate(new Date("2026-08-03T21:59:59Z"))).toBe("2026-08-03");
  expect(berlinDate(new Date("2026-08-03T22:00:00Z"))).toBe("2026-08-04");
  expect(berlinDate(new Date("2026-01-03T22:59:59Z"))).toBe("2026-01-03");
  expect(berlinDate(new Date("2026-01-03T23:00:00Z"))).toBe("2026-01-04");
});

test("daily key is stable without exposing the IP", async () => {
  const first = await dailyClientKey("203.0.113.7", "2026-08-03", "secret");
  const second = await dailyClientKey("203.0.113.7", "2026-08-03", "secret");
  expect(first).toBe(second);
  expect(first).toMatch(/^[0-9a-f]{64}$/);
  expect(first).not.toContain("203.0.113.7");
  expect(await dailyClientKey("203.0.113.7", "2026-08-04", "secret")).not.toBe(first);
});
