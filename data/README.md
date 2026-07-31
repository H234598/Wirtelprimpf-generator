# Öffentliche Hub-Daten

Dieser Ordner enthält ausschließlich kleine, redigierte Builddaten für `wirtelprimpf.telacore.org`:

- `publication-catalog.json`: nur vollständig provisionierte und verifizierte Archive;
- `current-story.md`: die veröffentlichte aktuelle Geschichte für die Landingpage;
- `hub-source.json`: globaler Band, kanonisches Archiv, Quellpfad und letzter bekannter Archivcommit;
- `media-manifest.json`: Release-gebundene URLs der aktuellsten Bilder.

Ein normaler Hub-Build verwendet die eingecheckte, redigierte Fallbackgeschichte. Nach jeder erfolgreichen
Generatorpublikation startet der Generator denselben Workflow mit dem exakten Archivcommit; dann wird die
Story direkt aus diesem unveränderlichen Commit gebaut. Unvollständige oder widersprüchliche Eingaben brechen
den Build ab.

Laufzeitkonfiguration, API-Tokens, private Zustandsdateien und lokale Pfade sind hier verboten.
