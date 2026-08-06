# Web-Custom-Domain

## Aktueller Vertrag

Die einzige öffentliche Website ist der zentrale Hub:
`https://wirtelprimpf.telacore.org`.

Die Repositories `Wirtelprimpf-0001`, `Wirtelprimpf-0002` und folgende sind
Publikations- und Archivquellen. Ihre Links führen direkt zu GitHub und nicht
zu eigenen Archiv-Webseiten. Für diese numerischen Namen werden weder
Wildcard-DNS noch eigene GitHub-Pages-Deployments benötigt.

Die zentrale Website erzeugt Canonicals, Sitemap, Feed, `robots.txt`,
Statusseiten und die Archivkarten. Die Archivkarten verlinken auf das jeweils
zugehörige Repository.

## Betreiberprüfung

1. Der zentrale Hub liefert das geprüfte statische Artefakt mit Canonical,
   Sitemap, Feed und Status.
2. Archivkarten zeigen auf das richtige GitHub-Repository.
3. Der Cloudflare-Rückbau entfernt Wildcard-DNS und numerische Redirects,
   ohne die benannten Alias-Regeln oder die übrigen Sicherheitsbedingungen zu
   verändern.
4. Ein bekannt gutes Hub-Artefakt und der Cloudflare-Read-back bleiben als
   Rollbackreferenz dokumentiert.
