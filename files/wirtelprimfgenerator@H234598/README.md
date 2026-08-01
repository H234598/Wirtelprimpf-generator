# Wirtelprimfgenerator Story Menu

Cinnamon-Applet für `H234598/Wirtelprimpf-generator`: aktuelles lokales Story-Bild, Generated-/Classic-Bild, Full-Story-Dateien, Storyteile, Buchfortschritt, 50-Story-/5-Bücher-Archivwarnung und TTS mit crash-sicherem Lese-State.

## Speed-of-Cinnamon-Abgleich

Version `0.9.0` übernimmt die relevanten Produktmuster aus Speed of Cinnamon, den getrennten Generator-/Archivvertrag und die freigegebene Buchhierarchie:

- responsive Logo in den Cinnamon-Optionen über `SettingsLogo.py` und `assets/settings-*.png`;
- Settings mit Seiten/Layout, About-Seite, TTS-Engine-Auswahl und Aktionsbuttons;
- zentriertes Zufallsgedicht in den Einstellungen, mit elf Varianten pro Öffnen;
- `Run doctor` und `Copy setup plan` direkt aus Menü und Optionen;
- Runtime-State unter `~/.local/state/wirtelprimfgenerator-applet` mit Migration aus der alten `~/.config`-Position;
- Helper/Backend-Grenze: Cinnamon macht UI, Python scannt Dateien, verwaltet State und TTS;
- Custom-TTS wird ohne Shell als Argumentliste gestartet. Shell-Operatoren wie `|`, `&&`, `>` werden abgelehnt;
- Geheimnisse werden nie aus `openai.env` in das Einstellungsfenster geladen. Ein leeres Geheimnisfeld bedeutet „vorhandenen Wert beibehalten“;
- das Applet schreibt weder `openai.env` noch systemd-Drop-ins selbst. Es übergibt sparse Änderungen an den gemeinsamen transaktionalen Kern und zeigt Validierungs- oder Feldkonflikte an;
- Storyteil-Nummern folgen den Überschriften der kanonischen Full Story und bleiben dadurch auch bei einer historisch fehlenden Sidecar-Datei korrekt.
- Alte gespeicherte Projektlinks zu `Katzenbilder` oder `Wirtelprimpf-0001` werden einmalig auf `Wirtelprimpf-generator` migriert; absichtlich gesetzte fremde URLs bleiben unverändert.
- Eine eigene Einstellungsseite verwaltet Vorgaben für die laufende und die nächsten zwei Storys; vergangene Vorgaben bleiben schreibgeschützt sichtbar, und die aktive Vorgabe wird vor dem Generatorlauf sicher in den Prompt projiziert.
- Je zehn vollständige Storys bilden ein Buch; fünf Bücher beziehungsweise 50 vollständige Storys schließen ein Publikationsarchiv ab.

## Transaktionale Generatoreinstellungen

Das Einstellungsfenster spricht ausschließlich mit dem installierten
`~/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-settings`. Snapshot und Apply laufen auf genau
einem privaten Worker-Thread; GTK-Widgets werden nur in der Main Loop verändert. Der Editor überwacht
`~/.config/wirtelprimpf/openai.env`, den Timer-Drop-in und `settings-state.json` über Gio. Ereignisse werden
für 250 ms zusammengefasst. Ein defensiver Refresh läuft alle 30 Sekunden sowie beim Öffnen und Fokussieren.
Fällt ein einzelner Dateimonitor aus, bleiben Initialsnapshot und Fallback aktiv; Fokus und Fallback versuchen
die Installation dieses Monitors erneut.

Lokale Entwürfe erhalten pro Feld ihre Basisrevision. Externe Änderungen aktualisieren nur saubere Felder.
Bei demselben Feld erscheint ein Konflikthinweis mit `Externen Wert übernehmen`; alternativ verwirft
`Alle lokalen Entwürfe verwerfen` nach Bestätigung sämtliche lokalen Entwürfe. Während eines Save sind alle
Konfigurationscontrols gesperrt. Generatorstart und Timer-Neustart bleiben separate Betriebsaktionen.

OpenAI-Schlüssel und Cloudflare-Token sind getrennte Write-only-Zeilen mit Präsenzanzeige sowie explizitem
Replace/Delete. Der Cloudflare-Token wird ausschließlich in `~/.config/cloudflare/api-token.env` gespeichert.
Kein Secret wird ausgelesen, in Argumente geschrieben oder in einer Fehlermeldung angezeigt.

Bild- und Storymodell sind Dropdowns aus demselben Serversnapshot wie im Webadmin. Der Bildkatalog ist
`gpt-image-2`, `gpt-image-1.5`, `gpt-image-1`, `gpt-image-1-mini`. Der Storykatalog ist `gpt-5.5`,
`gpt-5.5-pro`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.4-nano`, `gpt-5.4-pro`, `gpt-5.2`, `gpt-5.2-pro`,
`gpt-5.1`, `gpt-5`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5-pro`, `gpt-4.1`, `gpt-4.1-mini`,
`gpt-4.1-nano`, `gpt-4o`, `gpt-4o-mini`. Ein konfiguriertes Legacy-Modell bleibt sichtbar und unverändert,
ist aber keine neue Katalogauswahl.

## Installation lokal

Installiere zuerst das Generatorpaket in dessen lokaler venv. Der stabile
`wirtelprimpf-settings`-Entrypoint muss als reguläre ausführbare Datei vorhanden sein; das Installationsskript
prüft dies, bevor es einen bestehenden Applet-Baum ersetzt. Aus dem Generatorrepository:

```bash
./scripts/install-local.sh
```

Das Skript legt ausschließlich die benötigten privaten Konfigurationsverzeichnisse mit `0700` an, installiert
das Applet und lässt Environment, separaten Token, Revisionssignal und Timer-Drop-in unangetastet. Erst im
freigegebenen Rollout wird Cinnamon gezielt neu geladen; unter Wayland ist dafür gegebenenfalls eine erneute
Anmeldung nötig.

Empfohlene Pakete:

```bash
sudo apt install python3 xdg-utils speech-dispatcher zenity
sudo apt install espeak-ng   # optionaler Fallback
```

## Menü

```text
Aktuelles Bild
  Story
  Generated

Story
  Read Story
  Read part
    Last 1h
    Last 2h
    ...
    Last 15h
  TTS
    Continue reading
    Set
    Stop

Setup / Diagnose
  Run doctor
  Copy setup plan
  Outputordner öffnen
  Open applet settings
  GitHub öffnen
  Neu scannen
```

Während TTS läuft, zeigt das Panel `■`; ein Klick darauf stoppt das Vorlesen.

## Dateierkennung

Der Runtime-Helper liest `~/.config/wirtelprimpf/openai.env` zur Dateierkennung und nutzt die
Wirtelprimpf-Plattformdefaults. Der Einstellungseditor liest oder schreibt diese Datei nicht selbst:

```text
WIRTELPRIMPF_LOCAL_OUTDIR=$HOME/Hintergrundbilder
WIRTELPRIMPF_WORKING_DIR=$HOME/Hintergrundbilder/working
WIRTELPRIMPF_REPO_SUBDIR=Wirtelprimpf
```

Falls der Outputordner nicht gefunden wird, setze ihn in den Applet-Optionen. Die Globs in den Optionen überschreiben die automatische Erkennung.

## TTS

Die TTS-Engine wird in den Einstellungen per Dropdown gewählt:

- `Auto`: sucht Piper-TTS mit deutschem Modell, danach `spd-say`, danach `espeak-ng` und `espeak`.
- `Piper`: erzwingt Piper-TTS und braucht ein deutsches `.onnx`-Modell, entweder über das nur bei Piper sichtbare Feld `Piper-Stimmenmodell` oder über `WIRTELPRIMPF_TTS_PIPER_MODEL=/pfad/zur/stimme.onnx`.
- `Speech Dispatcher`, `eSpeak NG`, `eSpeak`: erzwingen die jeweilige lokale Engine.
- `Custom command`: nutzt das Custom-TTS-Kommando unten.

Hinweis: Fedora `/usr/bin/piper` ist häufig die GTK-App zur Mauskonfiguration, nicht Piper-TTS. Das Applet erkennt diesen Fall und fällt in `Auto` auf die nächste Engine zurück.

Der echte Piper-TTS-Befehl kann lokal installiert werden mit:

```bash
python3 -m pip install --user piper-tts
```

Das Feld `Piper-Stimmenmodell` enthält links ein Download-Menü für Thorsten-Voice-Modelle. Downloads landen unter `~/.local/share/piper/voices` und setzen den Modellpfad automatisch.

Custom-TTS ist ein sicherer Template-Modus ohne Shell:

```bash
piper --model /pfad/stimme.onnx --output_file /tmp/wirtel.wav {text_file}
```

Platzhalter:

```text
{file}       Originaldatei
{text_file}  temporäre Textdatei
{text}       Text als einzelnes Argument
```

Pipes und Redirections absichtlich nicht direkt verwenden. Falls du wirklich eine Shell willst, konfiguriere sie explizit, z.B. `sh -c 'cat "$1" | ...' sh {text_file}`.

## GitHub-Layout

Der Applet-Ordner liegt im Generatorrepository unter `files/wirtelprimfgenerator@H234598/`. Die Optionen öffnen standardmäßig `https://github.com/H234598/Wirtelprimpf-generator`; Publikationsdaten stammen aus dem lokalen Output und dem jeweils aktiven `Wirtelprimpf-####`-Archiv.
