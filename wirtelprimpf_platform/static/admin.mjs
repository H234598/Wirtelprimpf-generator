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

function text(value, fallback = "Unbekannt") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

async function bootstrap() {
  const form = document.querySelector("#settings");
  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
  const saveStatus = document.querySelector("#save-status");
  const requestGate = new RequestEpochGate();
  const interactionGate = new InteractionGate();
  let syncState = null;
  let settingsInFlight = false;
  let statusInFlight = false;

  const controls = () => [...form.elements].filter((element) => element.name);
  const settingControl = (name) => form.elements.namedItem(name);

  function setInterfaceEnabled(enabled) {
    for (const control of form.querySelectorAll("input, select, textarea, button")) {
      control.disabled = !enabled;
    }
  }

  setInterfaceEnabled(false);

  function controlValue(control) {
    if (control.type === "checkbox") return control.checked;
    if (control.type === "number") return Number(control.value);
    return control.value;
  }

  function setControlValue(control, value) {
    if (!control) return;
    if (control.type === "checkbox") control.checked = Boolean(value);
    else control.value = value ?? "";
  }

  function populateSelect(name, catalog, current, models = false) {
    const select = settingControl(name);
    const options = models
      ? modelOptions(catalog, current)
      : catalog.map((value) => ({ value: String(value), label: String(value), legacy: false }));
    select.replaceChildren(
      ...options.map((item) => {
        const option = document.createElement("option");
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
    for (const row of document.querySelectorAll("[data-field]")) {
      const name = row.dataset.field;
      const state = document.querySelector(`#${name}-state`);
      row.classList.toggle("is-dirty", syncState.dirty.has(name));
      row.classList.toggle("has-conflict", syncState.conflicts.has(name));
      state.replaceChildren();
      if (syncState.conflicts.has(name)) {
        state.append("Extern geändert – Speichern prüft den Konflikt");
      } else if (syncState.dirty.has(name)) {
        state.append("Ungespeichert");
      }
      if (syncState.dirty.has(name)) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "secondary";
        button.textContent = "Externen Wert übernehmen";
        button.addEventListener("click", () => discardField(name));
        state.append(document.createElement("br"), button);
      }
    }
    document.querySelector("#status-sync").textContent = syncState.dirty.size || syncState.secretDirty.size
      ? `${syncState.dirty.size + syncState.secretDirty.size} lokale Entwürfe`
      : "Synchron";
  }

  function renderSecretPresence(snapshot) {
    document.querySelector("#openai-presence").textContent = snapshot.secrets.openai_api_key_present
      ? "Vorhandener Schlüssel: ja"
      : "Vorhandener Schlüssel: nein";
    document.querySelector("#cloudflare-presence").textContent = snapshot.secrets.cloudflare_api_token_present
      ? "Vorhandener Token: ja"
      : "Vorhandener Token: nein";
  }

  function renderSettingsSnapshot(snapshot, visible) {
    for (const name of ["operandi", "image_size", "output_resolution"]) {
      populateSelect(name, snapshot.choices[name] ?? [], visible[name]);
    }
    populateSelect("image_model", snapshot.choices.image_model ?? [], visible.image_model, true);
    populateSelect("story_model", snapshot.choices.story_model ?? [], visible.story_model, true);
    for (const [name, value] of Object.entries(visible)) {
      if (!syncState.dirty.has(name)) setControlValue(settingControl(name), value);
      else setControlValue(settingControl(name), visible[name]);
    }
    renderSecretPresence(snapshot);
    renderFieldStates();
  }

  function applySettingsSnapshot(snapshot) {
    let visible;
    if (syncState === null) {
      syncState = new FormSyncState(snapshot);
      visible = structuredClone(syncState.visible);
      interactionGate.markReady();
      setInterfaceEnabled(true);
    } else {
      visible = syncState.mergeSnapshot(snapshot);
    }
    renderSettingsSnapshot(snapshot, visible);
  }

  function renderStatus(status) {
    document.querySelector("#status-health").textContent = text(status.health);
    document.querySelector("#status-last-run").textContent = text(status.generator?.last_run);
    document.querySelector("#status-next-run").textContent = text(status.timer?.next_run);
    document.querySelector("#status-timer").textContent = status.timer?.enabled === null
      ? "Unbekannt"
      : `${status.timer.enabled ? "aktiviert" : "deaktiviert"} · ${text(status.timer.interval_minutes)} min`;
    document.querySelector("#status-story").textContent = status.story?.current_volume === null
      ? "Unbekannt"
      : `Buch ${text(status.story?.book)} · Story ${text(status.story?.story_in_book)}/10`;
    document.querySelector("#status-repository").textContent = text(status.archive?.repository);
    document.querySelector("#status-result").textContent = text(status.generator?.result);
  }

  async function pollSettings() {
    if (settingsInFlight) return;
    const requestEpoch = requestGate.beginPoll();
    if (requestEpoch === null) return;
    settingsInFlight = true;
    try {
      const response = await fetch("/api/settings", { cache: "no-store" });
      if (!response.ok) throw new Error("settings unavailable");
      const snapshot = await response.json();
      if (requestGate.acceptPoll(requestEpoch)) applySettingsSnapshot(snapshot);
    } catch {
      saveStatus.textContent = "Einstellungen konnten nicht aktualisiert werden.";
    } finally {
      settingsInFlight = false;
    }
  }

  async function pollStatus() {
    if (statusInFlight) return;
    statusInFlight = true;
    try {
      const response = await fetch("/api/status", { cache: "no-store" });
      if (!response.ok) throw new Error("status unavailable");
      renderStatus(await response.json());
    } catch {
      document.querySelector("#status-health").textContent = "Nicht verfügbar";
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
      const input = document.querySelector(`#${name}`);
      const deletion = document.querySelector(`#${deleteId}`);
      if (deletion.checked) actions[name] = { action: "delete" };
      else if (input.value) actions[name] = { action: "replace", value: input.value };
    }
    return actions;
  }

  for (const row of document.querySelectorAll("[data-field]")) {
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
    const input = document.querySelector(`#${name}`);
    const deletion = document.querySelector(`#${deleteId}`);
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
      saveStatus.textContent = "Lokaler Secret-Entwurf ist unvollständig.";
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
        const data = await response.json();
        if (response.status === 409) {
          const visible = mergeConflictSnapshot(syncState, data.snapshot, data.conflicts ?? []);
          renderSettingsSnapshot(data.snapshot, visible);
          saveStatus.textContent = "Konflikt: lokale Entwürfe wurden nicht überschrieben.";
          return;
        }
        if (!response.ok) {
          saveStatus.textContent = data.error || "Änderung abgelehnt.";
          return;
        }
        syncState.acceptSavedSnapshot(data);
        document.querySelector("#openai_api_key").value = "";
        document.querySelector("#cloudflare_api_token").value = "";
        document.querySelector("#delete_openai_api_key").checked = false;
        document.querySelector("#delete_cloudflare_api_token").checked = false;
        applySettingsSnapshot(data);
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

  document.querySelector("#discard-all").addEventListener("click", () => {
    interactionGate.run(() => {
      if (!window.confirm("Alle lokalen, noch nicht gespeicherten Entwürfe verwerfen?")) return;
      for (const name of [...syncState.dirty]) discardField(name);
      for (const name of [...syncState.secretDirty]) syncState.discardSecret(name);
      document.querySelector("#openai_api_key").value = "";
      document.querySelector("#cloudflare_api_token").value = "";
      document.querySelector("#delete_openai_api_key").checked = false;
      document.querySelector("#delete_cloudflare_api_token").checked = false;
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
  void bootstrap();
}
