# Wirtelprimfgenerator Story Menu

Cinnamon-Applet für den Output von `H234598/Katzenbilder`: aktuelles Story-Bild, aktuelles Generated-/Classic-Bild, Full-Story-Dateien, Storyteile und TTS mit crash-sicherem Lese-State.

## Speed-of-Cinnamon-Abgleich

Version `0.3.2` übernimmt die relevanten Produktmuster aus Speed of Cinnamon:

- responsive Logo in den Cinnamon-Optionen über `SettingsLogo.py` und `assets/settings-*.png`;
- Settings mit Seiten/Layout, About-Seite, TTS-Engine-Auswahl und Aktionsbuttons;
- `Run doctor` und `Copy setup plan` direkt aus Menü und Optionen;
- Runtime-State unter `~/.local/state/wirtelprimfgenerator-applet` mit Migration aus der alten `~/.config`-Position;
- Helper/Backend-Grenze: Cinnamon macht UI, Python scannt Dateien, verwaltet State und TTS;
- Custom-TTS wird ohne Shell als Argumentliste gestartet. Shell-Operatoren wie `|`, `&&`, `>` werden abgelehnt.

## Installation lokal

Falls eine ältere lokale Vorversion installiert ist:

```bash
rm -rf ~/.local/share/cinnamon/applets/wirtelprimfgenerator@local
```

Dann die neue UUID installieren:

```bash
mkdir -p ~/.local/share/cinnamon/applets
cp -r wirtelprimfgenerator@H234598 ~/.local/share/cinnamon/applets/
chmod +x ~/.local/share/cinnamon/applets/wirtelprimfgenerator@H234598/helper.py
```

Dann Cinnamon neu laden: `Alt+F2`, `r`, Enter. Unter Wayland ab- und wieder anmelden.

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

Das Applet liest `~/.config/wirtelprimpf/openai.env` und nutzt die Katzenbilder-Defaults:

```text
WIRTELPRIMPF_LOCAL_OUTDIR=$HOME/Hintergrundbilder
WIRTELPRIMPF_WORKING_DIR=$HOME/Hintergrundbilder/working
WIRTELPRIMPF_REPO_SUBDIR=Wirtelprimpf
```

Falls der Outputordner nicht gefunden wird, setze ihn in den Applet-Optionen. Die Globs in den Optionen überschreiben die automatische Erkennung.

## TTS

Die TTS-Engine wird in den Einstellungen per Dropdown gewählt:

- `Auto`: sucht `piper` mit deutschem Modell, danach `spd-say`, danach `espeak-ng` und `espeak`.
- `Piper`: erzwingt Piper und braucht ein deutsches `.onnx`-Modell, zum Beispiel über `WIRTELPRIMPF_TTS_PIPER_MODEL=/pfad/zur/stimme.onnx`.
- `Speech Dispatcher`, `eSpeak NG`, `eSpeak`: erzwingen die jeweilige lokale Engine.
- `Custom command`: nutzt das Custom-TTS-Kommando unten.

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

Für ein Speed-of-Cinnamon-artiges Repo kann dieser Applet-Ordner unter `files/wirtelprimfgenerator@H234598/` eingecheckt werden. Die Optionen öffnen standardmäßig `https://github.com/H234598/Katzenbilder`.
