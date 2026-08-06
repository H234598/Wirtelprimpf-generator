import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const root = new URL("../src/", import.meta.url);
const layout = readFileSync(new URL("layouts/BaseLayout.astro", root), "utf8");
const index = readFileSync(new URL("pages/index.astro", root), "utf8");
const mediaCard = readFileSync(new URL("components/MediaCard.astro", root), "utf8");
const projectStatus = readFileSync(new URL("pages/projekt/status.astro", root), "utf8");

test("approved public copy is exact and superseded wording is absent", () => {
  assert.match(layout, /<small>Telacores:<\/small>/);
  assert.doesNotMatch(layout, /Zentrale Landingpage/);

  assert.doesNotMatch(index, /Die kanonische Storyansicht bleibt zusätzlich chronologisch lesbar\./);
  assert.doesNotMatch(index, /Keine leeren Repositories, keine Lücken\./);
  assert.match(index, /Wo Katzen Unfug und Geschichte schreiben\./);
  assert.doesNotMatch(index, /Wo Katzen, Möhren und Unfug Geschichte schreiben\./);

  assert.match(mediaCard, /Im Release <code>\{item\.release_tag\}<\/code> archiviert\./);
  assert.doesNotMatch(mediaCard, /hashgebunden archiviert/);

  assert.match(projectStatus, /Dass er unbedeutend ist, und nichts weiß\./);
  assert.doesNotMatch(projectStatus, /Keine Live-API, keine Trackingabfrage/);
  const project = readFileSync(new URL("pages/projekt/index.astro", root), "utf8");
  assert.doesNotMatch(project, /Diese Spiegelung wird bei jedem Build aus der README\.md erzeugt/);
});
