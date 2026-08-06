# Web-Geschichten

## Kanonische Kapitelwege

Eine Story-Bandroute unter `/geschichten/<band>/` bietet die Gesamtansicht.
Jedes veröffentlichte Storyteil erhält zusätzlich eine stabile Route unter
`/geschichten/<band>/<kapitel-id>/`. Die Kapitel-ID wird aus Bandnummer,
Zeitstempel und normalisiertem Kapitelinhalt abgeleitet; Positionsänderungen
ändern den Permalink nicht.

Die Kapitelroute bleibt ohne JavaScript lesbar und enthält:

- Inhaltsverzeichnis mit `aria-current` auf dem aktuellen Kapitel;
- direkte Kapiteladresse und stabile Abschnitts-ID;
- vorheriges Kapitel, Gesamtansicht und nächstes Kapitel;
- leeren, aber weiterhin verlinkbaren Zustand für ein ungültiges Kapitel;
- optionale, nur aus validierten Relationen eingebundene Kapitelbilder.

Der Hub lädt aus dem exakt gepinnten aktiven Archiv alle bis zur aktuellen
Story veröffentlichten `Wirtelprimpf_Story_*.md`-Quellen. Dadurch erscheinen
abgeschlossene Storys wie Story 1 neben der aktiven Story 2 im Katalog und
erhalten dieselben stabilen Story- und Kapitelrouten; `current-story.md` bleibt
nur der lokale Fallback für Vorschau und Validierung.

## EPUB und Relationen

EPUB-Links entstehen ausschließlich aus einem geprüften `epub-manifest.json`.
Fehlt das Manifest oder scheitert die ZIP-, MIME-, Größen-, Hash- oder
Releaseprüfung, werden keine Downloadlinks gerendert.

Ein EPUB kann lokal deterministisch aus einer kanonischen Storyquelle erzeugt
werden. Der Builder übernimmt alle timestamped `##`-Kapitel, lässt leere
Kapitel als leere, aber navigierbare EPUB-Kapitel bestehen und schreibt kein
Release oder Manifest automatisch:

```bash
python3 scripts/build_epub.py \
  --story data/current-story.md --volume 2 --output /tmp/story-2.epub
python3 -m unittest tests.test_epub_builder
```

Für veröffentlichte Downloads bleibt der geprüfte Manifestvertrag maßgeblich:
`mimetype` muss als erster unkomprimierter ZIP-Eintrag vorliegen; Hash, Größe,
MIME und Release-Asset müssen vor dem Eintrag in `epub-manifest.json` bestätigt
sein.

Die Manifestdatei wird erst aus einer separaten, externen Release-Inventur
erzeugt. Der Generator vergleicht lokale EPUB-Bytes mit dieser Inventur und
bricht bei fehlender oder nicht verifizierter Releaseevidenz ab:

```bash
python3 scripts/build_epub.py \
  --story data/current-story.md --volume 2 --output /tmp/story-2.epub
python3 scripts/build_epub_manifest.py \
  --owner H234598 --repository Wirtelprimpf-0001 \
  --release-tag archive-0001-epub-0001 \
  --release-inventory /path/to/verified-release-inventory.json \
  --volume 2=/tmp/story-2.epub --output /tmp/epub-manifest.json
```

Der Builder führt keine GitHub- oder Release-Schreiboperation aus. Eine
fehlende Inventur bleibt ein Fehler und erzeugt keinen veröffentlichungsfähigen
Manifesteintrag.

Medien-zu-Kapitel-Verweise werden nur über stabile Kapitel-IDs oder eindeutig
auflösbare Quellzeitstempel verbunden. Ein nicht auflösbarer Verweis wird
nicht in eine Route übersetzt. Wenn der Zeitstempel des Bilddateinamens von der
Überschrift des geprüften Sidecars abweicht, bindet das Manifest die nachweisbare
Kapitel-ID explizit per Fragment. Zeitstempel vor dem ersten veröffentlichten
Kapitel werden als `historical_orphan_count` sichtbar isoliert; eindeutig
nahe Zeitstempel werden als `approximate_resolved_count` separat ausgewiesen;
unbekannte, zukünftige oder formal ungültige Verweise bleiben Fehler. Die aktuelle
Generatorquelle enthält weiterhin bekannte historische Medienpfade außerhalb der
eingebundenen Storyquelle; dieser Bestand wird nicht automatisch umgeschrieben.

Die Relationsprüfung kann mehrere veröffentlichte Storyquellen in einem Lauf
prüfen. Jede Quelle erhält ihren Band über das zugehörige `--volume`; mit
`--source-root` darf ein geprüfter Sidecarpfad zusätzlich genau eine
Kapitelüberschrift als stabile Zuordnung liefern, wenn der Dateiname einen
historisch abweichenden Zeitstempel trägt:

```bash
python3 scripts/validate_web_relations.py \
  --manifest /path/to/media-manifest.json \
  --story /path/to/Wirtelprimpf_Story_I.md --volume 1 \
  --story /path/to/Wirtelprimpf_Story_II.md --volume 2 \
  --source-root /path/to/archive --strict
```

Die Sidecarauflösung bleibt auf den angegebenen Quellbaum begrenzt, akzeptiert
keine Fragmente oder Pfadüberläufe und schlägt bei nicht eindeutigen
Überschriften fehl. Existieren beide unterstützten Checkoutlayouts mit
widersprüchlichen Einzelüberschriften, wird der Relationsreport beziehungsweise
der Webbuild ebenfalls fail-closed abgebrochen, statt das erste Ergebnis zu
übernehmen. `sidecar_resolved_count` macht diese Ausnahmen im
Maschinenreport sichtbar; historische Orphans bleiben separat und werden nicht
als aktuelle Kapitelrelationen ausgegeben.

## Lokale Abnahme

```bash
npm --prefix web test
npm --prefix web run test:browser
python3 tests/test_web_plan.py
python3 -m unittest tests.test_epub_builder
python3 -m unittest tests.test_epub_manifest_builder
python3 tests/test_epub_contract.py
npm --prefix web run test:e2e -- full-story
```

Die Browserabnahme prüft direkte Kapitel- und No-JS-Links, TOC-Status,
Kapitelnavigation, reduzierte Bewegung und lokale Lesefortschrittszustände.

## Mobile Lesbarkeit

Story-Übersicht, Inhaltsverzeichnis und Kapitelinhalt dürfen auf kleinen
Viewporten keine breitere Layoutspur erzeugen. Lange Wörter, Codeblöcke,
Tabellen und eingebundene Medien werden innerhalb des verfügbaren Inhaltsraums
umgebrochen oder skaliert; dekorative Kapitelrotationen werden mobil entfernt.
Die Browserabnahme misst den Dokument- und Story-Overflow bei 320 Pixeln.
