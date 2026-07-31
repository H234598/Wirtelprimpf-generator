#!/usr/bin/env node

"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const APPLET_PATH = path.join(__dirname, "..", "files", "wirtelprimfgenerator@H234598", "applet.js");
let constructorCount = 0;
let nextSignalId = 1;
const pendingProcesses = [];
const removedSources = [];
const tooltipInstances = [];
let addedTimers = 0;
let commandLineSpawns = 0;

class Actor {
    constructor() { this.visible = true; }
    show() { this.visible = true; }
    hide() { this.visible = false; }
    add_style_class_name() {}
    remove_style_class_name() {}
}

class Menu {
    constructor() {
        this.items = [];
        this.isOpen = false;
        this.removeAllCount = 0;
        this.destroyCount = 0;
    }
    addMenuItem(item) { this.items.push(item); return item; }
    addAction(label, callback) {
        const item = new PopupMenuItem(label);
        item.connect("activate", callback);
        this.addMenuItem(item);
        return item;
    }
    removeAll() { this.removeAllCount += 1; this.items = []; }
    toggle() { this.isOpen = !this.isOpen; }
    destroy() { this.destroyCount += 1; }
}

class PopupMenuItem {
    constructor(label) {
        constructorCount += 1;
        this.label = { text: label || "" };
        this.actor = new Actor();
        this.sensitive = true;
        this.handlers = new Map();
    }
    connect(signal, callback) {
        const id = nextSignalId++;
        this.handlers.set(id, { signal, callback });
        return id;
    }
    activate() {
        for (const handler of this.handlers.values()) {
            if (handler.signal === "activate") handler.callback(this);
        }
    }
    setSensitive(value) { this.sensitive = Boolean(value); }
}

class PopupSubMenuMenuItem extends PopupMenuItem {
    constructor(label) { super(label); this.menu = new Menu(); }
}

class PopupSeparatorMenuItem extends PopupMenuItem {
    constructor() { super(""); }
}

class FakeCancellable {
    constructor() { this.cancelCount = 0; }
    cancel() { this.cancelCount += 1; }
}

class FakeTooltip {
    constructor(_actor, text) {
        this.text = text;
        this.destroyCount = 0;
        tooltipInstances.push(this);
    }
    set_text(text) { this.text = text; }
    destroy() { this.destroyCount += 1; }
}

class FakeProcess {
    constructor(args) {
        this.args = args;
        this.forceExitCount = 0;
        this.callback = null;
        pendingProcesses.push(this);
    }
    communicate_utf8_async(_input, cancellable, callback) {
        this.communicateCancellable = cancellable;
        if (this.args.includes("throw-async")) throw new Error("communicate scheduling failed");
        this.callback = callback;
    }
    communicate_utf8_finish(result) { return [true, result.stdout, result.stderr]; }
    get_exit_status() { return this.status || 0; }
    force_exit() { this.forceExitCount += 1; }
    send_signal() { this.forceExitCount += 1; }
    complete(status, stdout, stderr = "") {
        this.status = status;
        this.callback(this, { stdout, stderr });
    }
}

const context = {
    console,
    global: { log() {}, logError() {} },
    imports: {
        ui: {
            applet: {
                TextIconApplet: function() {},
                AppletPopupMenu: Menu,
            },
            popupMenu: {
                PopupMenuManager: class {
                    addMenu() {}
                    removeMenu() { this.removeCount = (this.removeCount || 0) + 1; }
                },
                PopupMenuItem,
                PopupSubMenuMenuItem,
                PopupSeparatorMenuItem,
            },
            settings: { BindingDirection: { IN: 1 }, AppletSettings: class {} },
            tooltips: { Tooltip: FakeTooltip },
            main: { notify() {} },
        },
        lang: { bind: (owner, fn) => fn.bind(owner) },
        gi: {
            Gio: {
                Cancellable: FakeCancellable,
                Subprocess: {
                    new: (args) => new FakeProcess(args),
                },
                SubprocessFlags: { NONE: 0, STDOUT_PIPE: 1, STDERR_PIPE: 2 },
            },
            GLib: {
                FileTest: { EXISTS: 1 },
                SOURCE_REMOVE: false,
                build_filenamev: (parts) => parts.join("/"),
                get_home_dir: () => "/home/test",
                file_test: () => true,
            },
            St: {},
        },
        mainloop: {
            source_remove: (id) => removedSources.push(id),
            timeout_add_seconds: () => { addedTimers += 1; return 99; },
        },
        misc: { util: { spawnCommandLine() { commandLineSpawns += 1; } } },
    },
};
context.imports.ui.applet.TextIconApplet.prototype = { _init() {} };

vm.createContext(context);
const source = fs.readFileSync(APPLET_PATH, "utf8") + "\nglobalThis.WirtelAppletForTest = WirtelApplet;";
vm.runInContext(source, context, { filename: APPLET_PATH });
const WirtelApplet = context.WirtelAppletForTest;

function makeApplet() {
    const applet = Object.create(WirtelApplet.prototype);
    applet.menu = new Menu();
    applet._removed = false;
    applet._menuBuilt = false;
    applet._menuFingerprint = "";
    applet._storyRows = [];
    applet._partRows = [];
    applet._errorRows = [];
    applet._helperProcesses = new Set();
    applet._scanInProgress = false;
    applet._scanPending = false;
    applet._scanGeneration = 0;
    applet._lastScan = null;
    applet._ttsProcess = null;
    applet._ttsWaitId = 0;
    applet._isReading = false;
    applet.notifyErrors = false;
    applet._setReading = (value) => { applet._isReading = value; };
    applet._openPath = (value) => { applet.openedPath = value; };
    applet._buildPersistentMenu();
    return applet;
}

function scanPayload(prefix = "scan", storyCount = 75) {
    return {
        ok: true,
        output_dir: `/output/${prefix}`,
        images: {
            story: { path: `/images/${prefix}-story.png` },
            generated: { path: `/images/${prefix}-generated.png` },
        },
        full_stories: Array.from({ length: storyCount }, (_unused, index) => ({
            label: `${prefix} story ${index}`,
            path: `/stories/${prefix}-${index}.md`,
        })),
        recent_parts: Array.from({ length: 20 }, (_unused, index) => ({
            label: `${prefix} part ${index}`,
            path: `/parts/${prefix}-${index}.md`,
            tooltip: `tooltip ${index}`,
        })),
        tts: { running: false, last_file: "", last_file_label: "" },
        stats: { known_full_story_count: storyCount },
        errors: [],
    };
}

function testPersistentMenuPools() {
    constructorCount = 0;
    const applet = makeApplet();
    const initial = scanPayload("initial", 75);
    applet._buildMenuFromScan(initial);
    assert.equal(applet._storyRows.length, 50, "story row pool is capped at the approved 50 completed volumes");
    assert.equal(applet._partRows.length, 15, "recent part pool follows the existing 15-row product limit");
    assert.equal(applet.menu.removeAllCount, 0, "data rendering never clears the root menu");
    assert.equal(applet._storyOverflowItem.actor.visible, true, "overflow notice is visible above the 50-volume limit");
    assert.match(applet._storyOverflowItem.label.text, /25 weitere vollständige Story-Bände nicht angezeigt/);
    assert.equal(applet._rotationWarningItem.actor.visible, true, "the repository-boundary warning is visible at 50 volumes");

    const warmedConstructors = constructorCount;
    for (let index = 0; index < 1000; index += 1) applet._buildMenuFromScan(initial);
    assert.equal(constructorCount, warmedConstructors, "identical scans allocate no menu objects after warm-up");

    const current = scanPayload("current", 75);
    applet._buildMenuFromScan(current);
    assert.equal(constructorCount, warmedConstructors, "changed scan data reuses existing story and part rows");
    applet._storyRows[0].activate();
    assert.equal(applet.openedPath, current.full_stories[25].path, "story action reads current data from the newest 50-volume window");

    applet._buildMenuFromScan(scanPayload("below-limit", 49));
    assert.equal(applet._storyOverflowItem.actor.visible, false, "overflow notice hides below the limit");
    assert.equal(applet._rotationWarningItem.actor.visible, false, "repository-boundary warning hides below 50 volumes");

    applet._buildLoadingMenu("loading");
    applet._buildErrorMenu("failure");
    assert.equal(applet.menu.removeAllCount, 0, "loading and error states preserve the root menu");
}

function testSinglePendingScanAndGeneration() {
    const applet = makeApplet();
    const requests = [];
    const renders = [];
    applet._helperBaseArgs = () => ["helper", "scan"];
    applet._spawnJson = (_args, callback) => { requests.push(callback); };
    applet._buildMenuFromScan = (data) => { renders.push(data.output_dir); };

    applet._refreshScan(false);
    applet._refreshScan(false);
    applet._refreshScan(false);
    assert.equal(requests.length, 1, "overlapping scans collapse into one in-flight request");
    assert.equal(applet._scanPending, true, "overlapping scans set exactly one pending flag");

    requests[0](scanPayload("first", 1));
    assert.equal(requests.length, 2, "one pending scan starts after the active scan completes");
    requests[1](scanPayload("second", 1));
    assert.deepEqual(renders, ["/output/first", "/output/second"]);

    requests[0](scanPayload("stale", 1));
    assert.deepEqual(renders, ["/output/first", "/output/second"], "stale scan generation cannot render again");
}

function testOwnedProcessTeardown() {
    removedSources.length = 0;
    pendingProcesses.length = 0;
    tooltipInstances.length = 0;
    const applet = makeApplet();
    applet._helperBaseArgs = (command) => ["helper", command];
    const scan = applet._spawnJson(["helper", "scan"], () => {});
    applet._startTts("tts-continue");
    const tts = applet._ttsProcess;
    applet._buildMenuFromScan(scanPayload("tooltips", 1));
    applet._ttsWaitId = 42;
    applet.settings = { finalized: 0, finalize() { this.finalized += 1; } };
    const settings = applet.settings;
    applet.menuManager = { removed: 0, removeMenu() { this.removed += 1; } };
    const manager = applet.menuManager;
    const menu = applet.menu;

    applet.on_applet_removed_from_panel();
    applet.on_applet_removed_from_panel();
    assert.ok(scan.communicateCancellable instanceof FakeCancellable, "scan I/O owns a cancellable");
    assert.ok(tts.communicateCancellable instanceof FakeCancellable, "TTS I/O owns a cancellable");
    assert.equal(scan.communicateCancellable.cancelCount, 1, "teardown cancels scan I/O exactly once");
    assert.equal(tts.communicateCancellable.cancelCount, 1, "teardown cancels TTS I/O exactly once");
    assert.equal(scan.forceExitCount, 1, "teardown stops active scan helper exactly once");
    assert.equal(tts.forceExitCount, 1, "teardown stops active TTS helper exactly once");
    assert.equal(tooltipInstances.length, 15, "part rows own a bounded tooltip pool");
    assert.ok(tooltipInstances.every((tooltip) => tooltip.destroyCount === 1), "teardown destroys every pooled tooltip exactly once");
    assert.deepEqual(removedSources, [42], "legacy wait timer is removed exactly once");
    assert.equal(settings.finalized, 1, "settings are finalized exactly once");
    assert.equal(manager.removed, 1, "menu manager releases the menu");
    assert.equal(menu.destroyCount, 1, "menu is destroyed exactly once");
    assert.equal(applet.menu, null, "menu reference is released");
    assert.equal(applet._storyRows.length, 0, "story row references are released");
    assert.equal(applet._partRows.length, 0, "part row references are released");
}

function testLateCallbacksAndTimerlessStop() {
    pendingProcesses.length = 0;
    addedTimers = 0;
    let delivered = 0;
    const removedApplet = makeApplet();
    const proc = removedApplet._spawnJson(["helper"], () => { delivered += 1; });
    removedApplet.on_applet_removed_from_panel();
    proc.complete(0, JSON.stringify({ ok: true }));
    assert.equal(delivered, 0, "helper callback after applet removal is ignored");

    const stopApplet = makeApplet();
    const tts = new FakeProcess(["tts"]);
    stopApplet._ttsProcess = tts;
    stopApplet._trackHelperProcess(tts);
    stopApplet._helperBaseArgs = () => ["helper", "tts-stop"];
    stopApplet._spawnJson = (_args, callback) => { callback({ ok: true }); };
    let refreshes = 0;
    stopApplet._refreshScan = () => { refreshes += 1; };
    stopApplet._stopTts();
    assert.equal(addedTimers, 0, "TTS stop does not create a delayed wait timer");
    assert.equal(stopApplet._ttsWaitId, 0, "TTS wait timer remains cleared");
    assert.equal(refreshes, 1, "TTS stop refreshes after the stop helper completes");
}

function testRemovedAppletCannotStartDetachedActions() {
    pendingProcesses.length = 0;
    commandLineSpawns = 0;
    const applet = makeApplet();
    applet._removed = true;

    applet._spawnDetached(["xdg-open", "https://example.invalid"]);
    applet._openAppletSettings();

    assert.equal(pendingProcesses.length, 0, "removed applet cannot start detached subprocesses");
    assert.equal(commandLineSpawns, 0, "removed applet cannot open settings through a stale action");
}

function testTtsSchedulingFailureReleasesOwnedOperation() {
    pendingProcesses.length = 0;
    const applet = makeApplet();
    applet._helperBaseArgs = () => ["helper", "throw-async"];

    applet._startTts("tts-continue");

    assert.equal(pendingProcesses.length, 1);
    assert.equal(pendingProcesses[0].forceExitCount, 1, "failed async setup terminates the owned subprocess");
    assert.equal(applet._helperProcesses.size, 0, "failed async setup releases the operation registry entry");
    assert.equal(applet._ttsProcess, null);
    assert.equal(applet._isReading, false);
}

testPersistentMenuPools();
testSinglePendingScanAndGeneration();
testOwnedProcessTeardown();
testLateCallbacksAndTimerlessStop();
testRemovedAppletCannotStartDetachedActions();
testTtsSchedulingFailureReleasesOwnedOperation();
console.log("Wirtel applet runtime stability tests passed");
