import { expect, test } from "vitest";
import { isAllowedOrigin, parseChatRequest } from "../src/contracts.ts";

test("accepts only bounded text history", () => {
  const request = parseChatRequest({
    message: "miau",
    history: [{ role: "assistant", content: "schnurr" }],
  });
  expect(request.message).toBe("miau");
  expect(() => parseChatRequest({ message: "x".repeat(1001), history: [] })).toThrow();
  expect(() => parseChatRequest({ message: "miau", history: Array(11).fill({ role: "user", content: "x" }) })).toThrow();
  expect(() => parseChatRequest({ message: [{ type: "image_url" }], history: [] })).toThrow();
});

test("origin allowlist rejects lookalikes", () => {
  expect(isAllowedOrigin("https://wirtelprimpf.telacore.org", "")).toBe(true);
  expect(isAllowedOrigin("https://wirtelprimpf-0042.telacore.org", "")).toBe(true);
  expect(isAllowedOrigin("https://wirtelprimpf.telacore.org.attacker.test", "")).toBe(false);
  expect(isAllowedOrigin("http://wirtelprimpf.telacore.org", "")).toBe(false);
  expect(isAllowedOrigin("https://preview.example", "https://preview.example")).toBe(true);
});
