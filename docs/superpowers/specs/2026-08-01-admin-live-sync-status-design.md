---
title: Wirtelprimpf Admin-Live-Synchronisierung und Betriebsstatus
date: 2026-08-01
status: approved
project: Wirtelprimpf-generator
---

# Wirtelprimpf Admin-Live-Synchronisierung und Betriebsstatus

## 1. Anlass und verbindlicher Vorrang

Dieses Dokument präzisiert den bestehenden Wirtelprimpf-Webseiten-Implementierungsplan additiv. Es ersetzt keine frühere Anforderung. Bei einem Widerspruch haben die am 1. August 2026 vom Benutzer ausdrücklich freigegebenen Festlegungen dieses Dokuments Vorrang:

- Webadmin und Cinnamon-Applet verwenden einen gemeinsamen transaktionalen Konfigurationskern.
- Änderungen werden live zwischen beiden geöffneten Oberflächen sichtbar.
- Ungespeicherte Eingaben werden niemals überschrieben.
- Gleichzeitige Änderungen desselben Feldes werden als Konflikt abgelehnt.
- `/api/status` liefert echten lokalen Betriebsstatus und ist kein Alias von `/api/settings` mehr.
- Bild- und Storymodell sind in beiden Oberflächen Dropdowns aus einem gemeinsamen Modellkatalog.
- Die ausdrücklich benannten öffentlichen Texte werden wortgetreu geändert.

## 2. Ziele

1. Eine einzige Schreib-, Validierungs- und Anwendungsschicht für alle gemeinsamen Generator-, Website-, Timer- und Secret-Einstellungen schaffen.
2. Veraltete Komplettformular-Schreibvorgänge verhindern und nicht überlappende Paralleländerungen sicher zusammenführen.
3. Webadmin und Applet ohne dauernde Subprozess- oder Netzwerklast live synchronisieren.
4. Das im Webadmin gesetzte Generierungsintervall mit dem tatsächlich wirksamen systemd-Timer verbinden.
5. Einen redigierten, belastbaren und partiell fehlertoleranten Betriebsstatus bereitstellen.
6. Die bestehende Loopback-, CSRF-, Dateirechte-, Symlink- und Secret-Sicherheitsgrenze erhalten.
7. Hub- und Archivseiten mit den vom Benutzer verlangten Textänderungen neu bauen und ausrollen.

## 3. Nichtziele und Abgrenzung

- Kein öffentlich erreichbares Admininterface und kein Login auf GitHub Pages.
- Kein CMS für nachträgliche redaktionelle Änderungen publizierter Storys oder Bilder.
- Kein Cinnamon-Upstream-Fix.
- Keine Änderung am separat geplanten `codex-master`-Watchdog-/Freeze-Fix.
- Keine Cloudflare-Redirect- oder DNS-Mutation in diesem Arbeitspaket. Die separat beauftragte Redirect-Erweiterung bleibt ein eigenes freizugebendes und zu prüfendes Cloudflare-Arbeitspaket.
- Keine vorzeitige Erzeugung von `Wirtelprimpf-0002` oder weiteren Publikationsrepositorys.

## 4. Öffentliche Textänderungen

Die folgenden Änderungen gelten für alle aus der Generator-Seitenfabrik erzeugten Profile, soweit die jeweilige Zeichenfolge dort vorkommt.

### 4.1 Kopf der Generator-Landingpage

Im Hubprofil wird die kleine Beschriftung oben links von `Zentrale Landingpage` in `Telacores:` geändert. Die bestehende Verlinkung auf die Hub-Startseite bleibt erhalten.

### 4.2 Hauptseite

Die folgenden Aussagen werden vollständig entfernt und nicht sinngleich ersetzt:

- `Die kanonische Storyansicht bleibt zusätzlich chronologisch lesbar.`
- `Keine leeren Repositories, keine Lücken.`

Die umgebenden Sätze bleiben grammatikalisch vollständig und enthalten keine doppelten Leerzeichen oder verwaisten Satzzeichen.

### 4.3 Bilderansichten

`Im Release <release> hashgebunden archiviert.` wird zu `Im Release <release> archiviert.` Die kryptografische Integritätsprüfung der Release-Artefakte bleibt technisch unverändert; nur diese öffentliche Formulierung entfällt.

### 4.4 Öffentlicher Projektstatus

Unter `/projekt/status/` wird der Satz

`Keine Live-API, keine Trackingabfrage: nur redigierte Daten aus dem validierten Buildmanifest.`

wortgetreu ersetzt durch:

`Dass er unbedeutend ist, und nichts weiß.`

### 4.5 Hero der Hauptseite

Die Überschrift `Wo Katzen, Möhren und Unfug Geschichte schreiben.` wird wortgetreu zu
`Wo Katzen Unfug und Geschichte schreiben.` geändert. Diese jüngere Vorgabe aus
`Ausbau II` gilt im Hub- und Archivprofil, soweit beide dasselbe Hero verwenden.

## 5. Architektur des transaktionalen Konfigurationskerns

### 5.1 Komponenten

Der neue Kern liegt als fachlich unabhängiges Pythonmodul im Paket `wirtelprimpf_platform`. Er kapselt:

- das gemeinsame Einstellungsschema;
- Modellkataloge und Wertevalidierung;
- sichere Environmentdatei-Verarbeitung;
- den getrennten Cloudflare-Secret-Speicher;
- systemd-Timerzustand und Drop-in-Erzeugung;
- Revisionsbildung und Konflikterkennung;
- transaktionale Anwendung und Rollback;
- die redigierte öffentliche Einstellungsansicht.

Das Webadmin importiert den Kern direkt. Das Applet greift über ein lokales JSON-CLI auf denselben Kern zu. Damit bleibt die GTK-Einstellungsoberfläche unabhängig vom Python-Virtualenv-Importpfad und folgt dem bereits bewährten Muster des Storydirektiven-CLI.

### 5.2 Kanonische Speicherorte

| Bereich | Kanonischer Speicherort | Bemerkung |
|---|---|---|
| Generator- und Websitewerte | `~/.config/wirtelprimpf/openai.env` | reguläre Datei, Modus `0600` |
| Timerkonfiguration | `~/.config/systemd/user/wirtelprimpf.timer.d/override.conf` | vom Kern aus den kanonischen Timerwerten erzeugt |
| Transaktionssperre | `~/.config/wirtelprimpf/settings.lock` | lokale exklusive Sperre, keine Nutzdaten |
| Revisionssignal | `~/.config/wirtelprimpf/settings-state.json` | redigierte Revision und Änderungszeit, Modus `0600` |
| OpenAI-Schlüssel | `~/.config/wirtelprimpf/openai.env` | write-only in den Oberflächen |
| Cloudflare-Token | `~/.config/cloudflare/api-token.env` | bleibt ausdrücklich außerhalb der Wirtel-Environmentdatei |
| GitHub-Anmeldung | bestehende `gh`-Anmeldung beziehungsweise Prozessumgebung | nur Präsenzstatus, kein Secret-Editor |

Der Kern übernimmt keinen Cloudflare-Token aus alten Wirtel-Konfigurationen automatisch. Ein vorhandener alter Eintrag wird als Konfigurationsdrift gemeldet; seine Entfernung oder Migration erfolgt nur über einen expliziten, getesteten Migrationsschritt.

Der Generator-One-shot importiert die getrennte Datei optional über
`EnvironmentFile=-%h/.config/cloudflare/api-token.env`, damit eine spätere
Repositoryrotation denselben kanonischen Token verwenden kann. Der Adminprozess
importiert weder diese Datei noch `openai.env` in seine Prozessumgebung; er greift
über den Konfigurationskern ausschließlich auf die explizit erlaubten Dateien zu.

## 6. Gemeinsames Einstellungsschema

### 6.1 Überlappende Felder

Mindestens die folgenden Felder sind zwischen Webadmin und Applet gemeinsam und müssen in beiden Richtungen synchronisiert werden:

- `operandi`
- `image_model`
- `story_model`
- `image_size`
- `output_resolution`
- `generation_interval_minutes`
- `publish_immediately`
- `story_finish_parts_min`
- `story_finish_parts_max`
- OpenAI-Schlüssel-Präsenz und write-only Ersatz/Löschung
- Cloudflare-Token-Präsenz und write-only Ersatz/Löschung über den getrennten Speicherort

Nur im Webadmin vorhandene Websitefelder wie `site_title` und `site_intro` werden ebenfalls vom Kern verwaltet, müssen aber nicht künstlich im Applet erscheinen. Nur im Applet vorhandene Expertenfelder bleiben dort sichtbar, laufen bei Speicherung jedoch ebenfalls durch denselben Kern.

### 6.2 Bildmodellkatalog

Der initiale gemeinsame Bildmodellkatalog lautet in dieser Reihenfolge:

1. `gpt-image-2`
2. `gpt-image-1.5`
3. `gpt-image-1`
4. `gpt-image-1-mini`

### 6.3 Storymodellkatalog

Der initiale gemeinsame, für den verwendeten Responses-API-Pfad kuratierte Storymodellkatalog lautet:

1. `gpt-5.5`
2. `gpt-5.5-pro`
3. `gpt-5.4`
4. `gpt-5.4-mini`
5. `gpt-5.4-nano`
6. `gpt-5.4-pro`
7. `gpt-5.2`
8. `gpt-5.2-pro`
9. `gpt-5.1`
10. `gpt-5`
11. `gpt-5-mini`
12. `gpt-5-nano`
13. `gpt-5-pro`
14. `gpt-4.1`
15. `gpt-4.1-mini`
16. `gpt-4.1-nano`
17. `gpt-4o`
18. `gpt-4o-mini`

Die Liste ist versioniert und wird nicht bei jedem Menüaufruf über eine externe API neu geladen. Ein bereits konfigurierter Wert außerhalb des aktuellen Katalogs bleibt sichtbar und wird als `konfiguriert · nicht mehr im empfohlenen Katalog` gekennzeichnet. Er darf unverändert mitgeführt werden, aber eine bewusste Modelländerung muss einen Katalogwert auswählen. Dadurch kann eine Katalogaktualisierung keine produktive Konfiguration stillschweigend ersetzen.

## 7. Revision und Konfliktvertrag

### 7.1 Revisionskennung

Jede öffentliche Einstellungsmomentaufnahme enthält eine opake Revisionskennung. Sie wird aus folgenden redigierten Bestandteilen gebildet:

- normalisierte nicht geheime Einstellungswerte;
- reine Präsenzmerkmale der Secrets;
- Dateistatistik-Fingerprints der betroffenen privaten Dateien;
- normalisierter Timer-Drop-in-Inhalt;
- tatsächlicher Enabled-Zustand des Timers.

Secretwerte selbst fließen weder direkt noch als veröffentlichter Hash in die Revisionsantwort ein.

### 7.2 Schreibanforderung

Ein Client sendet:

- seine `base_revision`;
- ausschließlich tatsächlich geänderte Felder;
- für jedes geänderte nicht geheime Feld den beim Bearbeitungsbeginn gesehenen Basiswert;
- Secretaktionen ausschließlich als replace/delete, niemals mit einem zurückgelesenen Basiswert.

### 7.3 Zusammenführung

Unter exklusiver Sperre liest der Kern den aktuellen Zustand neu:

- Ist die Revision unverändert, wird die Änderung normal angewendet.
- Ist sie veraltet, wird jedes geänderte nicht geheime Feld mit seinem Basiswert verglichen.
- Hat sich ein geändertes Feld extern nicht verändert, wird es sicher auf den aktuellen Zustand aufgesetzt.
- Hat sich dasselbe Feld extern verändert, wird die gesamte Transaktion mit einem Konflikt abgelehnt.
- Secretänderungen benötigen immer eine unveränderte Gesamtbasisrevision.

Eine Konfliktantwort enthält nur Feldnamen, aktuelle öffentliche Werte und eine frische Momentaufnahme. Kein Secretmaterial erscheint in Antwort, HTML, Log oder Diagnose.

## 8. Anwendungstransaktion und Rollback

Die Transaktion läuft in dieser Reihenfolge:

1. exklusive Sperre beziehen;
2. aktuellen Zustand und Dateitypen erneut prüfen;
3. Revision und Feldkonflikte bewerten;
4. Werte schema- und semantisch validieren;
5. wiederherstellbare bytegenaue Vorzustände der betroffenen Dateien festhalten;
6. neue Dateien jeweils über exklusive temporäre Datei, `fsync`, Rechteprüfung und `os.replace` bereitstellen;
7. Generator-Konfiguration mit dem bestehenden maschinenlesbaren Check validieren;
8. bei Timeränderung `systemctl --user daemon-reload` ausführen und den Timer kontrolliert neu starten beziehungsweise seinen Enabled-Zustand anwenden;
9. wirksame systemd-Werte erneut lesen;
10. Revisionssignal atomar aktualisieren;
11. Sperre freigeben und frische Momentaufnahme zurückgeben.

Schlägt ein Schritt nach der ersten Dateiersetzung fehl, werden alle betroffenen Dateien aus dem festgehaltenen Vorzustand wiederhergestellt. Danach folgen erneut `daemon-reload` und die Wiederherstellung des vorherigen Timerzustands. Kann auch das Rollback nicht vollständig bestätigt werden, wird ein harter lokaler Fehler mit den betroffenen Pfaden, aber ohne Geheimwerte ausgegeben; ein Erfolg darf dann nicht gemeldet werden.

Websitefelder werden beim nächsten Hub-/Archivbuild wirksam. Reine Generatorwerte gelten beim nächsten One-shot-Lauf. Timeränderungen werden sofort am realen User-Timer wirksam.

## 9. Live-Synchronisierung

### 9.1 Webadmin

- `/api/settings` wird im geöffneten Formular alle zwei Sekunden mit `cache: no-store` abgefragt.
- `/api/status` wird alle fünf Sekunden abgefragt.
- Nicht bearbeitete Felder werden unmittelbar aktualisiert.
- Sobald ein Benutzer ein Feld verändert, gilt es als dirty und wird durch Polling nicht überschrieben.
- Externe Änderungen eines dirty Feldes erzeugen eine sichtbare Konfliktmarkierung.
- Nach erfolgreicher Speicherung wird die lokale Basisaufnahme vollständig durch die Serverantwort ersetzt.

### 9.2 Applet

- Das Applet überwacht Environmentdatei, Timer-Drop-in und Revisionssignal per `Gio.FileMonitor` beziehungsweise dem in der Cinnamon-Pythonumgebung verfügbaren GLib-Dateimonitor.
- Ereignisbursts werden für 250 Millisekunden entprellt und lösen genau einen JSON-CLI-Lesevorgang aus.
- Beim Öffnen beziehungsweise Fokussieren der Einstellungsseite erfolgt immer eine frische Abfrage.
- Ein defensiver Abgleich alle 30 Sekunden fängt manuelle externe Änderungen ab, die kein beobachtetes Revisionssignal erzeugen.
- Auch hier werden nur saubere Felder automatisch ersetzt; dirty Felder bleiben erhalten und werden bei konkurrierender externer Änderung markiert.

Diese Gestaltung vermeidet einen dauernden schnellen Subprozess-Pollingloop und ist deshalb mit dem getrennt untersuchten Freeze-Thema vereinbar.

## 10. API-Vertrag

### 10.1 `GET /api/settings`

Die Antwort enthält mindestens:

- `ok`
- `schema_version`
- `revision`
- `settings`
- `choices` für Modelle, Modi, Größen und Auflösungen
- `secrets` ausschließlich als Präsenzstatus
- `invariants`
- `warnings`

### 10.2 `POST /api/settings`

Zusätzlich zu Origin- und CSRF-Schutz akzeptiert die Route den in Kapitel 7 beschriebenen Sparse-Change-Vertrag. Antwortklassen:

| HTTP | Bedeutung |
|---|---|
| `200` | vollständig angewendet und nachgeprüft |
| `409` | überlappender Revisionskonflikt, nichts verändert |
| `422` | ungültige oder semantisch widersprüchliche Eingabe, nichts verändert |
| `423` | lokale Konfigurationssperre nicht rechtzeitig verfügbar |
| `503` | Anwendung oder Nachprüfung fehlgeschlagen; Rollbackstatus wird redigiert gemeldet |

### 10.3 `GET /api/status`

`/api/status` ist eine eigenständige read-only Route. Sie liefert:

- `schema_version`, `observed_at`, `health` (`ok`, `degraded`, `error`);
- Konfigurationsrevision, Validität und Drift;
- Generator-Servicezustand, Aktivität, letztes Ergebnis und Exitcode;
- Timer-Enabled-/Active-Zustand, Intervall, Randomized Delay, Persistenz, letzten Trigger und nächsten Lauf;
- aktuelle Story, abgeschlossenes Storyvolumen, Buchnummer und Position von zehn;
- aktiven Archivindex und Repositorynamen;
- Rotationssperre, Ziel und Phase;
- letzten lokal bekannten Git-, Release-, Hub-, Pages- und DNS-Befund einschließlich Freshness, soweit persistiert;
- Authentifizierungen ausschließlich als Präsenzstatus;
- redigierte Warnungen und Fehler.

Die Route führt keine OpenAI-, GitHub- oder Cloudflare-Netzwerkanfrage aus. Teilquellen haben kurze lokale Timeouts. Fällt nur eine Teilquelle aus, antwortet die Route mit HTTP 200 und `health: degraded`; fehlende Werte lauten ausdrücklich `unknown` beziehungsweise `null`. Nur wenn keine belastbare Statushülle erzeugt werden kann, folgt HTTP 500.

## 11. Adminoberfläche

Über dem Formular erscheint eine kompakte, automatisch aktualisierte Betriebsstatuskarte mit:

- Gesamtzustand;
- letztem und nächstem Generatorlauf;
- Timerzustand;
- aktuellem Buch, Storyposition und Repository;
- letzter Laufantwort beziehungsweise redigierter Warnung;
- Konfigurations- und Synchronisationszustand.

Bildmodell und Storymodell sind `<select>`-Felder. Modelloptionen stammen ausschließlich aus `choices`; HTML und Applet pflegen keine voneinander abweichenden Kopien.

Dirty-, extern geändert-, Konflikt- und gespeichert-Zustände sind sowohl farblich als auch textuell erkennbar. Eine Farbe allein ist nie der einzige Informationsträger. Die vorhandene dunkle Ateliergestaltung bleibt erhalten.

## 12. Sicherheitsvertrag

- Bindung weiterhin ausschließlich an `127.0.0.1` oder `::1`.
- Host-, Origin- und CSRF-Prüfung bleiben fail-closed.
- `Cache-Control: no-store`, CSP, `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `nosniff` und `no-referrer` bleiben erhalten.
- Keine beliebigen Dateipfade aus Clientdaten.
- Sperr-, Ziel- und Elternpfade werden gegen Symlinks und falsche Dateitypen geprüft.
- Private Dateien bleiben `0600`, private Verzeichnisse `0700`; systemd-Drop-ins bleiben höchstens `0644` und enthalten keine Secrets.
- Der Admin-Userdienst erhält nur die zusätzlich notwendigen Schreibpfade für Wirtel-Konfiguration, Cloudflare-Tokendatei und Wirtel-systemd-Drop-ins.
- Status- und Konfliktantworten enthalten keine Tokens, Schlüssel, Promptinhalte oder vollständigen Journalausgaben.

## 13. Fehlerbehandlung

- Validierungsfehler verändern keine Datei.
- Ein Revisionskonflikt verändert keine Datei und keinen Dienst.
- Eine belegte Sperre läuft nach einer kurzen festen Wartezeit in HTTP 423 aus.
- systemd-Kommandos erhalten feste Timeouts und werden ohne Shell ausgeführt.
- Statusfehler werden pro Teilquelle gekapselt.
- Journal- und Prozessfehler werden auf eine kurze, redigierte Diagnose begrenzt.
- Eine unbekannte Modellkennung aus bestehender Konfiguration wird nicht still gelöscht.

## 14. Teststrategie

Die Implementierung erfolgt testgetrieben. Vor jedem Produktionsverhalten steht ein gezielt fehlschlagender Test.

### 14.1 Konfigurationskern

- identische Revision und erfolgreiche Sparse-Änderung;
- automatische Zusammenführung nicht überlappender Änderungen;
- Konflikt bei paralleler Änderung desselben Feldes;
- strenger Konflikt für Secretänderung auf veralteter Revision;
- unbekannte Felder und ungültige Modellwahl fail-closed;
- atomare Rechte und keine verbleibenden Part-Dateien;
- Lock-Timeout;
- Symlink-, Sonderdatei- und Elternpfadabwehr;
- echter Timer-Drop-in und bestätigte effektive Werte;
- bytegenaues Rollback bei Check- und systemd-Fehlern;
- Rollbackfehler wird nicht als Erfolg ausgegeben.

### 14.2 Admin-API und Oberfläche

- `/api/status` unterscheidet sich strukturell von `/api/settings`;
- Teilquellenfehler erzeugen `degraded` und keine erfundenen Werte;
- keinerlei Secretmaterial in Settings-, Status-, Konflikt- oder Fehlerantworten;
- Dropdowns werden aus dem gemeinsamen Katalog erzeugt;
- Polling überschreibt keine dirty Felder;
- konfliktfreie und konflikthafte Browsertransaktionen;
- bestehende Loopback-, Host-, Origin-, CSRF- und Traversaltests bleiben grün.

### 14.3 Applet

- Applet und JSON-CLI zeigen dieselben gemeinsamen Werte;
- Dateiüberwachung ist entprellt;
- saubere Felder aktualisieren sich live;
- dirty Felder bleiben erhalten;
- gleiches Feld erzeugt Konflikt statt Überschreibung;
- Speichern sendet nur geänderte Felder;
- Modellkataloge sind byte- beziehungsweise datenidentisch zur Kernantwort.

### 14.4 Website und Gesamtregression

- beide Siteprofile bauen;
- angeforderte neue Texte sind im gerenderten Artefakt vorhanden;
- entfernte Texte sind im gerenderten Artefakt nicht vorhanden;
- Hub-, Archiv-, Sitemap-, Feed-, Canonical- und Linkvalidierung bleiben grün;
- Python-Plattformtests, Applet-Runtime, Storydirektiven, Settingsschema, `make check`, Astro-Check und beide Pages-Artefaktprüfungen laufen vollständig.

## 15. Rollout und Verifikation

1. Gitstatus und Benutzeränderungen erneut prüfen.
2. Private Konfiguration, Wirtel-Applet und betroffene User-Units in einem privaten Wiederherstellungspunkt sichern.
3. Getesteten Generatorstand und JSON-CLI lokal installieren.
4. Applet aus exakt demselben Commit installieren und ausschließlich die Wirtel-UUID neu laden.
5. User-Daemon neu laden und Adminserver kontrolliert neu starten.
6. Vorherigen Timerzustand, Intervall und nächsten Lauf mit dem nachherigen Istzustand vergleichen.
7. Live-Synchronisierung in beiden Richtungen mit nicht geheimen Testwerten und anschließendem Rücksetzen auf den Sollwert prüfen.
8. `/api/settings` und `/api/status` auf Schema, Konfliktverhalten und Secretfreiheit prüfen.
9. Änderungen committen, pushen und über den bestehenden Review-/Mergeweg auf `main` bringen.
10. Hub-Pages und das aktuelle Archivprofil neu bauen und validieren.
11. Öffentliche HTTPS-Seiten auf die sechs Textanforderungen prüfen.
12. Lokale Installation gegen den gemergten Hauptzweig erneut hashen und Dienste/Applet abschließend kontrollieren.

## 16. Akzeptanzkriterien

- Eine in einer Oberfläche gespeicherte gemeinsame Einstellung wird in der anderen geöffneten Oberfläche sichtbar, ohne diese neu starten zu müssen.
- Nicht überlappende Paralleländerungen gehen nicht verloren.
- Überlappende Paralleländerungen können nicht still überschrieben werden.
- Das Webintervall entspricht nach Speicherung dem effektiven systemd-Timer.
- Beide Modellfelder sind in Webadmin und Applet Dropdowns aus demselben Katalog.
- `/api/status` zeigt echten lokalen Betriebszustand und keine Einstellungsduplikation.
- Keine API-Antwort und kein Artefakt enthält einen Geheimwert.
- Alle sechs öffentlichen Textvorgaben erscheinen exakt im gebauten und deployten Ergebnis.
- Vollständige lokale und CI-Testmatrizen bestehen.
- Der Cinnamon-Upstream-Fix, der Freeze-Watchdog-Fix und die separate Cloudflare-Redirect-Aufgabe bleiben unverändert.
