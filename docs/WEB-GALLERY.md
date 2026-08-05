# Web-Galerie

## Detailroute und Downloads

Jede Karte verlinkt ohne JavaScript auf `/bilder/<asset-id>/`. Diese Route
bleibt die kanonische Detailansicht und enthält verfügbare Derivate,
Metadaten, Nachbarbilder und den Originaldownload. Ein optionaler
EPUB-/Release- oder Medienlink wird nur aus einem validierten Manifest erzeugt;
fehlende Assets werden ruhig als nicht verfügbar behandelt.

Die Downloadziele werden vor dem Rendern nochmals gegen den Release-Assetvertrag
geprüft. Ein ungültiges oder fehlendes Ziel erzeugt einen Statushinweis statt
eines defekten Downloadlinks. Vollbild und Teilen sind progressive Aktionen:
Sie werden erst nach erkannter nativer Browserfähigkeit sichtbar und starten
nur durch eine ausdrückliche Nutzeraktion.

## Progressive Lightbox

Die Detailansicht enthält einen normalen Bildlink. JavaScript verbessert ihn
nachweisbar zu einem nativen `dialog` mit:

- Fokus auf den Schließen-Button beim Öffnen;
- Escape und sichtbarem Schließen;
- Fokusfalle für Tab und Shift+Tab;
- Rückgabe des Fokus an den Bildlink;
- Pfeiltasten für die vorherige/nächste Bildroute;
- horizontaler Touchnavigation ab einer 56-Pixel-Schwelle;
- stabiler Linkfläche und ruhigem Fehlerstatus bei fehlendem Medium;
- keiner Abhängigkeit von Storage oder externen Runtime-Requests.

Reduced Motion darf den Dialogvertrag nicht verändern. Ohne JavaScript bleibt
der Bildlink als direkter Bildzugang sichtbar und die Detailroute vollständig
lesbar.

## Abnahme

```bash
npm --prefix web test
npm --prefix web run test:browser
```

Die Browserabnahme prüft Mausöffnung, Fokus, Escape, Tab-Zyklus,
Touchnavigation, Detailnavigation, Downloads und den No-JS-Fallback.
