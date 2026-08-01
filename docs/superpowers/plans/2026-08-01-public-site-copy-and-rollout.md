# Public Site Copy and Coordinated Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the six approved public text changes, verify both site profiles, merge the complete transactional-settings feature, install the merged generator/applet/admin locally, and repin/deploy `Wirtelprimpf-0001` without changing Cloudflare.

**Architecture:** Public copy remains a small independent Astro change guarded by source and built-artifact contracts. After the complete generator branch passes review and merges, the local installation is replaced from that exact merged commit with private backups and targeted reloads. The archive repository then pins the immutable merged factory SHA so its reusable Pages build consumes the same site source.

**Tech Stack:** Astro 7, TypeScript/Node.js 24 tests, Python artifact validator, Git/GitHub CLI, systemd user services, Cinnamon D-Bus, GitHub Pages.

## Global Constraints

- Execute this plan only after every gate in `2026-08-01-transactional-settings-live-sync-status.md` is green.
- Preserve newest-story-part-first behavior, ten stories per book, five books/50 stories per archive, release-only image storage, canonical URLs, feed, sitemap, and artifact validation.
- Change exactly six public copy contracts: `Telacores:`, the Hero `Wo Katzen Unfug und Geschichte schreiben.`, two complete sentence removals, removal of `hashgebunden`, and the exact project-status sentence `Dass er unbedeutend ist, und nichts weiß.`
- Do not create `Wirtelprimpf-0002`; it remains gated on completion of Story 50.
- Do not change any Cloudflare DNS record, redirect rule, token policy, or zone setting in this plan.
- Do not change the Cinnamon upstream fix or `codex-master` freeze/watchdog configuration.
- Preserve user work and require clean, expected diffs before commit, push, merge, install, and archive pinning.
- Use a feature branch/worktree for generator code and a separate clean archive checkout for the immutable factory-reference commit.
- The generator receives one reviewed commit series; `Wirtelprimpf-0001` receives only the two-line factory SHA pin plus its plan-compatible validation.
- Respect the user's fleet limit: the generator may use only its one persistent `gpt-5.6-sol`/`max` worker; when Task 5 reaches the archive repository, that separate repository may use at most one separate persistent worker. Never dispatch task-per-agent swarms.

## Locked File Structure

### Generator website files

- Create: `web/tests/copy-contract.test.ts` — exact required/forbidden public wording.
- Modify: `web/src/layouts/BaseLayout.astro` — hub eyebrow `Telacores:`.
- Modify: `web/src/pages/index.astro` — remove exactly the two approved sentences.
- Modify: `web/src/components/MediaCard.astro` — remove `hashgebunden` only from copy.
- Modify: `web/src/pages/projekt/status.astro` — exact replacement sentence.

### Archive repository file

- Modify in `/home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001`: `.github/workflows/pages.yml` — pin both reusable-workflow ref and `factory_ref` to the merged generator SHA.

### Operational artifacts

- Append the final implementation evidence to the canonical Obsidian plan and parallel incoming plan; do not delete or rewrite historical sections.
- Store private deployment backup beneath `/home/teladi/.local/state/wirtelprimpf/deploy-backups/` with mode `0700`.

---

### Task 1: Exact public-copy contract and Astro source changes

**Files:**
- Create: `web/tests/copy-contract.test.ts`
- Modify: `web/src/layouts/BaseLayout.astro:47`
- Modify: `web/src/pages/index.astro:25-27`
- Modify: `web/src/components/MediaCard.astro:18`
- Modify: `web/src/pages/projekt/status.astro:9`

**Interfaces:**
- Consumes: existing `loadSiteData()` profile distinction.
- Produces: exact source wording for both hub and archive builds.
- Does not alter any data loader, media URL, story ordering, or route.

- [ ] **Step 1: Write the failing copy-contract test**

```typescript
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const root = new URL("../src/", import.meta.url);
const layout = readFileSync(new URL("layouts/BaseLayout.astro", root), "utf8");
const index = readFileSync(new URL("pages/index.astro", root), "utf8");
const mediaCard = readFileSync(new URL("components/MediaCard.astro", root), "utf8");
const projectStatus = readFileSync(new URL("pages/projekt/status.astro", root), "utf8");

test("approved public copy is exact and superseded wording is absent", () => {
  assert.match(layout, /data\.profile === "hub" \? "Telacores:"/);
  assert.doesNotMatch(layout, /Zentrale Landingpage/);

  assert.doesNotMatch(index, /Die kanonische Storyansicht bleibt zusätzlich chronologisch lesbar\./);
  assert.doesNotMatch(index, /Keine leeren Repositories, keine Lücken\./);
  assert.match(index, /Wo Katzen Unfug und Geschichte schreiben\./);
  assert.doesNotMatch(index, /Wo Katzen, Möhren und Unfug Geschichte schreiben\./);

  assert.match(mediaCard, /Im Release <code>\{item\.release_tag\}<\/code> archiviert\./);
  assert.doesNotMatch(mediaCard, /hashgebunden archiviert/);

  assert.match(projectStatus, /Dass er unbedeutend ist, und nichts weiß\./);
  assert.doesNotMatch(projectStatus, /Keine Live-API, keine Trackingabfrage/);
});
```

- [ ] **Step 2: Run the focused test and verify all six old contracts fail**

Run: `npm --prefix web test -- --test-name-pattern='approved public copy'`

If npm's script does not forward the filter on the installed Node version, run: `cd web && node --test --experimental-strip-types tests/copy-contract.test.ts`.

Expected: failures show the current old label, both old landing-page sentences, `hashgebunden`, and the old project-status sentence.

The failure set must also show the old Hero sentence with `Möhren`.

- [ ] **Step 3: Apply the exact four source-file edits**

Use these exact replacements:

```astro
<span><small>{data.profile === "hub" ? "Telacores:" : `Publikationsarchiv ${String(data.archiveIndex).padStart(4, "0")}`}</small>{data.title}</span>
```

```astro
<h1>Wo Katzen Unfug und Geschichte schreiben.</h1>
```

```astro
<p>Je zehn abgeschlossene Storys ergeben ein Buch; nach fünf Büchern beziehungsweise 50 Storys entsteht automatisch das nächste Archiv.</p>
```

```astro
<p>{currentParts.length ? `${currentParts.length} Teile in der aktuellen Story.` : "Sobald der nächste Storyteil veröffentlicht ist, erscheint er hier."}</p>
```

```astro
<p>Im Release <code>{item.release_tag}</code> archiviert.</p>
```

```astro
<header class="page-heading"><span class="eyebrow">Öffentlicher Status</span><h1>Was dieser Build sicher weiß.</h1><p class="lede">Dass er unbedeutend ist, und nichts weiß.</p></header>
```

Do not reflow unrelated compact Astro markup.

- [ ] **Step 4: Run web unit and type checks**

Run:

```bash
npm --prefix web test
WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site" WIRTELPRIMPF_SITE_PROFILE=hub npm --prefix web run check
```

Expected: all Node tests pass and Astro reports zero errors.

- [ ] **Step 5: Commit the independently reviewable copy change**

```bash
git add web/tests/copy-contract.test.ts web/src/layouts/BaseLayout.astro web/src/pages/index.astro web/src/components/MediaCard.astro web/src/pages/projekt/status.astro
git commit -m "feat(web): apply approved public story copy"
```

### Task 2: Build and validate both immutable site profiles

**Files:**
- Read: `web/dist/**` generated artifacts only; do not commit them.
- Read: `scripts/validate_pages_artifact.py`.

**Interfaces:**
- Consumes: Task 1 source and fixtures.
- Produces: locally validated hub and archive artifacts with exact required/forbidden text.

- [ ] **Step 1: Build and validate the hub profile**

Run:

```bash
WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site" \
WIRTELPRIMPF_SITE_PROFILE=hub \
WIRTELPRIMPF_SITE_URL=https://wirtelprimpf.telacore.org \
npm --prefix web run build
python3 scripts/validate_pages_artifact.py web/dist --expected-domain wirtelprimpf.telacore.org
```

Expected: build and validator exit 0.

- [ ] **Step 2: Assert the hub artifact's exact copy**

Run:

```bash
rg -F -- 'Telacores:' web/dist/index.html
rg -F -- 'Wo Katzen Unfug und Geschichte schreiben.' web/dist/index.html
rg -F -- 'Dass er unbedeutend ist, und nichts weiß.' web/dist/projekt/status/index.html
rg -F -- 'Im Release' web/dist/index.html
if rg -F -- 'Zentrale Landingpage' web/dist; then exit 1; fi
if rg -F -- 'Wo Katzen, Möhren und Unfug Geschichte schreiben.' web/dist; then exit 1; fi
if rg -F -- 'Die kanonische Storyansicht bleibt zusätzlich chronologisch lesbar.' web/dist; then exit 1; fi
if rg -F -- 'Keine leeren Repositories, keine Lücken.' web/dist; then exit 1; fi
if rg -F -- 'hashgebunden archiviert' web/dist; then exit 1; fi
if rg -F -- 'Keine Live-API, keine Trackingabfrage' web/dist; then exit 1; fi
```

Expected: required matches exist and every forbidden scan is empty.

- [ ] **Step 3: Build and validate the archive profile**

Run:

```bash
WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site" \
WIRTELPRIMPF_SITE_PROFILE=archive \
WIRTELPRIMPF_SITE_URL=https://wirtelprimpf-0001.telacore.org \
npm --prefix web run build
python3 scripts/validate_pages_artifact.py web/dist --expected-domain wirtelprimpf-0001.telacore.org
```

Expected: build and validator exit 0; generated canonical URLs use the archive hostname.

- [ ] **Step 4: Assert archive-specific wording and retained contracts**

Run:

```bash
rg -F -- 'Publikationsarchiv 0001' web/dist/index.html
rg -F -- 'Im Release' web/dist/index.html
rg -F -- ' archiviert.' web/dist/index.html
rg -F -- 'Dass er unbedeutend ist, und nichts weiß.' web/dist/projekt/status/index.html
rg -F -- '<link rel="canonical" href="https://wirtelprimpf-0001.telacore.org/' web/dist/index.html
if rg -F -- 'hashgebunden archiviert' web/dist; then exit 1; fi
```

Expected: all required matches exist; the archive header remains `Publikationsarchiv 0001`, not `Telacores:`.

- [ ] **Step 5: Verify generated files remain untracked**

Run: `git status --short`

Expected: no `web/dist` or dependency artifact appears; only expected plan/implementation files are tracked.

### Task 3: Full repository regression, review, push, PR, and merge

**Files:**
- Review: every generator branch diff from its merge base.
- No new production file is introduced in this task.

**Interfaces:**
- Consumes: all commits from both implementation plans.
- Produces: reviewed, CI-green merged `H234598/Wirtelprimpf-generator@main`.

- [ ] **Step 1: Run the complete local matrix from a clean branch**

Run:

```bash
python -m unittest discover -s tests/platform -p 'test_*.py' -v
make check
python -m compileall -q Sourcecode wirtelprimpf_platform scripts
npm --prefix web test
WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site" WIRTELPRIMPF_SITE_PROFILE=hub npm --prefix web run check
git diff --check
```

Then repeat the two profile builds and validators from Task 2. Expected: every command exits 0.

- [ ] **Step 2: Perform a fresh spec and security diff review**

Run:

```bash
git status --short
git log --oneline --decorate "$(git merge-base HEAD origin/main)"..HEAD
git diff --stat "$(git merge-base HEAD origin/main)"..HEAD
git diff "$(git merge-base HEAD origin/main)"..HEAD -- Sourcecode/systemd-user/wirtelprimpf-admin.service wirtelprimpf_platform files/wirtelprimfgenerator@H234598 web tests
```

Review every changed hunk against the approved spec. Explicitly verify no response/log path returns secrets, no applet file writer remains, `/api/status` has no network client, and public copy has exactly six changes.

- [ ] **Step 3: Incorporate newly arrived user commits, rerun, and push without force**

Run:

```bash
git fetch origin
if ! git merge-base --is-ancestor origin/main HEAD; then
  git log --oneline --decorate HEAD..origin/main
  git merge --no-edit origin/main
  python -m unittest discover -s tests/platform -p 'test_*.py' -v
  make check
  npm --prefix web test
fi
git merge-base --is-ancestor origin/main HEAD
git push --set-upstream origin HEAD
```

Expected: already-published user commits are preserved in branch history, the post-merge matrix is green, and the branch push succeeds without force. Stop for review if the merge reports a conflict or introduces a scope-changing behavior; do not resolve a user conflict by discarding either side.

- [ ] **Step 4: Open the pull request and wait for all checks**

Run:

```bash
generator_pr_url="$(gh pr create \
  --repo H234598/Wirtelprimpf-generator \
  --base main \
  --head "$(git branch --show-current)" \
  --title 'Transactional settings, live sync, status, and approved site copy' \
  --body 'Implements the approved 2026-08-01 design: one transactional configuration core, conflict-safe live web/applet synchronization, real local /api/status, shared model dropdowns, effective systemd timer application, and the six approved public copy changes. Cloudflare and Cinnamon upstream work remain out of scope.')"
generator_pr_number="${generator_pr_url##*/}"
[[ "$generator_pr_number" =~ ^[0-9]+$ ]]
gh pr checks "$generator_pr_number" --repo H234598/Wirtelprimpf-generator --watch --fail-fast
```

Expected: applet, platform, web, Pages-related checks, and configured review gates are successful. Address actual review findings with new focused test-first commits and rerun the full affected matrix; do not dismiss findings without evidence.

- [ ] **Step 5: Merge through GitHub and record the immutable generator SHA**

Run:

```bash
generator_pr_number="$(gh pr view --repo H234598/Wirtelprimpf-generator --json number --jq .number)"
[[ "$generator_pr_number" =~ ^[0-9]+$ ]]
gh pr merge "$generator_pr_number" --repo H234598/Wirtelprimpf-generator --merge --delete-branch
git -C /home/teladi/.local/share/wirtelprimpf-generator fetch origin
git -C /home/teladi/.local/share/wirtelprimpf-generator switch main
git -C /home/teladi/.local/share/wirtelprimpf-generator pull --ff-only origin main
git -C /home/teladi/.local/share/wirtelprimpf-generator rev-parse HEAD
```

Expected: local main is clean and equals `origin/main`. Record the printed 40-character SHA as the only factory reference permitted in Task 5.

### Task 4: Private backup, merged local install, targeted reload, and live synchronization smoke

**Files:**
- Back up: Wirtel environment, separate Cloudflare token file, timer drop-in, revision signal, installed applet, and installed user units.
- Install from: `/home/teladi/.local/share/wirtelprimpf-generator` merged main.

**Interfaces:**
- Consumes: merged generator SHA from Task 3.
- Produces: local package/admin/applet/user-unit installation exactly matching merged main.
- Preserves: token values, timer enabled/active state, and all unrelated Cinnamon applets/services.

- [ ] **Step 1: Capture clean source and live pre-state**

Run:

```bash
git -C /home/teladi/.local/share/wirtelprimpf-generator status --short
install -d -m0700 /home/teladi/.local/state/wirtelprimpf/deploy-backups
deploy_backup="$(mktemp -d /home/teladi/.local/state/wirtelprimpf/deploy-backups/20260801-admin-live.XXXXXX)"
chmod 0700 "$deploy_backup"
printf '%s\n' "$deploy_backup" > /home/teladi/.local/state/wirtelprimpf/deploy-backups/latest-admin-live-backup
chmod 0600 /home/teladi/.local/state/wirtelprimpf/deploy-backups/latest-admin-live-backup
timer_enabled_before="$(systemctl --user is-enabled wirtelprimpf.timer || true)"
timer_active_before="$(systemctl --user is-active wirtelprimpf.timer || true)"
printf '%s\n' "$timer_enabled_before" > "$deploy_backup/timer-enabled-before"
printf '%s\n' "$timer_active_before" > "$deploy_backup/timer-active-before"
chmod 0600 "$deploy_backup/timer-enabled-before" "$deploy_backup/timer-active-before"
printf 'timer enabled before: %s\ntimer active before: %s\n' "$timer_enabled_before" "$timer_active_before"
systemctl --user show wirtelprimpf.timer -p NextElapseUSecRealtime -p LastTriggerUSec -p RandomizedDelayUSec -p Persistent
systemctl --user show wirtelprimpf.service -p ActiveState -p Result -p ExecMainStatus
systemctl --user show wirtelprimpf-admin.service -p ActiveState -p SubState -p Result
if [[ "$timer_active_before" == active ]]; then systemctl --user stop wirtelprimpf.timer; fi
```

Expected: source checkout is clean; the private backup path and enabled/active values are durably recorded before any mutation; an active generator timer is stopped immediately after observation so it cannot fire during backup/install.

- [ ] **Step 2: Create a private, exact recovery point**

Run:

```bash
deploy_backup="$(< /home/teladi/.local/state/wirtelprimpf/deploy-backups/latest-admin-live-backup)"
[[ "$deploy_backup" == /home/teladi/.local/state/wirtelprimpf/deploy-backups/20260801-admin-live.* ]]
[[ -d "$deploy_backup" && ! -L "$deploy_backup" ]]
: > "$deploy_backup/backup-manifest.tsv"
chmod 0600 "$deploy_backup/backup-manifest.tsv"
for source_path in \
  /home/teladi/.config/wirtelprimpf/openai.env \
  /home/teladi/.config/cloudflare/api-token.env \
  /home/teladi/.config/systemd/user/wirtelprimpf.timer.d/override.conf \
  /home/teladi/.config/wirtelprimpf/settings-state.json \
  /home/teladi/.local/share/cinnamon/applets/wirtelprimfgenerator@H234598 \
  /home/teladi/.config/systemd/user/wirtelprimpf-admin.service; do
  if [[ -L "$source_path" ]]; then
    printf 'Unsafe symlink in backup scope: %s\n' "$source_path" >&2
    exit 1
  elif [[ -e "$source_path" ]]; then
    cp --archive -- "$source_path" "$deploy_backup/"
    printf 'present\t%s\n' "$source_path" >> "$deploy_backup/backup-manifest.tsv"
  else
    printf 'missing\t%s\n' "$source_path" >> "$deploy_backup/backup-manifest.tsv"
  fi
done
printf '%s\n' "$deploy_backup"
```

Expected: printed backup directory is private and contains only in-scope recovery material. Do not print any file contents.

- [ ] **Step 3: Install merged code while generation remains quiesced**

Load the private pre-state, assert an originally active timer is now inactive, then run:

```bash
deploy_backup="$(< /home/teladi/.local/state/wirtelprimpf/deploy-backups/latest-admin-live-backup)"
timer_active_before="$(< "$deploy_backup/timer-active-before")"
if [[ "$timer_active_before" == active ]]; then
  test "$(systemctl --user is-active wirtelprimpf.timer || true)" = inactive
fi
cd /home/teladi/.local/share/wirtelprimpf-generator
.venv/bin/python -m pip install --disable-pip-version-check --no-deps -e .
install -Dm0644 Sourcecode/systemd-user/wirtelprimpf-admin.service /home/teladi/.config/systemd/user/wirtelprimpf-admin.service
./scripts/install-local.sh
systemctl --user daemon-reload
systemctl --user restart wirtelprimpf-admin.service
```

Expected: every command exits 0; no generator run starts during the smoke window.

- [ ] **Step 4: Reload only the Wirtel applet and verify it is running**

Run:

```bash
gdbus call --session --dest org.Cinnamon --object-path /org/Cinnamon --method org.Cinnamon.ReloadXlet 'wirtelprimfgenerator@H234598' 'APPLET'
gdbus call --session --dest org.Cinnamon --object-path /org/Cinnamon --method org.Cinnamon.GetRunningXletUUIDs 'applet'
```

Expected: reload returns normally and the running UUID list contains `wirtelprimfgenerator@H234598`. Do not restart Cinnamon globally.

- [ ] **Step 5: Verify APIs, security headers, model choices, and local status**

Run:

```bash
smoke_dir="$(mktemp -d /home/teladi/.local/state/wirtelprimpf/admin-live-smoke.XXXXXX)"
chmod 0700 "$smoke_dir"
curl --fail --silent --show-error \
  --dump-header "$smoke_dir/settings.headers" \
  --output "$smoke_dir/settings.json" \
  http://127.0.0.1:8765/api/settings
curl --fail --silent --show-error \
  --output "$smoke_dir/status.json" \
  http://127.0.0.1:8765/api/status
rg -n -- 'Cache-Control: no-store|X-Frame-Options: DENY|X-Content-Type-Options: nosniff|Referrer-Policy: no-referrer' "$smoke_dir/settings.headers"
python - "$smoke_dir/settings.json" "$smoke_dir/status.json" <<'PY'
import json
import re
import sys
from pathlib import Path

settings = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
status = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
platform = json.loads(
    Path("/home/teladi/.local/state/wirtelprimpf/platform-state.json").read_text(encoding="utf-8")
)

image_models = ["gpt-image-2", "gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini"]
story_models = [
    "gpt-5.5", "gpt-5.5-pro", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.4-pro",
    "gpt-5.2", "gpt-5.2-pro", "gpt-5.1", "gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5-pro",
    "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o", "gpt-4o-mini",
]
assert settings["choices"]["image_model"] == image_models
assert settings["choices"]["story_model"] == story_models
assert re.fullmatch(r"[0-9a-f]{64}", settings["revision"])
assert not ({"openai_api_key", "cloudflare_api_token"} & settings["settings"].keys())
assert status["configuration"]["revision"] == settings["revision"]
assert status["timer"]["interval_minutes"] == settings["settings"]["generation_interval_minutes"]
assert status["timer"]["enabled"] == settings["settings"]["timer_enabled"]
assert status["timer"]["randomized_delay_seconds"] == settings["settings"]["timer_randomized_delay_seconds"]
assert status["timer"]["persistent"] == settings["settings"]["timer_persistent"]

current_volume = int(platform["current_volume"])
archive_index = int(platform["active_archive_index"])
assert status["story"]["current_volume"] == current_volume
assert status["story"]["book"] == ((current_volume - 1) // 10) + 1
assert status["story"]["story_in_book"] == ((current_volume - 1) % 10) + 1
assert status["archive"]["index"] == archive_index
assert status["archive"]["repository"] == f"Wirtelprimpf-{archive_index:04d}"
PY
printf 'Private smoke evidence: %s\n' "$smoke_dir"
```

Expected: both responses parse without printing contents; secrets are absent, choices are exact, effective timer fields agree with settings, and story/book/archive values agree with the live persisted platform state instead of a plan-time story number. The printed private directory is retained as rollout evidence.

- [ ] **Step 6: Perform a fully automated reversible HTTP/CLI live-sync and conflict smoke**

Run this against the installed webadmin and the exact CLI used by the applet. It changes only the non-secret `output_resolution`, proves both directions and a stale same-field conflict, and restores the captured original value in a guarded `finally` path:

```bash
/home/teladi/.local/share/wirtelprimpf-generator/.venv/bin/python - <<'PY'
import json
import re
import subprocess
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8765"
CLI = "/home/teladi/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-settings"
FIELD = "output_resolution"


def request(path, *, payload=None, csrf=None):
    body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers.update({
            "Content-Type": "application/json",
            "Origin": BASE,
            "X-Wirtelprimpf-CSRF": csrf,
        })
    operation = urllib.request.Request(BASE + path, data=body, headers=headers, method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(operation, timeout=10) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


with urllib.request.urlopen(BASE + "/", timeout=10) as response:
    page = response.read().decode("utf-8")
match = re.search(r'<meta name="csrf-token" content="([A-Za-z0-9_-]+)">', page)
assert match is not None
csrf = match.group(1)

status, initial = request("/api/settings")
assert status == 200
original = initial["settings"][FIELD]
variants = [value for value in ("source", "2k", "4k") if value != original]
assert len(variants) == 2
web_value, cli_value = variants
owned_values = {original, web_value, cli_value}


def envelope(snapshot, value):
    return {
        "base_revision": snapshot["revision"],
        "changes": {FIELD: value},
        "base_values": {FIELD: snapshot["settings"][FIELD]},
        "secret_actions": {},
    }


def cli(action, payload=None):
    result = subprocess.run(
        [CLI, action],
        input=None if payload is None else json.dumps(payload, separators=(",", ":")),
        text=True,
        capture_output=True,
        timeout=90 if action == "apply" else 10,
        check=False,
    )
    decoded = json.loads(result.stdout)
    return result.returncode, decoded


try:
    status, web_saved = request("/api/settings", payload=envelope(initial, web_value), csrf=csrf)
    assert status == 200 and web_saved["settings"][FIELD] == web_value

    cli_status, applet_view = cli("snapshot")
    assert cli_status == 0 and applet_view["settings"][FIELD] == web_value

    cli_status, cli_saved = cli("apply", envelope(applet_view, cli_value))
    assert cli_status == 0 and cli_saved["settings"][FIELD] == cli_value

    deadline = time.monotonic() + 4
    while True:
        status, web_view = request("/api/settings")
        assert status == 200
        if web_view["settings"][FIELD] == cli_value:
            break
        if time.monotonic() >= deadline:
            raise AssertionError("HTTP view did not observe the CLI change within four seconds")
        time.sleep(0.2)

    cli_status, stale_cli = cli("snapshot")
    assert cli_status == 0
    status, winner = request("/api/settings", payload=envelope(web_view, web_value), csrf=csrf)
    assert status == 200 and winner["settings"][FIELD] == web_value
    cli_status, conflict = cli("apply", envelope(stale_cli, original))
    assert cli_status == 3
    assert conflict["error"] == "conflict"
    assert conflict["conflicts"] == [FIELD]
    assert conflict["snapshot"]["settings"][FIELD] == web_value

    status, after_conflict = request("/api/settings")
    assert status == 200 and after_conflict["settings"][FIELD] == web_value
finally:
    status, current = request("/api/settings")
    assert status == 200
    if current["settings"][FIELD] != original:
        if current["settings"][FIELD] not in owned_values:
            raise RuntimeError("refusing to overwrite an unexpected external value during restoration")
        status, restored = request("/api/settings", payload=envelope(current, original), csrf=csrf)
        assert status == 200 and restored["settings"][FIELD] == original

cli_status, final_cli = cli("snapshot")
status, final_web = request("/api/settings")
assert cli_status == 0 and status == 200
assert final_cli["settings"][FIELD] == original
assert final_web["settings"][FIELD] == original
PY
```

Expected: exit 0 without printing settings or secrets. HTTP-to-CLI visibility, CLI-to-HTTP visibility, exit-code-3 same-field rejection, winner preservation, and exact original-value restoration all succeed. Task 8's browser epoch tests and Task 9's Gio/worker/dirty-state tests cover the two presentation adapters without requiring manual clicks. Keep the generator timer stopped until restoration is confirmed.

- [ ] **Step 7: Restore the recorded timer state and compare effective values**

Restore from the captured values rather than a plan-time assumption:

```bash
deploy_backup="$(< /home/teladi/.local/state/wirtelprimpf/deploy-backups/latest-admin-live-backup)"
timer_enabled_before="$(< "$deploy_backup/timer-enabled-before")"
timer_active_before="$(< "$deploy_backup/timer-active-before")"
case "$timer_enabled_before:$timer_active_before" in
  enabled:active) systemctl --user enable --now wirtelprimpf.timer ;;
  enabled:inactive) systemctl --user enable wirtelprimpf.timer; systemctl --user stop wirtelprimpf.timer ;;
  disabled:*) systemctl --user disable --now wirtelprimpf.timer ;;
  *) printf 'Unsupported recorded timer state: %s/%s\n' "$timer_enabled_before" "$timer_active_before" >&2; exit 1 ;;
esac
```

Then run:

```bash
systemctl --user show wirtelprimpf.timer -p ActiveState -p UnitFileState -p NextElapseUSecRealtime -p LastTriggerUSec -p RandomizedDelayUSec -p Persistent
systemctl --user show wirtelprimpf-admin.service -p ActiveState -p SubState -p Result
curl --fail --silent --show-error http://127.0.0.1:8765/api/status | python -m json.tool >/dev/null
```

Expected: enabled/active semantics and configured timer values match pre-state; admin is active/running; status is `ok` or only `degraded` for an explicitly unavailable persisted external observation.

- [ ] **Step 8: Prove installed applet and source are byte-identical**

Run:

```bash
diff --recursive --brief \
  --exclude='__pycache__' --exclude='*.pyc' \
  /home/teladi/.local/share/wirtelprimpf-generator/files/wirtelprimfgenerator@H234598 \
  /home/teladi/.local/share/cinnamon/applets/wirtelprimfgenerator@H234598
```

Expected: no difference.

### Task 5: Pin and deploy the current publication archive to the merged factory

**Files:**
- Modify: `/home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001/.github/workflows/pages.yml:19-23`

**Interfaces:**
- Consumes: exact merged generator SHA from Task 3.
- Produces: one archive commit that pins both reusable workflow and `factory_ref` to that identical SHA.
- Triggers: existing archive GitHub Pages workflow only; no DNS action.

- [ ] **Step 1: Verify the archive checkout and remote are clean/current**

Run:

```bash
git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 status --short
git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 fetch origin
git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 switch main
git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 pull --ff-only origin main
git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 switch -c chore/pin-transactional-site-factory
```

Expected: clean checkout; stop if unrelated user changes appear.

- [ ] **Step 2: Resolve and validate the immutable factory SHA**

Run:

```bash
generator_factory_sha="$(git -C /home/teladi/.local/share/wirtelprimpf-generator rev-parse HEAD)"
test "$generator_factory_sha" = "$(git -C /home/teladi/.local/share/wirtelprimpf-generator rev-parse origin/main)"
[[ "$generator_factory_sha" =~ ^[0-9a-f]{40}$ ]]
printf '%s\n' "$generator_factory_sha"
```

Expected: one valid SHA equal to merged generator main.

- [ ] **Step 3: Replace both old pins with the printed literal using `apply_patch`**

In `.github/workflows/pages.yml`, replace the SHA after `archive-pages.yml@` and the quoted `factory_ref` value with the exact same printed 40-character literal. Do not change triggers, permissions, archive index, custom domain, or any content file.

- [ ] **Step 4: Validate the two pins and exact diff**

Run:

```bash
generator_factory_sha="$(git -C /home/teladi/.local/share/wirtelprimpf-generator rev-parse HEAD)"
test "$(rg -o -- '[0-9a-f]{40}' /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001/.github/workflows/pages.yml | sort -u | wc -l)" -eq 1
rg -F -- "$generator_factory_sha" /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001/.github/workflows/pages.yml
git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 diff --check
git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 diff -- .github/workflows/pages.yml
```

Expected: exactly two occurrences of one SHA and a two-line value-only diff.

- [ ] **Step 5: Commit the isolated archive pin and open its pull request**

Run:

```bash
git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 add .github/workflows/pages.yml
git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 commit -m 'chore(pages): pin transactional site factory'
git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 push --set-upstream origin chore/pin-transactional-site-factory
archive_pr_url="$(gh pr create \
  --repo H234598/Wirtelprimpf-0001 \
  --base main \
  --head chore/pin-transactional-site-factory \
  --title 'Pin transactional Wirtelprimpf site factory' \
  --body 'Pins both reusable-workflow references to the reviewed immutable Wirtelprimpf-generator merge SHA. No story, media, DNS, or redirect content changes.')"
archive_pr_number="${archive_pr_url##*/}"
[[ "$archive_pr_number" =~ ^[0-9]+$ ]]
gh pr checks "$archive_pr_number" --repo H234598/Wirtelprimpf-0001 --watch --fail-fast
```

Expected: the branch contains only the two equal SHA-value changes and every configured pull-request check succeeds.

- [ ] **Step 6: Merge and watch the exact archive Pages run**

Run:

```bash
archive_pr_number="$(gh pr list \
  --repo H234598/Wirtelprimpf-0001 \
  --head chore/pin-transactional-site-factory \
  --state open \
  --limit 1 \
  --json number \
  --jq '.[0].number')"
[[ "$archive_pr_number" =~ ^[0-9]+$ ]]
gh pr merge "$archive_pr_number" --repo H234598/Wirtelprimpf-0001 --merge --delete-branch
git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 switch main
git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 pull --ff-only origin main
archive_sha="$(git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 rev-parse HEAD)"
archive_run_id=""
for attempt in $(seq 1 24); do
  archive_run_id="$(gh run list \
    --repo H234598/Wirtelprimpf-0001 \
    --workflow pages.yml \
    --branch main \
    --commit "$archive_sha" \
    --limit 1 \
    --json databaseId \
    --jq '.[0].databaseId')"
  if [[ -n "$archive_run_id" ]]; then break; fi
  sleep 5
done
test -n "$archive_run_id"
gh run watch "$archive_run_id" --repo H234598/Wirtelprimpf-0001 --exit-status
```

Expected: archive build, artifact validation, upload, and deploy complete successfully.

### Task 6: Hub Pages, public smoke, and additive plan closure

**Files:**
- Append: `/home/teladi/Dokumente/Obsidian_Vaults/Teladi_Programming/Projekte/Wirtelprimpf (Katzenbilder)/Baupläne!/Wirtelprimpf-Webseite-Implementierungsplan.md`
- Append: `/home/teladi/Dokumente/Obsidian_Vaults/Teladi_Programming/incomming/freeze-invasive-analyse-cinnamon-codex-watchdog-2026-07-31.md`

**Interfaces:**
- Consumes: merged generator, live local install, and successful archive workflow.
- Produces: successful exact-source hub deployment, public HTTPS evidence, and additive final plan record.

- [ ] **Step 1: Dispatch the hub with the exact active archive commit**

Run:

```bash
platform_state=/home/teladi/.local/state/wirtelprimpf/platform-state.json
current_volume="$(python -c 'import json,sys; print(int(json.load(open(sys.argv[1], encoding="utf-8"))["current_volume"]))' "$platform_state")"
active_archive_index="$(python -c 'import json,sys; print(int(json.load(open(sys.argv[1], encoding="utf-8"))["active_archive_index"]))' "$platform_state")"
active_repository="$(printf 'Wirtelprimpf-%04d' "$active_archive_index")"
test "$active_repository" = Wirtelprimpf-0001
active_archive_sha="$(git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 rev-parse HEAD)"
dispatch_started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
gh workflow run hub-pages.yml \
  --repo H234598/Wirtelprimpf-generator \
  --ref main \
  -f active_repository="$active_repository" \
  -f archive_ref="$active_archive_sha" \
  -f current_volume="$current_volume"
hub_run_id=""
for attempt in $(seq 1 24); do
  hub_run_id="$(gh run list \
    --repo H234598/Wirtelprimpf-generator \
    --workflow hub-pages.yml \
    --branch main \
    --event workflow_dispatch \
    --created ">=$dispatch_started_at" \
    --limit 1 \
    --json databaseId \
    --jq '.[0].databaseId')"
  if [[ -n "$hub_run_id" ]]; then break; fi
  sleep 5
done
test -n "$hub_run_id"
gh run watch "$hub_run_id" --repo H234598/Wirtelprimpf-generator --exit-status
```

Expected: the dispatch uses the live persisted current story and archive index, and source resolution, exact archive checkout, build, validation, upload, and deploy succeed. If the active archive is no longer `0001`, stop and revise Task 5 for that already-existing active repository; never create a repository here.

- [ ] **Step 2: Verify the public hub's six copy requirements and current-story order**

Fetch the following exact URLs with `curl --fail --location --silent --show-error`:

- `https://wirtelprimpf.telacore.org/`
- `https://wirtelprimpf.telacore.org/projekt/status/`
- one current media detail URL discovered from `/bilder/`.

Assert:

- hub HTML contains `Telacores:`;
- hub HTML omits both removed sentences;
- media HTML says `Im Release <tag> archiviert.` and omits `hashgebunden archiviert`;
- status HTML contains exactly `Dass er unbedeutend ist, und nichts weiß.`;
- the latest current-story part appears before the immediately preceding part.

- [ ] **Step 3: Verify archive deployment without changing the DNS/redirect workstream**

Use `gh api repos/H234598/Wirtelprimpf-0001/pages` and the successful workflow artifact/run metadata to confirm the archive was built from the merged factory SHA. Probe `https://wirtelprimpf-0001.telacore.org/` read-only.

If the hostname is unresolved or redirected by the separately managed Cloudflare layer, record that exact external gate and rely on the successful immutable workflow/artifact evidence. Do not create a DNS record or alter a redirect in this plan.

- [ ] **Step 4: Run final repository and live-state checks**

Run:

```bash
git -C /home/teladi/.local/share/wirtelprimpf-generator status --short
git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 status --short
systemctl --user is-active wirtelprimpf-admin.service
systemctl --user show wirtelprimpf.timer -p ActiveState -p UnitFileState -p NextElapseUSecRealtime
gdbus call --session --dest org.Cinnamon --object-path /org/Cinnamon --method org.Cinnamon.GetRunningXletUUIDs 'applet'
```

Expected: both repositories clean, admin active, timer state matches the recorded/restored policy, and the Wirtel applet is running.

- [ ] **Step 5: Append unabridged evidence to both Obsidian plans**

Append new numbered sections; never edit or remove older findings. Record:

- generator PR URL, merge commit, all task commits, and exact test counts;
- archive pin commit and Pages run;
- local backup path and source/install hashes;
- admin/status schemas and live-sync/conflict smoke result;
- timer pre/post state and next run;
- exact public hub checks;
- archive DNS/redirect observation without mutation;
- unchanged Cinnamon upstream, freeze/watchdog, and Cloudflare scopes.

- [ ] **Step 6: Declare completion only when every acceptance gate is evidenced**

Completion requires all of the following:

- shared model dropdowns in both interfaces;
- bidirectional live visibility and same-field conflict protection;
- effective timer equality and successful rollback tests;
- independent local `/api/status` with no secret/network leakage;
- six public copy requirements in built and live hub results;
- successful generator CI, hub Pages, and archive Pages runs;
- clean merged generator and archive repositories;
- exact local applet/source identity;
- no Cloudflare, upstream Cinnamon, or freeze/watchdog mutation.
