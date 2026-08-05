# Web-Optionenregister

Der MVP bleibt ein statischer, ohne JavaScript lesbarer Sitebaum. Jede Option
ist unabhängig, bekommt vor einer Implementierung einen eigenen Datenvertrag
und darf weder den Kernbuild noch die No-JS-Grundlage voraussetzen.

| Option | Entscheidung | Nutzen | Kosten/Risiko | A11y/Datenschutz | Eigener Test und Rollback |
| --- | --- | --- | --- | --- | --- |
| Suche mit Pagefind/MiniSearch | zurückgestellt | schneller Zugriff bei belastbarer Datenbasis | Indexgröße, Rebuild und zusätzliche Clientlogik | nur öffentliche Metadaten; Tastatur- und Screenreader-Tests | `tests/test_search_source.py`; Index entfernen, Kernbuild bleibt unverändert |
| PWA/Vollarchiv offline | verworfen für MVP | Offline-Lesen | sehr großer Cache, veraltete Medien, Speicherverbrauch | klare Cache-Löschung; keine privaten Daten | eigener Cachevertrag; Service Worker und Cache löschen |
| TTS/Audio | zurückgestellt | zusätzliche Lesemöglichkeit | Browser-/Stimmenunterschiede, Medienbudget | expliziter Start, keine Autoplay-Pflicht | Audio- und Reduced-Motion-/Keyboard-Test; Audioartefakte entfernen |
| Autoplay/Slideshow | verworfen | visuelle Demonstration | Kontrollverlust, Datenverbrauch, Motion-Risiko | niemals automatisch starten | Browser-Gate; UI und Timer vollständig entfernen |
| Zufallsbild/Überraschung | zurückgestellt | spielerische Erkundung | unklare Navigation und Deep-Link-Verlust | stabile URL und sichtbare Alternative erforderlich | Routen-Test; Option ausblenden, Kernnavigation bleibt |

Die bewusste Suchentscheidung wird erst bei einer gemessenen Datenbasis neu
bewertet. Keine Option darf ein globales Storage-Schema, externe Laufzeit-
Requests oder Originalmedien im Sitebaum erzwingen. Ein Optionstest muss
mindestens Nutzen, Kosten, A11y, Datenschutz und einen unabhängigen Rollback
belegen.
