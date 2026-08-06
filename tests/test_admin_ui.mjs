import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import * as AdminUI from "../wirtelprimpf_platform/static/admin.mjs";

const {
  FormSyncState,
  InteractionGate,
  RequestEpochGate,
  buildSecretActions,
  classifySettingsSaveResponse,
  extractCsrfToken,
  controlValue,
  isConflictPayload,
  isSettingsSnapshot,
  mergeConflictSnapshot,
  modelOptions,
  numericBounds,
  optionValuesMatch,
  pollSettingsOnce,
  postSettingsWithCsrf,
  prepareBootstrap,
  reconcileControlValue,
  runBootstrapFailClosed,
  statusLabels,
  withInteractionSave,
} = AdminUI;

const ADMIN_HTML = readFileSync(
  new URL("../wirtelprimpf_platform/static/admin.html", import.meta.url),
  "utf8",
);
const ADMIN_CSS = readFileSync(
  new URL("../wirtelprimpf_platform/static/admin.css", import.meta.url),
  "utf8",
);

function completeAdminSnapshot() {
  return {
    ok: true,
    schema_version: "2.0.0",
    revision: "c".repeat(64),
    settings: {
      operandi: "story",
      image_model: "gpt-image-2",
      story_model: "gpt-5.5",
      image_size: "1536x1024",
      output_resolution: "2k",
      generation_interval_minutes: 120,
      story_finish_parts_min: 3,
      story_finish_parts_max: 5,
      publish_immediately: true,
      site_title: "Wirtelprimpf",
      site_intro: "Aktuelle Geschichte",
    },
    choices: {
      operandi: ["classic", "story", "both"],
      image_model: ["gpt-image-2"],
      story_model: ["gpt-5.5"],
      image_size: ["1536x1024"],
      output_resolution: ["source", "2k", "4k"],
    },
    secrets: {
      openai_api_key_present: false,
      cloudflare_api_token_present: false,
      github_auth_present: true,
    },
    invariants: {
      numeric_bounds: {
        generation_interval_minutes: { minimum: 30, maximum: 10_080 },
        story_finish_parts_min: { minimum: 1, maximum: 12 },
        story_finish_parts_max: { minimum: 1, maximum: 12 },
      },
    },
    warnings: [],
  };
}

function bootstrapDocument({ csrf = "csrf-for-tests" } = {}) {
  const controls = [{ disabled: false }, { disabled: false }];
  const form = {
    querySelectorAll() {
      return controls;
    },
  };
  const saveStatus = { textContent: "" };
  const pollStatus = { textContent: "" };
  const meta = csrf === null ? null : { content: csrf };
  const document = {
    querySelector(selector) {
      return new Map([
        ["#settings", form],
        ["#save-status", saveStatus],
        ["#poll-status", pollStatus],
        ['meta[name="csrf-token"]', meta],
      ]).get(selector) ?? null;
    },
  };
  return { controls, document, form, pollStatus, saveStatus };
}

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

test("admin snapshots require valid bounds for every rendered numeric control", () => {
  const invalidSnapshots = [];

  const missingBounds = completeAdminSnapshot();
  missingBounds.invariants = {};
  invalidSnapshots.push(missingBounds);

  const missingField = completeAdminSnapshot();
  delete missingField.invariants.numeric_bounds.story_finish_parts_max;
  invalidSnapshots.push(missingField);

  const nonIntegerBound = completeAdminSnapshot();
  nonIntegerBound.invariants.numeric_bounds.story_finish_parts_min.minimum = 0.5;
  invalidSnapshots.push(nonIntegerBound);

  const reversedBounds = completeAdminSnapshot();
  reversedBounds.invariants.numeric_bounds.generation_interval_minutes = {
    minimum: 10_080,
    maximum: 30,
  };
  invalidSnapshots.push(reversedBounds);

  const excludedCurrentValue = completeAdminSnapshot();
  excludedCurrentValue.invariants.numeric_bounds.story_finish_parts_max = {
    minimum: 6,
    maximum: 12,
  };
  invalidSnapshots.push(excludedCurrentValue);

  const reversedStoryRange = completeAdminSnapshot();
  reversedStoryRange.settings.story_finish_parts_min = 8;
  reversedStoryRange.settings.story_finish_parts_max = 4;
  invalidSnapshots.push(reversedStoryRange);

  for (const snapshot of invalidSnapshots) {
    const gate = new InteractionGate();
    assert.throws(
      () => AdminUI.acceptInitialSettingsSnapshot(snapshot, gate),
      /complete settings snapshot/,
    );
    assert.equal(gate.ready, false);
  }
});

test("settings snapshots explicitly require ok true", () => {
  const absent = completeAdminSnapshot();
  delete absent.ok;
  assert.equal(isSettingsSnapshot(absent), false);

  const unsuccessful = completeAdminSnapshot();
  unsuccessful.ok = false;
  assert.equal(isSettingsSnapshot(unsuccessful), false);
  assert.equal(isSettingsSnapshot(completeAdminSnapshot()), true);
});

test("stale CSRF tokens refresh once before retrying the same save", async () => {
  const requests = [];
  const fetcher = async (endpoint, options = {}) => {
    requests.push({ endpoint, options });
    if (endpoint === "/") {
      return {
        ok: true,
        text: async () => '<meta name="csrf-token" content="fresh-token">',
      };
    }
    if (requests.filter((request) => request.endpoint === "/api/settings").length === 1) {
      return {
        ok: false,
        status: 403,
        json: async () => ({ ok: false, error: "invalid CSRF token" }),
      };
    }
    return {
      ok: true,
      status: 200,
      json: async () => completeAdminSnapshot(),
    };
  };
  const result = await postSettingsWithCsrf({ changes: { image_model: "gpt-image-2" } }, "stale-token", fetcher);

  assert.equal(result.outcome.kind, "success");
  assert.equal(result.csrfToken, "fresh-token");
  assert.equal(requests.length, 3);
  assert.equal(requests[0].options.headers["X-Wirtelprimpf-CSRF"], "stale-token");
  assert.deepEqual(requests[1], {
    endpoint: "/",
    options: { cache: "no-store" },
  });
  assert.equal(requests[2].options.headers["X-Wirtelprimpf-CSRF"], "fresh-token");
});

test("CSRF token extraction rejects missing or malformed admin pages", () => {
  assert.equal(
    extractCsrfToken('<meta name="csrf-token" content="token_123-abc">'),
    "token_123-abc",
  );
  assert.throws(() => extractCsrfToken("<html></html>"), /CSRF token is missing/);
  assert.throws(() => extractCsrfToken(null), /CSRF page is not text/);
});

test("settings snapshots require a 64-character lowercase hexadecimal revision", () => {
  for (const revision of ["r1", "C".repeat(64), "c".repeat(63), `${"c".repeat(64)}d`]) {
    const snapshot = completeAdminSnapshot();
    snapshot.revision = revision;
    assert.equal(isSettingsSnapshot(snapshot), false);
  }
  assert.equal(isSettingsSnapshot(completeAdminSnapshot()), true);
});

test("secret actions reject simultaneous deletion and replacement", () => {
  assert.deepEqual(
    buildSecretActions([
      { name: "openai_api_key", value: "", deleteSelected: true },
      { name: "cloudflare_api_token", value: "replacement", deleteSelected: false },
    ]),
    {
      openai_api_key: { action: "delete" },
      cloudflare_api_token: { action: "replace", value: "replacement" },
    },
  );
  assert.throws(
    () => buildSecretActions([
      { name: "openai_api_key", value: "replacement", deleteSelected: true },
    ]),
    {
      name: "TypeError",
      message: "Löschen und Ersetzen sind gleichzeitig gewählt.",
    },
  );
});

test("missing status timer and story sections render as wholly unknown", () => {
  for (const status of [{}, { timer: null, story: null }]) {
    const labels = statusLabels(status);
    assert.equal(labels.timer, "Unbekannt");
    assert.equal(labels.story, "Unbekannt");
  }
});

test("conflict payloads require a usable snapshot and a conflicts array", () => {
  const { ok: _ok, ...conflictSnapshot } = completeAdminSnapshot();
  const valid = {
    snapshot: conflictSnapshot,
    conflicts: ["site_title"],
  };
  assert.equal(isConflictPayload(valid), true);
  const explicitlyUnsuccessful = structuredClone(valid);
  explicitlyUnsuccessful.snapshot.ok = false;
  assert.equal(isConflictPayload(explicitlyUnsuccessful), true);
  assert.equal(isConflictPayload({ snapshot: null, conflicts: [] }), false);
  assert.equal(isConflictPayload({ snapshot: valid.snapshot, conflicts: null }), false);
  assert.equal(isConflictPayload({ snapshot: {}, conflicts: [] }), false);
  const incomplete = structuredClone(valid);
  delete incomplete.snapshot.warnings;
  assert.equal(isConflictPayload(incomplete), false);
});

test("save response classification handles empty malformed and non-string rejections", async () => {
  const malformed = await classifySettingsSaveResponse({
    ok: false,
    status: 400,
    async json() { throw new SyntaxError("empty response"); },
  });
  assert.deepEqual(malformed, { kind: "rejected", message: "Änderung abgelehnt." });

  for (const error of [17, null, {}, "   "]) {
    const classified = await classifySettingsSaveResponse({
      ok: false,
      status: 422,
      async json() { return { error }; },
    });
    assert.deepEqual(classified, { kind: "rejected", message: "Änderung abgelehnt." });
  }

  const readable = await classifySettingsSaveResponse({
    ok: false,
    status: 422,
    async json() { return { error: "Wert außerhalb des zulässigen Bereichs" }; },
  });
  assert.deepEqual(readable, {
    kind: "rejected",
    message: "Wert außerhalb des zulässigen Bereichs",
  });
});

test("save response classification preserves conflict and success contracts", async () => {
  const { ok: _ok, ...conflictSnapshot } = completeAdminSnapshot();
  const conflict = { snapshot: conflictSnapshot, conflicts: ["site_title"] };
  assert.deepEqual(
    await classifySettingsSaveResponse({
      ok: false,
      status: 409,
      async json() { return conflict; },
    }),
    { kind: "conflict", data: conflict },
  );

  const success = completeAdminSnapshot();
  assert.deepEqual(
    await classifySettingsSaveResponse({
      ok: true,
      status: 200,
      async json() { return success; },
    }),
    { kind: "success", snapshot: success },
  );
  await assert.rejects(
    classifySettingsSaveResponse({
      ok: true,
      status: 200,
      async json() { return "not a snapshot"; },
    }),
    /complete settings snapshot/,
  );
});

test("settings poll reports through its own live region and clears it on success", async () => {
  const requestGate = new RequestEpochGate();
  const pollStatus = { textContent: "" };
  const saveStatus = { textContent: "Konflikt: lokaler Entwurf bleibt erhalten." };
  let applied = 0;

  assert.equal(
    await pollSettingsOnce({
      requestGate,
      pollStatus,
      fetchSettings: async () => ({ ok: false }),
      applySnapshot: () => { applied += 1; },
    }),
    false,
  );
  assert.equal(pollStatus.textContent, "Einstellungen konnten nicht aktualisiert werden.");
  assert.equal(saveStatus.textContent, "Konflikt: lokaler Entwurf bleibt erhalten.");

  assert.equal(
    await pollSettingsOnce({
      requestGate,
      pollStatus,
      fetchSettings: async () => ({
        ok: true,
        async json() { return completeAdminSnapshot(); },
      }),
      applySnapshot: () => { applied += 1; },
    }),
    true,
  );
  assert.equal(applied, 1);
  assert.equal(pollStatus.textContent, "");
  assert.equal(saveStatus.textContent, "Konflikt: lokaler Entwurf bleibt erhalten.");
});

test("missing CSRF keeps every setting control disabled and reports visibly", () => {
  const fixture = bootstrapDocument({ csrf: null });
  assert.equal(prepareBootstrap(fixture.document), null);
  assert.ok(fixture.controls.every((control) => control.disabled));
  assert.match(fixture.saveStatus.textContent, /Sicherheitskonfiguration fehlt/);
});

test("unexpected bootstrap rejection is visible and restores fail-closed controls", async () => {
  const fixture = bootstrapDocument();
  const started = await runBootstrapFailClosed(fixture.document, async () => {
    for (const control of fixture.controls) control.disabled = false;
    throw new Error("private failure detail must stay hidden");
  });
  assert.equal(started, false);
  assert.ok(fixture.controls.every((control) => control.disabled));
  assert.equal(
    fixture.saveStatus.textContent,
    "Steuerkonsole konnte nicht sicher initialisiert werden; Einstellungen bleiben gesperrt.",
  );
  assert.doesNotMatch(fixture.saveStatus.textContent, /private failure detail/);
});

test("admin assets expose a dedicated poll live region and a visible invalid state", () => {
  assert.match(
    ADMIN_HTML,
    /<p[^>]*id="poll-status"[^>]*role="status"[^>]*aria-live="polite"[^>]*>/,
  );
  const invalidRule = ADMIN_CSS.match(/\.field\.is-invalid\{([^}]*)\}/);
  assert.ok(invalidRule, "missing .field.is-invalid CSS rule");
  assert.match(invalidRule[1], /border-color:var\(--rose\)/);
  assert.match(invalidRule[1], /box-shadow:/);
});

test("initial interaction unlocks only after one complete success snapshot", () => {
  const accept = AdminUI.acceptInitialSettingsSnapshot;
  const incompleteSnapshots = [];
  for (const name of Object.keys(completeAdminSnapshot().settings)) {
    const missingFormSetting = completeAdminSnapshot();
    delete missingFormSetting.settings[name];
    incompleteSnapshots.push(missingFormSetting);
    const wrongFormType = completeAdminSnapshot();
    const value = wrongFormType.settings[name];
    wrongFormType.settings[name] = typeof value === "string" ? 1 : value === true ? 1 : true;
    incompleteSnapshots.push(wrongFormType);
  }
  for (const name of Object.keys(completeAdminSnapshot().choices)) {
    const missingChoiceCatalog = completeAdminSnapshot();
    delete missingChoiceCatalog.choices[name];
    incompleteSnapshots.push(missingChoiceCatalog);
    const emptyChoiceCatalog = completeAdminSnapshot();
    emptyChoiceCatalog.choices[name] = [];
    incompleteSnapshots.push(emptyChoiceCatalog);
  }

  for (const incomplete of incompleteSnapshots) {
    const gate = new InteractionGate();
    assert.throws(
      () => accept(incomplete, gate),
      /complete settings snapshot/,
    );
    assert.equal(gate.ready, false);
  }

  const gate = new InteractionGate();
  const complete = completeAdminSnapshot();
  complete.settings.site_title = "Vollständig";
  const state = accept(complete, gate);
  assert.equal(gate.ready, true);
  assert.equal(state.visible.site_title, "Vollständig");
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

test("settings and status live poll requests are no-store and bounded", async () => {
  assert.equal(typeof AdminUI.fetchLivePoll, "function");

  const originalFetch = globalThis.fetch;
  const originalTimeout = AbortSignal.timeout;
  const requests = [];
  const timeoutMilliseconds = [];
  const signals = [];
  globalThis.fetch = async (endpoint, options) => {
    requests.push({ endpoint, options });
    return { ok: true };
  };
  AbortSignal.timeout = (milliseconds) => {
    timeoutMilliseconds.push(milliseconds);
    const signal = AbortSignal.abort();
    signals.push(signal);
    return signal;
  };

  try {
    await AdminUI.fetchLivePoll("settings");
    await AdminUI.fetchLivePoll("status");
  } finally {
    globalThis.fetch = originalFetch;
    AbortSignal.timeout = originalTimeout;
  }

  assert.equal(globalThis.fetch, originalFetch);
  assert.equal(AbortSignal.timeout, originalTimeout);
  assert.deepEqual(timeoutMilliseconds, [4000, 4000]);
  assert.equal(requests.length, 2);
  assert.equal(requests[0].endpoint, "/api/settings");
  assert.equal(requests[0].options.cache, "no-store");
  assert.equal(requests[0].options.signal, signals[0]);
  assert.equal(requests[1].endpoint, "/api/status");
  assert.equal(requests[1].options.cache, "no-store");
  assert.equal(requests[1].options.signal, signals[1]);
});
