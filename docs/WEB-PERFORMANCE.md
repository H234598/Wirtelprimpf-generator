# Web-Performance

## Blockierende Budgets

`config/web-budgets.json` und `scripts/validate_web_budgets.py` blockieren
deterministisch:

- einzelne HTML-Dateien und den Galerieindex;
- initiales JavaScript und CSS als reproduzierbare gzip-Werte;
- eager geladene Galerie-Bilder;
- Originalbildquellen im Sitebaum;
- fremde Runtime-Requests aus HTML.

Der aktuelle Messstand bleibt unter allen Grenzen. Originale werden nicht in
`web/dist` kopiert; Galeriequellen bleiben hashgebundene Release-URLs.

## Browser-Messung

```bash
npm --prefix web run test:performance
```

Der Playwright-Vertrag misst Home und Galerie in einer statischen Preview und
schreibt `web/test-results/web-performance.json`. Er prüft Navigation Timing,
gesamte Resource-Timing-Bytes, eager Bilder, fremde Runtime-Requests, LCP und
CLS, soweit der Browser Einträge liefert. INP bleibt zunächst `null`, weil ein
synthetischer Einzeltest keine belastbare Interaktionsbaseline erzeugt.

Die Werte sind Diagnose- und Baseline-Daten, keine künstliche harte
Millisekunden-Grenze. LCP/CLS/INP werden erst nach drei vergleichbaren Läufen
in derselben Runner-/Browserumgebung zu blockierenden Grenzwerten. Bis dahin
bleiben die statischen Budgets und die Artefaktprüfung fail-closed.

## Wiederholbare Messung

Für einen Bericht werden mindestens drei kalte oder warme Läufe mit derselben
Node-, Playwright-, Chromium- und Datenrevision ausgeführt. Zu jedem Lauf
gehören Buildzeit, Treehash, HTML-/Artefaktgröße, gzip-Werte, Cachemodus und
Runnerumgebung. Ein neuer Datenstand oder eine Toolchainänderung startet die
Baseline erneut.

Der lokale Medien-/Hostingbericht wird read-only aus dem aktuellen Build und Manifest erzeugt:

```bash
SOURCE_DATE_EPOCH=0 python3 scripts/measure_web_media.py \
  --root . --runs 3 --strict --output build/reports/web-media-costs.json
```

Er enthält Median/P95, maximale Kindprozess-RSS, Artefaktdateien/-bytes, Treehash, Manifestumfang,
Release-gegenüber-Pages-Transfer, Budgetentscheidung und eine Git-basierte 12/24/36-Monatsprojektion.
Fehlt eine belastbare Manifesthistorie, lautet der Status ausdrücklich `insufficient_history`.

## Lokaler Dreifachlauf 2026-08-05

`npm run test:performance -- --repeat-each=3` war auf der lokalen statischen
Preview mit drei von drei Läufen erfolgreich. Die Startseite blieb bei
1.908.709 Transferbytes und drei eager Bildern; die Galerie bei 34.649 Bytes
und ebenfalls drei eager Bildern. Alle sechs Messpunkte meldeten keine fremden
Runtime-Requests. Navigation Timing schwankte erwartbar durch die lokale
Umgebung: Home DOMContentLoaded 693–886 ms, Galerie 502–1.227 ms. Diese Werte
sind eine lokale Dreifachbaseline, kein Live- oder Merge-Nachweis.

## Strict artifact recheck on 2026-08-05

The exact CI artifact command passed against `web/dist`:

```bash
python3 scripts/validate_web_budgets.py \
  --root web/dist --config config/web-budgets.json --strict
```

The report measured 1,013 HTML files, a 1,142,289-byte gallery index
(51,053 bytes gzip), 5,449 bytes gzip initial JavaScript, 4,490 bytes gzip
initial CSS, three eager gallery images, no original image sources, and zero
foreign runtime requests. The targeted SEO/Canonical browser gate also passed
with `1/1`. These are local artifact checks; they do not prove Pages or
Cloudflare publication.
