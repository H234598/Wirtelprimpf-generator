# Revisionsbaseline

Diese Baseline trennt frozen von observed Evidenz. Freeze-Werte sind
reproduzierbare Referenzen, keine Behauptung über heutigen Remote-Zustand.
Beobachtungen werden nur nach dokumentierter Prüfung aktualisiert.

| Repository | Freeze-HEAD | Beobachtung |
| --- | --- | --- |
| `H234598/Wirtelprimpf-generator` | `274b25c9e1f9ea97d3b060997ed5c425d2b30e9f` | `3a60129417659bed9939755baf56d649510454d1`, lokal via `local-git`, Drift |
| `H234598/Wirtelprimpf-0001` | `79274c1fef77306eb9ee0e9bd2682f4b28b74849` | not-checked |
| `H234598/desinfect` | `3bed7ac358b861490727adce36a418db133f8daf` | not-checked |
| `H234598/ADHS-Lernpfad` | `ee91741ec71a1232a4c3b90f42b805591a0d9359` | not-checked |
| `H234598/Cheatsheets` | `71bcad7a8ab183144e8ff007b85aea8bb6cff3b9` | not-checked |

Generator-Drift ist explizit: lokales `main` wurde bei
`3a60129417659bed9939755baf56d649510454d1` beobachtet, nicht am Freeze.
Dies ist keine Fernabfrage und keine Aussage über den aktuellen Remote-Stand.

Archiv-Factory-Pin `b00d824adee47341e3251bc18e09239fde1c5939` bleibt
unverändert. Er ist ein eingefrorener Rollout-Rückstand, kein hier erlaubtes
Repin-Ziel.

## Manuelle Grenzen

Folgende Betreiberprüfungen sind unverified: Pages source configuration,
github-pages environment protection, rulesets/required checks/branch
protection, CodeRabbit organization configuration, custom-domain verification,
DNS and aliases, HTTPS enforcement, secrets, Actions policy und live content
of both domains. Keine davon ist als erfolgreich geprüft markiert.

## Wiederholung

Nach einer neuen, belegten Beobachtung `config/reference-revisions.json`
aktualisieren, `python3 scripts/validate_web_governance.py --root .` und
`python3 tests/test_web_governance.py` ausführen. Änderungen an Freeze, Pin
oder Plan-Digest benötigen neue Evidenz und erneute vollständige Prüfung.
