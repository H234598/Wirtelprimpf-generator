# Wirtelprimpf-generator

Generator, lokale Ateliersteuerung, Veröffentlichungsautomatik und gemeinsame Webseitenfabrik für
Wirtelprimpf.

Dieses Repository enthält ausschließlich ausführbaren Code, Konfigurationstemplates, Tests, öffentliche
Hub-Builddaten und die zentrale GitHub-Pages-Seite. Die eigentlichen Publikationen leben getrennt in
fortlaufenden Archiven:

- `Wirtelprimpf-0001` für die vollständigen Story-Bände 1 bis 50;
- `Wirtelprimpf-0002` für die Bände 51 bis 100;
- danach `Wirtelprimpf-0003`, `Wirtelprimpf-0004`, … nach demselben Vertrag.

Ein späteres Archiv wird nicht vorab angelegt. Der Abschluss jedes 50. vollständigen Story-Bands gibt eine
Warnung aus, speichert eine wiederaufnehmbare Rotation und provisioniert automatisch genau das nächste
Repository samt Releases, GitHub Pages, DNS-only-CNAME, HTTPS und zentralem Katalog. Bis dieser Ablauf
verifiziert ist, bleibt die nächste Generierung blockiert.

## Medienvertrag

Neue Bilddateien werden nicht nach Git `main` geschrieben. Der Generator veröffentlicht pro Bild genau vier
unveränderliche GitHub-Release-Assets: Original, WebP mit 640 Pixel Breite, WebP mit 1280 Pixel Breite und einen
JSON-Datensatz. Jedes Asset wird nach dem Upload über die öffentliche Downloadadresse erneut geladen und mit
SHA-256 geprüft. Erst danach darf das kleine `media-manifest.json` im Publikationsrepository fortgeschrieben,
committet und gepusht werden.

Der Bestandsmigrator wendet denselben Hashvertrag auf historische Bilder an und erzeugt zusätzlich
deterministische Originalpakete und Shardmanifeste. Bereits vorhandene Assets werden niemals überschrieben.

## Webseiten

- Zentrale: <https://wirtelprimpf.telacore.org>
- Archive: `https://wirtelprimpf-0001.telacore.org`, `…-0002…`, fortlaufend

Die Astro-Fabrik unter `web/` baut sowohl die zentrale Landingpage als auch jede Archivseite. Die Landingpage
zeigt die vollständige aktuelle Story mit dem neuesten Teil zuerst. Vollständige Bandseiten bleiben
chronologisch. Galerie, Bilddetails, Bandübersicht, Feed, Sitemap, Statusseiten und No-JavaScript-Kern werden
aus strikt validierten Manifesten erzeugt.

## Lokaler Betrieb

Die Python-Paketinstallation stellt drei Kommandos bereit:

```text
wirtelprimpf-generator   Bild-/Storylauf und Veröffentlichung
wirtelprimpf-platform    Migration, Status, Mapping und Rotationswerkzeuge
wirtelprimpf-admin       lokale Einstellungen auf 127.0.0.1:8765
```

Die Administrationsseite bindet ausschließlich an Loopback, prüft Host, Origin und CSRF, schreibt die private
Environmentdatei atomar als `0600` und gibt Schlüssel niemals zurück. Ein vollständiges, kommentiertes
Konfigurationsbeispiel steht in `Sourcecode/env.example`.

Für eine isolierte Entwicklungsinstallation:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
make check
.venv/bin/python -m unittest discover -s tests/platform -v
npm --prefix web ci --ignore-scripts
npm --prefix web test
npm --prefix web run check
```

Reale API-Schlüssel, Cloudflare-Tokens, private Plattformzustände, lokale Ausgabepfade und gestagte
Release-Assets gehören niemals in dieses Repository.

## Verzeichnisübersicht

- `Sourcecode/`: Generator, Promptvorlagen, private Environmentvorlage und systemd-User-Units;
- `wirtelprimpf_platform/`: Benennung, Zustände, Release-Publisher, GitHub-/Cloudflare-Provisionierung und Admin;
- `web/`: gemeinsame statische Astro-Seitenfabrik;
- `data/`: ausschließlich kleine öffentliche Hub-Builddaten;
- `files/wirtelprimfgenerator@H234598/`: Cinnamon-Applet;
- `scripts/validate_pages_artifact.py`: fail-closed Prüfung des exakten Pages-Artefakts;
- `tests/`: Generator-, Applet-, Plattform- und Vertragsprüfungen.
