---
tags:
  - wirtelprimpf
  - story-directives
  - cinnamon
  - systemd
type: technical-documentation
status: implemented
date: 2026-07-31
aliases:
  - Story-Vorgaben
  - Story Directives Ledger
created: 2026-07-31
title: Story-Vorgaben pro Wirtelprimpf-Band
---

# Story-Vorgaben pro Wirtelprimpf-Band

## Zweck

Der Wirtelprimpf-Generator kann für jeden Story-Band eine dauerhafte Vorgabe speichern. Die Cinnamon-Einstellungen zeigen die effektiv laufende Story und die zwei direkt folgenden Storys als editierbare Felder. Alle früheren Bände werden darunter vollständig und technisch read-only angezeigt.

Story III wird beim ersten Zugriff auf das Register vorbelegt: Actionstory, blutig, düstere und kompromisslose Thriller-/Horrorenergie, abstrahierte Motive von Markus Heitz und Richard Bachman sowie James-Bond-artige Spionage- und Actionelemente. Die Vorgabe verlangt ausdrücklich keine Kopie einer konkreten Autorenstimme.

## Dateien

| Zweck | Standardpfad |
|---|---|
| Vorgabenregister | `~/.config/wirtelprimpf/story_directives.json` |
| Story-State | `~/Hintergrundbilder/wirtelprimpf_story_state.json` |
| Story-Promptkonfiguration | `~/.config/wirtelprimpf/story_prompt_config.md` |
| Generator-Environment | `~/.config/wirtelprimpf/openai.env` |
| Gemeinsamer CLI-Helfer | `~/.local/bin/wirtelprimpf-story-directives` |

Der Registerpfad kann in `openai.env` überschrieben werden:

```bash
WIRTELPRIMPF_STORY_DIRECTIVES=$HOME/.config/wirtelprimpf/story_directives.json
```

## Installation

`make install-local` installiert das Cinnamon-Applet und denselben geprüften Kern zusätzlich als gemeinsamen CLI-Helfer:

```bash
make install-local
```

Bei einer manuellen Generatorinstallation muss der Helfer ebenfalls installiert werden, bevor die neue systemd-Unit aktiviert wird:

```bash
install -Dm0755 \
  files/wirtelprimfgenerator@H234598/story_directives_core.py \
  ~/.local/bin/wirtelprimpf-story-directives
```

Der Applet-Uninstaller entfernt den gemeinsam genutzten CLI-Helfer absichtlich nicht, weil die systemd-Generatorinstallation ihn weiterhin benötigen kann.

## Bandfenster

Das effektive Bandfenster wird aus dem Story-State berechnet:

- Normalfall: `current_volume` ist die laufende Story.
- Bei `pending_new_volume=true`: Die bisherige Story ist bereits abgeschlossen; der nächste Lauf beginnt `current_volume + 1`.
- Editierbar: effektiver Band, effektiver Band + 1, effektiver Band + 2.
- Read-only: alle positiven Bandnummern unterhalb des effektiven Bandes.

Dadurch wird Story III bereits vor ihrem ersten erzeugten Teil mit ihrer Story-III-Vorgabe gestartet. Ändert sich der laufende Band, während das Einstellungsfenster geöffnet ist, verweigert der Speichervorgang das veraltete Dreierfenster und lädt die neue Bandansicht. So kann kein inzwischen vergangener Band nachträglich verändert werden.

## Anwendung vor jedem Generatorlauf

Die systemd-User-Unit führt vor `wirtelprimpf_generator.py` folgenden Schritt aus:

```bash
~/.local/share/wirtelprimpf-venv/bin/python \
  ~/.local/bin/wirtelprimpf-story-directives \
  apply --env-file ~/.config/wirtelprimpf/openai.env
```

Der Helfer liest State und Register, bestimmt den aktiven Band und ersetzt genau den verwalteten Abschnitt:

```markdown
## Story-Vorgaben (verwaltet)
- Erste Vorgabe. Zweite Vorgabe.
```

Der Abschnitt ist absichtlich eine reguläre Promptkategorie mit genau einem Listeneintrag. Der vorhandene Markdown-Parser wählt diesen einzigen Eintrag daher immer aus und gibt ihn sowohl an die Storytext- als auch an die Bildprompt-Konfiguration weiter. Mehrzeilige Eingaben werden vollständig zu diesem einen Eintrag zusammengeführt. Eine vorübergehend verwendete ältere Überschrift `## Zwingende Story-Vorgaben (verwaltet)` wird beim nächsten Anwenden automatisch entfernt und migriert.

Bestehende Abschnitte außerhalb des verwalteten Blocks bleiben erhalten. Ist für den aktiven Band keine Vorgabe gespeichert, wird ein eventuell vorhandener verwalteter Block entfernt. Ein Fehler beim Lesen, Validieren oder Schreiben blockiert den Generatorlauf über `ExecStartPre`, anstatt mit einer falschen Vorgabe fortzufahren.

## Datenformat

```json
{
  "schema_version": 1,
  "created_at": "2026-07-31T17:00:12Z",
  "updated_at": "2026-07-31T17:00:12Z",
  "migrations": {
    "story_iii_seeded": true
  },
  "stories": {
    "3": {
      "volume": 3,
      "directive": "Actionstory.\nBlutig.\n...",
      "created_at": "2026-07-31T17:00:12Z",
      "updated_at": "2026-07-31T17:00:12Z",
      "source": "seed:story-iii"
    }
  }
}
```

Leere editierbare Felder entfernen die Vorgabe des betreffenden zukünftigen oder laufenden Bandes. Story III wird nur während der einmaligen Migration vorbelegt. Danach verhindert `migrations.story_iii_seeded=true` sowohl das Überschreiben einer Benutzerfassung als auch ein unerwünschtes Wiederherstellen nach bewusstem Leeren.

## Sicherheit

- Register und verwaltete Promptdatei werden atomar geschrieben.
- Nach verwalteten Schreibvorgängen gilt Dateimodus `0600`.
- Symlink-Ziele für Environment, State, Register und Promptdatei werden abgelehnt.
- Das JSON-Schema akzeptiert nur positive, konsistente Bandnummern und Vorgaben bis 20.000 Zeichen.
- Nur das aktuell gültige Dreierfenster kann über die Oberfläche gespeichert werden.
- Der Kern verwendet ausschließlich die Python-Standardbibliothek.

## Manuelle Prüfung

Status und sichtbare Rollen anzeigen:

```bash
~/.local/bin/wirtelprimpf-story-directives \
  status --env-file ~/.config/wirtelprimpf/openai.env
```

Aktive Vorgabe manuell anwenden:

```bash
~/.local/bin/wirtelprimpf-story-directives \
  apply --env-file ~/.config/wirtelprimpf/openai.env
```

Repository-Checks:

```bash
make check
```
