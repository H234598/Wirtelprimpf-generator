/* Wirtelprimfgenerator Cinnamon Applet - UUID: wirtelprimfgenerator@H234598 */

const Applet = imports.ui.applet;
const Lang = imports.lang;
const PopupMenu = imports.ui.popupMenu;
const Settings = imports.ui.settings;
const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const Mainloop = imports.mainloop;
const Util = imports.misc.util;
const Tooltips = imports.ui.tooltips;
const St = imports.gi.St;
const Main = imports.ui.main;

const UUID = "wirtelprimfgenerator@H234598";
const DEFAULT_GITHUB_URL = "https://github.com/H234598/Katzenbilder";
const HELPER_OUTPUT_LIMIT = 1024 * 1024;
const FULL_STORY_LIMIT = 50;
const RECENT_PART_LIMIT = 15;
const PANEL_ICON_FILES = {
    "orbit": "panel-icon.png",
    "moon": "panel-icon-moon.png",
    "spark": "panel-icon-spark.png"
};

function _(s) { return s; }

function WirtelApplet(metadata, orientation, panelHeight, instanceId) {
    this._init(metadata, orientation, panelHeight, instanceId);
}

WirtelApplet.prototype = {
    __proto__: Applet.TextIconApplet.prototype,

    _init: function(metadata, orientation, panelHeight, instanceId) {
        Applet.TextIconApplet.prototype._init.call(this, orientation, panelHeight, instanceId);
        this.metadata = metadata || {};
        this.orientation = orientation;
        this.instanceId = instanceId;
        this.appletDir = this.metadata.path || (GLib.get_home_dir() + "/.local/share/cinnamon/applets/" + UUID);
        this.helperPath = GLib.build_filenamev([this.appletDir, "helper.py"]);
        this.stateDir = GLib.build_filenamev([GLib.get_home_dir(), ".local", "state", "wirtelprimfgenerator-applet"]);

        this.outputDir = "";
        this.pythonCommand = "python3";
        this.openCommand = "xdg-open";
        this.ttsEngine = "auto";
        this.ttsPiperModel = "";
        this.ttsCommand = "";
        this.storyImageGlob = "";
        this.generatedImageGlob = "";
        this.fullStoryGlob = "";
        this.partGlob = "";
        this.scanMaxDepth = 4;
        this.refreshOnOpen = true;
        this.showPanelLabel = true;
        this.notifyErrors = true;
        this.githubUrl = DEFAULT_GITHUB_URL;
        this.panelIconChoice = "orbit";

        this._scanInProgress = false;
        this._scanPending = false;
        this._scanPendingOpen = false;
        this._scanGeneration = 0;
        this._scanProcess = null;
        this._lastScan = null;
        this._ttsProcess = null;
        this._ttsGeneration = 0;
        this._ttsWaitId = 0;
        this._isReading = false;
        this._removed = false;
        this._helperProcesses = new Set();
        this._menuBuilt = false;
        this._menuFingerprint = "";
        this._storyRows = [];
        this._partRows = [];
        this._errorRows = [];

        this.settings = new Settings.AppletSettings(this, UUID, instanceId);
        this._bindSettings();

        this._setIdlePresentation();
        this.set_applet_tooltip(_("Wirtelprimfgenerator"));

        this.menuManager = new PopupMenu.PopupMenuManager(this);
        this.menu = new Applet.AppletPopupMenu(this, orientation);
        this.menuManager.addMenu(this.menu);
        this._buildPersistentMenu();

        this._applet_context_menu.addAction(_("Einstellungen"), Lang.bind(this, this._openAppletSettings));
        this._applet_context_menu.addAction(_("Outputordner öffnen"), Lang.bind(this, this._openOutputFolderFromSettings));
        this._applet_context_menu.addAction(_("Run doctor"), Lang.bind(this, this._runDoctorFromSettings));
        this._applet_context_menu.addAction(_("GitHub öffnen"), Lang.bind(this, this._openProjectRepository));
        this._applet_context_menu.addAction(_("TTS stoppen"), Lang.bind(this, function() { this._stopTts(); }));

        this._buildLoadingMenu(_("Scanne Output …"));
        this._refreshScan(false);
    },

    _bindSettings: function() {
        let bind = Lang.bind(this, function(key, prop) {
            this.settings.bindProperty(Settings.BindingDirection.IN, key, prop, this._onSettingsChanged, null);
        });
        bind("output-dir", "outputDir");
        bind("python-command", "pythonCommand");
        bind("open-command", "openCommand");
        bind("tts-engine", "ttsEngine");
        bind("tts-piper-model", "ttsPiperModel");
        bind("tts-command", "ttsCommand");
        bind("story-image-glob", "storyImageGlob");
        bind("generated-image-glob", "generatedImageGlob");
        bind("full-story-glob", "fullStoryGlob");
        bind("part-glob", "partGlob");
        bind("scan-max-depth", "scanMaxDepth");
        bind("refresh-on-open", "refreshOnOpen");
        bind("show-panel-label", "showPanelLabel");
        bind("notify-errors", "notifyErrors");
        bind("github-url", "githubUrl");
        bind("panel-icon-choice", "panelIconChoice");
    },

    _onSettingsChanged: function() {
        this._setIdlePresentation();
        this._refreshScan(false);
    },

    on_applet_clicked: function(event) {
        if (this._removed || !this.menu) return;
        if (this._isReading) {
            this._stopTts();
            return;
        }
        this.menu.toggle();
        if (this.refreshOnOpen) this._refreshScan(false);
    },

    on_applet_removed_from_panel: function() {
        if (this._removed) return;
        this._removed = true;
        this._scanGeneration += 1;
        this._ttsGeneration += 1;
        if (this._ttsWaitId) {
            Mainloop.source_remove(this._ttsWaitId);
            this._ttsWaitId = 0;
        }
        for (let operation of Array.from(this._helperProcesses)) this._cancelHelperOperation(operation);
        this._helperProcesses.clear();
        this._scanProcess = null;
        this._ttsProcess = null;
        this._scanInProgress = false;
        this._scanPending = false;
        if (this.settings) {
            try { this.settings.finalize(); }
            catch (e2) {}
            this.settings = null;
        }
        if (this.menuManager && this.menu) {
            try { this.menuManager.removeMenu(this.menu); }
            catch (e3) {}
        }
        if (this.menu) {
            for (let row of this._partRows) {
                if (row && row._wpgTooltip && row._wpgTooltip.destroy) {
                    try { row._wpgTooltip.destroy(); }
                    catch (e4) {}
                }
                if (row) row._wpgTooltip = null;
            }
            try { this.menu.destroy(); }
            catch (e5) {}
            this.menu = null;
        }
        this.menuManager = null;
        this._storyRows = [];
        this._partRows = [];
        this._errorRows = [];
    },

    _setIdlePresentation: function() {
        let iconPath = this._panelIconPath();
        try {
            if (GLib.file_test(iconPath, GLib.FileTest.EXISTS)) this.set_applet_icon_path(iconPath);
            else this.set_applet_icon_symbolic_name("image-x-generic");
        } catch (e) {
            this.set_applet_icon_symbolic_name("image-x-generic");
        }
        this.set_applet_label(this.showPanelLabel ? "WP" : "");
        this.set_applet_tooltip(_("Wirtelprimfgenerator"));
    },

    _panelIconPath: function() {
        let iconFile = PANEL_ICON_FILES[this.panelIconChoice] || PANEL_ICON_FILES["orbit"];
        return GLib.build_filenamev([this.appletDir, "assets", iconFile]);
    },

    _setReading: function(reading) {
        this._isReading = reading;
        if (reading) {
            this.set_applet_label("■");
            this.set_applet_tooltip(_("TTS läuft – Klick stoppt"));
            try { this.actor.add_style_class_name("wpg-reading"); } catch (e) {}
        } else {
            this._setIdlePresentation();
            try { this.actor.remove_style_class_name("wpg-reading"); } catch (e2) {}
        }
    },

    _helperBaseArgs: function(command) {
        let py = (this.pythonCommand && this.pythonCommand.length > 0) ? this.pythonCommand : "python3";
        return [py, this.helperPath, command,
            "--state-dir", this.stateDir,
            "--output-dir", this.outputDir || "",
            "--open-command", this.openCommand || "xdg-open",
            "--tts-engine", this.ttsEngine || "auto",
            "--tts-piper-model", this.ttsPiperModel || "",
            "--tts-command", this.ttsCommand || "",
            "--story-image-glob", this.storyImageGlob || "",
            "--generated-image-glob", this.generatedImageGlob || "",
            "--full-story-glob", this.fullStoryGlob || "",
            "--part-glob", this.partGlob || "",
            "--max-depth", String(this.scanMaxDepth || 4)
        ];
    },

    _trackHelperProcess: function(proc) {
        let operation = {
            process: proc,
            cancellable: new Gio.Cancellable(),
            cancelled: false,
            finished: false
        };
        this._helperProcesses.add(operation);
        return operation;
    },

    _finishHelperOperation: function(operation) {
        if (!operation || operation.finished) return;
        operation.finished = true;
        this._helperProcesses.delete(operation);
    },

    _cancelHelperIo: function(operation) {
        if (!operation || operation.finished || operation.cancelled) return;
        operation.cancelled = true;
        if (operation.cancellable) {
            try { operation.cancellable.cancel(); }
            catch (e1) {}
        }
    },

    _cancelHelperOperation: function(operation) {
        if (!operation || operation.finished) return;
        this._cancelHelperIo(operation);
        if (operation.process) {
            try { operation.process.force_exit(); }
            catch (e2) {}
        }
        this._finishHelperOperation(operation);
    },

    _helperOperationForProcess: function(proc) {
        for (let operation of this._helperProcesses) {
            if (operation && operation.process === proc) return operation;
        }
        return null;
    },

    _spawnJson: function(args, callback) {
        if (this._removed) return null;
        let proc = null;
        let operation = null;
        try {
            proc = Gio.Subprocess.new(args, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            operation = this._trackHelperProcess(proc);
            proc.communicate_utf8_async(null, operation.cancellable, Lang.bind(this, function(p, res) {
                let stdout = "";
                let stderr = "";
                let status = 0;
                try {
                    let result = p.communicate_utf8_finish(res);
                    stdout = (result[1] || "").slice(0, HELPER_OUTPUT_LIMIT);
                    stderr = (result[2] || "").slice(0, HELPER_OUTPUT_LIMIT);
                    status = p.get_exit_status ? p.get_exit_status() : 0;
                } catch (e) { stderr = String(e); status = 1; }
                this._finishHelperOperation(operation);
                if (this._removed) return;
                let data = null;
                try { data = stdout ? JSON.parse(stdout) : {ok: false, errors: [stderr || "Kein Output"]}; }
                catch (e2) { data = {ok: false, errors: ["JSON parse failed", String(e2), stdout]}; }
                if (stderr && stderr.length > 0) global.log("[" + UUID + "] helper stderr: " + stderr);
                if (data && data.exit_status === undefined) data.exit_status = status;
                callback(data);
            }));
            return proc;
        } catch (e) {
            if (operation) this._cancelHelperOperation(operation);
            else if (proc) {
                try { proc.force_exit(); }
                catch (e2) {}
            }
            if (!this._removed) callback({ok: false, errors: [String(e)]});
            return null;
        }
    },

    _spawnDetached: function(args) {
        if (this._removed) return;
        try { Gio.Subprocess.new(args, Gio.SubprocessFlags.NONE); }
        catch (e) { global.logError("[" + UUID + "] spawn failed: " + e); }
    },

    _refreshScan: function(openAfter) {
        if (this._removed) return;
        if (this._scanInProgress) {
            this._scanPending = true;
            this._scanPendingOpen = this._scanPendingOpen || openAfter === true;
            return;
        }
        this._scanInProgress = true;
        this._scanPending = false;
        let generation = ++this._scanGeneration;
        let scanProcess = this._spawnJson(this._helperBaseArgs("scan"), Lang.bind(this, function(data) {
            if (this._removed || generation !== this._scanGeneration) return;
            this._scanInProgress = false;
            this._scanProcess = null;
            if (!data || data.ok === false) {
                this._buildErrorMenu(data && data.errors ? data.errors.join("\n") : _("Scan fehlgeschlagen"));
                if (this.notifyErrors) this._notify(_("Scan fehlgeschlagen"), data && data.errors ? data.errors[0] : _("Unbekannter Fehler"));
            } else {
                this._lastScan = data;
                this._setReading(data.tts && data.tts.running ? true : (this._ttsProcess !== null));
                this._buildMenuFromScan(data);
                if (openAfter && this.menu && !this.menu.isOpen) this.menu.toggle();
            }
            if (this._scanPending) {
                let pendingOpen = this._scanPendingOpen;
                this._scanPending = false;
                this._scanPendingOpen = false;
                this._refreshScan(pendingOpen);
            }
        }));
        if (!this._removed && generation === this._scanGeneration && this._scanInProgress) this._scanProcess = scanProcess;
    },

    _buildPersistentMenu: function() {
        if (this._menuBuilt || !this.menu) return;
        this._menuBuilt = true;

        this._statusItem = this._addDisabled(this.menu, _("Lade …"));
        this._statusSeparator = new PopupMenu.PopupSeparatorMenuItem();
        this.menu.addMenuItem(this._statusSeparator);

        this._currentImageMenu = new PopupMenu.PopupSubMenuMenuItem(_("Aktuelles Bild"));
        this.menu.addMenuItem(this._currentImageMenu);
        this._imageStoryItem = this._createAction(this._currentImageMenu.menu, _("Story"), Lang.bind(this, function() {
            this._openPath(this._imageStoryItem._wpgPath);
        }));
        this._imageGeneratedItem = this._createAction(this._currentImageMenu.menu, _("Generated"), Lang.bind(this, function() {
            this._openPath(this._imageGeneratedItem._wpgPath);
        }));

        this._storyMenu = new PopupMenu.PopupSubMenuMenuItem(_("Story"));
        this.menu.addMenuItem(this._storyMenu);
        this._readStoryMenu = new PopupMenu.PopupSubMenuMenuItem(_("Read Story"));
        this._storyMenu.menu.addMenuItem(this._readStoryMenu);
        this._storyEmptyItem = this._addDisabled(this._readStoryMenu.menu, _("Read Story – keine Full Story"));
        this._storyOverflowItem = this._addDisabled(this._readStoryMenu.menu, "");
        this._storyOverflowItem.actor.hide();
        this._readPartMenu = new PopupMenu.PopupSubMenuMenuItem(_("Read part"));
        this._storyMenu.menu.addMenuItem(this._readPartMenu);
        this._partEmptyItem = this._addDisabled(this._readPartMenu.menu, _("Keine Storyteile gefunden"));

        this._ttsMenu = new PopupMenu.PopupSubMenuMenuItem(_("TTS"));
        this._storyMenu.menu.addMenuItem(this._ttsMenu);
        this._createAction(this._ttsMenu.menu, _("Continue reading"), Lang.bind(this, function() { this._startTts("tts-continue"); }));
        this._createAction(this._ttsMenu.menu, _("Set"), Lang.bind(this, function() { this._startTts("tts-set"); }));
        this._ttsStopSeparator = new PopupMenu.PopupSeparatorMenuItem();
        this._ttsMenu.menu.addMenuItem(this._ttsStopSeparator);
        this._ttsStopItem = this._createAction(this._ttsMenu.menu, _("Stop"), Lang.bind(this, this._stopTts));
        this._ttsLastSeparator = new PopupMenu.PopupSeparatorMenuItem();
        this._ttsMenu.menu.addMenuItem(this._ttsLastSeparator);
        this._ttsLastHeadingItem = this._addDisabled(this._ttsMenu.menu, _("Letzte Datei:"));
        this._ttsLastFileItem = this._addDisabled(this._ttsMenu.menu, "");

        this._toolsMenu = new PopupMenu.PopupSubMenuMenuItem(_("Setup / Diagnose"));
        this.menu.addMenuItem(this._toolsMenu);
        this._createAction(this._toolsMenu.menu, _("Run doctor"), Lang.bind(this, this._runDoctorFromSettings));
        this._createAction(this._toolsMenu.menu, _("Copy setup plan"), Lang.bind(this, this._copySetupPlanFromSettings));
        this._createAction(this._toolsMenu.menu, _("Outputordner öffnen"), Lang.bind(this, this._openOutputFolderFromSettings));
        this._createAction(this._toolsMenu.menu, _("Open applet settings"), Lang.bind(this, this._openAppletSettings));
        this._createAction(this._toolsMenu.menu, _("GitHub öffnen"), Lang.bind(this, this._openProjectRepository));
        this._createAction(this._toolsMenu.menu, _("Neu scannen"), Lang.bind(this, function() { this._refreshScan(false); }));
        this._toolsStopItem = this._createAction(this._toolsMenu.menu, _("TTS stoppen"), Lang.bind(this, this._stopTts));

        this._outputSeparator = new PopupMenu.PopupSeparatorMenuItem();
        this.menu.addMenuItem(this._outputSeparator);
        this._outputItem = this._createAction(this.menu, _("Output nicht gefunden"), Lang.bind(this, function() {
            this._openPath(this._outputItem._wpgPath);
        }));
        this._storyCountItem = this._addDisabled(this.menu, "");
        this._rotationWarningItem = this._addDisabled(this.menu, "");

        this._errorSeparator = new PopupMenu.PopupSeparatorMenuItem();
        this.menu.addMenuItem(this._errorSeparator);
        this._errorHeadingItem = this._addDisabled(this.menu, _("Hinweise:"));
        for (let i = 0; i < 4; i++) this._errorRows.push(this._addDisabled(this.menu, ""));

        this._errorActionSeparator = new PopupMenu.PopupSeparatorMenuItem();
        this.menu.addMenuItem(this._errorActionSeparator);
        this._errorRetryItem = this._createAction(this.menu, _("Erneut scannen"), Lang.bind(this, function() { this._refreshScan(false); }));
        this._errorDoctorItem = this._createAction(this.menu, _("Run doctor"), Lang.bind(this, this._runDoctorFromSettings));
        this._errorPlanItem = this._createAction(this.menu, _("Copy setup plan"), Lang.bind(this, this._copySetupPlanFromSettings));
        this._errorSettingsItem = this._createAction(this.menu, _("Einstellungen"), Lang.bind(this, this._openAppletSettings));

        this._mainItems = [this._statusSeparator, this._currentImageMenu, this._storyMenu, this._toolsMenu, this._outputSeparator, this._outputItem, this._storyCountItem, this._rotationWarningItem];
        this._errorActionItems = [this._errorActionSeparator, this._errorRetryItem, this._errorDoctorItem, this._errorPlanItem, this._errorSettingsItem];
        this._setItemsVisible(this._mainItems, false);
        this._setItemsVisible(this._errorActionItems, false);
        this._setErrorRows([]);
        this._setTtsRows(false, null);
    },

    _createAction: function(menu, label, callback) {
        let item = new PopupMenu.PopupMenuItem(label || "");
        item.connect("activate", callback);
        menu.addMenuItem(item);
        return item;
    },

    _setItemsVisible: function(items, visible) {
        for (let item of items) {
            if (!item || !item.actor) continue;
            if (visible) item.actor.show();
            else item.actor.hide();
        }
    },

    _setErrorRows: function(errors) {
        let visibleErrors = Array.isArray(errors) ? errors.slice(0, 4) : [];
        let visible = visibleErrors.length > 0;
        this._setItemsVisible([this._errorSeparator, this._errorHeadingItem], visible);
        for (let i = 0; i < this._errorRows.length; i++) {
            let row = this._errorRows[i];
            if (i < visibleErrors.length) {
                row.label.text = String(visibleErrors[i]);
                row.actor.show();
            } else {
                row.label.text = "";
                row.actor.hide();
            }
        }
    },

    _setPathItem: function(item, label, path) {
        item._wpgPath = path || "";
        item.label.text = path ? label : label + _(" – nicht gefunden");
        item.setSensitive(!!path);
    },

    _setTtsRows: function(running, tts) {
        let lastFile = tts && tts.last_file ? tts.last_file : "";
        this._setItemsVisible([this._ttsStopSeparator, this._ttsStopItem, this._toolsStopItem], running);
        this._setItemsVisible([this._ttsLastSeparator, this._ttsLastHeadingItem, this._ttsLastFileItem], !!lastFile);
        this._ttsLastFileItem.label.text = lastFile ? (tts.last_file_label || lastFile) : "";
    },

    _updateStoryRows: function(stories, totalCount) {
        let allValues = Array.isArray(stories) ? stories : [];
        let values = allValues.length > FULL_STORY_LIMIT ? allValues.slice(-FULL_STORY_LIMIT) : allValues;
        let normalizedTotal = Number.isInteger(totalCount) && totalCount >= 0 ? totalCount : allValues.length;
        normalizedTotal = Math.max(normalizedTotal, allValues.length);
        let omittedCount = Math.max(0, normalizedTotal - values.length);
        while (this._storyRows.length < values.length) {
            let row = this._createAction(this._readStoryMenu.menu, "", Lang.bind(this, function() {
                this._openPath(row._wpgData ? row._wpgData.path : "");
            }));
            row._wpgData = null;
            row.actor.hide();
            this._storyRows.push(row);
        }
        for (let i = 0; i < this._storyRows.length; i++) {
            let row = this._storyRows[i];
            if (i < values.length) {
                row._wpgData = values[i];
                row.label.text = values[i].label || values[i].path || _("Story");
                row.actor.show();
            } else {
                row._wpgData = null;
                row.actor.hide();
            }
        }
        this._setItemsVisible([this._storyEmptyItem], values.length === 0);
        this._storyOverflowItem.label.text = omittedCount > 0
            ? (omittedCount + _(" weitere vollständige Story-Bände nicht angezeigt"))
            : "";
        this._setItemsVisible([this._storyOverflowItem], omittedCount > 0);
        this._rotationWarningItem.label.text = normalizedTotal >= FULL_STORY_LIMIT
            ? (_("Archivgrenze erreicht: 50 vollständige Story-Bände · Repositorywechsel erforderlich"))
            : "";
        this._setItemsVisible([this._rotationWarningItem], normalizedTotal >= FULL_STORY_LIMIT);
    },

    _updatePartRows: function(parts) {
        let values = Array.isArray(parts) ? parts.slice(0, RECENT_PART_LIMIT) : [];
        while (this._partRows.length < values.length) {
            let row = this._createAction(this._readPartMenu.menu, "", Lang.bind(this, function() {
                this._openPath(row._wpgData ? row._wpgData.path : "");
            }));
            row._wpgData = null;
            row.actor.hide();
            this._partRows.push(row);
        }
        for (let i = 0; i < this._partRows.length; i++) {
            let row = this._partRows[i];
            if (i < values.length) {
                row._wpgData = values[i];
                row.label.text = values[i].label || values[i].path || _("Storyteil");
                row.actor.show();
                let tooltip = values[i].tooltip || "";
                if (tooltip && !row._wpgTooltip) {
                    try { row._wpgTooltip = new Tooltips.Tooltip(row.actor, tooltip); }
                    catch (e) {}
                } else if (row._wpgTooltip && row._wpgTooltip.set_text) {
                    try { row._wpgTooltip.set_text(tooltip); }
                    catch (e2) {}
                }
            } else {
                row._wpgData = null;
                row.actor.hide();
            }
        }
        this._setItemsVisible([this._partEmptyItem], values.length === 0);
    },

    _buildLoadingMenu: function(text) {
        this._buildPersistentMenu();
        this._menuFingerprint = "loading:" + (text || "");
        this._statusItem.label.text = text || _("Lade …");
        this._setItemsVisible(this._mainItems, false);
        this._setItemsVisible(this._errorActionItems, false);
        this._setErrorRows([]);
    },

    _buildErrorMenu: function(message) {
        this._buildPersistentMenu();
        this._menuFingerprint = "error:" + (message || "");
        this._statusItem.label.text = _("Fehler");
        this._setItemsVisible(this._mainItems, false);
        this._setItemsVisible([this._toolsMenu], true);
        this._setItemsVisible(this._errorActionItems, true);
        this._setErrorRows([message || _("Unbekannter Fehler")]);
    },

    _buildMenuFromScan: function(data) {
        this._buildPersistentMenu();
        let safeData = data || {};
        let fingerprint = JSON.stringify({
            output_dir: safeData.output_dir || "",
            images: safeData.images || {},
            full_stories: safeData.full_stories || [],
            recent_parts: safeData.recent_parts || [],
            tts: safeData.tts || {},
            stats: safeData.stats || {},
            errors: safeData.errors || [],
            reading: this._isReading
        });
        if (fingerprint === this._menuFingerprint) return;
        this._menuFingerprint = fingerprint;

        let running = this._isReading || !!(safeData.tts && safeData.tts.running);
        this._statusItem.label.text = running ? _("TTS läuft · Klick aufs Panel stoppt") : (safeData.output_dir ? _("Wirtelprimpf") : _("Setup nötig"));
        this._setItemsVisible(this._mainItems, true);
        this._setItemsVisible(this._errorActionItems, false);

        this._setPathItem(this._imageStoryItem, _("Story"), safeData.images && safeData.images.story ? safeData.images.story.path : "");
        this._setPathItem(this._imageGeneratedItem, _("Generated"), safeData.images && safeData.images.generated ? safeData.images.generated.path : "");
        let stats = safeData.stats || {};
        let totalStoryCount = Number.isInteger(stats.current_full_story_count)
            ? stats.current_full_story_count
            : (Number.isInteger(stats.known_full_story_count) ? stats.known_full_story_count : (safeData.full_stories || []).length);
        this._updateStoryRows(safeData.full_stories || [], totalStoryCount);
        this._updatePartRows(safeData.recent_parts || []);
        this._setTtsRows(running, safeData.tts || {});

        this._outputItem._wpgPath = safeData.output_dir || "";
        this._outputItem.label.text = safeData.output_dir ? (_("Output: ") + safeData.output_dir) : _("Output nicht gefunden");
        this._outputItem.setSensitive(!!safeData.output_dir);
        let countKnown = safeData.stats && (safeData.stats.current_full_story_count !== undefined || safeData.stats.known_full_story_count !== undefined);
        this._storyCountItem.label.text = countKnown ? (_("Storys gemerkt: ") + totalStoryCount) : "";
        this._setItemsVisible([this._storyCountItem], countKnown);
        this._setErrorRows(safeData.errors || []);
    },

    _addDisabled: function(menu, label) {
        let item = new PopupMenu.PopupMenuItem(label || "");
        item.setSensitive(false);
        menu.addMenuItem(item);
        return item;
    },

    _openPath: function(path) {
        if (!path || path.length === 0) return;
        let args = this._helperBaseArgs("open");
        args.push("--path", path);
        this._spawnJson(args, Lang.bind(this, function(data) {
            if (!data || data.ok === false) {
                global.log("[" + UUID + "] open failed: " + JSON.stringify(data));
                if (this.notifyErrors) this._notify(_("Öffnen fehlgeschlagen"), data && data.errors ? data.errors[0] : String(path));
            }
        }));
    },

    _startTts: function(command) {
        if (this._removed || this._isReading) return;
        let args = this._helperBaseArgs(command);
        let generation = ++this._ttsGeneration;
        let activeProcess = null;
        let operation = null;
        try {
            activeProcess = Gio.Subprocess.new(args, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            this._ttsProcess = activeProcess;
            operation = this._trackHelperProcess(activeProcess);
            this._setReading(true);
            activeProcess.communicate_utf8_async(null, operation.cancellable, Lang.bind(this, function(proc, res) {
                let stdout = "";
                let stderr = "";
                try {
                    let result = proc.communicate_utf8_finish(res);
                    stdout = (result[1] || "").slice(0, HELPER_OUTPUT_LIMIT);
                    stderr = (result[2] || "").slice(0, HELPER_OUTPUT_LIMIT);
                } catch (e) { stderr = String(e); }
                this._finishHelperOperation(operation);
                if (this._removed || generation !== this._ttsGeneration) return;
                if (this._ttsProcess === proc) this._ttsProcess = null;
                this._setReading(false);
                if (stderr) global.log("[" + UUID + "] TTS stderr: " + stderr);
                try {
                    let data = stdout ? JSON.parse(stdout) : null;
                    if (data && data.ok === false && this.notifyErrors) this._notify(_("TTS"), data.errors ? data.errors[0] : _("Vorlesen fehlgeschlagen"));
                } catch (e2) {}
                this._refreshScan(false);
            }));
        } catch (e) {
            if (operation) this._cancelHelperOperation(operation);
            else if (activeProcess) {
                try { activeProcess.force_exit(); }
                catch (e2) {}
            }
            if (this._ttsProcess === activeProcess) this._ttsProcess = null;
            this._setReading(false);
            global.logError("[" + UUID + "] Could not start TTS: " + e);
            if (this.notifyErrors) this._notify(_("TTS"), String(e));
        }
    },

    _stopTts: function() {
        if (this._removed) return;
        this._ttsGeneration += 1;
        if (this._ttsProcess !== null) {
            let operation = this._helperOperationForProcess(this._ttsProcess);
            this._cancelHelperIo(operation);
            try { this._ttsProcess.send_signal(15); }
            catch (e1) { try { this._ttsProcess.force_exit(); } catch (e2) {} }
        }
        this._ttsProcess = null;
        this._setReading(false);
        if (this._ttsWaitId) {
            Mainloop.source_remove(this._ttsWaitId);
            this._ttsWaitId = 0;
        }
        this._spawnJson(this._helperBaseArgs("tts-stop"), Lang.bind(this, function(data) {
            if (this._removed) return;
            this._refreshScan(false);
        }));
    },

    _openAppletSettings: function() {
        if (this._removed) return;
        Util.spawnCommandLine("xlet-settings applet " + UUID + " -i " + this.instanceId);
    },

    _openProjectRepository: function() {
        this._spawnDetached(["xdg-open", this.githubUrl || DEFAULT_GITHUB_URL]);
    },

    _openOutputFolderFromSettings: function() {
        let dir = (this._lastScan && this._lastScan.output_dir) ? this._lastScan.output_dir : this.outputDir;
        if (dir && dir.length > 0) this._openPath(dir);
        else this._runDoctorFromSettings();
    },

    _runDoctorFromSettings: function() {
        this._spawnJson(this._helperBaseArgs("doctor"), Lang.bind(this, function(data) {
            if (!data) return;
            let title = data.ok ? _("Wirtel Doctor: ok") : _("Wirtel Doctor: Setup nötig");
            let msg = data.summary || (data.errors ? data.errors.join("\n") : "");
            this._notify(title, msg);
            global.log("[" + UUID + "] doctor: " + JSON.stringify(data));
            this._refreshScan(false);
        }));
    },

    _copySetupPlanFromSettings: function() {
        this._spawnJson(this._helperBaseArgs("setup-plan"), Lang.bind(this, function(data) {
            if (!data || data.ok === false) {
                if (this.notifyErrors) this._notify(_("Setup plan"), data && data.errors ? data.errors[0] : _("Konnte Setup-Plan nicht erzeugen"));
                return;
            }
            if (this._copyText(data.text || "")) this._notify(_("Setup plan"), _("In die Zwischenablage kopiert."));
        }));
    },

    _resetTtsStateFromSettings: function() {
        this._spawnJson(this._helperBaseArgs("reset-state"), Lang.bind(this, function(data) {
            this._notify(_("TTS-State"), data && data.ok ? _("Zurückgesetzt.") : _("Konnte nicht zurücksetzen."));
            this._refreshScan(false);
        }));
    },

    _copyText: function(text) {
        try {
            let clipboard = St.Clipboard.get_default();
            clipboard.set_text(St.ClipboardType.CLIPBOARD, text);
            return true;
        } catch (e) {
            global.logError("[" + UUID + "] clipboard failed: " + e);
            return false;
        }
    },

    _notify: function(title, message) {
        try { Main.notify(title || _("Wirtelprimfgenerator"), message || ""); }
        catch (e) { global.log("[" + UUID + "] notify: " + title + " " + message); }
    }
};

function main(metadata, orientation, panelHeight, instanceId) {
    return new WirtelApplet(metadata, orientation, panelHeight, instanceId);
}
