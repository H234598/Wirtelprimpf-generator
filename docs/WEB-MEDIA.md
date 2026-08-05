# Web-Medien, Derivate und Cache

Der öffentliche Medienvertrag ist releasegebunden. Ein Manifestdatensatz bindet das Original über seinen
SHA-256-Hash, zwei WebP-Derivate über die angeforderten Breiten `640` und `1280` sowie jedes Derivat erneut
über den eigenen Hash, MIME-Typ, Byteumfang und die tatsächlichen Pixelmaße. Das Manifest bleibt ein kleiner
JSON-Vertrag; Bildbinärdaten werden nicht in den Git-Hauptbaum geschrieben.

## Derivatcache

`wirtelprimpf_platform.media_cache.MediaDerivativeCache` verwendet einen Content-Addressed-Key aus:

- Original-SHA-256;
- Transformationswerkzeug und Werkzeugversion;
- Transformationskonfiguration;
- Zielformat;
- Zielbreite.

Ein Cache-Eintrag ist erst nach erfolgreicher Bildprüfung vollständig. Metadaten und Derivat werden in einem
temporären Verzeichnis geschrieben und danach als kompletter Eintrag atomar veröffentlicht. Unvollständige,
inkonsistente oder beschädigte Einträge gelten als Miss und werden neu erzeugt. Der Read-only-Modus darf weder
Cacheverzeichnisse noch temporäre Dateien anlegen und dient für Prüf- oder Wiederanlaufpfade.

Der Plattformlauf liefert Cachezähler einschließlich `requests`, `hits`, `misses`, `writes`,
`invalid_entries` und `cache_hit_rate` im vorbereiteten Releaseplan. Der Cache ersetzt keine öffentliche
Wiederabrufprüfung und keine Manifestvalidierung.

## Manifestprüfung

Der kanonische Buildstand liegt in `data/media-manifest.json`. Der fail-closed Validator prüft Schema-Version,
Archivbindung, geschlossene Shards, eindeutige IDs und Quellpfade, Release-Tags, Hashformate, Derivatbreiten
und assetgebundene URLs:

```bash
SOURCE_DATE_EPOCH=0 python3 scripts/validate_web_manifest.py --root . --strict
```

Der Validator liest nur. Er lädt keine Releaseassets nach, schreibt keine Quellen und erzeugt keine
Derivate. Die öffentliche Wiederabruf- und SHA-Prüfung bleibt Teil des Releasepublishers.

Der derzeit eingecheckte Manifeststand besteht aus `779` Medienobjekten in `4` geschlossenen Shards mit den
Derivatbreiten `640` und `1280`. Diese Zahlen sind Prüf- und Snapshotwerte, keine unveränderliche
Archivgesamtzahl.

## Vollständiger Cache-Replay

Wenn ein lokaler vollständiger Migrationsbestand vorhanden ist, prüft das
read-only Replaywerkzeug alle Original- und Derivatdateien gegen das Manifest
und legt einen temporären Cache mit der aktuell installierten Toolversion an:

```bash
python3 scripts/measure_media_cache_replay.py \
  --source-root /home/teladi/.local/state/wirtelprimpf/media-migration-0001 \
  --manifest data/media-manifest.json --passes 2 --strict \
  --output build/reports/media-cache-replay.json
```

Der Warm-Lauf vom 5. August 2026 fand `779` passende Originale und `1.558`
passende Derivate. Beide Replaypässe hatten `1.558` Requests, `1.558` Hits,
keine Misses, keine ungültigen Einträge und keine Writes, also
`cache_hit_rate=1.0`.

Der vollständige Kaltlauf wird mit demselben Werkzeug aus den Originalen
gestartet und vergleicht jeden Output mit dem Manifest:

```bash
python3 scripts/measure_media_cache_replay.py \
  --source-root /home/teladi/.local/state/wirtelprimpf/media-migration-0001 \
  --manifest data/media-manifest.json --passes 2 --measure-cold --strict \
  --output build/reports/media-cache-cold-replay.json
```

Der Kaltlauf erzeugte mit Pillow `12.2.0` alle `1.558` Derivate in
`1.151,148 s` (`0` Hits, `1.558` Misses, `1.558` Writes, `0` Invalids).
Die Outputs stimmen byte- und dimensionsgenau mit dem Manifest überein;
zwei anschließende read-only Replays erreichten jeweils `100%` Hits. Cache
und Ziele liegen nur temporär unter dem lokalen State-Verzeichnis und werden
nach dem Lauf entfernt.

## Neue-Story-Cachebaseline

Für die lokale Schwellenprüfung kann derselbe vollständige Archivcache gegen eine
deterministische synthetische 10-Bilder-Fixture gemessen werden. Die Fixture
repräsentiert keine echten Inhalte und dient nur zur Prüfung von Cache-Key,
Miss- und Write-Verhalten:

```bash
python3 scripts/measure_media_cache_replay.py \
  --source-root /home/teladi/.local/state/wirtelprimpf/media-migration-0001 \
  --manifest data/media-manifest.json --passes 2 --new-story-images 10 --strict \
  --output build/reports/media-cache-new-story-baseline.json
```

Am 5. August 2026 trafen `1.558` bestehende Requests den Archivcache. Die
synthetische Fixture erzeugte `20` neue Derivate mit `20` Misses und `20`
Writes; zusammen ergeben sich `1.558/1.578 = 98,7326 %` Cachehits bei `0`
Invalids. Eine reale Produktionsstory, drei vergleichbare Messpunkte, Rechte,
Plattformgrenzen und externe Abnahme bleiben davon unberührt.
