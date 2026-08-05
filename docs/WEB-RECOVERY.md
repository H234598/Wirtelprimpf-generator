# Web-Recovery und Rollback

## Grundsatz

Recovery ist ein Wiederherstellen eines bekannten Zustands, kein Reparieren
durch stilles Weglassen. Die letzte gute Kombination besteht aus:

1. Generator-/Datenrevision;
2. Medienmanifest und dessen SHA-256-Werten;
3. Freshnessstatus mit Buildzeit;
4. Pages-Artefaktbaumhash.

Diese Nachweise werden vor der Veröffentlichung notiert. Ohne verifizierbare
Revision oder Baumhash bleibt die Veröffentlichung blockiert.

## Standard-Recovery

1. Fehlerklasse und betroffene Revision identifizieren, ohne Quell- oder
   Archivdateien umzuschreiben.
2. Letzte gute Revision beziehungsweise das letzte gute Pages-Artefakt
   auswählen.
3. Einen frischen Arbeitsbaum oder ein frisches `web/dist` erzeugen.
4. `npm ci --ignore-scripts`, Check, Tests, Build, Artefaktvalidator und
   Budgetvalidator vollständig ausführen.
5. Den Status für denselben Profil-/Datenstand neu erzeugen und prüfen, dass
   keine lokalen Pfade oder Traces enthalten sind.
6. Nur das neu geprüfte Artefakt für einen ausdrücklich freigegebenen
   Redeploy verwenden.

## Medien- und Cachefehler

Bei fehlendem oder inkonsistentem Medienasset bleibt der fehlerhafte Datensatz
isoliert und das Manifest unverändert. `scripts/web_inventory.py --strict`
entscheidet, ob der Stand publishbar ist. Derivatfehler werden aus dem
vertrauenswürdigen Cache entfernt und aus dem Original mit identischer
Transformkonfiguration neu berechnet. Untrusted/CI-Läufe verwenden
`--cache-read-only` und schreiben niemals in den Trusted Cache.

## Generator-Pushfehler

Der Generator commitet nur die übergebenen Generatorpfade. Schlägt der Push an
einer Publish-Grenze fehl, bleibt der lokale Commit erhalten; der nächste
kontrollierte Lauf kann den Push erneut versuchen. Kein `git reset`, kein
Force-Push und keine fremde Stage wird als Reparatur verwendet. Der Story-State
bleibt durch den exklusiven Lock vor parallelen Übergängen geschützt.

## Rollback

Ein Rollback deployt exakt das letzte geprüfte Pages-Artefakt oder baut exakt
aus der dafür dokumentierten Revision neu. Es ändert keine DNS-, TLS-,
Cloudflare- oder Archivdaten. Nach dem Rollback werden Statusroute,
Artefaktvalidator und die öffentliche Domain separat verifiziert. Ein
Rollback ohne bekannte gute Referenz ist ein Blocker, kein Anlass für einen
best-effort Build.

## Verifizierter bekannter-Gut-Redeploy am 5. August 2026

Der Hub wurde aus Generator-Commit `1e280b0` mit dem unveränderlichen
Archivstand `H234598/Wirtelprimpf-0001@4692189ecf69a70f5526587649a2c426c0949126`
neu gebaut und veröffentlicht. Pages-Lauf `31040117355` bestand mit Build und
Deploy; der öffentliche Smoke lieferte für Hub und Galerie HTTP/2 `200`.
Die ausgelieferte Galerie enthielt die Seitengrößen `10`, `20`, `50`, `100`,
`200`, `500` und `Alle`, der Hub die Launcher `CatGPT-S` und `CatGPT-L`.

Dieser Nachweis belegt einen kontrollierten Redeploy eines bekannten guten
Stands. Ein destruktiver Rollback auf einen älteren Stand wurde nicht
ausgeführt; dafür bleiben die dokumentierte Referenz, separate Freigabe und
anschließende Rückabnahme erforderlich.
