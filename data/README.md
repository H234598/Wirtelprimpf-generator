# Öffentliche Hub-Daten

Dieser Ordner enthält ausschließlich kleine, redigierte Builddaten für `wirtelprimpf.telacore.org`:

- `publication-catalog.json`: nur vollständig provisionierte und verifizierte Archive;
- `current-story.md`: die veröffentlichte aktuelle Geschichte für die Landingpage;
- `hub-source.json`: globaler Band, kanonisches Archiv, Quellpfad und letzter bekannter Archivcommit;
- `media-manifest.json`: Release-gebundene URLs der aktuellsten Bilder.

Produktive Hub-Builds lösen bei einem geplanten Lauf den aktuellen `main`-Commit
des aktiven Archivs auf und bauen danach weiterhin exakt diesen vollständigen
Commit. Ein manueller `workflow_dispatch` kann ebenfalls alle drei Werte
explizit vorgeben: aktives Archiv, Archivcommit und globaler Band. Die
eingecheckten Fallbackdateien dienen nur lokaler Vorschau und Validierung.
Unvollständige oder widersprüchliche Eingaben brechen weiterhin den Build ab.

Laufzeitkonfiguration, API-Tokens, private Zustandsdateien und lokale Pfade sind hier verboten.
