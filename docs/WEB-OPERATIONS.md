# Web-Betrieb

Der öffentliche Betrieb ist ein statischer, reproduzierbarer Build. Generator,
Publikationsarchive und Pages-Artefakt sind getrennte Zustände. Änderungen an
DNS, Cloudflare, Repository-Branches oder OpenAI-Zugangsdaten gehören nicht in
den normalen Website-Build.

## Regelbetrieb

```bash
cd /home/teladi/.local/share/wirtelprimpf-generator
npm --prefix web ci --ignore-scripts
npm --prefix web run check
npm --prefix web test
python3 scripts/build_web_site.py \
  --profile hub \
  --site-url https://wirtelprimpf.telacore.org \
  --expected-domain wirtelprimpf.telacore.org \
  --data-root data \
  --check
python3 scripts/validate_pages_artifact.py web/dist --expected-domain wirtelprimpf.telacore.org
python3 scripts/validate_web_budgets.py --root web/dist --config config/web-budgets.json --strict
git diff --check
```

Publikationsarchive werden als GitHub-Repositories gepflegt und nicht als
eigene Websites gebaut. Der zentrale Hub übernimmt ihre geprüften Manifeste,
Storys und Repository-Links. Der Wrapper verwendet ein fixes
`SOURCE_DATE_EPOCH` aus der Quellrevision, prüft den Baum vor Veröffentlichung
und tauscht ihn erst danach atomar aus. Ein erfolgreicher lokaler Build ist
noch kein Deployment; dafür sind die externen Freigaben und die zentrale
GitHub-Pages-Abnahme offen.

## Öffentliche und interne Daten

Die Statusroute veröffentlicht nur die redigierten Freshnessdaten aus
`WEB-FRESHNESS.md`. Inventurberichte dürfen absolute lokale Quellpfade zur
Diagnose enthalten, werden aber nicht nach `web/dist` kopiert. Originalbilder
bleiben außerhalb des Git-Sitebaums und werden über die unveränderlichen
Releaseverweise bezogen.

## Störungsklassen

| Klasse | Erkennung | Maßnahme |
| --- | --- | --- |
| Statusinput fehlt/ungültig | Status-Test oder Buildfehler | Datenstand prüfen, Status neu erzeugen, nicht veröffentlichen |
| Medieninventur inkonsistent | `web_inventory.py --strict` | betroffenen Datensatz isolieren, Manifest nicht still kürzen |
| Derivat-/Cachefehler | Bild-/Cachetests oder fehlender Hash | vertrauenswürdigen Cacheeintrag entfernen und deterministisch neu bauen |
| Sitebaum ungültig | Artefaktvalidator/Budgetgate | Artefakt verwerfen, letzte gute Revision behalten |
| Pages-Upload/Deployment fehlerhaft | Workflowstatus | unverändertes geprüftes Artefakt erneut deployen oder zurückrollen |

Die Details und der Rückweg stehen in `WEB-RECOVERY.md` und `WEB-RUNBOOK.md`.
