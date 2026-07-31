#!/usr/bin/python3
"""Cinnamon settings widget for current, upcoming, and archived story directives."""

from __future__ import annotations

import sys
from pathlib import Path

from JsonSettingsWidgets import SettingsWidget
from gi.repository import Gtk

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import story_directives_core as core  # noqa: E402

ROLE_LABELS = {
    "current": "Laufende Story",
    "next": "Nächste Story",
    "upcoming": "Übernächste Story",
    "past": "Vergangene Story",
}


def _roman(value):
    numerals = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    remaining = int(value)
    result = []
    for number, marker in numerals:
        while remaining >= number:
            result.append(marker)
            remaining -= number
    return "".join(result)


class StoryDirectivesEditor(SettingsWidget):
    """Edit the active three story slots and show older slots read-only."""

    env_path = Path.home() / ".config" / "wirtelprimpf" / "openai.env"

    def __init__(self, info, key, settings):
        SettingsWidget.__init__(self)
        self.info = info
        self.key = key
        self.settings = settings
        self.editable_buffers = {}
        self.content_box = None
        self.status = Gtk.Label(label="")
        self.status.set_halign(Gtk.Align.START)
        self.status.set_line_wrap(True)
        self.status.set_selectable(True)

        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(8)
        self.set_hexpand(True)
        self.set_vexpand(True)

        heading = Gtk.Label()
        heading.set_markup("<big><b>Story-Vorgaben</b></big>")
        heading.set_halign(Gtk.Align.START)
        heading.set_line_wrap(True)
        self.pack_start(heading, False, True, 0)

        explanation = Gtk.Label(
            label=(
                "Bearbeitbar sind immer die laufende Story und die zwei unmittelbar folgenden Storys. "
                "Beim Start des Generators wird nur die Vorgabe des wirksamen aktuellen Bandes in die "
                "Story-Prompt-Konfiguration übernommen. Vergangene Storys bleiben als unveränderliches "
                "Archiv sichtbar."
            )
        )
        explanation.set_halign(Gtk.Align.START)
        explanation.set_line_wrap(True)
        explanation.set_selectable(True)
        self.pack_start(explanation, False, True, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_height(560)
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.content_box.set_margin_start(8)
        self.content_box.set_margin_end(8)
        self.content_box.set_margin_top(8)
        self.content_box.set_margin_bottom(8)
        scroller.add(self.content_box)
        self.pack_start(scroller, True, True, 0)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        save_button = Gtk.Button(label="Vorgaben speichern")
        save_button.connect("clicked", self._on_save)
        refresh_button = Gtk.Button(label="Neu laden")
        refresh_button.connect("clicked", self._on_refresh)
        buttons.pack_start(save_button, False, False, 0)
        buttons.pack_start(refresh_button, False, False, 0)
        self.pack_start(buttons, False, True, 0)
        self.pack_start(self.status, False, True, 0)
        self.content_widget = scroller

        self._reload()

    def _set_status(self, text):
        self.status.set_text(text)

    def _clear_content(self):
        for child in list(self.content_box.get_children()):
            self.content_box.remove(child)
        self.editable_buffers = {}

    def _read_context(self):
        paths = core.resolve_runtime_paths(self.env_path)
        state = core.load_story_state(paths["state"])
        current_volume = core.effective_current_volume(state)
        ledger = core.load_ledger(paths["ledger"], seed_story_iii=True)
        return paths, current_volume, ledger, core.story_roles(current_volume, ledger)

    def _reload(self):
        self._clear_content()
        try:
            paths, current_volume, _ledger, roles = self._read_context()
        except Exception as exc:
            self._add_error(str(exc))
            self._set_status("Vorgaben konnten nicht geladen werden: %s" % exc)
            self.show_all()
            return

        current_note = Gtk.Label(
            label=(
                "Wirksamer aktueller Band: Story %s · Ledger: %s"
                % (_roman(current_volume), paths["ledger"])
            )
        )
        current_note.set_halign(Gtk.Align.START)
        current_note.set_line_wrap(True)
        current_note.set_selectable(True)
        self.content_box.pack_start(current_note, False, True, 0)

        for item in roles["editable"]:
            self._add_story_editor(item)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(8)
        separator.set_margin_bottom(4)
        self.content_box.pack_start(separator, False, True, 0)

        archive_title = Gtk.Label()
        archive_title.set_markup("<b>Vergangene Storys · nur lesen</b>")
        archive_title.set_halign(Gtk.Align.START)
        self.content_box.pack_start(archive_title, False, True, 0)

        if not roles["past"]:
            empty = Gtk.Label(label="Noch keine vergangene Story vorhanden.")
            empty.set_halign(Gtk.Align.START)
            self.content_box.pack_start(empty, False, True, 0)
        else:
            for item in roles["past"]:
                self._add_story_editor(item)

        self._set_status("Geladen. Änderungen werden erst mit „Vorgaben speichern“ wirksam.")
        self.show_all()

    def _add_error(self, message):
        label = Gtk.Label(label=message)
        label.set_halign(Gtk.Align.START)
        label.set_line_wrap(True)
        label.set_selectable(True)
        self.content_box.pack_start(label, False, True, 0)

    def _story_title(self, item):
        role = ROLE_LABELS.get(item["role"], "Story")
        return "%s · Story %s" % (role, _roman(item["volume"]))

    def _add_story_editor(self, item):
        frame = Gtk.Frame(label=self._story_title(item))
        frame.set_hexpand(True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        text_view = Gtk.TextView()
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_monospace(False)
        text_view.set_left_margin(6)
        text_view.set_right_margin(6)
        text_view.set_top_margin(6)
        text_view.set_bottom_margin(6)
        text_view.set_size_request(-1, 130 if item["editable"] else 90)
        text_view.set_editable(bool(item["editable"]))
        text_view.set_cursor_visible(bool(item["editable"]))
        text_view.set_accepts_tab(False)
        displayed_directive = item.get("directive", "")
        if not item["editable"] and not displayed_directive.strip():
            displayed_directive = "Keine gespeicherten Vorgaben."
        text_view.get_buffer().set_text(displayed_directive)

        nested = Gtk.ScrolledWindow()
        nested.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        nested.set_shadow_type(Gtk.ShadowType.IN)
        nested.set_hexpand(True)
        nested.add(text_view)
        box.pack_start(nested, True, True, 0)

        if item["editable"]:
            self.editable_buffers[int(item["volume"])] = text_view.get_buffer()
        else:
            meta_parts = []
            if item.get("updated_at"):
                meta_parts.append("Stand: %s" % item["updated_at"])
            if item.get("source"):
                meta_parts.append("Quelle: %s" % item["source"])
            if meta_parts:
                meta = Gtk.Label(label=" · ".join(meta_parts))
                meta.set_halign(Gtk.Align.START)
                meta.set_selectable(True)
                box.pack_start(meta, False, True, 0)

        frame.add(box)
        self.content_box.pack_start(frame, False, True, 0)

    def _buffer_text(self, buffer_):
        start, end = buffer_.get_bounds()
        return buffer_.get_text(start, end, True)

    def _on_save(self, _button):
        try:
            paths, current_volume, _ledger, _roles = self._read_context()
            directives = {
                volume: self._buffer_text(buffer_)
                for volume, buffer_ in self.editable_buffers.items()
            }
            core.save_editable_window(
                paths["ledger"],
                current_volume=current_volume,
                directives=directives,
                source="cinnamon-settings",
            )
            applied = core.apply_active_directive(env_path=self.env_path)
            self._reload()
            action = "aktualisiert" if applied["directive_applied"] else "entfernt"
            self._set_status(
                "Gespeichert. Vorgabe für Story %s wurde im aktiven Prompt %s."
                % (_roman(applied["current_volume"]), action)
            )
        except ValueError as exc:
            if "editable story window changed" in str(exc):
                self._reload()
                self._set_status(
                    "Der laufende Band hat sich geändert. Die Ansicht wurde neu geladen; "
                    "bitte Änderungen im aktuellen Dreierfenster erneut vornehmen."
                )
            else:
                self._set_status("Speichern fehlgeschlagen: %s" % exc)
        except Exception as exc:
            self._set_status("Speichern fehlgeschlagen: %s" % exc)

    def _on_refresh(self, _button):
        self._reload()
