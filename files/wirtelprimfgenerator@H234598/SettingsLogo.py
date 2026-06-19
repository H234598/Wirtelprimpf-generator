#!/usr/bin/python3

import os
import json
import random
import re
import subprocess
import threading
import urllib.request

from JsonSettingsWidgets import SettingsWidget
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk


GENERATOR_IMAGE_CHOICES = {
    "atelier": "settings-generator-atelier.png",
    "machine": "settings-generator-machine.png",
}
ABOUT_IMAGE_CHOICES = {
    "story": "settings-about-story.png",
    "book": "settings-about-book.png",
}
IMAGE_MODEL_CHOICES = (
    "gpt-image-2",
    "gpt-image-1.5",
    "gpt-image-1",
    "gpt-image-1-mini",
)


def _choice_asset(choices, value, default_key):
    selected = (value or default_key).strip()
    return choices.get(selected, choices[default_key])


class _ResponsiveLogo(SettingsWidget):
    github_url = "https://github.com/H234598/Katzenbilder"
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
        box.set_tooltip_text("Open the Katzenbilder GitHub repository")

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
        event_box.set_tooltip_text("Open the Katzenbilder GitHub repository")
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
    repo_url = "https://github.com/H234598/Katzenbilder"

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

        link = Gtk.LinkButton.new_with_label(self.repo_url, "GitHub: H234598/Katzenbilder")
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


class GeneratorConfigEditor(SettingsWidget):
    env_path = os.path.expanduser("~/.config/wirtelprimpf/openai.env")
    systemd_user_dir = os.path.expanduser("~/.config/systemd/user")

    env_fields = (
        ("OPENAI_API_KEY", "OpenAI API Key", "secret", ()),
        ("WIRTELPRIMPF_LOCAL_OUTDIR", "Lokaler Output", "entry", ()),
        ("WIRTELPRIMPF_WORKING_DIR", "Working-Verzeichnis", "entry", ()),
        ("WIRTELPRIMPF_REPO_PATH", "Git-Repo-Pfad", "entry", ()),
        ("WIRTELPRIMPF_REPO_SLUG", "GitHub Repo-Slug", "entry", ()),
        ("WIRTELPRIMPF_REPO_SUBDIR", "Repo-Unterordner", "entry", ()),
        ("WIRTELPRIMPF_REPO_BRANCH", "Repo-Branch", "entry", ()),
        ("WIRTELPRIMPF_GIT_AUTHOR_NAME", "Git Autor Name", "entry", ()),
        ("WIRTELPRIMPF_GIT_AUTHOR_EMAIL", "Git Autor Mail", "entry", ()),
        ("WIRTELPRIMPF_IMAGE_MODEL", "Bildmodell", "combo", IMAGE_MODEL_CHOICES),
        ("WIRTELPRIMPF_IMAGE_SIZE", "Bildgroesse", "entry", ()),
        ("WIRTELPRIMPF_FLEX_PROCESSING", "Flex Processing", "combo", ("on", "off", "flex")),
        ("WIRTELPRIMPF_OPERANDI", "Modus", "combo", ("story", "classic", "both")),
        ("WIRTELPRIMPF_PROMPT_CONFIG", "Bildregeln", "entry", ()),
        ("WIRTELPRIMPF_STORY_PROMPT_CONFIG", "Storyregeln", "entry", ()),
        ("WIRTELPRIMPF_STORY_MODEL", "Storymodell", "entry", ()),
        ("WIRTELPRIMPF_STORY_DOCUMENT", "Story-Dokument", "entry", ()),
        ("WIRTELPRIMPF_STORY_STATE", "Story-Status", "entry", ()),
        ("WIRTELPRIMPF_STORY_FINISH", "Story abschliessen", "combo", ("false", "true")),
        ("WIRTELPRIMPF_STORY_FINISH_PARTS_MIN", "Finish Teile min", "entry", ()),
        ("WIRTELPRIMPF_STORY_FINISH_PARTS_MAX", "Finish Teile max", "entry", ()),
        ("WIRTELPRIMPF_OUTPUT_RESOLUTION", "Ausgabe-Aufloesung", "entry", ()),
    )

    defaults = {
        "WIRTELPRIMPF_REPO_SLUG": "H234598/Katzenbilder",
        "WIRTELPRIMPF_REPO_BRANCH": "main",
        "WIRTELPRIMPF_IMAGE_MODEL": "gpt-image-2",
        "WIRTELPRIMPF_IMAGE_SIZE": "1536x1024",
        "WIRTELPRIMPF_FLEX_PROCESSING": "on",
        "WIRTELPRIMPF_OPERANDI": "story",
        "WIRTELPRIMPF_STORY_MODEL": "gpt-5-mini",
        "WIRTELPRIMPF_STORY_FINISH": "false",
        "WIRTELPRIMPF_STORY_FINISH_PARTS_MIN": "3",
        "WIRTELPRIMPF_STORY_FINISH_PARTS_MAX": "5",
        "WIRTELPRIMPF_OUTPUT_RESOLUTION": "2k",
    }

    systemd_fields = (
        ("generator_timer_enabled", "Generator-Timer aktiv", "switch", "true"),
        ("generator_interval_minutes", "Generator-Intervall (Minuten)", "minutes", "120"),
        ("generator_randomized_delay", "Generator RandomizedDelaySec", "entry", "120"),
        ("generator_persistent", "Generator Persistent", "switch", "true"),
    )

    def __init__(self, info, key, settings):
        SettingsWidget.__init__(self)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(8)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.env_widgets = {}
        self.systemd_widgets = {}
        self.status = Gtk.Label(label="")
        self.status.set_halign(Gtk.Align.START)
        self.status.set_line_wrap(True)

        env_values = self._read_env_file()

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_height(520)
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_start(8)
        content.set_margin_end(8)
        content.set_margin_top(8)
        content.set_margin_bottom(8)
        scroller.add(content)

        content.pack_start(self._section_label("Generator-Environment"), False, True, 0)
        for name, label, kind, options in self.env_fields:
            default_value = self.defaults.get(name, "")
            widget = self._make_value_widget(kind, options, default_value)
            self._set_widget_value(widget, env_values.get(name, default_value))
            self.env_widgets[name] = widget
            content.pack_start(self._make_row(label, widget), False, True, 0)

        content.pack_start(self._section_label("systemd User-Units"), False, True, 0)
        systemd_values = self._read_systemd_values()
        for name, label, kind, default in self.systemd_fields:
            widget = self._make_value_widget(kind, (), default)
            self._set_widget_value(widget, systemd_values.get(name, default))
            self.systemd_widgets[name] = widget
            content.pack_start(self._make_row(label, widget), False, True, 0)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.START)
        save_button = Gtk.Button(label="Speichern")
        save_button.connect("clicked", self._on_save)
        restart_button = Gtk.Button(label="Speichern + Restart")
        restart_button.connect("clicked", self._on_save_restart)
        run_button = Gtk.Button(label="Generator jetzt starten")
        run_button.connect("clicked", self._on_start_generator)
        timer_button = Gtk.Button(label="Timer neu starten")
        timer_button.connect("clicked", self._on_restart_timers)
        for button in (save_button, restart_button, run_button, timer_button):
            buttons.pack_start(button, False, False, 0)

        self.pack_start(scroller, True, True, 0)
        self.pack_start(buttons, False, True, 0)
        self.pack_start(self.status, False, True, 0)
        self.content_widget = scroller

    def _section_label(self, text):
        label = Gtk.Label()
        label.set_markup("<b>%s</b>" % GLib.markup_escape_text(text))
        label.set_halign(Gtk.Align.START)
        label.set_margin_top(8)
        return label

    def _make_row(self, label_text, widget):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_hexpand(True)
        label = Gtk.Label(label=label_text)
        label.set_halign(Gtk.Align.START)
        label.set_size_request(230, -1)
        row.pack_start(label, False, False, 0)
        row.pack_start(widget, True, True, 0)
        return row

    def _make_value_widget(self, kind, options, default=""):
        if kind == "combo":
            combo = Gtk.ComboBoxText()
            for option in options:
                combo.append(option, option)
            combo._wirtel_options = tuple(options)
            combo._wirtel_default = str(default or (options[0] if options else ""))
            combo.set_hexpand(True)
            return combo
        if kind == "switch":
            switch = Gtk.Switch()
            switch.set_halign(Gtk.Align.START)
            return switch
        if kind == "minutes":
            spin = Gtk.SpinButton.new_with_range(1, 10080, 1)
            spin.set_numeric(True)
            spin.set_hexpand(True)
            return spin
        entry = Gtk.Entry()
        entry.set_hexpand(True)
        if kind == "secret":
            entry.set_visibility(False)
            entry.set_invisible_char("*")
        return entry

    def _set_widget_value(self, widget, value):
        value = "" if value is None else str(value)
        if isinstance(widget, Gtk.ComboBoxText):
            widget.set_active_id(value)
            if widget.get_active_id() is None:
                fallback = getattr(widget, "_wirtel_default", "")
                if fallback:
                    widget.set_active_id(fallback)
            if widget.get_active_id() is None:
                options = getattr(widget, "_wirtel_options", ())
                if options:
                    widget.set_active_id(options[0])
        elif isinstance(widget, Gtk.Switch):
            widget.set_active(value.lower() in ("1", "yes", "true", "on"))
        elif isinstance(widget, Gtk.SpinButton):
            widget.set_value(self._minutes_value(value, 120))
        else:
            widget.set_text(value)

    def _get_widget_value(self, widget):
        if isinstance(widget, Gtk.ComboBoxText):
            return widget.get_active_id() or ""
        if isinstance(widget, Gtk.Switch):
            return "true" if widget.get_active() else "false"
        if isinstance(widget, Gtk.SpinButton):
            return str(int(widget.get_value()))
        return widget.get_text()

    def _minutes_value(self, value, default):
        text = "" if value is None else str(value).strip().lower()
        if not text:
            return int(default)
        units = (
            ("min", 1),
            ("m", 1),
            ("h", 60),
            ("d", 1440),
            ("s", 1 / 60),
        )
        for suffix, multiplier in units:
            if text.endswith(suffix):
                number = text[: -len(suffix)].strip()
                try:
                    minutes = float(number) * multiplier
                except ValueError:
                    return int(default)
                return max(1, int(round(minutes)))
        try:
            return max(1, int(text))
        except ValueError:
            return int(default)

    def _timer_interval_minutes(self):
        dropin_value = self._read_timer_dropin_value("OnUnitActiveSec")
        if dropin_value:
            return str(self._minutes_value(dropin_value, 120))
        monotonic = self._systemctl_show("wirtelprimpf.timer", "TimersMonotonic")
        match = None
        if monotonic:
            match = re.search(r"OnUnitActiveUSec=([^;]+)", monotonic)
        if match:
            return str(self._minutes_value(match.group(1), 120))
        return "120"

    def _read_timer_dropin_value(self, name):
        path = os.path.join(self.systemd_user_dir, "wirtelprimpf.timer.d", "override.conf")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if line.startswith(name + "="):
                        return line.split("=", 1)[1].strip()
        except FileNotFoundError:
            return ""
        except Exception:
            return ""
        return ""

    def _read_env_file(self):
        values = {}
        try:
            with open(self.env_path, "r", encoding="utf-8") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = self._unquote_env_value(value.strip())
                    values[key] = value
        except FileNotFoundError:
            pass
        except Exception as exc:
            self._set_status("Env-Datei konnte nicht gelesen werden: %s" % exc)
        return values

    def _unquote_env_value(self, value):
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        return value.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")

    def _quote_env_value(self, value):
        value = "" if value is None else str(value)
        if value == "":
            return ""
        needs_quotes = any(char.isspace() or char in "\"'#$\\;" for char in value)
        if not needs_quotes:
            return value
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return '"%s"' % escaped

    def _write_env_file(self):
        os.makedirs(os.path.dirname(self.env_path), exist_ok=True)
        values = {name: self._get_widget_value(widget) for name, widget in self.env_widgets.items()}
        lines = [
            "# Wirtelprimpf generator settings.",
            "# Written by the Cinnamon applet settings UI.",
            "",
        ]
        for name, _label, _kind, _options in self.env_fields:
            lines.append("%s=%s" % (name, self._quote_env_value(values.get(name, ""))))
        with open(self.env_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        os.chmod(self.env_path, 0o600)

    def _read_systemd_values(self):
        return {
            "generator_timer_enabled": self._unit_enabled("wirtelprimpf.timer"),
            "generator_interval_minutes": self._timer_interval_minutes(),
            "generator_randomized_delay": self._systemctl_show("wirtelprimpf.timer", "RandomizedDelayUSec").replace("us", "") or "120",
            "generator_persistent": self._systemctl_show("wirtelprimpf.timer", "Persistent") or "true",
        }

    def _unit_enabled(self, unit):
        result = self._run(["systemctl", "--user", "is-enabled", unit], check=False)
        return "true" if result.returncode == 0 else "false"

    def _systemctl_show(self, unit, prop):
        result = self._run(["systemctl", "--user", "show", unit, "-p", prop, "--value"], check=False)
        if result.returncode != 0:
            return ""
        return result.stdout.strip()

    def _write_dropin(self, unit, content):
        dropin_dir = os.path.join(self.systemd_user_dir, "%s.d" % unit)
        os.makedirs(dropin_dir, exist_ok=True)
        with open(os.path.join(dropin_dir, "override.conf"), "w", encoding="utf-8") as handle:
            handle.write(content)

    def _write_systemd_dropins(self):
        env = {name: self._get_widget_value(widget) for name, widget in self.env_widgets.items()}
        sysvals = {name: self._get_widget_value(widget) for name, widget in self.systemd_widgets.items()}

        self._write_dropin(
            "wirtelprimpf.service",
            "\n".join(
                [
                    "[Service]",
                    "Environment=",
                    "Environment=WIRTELPRIMPF_OPERANDI=%s" % env.get("WIRTELPRIMPF_OPERANDI", "story"),
                    "",
                ]
            ),
        )
        self._write_dropin(
            "wirtelprimpf.timer",
            "\n".join(
                [
                    "[Timer]",
                    "OnCalendar=",
                    "OnBootSec=",
                    "OnUnitActiveSec=",
                    "OnBootSec=%smin" % self._minutes_value(sysvals.get("generator_interval_minutes"), 120),
                    "OnUnitActiveSec=%smin" % self._minutes_value(sysvals.get("generator_interval_minutes"), 120),
                    "RandomizedDelaySec=%s" % sysvals.get("generator_randomized_delay", "120"),
                    "Persistent=%s" % sysvals.get("generator_persistent", "true"),
                    "",
                ]
            ),
        )
    def _apply_enabled_state(self):
        sysvals = {name: self._get_widget_value(widget) for name, widget in self.systemd_widgets.items()}
        for unit, key in (
            ("wirtelprimpf.timer", "generator_timer_enabled"),
        ):
            if sysvals.get(key) == "true":
                self._run(["systemctl", "--user", "enable", "--now", unit])
            else:
                self._run(["systemctl", "--user", "disable", "--now", unit], check=False)

    def _save(self):
        self._write_env_file()
        self._write_systemd_dropins()
        self._run(["systemctl", "--user", "daemon-reload"])
        self._apply_enabled_state()

    def _on_save(self, _button):
        try:
            self._save()
            self._set_status("Gespeichert.")
        except Exception as exc:
            self._set_status("Speichern fehlgeschlagen: %s" % exc)

    def _on_save_restart(self, _button):
        try:
            self._save()
            self._restart_generator_timer()
            self._set_status("Gespeichert und neu gestartet.")
        except Exception as exc:
            self._set_status("Restart fehlgeschlagen: %s" % exc)

    def _on_start_generator(self, _button):
        try:
            self._run(["systemctl", "--user", "start", "wirtelprimpf.service"])
            self._set_status("Generator gestartet.")
        except Exception as exc:
            self._set_status("Generatorstart fehlgeschlagen: %s" % exc)

    def _on_restart_timers(self, _button):
        try:
            self._run(["systemctl", "--user", "daemon-reload"])
            self._restart_generator_timer()
            self._set_status("Timer neu gestartet.")
        except Exception as exc:
            self._set_status("Timer-Restart fehlgeschlagen: %s" % exc)

    def _restart_generator_timer(self):
        self._run(["systemctl", "--user", "restart", "wirtelprimpf.timer"], check=False)

    def _run(self, args, check=True):
        result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check and result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or "exit %s" % result.returncode
            raise RuntimeError("%s: %s" % (" ".join(args), message))
        return result

    def _set_status(self, text):
        self.status.set_text(text)
