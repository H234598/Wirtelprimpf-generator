# Wirtelprimpf Content Model

Die buildzeitigen Webdaten verwenden versionierte, strikt geschlossene Verträge:

- `web-image.schema.json` beschreibt Asset-ID, Quellpfad, Typ, Hash, Dimensionen,
  Releaseziel, Prompt-/Storybeziehung und 640/1280-Derivate.
- `web-story-volume.schema.json` beschreibt Bandnummer, Buchposition, Titel,
  Quelldatei und die geordneten Kapitel.
- `web-story-chapter.schema.json` beschreibt stabile Kapitel-ID, Quellzeitstempel,
  Markdown, sanitisiertes HTML und Reihenfolge.

Alle drei Schemas sind Draft 2020-12, tragen `schema_version: 1.0.0` und lehnen
unbekannte Felder ab. Kapitel-IDs werden aus Band, Timestamp und normalisiertem
Markdown reproduzierbar abgeleitet; eine Umbenennung darf die fachliche ID nur über
das separate Aliasregister ändern.

Die aktuellen Manifest- und Storyfixtures werden mit
`python3 tests/test_web_content_schemas.py` geprüft. Pairingpriorität, Fehlercodes
und Aliasmigration werden in den nachfolgenden P01-Verträgen ergänzt; bei
widersprüchlichen Quellen bleibt der Datensatz blockiert und wird nicht still zu
`classic`, `story` oder einer gültigen Kapitelroute hochgestuft.
