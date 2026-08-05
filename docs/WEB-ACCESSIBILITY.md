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
