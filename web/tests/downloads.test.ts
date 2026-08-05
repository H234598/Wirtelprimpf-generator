import test from "node:test";
import assert from "node:assert/strict";

import { resolveDownload } from "../src/lib/downloads.ts";

const validUrl = "https://github.com/H234598/Wirtelprimpf-0001/releases/download/archive-0001-media-0001/image-abcdef0123456789.png";

test("resolveDownload keeps valid release assets as original downloads", () => {
  assert.deepEqual(resolveDownload({ asset_name: "image.png", url: validUrl }), {
    filename: "image.png",
    href: validUrl,
  });
});

test("resolveDownload fails closed for missing or non-release targets", () => {
  assert.equal(resolveDownload(null), null);
  assert.equal(resolveDownload({ asset_name: "image.png", url: "https://example.test/image.png" }), null);
  assert.equal(resolveDownload({ asset_name: "../image.png", url: validUrl }), null);
  assert.equal(resolveDownload({ asset_name: "image.png", url: `${validUrl}?download=1` }), null);
});
