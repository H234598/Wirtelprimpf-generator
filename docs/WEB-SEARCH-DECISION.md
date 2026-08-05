# Suchentscheidung

## MVP-Entscheidung

Der MVP enthält keine sichtbare Volltextsuche. Bilder, Geschichten und
kanonische Routen bleiben direkt navigierbar; es gibt keine halbfertige
Suchkontrolle und keinen zusätzlichen Laufzeitdienst. Das ist eine bewusste
Produktentscheidung, keine fehlende Fehlerbehandlung.

## Wiedervorlage

Eine Suche wird erst neu bewertet, wenn ein konkreter öffentlicher
Nutzungsbedarf und eine stabile Datenbasis vorliegen. Dann werden Pagefind,
MiniSearch und „keine Suche“ mit realen Daten verglichen. Der Vergleich muss
mindestens Indexgröße, Rebuildzeit, Trefferqualität, Tastatur-/Screenreader-
Bedienung, No-JS-Verhalten und Datenschutz prüfen. Als Startgrenze gilt: der
Index bleibt ein eigenes, gemessenes Budget und darf den Kernbuild nicht
vergrößern oder externe Runtime-Requests einführen.

## Daten- und Rückbauvertrag

Der optionale Index enthält nur bereits öffentliche, stabile IDs und
Metadaten. Er ist nie kanonische Quelle und wird bei einem Rückbau vollständig
entfernt; statische Galerie-, Story- und Kapitelrouten bleiben unverändert.
Bis zur Wiedervorlage werden weder Pagefind noch MiniSearch als Abhängigkeit
installiert.
