# Wirtelprimpf Content-Model-Fehler

Der Pairingbericht verwendet einen festen Fehlerkatalog. Unbekannte Codes werden
nicht als Warnung akzeptiert.

| Code | Klasse | Bedeutung |
|---|---|---|
| `PAIR_SYMLINK` | block | Symlink ist kaputt oder verlässt den Quellbaum. |
| `PAIR_CASE_COLLISION` | block | Pfade kollidieren bei portabler Kleinschreibung. |
| `PAIR_AMBIGUOUS_HEADING` | block | Story-Sidecar enthält widersprüchliche Zeitstempel. |
| `PAIR_TIMESTAMP_COLLISION` | block | Mehrere Bilder erhalten denselben Timestamp. |
| `PAIR_TIMESTAMP_MISSING` | warn | Kein Timestamp konnte aus Heading, Dateiname, Gitzeit oder Fallback ermittelt werden. |
| `PAIR_ORPHAN_PROMPT` | warn | Ein Bild besitzt kein passendes Prompt-Sidecar. |
| `PAIR_ORPHAN_STORY` | warn | Ein Bild besitzt kein passendes Story-Sidecar. |
| `PAIR_ORPHAN_SIDECAR` | warn | Ein Prompt-/Story-Sidecar besitzt kein passendes Bild. |

Ausnahmen liegen ausschließlich in `config/web-content-exceptions.json`. Jede
Ausnahme bindet Code, relativen Pfad, Quell-SHA-256, Begründung, Ablaufdatum und
die im Katalog festgelegte Schwereklasse. Der aktuelle Bestand enthält keine
Ausnahme; reale Widersprüche bleiben daher sichtbar.

Prüfung:

```bash
python3 tests/test_web_pairing.py
python3 tests/test_web_content_errors.py
```
