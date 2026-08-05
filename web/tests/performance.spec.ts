import { mkdir, writeFile } from "node:fs/promises";

import { expect, test, type Page } from "@playwright/test";

type PerformanceSnapshot = {
  route: string;
  navigation: {
    dom_content_loaded_ms: number;
    load_event_ms: number;
    transfer_bytes: number;
  };
  external_runtime_requests: string[];
  eager_images: number;
  lcp_ms: number | null;
  cls: number;
  inp_ms: number | null;
};

const snapshots: PerformanceSnapshot[] = [];

async function measure(page: Page, route: string): Promise<PerformanceSnapshot> {
  const response = await page.goto(route, { waitUntil: "load" });
  expect(response?.status()).toBe(200);
  const snapshot = await page.evaluate((currentRoute) => {
    const navigation = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
    if (!navigation) throw new Error("navigation timing is unavailable");
    const resources = performance.getEntriesByType("resource") as PerformanceResourceTiming[];
    const runtimeInitiators = new Set(["script", "link", "fetch", "xmlhttprequest", "websocket"]);
    const externalRuntime = resources
      .filter((entry) => new URL(entry.name).origin !== window.location.origin && runtimeInitiators.has(entry.initiatorType))
      .map((entry) => entry.name);
    const lcpEntries = performance.getEntriesByType("largest-contentful-paint");
    const lcp = lcpEntries.at(-1);
    const layoutShifts = performance.getEntriesByType("layout-shift") as Array<PerformanceEntry & { value?: number; hadRecentInput?: boolean }>;
    const cls = layoutShifts.reduce((total, entry) => total + (entry.hadRecentInput ? 0 : entry.value ?? 0), 0);
    return {
      route: currentRoute,
      navigation: {
        dom_content_loaded_ms: navigation.domContentLoadedEventEnd - navigation.startTime,
        load_event_ms: navigation.loadEventEnd - navigation.startTime,
        transfer_bytes: resources.reduce((total, entry) => total + entry.transferSize, 0),
      },
      external_runtime_requests: [...new Set(externalRuntime)].sort(),
      eager_images: [...document.images].filter((image) => image.loading !== "lazy").length,
      lcp_ms: lcp ? lcp.startTime : null,
      cls,
      inp_ms: null,
    } satisfies PerformanceSnapshot;
  }, route);
  snapshots.push(snapshot);
  return snapshot;
}

test.afterAll(async () => {
  await mkdir("test-results", { recursive: true });
  await writeFile("test-results/web-performance.json", `${JSON.stringify(snapshots, null, 2)}\n`, "utf-8");
});

test("static routes expose measurable performance data without foreign runtime requests", async ({ page }) => {
  const home = await measure(page, "/");
  const gallery = await measure(page, "/bilder/");
  for (const snapshot of [home, gallery]) {
    expect(snapshot.navigation.dom_content_loaded_ms).toBeGreaterThanOrEqual(0);
    expect(snapshot.navigation.load_event_ms).toBeGreaterThanOrEqual(0);
    expect(snapshot.navigation.transfer_bytes).toBeGreaterThanOrEqual(0);
    expect(snapshot.external_runtime_requests).toEqual([]);
    expect(snapshot.cls).toBeGreaterThanOrEqual(0);
  }
  expect(gallery.eager_images).toBeLessThanOrEqual(6);
  expect(gallery.lcp_ms === null || gallery.lcp_ms >= 0).toBe(true);
  console.log(JSON.stringify({ performance: snapshots }));
});
