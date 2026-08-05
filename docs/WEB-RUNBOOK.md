# Web-Runbook

Dieses Runbook ist die kurze operative Checkliste. Es setzt voraus, dass kein
externer DNS-, Cloudflare- oder Pages-Zugriff ohne ausdrückliche Freigabe
ausgeführt wird.

## Vor jedem Build

```bash
cd /home/teladi/.local/share/wirtelprimpf-generator
git diff --check
npm --prefix web ci --ignore-scripts
npm --prefix web run check
npm --prefix web test
python3 tests/test_web_status.py
python3 tests/test_recovery_contract.py
python3 tests/test_web_publish_policy.py
python3 tests/test_search_source.py
python3 tests/test_optional_scope.py
```

## Build und Abnahme

```bash
npm --prefix web run build
python3 scripts/validate_pages_artifact.py web/dist --expected-domain wirtelprimpf.telacore.org
python3 scripts/validate_web_budgets.py --root web/dist --config config/web-budgets.json --strict
```

Für Archive ist der Datenroot explizit zu setzen; Hub- und Archivstatus dürfen
nicht vermischt werden. Vor einer Veröffentlichung werden Quellrevision,
Statusmanifest und Artefaktbaumhash als ein Satz von Nachweisen gesichert.

## Fehlerbehandlung

- Bei einem Gatefehler wird nichts hochgeladen.
- Bei fehlenden Medien wird nicht auf eine kleinere, scheinbar gültige Galerie
  ausgewichen.
- Bei einem Cachefehler wird nur der betroffene Derivatpfad neu erzeugt; die
  Originaldatei und ihr SHA-256 bleiben die Quelle der Wahrheit.
- Bei einem Pushfehler bleibt der lokale Commit erhalten und wird nicht durch
  einen Reset oder Force-Push versteckt.
- Bei einem Pages-Fehler wird das letzte geprüfte Artefakt erneut verwendet.

Die detaillierten Schritte stehen in `WEB-RECOVERY.md`. Jeder Rollback muss auf
eine konkrete frühere Revision oder einen unveränderten Artefaktbaum zeigen.
