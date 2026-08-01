import assert from "node:assert/strict";
import test from "node:test";

import {
  FormSyncState,
  InteractionGate,
  RequestEpochGate,
  mergeConflictSnapshot,
  modelOptions,
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

test("save wrapper unlocks controls after success, conflict, and rejected response branches", async () => {
  for (const branch of ["success", "409", "error-response"]) {
    const gate = new InteractionGate();
    const enabled = [];
    gate.markReady();
    const result = await withInteractionSave(
      gate,
      (value) => enabled.push(value),
      async () => branch,
    );
    assert.deepEqual(result, { started: true, value: branch });
    assert.deepEqual(enabled, [false, true]);
    assert.equal(gate.run(() => {}), true);
  }
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
