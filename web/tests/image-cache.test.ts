import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";


test("historical release image manifest binds every media item to its two stored derivative widths", () => {
  const manifest = JSON.parse(readFileSync(join(process.cwd(), "../data/media-manifest.json"), "utf8")) as {
    schema_version: string;
    media: Array<{ sha256: string; variants: Array<{ requested_width: number; sha256: string; mime_type: string }> }>;
  };
  assert.equal(manifest.schema_version, "1.0.0");
  assert.ok(manifest.media.length > 0);
  for (const item of manifest.media) {
    assert.match(item.sha256, /^[a-f0-9]{64}$/);
    assert.deepEqual(item.variants.map((variant) => variant.requested_width), [640, 1280]);
    assert.ok(item.variants.every((variant) => /^[a-f0-9]{64}$/.test(variant.sha256)));
    assert.ok(item.variants.every((variant) => variant.mime_type === "image/webp"));
  }
});
