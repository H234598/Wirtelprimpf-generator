# Wirtelprimpf-Webseite – Anforderungen

Autorität: `docs/plans/WIRTELPRIMPF-WEBSEITE-IMPLEMENTIERUNGSPLAN.md` (SHA-256 `0990f513112825fc511b0a8dce99affda1762b7bda48b3cd5042ce8893867132`). V2-Kapitel 0–28 hat Vorrang; diese Datei ist deterministische Projektion von `config/web-requirements.json`.

| ID | Anforderung | Paket(e) | Meilenstein(e) | Verifikation |
| --- | --- | --- | --- | --- |
| `WEB-REQ-001` | Übersetzt warm/ruhig in prüfbare Rollen und Komponenten statt Katzenkitsch. | `WEB-P08-01` | M03 | `cd web && npm run test:visual-contract` |
| `WEB-REQ-002` | Bietet sofort Bilder und Geschichten als zwei klare, ruhige Hauptwege. | `WEB-P04-01` | M03 | `cd web && npm run test:e2e -- homepage` |
| `WEB-REQ-003` | Sichert kleine Touchgeräte ebenso wie große Displays. | `WEB-P08-02` | M03 | `cd web && npm run test:e2e -- responsive` |
| `WEB-REQ-004` | Macht WCAG 2.2 AA, Tastatur und Screenreader zu blockierenden Qualitätsmerkmalen. | `WEB-P08-03` | M03 | `cd web && npm run test:e2e -- accessibility` |
| `WEB-REQ-005` | Verhindert sichtbare funktionslose JS-Kontrollen und erhält Kernwege. | `WEB-P07-03`, `WEB-P07-04` | M03, M06 | `cd web && npm run test:e2e -- no-js`<br>`python3 tests/test_search_source.py` |
| `WEB-REQ-006` | Macht Lade- und Buildqualität numerisch und reproduzierbar. | `WEB-P11-01` | M04 | `python3 scripts/validate_web_budgets.py`<br>`cd web && npm run test:performance` |
| `WEB-REQ-007` | Reduziert die bis zu 100 lokalen Commits dauernde Weblatenz, ohne Parallelpushes oder kaputte Zustände. | `WEB-P10-04` | M01, M05 | `python3 tests/test_web_publish_policy.py` |
| `WEB-REQ-008` | Trennt Quellen, Staging, generierte Daten und site-Artefakt fail-closed. | `WEB-P02-02` | M01, M04 | `python3 tests/test_web_build.py`<br>`python3 scripts/build_web_site.py --check` |
| `WEB-REQ-009` | Modernisiert CI, ohne Generator-/Applet-Abdeckung zu verlieren. | `WEB-P09-01` | Pflege | `python3 tests/test_check_equivalence.py`<br>`make check` |
| `WEB-REQ-010` | Trennt Quellen, Staging, generierte Daten und site-Artefakt fail-closed. | `WEB-P02-02` | M01, M04 | `python3 tests/test_web_build.py`<br>`python3 scripts/build_web_site.py --check` |
| `WEB-REQ-011` | Bietet sofort Bilder und Geschichten als zwei klare, ruhige Hauptwege. | `WEB-P04-01` | M03 | `cd web && npm run test:e2e -- homepage` |
| `WEB-REQ-012` | Erweitert die statische Galerie, ohne Endlosscrollen oder URL-Verlust. | `WEB-P04-03`, `WEB-P04-04` | M02, M03 | `cd web && npm run test:e2e -- gallery-filters`<br>`cd web && npm run test:e2e -- gallery-return` |
| `WEB-REQ-013` | Macht jedes Bild direkt erreichbar und legt die zugängliche Grundlage für die Lightbox. | `WEB-P05-01` | M02, M03 | `cd web && npm run test:e2e -- image-detail` |
| `WEB-REQ-014` | Bietet störungsarme Großansicht ohne die Detailroute zu ersetzen. | `WEB-P05-02` | M02, M03 | `cd web && npm run test:e2e -- lightbox` |
| `WEB-REQ-015` | Erlaubt bewusste Originalnutzung ohne versteckte Vollauflösungsdownloads. | `WEB-P05-03` | M02 | `cd web && npm run test:e2e -- downloads` |
| `WEB-REQ-016` | Zeigt alle Bände mit belastbarem Titel-Fallback, Status und Umfang. | `WEB-P06-01` | M03 | `cd web && npm run test:e2e -- story-library` |
| `WEB-REQ-017` | Bietet angenehme, tieflinkfähige Lektüre mit Kontext und Navigation. | `WEB-P06-02`, `WEB-P06-04` | M02 | `cd web && npm run test:e2e -- reader`<br>`python3 tests/test_web_relations.py` |
| `WEB-REQ-018` | Ermöglicht Wiederaufnahme ohne Konto, Tracking oder Zeitreihen. | `WEB-P07-02` | M03 | `cd web && npm run test:e2e -- comfort` |
| `WEB-REQ-019` | Bietet vollständiges Lesen, ohne eine unkontrolliert riesige HTML-Datei zu erzeugen. | `WEB-P06-03` | M02 | `python3 tests/test_epub_contract.py`<br>`cd web && npm run test:e2e -- full-story` |
| `WEB-REQ-020` | Hält technische Probleme ruhig, verständlich und rückführbar. | `WEB-P08-04` | M02, M03 | `cd web && npm run test:e2e -- error-states` |
| `WEB-REQ-021` | Definiert den stabilen buildzeitigen Datenvertrag für alle Routen und Derivate. | `WEB-P01-01` | M02, M04 | `python3 tests/test_web_content_schemas.py` |
| `WEB-REQ-022` | Definiert den stabilen buildzeitigen Datenvertrag für alle Routen und Derivate. | `WEB-P01-01` | M02, M04 | `python3 tests/test_web_content_schemas.py` |
| `WEB-REQ-023` | Definiert den stabilen buildzeitigen Datenvertrag für alle Routen und Derivate. | `WEB-P01-01` | M02, M04 | `python3 tests/test_web_content_schemas.py` |
| `WEB-REQ-024` | Skaliert das Archiv ohne unbegrenzte JSON- oder DOM-Dateien. | `WEB-P04-02` | M04 | `cd web && npm run test:e2e -- gallery` |
| `WEB-REQ-025` | Vereinigt Bilder, Prompts, Kapitel, Bände und working-Verweise nach einer einzigen nachvollziehbaren Fachlogik. | `WEB-P01-02`, `WEB-P01-03` | M02, M04 | `python3 tests/test_web_pairing.py` |
| `WEB-REQ-026` | Erhält Permalinks und lokale Zustände über Umbenennungen hinweg. | `WEB-P01-04` | M02, M03 | `python3 tests/test_web_ids.py` |
| `WEB-REQ-027` | Schafft belastbare Mess- und Sicherheitsdaten, ohne das große Medienarchiv zu verändern. | `WEB-P00-02` | M04 | `python3 tests/test_web_inventory.py`<br>`SOURCE_DATE_EPOCH=0 python3 scripts/web_inventory.py --root . --strict` |
| `WEB-REQ-028` | Schafft belastbare Mess- und Sicherheitsdaten, ohne das große Medienarchiv zu verändern. | `WEB-P00-02` | M04 | `python3 tests/test_web_inventory.py`<br>`SOURCE_DATE_EPOCH=0 python3 scripts/web_inventory.py --root . --strict` |
| `WEB-REQ-029` | Schafft belastbare Mess- und Sicherheitsdaten, ohne das große Medienarchiv zu verändern. | `WEB-P00-02` | M04 | `python3 tests/test_web_inventory.py`<br>`SOURCE_DATE_EPOCH=0 python3 scripts/web_inventory.py --root . --strict` |
| `WEB-REQ-030` | Erzeugt layoutgerechte, cachebare Webderivate ohne Originale zu verändern. | `WEB-P03-01`, `WEB-P03-04` | M04 | `cd web && npm run build:images`<br>`cd web && npm test -- images`<br>`python3 scripts/measure_web_media.py --runs 3` |
| `WEB-REQ-031` | Blockiert Dekompressionsbomben, extreme Maße, beschädigte Dateien und private Metadaten. | `WEB-P03-03` | M04 | `cd web && npm test -- image-security` |
| `WEB-REQ-032` | Blockiert Dekompressionsbomben, extreme Maße, beschädigte Dateien und private Metadaten. | `WEB-P03-03` | M04 | `cd web && npm test -- image-security` |
| `WEB-REQ-033` | Vermeidet vollständige Neuberechnung bei jedem neuen Bild. | `WEB-P03-02` | M04 | `cd web && npm test -- image-cache` |
| `WEB-REQ-034` | Setzt die gewählte Architektur minimal und ohne unnötige Laufzeit-JavaScript-Abhängigkeit auf. | `WEB-P02-01` | Pflege | `cd web && npm ci --ignore-scripts`<br>`cd web && npm run build` |
| `WEB-REQ-035` | Verhindert harte Annahmen über Root-Hosting und stabilisiert Canonicals. | `WEB-P02-04` | M03 | `cd web && npm test -- urls` |
| `WEB-REQ-036` | Blockiert unsichere oder übergroße Sitebäume vor dem Upload. | `WEB-P09-04` | Pflege | `python3 tests/test_pages_artifact.py` |
| `WEB-REQ-037` | Modernisiert CI, ohne Generator-/Applet-Abdeckung zu verlieren. | `WEB-P09-01` | Pflege | `python3 tests/test_check_equivalence.py`<br>`make check` |
| `WEB-REQ-038` | Führt alle statischen, Unit-, Contract-, Browser-, A11y- und Budgetgates ohne Secrets aus. | `WEB-P09-02` | M03, M04 | `python3 tests/test_web_workflows.py` |
| `WEB-REQ-039` | Führt alle statischen, Unit-, Contract-, Browser-, A11y- und Budgetgates ohne Secrets aus. | `WEB-P09-02` | M03, M04 | `python3 tests/test_web_workflows.py` |
| `WEB-REQ-040` | Veröffentlicht ausschließlich einen bereits validierten Sitebaum und lässt die letzte gute Site bei Fehlern stehen. | `WEB-P09-03` | M01 | `python3 tests/test_web_workflows.py` |
| `WEB-REQ-041` | Macht Fehlerbehebung und bekannte-gute Wiederveröffentlichung reproduzierbar. | `WEB-P10-03` | M05 | `python3 tests/test_recovery_contract.py` |
| `WEB-REQ-042` | Belegt, welche Quellrevision und neuesten Inhalte tatsächlich veröffentlicht wurden. | `WEB-P10-01` | M05 | `python3 tests/test_web_status.py` |
| `WEB-REQ-043` | Reduziert die bis zu 100 lokalen Commits dauernde Weblatenz, ohne Parallelpushes oder kaputte Zustände. | `WEB-P10-04` | M01, M05 | `python3 tests/test_web_publish_policy.py` |
| `WEB-REQ-044` | Hält Lizenz, Quellenstand und Betrieb auffindbar, aber aus der Hauptnavigation heraus. | `WEB-P10-02` | M05 | `cd web && npm run test:e2e -- maintenance` |
| `WEB-REQ-045` | Übersetzt warm/ruhig in prüfbare Rollen und Komponenten statt Katzenkitsch. | `WEB-P08-01` | M03 | `cd web && npm run test:visual-contract` |
| `WEB-REQ-046` | Speichert nur kleine Komfortzustände und degradiert bei gesperrtem Storage sauber. | `WEB-P07-01` | M03 | `cd web && npm test -- site-state` |
| `WEB-REQ-047` | Rendert Storytext deterministisch ohne aktives ungeprüftes HTML. | `WEB-P02-03` | Pflege | `cd web && npm test -- markdown` |
| `WEB-REQ-048` | Hält Lizenz, Quellenstand und Betrieb auffindbar, aber aus der Hauptnavigation heraus. | `WEB-P10-02` | M05 | `cd web && npm run test:e2e -- maintenance` |
| `WEB-REQ-049` | Macht stabile Inhalte auffindbar, ohne Diagnose- oder Promptinhalte unkontrolliert zu indexieren. | `WEB-P11-03` | M03, M04 | `cd web && npm run test:e2e -- seo` |
| `WEB-REQ-050` | Trennt technische Vorbereitung von bewusst manuellen GitHub-/DNS-Schritten. | `WEB-P11-04` | M01 | `manuelle Checkliste plus HTTP-Smoke` |
| `WEB-REQ-051` | Überführt die 60-KiB-Master-Spezifikation in eine pflegbare, tracebare Arbeitsgrundlage. | `WEB-P00-03` | M00 | `python3 scripts/validate_web_governance.py --root .` |
| `WEB-REQ-052` | Friert Pages/Originalstrategie auf Basis realer Messwerte statt Metadatenfeld ein. | `WEB-P11-02` | Pflege | `python3 scripts/validate_web_budgets.py` |
| `WEB-REQ-053` | Schafft belastbare Mess- und Sicherheitsdaten, ohne das große Medienarchiv zu verändern. | `WEB-P00-02` | M04 | `python3 tests/test_web_inventory.py`<br>`SOURCE_DATE_EPOCH=0 python3 scripts/web_inventory.py --root . --strict` |
| `WEB-REQ-054` | Führt alle statischen, Unit-, Contract-, Browser-, A11y- und Budgetgates ohne Secrets aus. | `WEB-P09-02` | M03, M04 | `python3 tests/test_web_workflows.py` |
| `WEB-REQ-055` | Macht Lade- und Buildqualität numerisch und reproduzierbar. | `WEB-P11-01` | M04 | `python3 scripts/validate_web_budgets.py`<br>`cd web && npm run test:performance` |
| `WEB-REQ-056` | Führt alle statischen, Unit-, Contract-, Browser-, A11y- und Budgetgates ohne Secrets aus. | `WEB-P09-02` | M03, M04 | `python3 tests/test_web_workflows.py` |
| `WEB-REQ-057` | Macht WCAG 2.2 AA, Tastatur und Screenreader zu blockierenden Qualitätsmerkmalen. | `WEB-P08-03` | M03 | `cd web && npm run test:e2e -- accessibility` |
| `WEB-REQ-058` | Übersetzt warm/ruhig in prüfbare Rollen und Komponenten statt Katzenkitsch. | `WEB-P08-01` | M03 | `cd web && npm run test:visual-contract` |
| `WEB-REQ-059` | Bewertet Überrasche mich, Favoriten, PWA, TTS, Slideshow, Suche und Offline-Lesezeichen getrennt vom Kern. | `WEB-P12-01` | M06 | `python3 tests/test_optional_scope.py` |
| `WEB-REQ-060` | Friert Ziel und Referenzen auf volle SHAs ein, dokumentiert nicht lesbare Einstellungen und macht Drift maschinenprüfbar. | `WEB-P00-01`, `WEB-P00-04` | M00, Pflege | `python3 tests/test_web_governance.py`<br>`python3 scripts/validate_web_governance.py --root .`<br>`make check`<br>`git diff --check` |
