# Programmplan – Wirtelprimfgenerator Cinnamon Applet

## Ziel

Ein Cinnamon-Applet als Seitenwagen für den Katzenbilder/Wirtelprimpf-Generator. Es zeigt Latest-Bilder, Storydateien und Storyteile, verwaltet TTS-State absturzsicher und bleibt UI-seitig klein.

## Abgleich mit Speed of Cinnamon

Speed of Cinnamon trennt Cinnamon-UI und Backend klar: Das Applet besitzt Panel-UI, Menü, Einstellungen und Aktionen; die eigentliche Arbeit wird an ein kleines Backend delegiert. Dieses Applet übernimmt genau dieses Muster: `applet.js` bleibt Menü-/Statusschicht, `helper.py` scannt Output, öffnet Dateien, führt Doctor aus und steuert TTS.

Übernommen wurden außerdem:

1. responsive Settings-Logo per `SettingsLogo.py` und PNG-Assets;
2. Settings-Layout mit Header, Footer, About-Seite und Aktionsbuttons;
3. Diagnose-/Setup-Aktionen (`Run doctor`, `Copy setup plan`);
4. Runtime-State unter `~/.local/state/...` statt Konfiguration als Datenablage;
5. gehärtete Custom-Kommandos ohne implizite Shell.

## Menüstruktur

```text
Aktuelles Bild
  Story
  Generated
  Story
  Read Story
  Read part: nur Last 1h bis Last 15h
  TTS
Setup / Diagnose
```

## State

`~/.local/state/wirtelprimfgenerator-applet/state.json` speichert `last_file` erst nach vollständig vorgelesener Datei. Alte States aus `~/.config/wirtelprimfgenerator-applet` werden beim ersten Lauf migriert.

## Story-Erkennung

Full Storys: `Wirtelprimpf_Story_<Römische Zahl>.md/.epub` plus `working/Full_Story.md`.

Storyteile: generierte `wirtelprimpf_YYYY-MM-DD_*.md`, gefiltert gegen die `## YYYY-MM-DD HH:MM:SS`-Headings der aktiven Full Story. Dadurch zählt `Part<N>` nur innerhalb der aktuellsten Storyserie.

## Absturzsicherheit

- State wird atomar geschrieben (`tmp` + `fsync` + `os.replace`).
- TTS-Lock enthält Parent-PID, Child-PID und aktuelle Datei.
- Stop tötet Child und Parent, entfernt Lock und cancelt `spd-say`.
- Auto-TTS bevorzugt `piper` mit deutschem Modell, dann `spd-say` mit deutscher Stimme, dann `espeak-ng`/`espeak`.
- `last_file` wird nur nach erfolgreichem Returncode gespeichert.

## Offene Integrationspunkte

Für ein echtes GitHub-Repo: Ordner nach `files/wirtelprimfgenerator@H234598/` verschieben, optional `Makefile install-local` ergänzen und Tests/CI analog Speed of Cinnamon hinzufügen.
