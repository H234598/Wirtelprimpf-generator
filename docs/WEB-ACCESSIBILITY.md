# Web-Accessibility-Abnahme

Die UI-Abnahme läuft mit Playwright und `axe-core` auf den Kernrouten. Sie
prüft direkte Links ohne JavaScript, Tastaturfokus, Lightbox-Dialog,
Touchnavigation, Reduced Motion, Storage-Ausfall, leere Filter, Medienfehler,
404 und 320 CSS-Pixel ohne horizontalen Überlauf. Die Settings- und CatGPT-
Enhancements sind bis zum frühen `data-js="enabled"`-Marker verborgen; der
CatGPT-Launcher sitzt im Header und kann deshalb keinen Seiteninhalt
überdecken.

Der automatisierbare Reflow-Proxy für 400 Prozent Zoom läuft in
`tests/browser/core.spec.ts`: Bei 320 CSS-Pixeln werden Startseite, Galerie und
Geschichtenbibliothek auf horizontales Dokumentübermaß und Überschriften-
Überlauf geprüft. Das entspricht der verfügbaren Breite bei 400 Prozent aus
einer 1280-CSS-Pixel-Basis. Ein echter Browserzoom mit Assistenztechnik sowie
manuelle Screenreader-/Zoomprüfung bleiben davon getrennte Abnahmen.

Status- und Fehlertexte verwenden bestehende `role="status"`-Regionen oder
klare Rückwege. Medienfehler behalten eine reservierte Fläche; versteckte
Enhancement-Kontrollen erscheinen ohne JavaScript nicht. Der blockierende
axe-Vertrag akzeptiert keine Verstöße mit Impact `serious` oder `critical`.

```bash
npm --prefix web run test:browser
npm --prefix web run test:e2e -- responsive
```

## Operator-Owned Manual Acceptance

Diese Prüfung ist absichtlich kein automatisierter Ersatz für die
Betreiberabnahme. Sie wird gegen den aktuell freigegebenen Live-Stand mit
Tastatur, echtem Browserzoom und einer Assistenztechnik durchgeführt.

### Routen und Zoom

Bei `100 %`, `200 %` und `400 %` werden mindestens diese Wege geprüft:

- `/`, `/bilder/`, `/geschichten/`
- `/projekt/`, `/projekt/status/`, `/projekt/lokaler-betrieb/`
- eine Bilddetailroute und eine eigenständige Kapitelroute

Für jede Stufe gilt: kein unerwarteter horizontaler Bildlauf, kein abgeschnittener
Text, kein verdeckter Fokus und keine unbedienbare Dialogkante. Auf einem
kleinen realen oder emulierten Mobilgerät werden zusätzlich Tippen, Zurück,
Pagination, Bildauswahl, Lightbox-Schließen und die beiden CatGPT-Launcher
geprüft.

### Screenreader-Fokusfolge

Mit aktiviertem Screenreader werden Skip-Link, Seitentitel, Hauptnavigation,
Landmarks, Überschriftenhierarchie, Links, Pagination, Filter, Bild-
Alternativtexte, Lightbox-Dialog, Schließen-Aktion, Statusmeldungen und die
CatGPT-Modusnamen `CatGPT-S` und `CatGPT-L` nacheinander angesagt und bedient.
Auf der Leseseite werden außerdem Inhaltsverzeichnis, Vorher-/Nächster-Link,
Kapitelüberschrift und Rückweg geprüft. Die No-JavaScript-Links bleiben als
Fallback erreichbar.

### Nachweisformat

Eine Abnahme ist erst belastbar, wenn Datum/Uhrzeit, Browser, Betriebssystem,
Assistenztechnik, Zoomstufe, geprüfte Routen, Ergebnis je Prüfschritt und die
geprüfte Quell-/Deployrevision notiert sind. Ein automatisierter Playwright-,
axe- oder HTTP-Erfolg darf diesen manuellen Nachweis nicht als `bestanden`
markieren.
