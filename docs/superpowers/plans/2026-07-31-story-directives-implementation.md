---
tags:
  - wirtelprimpf
  - story-directives
  - implementation-plan
  - tdd
  - cinnamon
  - systemd
  - github-actions
type: implementation-plan
status: implemented-review-pending
date: 2026-07-31
aliases:
  - Story-Vorgaben Implementierungsplan
  - Story Directives Implementation Plan
created: 2026-07-31
title: Story-Vorgaben Implementation Plan
---

# Story-Vorgaben Implementation Plan

> **Ausführungsregel:** Für eine erneute oder weiterführende Umsetzung sind die Superpowers-Workflows für testgetriebene Entwicklung, Planpflege, Reviewaufnahme und Abschlussverifikation zu verwenden. Die Checkboxen dokumentieren den tatsächlich erreichten Stand.

## Ziel

Für jeden Wirtelprimpf-Storyband werden dauerhaft gespeicherte Vorgaben bereitgestellt. Die effektiv laufende Story und die zwei unmittelbar folgenden Storys sind in den Cinnamon-Einstellungen vollständig sichtbar und editierbar. Alle früheren Storys bleiben mit ihren gespeicherten Vorgaben sichtbar, sind aber technisch und visuell read-only.

Story III wird genau einmal mit den gewünschten Leitplanken vorbelegt:

- Actionstory;
- blutig, einschließlich sichtbarer Verletzungen, Blutspuren und harter Konsequenzen, sofern dies der Geschichte dient;
- düstere, kompromisslose Thriller- und Horrorenergie mit eskalierender Bedrohung und moralischem Druck;
- abstrahierte Motive von Markus Heitz und Richard Bachman beziehungsweise Stephen King, ohne konkrete Autorenstimme oder Formulierungen nachzuahmen;
- James-Bond-artige Mission, Täuschungen, Wendungen, ungewöhnliche Hilfsmittel, markante Schauplätze und ein gefährlicher Gegenspieler;
- Morticia und Gomez bleiben nicht vermenschlichte Hauskatzen mit grünen Augen.

## Architektur

Ein reines Python-Kernmodul verwaltet ein versioniertes JSON-Register, bestimmt aus dem bestehenden Story-State den effektiv laufenden Band und projiziert dessen vollständige Vorgabe in eine verwaltete Markdown-Kategorie mit genau einem auswählbaren Listeneintrag. Der vorhandene Generatorparser wählt diesen einzigen Eintrag deterministisch aus und übernimmt ihn sowohl in den Storytext- als auch in den Bildprompt.

Ein getrenntes Cinnamon-GTK-Widget verwendet dieselbe Kernlogik für Anzeige und Speicherung. Systemd ruft vor jedem Generatorlauf einen stabil installierten CLI-Helfer unter `~/.local/bin/wirtelprimpf-story-directives` auf. Damit bleiben Generator und Cinnamon-Applet unabhängig installierbar.

## Technischer Stack

- Python 3.11 oder neuer;
- ausschließlich Python-Standardbibliothek im Direktivenkern;
- GTK 3 und Cinnamon `JsonSettingsWidgets` für die Oberfläche;
- JSON-Register;
- Markdown-Promptkonfiguration;
- systemd --user;
- `unittest`;
- Make;
- GitHub Actions mit Python 3.12.

## Verbindliche Randbedingungen

- Repository: `H234598/Katzenbilder`.
- Feature-Branch: `agent/story-directives-ledger`.
- Zielbranch: `main`.
- Keine direkte Umsetzung auf `main`.
- Keine Änderung an `Sourcecode/wirtelprimpf_generator.py`.
- Keine neue externe Laufzeitabhängigkeit für die Direktivenfunktion.
- Nur der effektiv laufende Band und seine zwei direkten Folgebände dürfen gespeichert werden.
- Ein veraltetes Einstellungsfenster darf keinen inzwischen vergangenen Band verändern.
- Vergangene Storys sind read-only, nicht nur optisch deaktiviert.
- Die vollständige mehrzeilige Vorgabe muss Storytext und Bildprompt erreichen.
- Bestehende Promptabschnitte außerhalb der verwalteten Sektion bleiben erhalten.
- Fehler beim Laden, Validieren oder Schreiben blockieren den systemd-Lauf, statt still mit falschen Vorgaben fortzufahren.
- Dokumentation, Spezifikation und Plan bleiben Obsidian-kompatibles Markdown mit vollständigem Frontmatter.

## Betroffene Dateien

- [x] Create: `files/wirtelprimfgenerator@H234598/story_directives_core.py`
- [x] Create: `files/wirtelprimfgenerator@H234598/StoryDirectives.py`
- [x] Create: `tests/test_story_directives.py`
- [x] Modify: `files/wirtelprimfgenerator@H234598/settings-schema.json`
- [x] Modify: `Sourcecode/systemd-user/wirtelprimpf.service`
- [x] Modify: `scripts/install-local.sh`
- [x] Modify: `scripts/uninstall-local.sh`
- [x] Modify: `Makefile`
- [x] Modify: `Sourcecode/env.example`
- [x] Modify: `Sourcecode/README.md`
- [x] Create: `Sourcecode/STORY_DIRECTIVES.md`
- [x] Modify: `.github/workflows/check.yml`
- [x] Create: `docs/superpowers/specs/2026-07-31-story-directives-design.md`
- [x] Create: `docs/superpowers/plans/2026-07-31-story-directives-implementation.md`

## Task 1: Register, Story-III-Migration und Rollenmodell

### Schnittstellen

- `read_env_file(path: Path) -> dict[str, str]`
- `resolve_runtime_paths(env_path: Path) -> dict[str, Path]`
- `load_story_state(path: Path) -> dict[str, object]`
- `effective_current_volume(state: dict[str, object]) -> int`
- `load_ledger(path: Path, *, seed_story_iii: bool = True, now: str | None = None) -> dict[str, object]`
- `save_directives(path: Path, directives: dict[int, str], *, now: str | None = None, source: str = ...) -> dict[str, object]`
- `story_roles(current_volume: int, ledger: dict[str, object]) -> dict[str, list[dict[str, object]]]`

### Schritte

- [x] Failing Tests für Story-III-Seed, bewusstes Leeren, Home-Pfadauflösung, Storywechsel und Rollen schreiben.
- [x] RED verifizieren: Die Tests scheiterten ausschließlich an den noch fehlenden Kernfunktionen.
- [x] Schema-Version 1 implementieren.
- [x] Positive, konsistente Bandnummern und Feldtypen validieren.
- [x] Vorgabenlänge auf 20.000 Zeichen begrenzen.
- [x] Story III genau einmal initialisieren.
- [x] Benutzeränderungen vor späterem Überschreiben schützen.
- [x] Bewusst entfernte Story-III-Vorgabe nicht erneut erzeugen.
- [x] `$HOME` und `${HOME}` aus der Environment-Datei auflösen.
- [x] `pending_new_volume=true` als bereits anstehenden nächsten Band interpretieren.
- [x] Rollen `current`, `next`, `upcoming` und `past` erzeugen.
- [x] GREEN der Register-, Migrations- und Rollentests bestätigen.

## Task 2: Sichere Promptprojektion

### Schnittstellen

- `replace_managed_prompt_section(prompt_text: str, directive: str) -> str`
- `apply_active_directive(*, env_path: Path | None = None) -> dict[str, object]`
- CLI: `wirtelprimpf-story-directives apply|status --env-file ...`

### Schritte

- [x] Failing Tests für Einfügen, Ersetzen, Entfernen, atomare Schreibvorgänge, Modus `0600` und Symlink-Abweisung schreiben.
- [x] Erste Fassung als vermeintlich feste Sektion `## Zwingende Story-Vorgaben (verwaltet)` implementieren.
- [x] Echten Generatorparser in einen Integrationstest einbinden.
- [x] Parserfehler reproduzieren: Die feste Sektion erreichte den Bildprompt, aber nicht die Storytext-Konfiguration.
- [x] RED des echten Parser-Integrationstests bestätigen.
- [x] Projektion auf `## Story-Vorgaben (verwaltet)` umstellen.
- [x] Alle nichtleeren Eingabezeilen vollständig zu genau einem regulären Listeneintrag zusammenführen.
- [x] Deterministische Auswahl dieses einzigen Eintrags durch den bestehenden Parser bestätigen.
- [x] Storytext und Bildprompt mit dem echten Generatorparser verifizieren.
- [x] Die ältere Zwischenüberschrift beim nächsten Anwenden automatisch entfernen und migrieren.
- [x] Leere Vorgabe entfernt die verwaltete Sektion vollständig.
- [x] Bestehende andere Promptkategorien bleiben erhalten.

## Task 3: Atomare Persistenz und Sicherheit

- [x] Register und Promptdatei über temporäre Datei im Zielverzeichnis und `os.replace` schreiben.
- [x] Zielmodus `0600` nach jedem verwalteten Schreibvorgang setzen.
- [x] Symlink-Ziele für Environment, Story-State, Register und Promptdatei ablehnen.
- [x] Ungültiges JSON mit klarer Fehlermeldung ablehnen.
- [x] Nicht reguläre Dateien und unsichere Elternpfade ablehnen.
- [x] CLI bei Fehlern mit Exitcode ungleich null beenden.
- [x] systemd-`ExecStartPre` dadurch als blockierendes Sicherheitsgate verwenden.

## Task 4: Cinnamon-Oberfläche und read-only Vertrag

### Schnittstellen

- Custom-Widget: `StoryDirectivesEditor(SettingsWidget)`
- Sicheres Speichern: `save_editable_window(path, *, current_volume, directives, ...)`

### Schritte

- [x] Failing statische Tests für die neue Settings-Seite und Widgetreferenz schreiben.
- [x] Neue Seite `Story-Vorgaben` in `settings-schema.json` ergänzen.
- [x] Drei editierbare Karten für laufende, nächste und übernächste Story implementieren.
- [x] Rolle, römische Bandnummer und vollständigen Vorgabentext anzeigen.
- [x] Vergangene Bände absteigend und vollständig read-only darstellen.
- [x] Fehlende historische Vorgaben als `Keine gespeicherten Vorgaben.` sichtbar machen.
- [x] Änderungszeitpunkt und Quelle anzeigen, sofern vorhanden.
- [x] Gemeinsames Speichern und bewusstes Neuladen bereitstellen.
- [x] Failing Regressionstest für ein veraltetes geöffnetes Dreierfenster schreiben.
- [x] Kernseitigen Fenster-Guard implementieren: erlaubt ist exakt `{current, current+1, current+2}`.
- [x] Bei einem während der Bearbeitung erfolgten Storywechsel das Speichern verweigern und die Ansicht neu laden.
- [x] Dadurch nachträgliche Änderungen an inzwischen vergangenen Bänden technisch verhindern.

## Task 5: Unabhängige Runtime- und Installationsintegration

### Schnittstellen

- Installierter Helfer: `~/.local/bin/wirtelprimpf-story-directives`
- systemd: `ExecStartPre=<venv-python> <shared-cli> apply --env-file ...`

### Schritte

- [x] Failing Regressionstests für systemd- und Installationspfad schreiben.
- [x] Fehler der ersten Fassung reproduzieren: systemd hing vom internen Cinnamon-Applet-Pfad ab.
- [x] Gemeinsamen CLI-Helfer über `scripts/install-local.sh` installieren.
- [x] systemd auf den stabilen gemeinsamen CLI-Pfad umstellen.
- [x] Applet-Uninstaller bewahrt den gemeinsam genutzten Helfer absichtlich für eine mögliche eigenständige Generatorinstallation.
- [x] Manuelle Generatorinstallation in `Sourcecode/STORY_DIRECTIVES.md` dokumentieren.
- [x] Primäre Installationsanleitung `Sourcecode/README.md` mit Obsidian-Frontmatter versehen und vollständig aktualisieren.
- [x] In der Hauptanleitung den CLI-Helfer ausdrücklich vor der systemd-Unit installieren.
- [x] `WIRTELPRIMPF_STORY_DIRECTIVES` im Story-Modus dokumentieren.
- [x] Direkten Storylauf so dokumentieren, dass die Vorgabe wie bei systemd zuerst angewendet wird.
- [x] Statische Regression ergänzen, die Installationsquelle, Zielpfad und Reihenfolge in `Sourcecode/README.md` prüft.

## Task 6: Repository-Gate, Dokumentation und Pull Request

- [x] `Makefile` um Kompilierung von Kernmodul und GTK-Widget ergänzen.
- [x] `Makefile` um Ausführung von `tests/test_story_directives.py` ergänzen.
- [x] Bestehenden `.github/workflows/check.yml` reproduzierbar machen.
- [x] Vollständigen Checkout des bildlastigen Repositories durch Sparse Checkout ersetzen.
- [x] Python 3.12 über `actions/setup-python@v6` verwenden.
- [x] Laufzeitabhängigkeiten aus `Sourcecode/requirements.txt` installieren.
- [x] Repository-Berechtigungen auf `contents: read` begrenzen.
- [x] Timeout und Concurrency mit Abbruch veralteter Läufe ergänzen.
- [x] Einen zunächst zusätzlich angelegten doppelten Workflow nach erfolgreicher Evidenz wieder entfernen.
- [x] `Sourcecode/env.example`, Betriebsdokumentation, Designspezifikation und diesen Plan pflegen.
- [x] Branch-Diff auf Scope, Secrets und unbeabsichtigte Binärdateien prüfen.
- [x] Draft-PR #2 gegen `main` öffnen.
- [x] PR-Text mit Architektur, Story-III-Vorgabe, Migration, Sicherheitsvertrag und Tests pflegen.

## Task 7: Testgetriebene Abschlusskorrekturen

- [x] Integrationsfehler 1 finden: systemd-Abhängigkeit vom internen Applet-Pfad.
- [x] Zuerst fehlschlagenden Regressionstest schreiben.
- [x] Gemeinsamen CLI-Pfad implementieren und Test grün machen.
- [x] Integrationsfehler 2 finden: feste Promptsektion erreicht nur den Bildprompt.
- [x] Zuerst fehlschlagenden echten Parser-Integrationstest schreiben.
- [x] Reguläre Ein-Eintrag-Kategorie implementieren und Test grün machen.
- [x] Integrationsfehler 3 finden: veraltetes offenes Einstellungsfenster könnte einen inzwischen vergangenen Band speichern.
- [x] Zuerst fehlschlagenden Fenster-Regressions­test schreiben.
- [x] Kernseitigen Dreierfenster-Guard implementieren und Test grün machen.
- [x] Integrationsfehler 4 finden: Die primäre manuelle Generatoranleitung installierte den neuen systemd-Helfer noch nicht.
- [x] Statische README-Regression ergänzen.
- [x] Hauptinstallationsanleitung korrigieren und Repository-Gate grün machen.

## Task 8: Abschlussverifikation

### Feature- und Repositorytests

- [x] Aktueller synthetischer Pull-Request-Merge-Checkout wurde durch GitHub Actions geprüft.
- [x] Python 3.12.13 wurde verwendet.
- [x] Reale Laufzeitabhängigkeiten wurden aus `Sourcecode/requirements.txt` installiert.
- [x] JSON-Prüfung von `metadata.json` und `settings-schema.json` bestand.
- [x] Python-Kompilierung des Generators, bestehender Helfer, Direktivenkerns und GTK-Widgets bestand.
- [x] Alle bestehenden Repositorytests bestanden.
- [x] `tests/test_story_directives.py` bestand mit **17 von 17 Tests**.
- [x] Vollständiges `make check` bestand auf dem synthetischen Merge-Commit.
- [x] GitHub-Actions-Lauf `check` Nummer 55 schloss erfolgreich ab.

### Reviews und externe Gates

- [x] Ein vollständiger CodeRabbit-Review wurde ausdrücklich über `@coderabbitai review` ausgelöst.
- [ ] CodeRabbit-Endergebnis für den endgültigen Head bestätigen.
- [ ] Eventuelle CodeRabbit-Threads nachvollziehbar bearbeiten und auflösen.
- [ ] Qlty-Endergebnis für den endgültigen Head bestätigen.

Der PR bleibt bis zur bestätigten externen Gate-Evidenz im Draftstatus. Ein zuvor lediglich wegen des Draftstatus übersprungener CodeRabbit-Status wird ausdrücklich nicht als bestandener Review gewertet.

## Umsetzungsevidenz

- Initiales TDD-RED: 11 erwartete Fehler durch fehlende Kern-, UI- und Integrationskomponenten.
- Erster grüner Kernstand: 8 von 8 Tests.
- Erweiterter Stand: 13 von 13 Tests.
- Installationsregression zuerst rot, danach gemeinsamer CLI-Pfad und systemd-Entkopplung grün.
- Parserregression zuerst rot, danach Storytext und Bildprompt mit echtem Parser grün.
- Read-only-Rennen zuerst rot, danach kernseitiger Dreierfenster-Guard grün.
- Primäre Installationsanleitung zuerst unvollständig, danach durch statische Regression abgesichert.
- Aktueller Stand: 17 von 17 Story-Vorgaben-Tests grün.
- Vollständiges Repository-`make check` grün.
- Python-Syntax, JSON-Syntax, CLI-Smoke-Test und Secret-Scan grün.
- Der bestehende GitHub-Actions-Workflow ist sparse, reproduzierbar und grün.
- Draft-PR #2 ist geöffnet, konfliktfrei und mergebar.
- `main` blieb unverändert.
