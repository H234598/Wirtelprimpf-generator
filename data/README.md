# Öffentliche Hub-Daten

Dieser Ordner enthält ausschließlich kleine, redigierte Builddaten für `wirtelprimpf.telacore.org`:

- `publication-catalog.json`: nur vollständig provisionierte und verifizierte Archive;
- `current-story.md`: die veröffentlichte aktuelle Geschichte für die Landingpage;
- `hub-source.json`: globaler Band, kanonisches Archiv, Quellpfad und letzter bekannter Archivcommit;
- `media-manifest.json`: Release-gebundene URLs der aktuellsten Bilder.

Produktive Hub-Builds starten nur als exakter `workflow_dispatch` mit allen drei Eingaben: aktivem
Archiv, vollständigem Archivcommit und globalem Band. Die eingecheckten Fallbackdateien dienen nur lokaler
Vorschau und Validierung. Unvollständige oder widersprüchliche Eingaben brechen weiterhin den Build ab.

Laufzeitkonfiguration, API-Tokens, private Zustandsdateien und lokale Pfade sind hier verboten.
