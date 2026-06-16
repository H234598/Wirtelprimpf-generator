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
        this.iconPath = GLib.build_filenamev([this.appletDir, "assets", "panel-icon.png"]);
        this.stateDir = GLib.build_filenamev([GLib.get_home_dir(), ".local", "state", "wirtelprimfgenerator-applet"]);

        this.outputDir = "";
        this.pythonCommand = "python3";
        this.openCommand = "xdg-open";
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

        this._scanInProgress = false;
        this._lastScan = null;
        this._ttsProcess = null;
        this._ttsWaitId = 0;
        this._isReading = false;

        this.settings = new Settings.AppletSettings(this, UUID, instanceId);
        this._bindSettings();

        this._setIdlePresentation();
        this.set_applet_tooltip(_("Wirtelprimfgenerator"));

        this.menuManager = new PopupMenu.PopupMenuManager(this);
        this.menu = new Applet.AppletPopupMenu(this, orientation);
        this.menuManager.addMenu(this.menu);

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
    },

    _onSettingsChanged: function() {
        this._setIdlePresentation();
        this._refreshScan(false);
    },

    on_applet_clicked: function(event) {
        if (this._isReading) {
            this._stopTts();
            return;
        }
        this.menu.toggle();
        if (this.refreshOnOpen) this._refreshScan(false);
    },

    on_applet_removed_from_panel: function() {
        if (this._ttsWaitId) {
            Mainloop.source_remove(this._ttsWaitId);
            this._ttsWaitId = 0;
        }
    },

    _setIdlePresentation: function() {
        try {
            if (GLib.file_test(this.iconPath, GLib.FileTest.EXISTS)) this.set_applet_icon_path(this.iconPath);
            else this.set_applet_icon_symbolic_name("image-x-generic");
        } catch (e) {
            this.set_applet_icon_symbolic_name("image-x-generic");
        }
        this.set_applet_label(this.showPanelLabel ? "WP" : "");
        this.set_applet_tooltip(_("Wirtelprimfgenerator"));
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
            "--tts-command", this.ttsCommand || "",
            "--story-image-glob", this.storyImageGlob || "",
            "--generated-image-glob", this.generatedImageGlob || "",
            "--full-story-glob", this.fullStoryGlob || "",
            "--part-glob", this.partGlob || "",
            "--max-depth", String(this.scanMaxDepth || 4)
        ];
    },

    _spawnJson: function(args, callback) {
        try {
            let proc = Gio.Subprocess.new(args, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            proc.communicate_utf8_async(null, null, Lang.bind(this, function(p, res) {
                let stdout = "";
                let stderr = "";
                let status = 0;
                try {
                    let result = p.communicate_utf8_finish(res);
                    stdout = result[1] || "";
                    stderr = result[2] || "";
                    status = p.get_exit_status ? p.get_exit_status() : 0;
                } catch (e) { stderr = String(e); status = 1; }
                let data = null;
                try { data = stdout ? JSON.parse(stdout) : {ok: false, errors: [stderr || "Kein Output"]}; }
                catch (e2) { data = {ok: false, errors: ["JSON parse failed", String(e2), stdout]}; }
                if (stderr && stderr.length > 0) global.log("[" + UUID + "] helper stderr: " + stderr);
                if (data && data.exit_status === undefined) data.exit_status = status;
                callback(data);
            }));
        } catch (e) { callback({ok: false, errors: [String(e)]}); }
    },

    _spawnDetached: function(args) {
        try { Gio.Subprocess.new(args, Gio.SubprocessFlags.NONE); }
        catch (e) { global.logError("[" + UUID + "] spawn failed: " + e); }
    },

    _refreshScan: function(openAfter) {
        if (this._scanInProgress) return;
        this._scanInProgress = true;
        this._spawnJson(this._helperBaseArgs("scan"), Lang.bind(this, function(data) {
            this._scanInProgress = false;
            if (!data || data.ok === false) {
                this._buildErrorMenu(data && data.errors ? data.errors.join("\n") : _("Scan fehlgeschlagen"));
                if (this.notifyErrors) this._notify(_("Scan fehlgeschlagen"), data && data.errors ? data.errors[0] : _("Unbekannter Fehler"));
                return;
            }
            this._lastScan = data;
            this._setReading(data.tts && data.tts.running ? true : (this._ttsProcess !== null));
            this._buildMenuFromScan(data);
            if (openAfter && !this.menu.isOpen) this.menu.toggle();
        }));
    },

    _buildLoadingMenu: function(text) {
        this.menu.removeAll();
        let item = new PopupMenu.PopupMenuItem(text || _("Lade …"));
        item.setSensitive(false);
        this.menu.addMenuItem(item);
    },

    _buildErrorMenu: function(message) {
        this.menu.removeAll();
        this._addDisabled(this.menu, _("Fehler"));
        this._addDisabled(this.menu, message || _("Unbekannter Fehler"));
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this.menu.addAction(_("Erneut scannen"), Lang.bind(this, function() { this._refreshScan(false); }));
        this.menu.addAction(_("Run doctor"), Lang.bind(this, this._runDoctorFromSettings));
        this.menu.addAction(_("Copy setup plan"), Lang.bind(this, this._copySetupPlanFromSettings));
        this.menu.addAction(_("Einstellungen"), Lang.bind(this, this._openAppletSettings));
    },

    _buildMenuFromScan: function(data) {
        this.menu.removeAll();

        let statusText = data.output_dir ? _("Wirtelprimpf") : _("Setup nötig");
        if (data.tts && data.tts.running) statusText = _("TTS läuft · Klick aufs Panel stoppt");
        this._addDisabled(this.menu, statusText);
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        let currentImage = new PopupMenu.PopupSubMenuMenuItem(_("Aktuelles Bild"));
        this.menu.addMenuItem(currentImage);
        this._addOpenOrDisabled(currentImage.menu, _("Story"), data.images && data.images.story ? data.images.story.path : null);
        this._addOpenOrDisabled(currentImage.menu, _("Generated"), data.images && data.images.generated ? data.images.generated.path : null);

        let story = new PopupMenu.PopupSubMenuMenuItem(_("Story"));
        this.menu.addMenuItem(story);
        this._addReadStory(story.menu, data);
        this._addReadPart(story.menu, data);
        this._addTts(story.menu, data);

        let tools = new PopupMenu.PopupSubMenuMenuItem(_("Setup / Diagnose"));
        this.menu.addMenuItem(tools);
        tools.menu.addAction(_("Run doctor"), Lang.bind(this, this._runDoctorFromSettings));
        tools.menu.addAction(_("Copy setup plan"), Lang.bind(this, this._copySetupPlanFromSettings));
        tools.menu.addAction(_("Outputordner öffnen"), Lang.bind(this, this._openOutputFolderFromSettings));
        tools.menu.addAction(_("Open applet settings"), Lang.bind(this, this._openAppletSettings));
        tools.menu.addAction(_("GitHub öffnen"), Lang.bind(this, this._openProjectRepository));
        tools.menu.addAction(_("Neu scannen"), Lang.bind(this, function() { this._refreshScan(false); }));
        if (this._isReading || (data.tts && data.tts.running)) tools.menu.addAction(_("TTS stoppen"), Lang.bind(this, this._stopTts));

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        let outLabel = data.output_dir ? (_("Output: ") + data.output_dir) : _("Output nicht gefunden");
        let outItem = new PopupMenu.PopupMenuItem(outLabel);
        outItem.setSensitive(!!data.output_dir);
        if (data.output_dir) outItem.connect("activate", Lang.bind(this, function() { this._openPath(data.output_dir); }));
        this.menu.addMenuItem(outItem);
        if (data.stats && data.stats.known_full_story_count !== undefined) this._addDisabled(this.menu, _("Storys gemerkt: ") + data.stats.known_full_story_count);
        if (data.errors && data.errors.length > 0) {
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addDisabled(this.menu, _("Hinweise:"));
            for (let i = 0; i < Math.min(data.errors.length, 4); i++) this._addDisabled(this.menu, data.errors[i]);
        }
    },

    _addReadStory: function(menu, data) {
        let stories = data.full_stories || [];
        if (stories.length === 0) { this._addDisabled(menu, _("Read Story – keine Full Story")); return; }
        if (stories.length === 1) {
            menu.addAction(_("Read Story"), Lang.bind(this, function() { this._openPath(stories[0].path); }));
            return;
        }
        let sub = new PopupMenu.PopupSubMenuMenuItem(_("Read Story"));
        menu.addMenuItem(sub);
        for (let i = 0; i < stories.length; i++) {
            let s = stories[i];
            sub.menu.addAction(s.label, Lang.bind(this, function() { this._openPath(s.path); }));
        }
    },

    _addReadPart: function(menu, data) {
        let parts = data.recent_parts || [];
        let sub = new PopupMenu.PopupSubMenuMenuItem(_("Read part"));
        menu.addMenuItem(sub);
        if (parts.length === 0) this._addDisabled(sub.menu, _("Keine Storyteile gefunden"));
        else for (let i = 0; i < parts.length; i++) this._addPartItem(sub.menu, parts[i].label, parts[i].path, parts[i].tooltip || "");
    },

    _addTts: function(menu, data) {
        let sub = new PopupMenu.PopupSubMenuMenuItem(_("TTS"));
        menu.addMenuItem(sub);
        sub.menu.addAction(_("Continue reading"), Lang.bind(this, function() { this._startTts("tts-continue"); }));
        sub.menu.addAction(_("Set"), Lang.bind(this, function() { this._startTts("tts-set"); }));
        if (this._isReading || (data.tts && data.tts.running)) {
            sub.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            sub.menu.addAction(_("Stop"), Lang.bind(this, function() { this._stopTts(); }));
        }
        if (data.tts && data.tts.last_file) {
            sub.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addDisabled(sub.menu, _("Letzte Datei:"));
            this._addDisabled(sub.menu, data.tts.last_file_label || data.tts.last_file);
        }
    },

    _addPartItem: function(menu, label, path, tooltip) {
        let item = new PopupMenu.PopupMenuItem(label);
        item.connect("activate", Lang.bind(this, function() { this._openPath(path); }));
        menu.addMenuItem(item);
        if (tooltip && tooltip.length > 0) {
            try { item._wpgTooltip = new Tooltips.Tooltip(item.actor, tooltip); } catch (e) {}
        }
    },

    _addOpenOrDisabled: function(menu, label, path) {
        if (path && path.length > 0) menu.addAction(label, Lang.bind(this, function() { this._openPath(path); }));
        else this._addDisabled(menu, label + _(" – nicht gefunden"));
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
        if (this._isReading) return;
        let args = this._helperBaseArgs(command);
        try {
            this._ttsProcess = Gio.Subprocess.new(args, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            this._setReading(true);
            this._ttsProcess.communicate_utf8_async(null, null, Lang.bind(this, function(proc, res) {
                let stdout = "";
                let stderr = "";
                try {
                    let result = proc.communicate_utf8_finish(res);
                    stdout = result[1] || "";
                    stderr = result[2] || "";
                } catch (e) { stderr = String(e); }
                this._ttsProcess = null;
                this._setReading(false);
                if (stderr) global.log("[" + UUID + "] TTS stderr: " + stderr);
                try {
                    let data = stdout ? JSON.parse(stdout) : null;
                    if (data && data.ok === false && this.notifyErrors) this._notify(_("TTS"), data.errors ? data.errors[0] : _("Vorlesen fehlgeschlagen"));
                } catch (e2) {}
                this._refreshScan(false);
            }));
        } catch (e) {
            this._ttsProcess = null;
            this._setReading(false);
            global.logError("[" + UUID + "] Could not start TTS: " + e);
            if (this.notifyErrors) this._notify(_("TTS"), String(e));
        }
    },

    _stopTts: function() {
        this._spawnJson(this._helperBaseArgs("tts-stop"), Lang.bind(this, function(data) {}));
        if (this._ttsProcess !== null) {
            try { this._ttsProcess.send_signal(15); }
            catch (e1) { try { this._ttsProcess.force_exit(); } catch (e2) {} }
        }
        this._setReading(false);
        if (this._ttsWaitId) Mainloop.source_remove(this._ttsWaitId);
        this._ttsWaitId = Mainloop.timeout_add_seconds(1, Lang.bind(this, function() {
            this._refreshScan(false);
            this._ttsWaitId = 0;
            return false;
        }));
    },

    _openAppletSettings: function() {
        Util.spawnCommandLine("cinnamon-settings applets " + UUID);
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
