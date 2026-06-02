# Wirtelprimpf Generator Sourcecode

This folder contains the portable source for the Wirtelprimpf image generator.
It is deliberately free of local machine paths, GitHub account names, and
secrets.

The generator creates one Wirtelprimpf-style cat image with the OpenAI Images
API, writes the PNG and prompt text file to a local output directory, and can
optionally copy both files into a Git repository folder, commit them, and push
them.

## Files

- `wirtelprimpf_generator.py`: portable generator.
- `wirtelprimpf_prompt_config.json`: default prompt building blocks and template.
- `wirtelprimpf-set-openai-key`: helper that writes an API key to a private env file.
- `env.example`: documented environment variables.
- `requirements.txt`: Python dependency list.
- `systemd-user/wirtelprimpf.service`: optional user service template.
- `systemd-user/wirtelprimpf.timer`: optional hourly timer template.

## Requirements

- Python 3.11 or newer.
- `openai` Python package.
- `Pillow` Python package for final output resizing.
- `git` if Git publishing is enabled.
- GitHub CLI `gh` if the configured repository should be cloned automatically.
- An OpenAI API key that can call Images generation. Restricted keys need at
  least this scope:

```text
api.model.images.request
```

## Install Example

```bash
python3 -m venv ~/.local/share/wirtelprimpf-venv
~/.local/share/wirtelprimpf-venv/bin/pip install -r Sourcecode/requirements.txt

install -Dm0755 Sourcecode/wirtelprimpf_generator.py ~/.local/bin/wirtelprimpf_generator.py
install -Dm0755 Sourcecode/wirtelprimpf-set-openai-key ~/.local/bin/wirtelprimpf-set-openai-key
install -Dm0644 Sourcecode/wirtelprimpf_prompt_config.json ~/.config/wirtelprimpf/prompt_config.json
install -Dm0644 Sourcecode/systemd-user/wirtelprimpf.service ~/.config/systemd/user/wirtelprimpf.service
install -Dm0644 Sourcecode/systemd-user/wirtelprimpf.timer ~/.config/systemd/user/wirtelprimpf.timer
```

## Configuration

Create a private environment file:

```bash
mkdir -p ~/.config/wirtelprimpf
cp Sourcecode/env.example ~/.config/wirtelprimpf/openai.env
chmod 600 ~/.config/wirtelprimpf/openai.env
```

Then edit it and replace placeholders. Alternatively, write only the API key
with:

```bash
~/.local/bin/wirtelprimpf-set-openai-key ~/.config/wirtelprimpf/openai.env
```

For Git publishing, set these values in the env file:

```bash
WIRTELPRIMPF_REPO_PATH=/path/to/local/git/worktree
WIRTELPRIMPF_REPO_SLUG=OWNER/REPOSITORY
WIRTELPRIMPF_REPO_SUBDIR=Wirtelprimpf
WIRTELPRIMPF_REPO_BRANCH=main
WIRTELPRIMPF_GIT_AUTHOR_NAME="Wirtelprimpf Bot"
WIRTELPRIMPF_GIT_AUTHOR_EMAIL=wirtelprimpf@example.invalid
WIRTELPRIMPF_PATCHES_PER_MINOR=100
WIRTELPRIMPF_MINOR_PUSHES_PER_RELEASE=10
WIRTELPRIMPF_MAJOR_VERSION_BUMP=0
WIRTELPRIMPF_BREAKING_CHANGE=0

# Optional: local publishing policy for commit cadence.
# Default behavior in this repository documentation:
# - every patch change is committed
# - patch number equals patch count inside the current minor window
#   (after each commit: .1, .2, ... .99, .100)
# - exactly every 100 committed patches, minor increases by 1
# - exactly every 100 minor increases, major increases by 1
# - release is prepared every 10 minor pushes
# - for breaking changes or new API features, bump major manually
# - configure WIRTELPRIMPF_MAJOR_VERSION_BUMP=N to add a manual major offset
#
# Every committed patch is also the patch version number.
```

If `WIRTELPRIMPF_REPO_PATH` is unset, the generator creates local files only
and does not touch Git.

Git-Publish policy:

- `WIRTELPRIMPF_PATCHES_PER_MINOR` is fixed to `100`; the runtime
  rejects any other value.
- `WIRTELPRIMPF_MINOR_PUSHES_PER_RELEASE` controls how many pushed minor
  boundaries should be grouped before a release should be prepared. Default:
  `10`.
- Set `WIRTELPRIMPF_BREAKING_CHANGE=true` for a one-time major bump on this
  execution (in addition to `WIRTELPRIMPF_MAJOR_VERSION_BUMP`).

Runtime state is stored in:

```text
.git/wirtelprimpf_publish_state.json
```

### Prompt Configuration

Prompt construction is configured in a separate JSON file:

```bash
WIRTELPRIMPF_PROMPT_CONFIG=$HOME/.config/wirtelprimpf/prompt_config.json
```

The config contains the random pools for `settings`, `actions`, `jokes`,
`moods`, and `styles`, plus the final `template`. The template can reference
these placeholders:

```text
{setting}
{action}
{joke}
{mood}
{style}
```

### Resolution

The OpenAI image API does not generate arbitrary 4K/2K frames directly. The
generator therefore separates API input size from final output resolution:

```bash
WIRTELPRIMPF_IMAGE_SIZE=1536x1024
WIRTELPRIMPF_OUTPUT_RESOLUTION=2k
```

`WIRTELPRIMPF_OUTPUT_RESOLUTION=2k` writes a final `2560x1440` PNG. Other
supported aliases are `4k` (`3840x2160`), `qhd`, `1440p`, `uhd`, `2160p`,
`original`, `source`, and `none`. Custom values like `1920x1080` are accepted.
Flex Processing ist standardmäßig aktiv und wird als `processing: high` an die
OpenAI-Images-API-Anfrage angehängt.

Steuerung:

```bash
WIRTELPRIMPF_FLEX_PROCESSING=on
```

```bash
WIRTELPRIMPF_FLEX_PROCESSING=off
```

```bash
WIRTELPRIMPF_FLEX_PROCESSING=low
```

```bash
WIRTELPRIMPF_FLEX_PROCESSING=high
```

Wenn `WIRTELPRIMPF_FLEX_PROCESSING` nicht gesetzt ist, bleibt Flex Processing
an.

## Manual Run

```bash
set -a
. ~/.config/wirtelprimpf/openai.env
set +a
~/.local/share/wirtelprimpf-venv/bin/python ~/.local/bin/wirtelprimpf_generator.py
```

### Wiederhol-Checks bei Minor-Version-Sprung

Für den gewünschten Ablauf:

- Warten auf `major.minor`-Änderung von `VERSION` in `wirtelprimpf_generator.py`
- Bei Änderung: kompletten Check-Block einmal ausführen
- Danach weiter in den Wartezustand gehen (`repeat`)

```bash
cd "$(git rev-parse --show-toplevel)"
chmod +x Sourcecode/check_wirtelprimpf.sh Sourcecode/watch_minor_version.sh

# Optionaler One-Shot-Check:
./Sourcecode/watch_minor_version.sh --once

# Dauerlauf:
./Sourcecode/watch_minor_version.sh

# Mit anderem Intervall (Sekunden):
SLEEP_SECONDS=120 ./Sourcecode/watch_minor_version.sh

# Optional: aggressive/robuste Lock- und Retry-Parameter
MAX_STALE_LOCK_SECONDS=1200 DEFAULT_RETRY_DELAY_SECONDS=10 ./Sourcecode/watch_minor_version.sh --once
```

Hinweise zu Minima:
- `SLEEP_SECONDS >= 1`
- `DEFAULT_RETRY_DELAY_SECONDS >= 1`
- `MAX_STALE_LOCK_SECONDS >= 10`

Ein einmaliger Check kann auch unabhängig laufen:

```bash
./Sourcecode/check_wirtelprimpf.sh
```

`watch_minor_version.sh` erzwingt einen einzelnen aktiven Lauf über Locking. Parallel-Starts werden auf demselben Host/Workdir abgeblockt.

`check_wirtelprimpf.sh` verwendet temporäre Dateien mit automatischer Aufräumung.

`watch_minor_version.sh` beobachtet den in der Generator-Logik berechneten Minor-Release-Fortschritt.
Standard ist: 100 Patches -> minor+, 100 Minors -> major+ (mit Patch-Suffix/Prefix).

Fehlertoleranzverhalten:
- Der Watcher beendet sich mit `exit 1`, wenn keine nutzbare Python-Interpretation gefunden wird.
- Er fällt auf einen sicher reparierten lokalen Stand zurück, wenn die State-Datei fehlt oder ungültig ist, und bricht ab, wenn diese Reparatur nicht geschrieben werden kann.
- Er bricht bei fehlerhafter Versionsberechnung (`get_minor_version`) und beim Timestamp-Schreiben nicht still, sondern mit klarer Logmeldung.

### Dauerstart via systemd --user

Du kannst den Watcher auch automatisch beim Benutzerstart laufen lassen:

```bash
mkdir -p ~/.config/systemd/user
cp Sourcecode/systemd-user/wirtelprimpf-version-watch.service ~/.config/systemd/user/wirtelprimpf-version-watch.service
cp Sourcecode/systemd-user/wirtelprimpf-version-watch.timer ~/.config/systemd/user/wirtelprimpf-version-watch.timer

systemctl --user daemon-reload
systemctl --user enable --now wirtelprimpf-version-watch.timer
systemctl --user status wirtelprimpf-version-watch.service --no-pager
systemctl --user status wirtelprimpf-version-watch.timer --no-pager
```

Der Dienst läuft im Dauermodus:
- Ein einzelner Watcher-Prozess hält exklusiv den Lock.
- Bei jeder erkannten Minor-Änderung wird genau ein Check-Block ausgeführt.
- Danach kehrt er in das Intervall zurück.

Validation helpers:

```bash
~/.local/share/wirtelprimpf-venv/bin/python ~/.local/bin/wirtelprimpf_generator.py --check-config
~/.local/share/wirtelprimpf-venv/bin/python ~/.local/bin/wirtelprimpf_generator.py --status --json
~/.local/share/wirtelprimpf-venv/bin/python ~/.local/bin/wirtelprimpf_generator.py --dry-run
~/.local/share/wirtelprimpf-venv/bin/python ~/.local/bin/wirtelprimpf_generator.py --json
~/.local/share/wirtelprimpf-venv/bin/python ~/.local/bin/wirtelprimpf_generator.py --version
```

Optional mit Repo-Kontext (für patch-state-reiche Checks):

```bash
WIRTELPRIMPF_REPO_PATH=/path/to/local/git/repo WIRTELPRIMPF_REPO_SLUG= WIRTELPRIMPF_REPO_BRANCH=main \
  ~/.local/share/wirtelprimpf-venv/bin/python ~/.local/bin/wirtelprimpf_generator.py --check-config --json
WIRTELPRIMPF_REPO_PATH=/path/to/local/git/repo WIRTELPRIMPF_REPO_SLUG= WIRTELPRIMPF_REPO_BRANCH=main \
  ~/.local/share/wirtelprimpf-venv/bin/python ~/.local/bin/wirtelprimpf_generator.py --dry-run --json
```

### Machine-readable status

`--status` and `--check-config --json` print structured diagnostics and use the
same stable envelope:
The JSON form can be used for automation and is emitted as one compact object per line:

```json
{
  "ok": true,
  "version": "0.5.6-hardening",
  "timestamp": "2026-06-02T19:23:00Z",
  "mode": "status",
  "status": "ok",
  "exit_code": 0,
  "details": {
    "git_available": true,
    "gh_available": false,
    "openai_key_present": true,
    "major_version_bump": 0,
    "breaking_change": false,
    "effective_major_version_base": 0
  },
  "checks": [
    {"name": "prompt_config_file", "ok": true, "path": "..."},
    {"name": "prompt_config_parse", "ok": true, "prompt_count": 1},
    {"name": "local_outdir", "ok": true, "path": "..."},
    {"name": "repo", "ok": false, "path": "...", "message": "..."}
  ]
}
```

`--dry-run --json` also emits machine-readable records using the same top-level
fields (`ok`, `version`, `timestamp`, `mode`, `status`, `exit_code`) per rendered prompt
record.

`mode` is a strict discriminator in machine-readable output and can only be:
`status`, `check_config`, `dry_run`, or `run`.

`exit_code` is treated as a top-level field for command-level results; nested
`summary` payloads intentionally only carry metric counters (`success`, `failed`,
`skipped`, `prompts`, `total`).

`--status` includes a non-required `openai_key` check entry when no API key is
present; it reports diagnostics without marking the command as failed, because API
credentials are only required for actual generation calls.

For non-JSON `--status`, the command prints an explicit `mode` and `exit_code`
line in its text output.

### Exit codes

- `0`: success
- `1`: unrecoverable setup/configuration failure (missing key, invalid config, repo errors)
- `2`: partial failure (one or more prompts/images failed, but at least one succeeded)

## Hourly Timer

```bash
systemctl --user daemon-reload
systemctl --user enable --now wirtelprimpf.timer
systemctl --user status wirtelprimpf.timer --no-pager
```

Logs:

```bash
journalctl --user -u wirtelprimpf.service -n 100 --no-pager
```

## Output

Each run creates two files:

```text
wirtelprimpf_YYYY-MM-DD_HH-MM-SS.png
wirtelprimpf_YYYY-MM-DD_HH-MM-SS.txt
```

The `.txt` file contains the exact prompt used for the image.
