import { mkdirSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

const routes = [
  { name: "home", path: "/" },
  { name: "gallery", path: "/bilder/" },
  { name: "stories", path: "/geschichten/" },
];

const viewports = [
  { name: "phone", width: 320, height: 800 },
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "tablet-landscape", width: 1024, height: 768 },
  { name: "desktop", width: 1440, height: 900 },
  { name: "wide", width: 1920, height: 1080 },
];

test("P08 visual sample keeps core routes framed at supported viewports", async ({ page }) => {
  test.setTimeout(60_000);
  const outputDirectory = join(process.cwd(), "test-results", "p08-visual");
  mkdirSync(outputDirectory, { recursive: true });

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    for (const route of routes) {
      await page.goto(route.path, { waitUntil: "domcontentloaded" });
      const scrollY = await page.evaluate(() => {
        window.history.scrollRestoration = "manual";
        window.scrollTo({ top: 0, left: 0, behavior: "auto" });
        return window.scrollY;
      });
      expect(scrollY).toBe(0);
      await expect(page.locator("main")).toBeVisible();
      await expect(page.locator("main h1")).toBeVisible();
      const finalScrollY = await page.evaluate(() => {
        window.history.scrollRestoration = "manual";
        window.scrollTo({ top: 0, left: 0, behavior: "auto" });
        return window.scrollY;
      });
      expect(finalScrollY).toBe(0);

      const metrics = await page.evaluate(() => ({
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
      }));
      expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth);

      if (route.name === "home" && viewport.width <= 560) {
        const launcherBoxes = await page.locator("[data-catgpt-launcher]").evaluateAll((launchers) => launchers.map((launcher) => {
          const box = launcher.getBoundingClientRect();
          return { left: box.left, right: box.right, top: box.top, bottom: box.bottom };
        }));
        const actionBoxes = await page.locator(".hero .button-row a").evaluateAll((links) => links.map((link) => {
          const box = link.getBoundingClientRect();
          return { left: box.left, right: box.right, top: box.top, bottom: box.bottom };
        }));
        expect(launcherBoxes).toHaveLength(2);
        for (const launcherBox of launcherBoxes) {
          for (const actionBox of actionBoxes) {
            const overlaps = launcherBox.left < actionBox.right && launcherBox.right > actionBox.left && launcherBox.top < actionBox.bottom && launcherBox.bottom > actionBox.top;
            expect(overlaps).toBe(false);
          }
        }
      }

      const screenshot = await page.screenshot({
        path: join(outputDirectory, `${route.name}-${viewport.name}.png`),
      });
      expect(screenshot.byteLength).toBeGreaterThan(5_000);
    }
  }
});
