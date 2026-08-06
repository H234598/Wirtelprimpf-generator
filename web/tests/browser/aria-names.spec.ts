import { expect, test } from "@playwright/test";

test("primary navigation and CatGPT modes expose named controls", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });

  const navigation = page.getByRole("navigation", { name: "Hauptnavigation" });
  const navigationSnapshot = await navigation.ariaSnapshot();
  expect(navigationSnapshot).toContain("Bilder");
  expect(navigationSnapshot).toContain("Geschichten");
  expect(navigationSnapshot).toContain("Projekt");

  const modes = page.getByRole("group", { name: "CatGPT-Modus" });
  const modeSnapshot = await modes.ariaSnapshot();
  expect(modeSnapshot).toContain("CatGPT-S");
  expect(modeSnapshot).toContain("CatGPT-L");
});

test("gallery filters and pagination expose their spoken context", async ({ page }) => {
  await page.goto("/bilder/?typ=favorites", { waitUntil: "domcontentloaded" });

  const filter = page.getByRole("navigation", { name: "Galerietyp" });
  const filterSnapshot = await filter.ariaSnapshot();
  expect(filterSnapshot).toContain("Favoriten");
  expect(filterSnapshot).toContain("Alle");

  await page.goto("/bilder/", { waitUntil: "domcontentloaded" });
  const pagination = page.getByRole("navigation", { name: "Galerieseiten" });
  const paginationSnapshot = await pagination.ariaSnapshot();
  expect(paginationSnapshot).toContain("1");
  expect(paginationSnapshot).toContain("2");
});

test("chapter reader exposes a named navigation landmark", async ({ page }) => {
  await page.goto("/geschichten/", { waitUntil: "domcontentloaded" });
  const storyLink = page.locator("a[href^='/geschichten/'][href$='/']:not([href='/geschichten/'])").first();
  await storyLink.click();
  const chapterHref = await page.locator("nav.story-toc a").first().getAttribute("href");
  if (!chapterHref) throw new Error("chapter link missing");

  await page.goto(chapterHref, { waitUntil: "domcontentloaded" });
  const navigation = page.getByRole("navigation", { name: "Kapitelnavigation" });
  const snapshot = await navigation.ariaSnapshot();
  expect(snapshot).toContain("Gesamtansicht");
  expect(snapshot).toMatch(/Kapitel/);
});
