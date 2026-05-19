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
```

If `WIRTELPRIMPF_REPO_PATH` is unset, the generator creates local files only
and does not touch Git.

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

## Manual Run

```bash
set -a
. ~/.config/wirtelprimpf/openai.env
set +a
~/.local/share/wirtelprimpf-venv/bin/python ~/.local/bin/wirtelprimpf_generator.py
```

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
