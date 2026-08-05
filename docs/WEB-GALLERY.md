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

## Seitennavigation und Seitengröße

Die Galerie hält den Seitenstand in der URL und aktualisiert ihn bei
JavaScript-Navigation ohne Rücksprung auf Seite 1. Die Seitengröße kann pro
Ansicht auf `10`, `20`, `50`, `100`, `200`, `500` oder `Alle` Bilder gestellt
werden. Filter, Seitenzahl und Seitengröße werden gemeinsam wiederhergestellt;
ohne JavaScript bleiben die statischen `/bilder/seite/<n>/`-Links nutzbar.

Die Browserabnahme prüft außerdem einen echten Wechsel auf Seite 2 mit
veränderter Seitengröße sowie die vollständige `Alle`-Ansicht.
