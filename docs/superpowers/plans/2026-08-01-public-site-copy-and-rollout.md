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

- [x] **Step 1: Write the failing copy-contract test**

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

- [x] **Step 2: Run the focused test and verify all six old contracts fail**

Run: `npm --prefix web test -- --test-name-pattern='approved public copy'`

If npm's script does not forward the filter on the installed Node version, run: `cd web && node --test --experimental-strip-types tests/copy-contract.test.ts`.

Expected: failures show the current old label, both old landing-page sentences, `hashgebunden`, and the old project-status sentence.

The failure set must also show the old Hero sentence with `Möhren`.

- [x] **Step 3: Apply the exact four source-file edits**

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

- [x] **Step 4: Run web unit and type checks**

Run:

```bash
npm --prefix web test
WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site" WIRTELPRIMPF_SITE_PROFILE=hub npm --prefix web run check
```

Expected: all Node tests pass and Astro reports zero errors.

- [x] **Step 5: Commit the independently reviewable copy change**

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

- [x] **Step 1: Build and validate the hub profile**

Run:

```bash
WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site" \
WIRTELPRIMPF_MEDIA_MANIFEST="$PWD/data/media-manifest.json" \
WIRTELPRIMPF_SITE_PROFILE=hub \
WIRTELPRIMPF_SITE_URL=https://wirtelprimpf.telacore.org \
npm --prefix web run build
python3 scripts/validate_pages_artifact.py web/dist --expected-domain wirtelprimpf.telacore.org
```

Expected: build and validator exit 0.

- [x] **Step 2: Assert the hub artifact's exact copy**

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

- [x] **Step 3: Build and validate the archive profile**

Run:

```bash
WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site" \
WIRTELPRIMPF_MEDIA_MANIFEST="$PWD/data/media-manifest.json" \
WIRTELPRIMPF_SITE_PROFILE=archive \
WIRTELPRIMPF_SITE_URL=https://wirtelprimpf-0001.telacore.org \
npm --prefix web run build
python3 scripts/validate_pages_artifact.py web/dist --expected-domain wirtelprimpf-0001.telacore.org
```

Expected: build and validator exit 0; generated canonical URLs use the archive hostname.

- [x] **Step 4: Assert archive-specific wording and retained contracts**

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

- [x] **Step 5: Verify generated files remain untracked**

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
generator_dirty="$(git status --porcelain)"
if [[ -n "$generator_dirty" ]]; then
  printf 'Generator checkout is not clean; aborting local matrix.\n' >&2
  printf '%s\n' "$generator_dirty" >&2
  exit 1
fi
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
generator_dirty="$(git status --porcelain)"
if [[ -n "$generator_dirty" ]]; then
  printf 'Generator checkout is not clean; aborting review.\n' >&2
  printf '%s\n' "$generator_dirty" >&2
  exit 1
fi
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
  if ! git merge --no-edit origin/main; then
    git merge --abort || true
    printf 'origin/main merge failed or conflicted; review required.\n' >&2
    exit 1
  fi
  test -z "$(git status --porcelain)"
  # An origin/main integration invalidates every earlier result. Repeat the
  # complete Step-1 matrix, including compileall, Astro check, and both full
  # profile builds plus artifact validators, before the push is permitted.
  python -m unittest discover -s tests/platform -p 'test_*.py' -v
  make check
  python -m compileall -q Sourcecode wirtelprimpf_platform scripts
  npm --prefix web test
  WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site" \
    WIRTELPRIMPF_SITE_PROFILE=hub npm --prefix web run check
  WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site" \
    WIRTELPRIMPF_MEDIA_MANIFEST="$PWD/data/media-manifest.json" \
    WIRTELPRIMPF_SITE_PROFILE=hub \
    WIRTELPRIMPF_SITE_URL=https://wirtelprimpf.telacore.org \
    npm --prefix web run build
  python3 scripts/validate_pages_artifact.py \
    web/dist --expected-domain wirtelprimpf.telacore.org
  WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site" \
    WIRTELPRIMPF_MEDIA_MANIFEST="$PWD/data/media-manifest.json" \
    WIRTELPRIMPF_SITE_PROFILE=archive \
    WIRTELPRIMPF_SITE_URL=https://wirtelprimpf-0001.telacore.org \
    npm --prefix web run build
  python3 scripts/validate_pages_artifact.py \
    web/dist --expected-domain wirtelprimpf-0001.telacore.org
  git diff --check
fi
git merge-base --is-ancestor origin/main HEAD
git push --set-upstream origin HEAD
```

Expected: already-published user commits are preserved in branch history, the post-merge matrix is green, and the branch push succeeds without force. Stop for review if the merge reports a conflict or introduces a scope-changing behavior; do not resolve a user conflict by discarding either side.

- [ ] **Step 4: Open the pull request and wait for all checks**

Run:

```bash
set -Eeuo pipefail
generator_head="$(git branch --show-current)"
generator_head_sha="$(git rev-parse HEAD)"
[[ -n "$generator_head" && "$generator_head_sha" =~ ^[0-9a-f]{40}$ ]]

# PR #4 is the known review surface.  Reuse it only after proving that its
# head/base pair is this exact branch; otherwise search the complete open set
# for the branch before a new PR is even permitted.
known_pr="$({ gh pr view 4 \
  --repo H234598/Wirtelprimpf-generator \
  --json number,url,state,headRefName,headRefOid,baseRefName,isDraft || true; } 2>/dev/null)"
if [[ -n "$known_pr" \
  && "$(jq -r '.state' <<<"$known_pr")" == OPEN \
  && "$(jq -r '.headRefName' <<<"$known_pr")" == "$generator_head" \
  && "$(jq -r '.baseRefName' <<<"$known_pr")" == main ]]; then
  generator_pr_number=4
  generator_pr_url="$(jq -r '.url' <<<"$known_pr")"
else
  matching_prs="$(gh pr list \
    --repo H234598/Wirtelprimpf-generator \
    --state open --base main --head "$generator_head" --limit 2 \
    --json number,url,headRefName,headRefOid,baseRefName,isDraft)"
  matching_count="$(jq 'length' <<<"$matching_prs")"
  case "$matching_count" in
    0)
      generator_pr_url="$(gh pr create \
        --repo H234598/Wirtelprimpf-generator \
        --base main \
        --head "$generator_head" \
        --title 'Transactional settings, live sync, status, and approved site copy' \
        --body 'Implements the approved 2026-08-01 design: one transactional configuration core, conflict-safe live web/applet synchronization, real local /api/status, shared model dropdowns, effective systemd timer application, and the six approved public copy changes. Cloudflare and Cinnamon upstream work remain out of scope.')"
      generator_pr_number="${generator_pr_url##*/}"
      ;;
    1)
      generator_pr_number="$(jq -r '.[0].number' <<<"$matching_prs")"
      generator_pr_url="$(jq -r '.[0].url' <<<"$matching_prs")"
      ;;
    *)
      printf 'Multiple open PRs use generator head %s; refusing ambiguity.\n' "$generator_head" >&2
      exit 1
      ;;
  esac
fi

[[ "$generator_pr_number" =~ ^[0-9]+$ ]]
verified_pr="$(gh pr view "$generator_pr_number" \
  --repo H234598/Wirtelprimpf-generator \
  --json state,headRefName,headRefOid,baseRefName,isDraft,url)"
test "$(jq -r '.state' <<<"$verified_pr")" = OPEN
test "$(jq -r '.headRefName' <<<"$verified_pr")" = "$generator_head"
test "$(jq -r '.headRefOid' <<<"$verified_pr")" = "$generator_head_sha"
test "$(jq -r '.baseRefName' <<<"$verified_pr")" = main
test "$(jq -r '.isDraft' <<<"$verified_pr")" = false
test "$(jq -r '.url' <<<"$verified_pr")" = "$generator_pr_url"
gh pr checks "$generator_pr_number" --repo H234598/Wirtelprimpf-generator --watch --fail-fast
```

Expected: applet, platform, web, Pages-related checks, and configured review gates are successful. Address actual review findings with new focused test-first commits and rerun the full affected matrix; do not dismiss findings without evidence.

- [ ] **Step 5: Merge through GitHub and record the immutable generator SHA**

Run:

```bash
set -Eeuo pipefail
generator_pr_number="$(gh pr view --repo H234598/Wirtelprimpf-generator --json number --jq .number)"
[[ "$generator_pr_number" =~ ^[0-9]+$ ]]
gh pr merge "$generator_pr_number" --repo H234598/Wirtelprimpf-generator --merge --delete-branch
generator_merge_sha="$(gh pr view "$generator_pr_number" \
  --repo H234598/Wirtelprimpf-generator --json mergeCommit --jq '.mergeCommit.oid')"
remote_main_sha="$(git ls-remote origin refs/heads/main | cut -f1)"
[[ "$generator_merge_sha" =~ ^[0-9a-f]{40}$ ]]
test "$remote_main_sha" = "$generator_merge_sha"
printf 'Merged generator SHA for Task 4/5: %s\n' "$generator_merge_sha"
```

Expected: GitHub main contains the merge commit and the printed 40-character SHA is recorded as the only factory reference permitted in Tasks 4–5. The runtime checkout is deliberately still untouched; its previous SHA is captured and its update begins only inside Task 4 after quiescence, backup, and rollback trapping.

#### Verbindliches Execution-Context-Erratum für Task 3 Step 5 und Task 4

Die Tool-Shell dieser Ausführung läuft als UID 0. Der Runtime-Checkout darf
deshalb in Task 3 Step 5 **nicht** mit einem unqualifizierten Root-`git`
aktualisiert werden. `fetch`, `switch`, `pull`, `rev-parse`, Status- und
Eigentümerprüfungen für
`/home/teladi/.local/share/wirtelprimpf-generator` laufen ausschließlich als
UID/GID `teladi`.

Ebenso laufen ausnahmslos **alle** Task-4-Operationen, insbesondere Befehle mit
`$HOME`, venv/Pip, Backup und Wiederherstellung, `install-local.sh`,
`systemctl --user`, der Curl-Livesmoke und `gdbus`, als UID/GID `teladi` mit
diesem expliziten Kontext:

```bash
runuser -u teladi -- env \
  HOME=/home/teladi \
  USER=teladi \
  LOGNAME=teladi \
  XDG_RUNTIME_DIR=/run/user/1000 \
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
  <Befehl>
```

Mehrzeilige Shellblöcke werden mit genau dieser Umgebung an eine Shell unter
`runuser -u teladi` übergeben; sie dürfen nicht teilweise vorab von der
Root-Shell expandiert werden. Bei einer Authentifizierungs-, Eigentümer- oder
`safe.directory`-Hürde wird pausiert und berichtet; sie darf nicht durch eine
Root-Ausführung oder eine globale Vertrauensausnahme umgangen werden. Nach dem
Task-3-Update sind Eigentümer, sauberer Status sowie Gleichheit von `HEAD` und
`origin/main` explizit zu prüfen.

Die zuvor aus der Root-Session beobachteten Ausgaben `LoadState=not-found` und
DBus `ServiceUnknown` betrafen die falsche Benutzerinstanz und sind als
Laufzeitbefund ungültig. Eine read-only Prüfung im korrekten `teladi`-Kontext
bestätigte stattdessen: Timer geladen/aktiv/enabled, Generator
inactive/success, Admin active/running und das Wirtel-Applet laufend. Dieses
Erratum autorisiert in Task 3 keinen Task-4-Schritt; Installation, Backup,
Service-/Timeränderung, Livesmoke und Applet-Reload bleiben bis Task 4
ausgesetzt.

#### Verbindliches Ownership-Gate vor jedem Runtime-Gitlauf

Der bereits read-only bestätigte Fremdbesitz umfasst exakt 450 Einträge im
Runtime-Checkout. Vor dem ersten und damit vor jedem folgenden Gitlauf als
`teladi` repariert Root ausschließlich diese aufgelöste, nicht verlinkte
Checkout-Wurzel; jede abweichende Anzahl bricht vor `chown` ab. Es gibt keine
`safe.directory`-Ausnahme:

```bash
test "$(id -u)" = 0
runtime=/home/teladi/.local/share/wirtelprimpf-generator
test -d "$runtime" && test ! -L "$runtime"
test "$(realpath -e -- "$runtime")" = "$runtime"
declare -a foreign_runtime_entries=()
while IFS= read -r -d '' entry; do
  foreign_runtime_entries+=("$entry")
done < <(find "$runtime" -xdev \( ! -user teladi -o ! -group teladi \) -print0)
test "${#foreign_runtime_entries[@]}" = 450
chown -h teladi:teladi -- "${foreign_runtime_entries[@]}"
test "$(find "$runtime" -xdev \( ! -user teladi -o ! -group teladi \) -print -quit | wc -l)" = 0
```

Danach kapselt Step 9 jeden einzelnen `git -C "$runtime" ...`-Aufruf in
`git_runtime`; der Wrapper beweist unmittelbar davor erneut null fremde
Einträge. Er darf keine Besitzreparatur vornehmen, sondern schlägt bei Drift
geschlossen fehl.

### Task 4: Private backup, merged local install, targeted reload, and live synchronization smoke

**Files:**
- Back up: Wirtel environment, separate Cloudflare token file, timer drop-in, revision signal, installed applet, and installed user units.
- Install from: `/home/teladi/.local/share/wirtelprimpf-generator` merged main.

**Interfaces:**
- Consumes: merged generator SHA from Task 3.
- Produces: local package/admin/applet/user-unit installation exactly matching merged main.
- Preserves: token values, timer enabled/active state, and all unrelated Cinnamon applets/services.

> **Verbindliche Ablaufkorrektur:** Die einzeln gedruckten Steps 1–8 bleiben als
> Audit- und Smoke-Details erhalten, dürfen aber nicht mehr als voneinander
> getrennte Shells ausgeführt werden. Maßgeblich ist der transaktionale Rahmen
> in Step 9: Er erfasst zuerst den alten Runtime-SHA und ausschließlich
> rekonstruierbare Timer-/Adminzustände, installiert einen Restore-Trap vor dem
> ersten operativen Write, stoppt den Timer, beweist den Generator als
> `inactive`, erstellt dann alle Backups und aktualisiert erst danach den
> Runtime-Checkout. Die korrigierten Smoke-Bodies aus Steps 5–6 laufen innerhalb
> derselben Trap-Lebensdauer.

- [ ] **Step 1: Capture clean source and live pre-state**

Run:

```bash
generator_runtime=/home/teladi/.local/share/wirtelprimpf-generator
generator_dirty="$(git -C "$generator_runtime" status --porcelain)"
if [[ -n "$generator_dirty" ]]; then
  printf 'Generator runtime checkout is not clean; refusing installation.\n' >&2
  printf '%s\n' "$generator_dirty" >&2
  exit 1
fi
install -d -m0700 /home/teladi/.local/state/wirtelprimpf/deploy-backups
deploy_backup="$(mktemp -d /home/teladi/.local/state/wirtelprimpf/deploy-backups/20260801-admin-live.XXXXXX)"
chmod 0700 "$deploy_backup"
printf '%s\n' "$deploy_backup" > /home/teladi/.local/state/wirtelprimpf/deploy-backups/latest-admin-live-backup
chmod 0600 /home/teladi/.local/state/wirtelprimpf/deploy-backups/latest-admin-live-backup
timer_enabled_before="$(systemctl --user is-enabled wirtelprimpf.timer || true)"
timer_active_before="$(systemctl --user is-active wirtelprimpf.timer || true)"
case "$timer_enabled_before" in
  enabled|enabled-runtime|disabled|static|indirect|linked|linked-runtime|alias|masked|masked-runtime|not-found) ;;
  *) printf 'Unsupported timer UnitFileState before mutation: %s\n' "$timer_enabled_before" >&2; exit 1 ;;
esac
case "$timer_active_before" in
  active|inactive|failed) ;;
  *) printf 'Unsupported timer ActiveState before mutation: %s\n' "$timer_active_before" >&2; exit 1 ;;
esac
case "$timer_enabled_before:$timer_active_before" in
  masked:active|masked-runtime:active|not-found:active)
    printf 'Inconsistent timer state cannot be restored safely: %s/%s\n' \
      "$timer_enabled_before" "$timer_active_before" >&2
    exit 1
    ;;
esac
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
  /home/teladi/.config/systemd/user/wirtelprimpf.service \
  /home/teladi/.config/systemd/user/wirtelprimpf.timer \
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
install -Dm0644 Sourcecode/systemd-user/wirtelprimpf.service /home/teladi/.config/systemd/user/wirtelprimpf.service
install -Dm0644 Sourcecode/systemd-user/wirtelprimpf-admin.service /home/teladi/.config/systemd/user/wirtelprimpf-admin.service
./scripts/install-local.sh
systemctl --user daemon-reload
cmp --silent Sourcecode/systemd-user/wirtelprimpf.service /home/teladi/.config/systemd/user/wirtelprimpf.service
cmp --silent Sourcecode/systemd-user/wirtelprimpf.timer /home/teladi/.config/systemd/user/wirtelprimpf.timer
cmp --silent Sourcecode/systemd-user/wirtelprimpf-admin.service /home/teladi/.config/systemd/user/wirtelprimpf-admin.service
systemctl --user restart wirtelprimpf-admin.service
```

Expected: every command exits 0; no generator run starts during the smoke window.

Additional expected recovery/unit invariant: the changed merged generator and
admin units are installed with mode `0644`; the unchanged timer unit was
preserved by the backup and all three installed unit sources compare
byte-identical with merged main before the admin restart.

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
  --dump-header "$smoke_dir/status.headers" \
  --output "$smoke_dir/status.json" \
  http://127.0.0.1:8765/api/status
for headers in "$smoke_dir/settings.headers" "$smoke_dir/status.headers"; do
  rg -F -- 'Cache-Control: no-store' "$headers"
  rg -F -- 'X-Frame-Options: DENY' "$headers"
  rg -F -- 'X-Content-Type-Options: nosniff' "$headers"
  rg -F -- 'Referrer-Policy: no-referrer' "$headers"
done
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

forbidden_keys = {"openai_api_key", "cloudflare_api_token"}


def reject_secret_keys(value):
    if isinstance(value, dict):
        assert not (forbidden_keys & value.keys())
        for child in value.values():
            reject_secret_keys(child)
    elif isinstance(value, list):
        for child in value:
            reject_secret_keys(child)


reject_secret_keys(settings)
reject_secret_keys(status)
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
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

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
        # Reads fail quickly; writes have a finite client socket timeout so a
        # wedged connection cannot hang the rollout forever. Disconnecting the
        # client does not cancel the server-owned settings transaction, so an
        # ambiguous write is reconciled by revision below instead of retried.
        opened = urllib.request.urlopen(operation, timeout=10 if body is None else 180)
        with opened as response:
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
last_owned_snapshot = initial


def envelope(snapshot, value):
    return {
        "base_revision": snapshot["revision"],
        "changes": {FIELD: value},
        "base_values": {FIELD: snapshot["settings"][FIELD]},
        "secret_actions": {},
    }


def reconcile_unknown(base_snapshot):
    deadline = time.monotonic() + 180
    while True:
        try:
            status, current = request("/api/settings")
        except (OSError, TimeoutError, ValueError, urllib.error.URLError):
            status, current = 0, None
        if status == 200:
            disposition = (
                "base-still-current"
                if current["revision"] == base_snapshot["revision"]
                else "revision-advanced-without-owned-response"
            )
            return disposition, current
        if time.monotonic() >= deadline:
            raise RuntimeError("unable to reconcile an unknown write outcome by revision")
        time.sleep(0.2)


def http_apply(base_snapshot, value):
    try:
        return request(
            "/api/settings",
            payload=envelope(base_snapshot, value),
            csrf=csrf,
        )
    except (OSError, TimeoutError, ValueError, urllib.error.URLError) as error:
        disposition, _current = reconcile_unknown(base_snapshot)
        raise RuntimeError(
            f"HTTP write outcome reconciled as {disposition}; refusing ownership"
        ) from error


def cli(action, payload=None):
    options = {
        "input": None if payload is None else json.dumps(payload, separators=(",", ":")),
        "text": True,
        "capture_output": True,
        "check": False,
    }
    if action == "snapshot":
        options["timeout"] = 10
    # Apply has no client kill deadline; the CLI transaction owns rollback.
    result = subprocess.run([CLI, action], **options)
    decoded = json.loads(result.stdout)
    return result.returncode, decoded


def cli_apply(base_snapshot, value):
    try:
        return cli("apply", envelope(base_snapshot, value))
    except (OSError, TimeoutError, ValueError, subprocess.SubprocessError) as error:
        disposition, _current = reconcile_unknown(base_snapshot)
        raise RuntimeError(
            f"CLI write outcome reconciled as {disposition}; refusing ownership"
        ) from error


try:
    status, web_saved = http_apply(initial, web_value)
    assert status == 200 and web_saved["settings"][FIELD] == web_value
    last_owned_snapshot = web_saved

    cli_status, applet_view = cli("snapshot")
    assert cli_status == 0 and applet_view["settings"][FIELD] == web_value

    cli_status, cli_saved = cli_apply(applet_view, cli_value)
    assert cli_status == 0 and cli_saved["settings"][FIELD] == cli_value
    last_owned_snapshot = cli_saved

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
    status, winner = http_apply(web_view, web_value)
    assert status == 200 and winner["settings"][FIELD] == web_value
    last_owned_snapshot = winner
    cli_status, conflict = cli_apply(stale_cli, original)
    assert cli_status == 3
    assert conflict["error"] == "conflict"
    assert conflict["conflicts"] == [FIELD]
    assert conflict["snapshot"]["settings"][FIELD] == web_value

    status, after_conflict = request("/api/settings")
    assert status == 200 and after_conflict["settings"][FIELD] == web_value

    # Prove restoration itself is conflict-safe: a competing commit after the
    # captured restore basis must yield 409 and preserve the competitor.
    restore_basis = winner
    status, competitor = http_apply(winner, cli_value)
    assert status == 200 and competitor["settings"][FIELD] == cli_value
    status, restore_conflict = http_apply(restore_basis, original)
    assert status == 409
    assert restore_conflict["conflicts"] == [FIELD]
    assert restore_conflict["snapshot"]["settings"][FIELD] == cli_value
    last_owned_snapshot = competitor
finally:
    status, current = request("/api/settings")
    assert status == 200
    if current["settings"][FIELD] != original:
        # Never adopt a fresh GET as write ownership.  Restore only from the
        # last revision returned by one of this smoke's successful writes.
        status, restored = http_apply(last_owned_snapshot, original)
        if status == 409:
            assert restored["snapshot"]["revision"] == current["revision"]
            raise RuntimeError("restoration conflict preserved a competing write")
        assert status == 200 and restored["settings"][FIELD] == original
        last_owned_snapshot = restored

cli_status, final_cli = cli("snapshot")
status, final_web = request("/api/settings")
assert cli_status == 0 and status == 200
assert final_cli["settings"][FIELD] == original
assert final_web["settings"][FIELD] == original
ownership_marker = os.environ.get("WIRTELPRIMPF_SMOKE_OWNERSHIP_MARKER")
if ownership_marker:
    marker_path = Path(ownership_marker)
    marker_path.write_text(
        json.dumps({"revision": final_web["revision"]}, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.chmod(marker_path, 0o600)
PY
```

Expected: exit 0 without printing settings or secrets. HTTP-to-CLI visibility, CLI-to-HTTP visibility, exit-code-3 same-field rejection, winner preservation, and exact original-value restoration all succeed. Task 8's browser epoch tests and Task 9's Gio/worker/dirty-state tests cover the two presentation adapters without requiring manual clicks. Keep the generator timer stopped until restoration is confirmed.

- [ ] **Step 7: Restore the recorded timer state and compare effective values**

Restore from the captured values rather than a plan-time assumption:

```bash
deploy_backup="$(< /home/teladi/.local/state/wirtelprimpf/deploy-backups/latest-admin-live-backup)"
timer_enabled_before="$(< "$deploy_backup/timer-enabled-before")"
timer_active_before="$(< "$deploy_backup/timer-active-before")"
timer_enabled_now="$(systemctl --user is-enabled wirtelprimpf.timer || true)"
if [[ "$timer_enabled_now" != "$timer_enabled_before" ]]; then
  case "$timer_enabled_before" in
    enabled) systemctl --user enable wirtelprimpf.timer ;;
    enabled-runtime) systemctl --user enable --runtime wirtelprimpf.timer ;;
    disabled) systemctl --user disable wirtelprimpf.timer ;;
    masked) systemctl --user mask wirtelprimpf.timer ;;
    masked-runtime) systemctl --user mask --runtime wirtelprimpf.timer ;;
    static|indirect|linked|linked-runtime|alias|not-found)
      printf 'Recorded timer UnitFileState drift cannot be reconstructed safely: %s -> %s\n' \
        "$timer_enabled_before" "$timer_enabled_now" >&2
      exit 1
      ;;
    *) printf 'Unsupported recorded timer UnitFileState: %s\n' "$timer_enabled_before" >&2; exit 1 ;;
  esac
fi
case "$timer_active_before" in
  active) systemctl --user start wirtelprimpf.timer ;;
  inactive) systemctl --user stop wirtelprimpf.timer ;;
  failed)
    test "$(systemctl --user is-active wirtelprimpf.timer || true)" = failed || {
      printf 'Recorded failed timer state drifted and cannot be recreated safely.\n' >&2
      exit 1
    }
    ;;
  *) printf 'Unsupported recorded timer ActiveState: %s\n' "$timer_active_before" >&2; exit 1 ;;
esac
test "$(systemctl --user is-enabled wirtelprimpf.timer || true)" = "$timer_enabled_before"
test "$(systemctl --user is-active wirtelprimpf.timer || true)" = "$timer_active_before"
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

- [ ] **Step 9: Execute Steps 1–8 through one guarded deployment transaction**

Materialize one private deployment script as UID `teladi`, insert the exact
read-only/API smoke from Step 5 and the corrected finite-HTTP-socket-timeout,
unbounded-CLI-apply conflict smoke from Step 6 at the marked location, run
`bash -n` over the resulting script, and execute it exactly once. The following
frame is normative; no standalone command from Steps 1–8 may run outside it:

```bash
set -Eeuo pipefail

target_sha="${GENERATOR_MERGE_SHA:?recorded Task-3 merge SHA required}"
runtime=/home/teladi/.local/share/wirtelprimpf-generator
backup_root=/home/teladi/.local/state/wirtelprimpf/deploy-backups
[[ "$target_sha" =~ ^[0-9a-f]{40}$ ]]

assert_runtime_owned() {
  test -d "$runtime" && test ! -L "$runtime"
  test "$(realpath -e -- "$runtime")" = "$runtime"
  test -z "$(find "$runtime" -xdev \( ! -user teladi -o ! -group teladi \) -print -quit)"
}
git_runtime() {
  assert_runtime_owned
  git -C "$runtime" "$@"
}

test -z "$(git_runtime status --porcelain)"
runtime_branch_before="$(git_runtime branch --show-current)"
runtime_sha_before="$(git_runtime rev-parse HEAD)"
test "$runtime_branch_before" = main
[[ "$runtime_sha_before" =~ ^[0-9a-f]{40}$ ]]
test "$runtime_sha_before" != "$target_sha"

timer_enabled_before="$(systemctl --user is-enabled wirtelprimpf.timer || true)"
timer_active_before="$(systemctl --user is-active wirtelprimpf.timer || true)"
admin_active_before="$(systemctl --user is-active wirtelprimpf-admin.service || true)"
case "$timer_enabled_before" in enabled|enabled-runtime|disabled) ;; *) exit 1 ;; esac
case "$timer_active_before" in active|inactive) ;; *) exit 1 ;; esac
case "$admin_active_before" in active|inactive) ;; *) exit 1 ;; esac
running_xlets="$(gdbus call --session --dest org.Cinnamon \
  --object-path /org/Cinnamon --method org.Cinnamon.GetRunningXletUUIDs applet)"
if [[ "$running_xlets" == *wirtelprimfgenerator@H234598* ]]; then
  applet_running_before=1
else
  applet_running_before=0
fi

install -d -m0700 "$backup_root"
deploy_backup="$(mktemp -d "$backup_root/20260801-admin-live.XXXXXX")"
chmod 0700 "$deploy_backup"
printf '%s\n' "$runtime_sha_before" >"$deploy_backup/runtime-sha-before"
printf '%s\n' "$runtime_branch_before" >"$deploy_backup/runtime-branch-before"
printf '%s\n' "$target_sha" >"$deploy_backup/target-sha"
printf '%s\n' "$timer_enabled_before" >"$deploy_backup/timer-enabled-before"
printf '%s\n' "$timer_active_before" >"$deploy_backup/timer-active-before"
printf '%s\n' "$admin_active_before" >"$deploy_backup/admin-active-before"
chmod 0600 "$deploy_backup"/*-before "$deploy_backup/target-sha"

backup_complete=0
software_commit_complete=0
deployment_complete=0

target_is_scoped() {
  case "$1" in
    /home/teladi/.config/wirtelprimpf/openai.env|\
    /home/teladi/.config/cloudflare/api-token.env|\
    /home/teladi/.config/systemd/user/wirtelprimpf.timer.d/override.conf|\
    /home/teladi/.config/wirtelprimpf/settings-state.json|\
    /home/teladi/.local/share/cinnamon/applets/wirtelprimfgenerator@H234598|\
    /home/teladi/.local/share/cinnamon/applets/wirtelprimfgenerator@local|\
    /home/teladi/.local/bin/wirtelprimpf-story-directives|\
    /home/teladi/.config/systemd/user/wirtelprimpf.service|\
    /home/teladi/.config/systemd/user/wirtelprimpf.timer|\
    /home/teladi/.config/systemd/user/wirtelprimpf-admin.service) return 0 ;;
    *) return 1 ;;
  esac
}

restore_targets() {
  local manifest="$1" state target payload
  while IFS=$'\t' read -r state target payload; do
    target_is_scoped "$target" || return 1
    rm -rf -- "$target"
    if [[ "$state" == present ]]; then
      test -e "$payload" && test ! -L "$payload"
      mkdir -p -- "$(dirname -- "$target")"
      cp -a -- "$payload" "$target"
    else
      test "$state" = missing
    fi
  done <"$manifest"
}

directory_is_mode_scoped() {
  case "$1" in
    /home/teladi/.config/wirtelprimpf|\
    /home/teladi/.config/cloudflare|\
    /home/teladi/.config/systemd/user/wirtelprimpf.timer.d) return 0 ;;
    *) return 1 ;;
  esac
}

restore_directory_modes() {
  local mode target
  while IFS=$'\t' read -r mode target; do
    [[ "$mode" =~ ^[0-7]{3,4}$ ]] || return 1
    directory_is_mode_scoped "$target" || return 1
    test -d "$target" && test ! -L "$target"
    chmod "$mode" -- "$target"
    test "$(stat -Lc '%a' -- "$target")" = "${mode#0}"
  done <"$deploy_backup/directory-modes-before.tsv"
}

settings_lock_held=0
acquire_settings_lock() {
  local lock_path=/home/teladi/.config/wirtelprimpf/settings.lock
  [[ "$settings_lock_held" == 0 ]] || return 0
  test ! -L "$lock_path"
  exec {settings_lock_fd}<>"$lock_path"
  chmod 0600 "$lock_path"
  if ! flock -n "$settings_lock_fd"; then
    exec {settings_lock_fd}>&-
    return 1
  fi
  settings_lock_held=1
}

acquire_settings_lock_bounded() {
  local lock_path=/home/teladi/.config/wirtelprimpf/settings.lock
  [[ "$settings_lock_held" == 0 ]] || return 0
  test ! -L "$lock_path"
  exec {settings_lock_fd}<>"$lock_path"
  chmod 0600 "$lock_path"
  if ! flock -w 180 "$settings_lock_fd"; then
    exec {settings_lock_fd}>&-
    return 1
  fi
  settings_lock_held=1
}

release_settings_lock() {
  [[ "$settings_lock_held" == 1 ]] || return 0
  flock -u "$settings_lock_fd"
  exec {settings_lock_fd}>&-
  settings_lock_held=0
}

capture_config_fingerprints() {
  local state target payload
  while IFS=$'\t' read -r state target payload; do
    target_is_scoped "$target" || return 1
    test ! -L "$target"
    if [[ -e "$target" ]]; then
      printf '%s\tpresent\t%s\t%s\n' \
        "$target" "$(stat -Lc '%d:%i:%s:%Y' -- "$target")" \
        "$(sha256sum -- "$target" | cut -d' ' -f1)"
    else
      printf '%s\tmissing\t-\t-\n' "$target"
    fi
  done <"$deploy_backup/config-manifest.tsv"
}

config_matches_backup() {
  local state target payload
  while IFS=$'\t' read -r state target payload; do
    if [[ "$state" == present ]]; then
      [[ -f "$target" && ! -L "$target" ]] || return 1
      cmp --silent -- "$payload" "$target" || return 1
    else
      [[ "$state" == missing && ! -e "$target" && ! -L "$target" ]] || return 1
    fi
  done <"$deploy_backup/config-manifest.tsv"
}

verify_config_preserved() {
  local current_fingerprints owned_revision current_revision
  config_matches_backup && return 0
  test -s "$deploy_backup/owned-config-fingerprints.tsv" || return 2
  current_fingerprints="$(mktemp "$deploy_backup/current-config.XXXXXX")"
  chmod 0600 "$current_fingerprints"
  capture_config_fingerprints >"$current_fingerprints" || return 1
  if ! cmp --silent -- "$deploy_backup/owned-config-fingerprints.tsv" "$current_fingerprints"; then
    rm -f -- "$current_fingerprints"
    return 2
  fi
  rm -f -- "$current_fingerprints"
  if ! owned_revision="$(jq -er '.revision' "$deploy_backup/smoke-owned-revision.json")"; then
    return 1
  fi
  if ! current_revision="$(jq -er '.revision' \
    /home/teladi/.config/wirtelprimpf/settings-state.json)"; then
    return 2
  fi
  test "$current_revision" = "$owned_revision" || return 2
  # A successful smoke restores values semantically and intentionally writes a
  # new valid revision signal. Preserve that owned state; never copy old
  # env/state bytes or their obsolete inode/mtime-bound revision back.
  return 0
}

quiesce_generator() {
  local deadline
  systemctl --user stop wirtelprimpf.timer || return 1
  deadline=$((SECONDS + 300))
  while [[ "$(systemctl --user show wirtelprimpf.service \
    -p ActiveState --value)" != inactive ]]; do
    (( SECONDS < deadline )) || return 1
    sleep 1
  done
  test "$(systemctl --user show wirtelprimpf.service \
    -p ActiveState --value)" = inactive
}

restore_timer_enablement_stopped() {
  local current
  systemctl --user stop wirtelprimpf.timer || return 1
  current="$(systemctl --user is-enabled wirtelprimpf.timer || true)"
  if [[ "$current" != "$timer_enabled_before" ]]; then
    systemctl --user disable wirtelprimpf.timer
    systemctl --user disable --runtime wirtelprimpf.timer
    case "$timer_enabled_before" in
      enabled) systemctl --user enable wirtelprimpf.timer ;;
      enabled-runtime) systemctl --user enable --runtime wirtelprimpf.timer ;;
      disabled) ;;
    esac
  fi
  systemctl --user stop wirtelprimpf.timer || return 1
  test "$(systemctl --user is-enabled wirtelprimpf.timer || true)" = "$timer_enabled_before"
  test "$(systemctl --user is-active wirtelprimpf.timer || true)" = inactive
}

restore_timer_activity() {
  case "$timer_active_before" in
    active) systemctl --user start wirtelprimpf.timer ;;
    inactive) systemctl --user stop wirtelprimpf.timer ;;
  esac
  test "$(systemctl --user is-enabled wirtelprimpf.timer || true)" = "$timer_enabled_before"
  test "$(systemctl --user is-active wirtelprimpf.timer || true)" = "$timer_active_before"
}

rollback_deployment() {
  local original_status="$1" rollback_failed=0 config_attention=0
  local config_status=0 generator_quiesced=0 critical_recovery_ok=0 final_status
  local main_ref_now="" main_ref_state=unknown
  trap - EXIT INT TERM
  [[ "$deployment_complete" == 1 ]] && return "$original_status"
  set +e
  # This is deliberately the first recovery mutation. Never replace installed
  # code, the checkout, or the venv while a generated story process may still
  # be executing those files.
  if quiesce_generator; then
    generator_quiesced=1
  else
    rollback_failed=1
  fi
  # A successful main fast-forward is the irreversible software commit point.
  # Detect it both from the shell flag and the ref itself, closing the INT/TERM
  # window between merge success and flag assignment. An unreadable ref is also
  # fail-closed: no install/config/worktree recovery may proceed on ambiguity.
  if [[ "$software_commit_complete" == 1 ]]; then
    main_ref_state=postcommit
  elif [[ "$target_sha" =~ ^[0-9a-f]{40}$ ]]; then
    if main_ref_now="$(git_runtime rev-parse refs/heads/main 2>/dev/null)"; then
      case "$main_ref_now" in
        "$runtime_sha_before") main_ref_state=precommit ;;
        "$target_sha") main_ref_state=postcommit ;;
        *) main_ref_state=unknown ;;
      esac
    fi
  fi
  if [[ "$main_ref_state" != precommit ]]; then
    printf 'MAIN REF %s; software preserved, timer stopped, deployment incomplete: %s\n' \
      "$main_ref_state" "$deploy_backup" >&2
    final_status="$original_status"
    [[ "$final_status" != 0 ]] || final_status=1
    exit "$final_status"
  fi
  systemctl --user stop wirtelprimpf-admin.service || rollback_failed=1
  # Wait boundedly for any in-flight applet/CLI settings transaction. All file,
  # checkout, venv, and unit recovery remains behind this same exclusive lock.
  if [[ "$generator_quiesced" == 1 ]] && acquire_settings_lock_bounded; then
    critical_recovery_ok=1
    if [[ "$backup_complete" == 1 ]]; then
      restore_targets "$deploy_backup/install-manifest.tsv" || {
        rollback_failed=1
        critical_recovery_ok=0
      }
      restore_directory_modes || {
        rollback_failed=1
        critical_recovery_ok=0
      }
      verify_config_preserved
      config_status=$?
      case "$config_status" in
        0) ;;
        2) config_attention=1 ;;
        *) rollback_failed=1; critical_recovery_ok=0 ;;
      esac
    fi
    git_runtime switch "$runtime_branch_before" || {
      rollback_failed=1
      critical_recovery_ok=0
    }
    test "$(git_runtime rev-parse HEAD)" = "$runtime_sha_before" || {
      rollback_failed=1
      critical_recovery_ok=0
    }
    "$runtime/.venv/bin/python" -m pip install \
      --disable-pip-version-check --no-deps -e "$runtime" || {
        rollback_failed=1
        critical_recovery_ok=0
      }
    systemctl --user daemon-reload || {
      rollback_failed=1
      critical_recovery_ok=0
    }
    release_settings_lock || {
      rollback_failed=1
      critical_recovery_ok=0
    }
  else
    rollback_failed=1
  fi
  if [[ "$settings_lock_held" == 1 ]]; then
    release_settings_lock || rollback_failed=1
  fi
  # Presentation writers and the original timer semantics are restored only
  # after the entire critical file/code/unit recovery completed under lock.
  if [[ "$critical_recovery_ok" == 1 ]]; then
    if [[ "$admin_active_before" == active ]]; then
      systemctl --user start wirtelprimpf-admin.service || rollback_failed=1
    else
      systemctl --user stop wirtelprimpf-admin.service || rollback_failed=1
    fi
    if [[ "$applet_running_before" == 1 ]]; then
      gdbus call --session --dest org.Cinnamon --object-path /org/Cinnamon \
        --method org.Cinnamon.ReloadXlet wirtelprimfgenerator@H234598 APPLET \
        >/dev/null || rollback_failed=1
    fi
    if restore_timer_enablement_stopped; then
      restore_timer_activity || rollback_failed=1
    else
      rollback_failed=1
    fi
  fi
  if [[ "$config_attention" != 0 ]]; then
    printf 'CONFIG RECOVERY ATTENTION REQUIRED; competing state preserved: %s\n' \
      "$deploy_backup" >&2
  fi
  if [[ "$rollback_failed" != 0 ]]; then
    printf 'DEPLOYMENT ROLLBACK INCOMPLETE: %s\n' "$deploy_backup" >&2
  fi
  final_status="$original_status"
  if [[ "$final_status" == 0 && ( "$rollback_failed" != 0 || "$config_attention" != 0 ) ]]; then
    final_status=1
  fi
  exit "$final_status"
}

trap 'rollback_deployment $?' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# The first operational mutation occurs only after the complete restorable
# pre-state and trap above exist.
quiesce_generator

# Stop the second settings writer, then hold the same exclusive flock used by
# SettingsManager. Applet requests now fail busy instead of racing the
# settings/state recovery point. Lock contention aborts without weakening it.
systemctl --user stop wirtelprimpf-admin.service
acquire_settings_lock

# Back up every target only after generation/admin quiescence and while the
# settings lock protects config/state. Config backups remain manual recovery
# evidence only; automatic rollback classifies and preserves current config
# bytes. Install artifacts retain automatic present/missing rollback semantics.
install -d -m0700 "$deploy_backup/files"
: >"$deploy_backup/config-manifest.tsv"
: >"$deploy_backup/install-manifest.tsv"
: >"$deploy_backup/directory-modes-before.tsv"
chmod 0600 "$deploy_backup/config-manifest.tsv" \
  "$deploy_backup/install-manifest.tsv" \
  "$deploy_backup/directory-modes-before.tsv"
for target in \
  /home/teladi/.config/wirtelprimpf \
  /home/teladi/.config/cloudflare \
  /home/teladi/.config/systemd/user/wirtelprimpf.timer.d; do
  directory_is_mode_scoped "$target"
  test -d "$target" && test ! -L "$target"
  printf '%s\t%s\n' "$(stat -Lc '%a' -- "$target")" "$target" \
    >>"$deploy_backup/directory-modes-before.tsv"
done
test "$(wc -l <"$deploy_backup/directory-modes-before.tsv")" = 3
backup_index=0
backup_one() {
  local manifest="$1" target="$2" payload
  target_is_scoped "$target"
  test ! -L "$target"
  backup_index=$((backup_index + 1))
  payload="$deploy_backup/files/$(printf '%03d' "$backup_index")"
  if [[ -e "$target" ]]; then
    cp -a -- "$target" "$payload"
    printf 'present\t%s\t%s\n' "$target" "$payload" >>"$manifest"
  else
    printf 'missing\t%s\t%s\n' "$target" "$payload" >>"$manifest"
  fi
}
for target in \
  /home/teladi/.config/wirtelprimpf/openai.env \
  /home/teladi/.config/cloudflare/api-token.env \
  /home/teladi/.config/systemd/user/wirtelprimpf.timer.d/override.conf \
  /home/teladi/.config/wirtelprimpf/settings-state.json; do
  backup_one "$deploy_backup/config-manifest.tsv" "$target"
done
for target in \
  /home/teladi/.local/share/cinnamon/applets/wirtelprimfgenerator@H234598 \
  /home/teladi/.local/share/cinnamon/applets/wirtelprimfgenerator@local \
  /home/teladi/.local/bin/wirtelprimpf-story-directives \
  /home/teladi/.config/systemd/user/wirtelprimpf.service \
  /home/teladi/.config/systemd/user/wirtelprimpf.timer \
  /home/teladi/.config/systemd/user/wirtelprimpf-admin.service; do
  backup_one "$deploy_backup/install-manifest.tsv" "$target"
done
backup_complete=1

git_runtime fetch origin main
test "$(git_runtime rev-parse origin/main)" = "$target_sha"
git_runtime switch --detach "$target_sha"
"$runtime/.venv/bin/python" -m pip install \
  --disable-pip-version-check --no-deps -e "$runtime"
install -Dm0644 "$runtime/Sourcecode/systemd-user/wirtelprimpf.service" \
  /home/teladi/.config/systemd/user/wirtelprimpf.service
# The timer base unit is a confirmed invariant: preserve its existing inode and
# bytes instead of replacing it; only generator/admin units are installed.
cmp --silent "$runtime/Sourcecode/systemd-user/wirtelprimpf.timer" \
  /home/teladi/.config/systemd/user/wirtelprimpf.timer
install -Dm0644 "$runtime/Sourcecode/systemd-user/wirtelprimpf-admin.service" \
  /home/teladi/.config/systemd/user/wirtelprimpf-admin.service
"$runtime/scripts/install-local.sh"
systemctl --user daemon-reload
release_settings_lock
test "$(systemctl --user is-active wirtelprimpf.timer || true)" = inactive
test "$(systemctl --user show wirtelprimpf.service \
  -p ActiveState --value)" = inactive
systemctl --user start wirtelprimpf-admin.service
if [[ "$applet_running_before" == 1 ]]; then
  gdbus call --session --dest org.Cinnamon --object-path /org/Cinnamon \
    --method org.Cinnamon.ReloadXlet wirtelprimfgenerator@H234598 APPLET >/dev/null
fi

# Prove quiescence immediately before the live settings transaction.
test "$(systemctl --user is-active wirtelprimpf.timer || true)" = inactive
test "$(systemctl --user show wirtelprimpf.service \
  -p ActiveState --value)" = inactive
export WIRTELPRIMPF_SMOKE_OWNERSHIP_MARKER="$deploy_backup/smoke-owned-revision.json"
# Execute the exact Step-5 API/header/status assertions and the exact corrected
# Step-6 live-sync script here, synchronously. POST has only a finite client
# socket timeout; CLI apply has no subprocess kill timeout. Unknown responses
# reconcile by revision; final restoration uses only last_owned_snapshot and
# proves a stale restore basis returns 409.

# Prove that neither the smoke nor an applet interaction restarted generation.
test "$(systemctl --user is-active wirtelprimpf.timer || true)" = inactive
test "$(systemctl --user show wirtelprimpf.service \
  -p ActiveState --value)" = inactive

# After the smoke returns success, its private marker contains the final
# last-owned revision. Reacquire the settings lock, reject a revision mismatch,
# and only then capture raw fingerprints used solely for ownership
# classification. Automatic rollback never copies a config backup.
acquire_settings_lock
smoke_owned_revision="$(jq -er '.revision' "$deploy_backup/smoke-owned-revision.json")"
state_revision="$(jq -er '.revision' /home/teladi/.config/wirtelprimpf/settings-state.json)"
test "$state_revision" = "$smoke_owned_revision"
capture_config_fingerprints >"$deploy_backup/owned-config-fingerprints.tsv"
chmod 0600 "$deploy_backup/owned-config-fingerprints.tsv"
release_settings_lock

diff --recursive --brief --exclude='__pycache__' --exclude='*.pyc' \
  "$runtime/files/wirtelprimfgenerator@H234598" \
  /home/teladi/.local/share/cinnamon/applets/wirtelprimfgenerator@H234598
cmp --silent "$runtime/Sourcecode/systemd-user/wirtelprimpf.timer" \
  /home/teladi/.config/systemd/user/wirtelprimpf.timer
if [[ "$admin_active_before" == inactive ]]; then
  systemctl --user stop wirtelprimpf-admin.service
fi
restore_timer_enablement_stopped

# Keep main untouched until every install/smoke assertion has passed. Timer
# enablement has its recorded value here, but activity remains fail-closed
# inactive across both worktree transitions.
git_runtime switch "$runtime_branch_before"
git_runtime merge --ff-only "$target_sha"
software_commit_complete=1
test "$(git_runtime rev-parse HEAD)" = "$target_sha"
test -z "$(git_runtime status --porcelain)"

# No checkout, install, config, unit, applet, or admin mutation follows this
# point. Restoring activity is the final operational phase; a failure invokes
# the post-commit fail-closed path and never rewinds main.
restore_timer_activity
deployment_complete=1
trap - EXIT INT TERM
```

Expected: the previous SHA and exact restorable service semantics are privately
recorded; generator activity cannot overlap backup/install/smoke; every
present/missing target has an allowlisted restore action; any failure restores
the old checkout, editable install, units, applet, admin state, exact timer
enablement/activity, and the three allowlisted pre-existing parent-directory
modes. Config/state backups remain manual evidence and are never copied by
automatic rollback. Success retains the intended `0700` directory hardening and
advances `main` only by `--ff-only`. The procedure contains no reset, force
push, forced checkout, or unscoped deletion.

- [ ] **Step 10: Syntax-check and failure-inject the restore semantics in isolation**

Before touching the live checkout, extract the complete Step-9 code block and
pipe it to `bash -n`. Then run this disposable harness; it exercises an injected
failure after install-target mutation, exact restoration of an originally
present target, deletion of an originally missing target, bounded fail-closed
generator quiescence before recovery mutation, and the full lock lifetime over
backup/code/install/unit recovery. It also proves the three config
classifications: backup-byte-equal is preserved, a semantically restored
smoke-owned revision is preserved without copying old bytes, and a later
competitor is preserved with an attention-required result. Finally, it proves
that an existing allowlisted parent changed from `0755` to `0700` by the
installer returns to `0755` only on rollback:

```bash
set -Eeuo pipefail
sandbox="$(mktemp -d /tmp/wirtelprimpf-restore-harness.XXXXXX)"
cleanup() {
  [[ "$sandbox" == /tmp/wirtelprimpf-restore-harness.* && -d "$sandbox" ]]
  rm -rf -- "$sandbox"
}
trap cleanup EXIT
mkdir -p "$sandbox/backup" "$sandbox/live"
printf 'old-install\n' >"$sandbox/backup/present"
mkdir "$sandbox/live/private-parent"
chmod 0755 "$sandbox/live/private-parent"
printf '755\n' >"$sandbox/backup/private-parent-mode"
printf 'lock-sentinel\n' >"$sandbox/settings.lock"
printf 'active\n' >"$sandbox/timer-state"
printf 'active\n' >"$sandbox/generator-state"
: >"$sandbox/recovery-events"

assert_recovery_lock_held() {
  if flock -n "$sandbox/settings.lock" true; then
    printf 'recovery mutation escaped the settings lock\n' >&2
    return 1
  fi
}

restore_install_targets() {
  test "$(<"$sandbox/generator-state")" = inactive
  assert_recovery_lock_held
  printf 'install-restore\n' >>"$sandbox/recovery-events"
  rm -rf -- "$sandbox/live/present" "$sandbox/live/was-missing"
  cp -a -- "$sandbox/backup/present" "$sandbox/live/present"
}

restore_private_parent_mode() {
  assert_recovery_lock_held
  printf 'directory-mode-restore\n' >>"$sandbox/recovery-events"
  chmod "$(<"$sandbox/backup/private-parent-mode")" \
    "$sandbox/live/private-parent"
}

quiesce_generator_harness() {
  local transition="$1" attempts=0 max_attempts=3
  printf 'timer-stop\n' >>"$sandbox/recovery-events"
  printf 'inactive\n' >"$sandbox/timer-state"
  while [[ "$(<"$sandbox/generator-state")" != inactive ]]; do
    attempts=$((attempts + 1))
    if [[ "$transition" == after-first-wait && "$attempts" == 1 ]]; then
      printf 'inactive\n' >"$sandbox/generator-state"
    fi
    (( attempts < max_attempts )) || return 1
  done
  printf 'generator-inactive\n' >>"$sandbox/recovery-events"
}

rollback_harness() {
  local transition="$1" lock_wait="$2"
  quiesce_generator_harness "$transition" || return 1
  printf 'admin-stop\n' >>"$sandbox/recovery-events"
  exec {recovery_lock}<>"$sandbox/settings.lock"
  if ! flock -w "$lock_wait" "$recovery_lock"; then
    exec {recovery_lock}>&-
    return 1
  fi
  printf 'settings-lock\n' >>"$sandbox/recovery-events"
  restore_install_targets
  restore_private_parent_mode
  assert_recovery_lock_held
  printf 'config-classify\n' >>"$sandbox/recovery-events"
  assert_recovery_lock_held
  printf 'checkout-restore\n' >>"$sandbox/recovery-events"
  test "$(<"$sandbox/generator-state")" = inactive
  assert_recovery_lock_held
  printf 'venv-restore\n' >>"$sandbox/recovery-events"
  assert_recovery_lock_held
  printf 'daemon-reload\n' >>"$sandbox/recovery-events"
  flock -u "$recovery_lock"
  exec {recovery_lock}>&-
  printf 'settings-unlock\n' >>"$sandbox/recovery-events"
  flock -n "$sandbox/settings.lock" true
  printf 'admin-restore\napplet-reload\ntimer-restore\n' \
    >>"$sandbox/recovery-events"
}

set +e
(
  set -Eeuo pipefail
  trap 'rollback_harness after-first-wait 0.2' EXIT
  printf 'new-install\n' >"$sandbox/live/present"
  printf 'created-by-install\n' >"$sandbox/live/was-missing"
  chmod 0700 "$sandbox/live/private-parent"
  false # injected deployment failure
)
injected_status=$?
set -e
test "$injected_status" -ne 0
cmp --silent "$sandbox/backup/present" "$sandbox/live/present"
test ! -e "$sandbox/live/was-missing"
test "$(stat -Lc '%a' "$sandbox/live/private-parent")" = 755
test "$(paste -sd, "$sandbox/recovery-events")" = \
  timer-stop,generator-inactive,admin-stop,settings-lock,install-restore,directory-mode-restore,config-classify,checkout-restore,venv-restore,daemon-reload,settings-unlock,admin-restore,applet-reload,timer-restore

# A generator that never becomes inactive exhausts its finite bound and no
# install/checkout/venv restoration is attempted beneath it.
: >"$sandbox/recovery-events"
printf 'active\n' >"$sandbox/generator-state"
set +e
rollback_harness never 0.2
quiesce_status=$?
set -e
test "$quiesce_status" -ne 0
test "$(paste -sd, "$sandbox/recovery-events")" = timer-stop

# Lock contention is also bounded and fail-closed: after quiescence/admin-stop,
# no install, directory-mode, config, checkout, venv, or unit restore occurs.
: >"$sandbox/recovery-events"
printf 'inactive\n' >"$sandbox/generator-state"
exec {competitor_lock}<>"$sandbox/settings.lock"
flock -n "$competitor_lock"
set +e
rollback_harness already-inactive 0.05
lock_wait_status=$?
set -e
test "$lock_wait_status" -ne 0
test "$(paste -sd, "$sandbox/recovery-events")" = \
  timer-stop,generator-inactive,admin-stop
flock -u "$competitor_lock"
exec {competitor_lock}>&-

# The lock opens read/write without truncation. It remains held over the exact
# deployment phases that can otherwise overlap an applet CLI transaction.
exec {held_lock}<>"$sandbox/settings.lock"
flock -n "$held_lock"
for phase in backup fetch detach pip units applet daemon-reload; do
  if flock -n "$sandbox/settings.lock" true; then
    printf 'lock escaped during %s\n' "$phase" >&2
    exit 1
  fi
done
test "$(<"$sandbox/settings.lock")" = lock-sentinel
flock -u "$held_lock"
exec {held_lock}>&-
for phase in admin-start live-smoke; do
  flock -n "$sandbox/settings.lock" true
done

# An active pre-state is restored only after target main is stable. There is no
# file/worktree event after timer-start. The injected signal window sets main to
# target while the shell flag is still zero; ref detection still quiesces and
# reports incomplete instead of trying to rewind main.
: >"$sandbox/success-events"
printf 'inactive\n' >"$sandbox/timer-state"
printf 'timer-enablement-restored-stopped\n' >>"$sandbox/success-events"
test "$(<"$sandbox/timer-state")" = inactive
printf 'worktree-switch-main\n' >>"$sandbox/success-events"
printf 'main-fast-forward\n' >>"$sandbox/success-events"
software_commit_complete=1
printf 'main-target-stable\n' >>"$sandbox/success-events"
test "$(tail -n1 "$sandbox/success-events")" = main-target-stable
printf 'active\n' >"$sandbox/timer-state"
printf 'timer-start\n' >>"$sandbox/success-events"
test "$(paste -sd, "$sandbox/success-events")" = \
  timer-enablement-restored-stopped,worktree-switch-main,main-fast-forward,main-target-stable,timer-start
test "$(tail -n1 "$sandbox/success-events")" = timer-start

software_commit_complete=0
target_sha=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
runtime_sha_before=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
third_sha=cccccccccccccccccccccccccccccccccccccccc
classify_main_ref() {
  case "$1" in
    "$runtime_sha_before") printf 'precommit\n' ;;
    "$target_sha") printf 'postcommit\n' ;;
    *) printf 'unknown\n' ;;
  esac
}
test "$(classify_main_ref "$runtime_sha_before")" = precommit
test "$(classify_main_ref "$target_sha")" = postcommit
test "$(classify_main_ref "$third_sha")" = unknown

for main_ref_now in "$target_sha" "$third_sha"; do
  : >"$sandbox/postcommit-events"
  printf 'active\n' >"$sandbox/timer-state"
  main_ref_state="$(classify_main_ref "$main_ref_now")"
  if [[ "$software_commit_complete" == 1 || "$main_ref_state" != precommit ]]; then
    printf 'inactive\n' >"$sandbox/timer-state"
    printf 'timer-stop\n%s-incomplete\n' "$main_ref_state" \
      >>"$sandbox/postcommit-events"
  fi
  test "$(<"$sandbox/timer-state")" = inactive
  test "$(paste -sd, "$sandbox/postcommit-events")" = \
    "timer-stop,${main_ref_state}-incomplete"
  if rg -q -- 'checkout|venv|install|worktree' "$sandbox/postcommit-events"; then
    exit 1
  fi
done

printf 'OUTPUT_RESOLUTION=source\n' >"$sandbox/backup/openai.env"
printf '{"revision":"old"}\n' >"$sandbox/backup/settings-state.json"
cp -a -- "$sandbox/backup/openai.env" "$sandbox/live/openai.env"
cp -a -- "$sandbox/backup/settings-state.json" "$sandbox/live/settings-state.json"

fingerprint_live_config() {
  local target
  for target in "$sandbox/live/openai.env" "$sandbox/live/settings-state.json"; do
    printf '%s\t%s\t%s\n' "$target" \
      "$(stat -Lc '%d:%i:%s:%Y' -- "$target")" \
      "$(sha256sum -- "$target" | cut -d' ' -f1)"
  done
}

classify_config_without_restore() {
  local current owned_revision current_revision
  if cmp --silent "$sandbox/backup/openai.env" "$sandbox/live/openai.env" && \
    cmp --silent "$sandbox/backup/settings-state.json" \
      "$sandbox/live/settings-state.json"; then
    return 0
  fi
  test -s "$sandbox/owned-config-fingerprints.tsv" || return 2
  current="$(fingerprint_live_config)" || return 1
  cmp --silent "$sandbox/owned-config-fingerprints.tsv" <(printf '%s\n' "$current") || return 2
  owned_revision="$(jq -er '.revision' "$sandbox/smoke-owned-revision.json")" || return 1
  current_revision="$(jq -er '.revision' "$sandbox/live/settings-state.json")" || return 2
  test "$owned_revision" = "$current_revision" || return 2
}

# Byte-equal backup classification performs no write.
before="$(fingerprint_live_config)"
classify_config_without_restore
test "$(fingerprint_live_config)" = "$before"

# The smoke restores the setting semantically but writes a fresh revision and
# possibly normalized env bytes. Preserve this complete state verbatim.
printf '# normalized by transaction\nOUTPUT_RESOLUTION=source\n' \
  >"$sandbox/live/openai.env"
printf '{"revision":"new-owned"}\n' >"$sandbox/live/settings-state.json"
printf '{"revision":"new-owned"}\n' >"$sandbox/smoke-owned-revision.json"
fingerprint_live_config >"$sandbox/owned-config-fingerprints.tsv"
owned_before="$(fingerprint_live_config)"
classify_config_without_restore
test "$(fingerprint_live_config)" = "$owned_before"
test "$(jq -r '.revision' "$sandbox/live/settings-state.json")" = new-owned
! cmp --silent "$sandbox/backup/openai.env" "$sandbox/live/openai.env"

# A later competitor produces attention-required (2) and is also untouched.
printf 'OUTPUT_RESOLUTION=4k\n' >"$sandbox/live/openai.env"
printf '{"revision":"competitor"}\n' >"$sandbox/live/settings-state.json"
competitor_before="$(fingerprint_live_config)"
set +e
classify_config_without_restore
config_status=$?
set -e
test "$config_status" = 2
test "$(fingerprint_live_config)" = "$competitor_before"
test "$(jq -r '.revision' "$sandbox/live/settings-state.json")" = competitor
```

Expected: `bash -n` and the harness exit 0. The rollback log proves timer stop
and bounded service quiescence precede every file/code restore; the stuck case
fails closed without reaching those mutations. The lock sentinel survives and
contention remains closed through `daemon-reload`, then opens before admin/smoke.
All three config cases retain their current bytes and semantic revision; no
automatic branch copies config backup bytes. The existing private-parent mode
returns from the simulated installer's `0700` to its recorded `0755`, while a
successful live installation would retain the intended `0700` hardening. The
active-timer trace ends at `timer-start` only after `main-target-stable`; its
merge-to-flag signal-window trace stops the timer and contains no worktree/file
rewind. A third/unexpected main SHA is classified `unknown` and preserves files
identically; only the exact recorded pre-deploy SHA authorizes rollback.
This is local disposable evidence, not permission to execute Step 9; the live
rollout remains separately gated.

#### Verbindliches Execution-Context-Erratum für Tasks 5–6

Dieses Erratum ist gegenüber allen unqualifizierten lokalen Befehlen in den
nachfolgenden Tasks normativ. Vor **jeder** lokalen Datei-, Git-, Build- oder
Validatoraktion am Archiv muss der bereits verlangte Null-Check des
Archivpreflights bestehen; anders als beim separat behandelten Runtime-Checkout
ist hier keine Besitzreparatur freigegeben:

```bash
archive_checkout=/home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001
test -d "$archive_checkout" && test ! -L "$archive_checkout"
test "$(realpath -e -- "$archive_checkout")" = "$archive_checkout"
test -z "$(find "$archive_checkout" -xdev \
  \( ! -user teladi -o ! -group teladi \) -print -quit)"
```

Alle lokalen Task-5-Operationen an diesem Checkout – einschließlich
`status/fetch/switch/pull/diff/add/commit/push/rev-parse`, der Änderung von
`pages.yml`, Builds und Validatoren – laufen vollständig als UID/GID `teladi`
im bereits oben definierten `runuser -u teladi -- env ...`-Kontext. Root darf
in Task 5 nur die GitHub-Remote-API über `gh` abfragen/auslösen. Lokale
Argumente oder Dateiinhalte dürfen nicht vorab durch eine Root-Shell expandiert
werden. Eine Eigentümer- oder Git-Vertrauenshürde ist ein Stop-Gate; weder
Root-Git noch `safe.directory` noch `chown` sind hier zulässige Abkürzungen.

Für Task 6 gilt dieselbe Trennung: Lesen von `platform-state.json`, lokales
Archiv-/Runtime-Git und alle lokalen `systemctl --user`-, `gdbus`- und
Runtime-Statusbefehle laufen im expliziten `teladi`-Desktopkontext mit
`XDG_RUNTIME_DIR=/run/user/1000` und
`DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus`. Root-`gh` darf erst die
dadurch gewonnenen, vollständig validierten Literale für Remote-Aktionen
verwenden; öffentliche read-only HTTPS-`curl`-Prüfungen dürfen separat laufen.
Damit kann weder die falsche User-Manager-/D-Bus-Instanz noch ein
Root-`safe.directory`-Workaround als Laufzeitevidenz in Task 6 eingehen.

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
archive_checkout=/home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001
archive_dirty="$(git -C "$archive_checkout" status --porcelain)"
if [[ -n "$archive_dirty" ]]; then
  printf 'Archive checkout is not clean before synchronization.\n' >&2
  printf '%s\n' "$archive_dirty" >&2
  exit 1
fi
git -C "$archive_checkout" fetch origin
git -C "$archive_checkout" switch main
git -C "$archive_checkout" pull --ff-only origin main
test -z "$(git -C "$archive_checkout" status --porcelain)"
git -C "$archive_checkout" switch -c chore/pin-transactional-site-factory
```

Expected: clean checkout; stop if unrelated user changes appear.

- [ ] **Step 2: Resolve and validate the immutable factory SHA**

Run:

```bash
generator_runtime=/home/teladi/.local/share/wirtelprimpf-generator
git_runtime() {
  test -z "$(find "$generator_runtime" -xdev \
    \( ! -user teladi -o ! -group teladi \) -print -quit)"
  git -C "$generator_runtime" "$@"
}
generator_factory_sha="$(git_runtime rev-parse HEAD)"
test "$generator_factory_sha" = "$(git_runtime rev-parse origin/main)"
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
generator_checkout=/home/teladi/.local/share/wirtelprimpf-generator
archive_checkout=/home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001
workflow="$archive_checkout/.github/workflows/pages.yml"
test "$generator_factory_sha" = "$(git -C "$generator_checkout" rev-parse origin/main)"
test "$generator_factory_sha" = "$(git -C "$generator_checkout" ls-remote origin refs/heads/main | cut -f1)"
test "$(rg -o -- '[0-9a-f]{40}' "$workflow" | sort -u | wc -l)" -eq 1
test "$(rg -o -F -- "$generator_factory_sha" "$workflow" | wc -l)" -eq 2
rg -F -- "$generator_factory_sha" "$workflow"
test "$(git -C "$archive_checkout" diff --name-only)" = .github/workflows/pages.yml
test "$(git -C "$archive_checkout" diff --numstat)" = $'2\t2\t.github/workflows/pages.yml'
git -C "$archive_checkout" diff --check
git -C "$archive_checkout" diff -- .github/workflows/pages.yml
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
archive_head_sha="$(git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 rev-parse HEAD)"
test "$(gh pr view "$archive_pr_number" --repo H234598/Wirtelprimpf-0001 --json headRefOid --jq .headRefOid)" = "$archive_head_sha"
archive_mergeable=UNKNOWN
for attempt in $(seq 1 15); do
  archive_mergeable="$(gh pr view "$archive_pr_number" --repo H234598/Wirtelprimpf-0001 --json mergeable --jq .mergeable)"
  case "$archive_mergeable" in
    MERGEABLE) break ;;
    CONFLICTING) printf 'Archive pin PR is conflicting.\n' >&2; exit 1 ;;
    UNKNOWN) sleep 2 ;;
    *) printf 'Unexpected mergeability state: %s\n' "$archive_mergeable" >&2; exit 1 ;;
  esac
done
test "$archive_mergeable" = MERGEABLE
test "$(gh pr view "$archive_pr_number" --repo H234598/Wirtelprimpf-0001 --json files --jq '.files[].path')" = .github/workflows/pages.yml
test "$(git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 diff --name-only origin/main...HEAD)" = .github/workflows/pages.yml
test "$(git -C /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001 diff --numstat origin/main...HEAD)" = $'2\t2\t.github/workflows/pages.yml'
check_count="$(gh pr view "$archive_pr_number" \
  --repo H234598/Wirtelprimpf-0001 \
  --json statusCheckRollup \
  --jq '.statusCheckRollup | length')"
if (( check_count > 0 )); then
  gh pr checks "$archive_pr_number" --repo H234598/Wirtelprimpf-0001 --watch --fail-fast
else
  printf '%s\n' 'No pull-request checks are configured for pages.yml; this is an accepted absence of PR CI, not a CI success.'
  rg -n -- '^\s*pull_request\s*:' /home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001/.github/workflows/pages.yml && exit 1 || true
fi
```

Expected: the PR head equals the reviewed local commit, GitHub reports it mergeable, the file list contains only `pages.yml`, and the committed diff is exactly two removed plus two added SHA-value lines. Every check that exists succeeds. Because the current `pages.yml` has no `pull_request` trigger, a genuine zero-check result is explicitly accepted only as **no PR CI configured**, never reported as CI success. The post-merge `main` Pages run in Step 6 is the real build/deploy gate.

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

## Additives Evidenzledger der lokalen Tasks 1–2

### 2026-08-01 — Task 1: exakt sechs freigegebene öffentliche Copy-Verträge

- Der Contract-Test `web/tests/copy-contract.test.ts` wurde vor jeder
  Produktionsänderung hinzugefügt. Der erste Lauf
  `npm --prefix web test -- --test-name-pattern='approved public copy'` endete
  erwartungsgemäß mit Exit 1: 8/9 Tests waren grün und ausschließlich der neue
  Copy-Vertrag rot. Da Node nach dem ersten Assertionfehler abbricht, belegte
  ein zusätzlicher read-only Quellcheck alle sechs Ausgangsverträge einzeln:
  `brand`, `hero`, `chronology`, `repositories`, `release` und `status` jeweils
  mit `old_present=True`, Zieltext abwesend, insgesamt 6/6 RED-Verträge.
- Nach exakt den sechs freigegebenen Änderungen bestand derselbe Fokuslauf
  9/9. Der Produktionsdiff umfasste ausschließlich vier Astro-Dateien mit sechs
  geänderten Zeilenpaaren: `Telacores:`, die neue Hero-Zeile, zwei vollständige
  Satzentfernungen, die Entfernung von `hashgebunden` und den exakten neuen
  Statussatz. Es gab keine siebte Copy-Änderung und keinen Reflow.
- `npm --prefix web test` bestand 9/9; der Hub-Check
  `WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site"
  WIRTELPRIMPF_SITE_PROFILE=hub npm --prefix web run check` prüfte 22 Dateien
  mit 0 Fehlern, 0 Warnungen und 0 Hinweisen. `git diff --check` war sauber.
- Der isolierte Codecommit ist
  `81d63ecd641316422004bfd903bac922d643a74b`
  (`feat(web): apply approved public story copy`): fünf Dateien einschließlich
  des 25-zeiligen Contract-Tests, insgesamt 31 Einfügungen und sechs
  Entfernungen. Unmittelbar nach dem Commit war `git status --short` leer.

### 2026-08-01 — Task 2: Hub- und Archivartefakte

- Der wörtliche Hub-Beispielbuild nur mit `web/fixtures/site` bestand Build und
  Validator (12 Dateien, 7 HTML, 77 interne Links, Baum-SHA-256
  `e75ba7c5ea614b5a92032394c6d95cdc3e4c8adbf638e61f03ec61a73bf884e6`),
  konnte den geforderten `Im Release`-Text jedoch nicht erzeugen: Das
  eingecheckte Fixture enthält kein `media-manifest.json` und rendert deshalb
  bestimmungsgemäß den Medien-Empty-State. Dies war ein Eingabedaten-, kein
  Copy-Vertragsfehler.
- Für den vollständigen, weiterhin rein lokalen Artefaktnachweis erhielten
  beide Builds zusätzlich den read-only Override
  `WIRTELPRIMPF_MEDIA_MANIFEST="$PWD/data/media-manifest.json"`. Dieses bereits
  getrackte Manifest der Branch enthält 779 validierte Medieneinträge; es wurde
  nicht verändert und es wurde keine siebte Quell- oder Copy-Datei ergänzt.
- Hub-Befehl: `WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site"
  WIRTELPRIMPF_MEDIA_MANIFEST="$PWD/data/media-manifest.json"
  WIRTELPRIMPF_SITE_PROFILE=hub
  WIRTELPRIMPF_SITE_URL=https://wirtelprimpf.telacore.org
  npm --prefix web run build`, danach
  `python3 scripts/validate_pages_artifact.py web/dist --expected-domain
  wirtelprimpf.telacore.org`. Ergebnis: 823 Dateien, 818 HTML, 10.840 interne
  Links, 4.344.374 Byte, Baum-SHA-256
  `0acc6695654d3e82e450a3467d96995da89e59d954d00340d5a5028916ab1bb6`.
  Required-Treffer auf der Start-/Statusseite: `Telacores:` 1,
  Hero 1, Statussatz 1 und `Im Release` 6. Alle sechs vorgegebenen
  Forbidden-Scans sowie ein zusätzlicher robuster `Möhren`-Scan waren leer.
  Die Canonicals lauteten `/` und `/projekt/status/` jeweils unter
  `https://wirtelprimpf.telacore.org`.
- Archivbefehl: derselbe Daten-/Manifestvertrag mit
  `WIRTELPRIMPF_SITE_PROFILE=archive` und
  `WIRTELPRIMPF_SITE_URL=https://wirtelprimpf-0001.telacore.org`, danach der
  Validator mit `--expected-domain wirtelprimpf-0001.telacore.org`. Ergebnis:
  823 Dateien, 818 HTML, 10.840 interne Links, 4.395.867 Byte, Baum-SHA-256
  `f6e682fa639f72863f8911bb2b94d416ba83e913613797334361e439308a91bd`.
  Required-Treffer: `Publikationsarchiv 0001` 1, `Im Release` 6,
  ` archiviert.` 6 und Statussatz 1. Alle sieben ausgeführten Forbidden-Scans,
  der zusätzliche `Telacores:`-Ausschluss im Archivheader und der robuste
  `Möhren`-Scan waren leer. Alle 818 HTML-Dateien besaßen eine Canonical unter
  `https://wirtelprimpf-0001.telacore.org/`; fehlend 0, fremde Domain 0.
- `git status --short` blieb nach beiden Builds leer. `web/dist/` und
  `web/.astro/` waren ausschließlich ignorierte Artefakte gemäß den
  `.gitignore`-Zeilen 19 und 20; kein Build- oder Dependency-Artefakt wurde
  getrackt.
- Task 3 und alle folgenden Tasks wurden nicht begonnen. Es erfolgten kein
  Fetch, Push, PR, Merge, Install, `systemctl`, Cinnamon-Reload, Pages-Dispatch,
  Cloudflare-/DNS-Zugriff, Upstream-Fix und keine Änderung am
  Generatorvertrag oder an laufenden Systemen.

### 2026-08-01 — Task 3: additive Schlussreview-Remediation vor dem erneuten Push

- Der historische Abschlussvermerk der lokalen Tasks 1–2 unmittelbar darüber
  bleibt unverändert erhalten. Task 3 wurde danach begonnen: Der bereits
  eröffnete, nicht als Draft markierte Generator-PR ist
  `https://github.com/H234598/Wirtelprimpf-generator/pull/4`. Vor dem erneuten
  Push wurde ausdrücklich weder gemergt noch der Runtime-Checkout berührt.
- Vier zusätzliche Root-Reviewbefunde wurden jeweils vor der
  Produktionsänderung reproduziert. Der RED-Lauf über 47 fokussierte Tests
  belegte: ein bereits existierender privater finaler Parent blieb `0755`;
  `Content-Length: 100` mit nur zwei Bodybytes blockierte den Handler bis zum
  Schließen des Peers und GET/HEAD lasen nichtleere Bodies; die reale doppelte
  systemd-Eigenschaft `TimersMonotonic=` verlor durch Dictionary-Überschreiben
  den `OnUnitActiveUSec`-Eintrag; Applet-Save und operative systemd-Aktionen
  besaßen getrennte Busy-Gates. Es gab sechs erwartete Assertionfehler und drei
  erwartete Fehlerpfade ausschließlich in diesen neuen Verträgen.
- Der Produktionsfix `6d4454a` (`fix(settings): close final review blockers`)
  umfasst genau acht Dateien. Neue private Zwischenverzeichnisse bleiben
  `0700`, und zusätzlich wird der bestehende finale private Parent wieder auf
  `0700` gehärtet. Der lokale HTTP-Handler verwirft nichtleere GET-/HEAD-Bodies,
  begrenzt POST-Bodyreads pro Verbindung auf zwei Sekunden, antwortet bei
  Timeout mit 408, bei vorzeitigem EOF mit 400 und stellt das vorherige
  Socket-Timeout wieder her. Der systemd-Adapter sammelt alle wiederholten
  Propertywerte und wählt den `OnUnitActiveUSec`-Eintrag unabhängig von der
  Reihenfolge. Applet-Save und operative Aktionen teilen ein gemeinsames Gate;
  Erfolgs-, Fehler- und Threadstartfehlerpfad geben es exakt wieder frei.
- Der GREEN-Fokuslauf bestand 47/47. Ein zusätzlicher read-only Livesmoke als
  UID/GID `teladi` mit `PYTHONPATH` auf diesen Worktree wertete die echte
  systemd-Ausgabe erfolgreich aus: Timer enabled/active, Intervall 120 Minuten,
  Randomisierung 120 Sekunden, persistent, Result `success`. Es wurden dabei
  weder Drop-in noch Timerzustand verändert.
- Die vollständige Matrix wurde anschließend auf dem sauberen Commit
  `6d4454a` wiederholt: Plattform 139/139; gesamtes `make check` einschließlich
  Admin-UI 22/22, Applet-Sync 20/20, Settings-Schema 12/12 und
  Story-Direktiven 31/31; Web 9/9; Astro 22 Dateien mit 0 Fehlern, 0 Warnungen
  und 0 Hinweisen; `compileall`, fokussiertes Ruff und `git diff --check`
  erfolgreich. Beide vollständigen Hub-/Archivprofile bestanden erneut Build,
  Artefaktvalidator, Copy-, Canonical- und Forbidden-Scans; der Archivbaum
  blieb bei 823 Dateien, 818 HTML, 10.840 internen Links und SHA-256
  `f6e682fa639f72863f8911bb2b94d416ba83e913613797334361e439308a91bd`.
- Der erneute Delta-Sicherheitsreview fand keine verbleibende Regression und
  keine Credential-/Key-Muster, neuen Shell-/Eval-/Deserialisierungs-Sinks oder
  erweiterten Schreibziele. Bis zu diesem Ledger-Eintrag erfolgten weiterhin
  kein erneuter Push, kein Merge, keine Installation, kein Service-/Timerwrite,
  kein Cinnamon-Reload und keine Cloudflare-/DNS-/Upstream-Mutation.

### 2026-08-01 — Task 3: transaktionale Schlussreview-Härtung und ausführbarer Rollbackvertrag

- Dieser Abschnitt ergänzt die vorherigen Ledger unverändert. Der lokale
  Produktions-/Testcommit ist
  `50c4ec94df1769fee788a3331714a74a28fb358d`
  (`fix(settings): harden transactional client boundaries`), ausgehend von
  `5d898a221f3100fa5b33634704f97412ac24f1e6`. Er umfasst zehn Dateien mit 599
  Einfügungen und 44 Entfernungen. Bis zu diesem Eintrag wurde er weder gepusht
  noch in einen Remote-Branch oder den Runtime-Checkout übernommen.
- Die zusätzlichen Verträge wurden vor der Produktionsänderung rot belegt. Der
  erste kombinierte Fokuslauf über 66 Python-Verträge endete mit sechs
  erwarteten Fehlschlägen und einem erwarteten Fehler; der Node-Lauf mit zwei
  erwarteten Fehlschlägen. Weitere isolierte RED-Läufe belegten, dass ein nur
  strukturell vorhandener, aber semantisch unvollständiger Snapshot sowie ein
  leerer Pflichtkatalog beide Oberflächen noch entsperren konnten. Der zuletzt
  ergänzte Slow-Drip-Vertrag sah beim Schreiben der 408-Antwort noch den fast
  abgelaufenen Sockettimeout (`0.0195484` statt des ursprünglichen `0.7`).
- Der Applet-Client besitzt nun für sämtliche 37 kanonisch
  `applet_visible=True` markierten Felder einen typisierten, per Paritätstest an
  `SETTING_SPECS` gebundenen Präsentationsvertrag. Erfolgreiche Snapshot- und
  Apply-Antworten müssen Settings, nichtleere Pflichtkataloge, Secret-Präsenz,
  Invarianten und Warnungen vollständig enthalten. Unvollständige Refresh-,
  Save- und 409-Snapshots werden fail-closed verworfen; lokale Entwürfe bleiben
  erhalten und selbst eine fehlerhafte Konfliktbehandlung kann nicht aus dem
  Completion-Callback entweichen. `snapshot` bleibt auf zehn Sekunden
  begrenzt; `apply` hat absichtlich keinen `subprocess.run`-Killtimeout, weil
  allein der CLI-Prozess die mehrstufige Write/Validate/Rollback-Transaktion zu
  Ende führen darf.
- Die Adminoberfläche validiert vor jedem initialen, Poll-, Save- oder
  Konflikt-Merge alle elf tatsächlich dargestellten Settings mit exaktem Typ,
  alle fünf Pflicht-Dropdownkataloge als nichtleer, die Secret-Präsenzfelder,
  Invarianten, Warnungen und die 64-stellige Revision. Bis zum ersten
  vollständigen Snapshot bleibt der gesamte `InteractionGate` gesperrt. Damit
  können weder Teilantworten noch leere Modellkataloge die Bedienoberfläche in
  einen nur teilweise synchronisierten Zustand versetzen.
- Der transaktionale Server vergleicht stale `base_values` jetzt typstreng;
  insbesondere kann `True` nicht mehr als Integer `1` einen Konflikt umgehen.
  Der Generatorvalidator erhält nach dem atomaren Write die exakt erneut aus
  dem persistenten Env-Dokument gelesenen Rohwerte und kein aus normalisierten
  Proposalwerten aufgebautes Overlay. Der Regressionstest mit einem bereits
  persistierten ungültigen Wert `99` belegt deshalb den Validatorfehler und die
  bytegenaue Rücknahme auch bei einer fachlich unabhängigen Änderung.
- Der systemd-Dauerparser akzeptiert die von systemd real ausgegebene exakte,
  einheitenlose Null, verwirft aber weiterhin jede andere nackte Zahl. Der
  Admin-Bodyreader verwendet für alle Teilreads eine einzige absolute
  monotone Frist. Nach Timeout wird zuerst der ursprüngliche Sockettimeout im
  `finally` wiederhergestellt und erst danach die 408-Antwort geschrieben;
  fortlaufende kleine Bodybytes können weder die Gesamtfrist verlängern noch
  den Antwortwrite mit der abgelaufenen Restfrist abbrechen.
- Die frische vollständige Matrix nach der letzten Codeänderung war grün:
  Plattform `143/143`; gesamtes `make check` mit Applet-Runtime, Admin-UI
  `23/23`, SemVer `8/8`, Git-Object-Fallback `3/3`, Release-Publication `3/3`,
  Helper-Environment `7/7`, Applet-Sync `23/23`, Settings-Schema `12/12` und
  Story-Directives `31/31`; Web `9/9`; Astro-Check über 22 Dateien mit null
  Fehlern, Warnungen und Hinweisen. `compileall`, Ruff 0.15.16 ohne Cache über
  alle geänderten Pythonpfade, `git diff --check`, Step-9-`bash -n` und der
  vollständig ausgeführte Step-10-Failure-Harness endeten jeweils mit Exit 0.
  Der unabhängige Rootlauf reproduzierte zusätzlich den kombinierten Fokus mit
  68/68 Python- und 23/23 Node-Verträgen sowie denselben Ruff-/Harnessbefund.
- Beide vollständigen Profile wurden nach der finalen Änderung erneut gebaut,
  copy-gescannt und validiert. Hub: 823 Dateien, 818 HTML, 10.840 interne Links,
  4.344.374 Byte und Baum-SHA-256
  `0acc6695654d3e82e450a3467d96995da89e59d954d00340d5a5028916ab1bb6`.
  Archiv: 823 Dateien, 818 HTML, 10.840 interne Links, 4.395.867 Byte und
  Baum-SHA-256
  `f6e682fa639f72863f8911bb2b94d416ba83e913613797334361e439308a91bd`.
  Required-, Forbidden- und Canonical-Prüfungen waren in beiden Profilen leer
  beziehungsweise exakt erfüllt; `web/dist` und `web/.astro` blieben ignoriert.
- Task 3 Step 3 wiederholt nach jedem neu integrierten `origin/main` nun die
  **vollständige** Matrix einschließlich `compileall`, Astro-Check und beider
  Profilbuilds/-validatoren. Die PR-Logik sucht zuerst alle passenden offenen
  PRs, verwendet PR 4 nur bei exakt geprüftem Head/Base-Paar und prüft vor den
  Checks erneut Zustand, Draftstatus und Head-OID. Merge- und Remote-main-SHA
  werden getrennt über GitHub und `ls-remote` belegt; der Runtime-Checkout wird
  dadurch noch nicht verändert.
- Der normative Task-4-Rolloutframe ist jetzt eine einzige reversible
  Transaktion im expliziten `teladi`-Desktopkontext. Generator und Timer werden
  vor jeder Mutation bounded bis `inactive` quiesziert, danach Admin gestoppt
  und derselbe Settings-`flock` ohne Truncation von Backup bis einschließlich
  Fetch, Detach, editable Pip, Units, Appletinstallation und `daemon-reload`
  gehalten. Rollback beginnt ebenfalls mit Timerstopp/Generatorquieszenz,
  wartet bounded auf den Settings-Lock und hält ihn über Installartefakte,
  Configklassifikation, altem Checkout, venv und `daemon-reload`. Bei
  Quieszenz- oder Lockfehler erfolgt keinerlei Datei-/Checkout-Restore.
- Configbackups sind ausschließlich private manuelle Recoveryevidenz. Der
  Automatismus führt genau drei Klassifikationen aus: bytegleich zum Backup,
  identisch zum finalen smoke-owned Fingerprint samt Revision oder
  konkurrierend/unbekannt. Alle drei erhalten die aktuellen Bytes; der dritte
  Fall endet attention-required und ungleich null. Das absichtliche semantische
  Restore des Smokes behält damit seine neue gültige Revision sowie konsistente
  Inode-/mtime-Signale. Nur Installartefakte besitzen automatische
  present/missing-Restoreaktionen.
- `install-local.sh` härtet drei vorhandene Elternverzeichnisse auf `0700`.
  Step 9 sichert deshalb ausschließlich ihre Modi in einer privaten,
  exakt allowlisteten Tabelle und stellt sie bei Rollback nur per `chmod`
  wieder her; es wird kein Elternverzeichnis gelöscht oder mit `cp -a`
  überschrieben. Ein erfolgreicher Rollout behält die `0700`-Härtung. Der
  Failure-Harness belegt separat `0755 -> 0700 -> 0755` im Rollback.
- HTTP-POST im Livesmoke besitzt nun einen endlichen 180-s-Sockettimeout. Ein
  Clientdisconnect beendet die serverseitige Transaktion nicht; ein unbekanntes
  Ergebnis wird ausschließlich anhand der Revision reconciled und niemals als
  Ownership übernommen. CLI-Apply bleibt ohne Killtimeout. Der Smoke restauriert
  nur von `last_owned_snapshot`, beweist einen stale Restore als 409 und prüft
  den weiterhin inaktiven Timer unmittelbar vor und nach allen Writes.
- Timer-Enablement und Timer-Aktivität sind getrennte Phasen. Enablement wird
  bei weiterhin gestopptem Timer restauriert; erst danach wechseln Worktree und
  `main` per Fast-forward stabil auf den Target-SHA. Aktivität ist die letzte
  operationale Phase. Der Software-Commitpoint wird sowohl durch das Flag als
  auch direkt über `refs/heads/main` erkannt: nur exakt der alte SHA erlaubt
  Precommit-Rollback, exakt der Target-SHA wird postcommit erhalten und ein
  dritter oder unlesbarer SHA bleibt `unknown`. Postcommit/unknown stoppt den
  Timer fail-closed und führt keinerlei Datei-, Install- oder Ref-Rücknahme aus.
- Der disposable Step-10-Harness beweist damit die Recoveryreihenfolge,
  bounded/fail-closed Generator- und Lockwartepfade, Lockhaltedauer in Deploy
  und Rollback, present/missing-Installrestore, Verzeichnismodusrestore, alle
  drei Configklassifikationen, das Merge-zu-Flag-Signalfenster, den Third-SHA-
  Pfad sowie `main-target-stable` vor einem Timerstart. Sowohl der vollständige
  Step-9-Block als auch der Harness bestanden `bash -n`; der Harness selbst
  bestand ohne Ausgabe und mit Exit 0.
- Ein additives Execution-Context-Erratum bindet sämtliche lokalen Archiv-
  Datei-/Git-/Buildaktionen in Task 5 und Plattformstate-, Runtime-,
  `systemctl --user`- und `gdbus`-Aktionen in Task 6 an UID/GID `teladi` und die
  richtige Desktop-D-Bus-Instanz. Vor jeder Archivaktion bleibt der
  Fremdbesitz-Nullcheck Pflicht. Root darf nur Remote-`gh` und öffentliche
  read-only HTTPS-Prüfungen ausführen; `safe.directory`, Root-Git und ein
  Archiv-`chown` sind ausdrücklich ausgeschlossen.
- Während dieser Schlussreview-Runde erfolgten kein Fetch, Push, PR-Write,
  Merge, Install, Reload, Deploy, `systemctl`, `gdbus`, Cloudflare-/DNS-Zugriff,
  Cinnamon-Upstream-Fix oder sonstige Laufzeitsystemmutation. Die bekannten
  Tokenmuster kamen in keiner gestagten Addition vor. Der Arbeitsumfang endet
  weiterhin unmittelbar vor Push/Merge/Task-4-Ausführung.
