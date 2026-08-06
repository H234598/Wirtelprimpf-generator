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
python3 scripts/build_web_site.py \
  --profile hub \
  --site-url https://wirtelprimpf.telacore.org \
  --expected-domain wirtelprimpf.telacore.org \
  --data-root data \
  --check
python3 scripts/validate_pages_artifact.py web/dist --expected-domain wirtelprimpf.telacore.org
python3 scripts/validate_web_budgets.py --root web/dist --config config/web-budgets.json --strict
```

Archiv-Repositories werden nicht als eigene Websites gebaut. Ihre Manifeste,
Storys und GitHub-Links werden in den zentralen Hub-Build übernommen; der
jeweilige Repositoryname und die Quellrevision werden gemeinsam als Nachweis
gesichert. Der Wrapper baut in einem temporären Ziel, validiert vor dem
atomaren Wechsel nach `web/dist` und lässt bei Fehlern das letzte vollständige
Hub-Artefakt stehen.

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

## Exakter Rollback-Redeploy

Nur mit separater produktiver Freigabe und einem vorhandenen bekannten-Gut-
Nachweissatz:

```bash
gh workflow run hub-pages.yml \
  --ref main \
  -f generator_ref=<40-stellige-Generator-SHA> \
  -f active_repository=Wirtelprimpf-0001 \
  -f archive_ref=<40-stellige-Archiv-SHA> \
  -f current_volume=<positives-Storyvolumen>
```

Der Generator- und der Archiv-SHA müssen beide vollständig und unveränderlich
festgelegt sein. Nach einem erfolgreichen Pages-Lauf werden Buildbericht,
Baumhash und die HTTP/2-Smokes für Hub, Galerie, Geschichten, Projekt,
Projektstatus, robots, Sitemap und Feed gemeinsam als Rückabnahme gespeichert.
Bei einem Fehler bleibt der aktuelle produktive Stand unverändert; es gibt
keinen best-effort- oder Branch-Rollback.
