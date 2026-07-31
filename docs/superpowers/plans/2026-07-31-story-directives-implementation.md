---
tags:
  - wirtelprimpf
  - story-directives
  - implementation-plan
  - tdd
  - cinnamon
  - systemd
type: implementation-plan
status: implemented-awaiting-remote-ci
date: 2026-07-31
aliases:
  - Story-Vorgaben Implementierungsplan
  - Story Directives Implementation Plan
created: 2026-07-31
title: Story-Vorgaben Implementation Plan
---

# Story-Vorgaben Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pro Story-Band dauerhaft gespeicherte Vorgaben bereitstellen, Story III vorbefüllen, die laufende und zwei kommende Storys editierbar darstellen und vergangene Storys technisch read-only anzeigen.

**Architecture:** Ein reines Python-Kernmodul verwaltet ein versioniertes JSON-Register, bestimmt aus dem Story-State den effektiv laufenden Band und projiziert dessen Vorgabe in eine verwaltete Markdown-Kategorie mit genau einem auswählbaren Listeneintrag. Dadurch übernimmt der bestehende Generatorparser die vollständige Vorgabe deterministisch sowohl in den Storytext- als auch in den Bildprompt. Ein getrenntes Cinnamon-GTK-Widget verwendet dieselbe Kernlogik; systemd ruft vor jedem Generatorlauf einen stabil installierten CLI-Helfer unter `~/.local/bin/wirtelprimpf-story-directives` auf.

**Tech Stack:** Python 3.11+, Standardbibliothek, GTK 3/Cinnamon `JsonSettingsWidgets`, JSON, Markdown, systemd --user, unittest, Make, GitHub Actions.

## Global Constraints

- Repository: `H234598/Katzenbilder`.
- Feature-Branch: `agent/story-directives-ledger`; keine Umsetzung auf `main`.
- Story III: Actionstory, blutig, abstrahierte Thriller-/Horror-Merkmale von Markus Heitz und Richard Bachman (Stephen King), kombiniert mit James-Bond-artigen Spionage-/Actionelementen.
- Keine konkrete Nachahmung einer Autorenstimme oder unverwechselbarer Formulierungen.
- Editierbar sind ausschließlich effektiv laufender Band, nächster Band und übernächster Band.
- Alle Bände kleiner als der effektiv laufende Band sind read-only.
- Ein veraltetes Einstellungsfenster darf keinen inzwischen vergangenen Band speichern.
- Bestehende lokale Promptregeln außerhalb der verwalteten Sektion bleiben erhalten.
- Die vollständige mehrzeilige Vorgabe muss Storytext und Bildprompt erreichen.
- Keine neue externe Laufzeitabhängigkeit.
- Keine Änderung an `Sourcecode/wirtelprimpf_generator.py`.
- Generator und Cinnamon-Applet dürfen unabhängig installiert sein; systemd darf nicht von einem internen Applet-Pfad abhängen.
- Alle Berichte, Spezifikationen und Pläne bleiben vollständiges Obsidian-Markdown mit Frontmatter.

---

## Dateistruktur

- Create: `files/wirtelprimfgenerator@H234598/story_directives_core.py` — Datenmodell, sichere Persistenz, State-Auflösung, Promptprojektion und CLI.
- Create: `files/wirtelprimfgenerator@H234598/StoryDirectives.py` — dynamisches GTK-Widget.
- Create: `tests/test_story_directives.py` — Verhaltens-, Parser- und Installationsintegrationstests.
- Modify: `files/wirtelprimfgenerator@H234598/settings-schema.json` — neue Seite und Custom-Widget.
- Modify: `Sourcecode/systemd-user/wirtelprimpf.service` — blockierendes `ExecStartPre` über den gemeinsamen CLI-Pfad.
- Modify: `scripts/install-local.sh` — Applet und gemeinsamen CLI-Helfer installieren.
- Modify: `scripts/uninstall-local.sh` — gemeinsame CLI bewusst für eine mögliche Generatorinstallation erhalten.
- Modify: `Makefile` — Kompilierung und Testlauf ergänzen.
- Modify: `Sourcecode/env.example` — optionalen Registerpfad dokumentieren.
- Create: `Sourcecode/STORY_DIRECTIVES.md` — Datenmodell, UI, Installation, systemd- und manuellen Ablauf dokumentieren.
- Create: `.github/workflows/wirtelprimpf-check.yml` — Repository-Check auf Push, Pull Request und manuelle Ausführung.
- Create: `docs/superpowers/specs/2026-07-31-story-directives-design.md` — technische Spezifikation.
- Create: `docs/superpowers/plans/2026-07-31-story-directives-implementation.md` — dieser gepflegte Plan.

## Task 1: Register, Story-III-Seed und Rollenmodell

**Interfaces:**

- `read_env_file(path: Path) -> dict[str, str]`
- `resolve_runtime_paths(env_path: Path) -> dict[str, Path]`
- `load_story_state(path: Path) -> dict[str, object]`
- `effective_current_volume(state: dict[str, object]) -> int`
- `load_ledger(path: Path, *, seed_story_iii: bool = True, now: str | None = None) -> dict[str, object]`
- `save_directives(path: Path, directives: dict[int, str], *, now: str | None = None, source: str = ...) -> dict[str, object]`
- `story_roles(current_volume: int, ledger: dict[str, object]) -> dict[str, list[dict[str, object]]]`

- [x] **Step 1: Failing Tests für Seed, bewusstes Leeren, Home-Pfade, Storywechsel und Rollen schreiben.**
- [x] **Step 2: RED verifizieren.** Die Tests scheiterten ausschließlich an den noch fehlenden Kernfunktionen.
- [x] **Step 3: Schema-Version 1, Story-III-Einmalmigration, Validierung und Rollenmodell implementieren.**
- [x] **Step 4: GREEN verifizieren.** Story III wird vorbelegt, Benutzeränderungen werden nicht überschrieben und eine bewusst entfernte Vorgabe wird nicht erneut erzeugt.

## Task 2: Sichere Promptprojektion in Storytext und Bildprompt

**Interfaces:**

- `replace_managed_prompt_section(prompt_text: str, directive: str) -> str`
- `apply_active_directive(*, env_path: Path | None = None) -> dict[str, object]`
- CLI: `wirtelprimpf-story-directives apply|status --env-file ...`

- [x] **Step 1: Failing Tests für Einfügen, Ersetzen, Entfernen, atomare Schreibvorgänge, Modus `0600` und Symlink-Abweisung schreiben.**
- [x] **Step 2: Erste Implementierung als vermeintlich feste `Zwingende`-Sektion erstellen.**
- [x] **Step 3: Echten Generatorparser in einen Integrationstest einbinden.** Der Test zeigte, dass eine fixe Sektion nur den Bildprompt, nicht den Storytext erreicht.
- [x] **Step 4: RED des Parser-Integrationstests verifizieren.** Die Storytext-Konfiguration enthielt die Vorgabe nicht.
- [x] **Step 5: Projektion auf `## Story-Vorgaben (verwaltet)` mit genau einem regulären Listeneintrag korrigieren.** Alle nichtleeren Eingabezeilen werden vollständig zu diesem einen deterministisch ausgewählten Eintrag zusammengeführt.
- [x] **Step 6: Legacy-Migration ergänzen.** Eine ältere Zwischenüberschrift `## Zwingende Story-Vorgaben (verwaltet)` wird entfernt und durch die korrekte Sektion ersetzt.
- [x] **Step 7: GREEN mit dem echten Parser verifizieren.** Action-, Blut- und Missionsvorgaben erreichen Storytext und Bildprompt.

## Task 3: Cinnamon-Editor, Sichtbarkeit und read-only Vertrag

**Interfaces:**

- Custom-Widget: `StoryDirectivesEditor(SettingsWidget)`
- Sicheres Speichern: `save_editable_window(path, *, current_volume, directives, ...)`

- [x] **Step 1: Failing statische Tests für die neue Settings-Seite und Widgetreferenz schreiben.**
- [x] **Step 2: Drei editierbare Karten für laufend, nächste und übernächste Story implementieren.**
- [x] **Step 3: Vollständiges read-only Archiv vergangener Storys implementieren.** Fehlende Altvorgaben werden als `Keine gespeicherten Vorgaben.` sichtbar gemacht.
- [x] **Step 4: Failing Regressionstest für ein veraltetes geöffnetes Dreierfenster schreiben.**
- [x] **Step 5: Kernseitigen Fenster-Guard implementieren.** Erlaubt ist exakt `{current, current+1, current+2}`; andernfalls wird der Schreibvorgang verweigert.
- [x] **Step 6: UI-Verhalten für einen Storywechsel implementieren.** Die Ansicht wird neu geladen und fordert zur erneuten Eingabe im aktuellen Fenster auf.
- [x] **Step 7: Syntax- und Verhaltenstests verifizieren.**

## Task 4: Unabhängige Runtime- und Installationsintegration

**Interfaces:**

- Installierter Helfer: `~/.local/bin/wirtelprimpf-story-directives`
- systemd: `ExecStartPre=<venv-python> <shared-cli> apply --env-file ...`

- [x] **Step 1: Failing Regressionstests für systemd- und Installationspfad schreiben.** Die erste Fassung hing vom internen Cinnamon-Applet-Pfad ab.
- [x] **Step 2: RED verifizieren.** Eine reine Generatorinstallation hätte den Helfer nicht besessen.
- [x] **Step 3: `install-local.sh` um die Installation des gemeinsamen CLI-Helfers ergänzen.**
- [x] **Step 4: systemd auf den stabilen gemeinsamen CLI-Pfad umstellen.**
- [x] **Step 5: Uninstaller-Vertrag dokumentieren.** Das Applet wird entfernt, der von systemd möglicherweise weiter benötigte Helfer bleibt bestehen.
- [x] **Step 6: Manuelle Generatorinstallation in der technischen Dokumentation vollständig beschreiben.**
- [x] **Step 7: GREEN der Installationsintegration verifizieren.**

## Task 5: Repository-Gates, Dokumentation und Pull Request

- [x] **Step 1: `Makefile` um Kompilierung von Kern/UI und Ausführung der neuen Tests ergänzen.**
- [x] **Step 2: GitHub-Actions-Workflow mit Sparse Checkout, Python 3.12, Laufzeitabhängigkeiten und `make check` erstellen.**
- [x] **Step 3: `env.example`, technische Dokumentation, Designspezifikation und diesen Plan pflegen.**
- [x] **Step 4: Branch-Diff auf Scope, Secrets und unbeabsichtigte Binärdateien prüfen.**
- [x] **Step 5: Draft-PR #2 gegen `main` öffnen.**
- [x] **Step 6: Review-Diff auf Integrationsfehler untersuchen und beide gefundenen Fehler testgetrieben beheben.**

## Task 6: Abschlussverifikation

- [x] **Step 1: Featuretests frisch ausführen.**

Run:

```bash
python3 tests/test_story_directives.py -v
```

Ergebnis: 16 Tests, 16 bestanden, 0 Fehler.

- [x] **Step 2: Python-Syntax frisch prüfen.**

Run:

```bash
python3 -m py_compile \
  files/wirtelprimfgenerator@H234598/story_directives_core.py \
  files/wirtelprimfgenerator@H234598/StoryDirectives.py
```

Ergebnis: Exit 0.

- [x] **Step 3: Cinnamon-Settings-JSON prüfen.**

Run:

```bash
python3 -m json.tool \
  files/wirtelprimfgenerator@H234598/settings-schema.json >/dev/null
```

Ergebnis: Exit 0.

- [x] **Step 4: CLI-Smoke-Test ausführen.**

Run:

```bash
python3 files/wirtelprimfgenerator@H234598/story_directives_core.py --help
```

Ergebnis: Exit 0; `apply` und `status` sichtbar.

- [x] **Step 5: Secret-Pattern-Scan über alle Featuredateien ausführen.**

Ergebnis: keine API-Schlüssel, Tokens oder Zugangsdaten gefunden.

- [ ] **Step 6: Vollständiges `make check` im GitHub-Actions-Checkout bestätigen.**

Der Workflow ist implementiert; der endgültige Remote-Lauf muss am aktuellen PR-Head noch als Erfolg erscheinen.

- [ ] **Step 7: Externe Quality-Gates am aktuellen PR-Head bestätigen.**

CodeRabbit und Qlty werden nach jedem neuen Commit erneut ausgewertet. Der PR bleibt bis zur endgültigen grünen Evidenz Draft.

## Umsetzungsevidenz

- Initiales TDD-RED: 11 erwartete Fehler durch fehlende Kern-, UI- und Integrationskomponenten.
- Zwischenstände: 8/8, anschließend 13/13 Featuretests grün.
- Installationsregression: zuerst rot, danach gemeinsamer CLI-Pfad und systemd-Entkopplung grün.
- Parserregression: zuerst rot, weil die Vorgabe nur den Bildprompt erreichte; danach echter Generatorparser für Storytext und Bildprompt grün.
- Read-only-Rennen: zuerst rot, danach kernseitiger Dreierfenster-Guard grün.
- Aktueller lokaler Stand: 16/16 Featuretests grün.
- Python-Syntax, JSON-Syntax, CLI-Smoke-Test und Secret-Scan grün.
- Draft-PR #2 ist geöffnet und bleibt bis zur abschließenden Remote-CI-Evidenz im Draftstatus.
