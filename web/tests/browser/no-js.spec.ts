import { expect, test } from "@playwright/test";


test("no JavaScript hides enhancement controls and keeps core routes usable", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();

  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.locator(".noscript-notice")).toContainText("JavaScript ist deaktiviert");
  await expect(page.locator("[data-settings-shell]")).toBeHidden();
  await expect(page.locator("[data-catgpt-shell]")).toBeHidden();
  await expect(page.locator("a[href='/bilder/']").first()).toBeVisible();
  await expect(page.locator("a[href='/geschichten/']").first()).toBeVisible();
  expect(await page.locator("button:visible").count()).toBe(0);

  await page.goto("/bilder/", { waitUntil: "domcontentloaded" });
  await expect(page.locator("nav[aria-label='Galerieseiten'] a").nth(1)).toHaveAttribute("href", "/bilder/seite/2/");
  await expect(page.locator("[data-gallery-card] a").first()).toBeVisible();
  await page.locator("[data-gallery-card] a").first().click();
  await expect(page).toHaveURL(/\/bilder\/[^/]+\/$/);
  await expect(page.locator("a[download]").first()).toBeVisible();
  await expect(page.locator("a[data-lightbox-open]")).toBeVisible();
  await expect(page.locator("dialog[data-lightbox]")).toBeHidden();

  await page.goto("/geschichten/", { waitUntil: "domcontentloaded" });
  await page.locator("a[href^='/geschichten/'][href$='/']:not([href='/geschichten/'])").first().click();
  await expect(page).toHaveURL(/\/geschichten\/\d+\/$/);
  const chapter = page.locator("nav.story-toc a").first();
  const chapterHref = await chapter.getAttribute("href");
  expect(chapterHref).toMatch(/^\/geschichten\/\d+\/band-[a-z0-9-]+\/$/);
  await chapter.click();
  await expect(page.locator("nav[aria-label='Kapitelnavigation']")).toBeVisible();
  await expect(page.locator("[data-reading-control]")).toBeHidden();
  expect(await page.locator("button:visible").count()).toBe(0);

  await context.close();
});
