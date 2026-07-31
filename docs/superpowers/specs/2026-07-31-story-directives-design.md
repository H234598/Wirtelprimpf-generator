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

Die Vorgaben werden in einem versionierten JSON-Register unter `~/.config/wirtelprimpf/story_directives.json` gespeichert. Ein reines Python-Kernmodul übernimmt Schema, Validierung, sichere atomare Schreibvorgänge, Story-III-Initialisierung, Ermittlung des effektiven Bandes und die Übertragung der aktiven Vorgabe in die bestehende Markdown-Promptkonfiguration. Ein getrenntes GTK-Widget verwendet dieselbe Kernlogik und stellt die Bedienoberfläche in Cinnamon bereit.

`make install-local` installiert das Kernmodul sowohl mit dem Applet als auch als gemeinsamen CLI-Helfer unter `~/.local/bin/wirtelprimpf-story-directives`. Die systemd-Unit ruft ausschließlich diesen stabilen CLI-Pfad auf und ist damit nicht vom internen Applet-Installationspfad abhängig. Bei einer manuellen Generatorinstallation muss derselbe Helfer zusätzlich installiert werden.

Der Generator selbst bleibt unverändert. Vor jedem systemd-Storylauf ruft `ExecStartPre` den Helfer auf. Dieser ersetzt ausschließlich die verwaltete Markdown-Sektion `## Story-Vorgaben (verwaltet)` in der bestehenden Story-Promptdatei.

Die Sektion ist bewusst **keine** „fixe“ Parsersektion: Der vorhandene Generator nimmt fixe Abschnitte nur in den Bildprompt auf. Stattdessen wird die gesamte mehrzeilige Vorgabe zu genau einem Listeneintrag einer regulären Kategorie zusammengeführt. Da die Kategorie nur diesen einen Eintrag besitzt, wird er deterministisch ausgewählt und erreicht sowohl Storytext als auch Bildprompt. Eine ältere Zwischenfassung mit der Überschrift `## Zwingende Story-Vorgaben (verwaltet)` wird beim Anwenden automatisch entfernt.

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
      "source": "seed:story-iii"
    }
  }
}
```

Regeln:

- `schema_version` ist exakt `1`.
- Schlüssel in `stories` sind positive Bandnummern und müssen mit `volume` übereinstimmen.
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

Darunter folgt **Vergangene Storys (read-only)**. Angezeigt werden alle Bände kleiner als der effektiv laufende Band, absteigend sortiert. Textfelder sind nicht editierbar und nicht speicherbar. Bände ohne registrierte Vorgabe zeigen ausdrücklich „Keine gespeicherten Vorgaben.“

Beim Speichern vergleicht die Kernlogik die im Fenster enthaltenen Bandnummern mit dem aktuell ermittelten Dreierfenster. Ist die Story während eines geöffneten Einstellungsfensters weitergesprungen, wird das veraltete Speichern verweigert und die Oberfläche lädt den neuen Stand. Damit lässt sich ein inzwischen vergangener Band nicht über ein altes Fenster nachträglich verändern.

## Prompt-Anwendung

Vor dem Storylauf:

1. sichere Environment-Datei lesen;
2. State und Register validieren;
3. Story-III-Seed genau einmal ergänzen, solange die Migration noch nicht als ausgeführt markiert ist;
4. effektiven Band bestimmen;
5. aktuelle sowie ältere verwaltete Promptsektion vollständig entfernen;
6. bei vorhandener Vorgabe alle nichtleeren Eingabezeilen zu einem einzigen regulären Kategorien-Eintrag zusammenführen;
7. atomar mit Modus `0600` schreiben.

Ohne Vorgabe wird die verwaltete Sektion entfernt. Andere Promptabschnitte und lokale Anpassungen bleiben erhalten.

## Fehlerbehandlung und Sicherheit

- Symlinks für Environment, State, Register und Promptdatei werden abgelehnt.
- JSON-Fehler, falsche Typen und widersprüchliche Bandnummern führen zu klaren Fehlermeldungen.
- Dateien werden über temporäre Dateien im Zielverzeichnis und `os.replace` geschrieben.
- Das Register und die Promptdatei erhalten nach verwalteten Schreibvorgängen Modus `0600`.
- Ein veraltetes editierbares Dreierfenster wird nicht gespeichert.
- Der CLI-Befehl beendet sich bei Fehlern ungleich null, sodass systemd den Storylauf blockiert statt mit falschen Vorgaben fortzufahren.

## Tests

Automatisiert werden geprüft:

- Story III wird genau einmal initialisiert, überschreibt keine Benutzeränderung und bleibt nach bewusstem Leeren leer.
- `pending_new_volume=true` schaltet die wirksame Bandnummer vor dem Generatorlauf korrekt weiter.
- Nur laufender Band und zwei Folgebände bilden das editierbare Fenster.
- Ein veraltetes Fenster mit einem inzwischen vergangenen Band wird abgelehnt.
- Die gesamte mehrzeilige Vorgabe wird als genau ein ausgewählter Kategorien-Eintrag gerendert.
- Ein Integrationstest mit dem echten Generatorparser belegt, dass die Vorgabe sowohl Storytext als auch Bildprompt erreicht.
- Die ältere Zwischenüberschrift wird ersetzt und bei leerer Vorgabe entfernt.
- Atomare Schreibvorgänge, Modus `0600` und Symlink-Abweisung funktionieren.
- Das Cinnamon-Schema referenziert die neue Seite und das neue Widget.
- Die systemd-Unit verwendet den installierten gemeinsamen CLI-Pfad.
- Der lokale Installer installiert den CLI-Helfer; der Uninstaller bewahrt ihn für die Generatorinstallation.
- `make check` kompiliert Kernmodul und GTK-Widget und führt die neuen Tests aus.

## Nicht-Ziele

- Keine Änderung an der Storyabschlusslogik.
- Keine Änderung an der OpenAI-Modellwahl.
- Keine nachträgliche Bearbeitung alter Storytexte.
- Keine direkte Stilkopie lebender Autorinnen oder Autoren; Namen dienen nur als Quellen für abstrahierte Merkmalsbeschreibungen.
- Keine Vermischung mit dem parallelen Webseiten-PR.
