import test from "node:test";
import assert from "node:assert/strict";

import { mediaYear, type MediaItem } from "../src/lib/data.ts";
import {
  availableGalleryYears,
  filterGalleryMedia,
  galleryPageCount,
  galleryPageItems,
  galleryUrl,
  normalizeGalleryState,
  parseGalleryQuery,
  serializeGalleryQuery,
} from "../src/lib/routes.ts";


function item(kind: MediaItem["kind"], year: number | null, id: string): MediaItem {
  return {
    asset_id: id,
    source_path: `${id}.png`,
    kind,
    year,
    width: 100,
    height: 100,
    release_tag: "release",
    original: { asset_name: `${id}.png`, url: "https://github.com/H234598/Wirtelprimpf-0001/releases/download/release/image.png" },
    story_part_path: null,
    variants: [],
  };
}


test("gallery query accepts the canonical fields and drops unknown values when serialized", () => {
  const state = parseGalleryQuery("?typ=story&seite=02&jahr=2026&proseite=50&sort=secret");
  assert.deepEqual(state, { typ: "story", seite: 2, jahr: 2026, proseite: 50 });
  assert.equal(serializeGalleryQuery(state), "?typ=story&seite=2&jahr=2026&proseite=50");
  assert.equal(galleryUrl("/bilder/seite/2/", state), "/bilder/seite/2/?typ=story&seite=2&jahr=2026&proseite=50");
});


test("invalid query values fall back without reflecting unknown parameters", () => {
  assert.deepEqual(parseGalleryQuery("?typ=unsafe&seite=0&jahr=20x6&proseite=24&debug=true"), { typ: "all", seite: 1, jahr: null, proseite: 100 });
  assert.equal(serializeGalleryQuery({ typ: "all", seite: 1, jahr: null, proseite: 100 }), "");
});


test("favorites is a serializable local gallery filter", () => {
  const state = parseGalleryQuery("?typ=favorites&seite=2&proseite=50");
  assert.deepEqual(state, { typ: "favorites", seite: 2, jahr: null, proseite: 50 });
  assert.equal(serializeGalleryQuery(state), "?typ=favorites&seite=2&proseite=50");
});


test("misc groups unknown and test media without absorbing regular images", () => {
  const media = [
    item("unknown", 2026, "u"),
    { ...item("classic", 2026, "test"), source_path: "testbild-2026.png" },
    item("legacy", 2026, "legacy"),
    item("story", 2026, "story"),
  ];
  assert.deepEqual(filterGalleryMedia(media, { typ: "misc", seite: 1, jahr: null, proseite: 20 }).map((entry) => entry.asset_id), ["u", "test"]);
});


test("unknown is a distinct media category and never becomes classic", () => {
  const media = [item("unknown", 2026, "u"), item("classic", 2026, "c"), item("story", 2025, "s")];
  assert.deepEqual(filterGalleryMedia(media, { typ: "unknown", seite: 1, jahr: null, proseite: 20 }).map((entry) => entry.asset_id), ["u"]);
  assert.deepEqual(filterGalleryMedia(media, { typ: "classic", seite: 1, jahr: null, proseite: 20 }).map((entry) => entry.asset_id), ["c"]);
  assert.deepEqual(availableGalleryYears(media), [2026, 2025]);
});


test("year is parsed from the source filename and page state clamps to available results", () => {
  assert.equal(mediaYear("Wirtelprimpf/wirtelprimpf_2026-08-05_02-06-17.png"), 2026);
  assert.equal(mediaYear("without-date.png"), null);
  const media = Array.from({ length: 25 }, (_, index) => item("story", 2026, String(index)));
  const raw = parseGalleryQuery("?seite=9&jahr=2025");
  const normalized = normalizeGalleryState(raw, { items: media });
  assert.deepEqual(normalized, { typ: "all", seite: 1, jahr: null, proseite: 100 });
  assert.equal(galleryPageCount(media, { typ: "all", seite: 1, jahr: null, proseite: 20 }), 2);
  assert.equal(galleryPageItems(media, { typ: "all", seite: 2, jahr: null, proseite: 20 }).length, 5);
});


test("page-size choices include all and change both page count and item slices", () => {
  const media = Array.from({ length: 25 }, (_, index) => item("story", 2026, String(index)));
  assert.deepEqual(parseGalleryQuery("?proseite=all").proseite, "all");
  assert.equal(galleryPageCount(media, { typ: "all", seite: 1, jahr: null, proseite: 10 }), 3);
  assert.equal(galleryPageItems(media, { typ: "all", seite: 2, jahr: null, proseite: 10 }).length, 10);
  assert.equal(galleryPageCount(media, { typ: "all", seite: 1, jahr: null, proseite: "all" }), 1);
  assert.equal(galleryPageItems(media, { typ: "all", seite: 1, jahr: null, proseite: "all" }).length, 25);
});
