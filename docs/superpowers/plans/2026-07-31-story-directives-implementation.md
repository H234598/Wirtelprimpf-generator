---
tags:
  - wirtelprimpf
  - story-directives
  - implementation-plan
  - tdd
  - cinnamon
type: implementation-plan
status: verification-in-progress
date: 2026-07-31
aliases:
  - Story-Vorgaben Implementierungsplan
  - Story Directives Implementation Plan
created: 2026-07-31
title: Story-Vorgaben Implementation Plan
---

# Story-Vorgaben Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pro Story-Band dauerhaft gespeicherte Vorgaben bereitstellen, Story III vorbefüllen, die laufende und zwei kommende Storys editierbar darstellen und vergangene Storys read-only anzeigen.

**Architecture:** Ein neues reines Python-Kernmodul verwaltet ein versioniertes JSON-Register und projiziert die Vorgabe des effektiv laufenden Bandes in einen festen Abschnitt der vorhandenen Markdown-Promptdatei. Ein separates Cinnamon-GTK-Widget nutzt dieses Modul für die dynamische Oberfläche. Der bestehende Generator bleibt unverändert; systemd wendet die Vorgabe per `ExecStartPre` unmittelbar vor jedem Lauf an.

**Tech Stack:** Python 3.11+, Standardbibliothek, GTK 3/Cinnamon `JsonSettingsWidgets`, JSON, Markdown, systemd --user, unittest, Make.

## Global Constraints

- Repository: `H234598/Katzenbilder`.
- Feature-Branch: `agent/story-directives-ledger`; keine Umsetzung auf `main`.
- Story III: Actionstory, blutig, abstrahierte Thriller-/Horror-Merkmale von Markus Heitz und Richard Bachman (Stephen King), kombiniert mit James-Bond-artigen Spionage-/Actionelementen.
- Keine konkrete Nachahmung einer Autorenstimme.
- Editierbar sind ausschließlich effektiv laufender Band, nächster Band und übernächster Band.
- Alle Bände kleiner als der effektiv laufende Band sind read-only.
- Bestehende lokale Promptregeln außerhalb der verwalteten Sektion bleiben byteinhaltlich unverändert, abgesehen von normalisierter Endzeile am Dateiende.
- Keine neue externe Laufzeitabhängigkeit.
- Keine Änderung an `Sourcecode/wirtelprimpf_generator.py`.
- Alle Berichte und Pläne bleiben vollständiges Obsidian-Markdown mit Frontmatter.

---

## Dateistruktur

- Create: `files/wirtelprimfgenerator@H234598/story_directives_core.py` — Datenmodell, sichere Persistenz, State-Auflösung, Promptprojektion und CLI.
- Create: `files/wirtelprimfgenerator@H234598/StoryDirectives.py` — dynamisches GTK-Widget.
- Create: `tests/test_story_directives.py` — verhaltensbasierte Tests für Kernlogik und Rollenmodell.
- Modify: `files/wirtelprimfgenerator@H234598/settings-schema.json` — neue Seite und Custom-Widget.
- Modify: `Sourcecode/systemd-user/wirtelprimpf.service` — `ExecStartPre` für aktive Vorgabe.
- Modify: `Makefile` — Kompilierung und Testlauf ergänzen.
- Modify: `Sourcecode/env.example` — optionalen Registerpfad dokumentieren.
- Create: `Sourcecode/STORY_DIRECTIVES.md` — Datenmodell, UI, systemd- und manuellen Ablauf dokumentieren.
- Create: `.github/workflows/wirtelprimpf-check.yml` — sparsamer Repository-Check auf Push und Pull Request.
- Create: `docs/superpowers/specs/2026-07-31-story-directives-design.md` — freigegebene technische Spezifikation.
- Create: `docs/superpowers/plans/2026-07-31-story-directives-implementation.md` — dieser Plan.

### Task 1: Kernverhalten testgetrieben festlegen

**Files:**
- Create: `tests/test_story_directives.py`
- Create: `files/wirtelprimfgenerator@H234598/story_directives_core.py`

**Interfaces:**
- Produces: `read_env_file(path: Path) -> dict[str, str]`
- Produces: `resolve_runtime_paths(env_path: Path) -> dict[str, Path]`
- Produces: `load_story_state(path: Path) -> dict[str, object]`
- Produces: `effective_current_volume(state: Mapping[str, object]) -> int`
- Produces: `load_ledger(path: Path, *, seed_story_iii: bool = True) -> dict[str, object]`
- Produces: `save_directives(path: Path, updates: Mapping[int, str], *, now: str | None = None) -> dict[str, object]`
- Produces: `story_roles(current_volume: int, ledger: Mapping[str, object]) -> dict[str, object]`
- Produces: `apply_active_directive(...) -> dict[str, object]`

- [x] **Step 1: Failing Tests für Seed, Rollen und wirksamen Band schreiben**

```python
def test_story_iii_seed_is_created_without_overwriting_user_value(): ...
def test_pending_new_volume_advances_effective_volume(): ...
def test_only_current_and_next_two_are_editable(): ...
```

- [x] **Step 2: RED verifizieren**

Run: `python3 tests/test_story_directives.py -v`
Expected: Import- oder Attributfehler, weil `story_directives_core.py` noch fehlt.

- [x] **Step 3: Minimales Register-, State- und Rollenmodell implementieren**

Implementiere Schema-Version 1, positive Bandnummern, Story-III-Seed, sichere JSON-Lesevorgänge, `pending_new_volume`-Semantik und die Rollen `current`, `next`, `upcoming`, `past`.

- [x] **Step 4: GREEN für Seed und Rollen verifizieren**

Run: `python3 tests/test_story_directives.py -v`
Expected: Seed-/State-/Rollentests PASS; Promptprojektionstests fehlen noch.

### Task 2: Promptprojektion und sichere Persistenz

**Files:**
- Modify: `tests/test_story_directives.py`
- Modify: `files/wirtelprimfgenerator@H234598/story_directives_core.py`

**Interfaces:**
- Consumes: Register- und State-Funktionen aus Task 1.
- Produces: `render_managed_prompt_section(directive: str) -> str`
- Produces: `replace_managed_prompt_section(prompt_text: str, directive: str) -> str`
- Produces: CLI `story_directives_core.py apply`.

- [x] **Step 1: Failing Tests für Einfügen, Ersetzen, Entfernen und atomaren Schreibschutz ergänzen**

```python
def test_active_directive_is_appended_as_zwingende_fixed_section(): ...
def test_existing_managed_section_is_replaced_once(): ...
def test_blank_directive_removes_managed_section(): ...
def test_apply_uses_pending_next_volume(): ...
```

- [x] **Step 2: RED verifizieren**

Run: `python3 tests/test_story_directives.py -v`
Expected: FAIL wegen fehlender Promptfunktionen.

- [x] **Step 3: Minimale Promptprojektion implementieren**

Die Funktion erkennt exakt `## Zwingende Story-Vorgaben (verwaltet)`, entfernt den Abschnitt bis zur nächsten `##`-Überschrift oder EOF und hängt bei nichtleerem Text jede nichtleere Direktivenzeile als Bullet an. Atomare Schreibvorgänge lehnen Symlinks ab und setzen `0600`.

- [x] **Step 4: GREEN und CLI-Smoke-Test verifizieren**

Run: `python3 tests/test_story_directives.py -v`
Expected: Alle Kerntests PASS.

Run: `python3 files/wirtelprimfgenerator@H234598/story_directives_core.py --help`
Expected: Exit 0 und Unterbefehl `apply` sichtbar.

### Task 3: Cinnamon-Editor und Settings-Schema

**Files:**
- Create: `files/wirtelprimfgenerator@H234598/StoryDirectives.py`
- Modify: `files/wirtelprimfgenerator@H234598/settings-schema.json`
- Modify: `tests/test_story_directives.py`
- Modify: `tests/test_settings_schema.py`

**Interfaces:**
- Consumes: `resolve_runtime_paths`, `load_ledger`, `save_directives`, `story_roles`, `apply_active_directive` aus dem Kernmodul.
- Produces: Custom-Widget-Klasse `StoryDirectivesEditor(SettingsWidget)`.

- [x] **Step 1: Failing statische Tests für neue Settings-Seite und Widgetreferenz schreiben**

Der Test lädt `settings-schema.json` und verlangt `story-directives-page`, `story-directives-section` und `StoryDirectives.py`/`StoryDirectivesEditor`.

- [x] **Step 2: RED verifizieren**

Run: `python3 tests/test_settings_schema.py -v && python3 tests/test_story_directives.py -v`
Expected: FAIL, weil Seite und Widget fehlen.

- [x] **Step 3: GTK-Widget und Schema minimal implementieren**

Das Widget zeigt drei editierbare TextViews für laufend/nächste/übernächste Story, speichert sie gemeinsam und zeigt vergangene Bände in nicht editierbaren TextViews. Beim Speichern wird die aktive Promptdatei sofort aktualisiert.

- [x] **Step 4: Syntax und statische Tests verifizieren**

Run: `python3 -m py_compile files/wirtelprimfgenerator@H234598/story_directives_core.py files/wirtelprimfgenerator@H234598/StoryDirectives.py`
Expected: PASS.

Run: `python3 tests/test_settings_schema.py -v && python3 tests/test_story_directives.py -v`
Expected: PASS.

### Task 4: systemd-Integration, Make-Gate und Dokumentation

**Files:**
- Modify: `Sourcecode/systemd-user/wirtelprimpf.service`
- Modify: `Makefile`
- Modify: `Sourcecode/env.example`
- Create: `Sourcecode/STORY_DIRECTIVES.md`
- Create: `.github/workflows/wirtelprimpf-check.yml`

**Interfaces:**
- Consumes: CLI `story_directives_core.py apply`.
- Produces: blockierendes `ExecStartPre` vor jedem systemd-Generatorlauf.

- [x] **Step 1: Failing Integrationsassertion ergänzen**

Der Test liest die Service-Datei und verlangt den Aufruf des Kernmoduls mit `apply`; der Makefile-Test verlangt Kompilierung und Ausführung des neuen Tests.

- [x] **Step 2: RED verifizieren**

Run: `python3 tests/test_story_directives.py -v`
Expected: FAIL wegen fehlender Service-/Makefile-Integration.

- [x] **Step 3: Service, Makefile und Konfigurationsdokumentation implementieren**

`ExecStartPre` verwendet dieselbe venv-Python-Installation wie `ExecStart`. `env.example` dokumentiert `WIRTELPRIMPF_STORY_DIRECTIVES`. `STORY_DIRECTIVES.md` beschreibt automatische und manuelle Anwendung, Archivsemantik sowie den read-only-Vertrag. Der Workflow führt `make check` mit Sparse Checkout aus.

- [ ] **Step 4: Vollständige Repository-Verifikation**

Run: `make check` im vollständigen GitHub-Checkout
Expected: alle bestehenden und neuen Checks PASS.

Run: `git diff --check`
Expected: keine Ausgabe, Exit 0.

### Task 5: Reviewfähigen Pull Request herstellen

**Files:**
- Modify: `docs/superpowers/plans/2026-07-31-story-directives-implementation.md`

**Interfaces:**
- Consumes: vollständig grüne Umsetzung.
- Produces: Draft-PR gegen `main`.

- [x] **Step 1: Planstatus und Checkboxen mit realer Evidenz aktualisieren**

Alle tatsächlich abgeschlossenen Schritte werden `[x]`; Prüfkommandos und Ergebnisse werden im Abschlussabschnitt dokumentiert.

- [x] **Step 2: Branch-Diff auf Scope, Secrets und unbeabsichtigte Binärdateien prüfen**

Run: `git diff --stat main...HEAD` und `git diff --check main...HEAD`.

- [x] **Step 3: Draft-PR öffnen**

Titel: `feat(story): add per-volume directives and read-only history`

Der PR-Text enthält Ziel, Architektur, Story-III-Vorgabe, Migrationsverhalten, UI-Vertrag und exakte Verifikation.

## Umsetzungsevidenz

- TDD-RED: 11 erwartete Fehler durch fehlende Kern-, UI- und Integrationsdateien.
- TDD-GREEN Kern: zunächst 8/8 Verhaltenstests bestanden.
- Ergänzende Regressionen: `$HOME`-/`${HOME}`-Pfadauflösung sowie einmalige Story-III-Migration wurden jeweils zuerst rot und danach grün implementiert.
- Aktueller lokaler Stand: 13/13 neue Tests bestanden.
- `python3 -m py_compile` für `story_directives_core.py` und `StoryDirectives.py`: bestanden.
- `python3 -m json.tool` für `settings-schema.json`: bestanden.
- CLI-Smoke-Test `story_directives_core.py --help`: bestanden.
- Secret-Pattern-Scan über den Feature-Baum: keine Treffer.
- Draft-PR #2 gegen `main` ist geöffnet; Branch-Diff umfasst ausschließlich die Story-Vorgaben-Funktion und ihre Prüf-/Dokumentationsdateien.
- CodeRabbit meldet Erfolg; Qlty und vollständiges Repository-`make check` sind noch in Prüfung.
