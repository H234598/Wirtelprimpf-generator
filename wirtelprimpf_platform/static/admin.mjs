export class FormSyncState {
  constructor(snapshot) {
    this.revision = snapshot.revision;
    this.server = structuredClone(snapshot.settings);
    this.visible = structuredClone(snapshot.settings);
    this.baseRevision = null;
    this.baseValues = new Map();
    this.dirty = new Set();
    this.secretDirty = new Set();
    this.conflicts = new Set();
  }

  change(name, value) {
    if (Object.is(value, this.server[name])) {
      this.visible[name] = structuredClone(this.server[name]);
      this.dirty.delete(name);
      this.conflicts.delete(name);
      this.baseValues.delete(name);
      if (this.dirty.size === 0 && this.secretDirty.size === 0) this.baseRevision = null;
      return;
    }
    if (!this.dirty.has(name)) {
      this.baseRevision ??= this.revision;
      this.baseValues.set(name, this.server[name]);
      this.dirty.add(name);
    }
    this.visible[name] = value;
  }

  markSecretDirty(name) {
    this.baseRevision ??= this.revision;
    this.secretDirty.add(name);
  }

  mergeSnapshot(snapshot) {
    for (const [name, value] of Object.entries(snapshot.settings)) {
      if (this.dirty.has(name)) {
        if (Object.is(value, this.baseValues.get(name))) this.conflicts.delete(name);
        else this.conflicts.add(name);
        continue;
      }
      this.visible[name] = value;
    }
    this.server = structuredClone(snapshot.settings);
    this.revision = snapshot.revision;
    return structuredClone(this.visible);
  }

  discard(name) {
    if (!this.dirty.has(name)) return this.visible[name];
    this.visible[name] = this.server[name];
    this.dirty.delete(name);
    this.conflicts.delete(name);
    this.baseValues.delete(name);
    if (this.dirty.size === 0 && this.secretDirty.size === 0) this.baseRevision = null;
    return this.visible[name];
  }

  discardSecret(name) {
    this.secretDirty.delete(name);
    if (this.dirty.size === 0 && this.secretDirty.size === 0) this.baseRevision = null;
  }

  buildRequest(values, secretActions) {
    const invalidValues = [...this.dirty].filter((name) => (
      values[name] === null
      || values[name] === undefined
      || (typeof values[name] === "number" && !Number.isFinite(values[name]))
    ));
    if (invalidValues.length > 0) {
      throw new TypeError(`invalid local value: ${invalidValues.join(", ")}`);
    }
    const changes = Object.fromEntries([...this.dirty].map((name) => [name, values[name]]));
    const baseValues = Object.fromEntries(
      [...this.dirty].map((name) => [name, this.baseValues.get(name)]),
    );
    const actionNames = Object.keys(secretActions).sort();
    const dirtySecretNames = [...this.secretDirty].sort();
    if (
      actionNames.length !== dirtySecretNames.length
      || actionNames.some((name, index) => name !== dirtySecretNames[index])
    ) {
      throw new TypeError("secret actions must match explicitly dirty secret controls");
    }
    return {
      base_revision: this.baseRevision ?? this.revision,
      changes,
      base_values: baseValues,
      secret_actions: structuredClone(secretActions),
    };
  }

  acceptSavedSnapshot(snapshot) {
    this.revision = snapshot.revision;
    this.server = structuredClone(snapshot.settings);
    this.visible = structuredClone(snapshot.settings);
    this.baseRevision = null;
    this.baseValues.clear();
    this.dirty.clear();
    this.secretDirty.clear();
    this.conflicts.clear();
  }
}

export class RequestEpochGate {
  constructor() {
    this.epoch = 0;
    this.saveInFlight = false;
  }

  beginPoll() {
    return this.saveInFlight ? null : this.epoch;
  }

  acceptPoll(epoch) {
    return !this.saveInFlight && epoch === this.epoch;
  }

  beginSave() {
    this.saveInFlight = true;
    this.epoch += 1;
    return this.epoch;
  }

  endSave() {
    this.saveInFlight = false;
  }
}

export class InteractionGate {
  constructor() {
    this.ready = false;
    this.saveBusy = false;
  }

  markReady() {
    this.ready = true;
  }

  beginSave() {
    if (!this.ready || this.saveBusy) return false;
    this.saveBusy = true;
    return true;
  }

  endSave() {
    this.saveBusy = false;
  }

  run(action) {
    if (!this.ready || this.saveBusy) return false;
    action();
    return true;
  }
}

export async function withInteractionSave(gate, setInterfaceEnabled, operation) {
  if (!gate.beginSave()) return { started: false };
  try {
    setInterfaceEnabled(false);
    return { started: true, value: await operation() };
  } finally {
    gate.endSave();
    setInterfaceEnabled(true);
  }
}

export function mergeConflictSnapshot(state, snapshot, conflictNames) {
  const visible = state.mergeSnapshot(snapshot);
  for (const name of conflictNames) state.conflicts.add(name);
  return visible;
}

export function modelOptions(catalog, current) {
  const options = catalog.map((value) => ({ value, label: value, legacy: false }));
  if (typeof current === "string" && current && !catalog.includes(current)) {
    options.unshift({
      value: current,
      label: `${current} · konfiguriert · nicht mehr im empfohlenen Katalog`,
      legacy: true,
    });
  }
  return options;
}

export function controlValue(control) {
  if (control.type === "checkbox") return control.checked;
  if (control.type === "number") {
    if (String(control.value).trim() === "") return null;
    const parsed = Number(control.value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return control.value;
}

export function setControlValue(control, value) {
  if (!control) return;
  if (control.type === "checkbox") control.checked = Boolean(value);
  else control.value = value ?? "";
}

export function reconcileControlValue(control, value, activeElement) {
  if (!control || control === activeElement || Object.is(controlValue(control), value)) return false;
  setControlValue(control, value);
  return true;
}

export function optionValuesMatch(select, options) {
  const existing = [...select.options].map((option) => option.value);
  return existing.length === options.length
    && options.every((item, index) => item.value === existing[index]);
}

export function numericBounds(invariants, name) {
  const bounds = invariants?.numeric_bounds?.[name];
  if (
    !bounds
    || !Number.isInteger(bounds.minimum)
    || !Number.isInteger(bounds.maximum)
    || bounds.minimum > bounds.maximum
  ) return null;
  return { minimum: bounds.minimum, maximum: bounds.maximum };
}

function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

const FORM_SETTING_KINDS = Object.freeze({
  operandi: "string",
  image_model: "string",
  story_model: "string",
  image_size: "string",
  output_resolution: "string",
  generation_interval_minutes: "integer",
  story_finish_parts_min: "integer",
  story_finish_parts_max: "integer",
  publish_immediately: "boolean",
  site_title: "string",
  site_intro: "string",
});
const FORM_CHOICE_KEYS = Object.freeze([
  "operandi",
  "image_model",
  "story_model",
  "image_size",
  "output_resolution",
]);
const FORM_NUMERIC_KEYS = Object.freeze([
  "generation_interval_minutes",
  "story_finish_parts_min",
  "story_finish_parts_max",
]);

function settingValueMatchesKind(value, kind) {
  if (kind === "boolean") return typeof value === "boolean";
  if (kind === "integer") return Number.isInteger(value);
  return typeof value === "string";
}

function numericBoundsMatchRenderedFields(invariants, settings) {
  return FORM_NUMERIC_KEYS.every((name) => {
    const bounds = numericBounds(invariants, name);
    const value = settings[name];
    return bounds !== null
      && value >= bounds.minimum
      && value <= bounds.maximum;
  });
}

function isPublicSettingsSnapshot(snapshot, requireSuccess) {
  return isRecord(snapshot)
    && (!requireSuccess || snapshot.ok === true)
    && typeof snapshot.schema_version === "string"
    && snapshot.schema_version.length > 0
    && typeof snapshot.revision === "string"
    && /^[0-9a-f]{64}$/.test(snapshot.revision)
    && isRecord(snapshot.settings)
    && Object.entries(FORM_SETTING_KINDS).every(
      ([name, kind]) => Object.hasOwn(snapshot.settings, name)
        && settingValueMatchesKind(snapshot.settings[name], kind),
    )
    && isRecord(snapshot.choices)
    && FORM_CHOICE_KEYS.every((name) => Object.hasOwn(snapshot.choices, name))
    && Object.values(snapshot.choices).every(
      (values) => Array.isArray(values)
        && values.length > 0
        && values.every((value) => typeof value === "string"),
    )
    && isRecord(snapshot.secrets)
    && typeof snapshot.secrets.openai_api_key_present === "boolean"
    && typeof snapshot.secrets.cloudflare_api_token_present === "boolean"
    && Object.values(snapshot.secrets).every((value) => typeof value === "boolean")
    && isRecord(snapshot.invariants)
    && numericBoundsMatchRenderedFields(snapshot.invariants, snapshot.settings)
    && snapshot.settings.story_finish_parts_min <= snapshot.settings.story_finish_parts_max
    && Array.isArray(snapshot.warnings)
    && snapshot.warnings.every((warning) => typeof warning === "string");
}

export function isSettingsSnapshot(snapshot) {
  return isPublicSettingsSnapshot(snapshot, true);
}

export function acceptInitialSettingsSnapshot(snapshot, interactionGate) {
  if (!isSettingsSnapshot(snapshot)) {
    throw new TypeError("complete settings snapshot required");
  }
  const state = new FormSyncState(snapshot);
  interactionGate.markReady();
  return state;
}

export function isConflictPayload(data) {
  return isRecord(data)
    && isPublicSettingsSnapshot(data.snapshot, false)
    && Array.isArray(data.conflicts)
    && data.conflicts.every((name) => typeof name === "string");
}

export async function classifySettingsSaveResponse(response) {
  let data;
  try {
    data = await response.json();
  } catch {
    data = undefined;
  }
  if (response.status === 409) return { kind: "conflict", data };
  if (!response.ok) {
    const error = isRecord(data) && typeof data.error === "string" ? data.error.trim() : "";
    return { kind: "rejected", message: error || "Änderung abgelehnt." };
  }
  if (!isSettingsSnapshot(data)) {
    throw new TypeError("complete settings snapshot required");
  }
  return { kind: "success", snapshot: data };
}

function text(value, fallback = "Unbekannt") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

export function statusLabels(status) {
  const payload = isRecord(status) ? status : {};
  const timer = isRecord(payload.timer) ? payload.timer : null;
  const story = isRecord(payload.story) ? payload.story : null;
  return {
    health: text(payload.health),
    lastRun: text(payload.generator?.last_run),
    nextRun: text(timer?.next_run),
    timer: timer && timer.enabled !== null && timer.enabled !== undefined
      ? `${timer.enabled ? "aktiviert" : "deaktiviert"} · ${text(timer.interval_minutes)} min`
      : "Unbekannt",
    story: story && story.current_volume !== null && story.current_volume !== undefined
      ? `Buch ${text(story.book)} · Story ${text(story.story_in_book)}/10`
      : "Unbekannt",
    repository: text(payload.archive?.repository),
    result: text(payload.generator?.result),
  };
}

const LIVE_POLL_ENDPOINTS = Object.freeze({
  settings: "/api/settings",
  status: "/api/status",
});

export function fetchLivePoll(resource) {
  return fetch(LIVE_POLL_ENDPOINTS[resource], {
    cache: "no-store",
    signal: AbortSignal.timeout(4000),
  });
}

export async function pollSettingsOnce({
  requestGate,
  pollStatus,
  fetchSettings = () => fetchLivePoll("settings"),
  applySnapshot,
}) {
  const requestEpoch = requestGate.beginPoll();
  if (requestEpoch === null) return false;
  try {
    const response = await fetchSettings();
    if (!response.ok) throw new Error("settings unavailable");
    const snapshot = await response.json();
    if (!isSettingsSnapshot(snapshot)) throw new TypeError("complete settings snapshot required");
    if (requestGate.acceptPoll(requestEpoch)) applySnapshot(snapshot);
    pollStatus.textContent = "";
    return true;
  } catch {
    pollStatus.textContent = "Einstellungen konnten nicht aktualisiert werden.";
    return false;
  }
}

function setFormControlsEnabled(form, enabled) {
  for (const control of form.querySelectorAll("input, select, textarea, button")) {
    control.disabled = !enabled;
  }
}

export function prepareBootstrap(documentRef) {
  const form = documentRef.querySelector("#settings");
  const saveStatus = documentRef.querySelector("#save-status");
  if (!form || !saveStatus) throw new TypeError("admin bootstrap surface is incomplete");
  setFormControlsEnabled(form, false);

  const csrfMeta = documentRef.querySelector('meta[name="csrf-token"]');
  if (!csrfMeta || typeof csrfMeta.content !== "string" || csrfMeta.content.trim() === "") {
    saveStatus.textContent = "Sicherheitskonfiguration fehlt; Einstellungen bleiben gesperrt.";
    return null;
  }
  const pollStatus = documentRef.querySelector("#poll-status");
  if (!pollStatus) throw new TypeError("admin polling status surface is incomplete");
  return {
    csrfToken: csrfMeta.content,
    form,
    pollStatus,
    saveStatus,
  };
}

function reportBootstrapFailure(documentRef) {
  const form = documentRef.querySelector("#settings");
  if (form) setFormControlsEnabled(form, false);
  const saveStatus = documentRef.querySelector("#save-status");
  if (saveStatus) {
    saveStatus.textContent = "Steuerkonsole konnte nicht sicher initialisiert werden; Einstellungen bleiben gesperrt.";
  }
}

export async function runBootstrapFailClosed(documentRef, operation = bootstrap) {
  try {
    await operation(documentRef);
    return true;
  } catch {
    reportBootstrapFailure(documentRef);
    return false;
  }
}

async function bootstrap(documentRef) {
  const prepared = prepareBootstrap(documentRef);
  if (prepared === null) return;
  const {
    csrfToken,
    form,
    pollStatus: settingsPollStatus,
    saveStatus,
  } = prepared;
  const requestGate = new RequestEpochGate();
  const interactionGate = new InteractionGate();
  let syncState = null;
  let settingsInFlight = false;
  let statusInFlight = false;

  const controls = () => [...form.elements].filter((element) => element.name);
  const settingControl = (name) => form.elements.namedItem(name);

  function setInterfaceEnabled(enabled) {
    setFormControlsEnabled(form, enabled);
  }

  function populateSelect(name, catalog, current, models = false) {
    const select = settingControl(name);
    const options = models
      ? modelOptions(catalog, current)
      : catalog.map((value) => ({ value: String(value), label: String(value), legacy: false }));
    if (optionValuesMatch(select, options)) return;
    select.replaceChildren(
      ...options.map((item) => {
        const option = documentRef.createElement("option");
        option.value = item.value;
        option.textContent = item.label;
        option.dataset.legacy = item.legacy ? "true" : "false";
        return option;
      }),
    );
  }

  function discardField(name) {
    setControlValue(settingControl(name), syncState.discard(name));
    renderFieldStates();
  }

  function renderFieldStates() {
    for (const row of documentRef.querySelectorAll("[data-field]")) {
      const name = row.dataset.field;
      const state = documentRef.querySelector(`#${name}-state`);
      const invalid = syncState.visible[name] === null;
      row.classList.toggle("is-dirty", syncState.dirty.has(name));
      row.classList.toggle("has-conflict", syncState.conflicts.has(name));
      row.classList.toggle("is-invalid", invalid);
      let message = state.querySelector("[data-role='field-message']");
      let lineBreak = state.querySelector("br");
      let button = state.querySelector("button");
      if (!message || !lineBreak || !button) {
        message = documentRef.createElement("span");
        message.dataset.role = "field-message";
        lineBreak = documentRef.createElement("br");
        button = documentRef.createElement("button");
        button.type = "button";
        button.className = "secondary";
        button.textContent = "Externen Wert übernehmen";
        button.addEventListener("click", () => discardField(name));
        state.replaceChildren(message, lineBreak, button);
      }
      if (invalid) {
        message.textContent = "Ungültige oder leere Zahl";
      } else if (syncState.conflicts.has(name)) {
        message.textContent = "Extern geändert – Speichern prüft den Konflikt";
      } else if (syncState.dirty.has(name)) {
        message.textContent = "Ungespeichert";
      } else {
        message.textContent = "";
      }
      lineBreak.hidden = !syncState.dirty.has(name);
      button.hidden = !syncState.dirty.has(name);
    }
    documentRef.querySelector("#status-sync").textContent = syncState.dirty.size || syncState.secretDirty.size
      ? `${syncState.dirty.size + syncState.secretDirty.size} lokale Entwürfe`
      : "Synchron";
  }

  function renderSecretPresence(snapshot) {
    documentRef.querySelector("#openai-presence").textContent = snapshot.secrets.openai_api_key_present
      ? "Vorhandener Schlüssel: ja"
      : "Vorhandener Schlüssel: nein";
    documentRef.querySelector("#cloudflare-presence").textContent = snapshot.secrets.cloudflare_api_token_present
      ? "Vorhandener Token: ja"
      : "Vorhandener Token: nein";
  }

  function renderSettingsSnapshot(snapshot, visible) {
    for (const name of ["operandi", "image_size", "output_resolution"]) {
      populateSelect(name, snapshot.choices[name] ?? [], visible[name]);
    }
    populateSelect("image_model", snapshot.choices.image_model ?? [], visible.image_model, true);
    populateSelect("story_model", snapshot.choices.story_model ?? [], visible.story_model, true);
    for (const name of [
      "generation_interval_minutes",
      "story_finish_parts_min",
      "story_finish_parts_max",
    ]) {
      const bounds = numericBounds(snapshot.invariants, name);
      const control = settingControl(name);
      if (bounds && control) {
        control.min = String(bounds.minimum);
        control.max = String(bounds.maximum);
      }
    }
    for (const [name, value] of Object.entries(visible)) {
      reconcileControlValue(settingControl(name), value, documentRef.activeElement);
    }
    renderSecretPresence(snapshot);
    renderFieldStates();
  }

  function applySettingsSnapshot(snapshot) {
    if (!isSettingsSnapshot(snapshot)) {
      throw new TypeError("complete settings snapshot required");
    }
    let visible;
    let initialized = false;
    if (syncState === null) {
      syncState = acceptInitialSettingsSnapshot(snapshot, interactionGate);
      visible = structuredClone(syncState.visible);
      initialized = true;
    } else {
      visible = syncState.mergeSnapshot(snapshot);
    }
    renderSettingsSnapshot(snapshot, visible);
    if (initialized) setInterfaceEnabled(true);
  }

  function renderStatus(status) {
    const labels = statusLabels(status);
    documentRef.querySelector("#status-health").textContent = labels.health;
    documentRef.querySelector("#status-last-run").textContent = labels.lastRun;
    documentRef.querySelector("#status-next-run").textContent = labels.nextRun;
    documentRef.querySelector("#status-timer").textContent = labels.timer;
    documentRef.querySelector("#status-story").textContent = labels.story;
    documentRef.querySelector("#status-repository").textContent = labels.repository;
    documentRef.querySelector("#status-result").textContent = labels.result;
  }

  async function pollSettings() {
    if (settingsInFlight) return;
    settingsInFlight = true;
    try {
      await pollSettingsOnce({
        requestGate,
        pollStatus: settingsPollStatus,
        applySnapshot: applySettingsSnapshot,
      });
    } finally {
      settingsInFlight = false;
    }
  }

  async function pollStatus() {
    if (statusInFlight) return;
    statusInFlight = true;
    try {
      const response = await fetchLivePoll("status");
      if (!response.ok) throw new Error("status unavailable");
      renderStatus(await response.json());
    } catch {
      documentRef.querySelector("#status-health").textContent = "Nicht verfügbar";
    } finally {
      statusInFlight = false;
    }
  }

  function publicValues() {
    return Object.fromEntries(
      controls()
        .filter((control) => control.name && !control.id.startsWith("delete_"))
        .map((control) => [control.name, controlValue(control)]),
    );
  }

  function secretActions() {
    const actions = {};
    for (const [name, deleteId] of [
      ["openai_api_key", "delete_openai_api_key"],
      ["cloudflare_api_token", "delete_cloudflare_api_token"],
    ]) {
      const input = documentRef.querySelector(`#${name}`);
      const deletion = documentRef.querySelector(`#${deleteId}`);
      if (deletion.checked) actions[name] = { action: "delete" };
      else if (input.value) actions[name] = { action: "replace", value: input.value };
    }
    return actions;
  }

  for (const row of documentRef.querySelectorAll("[data-field]")) {
    const name = row.dataset.field;
    const control = settingControl(name);
    const eventName = control.tagName === "SELECT" || control.type === "checkbox" ? "change" : "input";
    control.addEventListener(eventName, () => {
      interactionGate.run(() => {
        syncState.change(name, controlValue(control));
        renderFieldStates();
      });
    });
  }

  for (const [name, deleteId] of [
    ["openai_api_key", "delete_openai_api_key"],
    ["cloudflare_api_token", "delete_cloudflare_api_token"],
  ]) {
    const input = documentRef.querySelector(`#${name}`);
    const deletion = documentRef.querySelector(`#${deleteId}`);
    const update = () => {
      interactionGate.run(() => {
        if (input.value || deletion.checked) syncState.markSecretDirty(name);
        else syncState.discardSecret(name);
        renderFieldStates();
      });
    };
    input.addEventListener("input", update);
    deletion.addEventListener("change", update);
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!interactionGate.ready) {
      saveStatus.textContent = "Einstellungen sind noch nicht sicher geladen.";
      return;
    }
    const actions = secretActions();
    if (syncState.dirty.size === 0 && Object.keys(actions).length === 0) {
      saveStatus.textContent = "Keine lokalen Änderungen.";
      return;
    }
    let request;
    try {
      request = syncState.buildRequest(publicValues(), actions);
    } catch {
      saveStatus.textContent = "Lokale Eingabe ist unvollständig oder ungültig.";
      return;
    }
    const run = await withInteractionSave(interactionGate, setInterfaceEnabled, async () => {
      requestGate.beginSave();
      saveStatus.textContent = "Prüfe und speichere …";
      try {
        const response = await fetch("/api/settings", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Wirtelprimpf-CSRF": csrfToken,
          },
          body: JSON.stringify(request),
        });
        const outcome = await classifySettingsSaveResponse(response);
        if (outcome.kind === "conflict") {
          if (!isConflictPayload(outcome.data)) {
            saveStatus.textContent = "Konfliktantwort war ungültig; lokale Entwürfe bleiben erhalten.";
            return;
          }
          const visible = mergeConflictSnapshot(
            syncState,
            outcome.data.snapshot,
            outcome.data.conflicts,
          );
          renderSettingsSnapshot(outcome.data.snapshot, visible);
          saveStatus.textContent = "Konflikt: lokale Entwürfe wurden nicht überschrieben.";
          return;
        }
        if (outcome.kind === "rejected") {
          saveStatus.textContent = outcome.message;
          return;
        }
        const data = outcome.snapshot;
        syncState.acceptSavedSnapshot(data);
        documentRef.querySelector("#openai_api_key").value = "";
        documentRef.querySelector("#cloudflare_api_token").value = "";
        documentRef.querySelector("#delete_openai_api_key").checked = false;
        documentRef.querySelector("#delete_cloudflare_api_token").checked = false;
        renderSettingsSnapshot(data, structuredClone(syncState.visible));
        saveStatus.textContent = "Atomar gespeichert und validiert.";
      } catch {
        saveStatus.textContent = "Speichern ist lokal fehlgeschlagen.";
      } finally {
        requestGate.endSave();
      }
    });
    if (!run.started) {
      saveStatus.textContent = "Eine Speicherung läuft bereits.";
    } else {
      void pollSettings();
    }
  });

  documentRef.querySelector("#discard-all").addEventListener("click", () => {
    interactionGate.run(() => {
      if (!window.confirm("Alle lokalen, noch nicht gespeicherten Entwürfe verwerfen?")) return;
      for (const name of [...syncState.dirty]) discardField(name);
      for (const name of [...syncState.secretDirty]) syncState.discardSecret(name);
      documentRef.querySelector("#openai_api_key").value = "";
      documentRef.querySelector("#cloudflare_api_token").value = "";
      documentRef.querySelector("#delete_openai_api_key").checked = false;
      documentRef.querySelector("#delete_cloudflare_api_token").checked = false;
      renderFieldStates();
      saveStatus.textContent = "Lokale Entwürfe verworfen.";
    });
  });

  await pollSettings();
  await pollStatus();
  setInterval(pollSettings, 2000);
  setInterval(pollStatus, 5000);
}

if (typeof document !== "undefined") {
  void runBootstrapFailClosed(document);
}
