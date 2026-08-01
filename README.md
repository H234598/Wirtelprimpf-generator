# Wirtelprimpf-generator

Generator, lokale Ateliersteuerung, Veröffentlichungsautomatik und gemeinsame Webseitenfabrik für
Wirtelprimpf.

Dieses Repository enthält ausschließlich ausführbaren Code, Konfigurationstemplates, Tests, öffentliche
Hub-Builddaten und die zentrale GitHub-Pages-Seite. Die eigentlichen Publikationen leben getrennt in
fortlaufenden Archiven:

- `Wirtelprimpf-0001` für die vollständigen Storys 1 bis 50 beziehungsweise Bücher 1 bis 5;
- `Wirtelprimpf-0002` für Storys 51 bis 100 beziehungsweise Bücher 6 bis 10;
- danach `Wirtelprimpf-0003`, `Wirtelprimpf-0004`, … nach demselben Vertrag.

Je zehn vollständig abgeschlossene Storys ergeben ein Buch. Ein späteres Archiv wird nicht vorab angelegt.
Der Abschluss jeder 50. Story beziehungsweise jedes fünften Buchs gibt eine
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
zeigt die vollständige aktuelle Story mit dem neuesten Teil zuerst. Vollständige Storyseiten bleiben
chronologisch; die Bibliothek gruppiert jeweils zehn Storys zu einem Buch. Galerie, Bilddetails, Buchübersicht,
Feed, Sitemap, Statusseiten und No-JavaScript-Kern werden
aus strikt validierten Manifesten erzeugt.

## Lokaler Betrieb

Die Python-Paketinstallation stellt vier Kommandos bereit:

```text
wirtelprimpf-generator   Bild-/Storylauf und Veröffentlichung
wirtelprimpf-platform    Migration, Status, Mapping und Rotationswerkzeuge
wirtelprimpf-admin       lokale Einstellungen auf 127.0.0.1:8765
wirtelprimpf-settings    transaktionaler JSON-Kanal für Web und Cinnamon
```

Die Administrationsseite bindet ausschließlich an Loopback, prüft Host, Origin und CSRF und gibt Schlüssel
niemals zurück. Ein vollständiges, kommentiertes Konfigurationsbeispiel steht in `Sourcecode/env.example`.

## Transaktionale Einstellungen und Betriebsstatus

Webadmin und Cinnamon-Applet besitzen keine getrennten Writer. Beide verwenden denselben Schema-, Revisions-,
Validierungs-, systemd- und Rollback-Kern. Öffentliche Werte liegen in
`~/.config/wirtelprimpf/openai.env`; der OpenAI-Schlüssel wird dort nur
schreibgeschützt behandelt. Der Cloudflare-Token bleibt getrennt in
`~/.config/cloudflare/api-token.env`. Private Verzeichnisse werden mit `0700`, private Dateien mit `0600`
und der Timer-Drop-in höchstens mit `0644` verwaltet. Der revisionsfreie Koordinationslock und das
geheimnisfreie Revisionssignal liegen unter `~/.config/wirtelprimpf/`; letzteres heißt
`settings-state.json`.

Jede Änderung enthält eine opake Basisrevision, nur tatsächlich geänderte Werte und deren ursprüngliche
Feldwerte. Eine veraltete, aber nicht überlappende Änderung darf sicher zusammengeführt werden. Hat sich
dasselbe Feld extern geändert, wird die gesamte Transaktion abgelehnt und der lokale Entwurf bleibt sichtbar.
Secret-Aktionen sind immer `replace` oder `delete`, enthalten keine lesbaren Altwerte und werden bei jeder
veralteten Revision abgelehnt. Erfolgreiche Änderungen werden erst nach Schema- und Generatorprüfung
veröffentlicht. Die effektive Timerkonfiguration wird über
`~/.config/systemd/user/wirtelprimpf.timer.d/override.conf` angewendet; schlägt Validierung oder systemd fehl,
werden Dateibytes, Drop-in, Enabled-Zustand und Active-Zustand auf den beobachteten Vorzustand zurückgerollt.

Die beiden Modellfelder sind Dropdowns aus einem gemeinsamen Snapshot. Der Bildkatalog lautet
`gpt-image-2`, `gpt-image-1.5`, `gpt-image-1`, `gpt-image-1-mini`. Der Storykatalog lautet `gpt-5.5`,
`gpt-5.5-pro`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.4-nano`, `gpt-5.4-pro`, `gpt-5.2`, `gpt-5.2-pro`,
`gpt-5.1`, `gpt-5`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5-pro`, `gpt-4.1`, `gpt-4.1-mini`,
`gpt-4.1-nano`, `gpt-4o`, `gpt-4o-mini`. Ein bereits konfiguriertes älteres Modell bleibt beschriftet
sichtbar, wird dadurch aber nicht zu einer neuen Katalogauswahl.

Der Webadmin aktualisiert Einstellungen alle 2 Sekunden und den unabhängigen Betriebsstatus alle 5 Sekunden.
Dirty-Felder werden dabei nie überschrieben; während eines Save sind die Controls gesperrt. Das Applet
beobachtet Environment, Timer-Drop-in und Revisionssignal über Gio, fasst Ereignisse für 250 ms zusammen und
führt zusätzlich alle 30 Sekunden sowie beim Öffnen/Fokussieren einen Refresh aus. Genau ein Worker serialisiert
die blockierenden CLI-Aufrufe; GTK wird ausschließlich über die Main-Loop-Completion aktualisiert.

`GET /api/status` liefert ausschließlich lokalen, redigierten Betriebsstatus zu Generator, Timer,
Konfiguration, Story/Buch/Archiv, lokalem Git, Releases, Hub, Pages/DNS und Auth-Präsenz. Der Collector ruft
weder OpenAI noch GitHub noch Cloudflare auf. Ein fehlender oder defekter lokaler Teil bleibt explizit
`unknown`/`null` und setzt `health` auf `degraded`, statt Story 1 oder eine andere Erfolgslage zu erfinden.

Der Applet-Kanal ist auch direkt diagnostizierbar:

```bash
wirtelprimpf-settings snapshot
printf '%s' '<sparse-json-envelope>' | wirtelprimpf-settings apply
```

`wirtelprimpf-settings apply` liest JSON über stdin; Secrets gehören nie in Argumente. Beide Befehle geben nur
den öffentlichen Snapshot beziehungsweise eine redigierte Fehlermeldung aus.

## Backup und Wiederherstellung

Der freigegebene Rollout legt vor jeder lokalen Mutation ein privates Verzeichnis mit Modus `0700` unter
`~/.local/state/wirtelprimpf/deploy-backups/` an. Der Zeiger
`deploy-backups/latest-admin-live-backup` verweist auf die letzte Sicherung. Gesichert werden ohne
Inhaltsausgabe: Wirtel-Environment, separater Cloudflare-Token, Timer-Drop-in, Revisionssignal, installiertes
Applet und installierte Admin-Unit sowie der vorherige Enabled-/Active-Zustand des Timers. Das Manifest hält
auch zuvor fehlende Pfade fest. Eine Wiederherstellung verwendet genau diese Kopien und Zustandswerte; sie
darf keine unerwartet extern geänderte Datei überschreiben. `scripts/uninstall-local.sh` entfernt nur den
Applet-Baum und bewahrt CLI, Einstellungen, Token, Signal und Drop-in ausdrücklich auf.

Nicht Teil dieses lokalen Einstellungsrollouts sind Cloudflare-Redirects/DNS und der Cinnamon-Upstream-Fix.
Sie benötigen ihre jeweils eigene Freigabe und werden von Installation, Tests und Rollback nicht verändert.

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
