import { SELF } from "cloudflare:test";
import { expect, test } from "vitest";

test("Light endpoint is fail-closed while disabled", async () => {
  const response = await SELF.fetch("https://worker.test/v1/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: "https://wirtelprimpf.telacore.org",
    },
    body: JSON.stringify({ message: "miau", history: [] }),
  });
  expect(response.status).toBe(503);
  expect(await response.text()).toBe("");
});

test("Light endpoint rejects unsupported methods", async () => {
  const response = await SELF.fetch("https://worker.test/v1/chat");

  expect(response.status).toBe(405);
  expect(response.headers.get("Allow")).toBe("POST, OPTIONS");
});
