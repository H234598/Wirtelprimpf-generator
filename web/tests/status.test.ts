import assert from "node:assert/strict";
import test from "node:test";

import { parsePublicWebStatus } from "../src/lib/status.ts";

const valid = {
  schema_version: "1.0.0",
  profile: "hub",
  repository: "Wirtelprimpf-generator",
  archive_index: null,
  source_revision: "a".repeat(40),
  media: { count: 1, latest_id: "asset-1", latest_source_path: "Wirtelprimpf/image.png", latest_sha256: "b".repeat(64) },
  stories: { count: 1, chapter_count: 1, latest_id: "band-0001-teil-" + "c".repeat(12), latest_volume: 1, latest_timestamp: "2026-08-05T01:00:00Z" },
  publication: { manifest_generated_at: "2026-08-05T02:00:00Z" },
  build: { built_at: "2026-08-05T04:00:00Z", source_date_epoch: null },
  freshness: { state: "warning", last_published_at: "2026-08-05T02:00:00Z", age_seconds: 7200, warning_after_seconds: 5400, stale_after_seconds: 10800 },
};

test("public status accepts the versioned redacted contract", () => {
  assert.equal(parsePublicWebStatus(valid).freshness.state, "warning");
});

test("public status rejects local paths and invalid revisions", () => {
  assert.throws(() => parsePublicWebStatus({ ...valid, source_revision: "not-a-revision" }));
  assert.throws(() => parsePublicWebStatus({ ...valid, media: { ...valid.media, latest_source_path: "/home/teladi/private.png" } }));
});
