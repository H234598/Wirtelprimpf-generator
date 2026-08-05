# Web-Design- und Zustandsvertrag

Die statische Oberfläche verwendet dieselben Layout- und Farbtoken für
Normal-, Leer-, Fehler- und No-JS-Zustände. Reservierte Medienflächen halten
die Kartenhöhe stabil; ein Bildfehler wird als ruhiger, lokaler Status im
gleichen Rahmen angezeigt. Externe Bilder werden nicht durch interne Traces,
Pfade oder technische Fehlermeldungen erklärt.

## Farbrollen und Typografie

Die Rollen liegen in `web/src/styles/global.css`; die Papierwerte werden nur
über `:root[data-theme="paper"]` überschrieben. Schriften bleiben lokale
Systemstapel, es gibt keine externen Font-Requests.

| Rolle | Nacht | Papier | Verwendung |
| --- | --- | --- | --- |
| `--bg` | `#17121d` | `#f4e8d5` | Seitenfläche |
| `--surface` | `#241b2b` | `#fffaf0` | Karten und Panels |
| `--ink` | `#fff7e9` | `#32222e` | Primärtext |
| `--muted` | `#ccbfae` | `#6d5a62` | Sekundärtext |
| `--mint` | `#78d9b6` | geerbt | Eyebrows und Links |
| `--paper-code` | `#315f50` | geerbt | Code auf Papier |
| `--empty-ink` | `#8ee3c3` | `#315f50` | Leerzustände |
| `--carrot` | `#f29c52` | geerbt | Primäraktionen |

Die geprüften Textkombinationen erreichen mindestens WCAG-AA-Kontrast:

| Kombination | Kontrast |
| --- | ---: |
| Nacht `--ink` auf `--bg` | 17.30:1 |
| Nacht `--muted` auf `--bg` | 10.20:1 |
| Nacht `--empty-ink` auf `--bg` | 12.21:1 |
| Papier `--ink` auf `--bg` | 12.36:1 |
| Papier `--muted` auf `--bg` | 5.28:1 |
| Papier `--paper-code` auf `--paper` | 6.13:1 |
| `#231623` auf `--carrot` | 7.97:1 |

Die Galerie besitzt einen eigenen leeren Filterzustand mit Rückweg zum
vollständigen Filter. 404, leere Kapitel, fehlende Paarungen und unbekannter
Medientyp bleiben sachlich klassifiziert. Der statische Build verwendet keine
Ladeanimation als Voraussetzung für lesbare Inhalte.

Die visuelle Stichprobe lädt Home, Galerie und Storybibliothek in 320 px,
768 px hoch/quer, 1440 px und 1920 px. Sie erzeugt reproduzierbare Artefakte
unter `web/test-results/p08-visual/` und prüft zusätzlich, dass der CatGPT-
Launcher keine primären Home-Aktionen überdeckt:

```bash
npm --prefix web run test:e2e -- responsive
```
