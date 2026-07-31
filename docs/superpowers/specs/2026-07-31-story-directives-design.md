---
tags:
  - wirtelprimpf
  - story-directives
  - cinnamon
  - generator
  - design
type: design-specification
status: approved
date: 2026-07-31
aliases:
  - Story-Vorgaben Design
  - Story Directives Ledger Design
created: 2026-07-31
title: Story-Vorgaben für laufende, kommende und vergangene Wirtelprimpf-Storys
---

# Story-Vorgaben für laufende, kommende und vergangene Wirtelprimpf-Storys

## Ziel

Der Wirtelprimpf-Generator erhält pro Story-Band dauerhafte Vorgaben. Die laufende Story und die beiden unmittelbar folgenden Storys sind in den Cinnamon-Einstellungen editierbar und mit ihren aktuell gültigen Vorgaben sichtbar. Vorgaben vergangener Storys bleiben vollständig sichtbar, sind jedoch technisch und visuell schreibgeschützt.

Story III wird initial mit folgenden inhaltlichen Leitplanken vorbelegt:

- Actionstory;
- blutig;
- düsterer, harter Thriller-/Horrorton mit hoher Fallhöhe, stetig steigender Bedrohung, moralischem Druck und kompromisslosen Konsequenzen;
- abstrahierte Einflüsse von Markus Heitz sowie Richard Bachman (Stephen King), ohne konkrete Stimme, Formulierungen oder unverwechselbare Stilmittel nachzuahmen;
- James-Bond-artige Spionage- und Actionelemente mit riskanter Mission, eleganter Täuschung, überraschenden Wendungen, technischen Spielereien und einem katzentauglichen Gegenspieler.

## Gewählte Architektur

Die Vorgaben werden in einem versionierten JSON-Register unter `~/.config/wirtelprimpf/story_directives.json` gespeichert. Ein reines Python-Kernmodul übernimmt Schema, Validierung, sichere atomare Schreibvorgänge, Story-III-Initialisierung, Ermittlung des effektiv nächsten Bandes und die Übertragung der aktiven Vorgabe in die bestehende Markdown-Promptkonfiguration. Ein getrenntes GTK-Widget verwendet dieselbe Kernlogik und stellt die Bedienoberfläche in Cinnamon bereit.

Der Generator selbst bleibt unverändert. Vor jedem systemd-Storylauf ruft `ExecStartPre` das Kernmodul auf. Dieses ersetzt ausschließlich die verwaltete Markdown-Sektion `## Zwingende Story-Vorgaben (verwaltet)` in der bestehenden Story-Promptdatei. Die bereits vorhandene Prompt-Parserlogik erkennt „Zwingende“ als fixen Abschnitt und übernimmt deshalb alle Zeilen statt einer zufälligen Auswahl.

## Alternativen und Entscheidung

### Environment-Variablen pro Band

Vorteil: geringer Erstaufwand. Nachteile: schlecht für mehrzeilige Vorgaben, keine belastbare Historie, unübersichtliche Skalierung und schwierige UI-Abbildung. Verworfen.

### Eine Markdown-Datei pro Story

Vorteil: unmittelbar menschenlesbar. Nachteile: Bandindex, Schreibschutzstatus, Migration und atomare Aktualisierung müssten aus Dateinamen abgeleitet werden; fehleranfälliger als ein Register. Verworfen.

### Versioniertes JSON-Register

Vorteile: eindeutiges Schema, atomar speicherbar, leicht testbar, historisch stabil, dynamisch für beliebig viele Storys und ohne Änderung des Generators nutzbar. Gewählt.

## Datenmodell

```json
{
  "schema_version": 1,
  "migrations": {
    "story_iii_seeded": true
  },
  "stories": {
    "3": {
      "volume": 3,
      "directive": "Actionstory.\nBlutig.\n...",
      "created_at": "2026-07-31T17:00:12Z",
      "updated_at": "2026-07-31T17:00:12Z",
      "source": "initial-story-iii-request"
    }
  }
}
```

Regeln:

- `schema_version` ist exakt `1`.
- Schlüssel in `stories` sind positive Dezimalzahlen ohne führende Sonderzeichen.
- `volume` muss dem Schlüssel entsprechen.
- `directive` ist UTF-8-Text bis maximal 20.000 Zeichen.
- Leere Vorgaben werden beim Speichern entfernt.
- `migrations.story_iii_seeded=true` verhindert, dass eine bewusst geleerte oder entfernte Story-III-Vorgabe später erneut automatisch erscheint.
- `created_at` bleibt bei Änderungen erhalten; `updated_at` wird erneuert.
- Unbekannte zusätzliche Felder werden beim Lesen nicht als Steuerung interpretiert.

## Ermittlung der laufenden Story

Die UI und der Pre-Run-Helfer lesen `wirtelprimpf_story_state.json`. Normalerweise ist `current_volume` die laufende Story. Steht `pending_new_volume` auf `true`, ist die abgeschlossene Story bereits historisch und der nächste Generatorlauf beginnt `current_volume + 1`; daher wird dieser Band als effektiv laufend behandelt. Fehlt der State, wird Story I angenommen.

## Bedienoberfläche

Die Cinnamon-Einstellungen erhalten eine neue Seite **Story-Vorgaben**.

Oben werden genau drei editierbare Karten gezeigt:

1. laufende Story;
2. nächste Story;
3. übernächste Story.

Jede Karte zeigt Bandnummer, römische Bezeichnung, Status, den vollständigen Text und einen gemeinsamen Speicherknopf. Story III ist durch die Initialmigration bereits sichtbar, sobald sie in dieses Dreierfenster fällt.

Darunter folgt **Vergangene Storys (read-only)**. Angezeigt werden alle Bände kleiner als der effektiv laufende Band, absteigend sortiert. Textfelder sind nicht editierbar und nicht speicherbar. Auch Bände ohne registrierte Vorgaben werden als „Keine gespeicherten Vorgaben“ kenntlich gemacht, sofern sie aus dem State ableitbar sind.

## Prompt-Anwendung

Vor dem Storylauf:

1. sichere Environment-Datei lesen;
2. State und Register validieren;
3. Story-III-Seed genau einmal ergänzen, solange die Migration noch nicht als ausgeführt markiert ist;
4. effektiven Band bestimmen;
5. bestehende verwaltete Promptsektion vollständig entfernen;
6. bei vorhandener Vorgabe eine neue feste Sektion mit allen nichtleeren Zeilen anhängen;
7. atomar mit Modus `0600` schreiben.

Ohne Vorgabe wird die verwaltete Sektion entfernt. Andere Promptabschnitte, lokale Anpassungen und Formatierungen bleiben unverändert.

## Fehlerbehandlung und Sicherheit

- Symlinks für State, Register und Promptdatei werden abgelehnt.
- JSON-Fehler, falsche Typen und widersprüchliche Bandnummern führen zu klaren Fehlermeldungen.
- Dateien werden über temporäre Dateien im Zielverzeichnis und `os.replace` geschrieben.
- Das Register und die Promptdatei erhalten nach verwalteten Schreibvorgängen Modus `0600`.
- Der CLI-Befehl gibt bei Erfolg eine kompakte Statusmeldung aus und beendet sich bei Fehlern ungleich null, sodass systemd den Storylauf blockiert statt mit falschen Vorgaben fortzufahren.

## Tests

Automatisiert werden mindestens geprüft:

- Story III wird genau einmal initialisiert, überschreibt keine Benutzeränderung und bleibt nach bewusstem Leeren leer.
- `pending_new_volume=true` schaltet die wirksame Bandnummer vor dem Generatorlauf korrekt weiter.
- Eine aktive Vorgabe wird vollständig als feste Markdown-Sektion eingetragen.
- Eine alte verwaltete Sektion wird ersetzt, nicht dupliziert.
- Eine leere Vorgabe entfernt die verwaltete Sektion.
- Vergangene Bände werden vom Rollenmodell als read-only klassifiziert; nur laufend und zwei folgende sind editierbar.
- Das Cinnamon-Schema referenziert die neue Seite und das neue Widget.
- `make check` kompiliert Kernmodul und GTK-Widget und führt die neuen Tests aus.

## Nicht-Ziele

- Keine Änderung an der Storyabschlusslogik.
- Keine Änderung an der OpenAI-Modellwahl.
- Keine nachträgliche Bearbeitung alter Storytexte.
- Keine direkte Stilkopie lebender Autorinnen oder Autoren; Namen dienen nur als Quellen für abstrahierte Merkmalsbeschreibungen.
- Keine Vermischung mit dem parallelen Webseiten-PR.
