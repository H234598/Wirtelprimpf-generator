# Web-Custom-Domain

## Kanonische Hosts

- Hub: `https://wirtelprimpf.telacore.org`
- Archiv 0001: `https://wirtelprimpf-0001.telacore.org`
- Archiv `000N`: `https://wirtelprimpf-000N.telacore.org`

Die Hostnamen sind Bestandteil des Astro-URL-Vertrags, der Canonicals, der
Sitemap, des Feeds, von `robots.txt` und des fail-closed Pages-Validators.
Project-Pages-URLs bleiben nur als technischer Fallback erhalten.

## Read-only-Abnahme

Am 5. August 2026 antworteten Hub und Archiv über HTTPS mit HTTP 200, ohne
Redirectfehler und mit `Strict-Transport-Security`. Das ist eine beobachtete
Liveantwort, aber kein Freigabesignal fuer DNS-, GitHub-Pages- oder Cloudflare-
Mutationen. Repository-Einstellungen, Zertifikatsverwaltung und DNS bleiben
Betreiberaufgaben.

## Manuelle Freigabecheckliste

1. Pages-Source ist GitHub Actions und das `github-pages`-Environment ist
   geschützt.
2. Der passende Custom Hostname ist verifiziert und HTTPS erzwungen.
3. Hub und aktives Archiv liefern Canonical, Sitemap, Feed und Status vom
   geprüften Artefakt.
4. Ein bekanntes gutes Artefakt und sein Baumhash sind als Rollbackreferenz
   dokumentiert.
5. Rückbau auf den Project-Pages-Fallback ist nachvollziehbar getestet.
