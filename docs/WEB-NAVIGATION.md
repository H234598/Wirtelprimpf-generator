# Web-Navigation

## Galerie-URL

Die Galerie verwendet `typ`, `seite` und optional `jahr` als kanonische
Queryparameter. Unbekannte oder ungültige Werte werden verworfen. Die
statischen Seiten `/bilder/` und `/bilder/seite/<n>/` bleiben direkte
Einstiegspunkte; JavaScript ersetzt diese Links nicht.

## Rückkehr aus einem Bild

Beim Öffnen einer Detailseite markiert der Galerie-Harness den Kartenlink mit
einer stabilen DOM-ID und legt ausschließlich `focusId` sowie den gerundeten
`scrollY`-Wert in `history.state.gallery` ab. URL und Query bleiben die
Autorität; der History-Eintrag ist nur Komfort und wird bei fehlerhaftem oder
fehlendem State ignoriert.

`popstate` und `pageshow` wenden den URL-Zustand erneut an, scrollen nach dem
Rendern zum begrenzten Anker und geben den Fokus an den Ursprung zurück. Ein
fehlender Storagezugriff ist dafür unerheblich. Ohne JavaScript bleiben
Galerie-, Pagination- und Detail-Links funktionsfähig.

## Abnahme

```bash
npm --prefix web test
npm --prefix web run test:browser
```

Die Browserabnahme prüft Deep-Link, Filter und Pagination, Browser-Zurück,
Scrollposition, Ursprungsfokus, No-JS sowie den A11y-/Fokusvertrag der
Galerie.
