import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import type { MediaItem } from "../src/lib/data.ts";
import { neighboringMedia } from "../src/lib/routes.ts";


function item(id: string): MediaItem {
  return {
    asset_id: id,
    source_path: `${id}.png`,
    kind: "story",
    year: 2026,
    width: 100,
    height: 100,
    release_tag: "release",
    original: { asset_name: `${id}.png`, url: "https://github.com/H234598/Wirtelprimpf-0001/releases/download/archive-0001-media-0001/image-abcdef0123456789.png" },
    story_part_path: "story.md",
    variants: [{ requested_width: 640, actual_width: 640, actual_height: 640, asset_name: `${id}.webp`, url: "https://github.com/H234598/Wirtelprimpf-0001/releases/download/archive-0001-media-0001/image-abcdef0123456789.webp", mime_type: "image/webp" }],
  };
}


test("detail navigation preserves the ordered gallery and boundaries", () => {
  const media = [item("new"), item("current"), item("old")];
  assert.deepEqual(neighboringMedia(media, "current"), { previous: media[0], next: media[2] });
  assert.deepEqual(neighboringMedia(media, "new"), { previous: null, next: media[1] });
  assert.deepEqual(neighboringMedia(media, "missing"), { previous: null, next: null });
});


test("detail and lightbox retain progressive accessibility contracts", () => {
  const detail = readFileSync(new URL("../src/components/MediaDetail.astro", import.meta.url), "utf8");
  const lightbox = readFileSync(new URL("../src/components/Lightbox.astro", import.meta.url), "utf8");
  const script = readFileSync(new URL("../src/scripts/lightbox.ts", import.meta.url), "utf8");
  const actions = readFileSync(new URL("../src/components/ImageActions.astro", import.meta.url), "utf8");
  const actionScript = readFileSync(new URL("../src/scripts/image-actions.ts", import.meta.url), "utf8");
  assert.match(detail, /data-lightbox-open/);
  assert.match(actions, /download=/);
  assert.match(detail, /story_part_path/);
  assert.match(lightbox, /<dialog[^>]+data-lightbox/);
  assert.match(lightbox, /data-lightbox-nav="previous"/);
  assert.match(lightbox, /data-lightbox-nav="next"/);
  assert.match(script, /showModal/);
  assert.match(script, /event\.key !== "Tab"/);
  assert.match(script, /deltaX/);
  assert.match(script, /ArrowLeft/);
  assert.match(actions, /data-media-fullscreen/);
  assert.match(actions, /data-media-share/);
  assert.match(actionScript, /requestFullscreen/);
  assert.match(actionScript, /navigator\.share/);
});
