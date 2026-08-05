# Web-Freshness und Veröffentlichung

## Öffentlicher Status

`web/src/generated/status.json` wird unmittelbar vor `astro build` durch
`scripts/build_web_status.py` erzeugt. Der Build verwendet dabei den aktiven
Profil- und Datenroot. Bei einem Hub-Build werden die vom Dispatch aufgelösten
Werte `WIRTELPRIMPF_CURRENT_STORY`, `WIRTELPRIMPF_CURRENT_VOLUME`,
`WIRTELPRIMPF_MEDIA_MANIFEST` und `WIRTELPRIMPF_SOURCE_REVISION` ebenfalls an
den Statusgenerator gegeben. Damit beschreiben Status und gerenderte Site
denselben exakten Archivstand, statt auf einen veralteten Generator-Fallback
zurückzufallen. Das Dokument enthält nur:

- Profil und Repositoryname;
- Quellrevision, soweit Git sie sicher liefern kann;
- Bild-/Story-/Kapitelzahlen und neueste stabile IDs;
- Manifestzeitpunkt, Buildzeit und `SOURCE_DATE_EPOCH`;
- Freshnesszustand `fresh`, `warning`, `stale` oder `unknown`.

Lokale absolute Pfade, Parent-Traversal, Laufberichte, Stacktraces und Secrets
sind kein gültiger Statusinhalt. Die Erzeugung bricht bei einem solchen Input
ab. `unknown` ist der ehrliche Zustand, wenn kein veröffentlichter
Manifestzeitpunkt vorliegt; er wird nicht zu `fresh` umgedeutet.

## Schwellen

Die Standard-SLA beträgt sechs Stunden. Bis zur halben SLA gilt der Stand als
`fresh`, danach bis zur SLA als `warning`, und nach der SLA als `stale`. Die
SLA ist ein Buildparameter und darf für einen reproduzierbaren Build explizit
gesetzt werden:

```bash
python3 scripts/build_web_status.py \
  --root . \
  --data-root data \
  --profile hub \
  --output web/src/generated/status.json \
  --freshness-sla-seconds 21600
```

Die ergänzende Planregel „24 Stunden ohne neue Quellrevision“ benötigt eine
verlässliche erwartete Laufzeit-/Revisionshistorie und bleibt bis zum
Generator-/Pages-E2E-Nachweis ein offenes Gate; sie wird nicht aus dem Alter
des Manifestzeitpunkts erfunden.

## Gate-Reihenfolge

1. Exakten Datenstand und Quellrevision bestimmen.
2. Statusmanifest erzeugen und gegen Schema sowie Parser prüfen.
3. Statischen Sitebaum bauen.
4. Artefaktvalidator, Budget- und Browsergates ausführen.
5. Nur das geprüfte Artefakt hochladen; Deployment bleibt ein separater
   GitHub-Pages-Schritt.

Ein fehlendes, ungültiges oder profilfremdes Statusmanifest darf keine fremden
Archivdaten auf der Statusseite anzeigen. Die Seite fällt in diesem Fall auf
`unbekannt` zurück.
