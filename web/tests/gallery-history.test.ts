import { strict as assert } from "node:assert";
import { test } from "node:test";

import {
  galleryHistoryEntry,
  parseGalleryHistoryEntry,
  withGalleryHistoryEntry,
} from "../src/scripts/gallery-history.ts";


test("gallery history accepts a bounded focus and scroll entry", () => {
  const entry = { focusId: "gallery-card-asset-1", scrollY: 720 };
  assert.deepEqual(parseGalleryHistoryEntry(entry), entry);
  assert.deepEqual(galleryHistoryEntry({ gallery: entry }), entry);
});


test("gallery history rejects malformed or unsafe entries", () => {
  assert.equal(parseGalleryHistoryEntry(null), null);
  assert.equal(parseGalleryHistoryEntry({ focusId: "bad id", scrollY: 1 }), null);
  assert.equal(parseGalleryHistoryEntry({ focusId: "gallery-card-1", scrollY: -1 }), null);
  assert.equal(parseGalleryHistoryEntry({ focusId: "gallery-card-1", scrollY: 1.5 }), null);
  assert.equal(galleryHistoryEntry({ gallery: { focusId: "gallery-card-1" } }), null);
});


test("gallery history preserves unrelated browser state", () => {
  const entry = { focusId: "gallery-card-asset-1", scrollY: 120 };
  assert.deepEqual(withGalleryHistoryEntry({ route: "gallery" }, entry), {
    route: "gallery",
    gallery: entry,
  });
  assert.deepEqual(withGalleryHistoryEntry("unexpected", entry), { gallery: entry });
});
