#!/usr/bin/python3

import os
import random

from JsonSettingsWidgets import SettingsWidget
from gi.repository import Gdk, GdkPixbuf, Gtk


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
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_dir, "assets", self.asset_name)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_halign(Gtk.Align.FILL)
        box.set_hexpand(True)
        box.set_tooltip_text("Open the Katzenbilder GitHub repository")

        try:
            self._source_pixbuf = GdkPixbuf.Pixbuf.new_from_file(logo_path)
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
