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
set -Eeuo pipefail
test "$(id -u)" = 0
/usr/sbin/runuser -u teladi -- /usr/bin/env -i \
  HOME=/home/teladi \
  USER=teladi \
  LOGNAME=teladi \
  PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
  LANG=C.UTF-8 \
  LC_ALL=C.UTF-8 \
  /bin/bash -se <<'TASK3_STEP1_TELADI'
set -Eeuo pipefail
test "$(id -u)" = 1000
test "$(id -g)" = 1000
test "$(/usr/bin/git rev-parse --show-toplevel)" = "$(pwd -P)"
generator_dirty="$(/usr/bin/git status --porcelain)"
if [[ -n "$generator_dirty" ]]; then
  printf 'Generator checkout is not clean; aborting local matrix.\n' >&2
  printf '%s\n' "$generator_dirty" >&2
  exit 1
fi
python3 -m unittest discover -s tests/platform -p 'test_*.py' -v
make check
python3 -m compileall -q Sourcecode wirtelprimpf_platform scripts
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
/usr/bin/git diff --check
TASK3_STEP1_TELADI
```

Expected: every command, including both complete profile builds and their validators, exits 0 inside the same clean `teladi` execution context.

- [ ] **Step 2: Perform a fresh spec and security diff review**

Run:

```bash
set -Eeuo pipefail
test "$(id -u)" = 0
/usr/sbin/runuser -u teladi -- /usr/bin/env -i \
  HOME=/home/teladi \
  USER=teladi \
  LOGNAME=teladi \
  PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
  LANG=C.UTF-8 \
  LC_ALL=C.UTF-8 \
  /bin/bash -se <<'TASK3_STEP2_TELADI'
set -Eeuo pipefail
test "$(id -u)" = 1000
test "$(id -g)" = 1000
test "$(/usr/bin/git rev-parse --show-toplevel)" = "$(pwd -P)"
generator_dirty="$(/usr/bin/git status --porcelain)"
if [[ -n "$generator_dirty" ]]; then
  printf 'Generator checkout is not clean; aborting review.\n' >&2
  printf '%s\n' "$generator_dirty" >&2
  exit 1
fi
/usr/bin/git status --short
generator_review_base="$(/usr/bin/git merge-base HEAD origin/main)"
/usr/bin/git log --oneline --decorate "$generator_review_base"..HEAD
/usr/bin/git diff --stat "$generator_review_base"..HEAD
/usr/bin/git diff "$generator_review_base"..HEAD -- \
  Sourcecode/systemd-user/wirtelprimpf-admin.service \
  wirtelprimpf_platform files/wirtelprimfgenerator@H234598 web tests
TASK3_STEP2_TELADI
```

Review every changed hunk against the approved spec. Explicitly verify no response/log path returns secrets, no applet file writer remains, `/api/status` has no network client, and public copy has exactly six changes.

- [ ] **Step 3: Incorporate newly arrived user commits, rerun, and push without force**

Run:

```bash
set -Eeuo pipefail
test "$(id -u)" = 0
set +x
if [[ -z "${GH_TOKEN:-}" ]]; then
  printf 'A valid ephemeral GH_TOKEN is required before the first Git write.\n' >&2
  exit 1
fi
task3_ephemeral_token=$GH_TOKEN
unset GH_TOKEN
exec {task3_token_relay_fd}< <(printf '%s\0' "$task3_ephemeral_token")
unset task3_ephemeral_token

set +e
/usr/sbin/runuser -u teladi -- /usr/bin/env -i \
  HOME=/home/teladi \
  USER=teladi \
  LOGNAME=teladi \
  PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
  LANG=C.UTF-8 \
  LC_ALL=C.UTF-8 \
  /bin/bash -se "$task3_token_relay_fd" <<'TASK3_STEP3_TELADI'
set -Eeuo pipefail
set +x
test "$(id -u)" = 1000
test "$(id -g)" = 1000
test "$(/usr/bin/git rev-parse --show-toplevel)" = "$(pwd -P)"
task3_token_relay_fd=$1
[[ "$task3_token_relay_fd" =~ ^[0-9]+$ ]]
task3_ephemeral_token=
IFS= read -r -d '' task3_ephemeral_token <&"$task3_token_relay_fd"
exec {task3_token_relay_fd}<&-
test -n "$task3_ephemeral_token"
test -z "${GH_TOKEN+x}"

canonical_origin=https://github.com/H234598/Wirtelprimpf-generator.git

# BEGIN TASK3_FD_TOKEN_CALL
task3_token_call() {
  set +x
  local task3_token_status=0
  printf '%s\0' "$task3_ephemeral_token" |
    /usr/bin/env -i \
      HOME=/home/teladi \
      USER=teladi \
      LOGNAME=teladi \
      PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
      GIT_CONFIG_NOSYSTEM=1 \
      GIT_CONFIG_GLOBAL=/dev/null \
      GIT_TERMINAL_PROMPT=0 \
      GIT_ASKPASS=/bin/false \
      SSH_ASKPASS=/bin/false \
      /bin/bash -c '
        set -Eeuo pipefail
        set +x
        task3_call_token=
        IFS= read -r -d "" task3_call_token
        exec 0<&-
        GH_TOKEN="$task3_call_token" exec "$@"
      ' task3-token-call "$@" || task3_token_status=$?
  return "$task3_token_status"
}
# END TASK3_FD_TOKEN_CALL

task3_gh() {
  task3_token_call /usr/bin/gh "$@"
}

# BEGIN TASK3_GIT_CONFIG_GUARD
assert_safe_local_git_config() {
  local repository_path="$1" unsafe_keys
  unsafe_keys="$(
    /usr/bin/git -C "$repository_path" config --local --name-only \
      --get-regexp \
      '^(include\..*|includeif\..*|url\..*\.(insteadof|pushinsteadof)|http\..*|protocol\..*|alias\..*|credential\..*|core\.(askpass|hookspath|sshcommand|gitproxy|fsmonitor)|remote\..*\.(proxy|vcs|receivepack|uploadpack|pushurl))$' \
      || :
  )"
  if [[ -n "$unsafe_keys" ]]; then
    printf 'Unsafe local Git configuration rejected.\n' >&2
    return 1
  fi
}
# END TASK3_GIT_CONFIG_GUARD

# BEGIN TASK3_GIT_REMOTE
git_remote() {
  local operation="${1:-}" argument canonical_url_count=0
  case "$operation" in fetch|ls-remote|push) ;; *) return 1 ;; esac
  for argument in "$@"; do
    [[ "$argument" == "$canonical_origin" ]] && \
      canonical_url_count=$((canonical_url_count + 1))
  done
  test "$canonical_url_count" = 1
  assert_safe_local_git_config .
  task3_token_call \
    /usr/bin/git \
    -c http.extraHeader= \
    -c "http.$canonical_origin.extraHeader=" \
    -c http.proxy= \
    -c http.sslVerify=true \
    -c http.curloptResolve= \
    -c credential.helper= \
    -c 'credential.helper=!/usr/bin/gh auth git-credential' \
    -c core.askPass=/bin/false \
    -c core.hooksPath=/dev/null \
    -c core.fsmonitor=false \
    -c core.sshCommand=/bin/false \
    -c core.gitProxy=/bin/false \
    -c protocol.allow=never \
    -c protocol.https.allow=always \
    -c protocol.ext.allow=never \
    "$@"
}
# END TASK3_GIT_REMOTE

# BEGIN TASK3_IDENTITY_PREDICATES
canonical_repository=H234598/Wirtelprimpf-generator
canonical_repo_id=R_kgDOTpr2BA
task3_actor_login=H234598
task3_actor_id=54270221

assert_task3_actor_json() {
  local actor_json="$1"
  /usr/bin/jq -e \
    --arg login "$task3_actor_login" \
    --argjson actor_id "$task3_actor_id" \
    '.login == $login and .id == $actor_id' \
    <<<"$actor_json" >/dev/null
}

assert_canonical_repository_json() {
  local repository_json="$1"
  /usr/bin/jq -e \
    --arg repository_id "$canonical_repo_id" \
    --arg repository "$canonical_repository" \
    '.id == $repository_id and .nameWithOwner == $repository' \
    <<<"$repository_json" >/dev/null
}
# END TASK3_IDENTITY_PREDICATES

require_task3_auth() {
  local authenticated_user
  authenticated_user="$(task3_gh api "/user")"
  assert_task3_actor_json "$authenticated_user"
}

require_canonical_repository() {
  local canonical_repo_json
  canonical_repo_json="$(
    task3_gh repo view "$canonical_repository" --json id,nameWithOwner
  )"
  assert_canonical_repository_json "$canonical_repo_json"
}

# BEGIN TASK3_FEATURE_BRANCH_PREDICATE
assert_task3_feature_branch() {
  local branch_name="$1"
  test -n "$branch_name"
  /usr/bin/git check-ref-format --branch "$branch_name" >/dev/null
  [[ "$branch_name" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ ]]
  test "$branch_name" != main
}
# END TASK3_FEATURE_BRANCH_PREDICATE

assert_canonical_origin() {
  local -a task3_fetch_urls=() task3_push_urls=()
  mapfile -t task3_fetch_urls < <(/usr/bin/git remote get-url --all origin)
  mapfile -t task3_push_urls < <(/usr/bin/git remote get-url --push --all origin)
  test "${#task3_fetch_urls[@]}" = 1
  test "${#task3_push_urls[@]}" = 1
  test "${task3_fetch_urls[0]}" = "$canonical_origin"
  test "${task3_push_urls[0]}" = "$canonical_origin"
}

# BEGIN TASK3_STEP3_PREWRITE_GATE
generator_head="$(/usr/bin/git branch --show-current)"
assert_task3_feature_branch "$generator_head"
assert_canonical_origin
require_task3_auth
require_canonical_repository
# END TASK3_STEP3_PREWRITE_GATE
git_remote fetch "$canonical_origin" \
  '+refs/heads/main:refs/remotes/origin/main'
if ! /usr/bin/git merge-base --is-ancestor origin/main HEAD; then
  /usr/bin/git log --oneline --decorate HEAD..origin/main
  if ! /usr/bin/git -c core.hooksPath=/dev/null merge --no-edit origin/main; then
    /usr/bin/git -c core.hooksPath=/dev/null merge --abort || true
    printf 'origin/main merge failed or conflicted; review required.\n' >&2
    exit 1
  fi
  test -z "$(/usr/bin/git status --porcelain)"
  # An origin/main integration invalidates every earlier result. The token is a
  # non-exported shell variable, so no test/build/merge-hook process receives it.
  python3 -m unittest discover -s tests/platform -p 'test_*.py' -v
  make check
  python3 -m compileall -q Sourcecode wirtelprimpf_platform scripts
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
  /usr/bin/git diff --check
fi
/usr/bin/git merge-base --is-ancestor origin/main HEAD
test "$(/usr/bin/git branch --show-current)" = "$generator_head"
assert_task3_feature_branch "$generator_head"
assert_canonical_origin
require_task3_auth
require_canonical_repository
git_remote push "$canonical_origin" "HEAD:refs/heads/$generator_head"
unset task3_ephemeral_token
TASK3_STEP3_TELADI
task3_step3_status=$?
set -e
exec {task3_token_relay_fd}<&-
test "$task3_step3_status" = 0
```

Expected: already-published user commits are preserved in branch history, the post-merge matrix is green, and the branch push succeeds without force. Stop for review if the merge reports a conflict or introduces a scope-changing behavior; do not resolve a user conflict by discarding either side.

- [ ] **Step 4: Open the pull request and wait for all checks**

Run:

```bash
set -Eeuo pipefail
test "$(id -u)" = 0
set +x
if [[ -z "${GH_TOKEN:-}" ]]; then
  printf 'A valid ephemeral GH_TOKEN is required before PR writes.\n' >&2
  exit 1
fi
task3_ephemeral_token=$GH_TOKEN
unset GH_TOKEN
exec {task3_token_relay_fd}< <(printf '%s\0' "$task3_ephemeral_token")
unset task3_ephemeral_token

set +e
/usr/sbin/runuser -u teladi -- /usr/bin/env -i \
  HOME=/home/teladi \
  USER=teladi \
  LOGNAME=teladi \
  PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
  LANG=C.UTF-8 \
  LC_ALL=C.UTF-8 \
  /bin/bash -se "$task3_token_relay_fd" <<'TASK3_STEP4_TELADI'
set -Eeuo pipefail
set +x
test "$(id -u)" = 1000
test "$(id -g)" = 1000
test "$(/usr/bin/git rev-parse --show-toplevel)" = "$(pwd -P)"
task3_token_relay_fd=$1
[[ "$task3_token_relay_fd" =~ ^[0-9]+$ ]]
task3_ephemeral_token=
IFS= read -r -d '' task3_ephemeral_token <&"$task3_token_relay_fd"
exec {task3_token_relay_fd}<&-
test -n "$task3_ephemeral_token"
test -z "${GH_TOKEN+x}"

canonical_origin=https://github.com/H234598/Wirtelprimpf-generator.git

# BEGIN TASK3_FD_TOKEN_CALL
task3_token_call() {
  set +x
  local task3_token_status=0
  printf '%s\0' "$task3_ephemeral_token" |
    /usr/bin/env -i \
      HOME=/home/teladi \
      USER=teladi \
      LOGNAME=teladi \
      PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
      GIT_CONFIG_NOSYSTEM=1 \
      GIT_CONFIG_GLOBAL=/dev/null \
      GIT_TERMINAL_PROMPT=0 \
      GIT_ASKPASS=/bin/false \
      SSH_ASKPASS=/bin/false \
      /bin/bash -c '
        set -Eeuo pipefail
        set +x
        task3_call_token=
        IFS= read -r -d "" task3_call_token
        exec 0<&-
        GH_TOKEN="$task3_call_token" exec "$@"
      ' task3-token-call "$@" || task3_token_status=$?
  return "$task3_token_status"
}
# END TASK3_FD_TOKEN_CALL

task3_gh() {
  task3_token_call /usr/bin/gh "$@"
}

# BEGIN TASK3_IDENTITY_PREDICATES
canonical_repository=H234598/Wirtelprimpf-generator
canonical_repo_id=R_kgDOTpr2BA
task3_actor_login=H234598
task3_actor_id=54270221

assert_task3_actor_json() {
  local actor_json="$1"
  /usr/bin/jq -e \
    --arg login "$task3_actor_login" \
    --argjson actor_id "$task3_actor_id" \
    '.login == $login and .id == $actor_id' \
    <<<"$actor_json" >/dev/null
}

assert_canonical_repository_json() {
  local repository_json="$1"
  /usr/bin/jq -e \
    --arg repository_id "$canonical_repo_id" \
    --arg repository "$canonical_repository" \
    '.id == $repository_id and .nameWithOwner == $repository' \
    <<<"$repository_json" >/dev/null
}
# END TASK3_IDENTITY_PREDICATES

require_task3_auth() {
  local authenticated_user
  authenticated_user="$(task3_gh api "/user")"
  assert_task3_actor_json "$authenticated_user"
}

require_canonical_repository() {
  local canonical_repo_json
  canonical_repo_json="$(
    task3_gh repo view "$canonical_repository" --json id,nameWithOwner
  )"
  assert_canonical_repository_json "$canonical_repo_json"
}

assert_canonical_origin() {
  local -a task3_fetch_urls=() task3_push_urls=()
  mapfile -t task3_fetch_urls < <(/usr/bin/git remote get-url --all origin)
  mapfile -t task3_push_urls < <(/usr/bin/git remote get-url --push --all origin)
  test "${#task3_fetch_urls[@]}" = 1
  test "${#task3_push_urls[@]}" = 1
  test "${task3_fetch_urls[0]}" = "$canonical_origin"
  test "${task3_push_urls[0]}" = "$canonical_origin"
}

# BEGIN TASK3_STEP4_IDENTITY_GATE
require_task3_auth
assert_canonical_origin
require_canonical_repository
# END TASK3_STEP4_IDENTITY_GATE
generator_head="$(/usr/bin/git branch --show-current)"
generator_head_sha="$(/usr/bin/git rev-parse HEAD)"
[[ -n "$generator_head" && "$generator_head_sha" =~ ^[0-9a-f]{40}$ ]]
/usr/bin/git check-ref-format --branch "$generator_head" >/dev/null
[[ "$generator_head" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ ]]

pr_is_exact_generator_head() {
  local pr_json="$1"
  /usr/bin/jq -e \
    --arg head "$generator_head" \
    --arg oid "$generator_head_sha" \
    --arg repo_id "$canonical_repo_id" \
    --arg repository "$canonical_repository" '
      .headRefName == $head
      and .headRefOid == $oid
      and .baseRefName == "main"
      and .isDraft == false
      and .isCrossRepository == false
      and .headRepository.id == $repo_id
      and .headRepository.nameWithOwner == $repository
      and .headRepositoryOwner.login == "H234598"
    ' <<<"$pr_json" >/dev/null
}

# PR #4 is the known review surface.  Reuse it only after proving that its
# head/base pair is this exact branch; otherwise search the complete open set
# for the branch before a new PR is even permitted.
known_pr="$({ task3_gh pr view 4 \
  --repo "$canonical_repository" \
  --json number,url,state,headRefName,headRefOid,baseRefName,isDraft,isCrossRepository,headRepository,headRepositoryOwner || true; } 2>/dev/null)"
if [[ -n "$known_pr" \
  && "$(/usr/bin/jq -r '.state' <<<"$known_pr")" == OPEN ]] \
  && pr_is_exact_generator_head "$known_pr"; then
  generator_pr_number=4
  generator_pr_url="$(/usr/bin/jq -r '.url' <<<"$known_pr")"
else
  matching_prs="$(task3_gh pr list \
    --repo "$canonical_repository" \
    --state open --base main --head "H234598:$generator_head" --limit 2 \
    --json number,url,headRefName,headRefOid,baseRefName,isDraft,isCrossRepository,headRepository,headRepositoryOwner)"
  matching_count="$(/usr/bin/jq 'length' <<<"$matching_prs")"
  case "$matching_count" in
    0)
      require_task3_auth
      generator_pr_url="$(task3_gh pr create \
        --repo "$canonical_repository" \
        --base main \
        --head "H234598:$generator_head" \
        --title 'Transactional settings, live sync, status, and approved site copy' \
        --body 'Implements the approved 2026-08-01 design: one transactional configuration core, conflict-safe live web/applet synchronization, real local /api/status, shared model dropdowns, effective systemd timer application, and the six approved public copy changes. Cloudflare and Cinnamon upstream work remain out of scope.')"
      generator_pr_number="${generator_pr_url##*/}"
      ;;
    1)
      generator_pr_number="$(/usr/bin/jq -r '.[0].number' <<<"$matching_prs")"
      generator_pr_url="$(/usr/bin/jq -r '.[0].url' <<<"$matching_prs")"
      ;;
    *)
      printf 'Multiple open PRs use generator head %s; refusing ambiguity.\n' "$generator_head" >&2
      exit 1
      ;;
  esac
fi

[[ "$generator_pr_number" =~ ^[0-9]+$ ]]
verified_pr="$(task3_gh pr view "$generator_pr_number" \
  --repo "$canonical_repository" \
  --json state,headRefName,headRefOid,baseRefName,isDraft,isCrossRepository,headRepository,headRepositoryOwner,url)"
test "$(/usr/bin/jq -r '.state' <<<"$verified_pr")" = OPEN
pr_is_exact_generator_head "$verified_pr"
test "$(/usr/bin/jq -r '.url' <<<"$verified_pr")" = "$generator_pr_url"
task3_gh pr checks "$generator_pr_number" \
  --repo "$canonical_repository" --watch --fail-fast
post_check_pr="$(task3_gh pr view "$generator_pr_number" \
  --repo "$canonical_repository" \
  --json state,headRefName,headRefOid,baseRefName,isDraft,isCrossRepository,headRepository,headRepositoryOwner)"
test "$(/usr/bin/jq -r '.state' <<<"$post_check_pr")" = OPEN
pr_is_exact_generator_head "$post_check_pr"
printf 'Reviewed generator head SHA: %s\n' "$generator_head_sha"
unset task3_ephemeral_token
TASK3_STEP4_TELADI
task3_step4_status=$?
set -e
exec {task3_token_relay_fd}<&-
test "$task3_step4_status" = 0
```

Expected: applet, platform, web, Pages-related checks, and configured review gates are successful. Address actual review findings with new focused test-first commits and rerun the full affected matrix; do not dismiss findings without evidence.

- [ ] **Step 5: Merge through GitHub and record the immutable generator SHA**

Run:

```bash
set -Eeuo pipefail
test "$(id -u)" = 0
set +x
if [[ -z "${GH_TOKEN:-}" ]]; then
  printf 'A valid ephemeral GH_TOKEN is required; no Git or remote write occurred.\n' >&2
  exit 1
fi
task3_ephemeral_token=$GH_TOKEN
unset GH_TOKEN
exec {task3_token_relay_fd}< <(printf '%s\0' "$task3_ephemeral_token")
unset task3_ephemeral_token

set +e
/usr/sbin/runuser -u teladi -- /usr/bin/env -i \
  HOME=/home/teladi \
  USER=teladi \
  LOGNAME=teladi \
  PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
  LANG=C.UTF-8 \
  LC_ALL=C.UTF-8 \
  /bin/bash -se "$task3_token_relay_fd" <<'TASK3_TELADI'
set -Eeuo pipefail
set +x
test "$(id -u)" = 1000
test "$(id -g)" = 1000
test "$(/usr/bin/git rev-parse --show-toplevel)" = "$(pwd -P)"
task3_token_relay_fd=$1
[[ "$task3_token_relay_fd" =~ ^[0-9]+$ ]]
task3_ephemeral_token=
IFS= read -r -d '' task3_ephemeral_token <&"$task3_token_relay_fd"
exec {task3_token_relay_fd}<&-
test -n "$task3_ephemeral_token"
test -z "${GH_TOKEN+x}"

canonical_origin=https://github.com/H234598/Wirtelprimpf-generator.git
receipt_parent=/home/teladi/.local/state/wirtelprimpf
receipt_dir=/home/teladi/.local/state/wirtelprimpf/task3-merge
receipt_file="$receipt_dir/generator-main-receipt.json"
policy_probe=
task3_push_started=0
task3_remote_committed=0
task3_verified=0

# BEGIN TASK3_FD_TOKEN_CALL
task3_token_call() {
  set +x
  local task3_token_status=0
  printf '%s\0' "$task3_ephemeral_token" |
    /usr/bin/env -i \
      HOME=/home/teladi \
      USER=teladi \
      LOGNAME=teladi \
      PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
      GIT_CONFIG_NOSYSTEM=1 \
      GIT_CONFIG_GLOBAL=/dev/null \
      GIT_TERMINAL_PROMPT=0 \
      GIT_ASKPASS=/bin/false \
      SSH_ASKPASS=/bin/false \
      /bin/bash -c '
        set -Eeuo pipefail
        set +x
        task3_call_token=
        IFS= read -r -d "" task3_call_token
        exec 0<&-
        GH_TOKEN="$task3_call_token" exec "$@"
      ' task3-token-call "$@" || task3_token_status=$?
  return "$task3_token_status"
}
# END TASK3_FD_TOKEN_CALL

task3_gh() {
  task3_token_call /usr/bin/gh "$@"
}

# BEGIN TASK3_GIT_CONFIG_GUARD
assert_safe_local_git_config() {
  local repository_path="$1" unsafe_keys
  unsafe_keys="$(
    /usr/bin/git -C "$repository_path" config --local --name-only \
      --get-regexp \
      '^(include\..*|includeif\..*|url\..*\.(insteadof|pushinsteadof)|http\..*|protocol\..*|alias\..*|credential\..*|core\.(askpass|hookspath|sshcommand|gitproxy|fsmonitor)|remote\..*\.(proxy|vcs|receivepack|uploadpack|pushurl))$' \
      || :
  )"
  if [[ -n "$unsafe_keys" ]]; then
    printf 'Unsafe local Git configuration rejected.\n' >&2
    return 1
  fi
}
# END TASK3_GIT_CONFIG_GUARD

# BEGIN TASK3_GIT_REMOTE
git_remote() {
  local operation="${1:-}" argument canonical_url_count=0
  case "$operation" in fetch|ls-remote|push) ;; *) return 1 ;; esac
  for argument in "$@"; do
    [[ "$argument" == "$canonical_origin" ]] && \
      canonical_url_count=$((canonical_url_count + 1))
  done
  test "$canonical_url_count" = 1
  assert_safe_local_git_config .
  task3_token_call \
    /usr/bin/git \
    -c http.extraHeader= \
    -c "http.$canonical_origin.extraHeader=" \
    -c http.proxy= \
    -c http.sslVerify=true \
    -c http.curloptResolve= \
    -c credential.helper= \
    -c 'credential.helper=!/usr/bin/gh auth git-credential' \
    -c core.askPass=/bin/false \
    -c core.hooksPath=/dev/null \
    -c core.fsmonitor=false \
    -c core.sshCommand=/bin/false \
    -c core.gitProxy=/bin/false \
    -c protocol.allow=never \
    -c protocol.https.allow=always \
    -c protocol.ext.allow=never \
    "$@"
}
# END TASK3_GIT_REMOTE

# BEGIN TASK3_CANONICAL_ORIGIN
assert_canonical_origin() {
  local -a task3_fetch_urls=() task3_push_urls=()
  mapfile -t task3_fetch_urls < <(/usr/bin/git remote get-url --all origin)
  mapfile -t task3_push_urls < <(/usr/bin/git remote get-url --push --all origin)
  test "${#task3_fetch_urls[@]}" = 1
  test "${#task3_push_urls[@]}" = 1
  test "${task3_fetch_urls[0]}" = "$canonical_origin"
  test "${task3_push_urls[0]}" = "$canonical_origin"
}
# END TASK3_CANONICAL_ORIGIN

cleanup_policy_probe() {
  if [[ -n "$policy_probe" && -e "$policy_probe" ]]; then
    [[ "$policy_probe" == /tmp/wirtelprimpf-merge-policy.* ]]
    test -d "$policy_probe" && test ! -L "$policy_probe"
    rm -rf -- "$policy_probe"
  fi
  policy_probe=
}

task3_exit() {
  local original_status="$1"
  trap - EXIT
  set +x
  unset task3_ephemeral_token
  set +e
  cleanup_policy_probe
  if [[ "$task3_remote_committed" == 1 && "$task3_verified" != 1 ]]; then
    printf 'REMOTE COMMIT COMPLETE; VERIFICATION PENDING: %s\n' \
      "$receipt_file" >&2
  elif [[ "$task3_push_started" == 1 ]]; then
    printf 'PUSH OUTCOME REQUIRES RECEIPT RECONCILIATION; rerun Step 5, never push manually: %s\n' \
      "$receipt_file" >&2
  fi
  exit "$original_status"
}
trap 'task3_exit $?' EXIT

# BEGIN TASK3_IDENTITY_PREDICATES
canonical_repository=H234598/Wirtelprimpf-generator
canonical_repo_id=R_kgDOTpr2BA
task3_actor_login=H234598
task3_actor_id=54270221

assert_task3_actor_json() {
  local actor_json="$1"
  /usr/bin/jq -e \
    --arg login "$task3_actor_login" \
    --argjson actor_id "$task3_actor_id" \
    '.login == $login and .id == $actor_id' \
    <<<"$actor_json" >/dev/null
}

assert_canonical_repository_json() {
  local repository_json="$1"
  /usr/bin/jq -e \
    --arg repository_id "$canonical_repo_id" \
    --arg repository "$canonical_repository" \
    '.id == $repository_id and .nameWithOwner == $repository' \
    <<<"$repository_json" >/dev/null
}
# END TASK3_IDENTITY_PREDICATES

require_task3_auth() {
  local authenticated_user
  authenticated_user="$(task3_gh api "/user")"
  assert_task3_actor_json "$authenticated_user"
}

require_canonical_repository() {
  local canonical_repo_json
  canonical_repo_json="$(
    task3_gh repo view "$canonical_repository" --json id,nameWithOwner
  )"
  assert_canonical_repository_json "$canonical_repo_json"
}

assert_pr_identity() {
  local pr_json="$1"
  /usr/bin/jq -e \
    --arg head "$generator_head" \
    --arg oid "$generator_expected_head" \
    --arg repo_id "$canonical_repo_id" \
    --arg repository "$canonical_repository" '
      .headRefName == $head
      and .headRefOid == $oid
      and .baseRefName == "main"
      and .isDraft == false
      and .isCrossRepository == false
      and .headRepository.id == $repo_id
      and .headRepository.nameWithOwner == $repository
      and .headRepositoryOwner.login == "H234598"
    ' <<<"$pr_json" >/dev/null
}

# BEGIN TASK3_REVIEW_GATE
fetch_task3_review_overview() {
  task3_gh pr view "$generator_pr_number" \
    --repo "$canonical_repository" \
    --json state,headRefName,headRefOid,baseRefName,isDraft,isCrossRepository,headRepository,headRepositoryOwner,reviewDecision
}

fetch_task3_coderabbit_actor() {
  task3_gh api '/users/coderabbitai%5Bbot%5D'
}

fetch_task3_review_threads_page() {
  local cursor="${1:-}" query
  query='query($owner:String!,$name:String!,$number:Int!,$cursor:String){repository(owner:$owner,name:$name){pullRequest(number:$number){reviewThreads(first:100,after:$cursor){nodes{isResolved}pageInfo{hasNextPage endCursor}}}}}'
  if [[ -n "$cursor" ]]; then
    task3_gh api graphql -f query="$query" \
      -F owner=H234598 -F name=Wirtelprimpf-generator \
      -F number="$generator_pr_number" -f cursor="$cursor" \
      --jq '.data.repository.pullRequest.reviewThreads'
  else
    task3_gh api graphql -f query="$query" \
      -F owner=H234598 -F name=Wirtelprimpf-generator \
      -F number="$generator_pr_number" \
      --jq '.data.repository.pullRequest.reviewThreads'
  fi
}

fetch_task3_reviews_page() {
  local cursor="${1:-}" query
  query='query($owner:String!,$name:String!,$number:Int!,$cursor:String){repository(owner:$owner,name:$name){pullRequest(number:$number){reviews(first:100,after:$cursor){nodes{databaseId state author{login}commit{oid}}pageInfo{hasNextPage endCursor}}}}}'
  if [[ -n "$cursor" ]]; then
    task3_gh api graphql -f query="$query" \
      -F owner=H234598 -F name=Wirtelprimpf-generator \
      -F number="$generator_pr_number" -f cursor="$cursor" \
      --jq '.data.repository.pullRequest.reviews'
  else
    task3_gh api graphql -f query="$query" \
      -F owner=H234598 -F name=Wirtelprimpf-generator \
      -F number="$generator_pr_number" \
      --jq '.data.repository.pullRequest.reviews'
  fi
}

assert_task3_current_review() {
  local required_pr_state="${1:-OPEN}"
  local overview actor page cursor next_cursor has_next
  local review_candidates='[]'
  local -A seen_thread_cursors=() seen_review_cursors=()

  overview="$(fetch_task3_review_overview)"
  assert_pr_identity "$overview"
  /usr/bin/jq -e --arg required_pr_state "$required_pr_state" '
    ($required_pr_state == "OPEN" or $required_pr_state == "MERGED")
    and .state == $required_pr_state
    and .reviewDecision == "APPROVED"
  ' <<<"$overview" >/dev/null

  actor="$(fetch_task3_coderabbit_actor)"
  /usr/bin/jq -e '
    .login == "coderabbitai[bot]"
    and .id == 136622811
  ' <<<"$actor" >/dev/null

  cursor=
  while :; do
    page="$(fetch_task3_review_threads_page "$cursor")"
    /usr/bin/jq -e '
      type == "object"
      and (.nodes | type == "array")
      and (.pageInfo | type == "object")
      and (.pageInfo.hasNextPage | type == "boolean")
      and (.pageInfo.endCursor == null or (.pageInfo.endCursor | type == "string"))
      and all(.nodes[]; type == "object" and (.isResolved | type == "boolean"))
      and all(.nodes[]; .isResolved == true)
    ' <<<"$page" >/dev/null
    has_next="$(/usr/bin/jq -r '.pageInfo.hasNextPage' <<<"$page")"
    [[ "$has_next" == true || "$has_next" == false ]]
    [[ "$has_next" == true ]] || break
    next_cursor="$(/usr/bin/jq -r '.pageInfo.endCursor // empty' <<<"$page")"
    test -n "$next_cursor"
    test "$next_cursor" != "$cursor"
    [[ -z "${seen_thread_cursors[$next_cursor]+x}" ]]
    seen_thread_cursors[$next_cursor]=1
    cursor=$next_cursor
  done

  cursor=
  while :; do
    page="$(fetch_task3_reviews_page "$cursor")"
    /usr/bin/jq -e '
      type == "object"
      and (.nodes | type == "array")
      and (.pageInfo | type == "object")
      and (.pageInfo.hasNextPage | type == "boolean")
      and (.pageInfo.endCursor == null or (.pageInfo.endCursor | type == "string"))
      and all(.nodes[];
        type == "object"
        and (.databaseId | type == "number" and . > 0 and floor == .)
        and (.state | type == "string")
        and (.author.login | type == "string")
        and (.commit.oid | type == "string" and test("^[0-9a-f]{40}$"))
      )
    ' <<<"$page" >/dev/null
    review_candidates="$(
      /usr/bin/jq -cn \
        --argjson prior "$review_candidates" \
        --argjson current "$(
          /usr/bin/jq -c --arg expected_head "$generator_expected_head" '
            [.nodes[] | select(
              .state == "APPROVED"
              and .author.login == "coderabbitai[bot]"
              and .commit.oid == $expected_head
            )]
          ' <<<"$page"
        )" \
        '$prior + $current'
    )"
    has_next="$(/usr/bin/jq -r '.pageInfo.hasNextPage' <<<"$page")"
    [[ "$has_next" == true || "$has_next" == false ]]
    [[ "$has_next" == true ]] || break
    next_cursor="$(/usr/bin/jq -r '.pageInfo.endCursor // empty' <<<"$page")"
    test -n "$next_cursor"
    test "$next_cursor" != "$cursor"
    [[ -z "${seen_review_cursors[$next_cursor]+x}" ]]
    seen_review_cursors[$next_cursor]=1
    cursor=$next_cursor
  done

  test "$(/usr/bin/jq 'length' <<<"$review_candidates")" = 1
  generator_review_id="$(/usr/bin/jq -r '.[0].databaseId' <<<"$review_candidates")"
  generator_review_author_login="$(/usr/bin/jq -r '.[0].author.login' <<<"$review_candidates")"
  generator_review_author_id="$(/usr/bin/jq -r '.id' <<<"$actor")"
  generator_review_commit="$(/usr/bin/jq -r '.[0].commit.oid' <<<"$review_candidates")"
  generator_review_state="$(/usr/bin/jq -r '.[0].state' <<<"$review_candidates")"
  [[ "$generator_review_id" =~ ^[1-9][0-9]*$ ]]
  test "$generator_review_author_login" = 'coderabbitai[bot]'
  test "$generator_review_author_id" = 136622811
  test "$generator_review_commit" = "$generator_expected_head"
  test "$generator_review_state" = APPROVED
}
# END TASK3_REVIEW_GATE

assert_no_main_policy() {
  local classic_call_status
  require_task3_auth
  cleanup_policy_probe
  policy_probe="$(mktemp -d /tmp/wirtelprimpf-merge-policy.XXXXXX)"
  [[ "$policy_probe" == /tmp/wirtelprimpf-merge-policy.* ]]
  test -d "$policy_probe" && test ! -L "$policy_probe"
  chmod 0700 "$policy_probe"

  task3_gh api \
    "repos/$canonical_repository/rules/branches/main" \
    >"$policy_probe/rulesets.json"
  /usr/bin/jq -e 'type == "array" and length == 0' \
    "$policy_probe/rulesets.json" >/dev/null || {
      printf 'Any applied main rule forbids this direct exact-lease path.\n' >&2
      exit 1
    }

  set +e
  task3_gh api --include \
    "repos/$canonical_repository/branches/main/protection" \
    >"$policy_probe/branch_protection.response" \
    2>"$policy_probe/branch_protection.error"
  classic_call_status=$?
  set -e
  classic_protection_status="$(
    awk '/^HTTP\/[^ ]+ [0-9][0-9][0-9]/{code=$2} END{print code}' \
      "$policy_probe/branch_protection.response"
  )"
  if [[ -z "$classic_protection_status" ]]; then
    classic_protection_status="$(
      sed -n 's/.*(HTTP \([0-9][0-9][0-9]\))$/\1/p' \
        "$policy_probe/branch_protection.error" | tail -n1
    )"
  fi
  test "$classic_call_status" -ne 0
  test "$classic_protection_status" = 404 || {
    printf 'Classic main protection was not an authenticated exact 404.\n' >&2
    exit 1
  }
  cleanup_policy_probe
}

# BEGIN TASK3_RECEIPT_IO
ensure_receipt_dir() {
  test -d "$receipt_parent" && test ! -L "$receipt_parent"
  test "$(realpath -e -- "$receipt_parent")" = "$receipt_parent"
  test "$(stat -c '%u:%g:%a' "$receipt_parent")" = 1000:1000:700
  if [[ -e "$receipt_dir" ]]; then
    test -d "$receipt_dir" && test ! -L "$receipt_dir"
  else
    install -d -m0700 "$receipt_dir"
  fi
  test "$(realpath -e -- "$receipt_dir")" = "$receipt_dir"
  test "$(stat -c '%u:%g:%a' "$receipt_dir")" = 1000:1000:700
}

write_task3_receipt() (
  set -Eeuo pipefail
  local next_state="$1" receipt_tmp= original_status

  cleanup_receipt_tmp() {
    original_status=$?
    trap - EXIT
    if [[ -n "$receipt_tmp" && -e "$receipt_tmp" ]]; then
      [[ "$receipt_tmp" == "$receipt_dir"/.generator-main-receipt.* ]]
      test -f "$receipt_tmp" && test ! -L "$receipt_tmp"
      rm -f -- "$receipt_tmp"
    fi
    exit "$original_status"
  }
  trap cleanup_receipt_tmp EXIT

  case "$receipt_state:$next_state" in
    absent:planned|planned:remote_committed|remote_committed:verified) ;;
    *) return 1 ;;
  esac
  ensure_receipt_dir
  receipt_tmp="$(mktemp "$receipt_dir/.generator-main-receipt.XXXXXX")"
  [[ "$receipt_tmp" == "$receipt_dir"/.generator-main-receipt.* ]]
  test -f "$receipt_tmp" && test ! -L "$receipt_tmp"
  chmod 0600 "$receipt_tmp"
  /usr/bin/jq -n \
    --arg state "$next_state" \
    --arg actor_login "$task3_actor_login" \
    --argjson actor_id "$task3_actor_id" \
    --arg repository_id "$canonical_repo_id" \
    --arg repository "$canonical_repository" \
    --arg canonical_origin "$canonical_origin" \
    --argjson pr_number "$generator_pr_number" \
    --arg head_ref "$generator_head" \
    --arg expected_head "$generator_expected_head" \
    --arg base_before "$generator_base_before" \
    --arg head_tree "$generator_head_tree" \
    --arg merge_date "$generator_merge_date" \
    --arg merge_message "$generator_merge_message" \
    --arg merge_sha "$generator_merge_sha" \
    --argjson review_id "$generator_review_id" \
    --arg review_author_login "$generator_review_author_login" \
    --argjson review_author_id "$generator_review_author_id" \
    --arg review_commit "$generator_review_commit" \
    --arg review_state "$generator_review_state" \
    '{
      version: 3,
      state: $state,
      actor_login: $actor_login,
      actor_id: $actor_id,
      repository_id: $repository_id,
      repository: $repository,
      canonical_origin: $canonical_origin,
      pr_number: $pr_number,
      head_ref: $head_ref,
      expected_head: $expected_head,
      base_before: $base_before,
      head_tree: $head_tree,
      merge_date: $merge_date,
      merge_message: $merge_message,
      merge_sha: $merge_sha,
      review_id: $review_id,
      review_author_login: $review_author_login,
      review_author_id: $review_author_id,
      review_commit: $review_commit,
      review_state: $review_state
  }' >"$receipt_tmp"
  chmod 0600 "$receipt_tmp"
  sync -f "$receipt_tmp"
  mv -fT -- "$receipt_tmp" "$receipt_file"
  receipt_tmp=
  sync -f "$receipt_dir"
  test -f "$receipt_file" && test ! -L "$receipt_file"
  test "$(stat -c '%u:%g:%a' "$receipt_file")" = 1000:1000:600
)
# END TASK3_RECEIPT_IO

# BEGIN TASK3_DERIVE_MERGE
derive_task3_merge() {
  [[ "$generator_pr_number" =~ ^[0-9]+$ ]]
  [[ "$generator_expected_head" =~ ^[0-9a-f]{40}$ ]]
  [[ "$generator_base_before" =~ ^[0-9a-f]{40}$ ]]
  /usr/bin/git cat-file -e "$generator_expected_head^{commit}"
  /usr/bin/git cat-file -e "$generator_base_before^{commit}"
  /usr/bin/git merge-base --is-ancestor \
    "$generator_base_before" "$generator_expected_head"
  generator_head_tree="$(
    /usr/bin/git rev-parse "$generator_expected_head^{tree}"
  )"
  [[ "$generator_head_tree" =~ ^[0-9a-f]{40}$ ]]
  generator_merge_date="$(
    /usr/bin/git show -s --format=%cI "$generator_expected_head"
  )"
  test -n "$generator_merge_date"
  generator_merge_message="Merge pull request #${generator_pr_number} from ${generator_head}"
  generator_merge_sha="$(
    printf '%s\n' "$generator_merge_message" |
      GIT_AUTHOR_NAME=H234598 \
      GIT_AUTHOR_EMAIL=54270221+H234598@users.noreply.github.com \
      GIT_AUTHOR_DATE="$generator_merge_date" \
      GIT_COMMITTER_NAME=H234598 \
      GIT_COMMITTER_EMAIL=54270221+H234598@users.noreply.github.com \
      GIT_COMMITTER_DATE="$generator_merge_date" \
      /usr/bin/git -c core.hooksPath=/dev/null \
        commit-tree "$generator_head_tree" \
        -p "$generator_base_before" -p "$generator_expected_head"
  )"
  [[ "$generator_merge_sha" =~ ^[0-9a-f]{40}$ ]]
  test "$(/usr/bin/git rev-parse "$generator_merge_sha^{tree}")" = \
    "$generator_head_tree"
  test "$(/usr/bin/git rev-list --parents -n1 "$generator_merge_sha")" = \
    "$generator_merge_sha $generator_base_before $generator_expected_head"
}
# END TASK3_DERIVE_MERGE

# BEGIN TASK3_VALIDATE_RECEIPT
load_task3_receipt() {
  /usr/bin/jq -e \
    --arg actor_login "$task3_actor_login" \
    --argjson actor_id "$task3_actor_id" \
    --arg repository_id "$canonical_repo_id" \
    --arg repository "$canonical_repository" \
    --arg canonical_origin "$canonical_origin" \
    --arg head_ref "$generator_head" \
    --arg expected_head "$generator_expected_head" '
      keys == [
        "actor_id", "actor_login", "base_before", "canonical_origin",
        "expected_head", "head_ref", "head_tree", "merge_date",
        "merge_message", "merge_sha", "pr_number", "repository",
        "repository_id", "review_author_id", "review_author_login",
        "review_commit", "review_id", "review_state", "state", "version"
      ]
      and .version == 3
      and (.state == "planned" or .state == "remote_committed" or .state == "verified")
      and .actor_login == $actor_login
      and .actor_id == $actor_id
      and .repository_id == $repository_id
      and .repository == $repository
      and .canonical_origin == $canonical_origin
      and .head_ref == $head_ref
      and .expected_head == $expected_head
      and (.pr_number | type == "number" and . > 0 and floor == .)
      and (.base_before | type == "string" and test("^[0-9a-f]{40}$"))
      and (.head_tree | type == "string" and test("^[0-9a-f]{40}$"))
      and (.merge_date | type == "string" and length > 0)
      and (.merge_message | type == "string" and length > 0)
      and (.merge_sha | type == "string" and test("^[0-9a-f]{40}$"))
      and (.review_id | type == "number" and . > 0 and floor == .)
      and .review_author_login == "coderabbitai[bot]"
      and .review_author_id == 136622811
      and .review_commit == $expected_head
      and .review_state == "APPROVED"
    ' "$receipt_file" >/dev/null
  receipt_state="$(/usr/bin/jq -r '.state' "$receipt_file")"
  receipt_pr_number="$(/usr/bin/jq -r '.pr_number' "$receipt_file")"
  receipt_base_before="$(/usr/bin/jq -r '.base_before' "$receipt_file")"
  receipt_head_tree="$(/usr/bin/jq -r '.head_tree' "$receipt_file")"
  receipt_merge_date="$(/usr/bin/jq -r '.merge_date' "$receipt_file")"
  receipt_merge_message="$(/usr/bin/jq -r '.merge_message' "$receipt_file")"
  receipt_merge_sha="$(/usr/bin/jq -r '.merge_sha' "$receipt_file")"
  receipt_review_id="$(/usr/bin/jq -r '.review_id' "$receipt_file")"
  receipt_review_author_login="$(/usr/bin/jq -r '.review_author_login' "$receipt_file")"
  receipt_review_author_id="$(/usr/bin/jq -r '.review_author_id' "$receipt_file")"
  receipt_review_commit="$(/usr/bin/jq -r '.review_commit' "$receipt_file")"
  receipt_review_state="$(/usr/bin/jq -r '.review_state' "$receipt_file")"
}

validate_task3_receipt_derivation() {
  test "$receipt_pr_number" = "$generator_pr_number"
  test "$receipt_base_before" = "$generator_base_before"
  test "$receipt_head_tree" = "$generator_head_tree"
  test "$receipt_merge_date" = "$generator_merge_date"
  test "$receipt_merge_message" = "$generator_merge_message"
  test "$receipt_merge_sha" = "$generator_merge_sha"
  test "$receipt_review_id" = "$generator_review_id"
  test "$receipt_review_author_login" = "$generator_review_author_login"
  test "$receipt_review_author_id" = "$generator_review_author_id"
  test "$receipt_review_commit" = "$generator_review_commit"
  test "$receipt_review_state" = "$generator_review_state"
}
# END TASK3_VALIDATE_RECEIPT

# BEGIN TASK3_REMOTE_STATE
classify_task3_remote_action() {
  local state="$1" remote_main="$2" remote_head="$3"
  local base_before="$4" merge_sha="$5" expected_head="$6"
  if [[ "$state" == planned \
    && "$remote_main" == "$base_before" \
    && "$remote_head" == "$expected_head" ]]; then
    printf 'push\n'
  elif [[ "$state" == planned \
    && "$remote_main" == "$merge_sha" \
    && -z "$remote_head" ]]; then
    printf 'reconcile\n'
  elif [[ ( "$state" == remote_committed || "$state" == verified ) \
    && "$remote_main" == "$merge_sha" \
    && -z "$remote_head" ]]; then
    printf 'observe\n'
  else
    return 1
  fi
}
# END TASK3_REMOTE_STATE

# BEGIN TASK3_STEP5_IDENTITY_GATE
require_task3_auth
require_canonical_repository
generator_head="$(/usr/bin/git branch --show-current)"
test -n "$generator_head"
/usr/bin/git check-ref-format --branch "$generator_head" >/dev/null
[[ "$generator_head" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ ]]
test "$generator_head" != main
generator_expected_head="$(/usr/bin/git rev-parse HEAD)"
[[ "$generator_expected_head" =~ ^[0-9a-f]{40}$ ]]
assert_canonical_origin
# END TASK3_STEP5_IDENTITY_GATE

receipt_state=absent
if [[ -e "$receipt_file" ]]; then
  test -d "$receipt_dir" && test ! -L "$receipt_dir"
  test "$(realpath -e -- "$receipt_dir")" = "$receipt_dir"
  test "$(stat -c '%u:%g:%a' "$receipt_dir")" = 1000:1000:700
  test -f "$receipt_file" && test ! -L "$receipt_file"
  test "$(stat -c '%u:%g:%a' "$receipt_file")" = 1000:1000:600
  load_task3_receipt
  generator_pr_number=$receipt_pr_number
  generator_base_before=$receipt_base_before
else
  generator_pr_number="$(
    task3_gh pr view \
      --repo "$canonical_repository" --json number --jq .number
  )"
fi
[[ "$generator_pr_number" =~ ^[0-9]+$ ]]

generator_merge_gate="$(
  task3_gh pr view "$generator_pr_number" \
    --repo "$canonical_repository" \
    --json state,headRefName,headRefOid,baseRefName,isDraft,isCrossRepository,headRepository,headRepositoryOwner,mergeCommit
)"
assert_pr_identity "$generator_merge_gate"
generator_pr_state="$(/usr/bin/jq -r '.state' <<<"$generator_merge_gate")"

if [[ "$receipt_state" == absent ]]; then
  test "$generator_pr_state" = OPEN
  generator_base_before="$(
    git_remote ls-remote "$canonical_origin" refs/heads/main | cut -f1
  )"
  [[ "$generator_base_before" =~ ^[0-9a-f]{40}$ ]]
  test "$generator_base_before" = "$(/usr/bin/git rev-parse origin/main)"
  test "$(git_remote ls-remote "$canonical_origin" "refs/heads/$generator_head" | cut -f1)" = \
    "$generator_expected_head"
  /usr/bin/git merge-base --is-ancestor \
    "$generator_base_before" "$generator_expected_head"

  task3_gh pr checks "$generator_pr_number" \
    --repo "$canonical_repository" --watch --fail-fast
  generator_post_checks_gate="$(
    task3_gh pr view "$generator_pr_number" \
      --repo "$canonical_repository" \
      --json state,headRefName,headRefOid,baseRefName,isDraft,isCrossRepository,headRepository,headRepositoryOwner,mergeCommit
  )"
  assert_pr_identity "$generator_post_checks_gate"
  test "$(/usr/bin/jq -r '.state' <<<"$generator_post_checks_gate")" = OPEN
  test "$(git_remote ls-remote "$canonical_origin" refs/heads/main | cut -f1)" = \
    "$generator_base_before"
  test "$(git_remote ls-remote "$canonical_origin" "refs/heads/$generator_head" | cut -f1)" = \
    "$generator_expected_head"

  # Every nonempty applied-rule array and every classic-protection result other
  # than an authenticated exact 404 stops before commit-tree creates an object.
  assert_no_main_policy
  require_task3_auth
  assert_task3_current_review
  derive_task3_merge
  write_task3_receipt planned
  load_task3_receipt
  validate_task3_receipt_derivation
else
  case "$generator_pr_state" in OPEN|MERGED) ;; *) exit 1 ;; esac
  # Never trust content-derived fields from a persisted receipt. Reconstruct the
  # reviewed tree and deterministic merge from current trusted Git/PR inputs on
  # every retry, then compare every derived receipt field before remote reads.
  assert_task3_current_review "$generator_pr_state"
  derive_task3_merge
  validate_task3_receipt_derivation
fi

remote_main_sha="$(git_remote ls-remote "$canonical_origin" refs/heads/main | cut -f1)"
remote_head_sha="$(git_remote ls-remote "$canonical_origin" "refs/heads/$generator_head" | cut -f1)"
if ! task3_remote_action="$(classify_task3_remote_action \
  "$receipt_state" "$remote_main_sha" "$remote_head_sha" \
  "$generator_base_before" "$generator_merge_sha" \
  "$generator_expected_head")"; then
  printf 'Unknown receipt/remote ref combination; refusing mutation.\n' >&2
  exit 1
fi
case "$task3_remote_action" in
  push)
    test "$generator_pr_state" = OPEN
    task3_gh pr checks "$generator_pr_number" \
      --repo "$canonical_repository" --watch --fail-fast
    generator_pre_push_gate="$(
      task3_gh pr view "$generator_pr_number" \
        --repo "$canonical_repository" \
        --json state,headRefName,headRefOid,baseRefName,isDraft,isCrossRepository,headRepository,headRepositoryOwner,mergeCommit
    )"
    assert_pr_identity "$generator_pre_push_gate"
    test "$(/usr/bin/jq -r '.state' <<<"$generator_pre_push_gate")" = OPEN
    assert_no_main_policy
    test "$(git_remote ls-remote "$canonical_origin" refs/heads/main | cut -f1)" = \
      "$generator_base_before"
    test "$(git_remote ls-remote "$canonical_origin" "refs/heads/$generator_head" | cut -f1)" = \
      "$generator_expected_head"
    require_task3_auth
    assert_task3_current_review
    validate_task3_receipt_derivation
    task3_push_started=1
    git_remote push --atomic \
      --force-with-lease=refs/heads/main:$generator_base_before \
      --force-with-lease=refs/heads/$generator_head:$generator_expected_head \
      "$canonical_origin" \
      "$generator_merge_sha:refs/heads/main" \
      ":refs/heads/$generator_head"
    task3_remote_committed=1
    write_task3_receipt remote_committed
    receipt_state=remote_committed
    ;;
  reconcile)
    case "$generator_pr_state" in OPEN|MERGED) ;; *) exit 1 ;; esac
    task3_remote_committed=1
    write_task3_receipt remote_committed
    receipt_state=remote_committed
    printf 'planned_remote_committed state reconciled without another push.\n'
    ;;
  observe)
    task3_remote_committed=1
    ;;
  *) exit 1 ;;
esac

# The push is the remote commit point. Every following failure is explicitly a
# committed/pending observation failure and a rerun starts from the receipt,
# never from the push branch above.
test "$(git_remote ls-remote "$canonical_origin" refs/heads/main | cut -f1)" = \
  "$generator_merge_sha"
test -z "$(git_remote ls-remote "$canonical_origin" "refs/heads/$generator_head")"

merge_observation_deadline=$((SECONDS + 60))
merged_pr=
while :; do
  set +e
  merged_pr="$(
    task3_gh pr view "$generator_pr_number" \
      --repo "$canonical_repository" \
      --json state,headRefName,headRefOid,baseRefName,isDraft,isCrossRepository,headRepository,headRepositoryOwner,mergeCommit
  )"
  pr_observation_status=$?
  set -e
  if [[ "$pr_observation_status" == 0 \
    && "$(/usr/bin/jq -r '.state' <<<"$merged_pr")" == MERGED ]]; then
    break
  fi
  (( SECONDS < merge_observation_deadline )) || {
    printf 'GitHub merge observation is pending; do not repeat the push.\n' >&2
    exit 1
  }
  sleep 1
done
assert_pr_identity "$merged_pr"
test "$(/usr/bin/jq -r '.mergeCommit.oid' <<<"$merged_pr")" = \
  "$generator_merge_sha"
generator_merge_object="$(
  task3_gh api \
    "repos/$canonical_repository/git/commits/$generator_merge_sha"
)"
test "$(/usr/bin/jq -r '.tree.sha' <<<"$generator_merge_object")" = \
  "$generator_head_tree"
test "$(/usr/bin/jq '.parents | length' <<<"$generator_merge_object")" = 2
test "$(/usr/bin/jq -r '.parents[0].sha' <<<"$generator_merge_object")" = \
  "$generator_base_before"
test "$(/usr/bin/jq -r '.parents[1].sha' <<<"$generator_merge_object")" = \
  "$generator_expected_head"
if [[ "$receipt_state" != verified ]]; then
  write_task3_receipt verified
  receipt_state=verified
fi
task3_verified=1
printf 'Merged generator SHA for Task 4/5: %s\n' "$generator_merge_sha"
TASK3_TELADI
task3_status=$?
set -e
exec {task3_token_relay_fd}<&-
test "$task3_status" = 0
```

Expected: GitHub main contains the deterministic two-parent merge after one atomic exact-base/exact-head lease CAS, the reviewed PR head branch is deleted in that same atomic update, and the printed 40-character SHA is recorded as the only factory reference permitted in Tasks 4–5. GitHub reports the same object as the PR's indirect merge; see the official [indirect merges contract](https://docs.github.com/en/pull-requests/reference/pull-request-merges?apiVersion=2022-11-28#indirect-merges). The applied-rules response must be exactly `[]`, and classic protection must be an authenticated exact HTTP 404; every nonempty array, HTTP 200, unclassified response or API failure stops the remote mutation. The PR head name, OID, same-repository bit, owner, repository ID and `nameWithOwner` agree exactly. Every fetch-/push-URL value is enumerated with `--all`; each set has cardinality one and equals canonical HTTPS. Every subsequent fetch, `ls-remote`, and push uses that URL literal, never the mutable remote name. No protection is bypassed or weakened.

Both persisted `gh` authentication contexts were invalid at the last local preflight; successful unauthenticated public reads are not write authorization. Steps 3–5 therefore require an externally supplied ephemeral `GH_TOKEN`, immediately disable xtrace before its first reference, unset its exported source, and relay its bytes only through private anonymous descriptors into a clean UID/GID-`teladi` shell. That long-lived shell retains only a non-exported variable and closes the relay descriptor immediately. Each `gh` or authenticated Git process receives the token through a fresh short-lived pipe; it never appears in argv, here-doc text, files, tests/builds, or merge hooks. `/user` must equal login `H234598` and numeric ID `54270221`. Authenticated Git clears credential helpers, installs only `gh auth git-credential`, disables hooks with `core.hooksPath=/dev/null`, and receives no persistent credential setup.

The private atomic v3 receipt at `/home/teladi/.local/state/wirtelprimpf/task3-merge/generator-main-receipt.json` supersedes the earlier v2 contract. It is owned by `teladi`, mode `0600`, uses an exact no-extra-field schema, and binds actor login/ID, repository ID/name, canonical URL, PR/ref/head/base, the reviewed head tree, deterministic date/message, merge OID, and the exact trusted review ID/author/commit/state. Every run derives `expected_head^{tree}` from trusted Git state and reconstructs the deterministic commit from fixed identity plus trusted PR/head/base inputs before accepting receipt-derived values. Malformed, extra-field, stale, or forged receipts fail closed; failed atomic replacements remove their private temporary file. The state machine advances only `planned -> remote_committed -> verified`. A successful push is latched before any fallible observation; a push/receipt crash reconciles from the exact remote ref pair, while committed states classify only as `reconcile` or `observe` and can never re-enter `push`. API convergence failures report `REMOTE COMMIT COMPLETE; VERIFICATION PENDING`; every unknown combination fails closed. The runtime checkout remains untouched until Task 4.

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

##### Additive, vorrangige Klarstellung zur Runtime-Grenze

Die oben historisch erhaltene Formulierung zu einer Aktualisierung des
Runtime-Checkouts in Task 3 Step 5 ist **keine** Aktualisierungsfreigabe. Diese
Klarstellung ist für die Ausführung vorrangig: **Task 3 verändert den Runtime-Checkout nicht**.
Insbesondere laufen dort weder `fetch`, `pull`,
`switch`, `update-ref` noch ein anderer Git-Schreibvorgang gegen
`/home/teladi/.local/share/wirtelprimpf-generator`.

Root darf unmittelbar vor Task 4 ausschließlich das nachfolgende eng begrenzte
Ownership-Gate ausführen. Dieses Gate ändert keine Git-Referenz und liest weder
Remote- noch Arbeitsbaumdaten über Git. Beim Eintritt in den normativen
Task-4-Step-9-Rahmen bleibt `HEAD` der aufgezeichnete alte Runtime-SHA und muss
vom `target_sha` verschieden sein. Erst nach dem Task-4-CAS und allen davor
liegenden Backup-, Maskierungs-, Installations- und Smoke-Gates dürfen Runtime
`HEAD`, `refs/heads/main` und das bereits in Task 4 gefetchte `origin/main` dem
Ziel-SHA entsprechen. Jede frühere Gleichheit ist ein harter Abbruchgrund.

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
  --noproxy '*' --connect-timeout 2 --max-time 10 \
  --dump-header "$smoke_dir/settings.headers" \
  --output "$smoke_dir/settings.json" \
  http://127.0.0.1:8765/api/settings
curl --fail --silent --show-error \
  --noproxy '*' --connect-timeout 2 --max-time 10 \
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
curl --fail --silent --show-error \
  --noproxy '*' --connect-timeout 2 --max-time 10 \
  http://127.0.0.1:8765/api/status | python -m json.tool >/dev/null
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
git_runtime_fetch_bounded() {
  assert_runtime_owned
  timeout --foreground --signal=TERM --kill-after=10s 180s \
    git -c http.lowSpeedLimit=1024 -c http.lowSpeedTime=30 \
    -C "$runtime" fetch origin main
}

command -v timeout >/dev/null
test -z "$(git_runtime status --porcelain)"
runtime_branch_before="$(git_runtime branch --show-current)"
runtime_sha_before="$(git_runtime rev-parse HEAD)"
test "$runtime_branch_before" = main
[[ "$runtime_sha_before" =~ ^[0-9a-f]{40}$ ]]
test "$runtime_sha_before" != "$target_sha"

timer_enabled_before="$(systemctl --user is-enabled wirtelprimpf.timer || true)"
timer_active_before="$(systemctl --user is-active wirtelprimpf.timer || true)"
admin_active_before="$(systemctl --user is-active wirtelprimpf-admin.service || true)"
service_unit_state_before="$(systemctl --user is-enabled wirtelprimpf.service || true)"
service_load_state_before="$(systemctl --user show wirtelprimpf.service \
  -p LoadState --value)"
case "$timer_enabled_before" in enabled|enabled-runtime|disabled) ;; *) exit 1 ;; esac
case "$timer_active_before" in active|inactive) ;; *) exit 1 ;; esac
case "$admin_active_before" in active|inactive) ;; *) exit 1 ;; esac
test "$service_unit_state_before" = static
test "$service_load_state_before" = loaded
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
printf '%s\n' "$service_unit_state_before" >"$deploy_backup/service-unit-state-before"
printf '%s\n' "$service_load_state_before" >"$deploy_backup/service-load-state-before"
chmod 0600 "$deploy_backup"/*-before "$deploy_backup/target-sha"

backup_complete=0
software_commit_complete=0
deployment_complete=0
runtime_service_masked=0
runtime_timer_masked=0

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
settings_lock_is_safe() {
  local lock_path=/home/teladi/.config/wirtelprimpf/settings.lock candidate
  for candidate in \
    /home/teladi/.config/wirtelprimpf \
    /home/teladi/.config \
    /home/teladi \
    /home \
    /; do
    test ! -L "$candidate"
    test -d "$candidate"
  done
  test ! -L "$lock_path"
  [[ ! -e "$lock_path" || -f "$lock_path" ]]
}
acquire_settings_lock() {
  local lock_path=/home/teladi/.config/wirtelprimpf/settings.lock
  [[ "$settings_lock_held" == 0 ]] || return 0
  settings_lock_is_safe
  exec {settings_lock_fd}<>"$lock_path"
  test -f "/proc/$$/fd/$settings_lock_fd"
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
  settings_lock_is_safe
  exec {settings_lock_fd}<>"$lock_path"
  test -f "/proc/$$/fd/$settings_lock_fd"
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

wait_generator_inactive() {
  local deadline
  deadline=$((SECONDS + 300))
  while [[ "$(systemctl --user show wirtelprimpf.service \
    -p ActiveState --value)" != inactive ]]; do
    (( SECONDS < deadline )) || return 1
    sleep 1
  done
  test "$(systemctl --user show wirtelprimpf.service \
    -p ActiveState --value)" = inactive
}

mask_generator_runtime() {
  local current
  current="$(systemctl --user is-enabled wirtelprimpf.service || true)"
  if [[ "$current" != masked-runtime ]]; then
    test "$current" = static
    systemctl --user mask --runtime wirtelprimpf.service || return 1
  fi
  test "$(systemctl --user is-enabled wirtelprimpf.service || true)" = masked-runtime
  runtime_service_masked=1
}

quiesce_generator() {
  systemctl --user stop wirtelprimpf.timer || return 1
  # Waiting once before the mask lets an already-running oneshot finish
  # naturally. The runtime mask then closes every new activation path; the
  # second wait closes the narrow inactive-to-mask race before code mutation.
  wait_generator_inactive || return 1
  mask_generator_runtime || return 1
  wait_generator_inactive
}

mask_timer_runtime_stopped() {
  systemctl --user stop wirtelprimpf.timer || return 1
  systemctl --user mask --runtime wirtelprimpf.timer || return 1
  test "$(systemctl --user is-enabled wirtelprimpf.timer || true)" = masked-runtime
  test "$(systemctl --user is-active wirtelprimpf.timer || true)" = inactive
  runtime_timer_masked=1
}

unmask_timer_runtime_stopped() {
  [[ "$runtime_timer_masked" == 1 ]] || return 1
  systemctl --user unmask --runtime wirtelprimpf.timer || return 1
  runtime_timer_masked=0
  test "$(systemctl --user is-enabled wirtelprimpf.timer || true)" = "$timer_enabled_before"
  test "$(systemctl --user is-active wirtelprimpf.timer || true)" = inactive
}

unmask_generator_runtime() {
  [[ "$runtime_service_masked" == 1 ]] || return 1
  systemctl --user unmask --runtime wirtelprimpf.service || return 1
  runtime_service_masked=0
  systemctl --user daemon-reload || return 1
  test "$(systemctl --user is-enabled wirtelprimpf.service || true)" = \
    "$service_unit_state_before"
  test "$(systemctl --user show wirtelprimpf.service -p LoadState --value)" = \
    "$service_load_state_before"
  test "$(systemctl --user show wirtelprimpf.service -p ActiveState --value)" = inactive
}

fail_closed_runtime() {
  local failed=0
  systemctl --user stop wirtelprimpf-admin.service || failed=1
  systemctl --user stop wirtelprimpf.timer || failed=1
  systemctl --user mask --runtime wirtelprimpf.timer || failed=1
  systemctl --user mask --runtime wirtelprimpf.service || failed=1
  systemctl --user daemon-reload || failed=1
  runtime_timer_masked=1
  runtime_service_masked=1
  wait_generator_inactive || failed=1
  test "$(systemctl --user is-active wirtelprimpf-admin.service || true)" = inactive || failed=1
  test "$(systemctl --user is-active wirtelprimpf.timer || true)" = inactive || failed=1
  test "$(systemctl --user is-enabled wirtelprimpf.timer || true)" = masked-runtime || failed=1
  test "$(systemctl --user is-enabled wirtelprimpf.service || true)" = masked-runtime || failed=1
  return "$failed"
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

# BEGIN TASK4_ROLLBACK_DEPLOYMENT
rollback_deployment() {
  local original_status="$1" rollback_failed=0 config_attention=0
  local config_status=0 generator_quiesced=0 critical_recovery_ok=0 final_status
  local main_ref_now="" main_ref_state=unknown
  # Disarm only recursive EXIT handling. Once recovery begins, a second
  # HUP/INT/TERM is ignored by this shell and every subsequently executed child
  # until restore or fail-close and lock release have completed. The status
  # latched by the first signal remains original_status and is returned below.
  trap - EXIT
  trap '' HUP INT TERM
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
  # A successful compare-and-swap of main is the irreversible software commit
  # point.
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
    fail_closed_runtime || rollback_failed=1
    if [[ "$settings_lock_held" == 1 ]]; then
      release_settings_lock || rollback_failed=1
    fi
    printf 'MAIN REF %s; software preserved, runtime masked, deployment incomplete: %s\n' \
      "$main_ref_state" "$deploy_backup" >&2
    final_status="$original_status"
    [[ "$final_status" != 0 ]] || final_status=1
    exit "$final_status"
  fi
  systemctl --user stop wirtelprimpf-admin.service || rollback_failed=1
  # Wait boundedly for any in-flight applet/CLI settings transaction. All file,
  # checkout, venv, unit, applet, admin, and timer recovery remains behind this
  # same exclusive lock until either the complete old state is proven or both
  # runtime units have been left deliberately masked.
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
    timeout --foreground --signal=TERM --kill-after=10s 300s \
      "$runtime/.venv/bin/python" -m pip install \
      --disable-pip-version-check --no-build-isolation --no-deps -e "$runtime" || {
        rollback_failed=1
        critical_recovery_ok=0
      }
    systemctl --user daemon-reload || {
      rollback_failed=1
      critical_recovery_ok=0
    }
    cmp --silent "$runtime/Sourcecode/systemd-user/wirtelprimpf.service" \
      /home/teladi/.config/systemd/user/wirtelprimpf.service || {
      rollback_failed=1
      critical_recovery_ok=0
    }
    cmp --silent "$runtime/Sourcecode/systemd-user/wirtelprimpf.timer" \
      /home/teladi/.config/systemd/user/wirtelprimpf.timer || {
      rollback_failed=1
      critical_recovery_ok=0
    }
    cmp --silent "$runtime/Sourcecode/systemd-user/wirtelprimpf-admin.service" \
      /home/teladi/.config/systemd/user/wirtelprimpf-admin.service || {
      rollback_failed=1
      critical_recovery_ok=0
    }
    diff --recursive --brief --exclude='__pycache__' --exclude='*.pyc' \
      "$runtime/files/wirtelprimfgenerator@H234598" \
      /home/teladi/.local/share/cinnamon/applets/wirtelprimfgenerator@H234598 || {
      rollback_failed=1
      critical_recovery_ok=0
    }
  else
    rollback_failed=1
  fi

  # A competing config revision is never followed by enablement/activity
  # restoration. Its underlying files and enablement remain untouched; both
  # execution units and the admin writer stay fail-closed instead.
  if [[ "$critical_recovery_ok" == 1 && "$config_attention" == 0 && "$rollback_failed" == 0 ]]; then
    if [[ "$(systemctl --user is-enabled wirtelprimpf.timer || true)" == masked-runtime ]]; then
      runtime_timer_masked=1
      unmask_timer_runtime_stopped || rollback_failed=1
    fi
    restore_timer_enablement_stopped || rollback_failed=1
    if [[ "$(systemctl --user is-enabled wirtelprimpf.service || true)" == masked-runtime ]]; then
      runtime_service_masked=1
    fi
    unmask_generator_runtime || rollback_failed=1
    if [[ "$rollback_failed" == 0 ]]; then
      if [[ "$admin_active_before" == active ]]; then
        systemctl --user start wirtelprimpf-admin.service || rollback_failed=1
      else
        systemctl --user stop wirtelprimpf-admin.service || rollback_failed=1
      fi
      test "$(systemctl --user is-active wirtelprimpf-admin.service || true)" = \
        "$admin_active_before" || rollback_failed=1
      if [[ "$applet_running_before" == 1 ]]; then
        gdbus call --session --dest org.Cinnamon --object-path /org/Cinnamon \
          --method org.Cinnamon.ReloadXlet wirtelprimfgenerator@H234598 APPLET \
          >/dev/null || rollback_failed=1
      fi
      running_xlets="$(gdbus call --session --dest org.Cinnamon \
        --object-path /org/Cinnamon --method org.Cinnamon.GetRunningXletUUIDs applet)" || \
        rollback_failed=1
      if [[ "$applet_running_before" == 1 ]]; then
        [[ "$running_xlets" == *wirtelprimfgenerator@H234598* ]] || rollback_failed=1
      else
        [[ "$running_xlets" != *wirtelprimfgenerator@H234598* ]] || rollback_failed=1
      fi
      if [[ "$rollback_failed" == 0 ]]; then
        restore_timer_activity || rollback_failed=1
      fi
    fi
  fi
  if [[ "$config_attention" != 0 || "$rollback_failed" != 0 || "$critical_recovery_ok" != 1 ]]; then
    fail_closed_runtime || rollback_failed=1
  fi
  if [[ "$settings_lock_held" == 1 ]]; then
    release_settings_lock || rollback_failed=1
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
# END TASK4_ROLLBACK_DEPLOYMENT

trap 'rollback_deployment $?' EXIT
trap 'exit 129' HUP
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

git_runtime_fetch_bounded
test "$(git_runtime rev-parse origin/main)" = "$target_sha"
git_runtime switch --detach "$target_sha"
timeout --foreground --signal=TERM --kill-after=10s 300s \
  "$runtime/.venv/bin/python" -m pip install \
  --disable-pip-version-check --no-build-isolation --no-deps -e "$runtime"
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

# Before any live writer is admitted, prove every installed artifact and the
# two execution barriers. The generator service remains runtime-masked; the
# timer is still stopped and has not yet received its own commit-point mask.
cmp --silent "$runtime/Sourcecode/systemd-user/wirtelprimpf.service" \
  /home/teladi/.config/systemd/user/wirtelprimpf.service
cmp --silent "$runtime/Sourcecode/systemd-user/wirtelprimpf.timer" \
  /home/teladi/.config/systemd/user/wirtelprimpf.timer
cmp --silent "$runtime/Sourcecode/systemd-user/wirtelprimpf-admin.service" \
  /home/teladi/.config/systemd/user/wirtelprimpf-admin.service
diff --recursive --brief --exclude='__pycache__' --exclude='*.pyc' \
  "$runtime/files/wirtelprimfgenerator@H234598" \
  /home/teladi/.local/share/cinnamon/applets/wirtelprimfgenerator@H234598
test "$(systemctl --user is-enabled wirtelprimpf.service || true)" = masked-runtime
test "$(systemctl --user show wirtelprimpf.service \
  -p ActiveState --value)" = inactive
test "$(systemctl --user is-enabled wirtelprimpf.timer || true)" = \
  "$timer_enabled_before"
test "$(systemctl --user is-active wirtelprimpf.timer || true)" = inactive
release_settings_lock
systemctl --user start wirtelprimpf-admin.service
if [[ "$applet_running_before" == 1 ]]; then
  gdbus call --session --dest org.Cinnamon --object-path /org/Cinnamon \
    --method org.Cinnamon.ReloadXlet wirtelprimfgenerator@H234598 APPLET >/dev/null
fi
running_xlets="$(gdbus call --session --dest org.Cinnamon \
  --object-path /org/Cinnamon --method org.Cinnamon.GetRunningXletUUIDs applet)"
if [[ "$applet_running_before" == 1 ]]; then
  [[ "$running_xlets" == *wirtelprimfgenerator@H234598* ]]
else
  [[ "$running_xlets" != *wirtelprimfgenerator@H234598* ]]
fi

# Prove quiescence immediately before the live settings transaction.
test "$(systemctl --user is-active wirtelprimpf.timer || true)" = inactive
test "$(systemctl --user is-enabled wirtelprimpf.timer || true)" = \
  "$timer_enabled_before"
test "$(systemctl --user show wirtelprimpf.service \
  -p ActiveState --value)" = inactive
test "$(systemctl --user is-enabled wirtelprimpf.service || true)" = masked-runtime
export WIRTELPRIMPF_SMOKE_OWNERSHIP_MARKER="$deploy_backup/smoke-owned-revision.json"
# The following Step-5 and Step-6 bodies are materialized byte-for-byte from
# their audited source blocks. They execute synchronously in this transaction;
# no external insertion or second shell is permitted.
smoke_dir="$(mktemp -d /home/teladi/.local/state/wirtelprimpf/admin-live-smoke.XXXXXX)"
chmod 0700 "$smoke_dir"
curl --fail --silent --show-error \
  --noproxy '*' --connect-timeout 2 --max-time 10 \
  --dump-header "$smoke_dir/settings.headers" \
  --output "$smoke_dir/settings.json" \
  http://127.0.0.1:8765/api/settings
curl --fail --silent --show-error \
  --noproxy '*' --connect-timeout 2 --max-time 10 \
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

# Prove that neither the smoke nor an applet interaction restarted generation.
test "$(systemctl --user is-active wirtelprimpf.timer || true)" = inactive
test "$(systemctl --user is-enabled wirtelprimpf.timer || true)" = \
  "$timer_enabled_before"
test "$(systemctl --user show wirtelprimpf.service \
  -p ActiveState --value)" = inactive
test "$(systemctl --user is-enabled wirtelprimpf.service || true)" = masked-runtime
systemctl --user stop wirtelprimpf-admin.service

# After the smoke returns success, its private marker contains the final
# last-owned revision. Reacquire the settings lock, reject a revision mismatch,
# and only then capture raw fingerprints used solely for ownership
# classification. Keep this lock across the ref commit, worktree attachment,
# service/admin/applet restoration, timer restoration, and every final proof.
# Automatic rollback never copies a config backup.
acquire_settings_lock_bounded
smoke_owned_revision="$(jq -er '.revision' "$deploy_backup/smoke-owned-revision.json")"
state_revision="$(jq -er '.revision' /home/teladi/.config/wirtelprimpf/settings-state.json)"
test "$state_revision" = "$smoke_owned_revision"
capture_config_fingerprints >"$deploy_backup/owned-config-fingerprints.tsv"
chmod 0600 "$deploy_backup/owned-config-fingerprints.tsv"

diff --recursive --brief --exclude='__pycache__' --exclude='*.pyc' \
  "$runtime/files/wirtelprimfgenerator@H234598" \
  /home/teladi/.local/share/cinnamon/applets/wirtelprimfgenerator@H234598
cmp --silent "$runtime/Sourcecode/systemd-user/wirtelprimpf.service" \
  /home/teladi/.config/systemd/user/wirtelprimpf.service
cmp --silent "$runtime/Sourcecode/systemd-user/wirtelprimpf.timer" \
  /home/teladi/.config/systemd/user/wirtelprimpf.timer
cmp --silent "$runtime/Sourcecode/systemd-user/wirtelprimpf-admin.service" \
  /home/teladi/.config/systemd/user/wirtelprimpf-admin.service
restore_timer_enablement_stopped
mask_timer_runtime_stopped
test "$(systemctl --user is-enabled wirtelprimpf.service || true)" = masked-runtime
test "$(systemctl --user is-enabled wirtelprimpf.timer || true)" = masked-runtime
test "$(systemctl --user is-active wirtelprimpf.timer || true)" = inactive
test "$(systemctl --user show wirtelprimpf.service \
  -p ActiveState --value)" = inactive
test "$(systemctl --user is-active wirtelprimpf-admin.service || true)" = inactive
running_xlets="$(gdbus call --session --dest org.Cinnamon \
  --object-path /org/Cinnamon --method org.Cinnamon.GetRunningXletUUIDs applet)"
if [[ "$applet_running_before" == 1 ]]; then
  [[ "$running_xlets" == *wirtelprimfgenerator@H234598* ]]
else
  [[ "$running_xlets" != *wirtelprimfgenerator@H234598* ]]
fi

# Keep main untouched until every install/smoke assertion has passed. Commit it
# with a compare-and-swap from the exact recorded SHA while the worktree is
# already detached at the target tree. Attaching main can therefore never
# expose the old tree. The timer and service remain runtime-masked throughout.
git_runtime merge-base --is-ancestor "$runtime_sha_before" "$target_sha"
test "$(git_runtime rev-parse HEAD)" = "$target_sha"
test "$(git_runtime rev-parse refs/heads/main)" = "$runtime_sha_before"
target_tree="$(git_runtime rev-parse "$target_sha^{tree}")"
test "$(git_runtime rev-parse 'HEAD^{tree}')" = "$target_tree"
git_runtime update-ref refs/heads/main "$target_sha" "$runtime_sha_before"
software_commit_complete=1
test "$(git_runtime rev-parse refs/heads/main)" = "$target_sha"
test "$(git_runtime rev-parse HEAD)" = "$target_sha"
git_runtime switch "$runtime_branch_before"
test "$(git_runtime branch --show-current)" = "$runtime_branch_before"
test "$(git_runtime rev-parse HEAD)" = "$target_sha"
test "$(git_runtime rev-parse 'HEAD^{tree}')" = "$target_tree"
test -z "$(git_runtime status --porcelain)"

# Restore every execution surface beneath the still-held settings lock. Any
# failure after the ref CAS invokes the post-commit fail-closed path, masks both
# units, stops admin, and never rewinds main.
unmask_timer_runtime_stopped
unmask_generator_runtime
cmp --silent "$runtime/Sourcecode/systemd-user/wirtelprimpf.service" \
  /home/teladi/.config/systemd/user/wirtelprimpf.service
cmp --silent "$runtime/Sourcecode/systemd-user/wirtelprimpf.timer" \
  /home/teladi/.config/systemd/user/wirtelprimpf.timer
cmp --silent "$runtime/Sourcecode/systemd-user/wirtelprimpf-admin.service" \
  /home/teladi/.config/systemd/user/wirtelprimpf-admin.service
diff --recursive --brief --exclude='__pycache__' --exclude='*.pyc' \
  "$runtime/files/wirtelprimfgenerator@H234598" \
  /home/teladi/.local/share/cinnamon/applets/wirtelprimfgenerator@H234598
if [[ "$admin_active_before" == active ]]; then
  systemctl --user start wirtelprimpf-admin.service
else
  systemctl --user stop wirtelprimpf-admin.service
fi
test "$(systemctl --user is-active wirtelprimpf-admin.service || true)" = \
  "$admin_active_before"
if [[ "$admin_active_before" == active ]]; then
  test "$(systemctl --user show wirtelprimpf-admin.service \
    -p SubState --value)" = running
fi
# The target applet was already reloaded and UUID-proven before the smoke, and
# its installed tree has just been proven byte-identical again. Do not issue a
# second ReloadXlet while holding the exclusive settings lock: a settings UI
# initial snapshot must never be forced into a synthetic busy result here.
running_xlets="$(gdbus call --session --dest org.Cinnamon \
  --object-path /org/Cinnamon --method org.Cinnamon.GetRunningXletUUIDs applet)"
if [[ "$applet_running_before" == 1 ]]; then
  [[ "$running_xlets" == *wirtelprimfgenerator@H234598* ]]
else
  [[ "$running_xlets" != *wirtelprimfgenerator@H234598* ]]
fi
restore_timer_activity
test "$(systemctl --user is-enabled wirtelprimpf.service || true)" = \
  "$service_unit_state_before"
test "$(systemctl --user show wirtelprimpf.service -p LoadState --value)" = \
  "$service_load_state_before"
test "$(systemctl --user show wirtelprimpf.service \
  -p ActiveState --value)" = inactive
# Close the only post-lock race explicitly. HUP/INT/TERM are ignored while the
# lock is released and the infallible shell-state commit disarms EXIT recovery.
# If release_settings_lock itself fails, set -e still enters the armed EXIT
# rollback before deployment_complete changes.
trap '' HUP INT TERM
release_settings_lock
deployment_complete=1
trap - EXIT
trap - HUP INT TERM
```

Expected: the previous SHA and exact restorable service semantics are privately
recorded; generator activity cannot overlap backup/install/smoke; every
present/missing target has an allowlisted restore action; any failure restores
the old checkout, editable install, units, applet, admin state, exact timer
enablement/activity, and the three allowlisted pre-existing parent-directory
modes. Config/state backups remain manual evidence and are never copied by
automatic rollback. Success retains the intended `0700` directory hardening,
advances `main` only by an exact-old-SHA compare-and-swap, and attaches the
already-target worktree without exposing old-tree code. Both runtime masks
remain in force through the commit and are removed only during the lock-held
final restoration; the settings lock remains held through every final state
proof. A redundant final Applet-Reload is deliberately omitted, and the final
lock release is enclosed by an explicit signal-ignore/EXIT-disarm contract.
The procedure contains no reset, force push, forced checkout, or unscoped
deletion.

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
installer returns to `0755` only on rollback. The checked-in structural runner
`python -m unittest tests.test_rollout_plan_contract -v` additionally extracts
the exact Step-9/Step-10 blocks, syntax-checks both, requires the complete
audited Step-5/Step-6 bodies byte-for-byte inside Step 9, proves marker-producer
ordering, and executes this disposable harness:

```bash
set -Eeuo pipefail
sandbox="$(mktemp -d /tmp/wirtelprimpf-restore-harness.XXXXXX)"
cleanup() {
  [[ "$sandbox" == /tmp/wirtelprimpf-restore-harness.* && -d "$sandbox" ]]
  rm -rf -- "$sandbox"
}
trap cleanup EXIT
mkdir -p "$sandbox/backup" "$sandbox/live" \
  "$sandbox/source/units" "$sandbox/live/units" \
  "$sandbox/source/applet" "$sandbox/live/applet"
printf 'old-install\n' >"$sandbox/backup/present"
mkdir "$sandbox/live/private-parent"
chmod 0755 "$sandbox/live/private-parent"
printf '755\n' >"$sandbox/backup/private-parent-mode"
printf 'lock-sentinel\n' >"$sandbox/settings.lock"
printf 'active\n' >"$sandbox/timer-state"
printf 'enabled\n' >"$sandbox/timer-enablement"
printf 'enabled\n' >"$sandbox/timer-persistent-enablement"
printf 'active\n' >"$sandbox/generator-state"
printf 'static\n' >"$sandbox/service-enablement"
printf 'active\n' >"$sandbox/admin-state"
printf 'running\n' >"$sandbox/applet-state"
for unit in wirtelprimpf.service wirtelprimpf.timer wirtelprimpf-admin.service; do
  printf 'unit=%s\n' "$unit" >"$sandbox/source/units/$unit"
  cp -a -- "$sandbox/source/units/$unit" "$sandbox/live/units/$unit"
done
printf 'applet-target\n' >"$sandbox/source/applet/metadata.json"
cp -a -- "$sandbox/source/applet/metadata.json" \
  "$sandbox/live/applet/metadata.json"
: >"$sandbox/recovery-events"

assert_recovery_lock_held() {
  if flock -n "$sandbox/settings.lock" true; then
    printf 'recovery mutation escaped the settings lock\n' >&2
    return 1
  fi
}

restore_install_targets() {
  test "$(<"$sandbox/generator-state")" = inactive
  test "$(<"$sandbox/service-enablement")" = masked-runtime
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
  printf 'generator-inactive-before-mask\n' >>"$sandbox/recovery-events"
  printf 'masked-runtime\n' >"$sandbox/service-enablement"
  printf 'service-runtime-mask\n' >>"$sandbox/recovery-events"
  if [[ "$transition" == after-mask-reactivation ]]; then
    printf 'active\n' >"$sandbox/generator-state"
  fi
  attempts=0
  while [[ "$(<"$sandbox/generator-state")" != inactive ]]; do
    attempts=$((attempts + 1))
    if [[ "$transition" == after-mask-reactivation && "$attempts" == 1 ]]; then
      printf 'inactive\n' >"$sandbox/generator-state"
    fi
    (( attempts < max_attempts )) || return 1
  done
  printf 'generator-inactive-after-mask\n' >>"$sandbox/recovery-events"
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
  for unit in wirtelprimpf.service wirtelprimpf.timer wirtelprimpf-admin.service; do
    cmp --silent "$sandbox/source/units/$unit" "$sandbox/live/units/$unit"
  done
  assert_recovery_lock_held
  printf 'unit-proof\n' >>"$sandbox/recovery-events"
  diff --recursive --brief "$sandbox/source/applet" "$sandbox/live/applet"
  assert_recovery_lock_held
  printf 'applet-proof\n' >>"$sandbox/recovery-events"
  printf 'enabled\n' >"$sandbox/timer-enablement"
  test "$(<"$sandbox/timer-state")" = inactive
  assert_recovery_lock_held
  printf 'timer-enablement-proof\n' >>"$sandbox/recovery-events"
  printf 'static\n' >"$sandbox/service-enablement"
  test "$(<"$sandbox/service-enablement")" = static
  assert_recovery_lock_held
  printf 'service-runtime-unmask\nservice-proof\n' \
    >>"$sandbox/recovery-events"
  printf 'active\n' >"$sandbox/admin-state"
  test "$(<"$sandbox/admin-state")" = active
  assert_recovery_lock_held
  printf 'admin-restore\nadmin-proof\n' >>"$sandbox/recovery-events"
  printf 'running\n' >"$sandbox/applet-state"
  test "$(<"$sandbox/applet-state")" = running
  assert_recovery_lock_held
  printf 'applet-reload\napplet-running-proof\n' \
    >>"$sandbox/recovery-events"
  printf 'active\n' >"$sandbox/timer-state"
  test "$(<"$sandbox/timer-enablement")" = enabled
  test "$(<"$sandbox/timer-state")" = active
  assert_recovery_lock_held
  printf 'timer-restore\ntimer-proof\n' >>"$sandbox/recovery-events"
  flock -u "$recovery_lock"
  exec {recovery_lock}>&-
  printf 'settings-unlock\n' >>"$sandbox/recovery-events"
  flock -n "$sandbox/settings.lock" true
}

fail_closed_harness() {
  printf 'inactive\n' >"$sandbox/admin-state"
  printf 'inactive\n' >"$sandbox/timer-state"
  printf 'masked-runtime\n' >"$sandbox/timer-enablement"
  printf 'masked-runtime\n' >"$sandbox/service-enablement"
  printf 'fail-closed-admin-stop\nfail-closed-timer-stop\ntimer-runtime-mask\nservice-runtime-mask\n' \
    >>"$sandbox/recovery-events"
  test "$(<"$sandbox/timer-persistent-enablement")" = enabled
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
  timer-stop,generator-inactive-before-mask,service-runtime-mask,generator-inactive-after-mask,admin-stop,settings-lock,install-restore,directory-mode-restore,config-classify,checkout-restore,venv-restore,daemon-reload,unit-proof,applet-proof,timer-enablement-proof,service-runtime-unmask,service-proof,admin-restore,admin-proof,applet-reload,applet-running-proof,timer-restore,timer-proof,settings-unlock
test "$(<"$sandbox/service-enablement")" = static
test "$(<"$sandbox/timer-state")" = active
test "$(<"$sandbox/admin-state")" = active

# A generator that never becomes inactive exhausts its finite bound and no
# install/checkout/venv restoration is attempted beneath it.
: >"$sandbox/recovery-events"
printf 'active\n' >"$sandbox/generator-state"
printf 'static\n' >"$sandbox/service-enablement"
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
printf 'static\n' >"$sandbox/service-enablement"
printf 'enabled\n' >"$sandbox/timer-enablement"
printf 'enabled\n' >"$sandbox/timer-persistent-enablement"
printf 'active\n' >"$sandbox/admin-state"
exec {competitor_lock}<>"$sandbox/settings.lock"
flock -n "$competitor_lock"
set +e
rollback_harness already-inactive 0.05
lock_wait_status=$?
set -e
test "$lock_wait_status" -ne 0
fail_closed_harness
test "$(paste -sd, "$sandbox/recovery-events")" = \
  timer-stop,generator-inactive-before-mask,service-runtime-mask,generator-inactive-after-mask,admin-stop,fail-closed-admin-stop,fail-closed-timer-stop,timer-runtime-mask,service-runtime-mask
test "$(<"$sandbox/service-enablement")" = masked-runtime
test "$(<"$sandbox/timer-enablement")" = masked-runtime
test "$(<"$sandbox/timer-persistent-enablement")" = enabled
test "$(<"$sandbox/timer-state")" = inactive
test "$(<"$sandbox/admin-state")" = inactive
flock -u "$competitor_lock"
exec {competitor_lock}>&-

# Exercise the actual shell signal contract while recovery is deliberately
# blocked and owns the settings lock. The first TERM latches status 143 and
# enters EXIT recovery; a second HUP must not interrupt restore/fail-close.
signal_recovery_probe() {
  # shellcheck disable=SC2329  # invoked by the EXIT trap below
  signal_recovery() {
    local original_status="$1"
    trap - EXIT
    trap '' HUP INT TERM
    exec {signal_lock}<>"$sandbox/settings.lock"
    flock -n "$signal_lock"
    printf 'rollback-entered:%s\n' "$original_status" \
      >>"$sandbox/signal-recovery-events"
    : >"$sandbox/signal-recovery-ready"
    while [[ ! -e "$sandbox/signal-recovery-release" ]]; do
      sleep 0.01
    done
    printf 'inactive\n' >"$sandbox/admin-state"
    printf 'inactive\n' >"$sandbox/timer-state"
    printf 'masked-runtime\n' >"$sandbox/timer-enablement"
    printf 'masked-runtime\n' >"$sandbox/service-enablement"
    test "$(<"$sandbox/timer-persistent-enablement")" = enabled
    printf 'restore-complete\nfail-close-proof\n' \
      >>"$sandbox/signal-recovery-events"
    flock -u "$signal_lock"
    exec {signal_lock}>&-
    printf 'settings-unlock\n' >>"$sandbox/signal-recovery-events"
    exit "$original_status"
  }
  trap 'signal_recovery $?' EXIT
  trap 'exit 129' HUP
  trap 'exit 130' INT
  trap 'exit 143' TERM
  : >"$sandbox/signal-probe-armed"
  while :; do sleep 0.01; done
}

: >"$sandbox/signal-recovery-events"
signal_recovery_probe &
recovery_pid=$!
for _attempt in $(seq 1 200); do
  [[ -e "$sandbox/signal-probe-armed" ]] && break
  sleep 0.01
done
test -e "$sandbox/signal-probe-armed"
kill -TERM "$recovery_pid"
for _attempt in $(seq 1 200); do
  [[ -e "$sandbox/signal-recovery-ready" ]] && break
  sleep 0.01
done
test -e "$sandbox/signal-recovery-ready"
if flock -n "$sandbox/settings.lock" true; then
  printf 'signal recovery did not retain the settings lock\n' >&2
  exit 1
fi
kill -HUP "$recovery_pid"
sleep 0.05
kill -0 "$recovery_pid"
: >"$sandbox/signal-recovery-release"
set +e
wait "$recovery_pid"
signal_status=$?
set -e
test "$signal_status" = 143
test "$(paste -sd, "$sandbox/signal-recovery-events")" = \
  rollback-entered:143,restore-complete,fail-close-proof,settings-unlock
test "$(<"$sandbox/admin-state")" = inactive
test "$(<"$sandbox/timer-state")" = inactive
test "$(<"$sandbox/timer-enablement")" = masked-runtime
test "$(<"$sandbox/service-enablement")" = masked-runtime
test "$(<"$sandbox/timer-persistent-enablement")" = enabled
flock -n "$sandbox/settings.lock" true

# Even a synthetic activation in the first inactive-to-mask boundary is caught
# by the mandatory second wait; no recovery mutation can precede it.
: >"$sandbox/recovery-events"
printf 'inactive\n' >"$sandbox/generator-state"
printf 'static\n' >"$sandbox/service-enablement"
quiesce_generator_harness after-mask-reactivation
test "$(<"$sandbox/generator-state")" = inactive
test "$(<"$sandbox/service-enablement")" = masked-runtime
test "$(paste -sd, "$sandbox/recovery-events")" = \
  timer-stop,generator-inactive-before-mask,service-runtime-mask,generator-inactive-after-mask

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

# The final lock is reacquired after the deliberately unlocked live smoke. A
# real disposable repository proves the exact compare-and-swap and that
# attaching main never presents the old tree: HEAD is already detached at the
# target tree when refs/heads/main changes.
runtime_harness="$sandbox/runtime"
git init -q -b main "$runtime_harness"
git -C "$runtime_harness" config user.name 'Wirtelprimpf Harness'
git -C "$runtime_harness" config user.email harness@example.invalid
printf 'old-tree\n' >"$runtime_harness/application.txt"
git -C "$runtime_harness" add application.txt
git -C "$runtime_harness" commit -qm old
runtime_sha_before="$(git -C "$runtime_harness" rev-parse HEAD)"
printf 'target-tree\n' >"$runtime_harness/application.txt"
git -C "$runtime_harness" commit -qam target
target_sha="$(git -C "$runtime_harness" rev-parse HEAD)"
target_tree="$(git -C "$runtime_harness" rev-parse "$target_sha^{tree}")"
git -C "$runtime_harness" switch --detach -q "$target_sha"
git -C "$runtime_harness" update-ref refs/heads/main \
  "$runtime_sha_before" "$target_sha"
test "$(<"$runtime_harness/application.txt")" = target-tree

assert_final_lock_held() {
  if flock -n "$sandbox/settings.lock" true; then
    printf 'final transaction escaped the settings lock\n' >&2
    return 1
  fi
}

: >"$sandbox/success-events"
printf 'inactive\n' >"$sandbox/timer-state"
printf 'enabled\n' >"$sandbox/timer-enablement"
printf 'masked-runtime\n' >"$sandbox/service-enablement"
printf 'inactive\n' >"$sandbox/admin-state"
exec {final_lock}<>"$sandbox/settings.lock"
flock -n "$final_lock"
printf 'settings-lock\n' >>"$sandbox/success-events"
for phase in revision-proof fingerprints artifact-proof; do
  assert_final_lock_held
  printf '%s\n' "$phase" >>"$sandbox/success-events"
done
test "$(<"$sandbox/timer-state")" = inactive
test "$(<"$sandbox/timer-enablement")" = enabled
printf 'timer-enablement-restored-stopped\n' >>"$sandbox/success-events"
assert_final_lock_held
printf 'masked-runtime\n' >"$sandbox/timer-enablement"
printf 'timer-runtime-mask\n' >>"$sandbox/success-events"
test "$(<"$sandbox/service-enablement")" = masked-runtime
test "$(<"$sandbox/timer-enablement")" = masked-runtime
test "$(<"$sandbox/timer-state")" = inactive
git -C "$runtime_harness" merge-base --is-ancestor \
  "$runtime_sha_before" "$target_sha"
printf 'ancestry-proof\n' >>"$sandbox/success-events"
assert_final_lock_held
test "$(git -C "$runtime_harness" rev-parse HEAD)" = "$target_sha"
test "$(git -C "$runtime_harness" rev-parse refs/heads/main)" = \
  "$runtime_sha_before"
test "$(git -C "$runtime_harness" rev-parse 'HEAD^{tree}')" = "$target_tree"
git -C "$runtime_harness" update-ref refs/heads/main \
  "$target_sha" "$runtime_sha_before"
software_commit_complete=1
printf 'update-ref-cas\n' >>"$sandbox/success-events"
assert_final_lock_held
test "$(git -C "$runtime_harness" rev-parse refs/heads/main)" = "$target_sha"
test "$(git -C "$runtime_harness" rev-parse HEAD)" = "$target_sha"
test "$(<"$runtime_harness/application.txt")" = target-tree
git -C "$runtime_harness" switch -q main
test "$(git -C "$runtime_harness" branch --show-current)" = main
test "$(git -C "$runtime_harness" rev-parse 'HEAD^{tree}')" = "$target_tree"
test "$(<"$runtime_harness/application.txt")" = target-tree
test -z "$(git -C "$runtime_harness" status --porcelain)"
printf 'attach-main-same-tree\n' >>"$sandbox/success-events"
assert_final_lock_held
printf 'enabled\n' >"$sandbox/timer-enablement"
test "$(<"$sandbox/timer-state")" = inactive
printf 'timer-runtime-unmask\n' >>"$sandbox/success-events"
printf 'static\n' >"$sandbox/service-enablement"
test "$(<"$sandbox/service-enablement")" = static
printf 'service-runtime-unmask\nservice-proof\n' \
  >>"$sandbox/success-events"
for unit in wirtelprimpf.service wirtelprimpf.timer wirtelprimpf-admin.service; do
  cmp --silent "$sandbox/source/units/$unit" "$sandbox/live/units/$unit"
done
printf 'unit-proof\n' >>"$sandbox/success-events"
diff --recursive --brief "$sandbox/source/applet" "$sandbox/live/applet"
test "$(<"$sandbox/applet-state")" = running
printf 'applet-proof\n' >>"$sandbox/success-events"
assert_final_lock_held
printf 'active\n' >"$sandbox/admin-state"
test "$(<"$sandbox/admin-state")" = active
printf 'admin-proof\n' >>"$sandbox/success-events"
assert_final_lock_held
printf 'active\n' >"$sandbox/timer-state"
test "$(<"$sandbox/timer-enablement")" = enabled
test "$(<"$sandbox/timer-state")" = active
printf 'timer-start\ntimer-proof\n' >>"$sandbox/success-events"
assert_final_lock_held
printf 'final-signal-window-ordered\n' >>"$sandbox/success-events"
flock -u "$final_lock"
exec {final_lock}>&-
printf 'settings-unlock\n' >>"$sandbox/success-events"
deployment_complete=1
test "$deployment_complete" = 1
printf 'deployment-complete\nexit-trap-cleared\nsignals-restored\n' \
  >>"$sandbox/success-events"
flock -n "$sandbox/settings.lock" true
test "$(<"$sandbox/settings.lock")" = lock-sentinel
test "$(paste -sd, "$sandbox/success-events")" = \
  settings-lock,revision-proof,fingerprints,artifact-proof,timer-enablement-restored-stopped,timer-runtime-mask,ancestry-proof,update-ref-cas,attach-main-same-tree,timer-runtime-unmask,service-runtime-unmask,service-proof,unit-proof,applet-proof,admin-proof,timer-start,timer-proof,final-signal-window-ordered,settings-unlock,deployment-complete,exit-trap-cleared,signals-restored
if rg -q -- 'old-tree|fast-forward|checkout-old|applet-reload|fail-closed' \
  "$sandbox/success-events"; then
  exit 1
fi
test "$(tail -n1 "$sandbox/success-events")" = signals-restored

# If INT/TERM lands after update-ref but before the shell flag, exact ref
# classification still selects postcommit. A third SHA selects unknown. Both
# paths stop admin/timer, runtime-mask timer and service, and never rewind or
# reinstall anything.
software_commit_complete=0
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
  printf 'enabled\n' >"$sandbox/timer-enablement"
  printf 'static\n' >"$sandbox/service-enablement"
  printf 'active\n' >"$sandbox/admin-state"
  main_ref_state="$(classify_main_ref "$main_ref_now")"
  if [[ "$software_commit_complete" == 1 || "$main_ref_state" != precommit ]]; then
    printf 'inactive\n' >"$sandbox/admin-state"
    printf 'inactive\n' >"$sandbox/timer-state"
    printf 'masked-runtime\n' >"$sandbox/timer-enablement"
    printf 'masked-runtime\n' >"$sandbox/service-enablement"
    printf 'admin-stop\ntimer-stop\ntimer-runtime-mask\nservice-runtime-mask\n%s-incomplete\n' \
      "$main_ref_state" \
      >>"$sandbox/postcommit-events"
  fi
  test "$(<"$sandbox/admin-state")" = inactive
  test "$(<"$sandbox/timer-state")" = inactive
  test "$(<"$sandbox/timer-enablement")" = masked-runtime
  test "$(<"$sandbox/service-enablement")" = masked-runtime
  test "$(paste -sd, "$sandbox/postcommit-events")" = \
    "admin-stop,timer-stop,timer-runtime-mask,service-runtime-mask,${main_ref_state}-incomplete"
  if rg -q -- 'checkout|venv|install|worktree|restore' \
    "$sandbox/postcommit-events"; then
    exit 1
  fi
done
test "$(git -C "$runtime_harness" rev-parse refs/heads/main)" = "$target_sha"

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
if cmp --silent "$sandbox/backup/openai.env" "$sandbox/live/openai.env"; then
  exit 1
fi

# A later competitor produces attention-required (2), is left byte-for-byte
# untouched, and selects the explicit fail-closed end state. The persistent
# enablement value is not restored or rewritten; runtime masks merely override
# execution until an operator reconciles the competitor.
printf 'OUTPUT_RESOLUTION=4k\n' >"$sandbox/live/openai.env"
printf '{"revision":"competitor"}\n' >"$sandbox/live/settings-state.json"
printf 'enabled\n' >"$sandbox/timer-persistent-enablement"
printf 'enabled\n' >"$sandbox/timer-enablement"
printf 'static\n' >"$sandbox/service-enablement"
printf 'active\n' >"$sandbox/timer-state"
printf 'active\n' >"$sandbox/admin-state"
competitor_before="$(fingerprint_live_config)"
exec {attention_lock}<>"$sandbox/settings.lock"
flock -n "$attention_lock"
set +e
classify_config_without_restore
config_status=$?
set -e
test "$config_status" = 2
: >"$sandbox/config-attention-events"
printf 'inactive\n' >"$sandbox/admin-state"
printf 'inactive\n' >"$sandbox/timer-state"
printf 'masked-runtime\n' >"$sandbox/timer-enablement"
printf 'masked-runtime\n' >"$sandbox/service-enablement"
printf 'admin-stop\ntimer-stop\ntimer-runtime-mask\nservice-runtime-mask\nattention-required\n' \
  >>"$sandbox/config-attention-events"
assert_final_lock_held
test "$(fingerprint_live_config)" = "$competitor_before"
test "$(jq -r '.revision' "$sandbox/live/settings-state.json")" = competitor
test "$(<"$sandbox/timer-persistent-enablement")" = enabled
test "$(<"$sandbox/timer-enablement")" = masked-runtime
test "$(<"$sandbox/service-enablement")" = masked-runtime
test "$(<"$sandbox/timer-state")" = inactive
test "$(<"$sandbox/admin-state")" = inactive
test "$(paste -sd, "$sandbox/config-attention-events")" = \
  admin-stop,timer-stop,timer-runtime-mask,service-runtime-mask,attention-required
if rg -q -- 'restore|unmask|start' "$sandbox/config-attention-events"; then
  exit 1
fi
flock -u "$attention_lock"
exec {attention_lock}>&-

# The private smoke marker has one producer and one later consumer. This
# behavioral probe rejects a missing/stale marker and records the required
# ordering; the checked-in structural gate ties those operations to Step 9.
marker_revision=dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
marker_path="$sandbox/materialized-smoke-owned-revision.json"
test ! -e "$marker_path"
: >"$sandbox/marker-events"
printf '{"revision":"%s"}\n' "$marker_revision" >"$marker_path"
chmod 0600 "$marker_path"
printf 'marker-producer\n' >>"$sandbox/marker-events"
consumed_marker_revision="$(jq -er '.revision' "$marker_path")"
test "$consumed_marker_revision" = "$marker_revision"
printf 'marker-consumer\n' >>"$sandbox/marker-events"
test "$(paste -sd, "$sandbox/marker-events")" = \
  marker-producer,marker-consumer

# Exercise the real local receive-pack CAS without GitHub or network access.
# The deterministic object has head's tree and exact ordered base/head parents.
# A head race and a base race must each reject the entire atomic push; only the
# exact pair may advance main and delete the reviewed head in one transaction.
merge_source="$sandbox/merge-source"
merge_remote="$sandbox/merge-remote.git"
git init -q -b main "$merge_source"
git -C "$merge_source" config user.name 'Wirtelprimpf Merge Harness'
git -C "$merge_source" config user.email merge-harness@example.invalid
printf 'base\n' >"$merge_source/content.txt"
git -C "$merge_source" add content.txt
git -C "$merge_source" commit -qm base
lease_base="$(git -C "$merge_source" rev-parse HEAD)"
git -C "$merge_source" switch -qc reviewed-head
printf 'reviewed\n' >"$merge_source/content.txt"
git -C "$merge_source" commit -qam reviewed-head
lease_head="$(git -C "$merge_source" rev-parse HEAD)"
lease_tree="$(git -C "$merge_source" rev-parse "$lease_head^{tree}")"
lease_merge="$(
  printf 'deterministic indirect merge\n' |
    GIT_AUTHOR_NAME='Wirtelprimpf Merge Harness' \
    GIT_AUTHOR_EMAIL=merge-harness@example.invalid \
    GIT_AUTHOR_DATE='2001-01-01T00:00:00+00:00' \
    GIT_COMMITTER_NAME='Wirtelprimpf Merge Harness' \
    GIT_COMMITTER_EMAIL=merge-harness@example.invalid \
    GIT_COMMITTER_DATE='2001-01-01T00:00:00+00:00' \
    git -C "$merge_source" commit-tree "$lease_tree" \
      -p "$lease_base" -p "$lease_head"
)"
test "$(git -C "$merge_source" rev-parse "$lease_merge^{tree}")" = "$lease_tree"
test "$(git -C "$merge_source" rev-list --parents -n1 "$lease_merge")" = \
  "$lease_merge $lease_base $lease_head"
git init -q --bare "$merge_remote"
git -C "$merge_source" remote add origin "$merge_remote"
git -C "$merge_source" push -q origin \
  "$lease_base:refs/heads/main" \
  "$lease_head:refs/heads/reviewed-head"

atomic_lease_push() {
  git -C "$merge_source" push --atomic \
    "--force-with-lease=refs/heads/main:$lease_base" \
    "--force-with-lease=refs/heads/reviewed-head:$lease_head" \
    origin \
    "$lease_merge:refs/heads/main" \
    ':refs/heads/reviewed-head'
}

: >"$sandbox/merge-events"
git -C "$merge_remote" update-ref \
  refs/heads/reviewed-head "$lease_base" "$lease_head"
set +e
atomic_lease_push >"$sandbox/head-lease-race.output" 2>&1
head_lease_status=$?
set -e
test "$head_lease_status" -ne 0
test "$(git -C "$merge_remote" rev-parse refs/heads/main)" = "$lease_base"
test "$(git -C "$merge_remote" rev-parse refs/heads/reviewed-head)" = "$lease_base"
printf 'head-lease-race-rejected\n' >>"$sandbox/merge-events"

git -C "$merge_remote" update-ref \
  refs/heads/reviewed-head "$lease_head" "$lease_base"
git -C "$merge_remote" update-ref refs/heads/main "$lease_head" "$lease_base"
set +e
atomic_lease_push >"$sandbox/base-lease-race.output" 2>&1
base_lease_status=$?
set -e
test "$base_lease_status" -ne 0
test "$(git -C "$merge_remote" rev-parse refs/heads/main)" = "$lease_head"
test "$(git -C "$merge_remote" rev-parse refs/heads/reviewed-head)" = "$lease_head"
printf 'base-lease-race-rejected\n' >>"$sandbox/merge-events"

git -C "$merge_remote" update-ref refs/heads/main "$lease_base" "$lease_head"
atomic_lease_push >"$sandbox/exact-lease.output" 2>&1
test "$(git -C "$merge_remote" rev-parse refs/heads/main)" = "$lease_merge"
test "$(git -C "$merge_remote" rev-parse 'refs/heads/main^{tree}')" = "$lease_tree"
test "$(git -C "$merge_remote" rev-list --parents -n1 refs/heads/main)" = \
  "$lease_merge $lease_base $lease_head"
if git -C "$merge_remote" show-ref --verify --quiet refs/heads/reviewed-head; then
  exit 1
fi
printf 'exact-base-head-lease-cas\n' >>"$sandbox/merge-events"
test "$(paste -sd, "$sandbox/merge-events")" = \
  head-lease-race-rejected,base-lease-race-rejected,exact-base-head-lease-cas

# Exercise the durable Task-3 commitpoint state machine against another real
# bare remote. A crash in the uncloseable remote-push/local-receipt window must
# reconcile from planned, and neither an API failure nor a later rerun may push
# the already committed merge a second time.
receipt_remote="$sandbox/receipt-remote.git"
receipt_file_harness="$sandbox/generator-main-receipt.state"
receipt_push_count="$sandbox/receipt-push-count"
receipt_events="$sandbox/receipt-events"
git init -q --bare "$receipt_remote"
git -C "$merge_source" remote add receipt-origin "$receipt_remote"
git -C "$merge_source" push -q receipt-origin \
  "$lease_base:refs/heads/main" \
  "$lease_head:refs/heads/reviewed-head"
printf '0\n' >"$receipt_push_count"
: >"$receipt_events"

write_receipt_harness() {
  local next_state="$1" receipt_tmp
  case "$next_state" in planned|remote_committed|verified) ;; *) return 1 ;; esac
  receipt_tmp="$(mktemp "$sandbox/.receipt.XXXXXX")"
  chmod 0600 "$receipt_tmp"
  printf '%s\n' "$next_state" >"$receipt_tmp"
  mv -fT -- "$receipt_tmp" "$receipt_file_harness"
  test "$(stat -c '%a' "$receipt_file_harness")" = 600
}

receipt_commitpoint_harness() {
  local injection="$1" pr_state="$2" api_state="$3"
  local receipt_state remote_main remote_head pushes
  receipt_state="$(<"$receipt_file_harness")"
  remote_main="$(git -C "$merge_source" ls-remote \
    receipt-origin refs/heads/main | cut -f1)"
  remote_head="$(git -C "$merge_source" ls-remote \
    receipt-origin refs/heads/reviewed-head | cut -f1)"
  case "$receipt_state" in
    planned)
      if [[ "$remote_main" == "$lease_base" && "$remote_head" == "$lease_head" ]]; then
        test "$pr_state" = OPEN
        pushes="$(( $(<"$receipt_push_count") + 1 ))"
        printf '%s\n' "$pushes" >"$receipt_push_count"
        git -C "$merge_source" push --atomic \
          "--force-with-lease=refs/heads/main:$lease_base" \
          "--force-with-lease=refs/heads/reviewed-head:$lease_head" \
          receipt-origin \
          "$lease_merge:refs/heads/main" \
          ':refs/heads/reviewed-head' >/dev/null
        if [[ "$injection" == after-push-before-receipt ]]; then
          printf 'after-push-before-receipt\n' >>"$receipt_events"
          return 97
        fi
        write_receipt_harness remote_committed
      elif [[ "$remote_main" == "$lease_merge" && -z "$remote_head" ]]; then
        case "$pr_state" in OPEN|MERGED) ;; *) return 1 ;; esac
        write_receipt_harness remote_committed
        printf 'planned-remote-committed-reconciled\n' >>"$receipt_events"
      else
        return 1
      fi
      ;;
    remote_committed)
      test "$remote_main" = "$lease_merge"
      test -z "$remote_head"
      ;;
    verified)
      test "$remote_main" = "$lease_merge"
      test -z "$remote_head"
      test "$pr_state" = MERGED
      return 0
      ;;
    *) return 1 ;;
  esac
  if [[ "$api_state" == failure ]]; then
    printf 'remote-committed-api-failure\n' >>"$receipt_events"
    return 98
  fi
  test "$pr_state" = MERGED
  write_receipt_harness verified
  printf 'verified-without-second-push\n' >>"$receipt_events"
}

write_receipt_harness planned
set +e
receipt_commitpoint_harness after-push-before-receipt OPEN success
after_push_status=$?
set -e
test "$after_push_status" = 97
test "$(<"$receipt_file_harness")" = planned
test "$(git -C "$receipt_remote" rev-parse refs/heads/main)" = "$lease_merge"
test ! -e "$receipt_remote/refs/heads/reviewed-head"
test "$(<"$receipt_push_count")" = 1

set +e
receipt_commitpoint_harness reconcile OPEN failure
api_failure_status=$?
set -e
test "$api_failure_status" = 98
test "$(<"$receipt_file_harness")" = remote_committed
test "$(<"$receipt_push_count")" = 1

receipt_commitpoint_harness reconcile MERGED success
test "$(<"$receipt_file_harness")" = verified
test "$(<"$receipt_push_count")" = 1

# No receipt state authorizes an unknown remote ref pair.
write_receipt_harness planned
git -C "$receipt_remote" update-ref \
  refs/heads/main "$lease_head" "$lease_merge"
set +e
receipt_commitpoint_harness reconcile MERGED success
unknown_receipt_status=$?
set -e
test "$unknown_receipt_status" -ne 0
test "$(<"$receipt_push_count")" = 1
printf 'unknown-state-failed-closed\n' >>"$receipt_events"
test "$(paste -sd, "$receipt_events")" = \
  after-push-before-receipt,planned-remote-committed-reconciled,remote-committed-api-failure,verified-without-second-push,unknown-state-failed-closed
```

Expected: `bash -n` and the harness exit 0. The rollback log proves timer stop
and bounded service quiescence precede every file/code restore; the stuck case
fails closed without reaching those mutations. The lock sentinel survives and
contention remains closed through `daemon-reload`, then opens before admin/smoke.
All three config cases retain their current bytes and semantic revision; no
automatic branch copies config backup bytes. A competitor additionally leaves
admin/timer stopped and both runtime execution units masked without rewriting
persistent enablement. The existing private-parent mode returns from the
simulated installer's `0700` to its recorded `0755`, while a successful live
installation would retain the intended `0700` hardening. The success trace
proves an exact-old-SHA CAS, target-tree-only main attachment, and a settings
lock held through unit/applet/admin/timer proofs and the final timer path. Its
update-ref-to-flag signal-window stops both writers and contains no worktree or
file rewind. A third/unexpected main SHA is classified `unknown` and preserves
files identically; only the exact recorded pre-deploy SHA authorizes rollback.
The real signal probe sends TERM to enter rollback, sends HUP while recovery is
blocked beneath the settings lock, and proves the original status survives
through restore/fail-close and unlock. Lock contention explicitly leaves admin
and timer inactive, both runtime units masked, and persistent timer enablement
unchanged. The local bare-remote probe rejects both a head-only and base-only
lease race without a partial ref update; the exact pair atomically advances
main to the deterministic head-tree/base-head-parent merge and deletes the
review head. The second bare-remote probe then injects failure immediately
after that remote commitpoint while the receipt is still `planned`, reconciles
`OPEN + planned + remote committed`, preserves `remote_committed` across an API
failure, reaches `verified` from a matching `MERGED` observation without a
second push, and rejects an unknown ref pair. The marker trace and checked-in
structural gate prove producer before consumer in the self-contained Step-9
artifact. The same contract directly binds the normative
`rollback_deployment` prolog: recursive EXIT is disarmed before HUP/INT/TERM are
ignored, both precede recovery, and settings-lock release precedes its final
status exit.
This is local disposable evidence, not permission to execute Step 9; the live
rollout remains separately gated.

#### 2026-08-02 — Additive Author-Evidenz zur adversarial Rollout-Remediation

- Dieser Abschnitt ersetzt keine historische Passage. Er dokumentiert die
  vorrangigen Korrekturen des separaten Read-only-Gegenreviews; Remote-,
  Runtime-, Cloudflare- und Upstream-Arbeiten bleiben weiterhin unberührt.
- Task 3 erzeugt lokal genau einen deterministischen Mergecommit mit dem Tree
  des geprüften Heads und den geordneten Eltern `base, head`. Ein read-only
  Ruleset-/Classic-Protection-Gate stoppt bei einem vorgeschriebenen anderen
  Mergepfad. Ein einziger atomarer Push bindet `main` und den streng validierten
  PR-Branch mit exakten Leases, aktualisiert `main` und löscht denselben
  geprüften Head; anschließend müssen Remote-Main, indirekter GitHub-PR-Merge,
  Commit-OID, Tree und beide Eltern exakt übereinstimmen.
- Die additive Runtime-Klarstellung verbietet jede Task-3-Änderung am lokalen
  Runtime-Checkout. Das eng begrenzte Ownership-Gate ist die einzige
  Vor-Task-4-Mutation; `HEAD != target_sha` bleibt bis zum geschützten Task-4-CAS
  verpflichtend.
- Der normative Step 9 enthält die vollständigen Step-5- und Step-6-Smokes
  bytegleich in demselben Codeblock. Der Marker-Produzent liegt nachweislich
  vor seinem Konsumenten; kein manueller Einfügeplatzhalter bleibt.
- Rollback disarmt nur die rekursive EXIT-Behandlung und ignoriert HUP/INT/TERM
  bis Restore oder Fail-close und Settings-Lock-Freigabe abgeschlossen sind.
  Step 10 sendet real TERM, blockiert die Recovery unter Lock, sendet danach
  HUP und beweist Status `143`, abgeschlossene Recovery und Lockfreigabe.
- Der erweiterte disposable Harness beweist zusätzlich Admin/Timer inaktiv,
  Service- und Timer-`masked-runtime`, unveränderte persistente
  Timer-Enablement-Semantik, Markerreihenfolge sowie echte Base- und
  Head-Lease-Races gegen einen lokalen Bare-Remote. Beide Races bleiben atomar
  ohne Teilupdate; nur das exakte Paar setzt Main und löscht den Head.
- Test-first-Evidenz: Der neue Vertragstest lief initial mit vier gezielten
  Fehlern bei sechs Tests rot; die nachträglich geforderte `make check`-Bindung
  lief separat rot, während Task-3/9/10-Syntax bereits grün blieb. Der aktuelle
  Stand besteht `tests.test_rollout_plan_contract` mit `7/7`.
- Frische Gesamtverifikation: `make check` Exit 0; Applet-Runtime grün,
  Admin-UI `24/24`, SemVer `8/8`, Git-Object-Fallback `3/3`,
  Release-Publication `3/3`, Helper-Environment `7/7`, Applet-Sync `25/25`,
  Settings-Schema `14/14`, Story-Directives `31/31` und Rollout-Vertrag `7/7`.
  Der neue Vertragstest ist dauerhaft im Makefile und damit im vorhandenen
  GitHub-CI-Pfad verankert. Es wurde keine Produktions- oder Weblogik geändert;
  deshalb war kein erneuter Siteprofil-Build Teil dieser fokussierten Runde.

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
set -Eeuo pipefail
test "$(id -u)" = 0
/usr/sbin/runuser -u teladi -- /usr/bin/env -i \
  HOME=/home/teladi \
  USER=teladi \
  LOGNAME=teladi \
  PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
  LANG=C.UTF-8 \
  LC_ALL=C.UTF-8 \
  GIT_TERMINAL_PROMPT=0 \
  GIT_ASKPASS=/bin/false \
  SSH_ASKPASS=/bin/false \
  /bin/bash -se <<'TASK5_STEP1_TELADI'
set -Eeuo pipefail
test "$(id -u)" = 1000
test "$(id -g)" = 1000
receipt_file=/home/teladi/.local/state/wirtelprimpf/task3-merge/generator-main-receipt.json
generator_runtime=/home/teladi/.local/share/wirtelprimpf-generator
archive_checkout=/home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001
canonical_generator_origin=https://github.com/H234598/Wirtelprimpf-generator.git
canonical_archive_origin=https://github.com/H234598/Wirtelprimpf-0001.git

# BEGIN TASK5_FACTORY_RECEIPT
load_verified_task3_factory_sha() {
  test -f "$receipt_file" && test ! -L "$receipt_file"
  test "$(stat -c '%u:%g:%a' "$receipt_file")" = 1000:1000:600
  /usr/bin/jq -e '
    keys == [
      "actor_id", "actor_login", "base_before", "canonical_origin",
      "expected_head", "head_ref", "head_tree", "merge_date",
      "merge_message", "merge_sha", "pr_number", "repository",
      "repository_id", "review_author_id", "review_author_login",
      "review_commit", "review_id", "review_state", "state", "version"
    ]
    and .version == 3 and .state == "verified"
    and .actor_login == "H234598" and .actor_id == 54270221
    and .repository_id == "R_kgDOTpr2BA"
    and .repository == "H234598/Wirtelprimpf-generator"
    and .canonical_origin == "https://github.com/H234598/Wirtelprimpf-generator.git"
    and (.pr_number | type == "number" and . > 0 and floor == .)
    and (.expected_head | type == "string" and test("^[0-9a-f]{40}$"))
    and (.base_before | type == "string" and test("^[0-9a-f]{40}$"))
    and (.head_tree | type == "string" and test("^[0-9a-f]{40}$"))
    and (.merge_sha | type == "string" and test("^[0-9a-f]{40}$"))
    and (.review_id | type == "number" and . > 0 and floor == .)
    and .review_author_login == "coderabbitai[bot]"
    and .review_author_id == 136622811
    and .review_commit == .expected_head
    and .review_state == "APPROVED"
  ' "$receipt_file" >/dev/null
  /usr/bin/jq -r '.merge_sha' "$receipt_file"
}
# END TASK5_FACTORY_RECEIPT

# BEGIN TASK5_GIT_CONFIG_GUARD
assert_safe_local_git_config() {
  local repository_path="$1" unsafe_keys
  unsafe_keys="$(
    /usr/bin/git -C "$repository_path" config --local --name-only \
      --get-regexp \
      '^(include\..*|includeif\..*|url\..*\.(insteadof|pushinsteadof)|http\..*|protocol\..*|alias\..*|credential\..*|core\.(askpass|hookspath|sshcommand|gitproxy|fsmonitor)|remote\..*\.(proxy|vcs|receivepack|uploadpack|pushurl))$' \
      || :
  )"
  test -z "$unsafe_keys" || {
    printf 'Unsafe local Git configuration rejected.\n' >&2
    return 1
  }
}

task5_git_remote() {
  local operation="${1:-}" argument canonical_url_count=0
  case "$operation" in fetch|ls-remote|push) ;; *) return 1 ;; esac
  for argument in "$@"; do
    [[ "$argument" == "$canonical_origin" ]] && \
      canonical_url_count=$((canonical_url_count + 1))
  done
  test "$canonical_url_count" = 1
  assert_safe_local_git_config "$task5_git_repository"
  /usr/bin/env -i \
    HOME=/home/teladi USER=teladi LOGNAME=teladi \
    PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
    GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
    GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/false SSH_ASKPASS=/bin/false \
    /usr/bin/git \
      -c http.extraHeader= -c "http.$canonical_origin.extraHeader=" \
      -c http.proxy= -c http.sslVerify=true \
      -c http.curloptResolve= -c credential.helper= \
      -c core.askPass=/bin/false -c core.hooksPath=/dev/null \
      -c core.fsmonitor=false -c core.sshCommand=/bin/false \
      -c core.gitProxy=/bin/false -c protocol.allow=never \
      -c protocol.https.allow=always -c protocol.ext.allow=never \
      -C "$task5_git_repository" "$@"
}
# END TASK5_GIT_CONFIG_GUARD

generator_factory_sha="$(load_verified_task3_factory_sha)"
[[ "$generator_factory_sha" =~ ^[0-9a-f]{40}$ ]]
test -d "$generator_runtime" && test ! -L "$generator_runtime"
test "$(realpath -e -- "$generator_runtime")" = "$generator_runtime"
test -z "$(find "$generator_runtime" -xdev \
  \( ! -user teladi -o ! -group teladi \) -print -quit)"
test "$generator_factory_sha" = \
  "$(/usr/bin/git -C "$generator_runtime" rev-parse HEAD)"
test "$generator_factory_sha" = \
  "$(/usr/bin/git -C "$generator_runtime" rev-parse origin/main)"
task5_git_repository=$generator_runtime
canonical_origin=$canonical_generator_origin
test "$generator_factory_sha" = \
  "$(task5_git_remote ls-remote "$canonical_origin" refs/heads/main | cut -f1)"

test -d "$archive_checkout" && test ! -L "$archive_checkout"
test "$(realpath -e -- "$archive_checkout")" = "$archive_checkout"
test -z "$(find "$archive_checkout" -xdev \
  \( ! -user teladi -o ! -group teladi \) -print -quit)"
test "$(/usr/bin/git -C "$archive_checkout" remote get-url origin)" = \
  "$canonical_archive_origin"
archive_dirty="$(/usr/bin/git -C "$archive_checkout" status --porcelain)"
if [[ -n "$archive_dirty" ]]; then
  printf 'Archive checkout is not clean before synchronization.\n' >&2
  printf '%s\n' "$archive_dirty" >&2
  exit 1
fi
task5_git_repository=$archive_checkout
canonical_origin=$canonical_archive_origin
task5_git_remote fetch "$canonical_origin" \
  '+refs/heads/main:refs/remotes/origin/main'
/usr/bin/git -C "$archive_checkout" switch main
test "$(/usr/bin/git -C "$archive_checkout" rev-parse HEAD)" = \
  "$(/usr/bin/git -C "$archive_checkout" rev-parse origin/main)"
test -z "$(/usr/bin/git -C "$archive_checkout" status --porcelain)"
/usr/bin/git -C "$archive_checkout" switch -c chore/pin-transactional-site-factory
TASK5_STEP1_TELADI
```

Expected: clean checkout; stop if unrelated user changes appear.

- [ ] **Step 2: Resolve and validate the immutable factory SHA**

Run:

```bash
set -Eeuo pipefail
test "$(id -u)" = 0
/usr/sbin/runuser -u teladi -- /usr/bin/env -i \
  HOME=/home/teladi \
  USER=teladi \
  LOGNAME=teladi \
  PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
  LANG=C.UTF-8 \
  LC_ALL=C.UTF-8 \
  GIT_TERMINAL_PROMPT=0 \
  GIT_ASKPASS=/bin/false \
  SSH_ASKPASS=/bin/false \
  /bin/bash -se <<'TASK5_STEP2_TELADI'
set -Eeuo pipefail
test "$(id -u)" = 1000
test "$(id -g)" = 1000
receipt_file=/home/teladi/.local/state/wirtelprimpf/task3-merge/generator-main-receipt.json
generator_runtime=/home/teladi/.local/share/wirtelprimpf-generator
canonical_origin=https://github.com/H234598/Wirtelprimpf-generator.git

# BEGIN TASK5_FACTORY_RECEIPT
load_verified_task3_factory_sha() {
  test -f "$receipt_file" && test ! -L "$receipt_file"
  test "$(stat -c '%u:%g:%a' "$receipt_file")" = 1000:1000:600
  /usr/bin/jq -e '
    keys == [
      "actor_id", "actor_login", "base_before", "canonical_origin",
      "expected_head", "head_ref", "head_tree", "merge_date",
      "merge_message", "merge_sha", "pr_number", "repository",
      "repository_id", "review_author_id", "review_author_login",
      "review_commit", "review_id", "review_state", "state", "version"
    ]
    and .version == 3 and .state == "verified"
    and .actor_login == "H234598" and .actor_id == 54270221
    and .repository_id == "R_kgDOTpr2BA"
    and .repository == "H234598/Wirtelprimpf-generator"
    and .canonical_origin == "https://github.com/H234598/Wirtelprimpf-generator.git"
    and (.pr_number | type == "number" and . > 0 and floor == .)
    and (.expected_head | type == "string" and test("^[0-9a-f]{40}$"))
    and (.base_before | type == "string" and test("^[0-9a-f]{40}$"))
    and (.head_tree | type == "string" and test("^[0-9a-f]{40}$"))
    and (.merge_sha | type == "string" and test("^[0-9a-f]{40}$"))
    and (.review_id | type == "number" and . > 0 and floor == .)
    and .review_author_login == "coderabbitai[bot]"
    and .review_author_id == 136622811
    and .review_commit == .expected_head
    and .review_state == "APPROVED"
  ' "$receipt_file" >/dev/null
  /usr/bin/jq -r '.merge_sha' "$receipt_file"
}
# END TASK5_FACTORY_RECEIPT

# BEGIN TASK5_GIT_CONFIG_GUARD
assert_safe_local_git_config() {
  local repository_path="$1" unsafe_keys
  unsafe_keys="$(
    /usr/bin/git -C "$repository_path" config --local --name-only \
      --get-regexp \
      '^(include\..*|includeif\..*|url\..*\.(insteadof|pushinsteadof)|http\..*|protocol\..*|alias\..*|credential\..*|core\.(askpass|hookspath|sshcommand|gitproxy|fsmonitor)|remote\..*\.(proxy|vcs|receivepack|uploadpack|pushurl))$' \
      || :
  )"
  test -z "$unsafe_keys" || return 1
}
task5_git_remote() {
  local operation="${1:-}" argument canonical_url_count=0
  case "$operation" in fetch|ls-remote|push) ;; *) return 1 ;; esac
  for argument in "$@"; do
    [[ "$argument" == "$canonical_origin" ]] && \
      canonical_url_count=$((canonical_url_count + 1))
  done
  test "$canonical_url_count" = 1
  assert_safe_local_git_config "$task5_git_repository"
  /usr/bin/env -i \
    HOME=/home/teladi USER=teladi LOGNAME=teladi \
    PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
    GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
    GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/false SSH_ASKPASS=/bin/false \
    /usr/bin/git \
      -c http.extraHeader= -c "http.$canonical_origin.extraHeader=" \
      -c http.proxy= -c http.sslVerify=true \
      -c http.curloptResolve= -c credential.helper= \
      -c core.askPass=/bin/false -c core.hooksPath=/dev/null \
      -c core.fsmonitor=false -c core.sshCommand=/bin/false \
      -c core.gitProxy=/bin/false -c protocol.allow=never \
      -c protocol.https.allow=always -c protocol.ext.allow=never \
      -C "$task5_git_repository" "$@"
}
# END TASK5_GIT_CONFIG_GUARD

test -d "$generator_runtime" && test ! -L "$generator_runtime"
test "$(realpath -e -- "$generator_runtime")" = "$generator_runtime"
test -z "$(find "$generator_runtime" -xdev \
  \( ! -user teladi -o ! -group teladi \) -print -quit)"
test "$(( $(/usr/bin/git -C "$generator_runtime" remote get-url --all origin | wc -l) ))" = 1
test "$(/usr/bin/git -C "$generator_runtime" remote get-url origin)" = "$canonical_origin"
generator_factory_sha="$(load_verified_task3_factory_sha)"
[[ "$generator_factory_sha" =~ ^[0-9a-f]{40}$ ]]
test "$generator_factory_sha" = \
  "$(/usr/bin/git -C "$generator_runtime" rev-parse HEAD)"
test "$generator_factory_sha" = \
  "$(/usr/bin/git -C "$generator_runtime" rev-parse origin/main)"
task5_git_repository=$generator_runtime
test "$generator_factory_sha" = \
  "$(task5_git_remote ls-remote "$canonical_origin" refs/heads/main | cut -f1)"
printf '%s\n' "$generator_factory_sha"
TASK5_STEP2_TELADI
```

Expected: one valid SHA equal to merged generator main.

- [ ] **Step 3: Replace both old pins with the validated literal inside the teladi fence**

Run the following exact, mechanically bounded replacement. It derives the SHA
again inside the unexpanded `teladi` child, requires exactly the two intended
old SHA fields, rejects symlinks/wrong ownership/wrong mode, and atomically
replaces only `pages.yml`:

```bash
set -Eeuo pipefail
test "$(id -u)" = 0
/usr/sbin/runuser -u teladi -- /usr/bin/env -i \
  HOME=/home/teladi \
  USER=teladi \
  LOGNAME=teladi \
  PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
  LANG=C.UTF-8 \
  LC_ALL=C.UTF-8 \
  GIT_TERMINAL_PROMPT=0 \
  GIT_ASKPASS=/bin/false \
  SSH_ASKPASS=/bin/false \
  /bin/bash -se <<'TASK5_STEP3_TELADI'
set -Eeuo pipefail
test "$(id -u)" = 1000
test "$(id -g)" = 1000
generator_checkout=/home/teladi/.local/share/wirtelprimpf-generator
archive_checkout=/home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001
workflow="$archive_checkout/.github/workflows/pages.yml"
receipt_file=/home/teladi/.local/state/wirtelprimpf/task3-merge/generator-main-receipt.json
canonical_origin=https://github.com/H234598/Wirtelprimpf-generator.git

# BEGIN TASK5_FACTORY_RECEIPT
load_verified_task3_factory_sha() {
  test -f "$receipt_file" && test ! -L "$receipt_file"
  test "$(stat -c '%u:%g:%a' "$receipt_file")" = 1000:1000:600
  /usr/bin/jq -e '
    keys == [
      "actor_id", "actor_login", "base_before", "canonical_origin",
      "expected_head", "head_ref", "head_tree", "merge_date",
      "merge_message", "merge_sha", "pr_number", "repository",
      "repository_id", "review_author_id", "review_author_login",
      "review_commit", "review_id", "review_state", "state", "version"
    ]
    and .version == 3 and .state == "verified"
    and .actor_login == "H234598" and .actor_id == 54270221
    and .repository_id == "R_kgDOTpr2BA"
    and .repository == "H234598/Wirtelprimpf-generator"
    and .canonical_origin == "https://github.com/H234598/Wirtelprimpf-generator.git"
    and (.pr_number | type == "number" and . > 0 and floor == .)
    and (.expected_head | test("^[0-9a-f]{40}$"))
    and (.base_before | test("^[0-9a-f]{40}$"))
    and (.head_tree | test("^[0-9a-f]{40}$"))
    and (.merge_sha | test("^[0-9a-f]{40}$"))
    and (.review_id | type == "number" and . > 0 and floor == .)
    and .review_author_login == "coderabbitai[bot]"
    and .review_author_id == 136622811
    and .review_commit == .expected_head
    and .review_state == "APPROVED"
  ' "$receipt_file" >/dev/null
  /usr/bin/jq -r '.merge_sha' "$receipt_file"
}
# END TASK5_FACTORY_RECEIPT

# BEGIN TASK5_GIT_CONFIG_GUARD
assert_safe_local_git_config() {
  local repository_path="$1" unsafe_keys
  unsafe_keys="$(/usr/bin/git -C "$repository_path" config --local --name-only \
    --get-regexp '^(include\..*|includeif\..*|url\..*\.(insteadof|pushinsteadof)|http\..*|protocol\..*|alias\..*|credential\..*|core\.(askpass|hookspath|sshcommand|gitproxy|fsmonitor)|remote\..*\.(proxy|vcs|receivepack|uploadpack|pushurl))$' || :)"
  test -z "$unsafe_keys"
}
task5_git_remote() {
  local operation="${1:-}" argument canonical_url_count=0
  case "$operation" in fetch|ls-remote|push) ;; *) return 1 ;; esac
  for argument in "$@"; do
    [[ "$argument" == "$canonical_origin" ]] && canonical_url_count=$((canonical_url_count + 1))
  done
  test "$canonical_url_count" = 1
  assert_safe_local_git_config "$task5_git_repository"
  /usr/bin/env -i HOME=/home/teladi USER=teladi LOGNAME=teladi \
    PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
    GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
    GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/false SSH_ASKPASS=/bin/false \
    /usr/bin/git -c http.extraHeader= \
      -c "http.$canonical_origin.extraHeader=" -c http.proxy= \
      -c http.sslVerify=true \
      -c http.curloptResolve= -c credential.helper= \
      -c core.askPass=/bin/false -c core.hooksPath=/dev/null \
      -c core.fsmonitor=false -c core.sshCommand=/bin/false \
      -c core.gitProxy=/bin/false -c protocol.allow=never \
      -c protocol.https.allow=always -c protocol.ext.allow=never \
      -C "$task5_git_repository" "$@"
}
# END TASK5_GIT_CONFIG_GUARD

test -d "$generator_checkout" && test ! -L "$generator_checkout"
test -d "$archive_checkout" && test ! -L "$archive_checkout"
test "$(realpath -e -- "$archive_checkout")" = "$archive_checkout"
test -z "$(find "$archive_checkout" -xdev \
  \( ! -user teladi -o ! -group teladi \) -print -quit)"
generator_factory_sha="$(load_verified_task3_factory_sha)"
[[ "$generator_factory_sha" =~ ^[0-9a-f]{40}$ ]]
test "$(/usr/bin/git -C "$generator_checkout" remote get-url origin)" = \
  "$canonical_origin"
test "$generator_factory_sha" = \
  "$(/usr/bin/git -C "$generator_checkout" rev-parse HEAD)"
test "$generator_factory_sha" = \
  "$(/usr/bin/git -C "$generator_checkout" rev-parse origin/main)"
task5_git_repository=$generator_checkout
test "$generator_factory_sha" = \
  "$(task5_git_remote ls-remote "$canonical_origin" refs/heads/main | cut -f1)"
/usr/bin/python3 - "$workflow" "$generator_factory_sha" <<'TASK5_REWRITE_PY'
import os
import re
import stat
import sys
from pathlib import Path

workflow = Path(sys.argv[1])
new_sha = sys.argv[2]
if not re.fullmatch(r"[0-9a-f]{40}", new_sha):
    raise SystemExit("invalid immutable generator SHA")
st = workflow.lstat()
if not stat.S_ISREG(st.st_mode) or not (st.st_uid == 1000 and st.st_gid == 1000):
    raise SystemExit("archive workflow must be a teladi-owned regular file")
if stat.S_IMODE(st.st_mode) != 0o644:
    raise SystemExit("archive workflow mode must be 0644")
original = workflow.read_text(encoding="utf-8")
patterns = (
    re.compile(
        r"(?m)^(\s*uses:\s+H234598/Wirtelprimpf-generator/"
        r"\.github/workflows/archive-pages\.yml@)([0-9a-f]{40})(\s*)$"
    ),
    re.compile(r'(?m)^(\s*factory_ref:\s*")([0-9a-f]{40})("\s*)$'),
)
matches = [list(pattern.finditer(original)) for pattern in patterns]
old_count = sum(len(group) for group in matches)
if old_count != 2 or any(len(group) != 1 for group in matches):
    raise SystemExit("archive workflow does not contain exactly the two pin fields")
old_values = [group[0].group(2) for group in matches]
if old_values == [new_sha, new_sha]:
    raise SystemExit("archive workflow is already pinned to the requested SHA")
updated = original
for pattern in patterns:
    updated = pattern.sub(lambda match: f"{match.group(1)}{new_sha}{match.group(3)}", updated)
new_count = len(re.findall(re.escape(new_sha), updated))
if new_count != 2 or re.findall(r"[0-9a-f]{40}", updated) != [new_sha, new_sha]:
    raise SystemExit("archive workflow pin replacement was not exact")
part = workflow.with_name(f".{workflow.name}.{os.getpid()}.part")
try:
    descriptor = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
        handle.write(updated)
        handle.flush()
        os.fsync(handle.fileno())
        os.fchmod(handle.fileno(), 0o644)
    os.replace(part, workflow)
    directory_fd = os.open(workflow.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
finally:
    part.unlink(missing_ok=True)
TASK5_REWRITE_PY
TASK5_STEP3_TELADI
```

Do not change triggers, permissions, archive index, custom domain, or any
content file. The earlier unqualified `apply_patch` direction is superseded by
this executable UID/GID-bound replacement because root must not expand or
write the archive path, arguments, or contents.

- [ ] **Step 4: Validate the two pins and exact diff**

Run:

```bash
set -Eeuo pipefail
test "$(id -u)" = 0
/usr/sbin/runuser -u teladi -- /usr/bin/env -i \
  HOME=/home/teladi \
  USER=teladi \
  LOGNAME=teladi \
  PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
  LANG=C.UTF-8 \
  LC_ALL=C.UTF-8 \
  GIT_TERMINAL_PROMPT=0 \
  GIT_ASKPASS=/bin/false \
  SSH_ASKPASS=/bin/false \
  /bin/bash -se <<'TASK5_STEP4_TELADI'
set -Eeuo pipefail
test "$(id -u)" = 1000
test "$(id -g)" = 1000
generator_checkout=/home/teladi/.local/share/wirtelprimpf-generator
archive_checkout=/home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001
workflow="$archive_checkout/.github/workflows/pages.yml"
receipt_file=/home/teladi/.local/state/wirtelprimpf/task3-merge/generator-main-receipt.json
canonical_origin=https://github.com/H234598/Wirtelprimpf-generator.git

# BEGIN TASK5_FACTORY_RECEIPT
load_verified_task3_factory_sha() {
  test -f "$receipt_file" && test ! -L "$receipt_file"
  test "$(stat -c '%u:%g:%a' "$receipt_file")" = 1000:1000:600
  /usr/bin/jq -e '
    keys == [
      "actor_id", "actor_login", "base_before", "canonical_origin",
      "expected_head", "head_ref", "head_tree", "merge_date",
      "merge_message", "merge_sha", "pr_number", "repository",
      "repository_id", "review_author_id", "review_author_login",
      "review_commit", "review_id", "review_state", "state", "version"
    ]
    and .version == 3 and .state == "verified"
    and .actor_login == "H234598" and .actor_id == 54270221
    and .repository_id == "R_kgDOTpr2BA"
    and .repository == "H234598/Wirtelprimpf-generator"
    and .canonical_origin == "https://github.com/H234598/Wirtelprimpf-generator.git"
    and (.pr_number | type == "number" and . > 0 and floor == .)
    and (.expected_head | type == "string" and test("^[0-9a-f]{40}$"))
    and (.base_before | type == "string" and test("^[0-9a-f]{40}$"))
    and (.head_tree | type == "string" and test("^[0-9a-f]{40}$"))
    and (.merge_sha | type == "string" and test("^[0-9a-f]{40}$"))
    and (.review_id | type == "number" and . > 0 and floor == .)
    and .review_author_login == "coderabbitai[bot]"
    and .review_author_id == 136622811
    and .review_commit == .expected_head
    and .review_state == "APPROVED"
  ' "$receipt_file" >/dev/null
  /usr/bin/jq -r '.merge_sha' "$receipt_file"
}
# END TASK5_FACTORY_RECEIPT

# BEGIN TASK5_GIT_CONFIG_GUARD
assert_safe_local_git_config() {
  local repository_path="$1" unsafe_keys
  unsafe_keys="$(/usr/bin/git -C "$repository_path" config --local --name-only \
    --get-regexp '^(include\..*|includeif\..*|url\..*\.(insteadof|pushinsteadof)|http\..*|protocol\..*|alias\..*|credential\..*|core\.(askpass|hookspath|sshcommand|gitproxy|fsmonitor)|remote\..*\.(proxy|vcs|receivepack|uploadpack|pushurl))$' || :)"
  test -z "$unsafe_keys"
}
task5_git_remote() {
  local operation="${1:-}" argument canonical_url_count=0
  case "$operation" in fetch|ls-remote|push) ;; *) return 1 ;; esac
  for argument in "$@"; do
    [[ "$argument" == "$canonical_origin" ]] && canonical_url_count=$((canonical_url_count + 1))
  done
  test "$canonical_url_count" = 1
  assert_safe_local_git_config "$task5_git_repository"
  /usr/bin/env -i HOME=/home/teladi USER=teladi LOGNAME=teladi \
    PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
    GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
    GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/false SSH_ASKPASS=/bin/false \
    /usr/bin/git -c http.extraHeader= \
      -c "http.$canonical_origin.extraHeader=" -c http.proxy= \
      -c http.sslVerify=true \
      -c http.curloptResolve= -c credential.helper= \
      -c core.askPass=/bin/false -c core.hooksPath=/dev/null \
      -c core.fsmonitor=false -c core.sshCommand=/bin/false \
      -c core.gitProxy=/bin/false -c protocol.allow=never \
      -c protocol.https.allow=always -c protocol.ext.allow=never \
      -C "$task5_git_repository" "$@"
}
# END TASK5_GIT_CONFIG_GUARD

test -d "$archive_checkout" && test ! -L "$archive_checkout"
test "$(realpath -e -- "$archive_checkout")" = "$archive_checkout"
test -z "$(find "$archive_checkout" -xdev \
  \( ! -user teladi -o ! -group teladi \) -print -quit)"
test -d "$generator_checkout" && test ! -L "$generator_checkout"
test "$(realpath -e -- "$generator_checkout")" = "$generator_checkout"
test -z "$(find "$generator_checkout" -xdev \
  \( ! -user teladi -o ! -group teladi \) -print -quit)"
generator_factory_sha="$(load_verified_task3_factory_sha)"
[[ "$generator_factory_sha" =~ ^[0-9a-f]{40}$ ]]
test "$(/usr/bin/git -C "$generator_checkout" remote get-url origin)" = \
  "$canonical_origin"
test "$generator_factory_sha" = \
  "$(/usr/bin/git -C "$generator_checkout" rev-parse HEAD)"
test "$generator_factory_sha" = \
  "$(/usr/bin/git -C "$generator_checkout" rev-parse origin/main)"
task5_git_repository=$generator_checkout
test "$generator_factory_sha" = \
  "$(task5_git_remote ls-remote "$canonical_origin" refs/heads/main | cut -f1)"
test "$(/usr/bin/rg -o -- '[0-9a-f]{40}' "$workflow" | sort -u | wc -l)" -eq 1
test "$(/usr/bin/rg -o -F -- "$generator_factory_sha" "$workflow" | wc -l)" -eq 2
/usr/bin/rg -F -- "$generator_factory_sha" "$workflow"
test "$(/usr/bin/git -C "$archive_checkout" diff --name-only)" = \
  .github/workflows/pages.yml
test "$(/usr/bin/git -C "$archive_checkout" diff --numstat)" = \
  $'2\t2\t.github/workflows/pages.yml'
/usr/bin/git -C "$archive_checkout" diff --check
/usr/bin/git -C "$archive_checkout" diff -- .github/workflows/pages.yml
TASK5_STEP4_TELADI
```

Expected: exactly two occurrences of one SHA and a two-line value-only diff.

- [ ] **Step 5: Commit the isolated archive pin and open its pull request**

Run:

```bash
set -Eeuo pipefail
test "$(id -u)" = 0
set +x
if [[ -z "${GH_TOKEN:-}" ]]; then
  printf 'A valid ephemeral GH_TOKEN is required before archive writes.\n' >&2
  exit 1
fi
task5_ephemeral_token=$GH_TOKEN
unset GH_TOKEN
task5_token_call() {
  set +x
  local task5_token_status=0
  printf '%s\0' "$task5_ephemeral_token" |
    /usr/bin/env -i \
      HOME=/root \
      PATH=/usr/local/bin:/usr/bin:/bin \
      GIT_CONFIG_NOSYSTEM=1 \
      GIT_CONFIG_GLOBAL=/dev/null \
      GIT_TERMINAL_PROMPT=0 \
      GIT_ASKPASS=/bin/false \
      SSH_ASKPASS=/bin/false \
      /bin/bash -c '
        set -Eeuo pipefail
        set +x
        task5_call_token=
        IFS= read -r -d "" task5_call_token
        exec 0<&-
        GH_TOKEN="$task5_call_token" exec "$@"
      ' task5-token-call "$@" || task5_token_status=$?
  return "$task5_token_status"
}
task5_gh() {
  task5_token_call /usr/bin/gh "$@"
}
canonical_archive_repository=H234598/Wirtelprimpf-0001
canonical_archive_repo_id=R_kgDOSg7oRg
test "$(task5_gh api /user --jq '.login + ":" + (.id | tostring)')" = H234598:54270221
archive_repository_json="$(task5_gh repo view "$canonical_archive_repository" \
  --json id,nameWithOwner)"
/usr/bin/jq -e --arg id "$canonical_archive_repo_id" \
  --arg name "$canonical_archive_repository" \
  '.id == $id and .nameWithOwner == $name' \
  <<<"$archive_repository_json" >/dev/null
exec {task5_token_relay_fd}< <(printf '%s\0' "$task5_ephemeral_token")

set +e
task5_archive_facts="$(
  /usr/sbin/runuser -u teladi -- /usr/bin/env -i \
    HOME=/home/teladi \
    USER=teladi \
    LOGNAME=teladi \
    PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    /bin/bash -se "$task5_token_relay_fd" <<'TASK5_STEP5_TELADI'
set -Eeuo pipefail
set +x
test "$(id -u)" = 1000
test "$(id -g)" = 1000
task5_token_relay_fd=$1
[[ "$task5_token_relay_fd" =~ ^[0-9]+$ ]]
task5_ephemeral_token=
IFS= read -r -d '' task5_ephemeral_token <&"$task5_token_relay_fd"
exec {task5_token_relay_fd}<&-
test -n "$task5_ephemeral_token"
test -z "${GH_TOKEN+x}"
archive_checkout=/home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001
canonical_origin=https://github.com/H234598/Wirtelprimpf-0001.git
generator_checkout=/home/teladi/.local/share/wirtelprimpf-generator
canonical_generator_origin=https://github.com/H234598/Wirtelprimpf-generator.git
receipt_file=/home/teladi/.local/state/wirtelprimpf/task3-merge/generator-main-receipt.json

# BEGIN TASK5_FACTORY_RECEIPT
load_verified_task3_factory_sha() {
  test -f "$receipt_file" && test ! -L "$receipt_file"
  test "$(stat -c '%u:%g:%a' "$receipt_file")" = 1000:1000:600
  /usr/bin/jq -e '
    keys == [
      "actor_id", "actor_login", "base_before", "canonical_origin",
      "expected_head", "head_ref", "head_tree", "merge_date",
      "merge_message", "merge_sha", "pr_number", "repository",
      "repository_id", "review_author_id", "review_author_login",
      "review_commit", "review_id", "review_state", "state", "version"
    ]
    and .version == 3 and .state == "verified"
    and .actor_login == "H234598" and .actor_id == 54270221
    and .repository_id == "R_kgDOTpr2BA"
    and .repository == "H234598/Wirtelprimpf-generator"
    and .canonical_origin == "https://github.com/H234598/Wirtelprimpf-generator.git"
    and (.pr_number | type == "number" and . > 0 and floor == .)
    and (.expected_head | type == "string" and test("^[0-9a-f]{40}$"))
    and (.base_before | type == "string" and test("^[0-9a-f]{40}$"))
    and (.head_tree | type == "string" and test("^[0-9a-f]{40}$"))
    and (.merge_sha | type == "string" and test("^[0-9a-f]{40}$"))
    and (.review_id | type == "number" and . > 0 and floor == .)
    and .review_author_login == "coderabbitai[bot]"
    and .review_author_id == 136622811
    and .review_commit == .expected_head
    and .review_state == "APPROVED"
  ' "$receipt_file" >/dev/null
  /usr/bin/jq -r '.merge_sha' "$receipt_file"
}
# END TASK5_FACTORY_RECEIPT

test -d "$archive_checkout" && test ! -L "$archive_checkout"
test "$(realpath -e -- "$archive_checkout")" = "$archive_checkout"
test -z "$(find "$archive_checkout" -xdev \
  \( ! -user teladi -o ! -group teladi \) -print -quit)"
test "$(/usr/bin/git -C "$archive_checkout" branch --show-current)" = \
  chore/pin-transactional-site-factory
test "$(/usr/bin/git -C "$archive_checkout" remote get-url origin)" = "$canonical_origin"
test "$(/usr/bin/git -C "$archive_checkout" diff --name-only)" = \
  .github/workflows/pages.yml

generator_factory_sha="$(load_verified_task3_factory_sha)"
[[ "$generator_factory_sha" =~ ^[0-9a-f]{40}$ ]]
test -d "$generator_checkout" && test ! -L "$generator_checkout"
test -z "$(find "$generator_checkout" -xdev \
  \( ! -user teladi -o ! -group teladi \) -print -quit)"
test "$generator_factory_sha" = \
  "$(/usr/bin/git -C "$generator_checkout" rev-parse HEAD)"
test "$generator_factory_sha" = \
  "$(/usr/bin/git -C "$generator_checkout" rev-parse origin/main)"
test "$(/usr/bin/rg -o -F -- "$generator_factory_sha" \
  "$archive_checkout/.github/workflows/pages.yml" | wc -l)" = 2

task5_token_call() {
  set +x
  local task5_token_status=0
  printf '%s\0' "$task5_ephemeral_token" |
    /usr/bin/env -i \
      HOME=/home/teladi \
      USER=teladi \
      LOGNAME=teladi \
      PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
      GIT_CONFIG_NOSYSTEM=1 \
      GIT_CONFIG_GLOBAL=/dev/null \
      GIT_TERMINAL_PROMPT=0 \
      GIT_ASKPASS=/bin/false \
      SSH_ASKPASS=/bin/false \
      /bin/bash -c '
        set -Eeuo pipefail
        set +x
        task5_call_token=
        IFS= read -r -d "" task5_call_token
        exec 0<&-
        GH_TOKEN="$task5_call_token" exec "$@"
      ' task5-token-call "$@" || task5_token_status=$?
  return "$task5_token_status"
}
# BEGIN TASK5_GIT_CONFIG_GUARD
assert_safe_local_git_config() {
  local repository_path="$1" unsafe_keys
  unsafe_keys="$(/usr/bin/git -C "$repository_path" config --local --name-only \
    --get-regexp '^(include\..*|includeif\..*|url\..*\.(insteadof|pushinsteadof)|http\..*|protocol\..*|alias\..*|credential\..*|core\.(askpass|hookspath|sshcommand|gitproxy|fsmonitor)|remote\..*\.(proxy|vcs|receivepack|uploadpack|pushurl))$' || :)"
  test -z "$unsafe_keys"
}
task5_git_remote() {
  local operation="${1:-}" argument canonical_url_count=0
  case "$operation" in fetch|ls-remote|push) ;; *) return 1 ;; esac
  for argument in "$@"; do
    [[ "$argument" == "$canonical_origin" ]] && canonical_url_count=$((canonical_url_count + 1))
  done
  test "$canonical_url_count" = 1
  assert_safe_local_git_config "$task5_git_repository"
  task5_token_call \
    /usr/bin/git \
      -c http.extraHeader= \
      -c "http.$canonical_origin.extraHeader=" \
      -c http.proxy= -c http.sslVerify=true \
      -c http.curloptResolve= \
      -c credential.helper= \
      -c credential.helper='!/usr/bin/gh auth git-credential' \
      -c core.askPass=/bin/false -c core.hooksPath=/dev/null \
      -c core.fsmonitor=false -c core.sshCommand=/bin/false \
      -c core.gitProxy=/bin/false -c protocol.allow=never \
      -c protocol.https.allow=always -c protocol.ext.allow=never \
      -C "$task5_git_repository" "$@"
}
# END TASK5_GIT_CONFIG_GUARD

task5_git_repository=$generator_checkout
canonical_origin=$canonical_generator_origin
test "$generator_factory_sha" = \
  "$(task5_git_remote ls-remote "$canonical_origin" refs/heads/main | cut -f1)"
canonical_origin=https://github.com/H234598/Wirtelprimpf-0001.git
task5_git_repository=$archive_checkout
archive_base_sha="$(/usr/bin/git -C "$archive_checkout" rev-parse origin/main)"
[[ "$archive_base_sha" =~ ^[0-9a-f]{40}$ ]]

/usr/bin/git -c core.hooksPath=/dev/null -C "$archive_checkout" \
  add -- .github/workflows/pages.yml
/usr/bin/git -c core.hooksPath=/dev/null -c user.name=H234598 \
  -c user.email=54270221+H234598@users.noreply.github.com \
  -C "$archive_checkout" commit -m 'chore(pages): pin transactional site factory' >&2
task5_git_remote push --set-upstream "$canonical_origin" \
  chore/pin-transactional-site-factory >&2
archive_head_sha="$(/usr/bin/git -C "$archive_checkout" rev-parse HEAD)"
[[ "$archive_head_sha" =~ ^[0-9a-f]{40}$ ]]
test "$(task5_git_remote ls-remote "$canonical_origin" refs/heads/main | cut -f1)" = \
  "$archive_base_sha"
test "$(task5_git_remote ls-remote "$canonical_origin" \
  refs/heads/chore/pin-transactional-site-factory | cut -f1)" = \
  "$archive_head_sha"
test "$(/usr/bin/git -C "$archive_checkout" diff --name-only origin/main...HEAD)" = \
  .github/workflows/pages.yml
test "$(/usr/bin/git -C "$archive_checkout" diff --numstat origin/main...HEAD)" = \
  $'2\t2\t.github/workflows/pages.yml'
if /usr/bin/rg -q -- '^\s*pull_request\s*:' \
  "$archive_checkout/.github/workflows/pages.yml"; then
  archive_has_pr_trigger=1
else
  archive_has_pr_trigger=0
fi
unset task5_ephemeral_token
printf '%s\n%s\n' "$archive_head_sha" "$archive_has_pr_trigger"
TASK5_STEP5_TELADI
)"
task5_step5_status=$?
set -e
exec {task5_token_relay_fd}<&-
test "$task5_step5_status" = 0
archive_head_sha="${task5_archive_facts%%$'\n'*}"
archive_has_pr_trigger="${task5_archive_facts##*$'\n'}"
[[ "$archive_head_sha" =~ ^[0-9a-f]{40}$ ]]
[[ "$archive_has_pr_trigger" =~ ^[01]$ ]]

archive_pr_url="$(task5_gh pr create \
  --repo H234598/Wirtelprimpf-0001 \
  --base main \
  --head chore/pin-transactional-site-factory \
  --title 'Pin transactional Wirtelprimpf site factory' \
  --body 'Pins both reusable-workflow references to the reviewed immutable Wirtelprimpf-generator merge SHA. No story, media, DNS, or redirect content changes.')"
archive_pr_number="${archive_pr_url##*/}"
[[ "$archive_pr_number" =~ ^[0-9]+$ ]]
archive_pr_json="$(task5_gh pr view "$archive_pr_number" \
  --repo "$canonical_archive_repository" \
  --json state,headRefName,headRefOid,baseRefName,isDraft,isCrossRepository,headRepository)"
/usr/bin/jq -e --arg head "$archive_head_sha" \
  --arg repo_id "$canonical_archive_repo_id" '
    .state == "OPEN"
    and .headRefName == "chore/pin-transactional-site-factory"
    and .headRefOid == $head
    and .baseRefName == "main"
    and .isDraft == false
    and .isCrossRepository == false
    and .headRepository.id == $repo_id
    and .headRepository.nameWithOwner == "H234598/Wirtelprimpf-0001"
  ' <<<"$archive_pr_json" >/dev/null
archive_mergeable=UNKNOWN
for attempt in $(seq 1 15); do
  archive_mergeable="$(task5_gh pr view "$archive_pr_number" \
    --repo H234598/Wirtelprimpf-0001 --json mergeable --jq .mergeable)"
  case "$archive_mergeable" in
    MERGEABLE) break ;;
    CONFLICTING) printf 'Archive pin PR is conflicting.\n' >&2; exit 1 ;;
    UNKNOWN) sleep 2 ;;
    *) printf 'Unexpected mergeability state: %s\n' "$archive_mergeable" >&2; exit 1 ;;
  esac
done
test "$archive_mergeable" = MERGEABLE
test "$(task5_gh pr view "$archive_pr_number" --repo H234598/Wirtelprimpf-0001 \
  --json files --jq '.files[].path')" = .github/workflows/pages.yml
check_count="$(task5_gh pr view "$archive_pr_number" \
  --repo H234598/Wirtelprimpf-0001 \
  --json statusCheckRollup \
  --jq '.statusCheckRollup | length')"
if (( check_count > 0 )); then
  task5_gh pr checks "$archive_pr_number" \
    --repo H234598/Wirtelprimpf-0001 --watch --fail-fast
else
  printf '%s\n' 'No pull-request checks are configured for pages.yml; this is an accepted absence of PR CI, not a CI success.'
  test "$archive_has_pr_trigger" = 0
fi
unset task5_ephemeral_token
```

Expected: the PR head equals the reviewed local commit, GitHub reports it mergeable, the file list contains only `pages.yml`, and the committed diff is exactly two removed plus two added SHA-value lines. Every check that exists succeeds. Because the current `pages.yml` has no `pull_request` trigger, a genuine zero-check result is explicitly accepted only as **no PR CI configured**, never reported as CI success. The post-merge `main` Pages run in Step 6 is the real build/deploy gate.

- [ ] **Step 6: Merge and watch the exact archive Pages run**

Run:

```bash
set -Eeuo pipefail
test "$(id -u)" = 0
set +x
if [[ -z "${GH_TOKEN:-}" ]]; then
  printf 'A valid ephemeral GH_TOKEN is required before archive merge.\n' >&2
  exit 1
fi
task5_ephemeral_token=$GH_TOKEN
unset GH_TOKEN
task5_token_call() {
  set +x
  local task5_token_status=0
  printf '%s\0' "$task5_ephemeral_token" |
    /usr/bin/env -i \
      HOME=/root PATH=/usr/local/bin:/usr/bin:/bin \
      GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
      GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/false SSH_ASKPASS=/bin/false \
      /bin/bash -c '
        set -Eeuo pipefail
        set +x
        task5_call_token=
        IFS= read -r -d "" task5_call_token
        exec 0<&-
        GH_TOKEN="$task5_call_token" exec "$@"
      ' task5-token-call "$@" || task5_token_status=$?
  return "$task5_token_status"
}
task5_gh() { task5_token_call /usr/bin/gh "$@"; }
canonical_archive_repository=H234598/Wirtelprimpf-0001
canonical_archive_repo_id=R_kgDOSg7oRg
test "$(task5_gh api /user --jq '.login + ":" + (.id | tostring)')" = \
  H234598:54270221
archive_repository_json="$(task5_gh repo view "$canonical_archive_repository" \
  --json id,nameWithOwner)"
/usr/bin/jq -e --arg id "$canonical_archive_repo_id" \
  --arg name "$canonical_archive_repository" \
  '.id == $id and .nameWithOwner == $name' \
  <<<"$archive_repository_json" >/dev/null

task5_step6_local_gate() {
  /usr/sbin/runuser -u teladi -- /usr/bin/env -i \
    HOME=/home/teladi \
    USER=teladi \
    LOGNAME=teladi \
    PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    /bin/bash -se <<'TASK5_STEP6_TELADI'
set -Eeuo pipefail
test "$(id -u)" = 1000
test "$(id -g)" = 1000
archive_checkout=/home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001
generator_checkout=/home/teladi/.local/share/wirtelprimpf-generator
receipt_file=/home/teladi/.local/state/wirtelprimpf/task3-merge/generator-main-receipt.json
canonical_generator_origin=https://github.com/H234598/Wirtelprimpf-generator.git
canonical_archive_origin=https://github.com/H234598/Wirtelprimpf-0001.git

# BEGIN TASK5_STEP6_ARCHIVE_CONTENT_GATE
assert_task5_archive_candidate() {
  local repository_path="$1" base_sha="$2" head_sha="$3" factory_sha="$4"
  local workflow_text sha_lines
  [[ "$base_sha" =~ ^[0-9a-f]{40}$ ]]
  [[ "$head_sha" =~ ^[0-9a-f]{40}$ ]]
  [[ "$factory_sha" =~ ^[0-9a-f]{40}$ ]]
  test "$(/usr/bin/git -C "$repository_path" diff --name-only \
    "$base_sha...$head_sha")" = .github/workflows/pages.yml
  test "$(/usr/bin/git -C "$repository_path" diff --numstat \
    "$base_sha...$head_sha")" = $'2\t2\t.github/workflows/pages.yml'
  workflow_text="$(/usr/bin/git -C "$repository_path" \
    show "$head_sha:.github/workflows/pages.yml")"
  test "$(/usr/bin/rg -c -- \
    "^[[:space:]]*uses:[[:space:]]+H234598/Wirtelprimpf-generator/\\.github/workflows/archive-pages\\.yml@$factory_sha[[:space:]]*$" \
    <<<"$workflow_text")" = 1
  test "$(/usr/bin/rg -c -- \
    "^[[:space:]]*factory_ref:[[:space:]]*\"$factory_sha\"[[:space:]]*$" \
    <<<"$workflow_text")" = 1
  sha_lines="$(/usr/bin/rg -o -- '[0-9a-f]{40}' <<<"$workflow_text")"
  test "$sha_lines" = "$factory_sha"$'\n'"$factory_sha"
  if /usr/bin/rg -q -- '^[[:space:]]*pull_request[[:space:]]*:' \
    <<<"$workflow_text"; then
    printf '1\n'
  else
    printf '0\n'
  fi
}
# END TASK5_STEP6_ARCHIVE_CONTENT_GATE

# BEGIN TASK5_FACTORY_RECEIPT
load_verified_task3_factory_sha() {
  test -f "$receipt_file" && test ! -L "$receipt_file"
  test "$(stat -c '%u:%g:%a' "$receipt_file")" = 1000:1000:600
  /usr/bin/jq -e '
    keys == [
      "actor_id", "actor_login", "base_before", "canonical_origin",
      "expected_head", "head_ref", "head_tree", "merge_date",
      "merge_message", "merge_sha", "pr_number", "repository",
      "repository_id", "review_author_id", "review_author_login",
      "review_commit", "review_id", "review_state", "state", "version"
    ]
    and .version == 3 and .state == "verified"
    and .actor_login == "H234598" and .actor_id == 54270221
    and .repository_id == "R_kgDOTpr2BA"
    and .repository == "H234598/Wirtelprimpf-generator"
    and .canonical_origin == "https://github.com/H234598/Wirtelprimpf-generator.git"
    and (.pr_number | type == "number" and . > 0 and floor == .)
    and (.expected_head | type == "string" and test("^[0-9a-f]{40}$"))
    and (.base_before | type == "string" and test("^[0-9a-f]{40}$"))
    and (.head_tree | type == "string" and test("^[0-9a-f]{40}$"))
    and (.merge_sha | type == "string" and test("^[0-9a-f]{40}$"))
    and (.review_id | type == "number" and . > 0 and floor == .)
    and .review_author_login == "coderabbitai[bot]"
    and .review_author_id == 136622811
    and .review_commit == .expected_head
    and .review_state == "APPROVED"
  ' "$receipt_file" >/dev/null
  /usr/bin/jq -r '.merge_sha' "$receipt_file"
}
# END TASK5_FACTORY_RECEIPT

# BEGIN TASK5_GIT_CONFIG_GUARD
assert_safe_local_git_config() {
  local repository_path="$1" unsafe_keys
  unsafe_keys="$(/usr/bin/git -C "$repository_path" config --local --name-only \
    --get-regexp '^(include\..*|includeif\..*|url\..*\.(insteadof|pushinsteadof)|http\..*|protocol\..*|alias\..*|credential\..*|core\.(askpass|hookspath|sshcommand|gitproxy|fsmonitor)|remote\..*\.(proxy|vcs|receivepack|uploadpack|pushurl))$' || :)"
  test -z "$unsafe_keys"
}
task5_git_remote() {
  local operation="${1:-}" argument canonical_url_count=0
  case "$operation" in fetch|ls-remote|push) ;; *) return 1 ;; esac
  for argument in "$@"; do
    [[ "$argument" == "$canonical_origin" ]] && canonical_url_count=$((canonical_url_count + 1))
  done
  test "$canonical_url_count" = 1
  assert_safe_local_git_config "$task5_git_repository"
  /usr/bin/env -i HOME=/home/teladi USER=teladi LOGNAME=teladi \
    PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
    GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
    GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/false SSH_ASKPASS=/bin/false \
    /usr/bin/git -c http.extraHeader= \
      -c "http.$canonical_origin.extraHeader=" -c http.proxy= \
      -c http.sslVerify=true \
      -c http.curloptResolve= -c credential.helper= \
      -c core.askPass=/bin/false -c core.hooksPath=/dev/null \
      -c core.fsmonitor=false -c core.sshCommand=/bin/false \
      -c core.gitProxy=/bin/false -c protocol.allow=never \
      -c protocol.https.allow=always -c protocol.ext.allow=never \
      -C "$task5_git_repository" "$@"
}
# END TASK5_GIT_CONFIG_GUARD

test -d "$archive_checkout" && test ! -L "$archive_checkout"
test "$(realpath -e -- "$archive_checkout")" = "$archive_checkout"
test -z "$(find "$archive_checkout" -xdev \
  \( ! -user teladi -o ! -group teladi \) -print -quit)"
test -d "$generator_checkout" && test ! -L "$generator_checkout"
test -z "$(find "$generator_checkout" -xdev \
  \( ! -user teladi -o ! -group teladi \) -print -quit)"
generator_factory_sha="$(load_verified_task3_factory_sha)"
[[ "$generator_factory_sha" =~ ^[0-9a-f]{40}$ ]]
test "$generator_factory_sha" = \
  "$(/usr/bin/git -C "$generator_checkout" rev-parse HEAD)"
test "$generator_factory_sha" = \
  "$(/usr/bin/git -C "$generator_checkout" rev-parse origin/main)"
task5_git_repository=$generator_checkout
canonical_origin=$canonical_generator_origin
test "$generator_factory_sha" = \
  "$(task5_git_remote ls-remote "$canonical_origin" refs/heads/main | cut -f1)"

task5_git_repository=$archive_checkout
canonical_origin=$canonical_archive_origin
task5_git_remote fetch "$canonical_origin" \
  '+refs/heads/main:refs/remotes/origin/main' \
  '+refs/heads/chore/pin-transactional-site-factory:refs/remotes/origin/chore/pin-transactional-site-factory'
archive_base_sha="$(/usr/bin/git -C "$archive_checkout" rev-parse origin/main)"
archive_head_sha="$(/usr/bin/git -C "$archive_checkout" \
  rev-parse origin/chore/pin-transactional-site-factory)"
[[ "$archive_base_sha" =~ ^[0-9a-f]{40}$ ]]
[[ "$archive_head_sha" =~ ^[0-9a-f]{40}$ ]]
test "$archive_head_sha" = \
  "$(/usr/bin/git -C "$archive_checkout" rev-parse chore/pin-transactional-site-factory)"
archive_has_pr_trigger="$(assert_task5_archive_candidate \
  "$archive_checkout" "$archive_base_sha" "$archive_head_sha" \
  "$generator_factory_sha")"
[[ "$archive_has_pr_trigger" =~ ^[01]$ ]]
printf '%s\t%s\t%s\t%s\n' \
  "$archive_head_sha" "$archive_base_sha" "$generator_factory_sha" \
  "$archive_has_pr_trigger"
TASK5_STEP6_TELADI
}
task5_premerge_facts="$(task5_step6_local_gate)"
IFS=$'\t' read -r archive_head_sha archive_base_sha generator_factory_sha \
  archive_has_pr_trigger \
  <<<"$task5_premerge_facts"
[[ "$archive_head_sha" =~ ^[0-9a-f]{40}$ ]]
[[ "$archive_base_sha" =~ ^[0-9a-f]{40}$ ]]
[[ "$generator_factory_sha" =~ ^[0-9a-f]{40}$ ]]
[[ "$archive_has_pr_trigger" =~ ^[01]$ ]]

archive_pr_list="$(task5_gh pr list \
  --repo "$canonical_archive_repository" \
  --head chore/pin-transactional-site-factory --state open --limit 100 \
  --json number,state,headRefName,headRefOid,baseRefName,isDraft,isCrossRepository,headRepository)"
test "$(/usr/bin/jq 'length' <<<"$archive_pr_list")" = 1
archive_pr_number="$(/usr/bin/jq -r '.[0].number' <<<"$archive_pr_list")"
[[ "$archive_pr_number" =~ ^[1-9][0-9]*$ ]]
/usr/bin/jq -e --arg head "$archive_head_sha" \
  --arg repo_id "$canonical_archive_repo_id" '
    .[0].state == "OPEN"
    and .[0].headRefName == "chore/pin-transactional-site-factory"
    and .[0].headRefOid == $head
    and .[0].baseRefName == "main"
    and .[0].isDraft == false
    and .[0].isCrossRepository == false
    and .[0].headRepository.id == $repo_id
  ' <<<"$archive_pr_list" >/dev/null
test "$(task5_gh pr view "$archive_pr_number" \
  --repo "$canonical_archive_repository" --json files --jq '.files[].path')" = \
  .github/workflows/pages.yml
archive_check_count="$(task5_gh pr view "$archive_pr_number" \
  --repo "$canonical_archive_repository" --json statusCheckRollup \
  --jq '.statusCheckRollup | length')"
[[ "$archive_check_count" =~ ^[0-9]+$ ]]
if (( archive_check_count > 0 )); then
  task5_gh pr checks "$archive_pr_number" \
    --repo "$canonical_archive_repository" --watch --fail-fast
else
  # A zero-check fallback is valid only for this exact fetched head when its
  # exact pages.yml still has no pull_request trigger.
  test "$archive_has_pr_trigger" = 0
fi

# BEGIN TASK5_STEP6_FINAL_PREMERGE
# Re-enter a new clean teladi process immediately before the merge. This
# independently reloads receipt v3, rebinds generator local/origin/remote main,
# refetches archive base/head, and reruns the exact diff/pin/trigger gate.
task5_final_premerge_facts="$(task5_step6_local_gate)"
IFS=$'\t' read -r final_archive_head_sha final_archive_base_sha \
  final_generator_factory_sha final_archive_has_pr_trigger \
  <<<"$task5_final_premerge_facts"
test "$final_archive_head_sha" = "$archive_head_sha"
test "$final_archive_base_sha" = "$archive_base_sha"
test "$final_generator_factory_sha" = "$generator_factory_sha"
test "$final_archive_has_pr_trigger" = "$archive_has_pr_trigger"

archive_final_pr="$(task5_gh pr view "$archive_pr_number" \
  --repo "$canonical_archive_repository" \
  --json state,headRefName,headRefOid,baseRefName,isDraft,isCrossRepository,headRepository,files)"
/usr/bin/jq -e --arg head "$archive_head_sha" \
  --arg repo_id "$canonical_archive_repo_id" '
    .state == "OPEN"
    and .headRefName == "chore/pin-transactional-site-factory"
    and .headRefOid == $head
    and .baseRefName == "main"
    and .isDraft == false
    and .isCrossRepository == false
    and .headRepository.id == $repo_id
    and .headRepository.nameWithOwner == "H234598/Wirtelprimpf-0001"
    and (.files | type == "array" and length == 1)
    and .files[0].path == ".github/workflows/pages.yml"
  ' <<<"$archive_final_pr" >/dev/null
test "$(task5_gh api \
  "repos/$canonical_archive_repository/git/ref/heads/main" --jq .object.sha)" = \
  "$archive_base_sha"
test "$(task5_gh api \
  "repos/$canonical_archive_repository/git/ref/heads/chore/pin-transactional-site-factory" \
  --jq .object.sha)" = "$archive_head_sha"
# END TASK5_STEP6_FINAL_PREMERGE
task5_gh pr merge "$archive_pr_number" \
  --repo "$canonical_archive_repository" --merge --delete-branch \
  --match-head-commit "$archive_head_sha"
archive_merged_pr="$(task5_gh pr view "$archive_pr_number" \
  --repo "$canonical_archive_repository" --json state,headRefOid,mergeCommit)"
/usr/bin/jq -e --arg head "$archive_head_sha" '
  .state == "MERGED"
  and .headRefOid == $head
  and (.mergeCommit.oid | type == "string" and test("^[0-9a-f]{40}$"))
' <<<"$archive_merged_pr" >/dev/null
archive_sha="$(/usr/bin/jq -r '.mergeCommit.oid' <<<"$archive_merged_pr")"
[[ "$archive_sha" =~ ^[0-9a-f]{40}$ ]]
test "$(task5_gh api \
  "repos/$canonical_archive_repository/git/ref/heads/main" --jq .object.sha)" = \
  "$archive_sha"
archive_feature_refs="$(task5_gh api \
  "repos/$canonical_archive_repository/git/matching-refs/heads/chore/pin-transactional-site-factory")"
/usr/bin/jq -e 'type == "array" and length == 0' \
  <<<"$archive_feature_refs" >/dev/null
archive_run_id=""
for attempt in $(seq 1 24); do
  archive_run_id="$(task5_gh run list \
    --repo "$canonical_archive_repository" \
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
task5_gh run watch "$archive_run_id" \
  --repo "$canonical_archive_repository" --exit-status
unset task5_ephemeral_token
```

Expected: immediately before merge, a second clean `teladi` child independently
reloads the verified receipt v3, rebinds generator local/tracking/remote main,
refetches the exact archive base/head, and proves the candidate changes only
`pages.yml` by exactly `2\t2`, contains exactly the two required factory pin
fields and no other 40-hex value. Root then refetches the exact OPEN PR identity,
head, immutable repository and one-file list and uses `--match-head-commit`.
A zero-check fallback is accepted only when that exact head has no
`pull_request` trigger. After merge, GitHub must report `MERGED` and a 40-hex
merge commit, remote main must equal it, and the feature ref list must be empty
before the exact Pages run may be selected. Only then do archive build, artifact
validation, upload, and deploy complete successfully.

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

### 2026-08-02 — Additive Finalisierung des transaktionalen Rolloutvertrags

- Dieser Eintrag superseded ausschließlich die in älteren Ledgerständen noch
  genannten Fast-forward-, Einzelmasken- und frühen Lockfreigabeabläufe; die
  historischen Einträge bleiben unverändert erhalten. Der lokale Code- und
  Testcommit ist
  `d10f36fefee8f1110e2204b8e9f75677fc457549`
  (`fix(settings): serialize applet operations safely`). Er fügt dem Applet
  einen echten, symlinkgeschützten, auf 100 ms begrenzten exklusiven
  Settings-`flock` hinzu und hält ihn über die vollständige mehrteilige
  Generatoroperation. Konkurrenz endet redigiert als busy und startet keinen
  `systemctl`-Teilbefehl. Die Adminoberfläche validiert außerdem die
  `numeric_bounds` aller tatsächlich dargestellten Zahlenfelder vollständig,
  einschließlich Ganzzahligkeit, `min <= max`, aktuellem Wertebereich und
  `story_finish_parts_min <= story_finish_parts_max`.
- Task 3 prüft den PR nach den Checks erneut auf `OPEN`, exakten Head-OID,
  `main` und Non-Draft sowie die unveränderte Remote-Basis. Der Merge ist an
  `--match-head-commit` gebunden; danach müssen Remote-main und Merge-SHA
  übereinstimmen und das Mergeobjekt exakt zwei Eltern in der Reihenfolge
  geprüfte Basis, geprüfter Head besitzen. Ein Headwechsel kann damit keinen
  Mergeaufruf passieren.
- Sämtliche lokalen HTTP-Smokes besitzen `--noproxy '*'`, zwei Sekunden
  Connect- und zehn Sekunden Gesamtfrist. Runtime-Fetch ist durch GNU
  `timeout` sowie Git-Low-Speed-Grenzen begrenzt; beide editable
  Pip-Installationen sind auf 300 Sekunden begrenzt und verwenden
  `--no-build-isolation --no-deps`. Diese Grenzen ändern weder Runtime noch
  Environment, solange der weiterhin separat freizugebende Step 9 nicht
  ausgeführt wird.
- Der normative Step-9-Rahmen stoppt zuerst den Timer, wartet begrenzt auf den
  Generator, maskiert anschließend `wirtelprimpf.service` zur Laufzeit und
  wiederholt die Inaktivitätsprüfung, wodurch auch das
  Inactive-to-Mask-Rennen geschlossen wird. Direkt vor dem Git-Commitpunkt wird
  zusätzlich der gestoppte Timer runtime-maskiert. Postcommit-, unbekannte
  SHA-, Recovery- und Konfigurationskonkurrenzfehler stoppen Admin/Timer und
  hinterlassen **beide** Units `masked-runtime`; kein solcher Pfad spult Code,
  Ref oder konkurrierende Konfigurationsbytes zurück.
- Nach dem Livesmoke wird derselbe Settings-Lock begrenzt wieder erworben und
  bis über Revision/Fingerprints, alle drei Unitvergleiche, Applet-Diff,
  Timerenablement, beide Masken, Git-Commitpunkt, Worktree-Anbindung,
  Service-/Admin-/Applet-/Timerzustände und sämtliche Schlussbeweise gehalten.
  `refs/heads/main` wechselt ausschließlich per
  `git update-ref <target> <exact-old>`; der Worktree steht vorher bereits
  detached auf dem Target-Tree und wird danach ohne Old-Tree-Fenster an `main`
  gebunden. Der redundante zweite `ReloadXlet` entfällt: Target-Applet und UUID
  sind vor dem Smoke geprüft, der installierte Baum danach unverändert.
- Das Abschlussfenster ist explizit: Unter weiterhin gehaltenem Lock werden
  HUP/INT/TERM ignoriert; erst danach folgen Lockfreigabe, das infallible
  `deployment_complete=1`, EXIT-Trap-Disarm und Signalreset. Scheitert bereits
  die Lockfreigabe, bleibt die EXIT-Recovery aktiv. Eine unmittelbar danach
  beginnende legitime Settings-Transaktion kann daher nicht mehr durch einen
  verspäteten Postcommit-Fail-closed-Pfad überfahren werden.
- Der vollständig extrahierte Step-9-Codeblock bestand `bash -n`. Der
  Step-10-Block bestand sowohl `bash -n` als auch den realen disposable Lauf mit
  Exit 0. Der Harness injiziert und beweist: doppelte
  Generator-Inaktivitätsbarriere samt Service-Mask, begrenzte Lockkonkurrenz,
  present/missing- und Verzeichnismodus-Recovery, Lockhaltedauer bis zum letzten
  Timerproof, echte Git-CAS ohne Old-Tree, Update-ref-zu-Flag-Signalrand,
  Target- und Third-SHA-Fail-closed, konkurrierende Config ohne Restore,
  vollständige Unit/Applet/Admin/Timerproofs sowie Head-Match und exakt
  geordnete Mergeeltern.
- Finale lokale Matrix nach der letzten Planänderung: Plattform `143/143`;
  `make check` mit Applet-Runtime grün, Admin-UI `24/24`, SemVer `8/8`,
  Git-Object-Fallback `3/3`, Release-Publication `3/3`, Helper-Environment
  `7/7`, Applet-Sync `25/25`, Settings-Schema `14/14` und Story-Directives
  `31/31`; Web `9/9`; Astro-Check über 22 Dateien mit null Fehlern, Warnungen
  und Hinweisen. `compileall`, Ruff 0.15.16 (vollständig auf den neuen
  Pythonpfaden, E9/F/I auf der Legacy-`SettingsLogo.py`) und `git diff --check`
  endeten ebenfalls mit Exit 0.
- Beide Profile wurden vollständig gebaut und validiert. Hub: 823 Dateien,
  818 HTML, 10.840 interne Links, 4.344.374 Byte, Baum-SHA-256
  `0acc6695654d3e82e450a3467d96995da89e59d954d00340d5a5028916ab1bb6`.
  Archiv: 823 Dateien, 818 HTML, 10.840 interne Links, 4.395.867 Byte,
  Baum-SHA-256
  `f6e682fa639f72863f8911bb2b94d416ba83e913613797334361e439308a91bd`.
- Diese Author-Runde führte keinen Fetch, Push, PR-Write, Merge, Install,
  Reload, Deploy, `systemctl`, `gdbus`, Cloudflare-/DNS-Zugriff,
  Cinnamon-Upstream-Fix oder sonstige Runtime-/Remote-Mutation aus. Der
  Doku-/Evidenz-SHA ist der Commit, der diesen Ledgerabschnitt enthält, und
  wird im Übergabebericht exakt ausgewiesen.

### 2026-08-02 — Additive Auth-/Policy-/Commitpoint-Remediation für Task 3

- Dieser Eintrag ist additiv. Er superseded ausschließlich die unmittelbar
  zuvor als unzureichend erkannten Task-3-Aussagen zu einem klassifizierenden
  Ruleset-Allowlist-Gate, unqualifiziertem Root-Git, impliziter PR-Head-Bindung
  und undifferenzierten Fehlern nach dem Remote-Commitpunkt. Runtime-, Web-,
  Generator- und Konfigurationsproduktionscode blieben unverändert.
- Der reale lokale Auth-Preflight ergab, dass sowohl der persistierte
  `teladi`- als auch der Root-`gh`-Kontext derzeit ungültig sind. Erfolgreiche
  unauthentifizierte öffentliche Reads sind ausdrücklich keine
  Write-Autorisierung. Step 4 und Step 5 verlangen deshalb einen extern
  bereitgestellten ephemeren `GH_TOKEN` und beweisen ihn über `/user`, bevor
  irgendeine Writephase beginnt. Ohne diesen Nachweis endet der Ablauf
  prämutativ; der Plan erfindet, lädt oder persistiert keine Credentials.
- Step 5 prüft die Identität zunächst in einer leeren Root-Umgebung und führt
  anschließend sämtliche Git-, `commit-tree`-, Receipt- und Pushoperationen
  als UID/GID `teladi` unter `env -i`, festem `HOME` und sicherem `PATH` aus.
  Der Token wird nur als Prozessumgebung weitergereicht, nie gedruckt oder in
  eine Datei geschrieben. HTTPS-Git verwendet pro Remote-Befehl eine zuerst
  geleerte Helperliste und ausschließlich
  `!/usr/bin/gh auth git-credential`; `gh auth setup-git`, persistente Helper
  und `safe.directory` bleiben verboten.
- Step 4 und Step 5 binden den PR erneut an exakten Headnamen und OID,
  `isCrossRepository=false`, Owner, Repository-ID und `nameWithOwner`. Fetch-
  und Push-URL von `origin` müssen beide exakt
  `https://github.com/H234598/Wirtelprimpf-generator.git` sein. Die
  deterministische Merge-Nachricht verwendet nur die einmal geprüfte Variable
  `$generator_head`; ein zweiter racy Branch-Read existiert nicht mehr.
- Der Policy-Gate ist nun konservativ: Applied Rules müssen exakt `[]` sein,
  Classic Protection muss nach erfolgreicher Auth-/Repo-Prüfung exakt HTTP 404
  liefern. Jedes nichtleere Array, HTTP 200, jede unbekannte Antwort und jeder
  API-Fehler stoppt vor `commit-tree`; es gibt keine Typ-Allowlist und keinen
  Adminbypass.
- Ein privates, atomar ersetztes und synchronisiertes Receipt mit Eigentümer
  `teladi`, Verzeichnismodus `0700` und Dateimodus `0600` bildet ausschließlich
  `planned -> remote_committed -> verified` ab. Der erfolgreiche atomare Push
  wird sofort gelatcht und gespeichert. EXIT unterscheidet
  `REMOTE COMMIT COMPLETE; VERIFICATION PENDING` vom engen
  Pushausgangsfenster. Ein Wiederanlauf reconciled sowohl
  `OPEN + planned + Remote bereits Merge/Head gelöscht` als auch
  `MERGED + Receipt`, ohne jemals ein zweites Mal zu pushen; unbekannte
  Receipt-/Refkombinationen bleiben fail-closed.
- Step 10 injiziert dieses Verhalten real gegen einen zweiten lokalen
  Bare-Remote: Abbruch direkt nach Push vor Receipt, Wiederanlauf aus
  `planned`, API-Ausfall in `remote_committed`, Abschluss zu `verified` ohne
  zweiten Push und unbekannter Refzustand. Der Vertragstest bindet außerdem den
  normativen Step-9-`rollback_deployment`-Prolog direkt: `trap - EXIT` liegt vor
  `trap '' HUP INT TERM`, beide vor Recovery; Lockaufnahme/-freigabe und finaler
  Statusausgang bleiben geordnet. Der bestehende echte TERM/HUP-Harness bleibt
  zusätzlich aktiv.
- Test-first-Evidenz: Die erste Erweiterung lief mit fünf gezielten Fehlern bei
  zwölf Vertragstests rot. Nach GREEN deckten zwei weitere einzelne rote
  Fokustests das Push-zu-Latch-Signalfenster und die fehlende prämutative
  Receipt-Elternpfadprüfung auf; nach `task3_push_started` und dem exakten
  `0700`-/Realpath-/Owner-Gate bestanden beide. Der aktuelle Vertrag besteht
  `12/12`; Task-3-Step-5, Step 9 und Step 10 bestehen `bash -n`, Step 10
  zusätzlich seinen vollständigen realen disposable Lauf.
- Die vollständige lokale `make check`-Matrix lief als `teladi` unter
  `env -i` mit Exit 0: Applet-Runtime grün, Admin-UI `24/24`, SemVer `8/8`,
  Git-Object-Fallback `3/3`, Release-Publication `3/3`, Helper-Environment
  `7/7`, Applet-Sync `25/25`, Settings-Schema `14/14`, Story-Directives
  `31/31` und Rollout-Vertrag `12/12`.
- Diese Remediation führte keinen Fetch, Push, PR-Write, Merge, Install,
  Reload, Deploy, Runtime-, `systemctl`-, `gdbus`-, Cloudflare-, DNS- oder
  Upstreamzugriff aus. Insbesondere wurde kein GitHub-Token erfunden oder aus
  einem ungültigen Keyring übernommen. Der Doku-/Test-SHA ist der lokale
  `teladi`-Commit, der diesen Abschnitt enthält, und wird in der Übergabe
  ausgewiesen.

### 2026-08-02 — Additive Gegenreview-Härtung: anonymer Tokenkanal und Receipt v2

- Dieser Abschnitt ist additiv. Er superseded die älteren Task-3-Aussagen,
  soweit sie einen Token allgemein als Prozessumgebung beschrieben, Root als
  Git-Akteur zuließen, nur eine einzelne Origin-URL betrachteten oder ein
  Receipt ohne vollständig rekonstruierbaren Vertrauensanker akzeptierten.
  Produktions-, Runtime- und Webcode wurden in dieser Author-Runde nicht
  verändert.
- Steps 1 bis 5 erzwingen ihren Ausführungskontext explizit: Der äußere
  privilegierte Prozess prüft UID 0 und reicht anschließend ausschließlich
  einen anonymen, geerbten Dateideskriptor an `runuser -u teladi -- env -i`
  weiter. Der lange Shellprozess beweist UID/GID 1000, festes `HOME`, festen
  sicheren `PATH` und das erwartete Repository. Vor jeder Berührung des
  Geheimnisses ist Tracing mit `set +x` abgeschaltet. Der Token erscheint
  weder in `argv`, Heredoc, Datei noch im Environment des langen
  Shellprozesses, der Tests, Builds oder Hooks; nur der jeweils kurze
  `/user`-, `gh`- oder Credential-Helper-Aufruf erhält ihn nach einem
  NUL-begrenzten Read aus dem anonymen FD.
- Noch vor dem ersten Fetch und erneut vor Merge-/Pushphasen muss `/user`
  exakt Login `H234598` und numerische ID `54270221` liefern. Alle Fetch- und
  Push-URLs werden mit `git remote get-url --all` getrennt ausgelesen; beide
  Mengen müssen jeweils genau ein Element enthalten und dieses muss wörtlich
  `https://github.com/H234598/Wirtelprimpf-generator.git` sein. `ls-remote`,
  Fetch und der atomare Push adressieren ebenfalls nur dieses Literal. Jeder
  Gitbefehl leert die Credential-Helperliste, setzt ausschließlich den
  kontrollierten `gh auth git-credential`-Helper und neutralisiert Hooks mit
  `core.hooksPath=/dev/null`.
- Receipt v2 besitzt eine exakte, gegen Zusatzfelder geschlossene
  JSON-Schemabindung für Actor, Repository-ID/-Name, kanonische URL,
  PR-Nummer, Head-Ref/-OID, Base-OID, Head-Tree, Mergezeit, Mergenachricht,
  Merge-OID und Zustand. Auf jedem Lauf werden der vertrauenswürdige
  Head-Tree und der deterministische Zwei-Eltern-Merge aus den aktuell
  verifizierten Gitobjekten neu erzeugt. Ein syntaktisch plausibles Receipt
  mit frei gewähltem Tree und korrekten Eltern reicht deshalb nicht;
  zusätzliche, fehlende, veraltete oder abweichende Felder enden fail-closed.
  Der atomare Writer räumt auch bei einem fehlgeschlagenen Rename seine
  private temporäre Datei auf.
- Die direkte Zustandsklassifikation erlaubt einen Push nur für
  `planned + Base/Head vorhanden`. `planned + Merge/Head fehlt` wird
  reconciled; `remote_committed` und `verified` dürfen nur beobachten und
  verifizieren. Unbekannte Receipt-/Remote-Kombinationen brechen ab. Damit
  kann ein Wiederanlauf nach dem Remote-Commitpunkt keinen zweiten Push
  auslösen.
- Test-first-Evidenz dieses Gegenreviews: Die erste Erweiterung lief bei
  `17` Vertragstests mit neun gezielten Fehlern rot; die Receipt-v2-Stufe bei
  `20` Tests mit drei gezielten Fehlern. Anschließend liefen je ein direkter
  Rollback- und ein Zustandsklassifikator-Fokustest zunächst rot. GREEN sind
  nun `22/22`. Die Suite führt den anonymen FD real unter `bash -x` aus,
  untersucht Prozessargumente und -umgebungen, provoziert einen bösartigen
  Pre-Push-Hook, pusht dennoch nur hookneutral in ein lokales Bare-Remote,
  rekonstruiert den Merge unabhängig, versucht Receipt-Fälschungen und
  Rename-Fehler und löst den normativen Rollback mit echten Signalen aus.
- Die frische vollständige Matrix lief als `teladi` unter `env -i` mit Exit
  0: Applet-Runtime grün, Admin-UI `24/24`, SemVer `8/8`,
  Git-Object-Fallback `3/3`, Release-Publication `3/3`, Helper-Environment
  `7/7`, Applet-Sync `25/25`, Settings-Schema `14/14`, Story-Directives
  `31/31` und Rollout-Vertrag `22/22`.
- Diese Gegenreview-Runde führte keinen Fetch, Push, PR-Write, Merge,
  Install, Reload, Deploy, Runtime-, `systemctl`-, `gdbus`-, Cloudflare-,
  DNS- oder Upstreamzugriff aus. Alle schreibenden Gitproben nutzten
  ausschließlich disposable lokale Repositories. Der lokale
  Doku-/Test-Commit wird in der Übergabe ausgewiesen.

### 2026-08-02 — Additive NO-GO-Schließung: Ausführungskontext und feste Identität

- Dieser Abschnitt ist additiv und korrigiert die unmittelbar vorherige
  Gegenreview-Evidenz dort, wo sie den `teladi`-Kontext pauschal für Steps 1
  bis 5 behauptete, die Repository-ID nur receipt-intern selbstkonsistent
  band oder persistente Git-HTTP-/AskPass-Konfiguration nicht betrachtete.
  Historische Aussagen bleiben als Auditspur erhalten; für Task 3 gilt diese
  spätere, strengere Fassung.
- Step 1 enthält nun beide vollständigen Hub-/Archiv-Profilbuilds und beide
  `validate_pages_artifact.py`-Aufrufe ausdrücklich vor dem schließenden
  `TASK3_STEP1_TELADI`-Marker. Außerhalb des `runuser -u teladi -- env -i`-
  Heredocs bleibt keine Prosa-Anweisung zur Ausführung von Buildcode zurück.
- Step 3 liest und validiert den Branch im markierten prämutativen Callgate.
  Der ausführbare Branch-Predicate lehnt `main` hart ab, bevor Origin-, Actor-
  und Repository-Gates sowie der erste Fetch erreicht werden. Derselbe einmal
  gebundene Feature-Branch wird vor dem Push erneut gegen den aktuellen
  Checkout geprüft; ein direkter `HEAD:refs/heads/main`-Pfad existiert nicht.
- Steps 3, 4 und 5 pinnen sowohl `H234598/Wirtelprimpf-generator` als auch die
  unveränderliche GitHub-Node-ID `R_kgDOTpr2BA`. Die jeweiligen ausführbaren
  JSON-Prädikate lehnen falsche, fehlende und dynamisch aus einem Ersatzrepo
  übernommene IDs ab. Receipt v2 und sämtliche PR-Identitätsvergleiche
  konsumieren nur diese feste ID, niemals eine aus der Antwort übernommene
  Zuweisung.
- Jeder tokenisierte Kurzprozess ist nichtinteraktiv und setzt
  `GIT_ASKPASS=/bin/false`, `SSH_ASKPASS=/bin/false` sowie
  `GIT_TERMINAL_PROMPT=0`. `git_remote` leert weiterhin die Helperliste,
  ergänzt ausschließlich `gh auth git-credential`, deaktiviert Hooks und
  neutralisiert `core.askPass`. HTTP-Zusatzheader werden zuerst global und
  danach für die exakte kanonische Remote-URL geleert; die zweite, spezifische
  Rücksetzung gewinnt damit auch gegen persistente URL-spezifische
  `http.<url>.extraHeader`-Werte.
- Test-first-Evidenz: Die unveränderte Basis bestand `22/22`. Die erweiterte
  Suite lief anschließend mit `29` Tests und `14` gezielten Fehlern bei null
  Errors rot. Die Fehler belegten fehlende Profilkommandos, den akzeptierten
  `main`-Pfad, fehlende reale Callgates/feste Identity-Prädikate, drei
  ungeschützte Tokenkinder, zwei gesendete URL-spezifische Authorization-
  Header und ausgeführtes AskPass in Steps 3/5. GREEN sind `29/29`.
- Die Suite führt Feature-/`main`- und Actor-/Repository-Prädikate real aus.
  Zwei disposable Git-Repositories senden echte HTTP-Requests an einen
  Loopback-Server; kein konfigurierter Authorization-Header erreicht ihn.
  Eine absichtlich fehlschlagende Helperkette führt das ausführbare,
  tokenlesende AskPass-Programm weder in Step 3 noch Step 5 aus. Die alten
  vakuösen Definition-vor-Sink-Indexchecks wurden durch markierte tatsächliche
  Callgates und ausführbare Negativtests ersetzt.
- Step 3, Step 4, Step 5, Step 9 und Step 10 bestehen jeweils `bash -n` und
  ShellCheck 0.11.0 ohne Befund. Die frische vollständige `make check`-Matrix
  lief als `teladi` unter `env -i` mit Exit 0: Applet-Runtime grün, Admin-UI
  `24/24`, SemVer `8/8`, Git-Object-Fallback `3/3`, Release-Publication `3/3`,
  Helper-Environment `7/7`, Applet-Sync `25/25`, Settings-Schema `14/14`,
  Story-Directives `31/31` und Rollout-Vertrag `29/29`.
- Diese NO-GO-Schließung führte keinen Fetch, Push, PR-Write, Merge, Install,
  Reload, Deploy, Runtime-, Service-, `systemctl`-, `gdbus`-, Cloudflare-,
  DNS- oder Upstreamzugriff aus. Alle schreibenden Git-/HTTP-Proben blieben in
  disposable lokalen Repositories beziehungsweise auf Loopback begrenzt. Der
  lokale `teladi`-Commit wird in der Übergabe ausgewiesen.

### 2026-08-02 — Additive Author-Evidenz zu den vier finalen CodeRabbit-Punkten

- Diese additive Autorenschicht schließt vor dem Rollout genau vier aktuelle
  Reviewpunkte: deterministische öffentliche Parentmodi, die explizite
  Applet-Lock-API, konsistente Homepfadexpansion und echte
  Admin-Pollrequest-Verhaltensabdeckung. Sie ändert weder die normative
  Task-3-Vertrauenskette noch die Reihenfolge der späteren Runtime-, Merge- und
  Deploymentaufgaben.
- Neu erzeugte öffentliche Parents erhalten auch unter `umask 0077` exakt
  `0755`; no-follow geöffnete Verzeichnisdeskriptoren bewahren die
  Symlinkgrenze, während vorhandene öffentliche Zwischenparents unangetastet
  bleiben. Private Parents, atomare Dateioperationen und Rollbackpfade bestehen
  unverändert ihre Regressionen.
- `SettingsOperationLockError` und `exclusive_settings_lock` gehören nun zum
  öffentlichen Applet-Modulvertrag. Die Absolutpfadprüfung folgt der
  `expanduser`-Normalisierung: gültiges `~/...` wird akzeptiert, ein echter
  Relativpfad weiterhin vor jeder Dateianlage abgelehnt; Symlinkparents und
  nichtreguläre Lockziele bleiben fail-closed.
- Die Adminoberfläche ruft ihre fest gebundenen Ressourcen `/api/settings` und
  `/api/status` über `fetchLivePoll(resource)` ab. Der Verhaltenstest beobachtet
  für beide Requests `cache: "no-store"`, den 4000-ms-Abortsignalpfad und die
  Wiederherstellung aller Stubs statt den JavaScript-Quelltext zu durchsuchen.
  Die vorhandenen Epoch-, In-flight-, Save- und Fehlerverträge wurden nicht
  umgebaut.
- RED-Evidenz: je ein gezielter Fehlschlag für umask/0755, die zwei fehlenden
  Exporte, den zunächst abgelehnten Homepfad und die fehlende Admin-Request-API;
  der relative Pfad blieb schon im RED-Lauf geschlossen. GREEN: Settings-IO
  `12/12`, Applet-Sync `28/28`, Admin-UI `24/24`, direkt betroffene Pythonmatrix
  `107/107` und Ruff 0.15.16 ohne Befund.
- `make check` lief frisch als `teladi` unter `env -i` mit Exit 0, einschließlich
  Rollout-Vertrag `29/29`. Beide vollständigen Siteprofile bestanden Build und
  Validator: jeweils 823 Dateien, 818 HTML und 10.840 interne Links; Hub-Hash
  `0acc6695654d3e82e450a3467d96995da89e59d954d00340d5a5028916ab1bb6`,
  Archiv-Hash
  `f6e682fa639f72863f8911bb2b94d416ba83e913613797334361e439308a91bd`.
- Es gab keinen Fetch, Push, PR-Kommentar, Merge, Install, Reload, Deploy,
  Runtime-/Ownership-/Service-/Pages-/DNS-/Cloudflare- oder Upstream-Write.
  Der korrigierte lokale `teladi`-Commit wird vor jeder späteren Rolloutmutation
  erneut durch die bereits normierten Head-/Tree-/Policy-Gates gebunden.

### 2026-08-02 — Additive Vollreview-Schließung für CodeRabbit-Run `814f2270-ed94-415a-a8bc-f460663dd0a3`

- Diese Autorenschicht bezieht sich exakt auf den geprüften Generator-Head
  `a2f0cff98450b25bbd8ffe20f95b612cdd039e9b` und schließt die sechs
  Actionable Comments sowie sieben Nitpicks des Ergebnisses
  `CHANGES_REQUESTED`. Frühere Planfassungen und Evidenz bleiben unverändert
  als Auditspur erhalten; dieser spätere Abschnitt beschreibt den jetzt
  maßgeblichen lokalen Stand.
- Task 5 führt die lokalen Archiv- und Generatoroperationen der Steps 1 bis 6
  nun unter wörtlich gequoteten `runuser`-/`env -i`-Grenzen aus. UID/GID 1000,
  kanonische reale Checkoutpfade,
  Teladi-Eigentum und ein sauberer Diff werden im Kind geprüft; der Root-Shell
  stehen weder expandierte Archivpfade noch Workflowargumente oder
  Workflowinhalte zur Verfügung. Step 5 beschränkt Root auf die bewachten
  kurzen GitHub-Aufrufe und reicht das ephemere Geheimnis ausschließlich über
  einen anonymen Deskriptor an das Teladi-Kind weiter. **Keiner dieser
  Rolloutschritte wurde in dieser Autorenschicht ausgeführt.**
- Der frühere unqualifizierte Workflow-Edit ist durch einen ausführbaren,
  mechanisch begrenzten Writer ersetzt. Er akzeptiert ausschließlich eine
  reguläre, nicht verlinkte, UID/GID-1000-eigene `0644`-Datei, verlangt genau
  je ein `uses`- und `factory_ref`-Pin, ersetzt genau diese beiden 40-stelligen
  Werte, schreibt über eine exklusive private Part-Datei, synchronisiert Datei
  und Verzeichnis und beendet sich bei jedem Form-, Mengen-, Eigentums- oder
  Modusfehler geschlossen.
- Die übrigen Reviewkorrekturen sind ebenfalls vollständig abgedeckt: Applet-
  Auswahl- und Modellfelder teilen den Legacy-erhaltenden Katalogpfad und
  werden bei externen Snapshots vollständig unter Dirty-Unterdrückung neu
  aufgebaut; ein abweichender Admin-Settingspfad liefert redigiertes JSON und
  den einheitlichen Validierungs-Exitcode statt Traceback oder Pfadleck; die
  Story-Zielableitung liegt innerhalb der redigierenden Statusquellengrenze;
  Save-Antworten werden defensiv und statusabhängig klassifiziert;
  Erfolgssnapshots erfordern ausdrücklich `ok: true`, während der bewusst
  andere Konfliktsnapshotvertrag erhalten bleibt; Pollfehler besitzen eine
  eigene ARIA-Liveregion und überschreiben keinen Save-/Konfliktstatus;
  fehlendes CSRF und unerwartete Bootstrapfehler lassen alle Controls sichtbar
  gesperrt; und `.field.is-invalid` ist nun visuell erkennbar.
- Zwei fragile Quelltexttests prüfen jetzt das tatsächliche modale Dialog- und
  gemeinsame Busy-Guard-Verhalten. Doppelte `snapshot_for_test`-Definitionen
  wurden in eine einzige lokale Plattform-Testfixture überführt. Die
  Produktionsänderungen wurden nicht durch neue Suppressionskommentare
  verdeckt.
- Die gemeldete Variante eines malformed-JSON-`current_volume` war am
  geprüften Head bereits redigiert: `StateStore` übersetzt den Typfehler beim
  Einlesen in eine von `_collect_source` behandelte Ausnahme. Ein
  Baseline-Regressionsfall hält diese Tatsache fest. Der tatsächlich noch
  offene Nachladepfad wurde separat zunächst rot nachgewiesen: Liefert ein
  kontrollierter Store ein unerwartet typwidriges Objekt, wird nun nur
  `platform_state` degradiert und die gültige Konfiguration bleibt erhalten;
  ein globales Verschlucken beliebiger `TypeError` wurde bewusst vermieden.
- Test-first-Evidenz vor der Produktionsänderung: zwei neue Task-5-Tests
  erzeugten vier Errors und einen Failure, Applet-Legacy-Refresh einen
  Failure, der CLI-Pfad einen Error, die unerwartete Storyableitung einen
  Error und die Adminmatrix sechs Failures. GREEN sind anschließend die drei
  realen Task-5-Rootproben `3/3`, der vollständige Rolloutvertrag `32/32`,
  Admin-UI `31/31`, Applet-Sync `28/28`, Settings-Schema `15/15` und die
  Plattform-Discovery `147/147`.
- `make check` lief frisch als `teladi` unter `env -i` mit Exit 0; im normalen
  Teladi-Lauf bestanden `30` Rollouttests und nur die zwei ausdrücklich
  rootgebundenen Realproben wurden erwartungsgemäß übersprungen. Zusätzlich
  bestanden die Webtests `9/9` und Astro prüfte 22 Dateien mit null Fehlern,
  Warnungen oder Hinweisen. Beide immutable Siteprofile bestanden Build und
  Validator mit jeweils 823 Dateien, 818 HTML und 10.840 internen Links. Hub-
  SHA-256:
  `0acc6695654d3e82e450a3467d96995da89e59d954d00340d5a5028916ab1bb6`;
  Archiv-SHA-256:
  `f6e682fa639f72863f8911bb2b94d416ba83e913613797334361e439308a91bd`.
- `compileall` über Sourcecode, Plattform, Skripte und Tests, `node --check`
  für das Adminmodul sowie `git diff --check` bestanden. Ruff prüfte alle
  geänderten Pythonpfade ohne neuen Befund; ausschließlich die bereits am
  Basis-SHA vorhandenen dateiweiten Baselineausnahmen von `SettingsLogo.py`
  und die unveränderten `I001`-/`RUF001`-Altstellen des Rollouttests wurden
  explizit ausgeklammert. Der abschließende Eigentumsscan ergab null von
  `teladi:teladi` abweichende Einträge, der High-Confidence-Secretmusterscan
  über Diff und neue Fixture null Treffer.
- Diese Vollreview-Schließung blieb vollständig im isolierten lokalen
  Generator-Worktree: kein Credentialzugriff, Fetch, Push, PR-Kommentar,
  Merge, Install, Reload, Deploy, Runtime-/Service-/Applet-/Archiv-/Pages-,
  DNS-, Cloudflare- oder Upstream-Write. Die einzigen schreibenden Proben
  verwendeten disposable lokale Dateien beziehungsweise Repositories; alle
  Projektdateien und der abschließende Commit bleiben UID/GID `teladi`.

### 2026-08-02 — Additive Schließung der drei verbleibenden Rollout-Blocker

- Diese spätere Autorenschicht setzt exakt auf dem unveränderten lokalen
  Parent `44aeb9df762b4fd362a60d38787eaaff8708bb49` auf. Sie ersetzt oder kürzt
  keinen früheren Evidenzabschnitt. Ihr einziger Gegenstand sind die drei im
  anschließenden Read-only-Sicherheitsreview verbliebenen Blocker: fremde
  effektive Git-Konfiguration in tokenisierten Kindprozessen, die fehlende
  bindende Current-Head-Reviewfreigabe vor Task 3 sowie die fehlende
  Receipt-/Head-CAS-Bindung in Task 5/6.
- Alle kurzen Task-3- und Task-5-Tokenkinder setzen jetzt ausdrücklich
  `GIT_CONFIG_NOSYSTEM=1` und `GIT_CONFIG_GLOBAL=/dev/null`; Prompt und beide
  Askpass-Pfade bleiben deaktiviert. Vor jedem planmäßigen Netzwerk-Git prüft
  ein ausführbarer Local-Config-Guard fail-closed auf `include/includeIf`,
  URL-Rewrites, jede lokale HTTP-/Extraheader-/Proxy-/TLS-Konfiguration,
  Protokoll-, Credential-, Alias-, Hook-, Askpass-, Remote-Helper-, Routing-
  und Exec-Vektoren. Die danach einzig zulässige Kapsel verwendet das
  kanonische HTTPS-Literal genau einmal und setzt Helper, Hooks, Askpass,
  Proxy/TLS und Protokollfreigaben selbst kontrolliert.
- Task 3 fordert vor dem ersten `planned`-Receipt und unmittelbar vor dem
  atomaren Exact-Lease-Push erneut denselben offenen PR, denselben Head und
  `reviewDecision=APPROVED`. Reviewthreads und Reviews werden vollständig mit
  Cursorprüfung paginiert. Akzeptiert wird genau eine Freigabe des unverändert
  erwarteten Heads durch `coderabbitai[bot]` mit numerischer GitHub-ID
  `136622811`; ungelöste Threads, stale/mehrdeutige Reviews, Head-Drift,
  unbekannte Zustände, kaputte Pagination und API-Fehler stoppen.
- Das private Receipt besitzt nun die strikte Version 3. Zusätzlich zu Actor,
  unveränderlicher Generator-Repository-ID, PR, Head, Base, Tree und
  deterministischem Merge bindet es Review-ID, Review-Login/-ID, Reviewcommit
  und Zustand `APPROVED`. Jeder Push-Retry liest das Receipt streng, erhebt
  die Freigabe frisch und vergleicht die Bindung erneut, bevor der atomare
  Push erreichbar wird; bereits commitete Reconciliation bleibt pushfrei.
- Jeder Task-5-Step akzeptiert den Factory-SHA ausschließlich aus einem
  `verified` Task-3-v3-Receipt ohne Zusatzfelder und bindet ihn erneut an
  Generator-`HEAD`, `origin/main` und das kanonische Remote-Main. Netzwerk-Git
  läuft auch dort nur durch den gehärteten Literal-Wrapper. Step 5/6 binden
  Actor `H234598/54270221`, das Archiv
  `H234598/Wirtelprimpf-0001` und seine verifizierte unveränderliche Node-ID
  `R_kgDOSg7oRg`; Branch, Base, Head, Dateiliste, Checks und Remote-Refs werden
  exakt geprüft. Der Merge verwendet zwingend
  `gh pr merge --match-head-commit "$archive_head_sha"` in demselben
  kurzlebigen Tokenkontext.
- TDD-Evidenz: Die sieben neuen fokussierten Verträge liefen zunächst mit 22
  erwarteten Teilfehlern rot. Nach ausschließlich Plan- und Vertragstest-
  Änderungen bestanden dieselben `7/7`. Der vollständige Rolloutvertrag
  bestand anschließend als `teladi` mit `39/39`; seine zwei erwartungsgemäß
  übersprungenen UID-0-Probes bestanden separat mit `2/2` und unter
  `PYTHONDONTWRITEBYTECODE=1`.
- Frische Gesamtverifikation: `make check` bestand als UID/GID `teladi` unter
  `env -i`; darin Admin-UI `31/31`, SemVer `8/8`, Git-Object-Fallback `3/3`,
  Release-Publication `3/3`, Helper-Environment `7/7`, Applet-Sync `28/28`,
  Settings-Schema `15/15`, Story-Directives `31/31` und Rolloutvertrag
  `39/39` mit den zwei dokumentierten Root-Skips. Die Webtests bestanden
  `9/9`; Astro prüfte für Hub und Archiv jeweils 22 Dateien mit null Fehlern,
  Warnungen oder Hinweisen. Da weder Produktions- noch Webcode geändert wurde,
  wurden keine neuen Siteprofil-Buildartefakte erzeugt.
- Diese Schließung führte keine Rolloutanweisung aus: kein Credentialzugriff,
  kein Git-Fetch oder -Push, kein PR-/Merge-Write, keine Runtime-, Archiv-,
  Ownership-, Install-, Reload-, Service-, Pages-, DNS-, Cloudflare- oder
  Upstream-Mutation. Der einzige externe Zugriff war die anonyme read-only
  Bestätigung der bereits existierenden Archiv-Node-ID; alle schreibenden
  Probes blieben in disposable lokalen Verzeichnissen.

### 2026-08-02 — Additive Final-Gate- und Redaktionsnachbesserung

- Basis ist exakt Parent `1d0b8cd1fdd28e6aea9b093aa966a422d2a46b88`;
  frühere Ledgerpassagen bleiben unverändert erhalten. Sämtliche Git-Config-
  Guards brechen weiterhin geschlossen ab, geben aber nur noch eine generische
  Meldung oder gar nichts aus. Ein ausführbarer Test hinterlegt einen
  credentialartig aufgebauten Config-Key und beweist für alle Task-3-/Task-5-
  Varianten: Exit ungleich null, Sentinel weder auf stdout noch stderr.
- Step 6 führt dasselbe lokale Gate zweimal in voneinander getrennten sauberen
  `teladi`-Prozessen aus, zuletzt unmittelbar vor dem Merge. Es lädt Receipt v3
  neu, bindet Generator-Head/Tracking/Remote-Main, refetcht Archive-Base/-Head
  und verlangt ausschließlich `pages.yml`, exakt `2\t2`, exakt die beiden
  Factory-Pinfelder, insgesamt genau zwei Receipt-SHA-Vorkommen und keinen
  anderen 40-Hex-Wert. Der Null-Check-Fallback verlangt zusätzlich, dass
  exakt dieser Head keinen `pull_request`-Trigger besitzt.
- Direkt vor `--match-head-commit` werden OPEN-Zustand, Head, Base,
  unveränderliche Repository-ID und genau eine Datei erneut über GitHub
  gebunden. Erst nachdem der PR `MERGED` mit 40-Hex-Mergecommit meldet, Remote-
  Main exakt diesem Commit entspricht und der Feature-Ref nicht mehr existiert,
  darf die Pages-Run-Suche beginnen. Der unmittelbar normative Expected-Text
  benennt Receipt v3 ausdrücklich als Supersession von v2; es verbleibt dort
  keine v2-Anweisung.
- TDD-Evidenz: vier fokussierte Tests liefen mit sechs erwarteten Fehlern rot
  und danach `4/4` grün. Der vollständige Rolloutvertrag bestand mit `43/43`
  und zwei erwarteten UID-0-Skips; die beiden Root-Probes separat `2/2`.
  `make check` bestand vollständig als `teladi` unter `env -i`.
- Es wurden ausschließlich Rolloutplan, Vertragstest und additive Repo-Ledger
  verändert. Kein Credentialzugriff, Fetch, Push, PR-Write, Merge, Runtime-,
  Archiv-, Install-, Reload-, Service-, Pages-, DNS-, Cloudflare- oder
  Upstream-Write fand statt; alle schreibenden Tests nutzten disposable lokale
  Repositories.

### 2026-08-02 — Additive TLS-Truststore-Korrektur nach sicherem Push-Preflight-Abbruch

- Diese Ergänzung basiert exakt auf Parent
  `8855e65b58ec83e38547f3e8cd2387e252af2c2b` und lässt alle früheren
  Ledgerpassagen unverändert. Der erste autorisierte Pushversuch endete im
  sauberen `teladi`-Kontext beim ersten authentifizierten `git ls-remote`, also
  vor jedem Remote-Write. PR-Head
  `a2f0cff98450b25bbd8ffe20f95b612cdd039e9b` und Remote-Main
  `b00d824adee47341e3251bc18e09239fde1c5939` blieben unverändert.
- Die Root-Reproduktion unter `env -i` isolierte den Fehler: Mit
  `-c http.sslCAInfo=` endete der read-only Transport mit Status 128 und
  `error adding trust anchors from file:`; `-c http.sslCAPath=` allein sowie
  die vollständige Wrappermatrix ohne beide leeren CA-Overrides erreichten
  Status 0. Ein leerer `http.sslCAInfo`-Wert ist damit ein leerer CA-Dateipfad
  und keine neutrale Aufhebung fremder Konfiguration.
- Alle acht normativen Netzwerk-Git-Wrapper — zwei in Task 3 und sechs in
  Task 5 — lassen deshalb ausschließlich diese beiden Leer-Overrides fort und
  verwenden wieder den System-Truststore. `http.sslVerify=true`, kanonische
  HTTPS-Literale, `env -i`, `GIT_CONFIG_NOSYSTEM=1`,
  `GIT_CONFIG_GLOBAL=/dev/null`, Prompt-/Askpass-Sperren und die fail-closed
  Local-Config-Guards bleiben unverändert erhalten.
- TDD-Evidenz: Der neue Vertrag lief vor der Planänderung mit acht erwarteten
  Unterfallfehlern rot, je einem pro Wrapper. Danach bestanden die sieben
  fokussierten TLS-/Config-/Remote-Sicherheitsverträge `7/7`, der vollständige
  Rolloutvertrag `44/44` mit zwei erwarteten Root-Skips und die beiden
  rootgebundenen Runuser-Probes separat `2/2`.
- Diese Korrekturrunde führte keinen Credentialzugriff, Fetch, Push,
  PR-Write, Merge, Install, Reload, Runtime-, Archiv-, Service-, Pages-, DNS-,
  Cloudflare- oder Upstream-Write aus. Die abgebrochene autorisierte
  Vorphase ist ausschließlich als unveränderte historische Evidenz
  protokolliert; alle schreibenden Testproben blieben lokal und disposable.
