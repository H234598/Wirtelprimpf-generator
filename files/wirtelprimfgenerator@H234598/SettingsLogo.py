#!/usr/bin/python3

import os
import json
import random
import subprocess
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import settings_sync
from JsonSettingsWidgets import SettingsWidget
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk


GENERATOR_IMAGE_CHOICES = {
    "atelier": "settings-generator-atelier.png",
    "machine": "settings-generator-machine.png",
}
ABOUT_IMAGE_CHOICES = {
    "story": "settings-about-story.png",
    "book": "settings-about-book.png",
}
def _choice_asset(choices, value, default_key):
    selected = (value or default_key).strip()
    return choices.get(selected, choices[default_key])


class _ResponsiveLogo(SettingsWidget):
    github_url = "https://github.com/H234598/Wirtelprimpf-generator"
    asset_name = ""
    top_margin = 10
    bottom_margin = 10
    max_height = 220

    def __init__(self, info, key, settings):
        SettingsWidget.__init__(self)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(0)
        self.set_margin_top(self.top_margin)
        self.set_margin_bottom(self.bottom_margin)
        self.set_hexpand(True)

        self._last_render_size = (0, 0)
        self._source_pixbuf = None
        self._scaled_pixbuf = None
        self._drawing_area = None
        self._base_dir = os.path.dirname(os.path.abspath(__file__))

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_halign(Gtk.Align.FILL)
        box.set_hexpand(True)
        box.set_tooltip_text("Wirtelprimpf-generator auf GitHub öffnen")

        try:
            self._source_pixbuf = self._load_source_pixbuf()
            self._drawing_area = Gtk.DrawingArea()
            self._drawing_area.set_halign(Gtk.Align.FILL)
            self._drawing_area.set_hexpand(True)
            self._drawing_area.set_size_request(1, 1)
            self._drawing_area.connect("draw", self._on_draw)
            box.pack_start(self._drawing_area, True, True, 0)
            box.connect("size-allocate", self._on_size_allocate)
            self._set_render_width(720)
        except Exception:
            self._drawing_area = None
            fallback = Gtk.Label(label=info.get("description", ""))
            fallback.set_halign(Gtk.Align.CENTER)
            box.pack_start(fallback, True, True, 0)

        event_box = Gtk.EventBox()
        event_box.set_visible_window(False)
        event_box.set_tooltip_text("Wirtelprimpf-generator auf GitHub öffnen")
        event_box.connect("button-press-event", self._open_project_repository)
        event_box.add(box)

        self.content_widget = event_box
        self.pack_start(event_box, True, True, 0)

    def _asset_path(self):
        return os.path.join(self._base_dir, "assets", self.asset_name)

    def _load_source_pixbuf(self):
        return GdkPixbuf.Pixbuf.new_from_file(self._asset_path())

    def _reload_source_pixbuf(self):
        if self._drawing_area is None:
            return
        try:
            self._source_pixbuf = self._load_source_pixbuf()
        except Exception:
            return
        self._scaled_pixbuf = None
        self._last_render_size = (0, 0)
        allocation = self._drawing_area.get_allocation()
        self._set_render_width(allocation.width or 720)
        self._drawing_area.queue_draw()

    def _open_project_repository(self, *_args):
        try:
            Gtk.show_uri_on_window(None, self.github_url, Gtk.get_current_event_time())
        except Exception:
            return False
        return True

    def _on_size_allocate(self, widget, allocation):
        self._set_render_width(allocation.width)

    def _fit_size_for_width(self, width):
        target_width = max(1, int(width))
        if self._source_pixbuf is None:
            return 1, 1
        source_width = max(1, self._source_pixbuf.get_width())
        source_height = max(1, self._source_pixbuf.get_height())
        target_height = max(1, int(round(target_width * source_height / source_width)))
        if self.max_height and target_height > self.max_height:
            scale = float(self.max_height) / float(target_height)
            target_height = self.max_height
            target_width = max(1, int(round(target_width * scale)))
        return target_width, target_height

    def _set_render_width(self, width):
        if self._source_pixbuf is None or self._drawing_area is None:
            return
        target_width, target_height = self._fit_size_for_width(width)
        current = (target_width, target_height)
        if current == self._last_render_size and self._scaled_pixbuf is not None:
            return
        self._last_render_size = current
        self._scaled_pixbuf = self._source_pixbuf.scale_simple(
            target_width,
            target_height,
            GdkPixbuf.InterpType.BILINEAR,
        )
        self._drawing_area.set_size_request(1, target_height)
        self._drawing_area.queue_draw()

    def _on_draw(self, widget, cr):
        if self._source_pixbuf is None:
            return False
        allocation = widget.get_allocation()
        self._set_render_width(allocation.width)
        if self._scaled_pixbuf is None:
            return False
        x_offset = max(0, int((allocation.width - self._scaled_pixbuf.get_width()) / 2))
        y_offset = max(0, int((allocation.height - self._scaled_pixbuf.get_height()) / 2))
        Gdk.cairo_set_source_pixbuf(cr, self._scaled_pixbuf, x_offset, y_offset)
        cr.paint()
        return False


class HeaderLogo(_ResponsiveLogo):
    asset_name = "settings-header-logo.png"
    top_margin = 0
    bottom_margin = 18
    max_height = 220


class FooterLogo(_ResponsiveLogo):
    asset_name = "settings-footer-logo.png"
    top_margin = 18
    bottom_margin = 0
    max_height = 110


class _ConfigurableImage(_ResponsiveLogo):
    setting_key = ""
    default_key = ""
    choices = {}
    top_margin = 8
    bottom_margin = 16
    max_height = 170

    def __init__(self, info, key, settings):
        self.settings = settings
        self.asset_name = _choice_asset(self.choices, settings.get_value(self.setting_key), self.default_key)
        _ResponsiveLogo.__init__(self, info, key, settings)
        settings.listen(self.setting_key, self._on_choice_changed)

    def _on_choice_changed(self, _key, value):
        self.asset_name = _choice_asset(self.choices, value, self.default_key)
        self._reload_source_pixbuf()


class GeneratorImage(_ConfigurableImage):
    setting_key = "generator-image-choice"
    default_key = "atelier"
    choices = GENERATOR_IMAGE_CHOICES


class AboutImage(_ConfigurableImage):
    setting_key = "about-image-choice"
    default_key = "story"
    choices = ABOUT_IMAGE_CHOICES


class AboutWirtelprimpf(SettingsWidget):
    repo_url = "https://github.com/H234598/Wirtelprimpf-generator"

    def __init__(self, info, key, settings):
        SettingsWidget.__init__(self)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(10)
        self.set_margin_start(18)
        self.set_margin_end(18)
        self.set_margin_top(12)
        self.set_margin_bottom(18)
        self.set_hexpand(True)

        metadata = self._read_metadata()
        name = metadata.get("name", "Wirtelprimfgenerator Story Menu")
        version = metadata.get("version", "")
        author = metadata.get("author", "H234598")
        description = metadata.get(
            "description",
            "Cinnamon applet for Wirtelprimpf images, stories and TTS.",
        )

        title = Gtk.Label()
        title.set_markup("<big><b>%s</b></big>" % GLib.markup_escape_text(name))
        title.set_halign(Gtk.Align.START)
        self.pack_start(title, False, True, 0)

        subtitle = Gtk.Label(label="Version %s - %s" % (version, author))
        subtitle.set_halign(Gtk.Align.START)
        self.pack_start(subtitle, False, True, 0)

        body = Gtk.Label(
            label=(
                "%s\n\n"
                "Dieses Applet haelt den Wirtelprimpf-Arbeitsfluss erreichbar: "
                "aktuelle Bilder, Storyteile, Full-Story, Vorlesen, Piper-Stimmen "
                "und Generator-/systemd-Steuerung liegen an einem Ort.\n\n"
                "Die Applet-Einstellungen schreiben bewusst in die echten lokalen "
                "Wirtelprimpf-Konfigurationsflaechen. API-Key, Outputpfade, Modelle, "
                "Storymodus, Bildmodus, Watcher-Werte und Timer bleiben damit nicht "
                "neben dem System stehen, sondern steuern den laufenden Generator."
            )
            % description
        )
        body.set_halign(Gtk.Align.START)
        body.set_justify(Gtk.Justification.LEFT)
        body.set_line_wrap(True)
        body.set_selectable(True)
        self.pack_start(body, False, True, 0)

        bullets = Gtk.Label(
            label=(
                "Kurzfassung:\n"
                "- Menue zeigt Latest, Full Story und die letzten Storyteile.\n"
                "- TTS kann ueber Auto, Piper, Speech Dispatcher, eSpeak oder Custom laufen.\n"
                "- Der Generator-Tab steuert openai.env und systemd-User-Units.\n"
                "- Die Wirtelgedichte wechseln zufaellig beim Oeffnen der Einstellungen."
            )
        )
        bullets.set_halign(Gtk.Align.START)
        bullets.set_justify(Gtk.Justification.LEFT)
        bullets.set_line_wrap(True)
        bullets.set_selectable(True)
        self.pack_start(bullets, False, True, 0)

        link = Gtk.LinkButton.new_with_label(self.repo_url, "GitHub: H234598/Wirtelprimpf-generator")
        link.set_halign(Gtk.Align.START)
        self.pack_start(link, False, True, 0)

        self.content_widget = body

    def _read_metadata(self):
        metadata_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metadata.json")
        try:
            with open(metadata_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {}


class WirtelPoem(SettingsWidget):
    poems = (
        (
            "Im kleinen Kreis der Stunden steht ein Name,\n"
            "hell wie ein Fenster ueber schlafendem Code.\n"
            "Ein Bild atmet, eine Geschichte hebt den Blick,\n"
            "und Wirtelprimpf ordnet die Funken zu Sinn.\n"
            "Wer liest, tritt leise in die Maschine ein;\n"
            "wer hoert, findet Waerme im Takt der Datei."
        ),
        (
            "Wo Pfade schweigen, legt ein Bild die Stirn ans Licht,\n"
            "und jede Stunde faltet ihre kleine Karte.\n"
            "Wirtelprimpf zaehlt nicht nur Dateien,\n"
            "er merkt sich das Zucken der Moeglichkeit.\n"
            "Aus Pixel, Satz und leiser Ordnung\n"
            "wird eine Tuer, die beim Lesen aufgeht."
        ),
        (
            "Ein Prompt ist nur ein Stein im Wasser,\n"
            "doch Kreise koennen denken lernen.\n"
            "Zwischen Mohnrot, Log und Sternenstaub\n"
            "tritt Wirtelprimpf mit ruhiger Hand.\n"
            "Er hebt das Bild nicht aus dem Nichts,\n"
            "sondern aus dem Mut, genau hinzusehen."
        ),
        (
            "Die Stunde kommt in weichen Schuhen,\n"
            "bringt eine Datei und geht nicht gleich.\n"
            "Wirtelprimpf liest ihr den Rand der Welt,\n"
            "wo Katzen, Regeln, Licht sich treffen.\n"
            "Was eben noch Verzeichnis war,\n"
            "wird ploetzlich Atem, Szene, Spur."
        ),
        (
            "Im Speicher liegt kein kalter Vorrat,\n"
            "sondern ein Garten aus Entscheidungen.\n"
            "Wirtelprimpf geht zwischen den Beeten,\n"
            "waehlt nicht das Laute, sondern das Wahre.\n"
            "Und wenn ein Bild sich selbst erkennt,\n"
            "nickt die Geschichte wie ein heller Baum."
        ),
        (
            "Der Zufall ist kein schlechter Meister,\n"
            "wenn er an eine kluge Tuer klopft.\n"
            "Wirtelprimpf oeffnet, prueft den Wind,\n"
            "und laesst nur jene Funken ein,\n"
            "die aus der Ordnung Freude machen\n"
            "und aus dem Bild ein leises Denken."
        ),
        (
            "Kein Menue erklaert die Nacht vollstaendig,\n"
            "kein Schalter misst den Zauber aus.\n"
            "Doch Wirtelprimpf stellt seine Lampe\n"
            "genau dort hin, wo Wege kreuzen.\n"
            "Dann sieht man: selbst ein Arbeitsordner\n"
            "kann einen Horizont besitzen."
        ),
        (
            "Wenn Stimmen durch den Text spazieren,\n"
            "traegt jede Silbe eine kleine Uhr.\n"
            "Wirtelprimpf lauscht, bis aus Sekunden\n"
            "eine Form von Gegenwart entsteht.\n"
            "Und was der Rechner trocken fand,\n"
            "bekommt im Klang ein menschlich Dach."
        ),
        (
            "Es gibt ein Licht fuer neue Bilder,\n"
            "das nicht befiehlt und nicht erklaert.\n"
            "Wirtelprimpf haelt es in der Schwebe,\n"
            "bis eine Szene Antwort gibt.\n"
            "Dann schreibt die Stunde ihren Namen\n"
            "in eine Datei aus Staub und Glanz."
        ),
        (
            "Zwischen Zufall und Gewohnheit\n"
            "liegt ein schmaler, kluger Steg.\n"
            "Wirtelprimpf geht ihn ohne Eile,\n"
            "mit Bild im Arm und Satz im Blick.\n"
            "So wird aus Wiederholung Rhythmus,\n"
            "aus Rhythmus eine kleine Welt."
        ),
        (
            "Nicht jede Regel ist ein Kaefig,\n"
            "nicht jeder Traum ist schwerelos.\n"
            "Wirtelprimpf spannt feine Faeden\n"
            "zwischen Auftrag und Erstaunen.\n"
            "Dort haengt das Bild, wach und gelassen,\n"
            "und wartet, bis die Geschichte spricht."
        ),
        (
            "Der Timer spricht: Nun sei es Zeit,\n"
            "die Stunde steht im Festtagskleid.\n"
            "Wirtelprimpf nickt, der Prompt wird rund,\n"
            "und lacht den trocknen Cron gesund."
        ),
        (
            "Ein Bit fiel tief ins Morgenrot,\n"
            "der Log vermerkte: halbwegs tot.\n"
            "Doch Wirtelprimpf, mit feinem Sinn,\n"
            "schrieb trotzdem noch ein Bildchen hin."
        ),
        (
            "Die Regel kam im Stahlhelm an,\n"
            "und fragte streng: Was darf ich dann?\n"
            "Der Zufall sprach: Sei nicht so hart,\n"
            "wir reisen heute Gegenwart."
        ),
        (
            "Im Prompt sass eine kluge List,\n"
            "die wusste, was zu fade ist.\n"
            "Sie bog den Satz mit leisem Schwung,\n"
            "und ploetzlich roch die Seite jung."
        ),
        (
            "Ein Bild erstand aus Rand und Ruh,\n"
            "der Text zog seine Schuhe zu.\n"
            "Dann gingen beide, sehr apart,\n"
            "durch Unsinn mit Verstand gepaart."
        ),
        (
            "Der Pfad war lang, der Cache war leer,\n"
            "die Nacht tat informatisch schwer.\n"
            "Da sprach der Dienst mit sanftem Hohn:\n"
            "Ich starte, denn ich wohn hier schon."
        ),
        (
            "Ein Service lag im Userraum,\n"
            "und traeumte seinen Rootlos-Traum.\n"
            "Er starb kurz weg, ganz ohne Schmerz,\n"
            "systemd schrieb es sich ans Herz."
        ),
        (
            "Die Stunde sass im Warteflur,\n"
            "und kaute still auf der Zensur.\n"
            "Wirtelprimpf trat elegant vorbei,\n"
            "mit Bild, Idee und Spott dabei."
        ),
        (
            "Wenn Schwarz sich sanft zum Witze neigt,\n"
            "und keiner gleich den Zeiger zeigt,\n"
            "dann darf ein Satz am Abgrund stehn,\n"
            "und trotzdem sauber weitergehn."
        ),
        (
            "Ein Prompt, der nur Befehle kennt,\n"
            "ist wie ein Ofen, der nicht brennt.\n"
            "Gib ihm ein Ziel, doch lass ihm Raum,\n"
            "dann baut er mehr als Tabellen-Schaum."
        ),
        (
            "Die erste Seite braucht Gewicht,\n"
            "sonst glaubt ihr selbst der Zufall nicht.\n"
            "Drum tritt sie ein mit hellem Klang,\n"
            "und nimmt die Langweil gleich gefang."
        ),
        (
            "Im Arbeitsordner, frisch sortiert,\n"
            "hat Sinn die Schuhe poliert.\n"
            "Der Link zeigt hin, die Story wacht,\n"
            "und laechelt kurz: Ich bin gemacht."
        ),
        (
            "Ein Bild sah seinen Namen stehn,\n"
            "und wollte nicht nach Schema gehn.\n"
            "Es nahm die Regel, bog sie klein,\n"
            "und liess noch etwas Seele rein."
        ),
        (
            "Der Zufall ist ein feiner Koch,\n"
            "doch Salz allein ertraegt man doch.\n"
            "Er braucht Idee, Gefahr und Scherz,\n"
            "sonst schmeckt der Plot nach Aktenherz."
        ),
        (
            "Die Technik nickt, die Kunst sagt: Halt,\n"
            "so wirst du nur verwaltet alt.\n"
            "Wirtelprimpf mischt beides schlau,\n"
            "und macht aus Grau ein tieferes Blau."
        ),
        (
            "Ein Satz, der nur Kulissen schiebt,\n"
            "hat nie gewusst, was Lesen liebt.\n"
            "Drum kriegt er heute keinen Lohn,\n"
            "und wandert in die Revision."
        ),
        (
            "Der Tod stand kurz im Nebensatz,\n"
            "doch fand dort keinen rechten Platz.\n"
            "Er blieb als Pointe, knapp und fein,\n"
            "und durfte nicht der Inhalt sein."
        ),
        (
            "Wenn Witz und Wunde sich begegnen,\n"
            "muss keiner gleich den Text enteignen.\n"
            "Ein kluger Ton, ein schiefer Blick,\n"
            "und Ernst bekommt sein Echo zurueck."
        ),
        (
            "Der Prompt trug stolz sein Regelhemd,\n"
            "doch wirkte darin leicht verklemmt.\n"
            "Da schnitt der Zufall eine Naht,\n"
            "und ploetzlich klang der Apparat."
        ),
        (
            "Ein Titel schlief im letzten Teil,\n"
            "noch namenlos, doch nicht sehr heil.\n"
            "Als Schluss und Sinn sich endlich trafen,\n"
            "stand er dort, um aufzuwachen."
        ),
        (
            "Der Log war duenn, der Fehler breit,\n"
            "die Ausrede trug Abendkleid.\n"
            "Wirtelprimpf las, verwarf den Tand,\n"
            "und schrieb den Grund mit ruhiger Hand."
        ),
        (
            "Ein Dropdown waehlt, ein Schalter denkt,\n"
            "ein Timer wird zurechtgelenkt.\n"
            "So fuegt sich, was im System geschieht,\n"
            "zu einem fast anmutigen Lied."
        ),
        (
            "Die Stimme klang wie Blech im Wind,\n"
            "als haette Klang ein krankes Kind.\n"
            "Dann kam ein Modell mit besserem Ton,\n"
            "und rettete die Lesefunktion."
        ),
        (
            "Nicht jede Pointe muss beissen,\n"
            "doch darf sie kurz am Abgrund gleissen.\n"
            "Wer klug lacht, lacht nicht blind,\n"
            "sondern weiss, wo Narben sind."
        ),
        (
            "Die Datei, sie mochte Klarheit sehr,\n"
            "doch Klarheit ohne Traum bleibt leer.\n"
            "Drum legt der Text, ganz ungeniert,\n"
            "ein Raetsel hin, das funktioniert."
        ),
        (
            "Ein Commit ging bei Nacht hinaus,\n"
            "mit ernster Stirn und kleinem Applaus.\n"
            "Der Push kam nach, der Dienst erwacht,\n"
            "und alles wirkte fast durchdacht."
        ),
        (
            "Wenn Einstellungen alles koennen,\n"
            "muss Kunst sich nicht in Listen sonnen.\n"
            "Sie nutzt die Knopfe, bleibt doch frei,\n"
            "und schreibt am Rand Magie vorbei."
        ),
        (
            "Der alte Satz vom grauen Dreh\n"
            "tat jeder ersten Seite weh.\n"
            "Nun tritt ein Blick mit Laune ein,\n"
            "und laesst den Plot gefaehrlich sein."
        ),
        (
            "Ein Backup roch nach altem Staub,\n"
            "der Fehler war erstaunlich taub.\n"
            "Doch wer beim Lesen sauber misst,\n"
            "merkt frueh, wo Unsinn heimisch ist."
        ),
        (
            "Der Schluss ist selten wirklich Schluss,\n"
            "wenn Zufall weiter atmen muss.\n"
            "Wirtelprimpf macht die Tuer nur klein,\n"
            "damit noch Licht hindurch kann sein."
        ),
    )

    def __init__(self, info, key, settings):
        SettingsWidget.__init__(self)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_margin_top(8)
        self.set_margin_bottom(16)
        self.set_hexpand(True)

        label = Gtk.Label(label=random.choice(self.poems))
        label.set_halign(Gtk.Align.CENTER)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_line_wrap(True)
        label.set_selectable(False)
        label.set_margin_start(20)
        label.set_margin_end(20)

        self.content_widget = label
        self.pack_start(label, True, True, 0)


class PiperModelChooser(SettingsWidget):
    voice_dir = os.path.expanduser("~/.local/share/piper/voices")
    voices = (
        (
            "Thorsten medium",
            "de_DE-thorsten-medium.onnx",
            "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten-medium.onnx",
            "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten-medium.onnx.json",
        ),
        (
            "Thorsten high",
            "de_DE-thorsten-high.onnx",
            "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten-high.onnx",
            "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten-high.onnx.json",
        ),
        (
            "Thorsten emotional",
            "de_DE-thorsten_emotional-medium.onnx",
            "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten_emotional-medium.onnx",
            "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten_emotional-medium.onnx.json",
        ),
    )

    def __init__(self, info, key, settings):
        SettingsWidget.__init__(self)
        self.key = info.get("target", key)
        self.settings = settings
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(4)
        self.set_hexpand(True)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_hexpand(True)

        label = Gtk.Label(label=info.get("description", "Piper-Stimmenmodell"))
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        row.pack_start(label, True, True, 0)

        self.status = Gtk.Label(label="")
        self.status.set_halign(Gtk.Align.START)

        download_button = Gtk.MenuButton()
        download_button.set_label("Download")
        download_button.set_tooltip_text("Piper-Stimmenmodell herunterladen")
        download_button.set_popup(self._build_download_menu())
        row.pack_start(download_button, False, False, 0)
        self.download_button = download_button

        chooser = Gtk.FileChooserButton(
            title="Piper-Stimmenmodell waehlen",
            action=Gtk.FileChooserAction.OPEN,
        )
        chooser.set_hexpand(True)
        chooser.set_tooltip_text(info.get("tooltip", ""))
        model_filter = Gtk.FileFilter()
        model_filter.set_name("Piper ONNX (*.onnx)")
        model_filter.add_pattern("*.onnx")
        chooser.add_filter(model_filter)
        chooser.connect("file-set", self._on_file_set)
        row.pack_start(chooser, True, True, 0)
        self.chooser = chooser

        self.pack_start(row, False, True, 0)
        self.pack_start(self.status, False, True, 0)
        self.content_widget = row

        self._set_chooser_filename(settings.get_value(self.key))
        settings.listen(self.key, self._on_setting_changed)

    def _build_download_menu(self):
        menu = Gtk.Menu()
        for label, filename, model_url, config_url in self.voices:
            item = Gtk.MenuItem(label=label)
            item.connect("activate", self._download_voice, filename, model_url, config_url)
            menu.append(item)
        menu.append(Gtk.SeparatorMenuItem())
        folder_item = Gtk.MenuItem(label="Stimmenordner oeffnen")
        folder_item.connect("activate", self._open_uri, "file://" + os.path.abspath(os.path.expanduser(self.voice_dir)))
        menu.append(folder_item)
        project_item = Gtk.MenuItem(label="Thorsten-Voice/Piper oeffnen")
        project_item.connect("activate", self._open_uri, "https://huggingface.co/Thorsten-Voice/Piper/tree/main")
        menu.append(project_item)
        menu.show_all()
        return menu

    def _open_uri(self, _item, uri):
        try:
            Gtk.show_uri_on_window(None, uri, Gtk.get_current_event_time())
        except Exception as exc:
            self._set_status("Oeffnen fehlgeschlagen: %s" % exc)

    def _on_setting_changed(self, _key, value):
        self._set_chooser_filename(value)

    def _on_file_set(self, chooser):
        filename = chooser.get_filename()
        if filename:
            self.settings.set_value(self.key, filename)
            self._set_status("")

    def _set_chooser_filename(self, filename):
        if filename and os.path.exists(filename):
            self.chooser.set_filename(filename)

    def _download_voice(self, _item, filename, model_url, config_url):
        self.download_button.set_sensitive(False)
        self._set_status("Download laeuft...")
        thread = threading.Thread(
            target=self._download_voice_worker,
            args=(filename, model_url, config_url),
            daemon=True,
        )
        thread.start()

    def _download_voice_worker(self, filename, model_url, config_url):
        try:
            os.makedirs(self.voice_dir, exist_ok=True)
            model_path = os.path.join(self.voice_dir, filename)
            config_path = model_path + ".json"
            self._download_url(model_url, model_path)
            self._download_url(config_url, config_path)
            GLib.idle_add(self._download_finished, model_path, None)
        except Exception as exc:
            GLib.idle_add(self._download_finished, "", str(exc))

    def _download_url(self, url, target):
        tmp = target + ".tmp"
        urllib.request.urlretrieve(url, tmp)
        os.replace(tmp, target)

    def _download_finished(self, model_path, error):
        self.download_button.set_sensitive(True)
        if error:
            self._set_status("Download fehlgeschlagen: %s" % error)
            return False
        self.settings.set_value(self.key, model_path)
        self._set_chooser_filename(model_path)
        self._set_status("Gespeichert: %s" % model_path)
        return False

    def _set_status(self, text):
        self.status.set_text(text)


class _GLibScheduler:
    def call_later(self, milliseconds, callback):
        return GLib.timeout_add(milliseconds, callback)

    def call_repeated(self, seconds, callback):
        return GLib.timeout_add_seconds(seconds, callback)

    def cancel(self, handle):
        try:
            GLib.source_remove(handle)
        except Exception:
            return


class _GioMonitorFactory:
    def __call__(self, target, callback):
        normalized_target = os.path.normpath(os.path.abspath(target))
        parent = Gio.File.new_for_path(os.path.dirname(normalized_target))
        monitor = parent.monitor_directory(Gio.FileMonitorFlags.NONE, None)

        def changed(_monitor, changed_file, other_file, _event_type):
            for candidate in (changed_file, other_file):
                if candidate is None:
                    continue
                candidate_path = candidate.get_path()
                if candidate_path and os.path.normpath(os.path.abspath(candidate_path)) == normalized_target:
                    callback(normalized_target)
                    break

        monitor.connect("changed", changed)
        return monitor


class GeneratorConfigEditor(SettingsWidget):
    settings_cli_path = os.path.expanduser(
        "~/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-settings"
    )
    env_path = os.path.expanduser("~/.config/wirtelprimpf/openai.env")
    timer_dropin_path = os.path.expanduser(
        "~/.config/systemd/user/wirtelprimpf.timer.d/override.conf"
    )
    revision_state_path = os.path.expanduser(
        "~/.config/wirtelprimpf/settings-state.json"
    )

    field_sections = (
        (
            "Generierung",
            (
                ("operandi", "Modus", "choice", "operandi"),
                ("image_model", "Bildmodell", "model", "image_model"),
                ("story_model", "Storymodell", "model", "story_model"),
                ("image_size", "Bildgröße", "choice", "image_size"),
                ("output_resolution", "Ausgabe-Auflösung", "choice", "output_resolution"),
                (
                    "generation_interval_minutes",
                    "Generator-Intervall (Minuten)",
                    "integer",
                    None,
                ),
                ("publish_immediately", "Sofort publizieren", "boolean", None),
                ("story_finish_parts_min", "Finish-Teile min", "integer", None),
                ("story_finish_parts_max", "Finish-Teile max", "integer", None),
            ),
        ),
        (
            "Archive und Publikation",
            (
                ("local_outdir", "Lokaler Output", "string", None),
                ("working_dir", "Working-Verzeichnis", "string", None),
                ("repo_path", "Git-Repo-Pfad", "string", None),
                ("repo_slug", "GitHub Repo-Slug", "string", None),
                ("repo_subdir", "Repo-Unterordner", "string", None),
                ("repo_branch", "Repo-Branch", "string", None),
                ("github_owner", "GitHub Eigentümer", "string", None),
                ("media_mode", "Medienpublikation", "choice", "media_mode"),
                ("media_staging", "Release-Staging", "string", None),
                ("platform_state", "Plattformstatus", "string", None),
                ("hub_dispatch_state", "Hub-Outbox", "string", None),
                ("generator_root", "Generator-Checkout", "string", None),
                ("archive_root", "Archivwurzel", "string", None),
                ("platform_catalog", "Publikationskatalog", "string", None),
            ),
        ),
        (
            "Laufzeit und Regeln",
            (
                ("settings_path", "Private Einstellungen", "string", None),
                ("cloudflare_zone", "Cloudflare-Zone", "string", None),
                ("cloudflare_zone_id", "Cloudflare-Zonen-ID", "string", None),
                ("git_author_name", "Git Autor Name", "string", None),
                ("git_author_email", "Git Autor Mail", "string", None),
                ("flex_processing", "Flex Processing", "choice", "flex_processing"),
                ("prompt_config", "Bildregeln", "string", None),
                ("story_prompt_config", "Storyregeln", "string", None),
                ("story_document", "Story-Dokument", "string", None),
                ("story_state", "Story-Status", "string", None),
                ("story_finish", "Story abschließen", "boolean", None),
            ),
        ),
        (
            "systemd User-Timer",
            (
                ("timer_enabled", "Generator-Timer aktiv", "boolean", None),
                (
                    "timer_randomized_delay_seconds",
                    "RandomizedDelaySec",
                    "integer",
                    None,
                ),
                ("timer_persistent", "Persistent", "boolean", None),
            ),
        ),
    )

    integer_ranges = {  # noqa: RUF012 - immutable class-level schema contract
        "generation_interval_minutes": (30, 10080),
        "story_finish_parts_min": (1, 12),
        "story_finish_parts_max": (1, 12),
        "timer_randomized_delay_seconds": (0, 86400),
    }

    secret_specs = (
        ("openai_api_key", "OpenAI API Key", "openai_api_key_present"),
        (
            "cloudflare_api_token",
            "Cloudflare API Token",
            "cloudflare_api_token_present",
        ),
    )

    def __init__(self, info, key, settings):
        SettingsWidget.__init__(self)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(8)
        self.set_hexpand(True)
        self.set_vexpand(True)

        self.widgets = {}
        self.field_state_labels = {}
        self.field_discard_buttons = {}
        self.secret_entries = {}
        self.secret_delete_checks = {}
        self.secret_presence_labels = {}
        self.secret_state_labels = {}
        self.secret_discard_buttons = {}
        self.sync_state = None
        self.sync_coordinator = None
        self.settings_client = None
        self._suppress_dirty = False
        self._save_busy = False
        self._operation_busy = False
        self._disposed = False
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="wirtel-settings",
        )

        self.status = Gtk.Label(label="Lade transaktionale Einstellungen …")
        self.status.set_halign(Gtk.Align.START)
        self.status.set_line_wrap(True)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_height(520)
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)

        self.settings_content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
        )
        self.settings_content.set_margin_start(8)
        self.settings_content.set_margin_end(8)
        self.settings_content.set_margin_top(8)
        self.settings_content.set_margin_bottom(8)
        scroller.add(self.settings_content)

        self.loading_label = Gtk.Label(label="Einstellungen werden sicher geladen …")
        self.loading_label.set_halign(Gtk.Align.START)
        self.settings_content.pack_start(self.loading_label, False, True, 0)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.START)

        self.save_button = Gtk.Button(label="Speichern")
        self.save_button.set_sensitive(False)
        self.save_button.connect("clicked", self._on_save)

        self.discard_all_button = Gtk.Button(label="Alle lokalen Entwürfe verwerfen")
        self.discard_all_button.set_sensitive(False)
        self.discard_all_button.connect("clicked", self._on_discard_all)

        self.run_button = Gtk.Button(label="Generator jetzt starten")
        self.run_button.connect("clicked", self._on_start_generator)

        self.timer_button = Gtk.Button(label="Timer neu starten")
        self.timer_button.connect("clicked", self._on_restart_timers)

        for button in (
            self.save_button,
            self.discard_all_button,
            self.run_button,
            self.timer_button,
        ):
            buttons.pack_start(button, False, False, 0)

        self.pack_start(scroller, True, True, 0)
        self.pack_start(buttons, False, True, 0)
        self.pack_start(self.status, False, True, 0)
        self.content_widget = scroller

        self.connect("map", self._on_map)
        self.connect("focus-in-event", self._on_focus_in)
        self.connect("destroy", self._dispose_sync)

        try:
            self.settings_client = settings_sync.SettingsCliClient(
                self.settings_cli_path
            )
            self.sync_coordinator = settings_sync.SettingsSyncCoordinator(
                client=self.settings_client,
                scheduler=_GLibScheduler(),
                monitor_factory=_GioMonitorFactory(),
                executor=self._executor,
                completion_dispatch=self._dispatch_completion,
                on_snapshot=self._on_snapshot,
                on_error=self._on_sync_error,
                on_busy=self._on_sync_busy,
                on_save_result=self._on_save_result,
            )
            self.sync_coordinator.start(
                (
                    self.env_path,
                    self.timer_dropin_path,
                    self.revision_state_path,
                )
            )
        except Exception as exc:
            if self.sync_coordinator is not None:
                self.sync_coordinator.dispose()
            else:
                self._executor.shutdown(wait=False, cancel_futures=True)
            self._set_status(
                f"Transaktionale Einstellungen sind nicht verfügbar: {exc}"
            )

    def _dispatch_completion(self, callback, *args):
        return GLib.idle_add(callback, *args)

    def _section_label(self, text):
        label = Gtk.Label()
        label.set_markup("<b>%s</b>" % GLib.markup_escape_text(text))
        label.set_halign(Gtk.Align.START)
        label.set_margin_top(8)
        return label

    def _make_field_row(self, key, label_text, widget):
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        row.set_hexpand(True)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        controls.set_hexpand(True)
        label = Gtk.Label(label=label_text)
        label.set_halign(Gtk.Align.START)
        label.set_size_request(230, -1)
        controls.pack_start(label, False, False, 0)
        controls.pack_start(widget, True, True, 0)
        row.pack_start(controls, False, True, 0)

        state_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        state_row.set_margin_start(240)
        state_label = Gtk.Label(label="")
        state_label.set_halign(Gtk.Align.START)
        discard = Gtk.Button(label="Externen Wert übernehmen")
        discard.set_no_show_all(True)
        discard.set_visible(False)
        discard.connect("clicked", self._on_discard_field, key)
        state_row.pack_start(state_label, False, True, 0)
        state_row.pack_start(discard, False, False, 0)
        row.pack_start(state_row, False, True, 0)

        self.field_state_labels[key] = state_label
        self.field_discard_buttons[key] = discard
        return row

    def _make_secret_row(self, key, label_text):
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        label = Gtk.Label(label=label_text)
        label.set_halign(Gtk.Align.START)
        label.set_size_request(230, -1)

        secret_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        entry = Gtk.Entry()
        entry.set_hexpand(True)
        entry.set_visibility(False)
        entry.set_invisible_char("*")
        entry.set_placeholder_text("Leer lassen = vorhandenen Wert beibehalten")
        deletion = Gtk.CheckButton(label="Vorhandenen Wert löschen")
        presence = Gtk.Label(label="Vorhandener Wert: unbekannt")
        presence.set_halign(Gtk.Align.START)

        secret_box.pack_start(entry, False, True, 0)
        secret_box.pack_start(deletion, False, True, 0)
        secret_box.pack_start(presence, False, True, 0)
        controls.pack_start(label, False, False, 0)
        controls.pack_start(secret_box, True, True, 0)
        row.pack_start(controls, False, True, 0)

        state_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        state_row.set_margin_start(240)
        state_label = Gtk.Label(label="")
        state_label.set_halign(Gtk.Align.START)
        discard = Gtk.Button(label="Externen Wert übernehmen")
        discard.set_no_show_all(True)
        discard.set_visible(False)
        discard.connect("clicked", self._on_discard_secret, key)
        state_row.pack_start(state_label, False, True, 0)
        state_row.pack_start(discard, False, False, 0)
        row.pack_start(state_row, False, True, 0)

        entry.connect("changed", self._on_secret_changed, key)
        deletion.connect("toggled", self._on_secret_changed, key)
        self.secret_entries[key] = entry
        self.secret_delete_checks[key] = deletion
        self.secret_presence_labels[key] = presence
        self.secret_state_labels[key] = state_label
        self.secret_discard_buttons[key] = discard
        return row

    def _make_value_widget(self, key, kind, choices, current):
        if kind in ("choice", "model"):
            if kind == "model":
                return self._make_catalog_combo(choices, current)
            combo = Gtk.ComboBoxText()
            for option in choices:
                combo.append(str(option), str(option))
            combo.set_hexpand(True)
            return combo
        if kind == "boolean":
            switch = Gtk.Switch()
            switch.set_halign(Gtk.Align.START)
            return switch
        if kind == "integer":
            minimum, maximum = self.integer_ranges[key]
            spin = Gtk.SpinButton.new_with_range(minimum, maximum, 1)
            spin.set_numeric(True)
            spin.set_hexpand(True)
            return spin
        entry = Gtk.Entry()
        entry.set_hexpand(True)
        return entry

    def _make_catalog_combo(self, choices, current):
        combo = Gtk.ComboBoxText()
        combo.set_hexpand(True)
        self._populate_catalog_combo(combo, choices, current)
        return combo

    def _populate_catalog_combo(self, combo, choices, current):
        combo.remove_all()
        for value, label, _legacy in settings_sync.catalog_options(choices, current):
            combo.append(value, label)

    def _build_fields(self, payload, visible):
        self.loading_label.set_visible(False)
        choices_payload = payload.get("choices", {})
        if not isinstance(choices_payload, dict):
            choices_payload = {}

        for section, fields in self.field_sections:
            self.settings_content.pack_start(
                self._section_label(section),
                False,
                True,
                0,
            )
            for key, label, kind, choice_key in fields:
                choices = choices_payload.get(choice_key, []) if choice_key else []
                current = visible.get(key)
                widget = self._make_value_widget(key, kind, choices, current)
                self._set_widget_public_value(widget, current)
                self.widgets[key] = widget
                self.settings_content.pack_start(
                    self._make_field_row(key, label, widget),
                    False,
                    True,
                    0,
                )

        self.settings_content.pack_start(
            self._section_label("Schreibgeschützte Secrets"),
            False,
            True,
            0,
        )
        for key, label, _presence_key in self.secret_specs:
            self.settings_content.pack_start(
                self._make_secret_row(key, label),
                False,
                True,
                0,
            )

        for key, widget in self.widgets.items():
            if isinstance(widget, Gtk.Switch):
                widget.connect("notify::active", self._on_widget_changed, key)
            elif isinstance(widget, Gtk.SpinButton):
                widget.connect("value-changed", self._on_widget_changed, key)
            else:
                widget.connect("changed", self._on_widget_changed, key)

        self.settings_content.show_all()
        for button in self.field_discard_buttons.values():
            button.set_visible(False)
        for button in self.secret_discard_buttons.values():
            button.set_visible(False)

    def _set_widget_public_value(self, widget, value):
        if isinstance(widget, Gtk.ComboBoxText):
            widget.set_active_id("" if value is None else str(value))
        elif isinstance(widget, Gtk.Switch):
            widget.set_active(bool(value))
        elif isinstance(widget, Gtk.SpinButton):
            widget.set_value(int(value or 0))
        else:
            widget.set_text("" if value is None else str(value))

    def _widget_public_value(self, widget):
        if isinstance(widget, Gtk.ComboBoxText):
            return widget.get_active_id() or ""
        if isinstance(widget, Gtk.Switch):
            return bool(widget.get_active())
        if isinstance(widget, Gtk.SpinButton):
            return int(widget.get_value())
        return widget.get_text()

    def _apply_visible_values(self, payload, visible):
        choices_payload = payload.get("choices", {})
        if not isinstance(choices_payload, dict):
            choices_payload = {}
        self._suppress_dirty = True
        try:
            for key in ("image_model", "story_model"):
                widget = self.widgets.get(key)
                if widget is not None:
                    self._populate_catalog_combo(
                        widget,
                        choices_payload.get(key, []),
                        visible.get(key),
                    )
            for key, widget in self.widgets.items():
                self._set_widget_public_value(widget, visible.get(key))
        finally:
            self._suppress_dirty = False

    def _on_widget_changed(self, widget, *args):
        key = args[-1]
        if (
            self._suppress_dirty
            or self._save_busy
            or self.sync_coordinator is None
            or self.sync_coordinator.state is None
        ):
            return
        self.sync_coordinator.state.change(
            key,
            self._widget_public_value(widget),
        )
        self.sync_state = self.sync_coordinator.state
        self._render_field_states()

    def _on_secret_changed(self, changed_widget, key):
        if (
            self._suppress_dirty
            or self._save_busy
            or self.sync_coordinator is None
            or self.sync_coordinator.state is None
        ):
            return
        entry = self.secret_entries[key]
        deletion = self.secret_delete_checks[key]
        self._suppress_dirty = True
        try:
            if changed_widget is entry and entry.get_text():
                deletion.set_active(False)
            elif changed_widget is deletion and deletion.get_active():
                entry.set_text("")
        finally:
            self._suppress_dirty = False

        state = self.sync_coordinator.state
        if entry.get_text() or deletion.get_active():
            state.mark_secret_dirty(key)
        else:
            state.discard_secret(key)
        self.sync_state = state
        self._render_field_states()

    def _on_snapshot(self, payload, visible, state):
        self.sync_state = state
        if not self.widgets:
            self._suppress_dirty = True
            try:
                self._build_fields(payload, visible)
            finally:
                self._suppress_dirty = False
        else:
            self._apply_visible_values(payload, visible)

        secrets = payload.get("secrets", {})
        if not isinstance(secrets, dict):
            secrets = {}
        for key, _label, presence_key in self.secret_specs:
            present = bool(secrets.get(presence_key))
            self.secret_presence_labels[key].set_text(
                "Vorhandener Wert: %s" % ("ja" if present else "nein")
            )
        self._render_field_states()
        if not state.dirty and not state.secret_dirty:
            self._set_status("Synchron.")

    def _render_field_states(self):
        state = self.sync_state
        if state is None:
            self.save_button.set_sensitive(False)
            self.discard_all_button.set_sensitive(False)
            return

        for key, label in self.field_state_labels.items():
            if key in state.conflicts:
                label.set_text("Extern geändert – lokaler Entwurf bleibt erhalten")  # noqa: RUF001
            elif key in state.dirty:
                label.set_text("Ungespeichert")
            else:
                label.set_text("")
            self.field_discard_buttons[key].set_visible(
                key in state.conflicts and not self._save_busy
            )

        for key, label in self.secret_state_labels.items():
            if key in state.conflicts:
                label.set_text("Extern geändert – Secret-Entwurf bleibt erhalten")  # noqa: RUF001
            elif key in state.secret_dirty:
                label.set_text("Ungespeicherter Secret-Entwurf")
            else:
                label.set_text("")
            self.secret_discard_buttons[key].set_visible(
                key in state.conflicts and not self._save_busy
            )

        draft_count = len(state.dirty) + len(state.secret_dirty)
        self.save_button.set_sensitive(draft_count > 0 and not self._save_busy)
        self.discard_all_button.set_sensitive(
            draft_count > 0 and not self._save_busy
        )

    def _on_discard_field(self, _button, key):
        if self._save_busy or self.sync_state is None:
            return
        value = self.sync_state.discard(key)
        self._suppress_dirty = True
        try:
            self._set_widget_public_value(self.widgets[key], value)
        finally:
            self._suppress_dirty = False
        self._render_field_states()

    def _on_discard_secret(self, _button, key):
        if self._save_busy or self.sync_state is None:
            return
        self._suppress_dirty = True
        try:
            self.sync_state.discard_secret(key)
            self.secret_entries[key].set_text("")
            self.secret_delete_checks[key].set_active(False)
        finally:
            self._suppress_dirty = False
        self._render_field_states()

    def _on_discard_all(self, _button):
        if self._save_busy or self.sync_state is None:
            return
        transient_for = self.get_toplevel()
        if not isinstance(transient_for, Gtk.Window):
            transient_for = None
        dialog = Gtk.MessageDialog(
            transient_for=transient_for,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Alle lokalen, noch nicht gespeicherten Entwürfe verwerfen?",
        )
        try:
            confirmed = dialog.run() == Gtk.ResponseType.OK
        finally:
            dialog.destroy()
        if not confirmed:
            return

        self._suppress_dirty = True
        try:
            for key in list(self.sync_state.dirty):
                value = self.sync_state.discard(key)
                self._set_widget_public_value(self.widgets[key], value)
            for key in list(self.sync_state.secret_dirty):
                self.sync_state.discard_secret(key)
                self.secret_entries[key].set_text("")
                self.secret_delete_checks[key].set_active(False)
        finally:
            self._suppress_dirty = False
        self._set_status("Lokale Entwürfe verworfen.")
        self._render_field_states()

    def _secret_actions(self):
        actions = {}
        if self.sync_state is None:
            return actions
        for key in self.sync_state.secret_dirty:
            if self.secret_delete_checks[key].get_active():
                actions[key] = {"action": "delete"}
            else:
                value = self.secret_entries[key].get_text()
                if value:
                    actions[key] = {"action": "replace", "value": value}
        return actions

    def _on_save(self, _button):
        if (
            self._save_busy
            or self.sync_coordinator is None
            or self.sync_coordinator.state is None
        ):
            return
        state = self.sync_coordinator.state
        values = {
            key: self._widget_public_value(widget)
            for key, widget in self.widgets.items()
        }
        try:
            request = state.build_request(values, self._secret_actions())
        except settings_sync.SettingsCliError as exc:
            self._set_status(f"Speichern abgelehnt: {exc}")
            return
        if not request["changes"] and not request["secret_actions"]:
            self._set_status("Keine lokalen Änderungen.")
            return
        if self.sync_coordinator.submit_save(request):
            self._set_status("Prüfe und speichere atomar …")
        else:
            self._set_status("Eine Speicherung läuft bereits.")

    def _on_sync_busy(self, busy):
        self._save_busy = bool(busy)
        for widget in self.widgets.values():
            widget.set_sensitive(not self._save_busy)
        for key in self.secret_entries:
            self.secret_entries[key].set_sensitive(not self._save_busy)
            self.secret_delete_checks[key].set_sensitive(not self._save_busy)
        self._render_field_states()

    def _on_save_result(self, kind, message, _payload):
        if kind == "success":
            self._suppress_dirty = True
            try:
                for key in self.secret_entries:
                    self.secret_entries[key].set_text("")
                    self.secret_delete_checks[key].set_active(False)
            finally:
                self._suppress_dirty = False
        self._set_status(message)
        self._render_field_states()

    def _on_sync_error(self, message):
        self._set_status(message)

    def _on_map(self, *_args):
        if self.sync_coordinator is not None:
            return self.sync_coordinator.focus_refresh()
        return False

    def _on_focus_in(self, *_args):
        if self.sync_coordinator is not None:
            return self.sync_coordinator.focus_refresh()
        return False

    def _dispose_sync(self, *_args):
        if self._disposed:
            return False
        self._disposed = True
        if self.sync_coordinator is not None:
            self.sync_coordinator.dispose()
        else:
            self._executor.shutdown(wait=False, cancel_futures=True)
        return False

    def _on_start_generator(self, _button):
        self._run_operation(
            (["systemctl", "--user", "start", "wirtelprimpf.service"],),
            "Generator gestartet.",
            "Generatorstart fehlgeschlagen",
        )

    def _on_restart_timers(self, _button):
        self._run_operation(
            (
                ["systemctl", "--user", "daemon-reload"],
                ["systemctl", "--user", "restart", "wirtelprimpf.timer"],
            ),
            "Timer neu gestartet.",
            "Timer-Restart fehlgeschlagen",
        )

    def _run_operation(self, commands, success, failure_prefix):
        if self._operation_busy or self._disposed:
            return
        self._operation_busy = True
        self.run_button.set_sensitive(False)
        self.timer_button.set_sensitive(False)
        thread = threading.Thread(
            target=self._operation_worker,
            args=(commands, success, failure_prefix),
            daemon=True,
        )
        try:
            thread.start()
        except Exception:
            self._finish_operation_idle(failure_prefix)

    def _operation_worker(self, commands, success, failure_prefix):
        try:
            for command in commands:
                self._run(command)
            message = success
        except Exception as exc:
            message = f"{failure_prefix}: {exc}"
        GLib.idle_add(self._finish_operation_idle, message)

    def _run(self, args):
        result = subprocess.run(
            args,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
            shell=False,
        )
        if result.returncode != 0:
            message = (
                result.stderr.strip()
                or result.stdout.strip()
                or f"exit {result.returncode}"
            )
            raise RuntimeError("%s: %s" % (" ".join(args), message))
        return result

    def _finish_operation_idle(self, text):
        self._operation_busy = False
        if not self._disposed:
            self.run_button.set_sensitive(True)
            self.timer_button.set_sensitive(True)
            self._set_status(text)
        return False

    def _set_status(self, text):
        self.status.set_text(str(text))
