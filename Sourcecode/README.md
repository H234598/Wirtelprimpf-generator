---
tags:
  - wirtelprimpf
  - generator
  - installation
  - sourcecode
  - systemd
type: technical-documentation
status: maintained
date: 2026-07-31
aliases:
  - Wirtelprimpf Generator Sourcecode
  - Generator Installationsanleitung
created: 2026-07-31
title: Wirtelprimpf Generator Sourcecode
---

# Wirtelprimpf Generator Sourcecode

This folder contains the portable source for the Wirtelprimpf image generator.
It is deliberately free of local machine paths, GitHub account names, and
secrets.

The generator creates Wirtelprimpf images and continuing story parts with the
OpenAI API. Local PNGs remain in the private output directory. In the production
`release` mode, originals and three WebP derivatives are published as immutable
GitHub Release assets, including a high-quality lossless 3840-pixel (4K) upscale.
Every asset is publicly downloaded, SHA-256 verified and only then referenced by
the small manifest committed to the active publication archive.

## Files

- `wirtelprimpf_generator.py`: portable generator.
- `wirtelprimpf_prompt_config.md`: default prompt building blocks and template.
- `wirtelprimpf_story_prompt_config.md`: second prompt config for the continuing story mode.
- `wirtelprimpf-set-openai-key`: helper that writes an API key to a private env file.
- `env.example`: documented environment variables.
- `requirements.txt`: Python dependency list.
- `STORY_DIRECTIVES.md`: complete per-story-directives format, UI, installation, security, and operations guide.
- `../files/wirtelprimfgenerator@H234598/story_directives_core.py`: shared story-directives CLI source used by Cinnamon and systemd.
- `systemd-user/wirtelprimpf.service`: optional scheduled story-generation service template.
- `systemd-user/wirtelprimpf-atelier.service`: optional manual classic/atelier-generation service template.
- `systemd-user/wirtelprimpf.timer`: optional two-hour timer template.
- `systemd-user/wirtelprimpf-atelier.timer`: optional two-hour atelier timer template.

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

The story-directives helper must be installed before the systemd service,
because `wirtelprimpf.service` applies the active story directive through this
stable CLI path in `ExecStartPre`.

```bash
git clone https://github.com/H234598/Wirtelprimpf-generator ~/.local/share/wirtelprimpf-generator
python3 -m venv ~/.local/share/wirtelprimpf-generator/.venv
cd ~/.local/share/wirtelprimpf-generator
~/.local/share/wirtelprimpf-generator/.venv/bin/pip install -e ~/.local/share/wirtelprimpf-generator

install -Dm0755 Sourcecode/wirtelprimpf-set-openai-key ~/.local/bin/wirtelprimpf-set-openai-key
install -Dm0755 files/wirtelprimfgenerator@H234598/story_directives_core.py ~/.local/bin/wirtelprimpf-story-directives
install -Dm0644 Sourcecode/wirtelprimpf_prompt_config.md ~/.config/wirtelprimpf/prompt_config.md
install -Dm0644 Sourcecode/wirtelprimpf_story_prompt_config.md ~/.config/wirtelprimpf/story_prompt_config.md
install -Dm0644 Sourcecode/systemd-user/wirtelprimpf.service ~/.config/systemd/user/wirtelprimpf.service
install -Dm0644 Sourcecode/systemd-user/wirtelprimpf-atelier.service ~/.config/systemd/user/wirtelprimpf-atelier.service
install -Dm0644 Sourcecode/systemd-user/wirtelprimpf.timer ~/.config/systemd/user/wirtelprimpf.timer
install -Dm0644 Sourcecode/systemd-user/wirtelprimpf-atelier.timer ~/.config/systemd/user/wirtelprimpf-atelier.timer
systemctl --user daemon-reload
```

The Cinnamon installation path can install the same shared helper together with
the applet:

```bash
make install-local
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
WIRTELPRIMPF_REPO_PATH=$HOME/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001
WIRTELPRIMPF_REPO_SLUG=H234598/Wirtelprimpf-0001
WIRTELPRIMPF_REPO_SUBDIR=Wirtelprimpf
WIRTELPRIMPF_REPO_BRANCH=main
WIRTELPRIMPF_MEDIA_MODE=release
WIRTELPRIMPF_MEDIA_STAGING=$HOME/.local/state/wirtelprimpf/media-staging
WIRTELPRIMPF_MEDIA_CACHE=$HOME/.local/state/wirtelprimpf/media-cache
WIRTELPRIMPF_PUBLISH_IMMEDIATELY=true
WIRTELPRIMPF_GIT_AUTHOR_NAME="Wirtelprimpf Bot"
WIRTELPRIMPF_GIT_AUTHOR_EMAIL=wirtelprimpf@example.invalid
# Versioning follows SemVer:
# - VERSION in wirtelprimpf_generator.py is the SemVer base.
# - every committed generated image increments the patch component
# - major/minor changes are made deliberately by changing VERSION
# - verified release publications are pushed immediately
```

If `WIRTELPRIMPF_REPO_PATH` is unset, the generator creates local files only
and does not touch Git.
If `WIRTELPRIMPF_REPO_PATH` points to a non-repository directory, set
`WIRTELPRIMPF_REPO_SLUG` as `OWNER/REPOSITORY` so the generator can clone it.
`WIRTELPRIMPF_REPO_SLUG` is optional when `WIRTELPRIMPF_REPO_PATH` already
contains a valid local Git repository.

The release pipeline stores WebP derivatives in the trusted media cache. Each
entry is keyed by the original SHA-256, Pillow tool version, transform config,
format, and target width. Changed inputs create new entries; incomplete or
corrupt entries are rebuilt atomically. CI or other untrusted runs must use
the CLI's `--cache-read-only` mode and must never write to the trusted cache.

Publication policy:

- The runtime version is derived from the SemVer `VERSION` constant plus the
  generated-image patch offset in the publish-state file.
- When `VERSION` changes, the generator treats that value as the new SemVer
  base and starts counting generated-image patches from that point.
- Every new image is uploaded as original, 640-WebP, 1280-WebP, lossless
  3840-WebP (4K) and immutable record JSON; all five public downloads must
  match their local SHA-256 values.
- Git receives prompt, story documents and `media-manifest.json`, never the PNG.
- Each verified publication commit is pushed immediately.
- Exactly ten completed stories form one book and five books (50 completed stories) belong to one archive. Boundary completion
  blocks further generation until the next sequential archive is fully ready.

Runtime state is stored in:

```text
.git/wirtelprimpf_publish_state.json
```

### Prompt Configuration

Prompt construction is configured in a separate Markdown file:

```bash
WIRTELPRIMPF_PROMPT_CONFIG=$HOME/.config/wirtelprimpf/prompt_config.md
```

The config uses `## Hauptteil` as the interpreted main part. Every other `##`
section is treated as a category, and each run randomly picks one line from
each category.

The local mirror file is intentionally separate from the repository default.
If you changed local rules, keep them intact and check drift before syncing:

```bash
PROMPT_CONFIG="${WIRTELPRIMPF_PROMPT_CONFIG:-$HOME/.config/wirtelprimpf/prompt_config.md}"
cmp -s Sourcecode/wirtelprimpf_prompt_config.md "$PROMPT_CONFIG" || echo "Local prompt config differs from default"

# Optional intentional sync from repository default (back up custom file first).
if [[ -e "$PROMPT_CONFIG" ]]; then
  cp -p -- "$PROMPT_CONFIG" "$PROMPT_CONFIG.bak"
fi
mkdir -p -- "$(dirname -- "$PROMPT_CONFIG")"
install -m 600 Sourcecode/wirtelprimpf_prompt_config.md "$PROMPT_CONFIG"
```

### Operandi

The generator supports three working modes:

```bash
WIRTELPRIMPF_OPERANDI=classic
```

`classic` is the previous behavior: build one image prompt from the first
Markdown config, write the PNG next to a `.txt` prompt file, and optionally
publish both to Git.

```bash
WIRTELPRIMPF_OPERANDI=story
WIRTELPRIMPF_STORY_PROMPT_CONFIG=$HOME/.config/wirtelprimpf/story_prompt_config.md
WIRTELPRIMPF_STORY_MODEL=gpt-5-mini
WIRTELPRIMPF_STORY_DOCUMENT=$HOME/Hintergrundbilder/Wirtelprimpf_Story_I.md
WIRTELPRIMPF_STORY_STATE=$HOME/Hintergrundbilder/wirtelprimpf_story_state.json
WIRTELPRIMPF_STORY_DIRECTIVES=$HOME/.config/wirtelprimpf/story_directives.json
WIRTELPRIMPF_WORKING_DIR=$HOME/Hintergrundbilder/working
```

```bash
WIRTELPRIMPF_OPERANDI=both
```

`both` runs the classic image mode and the continuing story mode in one
execution. The stable `working/latest.*` files are rotated after the story
output, so they point at the newest story image/prompt/story triplet.

`story` loads the second Markdown config, randomly picks one line from each
category, reads the last 10 entries from the story document, generates the next
two-hour story part, then generates an image prompt for that part. The first
part of a new story document targets about one full DIN-A4 page; later parts
target about half a DIN-A4 page. When there is no previous story entry, the
text prompt also receives one temporary high-level story direction for the
opening part. That direction is not persisted in state and is not repeated for
later parts. The run writes:

- `wirtelprimpf_*.png`
- `wirtelprimpf_*.txt` with the image prompt
- `wirtelprimpf_*.md` with the new story part
- `Wirtelprimpf_Story_I.md`, appended after each successful run
- `working/latest.png`, `working/latest.txt`, and `working/latest.md`,
  replaced on every successful run
- `working/Full_Story.md`, a symlink to the active full story document

When Git publishing is enabled, the same stable working files are copied into
the repository under `Wirtelprimpf/working/`. The repository
`Wirtelprimpf/working/Full_Story.md` link is written relative to the repository
story document so GitHub can show the current full story snapshot.

### Per-story directives

The shared CLI resolves the effective current volume from
`WIRTELPRIMPF_STORY_STATE`, loads the versioned directives ledger, and projects
the active volume's complete directive into the managed section of
`WIRTELPRIMPF_STORY_PROMPT_CONFIG`.

Status:

```bash
~/.local/bin/wirtelprimpf-story-directives \
  status --env-file ~/.config/wirtelprimpf/openai.env
```

Apply manually:

```bash
~/.local/bin/wirtelprimpf-story-directives \
  apply --env-file ~/.config/wirtelprimpf/openai.env
```

The Cinnamon settings page shows the effective current story and the next two
stories as editable. Every older story is shown read-only. Full format,
migration, safety, and recovery details are documented in
`Sourcecode/STORY_DIRECTIVES.md`.

To close the current story arc, set:

```bash
WIRTELPRIMPF_STORY_FINISH=true
```

The generator persists that request in `WIRTELPRIMPF_STORY_STATE`, lets the
current story end over 3-5 story parts, and then starts the next volume on the
following story run, for example `Wirtelprimpf_Story_II.md`. Every later
off-to-on press repeats that sequence from the current volume, so the next
accepted close request after Story II starts `Wirtelprimpf_Story_III.md`, then
IV, and so on. Turn the switch off again after the request has been accepted;
the persisted state prevents a still-enabled switch from immediately closing
every new volume.

When the final closing part is written, the generator asks the story model for
a short title and prepends it as an H1 if the story document does not already
have one.

For systemd, set `WIRTELPRIMPF_OPERANDI=story` in
`~/.config/wirtelprimpf/openai.env` or via a user-service override.

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
Flex Processing ist standardmäßig aktiv und wird als `service_tier: flex` nur an
die Textgenerierung gesendet. Bildrequests erhalten keinen Flex-Service-Tier.

Steuerung:

```bash
WIRTELPRIMPF_FLEX_PROCESSING=on
```

```bash
WIRTELPRIMPF_FLEX_PROCESSING=off
```

```bash
WIRTELPRIMPF_FLEX_PROCESSING=flex
```

Wenn `WIRTELPRIMPF_FLEX_PROCESSING` nicht gesetzt ist, bleibt Flex Processing
an.

### Image Batch API

Mit `WIRTELPRIMPF_IMAGE_BATCH_MODE=on` werden Bildrequests als asynchroner
OpenAI-Batch über `/v1/images/generations` eingereicht. Der erste Lauf legt
einen privaten Pending-Zustand im Working-Verzeichnis an; ein späterer Lauf
holt das Ergebnis ab und veröffentlicht es. Der Standardwert `off` nutzt den
direkten Images-Request. Der Batch-Modus hat das dokumentierte Abschlussfenster
von bis zu 24 Stunden und darf deshalb nicht als sofortige Bildantwort behandelt
werden.

## Manual Run

For story mode, apply the active directive before a direct generator run, just
as the systemd service does:

```bash
set -a
. ~/.config/wirtelprimpf/openai.env
set +a
~/.local/share/wirtelprimpf-generator/.venv/bin/python \
  ~/.local/bin/wirtelprimpf-story-directives \
  apply --env-file ~/.config/wirtelprimpf/openai.env
~/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-generator
```

### Wiederhol-Checks bei Versionssprung

Für den gewünschten Ablauf:

- Warten auf eine aus `VERSION` plus Publish-State abgeleitete SemVer-Änderung
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

`watch_minor_version.sh` erzwingt einen einzelnen aktiven Lauf über Locking.
Parallel-Starts werden auf demselben Host/Workdir abgeblockt.

`check_wirtelprimpf.sh` verwendet temporäre Dateien mit automatischer
Aufräumung.

`watch_minor_version.sh` beobachtet dieselbe SemVer-Ableitung wie der Generator.
Standard ist: `VERSION` liefert Major/Minor/Basis-Patch, der Publish-State addiert
den generierten Patch-Zähler.

Fehlertoleranzverhalten:

- Der Watcher beendet sich mit `exit 1`, wenn keine nutzbare Python-Interpretation gefunden wird.
- Er fällt auf einen sicher reparierten lokalen Stand zurück, wenn die State-Datei fehlt oder ungültig ist, und bricht ab, wenn diese Reparatur nicht geschrieben werden kann.
- Er bricht bei fehlerhafter Versionsberechnung (`get_minor_version`) und beim Timestamp-Schreiben nicht still, sondern mit klarer Logmeldung.

### Dauerstart via systemd --user

Du kannst den Watcher auch automatisch beim Benutzerstart laufen lassen.
Watcher-Feintuning (`SLEEP_SECONDS`, `DEFAULT_RETRY_DELAY_SECONDS`,
`MAX_STALE_LOCK_SECONDS`) erfolgt ausschließlich über Service-Overrides, zum
Beispiel `systemctl --user edit wirtelprimpf-version-watch.service`, und nicht
über `openai.env`.

Beispiel ohne Secret-File, nur mit Watcher-Parametern:

```bash
mkdir -p ~/.config/systemd/user/wirtelprimpf-version-watch.service.d
cat <<'EOF' > ~/.config/systemd/user/wirtelprimpf-version-watch.service.d/override.conf
[Service]
Environment=SLEEP_SECONDS=300
Environment=DEFAULT_RETRY_DELAY_SECONDS=5
Environment=MAX_STALE_LOCK_SECONDS=900
EOF

systemctl --user daemon-reload
systemctl --user restart wirtelprimpf-version-watch.service
```

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
- Bei jeder erkannten Versionsänderung wird genau ein Check-Block ausgeführt.
- Danach kehrt er in das Intervall zurück.

Validation helpers:

```bash
~/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-generator --check-config
~/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-generator --status --json
~/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-generator --dry-run
~/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-generator --json
~/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-generator --version
```

Optional mit Repo-Kontext für patch-state-reiche Checks:

```bash
WIRTELPRIMPF_REPO_PATH=/path/to/local/git/repo WIRTELPRIMPF_REPO_SLUG= WIRTELPRIMPF_REPO_BRANCH=main \
  ~/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-generator --check-config --json
WIRTELPRIMPF_REPO_PATH=/path/to/local/git/repo WIRTELPRIMPF_REPO_SLUG= WIRTELPRIMPF_REPO_BRANCH=main \
  ~/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-generator --dry-run --json
```

### Machine-readable status

`--status` and `--check-config --json` print structured diagnostics and use the
same stable envelope. The JSON form can be used for automation and is emitted
as one compact object per line:

```json
{
  "ok": true,
  "version": "0.6.65",
  "timestamp": "2026-06-02T19:23:00Z",
  "mode": "status",
  "status": "ok",
  "exit_code": 0,
  "details": {
    "git_available": true,
    "gh_available": false,
    "openai_key_present": true,
    "semver_base": "1.0.0",
    "semver_base_patch_count": 0,
    "semver_patch_offset": 65,
    "publish_push_count": 0,
    "publish_push_interval_patches": 100,
    "publish_release_push_interval": 10
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
fields (`ok`, `version`, `timestamp`, `mode`, `status`, `exit_code`) per rendered
prompt record.

Praktische Fehlerauswertung:

- `exit_code == 0`: kein command-wide Fehler; bei `--status` können Einzelchecks fehlerhaft sein, ohne dass der Kommando-Exitcode steigt.
- `exit_code == 1`: kritische Setup-, Config- oder Repo-Fehler; keine erfolgreiche Ausführung.
- `exit_code == 2`: one or more per-plan generation, write, transform, or repository-publication operations failed; das gilt auch dann, wenn alle Pläne fehlschlagen.
- Für `dry_run`-Events gilt: `status` spiegelt den Laufstatus pro Block; `checks` enthält die Einzelbewertung.

`mode` ist ein strikter Diskriminator und kann nur `status`, `check_config`,
`dry_run` oder `run` sein.

`exit_code` ist ein Top-Level-Feld für kommandoweite Ergebnisse. Verschachtelte
`summary`-Payloads enthalten absichtlich nur Zähler wie `success`, `failed`,
`skipped`, `prompts` und `total`.

`--status` enthält einen nicht verpflichtenden `openai_key`-Check, wenn kein
API-Key vorhanden ist. Die Diagnose markiert den Befehl nicht als fehlgeschlagen,
weil Zugangsdaten erst für echte Generierungsaufrufe notwendig sind.

Für nicht JSON-basiertes `--status` gibt der Befehl `mode` und `exit_code`
ausdrücklich als Textzeilen aus.

### Exit codes

- `0`: success
- `1`: unrecoverable setup/configuration failure for execution paths
- `2`: one or more per-plan generation, write, transform, or repository-publication operations failed, including when all plans fail

## Two-hour Timer

```bash
systemctl --user daemon-reload
systemctl --user enable --now wirtelprimpf.timer
systemctl --user status wirtelprimpf.timer --no-pager
```

Logs:

```bash
journalctl --user -u wirtelprimpf.service -n 100 --no-pager
```

Wenn der Dienst wegen der systemd-Härtung nicht startet oder sofort beendet
wird, prüfe zuerst:

```bash
systemd-analyze verify Sourcecode/systemd-user/wirtelprimpf.service
journalctl --user -u wirtelprimpf.service -n 200 --no-pager
```

`MemoryDenyWriteExecute=true` ist für den Python/OpenAI/Pillow-Pfad in der Regel
unkritisch. Sollte der Dienst trotzdem mit Hardening-bezogenen
`EACCES`- beziehungsweise `Operation not permitted`-Fehlern starten oder
abbrechen, prüfe zuerst den konkreten Fehler im Journal und deaktiviere diese
Direktive testweise isoliert als letzten Schritt.

## Output

Classic mode creates:

```text
wirtelprimpf_YYYY-MM-DD_HH-MM-SS.png
wirtelprimpf_YYYY-MM-DD_HH-MM-SS.txt
```

The `.txt` file contains the exact prompt used for the image. Story mode also
creates the story-part Markdown, appends the active full-story document, and
rotates the stable files under `working/` as described above.
