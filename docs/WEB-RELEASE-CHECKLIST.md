# Web-Release-Checkliste

Diese Checkliste trennt lokale Nachweise von externen Freigaben. Ein grüner
lokaler Build deployt nichts.

## Lokal

```bash
make check
npm --prefix web run check
npm --prefix web test
npm --prefix web run test:browser
python3 scripts/build_web_site.py --profile hub --data-root web/fixtures/site \
  --site-url https://wirtelprimpf.telacore.org --check
python3 scripts/validate_web_plan.py --root .
python3 scripts/validate_web_governance.py --root .
git diff --check
```

Der Report des Pages-Artefakts enthält Dateizahl, interne Links, Budgets und
Baumhash. Statusmanifest, Quellrevision und exakter Datenstand gehören zu
demselben Nachweissatz.

## Extern

1. Factory- und Archiv-Revision unveränderlich pinnen.
2. Read-only CI und den zuständigen Pages-Build erfolgreich ausführen.
3. Nur das geprüfte Pages-Artefakt deployen; Deployjob und Buildjob bleiben
   getrennt.
4. Custom Domains, HTTPS, Status, Feed, Sitemap und robots live prüfen.
5. Review-/Mergeevidenz, Abnahme und letzte gute Revision dokumentieren.

Ohne diese externen Nachweise bleibt der Release in Arbeit. DNS-, Cloudflare-,
Secret- und Pages-Schreiboperationen sind nicht Bestandteil lokaler Checks.
