# Web-Hosting-Messstand

## Aktueller Vertrag ab 6. August 2026

Die öffentliche Veröffentlichung ist auf den zentralen Hub
`https://wirtelprimpf.telacore.org` konzentriert. `Wirtelprimpf-0001`,
`Wirtelprimpf-0002` und weitere Archive bleiben GitHub-Repositories und werden
von den Archivkarten direkt verlinkt; sie erhalten keine eigenen Webseiten.
Die Archiv-Pages-Workflow-Datei wurde aus der Fabrik entfernt. Der produktive
Cloudflare-Rückbau von Wildcard-DNS, numerischem Redirect und numerischer
SecurityRule-Ausnahme erfolgt separat mit Vorher-/Nachher-Snapshot und
Read-back. Die folgenden Abschnitte sind historische Mess- und Abnahmebelege
aus dem damaligen Mehrseitenstand und überschreiben diesen aktuellen Vertrag
nicht.

Der Messbericht beschreibt den lokal reproduzierbaren Stand. Der separate
read-only Abschnitt weiter unten dokumentiert lediglich die beobachtete
Liveantwort; er aktiviert weder GitHub Pages noch DNS, Cloudflare oder eine
externe Veröffentlichung.

Der Messlauf `scripts/measure_web_media.py --runs 3` baut die statische Site wiederholt, validiert das
Pages-Artefakt, misst kalte/warme Laufzeiten mit Median und P95, prüft die Arbeitskopie, berechnet
Manifest-/Releaseumfang und liest die vorhandenen Webbudgets. Ein Bericht darf nur atomar unter
`build/reports/` entstehen:

```bash
SOURCE_DATE_EPOCH=0 python3 scripts/measure_web_media.py \
  --root . --runs 3 --strict --output build/reports/web-media-costs.json
```

Der Bericht trennt Pages-Transfer vom releasegebundenen Originalumfang. Originale werden nicht in `web/dist`
kopiert; der Cache-Key wird als Vertrag ausgewiesen, aber ein statischer Sitebuild behauptet keine
Release-Cache-Hit-Rate. Die Wachstumsprojektion bleibt `insufficient_history`, wenn die Manifest-Historie
keine belastbaren Punkte enthält.

Eine Hostingentscheidung bleibt bis zur vollständigen Medieninventur, drei vergleichbaren Läufen, aktueller
Plattformgrenzen, Rechteprüfung und externer Pages-/DNS-Abnahme offen. Lokale Messwerte sind keine
Live- oder Mergeevidenz.

Der vollständige lokale Cache-Replay des Migrationsbestands ist separat
belegt: `scripts/measure_media_cache_replay.py` fand `779` Originale und
`1.558` Derivate mit Manifest-Hashgleichheit. Der Kaltlauf erzeugte mit
Pillow `12.2.0` alle `1.558` Einträge in `1.151,148 s` aus leerem Cache
(`1.558` Misses/Writes, `0` Invalids); zwei anschließende read-only Pässe
erreichten jeweils `1.0` Cache-Hit-Rate ohne Misses, Invalids oder Writes.
Der Nachweis ist lokal und ersetzt keine externe Pages-/Merge-/Reviewabnahme.

Die lokale Cache-Schwellenprobe ergänzt diesen Nachweis: Gegen den vollständig
vorgefüllten Manifestcache erreichten `1.558` Archiv-Requests `100 %` Hits.
Eine deterministische synthetische 10-Bilder-Fixture erzeugte anschließend `20`
neue Derivate mit `20` Misses/Writes; kombiniert lag die Hit-Rate bei
`98,7326 %` (`1.558/1.578`) und `0` Invalids. Das ist eine Cache-Key- und
Miss-Rate-Fixture, keine Produktionsstory und keine Freigabe für Hosting,
Rechte, Merge oder externe Veröffentlichung.

## Aktueller lokaler Dreifachlauf am 5. August 2026

Der read-only Messlauf mit `SOURCE_DATE_EPOCH=0` bestand mit drei Builds und
unverändertem Arbeitsbaum. Die Laufzeiten betrugen `14,637 s`, `16,476 s` und
`15,664 s` (Median `15,664 s`, P95 `16,395 s`); die maximale Kindprozess-RSS
lag bei `568.072 KiB`. Das validierte Pages-Artefakt umfasst `1.036` Dateien,
`1.013` HTML-Dateien, `21.910.908` Bytes und `59.820` geprüfte interne Links;
Treehash ist
`23748a6549e671074b3ee60d98a28dd1596922e97471d38e0a4d8e9fd370ec61`.

Das Budgeturteil ist `pass`, die Quelle umfasst `779` Medien in vier Shards
mit `3.654.670.091` Quellbytes und die Transfer-/Release-Relation beträgt
`0,0059953`. Der Git-Wachstumsstatus bleibt wegen nur eines verfügbaren
Manifestpunkts `insufficient_history`; der statische Build behauptet keine
Cache-Hit-Rate (`cache_hit_rate=null`), weil die Medien releasegebundene URLs
sind. Diese Messung aktualisiert die lokale Baseline, schließt aber weiterhin
keine externe Hosting-, Rechte-, Merge-, Pages- oder DNS-Abnahme.

## Read-only Liveabnahme am 5. August 2026

Die beiden konfigurierten HTTPS-Domains antworteten ohne Redirectfehler mit
HTTP 200 und `Strict-Transport-Security`: Hub
`https://wirtelprimpf.telacore.org/` sowie Archiv
`https://wirtelprimpf-0001.telacore.org/`. Hub-Status, robots.txt, Sitemap und
Feed sowie die entsprechenden Archiv-robots-/Sitemap-Routen waren ebenfalls
erreichbar.

Der öffentliche Hub-Status meldete `796` Bilder, `268` Storyteile und den
Manifeststand `2026-08-05T04:10:44Z`; der lokale Generatorstand enthält
`779` Medien und `195` Kapitel. Das ist belastbare Live-Evidenz, aber zugleich
ein nachgewiesener Factory-/Datenstand-Drift. Deshalb ersetzt die Probe weder
Factory-Repin noch vollständige Release-, Review- und Rollbackabnahme.

Der zugehörige read-only Remoteabgleich ergab: `H234598/Wirtelprimpf-generator/main`
steht auf `274b25c9e1f9ea97d3b060997ed5c425d2b30e9f`, `H234598/Wirtelprimpf-0001/main`
auf `732b62d6ad25b5bfee7a35b673c69568dcd9e75a`. Der jüngste erfolgreiche
Archivlauf ist GitHub Actions `30974608315`, der jüngste erfolgreiche Hublauf
`30974607541`; beide wurden am `2026-08-05T04:15:18Z` angelegt. Der Archiv-
Workflow ruft die Factory jedoch weiterhin über
`@b00d824adee47341e3251bc18e09239fde1c5939` auf und setzt denselben
`factory_ref`. Die erfolgreichen Läufe belegen somit die bestehende Pipeline,
nicht die Veröffentlichung des aktuellen lokalen Arbeitsstands.

## Read-only Live-Recheck am 5. August 2026, 08:17:57Z

Eine erneute öffentliche Prüfung ohne Schreibrechte ergab für Hub und Archiv
HTTP/2 `200`, keinen `Location`-Header und HSTS. `robots.txt`, `sitemap.xml`
und `feed.xml` lieferten auf beiden Hosts HTTP `200`.

Der Hub meldete `798 Bilder` und `1 Story`, das Archiv `798 Bilder` und `2
Storys`, jeweils mit Manifestzeit `2026-08-05T08:17:57Z`. Lokal bleiben `779`
Medien und `195` Kapitel. Die getesteten nummerischen Negativhosts `0000`,
`0042`, `9999`, `10000` und ein zufälliger Host lieferten keine A-/AAAA-
Antworten. Diese öffentliche Sicht bestätigt Erreichbarkeit und Negativfälle,
aber weder Factory-Repin noch autoritative Cloudflare- oder Pages-Einstellungen.

## Pages-/Factory-Reconcile am 5. August 2026, 20:45 CEST

Der Archiv-Repin wurde in `H234598/Wirtelprimpf-0001#5` reviewt und gemergt.
Archiv-`main` steht auf `4692189ecf69a70f5526587649a2c426c0949126`; die beiden
Workflow-Pin-Stellen verwenden den geprüften Generator-SHA
`01971ea3eed05d00a1c50a31834496f8dfab65c4`.

Der Pages-Lauf `31036064433` bestand mit `1.384` Dateien, `1.362` HTML-Seiten,
`164.445` internen Links, `41.982.400` Bytes und Treehash
`7f18a64c410d92baf0e0a726d1e1aacdb87cd2786d54fe6c0a6301e614da01b7`.
Der öffentliche Archiv-Smoke lieferte HTTP/2 `200`, keinen Redirect, korrekten
Canonical und HSTS. Die Statusseite meldete `803` Bilder und `2` Storys mit
Manifest `2026-08-05T18:24:34Z`; die Startseite enthält `CatGPT-S` und
`CatGPT-L`.

Der Repin-/Pages-Nachweis ist damit technisch abgeschlossen. Offen bleiben
produktiver Rollback-/Redeploytest, vollständige Betreiberabnahme und der
separate Cloudflare-Alias-/Wildcard-Rollout.

## Vergleichsreihe Remote-CI-Performance am 5. August 2026

Die drei erfolgreichen `check`-Läufe `31035178872`, `31039700680` und
`31040896873` enthielten jeweils ein nicht abgelaufenes
`web-diagnostics-<run>`-Artefakt mit demselben Chromium-Performance-Gate. Die
Messungen stammen vom GitHub-Actions-Runner und sind daher eine vergleichbare
Remote-CI-Baseline, aber keine direkte Pages-Produktionsmessung.

| Lauf | Generator-SHA | Hub DCL/Load | Hub Transfer | Galerie DCL/Load | Galerie Transfer | CLS | Fremde Runtime-Requests |
|---|---|---:|---:|---:|---:|---:|---:|
| `31035178872` | `01971ea` | `267,2/269,7 ms` | `16.517 B` | `280,8/282,2 ms` | `5.234 B` | `0` | `0` |
| `31039700680` | `1e280b0` | `359,4/359,9 ms` | `16.482 B` | `261,5/262,4 ms` | `5.433 B` | `0` | `0` |
| `31040896873` | `ef84058` | `364,7/365,1 ms` | `16.482 B` | `243,6/245,2 ms` | `5.433 B` | `0` | `0` |

Die Reihe stärkt den reproduzierbaren Runner-Nachweis für Transfer, Ladezeit,
CLS und Fremdrequests. Sie ersetzt weder die fehlende historische
Medienwachstumskurve (`insufficient_history`) noch Pages-/DNS-/Rechte- oder
Rollbackabnahme.

## Read-only Archivhistorie für Medienwachstum am 5. August 2026

Das kanonische Archiv `H234598/Wirtelprimpf-0001` führt `media-manifest.json`
über `26` echte Historienpunkte vom Commit `ba74783` bis
`717346e41fb9939d04cb8d0f0add2605bbbffe78`. Der initiale Seed-Sprung von `0`
auf `779` Medien wird nicht als laufende Wachstumsrate verwendet. Im
inkrementellen Nachlauf von `db5500b` (`779` Medien,
`3.654.670.091` Quellbytes, 1. August) bis `717346e` (`803` Medien,
`3.766.196.025` Quellbytes, 5. August) liegen `4,754` Tage echte Historie.

- Rate im kurzen Nachlauf: `5,048` Medien/Tag und `23.458.452` Quellbytes/Tag.
- Lineare Szenarien ab `803` Medien / `3.766.196.025` Bytes ergeben nach
  12/24/36 Monaten rechnerisch `2.647`/`4.491`/`6.335` Medien und
  `12.334`/`20.903`/`29.471` Millionen Quellbytes.
- Diese Werte sind ausdrücklich Kurzzeit-Szenarien aus weniger als fünf Tagen,
  keine eingefrorene Produktionsprognose. Die Langzeit-Wachstumshistorie bleibt
  bis zu einer mehrmonatigen Reihe `insufficient_history`.

## Reproduzierbare externe Wachstumsauswertung am 5. August 2026

`scripts/measure_web_media.py` akzeptiert für den Wachstumsabschnitt jetzt ein
separates, read-only Git-Checkout über `--growth-root`, einen abweichenden
Manifestpfad über `--growth-manifest` und optional den ältesten einzubeziehenden
Commit über `--growth-baseline-commit`. Die Projektionen starten bei der
aktuellen Archivspitze statt beim lokalen Generatorstand. Der Report trennt
`history_source=external_git` von `local_git`, dokumentiert Punktzahl und
Zeitfenster und setzt `long_term_status=insufficient_history`, solange weniger
als 90 Tage echte Historie vorliegen.

Der reproduzierbare Fixture-Test `test_external_growth_history_uses_archive_anchor_and_baseline`
prüft genau diesen Vertrag, einschließlich Ausschluss eines Seed-Sprungs und
read-only Git-Auswertung. Die Produktionshistorie bleibt trotz der nun
wiederholbaren Messung ein Kurzzeit-Szenario; Pages-, DNS-, Rechte- und
Rollbackabnahme sind davon getrennt.

Der echte read-only Lauf gegen `H234598/Wirtelprimpf-0001` mit Baseline
`db5500b743b68dd47cdc2bb3d7f8896bea7557e1` ergab `25` einbezogene Punkte,
`4,7541898148` Tage, den Archivanker `803` Medien / `3.766.196.025`
Quellbytes und für 12 Monate `2.646,8473` Medien / `12.334.395.651`
Quellbytes. Der Lauf meldete `long_term_status=insufficient_history` und
bestätigt damit die dokumentierte Kurzzeit-Szenario-Einstufung.
