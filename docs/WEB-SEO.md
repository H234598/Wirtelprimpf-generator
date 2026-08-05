# Web-SEO

## Lokaler Vertrag

Die Astro-Fabrik erzeugt Canonicals aus der konfigurierten `site`-URL. Sitemap,
Atomfeed und `robots.txt` enthalten nur publizierte Hub-/Archivpfade. Open Graph
und Twitter-Metadaten verwenden dieselbe öffentliche URL und keine lokalen
Dateien, Prompts oder Diagnoseberichte.

Der lokale SEO-Gate ist:

```bash
npm --prefix web run test:e2e -- seo
python3 scripts/validate_pages_artifact.py web/dist --expected-domain wirtelprimpf.telacore.org
```

Am 5. August 2026 bestand der Browser-Gate mit `1/1`; der Artefaktvalidator
und das Budgetgate bestanden im Hub-Fixturelauf ebenfalls. Suchmaschinen-
Indexierung und Social-Preview-Abnahme sind externe Folgeprüfungen und werden
hier nicht behauptet.

## Pflege

Neue öffentliche Routen werden nur zusammen mit Canonical-, Sitemap-, Feed-
und Artefaktprüfung aufgenommen. Wartungsstatus, Laufberichte, lokale Pfade
und technische Fehlerdetails bleiben aus dem Index ausgeschlossen.
