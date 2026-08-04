# Task 6 Report: CatGPT Light mit stillem Static-Fallback

## Ergebnis

- Light wird nur durch den byte-exakten Endpoint `https://catgpt.wirtelprimpf.telacore.org/v1/chat` aktiviert.
- Ohne gültigen Endpoint bleibt CatGPT effektiv Static, der Switch deaktiviert und CSP bei `connect-src 'none'`.
- Light sendet einen gehärteten einzelnen POST und fällt bei jedem Fehler ohne sichtbaren Hinweis exakt einmal auf Static zurück.
- Session-Historie enthält nur strikt validierte `ChatMessage`-Objekte und höchstens die neuesten zehn Einträge.
- Mode-Wechsel trennt fehlertolerant Storage-Akquise, Mode-Persistenz, Session-Löschung und Event-Dispatch; laufende Generationen werden invalidiert und alte Requests verändern weder Chat noch Controls.
- Wenn bereits der globale `sessionStorage`-Getter fehlschlägt, startet das Widget mit leerer Historie.

## TDD-Nachweise

### RED

1. Initialer scoped Lauf der neuen Endpoint-, History-, Provider-, Mode- und Komponenten-Vertragstests: Exit 1, 7 fehlgeschlagen, 1 bestanden. Ursachen waren fehlende neue Module/Exports und der alte Static-only-Komponentenvertrag.
2. Funktionaler Mode-Fehlertest mit echtem `EventTarget`: Exit 1, `TypeError: announce is not a function`. Danach dispatcht der Helper selbst den echten `CustomEvent`.
3. Striktes History-/Payload-Schema: Exit 1, 2 fehlgeschlagen. Zusätzliche Felder wurden zunächst aus Storage übernommen und im Light-Payload gesendet; danach strikte Schema-Prüfung und Payload-Projektion.
4. Review-Race-Test: Exit 1, 1 fehlgeschlagen. Stale Requests konnten Controls eines neueren Requests aktivieren; danach Generation-Guard im `finally`.
5. Getter-Akquise-Regression: scoped Exit 1, 3 fehlgeschlagen, 5 bestanden. `localStorage`-Getterfehler verhinderte Session-Löschung/Event und der `sessionStorage`-Getter wurde bei Widget-Initialisierung nicht fail-closed akquiriert; danach verzögerte Getter in getrennten `try`-Grenzen.

### GREEN

- `npm --prefix web test`: 34 Tests, 34 bestanden, 0 fehlgeschlagen.
- `WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site" WIRTELPRIMPF_SITE_PROFILE=hub npm --prefix web run check`: 38 Dateien, 0 Fehler, 0 Warnungen, 0 Hinweise.

## Builds und CSP

- Static-Build ohne `PUBLIC_CATGPT_LIGHT_ENDPOINT`: Exit 0.
- `rg -n "connect-src 'none'" web/dist`: Exit 0, Treffer in allen 7 erzeugten HTML-Seiten.
- Light-Build mit exakt gültigem Endpoint: Exit 0.
- `rg -n "connect-src https://catgpt\.wirtelprimpf\.telacore\.org" web/dist`: Exit 0, Treffer in allen 7 erzeugten HTML-Seiten.

## Dateien

- `web/src/lib/catgpt/config.ts`
- `web/src/lib/catgpt/history.ts`
- `web/src/lib/catgpt/light-provider.ts`
- `web/src/lib/catgpt/settings.ts`
- `web/src/env.d.ts`
- `web/src/components/SettingsPanel.astro`
- `web/src/components/CatGptWidget.astro`
- `web/src/layouts/BaseLayout.astro`
- `web/tests/catgpt-config.test.ts`
- `web/tests/catgpt-history.test.ts`
- `web/tests/catgpt-light-provider.test.ts`
- `web/tests/catgpt-settings.test.ts`
- `web/tests/catgpt-components.test.ts`
- `.superpowers/sdd/2026-08-03-CatGPT-Phase-2-Light-Fallback-Implementierungsplan/task-6-report.md`

## Commit

`feat(web): add CatGPT Light with silent Static fallback` (dieser Commit)

Fix-Runde: `fix(web): isolate CatGPT storage failures`.

## Risiken / Grenzen

- Kein echter Netzwerk-/Worker-Test, Deploy oder Secret-Einsatz; durch Task-Grenzen ausgeschlossen.
- Astro-Build und Komponentenverträge prüfen Integration, aber kein Browser-E2E-DOM-Harness ist im Projekt vorhanden.
