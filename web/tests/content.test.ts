import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import {
  assertReleaseAssetUrl,
  parseStoryDocument,
  renderSafeMarkdown,
  sortStoryPartsNewestFirst,
} from "../src/lib/content.ts";
import { loadStories } from "../src/lib/data.ts";


function relativeLuminance(hex: string): number {
  const channels = hex.match(/[0-9a-f]{2}/gi)?.map((channel) => Number.parseInt(channel, 16) / 255);
  assert.equal(channels?.length, 3);
  const linear = channels!.map((channel) => (
    channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
  ));
  return 0.2126 * linear[0]! + 0.7152 * linear[1]! + 0.0722 * linear[2]!;
}


function contrastRatio(first: string, second: string): number {
  const firstLuminance = relativeLuminance(first);
  const secondLuminance = relativeLuminance(second);
  return (Math.max(firstLuminance, secondLuminance) + 0.05)
    / (Math.min(firstLuminance, secondLuminance) + 0.05);
}


test("story parts are parsed chronologically and can be rendered newest first", () => {
  const story = parseStoryDocument(`# Die funkelnde Möhre

## 2026-07-01 10:00:00

Erster Teil.

## 2026-07-01 12:00:00

Zweiter Teil.
`, "Wirtelprimpf_Story_II.md", 2);

  assert.equal(story.title, "Die funkelnde Möhre");
  assert.deepEqual(story.parts.map((part) => part.timestamp), [
    "2026-07-01 10:00:00",
    "2026-07-01 12:00:00",
  ]);
  assert.deepEqual(sortStoryPartsNewestFirst(story.parts).map((part) => part.timestamp), [
    "2026-07-01 12:00:00",
    "2026-07-01 10:00:00",
  ]);
  assert.match(story.parts[0]?.id ?? "", /^band-0002-teil-[a-f0-9]{12}$/);
});


test("unsafe markdown HTML, scripts and javascript URLs are removed", () => {
  const rendered = renderSafeMarkdown(`Hallo **Welt**.

<script>alert(1)</script>

[böse](javascript:alert(1))
`);

  assert.match(rendered, /<strong>Welt<\/strong>/);
  assert.doesNotMatch(rendered, /<script/i);
  assert.doesNotMatch(rendered, /javascript:/i);
});


test("only hash-bound release URLs from the declared archive are accepted", () => {
  const valid = "https://github.com/H234598/Wirtelprimpf-0001/releases/download/archive-0001-media-0001/wirtel--abcdef1234567890.w640.webp";
  assert.equal(assertReleaseAssetUrl(valid, "H234598", "Wirtelprimpf-0001"), valid);
  assert.throws(
    () => assertReleaseAssetUrl("https://attacker.invalid/image.webp", "H234598", "Wirtelprimpf-0001"),
    /release asset URL/,
  );
  assert.throws(
    () => assertReleaseAssetUrl("https://github.com/H234598/Other/releases/download/tag/x.webp", "H234598", "Wirtelprimpf-0001"),
    /release asset URL/,
  );
});


test("hub loads the explicit current story with its declared global volume", () => {
  const root = mkdtempSync(join(process.cwd(), ".test-hub-story-"));
  try {
    writeFileSync(join(root, "current-story.md"), "# Band zwei\n\n## 2026-07-31 20:00:00\n\nAktuell.\n");
    writeFileSync(join(root, "hub-source.json"), JSON.stringify({
      schema_version: "1.0.0",
      current_volume: 2,
      repository: "Wirtelprimpf-0001",
      story_path: "Wirtelprimpf/Wirtelprimpf_Story_II.md",
    }));

    const stories = loadStories(root, "hub");

    assert.equal(stories.length, 1);
    assert.equal(stories[0]?.volume, 2);
    assert.equal(stories[0]?.title, "Band zwei");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});


test("code inside paper story cards keeps WCAG AA text contrast", () => {
  const css = readFileSync(new URL("../src/styles/global.css", import.meta.url), "utf8");
  const paper = css.match(/--paper:\s*(#[0-9a-f]{6})/i)?.[1];
  const paperCode = css.match(/--paper-code:\s*(#[0-9a-f]{6})/i)?.[1];

  assert.ok(paper);
  assert.ok(paperCode);
  assert.match(css, /\.story-part code\s*\{[^}]*color:\s*var\(--paper-code\)/s);
  assert.ok(contrastRatio(paperCode, paper) >= 4.5);
});
