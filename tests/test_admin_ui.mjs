import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  FormSyncState,
  InteractionGate,
  RequestEpochGate,
  controlValue,
  isConflictPayload,
  mergeConflictSnapshot,
  modelOptions,
  numericBounds,
  optionValuesMatch,
  reconcileControlValue,
  statusLabels,
  withInteractionSave,
} from "../wirtelprimpf_platform/static/admin.mjs";

test("polling updates clean fields but preserves and marks a dirty conflict", () => {
  const state = new FormSyncState({
    revision: "r1",
    settings: { operandi: "story", site_title: "Alt" },
  });
  state.change("site_title", "Mein Entwurf");
  const merged = state.mergeSnapshot({
    revision: "r2",
    settings: { operandi: "both", site_title: "Extern" },
  });
  assert.equal(merged.operandi, "both");
  assert.equal(merged.site_title, "Mein Entwurf");
  assert.deepEqual([...state.dirty], ["site_title"]);
  assert.deepEqual([...state.conflicts], ["site_title"]);
});

test("returning to the typed server value clears the public draft", () => {
  const state = new FormSyncState({
    revision: "r1",
    settings: { timer_enabled: true, site_title: "Alt" },
  });
  state.change("site_title", "Neu");
  state.change("site_title", "Alt");

  assert.deepEqual([...state.dirty], []);
  assert.deepEqual([...state.baseValues], []);
  assert.equal(state.baseRevision, null);

  state.change("timer_enabled", 1);
  assert.deepEqual([...state.dirty], ["timer_enabled"]);
});

test("request contains only dirty values and their original bases", () => {
  const state = new FormSyncState({
    revision: "r1",
    settings: { operandi: "story", site_title: "Alt" },
  });
  state.change("site_title", "Neu");
  assert.deepEqual(state.buildRequest({ site_title: "Neu" }, {}), {
    base_revision: "r1",
    changes: { site_title: "Neu" },
    base_values: { site_title: "Alt" },
    secret_actions: {},
  });
});

test("empty and invalid numeric controls stay invalid and cannot enter a request", () => {
  assert.equal(controlValue({ type: "number", value: "" }), null);
  assert.equal(controlValue({ type: "number", value: "not-a-number" }), null);
  assert.equal(controlValue({ type: "number", value: "120" }), 120);

  const state = new FormSyncState({
    revision: "r1",
    settings: { generation_interval_minutes: 120 },
  });
  state.change("generation_interval_minutes", null);
  assert.throws(
    () => state.buildRequest({ generation_interval_minutes: null }, {}),
    /invalid local value/,
  );
});

test("clean controls reconcile only when unfocused and materially changed", () => {
  const control = { type: "text", value: "Alt" };
  assert.equal(reconcileControlValue(control, "Extern", control), false);
  assert.equal(control.value, "Alt");
  assert.equal(reconcileControlValue(control, "Alt", null), false);
  assert.equal(reconcileControlValue(control, "Extern", null), true);
  assert.equal(control.value, "Extern");
});

test("unchanged select catalogs preserve their existing option nodes", () => {
  const select = { options: [{ value: "story" }, { value: "both" }] };
  assert.equal(optionValuesMatch(select, [{ value: "story" }, { value: "both" }]), true);
  assert.equal(optionValuesMatch(select, [{ value: "classic" }, { value: "both" }]), false);
});

test("numeric bounds come from the public settings invariants", () => {
  const invariants = {
    numeric_bounds: {
      generation_interval_minutes: { minimum: 30, maximum: 10_080 },
      story_finish_parts_min: { minimum: 1, maximum: 12 },
    },
  };
  assert.deepEqual(numericBounds(invariants, "generation_interval_minutes"), {
    minimum: 30,
    maximum: 10_080,
  });
  assert.equal(numericBounds({}, "generation_interval_minutes"), null);
});

test("missing status timer and story sections render as wholly unknown", () => {
  for (const status of [{}, { timer: null, story: null }]) {
    const labels = statusLabels(status);
    assert.equal(labels.timer, "Unbekannt");
    assert.equal(labels.story, "Unbekannt");
  }
});

test("conflict payloads require a usable snapshot and a conflicts array", () => {
  const valid = {
    snapshot: {
      revision: "r2",
      settings: { site_title: "Extern" },
      choices: {},
      secrets: {},
      invariants: {},
    },
    conflicts: ["site_title"],
  };
  assert.equal(isConflictPayload(valid), true);
  assert.equal(isConflictPayload({ snapshot: null, conflicts: [] }), false);
  assert.equal(isConflictPayload({ snapshot: valid.snapshot, conflicts: null }), false);
  assert.equal(isConflictPayload({ snapshot: {}, conflicts: [] }), false);
});

test("legacy model remains visible without becoming a catalog choice", () => {
  assert.deepEqual(modelOptions(["gpt-5-mini", "gpt-4.1"], "retired-model"), [
    {
      value: "retired-model",
      label: "retired-model · konfiguriert · nicht mehr im empfohlenen Katalog",
      legacy: true,
    },
    { value: "gpt-5-mini", label: "gpt-5-mini", legacy: false },
    { value: "gpt-4.1", label: "gpt-4.1", legacy: false },
  ]);
});

test("saved snapshot clears dirty and conflict state only after explicit acceptance", () => {
  const state = new FormSyncState({
    revision: "r1",
    settings: { operandi: "story", site_title: "Alt" },
  });
  state.change("site_title", "Mein Entwurf");
  state.mergeSnapshot({
    revision: "r2",
    settings: { operandi: "story", site_title: "Extern" },
  });
  assert.deepEqual([...state.dirty], ["site_title"]);
  assert.deepEqual([...state.conflicts], ["site_title"]);

  state.acceptSavedSnapshot({
    revision: "r3",
    settings: { operandi: "story", site_title: "Mein Entwurf" },
  });

  assert.deepEqual([...state.dirty], []);
  assert.deepEqual([...state.conflicts], []);
  assert.equal(state.baseRevision, null);
  assert.deepEqual([...state.baseValues], []);
  assert.equal(state.revision, "r3");
});

test("secret actions remain separate from sparse non-secret changes", () => {
  const state = new FormSyncState({ revision: "r1", settings: { operandi: "story" } });
  state.change("operandi", "both");
  state.markSecretDirty("openai_api_key");
  const request = state.buildRequest(
    { operandi: "both" },
    { openai_api_key: { action: "replace", value: "test-secret-never-log" } },
  );
  assert.deepEqual(request.changes, { operandi: "both" });
  assert.equal(Object.hasOwn(request.changes, "openai_api_key"), false);
  assert.deepEqual(request.secret_actions, {
    openai_api_key: { action: "replace", value: "test-secret-never-log" },
  });
});

test("secret edit keeps its original base revision across polling", () => {
  const state = new FormSyncState({ revision: "r1", settings: { operandi: "story" } });
  state.markSecretDirty("cloudflare_api_token");
  state.mergeSnapshot({ revision: "r2", settings: { operandi: "both" } });
  const request = state.buildRequest(
    {},
    { cloudflare_api_token: { action: "replace", value: "test-secret-never-log" } },
  );
  assert.equal(request.base_revision, "r1");
  assert.deepEqual([...state.secretDirty], ["cloudflare_api_token"]);
  state.discardSecret("cloudflare_api_token");
  assert.equal(state.baseRevision, null);
});

test("discard accepts the current server value and clears the field conflict", () => {
  const state = new FormSyncState({ revision: "r1", settings: { site_title: "Alt" } });
  state.change("site_title", "Mein Entwurf");
  state.mergeSnapshot({ revision: "r2", settings: { site_title: "Extern" } });
  assert.equal(state.discard("site_title"), "Extern");
  assert.deepEqual([...state.dirty], []);
  assert.deepEqual([...state.conflicts], []);
  assert.deepEqual([...state.baseValues], []);
  assert.equal(state.baseRevision, null);
});

test("poll response started before a save cannot overwrite the save result", () => {
  const gate = new RequestEpochGate();
  const pollEpoch = gate.beginPoll();
  assert.equal(pollEpoch, 0);
  gate.beginSave();
  assert.equal(gate.acceptPoll(pollEpoch), false);
  assert.equal(gate.beginPoll(), null);
  gate.endSave();
  assert.equal(gate.beginPoll(), 1);
});

test("secret actions must correspond exactly to controls the user dirtied", () => {
  const state = new FormSyncState({ revision: "r1", settings: {} });
  assert.throws(
    () => state.buildRequest({}, { openai_api_key: { action: "delete" } }),
    /explicitly dirty/,
  );
});

test("interaction stays fail-closed until a valid initial snapshot is accepted", () => {
  const gate = new InteractionGate();
  let mutations = 0;
  assert.equal(gate.run(() => { mutations += 1; }), false);
  assert.equal(mutations, 0);
  gate.markReady();
  assert.equal(gate.run(() => { mutations += 1; }), true);
  assert.equal(mutations, 1);
});

test("save-busy interaction gate blocks post-snapshot edits and reopens afterwards", () => {
  const gate = new InteractionGate();
  let mutations = 0;
  gate.markReady();

  assert.equal(gate.beginSave(), true);
  assert.equal(gate.run(() => { mutations += 1; }), false);
  assert.equal(mutations, 0);
  assert.equal(gate.beginSave(), false);

  gate.endSave();
  assert.equal(gate.run(() => { mutations += 1; }), true);
  assert.equal(mutations, 1);
});

test("save wrapper unlocks controls after a resolved operation", async () => {
  const gate = new InteractionGate();
  const enabled = [];
  gate.markReady();
  const result = await withInteractionSave(
    gate,
    (value) => enabled.push(value),
    async () => "resolved",
  );
  assert.deepEqual(result, { started: true, value: "resolved" });
  assert.deepEqual(enabled, [false, true]);
  assert.equal(gate.run(() => {}), true);
});

test("save wrapper unlocks controls when the operation throws", async () => {
  const gate = new InteractionGate();
  const enabled = [];
  gate.markReady();
  await assert.rejects(
    withInteractionSave(
      gate,
      (value) => enabled.push(value),
      async () => { throw new Error("simulated network failure"); },
    ),
    /simulated network failure/,
  );
  assert.deepEqual(enabled, [false, true]);
  assert.equal(gate.run(() => {}), true);
});

test("a conflict snapshot is logically merged exactly once", () => {
  const fake = {
    conflicts: new Set(),
    calls: 0,
    mergeSnapshot(snapshot) {
      this.calls += 1;
      return structuredClone(snapshot.settings);
    },
  };
  const visible = mergeConflictSnapshot(
    fake,
    { revision: "r2", settings: { site_title: "Extern" } },
    ["site_title"],
  );
  assert.equal(fake.calls, 1);
  assert.deepEqual(visible, { site_title: "Extern" });
  assert.deepEqual([...fake.conflicts], ["site_title"]);
});

test("both live polls use bounded request timeouts", () => {
  const source = readFileSync(
    new URL("../wirtelprimpf_platform/static/admin.mjs", import.meta.url),
    "utf8",
  );
  assert.equal(source.match(/signal: AbortSignal\.timeout\(4000\)/g)?.length, 2);
});
