# Wirtelprimpf Web-Inventur

`scripts/web_inventory.py` erstellt eine deterministische, read-only Inventur des
öffentlichen Medienmanifests. Der Scanner verändert weder Quellen noch Releases.

## Lauf

Im Generator-Repository:

```bash
python3 tests/test_web_inventory.py
SOURCE_DATE_EPOCH=0 python3 scripts/web_inventory.py --root . --strict
```

Ein Bericht darf ausschließlich atomar unter `build/reports/` geschrieben werden:

```bash
SOURCE_DATE_EPOCH=0 python3 scripts/web_inventory.py \
  --root . --strict --output build/reports/web-inventory.json
```

Andere Ausgabeziele werden mit Exitcode 3 abgewiesen. Ein ungültiges Manifest oder
ein unsicherer Quellbaum beendet den Strict-Lauf mit Exitcode 2.

## Messumfang

Der Manifestteil enthält Medienanzahl, Originalbytes, Byte-Perzentile, Dimensionen,
MIME-/Typverteilung, Derivatgrößen, fehlende Prompt-/Storybeziehungen,
Shard-Vollständigkeit und manifestgebundene Hash-/Pfadduplikate.

Mit `--source-root <checkout>/Wirtelprimpf` kommt ein read-only Quellscan hinzu:

- Symlinks werden nicht verfolgt; kaputte oder aus dem Quellbaum führende Links blockieren.
- Sonderdateien, LFS-Pointer und portable Case-Kollisionen werden als Fehler gemeldet.
- EPUB-, Markdown- und Promptdateien werden getrennt gezählt.
- Inhaltsduplikate und Hardlink-Gruppen werden mit Pfadlisten ausgewiesen.
- Dateianzahl, Gesamtbytes und Größenperzentile werden zusätzlich erfasst.

Wenn der kanonische Mediencheckout im Generator-Repository nicht vorhanden ist,
bleibt `source_scan` bewusst `null`; daraus wird keine Archivgröße erfunden. Für
die aktuelle öffentliche Manifestbasis wurden zuletzt 779 Medien, 3.654.670.091
Originalbytes, vier geschlossene Shards und 2.345 deklarierte Release-Assets
gemessen. Die vollständige JSON-Struktur ist durch
`config/schemas/web-inventory.schema.json` versioniert.

## Vollständiger Migrationscheckout

Der lokale vollständige Checkout von Archiv 0001 wurde am 5. August 2026 mit
dem Manifest abgeglichen:

```bash
SOURCE_DATE_EPOCH=0 python3 scripts/web_inventory.py \
  --root . --manifest data/media-manifest.json \
  --source-root /home/teladi/.local/state/wirtelprimpf/media-migration-0001 \
  --strict --output build/reports/web-inventory-migration-0001.json
```

Der Bericht enthält `779` Manifestmedien, vier geschlossene Shards und `2.345`
deklarierte Release-Assets. Der gemischte Migration-Checkout enthält `2.346`
reguläre Dateien und `2.337` Bilddateien: `779` PNG-Originale sowie `1.558`
WebP-Derivate. Diese Bildgesamtzahl ist deshalb ausdrücklich kein
Originalbestand. Der Source-Scan fand keine Symlinks, LFS-Pointer,
portablen Case-Kollisionen, Hardlinkgruppen oder Fehler. Die Originalbytes im
Manifest betragen `3.654.670.091`; die Derivate umfassen `33.259.980` Bytes
bei 640 Pixeln und `103.272.240` Bytes bei 1280 Pixeln.

`build/reports/` ist ein abgeleiteter Prüfbereich. Quellen, Prompts, Geschichten,
Git-Objekte und Release-Assets werden durch diesen Lauf nicht geschrieben,
umbenannt oder neu formatiert.
