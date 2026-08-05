import { createRequire } from "node:module";
import { readFileSync } from "node:fs";

import { expect, test, type Page } from "@playwright/test";

const require = createRequire(import.meta.url);
const axePath = require.resolve("axe-core/axe.min.js");

async function assertNoForeignRuntimeRequests(page: Page): Promise<void> {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (!["document", "script", "stylesheet", "fetch", "xhr", "websocket"].includes(request.resourceType())) return;
    requests.push(request.url());
  });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const localOrigin = new URL(page.url()).origin;
  const foreign = requests.filter((url) => new URL(url).origin !== localOrigin);
  expect(foreign).toEqual([]);
}

async function runAxe(page: Page): Promise<void> {
  await page.evaluate((source) => {
    const script = document.createElement("script");
    script.textContent = source;
    document.head.append(script);
  }, readFileSync(axePath, "utf8"));
  const result = await page.evaluate(async () => {
    const axe = (window as Window & { axe?: { run: () => Promise<{ violations: Array<{ id: string; impact: string | null }> }> } }).axe;
    if (!axe) throw new Error("axe did not load");
    return axe.run();
  });
  expect(result.violations.filter((violation) => violation.impact === "critical" || violation.impact === "serious")).toEqual([]);
}

test("core routes expose static navigation and no foreign runtime requests", async ({ page }) => {
  await assertNoForeignRuntimeRequests(page);
  for (const route of ["/bilder/", "/geschichten/", "/projekt/status/", "/does-not-exist/"]) {
    const response = await page.goto(route, { waitUntil: "domcontentloaded" });
    expect(response?.status()).toBe(route === "/does-not-exist/" ? 404 : 200);
    await expect(page.locator("main")).toBeVisible();
  }
});

test("gallery pagination preserves page and selected page size", async ({ page }) => {
  await page.goto("/bilder/", { waitUntil: "domcontentloaded" });
  const select = page.locator("[data-gallery-page-size]");
  await expect(select).toHaveValue("20");
  await select.selectOption("50");
  await expect(page).toHaveURL(/\/bilder\/\?proseite=50$/);
  await expect(page.locator("[data-gallery-card]:visible")).toHaveCount(50);
  await page.locator("[data-gallery-pagination][data-gallery-page='2']").click();
  await expect(page).toHaveURL(/\/bilder\/\?seite=2&proseite=50$/);
  await expect(page.locator("[data-gallery-card]:visible")).toHaveCount(50);
  await expect(page.locator("[data-gallery-status]")).toContainText("Seite 2");
  await select.selectOption("all");
  await expect(page).toHaveURL(/\/bilder\/\?proseite=all$/);
  await expect(page.locator("[data-gallery-card]:visible")).toHaveCount(await page.locator("[data-gallery-card]").count());
  await expect(page.locator("[data-gallery-pagination-nav]")).toBeHidden();
});

test("maintenance pages expose only redacted public status", async ({ page }) => {
  for (const route of ["/projekt/", "/projekt/status/"]) {
    const response = await page.goto(route, { waitUntil: "domcontentloaded" });
    expect(response?.status()).toBe(200);
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("nav a[href='/bilder/']")).toBeVisible();
    await expect(page.locator("nav a[href='/geschichten/']")).toBeVisible();
    const body = await page.locator("body").innerText();
    expect(body).not.toMatch(/(?:\/home\/|\/tmp\/|stack trace|api[_ -]?key|secret|password|token)/i);
  }
});

test("seo routes and metadata stay bound to the configured public origin", async ({ page, request }) => {
  for (const route of ["/", "/bilder/"]) {
    await page.goto(route, { waitUntil: "domcontentloaded" });
    const canonical = await page.locator("link[rel='canonical']").getAttribute("href");
    expect(canonical).toMatch(new RegExp(`^https://wirtelprimpf\\.telacore\\.org${route.replaceAll("/", "\\/")}$`));
    await expect(page.locator("meta[property='og:url']")).toHaveAttribute("content", canonical ?? "");
    await expect(page.locator("meta[property='og:title']")).toHaveAttribute("content", /.+/);
  }

  const sitemap = await request.get("/sitemap.xml");
  expect(sitemap.status()).toBe(200);
  expect(await sitemap.text()).toContain("https://wirtelprimpf.telacore.org/");
  const feed = await request.get("/feed.xml");
  expect(feed.status()).toBe(200);
  expect(await feed.text()).toContain("<feed");
  const robots = await request.get("/robots.txt");
  expect(robots.status()).toBe(200);
  expect(await robots.text()).toContain("Sitemap: https://wirtelprimpf.telacore.org/sitemap.xml");
});

test("gallery return keeps filter, page, scroll position and origin focus", async ({ page }) => {
  await page.goto("/bilder/?typ=classic&seite=2", { waitUntil: "domcontentloaded" });
  const visibleCard = page.locator("[data-gallery-card]:not([hidden])").first();
  await expect(visibleCard).toBeVisible();
  await visibleCard.scrollIntoViewIfNeeded();
  await page.evaluate(() => window.scrollBy(0, 120));
  const expectedScroll = await page.evaluate(() => window.scrollY);
  const originId = await visibleCard.locator("a").getAttribute("id");
  expect(originId).toMatch(/^gallery-card-/);
  await visibleCard.locator("a").click();
  await expect(page).toHaveURL(/\/bilder\/archive-/);
  await page.goBack();
  await expect(page).toHaveURL(/\/bilder\/\?typ=classic&seite=2/);
  await expect(page.locator("[data-gallery-card]:not([hidden])").first()).toBeVisible();
  await expect(page.locator(`#${originId}`)).toBeFocused();
  expect(Math.abs((await page.evaluate(() => window.scrollY)) - expectedScroll)).toBeLessThanOrEqual(2);
});

test("empty filters and failed media expose quiet reversible states", async ({ page }) => {
  await page.goto("/bilder/?typ=unknown&jahr=2026", { waitUntil: "domcontentloaded" });
  await expect(page.locator("[data-gallery-empty]")).toBeVisible();
  await expect(page.locator("[data-gallery-status]")).toContainText("0 Bilder");
  await page.locator("#galerie-filter-all").click();
  await expect(page.locator("[data-gallery-empty]")).toBeHidden();
  await page.goto("/bilder/", { waitUntil: "domcontentloaded" });
  const image = page.locator("[data-gallery-card] [data-media-image]").first();
  await image.evaluate((element) => element.dispatchEvent(new Event("error")));
  await expect(page.locator("[data-gallery-card]").first().locator("[data-media-error]")).toBeVisible();
  await expect(image).toBeHidden();
});

test("no JavaScript keeps direct page links and announces the degradation", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("/bilder/", { waitUntil: "domcontentloaded" });
  await expect(page.locator("noscript .noscript-notice")).toContainText("JavaScript ist deaktiviert");
  await expect(page.locator("nav[aria-label=Galerieseiten] a").nth(1)).toHaveAttribute("href", "/bilder/seite/2/");
  await expect(page.locator("[data-gallery-card] a").first()).toHaveAttribute("href", /\/bilder\/archive-/);
  await page.locator("[data-gallery-card] a").first().click();
  await expect(page.locator("a[data-lightbox-open]")).toBeVisible();
  await expect(page.locator("button[data-favorite-id]").first()).toBeHidden();
  await context.close();
});

test("lightbox opens progressively, traps focus and closes on Escape", async ({ page }) => {
  await page.goto("/bilder/", { waitUntil: "domcontentloaded" });
  await page.locator("[data-gallery-card] a").first().click();
  await expect(page.locator("a[download]").first()).toHaveAttribute("href", /\.png$/);
  await page.locator("[data-lightbox-open]").click();
  const dialog = page.locator("dialog[data-lightbox]");
  await expect(dialog).toBeVisible();
  await expect(dialog.locator("[data-lightbox-close]")).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(dialog.locator("[data-lightbox-nav='next']")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(dialog.locator("[data-lightbox-close]")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(page.locator("[data-lightbox-open]")).toBeFocused();
});

test("lightbox horizontal touch navigation uses the canonical next route", async ({ page }) => {
  await page.goto("/bilder/", { waitUntil: "domcontentloaded" });
  await page.locator("[data-gallery-card] a").first().click();
  await page.locator("[data-lightbox-open]").click();
  await page.evaluate(() => {
    const surface = document.querySelector<HTMLElement>("[data-lightbox-surface]");
    if (!surface) throw new Error("lightbox surface missing");
    const touch = (x: number) => new Touch({ identifier: 1, target: surface, clientX: x, clientY: 100 });
    surface.dispatchEvent(new TouchEvent("touchstart", { bubbles: true, changedTouches: [touch(300)] }));
    surface.dispatchEvent(new TouchEvent("touchend", { bubbles: true, changedTouches: [touch(100)] }));
  });
  await expect(page).toHaveURL(/\/bilder\/archive-/);
});

test("media detail exposes canonical previous and next navigation", async ({ page }) => {
  await page.goto("/bilder/", { waitUntil: "domcontentloaded" });
  await page.locator("[data-gallery-card] a").first().click();
  await expect(page.locator("main")).toBeVisible();
  const navigation = page.locator("nav.media-navigation").first();
  await expect(navigation).toBeVisible();
  const detailLinks = navigation.locator("a[href^='/bilder/']");
  const disabledBoundary = navigation.locator("[aria-disabled='true']");
  expect((await detailLinks.count()) + (await disabledBoundary.count())).toBe(2);
  for (const href of await detailLinks.evaluateAll((links) => links.map((link) => link.getAttribute("href")))) {
    expect(href).toMatch(/^\/bilder\/[^/]+\/$/);
  }
});

test("media actions use native fullscreen and share only after capability detection", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(document, "fullscreenEnabled", { configurable: true, value: true });
    Object.defineProperty(HTMLElement.prototype, "requestFullscreen", {
      configurable: true,
      value: async function requestFullscreen() {
        this.setAttribute("data-fullscreen-requested", "true");
      },
    });
    Object.defineProperty(navigator, "share", {
      configurable: true,
      value: async (data: { title: string; url: string }) => {
        (window as Window & { __shared?: unknown }).__shared = data;
      },
    });
  });
  await page.goto("/bilder/", { waitUntil: "domcontentloaded" });
  await page.locator("[data-gallery-card] a").first().click();
  const frame = page.locator("[data-media-frame]").first();
  await expect(page.locator("[data-media-fullscreen]")).toBeVisible();
  await expect(page.locator("[data-media-share]")).toBeVisible();
  await page.locator("[data-media-fullscreen]").click();
  await expect(frame).toHaveAttribute("data-fullscreen-requested", "true");
  await page.locator("[data-media-share]").click();
  expect(await page.evaluate(() => (window as Window & { __shared?: { url?: string } }).__shared?.url)).toContain("/bilder/");
});

test("lightbox exposes a quiet fallback when its media fails", async ({ page }) => {
  await page.goto("/bilder/", { waitUntil: "domcontentloaded" });
  await page.locator("[data-gallery-card] a").first().click();
  await page.locator("[data-lightbox-open]").click();
  const image = page.locator("[data-lightbox-image]");
  await image.evaluate((element) => element.dispatchEvent(new Event("error")));
  await expect(page.locator("dialog [data-media-error]")).toBeVisible();
  await expect(image).toBeHidden();
});

test("reader supports reduced motion, progress control and chapter navigation", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/geschichten/2/", { waitUntil: "domcontentloaded" });
  await page.locator("a[href*='/geschichten/2/band-']").first().click();
  await expect(page.locator("[data-reading-progress]")).toBeVisible();
  await expect(page.locator("[aria-label='Kapitelnavigation']")).toBeVisible();
  expect(await page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches)).toBe(true);
});

test("chapter deep links keep TOC state and navigation without JavaScript", async ({ browser, page }) => {
  await page.goto("/geschichten/2/", { waitUntil: "domcontentloaded" });
  const chapterLink = page.locator("nav.story-toc a").first();
  const chapterHref = await chapterLink.getAttribute("href");
  expect(chapterHref).toMatch(/^\/geschichten\/2\/band-0002-teil-[a-f0-9]{12}\/$/);
  if (!chapterHref) throw new Error("chapter href missing");

  const context = await browser.newContext({ javaScriptEnabled: false });
  const noScriptPage = await context.newPage();
  await noScriptPage.goto(chapterHref, { waitUntil: "domcontentloaded" });
  await expect(noScriptPage.locator("main")).toBeVisible();
  await expect(noScriptPage.locator("nav.story-toc a[aria-current='page']")).toHaveAttribute("href", chapterHref);
  await expect(noScriptPage.locator("nav[aria-label='Kapitelnavigation']")).toBeVisible();
  await context.close();
});

test("comfort state persists locally and can be explicitly cleared", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("wirtelprimpf.site-state.v1", JSON.stringify({
      schema_version: 1,
      theme: "night",
      reading_view: "chapter",
      gallery: { typ: "all", seite: 1, jahr: null, focus_id: null, scroll_y: 0 },
      progress: {},
      favorites: [],
    }));
  });
  await page.goto("/geschichten/2/", { waitUntil: "domcontentloaded" });
  await page.locator("a[href*='/geschichten/2/band-']").first().click();
  await page.locator("[data-reading-save]").click();
  await expect(page.locator("[data-reading-status]")).toContainText("Lesefortschritt gespeichert");
  await page.goto("/bilder/", { waitUntil: "domcontentloaded" });
  const favorite = page.locator("button[data-favorite-id]").first();
  await favorite.click();
  await expect(favorite).toHaveAttribute("aria-pressed", "true");
  await page.locator("[data-settings-toggle]").click();
  await page.locator("[data-settings-clear]").click();
  expect(await page.evaluate(() => localStorage.getItem("wirtelprimpf.site-state.v1"))).toBeNull();
});

test("CatGPT Light falls back silently when the Worker is unavailable", async ({ page }) => {
  await page.addInitScript(() => {
    const nativeFetch = window.fetch.bind(window);
    window.fetch = (input, init) => {
      const url = typeof input === "string" ? input : input instanceof Request ? input.url : String(input);
      if (url.startsWith("https://catgpt.wirtelprimpf.telacore.org/v1/chat")) {
        const state = window as typeof window & { __catgptLightRequests?: string[] };
        state.__catgptLightRequests = [...(state.__catgptLightRequests ?? []), url];
        return Promise.reject(new TypeError("synthetic CatGPT Worker outage"));
      }
      return nativeFetch(input, init);
    };
  });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const lightLauncher = page.locator("[data-catgpt-launcher='light']");
  if (await lightLauncher.isDisabled()) {
    await expect(lightLauncher).toHaveAttribute("aria-label", "CatGPT-L nicht verfügbar");
    return;
  }
  await expect(lightLauncher).toBeEnabled();
  await lightLauncher.click();
  await expect(page.locator("[data-catgpt-window]")).toBeVisible();
  await expect(page.locator("[data-catgpt-shell]")).toHaveAttribute("data-light-endpoint", "https://catgpt.wirtelprimpf.telacore.org/v1/chat");
  expect(await page.evaluate(() => localStorage.getItem("wirtelprimpf-catgpt-mode"))).toBe("light");
  await page.locator("#catgpt-input").fill("Bitte antworte kurz.");
  await page.locator("[data-catgpt-form] button[type='submit']").click();
  await expect(page.locator("[data-catgpt-messages] li[data-role='assistant']")).toHaveCount(1);
  await expect(page.locator("[data-catgpt-messages] li[data-role='assistant']")).toContainText(/.+/);
  expect(await page.evaluate(() => (window as typeof window & { __catgptLightRequests?: string[] }).__catgptLightRequests ?? [])).toEqual([
    "https://catgpt.wirtelprimpf.telacore.org/v1/chat",
  ]);
  await page.locator("[data-catgpt-close]").click();
  await page.locator("[data-catgpt-launcher='static']").click();
  await expect(page.locator("[data-catgpt-title]")).toHaveText("CatGPT-S");
  await expect(page.locator("[data-catgpt-messages] li")).toHaveCount(0);
  expect(await page.evaluate(() => localStorage.getItem("wirtelprimpf-catgpt-mode"))).toBe("static");
  expect(await page.evaluate(() => sessionStorage.getItem("wirtelprimpf-catgpt-history"))).toBeNull();
});

test("CatGPT-L remains Light on a mobile viewport when the Worker replies", async ({ page }) => {
  await page.setViewportSize({ width: 393, height: 852 });
  await page.addInitScript(() => {
    const nativeFetch = window.fetch.bind(window);
    window.fetch = (input, init) => {
      const url = typeof input === "string" ? input : input instanceof Request ? input.url : String(input);
      if (url.startsWith("https://catgpt.wirtelprimpf.telacore.org/v1/chat")) {
        const state = window as typeof window & { __catgptLightRequests?: string[] };
        state.__catgptLightRequests = [...(state.__catgptLightRequests ?? []), url];
        return Promise.resolve(new Response(JSON.stringify({ reply: "Antwort aus CatGPT-L" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }));
      }
      return nativeFetch(input, init);
    };
  });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const lightLauncher = page.locator("[data-catgpt-launcher='light']");
  test.skip(await lightLauncher.isDisabled(), "Light endpoint is not enabled in this build profile");
  await lightLauncher.click();
  await expect(page.locator("[data-catgpt-title]")).toHaveText("CatGPT-L");
  await page.locator("#catgpt-input").fill("Hallo Light");
  await page.locator("[data-catgpt-form] button[type='submit']").click();
  await expect(page.locator("[data-catgpt-messages] li[data-role='assistant']")).toHaveText("Antwort aus CatGPT-L");
  expect(await page.evaluate(() => (window as typeof window & { __catgptLightRequests?: string[] }).__catgptLightRequests ?? [])).toEqual([
    "https://catgpt.wirtelprimpf.telacore.org/v1/chat",
  ]);
});

test("paper theme is visible and switchable through settings", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("wirtelprimpf-theme", "paper"));
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "paper");
  await page.locator("[data-settings-toggle]").click();
  await expect(page.locator("[data-settings-panel]")).toBeVisible();
  await expect(page.locator("[data-theme-option][value='paper']")).toBeChecked();
  await expect(page.locator("body")).toHaveCSS("background-color", "rgb(244, 232, 213)");
  await page.locator("[data-theme-option][value='night']").check();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "night");
  await expect(page.locator("[data-theme-option][value='night']")).toBeChecked();
});

test("keyboard entry points expose the skip link and restore settings focus", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.keyboard.press("Tab");
  await expect(page.locator(".skip-link")).toBeFocused();
  await expect(page.locator(".skip-link")).toBeVisible();
  await page.locator("[data-settings-toggle]").click();
  await expect(page.locator("[data-settings-panel]")).toBeVisible();
  await expect(page.locator("[data-settings-close]")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.locator("[data-settings-toggle]")).toBeFocused();
  await expect(page.locator("[data-settings-toggle]")).toHaveAttribute("aria-expanded", "false");
});

test("320 pixel pages have no horizontal document overflow", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  for (const route of ["/", "/bilder/", "/geschichten/"]) {
    await page.goto(route, { waitUntil: "domcontentloaded" });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    const heading = await page.locator("main h1").evaluate((element) => ({
      clientWidth: element.clientWidth,
      scrollWidth: element.scrollWidth,
    }));
    expect(heading.scrollWidth).toBeLessThanOrEqual(heading.clientWidth);
  }
});

test("mobile story stream and reader stay within the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto("/geschichten/2/", { waitUntil: "domcontentloaded" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const story = page.locator(".story-overview");
  expect(await story.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  expect(await page.locator(".story-part").first().evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
});

test("mobile main navigation keeps every link fully visible", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const geometry = await page.locator(".site-header > nav").evaluate((nav) => {
    const bounds = nav.getBoundingClientRect();
    return Array.from(nav.querySelectorAll("a")).map((link) => {
      const linkBounds = link.getBoundingClientRect();
      return {
        label: link.textContent?.trim(),
        left: linkBounds.left,
        right: linkBounds.right,
        top: linkBounds.top,
        bottom: linkBounds.bottom,
        width: linkBounds.width,
        navLeft: bounds.left,
        navRight: bounds.right,
        navTop: bounds.top,
        navBottom: bounds.bottom,
      };
    });
  });
  expect(geometry.map(({ label }) => label)).toEqual(["Start", "Bilder", "Geschichten", "Projekt"]);
  for (const link of geometry) {
    expect(link.width).toBeGreaterThan(0);
    expect(link.left).toBeGreaterThanOrEqual(link.navLeft);
    expect(link.right).toBeLessThanOrEqual(link.navRight);
    expect(link.top).toBeGreaterThanOrEqual(link.navTop);
    expect(link.bottom).toBeLessThanOrEqual(link.navBottom);
  }
});

test("mobile settings and CatGPT overlays stay in the viewport and exclude each other", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.locator("[data-catgpt-launcher='static']")).toBeEnabled();
  const viewport = { width: 320, height: 800 };
  const assertInsideViewport = async (selector: string): Promise<void> => {
    const box = await page.locator(selector).boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width);
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.y + box!.height).toBeLessThanOrEqual(viewport.height);
  };

  await page.locator("[data-settings-toggle]").click();
  await expect(page.locator("[data-settings-panel]")).toBeVisible();
  await assertInsideViewport("[data-settings-panel]");
  await page.locator("[data-catgpt-launcher='static']").click();
  await expect(page.locator("[data-settings-panel]")).toBeHidden();
  await expect(page.locator("[data-catgpt-window]")).toBeVisible();
  await assertInsideViewport("[data-catgpt-window]");
  await page.locator("[data-settings-toggle]").click();
  await expect(page.locator("[data-catgpt-window]")).toBeHidden();
  await expect(page.locator("[data-settings-panel]")).toBeVisible();
  await assertInsideViewport("[data-settings-panel]");
});

test("tablet and desktop layouts keep their content inside the viewport", async ({ page }) => {
  for (const width of [768, 1440, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/bilder/", { waitUntil: "domcontentloaded" });
    const metrics = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth);
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("main h1")).toBeVisible();
  }
});

test("storage failure does not break the page", async ({ browser }) => {
  const context = await browser.newContext();
  await context.addInitScript(() => {
    Object.defineProperty(window, "localStorage", {
      configurable: false,
      get() {
        throw new DOMException("blocked", "SecurityError");
      },
    });
  });
  const page = await context.newPage();
  await page.goto("/geschichten/", { waitUntil: "domcontentloaded" });
  await expect(page.locator("main")).toBeVisible();
  await context.close();
});

test("home, gallery and story pages pass serious and critical axe checks", async ({ page }) => {
  for (const route of ["/", "/bilder/", "/geschichten/"]) {
    await page.goto(route, { waitUntil: "domcontentloaded" });
    await runAxe(page);
  }
});
