import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import {
  classifyStoryPart,
  fallbackStoryTitle,
  parseStoryDocument,
} from "../src/lib/content.ts";
import type { MediaItem } from "../src/lib/data.ts";
import { formatDownloadSize, isValidEpubBytes, loadEpubDownloads } from "../src/lib/epub.ts";
import {
  chapterAnchor,
  chapterForMedia,
  chapterNavigation,
  chapterPath,
  mediaForChapter,
} from "../src/lib/story-routes.ts";


function storyFixture() {
  return parseStoryDocument(`# Teststory

## 2026-08-01 10:00:00

Erstes Kapitel.

## 2026-08-01 11:00:00

Zweites Kapitel.

## 2026-08-01 12:00:00

Drittes Kapitel.
`, "Wirtelprimpf_Story_I.md", 1);
}


function mediaFixture(path: string): MediaItem {
  return {
    asset_id: "asset-1",
    source_path: "Wirtelprimpf/example.png",
    kind: "story",
    year: 2026,
    width: 1200,
    height: 900,
    release_tag: "archive-0001-media-0001",
    original: {
      asset_name: "example.png",
      url: "https://github.com/H234598/Wirtelprimpf-0001/releases/download/archive-0001-media-0001/example.png",
    },
    story_part_path: path,
    variants: [],
  };
}


function epubFixture(): Buffer {
  const mimetype = Buffer.from("application/epub+zip", "utf8");
  const header = Buffer.alloc(30);
  header.write("PK\x03\x04", 0, "ascii");
  header.writeUInt16LE(0, 6);
  header.writeUInt16LE(0, 8);
  header.writeUInt32LE(mimetype.length, 18);
  header.writeUInt32LE(mimetype.length, 22);
  header.writeUInt16LE("mimetype".length, 26);
  return Buffer.concat([header, Buffer.from("mimetype", "ascii"), mimetype]);
}


test("chapter routes use stable source IDs and navigate by neighboring IDs", () => {
  const story = storyFixture();
  const first = story.parts[0]!;
  const middle = story.parts[1]!;
  const last = story.parts[2]!;

  assert.match(first.id, /^band-0001-teil-[a-f0-9]{12}$/);
  assert.equal(chapterPath(story.volume, middle.id), `/geschichten/1/${middle.id}/`);
  assert.equal(chapterAnchor(middle.id), `#${middle.id}`);
  assert.deepEqual(chapterNavigation(story, first.id), { previous: null, next: middle });
  assert.deepEqual(chapterNavigation(story, middle.id), { previous: first, next: last });
  assert.deepEqual(chapterNavigation(story, last.id), { previous: middle, next: null });
  assert.throws(() => chapterPath(1, "1"), /unsafe chapter id/);
  assert.throws(() => chapterAnchor("#bad"), /unsafe chapter id/);
});


test("missing titles use the documented fallback and empty chapters stay classified", () => {
  const missingTitle = parseStoryDocument("## 2026-08-01 10:00:00\n\nText.\n", "story.md", 7);
  assert.equal(missingTitle.title, fallbackStoryTitle(7));
  assert.equal(classifyStoryPart(missingTitle.parts[0]!), "ready");

  const emptyChapter = parseStoryDocument("# Leer\n\n## 2026-08-01 10:00:00\n\n", "story.md", 8);
  assert.equal(classifyStoryPart(emptyChapter.parts[0]!), "empty");
  assert.equal(parseStoryDocument("# Noch leer\n", "story.md", 9).parts.length, 0);
});


test("story image paths pair to a chapter by their source timestamp", () => {
  const story = storyFixture();
  const part = story.parts[1]!;
  const item = mediaFixture("Wirtelprimpf/wirtelprimpf_2026-08-01_11-00-00-123456_story-01.md");

  assert.deepEqual(chapterForMedia(item, [story]), { story, part });
  assert.deepEqual(mediaForChapter([item], story, part), [item]);
  assert.deepEqual(mediaForChapter([item], story, story.parts[0]!), []);
  assert.equal(chapterForMedia(mediaFixture("Wirtelprimpf/unrelated_story.md"), [story]), null);
});


test("a validated sidecar chapter ID resolves filename timestamp drift", () => {
  const story = storyFixture();
  const part = story.parts[1]!;
  const item = { ...mediaFixture("Wirtelprimpf/generated-at-2026-08-01_20-00-00.md"), story_part_id: part.id };

  assert.deepEqual(chapterForMedia(item, [story]), { story, part });
  assert.deepEqual(mediaForChapter([item], story, part), [item]);
  assert.deepEqual(mediaForChapter([item], story, story.parts[0]!), []);
});


test("EPUB downloads are fail-closed and reject non-EPUB or LFS content", () => {
  const bytes = epubFixture();
  assert.equal(isValidEpubBytes(bytes), true);
  assert.equal(isValidEpubBytes(Buffer.from("version https://git-lfs.github.com/spec/v1\n")), false);
  assert.equal(formatDownloadSize(bytes.length), "1 KB");

  const root = mkdtempSync(join(process.cwd(), ".test-epub-contract-"));
  try {
    assert.deepEqual(loadEpubDownloads(root, "H234598", "Wirtelprimpf-0001"), []);
    const filename = "story-abcdef1234567890.epub";
    writeFileSync(join(root, filename), bytes);
    writeFileSync(join(root, "epub-manifest.json"), JSON.stringify({
      schema_version: "1.0.0",
      downloads: [{
        volume: 1,
        asset_name: filename,
        url: `https://github.com/H234598/Wirtelprimpf-0001/releases/download/archive-0001-epub-0001/${filename}`,
        size_bytes: bytes.length,
        sha256: createHash("sha256").update(bytes).digest("hex"),
        mime_type: "application/epub+zip",
        header_verified: true,
        release_asset_verified: true,
        local_path: filename,
      }],
    }));
    const downloads = loadEpubDownloads(root, "H234598", "Wirtelprimpf-0001");
    assert.equal(downloads[0]?.volume, 1);
    assert.equal(downloads[0]?.asset_name, filename);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});


test("EPUB downloads may come from any verified publication archive", () => {
  const root = mkdtempSync(join(process.cwd(), ".test-epub-repositories-"));
  try {
    const filename = "story-51-abcdef1234567890.epub";
    writeFileSync(join(root, "epub-manifest.json"), JSON.stringify({
      schema_version: "1.0.0",
      downloads: [{
        volume: 51,
        asset_name: filename,
        url: `https://github.com/H234598/Wirtelprimpf-0002/releases/download/archive-0002-epub-0001/${filename}`,
        size_bytes: 31,
        sha256: "a".repeat(64),
        mime_type: "application/epub+zip",
        header_verified: true,
        release_asset_verified: true,
      }],
    }));

    const downloads = loadEpubDownloads(root, "H234598", ["Wirtelprimpf-0001", "Wirtelprimpf-0002"]);
    assert.equal(downloads[0]?.volume, 51);
    assert.throws(
      () => loadEpubDownloads(root, "H234598", "Wirtelprimpf-0001"),
      /not bound to a verified archive/,
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});


test("reader, TOC, band and detail routes expose the chapter relationship", () => {
  const reader = readFileSync(new URL("../src/components/Reader.astro", import.meta.url), "utf8");
  const toc = readFileSync(new URL("../src/components/StoryToc.astro", import.meta.url), "utf8");
  const band = readFileSync(new URL("../src/pages/geschichten/[volume].astro", import.meta.url), "utf8");
  const chapter = readFileSync(new URL("../src/pages/geschichten/[volume]/[chapter].astro", import.meta.url), "utf8");
  const library = readFileSync(new URL("../src/pages/geschichten/index.astro", import.meta.url), "utf8");
  const detail = readFileSync(new URL("../src/components/MediaDetail.astro", import.meta.url), "utf8");
  const noScript = readFileSync(new URL("../src/components/NoScriptNotice.astro", import.meta.url), "utf8");

  assert.match(reader, /chapterMediaHref/);
  assert.match(reader, /Kapitelnavigation/);
  assert.match(toc, /chapterPath/);
  assert.match(band, /StoryToc/);
  assert.match(band, /chapterHref/);
  assert.match(chapter, /getStaticPaths/);
  assert.match(chapter, /mediaForChapter/);
  assert.match(library, /EpubDownload/);
  assert.match(library, /compact/);
  assert.match(detail, /storyHref/);
  assert.match(noScript, /<noscript>/);
});
