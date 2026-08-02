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
expected_task1_paths=(
  web/tests/copy-contract.test.ts
  web/src/layouts/BaseLayout.astro
  web/src/pages/index.astro
  web/src/components/MediaCard.astro
  web/src/pages/projekt/status.astro
)
git diff --cached --quiet
git add -- "${expected_task1_paths[@]}"
expected_task1_index="$(mktemp)"
actual_task1_index="$(mktemp)"
trap 'rm -f -- "$expected_task1_index" "$actual_task1_index"' EXIT
printf '%s\n' "${expected_task1_paths[@]}" | LC_ALL=C sort >"$expected_task1_index"
git diff --cached --name-only --diff-filter=ACMRTUXB | LC_ALL=C sort >"$actual_task1_index"
cmp --silent "$expected_task1_index" "$actual_task1_index"
git commit -m "feat(web): apply approved public story copy"
trap - EXIT
rm -f -- "$expected_task1_index" "$actual_task1_index"
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
task3_pr4_cleanup_pending=0

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
task3_git_probe() {
  /usr/bin/env -i \
    HOME=/home/teladi \
    USER=teladi \
    LOGNAME=teladi \
    PATH=/usr/bin:/bin \
    GIT_CONFIG_NOSYSTEM=1 \
    GIT_CONFIG_GLOBAL=/dev/null \
    /usr/bin/git "$@"
}

assert_canonical_origin() {
  local -a task3_fetch_urls=() task3_push_urls=()
  mapfile -t task3_fetch_urls < <(task3_git_probe remote get-url --all origin)
  mapfile -t task3_push_urls < <(task3_git_probe remote get-url --push --all origin)
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
  if [[ "$task3_pr4_cleanup_pending" == 1 ]]; then
    printf 'PR4 MERGE VERIFIED; EXACT FEATURE CLEANUP PENDING; rerun Step 5, never write main: %s\n' \
      "$receipt_file" >&2
  elif [[ "$task3_remote_committed" == 1 && "$task3_verified" != 1 ]]; then
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
  query='query($owner:String!,$name:String!,$number:Int!,$cursor:String){repository(owner:$owner,name:$name){pullRequest(number:$number){reviews(first:100,after:$cursor){nodes{databaseId state author{__typename login ... on Bot{id databaseId url}}commit{oid}}pageInfo{hasNextPage endCursor}}}}}'
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
  local overview actor actor_id page cursor next_cursor has_next
  local review_candidates='[]'
  local -A seen_thread_cursors=() seen_review_cursors=()

  overview="$(fetch_task3_review_overview)"
  assert_pr_identity "$overview"
  /usr/bin/jq -e --arg required_pr_state "$required_pr_state" '
    ($required_pr_state == "OPEN"
      or $required_pr_state == "MERGED"
      or $required_pr_state == "CLOSED")
    and .state == $required_pr_state
    and .reviewDecision == "APPROVED"
  ' <<<"$overview" >/dev/null

  actor="$(fetch_task3_coderabbit_actor)"
  /usr/bin/jq -e '
    .login == "coderabbitai[bot]"
    and .id == 136622811
  ' <<<"$actor" >/dev/null
  actor_id="$(/usr/bin/jq -r '.id' <<<"$actor")"
  test "$actor_id" = 136622811

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
        and (.author | type == "object")
        and (.author.__typename | type == "string")
        and (.author.login | type == "string")
        and (
          .author.__typename != "Bot"
          or (
            (.author.id | type == "string")
            and (.author.url | type == "string")
            and (.author.databaseId |
              type == "number" and . > 0 and floor == .)
          )
        )
        and (.commit.oid | type == "string" and test("^[0-9a-f]{40}$"))
      )
    ' <<<"$page" >/dev/null
    review_candidates="$(
      /usr/bin/jq -cn \
        --argjson prior "$review_candidates" \
        --argjson current "$(
          /usr/bin/jq -c \
            --arg expected_head "$generator_expected_head" \
            --argjson expected_actor_id "$actor_id" '
            [.nodes[] | select(
              .state == "APPROVED"
              and .author.__typename == "Bot"
              and .author.login == "coderabbitai"
              and .author.databaseId == $expected_actor_id
              and .author.id == "BOT_kgDOCCSy2w"
              and .author.url == "https://github.com/apps/coderabbitai"
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
  generator_review_author_login="$(/usr/bin/jq -r '.login' <<<"$actor")"
  generator_review_author_id="$actor_id"
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

# BEGIN TASK3_PR4_CLOSED_RECOVERY
# This is a one-off reconciliation for PR 4 only. It is deliberately not a
# generic CLOSED => verified rule. The failed reopen request recorded below is
# historical evidence and MUST NOT be replayed.
PR4_REOPEN_EVIDENCE_BLOB=769dac62c3d3fa734945de5e83af4444fad1b9b3
pr4_evidence_relative=docs/superpowers/evidence/2026-08-02-pr4-reopen-422.json

assert_task3_pr4_historical_reopen() {
  local evidence="$1"
  /usr/bin/jq -e '
    keys == ["attempt_count", "binding", "request", "response", "schema"]
    and .schema == "wirtelprimpf-pr4-reopen-rejection/v1"
    and .attempt_count == 1
    and .request == {
      method: "PATCH",
      path: "/repos/H234598/Wirtelprimpf-generator/pulls/4",
      body: {state: "open"}
    }
    and .response == {
      status: 422,
      error: {
        resource: "PullRequest",
        code: "custom",
        field: "state",
        message: "state cannot be changed. These commits are already merged."
      }
    }
    and .binding == {
      actor_login: "H234598",
      actor_id: 54270221,
      repository_id: "R_kgDOTpr2BA",
      repository: "H234598/Wirtelprimpf-generator",
      pr_number: 4,
      receipt_version: 3,
      receipt_state: "remote_committed",
      base_before: "b00d824adee47341e3251bc18e09239fde1c5939",
      expected_head: "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
      head_tree: "967a0b41f6525de79dfc91e1b52dd8ca3dc85ac8",
      merge_sha: "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f",
      merge_parents: [
        "b00d824adee47341e3251bc18e09239fde1c5939",
        "5aab1907b9af73fe6d8ef56e49beb7a527877e19"
      ],
      review_id: 4838199265,
      review_author_id: 136622811,
      review_commit: "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
      review_state: "APPROVED"
    }
  ' <<<"$evidence" >/dev/null
}

assert_task3_pr4_timeline() {
  local timeline="$1"
  /usr/bin/jq -e '
    type == "array"
    and ([.[] | select(
      .event == "closed"
      and .actor.login == "H234598"
      and .actor.id == 54270221
      and .created_at == "2026-08-02T11:08:29Z"
    )] | length) == 1
    and ([.[] | select(
      .event == "head_ref_deleted"
      and .actor.login == "H234598"
      and .actor.id == 54270221
      and .created_at == "2026-08-02T11:08:29Z"
    )] | length) == 1
    and ([.[] | select(
      .event == "head_ref_restored"
      and .actor.login == "H234598"
      and .actor.id == 54270221
      and .created_at == "2026-08-02T11:14:21Z"
    )] | length) == 1
    and ([.[] | select(
      (.created_at > "2026-08-02T11:14:21Z")
      and .event == "head_ref_deleted"
      and .actor.login == "H234598"
      and .actor.id == 54270221
    )] | length) <= 1
    and all(.[];
      (
        .event == "closed"
        and .actor.login == "H234598"
        and .actor.id == 54270221
        and .created_at == "2026-08-02T11:08:29Z"
      )
      or (
        .event == "head_ref_deleted"
        and .actor.login == "H234598"
        and .actor.id == 54270221
        and .created_at == "2026-08-02T11:08:29Z"
      )
      or (
        .event == "head_ref_restored"
        and .actor.login == "H234598"
        and .actor.id == 54270221
        and .created_at == "2026-08-02T11:14:21Z"
      )
      or (
        .created_at > "2026-08-02T11:14:21Z"
        and .event == "head_ref_deleted"
        and .actor.login == "H234598"
        and .actor.id == 54270221
      )
    )
  ' <<<"$timeline" >/dev/null
}

assert_task3_pr4_compare() {
  local compare="$1"
  /usr/bin/jq -e '
    .status == "ahead"
    and .ahead_by == 1
    and .behind_by == 0
    and .total_commits == 1
    and .merge_base_commit.sha == "5aab1907b9af73fe6d8ef56e49beb7a527877e19"
    and .base_commit.sha == "5aab1907b9af73fe6d8ef56e49beb7a527877e19"
    and [.commits[].sha] == ["274b25c9e1f9ea97d3b060997ed5c425d2b30e9f"]
    and (.files | type == "array" and length == 0)
  ' <<<"$compare" >/dev/null
}

assert_task3_pr4_merge_object() {
  local merge_object="$1"
  /usr/bin/jq -e '
    .sha == "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f"
    and .tree.sha == "967a0b41f6525de79dfc91e1b52dd8ca3dc85ac8"
    and [.parents[].sha] == [
      "b00d824adee47341e3251bc18e09239fde1c5939",
      "5aab1907b9af73fe6d8ef56e49beb7a527877e19"
    ]
    and .author == {
      name: "H234598",
      email: "54270221+H234598@users.noreply.github.com",
      date: "2026-08-02T11:00:40Z"
    }
    and .committer == {
      name: "H234598",
      email: "54270221+H234598@users.noreply.github.com",
      date: "2026-08-02T11:00:40Z"
    }
    and .message == "Merge pull request #4 from agent/transactional-settings-live-sync-status"
  ' <<<"$merge_object" >/dev/null
}

assert_task3_pr4_closed_binding() {
  local state="$1" remote_main="$2" remote_head="$3" binding="$4"
  /usr/bin/jq -e \
    --arg state "$state" \
    --arg remote_main "$remote_main" \
    --arg remote_head "$remote_head" '
    keys == [
      "actor", "commit", "compare", "graphql_pr", "historical_reopen",
      "receipt", "refs", "repository", "rest_pr", "review", "timeline",
      "version"
    ]
    and .version == 1
    and .actor == {login: "H234598", id: 54270221}
    and .repository == {
      id: "R_kgDOTpr2BA",
      name_with_owner: "H234598/Wirtelprimpf-generator",
      canonical_origin: "https://github.com/H234598/Wirtelprimpf-generator.git"
    }
    and .receipt == {
      version: 3,
      state: $state,
      pr_number: 4,
      head_ref: "agent/transactional-settings-live-sync-status",
      base_before: "b00d824adee47341e3251bc18e09239fde1c5939",
      expected_head: "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
      head_tree: "967a0b41f6525de79dfc91e1b52dd8ca3dc85ac8",
      merge_sha: "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f"
    }
    and .refs == {main: $remote_main, feature: $remote_head}
    and .graphql_pr == {
      number: 4,
      state: "CLOSED",
      merged: false,
      merge_commit: null,
      viewer_can_reopen: false,
      base_ref: "main",
      head_ref: "agent/transactional-settings-live-sync-status",
      head_oid: "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
      is_draft: false,
      is_cross_repository: false,
      head_repository_id: "R_kgDOTpr2BA",
      head_repository: "H234598/Wirtelprimpf-generator",
      head_owner: "H234598",
      review_decision: "APPROVED"
    }
    and .rest_pr == {
      number: 4,
      state: "closed",
      merged: false,
      merge_commit_sha: "01df605da0cd39f5bbcddfd2ebc9837d74f3f375",
      base_ref: "main",
      base_sha: "b00d824adee47341e3251bc18e09239fde1c5939",
      head_ref: "agent/transactional-settings-live-sync-status",
      head_sha: "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
      base_repository_node_id: "R_kgDOTpr2BA",
      base_repository: "H234598/Wirtelprimpf-generator",
      head_repository_node_id: "R_kgDOTpr2BA",
      head_repository: "H234598/Wirtelprimpf-generator",
      author_login: "H234598",
      author_id: 54270221,
      mergeable: true,
      mergeable_state: "clean"
    }
    and .timeline == [
      {
        event: "closed", actor_login: "H234598", actor_id: 54270221,
        created_at: "2026-08-02T11:08:29Z"
      },
      {
        event: "head_ref_deleted", actor_login: "H234598", actor_id: 54270221,
        created_at: "2026-08-02T11:08:29Z"
      },
      {
        event: "head_ref_restored", actor_login: "H234598", actor_id: 54270221,
        created_at: "2026-08-02T11:14:21Z"
      }
    ]
    and .compare == {
      status: "ahead", ahead_by: 1, behind_by: 0, total_commits: 1,
      merge_base: "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
      base_commit: "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
      commits: ["274b25c9e1f9ea97d3b060997ed5c425d2b30e9f"],
      files_count: 0
    }
    and .commit == {
      sha: "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f",
      tree: "967a0b41f6525de79dfc91e1b52dd8ca3dc85ac8",
      parents: [
        "b00d824adee47341e3251bc18e09239fde1c5939",
        "5aab1907b9af73fe6d8ef56e49beb7a527877e19"
      ],
      author_name: "H234598",
      author_email: "54270221+H234598@users.noreply.github.com",
      author_date: "2026-08-02T11:00:40Z",
      committer_name: "H234598",
      committer_email: "54270221+H234598@users.noreply.github.com",
      committer_date: "2026-08-02T11:00:40Z",
      message: "Merge pull request #4 from agent/transactional-settings-live-sync-status"
    }
    and .review == {
      id: 4838199265,
      author_login: "coderabbitai[bot]",
      author_id: 136622811,
      author_node_id: "BOT_kgDOCCSy2w",
      author_url: "https://github.com/apps/coderabbitai",
      commit: "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
      state: "APPROVED",
      unresolved_threads: 0
    }
    and (.historical_reopen | type == "object")
    and .historical_reopen.schema == "wirtelprimpf-pr4-reopen-rejection/v1"
    and .historical_reopen.attempt_count == 1
    and .historical_reopen.response.status == 422
    and .historical_reopen.response.error == {
      resource: "PullRequest", code: "custom", field: "state",
      message: "state cannot be changed. These commits are already merged."
    }
  ' <<<"$binding" >/dev/null
}

classify_task3_pr4_closed_action() {
  local state="$1" remote_main="$2" remote_head="$3" binding="$4"
  local expected_head=5aab1907b9af73fe6d8ef56e49beb7a527877e19
  local merge_sha=274b25c9e1f9ea97d3b060997ed5c425d2b30e9f
  assert_task3_pr4_closed_binding \
    "$state" "$remote_main" "$remote_head" "$binding"
  if [[ "$state" == remote_committed \
    && "$remote_main" == "$merge_sha" \
    && "$remote_head" == "$expected_head" ]]; then
    printf 'closed-verify-cleanup\n'
  elif [[ "$state" == verified \
    && "$remote_main" == "$merge_sha" \
    && "$remote_head" == "$expected_head" ]]; then
    printf 'closed-cleanup\n'
  elif [[ "$state" == verified \
    && "$remote_main" == "$merge_sha" \
    && -z "$remote_head" ]]; then
    printf 'closed-observe\n'
  else
    return 1
  fi
}

is_task3_pr4_receipt_candidate() {
  test -f "$receipt_file" && test ! -L "$receipt_file"
  test "$(stat -c '%u:%g:%a' "$receipt_file")" = 1000:1000:600
  /usr/bin/jq -e '
    .version == 3
    and (.state == "remote_committed" or .state == "verified")
    and .actor_login == "H234598"
    and .actor_id == 54270221
    and .repository_id == "R_kgDOTpr2BA"
    and .repository == "H234598/Wirtelprimpf-generator"
    and .canonical_origin == "https://github.com/H234598/Wirtelprimpf-generator.git"
    and .pr_number == 4
    and .head_ref == "agent/transactional-settings-live-sync-status"
    and .expected_head == "5aab1907b9af73fe6d8ef56e49beb7a527877e19"
    and .base_before == "b00d824adee47341e3251bc18e09239fde1c5939"
    and .head_tree == "967a0b41f6525de79dfc91e1b52dd8ca3dc85ac8"
    and .merge_sha == "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f"
    and .review_id == 4838199265
    and .review_author_login == "coderabbitai[bot]"
    and .review_author_id == 136622811
    and .review_commit == "5aab1907b9af73fe6d8ef56e49beb7a527877e19"
    and .review_state == "APPROVED"
  ' "$receipt_file" >/dev/null
}

run_task3_pr4_closed_gate() {
  local source_root evidence_path evidence tracked_blob
  local graphql_repository graphql_pr timeline rest_pr compare merge_object
  local graphql_query remote_main remote_head

  generator_head=agent/transactional-settings-live-sync-status
  generator_expected_head=5aab1907b9af73fe6d8ef56e49beb7a527877e19
  load_task3_receipt
  generator_pr_number=$receipt_pr_number
  generator_base_before=$receipt_base_before
  generator_review_id=$receipt_review_id
  generator_review_author_login=$receipt_review_author_login
  generator_review_author_id=$receipt_review_author_id
  generator_review_commit=$receipt_review_commit
  generator_review_state=$receipt_review_state
  derive_task3_merge
  validate_task3_receipt_derivation
  test "$generator_pr_number" = 4
  test "$generator_base_before" = b00d824adee47341e3251bc18e09239fde1c5939
  test "$generator_head_tree" = 967a0b41f6525de79dfc91e1b52dd8ca3dc85ac8
  test "$generator_merge_sha" = 274b25c9e1f9ea97d3b060997ed5c425d2b30e9f
  test "$(/usr/bin/git rev-list --parents -n1 "$generator_merge_sha")" = \
    "$generator_merge_sha $generator_base_before $generator_expected_head"
  /usr/bin/git diff --quiet "$generator_expected_head" "$generator_merge_sha"

  source_root="$(task3_git_probe rev-parse --show-toplevel)"
  test "$source_root" = "$(pwd -P)"
  evidence_path="$source_root/$pr4_evidence_relative"
  test -f "$evidence_path" && test ! -L "$evidence_path"
  test "$(realpath -e -- "$evidence_path")" = "$evidence_path"
  tracked_blob="$(
    task3_git_probe ls-tree HEAD -- "$pr4_evidence_relative" |
      /usr/bin/awk 'NR == 1 {print $3} END {if (NR != 1) exit 1}'
  )"
  test "$tracked_blob" = "$PR4_REOPEN_EVIDENCE_BLOB"
  test "$(task3_git_probe hash-object -- "$evidence_path")" = \
    "$PR4_REOPEN_EVIDENCE_BLOB"
  evidence="$(/usr/bin/jq -c . "$evidence_path")"
  assert_task3_pr4_historical_reopen "$evidence"

  assert_canonical_origin
  require_task3_auth
  require_canonical_repository
  remote_main="$(git_remote ls-remote "$canonical_origin" refs/heads/main | cut -f1)"
  remote_head="$(
    git_remote ls-remote "$canonical_origin" "refs/heads/$generator_head" |
      cut -f1
  )"

  graphql_query='query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){id nameWithOwner pullRequest(number:$number){number state merged viewerCanReopen headRefName headRefOid baseRefName isDraft isCrossRepository headRepository{id nameWithOwner} headRepositoryOwner{login} mergeCommit{oid} reviewDecision}}}'
  graphql_repository="$(
    task3_gh api graphql -f query="$graphql_query" \
      -F owner=H234598 -F name=Wirtelprimpf-generator -F number=4 \
      --jq '.data.repository'
  )"
  assert_canonical_repository_json "$graphql_repository"
  graphql_pr="$(/usr/bin/jq -c '.pullRequest' <<<"$graphql_repository")"
  assert_pr_identity "$graphql_pr"
  /usr/bin/jq -e '
    .number == 4
    and .state == "CLOSED"
    and .merged == false
    and .mergeCommit == null
    and .viewerCanReopen == false
    and .reviewDecision == "APPROVED"
  ' <<<"$graphql_pr" >/dev/null
  timeline="$(
    task3_gh api --paginate --slurp \
      -H 'Accept: application/vnd.github+json' \
      "repos/$canonical_repository/issues/4/timeline?per_page=100" |
      /usr/bin/jq -c '[add[] | select(
        .event == "closed"
        or .event == "head_ref_deleted"
        or .event == "head_ref_restored"
      )]'
  )"
  assert_task3_pr4_timeline "$timeline"

  rest_pr="$(task3_gh api "repos/$canonical_repository/pulls/4")"
  /usr/bin/jq -e '
    .number == 4
    and .state == "closed"
    and .merged == false
    and .merge_commit_sha == "01df605da0cd39f5bbcddfd2ebc9837d74f3f375"
    and .base.ref == "main"
    and .base.sha == "b00d824adee47341e3251bc18e09239fde1c5939"
    and .head.ref == "agent/transactional-settings-live-sync-status"
    and .head.sha == "5aab1907b9af73fe6d8ef56e49beb7a527877e19"
    and .base.repo.node_id == "R_kgDOTpr2BA"
    and .base.repo.full_name == "H234598/Wirtelprimpf-generator"
    and .head.repo.node_id == "R_kgDOTpr2BA"
    and .head.repo.full_name == "H234598/Wirtelprimpf-generator"
    and .user.login == "H234598"
    and .user.id == 54270221
    and .mergeable == true
    and .mergeable_state == "clean"
  ' <<<"$rest_pr" >/dev/null

  compare="$(
    task3_gh api \
      "repos/$canonical_repository/compare/$generator_expected_head...$generator_merge_sha"
  )"
  assert_task3_pr4_compare "$compare"
  merge_object="$(
    task3_gh api "repos/$canonical_repository/git/commits/$generator_merge_sha"
  )"
  assert_task3_pr4_merge_object "$merge_object"

  assert_task3_current_review CLOSED
  test "$generator_review_id" = 4838199265
  test "$generator_review_author_login" = 'coderabbitai[bot]'
  test "$generator_review_author_id" = 136622811
  test "$generator_review_commit" = "$generator_expected_head"
  test "$generator_review_state" = APPROVED
  validate_task3_receipt_derivation

  task3_pr4_binding="$(
    /usr/bin/jq -cn \
      --arg receipt_state "$receipt_state" \
      --arg remote_main "$remote_main" \
      --arg remote_head "$remote_head" \
      --argjson historical_reopen "$evidence" '
      {
        version: 1,
        actor: {login: "H234598", id: 54270221},
        repository: {
          id: "R_kgDOTpr2BA",
          name_with_owner: "H234598/Wirtelprimpf-generator",
          canonical_origin: "https://github.com/H234598/Wirtelprimpf-generator.git"
        },
        receipt: {
          version: 3, state: $receipt_state, pr_number: 4,
          head_ref: "agent/transactional-settings-live-sync-status",
          base_before: "b00d824adee47341e3251bc18e09239fde1c5939",
          expected_head: "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
          head_tree: "967a0b41f6525de79dfc91e1b52dd8ca3dc85ac8",
          merge_sha: "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f"
        },
        refs: {main: $remote_main, feature: $remote_head},
        graphql_pr: {
          number: 4, state: "CLOSED", merged: false, merge_commit: null,
          viewer_can_reopen: false, base_ref: "main",
          head_ref: "agent/transactional-settings-live-sync-status",
          head_oid: "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
          is_draft: false, is_cross_repository: false,
          head_repository_id: "R_kgDOTpr2BA",
          head_repository: "H234598/Wirtelprimpf-generator",
          head_owner: "H234598", review_decision: "APPROVED"
        },
        rest_pr: {
          number: 4, state: "closed", merged: false,
          merge_commit_sha: "01df605da0cd39f5bbcddfd2ebc9837d74f3f375",
          base_ref: "main",
          base_sha: "b00d824adee47341e3251bc18e09239fde1c5939",
          head_ref: "agent/transactional-settings-live-sync-status",
          head_sha: "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
          base_repository_node_id: "R_kgDOTpr2BA",
          base_repository: "H234598/Wirtelprimpf-generator",
          head_repository_node_id: "R_kgDOTpr2BA",
          head_repository: "H234598/Wirtelprimpf-generator",
          author_login: "H234598", author_id: 54270221,
          mergeable: true, mergeable_state: "clean"
        },
        timeline: [
          {event: "closed", actor_login: "H234598", actor_id: 54270221, created_at: "2026-08-02T11:08:29Z"},
          {event: "head_ref_deleted", actor_login: "H234598", actor_id: 54270221, created_at: "2026-08-02T11:08:29Z"},
          {event: "head_ref_restored", actor_login: "H234598", actor_id: 54270221, created_at: "2026-08-02T11:14:21Z"}
        ],
        compare: {
          status: "ahead", ahead_by: 1, behind_by: 0, total_commits: 1,
          merge_base: "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
          base_commit: "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
          commits: ["274b25c9e1f9ea97d3b060997ed5c425d2b30e9f"],
          files_count: 0
        },
        commit: {
          sha: "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f",
          tree: "967a0b41f6525de79dfc91e1b52dd8ca3dc85ac8",
          parents: ["b00d824adee47341e3251bc18e09239fde1c5939", "5aab1907b9af73fe6d8ef56e49beb7a527877e19"],
          author_name: "H234598",
          author_email: "54270221+H234598@users.noreply.github.com",
          author_date: "2026-08-02T11:00:40Z",
          committer_name: "H234598",
          committer_email: "54270221+H234598@users.noreply.github.com",
          committer_date: "2026-08-02T11:00:40Z",
          message: "Merge pull request #4 from agent/transactional-settings-live-sync-status"
        },
        review: {
          id: 4838199265, author_login: "coderabbitai[bot]",
          author_id: 136622811, author_node_id: "BOT_kgDOCCSy2w",
          author_url: "https://github.com/apps/coderabbitai",
          commit: "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
          state: "APPROVED", unresolved_threads: 0
        },
        historical_reopen: $historical_reopen
      }'
  )"
  task3_pr4_remote_main=$remote_main
  task3_pr4_remote_head=$remote_head
  assert_task3_pr4_closed_binding \
    "$receipt_state" "$remote_main" "$remote_head" "$task3_pr4_binding"
}

if [[ -e "$receipt_file" ]] && is_task3_pr4_receipt_candidate; then
  task3_remote_committed=1
  run_task3_pr4_closed_gate
  task3_pr4_action="$(classify_task3_pr4_closed_action \
    "$receipt_state" "$task3_pr4_remote_main" "$task3_pr4_remote_head" \
    "$task3_pr4_binding")"
  case "$task3_pr4_action" in
    closed-verify-cleanup)
      write_task3_receipt verified
      receipt_state=verified
      ;;
    closed-cleanup|closed-observe) ;;
    *) exit 1 ;;
  esac
  task3_verified=1

  if [[ "$task3_pr4_action" != closed-observe ]]; then
    task3_pr4_cleanup_pending=1
    # Rebind every live surface after the local receipt transition and
    # immediately before the only permitted remote mutation.
    run_task3_pr4_closed_gate
    test "$(classify_task3_pr4_closed_action \
      "$receipt_state" "$task3_pr4_remote_main" "$task3_pr4_remote_head" \
      "$task3_pr4_binding")" = closed-cleanup
    # BEGIN TASK3_PR4_FEATURE_REF_DELETE
    git_remote push \
      --force-with-lease=refs/heads/$generator_head:$generator_expected_head \
      "$canonical_origin" \
      ":refs/heads/$generator_head"
    # END TASK3_PR4_FEATURE_REF_DELETE
    test "$(git_remote ls-remote "$canonical_origin" refs/heads/main | cut -f1)" = \
      "$generator_merge_sha"
    test -z "$(
      git_remote ls-remote "$canonical_origin" "refs/heads/$generator_head"
    )"
    task3_pr4_cleanup_pending=0
  fi
  printf 'Verified closed-state generator SHA for Task 4/5: %s\n' \
    "$generator_merge_sha"
  exit 0
fi
# END TASK3_PR4_CLOSED_RECOVERY

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
  generator_pr_candidates="$(
    task3_gh pr list \
      --repo "$canonical_repository" \
      --state open --base main --head "$generator_head" --limit 2 \
      --json number,state,headRefName,headRefOid,baseRefName,isDraft,isCrossRepository,headRepository,headRepositoryOwner
  )"
  /usr/bin/jq -e '
    type == "array"
    and length == 1
    and (.[0].number | type == "number" and . > 0 and floor == .)
    and .[0].state == "OPEN"
  ' <<<"$generator_pr_candidates" >/dev/null
  generator_pr_candidate="$(/usr/bin/jq -c '.[0]' <<<"$generator_pr_candidates")"
  assert_pr_identity "$generator_pr_candidate"
  generator_pr_number="$(/usr/bin/jq -r '.[0].number' <<<"$generator_pr_candidates")"
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
  # The exact v3 parser above already bound this persisted approval to the
  # immutable reviewed head. Hydrate only those validated fields, reconstruct
  # the deterministic merge, and compare the complete derivation before any
  # remote-state classification. A live review gate remains mandatory in the
  # push branch immediately before mutation, but never gates reconcile/observe.
  generator_review_id="$receipt_review_id"
  generator_review_author_login="$receipt_review_author_login"
  generator_review_author_id="$receipt_review_author_id"
  generator_review_commit="$receipt_review_commit"
  generator_review_state="$receipt_review_state"
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

Expected: GitHub main contains the deterministic two-parent merge after one atomic exact-base/exact-head lease CAS, the reviewed PR head branch is deleted in that same atomic update, and the printed 40-character SHA is recorded as the only factory reference permitted in Tasks 4–5. Normally GitHub reports the same object as the PR's indirect merge; see the official [indirect merges contract](https://docs.github.com/en/pull-requests/reference/pull-request-merges?apiVersion=2022-11-28#indirect-merges). The applied-rules response must be exactly `[]`, and classic protection must be an authenticated exact HTTP 404; every nonempty array, HTTP 200, unclassified response or API failure stops the remote mutation. The PR head name, OID, same-repository bit, owner, repository ID and `nameWithOwner` agree exactly. Every fetch-/push-URL value is enumerated with `--all`; each set has cardinality one and equals canonical HTTPS. Every subsequent fetch, `ls-remote`, and push uses that URL literal, never the mutable remote name. No protection is bypassed or weakened.

Both persisted `gh` authentication contexts were invalid at the last local preflight; successful unauthenticated public reads are not write authorization. Steps 3–5 therefore require an externally supplied ephemeral `GH_TOKEN`, immediately disable xtrace before its first reference, unset its exported source, and relay its bytes only through private anonymous descriptors into a clean UID/GID-`teladi` shell. That long-lived shell retains only a non-exported variable and closes the relay descriptor immediately. Each `gh` or authenticated Git process receives the token through a fresh short-lived pipe; it never appears in argv, here-doc text, files, tests/builds, or merge hooks. `/user` must equal login `H234598` and numeric ID `54270221`. Authenticated Git clears credential helpers, installs only `gh auth git-credential`, disables hooks with `core.hooksPath=/dev/null`, and receives no persistent credential setup.

The private atomic v3 receipt at `/home/teladi/.local/state/wirtelprimpf/task3-merge/generator-main-receipt.json` supersedes the earlier v2 contract. It is owned by `teladi`, mode `0600`, uses an exact no-extra-field schema, and binds actor login/ID, repository ID/name, canonical URL, PR/ref/head/base, the reviewed head tree, deterministic date/message, merge OID, and the exact trusted review ID/author/commit/state. Every run derives `expected_head^{tree}` from trusted Git state and reconstructs the deterministic commit from fixed identity plus trusted PR/head/base inputs before accepting receipt-derived values. Malformed, extra-field, stale, or forged receipts fail closed; failed atomic replacements remove their private temporary file. The normal state machine advances only `planned -> remote_committed -> verified`. A successful push is latched before any fallible observation; a push/receipt crash reconciles from the exact remote ref pair, while normal committed states classify only as `reconcile` or `observe` and can never re-enter `push`. API convergence failures report `REMOTE COMMIT COMPLETE; VERIFICATION PENDING`; every unknown combination fails closed. The runtime checkout remains untouched until Task 4.

PR 4 is the sole, hard-coded exception to GitHub's normal visible merge
classification. It may enter the additive recovery block only with the exact
v3 receipt, Actor/Repository/PR/Base/Head/Tree/Merge/parent/review constants
printed in that block. Every run then rebinds live authentication, canonical
repository, main and feature refs, `CLOSED + merged=false + mergeCommit=null +
viewerCanReopen=false`, the complete relevant paginated timeline, REST PR,
head-to-merge Compare result, immutable Git commit and the current exact
CodeRabbit approval with no unresolved thread. The one previously rejected
reopen request is a committed machine-readable blob with exact HTTP 422 and
`PullRequest/custom/state/already merged` fields; it is never sent again.

Only this complete conjunction may move the v3 receipt from
`remote_committed` to `verified`. Before the restored feature ref is removed,
the entire live conjunction is fetched and checked a second time. That cleanup
contains one feature-only exact lease deletion and no main refspec, force of
main, PR mutation or generic `CLOSED => verified` rule. A verified retry with
the exact restored ref may only finish that cleanup; a verified retry with an
absent ref may only observe. Any other receipt/ref/API/timeline combination
fails closed and never reaches either push path.

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

Die frühere Zahl 450 war ein veralteter Snapshot und darf keine Besitzänderung
mehr autorisieren. Die unmittelbar vorherige 84-Pfad-Runtime-Allowlist bleibt
historisch und idempotent unverändert; ihr separater Live-Runtime-Arbeitsbaum
ist nach dem bereits abgeschlossenen Handoff vollständig `1000:1000`. Ein
irrtümlich als Root erzeugter lokaler Commit schrieb jedoch exakt 16 neue
`root:root`-Einträge in das von allen Worktrees gemeinsam verwendete
`/home/teladi/.local/share/wirtelprimpf-generator/.git`: acht lose Objekte,
sechs dazugehörige Shard-Verzeichnisse, den Branchref und den verknüpften
Worktree-Index. Der aktuelle read-only Befund bindet diese 16 Positionen mit
Device, Inode, Typ, Modus, Linkzahl und bei Dateien zusätzlich Größe und
SHA-256; kein Modus erzeugt die Allowlist bei Drift neu. Davon strikt getrennt
liegen sieben root-eigene Pyc-Dateien ausschließlich im Agent-Worktree
`/home/teladi/codex_worktrees/Wirtelprimpf-generator-transactional`. Sechs
entstanden bei einem vorzeitig im Root-Kontext gestarteten und vor jeder
Installation/Laufzeitaktion abgebrochenen Matrixlauf; ein Rollout-Pyc bestand
schon zuvor. Auch diese sieben Dateien sind mit Root-Device/Inode, Modus,
Linkzahl, Größe und SHA-256 unveränderlich gebunden. Sie werden weder als Teil
der Live-Runtime noch als Erweiterung der 84-Pfad-Allowlist behandelt.

Der exakte Zwei-Root-Gate läuft deshalb zuerst. Er darf jede der 16
Shared-Git- und sieben Agent-Worktree-Positionen
entweder als exakten `root:root`-Eintritt oder als bereits übergebenes
`1000:1000`-Objekt finden und vervollständigt ausschließlich zielwärts. Für die
14 unveränderlichen Objektpositionen bleiben Inode und Dateiinhalt auch nach
dem Handoff fest. Nur Ref und Index dürfen nach vollständiger Übergabe durch
einen späteren Git-Write als `teladi` atomar ersetzt werden; ein neuer
root-eigener Ref/Index-Inode wird niemals gelernt oder repariert. Jeder dritte
Besitzer, jeder zusätzliche fremdbesessene Pfad, eine fehlende Position,
Symlinks oder Special Files in der Fremdbesitzmenge, mehrfach verlinkte
reguläre Dateien, Submounts und nichtkanonische Pfade stoppen vor dem ersten
Write. Erst danach bestätigt der unveränderte 84-Pfad-Gate, dass auch der
Runtime-Arbeitsbaum vollständig `teladi` gehört. Bereits korrekte venv-Symlinks
werden weiterhin weder verfolgt noch verändert.

Danach öffnet Root jeden aufgezeichneten Pfad komponentenweise relativ zu einem
kanonischen Runtime-Directory-FD mit `O_NOFOLLOW`, bindet Device, Inode, Typ,
Linkzahl, den individuellen Eintrittsbesitzer und den festen Zielbesitzer
nochmals per `fstat` und hält alle FDs bis zum Transaktionsende offen.
Unmittelbar vor **jedem** `fchown` wird derselbe Stand erneut geprüft. Bei
Prüfungs-/Writefehlern sowie HUP, INT oder TERM klassifiziert der Rollback unter
blockierten Transaktionssignalen **jeden** vorregistrierten FD: unveränderter
Eintrittsbesitz bleibt unangetastet; nur ein vom individuellen
`root:root`-Eintrittszustand bereits auf `1000:1000` gewechselter FD wird exakt
auf seinen Eintrittsbesitzer zurückgesetzt und verifiziert. Jeder dritte Zustand
macht den Rollback ausdrücklich `INCOMPLETE` und ist ein eigener harter Fehler.
Ein signalbedingter, vollständiger Rollback endet mit `128 + Signalnummer` und
druckt niemals die Erfolgsmeldung.

Beide finalen Commitpunkte blockieren HUP, INT und TERM, konsumieren bereits
anstehende Transaktionssignale und stellen die vorherigen Signalhandler noch vor
dem Entsperren wieder her; ein spät eintreffendes Signal kann daher nicht als
scheinbarer Erfolg verschluckt werden. SIGKILL ist nicht abfangbar: Ein dadurch
zurückbleibender Mischzustand wird beim nächsten Lauf aus denselben statischen
16-, 7- beziehungsweise 84-Pfad-Allowlisten erkannt und zielwärts beendet, niemals
aus einem neu erzeugten Inventar. Beide Heredocs starten ausschließlich mit dem
absoluten Interpreter und `-I`; die Programme prüfen `isolated` und `safe_path`
vor jedem schattenbaren Import. Es gibt keine `safe.directory`-Ausnahme und
keinen pfadbasierten rekursiven `chown`:

```bash
test "$(id -u)" = 0
runtime=/home/teladi/.local/share/wirtelprimpf-generator
test -d "$runtime" && test ! -L "$runtime"
test "$(realpath -e -- "$runtime")" = "$runtime"

# The shared common Git directory is repaired first. The branch ref and linked
# worktree index are exact root-owned handoff records now, but Git may replace
# their inode/content after this handoff once every write runs as teladi. Such
# target-owned post-handoff drift is accepted; a newly root-owned replacement
# is never inferred or repaired. Every object record remains immutable.
shared_git_common=/home/teladi/.local/share/wirtelprimpf-generator/.git
expected_shared_git_inventory_count=16
expected_shared_git_inventory_sha256=1567d717e89da2f2acaf88ea1c2d7cba6c7a4e5fa646ab4c3a94f0e008aa8bf0
agent_worktree=/home/teladi/codex_worktrees/Wirtelprimpf-generator-transactional
expected_agent_worktree_inventory_count=7
expected_agent_worktree_inventory_sha256=7c35636e7407ea0ce0edc52010a932e858dc749e0f0a0354fd3debe49ccb361a
/usr/bin/python3 -I - "$shared_git_common" \
  "$expected_shared_git_inventory_count" \
  "$expected_shared_git_inventory_sha256" \
  "$agent_worktree" \
  "$expected_agent_worktree_inventory_count" \
  "$expected_agent_worktree_inventory_sha256" <<'TASK4_SHARED_GIT_OWNERSHIP_PY'
from __future__ import annotations

import sys

if __name__ == "__main__" and (
    sys.flags.isolated != 1 or sys.flags.safe_path != 1
):
    raise SystemExit("shared Git ownership gate requires isolated safe-path Python")

import hashlib
import json
import os
import signal
import stat
from pathlib import Path
from typing import Any


EXPECTED_SHARED_GIT_ROOT = {
    "dev": 53,
    "ino": 7962067,
    "mode": 0o755,
}
EXPECTED_AGENT_WORKTREE_ROOT = {
    "dev": 53,
    "ino": 8063998,
    "mode": 0o755,
}
EXPECTED_OWNERSHIP_ROOTS = {
    "/home/teladi/.local/share/wirtelprimpf-generator/.git": EXPECTED_SHARED_GIT_ROOT,
    "/home/teladi/codex_worktrees/Wirtelprimpf-generator-transactional": EXPECTED_AGENT_WORKTREE_ROOT,
}
EXPECTED_SHARED_GIT_INVENTORY = (
    {
        "type": "f",
        "path": "objects/36/5ac97aa8e7d6e5e57a8cbd28fd4d6fb726f305",
        "dev": 53,
        "ino": 8255432,
        "mode": 0o444,
        "nlink": 1,
        "size": 122911,
        "sha256": "f30bc04feea78c722b9e5ceedc538cb37f71a8c3c1afb3d6bc57cf160a5c8580",
        "mutable_after_handoff": False,
    },
    {"type": "d", "path": "objects/72", "dev": 53, "ino": 8255440, "mode": 0o755, "nlink": 1, "mutable_after_handoff": False},
    {
        "type": "f",
        "path": "objects/72/32f8d030b796cfc3f3f3d58ab5c4274b7a9d15",
        "dev": 53,
        "ino": 8255441,
        "mode": 0o444,
        "nlink": 1,
        "size": 54,
        "sha256": "deb7ce19bde9b9581efa0e4a09a4c070749cd67112fb8d253d1a7b085d962397",
        "mutable_after_handoff": False,
    },
    {"type": "d", "path": "objects/88", "dev": 53, "ino": 8255438, "mode": 0o755, "nlink": 1, "mutable_after_handoff": False},
    {
        "type": "f",
        "path": "objects/88/728187e9d0b9b06f0d645f12292c2ba4433a5f",
        "dev": 53,
        "ino": 8255439,
        "mode": 0o444,
        "nlink": 1,
        "size": 110,
        "sha256": "a03625cf425d2f01446ba96f47d5b78bcb076e2d96e76ade42bb81d4a9ea205c",
        "mutable_after_handoff": False,
    },
    {"type": "d", "path": "objects/95", "dev": 53, "ino": 8255433, "mode": 0o755, "nlink": 1, "mutable_after_handoff": False},
    {
        "type": "f",
        "path": "objects/95/6c9fa1c5f623e5c5280a5f76e32c4266b95e90",
        "dev": 53,
        "ino": 8255434,
        "mode": 0o444,
        "nlink": 1,
        "size": 42909,
        "sha256": "9b392082ba24bb04ed012787f64d85bb26347716b298825ce29849c3963fbccb",
        "mutable_after_handoff": False,
    },
    {"type": "d", "path": "objects/a1", "dev": 53, "ino": 8255436, "mode": 0o755, "nlink": 1, "mutable_after_handoff": False},
    {
        "type": "f",
        "path": "objects/a1/1733f4032575b4ff75ccff8d8875dcdc0c8fd5",
        "dev": 53,
        "ino": 8255437,
        "mode": 0o444,
        "nlink": 1,
        "size": 212,
        "sha256": "e264dcdbf636ec8d7f9bb099a2bb98d51cacae5068181897d1d2d18d78671c87",
        "mutable_after_handoff": False,
    },
    {"type": "d", "path": "objects/b2", "dev": 53, "ino": 8255443, "mode": 0o755, "nlink": 1, "mutable_after_handoff": False},
    {
        "type": "f",
        "path": "objects/b2/51ed552f7eaf74e18dd0362b9e10db50a3001a",
        "dev": 53,
        "ino": 8255444,
        "mode": 0o444,
        "nlink": 1,
        "size": 542,
        "sha256": "afa9a26b1fa7f6a53a5d5566ac90732141c8ad5a322e1d06ec8fe4f9370e8857",
        "mutable_after_handoff": False,
    },
    {"type": "d", "path": "objects/c8", "dev": 53, "ino": 8255445, "mode": 0o755, "nlink": 1, "mutable_after_handoff": False},
    {
        "type": "f",
        "path": "objects/c8/4d957dee6206774a4d98689726dce38472e4b3",
        "dev": 53,
        "ino": 8255446,
        "mode": 0o444,
        "nlink": 1,
        "size": 185,
        "sha256": "d4a47fdefa6800ac688b9ebb72f069a60137a72c08e15809d4883a6c5fa8d8bc",
        "mutable_after_handoff": False,
    },
    {
        "type": "f",
        "path": "objects/cb/0cea7105f5cc3fd1ae622e6513ea09681821b0",
        "dev": 53,
        "ino": 8255442,
        "mode": 0o444,
        "nlink": 1,
        "size": 453,
        "sha256": "a4f55d1f9586d51eeaa44c7a6f2e3161e51f23c59b9cd128545eed1c28f64c5a",
        "mutable_after_handoff": False,
    },
    {
        "type": "f",
        "path": "refs/heads/agent/pr4-closed-merge-reconcile",
        "dev": 53,
        "ino": 8255448,
        "mode": 0o644,
        "nlink": 1,
        "size": 41,
        "sha256": "3f80500cb40140e6642e336b26e8246d538cb3d82d6351724b79dd460e9a8633",
        "mutable_after_handoff": True,
    },
    {
        "type": "f",
        "path": "worktrees/Wirtelprimpf-generator-transactional/index",
        "dev": 53,
        "ino": 8255435,
        "mode": 0o644,
        "nlink": 1,
        "size": 16384,
        "sha256": "27711dcae0f8384c048416b540b052dfebd27ce790e67ba6717230653defd10b",
        "mutable_after_handoff": True,
    },
)
EXPECTED_SHARED_GIT_INVENTORY_SHA256 = "1567d717e89da2f2acaf88ea1c2d7cba6c7a4e5fa646ab4c3a94f0e008aa8bf0"
EXPECTED_AGENT_WORKTREE_INVENTORY = (
    {
        "type": "f",
        "path": "Sourcecode/__pycache__/wirtelprimpf_generator.cpython-314.pyc",
        "dev": 53,
        "ino": 8260528,
        "mode": 0o644,
        "nlink": 1,
        "size": 179978,
        "sha256": "a87459c4d56cb0f4a19c8c9887b2e063bd4439cfbd103420f3e43aa563c90ba4",
        "mutable_after_handoff": False,
    },
    {
        "type": "f",
        "path": "files/wirtelprimfgenerator@H234598/__pycache__/SettingsLogo.cpython-314.pyc",
        "dev": 53,
        "ino": 8260530,
        "mode": 0o644,
        "nlink": 1,
        "size": 79049,
        "sha256": "88da66685a5126fa15f86ef0dbd4ff8f87d81cc9acd018bc92845f566c64b6a8",
        "mutable_after_handoff": False,
    },
    {
        "type": "f",
        "path": "files/wirtelprimfgenerator@H234598/__pycache__/StoryDirectives.cpython-314.pyc",
        "dev": 53,
        "ino": 8260533,
        "mode": 0o644,
        "nlink": 1,
        "size": 17229,
        "sha256": "c2db579a19d9ab4fc6da858ab4794bb12fd50a6f4b148c94956901d73a173f72",
        "mutable_after_handoff": False,
    },
    {
        "type": "f",
        "path": "files/wirtelprimfgenerator@H234598/__pycache__/helper.cpython-314.pyc",
        "dev": 53,
        "ino": 8260529,
        "mode": 0o644,
        "nlink": 1,
        "size": 103680,
        "sha256": "4c4eb97a67f1699ead445bed3caa703522b99470f97eecdbd4b3118023619a25",
        "mutable_after_handoff": False,
    },
    {
        "type": "f",
        "path": "files/wirtelprimfgenerator@H234598/__pycache__/settings_sync.cpython-314.pyc",
        "dev": 53,
        "ino": 8260531,
        "mode": 0o644,
        "nlink": 1,
        "size": 71684,
        "sha256": "2dd89ccf346e4215a49a425a4755aeea51b5c106865e25a53b5f4122629ff41d",
        "mutable_after_handoff": False,
    },
    {
        "type": "f",
        "path": "files/wirtelprimfgenerator@H234598/__pycache__/story_directives_core.cpython-314.pyc",
        "dev": 53,
        "ino": 8260532,
        "mode": 0o644,
        "nlink": 1,
        "size": 40742,
        "sha256": "ced12684398a0f49b4f581ce393809150cc4f1e0d7f3ce3ac2d8e4a0b2e4dc68",
        "mutable_after_handoff": False,
    },
    {
        "type": "f",
        "path": "tests/__pycache__/test_rollout_plan_contract.cpython-314.pyc",
        "dev": 53,
        "ino": 8255088,
        "mode": 0o644,
        "nlink": 1,
        "size": 233891,
        "sha256": "1d2bf1c7cccad0c82e0e224f8546a47a0e2992144db0187cf3e44adcf86da377",
        "mutable_after_handoff": False,
    },
)
EXPECTED_AGENT_WORKTREE_INVENTORY_SHA256 = "7c35636e7407ea0ce0edc52010a932e858dc749e0f0a0354fd3debe49ccb361a"
TRANSACTION_SIGNALS = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)


class SharedGitOwnershipInterrupted(RuntimeError):
    def __init__(self, signum: int) -> None:
        super().__init__(f"shared Git ownership interrupted by signal {signum}")
        self.signum = signum
        self.exit_code = 128 + signum


def canonical_shared_git_inventory_digest(records: tuple[dict[str, Any], ...]) -> str:
    projection = sorted(records, key=lambda record: os.fsencode(str(record["path"])))
    payload = json.dumps(
        projection,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _canonical_shared_git_root(root: str, target_uid: int, target_gid: int) -> str:
    path = Path(root)
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise RuntimeError("shared Git root is not an absolute real directory")
    canonical = os.path.realpath(root)
    if canonical != root:
        raise RuntimeError("shared Git root is not canonical")
    metadata = os.lstat(root)
    if not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError("shared Git root type drift")
    if (metadata.st_uid, metadata.st_gid) != (target_uid, target_gid):
        raise RuntimeError("shared Git root ownership drift")
    expected_root = EXPECTED_OWNERSHIP_ROOTS.get(root)
    if expected_root is not None and (
        metadata.st_dev != expected_root["dev"]
        or metadata.st_ino != expected_root["ino"]
        or stat.S_IMODE(metadata.st_mode) != expected_root["mode"]
    ):
        raise RuntimeError("exact ownership root identity drift")
    return canonical


def _validate_static_shared_git_inventory(
    expected_static: tuple[dict[str, Any], ...],
) -> dict[str, dict[str, Any]]:
    if not isinstance(expected_static, tuple) or not expected_static:
        raise RuntimeError("empty shared Git inventory rejected")
    expected_by_path: dict[str, dict[str, Any]] = {}
    for record in expected_static:
        kind = record.get("type")
        path = record.get("path")
        common = {"type", "path", "dev", "ino", "mode", "nlink", "mutable_after_handoff"}
        required = common | ({"size", "sha256"} if kind == "f" else set())
        if set(record) != required:
            raise RuntimeError("invalid shared Git inventory record fields")
        if (
            kind not in ("f", "d")
            or not isinstance(path, str)
            or os.path.isabs(path)
            or any(part in ("", ".", "..") for part in path.split(os.sep))
            or path in expected_by_path
            or not isinstance(record.get("mutable_after_handoff"), bool)
            or (record.get("mutable_after_handoff") and kind != "f")
        ):
            raise RuntimeError("invalid shared Git inventory path/type")
        if kind == "f" and (
            not isinstance(record.get("size"), int)
            or record["size"] < 1
            or not isinstance(record.get("sha256"), str)
            or len(record["sha256"]) != 64
        ):
            raise RuntimeError("invalid shared Git file binding")
        expected_by_path[path] = record
    return expected_by_path


def _sha256_fd(fd: int) -> str:
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        digest.update(chunk)
    os.lseek(fd, 0, os.SEEK_SET)
    return digest.hexdigest()


def _open_relative_shared_git(root_fd: int, relative: str, kind: str) -> int:
    components = relative.split(os.sep)
    directory_fd = os.dup(root_fd)
    try:
        for component in components[:-1]:
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            next_fd = os.open(component, flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        flags = os.O_RDONLY | os.O_CLOEXEC
        if kind == "d":
            flags |= os.O_DIRECTORY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        return os.open(components[-1], flags, dir_fd=directory_fd)
    finally:
        os.close(directory_fd)


def _validate_shared_git_fd(
    fd: int,
    record: dict[str, Any],
    source_uid: int,
    source_gid: int,
    target_uid: int,
    target_gid: int,
) -> dict[str, Any]:
    metadata = os.fstat(fd)
    kind = "f" if stat.S_ISREG(metadata.st_mode) else "d" if stat.S_ISDIR(metadata.st_mode) else "?"
    owner = (metadata.st_uid, metadata.st_gid)
    if kind != record["type"]:
        raise RuntimeError("shared Git object type drift")
    if owner not in {(source_uid, source_gid), (target_uid, target_gid)}:
        raise RuntimeError("shared Git object third-owner drift")
    if (
        metadata.st_dev != record["dev"]
        or stat.S_IMODE(metadata.st_mode) != record["mode"]
        or metadata.st_nlink != record["nlink"]
    ):
        raise RuntimeError("shared Git object metadata drift")
    exact_identity_required = owner == (source_uid, source_gid) or not record["mutable_after_handoff"]
    if exact_identity_required and metadata.st_ino != record["ino"]:
        raise RuntimeError("shared Git object identity drift")
    if kind == "f" and exact_identity_required:
        if metadata.st_size != record["size"]:
            raise RuntimeError("shared Git object size drift")
        if _sha256_fd(fd) != record["sha256"]:
            raise RuntimeError("shared Git object digest drift")
    return {
        "path": record["path"],
        "type": kind,
        "dev": metadata.st_dev,
        "ino": metadata.st_ino,
        "mode": stat.S_IMODE(metadata.st_mode),
        "nlink": metadata.st_nlink,
        "size": metadata.st_size,
        "uid": metadata.st_uid,
        "gid": metadata.st_gid,
        "mutable_after_handoff": record["mutable_after_handoff"],
        "sha256": _sha256_fd(fd) if kind == "f" else None,
    }


def _scan_foreign_shared_git_paths(
    root: str,
    source_uid: int,
    source_gid: int,
    target_uid: int,
    target_gid: int,
    allowed_paths: set[str],
) -> set[str]:
    root_device = os.lstat(root).st_dev
    foreign: set[str] = set()
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                metadata = entry.stat(follow_symlinks=False)
                if metadata.st_dev != root_device:
                    raise RuntimeError("unexpected shared Git submount")
                relative = os.path.relpath(entry.path, root)
                if (
                    os.path.isabs(relative)
                    or any(part in ("", ".", "..") for part in relative.split(os.sep))
                ):
                    raise RuntimeError("invalid shared Git relative path")
                owner = (metadata.st_uid, metadata.st_gid)
                if owner != (target_uid, target_gid):
                    if owner != (source_uid, source_gid):
                        raise RuntimeError("unexpected foreign shared Git owner")
                    if relative not in allowed_paths:
                        raise RuntimeError("unexpected foreign shared Git path")
                    if stat.S_ISLNK(metadata.st_mode):
                        raise RuntimeError("foreign shared Git symlink rejected")
                    foreign.add(relative)
                if stat.S_ISDIR(metadata.st_mode):
                    pending.append(entry.path)
    return foreign


def capture_shared_git_repair_inventory(
    root: str,
    expected_static: tuple[dict[str, Any], ...],
    source_uid: int,
    source_gid: int,
    target_uid: int,
    target_gid: int,
) -> tuple[dict[str, Any], ...]:
    if (source_uid, source_gid) == (target_uid, target_gid):
        raise RuntimeError("shared Git source and target owners must differ")
    canonical = _canonical_shared_git_root(root, target_uid, target_gid)
    expected_by_path = _validate_static_shared_git_inventory(expected_static)
    foreign = _scan_foreign_shared_git_paths(
        canonical,
        source_uid,
        source_gid,
        target_uid,
        target_gid,
        set(expected_by_path),
    )
    root_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        root_flags |= os.O_NOFOLLOW
    root_fd = os.open(canonical, root_flags)
    observed: list[dict[str, Any]] = []
    try:
        for relative in sorted(expected_by_path, key=os.fsencode):
            record = expected_by_path[relative]
            fd = _open_relative_shared_git(root_fd, relative, record["type"])
            try:
                current = _validate_shared_git_fd(
                    fd,
                    record,
                    source_uid,
                    source_gid,
                    target_uid,
                    target_gid,
                )
            finally:
                os.close(fd)
            if (current["uid"], current["gid"]) == (source_uid, source_gid):
                if relative not in foreign:
                    raise RuntimeError("shared Git foreign scan/binding mismatch")
            elif relative in foreign:
                raise RuntimeError("shared Git target scan/binding mismatch")
            current["static"] = record
            observed.append(current)
    finally:
        os.close(root_fd)
    return tuple(observed)


def bind_shared_git_inventory_fds(
    root: str,
    observed: tuple[dict[str, Any], ...],
    source_uid: int,
    source_gid: int,
    target_uid: int,
    target_gid: int,
) -> list[dict[str, Any]]:
    canonical = _canonical_shared_git_root(root, target_uid, target_gid)
    root_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        root_flags |= os.O_NOFOLLOW
    root_fd = os.open(canonical, root_flags)
    bound: list[dict[str, Any]] = []
    try:
        for captured in observed:
            fd = _open_relative_shared_git(
                root_fd, captured["path"], captured["type"]
            )
            try:
                rebound = _validate_shared_git_fd(
                    fd,
                    captured["static"],
                    source_uid,
                    source_gid,
                    target_uid,
                    target_gid,
                )
                for key in ("path", "type", "dev", "ino", "mode", "nlink", "size", "uid", "gid", "sha256"):
                    if rebound[key] != captured[key]:
                        raise RuntimeError("shared Git object changed before FD binding")
                item = dict(captured)
                item["fd"] = fd
                bound.append(item)
                fd = -1
            finally:
                if fd >= 0:
                    os.close(fd)
    except BaseException:
        close_bound_shared_git_inventory(bound)
        raise
    finally:
        os.close(root_fd)
    return bound


def close_bound_shared_git_inventory(bound: list[dict[str, Any]]) -> None:
    for item in bound:
        fd = item.pop("fd", None)
        if isinstance(fd, int):
            os.close(fd)


def _verify_bound_shared_git_item(item: dict[str, Any]) -> tuple[int, int]:
    metadata = os.fstat(item["fd"])
    kind = "f" if stat.S_ISREG(metadata.st_mode) else "d" if stat.S_ISDIR(metadata.st_mode) else "?"
    if (
        kind != item["type"]
        or metadata.st_dev != item["dev"]
        or metadata.st_ino != item["ino"]
        or stat.S_IMODE(metadata.st_mode) != item["mode"]
        or metadata.st_nlink != item["nlink"]
        or (kind == "f" and metadata.st_size != item["size"])
        or (kind == "f" and _sha256_fd(item["fd"]) != item["sha256"])
    ):
        raise RuntimeError("bound shared Git object drift")
    return metadata.st_uid, metadata.st_gid


def apply_shared_git_ownership_transaction(
    bound: list[dict[str, Any]],
    source_uid: int,
    source_gid: int,
    target_uid: int,
    target_gid: int,
) -> None:
    source = (source_uid, source_gid)
    target = (target_uid, target_gid)
    prior_handlers = {signum: signal.getsignal(signum) for signum in TRANSACTION_SIGNALS}
    changed: list[dict[str, Any]] = []
    handlers_restored = False
    blocked = False

    def interrupt(signum: int, _frame: object) -> None:
        raise SharedGitOwnershipInterrupted(signum)

    for signum in TRANSACTION_SIGNALS:
        signal.signal(signum, interrupt)
    try:
        try:
            for item in bound:
                owner = _verify_bound_shared_git_item(item)
                if owner == target:
                    continue
                if owner != source:
                    raise RuntimeError("bound shared Git object owner drift")
                os.fchown(item["fd"], target_uid, target_gid)
                if _verify_bound_shared_git_item(item) != target:
                    raise RuntimeError("shared Git fchown verification failed")
                changed.append(item)
            signal.pthread_sigmask(signal.SIG_BLOCK, TRANSACTION_SIGNALS)
            blocked = True
            pending = set(signal.sigpending()).intersection(TRANSACTION_SIGNALS)
            if pending:
                raise SharedGitOwnershipInterrupted(min(int(item) for item in pending))
            for signum, handler in prior_handlers.items():
                signal.signal(signum, handler)
            handlers_restored = True
            signal.pthread_sigmask(signal.SIG_UNBLOCK, TRANSACTION_SIGNALS)
            blocked = False
            return
        except BaseException as exc:
            if not blocked:
                signal.pthread_sigmask(signal.SIG_BLOCK, TRANSACTION_SIGNALS)
                blocked = True
            rollback_incomplete = False
            for item in reversed(bound):
                try:
                    owner = _verify_bound_shared_git_item(item)
                    initial = (item["uid"], item["gid"])
                    if initial == source and owner == target:
                        os.fchown(item["fd"], source_uid, source_gid)
                        if _verify_bound_shared_git_item(item) != source:
                            rollback_incomplete = True
                    elif owner != initial:
                        rollback_incomplete = True
                except BaseException:
                    rollback_incomplete = True
            outcome = "INCOMPLETE" if rollback_incomplete else "complete"
            if isinstance(exc, SharedGitOwnershipInterrupted):
                if rollback_incomplete:
                    raise RuntimeError("shared Git ownership rollback INCOMPLETE") from exc
                raise
            raise RuntimeError(f"shared Git ownership rollback {outcome}") from exc
    finally:
        if not handlers_restored:
            for signum, handler in prior_handlers.items():
                signal.signal(signum, handler)
        if blocked:
            signal.pthread_sigmask(signal.SIG_UNBLOCK, TRANSACTION_SIGNALS)


def _main(argv: list[str]) -> None:
    if sys.flags.isolated != 1 or sys.flags.safe_path != 1:
        raise RuntimeError("shared Git ownership gate requires isolated safe-path Python")
    if len(argv) != 6:
        raise RuntimeError("invalid exact two-root ownership gate arguments")
    (
        shared_root,
        shared_count_text,
        shared_digest,
        worktree_root,
        worktree_count_text,
        worktree_digest,
    ) = argv
    if os.geteuid() != 0 or os.getegid() != 0:
        raise RuntimeError("exact two-root ownership repair requires root:root")
    if set((shared_root, worktree_root)) != set(EXPECTED_OWNERSHIP_ROOTS):
        raise RuntimeError("exact ownership root path drift")
    if int(shared_count_text) != len(EXPECTED_SHARED_GIT_INVENTORY):
        raise RuntimeError("shared Git ownership inventory count drift")
    if shared_digest != EXPECTED_SHARED_GIT_INVENTORY_SHA256:
        raise RuntimeError("shared Git shell/program digest mismatch")
    if canonical_shared_git_inventory_digest(EXPECTED_SHARED_GIT_INVENTORY) != shared_digest:
        raise RuntimeError("shared Git ownership inventory digest drift")
    if int(worktree_count_text) != len(EXPECTED_AGENT_WORKTREE_INVENTORY):
        raise RuntimeError("agent worktree ownership inventory count drift")
    if worktree_digest != EXPECTED_AGENT_WORKTREE_INVENTORY_SHA256:
        raise RuntimeError("agent worktree shell/program digest mismatch")
    if canonical_shared_git_inventory_digest(EXPECTED_AGENT_WORKTREE_INVENTORY) != worktree_digest:
        raise RuntimeError("agent worktree ownership inventory digest drift")
    shared_observed = capture_shared_git_repair_inventory(
        shared_root, EXPECTED_SHARED_GIT_INVENTORY, 0, 0, 1000, 1000
    )
    worktree_observed = capture_shared_git_repair_inventory(
        worktree_root, EXPECTED_AGENT_WORKTREE_INVENTORY, 0, 0, 1000, 1000
    )
    bound: list[dict[str, Any]] = []
    try:
        bound.extend(bind_shared_git_inventory_fds(
            shared_root, shared_observed, 0, 0, 1000, 1000
        ))
        bound.extend(bind_shared_git_inventory_fds(
            worktree_root, worktree_observed, 0, 0, 1000, 1000
        ))
        apply_shared_git_ownership_transaction(bound, 0, 0, 1000, 1000)
    finally:
        close_bound_shared_git_inventory(bound)
    capture_shared_git_repair_inventory(
        shared_root, EXPECTED_SHARED_GIT_INVENTORY, 0, 0, 1000, 1000
    )
    capture_shared_git_repair_inventory(
        worktree_root, EXPECTED_AGENT_WORKTREE_INVENTORY, 0, 0, 1000, 1000
    )
    print("exact two-root ownership handoff complete: 16 + 7 records")


if __name__ == "__main__":
    try:
        _main(sys.argv[1:])
    except SharedGitOwnershipInterrupted as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(exc.exit_code)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"shared Git ownership gate rejected: {exc}", file=sys.stderr)
        raise SystemExit(1)
TASK4_SHARED_GIT_OWNERSHIP_PY

expected_runtime_inventory_count=84
expected_runtime_inventory_sha256=713307aef872976278c81ef74dd7ddf635767e7e4bbb3441941db2e17b2dc368
/usr/bin/python3 -I - "$runtime" \
  "$expected_runtime_inventory_count" \
  "$expected_runtime_inventory_sha256" <<'TASK4_OWNERSHIP_BINDING_PY'
from __future__ import annotations

import sys

if __name__ == "__main__" and (
    sys.flags.isolated != 1 or sys.flags.safe_path != 1
):
    raise SystemExit("ownership gate requires isolated safe-path Python")

import hashlib
import json
import os
import signal
import stat
from pathlib import Path
from typing import Any, Callable


EXPECTED_RUNTIME_INVENTORY = (
    {"type": "d", "path": "docs"},
    {"type": "d", "path": "docs/superpowers"},
    {"type": "d", "path": "docs/superpowers/plans"},
    {"type": "d", "path": "docs/superpowers/specs"},
    {"type": "d", "path": "files/wirtelprimfgenerator@H234598/__pycache__"},
    {"type": "d", "path": "scripts/__pycache__"},
    {"type": "d", "path": "tests/__pycache__"},
    {"type": "d", "path": "tests/platform/__pycache__"},
    {"type": "f", "path": ".github/workflows/check.yml"},
    {"type": "f", "path": "Makefile"},
    {"type": "f", "path": "README.md"},
    {"type": "f", "path": "Sourcecode/README.md"},
    {"type": "f", "path": "Sourcecode/STORY_DIRECTIVES.md"},
    {"type": "f", "path": "Sourcecode/env.example"},
    {"type": "f", "path": "Sourcecode/systemd-user/wirtelprimpf.service"},
    {"type": "f", "path": "Sourcecode/wirtelprimpf_generator.py"},
    {"type": "f", "path": "docs/superpowers/plans/2026-07-31-story-directives-implementation.md"},
    {"type": "f", "path": "docs/superpowers/plans/2026-08-01-public-site-copy-and-rollout.md"},
    {"type": "f", "path": "docs/superpowers/plans/2026-08-01-transactional-settings-live-sync-status.md"},
    {"type": "f", "path": "docs/superpowers/specs/2026-07-31-story-directives-design.md"},
    {"type": "f", "path": "docs/superpowers/specs/2026-08-01-admin-live-sync-status-design.md"},
    {"type": "f", "path": "files/wirtelprimfgenerator@H234598/PROGRAMMPLAN.md"},
    {"type": "f", "path": "files/wirtelprimfgenerator@H234598/README.md"},
    {"type": "f", "path": "files/wirtelprimfgenerator@H234598/StoryDirectives.py"},
    {"type": "f", "path": "files/wirtelprimfgenerator@H234598/__pycache__/SettingsLogo.cpython-314.pyc"},
    {"type": "f", "path": "files/wirtelprimfgenerator@H234598/__pycache__/helper.cpython-314.pyc"},
    {"type": "f", "path": "files/wirtelprimfgenerator@H234598/applet.js"},
    {"type": "f", "path": "files/wirtelprimfgenerator@H234598/metadata.json"},
    {"type": "f", "path": "files/wirtelprimfgenerator@H234598/settings-schema.json"},
    {"type": "f", "path": "files/wirtelprimfgenerator@H234598/story_directives_core.py"},
    {"type": "f", "path": "scripts/__pycache__/validate_pages_artifact.cpython-314.pyc"},
    {"type": "f", "path": "scripts/install-local.sh"},
    {"type": "f", "path": "scripts/uninstall-local.sh"},
    {"type": "f", "path": "tests/__pycache__/test_git_object_fallback.cpython-314.pyc"},
    {"type": "f", "path": "tests/__pycache__/test_helper_env.cpython-314.pyc"},
    {"type": "f", "path": "tests/__pycache__/test_release_publication.cpython-314.pyc"},
    {"type": "f", "path": "tests/__pycache__/test_semver.cpython-314.pyc"},
    {"type": "f", "path": "tests/__pycache__/test_settings_schema.cpython-314.pyc"},
    {"type": "f", "path": "tests/platform/__pycache__/test_admin.cpython-314.pyc"},
    {"type": "f", "path": "tests/platform/__pycache__/test_cloudflare_credentials.cpython-314.pyc"},
    {"type": "f", "path": "tests/platform/__pycache__/test_github_provision.cpython-314.pyc"},
    {"type": "f", "path": "tests/platform/__pycache__/test_hub.cpython-314.pyc"},
    {"type": "f", "path": "tests/platform/__pycache__/test_incremental_media.cpython-314.pyc"},
    {"type": "f", "path": "tests/platform/__pycache__/test_media_release.cpython-314.pyc"},
    {"type": "f", "path": "tests/platform/__pycache__/test_naming_state.cpython-314.pyc"},
    {"type": "f", "path": "tests/platform/__pycache__/test_pages_artifact.cpython-314.pyc"},
    {"type": "f", "path": "tests/platform/__pycache__/test_provisioning.cpython-314.pyc"},
    {"type": "f", "path": "tests/platform/__pycache__/test_runtime.cpython-314.pyc"},
    {"type": "f", "path": "tests/platform/__pycache__/test_systemd_units.cpython-314.pyc"},
    {"type": "f", "path": "tests/platform/__pycache__/test_target_switch.cpython-314.pyc"},
    {"type": "f", "path": "tests/platform/test_admin.py"},
    {"type": "f", "path": "tests/platform/test_github_provision.py"},
    {"type": "f", "path": "tests/platform/test_naming_state.py"},
    {"type": "f", "path": "tests/platform/test_provisioning.py"},
    {"type": "f", "path": "tests/test_applet_runtime.js"},
    {"type": "f", "path": "tests/test_story_directives.py"},
    {"type": "f", "path": "web/fixtures/site/archive-manifest.json"},
    {"type": "f", "path": "web/fixtures/site/publication-catalog.json"},
    {"type": "f", "path": "web/src/components/ArchiveCard.astro"},
    {"type": "f", "path": "web/src/lib/content.ts"},
    {"type": "f", "path": "web/src/lib/data.ts"},
    {"type": "f", "path": "web/src/pages/geschichten/[volume].astro"},
    {"type": "f", "path": "web/src/pages/geschichten/index.astro"},
    {"type": "f", "path": "web/src/pages/index.astro"},
    {"type": "f", "path": "web/src/pages/projekt/index.astro"},
    {"type": "f", "path": "web/src/pages/projekt/status.astro"},
    {"type": "f", "path": "web/tests/content.test.ts"},
    {"type": "f", "path": "wirtelprimpf_platform/__init__.py"},
    {"type": "f", "path": "wirtelprimpf_platform/__pycache__/__init__.cpython-314.pyc"},
    {"type": "f", "path": "wirtelprimpf_platform/__pycache__/admin.cpython-314.pyc"},
    {"type": "f", "path": "wirtelprimpf_platform/__pycache__/catalog.cpython-314.pyc"},
    {"type": "f", "path": "wirtelprimpf_platform/__pycache__/cli.cpython-314.pyc"},
    {"type": "f", "path": "wirtelprimpf_platform/__pycache__/github_provision.cpython-314.pyc"},
    {"type": "f", "path": "wirtelprimpf_platform/__pycache__/hub.cpython-314.pyc"},
    {"type": "f", "path": "wirtelprimpf_platform/__pycache__/incremental_media.cpython-314.pyc"},
    {"type": "f", "path": "wirtelprimpf_platform/__pycache__/naming.cpython-314.pyc"},
    {"type": "f", "path": "wirtelprimpf_platform/__pycache__/runtime.cpython-314.pyc"},
    {"type": "f", "path": "wirtelprimpf_platform/__pycache__/state.cpython-314.pyc"},
    {"type": "f", "path": "wirtelprimpf_platform/admin.py"},
    {"type": "f", "path": "wirtelprimpf_platform/catalog.py"},
    {"type": "f", "path": "wirtelprimpf_platform/cli.py"},
    {"type": "f", "path": "wirtelprimpf_platform/github_provision.py"},
    {"type": "f", "path": "wirtelprimpf_platform/naming.py"},
    {"type": "f", "path": "wirtelprimpf_platform/state.py"},
)

EXPECTED_RUNTIME_INVENTORY_SHA256 = "713307aef872976278c81ef74dd7ddf635767e7e4bbb3441941db2e17b2dc368"


def canonical_inventory_digest(records: tuple[dict[str, Any], ...]) -> str:
    projection = sorted(
        ({"path": str(item["path"]), "type": str(item["type"])} for item in records),
        key=lambda item: os.fsencode(item["path"]),
    )
    payload = json.dumps(
        projection,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _canonical_root(root: str) -> str:
    path = Path(root)
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise RuntimeError("runtime root is not an absolute real directory")
    canonical = os.path.realpath(root)
    if canonical != root:
        raise RuntimeError("runtime root is not canonical")
    return canonical


def _relative_components(root: str, full_path: str) -> str:
    relative = os.path.relpath(full_path, root)
    if relative in ("", ".") or os.path.isabs(relative):
        raise RuntimeError("invalid relative inventory path")
    components = relative.split(os.sep)
    if any(component in ("", ".", "..") for component in components):
        raise RuntimeError("non-lexical relative inventory path")
    return relative


def _lexical_relative(root: str, full_path: str) -> str:
    relative = _relative_components(root, full_path)
    resolved = os.path.realpath(os.path.join(root, relative))
    if os.path.commonpath((root, resolved)) != root:
        raise RuntimeError("inventory path resolves outside runtime")
    return relative


def _type_code(metadata: os.stat_result) -> str:
    if stat.S_ISREG(metadata.st_mode):
        if metadata.st_nlink != 1:
            raise RuntimeError("regular runtime file does not have nlink == 1")
        return "f"
    if stat.S_ISDIR(metadata.st_mode):
        return "d"
    if stat.S_ISLNK(metadata.st_mode):
        raise RuntimeError("runtime symlink rejected")
    raise RuntimeError("runtime special file rejected")


def capture_runtime_inventory(
    root: str,
    target_uid: int,
    target_gid: int,
) -> tuple[dict[str, Any], ...]:
    canonical = _canonical_root(root)
    root_metadata = os.lstat(canonical)
    root_device = root_metadata.st_dev
    records: list[dict[str, Any]] = []
    pending = [canonical]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                metadata = entry.stat(follow_symlinks=False)
                if metadata.st_dev != root_device:
                    raise RuntimeError("unexpected runtime submount")
                if stat.S_ISLNK(metadata.st_mode):
                    if metadata.st_uid == target_uid and metadata.st_gid == target_gid:
                        continue
                    raise RuntimeError("foreign runtime symlink rejected")
                kind = _type_code(metadata)
                relative = _lexical_relative(canonical, entry.path)
                if kind == "d":
                    pending.append(entry.path)
                if metadata.st_uid != target_uid or metadata.st_gid != target_gid:
                    records.append(
                        {
                            "path": relative,
                            "type": kind,
                            "uid": metadata.st_uid,
                            "gid": metadata.st_gid,
                            "dev": metadata.st_dev,
                            "ino": metadata.st_ino,
                            "nlink": metadata.st_nlink,
                            "target_uid": target_uid,
                            "target_gid": target_gid,
                        }
                    )
    records.sort(key=lambda item: os.fsencode(str(item["path"])))
    return tuple(records)


def capture_allowlisted_runtime_inventory(
    root: str,
    expected_static: tuple[dict[str, Any], ...],
    source_uid: int,
    source_gid: int,
    target_uid: int,
    target_gid: int,
) -> tuple[dict[str, Any], ...]:
    canonical = _canonical_root(root)
    if (source_uid, source_gid) == (target_uid, target_gid):
        raise RuntimeError("source and target ownership must differ")
    expected_by_path: dict[str, str] = {}
    for item in expected_static:
        if set(item) != {"path", "type"}:
            raise RuntimeError("invalid static inventory record")
        relative = str(item["path"])
        kind = str(item["type"])
        if (
            os.path.isabs(relative)
            or any(part in ("", ".", "..") for part in relative.split(os.sep))
            or kind not in ("f", "d")
            or relative in expected_by_path
        ):
            raise RuntimeError("invalid static inventory path or type")
        expected_by_path[relative] = kind
    if not expected_by_path:
        raise RuntimeError("empty static ownership inventory rejected")

    root_metadata = os.lstat(canonical)
    root_device = root_metadata.st_dev
    allowed_owners = {(source_uid, source_gid), (target_uid, target_gid)}
    records_by_path: dict[str, dict[str, Any]] = {}
    pending = [canonical]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                metadata = entry.stat(follow_symlinks=False)
                if metadata.st_dev != root_device:
                    raise RuntimeError("unexpected runtime submount")
                if stat.S_ISLNK(metadata.st_mode):
                    relative = _relative_components(canonical, entry.path)
                    if relative in expected_by_path:
                        raise RuntimeError("allowlisted runtime symlink rejected")
                    if (metadata.st_uid, metadata.st_gid) == (target_uid, target_gid):
                        continue
                    raise RuntimeError("foreign runtime symlink rejected")
                relative = _lexical_relative(canonical, entry.path)
                kind = _type_code(metadata)
                if kind == "d":
                    pending.append(entry.path)
                if relative in expected_by_path:
                    if kind != expected_by_path[relative]:
                        raise RuntimeError("static runtime object type drift")
                    if (metadata.st_uid, metadata.st_gid) not in allowed_owners:
                        raise RuntimeError("allowlisted runtime owner drift")
                    records_by_path[relative] = {
                        "path": relative,
                        "type": kind,
                        "uid": metadata.st_uid,
                        "gid": metadata.st_gid,
                        "dev": metadata.st_dev,
                        "ino": metadata.st_ino,
                        "nlink": metadata.st_nlink,
                        "target_uid": target_uid,
                        "target_gid": target_gid,
                    }
                elif (metadata.st_uid, metadata.st_gid) != (target_uid, target_gid):
                    raise RuntimeError("unexpected foreign runtime path")
    if set(records_by_path) != set(expected_by_path):
        raise RuntimeError("static runtime inventory path drift")
    return tuple(
        records_by_path[path]
        for path in sorted(records_by_path, key=os.fsencode)
    )


def validate_expected_inventory(
    root: str,
    expected: tuple[dict[str, Any], ...],
    source_uid: int,
    source_gid: int,
) -> tuple[dict[str, Any], ...]:
    if not expected:
        raise RuntimeError("empty ownership inventory rejected")
    target_pairs = {
        (int(item["target_uid"]), int(item["target_gid"])) for item in expected
    }
    if len(target_pairs) != 1:
        raise RuntimeError("ambiguous target ownership")
    target_uid, target_gid = next(iter(target_pairs))
    allowed_owners = {(source_uid, source_gid), (target_uid, target_gid)}
    for item in expected:
        if set(item) != {
            "dev",
            "gid",
            "ino",
            "nlink",
            "path",
            "target_gid",
            "target_uid",
            "type",
            "uid",
        }:
            raise RuntimeError("invalid dynamic inventory record")
        relative = str(item["path"])
        if os.path.isabs(relative) or any(
            part in ("", ".", "..") for part in relative.split(os.sep)
        ):
            raise RuntimeError("invalid expected relative path")
        if item["type"] not in ("f", "d"):
            raise RuntimeError("invalid expected object type")
        if (int(item["uid"]), int(item["gid"])) not in allowed_owners:
            raise RuntimeError("unexpected bound ownership")
        if item["type"] == "f" and int(item["nlink"]) != 1:
            raise RuntimeError("expected regular file is multiply linked")
    static_inventory = tuple(
        {"path": str(item["path"]), "type": str(item["type"])}
        for item in expected
    )
    current = capture_allowlisted_runtime_inventory(
        root,
        static_inventory,
        source_uid,
        source_gid,
        target_uid,
        target_gid,
    )
    if current != expected:
        raise RuntimeError("runtime ownership inventory drift")
    return current


def _fd_snapshot(fd: int) -> tuple[int, int, str, int, int, int]:
    metadata = os.fstat(fd)
    kind = _type_code(metadata)
    return (
        metadata.st_dev,
        metadata.st_ino,
        kind,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
    )


def _assert_fd_identity(fd: int, record: dict[str, Any]) -> None:
    expected = (
        int(record["dev"]),
        int(record["ino"]),
        str(record["type"]),
        int(record["nlink"]),
    )
    if _fd_snapshot(fd)[:4] != expected:
        raise RuntimeError("open runtime object drift")


def _fd_owner(fd: int, record: dict[str, Any]) -> tuple[int, int]:
    snapshot = _fd_snapshot(fd)
    expected_identity = (
        int(record["dev"]),
        int(record["ino"]),
        str(record["type"]),
        int(record["nlink"]),
    )
    if snapshot[:4] != expected_identity:
        raise RuntimeError("open runtime object drift")
    return snapshot[4], snapshot[5]


def _assert_fd_binding(fd: int, record: dict[str, Any], uid: int, gid: int) -> None:
    if _fd_owner(fd, record) != (uid, gid):
        raise RuntimeError("open runtime ownership drift")


def _open_beneath(root_fd: int, relative: str, kind: str) -> int:
    parts = relative.split(os.sep)
    parent_fd = os.dup(root_fd)
    try:
        for component in parts[:-1]:
            next_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=parent_fd,
            )
            os.close(parent_fd)
            parent_fd = next_fd
        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
        if kind == "d":
            flags |= os.O_DIRECTORY
        return os.open(parts[-1], flags, dir_fd=parent_fd)
    finally:
        os.close(parent_fd)


def bind_runtime_inventory_fds(
    root: str,
    expected: tuple[dict[str, Any], ...],
    source_uid: int,
    source_gid: int,
) -> list[dict[str, Any]]:
    canonical = _canonical_root(root)
    validate_expected_inventory(canonical, expected, source_uid, source_gid)
    root_fd = os.open(
        canonical,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    bound: list[dict[str, Any]] = []
    try:
        for record in expected:
            fd = _open_beneath(root_fd, str(record["path"]), str(record["type"]))
            try:
                _assert_fd_binding(
                    fd,
                    record,
                    int(record["uid"]),
                    int(record["gid"]),
                )
            except BaseException:
                os.close(fd)
                raise
            bound.append({"fd": fd, "record": record})
        validate_expected_inventory(canonical, expected, source_uid, source_gid)
        for item in bound:
            _assert_fd_binding(
                int(item["fd"]),
                item["record"],
                int(item["record"]["uid"]),
                int(item["record"]["gid"]),
            )
        return bound
    except BaseException:
        close_bound_inventory(bound)
        raise
    finally:
        os.close(root_fd)


def close_bound_inventory(bound: list[dict[str, Any]]) -> None:
    while bound:
        item = bound.pop()
        os.close(int(item["fd"]))


OWNERSHIP_SIGNALS = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)


class OwnershipInterrupted(BaseException):
    def __init__(self, signum: int) -> None:
        super().__init__(f"ownership transaction interrupted by signal {signum}")
        self.signum = signum
        self.exit_code = 128 + signum


def rollback_runtime_ownership_transaction(
    bound: list[dict[str, Any]],
    source_uid: int,
    source_gid: int,
    target_uid: int,
    target_gid: int,
) -> None:
    rollback_errors: list[str] = []
    for item in reversed(bound):
        fd = int(item["fd"])
        record = item["record"]
        try:
            original_owner = (int(record["uid"]), int(record["gid"]))
            recorded_target = (
                int(record["target_uid"]),
                int(record["target_gid"]),
            )
            if recorded_target != (target_uid, target_gid):
                raise RuntimeError("recorded target ownership drift")
            if original_owner not in {
                (source_uid, source_gid),
                (target_uid, target_gid),
            }:
                raise RuntimeError("recorded original owner is not allowed")
            current_owner = _fd_owner(fd, record)
            if current_owner == original_owner:
                continue
            if (
                original_owner == (source_uid, source_gid)
                and current_owner == (target_uid, target_gid)
            ):
                os.fchown(fd, *original_owner)
                _assert_fd_binding(fd, record, *original_owner)
                continue
            raise RuntimeError(
                f"third ownership state {current_owner[0]}:{current_owner[1]}"
            )
        except BaseException as rollback_error:
            rollback_errors.append(
                f"{record['path']}: {type(rollback_error).__name__}: {rollback_error}"
            )
    if rollback_errors:
        raise RuntimeError(
            "rollback INCOMPLETE: " + "; ".join(rollback_errors)
        )


def _rollback_with_signals_blocked(
    bound: list[dict[str, Any]],
    source_uid: int,
    source_gid: int,
    target_uid: int,
    target_gid: int,
) -> None:
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set(OWNERSHIP_SIGNALS))
    try:
        rollback_runtime_ownership_transaction(
            bound,
            source_uid,
            source_gid,
            target_uid,
            target_gid,
        )
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


def apply_runtime_ownership_transaction(
    bound: list[dict[str, Any]],
    source_uid: int,
    source_gid: int,
    target_uid: int,
    target_gid: int,
    postcondition: Callable[[], None] | None = None,
) -> None:
    if not bound:
        raise RuntimeError("empty bound ownership inventory rejected")
    if (source_uid, source_gid) == (target_uid, target_gid):
        raise RuntimeError("source and target ownership must differ")
    pending: dict[str, int | bool | None] = {"signum": None, "committed": False}
    previous_handlers = {
        signum: signal.getsignal(signum) for signum in OWNERSHIP_SIGNALS
    }
    handlers_restored = False

    def record_signal(signum: int, _frame: Any) -> None:
        if pending["committed"] is False and pending["signum"] is None:
            pending["signum"] = signum

    def raise_if_interrupted() -> None:
        signum = pending["signum"]
        if isinstance(signum, int):
            raise OwnershipInterrupted(signum)

    for signum in OWNERSHIP_SIGNALS:
        signal.signal(signum, record_signal)
    try:
        try:
            raise_if_interrupted()
            for item in bound:
                fd = int(item["fd"])
                record = item["record"]
                original_owner = (int(record["uid"]), int(record["gid"]))
                recorded_target = (
                    int(record["target_uid"]),
                    int(record["target_gid"]),
                )
                if recorded_target != (target_uid, target_gid):
                    raise RuntimeError("recorded target ownership drift")
                if original_owner not in {
                    (source_uid, source_gid),
                    (target_uid, target_gid),
                }:
                    raise RuntimeError("recorded original owner is not allowed")
                _assert_fd_binding(fd, record, *original_owner)
                raise_if_interrupted()
                if original_owner == (target_uid, target_gid):
                    continue
                os.fchown(fd, target_uid, target_gid)
                raise_if_interrupted()
                _assert_fd_binding(fd, record, target_uid, target_gid)
            raise_if_interrupted()
            if postcondition is not None:
                postcondition()
            raise_if_interrupted()

            previous_mask = signal.pthread_sigmask(
                signal.SIG_BLOCK,
                set(OWNERSHIP_SIGNALS),
            )
            try:
                blocked_pending = sorted(
                    set(signal.sigpending()).intersection(OWNERSHIP_SIGNALS),
                    key=int,
                )
                for signum in blocked_pending:
                    signal.sigwait({signum})
                    if pending["signum"] is None:
                        pending["signum"] = int(signum)
                raise_if_interrupted()
                for signum, previous_handler in previous_handlers.items():
                    signal.signal(signum, previous_handler)
                handlers_restored = True
                pending["committed"] = True
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        except BaseException as original_error:
            if pending["committed"] is True:
                raise
            rollback_error: BaseException | None = None
            try:
                _rollback_with_signals_blocked(
                    bound,
                    source_uid,
                    source_gid,
                    target_uid,
                    target_gid,
                )
            except BaseException as caught_rollback_error:
                rollback_error = caught_rollback_error
            if rollback_error is not None:
                raise RuntimeError(
                    "ownership transaction failed; rollback INCOMPLETE: "
                    f"{type(rollback_error).__name__}: {rollback_error}"
                ) from original_error
            signum = pending["signum"]
            if isinstance(original_error, OwnershipInterrupted):
                raise original_error
            if isinstance(signum, int):
                raise OwnershipInterrupted(signum) from original_error
            raise RuntimeError(
                "ownership transaction failed; rollback complete"
            ) from original_error
    finally:
        if not handlers_restored:
            for signum, previous_handler in previous_handlers.items():
                signal.signal(signum, previous_handler)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("exact runtime/count/digest arguments required")
    root, expected_count_text, expected_digest = sys.argv[1:]
    if os.geteuid() != 0 or os.getegid() != 0:
        raise SystemExit("ownership transaction requires root")
    if root != "/home/teladi/.local/share/wirtelprimpf-generator":
        raise SystemExit("unexpected runtime root")
    if int(expected_count_text) != len(EXPECTED_RUNTIME_INVENTORY) or int(
        expected_count_text
    ) != 84:
        raise SystemExit("unexpected inventory count")
    if expected_digest != EXPECTED_RUNTIME_INVENTORY_SHA256:
        raise SystemExit("unexpected inventory digest argument")
    if canonical_inventory_digest(EXPECTED_RUNTIME_INVENTORY) != expected_digest:
        raise SystemExit("embedded inventory digest mismatch")

    current = capture_allowlisted_runtime_inventory(
        root,
        EXPECTED_RUNTIME_INVENTORY,
        0,
        0,
        1000,
        1000,
    )
    current_allowlist = tuple(
        {"type": str(item["type"]), "path": str(item["path"])} for item in current
    )
    if current_allowlist != tuple(
        sorted(EXPECTED_RUNTIME_INVENTORY, key=lambda item: os.fsencode(item["path"]))
    ):
        raise SystemExit("runtime ownership allowlist drift")

    bound = bind_runtime_inventory_fds(root, current, 0, 0)

    def assert_committed_inventory() -> None:
        committed = capture_allowlisted_runtime_inventory(
            root,
            EXPECTED_RUNTIME_INVENTORY,
            0,
            0,
            1000,
            1000,
        )
        if any(
            (int(item["uid"]), int(item["gid"])) != (1000, 1000)
            for item in committed
        ):
            raise RuntimeError("source ownership remains after transaction")

    try:
        try:
            apply_runtime_ownership_transaction(
                bound,
                0,
                0,
                1000,
                1000,
                assert_committed_inventory,
            )
        except OwnershipInterrupted as interruption:
            print(
                f"ownership transaction interrupted by signal "
                f"{interruption.signum}; rollback complete",
                file=sys.stderr,
            )
            raise SystemExit(interruption.exit_code) from interruption
    finally:
        close_bound_inventory(bound)
    print(
        f"ownership inventory committed: count={len(current)} "
        f"sha256={expected_digest}"
    )


if __name__ == "__main__":
    main()
TASK4_OWNERSHIP_BINDING_PY
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

`systemctl --user mask --runtime` alone is not an execution barrier for these
locally installed units: it writes below `~/.config/systemd/user` in the user
manager's load path, so the persistent unit wins and remains `loaded`. The
transaction therefore binds the compatibility link created by `systemctl` and
adds the effective `/run/user/1000/systemd/user.control/<unit> -> /dev/null`
link. Success always requires `daemon-reload`, `masked-runtime`, and
`LoadState=masked`. Removal validates both recorded parent/link identities,
removes the ineffective link first so the high-priority barrier survives an
interruption, and removes the effective link last. The two observed failed
attempts form one immutable evidence chain: historical `HNkEdc` plus the unique
current leaf `f1iePQ`, whose eight-file prestate, three complete manifests,
payload inventory, parent directories, and four current runtime links are all
inode/hash-bound. Only that current chain is adopted; every other mixed state is
rejected without mutation.

The failed editable install was deterministic rather than transient: the live
venv has Python 3.14.5 and Pip 26.0.1 but intentionally no `setuptools`, while
`pyproject.toml` requires `setuptools>=82`. The old
`--no-build-isolation` option therefore made `setuptools.build_meta`
unimportable in both the forward and rollback directions. The corrected
transaction performs exactly one bounded HTTPS acquisition of the immutable
`setuptools==83.0.0` wheel before the first operational mutation, validates its
filename, byte count, SHA-256, owner and mode, and writes an exact hashed build
constraint. Forward install and rollback then share one helper using normal
ephemeral build isolation in strictly offline `--no-index --find-links`
mode. An existing corrupt bundle is rejected without deletion, redownload or
blind retry.

```bash
set -Eeuo pipefail

target_sha="${GENERATOR_MERGE_SHA:?recorded Task-3 merge SHA required}"
runtime=/home/teladi/.local/share/wirtelprimpf-generator
runtime_canonical_origin=https://github.com/H234598/Wirtelprimpf-generator.git
backup_root=/home/teladi/.local/state/wirtelprimpf/deploy-backups
[[ "$target_sha" =~ ^[0-9a-f]{40}$ ]]

assert_runtime_owned() {
  test -d "$runtime" && test ! -L "$runtime"
  test "$(realpath -e -- "$runtime")" = "$runtime"
  test -z "$(find "$runtime" -xdev \( ! -user teladi -o ! -group teladi \) -print -quit)"
}
# BEGIN TASK4_RUNTIME_GIT_GUARD
assert_safe_runtime_git_config() {
  local key value
  runtime_local_config() {
    /usr/bin/env -i HOME=/home/teladi USER=teladi LOGNAME=teladi \
    PATH=/usr/local/bin:/usr/bin:/bin \
    GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
    GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/false SSH_ASKPASS=/bin/false \
    /usr/bin/git -C "$runtime" config --local --no-includes "$@"
  }
  while IFS= read -r key; do
    case "$key" in
      core.repositoryformatversion|core.filemode|core.bare|core.logallrefupdates|\
      remote.origin.url|remote.origin.fetch|remote.origin.promisor|\
      remote.origin.partialclonefilter|branch.*.remote|branch.*.merge)
        ;;
      *)
        return 1
        ;;
    esac
  done < <(runtime_local_config --name-only --get-regexp '.*')
  case "$(runtime_local_config --get-all core.repositoryformatversion)" in 0|1) ;; *) return 1 ;; esac
  case "$(runtime_local_config --get-all core.filemode)" in true|false) ;; *) return 1 ;; esac
  test "$(runtime_local_config --get-all core.bare)" = false
  test "$(runtime_local_config --get-all core.logallrefupdates)" = true
  test "$(runtime_local_config --get-all remote.origin.url)" = "$runtime_canonical_origin"
  test "$(runtime_local_config --get-all remote.origin.fetch)" = \
    '+refs/heads/main:refs/remotes/origin/main'
  value="$(runtime_local_config --get-all remote.origin.promisor || :)"
  case "$value" in ""|true) ;; *) return 1 ;; esac
  value="$(runtime_local_config --get-all remote.origin.partialclonefilter || :)"
  case "$value" in ""|blob:none) ;; *) return 1 ;; esac
  test "$(runtime_local_config --get-all branch.main.remote)" = origin
  test "$(runtime_local_config --get-all branch.main.merge)" = refs/heads/main
  while IFS= read -r key; do
    case "$key" in
      branch.*.remote)
        value="${key#branch.}"
        value="${value%.remote}"
        /usr/bin/git check-ref-format "refs/heads/$value" >/dev/null || return 1
        test "$(runtime_local_config --get-all "$key")" = origin || return 1
        ;;
      branch.*.merge)
        value="${key#branch.}"
        value="${value%.merge}"
        /usr/bin/git check-ref-format "refs/heads/$value" >/dev/null || return 1
        test "$(runtime_local_config --get-all "$key")" = "refs/heads/$value" || return 1
        ;;
    esac
  done < <(runtime_local_config --name-only --get-regexp '^branch\..*\.(remote|merge)$')
}
git_runtime() {
  local operation="${1:-}"
  case "$operation" in
    status|branch|rev-parse|merge-base|update-ref) ;;
    remote)
      [[ "$*" == "remote get-url origin" ]] || return 1
      ;;
    switch)
      if [[ "$*" == "switch main" ]]; then
        :
      elif [[ "${2:-}" == --detach && "${3:-}" =~ ^[0-9a-f]{40}$ && $# == 3 ]]; then
        :
      else
        return 1
      fi
      ;;
    *) return 1 ;;
  esac
  assert_runtime_owned
  assert_safe_runtime_git_config
  /usr/bin/env -i HOME=/home/teladi USER=teladi LOGNAME=teladi \
    PATH=/usr/local/bin:/usr/bin:/bin \
    GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
    GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/false SSH_ASKPASS=/bin/false \
    /usr/bin/git -c http.extraHeader= \
      -c "http.$runtime_canonical_origin.extraHeader=" -c http.proxy= \
      -c http.sslVerify=true -c http.curloptResolve= -c credential.helper= \
      -c core.askPass=/bin/false -c core.hooksPath=/dev/null \
      -c core.fsmonitor=false -c core.sshCommand=/bin/false \
      -c core.gitProxy=/bin/false -c protocol.allow=never \
      -c protocol.https.allow=always -c protocol.ext.allow=never \
      -C "$runtime" "$@"
}
git_runtime_fetch_bounded() {
  assert_runtime_owned
  assert_safe_runtime_git_config
  test "$(git_runtime remote get-url origin)" = "$runtime_canonical_origin"
  timeout --foreground --signal=TERM --kill-after=10s 180s \
    /usr/bin/env -i HOME=/home/teladi USER=teladi LOGNAME=teladi \
      PATH=/usr/local/bin:/usr/bin:/bin \
      GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
      GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/false SSH_ASKPASS=/bin/false \
      /usr/bin/git -c http.extraHeader= \
        -c "http.$runtime_canonical_origin.extraHeader=" -c http.proxy= \
        -c http.sslVerify=true -c http.curloptResolve= -c credential.helper= \
        -c core.askPass=/bin/false -c core.hooksPath=/dev/null \
        -c core.fsmonitor=false -c core.sshCommand=/bin/false \
        -c core.gitProxy=/bin/false -c protocol.allow=never \
        -c protocol.https.allow=always -c protocol.ext.allow=never \
        -c http.lowSpeedLimit=1024 -c http.lowSpeedTime=30 \
        -C "$runtime" fetch "$runtime_canonical_origin" \
        refs/heads/main:refs/remotes/origin/main
}
# END TASK4_RUNTIME_GIT_GUARD

# BEGIN TASK4_BACKUP_ROOT_PREFLIGHT
assert_private_backup_root() {
  local candidate="$1" expected="$2" expected_uid="$3" expected_gid="$4"
  local expected_dev="$5" expected_ino="$6"
  local metadata
  test "$candidate" = "$expected"
  test -d "$candidate" && test ! -L "$candidate"
  test "$(realpath -e -- "$candidate")" = "$expected"
  metadata="$(stat -Lc '%u:%g:%a:%d:%i' -- "$candidate")"
  test "$metadata" = \
    "$expected_uid:$expected_gid:700:$expected_dev:$expected_ino"
}
# END TASK4_BACKUP_ROOT_PREFLIGHT

# BEGIN TASK4_BUILD_BACKEND_BUNDLE
backend_wheel_name=setuptools-83.0.0-py3-none-any.whl
backend_wheel_size=1008090
backend_wheel_sha256=29b23c360f22f414dc7336bb39178cc7bcbf6021ed2733cde173f09dba19abb3
backend_wheel_url=https://files.pythonhosted.org/packages/5d/40/e1e72872c6354b306daef1703549e8e83b4d43cfea356311bf722a043752/setuptools-83.0.0-py3-none-any.whl
backend_constraint_value='setuptools==83.0.0'
backend_constraint_sha256=4723b97f4d3f3c1d817e4896c0f7d59642e326ad891c7037482d2455b8a6bb4c

validate_exact_build_backend_file() {
  local candidate="$1" expected_size="$2" expected_sha256="$3"
  local metadata actual_sha256
  [[ "$expected_size" =~ ^[1-9][0-9]*$ ]]
  [[ "$expected_sha256" =~ ^[0-9a-f]{64}$ ]]
  test -f "$candidate" && test ! -L "$candidate"
  test "$(realpath -e -- "$candidate")" = "$candidate"
  metadata="$(stat -Lc '%u:%g:%a:%h:%s' -- "$candidate")"
  test "$metadata" = \
    "$(id -u):$(id -g):600:1:$expected_size"
  actual_sha256="$(sha256sum -- "$candidate")"
  test "$actual_sha256" = "$expected_sha256  $candidate"
}

download_exact_build_backend() {
  local source_url="$1" destination="$2" expected_size="$3"
  local expected_sha256="$4" parent temporary curl_path
  [[ "$source_url" == https://* ]]
  parent="$(dirname -- "$destination")"
  test -d "$parent" && test ! -L "$parent"
  test "$(realpath -e -- "$parent")" = "$parent"
  test "$(stat -Lc '%u:%g:%a' -- "$parent")" = \
    "$(id -u):$(id -g):700"
  if [[ -e "$destination" || -L "$destination" ]]; then
    validate_exact_build_backend_file \
      "$destination" "$expected_size" "$expected_sha256"
    return
  fi
  curl_path="$(command -v curl)"
  test -x "$curl_path"
  temporary="$(mktemp "$parent/.backend-wheel.XXXXXX")"
  chmod 0600 "$temporary"
  if ! timeout --foreground --signal=TERM --kill-after=5s 150s \
    "$curl_path" --fail --location --silent --show-error \
      --proto '=https' --tlsv1.2 --connect-timeout 15 --max-time 120 \
      --retry 0 --output "$temporary" "$source_url"; then
    rm -f -- "$temporary"
    return 1
  fi
  if ! validate_exact_build_backend_file \
    "$temporary" "$expected_size" "$expected_sha256"; then
    rm -f -- "$temporary"
    return 1
  fi
  if ! ln -- "$temporary" "$destination"; then
    rm -f -- "$temporary"
    validate_exact_build_backend_file \
      "$destination" "$expected_size" "$expected_sha256"
    return
  fi
  rm -f -- "$temporary"
  validate_exact_build_backend_file \
    "$destination" "$expected_size" "$expected_sha256"
}

install_editable_offline_bounded() {
  local checkout="$1" wheelhouse="$2" wheel="$3" expected_size="$4"
  local expected_sha256="$5" constraint="$6" constraint_sha256="$7"
  test "$checkout" = "$runtime"
  test -d "$checkout" && test ! -L "$checkout"
  test "$(realpath -e -- "$checkout")" = "$checkout"
  test -d "$wheelhouse" && test ! -L "$wheelhouse"
  test "$(realpath -e -- "$wheelhouse")" = "$wheelhouse"
  validate_exact_build_backend_file \
    "$wheel" "$expected_size" "$expected_sha256"
  validate_exact_build_backend_file \
    "$constraint" "$(printf '%s\n' "$backend_constraint_value" | wc -c)" \
    "$constraint_sha256"
  : "${PIP_CACHE_DIR:?private deployment pip cache required}"
  : "${TMPDIR:?private deployment temporary directory required}"
  install -d -m0700 "$PIP_CACHE_DIR" "$TMPDIR"
  PIP_CONFIG_FILE=/dev/null \
  PIP_NO_INDEX=1 \
  PIP_FIND_LINKS="$wheelhouse" \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  PIP_NO_INPUT=1 \
  PIP_REQUIRE_VIRTUALENV=1 \
  PIP_CACHE_DIR="$PIP_CACHE_DIR" \
  TMPDIR="$TMPDIR" \
  PYTHONNOUSERSITE=1 \
    timeout --foreground --signal=TERM --kill-after=10s 300s \
      "$checkout/.venv/bin/python" -m pip install \
      --disable-pip-version-check --no-index --find-links "$wheelhouse" \
      --build-constraint "$constraint" --no-deps -e "$checkout"
}

provision_build_backend_bundle() {
  local constraint_temporary
  test -n "${backend_wheelhouse:-}"
  test -n "${backend_wheel:-}"
  test -n "${backend_constraint:-}"
  install -d -m0700 "$backend_wheelhouse"
  test "$(stat -Lc '%u:%g:%a' -- "$backend_wheelhouse")" = \
    "$(id -u):$(id -g):700"
  download_exact_build_backend \
    "$backend_wheel_url" "$backend_wheel" \
    "$backend_wheel_size" "$backend_wheel_sha256"
  if [[ -e "$backend_constraint" || -L "$backend_constraint" ]]; then
    validate_exact_build_backend_file \
      "$backend_constraint" \
      "$(printf '%s\n' "$backend_constraint_value" | wc -c)" \
      "$backend_constraint_sha256"
    return
  fi
  constraint_temporary="$(mktemp "$backend_wheelhouse/.constraint.XXXXXX")"
  chmod 0600 "$constraint_temporary"
  printf '%s\n' "$backend_constraint_value" >"$constraint_temporary"
  validate_exact_build_backend_file \
    "$constraint_temporary" \
    "$(printf '%s\n' "$backend_constraint_value" | wc -c)" \
    "$backend_constraint_sha256"
  if ! ln -- "$constraint_temporary" "$backend_constraint"; then
    rm -f -- "$constraint_temporary"
    validate_exact_build_backend_file \
      "$backend_constraint" \
      "$(printf '%s\n' "$backend_constraint_value" | wc -c)" \
      "$backend_constraint_sha256"
    return
  fi
  rm -f -- "$constraint_temporary"
  validate_exact_build_backend_file \
    "$backend_constraint" \
    "$(printf '%s\n' "$backend_constraint_value" | wc -c)" \
    "$backend_constraint_sha256"
}
# END TASK4_BUILD_BACKEND_BUNDLE

runtime_control_dir=/run/user/1000/systemd/user.control
runtime_legacy_dir=/run/user/1000/systemd/user
runtime_barrier_python() {
  /usr/bin/python3 -I -S - "$@" <<'TASK4_RUNTIME_BARRIER_PY'
import json
import hashlib
import os
import re
import stat
import sys


ALLOWED_UNITS = frozenset(("wirtelprimpf.service", "wirtelprimpf.timer"))
INTERRUPTED_ATTEMPT_CHAIN = (
    {
        "name": "HNkEdc",
        "current": False,
        "path": "/home/teladi/.local/state/wirtelprimpf/deploy-backups/20260801-admin-live.HNkEdc",
        "dev": 53,
        "ino": 8250927,
        "files": {
            "runtime-sha-before": {"dev": 53, "ino": 8250928, "sha256": "c884bec764a03e4c876acf6beaee32b17ad55b863c11b22b5d80724f51392873"},
            "runtime-branch-before": {"dev": 53, "ino": 8250929, "sha256": "6403203dd5a0867eb14d104ee8a73730bd72dd9ad92e78d996a6dba0a5dcfc01"},
            "target-sha": {"dev": 53, "ino": 8250930, "sha256": "784140f1bd8201950fe8f91ba37775371cc87530643efe6fb3d814203ca81aa2"},
            "timer-enabled-before": {"dev": 53, "ino": 8250931, "sha256": "e056a35db086947e2f5969d747f0a7517bff00c7ffff1f9e7b47b72bfac9d948"},
            "timer-active-before": {"dev": 53, "ino": 8250932, "sha256": "45df5ad5e0ecfa54d3226343e0e6857337494ba6e32f189d1174070665d8c659"},
            "admin-active-before": {"dev": 53, "ino": 8250933, "sha256": "45df5ad5e0ecfa54d3226343e0e6857337494ba6e32f189d1174070665d8c659"},
            "service-unit-state-before": {"dev": 53, "ino": 8250934, "sha256": "652cabf0de6cd70f66f72b17d6409203b84909be9864261feb614943f2e6cc62"},
            "service-load-state-before": {"dev": 53, "ino": 8250935, "sha256": "25dbd4fa5b9f0710b9f27009c1e38969b8cbb2806502388beae5063d460a85f5"},
        },
    },
    {
        "name": "f1iePQ",
        "current": True,
        "path": "/home/teladi/.local/state/wirtelprimpf/deploy-backups/20260801-admin-live.f1iePQ",
        "dev": 53,
        "ino": 8256518,
        "files": {
            "runtime-sha-before": {"dev": 53, "ino": 8256519, "sha256": "c884bec764a03e4c876acf6beaee32b17ad55b863c11b22b5d80724f51392873"},
            "runtime-branch-before": {"dev": 53, "ino": 8256520, "sha256": "6403203dd5a0867eb14d104ee8a73730bd72dd9ad92e78d996a6dba0a5dcfc01"},
            "target-sha": {"dev": 53, "ino": 8256521, "sha256": "784140f1bd8201950fe8f91ba37775371cc87530643efe6fb3d814203ca81aa2"},
            "timer-enabled-before": {"dev": 53, "ino": 8256522, "sha256": "e056a35db086947e2f5969d747f0a7517bff00c7ffff1f9e7b47b72bfac9d948"},
            "timer-active-before": {"dev": 53, "ino": 8256523, "sha256": "45df5ad5e0ecfa54d3226343e0e6857337494ba6e32f189d1174070665d8c659"},
            "admin-active-before": {"dev": 53, "ino": 8256524, "sha256": "45df5ad5e0ecfa54d3226343e0e6857337494ba6e32f189d1174070665d8c659"},
            "service-unit-state-before": {"dev": 53, "ino": 8256525, "sha256": "652cabf0de6cd70f66f72b17d6409203b84909be9864261feb614943f2e6cc62"},
            "service-load-state-before": {"dev": 53, "ino": 8256526, "sha256": "25dbd4fa5b9f0710b9f27009c1e38969b8cbb2806502388beae5063d460a85f5"},
        },
        "evidence_files": {
            "config-manifest.tsv": {"dev": 53, "ino": 8256539, "size": 610, "sha256": "76aaf7d6461ae8460b62c6abdec2976fe0c3cc7920c7159e7ef705fdee2cdbd3"},
            "install-manifest.tsv": {"dev": 53, "ino": 8256540, "size": 959, "sha256": "806f2a93095233058b2e787abde9f1a9196c5292db412f66fbc1f44c5336c486"},
            "directory-modes-before.tsv": {"dev": 53, "ino": 8256541, "size": 133, "sha256": "9eb4d6d28e9058ff0297965dee2f2d1eaa5649fb849549a1bbd2deb71c416c89"},
        },
        "payload_directory": {
            "path": "files",
            "dev": 53,
            "ino": 8256538,
            "mode": 0o700,
            "entries": {
                "001": {"type": "f", "dev": 53, "ino": 8256542, "mode": 0o600, "nlink": 1, "size": 2080},
                "002": {"type": "f", "dev": 53, "ino": 8256543, "mode": 0o600, "nlink": 1, "size": 75},
                "003": {"type": "f", "dev": 53, "ino": 8256544, "mode": 0o644, "nlink": 1, "size": 128},
                "005": {"type": "d", "dev": 53, "ino": 8256545, "mode": 0o755, "nlink": 1, "size": 326},
                "007": {"type": "f", "dev": 53, "ino": 8256571, "mode": 0o755, "nlink": 1, "size": 24639},
                "008": {"type": "f", "dev": 53, "ino": 8256572, "mode": 0o644, "nlink": 1, "size": 1047},
                "009": {"type": "f", "dev": 53, "ino": 8256573, "mode": 0o644, "nlink": 1, "size": 187},
                "010": {"type": "f", "dev": 53, "ino": 8256574, "mode": 0o644, "nlink": 1, "size": 968},
            },
        },
    },
)
CURRENT_INTERRUPTED_ATTEMPT = "f1iePQ"
INTERRUPTED_BARRIER_HISTORY = {
    "HNkEdc": {
        "parents": {
            "control": {"dev": 84, "ino": 48464},
            "legacy": {"dev": 84, "ino": 47827},
        },
        "links": {
            "control": {
                "wirtelprimpf.service": {"dev": 84, "ino": 48465},
                "wirtelprimpf.timer": {"dev": 84, "ino": 48466},
            },
            "legacy": {
                "wirtelprimpf.service": {"dev": 84, "ino": 47828},
                "wirtelprimpf.timer": {"dev": 84, "ino": 48126},
            },
        },
    },
    "f1iePQ": {
        "parents": {
            "control": {"dev": 84, "ino": 48464},
            "legacy": {"dev": 84, "ino": 47827},
        },
        "links": {
            "control": {
                "wirtelprimpf.service": {"dev": 84, "ino": 48465},
                "wirtelprimpf.timer": {"dev": 84, "ino": 49929},
            },
            "legacy": {
                "wirtelprimpf.service": {"dev": 84, "ino": 47828},
                "wirtelprimpf.timer": {"dev": 84, "ino": 49854},
            },
        },
    },
}


def _require_unit(unit):
    if unit not in ALLOWED_UNITS:
        raise RuntimeError("runtime barrier unit outside the exact allowlist")


def _open_directory(path, uid, gid, mode):
    if not os.path.isabs(path) or os.path.realpath(path) != path:
        raise RuntimeError("runtime barrier directory is not canonical")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        current = os.fstat(fd)
        if not stat.S_ISDIR(current.st_mode):
            raise RuntimeError("runtime barrier parent is not a directory")
        if (current.st_uid, current.st_gid) != (uid, gid):
            raise RuntimeError("runtime barrier parent ownership drift")
        if stat.S_IMODE(current.st_mode) != mode:
            raise RuntimeError("runtime barrier parent mode drift")
        return fd, {
            "dev": current.st_dev,
            "ino": current.st_ino,
            "uid": current.st_uid,
            "gid": current.st_gid,
            "mode": stat.S_IMODE(current.st_mode),
        }
    except BaseException:
        os.close(fd)
        raise


def _capture_at(directory_fd, parent, unit, uid, gid):
    current = os.stat(unit, dir_fd=directory_fd, follow_symlinks=False)
    if not stat.S_ISLNK(current.st_mode):
        raise RuntimeError("runtime barrier entry is not a symlink")
    if (current.st_uid, current.st_gid) != (uid, gid):
        raise RuntimeError("runtime barrier entry ownership drift")
    if current.st_nlink != 1:
        raise RuntimeError("runtime barrier entry link-count drift")
    target = os.readlink(unit, dir_fd=directory_fd)
    if target != "/dev/null":
        raise RuntimeError("runtime barrier target drift")
    return {
        "dev": current.st_dev,
        "ino": current.st_ino,
        "uid": current.st_uid,
        "gid": current.st_gid,
        "mode": stat.S_IMODE(current.st_mode),
        "nlink": current.st_nlink,
        "target": target,
        "parent": parent,
    }


def _open_or_create_control_directory(path, uid, gid):
    if not os.path.isabs(path) or os.path.normpath(path) != path:
        raise RuntimeError("runtime control directory path is not canonical")
    if os.path.basename(path) != "user.control":
        raise RuntimeError("runtime control directory basename drift")
    parent_path = os.path.dirname(path)
    parent_fd, parent = _open_directory(parent_path, uid, gid, 0o755)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    created = False
    try:
        try:
            control_fd = os.open("user.control", flags, dir_fd=parent_fd)
        except FileNotFoundError:
            if (os.geteuid(), os.getegid()) != (uid, gid):
                raise RuntimeError(
                    "runtime control directory creator identity drift"
                )
            try:
                os.mkdir("user.control", 0o700, dir_fd=parent_fd)
                created = True
            except FileExistsError:
                pass
            control_fd = os.open("user.control", flags, dir_fd=parent_fd)
        current_parent = os.fstat(parent_fd)
        if (current_parent.st_dev, current_parent.st_ino) != (
            parent["dev"], parent["ino"]
        ):
            os.close(control_fd)
            raise RuntimeError("runtime systemd parent identity drift")
        current = os.fstat(control_fd)
        if not stat.S_ISDIR(current.st_mode):
            os.close(control_fd)
            raise RuntimeError("runtime control path is not a directory")
        if (current.st_uid, current.st_gid) != (uid, gid):
            os.close(control_fd)
            raise RuntimeError("runtime control directory ownership drift")
        if stat.S_IMODE(current.st_mode) != 0o700:
            os.close(control_fd)
            raise RuntimeError("runtime control directory mode drift")
        if current.st_dev != parent["dev"]:
            os.close(control_fd)
            raise RuntimeError("runtime control directory filesystem drift")
        if created:
            os.fsync(parent_fd)
        return control_fd, {
            "dev": current.st_dev,
            "ino": current.st_ino,
            "uid": current.st_uid,
            "gid": current.st_gid,
            "mode": stat.S_IMODE(current.st_mode),
        }
    finally:
        os.close(parent_fd)


def capture_runtime_barrier(directory, unit, uid, gid):
    _require_unit(unit)
    expected_mode = 0o700 if directory.endswith("/user.control") else 0o755
    directory_fd, parent = _open_directory(directory, uid, gid, expected_mode)
    try:
        return _capture_at(directory_fd, parent, unit, uid, gid)
    finally:
        os.close(directory_fd)


def capture_runtime_barrier_pair(control_dir, legacy_dir, unit, uid, gid):
    return {
        "control": capture_runtime_barrier(control_dir, unit, uid, gid),
        "legacy": capture_runtime_barrier(legacy_dir, unit, uid, gid),
    }


def _read_bound_regular(directory_fd, name, expected, uid, gid):
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    file_fd = os.open(name, flags, dir_fd=directory_fd)
    try:
        current = os.fstat(file_fd)
        if not stat.S_ISREG(current.st_mode):
            raise RuntimeError("interrupted prestate member is not regular")
        if (current.st_uid, current.st_gid) != (uid, gid):
            raise RuntimeError("interrupted prestate member ownership drift")
        if stat.S_IMODE(current.st_mode) != 0o600 or current.st_nlink != 1:
            raise RuntimeError("interrupted prestate member metadata drift")
        if (current.st_dev, current.st_ino) != (
            expected["dev"], expected["ino"]
        ):
            raise RuntimeError("interrupted prestate member identity drift")
        payload = b""
        while True:
            chunk = os.read(file_fd, 256)
            if not chunk:
                break
            payload += chunk
            if len(payload) > 256:
                raise RuntimeError("interrupted prestate member is oversized")
        if hashlib.sha256(payload).hexdigest() != expected["sha256"]:
            raise RuntimeError("interrupted prestate member digest drift")
        try:
            decoded = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError("interrupted prestate member encoding drift") from exc
        if not decoded.endswith("\n") or "\n" in decoded[:-1]:
            raise RuntimeError("interrupted prestate member line-shape drift")
        return decoded[:-1]
    finally:
        os.close(file_fd)


def _validate_hash_bound_evidence_file(directory_fd, name, expected, uid, gid):
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    file_fd = os.open(name, flags, dir_fd=directory_fd)
    try:
        current = os.fstat(file_fd)
        if not stat.S_ISREG(current.st_mode):
            raise RuntimeError("interrupted evidence member is not regular")
        if (current.st_uid, current.st_gid) != (uid, gid):
            raise RuntimeError("interrupted evidence member ownership drift")
        if stat.S_IMODE(current.st_mode) != 0o600 or current.st_nlink != 1:
            raise RuntimeError("interrupted evidence member metadata drift")
        if (current.st_dev, current.st_ino, current.st_size) != (
            expected["dev"], expected["ino"], expected["size"]
        ):
            raise RuntimeError("interrupted evidence member identity drift")
        digest = hashlib.sha256()
        while True:
            chunk = os.read(file_fd, 65536)
            if not chunk:
                break
            digest.update(chunk)
        if digest.hexdigest() != expected["sha256"]:
            raise RuntimeError("interrupted evidence member digest drift")
    finally:
        os.close(file_fd)


def _validate_payload_directory(directory_fd, expected, uid, gid):
    if not isinstance(expected, dict) or expected.get("path") != "files":
        raise RuntimeError("invalid interrupted payload directory record")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    payload_fd = os.open("files", flags, dir_fd=directory_fd)
    try:
        current = os.fstat(payload_fd)
        if not stat.S_ISDIR(current.st_mode):
            raise RuntimeError("interrupted payload root is not a directory")
        if (current.st_uid, current.st_gid) != (uid, gid):
            raise RuntimeError("interrupted payload root ownership drift")
        if (
            current.st_dev != expected.get("dev")
            or current.st_ino != expected.get("ino")
            or stat.S_IMODE(current.st_mode) != expected.get("mode")
        ):
            raise RuntimeError("interrupted payload root identity drift")
        entries = expected.get("entries")
        if not isinstance(entries, dict) or set(os.listdir(payload_fd)) != set(entries):
            raise RuntimeError("interrupted payload inventory drift")
        for name, record in entries.items():
            if not isinstance(name, str) or not re.fullmatch(r"[0-9]{3}", name):
                raise RuntimeError("invalid interrupted payload name")
            metadata = os.stat(name, dir_fd=payload_fd, follow_symlinks=False)
            if stat.S_ISREG(metadata.st_mode):
                kind = "f"
            elif stat.S_ISDIR(metadata.st_mode):
                kind = "d"
            else:
                raise RuntimeError("interrupted payload type drift")
            if (
                kind != record.get("type")
                or metadata.st_dev != record.get("dev")
                or metadata.st_ino != record.get("ino")
                or (metadata.st_uid, metadata.st_gid) != (uid, gid)
                or stat.S_IMODE(metadata.st_mode) != record.get("mode")
                or metadata.st_nlink != record.get("nlink")
                or metadata.st_size != record.get("size")
            ):
                raise RuntimeError("interrupted payload member drift")
    finally:
        os.close(payload_fd)


def validate_interrupted_prestate(path, expected, uid, gid):
    if path != expected.get("path"):
        raise RuntimeError("interrupted prestate path drift")
    directory_fd, parent = _open_directory(path, uid, gid, 0o700)
    try:
        if (parent["dev"], parent["ino"]) != (
            expected.get("dev"), expected.get("ino")
        ):
            raise RuntimeError("interrupted prestate directory identity drift")
        expected_files = expected.get("files")
        if not isinstance(expected_files, dict):
            raise RuntimeError("invalid interrupted prestate inventory")
        evidence_files = expected.get("evidence_files", {})
        if not isinstance(evidence_files, dict):
            raise RuntimeError("invalid interrupted evidence inventory")
        payload_directory = expected.get("payload_directory")
        expected_names = set(expected_files) | set(evidence_files)
        if payload_directory is not None:
            expected_names.add("files")
        if set(os.listdir(directory_fd)) != expected_names:
            raise RuntimeError("interrupted prestate inventory drift")
        values = {
            name: _read_bound_regular(
                directory_fd, name, record, uid, gid
            )
            for name, record in expected_files.items()
        }
        for name, record in evidence_files.items():
            _validate_hash_bound_evidence_file(
                directory_fd, name, record, uid, gid
            )
        if payload_directory is not None:
            _validate_payload_directory(
                directory_fd, payload_directory, uid, gid
            )
    finally:
        os.close(directory_fd)
    if not re.fullmatch(r"[0-9a-f]{40}", values["runtime-sha-before"]):
        raise RuntimeError("invalid interrupted runtime SHA")
    if values["runtime-branch-before"] != "main":
        raise RuntimeError("invalid interrupted runtime branch")
    if not re.fullmatch(r"[0-9a-f]{40}", values["target-sha"]):
        raise RuntimeError("invalid interrupted target SHA")
    if values["timer-enabled-before"] not in {
        "enabled", "enabled-runtime", "disabled"
    }:
        raise RuntimeError("invalid interrupted timer enablement")
    if values["timer-active-before"] not in {"active", "inactive"}:
        raise RuntimeError("invalid interrupted timer activity")
    if values["admin-active-before"] not in {"active", "inactive"}:
        raise RuntimeError("invalid interrupted admin activity")
    if values["service-unit-state-before"] != "static":
        raise RuntimeError("invalid interrupted service unit state")
    if values["service-load-state-before"] != "loaded":
        raise RuntimeError("invalid interrupted service load state")
    return values


def validate_interrupted_attempt_chain(expected_chain, uid, gid):
    if not isinstance(expected_chain, tuple) or not expected_chain:
        raise RuntimeError("invalid interrupted attempt chain")
    names = [record.get("name") for record in expected_chain]
    if (
        any(not isinstance(name, str) or not name for name in names)
        or len(names) != len(set(names))
    ):
        raise RuntimeError("invalid interrupted attempt identity")
    current = [record for record in expected_chain if record.get("current") is True]
    if len(current) != 1 or current[0] is not expected_chain[-1]:
        raise RuntimeError("interrupted chain has no unique current leaf")
    observed = [
        validate_interrupted_prestate(record["path"], record, uid, gid)
        for record in expected_chain
    ]
    if any(values != observed[-1] for values in observed[:-1]):
        raise RuntimeError("interrupted prestate lineage drift")
    return observed[-1]


def adopt_exact_interrupted_barriers(control_dir, legacy_dir, uid, gid):
    expected_history = INTERRUPTED_BARRIER_HISTORY.get(
        CURRENT_INTERRUPTED_ATTEMPT
    )
    if not isinstance(expected_history, dict):
        raise RuntimeError("missing current interrupted barrier history")
    expected_parents = expected_history.get("parents")
    expected_links = expected_history.get("links")
    bindings = {
        unit: capture_runtime_barrier_pair(
            control_dir, legacy_dir, unit, uid, gid
        )
        for unit in sorted(ALLOWED_UNITS)
    }
    for side, directory in (("control", control_dir), ("legacy", legacy_dir)):
        parent = bindings["wirtelprimpf.service"][side]["parent"]
        expected_parent = expected_parents[side]
        if (parent["dev"], parent["ino"]) != (
            expected_parent["dev"], expected_parent["ino"]
        ):
            raise RuntimeError("interrupted runtime barrier parent drift")
        for unit in ALLOWED_UNITS:
            current = bindings[unit][side]
            expected = expected_links[side][unit]
            if (current["dev"], current["ino"]) != (
                expected["dev"], expected["ino"]
            ):
                raise RuntimeError("interrupted runtime barrier identity drift")
    return {
        "service": bindings["wirtelprimpf.service"],
        "timer": bindings["wirtelprimpf.timer"],
    }


def _same_record(left, right):
    return left == right


def ensure_runtime_barrier(control_dir, legacy_dir, unit, uid, gid):
    _require_unit(unit)
    control_fd, control_parent = _open_or_create_control_directory(
        control_dir, uid, gid
    )
    legacy_fd, legacy_parent = _open_directory(legacy_dir, uid, gid, 0o755)
    try:
        try:
            legacy_before = _capture_at(
                legacy_fd, legacy_parent, unit, uid, gid
            )
        except FileNotFoundError:
            try:
                os.symlink("/dev/null", unit, dir_fd=legacy_fd)
            except FileExistsError:
                pass
            legacy_before = _capture_at(
                legacy_fd, legacy_parent, unit, uid, gid
            )
        try:
            control_before = _capture_at(
                control_fd, control_parent, unit, uid, gid
            )
        except FileNotFoundError:
            try:
                os.symlink("/dev/null", unit, dir_fd=control_fd)
            except FileExistsError:
                pass
            control_before = _capture_at(
                control_fd, control_parent, unit, uid, gid
            )
        legacy_after = _capture_at(legacy_fd, legacy_parent, unit, uid, gid)
        if not _same_record(legacy_before, legacy_after):
            raise RuntimeError("legacy runtime barrier changed during adoption")
        return {"control": control_before, "legacy": legacy_after}
    finally:
        os.close(legacy_fd)
        os.close(control_fd)


def _validate_binding(binding):
    if not isinstance(binding, dict) or set(binding) != {"control", "legacy"}:
        raise RuntimeError("invalid runtime barrier binding")
    for key in ("control", "legacy"):
        record = binding[key]
        if not isinstance(record, dict):
            raise RuntimeError("invalid runtime barrier record")
        if set(record) != {
            "dev", "ino", "uid", "gid", "mode", "nlink", "target", "parent"
        }:
            raise RuntimeError("invalid runtime barrier record fields")


def reconcile_runtime_barrier_binding(previous, candidate):
    _validate_binding(previous)
    _validate_binding(candidate)
    if previous == candidate:
        return candidate
    # A failed exact removal deliberately removes legacy first while the
    # effective control inode stays in place. A fail-closed retry may recreate
    # and rebind only that ineffective compatibility link; control drift is
    # never adopted.
    if previous["control"] != candidate["control"]:
        raise RuntimeError("effective runtime barrier identity drift")
    return candidate


def remove_runtime_barrier(control_dir, legacy_dir, unit, binding, uid, gid):
    _require_unit(unit)
    _validate_binding(binding)
    control_fd, control_parent = _open_directory(control_dir, uid, gid, 0o700)
    legacy_fd, legacy_parent = _open_directory(legacy_dir, uid, gid, 0o755)
    try:
        control_now = _capture_at(control_fd, control_parent, unit, uid, gid)
        legacy_now = _capture_at(legacy_fd, legacy_parent, unit, uid, gid)
        if not _same_record(control_now, binding["control"]):
            raise RuntimeError("high-priority runtime barrier replacement detected")
        if not _same_record(legacy_now, binding["legacy"]):
            raise RuntimeError("legacy runtime barrier replacement detected")
        # Remove the ineffective low-priority compatibility link first. If this
        # process dies here, user.control remains the effective fail-closed gate.
        os.unlink(unit, dir_fd=legacy_fd)
        control_now = _capture_at(control_fd, control_parent, unit, uid, gid)
        if not _same_record(control_now, binding["control"]):
            raise RuntimeError("high-priority runtime barrier changed during removal")
        os.unlink(unit, dir_fd=control_fd)
    finally:
        os.close(legacy_fd)
        os.close(control_fd)


def _main(argv):
    if not sys.flags.isolated or not sys.flags.no_site or not sys.flags.safe_path:
        raise RuntimeError("runtime barrier requires isolated safe-path Python")
    if len(argv) == 3 and argv[0] == "recover-interrupted":
        action, uid_text, gid_text = argv
        del action
        current = [
            record for record in INTERRUPTED_ATTEMPT_CHAIN
            if record.get("current") is True
        ]
        if (
            len(current) != 1
            or current[0].get("name") != CURRENT_INTERRUPTED_ATTEMPT
        ):
            raise RuntimeError("static interrupted chain current leaf drift")
        if set(INTERRUPTED_BARRIER_HISTORY) != {
            record.get("name") for record in INTERRUPTED_ATTEMPT_CHAIN
        }:
            raise RuntimeError("interrupted evidence/barrier history drift")
        values = validate_interrupted_attempt_chain(
            INTERRUPTED_ATTEMPT_CHAIN, int(uid_text), int(gid_text)
        )
        print(json.dumps(values, sort_keys=True, separators=(",", ":")))
        return
    if len(argv) == 5 and argv[0] == "adopt-interrupted":
        action, control_dir, legacy_dir, uid_text, gid_text = argv
        del action
        bindings = adopt_exact_interrupted_barriers(
            control_dir, legacy_dir, int(uid_text), int(gid_text)
        )
        print(json.dumps(bindings, sort_keys=True, separators=(",", ":")))
        return
    if len(argv) == 3 and argv[0] == "reconcile":
        binding = reconcile_runtime_barrier_binding(
            json.loads(argv[1]), json.loads(argv[2])
        )
        print(json.dumps(binding, sort_keys=True, separators=(",", ":")))
        return
    if len(argv) not in (6, 7):
        raise RuntimeError("invalid runtime barrier command")
    action, control_dir, legacy_dir, unit, uid_text, gid_text, *rest = argv
    uid = int(uid_text)
    gid = int(gid_text)
    if action == "ensure" and not rest:
        binding = ensure_runtime_barrier(
            control_dir, legacy_dir, unit, uid, gid
        )
        print(json.dumps(binding, sort_keys=True, separators=(",", ":")))
        return
    if action == "remove" and len(rest) == 1:
        remove_runtime_barrier(
            control_dir,
            legacy_dir,
            unit,
            json.loads(rest[0]),
            uid,
            gid,
        )
        return
    raise RuntimeError("invalid runtime barrier command")


if __name__ == "__main__":
    try:
        _main(sys.argv[1:])
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"runtime barrier rejected: {exc}", file=sys.stderr)
        raise SystemExit(1)
TASK4_RUNTIME_BARRIER_PY
}

command -v timeout >/dev/null
command -v jq >/dev/null
assert_private_backup_root "$backup_root" "/home/teladi/.local/state/wirtelprimpf/deploy-backups" 1000 1000 53 7999241
test -z "$(git_runtime status --porcelain)"
runtime_branch_before="$(git_runtime branch --show-current)"
runtime_sha_before="$(git_runtime rev-parse HEAD)"
test "$runtime_branch_before" = main
[[ "$runtime_sha_before" =~ ^[0-9a-f]{40}$ ]]
test "$runtime_sha_before" != "$target_sha"

# BEGIN TASK4_INTERRUPTED_MASK_RECOVERY
interrupted_runtime_barriers=0
interrupted_timer_normalized=0
runtime_service_barrier_binding=
runtime_timer_barrier_binding=
current_timer_enabled="$(systemctl --user is-enabled wirtelprimpf.timer || true)"
current_timer_active="$(systemctl --user is-active wirtelprimpf.timer || true)"
current_timer_load="$(systemctl --user show wirtelprimpf.timer \
  -p LoadState --value)"
current_admin_active="$(systemctl --user is-active wirtelprimpf-admin.service || true)"
current_service_unit="$(systemctl --user is-enabled wirtelprimpf.service || true)"
current_service_load="$(systemctl --user show wirtelprimpf.service \
  -p LoadState --value)"
current_service_active="$(systemctl --user is-active wirtelprimpf.service || true)"
if [[ "$current_service_unit" == static && "$current_service_load" == loaded && \
      "$current_timer_load" == loaded ]]; then
  case "$current_timer_enabled" in enabled|enabled-runtime|disabled) ;; *) exit 1 ;; esac
  case "$current_timer_active" in active|inactive) ;; *) exit 1 ;; esac
  case "$current_admin_active" in active|inactive) ;; *) exit 1 ;; esac
  for barrier_path in \
    "$runtime_control_dir/wirtelprimpf.service" \
    "$runtime_control_dir/wirtelprimpf.timer" \
    "$runtime_legacy_dir/wirtelprimpf.service" \
    "$runtime_legacy_dir/wirtelprimpf.timer"; do
    [[ ! -e "$barrier_path" && ! -L "$barrier_path" ]]
  done
  timer_enabled_before="$current_timer_enabled"
  timer_active_before="$current_timer_active"
  admin_active_before="$current_admin_active"
  service_unit_state_before="$current_service_unit"
  service_load_state_before="$current_service_load"
elif [[ "$current_service_unit" == masked-runtime && \
        "$current_service_load" == masked && \
        "$current_service_active" == inactive && \
        "$current_timer_enabled" == masked-runtime && \
        "$current_timer_load" == masked && \
        "$current_timer_active" == inactive && \
        "$current_admin_active" == inactive ]]; then
  interrupted_prestate_json="$(runtime_barrier_python recover-interrupted \
    1000 1000)"
  interrupted_bindings_json="$(runtime_barrier_python adopt-interrupted \
    "$runtime_control_dir" "$runtime_legacy_dir" 1000 1000)"
  test "$(jq -er '."runtime-sha-before"' <<<"$interrupted_prestate_json")" = \
    "$runtime_sha_before"
  test "$(jq -er '."runtime-branch-before"' <<<"$interrupted_prestate_json")" = \
    "$runtime_branch_before"
  test "$(jq -er '."target-sha"' <<<"$interrupted_prestate_json")" = "$target_sha"
  timer_enabled_before="$(jq -er '."timer-enabled-before"' \
    <<<"$interrupted_prestate_json")"
  timer_active_before="$(jq -er '."timer-active-before"' \
    <<<"$interrupted_prestate_json")"
  admin_active_before="$(jq -er '."admin-active-before"' \
    <<<"$interrupted_prestate_json")"
  service_unit_state_before="$(jq -er '."service-unit-state-before"' \
    <<<"$interrupted_prestate_json")"
  service_load_state_before="$(jq -er '."service-load-state-before"' \
    <<<"$interrupted_prestate_json")"
  runtime_service_barrier_binding="$(jq -cS '.service' \
    <<<"$interrupted_bindings_json")"
  runtime_timer_barrier_binding="$(jq -cS '.timer' \
    <<<"$interrupted_bindings_json")"
  interrupted_runtime_barriers=1
else
  exit 1
fi
case "$timer_enabled_before" in enabled|enabled-runtime|disabled) ;; *) exit 1 ;; esac
case "$timer_active_before" in active|inactive) ;; *) exit 1 ;; esac
case "$admin_active_before" in active|inactive) ;; *) exit 1 ;; esac
test "$service_unit_state_before" = static
test "$service_load_state_before" = loaded
# END TASK4_INTERRUPTED_MASK_RECOVERY
running_xlets="$(gdbus call --session --dest org.Cinnamon \
  --object-path /org/Cinnamon --method org.Cinnamon.GetRunningXletUUIDs applet)"
if [[ "$running_xlets" == *wirtelprimfgenerator@H234598* ]]; then
  applet_running_before=1
else
  applet_running_before=0
fi

deploy_backup="$(mktemp -d "$backup_root/20260801-admin-live.XXXXXX")"
chmod 0700 "$deploy_backup"
backend_wheelhouse="$deploy_backup/build-backend"
backend_wheel="$backend_wheelhouse/$backend_wheel_name"
backend_constraint="$backend_wheelhouse/build-constraint.txt"
PIP_CACHE_DIR="$deploy_backup/pip-cache"
TMPDIR="$deploy_backup/pip-tmp"
printf '%s\n' "$runtime_sha_before" >"$deploy_backup/runtime-sha-before"
printf '%s\n' "$runtime_branch_before" >"$deploy_backup/runtime-branch-before"
printf '%s\n' "$target_sha" >"$deploy_backup/target-sha"
printf '%s\n' "$timer_enabled_before" >"$deploy_backup/timer-enabled-before"
printf '%s\n' "$timer_active_before" >"$deploy_backup/timer-active-before"
printf '%s\n' "$admin_active_before" >"$deploy_backup/admin-active-before"
printf '%s\n' "$service_unit_state_before" >"$deploy_backup/service-unit-state-before"
printf '%s\n' "$service_load_state_before" >"$deploy_backup/service-load-state-before"
chmod 0600 "$deploy_backup"/*-before "$deploy_backup/target-sha"
provision_build_backend_bundle

backup_complete=0
software_commit_complete=0
deployment_complete=0
runtime_service_masked="$interrupted_runtime_barriers"
runtime_timer_masked="$interrupted_runtime_barriers"

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

# BEGIN TASK4_GENERATOR_QUIESCE
snapshot_generator_state() {
  local snapshot line active_seen=0 sub_seen=0
  generator_active_state=
  generator_sub_state=
  if ! snapshot="$(systemctl --user show wirtelprimpf.service \
    -p ActiveState -p SubState --no-pager)"; then
    return 1
  fi
  while IFS= read -r line; do
    case "$line" in
      ActiveState=*)
        (( active_seen == 0 )) || return 1
        generator_active_state="${line#ActiveState=}"
        [[ -n "$generator_active_state" ]] || return 1
        active_seen=1
        ;;
      SubState=*)
        (( sub_seen == 0 )) || return 1
        generator_sub_state="${line#SubState=}"
        [[ -n "$generator_sub_state" ]] || return 1
        sub_seen=1
        ;;
      *) return 1 ;;
    esac
  done <<<"$snapshot"
  (( active_seen == 1 && sub_seen == 1 ))
}

assert_generator_inactive() {
  snapshot_generator_state || return 1
  [[ "$generator_active_state" == inactive && "$generator_sub_state" == dead ]]
}

wait_generator_inactive() {
  local deadline
  deadline=$((SECONDS + 300))
  while :; do
    snapshot_generator_state || return 1
    case "$generator_active_state/$generator_sub_state" in
      inactive/dead)
        return 0
        ;;
      activating/start-pre|activating/start|activating/auto-restart-queued)
        (( SECONDS < deadline )) || return 1
        sleep 1 || return 1
        ;;
      activating/auto-restart)
        (( SECONDS < deadline )) || return 1
        # The second property snapshot is only an early semantic filter. The
        # fail-mode stop below is the manager-side race gate: a concurrently
        # queued/running start must make it fail instead of being replaced.
        snapshot_generator_state || return 1
        [[ "$generator_active_state" == activating && \
          "$generator_sub_state" == auto-restart ]] || return 1
        systemctl --user --job-mode=fail stop wirtelprimpf.service || return 1
        assert_generator_inactive
        return
        ;;
      *)
        # No other service state is safe to reinterpret as either a naturally
        # running oneshot or an idle retry delay.
        return 1
        ;;
    esac
  done
}

mask_generator_runtime() {
  local current candidate_binding
  assert_generator_inactive || return 1
  current="$(systemctl --user is-enabled wirtelprimpf.service || true)"
  case "$current" in
    static)
      systemctl --user mask --runtime wirtelprimpf.service || return 1
      ;;
    masked-runtime)
      ;;
    *)
      return 1
      ;;
  esac
  candidate_binding="$(runtime_barrier_python ensure \
    "$runtime_control_dir" "$runtime_legacy_dir" \
    wirtelprimpf.service 1000 1000)" || return 1
  if [[ -n "$runtime_service_barrier_binding" ]]; then
    candidate_binding="$(runtime_barrier_python reconcile \
      "$runtime_service_barrier_binding" "$candidate_binding")" || return 1
  fi
  runtime_service_barrier_binding="$candidate_binding"
  systemctl --user daemon-reload || return 1
  test "$(systemctl --user is-enabled wirtelprimpf.service || true)" = \
    masked-runtime || return 1
  test "$(systemctl --user show wirtelprimpf.service -p LoadState --value)" = \
    masked || return 1
  runtime_service_masked=1
}

quiesce_generator() {
  systemctl --user stop wirtelprimpf.timer || return 1
  # A start-pre/start oneshot finishes naturally. Only a twice-observed idle
  # auto-restart delay is cancelled with a targeted service stop. Every other
  # state fails closed without stopping a potentially running generator.
  wait_generator_inactive || return 1
  mask_generator_runtime || return 1
  normalize_interrupted_timer_barrier || return 1
  # The strict post-mask snapshot closes the inactive-to-mask race. A process
  # appearing here is not waited out or stopped and no code mutation follows.
  assert_generator_inactive
}
# END TASK4_GENERATOR_QUIESCE

mask_timer_runtime_stopped() {
  local current candidate_binding
  systemctl --user stop wirtelprimpf.timer || return 1
  current="$(systemctl --user is-enabled wirtelprimpf.timer || true)"
  case "$current" in
    enabled|enabled-runtime|disabled)
      systemctl --user mask --runtime wirtelprimpf.timer || return 1
      ;;
    masked-runtime)
      ;;
    *)
      return 1
      ;;
  esac
  candidate_binding="$(runtime_barrier_python ensure \
    "$runtime_control_dir" "$runtime_legacy_dir" \
    wirtelprimpf.timer 1000 1000)" || return 1
  if [[ -n "$runtime_timer_barrier_binding" ]]; then
    candidate_binding="$(runtime_barrier_python reconcile \
      "$runtime_timer_barrier_binding" "$candidate_binding")" || return 1
  fi
  runtime_timer_barrier_binding="$candidate_binding"
  systemctl --user daemon-reload || return 1
  test "$(systemctl --user is-enabled wirtelprimpf.timer || true)" = \
    masked-runtime || return 1
  test "$(systemctl --user show wirtelprimpf.timer -p LoadState --value)" = \
    masked || return 1
  test "$(systemctl --user is-active wirtelprimpf.timer || true)" = \
    inactive || return 1
  runtime_timer_masked=1
}

unmask_timer_runtime_stopped() {
  [[ "$runtime_timer_masked" == 1 ]] || return 1
  [[ -n "$runtime_timer_barrier_binding" ]] || return 1
  runtime_barrier_python remove \
    "$runtime_control_dir" "$runtime_legacy_dir" \
    wirtelprimpf.timer 1000 1000 \
    "$runtime_timer_barrier_binding" || return 1
  runtime_timer_barrier_binding=
  runtime_timer_masked=0
  systemctl --user daemon-reload || return 1
  test "$(systemctl --user is-enabled wirtelprimpf.timer || true)" = "$timer_enabled_before"
  test "$(systemctl --user is-active wirtelprimpf.timer || true)" = inactive
}

normalize_interrupted_timer_barrier() {
  [[ "$interrupted_runtime_barriers" == 1 && \
    "$interrupted_timer_normalized" == 0 ]] || return 0
  [[ "$runtime_service_masked" == 1 && "$runtime_timer_masked" == 1 ]]
  test "$(systemctl --user show wirtelprimpf.service -p LoadState --value)" = masked
  unmask_timer_runtime_stopped || return 1
  test "$(systemctl --user show wirtelprimpf.service -p LoadState --value)" = masked
  interrupted_timer_normalized=1
}

unmask_generator_runtime() {
  [[ "$runtime_service_masked" == 1 ]] || return 1
  # Restore symmetry never starts or restarts the oneshot directly. It may be
  # unmasked only while the same strict inactive/dead state is still proven;
  # timer activity is restored separately and last.
  assert_generator_inactive || return 1
  [[ -n "$runtime_service_barrier_binding" ]] || return 1
  runtime_barrier_python remove \
    "$runtime_control_dir" "$runtime_legacy_dir" \
    wirtelprimpf.service 1000 1000 \
    "$runtime_service_barrier_binding" || return 1
  runtime_service_barrier_binding=
  runtime_service_masked=0
  systemctl --user daemon-reload || return 1
  test "$(systemctl --user is-enabled wirtelprimpf.service || true)" = \
    "$service_unit_state_before"
  test "$(systemctl --user show wirtelprimpf.service -p LoadState --value)" = \
    "$service_load_state_before"
  assert_generator_inactive
}

fail_closed_runtime() {
  local failed=0
  systemctl --user stop wirtelprimpf-admin.service || failed=1
  mask_timer_runtime_stopped || failed=1
  if wait_generator_inactive; then
    mask_generator_runtime || failed=1
  else
    failed=1
    systemctl --user stop wirtelprimpf.service || failed=1
    wait_generator_inactive || failed=1
    mask_generator_runtime || failed=1
  fi
  test "$(systemctl --user is-active wirtelprimpf-admin.service || true)" = inactive || failed=1
  test "$(systemctl --user is-active wirtelprimpf.timer || true)" = inactive || failed=1
  test "$(systemctl --user is-enabled wirtelprimpf.timer || true)" = masked-runtime || failed=1
  [[ "$runtime_service_masked" == 1 ]] || failed=1
  test "$(systemctl --user is-enabled wirtelprimpf.service || true)" = \
    masked-runtime || failed=1
  test "$(systemctl --user show wirtelprimpf.service -p LoadState --value)" = \
    masked || failed=1
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
    install_editable_offline_bounded "$runtime" \
      "$backend_wheelhouse" "$backend_wheel" \
      "$backend_wheel_size" "$backend_wheel_sha256" \
      "$backend_constraint" "$backend_constraint_sha256" || {
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
install_editable_offline_bounded "$runtime" \
  "$backend_wheelhouse" "$backend_wheel" \
  "$backend_wheel_size" "$backend_wheel_sha256" \
  "$backend_constraint" "$backend_constraint_sha256"
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
the old checkout, offline editable install from the same hash-bound backend
bundle, units, applet, admin state, exact timer
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
installer returns to `0755` only on rollback. Its generator state stub mirrors
Step 9: timer-first ordering, natural `start-pre`/`start` completion, confirmed
`auto-restart` cancellation, strict inactive-before/after-mask proof, and
fail-closed timeout, unexpected-state, confirmation-race, and post-mask-race
paths. The checked-in structural runner
`python -m unittest tests.test_rollout_plan_contract -v` additionally extracts
the exact Step-9/Step-10 blocks, syntax-checks both, requires the complete
audited Step-5/Step-6 bodies byte-for-byte inside Step 9, proves marker-producer
ordering, executes the actual backend provision/install helpers with a
single-call fake downloader and offline fake Pip, rejects a pre-existing
corrupt wheel without retry, and calls the identical install helper in both
forward and rollback positions. It also executes the exact interrupted-attempt
validator against a disposable two-node chain, rejects two current leaves and
binds the live constants to historical `HNkEdc`, current `f1iePQ`, all current
barrier Inodes and complete manifest/payload metadata. Finally it
failure-injects the separate 16-entry shared-Git FD transaction and proves
rollback, hash drift and foreign-owner rejection. Then it executes this
disposable shell harness:

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
printf 'activating\n' >"$sandbox/generator-active-state"
printf 'start\n' >"$sandbox/generator-sub-state"
printf 'static\n' >"$sandbox/service-enablement"
printf 'active\n' >"$sandbox/admin-state"
printf 'running\n' >"$sandbox/applet-state"
: >"$sandbox/barrier-proof"
for unit in wirtelprimpf.service wirtelprimpf.timer wirtelprimpf-admin.service; do
  printf 'unit=%s\n' "$unit" >"$sandbox/source/units/$unit"
  cp -a -- "$sandbox/source/units/$unit" "$sandbox/live/units/$unit"
done
printf 'applet-target\n' >"$sandbox/source/applet/metadata.json"
cp -a -- "$sandbox/source/applet/metadata.json" \
  "$sandbox/live/applet/metadata.json"
: >"$sandbox/recovery-events"

# BEGIN TASK4_BUILD_BACKEND_HARNESS
# The checked-in Python contract executes the exact Step-9 functions. This
# shell model independently proves the Step-10 event sequence and the absence
# of a download fallback once a destination already exists.
mkdir -m0700 "$sandbox/backend-wheelhouse"
printf 'disposable exact backend wheel\n' >"$sandbox/backend-fixture.whl"
backend_fixture_size="$(stat -Lc '%s' "$sandbox/backend-fixture.whl")"
backend_fixture_sha256="$(sha256sum "$sandbox/backend-fixture.whl" | cut -d' ' -f1)"
backend_destination="$sandbox/backend-wheelhouse/backend.whl"
backend_download_attempts=0
: >"$sandbox/backend-events"

validate_backend_fixture() {
  local candidate="$1"
  test -f "$candidate" && test ! -L "$candidate"
  test "$(stat -Lc '%s' "$candidate")" = "$backend_fixture_size"
  test "$(sha256sum "$candidate" | cut -d' ' -f1)" = \
    "$backend_fixture_sha256"
}

download_backend_once_harness() {
  local temporary
  if [[ -e "$backend_destination" || -L "$backend_destination" ]]; then
    validate_backend_fixture "$backend_destination"
    return
  fi
  backend_download_attempts=$((backend_download_attempts + 1))
  temporary="$(mktemp "$sandbox/backend-wheelhouse/.download.XXXXXX")"
  chmod 0600 "$temporary"
  cp -- "$sandbox/backend-fixture.whl" "$temporary"
  validate_backend_fixture "$temporary"
  ln -- "$temporary" "$backend_destination"
  rm -f -- "$temporary"
  validate_backend_fixture "$backend_destination"
  printf 'backend-single-fetch\n' >>"$sandbox/backend-events"
}

offline_build_harness() {
  local direction="$1"
  case "$direction" in forward|rollback) ;; *) return 1 ;; esac
  validate_backend_fixture "$backend_destination"
  printf 'backend-offline-%s\n' "$direction" >>"$sandbox/backend-events"
}

download_backend_once_harness
download_backend_once_harness
test "$backend_download_attempts" = 1
offline_build_harness forward
offline_build_harness rollback
printf 'corrupt existing destination\n' >"$backend_destination"
set +e
download_backend_once_harness
backend_corrupt_status=$?
set -e
test "$backend_corrupt_status" -ne 0
test "$backend_download_attempts" = 1
printf 'backend-corruption-rejected\n' >>"$sandbox/backend-events"
test "$(paste -sd, "$sandbox/backend-events")" = \
  backend-single-fetch,backend-offline-forward,backend-offline-rollback,backend-corruption-rejected
# END TASK4_BUILD_BACKEND_HARNESS

runtime_load_state_harness() {
  local unit="$1"
  case "$unit" in service|timer) ;; *) return 1 ;; esac
  if [[ -e "$sandbox/$unit-control-mask" ]]; then
    printf 'masked\n'
  else
    printf 'loaded\n'
  fi
}

assert_recovery_lock_held() {
  if flock -n "$sandbox/settings.lock" true; then
    printf 'recovery mutation escaped the settings lock\n' >&2
    return 1
  fi
}

restore_install_targets() {
  test "$(<"$sandbox/generator-active-state")" = inactive
  test "$(<"$sandbox/generator-sub-state")" = dead
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
  if [[ "$(<"$sandbox/service-enablement")" == static ]]; then
    rm -f -- "$sandbox/service-legacy-mask" "$sandbox/service-control-mask"
  fi
  printf 'timer-stop\n' >>"$sandbox/recovery-events"
  printf 'inactive\n' >"$sandbox/timer-state"
  while :; do
    case "$(<"$sandbox/generator-active-state")/$(<"$sandbox/generator-sub-state")" in
      inactive/dead)
        break
        ;;
      activating/start-pre|activating/start)
        attempts=$((attempts + 1))
        if [[ "$transition" == after-first-wait && "$attempts" == 1 ]]; then
          printf 'inactive\n' >"$sandbox/generator-active-state"
          printf 'dead\n' >"$sandbox/generator-sub-state"
        elif [[ "$transition" == running-auto-restart && "$attempts" == 1 ]]; then
          printf 'activating\n' >"$sandbox/generator-active-state"
          printf 'auto-restart\n' >"$sandbox/generator-sub-state"
        fi
        (( attempts < max_attempts )) || return 1
        ;;
      activating/auto-restart)
        if [[ "$transition" == auto-restart-race ]]; then
          printf 'activating\n' >"$sandbox/generator-active-state"
          printf 'start\n' >"$sandbox/generator-sub-state"
        fi
        test "$(<"$sandbox/generator-active-state")" = activating || return 1
        test "$(<"$sandbox/generator-sub-state")" = auto-restart || return 1
        printf 'service-auto-restart-stop\n' >>"$sandbox/recovery-events"
        printf 'inactive\n' >"$sandbox/generator-active-state"
        printf 'dead\n' >"$sandbox/generator-sub-state"
        test "$(<"$sandbox/generator-active-state")" = inactive || return 1
        test "$(<"$sandbox/generator-sub-state")" = dead || return 1
        break
        ;;
      *) return 1 ;;
    esac
  done
  printf 'generator-inactive-before-mask\n' >>"$sandbox/recovery-events"
  : >"$sandbox/service-legacy-mask"
  test ! -e "$sandbox/service-control-mask"
  printf 'lower-priority-mask-is-ineffective\n' >>"$sandbox/barrier-proof"
  : >"$sandbox/service-control-mask"
  test "$(runtime_load_state_harness service)" = masked
  printf 'masked-runtime\n' >"$sandbox/service-enablement"
  printf 'service-runtime-mask\n' >>"$sandbox/recovery-events"
  if [[ "$transition" == after-mask-reactivation ]]; then
    printf 'activating\n' >"$sandbox/generator-active-state"
    printf 'start\n' >"$sandbox/generator-sub-state"
  fi
  test "$(<"$sandbox/generator-active-state")" = inactive || return 1
  test "$(<"$sandbox/generator-sub-state")" = dead || return 1
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
  test "$(<"$sandbox/generator-active-state")" = inactive
  test "$(<"$sandbox/generator-sub-state")" = dead
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
  rm -f -- "$sandbox/service-legacy-mask"
  test "$(runtime_load_state_harness service)" = masked
  rm -f -- "$sandbox/service-control-mask"
  test "$(runtime_load_state_harness service)" = loaded
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
  : >"$sandbox/timer-legacy-mask"
  : >"$sandbox/timer-control-mask"
  : >"$sandbox/service-legacy-mask"
  : >"$sandbox/service-control-mask"
  test "$(runtime_load_state_harness timer)" = masked
  test "$(runtime_load_state_harness service)" = masked
  printf 'fail-closed-admin-stop\nfail-closed-timer-stop\ntimer-runtime-mask\nservice-runtime-mask\n' \
    >>"$sandbox/recovery-events"
  test "$(<"$sandbox/timer-persistent-enablement")" = enabled
}

# BEGIN TASK4_INTERRUPTED_FOUR_LINK_HARNESS
# Model the exact state left by the failed lower-priority mask attempt plus the
# effective user.control containment. Adoption itself is read-only; only after
# the service barrier is proven continuously effective may the stopped timer's
# pair be normalized for the fresh transaction.
: >"$sandbox/service-legacy-mask"
: >"$sandbox/service-control-mask"
: >"$sandbox/timer-legacy-mask"
: >"$sandbox/timer-control-mask"
printf 'masked-runtime\n' >"$sandbox/service-enablement"
printf 'masked-runtime\n' >"$sandbox/timer-enablement"
printf 'inactive\n' >"$sandbox/generator-active-state"
printf 'dead\n' >"$sandbox/generator-sub-state"
printf 'inactive\n' >"$sandbox/timer-state"
printf 'inactive\n' >"$sandbox/admin-state"
test "$(runtime_load_state_harness service)" = masked
test "$(runtime_load_state_harness timer)" = masked
printf 'historical-HNkEdc-evidence\ncurrent-f1iePQ-inode-hash-chain\n' \
  >>"$sandbox/barrier-proof"
printf 'interrupted-four-link-adoption\n' >>"$sandbox/barrier-proof"
rm -f -- "$sandbox/timer-legacy-mask"
test "$(runtime_load_state_harness service)" = masked
test "$(runtime_load_state_harness timer)" = masked
rm -f -- "$sandbox/timer-control-mask"
printf 'enabled\n' >"$sandbox/timer-enablement"
test "$(runtime_load_state_harness service)" = masked
test "$(runtime_load_state_harness timer)" = loaded
printf 'timer-recovery-normalized\n' >>"$sandbox/barrier-proof"
printf 'static\n' >"$sandbox/service-enablement"
printf 'active\n' >"$sandbox/timer-state"
printf 'active\n' >"$sandbox/admin-state"
# END TASK4_INTERRUPTED_FOUR_LINK_HARNESS

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
printf 'activating\n' >"$sandbox/generator-active-state"
printf 'start\n' >"$sandbox/generator-sub-state"
printf 'static\n' >"$sandbox/service-enablement"
set +e
rollback_harness never 0.2
quiesce_status=$?
set -e
test "$quiesce_status" -ne 0
test "$(paste -sd, "$sandbox/recovery-events")" = timer-stop

# The observed production preflight state is an idle RestartSec delay, not a
# running generator. Two matching snapshots permit exactly one targeted stop,
# followed by inactive proof and the runtime mask without a polling delay.
: >"$sandbox/recovery-events"
printf 'activating\n' >"$sandbox/generator-active-state"
printf 'auto-restart\n' >"$sandbox/generator-sub-state"
printf 'static\n' >"$sandbox/service-enablement"
quiesce_generator_harness current-auto-restart
test "$(<"$sandbox/generator-active-state")" = inactive
test "$(<"$sandbox/generator-sub-state")" = dead
test "$(<"$sandbox/service-enablement")" = masked-runtime
test "$(paste -sd, "$sandbox/recovery-events")" = \
  timer-stop,service-auto-restart-stop,generator-inactive-before-mask,service-runtime-mask,generator-inactive-after-mask

# A real start is never stopped. If it later enters the idle auto-restart
# delay, only that twice-confirmed delay is cancelled before masking.
: >"$sandbox/recovery-events"
printf 'activating\n' >"$sandbox/generator-active-state"
printf 'start\n' >"$sandbox/generator-sub-state"
printf 'static\n' >"$sandbox/service-enablement"
quiesce_generator_harness running-auto-restart
test "$(<"$sandbox/generator-active-state")" = inactive
test "$(<"$sandbox/generator-sub-state")" = dead
test "$(<"$sandbox/service-enablement")" = masked-runtime
test "$(paste -sd, "$sandbox/recovery-events")" = \
  timer-stop,service-auto-restart-stop,generator-inactive-before-mask,service-runtime-mask,generator-inactive-after-mask

# A change between the first and confirming auto-restart snapshots fails
# closed before both the targeted stop and the mask.
: >"$sandbox/recovery-events"
printf 'activating\n' >"$sandbox/generator-active-state"
printf 'auto-restart\n' >"$sandbox/generator-sub-state"
printf 'static\n' >"$sandbox/service-enablement"
set +e
quiesce_generator_harness auto-restart-race
auto_restart_race_status=$?
set -e
test "$auto_restart_race_status" -ne 0
test "$(<"$sandbox/generator-active-state")" = activating
test "$(<"$sandbox/generator-sub-state")" = start
test "$(<"$sandbox/service-enablement")" = static
test "$(paste -sd, "$sandbox/recovery-events")" = timer-stop

# An unclassified state is not waited out, stopped, or masked.
: >"$sandbox/recovery-events"
printf 'active\n' >"$sandbox/generator-active-state"
printf 'running\n' >"$sandbox/generator-sub-state"
printf 'static\n' >"$sandbox/service-enablement"
set +e
quiesce_generator_harness unexpected
unexpected_state_status=$?
set -e
test "$unexpected_state_status" -ne 0
test "$(<"$sandbox/service-enablement")" = static
test "$(paste -sd, "$sandbox/recovery-events")" = timer-stop

# Lock contention is also bounded and fail-closed: after quiescence/admin-stop,
# no install, directory-mode, config, checkout, venv, or unit restore occurs.
: >"$sandbox/recovery-events"
printf 'inactive\n' >"$sandbox/generator-active-state"
printf 'dead\n' >"$sandbox/generator-sub-state"
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

# A synthetic activation in the inactive-to-mask boundary is caught by the
# strict post-mask proof. It is neither waited out nor stopped, and no recovery
# mutation can follow; the already-applied mask remains fail-closed.
: >"$sandbox/recovery-events"
printf 'inactive\n' >"$sandbox/generator-active-state"
printf 'dead\n' >"$sandbox/generator-sub-state"
printf 'static\n' >"$sandbox/service-enablement"
set +e
quiesce_generator_harness after-mask-reactivation
after_mask_race_status=$?
set -e
test "$after_mask_race_status" -ne 0
test "$(<"$sandbox/generator-active-state")" = activating
test "$(<"$sandbox/generator-sub-state")" = start
test "$(<"$sandbox/service-enablement")" = masked-runtime
test "$(paste -sd, "$sandbox/recovery-events")" = \
  timer-stop,generator-inactive-before-mask,service-runtime-mask

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
git -C "$runtime_harness" switch --detach -q "$runtime_sha_before"
printf 'target-tree\n' >"$runtime_harness/application.txt"
git -C "$runtime_harness" commit -qam target
target_sha="$(git -C "$runtime_harness" rev-parse HEAD)"
target_tree="$(git -C "$runtime_harness" rev-parse "$target_sha^{tree}")"
test "$(<"$runtime_harness/application.txt")" = target-tree

assert_final_lock_held() {
  if flock -n "$sandbox/settings.lock" true; then
    printf 'final transaction escaped the settings lock\n' >&2
    return 1
  fi
}

: >"$sandbox/success-events"
rm -f -- "$sandbox/timer-legacy-mask" "$sandbox/timer-control-mask"
printf 'inactive\n' >"$sandbox/timer-state"
printf 'enabled\n' >"$sandbox/timer-enablement"
printf 'masked-runtime\n' >"$sandbox/service-enablement"
: >"$sandbox/service-legacy-mask"
: >"$sandbox/service-control-mask"
test "$(runtime_load_state_harness service)" = masked
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
: >"$sandbox/timer-legacy-mask"
test ! -e "$sandbox/timer-control-mask"
: >"$sandbox/timer-control-mask"
test "$(runtime_load_state_harness timer)" = masked
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
rm -f -- "$sandbox/timer-legacy-mask"
test "$(runtime_load_state_harness timer)" = masked
rm -f -- "$sandbox/timer-control-mask"
test "$(runtime_load_state_harness timer)" = loaded
printf 'enabled\n' >"$sandbox/timer-enablement"
test "$(<"$sandbox/timer-state")" = inactive
printf 'timer-runtime-unmask\n' >>"$sandbox/success-events"
rm -f -- "$sandbox/service-legacy-mask"
test "$(runtime_load_state_harness service)" = masked
rm -f -- "$sandbox/service-control-mask"
test "$(runtime_load_state_harness service)" = loaded
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
parent = workflow.parent
archive_root = workflow.parents[2]
if workflow != archive_root / ".github" / "workflows" / "pages.yml":
    raise SystemExit("archive workflow path is outside the trusted layout")
workflow_name = workflow.name
part_name = f".{workflow_name}.{os.getpid()}.part"
root_fd = os.open(
    archive_root,
    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
)
github_fd = None
parent_fd = None
try:
    root_st = os.fstat(root_fd)
    if not stat.S_ISDIR(root_st.st_mode) or not (root_st.st_uid == 1000 and root_st.st_gid == 1000):
        raise SystemExit("archive root must be a teladi-owned directory")
    root_identity = (root_st.st_dev, root_st.st_ino)
    github_fd = os.open(
        ".github",
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        dir_fd=root_fd,
    )
    github_st = os.fstat(github_fd)
    if not stat.S_ISDIR(github_st.st_mode) or not (
        github_st.st_uid == 1000 and github_st.st_gid == 1000
    ):
        raise SystemExit("archive .github must be a teladi-owned directory")
    github_identity = (github_st.st_dev, github_st.st_ino)
    parent_fd = os.open(
        "workflows",
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        dir_fd=github_fd,
    )
    parent_st = os.fstat(parent_fd)
    if not stat.S_ISDIR(parent_st.st_mode) or not (
        parent_st.st_uid == 1000 and parent_st.st_gid == 1000
    ):
        raise SystemExit("archive workflow parent must be a teladi-owned directory")
    parent_identity = (parent_st.st_dev, parent_st.st_ino)
    source_fd = os.open(
        workflow_name,
        os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        dir_fd=parent_fd,
    )
    with os.fdopen(source_fd, "r", encoding="utf-8", newline="") as source:
        st = os.fstat(source.fileno())
        if not stat.S_ISREG(st.st_mode) or not (st.st_uid == 1000 and st.st_gid == 1000):
            raise SystemExit("archive workflow must be a teladi-owned regular file")
        if stat.S_IMODE(st.st_mode) != 0o644:
            raise SystemExit("archive workflow mode must be 0644")
        target_identity = (
            st.st_dev,
            st.st_ino,
            st.st_uid,
            st.st_gid,
            st.st_mode,
            st.st_size,
            st.st_mtime_ns,
            st.st_ctime_ns,
        )
        original = source.read()
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
    descriptor = os.open(
        part_name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=parent_fd,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
        handle.write(updated)
        handle.flush()
        os.fsync(handle.fileno())
        os.fchmod(handle.fileno(), 0o644)
    current_root = os.stat(archive_root, follow_symlinks=False)
    if (current_root.st_dev, current_root.st_ino) != root_identity:
        raise SystemExit("archive root identity changed")
    current_github = os.stat(".github", dir_fd=root_fd, follow_symlinks=False)
    if (current_github.st_dev, current_github.st_ino) != github_identity:
        raise SystemExit("archive .github identity changed")
    current_parent = os.stat(parent, follow_symlinks=False)
    if (current_parent.st_dev, current_parent.st_ino) != parent_identity:
        raise SystemExit("archive workflow parent identity changed")
    current_target = os.stat(workflow_name, dir_fd=parent_fd, follow_symlinks=False)
    current_target_identity = (
        current_target.st_dev,
        current_target.st_ino,
        current_target.st_uid,
        current_target.st_gid,
        current_target.st_mode,
        current_target.st_size,
        current_target.st_mtime_ns,
        current_target.st_ctime_ns,
    )
    if current_target_identity != target_identity:
        raise SystemExit("archive workflow target identity changed")
    os.replace(part_name, workflow_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
    os.fsync(parent_fd)
finally:
    if parent_fd is not None:
        try:
            os.unlink(part_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        os.close(parent_fd)
    if github_fd is not None:
        os.close(github_fd)
    os.close(root_fd)
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
  test "$(/usr/bin/grep -Ec -- \
    "^[[:space:]]*uses:[[:space:]]+H234598/Wirtelprimpf-generator/\\.github/workflows/archive-pages\\.yml@$factory_sha[[:space:]]*$" \
    <<<"$workflow_text")" = 1
  test "$(/usr/bin/grep -Ec -- \
    "^[[:space:]]*factory_ref:[[:space:]]*\"$factory_sha\"[[:space:]]*$" \
    <<<"$workflow_text")" = 1
  sha_lines="$(/usr/bin/grep -Eo -- '[0-9a-f]{40}' <<<"$workflow_text")"
  test "$sha_lines" = "$factory_sha"$'\n'"$factory_sha"
  if /usr/bin/grep -Eq -- '^[[:space:]]*pull_request[[:space:]]*:' \
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

# Materialize the observed remote merge into the unprivileged archive checkout.
# Task 6 consumes these named main refs exclusively; it never reads feature HEAD.
task5_postmerge_local_main() {
  local merged_sha="$1"
  [[ "$merged_sha" =~ ^[0-9a-f]{40}$ ]]
  /usr/sbin/runuser -u teladi -- /usr/bin/env -i \
    HOME=/home/teladi \
    USER=teladi \
    LOGNAME=teladi \
    PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    GIT_CONFIG_NOSYSTEM=1 \
    GIT_CONFIG_GLOBAL=/dev/null \
    GIT_TERMINAL_PROMPT=0 \
    GIT_ASKPASS=/bin/false \
    SSH_ASKPASS=/bin/false \
    /bin/bash -se -- "$merged_sha" <<'TASK5_POSTMERGE_TELADI'
set -Eeuo pipefail
set +x
test "$(id -u)" = 1000
test "$(id -g)" = 1000
merged_sha="$1"
[[ "$merged_sha" =~ ^[0-9a-f]{40}$ ]]
archive_checkout=/home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001
canonical_origin=https://github.com/H234598/Wirtelprimpf-0001.git
test -d "$archive_checkout" && test ! -L "$archive_checkout"
test "$(realpath -e -- "$archive_checkout")" = "$archive_checkout"
test -z "$(find "$archive_checkout" -xdev \
  \( ! -uid 1000 -o ! -gid 1000 \) -print -quit)"

task5_postmerge_git() {
  /usr/bin/timeout --foreground --signal=TERM --kill-after=10s 180s \
    /usr/bin/git \
      -c http.extraHeader= \
      -c "http.$canonical_origin.extraHeader=" \
      -c http.proxy= \
      -c http.sslVerify=true \
      -c http.curloptResolve= \
      -c credential.helper= \
      -c core.askPass=/bin/false \
      -c core.hooksPath=/dev/null \
      -c core.fsmonitor=false \
      -c core.sshCommand=/bin/false \
      -c core.gitProxy=/bin/false \
      -c protocol.allow=never \
      -c protocol.https.allow=always \
      -c protocol.ext.allow=never \
      -C "$archive_checkout" "$@"
}

# BEGIN TASK5_POSTMERGE_GIT_GUARD
task5_postmerge_local_config() {
  /usr/bin/git -C "$archive_checkout" config --local --no-includes "$@"
}

assert_safe_task5_postmerge_config() {
  local key value branch_name
  while IFS= read -r key; do
    case "$key" in
      core.repositoryformatversion|core.filemode|core.bare|core.logallrefupdates|\
      remote.origin.url|remote.origin.fetch|remote.origin.promisor|\
      remote.origin.partialclonefilter|branch.*.remote|branch.*.merge)
        ;;
      *)
        return 1
        ;;
    esac
  done < <(task5_postmerge_local_config --name-only --get-regexp '.*')
  case "$(task5_postmerge_local_config --get-all \
    core.repositoryformatversion)" in 0|1) ;; *) return 1 ;; esac
  case "$(task5_postmerge_local_config --get-all core.filemode)" in
    true|false) ;;
    *) return 1 ;;
  esac
  test "$(task5_postmerge_local_config --get-all core.bare)" = false
  test "$(task5_postmerge_local_config --get-all core.logallrefupdates)" = true
  test "$(task5_postmerge_local_config --get-all remote.origin.url)" = \
    "$canonical_origin"
  test "$(task5_postmerge_local_config --get-all remote.origin.fetch)" = \
    '+refs/heads/main:refs/remotes/origin/main'
  value="$(task5_postmerge_local_config --get-all \
    remote.origin.promisor || :)"
  case "$value" in ""|true) ;; *) return 1 ;; esac
  value="$(task5_postmerge_local_config --get-all \
    remote.origin.partialclonefilter || :)"
  case "$value" in ""|blob:none) ;; *) return 1 ;; esac
  test "$(task5_postmerge_local_config --get-all branch.main.remote)" = origin
  test "$(task5_postmerge_local_config --get-all branch.main.merge)" = \
    refs/heads/main
  while IFS= read -r key; do
    case "$key" in
      branch.*.remote)
        branch_name="${key#branch.}"
        branch_name="${branch_name%.remote}"
        /usr/bin/git check-ref-format "refs/heads/$branch_name" >/dev/null || \
          return 1
        test "$(task5_postmerge_local_config --get-all "$key")" = origin || \
          return 1
        ;;
      branch.*.merge)
        branch_name="${key#branch.}"
        branch_name="${branch_name%.merge}"
        /usr/bin/git check-ref-format "refs/heads/$branch_name" >/dev/null || \
          return 1
        test "$(task5_postmerge_local_config --get-all "$key")" = \
          "refs/heads/$branch_name" || return 1
        ;;
    esac
  done < <(task5_postmerge_local_config --name-only \
    --get-regexp '^branch\..*\.(remote|merge)$')
}
# END TASK5_POSTMERGE_GIT_GUARD

assert_safe_task5_postmerge_config
test -z "$(task5_postmerge_git status --porcelain)"
local_main="$(task5_postmerge_git rev-parse --verify \
  'refs/heads/main^{commit}')"
[[ "$local_main" =~ ^[0-9a-f]{40}$ ]]
task5_postmerge_git fetch "$canonical_origin" \
  '+refs/heads/main:refs/remotes/origin/main'
remote_main="$(task5_postmerge_git rev-parse --verify \
  'refs/remotes/origin/main^{commit}')"
test "$remote_main" = "$merged_sha"
task5_postmerge_git merge-base --is-ancestor "$local_main" "$remote_main"
task5_postmerge_git switch main
task5_postmerge_git merge --ff-only refs/remotes/origin/main
local_main="$(task5_postmerge_git rev-parse --verify \
  'refs/heads/main^{commit}')"
remote_main="$(task5_postmerge_git rev-parse --verify \
  'refs/remotes/origin/main^{commit}')"
test "$local_main" = "$merged_sha"
test "$remote_main" = "$merged_sha"
test "$(task5_postmerge_git branch --show-current)" = main
test -z "$(task5_postmerge_git status --porcelain)"
test -z "$(find "$archive_checkout" -xdev \
  \( ! -uid 1000 -o ! -gid 1000 \) -print -quit)"
printf '%s\n' "$local_main"
TASK5_POSTMERGE_TELADI
}
test "$(task5_postmerge_local_main "$archive_sha")" = "$archive_sha"
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
set -Eeuo pipefail
set +x
test "$(id -u)" = 0
test "$(id -g)" = 0

canonical_generator_repository=H234598/Wirtelprimpf-generator
canonical_generator_repo_id=R_kgDOTpr2BA
canonical_archive_repository=H234598/Wirtelprimpf-0001
canonical_archive_repo_id=R_kgDOSg7oRg

# The root shell receives only five already-validated, non-secret literals.
# The complete state and local-ref probe runs unprivileged, without inherited
# authentication variables, but with the desktop session environment available.
task6_probe_output="$(
  /usr/sbin/runuser -u teladi -- /usr/bin/env -i \
    HOME=/home/teladi \
    USER=teladi \
    LOGNAME=teladi \
    PATH=/home/teladi/.local/bin:/usr/local/bin:/usr/bin:/bin \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    DISPLAY=:0 \
    XAUTHORITY=/home/teladi/.Xauthority \
    XDG_RUNTIME_DIR=/run/user/1000 \
    DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
    /bin/bash --noprofile --norc <<'TASK6_LOCAL_PROBE'
set -Eeuo pipefail
set +x
test "$(id -u)" = 1000
test "$(id -g)" = 1000

platform_state=/home/teladi/.local/state/wirtelprimpf/platform-state.json
generator_checkout=/home/teladi/.local/share/wirtelprimpf-generator
archive_parent=/home/teladi/.local/share/wirtelprimpf/archives

state_fields="$(
  /usr/bin/python3 - "$platform_state" <<'TASK6_STATE'
import json
import os
import stat
import sys

path = sys.argv[1]
fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
try:
    metadata = os.fstat(fd)
    if not stat.S_ISREG(metadata.st_mode):
        raise SystemExit("platform state is not a regular file")
    if (metadata.st_uid, metadata.st_gid) != (1000, 1000):
        raise SystemExit("platform state ownership mismatch")
    if metadata.st_size < 2 or metadata.st_size > 65_536:
        raise SystemExit("platform state size outside the accepted bound")
    raw = os.read(fd, 65_537)
finally:
    os.close(fd)
if len(raw) > 65_536:
    raise SystemExit("platform state exceeds the accepted bound")
payload = json.loads(raw.decode("utf-8"))
current_volume = payload.get("current_volume")
archive_index = payload.get("active_archive_index")
if type(current_volume) is not int or not 1 <= current_volume <= 499_950:
    raise SystemExit("invalid current volume")
if type(archive_index) is not int or not 1 <= archive_index <= 9_999:
    raise SystemExit("invalid active archive index")
expected_index = ((current_volume - 1) // 50) + 1
if archive_index != expected_index:
    raise SystemExit("active archive index does not match current volume")
print(f"{current_volume}\t{archive_index}\tWirtelprimpf-{archive_index:04d}")
TASK6_STATE
)"
IFS=$'\t' read -r current_volume active_archive_index active_repository \
  unexpected_state_field <<<"$state_fields"
test -z "${unexpected_state_field:-}"
[[ "$current_volume" =~ ^[1-9][0-9]{0,5}$ ]]
[[ "$active_archive_index" =~ ^[1-9][0-9]{0,3}$ ]]
[[ "$active_repository" =~ ^Wirtelprimpf-[0-9]{4}$ ]]
test "$active_repository" = \
  "$(printf 'Wirtelprimpf-%04d' "$active_archive_index")"
test "$active_repository" = Wirtelprimpf-0001

archive_checkout="$archive_parent/$active_repository"
for checkout in "$generator_checkout" "$archive_checkout"; do
  test -d "$checkout"
  test ! -L "$checkout"
  test "$(realpath -e -- "$checkout")" = "$checkout"
  test -z "$(find "$checkout" -xdev \
    \( ! -uid 1000 -o ! -gid 1000 \) -print -quit)"
done

task6_local_git() {
  local checkout="$1" operation="${2:-}"
  shift 2
  case "$operation" in config|rev-parse) ;; *) return 1 ;; esac
  /usr/bin/timeout --foreground --signal=TERM --kill-after=2s 15s \
    /usr/bin/env -i \
      HOME=/home/teladi USER=teladi LOGNAME=teladi \
      PATH=/usr/local/bin:/usr/bin:/bin \
      GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null \
      GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/false SSH_ASKPASS=/bin/false \
      /usr/bin/git \
        -c core.askPass=/bin/false \
        -c core.hooksPath=/dev/null \
        -c core.fsmonitor=false \
        -c core.sshCommand=/bin/false \
        -c core.gitProxy=/bin/false \
        -c core.attributesFile=/dev/null \
        -c credential.helper= \
        -c http.extraHeader= \
        -c http.proxy= \
        -c protocol.allow=never \
        -c protocol.ext.allow=never \
        -C "$checkout" "$operation" "$@"
}

assert_task6_checkout() {
  local checkout="$1" canonical_origin="$2" top_level fetch_url push_url
  top_level="$(task6_local_git "$checkout" rev-parse --show-toplevel)"
  test "$top_level" = "$checkout"
  fetch_url="$(task6_local_git "$checkout" config --local --no-includes \
    --get-all remote.origin.url)"
  push_url="$(task6_local_git "$checkout" config --local --no-includes \
    --get-all remote.origin.pushurl || :)"
  test "$fetch_url" = "$canonical_origin"
  test -z "$push_url"
}

resolve_task6_main() {
  local checkout="$1" local_main remote_main
  local_main="$(task6_local_git "$checkout" rev-parse --verify \
    'refs/heads/main^{commit}')"
  remote_main="$(task6_local_git "$checkout" rev-parse --verify \
    'refs/remotes/origin/main^{commit}')"
  [[ "$local_main" =~ ^[0-9a-f]{40}$ ]]
  test "$local_main" = "$remote_main"
  printf '%s\n' "$local_main"
}

assert_task6_checkout "$generator_checkout" \
  https://github.com/H234598/Wirtelprimpf-generator.git
assert_task6_checkout "$archive_checkout" \
  https://github.com/H234598/Wirtelprimpf-0001.git
generator_main_sha="$(resolve_task6_main "$generator_checkout")"
archive_main_sha="$(resolve_task6_main "$archive_checkout")"
printf '%s\t%s\t%s\t%s\t%s\n' \
  "$current_volume" "$active_archive_index" "$active_repository" \
  "$archive_main_sha" "$generator_main_sha"
TASK6_LOCAL_PROBE
)"

[[ "$task6_probe_output" != *$'\n'* ]]
IFS=$'\t' read -r current_volume active_archive_index active_repository \
  archive_main_sha generator_main_sha unexpected_probe_field \
  <<<"$task6_probe_output"
test -z "${unexpected_probe_field:-}"
[[ "$current_volume" =~ ^[1-9][0-9]{0,5}$ ]]
[[ "$active_archive_index" =~ ^[1-9][0-9]{0,3}$ ]]
[[ "$active_repository" =~ ^Wirtelprimpf-[0-9]{4}$ ]]
test "$active_repository" = Wirtelprimpf-0001
[[ "$archive_main_sha" =~ ^[0-9a-f]{40}$ ]]
[[ "$generator_main_sha" =~ ^[0-9a-f]{40}$ ]]

# Accept exactly one inherited ephemeral credential, remove both conventional
# names immediately, and relay the value through a private descriptor. Stdin
# stays untouched so the exact dispatch JSON can be supplied with --input -.
if [[ -n "${GH_TOKEN:-}" && -n "${GITHUB_TOKEN:-}" ]]; then
  printf 'Refusing ambiguous GitHub authentication.\n' >&2
  exit 1
fi
task6_ephemeral_token="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
unset GH_TOKEN GITHUB_TOKEN
test -n "$task6_ephemeral_token"

task6_cleanup() {
  set +x
  unset task6_ephemeral_token
}
trap 'task6_status=$?; trap - EXIT; task6_cleanup; exit "$task6_status"' EXIT

task6_token_call() {
  set +x
  local task6_token_status=0
  /usr/bin/env -i \
    HOME=/root \
    USER=root \
    LOGNAME=root \
    PATH=/usr/local/bin:/usr/bin:/bin \
    GIT_CONFIG_NOSYSTEM=1 \
    GIT_CONFIG_GLOBAL=/dev/null \
    GIT_TERMINAL_PROMPT=0 \
    GIT_ASKPASS=/bin/false \
    SSH_ASKPASS=/bin/false \
    /bin/bash -c '
      set -Eeuo pipefail
      set +x
      task6_call_token=
      IFS= read -r -d "" task6_call_token <&9
      exec 9<&-
      GH_TOKEN="$task6_call_token" exec "$@"
    ' task6-token-call "$@" 9< <(
      printf '%s\0' "$task6_ephemeral_token"
    ) || task6_token_status=$?
  return "$task6_token_status"
}

task6_gh() {
  task6_token_call /usr/bin/gh "$@"
}

task6_actor_json="$(task6_gh api /user)"
/usr/bin/jq -e \
  '.login == "H234598" and .id == 54270221' \
  <<<"$task6_actor_json" >/dev/null

task6_generator_repository_json="$(
  task6_gh repo view "$canonical_generator_repository" --json id,nameWithOwner
)"
/usr/bin/jq -e \
  '.id == "R_kgDOTpr2BA" and
   .nameWithOwner == "H234598/Wirtelprimpf-generator"' \
  <<<"$task6_generator_repository_json" >/dev/null

task6_archive_repository_json="$(
  task6_gh repo view "$canonical_archive_repository" --json id,nameWithOwner
)"
/usr/bin/jq -e \
  --arg id "$canonical_archive_repo_id" \
  --arg name "$canonical_archive_repository" \
  '.id == $id and .nameWithOwner == $name' \
  <<<"$task6_archive_repository_json" >/dev/null

test "$(task6_gh api \
  "repos/$canonical_generator_repository/git/ref/heads/main" \
  --jq .object.sha)" = "$generator_main_sha"
test "$(task6_gh api \
  "repos/$canonical_archive_repository/git/ref/heads/main" \
  --jq .object.sha)" = "$archive_main_sha"

task6_workflow_json="$(task6_gh api \
  "repos/$canonical_generator_repository/actions/workflows/hub-pages.yml")"
task6_workflow_id="$(/usr/bin/jq -er \
  '.id | select(type == "number" and . > 0 and floor == .) | tostring' \
  <<<"$task6_workflow_json")"
expected_workflow_url="https://api.github.com/repos/$canonical_generator_repository/actions/workflows/$task6_workflow_id"
/usr/bin/jq -e \
  --argjson workflow_id "$task6_workflow_id" \
  --arg workflow_url "$expected_workflow_url" '
    .id == $workflow_id
    and .name == "Publish Wirtelprimpf hub Pages"
    and .path == ".github/workflows/hub-pages.yml"
    and .state == "active"
    and .url == $workflow_url
  ' <<<"$task6_workflow_json" >/dev/null

expected_display_title="Wirtelprimpf hub · ${active_repository}@${archive_main_sha}"
task6_dispatch_endpoint=repos/H234598/Wirtelprimpf-generator/actions/workflows/hub-pages.yml/dispatches
task6_dispatch_payload="$(/usr/bin/jq -n \
  --arg active_repository "$active_repository" \
  --arg archive_main_sha "$archive_main_sha" \
  --arg current_volume "$current_volume" '
    {
      "ref": "main",
      "inputs": {
        "active_repository": $active_repository,
        "archive_ref": $archive_main_sha,
        "current_volume": $current_volume
      },
      "return_run_details": true
    }
  ')"
task6_dispatch_response="$(
  printf '%s\n' "$task6_dispatch_payload" |
    task6_gh api -X POST \
      -H 'Accept: application/vnd.github+json' \
      -H 'X-GitHub-Api-Version: 2026-03-10' \
      "$task6_dispatch_endpoint" \
      --input -
)"

hub_run_id="$(/usr/bin/jq -er \
  '.workflow_run_id |
   select(type == "number" and . > 0 and floor == .) | tostring' \
  <<<"$task6_dispatch_response")"
[[ "$hub_run_id" =~ ^[1-9][0-9]{0,19}$ ]]
expected_run_url="https://api.github.com/repos/$canonical_generator_repository/actions/runs/$hub_run_id"
expected_run_html_url="https://github.com/$canonical_generator_repository/actions/runs/$hub_run_id"
/usr/bin/jq -e \
  --argjson run_id "$hub_run_id" \
  --arg run_url "$expected_run_url" \
  --arg html_url "$expected_run_html_url" '
    .workflow_run_id == $run_id
    and .run_url == $run_url
    and .html_url == $html_url
  ' <<<"$task6_dispatch_response" >/dev/null

verify_hub_run_identity() {
  local attempt task6_run_json
  for attempt in $(seq 1 24); do
    if task6_run_json="$(task6_gh api \
      "repos/$canonical_generator_repository/actions/runs/$hub_run_id")"; then
      /usr/bin/jq -e \
        --argjson run_id "$hub_run_id" \
        --arg generator_main_sha "$generator_main_sha" \
        --arg display_title "$expected_display_title" \
        --arg repo_id "$canonical_generator_repo_id" \
        --arg repository "$canonical_generator_repository" \
        --arg workflow_url "$expected_workflow_url" '
          .id == $run_id
          and .event == "workflow_dispatch"
          and .head_branch == "main"
          and .head_sha == $generator_main_sha
          and .display_title == $display_title
          and .name == "Publish Wirtelprimpf hub Pages"
          and .path == ".github/workflows/hub-pages.yml"
          and .workflow_url == $workflow_url
          and .repository.node_id == $repo_id
          and .repository.full_name == $repository
        ' <<<"$task6_run_json" >/dev/null
      return
    fi
    sleep 5
  done
  return 1
}

verify_hub_run_identity
task6_gh run watch "$hub_run_id" \
  --repo "$canonical_generator_repository" --exit-status
task6_cleanup
trap - EXIT
```

Expected: an unprivileged, token-free local probe derives the live persisted
current story and archive index, proves both local `refs/heads/main` values equal
their respective `refs/remotes/origin/main`, and returns only bounded literals.
Root independently binds those SHAs to GitHub's exact repositories and remote
`main` refs. The API-versioned dispatch returns its own run ID atomically; that
exact run must match the requested generator SHA, archive SHA, repository,
workflow, event, branch, and display title before it may be watched. Source
resolution, exact archive checkout, build, validation, upload, and deploy then
succeed. If the active archive is no longer `0001`, stop and revise Task 5 for
that already-existing active repository; never create a repository here.

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
  Required-Treffer: `Publikationsarchiv 0001` 1, `Im Release` 6, das Suffix
  `archiviert.` 6 und Statussatz 1. Alle sieben ausgeführten Forbidden-Scans,
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

### 2026-08-02 — Additive GitHub-Runner-Portabilitätskorrektur

- Diese Ergänzung basiert exakt auf Parent
  `9b23708d4f77031a52acd48f7438a48e1163725e` und ersetzt oder kürzt keine
  frühere Ledgerpassage. Die öffentlichen CI-Metadaten zeigen in Run
  `30734454711` die Jobs `web` `91460584201` und `platform` `91460584216`
  erfolgreich, während ausschließlich `applet` `91460584205` fehlschlug. In
  Run `30734455745` waren `platform` `91460588663` und `web` `91460588664`
  erfolgreich; ausschließlich `applet` `91460588635` schlug identisch fehl.
- Die erste Ursache lag nur im Vertragstest: GitHub-hosted Runner laufen als
  nichtprivilegierte UID/GID ungleich `1000:1000`, während der extrahierte
  Produktionsguard korrekt `1000:1000:600` fordert. Der Test konnte seine
  Fixture nur als Root auf 1000:1000 setzen. Der Produktionsliteral bleibt
  unverändert und wird separat exakt gebunden. Ausschließlich bei nonroot und
  einer effektiven Fixture-Identität ungleich `1000:1000` ersetzt der Harness
  diesen einen Literal in seiner Testkopie einmal durch die tatsächliche
  Fixture-UID/GID; Root und UID/GID 1000 führen weiter den echten Guard aus.
- Die zweite Ursache war die im ausgeführten Step-6-Content-Gate hart
  vorausgesetzte Datei `/usr/bin/rg`, die auf dem Ubuntu-Runner nicht
  vorhanden war. Nur die vier Textprüfungen dieses Blocks verwenden nun
  `/usr/bin/grep`: `-Ec` für je exakt eine Uses- und Factory-Pinzeile, `-Eo`
  für genau die beiden identischen 40-Hex-Werte und `-Eq` für die
  `pull_request`-Triggererkennung. Ein-Datei-Diff, exakt `2\t2`, Pin-, SHA-
  und Triggersemantik bleiben unverändert; es wird kein CI-Paket installiert.
- RED/GREEN-Evidenz: Der unveränderte Receipt-Test reproduzierte unter
  UID/GID `65534:65534` zunächst Returncode 1 mit leerem stderr. Der neue
  Werkzeugvertrag lief an den vier `rg`-Referenzen rot. Danach bestanden
  Receipt-, Werkzeug- und vollständiger Content-Gate-Vertrag lokal `3/3` und
  unter derselben synthetischen Runner-UID/GID erneut `3/3`. Der vollständige
  Rolloutvertrag bestand `45/45` mit zwei erwarteten Root-Skips; die beiden
  rootgebundenen Runuser-Probes bestanden separat `2/2`.
- Außer einem anonymen read-only Abruf der öffentlichen Run-/Jobmetadaten gab
  es keinen Netzwerkzugriff. Es erfolgten kein Credentialzugriff, Push,
  PR-Write, Merge, Install, Reload, Runtime-, Archiv-, Service-, Pages-, DNS-,
  Cloudflare- oder Upstream-Write; schreibende Proben blieben lokal und
  disposable.

### 2026-08-02 — Additive gh-2.92-PR-Ermittlungskorrektur nach sicherem Step-5-Abbruch

- Diese Ergänzung basiert exakt auf Parent
  `beb3371ea2f8766125138c6b8d547952f15e0472` und lässt sämtliche früheren
  Plan- und Evidenzabschnitte unverändert. Der reale normative Task-3-Step-5-
  Lauf endete bei sauberem Worktree, Remote-Main
  `b00d824adee47341e3251bc18e09239fde1c5939`, Remote-Feature
  `beb3371ea2f8766125138c6b8d547952f15e0472` sowie fehlendem Receipt und
  Receiptverzeichnis vor Receipt-Erzeugung, `commit-tree` und jedem
  Remote-Write.
- Ursache war ausschließlich die implizite PR-Auflösung: GitHub CLI 2.92.0
  akzeptiert bei explizitem `--repo` keinen argumentlosen `pr view`-Aufruf
  und brach mit `argument required when using the --repo flag` ab. Der Audit
  aller normativen Task-3-/Task-5-Views fand genau diese eine argumentlose
  Stelle; alle übrigen Views waren bereits an eine explizite PR-Nummer
  gebunden.
- Bei absentem Receipt ermittelt Step 5 den PR nun generisch mit
  `pr list --state open --base main --head "$generator_head" --limit 2`.
  Der Rückgabewert muss ein Array mit exakt einem Kandidaten und einer
  positiven ganzzahligen Nummer sein. Das bestehende
  `assert_pr_identity` bindet diesen Kandidaten zusätzlich an den erwarteten
  Head-SHA, `main`, Non-Draft, Same-Repository, die feste Repository-ID
  `R_kgDOTpr2BA`, den kanonischen Repositorynamen und Owner `H234598`.
  Erst danach folgt der weiterhin nummerierte View samt erneuter
  Identity-Prüfung. Keine PR-Nummer ist hart codiert; null, mehrere,
  fehlgeformte oder identityfremde Kandidaten brechen geschlossen ab.
- RED reproduzierte den echten CLI-Vertrag zweifach: Der Strukturtest fand die
  argumentlose Form, und der ausgeführte unveränderte Step-5-Ausschnitt endete
  im strikten gh-Stub mit Returncode 2 und exakt derselben Fehlermeldung.
  GREEN bestanden beide fokussierten Verträge `2/2`; der Stub akzeptiert nur
  den exakten List- und nummerierten View-Aufruf und weist null Kandidaten,
  zwei Kandidaten sowie einen Kandidaten mit falschem Head zurück.
- Der vollständige Rolloutvertrag bestand als `teladi` `48/48` mit genau
  zwei erwarteten Root-Skips. `make check` bestand frisch unter
  `teladi`/`env -i`: Applet-Runtime grün, Admin-UI `31/31`, SemVer
  `8/8`, Git-Object-Fallback `3/3`, Release-Publication `3/3`,
  Helper-Environment `7/7`, Applet-Sync `28/28`, Settings-Schema
  `15/15`, Story-Directives `31/31` und Rolloutvertrag `48/48` mit den
  zwei erwarteten Root-Skips.
- Diese Runde führte keinen Credentialzugriff, Fetch, Push, PR-Write, Merge,
  Install, Reload, Deploy, Runtime-, Service-, Applet-, Archiv-, Pages-, DNS-,
  Cloudflare- oder Upstream-Write aus. Der gh-Vertrag wurde ausschließlich
  durch lokale Hilfe und einen kontrollierten ausführbaren Stub geprüft; alle
  schreibenden Proben blieben disposable und lokal.

### 2026-08-02 — Additive d4-Vollreview-Schließung und Dispatchbindung

- Diese Schicht basiert exakt auf Parent
  `d4a2938672d27a35a3b20dbf16e4c6bdbf4283f0`. Sie ersetzt, kürzt oder
  korrigiert keinen älteren Ledgerabschnitt. Der Arbeitsumfang folgte zunächst
  einer vorläufigen technischen Arbeitsliste mit 19 Maßnahmen und zwölf
  Nacharbeiten; die verbindliche Reviewtaxonomie und Endbilanz stehen weiter
  unten.
- Vorläufige technische Arbeitsliste (19): A01 bindet Origin-Scheme, Host und den effektiven
  Port exakt; A02 schließt die Verbindung nach `413`; A03 begrenzt bereits die
  geerbte HTTP-Requestline; A04 redigiert unerwartete `500`-/`503`-Antworten;
  A05 akzeptiert Environmentwerte nur als null oder genau ein Shellwort; A06
  entfernt fehlgeschlagene atomare `.part`-Dateien; A07 hält ausschließlich
  die aus der Umgebung abgeleitete GitHub-Auth-Anwesenheit aus der Revision;
  A08 begrenzt Validator-stdout streamend auf 64 KiB und beendet den Prozess
  bei Überschreitung; A09 behandelt unerwartete `flock`-Fehler redigiert und
  entsperrt keinen nie erworbenen Lock; A10 begrenzt und dekodiert CLI-stdin
  bytegenau; A11 trennt unerwartete Settingsfehler mit Exit 7 von
  Rollbackfehlern mit Exit 6; A12 leitet alle Statuspfade aus denselben
  `SettingsPaths` ab und hält Story-, Archiv-, Hub- und Katalogzugriffe in der
  redigierenden Quellgrenze; A13 validiert Archiv-Releasetags strikt und
  erkennt finalen Zustandsdrift; A14 erlaubt im Runtime-Checkout nur die exakt
  bekannte lokale Git-Konfiguration und den kanonischen Main-Refspec; A15
  schließt die systemd-Auto-Restart-Race mit `--job-mode=fail` sowie
  nachgewiesenem Runtime-Maskenzustand; A16 ersetzt den Archivworkflow nur über
  verankerte, eigentums- und identitätsgeprüfte Verzeichnisdeskriptoren; A17
  bindet den Hub-Dispatch atomar über GitHub API `2026-03-10` und
  `return_run_details:true` an genau den zurückgegebenen Run; A18 beginnt den
  Copy-Commit mit leerem Index und staged exakt fünf deklarierte Pfade; A19
  wurde als bereits korrekt behandelter Hinweis klassifiziert und durch den
  Regressionstest belegt: ein persistierter Integer außerhalb des Bereichs
  fällt schon auf Default plus Warnung zurück und benötigt keine
  Produktionsänderung.
- Vorläufige technische Nacharbeitsliste (12): N01 ergänzt den Slow-Drip-Join-Test; N02 prüft
  tatsächlich emittierte Security-Header; N03 macht Bild- und Storymodelle
  schemaweit zu offenen Dropdown-Auswahlen; N04 dokumentiert Secrets als
  write-only Ersetzen/Löschen ohne Klartext-Readback; N05 ruft der lokale
  Installer den Settings-Wrapper aus exakt der Ziel-Venv auf; N06 verwendet
  die gemeinsame `STORIES_PER_BOOK`-Konstante; N07 beweist der Statuscollector
  die exakten Managerpfade; N08 liegt die Angreiferfixture ausschließlich im
  temporären Testverzeichnis; N09 laufen alle Git-Fixtures des Rolloutvertrags
  über einen gemeinsamen absoluten, `env -i`-äquivalent isolierten und auf 15
  Sekunden begrenzten Helper; N10 besitzt der echte Rollback-Signaltest je eine
  frische Armierungs- und Recovery-Deadline sowie garantierte Kill-/Wait-
  Bereinigung im `finally`; N11 ist der verbleibende MD038-Leerraum im
  Inline-Code entfernt; N12 erläutert die additive `open_choices`-Semantik in
  der Spezifikation, ohne historische Aufzählungen zu streichen.
- Zusätzlich materialisiert Task 5 den bestätigten Archiv-Merge vor der
  Pages-Auswahl in einem sauberen, tokenfreien `teladi`-Kind: kanonischer
  HTTPS-Fetch, Fast-forward auf lokalen `main`, danach müssen
  `refs/heads/main` und `refs/remotes/origin/main` beide exakt dem beobachteten
  Merge-SHA entsprechen. Task 6 verwendet ausschließlich diese benannten
  Main-Refs und niemals den Feature-`HEAD`; fehlende lokale Synchronität bricht
  deshalb bewusst fail-closed ab.
- Die fokussierten Task-6- und Task-5-Verträge wurden vor der jeweiligen
  Planänderung rot ausgeführt. Der Task-6-Vertrag bestand danach `1/1`; die
  vollständige Verifikationsbilanz wird nach dem frischen Gesamtlauf additiv
  unterhalb dieses Abschnitts ergänzt.
- Bis zu diesem Ledgerstand wurden keine Rolloutanweisungen ausgeführt: kein
  Credentialzugriff, Fetch, Push, PR-/Merge-Write, Install, Reload, Deploy,
  Runtime-, Service-, Applet-, Archiv-, Pages-, DNS-, Cloudflare- oder
  Upstream-Write. Schreibende Proben blieben in temporären lokalen Dateien und
  Repositories.
- Frische Vertragsverifikation nach Schließung des Task-5-Main-Gates: Der
  vollständige Rolloutvertrag entdeckte 55 Tests und endete in 5,495 Sekunden
  mit `OK`; 54 wurden grün ausgeführt, genau die eine erwartete reale
  Root-/`runuser`-Probe wurde im `teladi`-Gesamtlauf übersprungen. Es gab null
  Failures und null Errors.

#### Finale Reviewklassifikation und Verifikationsbilanz

- Die verbindliche Taxonomie aus Review `4837716445` umfasst zwölf originale
  Inline-Befunde der Stufe Major/Critical, zehn Minor und 19 Nitpicks, insgesamt
  41 Punkte. Dieses Ledger erfindet dafür bewusst keine neuen `MAJ-*`- oder
  `MIN-*`-Zuordnungen: maßgeblich bleiben die ursprünglichen Reviewerpositionen.
  Endstatus über alle 41 Punkte: 39 umgesetzt, ein durch Regressionstest
  belegtes False Positive, ein Reviewvorschlag wegen einer höherrangigen
  exakten Nutzervorgabe bewusst verworfen, null unbeabsichtigt offen und null
  technisch zurückgestellt.
- Das False Positive ist der numerische Admin-/Persistenzhinweis: Ein
  persistierter Integer außerhalb seines erlaubten Bereichs fiel bereits vor
  dieser Runde auf den Defaultwert zurück und erzeugte eine Warnung. Der neue
  Test hält genau dieses bestehende Verhalten fest; eine zusätzliche
  Produktionsänderung wäre redundant gewesen.
- Bewusst nicht umgesetzt wurde ausschließlich die vorgeschlagene Entfernung
  des Kommas aus dem Statussatz. Der vom Nutzer wörtlich vorgegebene Vertrag
  lautet `Dass er unbedeutend ist, und nichts weiß.` und behält deshalb das
  Komma. Das ist weder ein vergessenes Finding noch ein technischer Deferred,
  sondern die dokumentierte Auflösung eines Konflikts zugunsten der
  höherrangigen exakten Nutzervorgabe.
- Die SemVer-Prämisse des betreffenden Reviewerhinweises traf den realen
  Releasevertrag nicht zu. Unabhängig davon wurde der tatsächlich verwendete
  Archivtagparser numerisch, bereichsgebunden und auf das exakte reale
  Tagformat gehärtet. Diese Härtung bestätigt nicht nachträglich die falsche
  Prämisse, sondern schließt den realen Robustheitspfad.
- Die 39 umgesetzten Punkte decken nach ihren ursprünglichen Reviewerpositionen
  insbesondere HTTP-Grenzen und Redaktion, transaktionale Settingsrevisionen,
  Locking, Validator-Prozessgrenzen, CLI/Applet-Fehlersemantik, Statusquellen,
  schemaweite Modelldropdowns, systemd-Race-Gates, Runtime- und Archiv-Git-
  Allowlisten, descriptorverankerte Workflow-Ersetzung, atomare
  Dispatch-Run-Bindung, Testprozessbereinigung, Dokumentation und
  Verpackungspfade ab. Diese technische Zusammenfassung ist keine
  Umklassifizierung der zwölf originalen Inline-Befunde.
- Die Exit-7-Regressionsprobe lief vor der Appletänderung gezielt rot und danach
  `1/1` grün; die vollständige Applet-Synchronisation bestand `28/28`. Die
  gemeinsame Matrix der geänderten Plattformkomponenten entdeckte 152 Tests:
  151 wurden grün ausgeführt, genau eine reale Root-Probe erwartungsgemäß
  übersprungen. Der abschließende
  `make check` endete mit Exit 0: Applet-Runtime grün, Admin-UI `31/31`, SemVer
  `8/8`, Git-Object-Fallback `3/3`, Release-Publication `3/3`, Helper-Environment
  `7/7`, Applet-Sync `28/28`, Settings-Schema `15/15`, Story-Directives `31/31`
  und Rolloutvertrag 56 entdeckt, 55 grün ausgeführt, ein erwarteter
  Root-/`runuser`-Skip, null Failures und null Errors.
- Alle sechs geänderten ausführbaren Planblöcke bestanden separat `bash -n`
  und ShellCheck auf Error-Severity. Ruff meldete für sämtliche geänderten
  Pythonpfade „All checks passed“; Bandit High endete mit Exit 0. Auch diese
  Abschlussrunde blieb ohne Credentialzugriff und ohne Netzwerk-, System-,
  Runtime-, Installations-, Deployment-, DNS-, Cloudflare- oder Upstream-Write.
- Der erste strikt als `teladi` ausgeführte Commitversuch stoppte noch vor
  einem Indexupdate, weil das gemeinsame Git-Objektverzeichnis das Einfügen
  eines Objekts verweigerte. Der Read-only-Befund zeigte den Worktree weiterhin
  vollständig als `1000:1000`, Index 0, 20 geplante Modifikationen und null
  ungetrackte Pfade; fremd waren ausschließlich Einträge unter dem gemeinsamen
  Git-Metadatenpfad. Die anschließende begrenzte Infrastrukturreparatur prüfte
  dort exakt 45/45 Einträge als `root:root` und null Symlinks und änderte nur
  diese vorab aufgelisteten Pfade, nichtrekursiv, ohne Dereferenzierung und nur
  bei weiterhin passendem Ausgangseigentümer `0:0`, auf `1000:1000`. Danach
  verblieben im gemeinsamen Gitdir und im Featureworktree jeweils null fremde
  Einträge; staged blieb 0, modified 20, untracked 0. Es gab kein `chown` auf
  Projekt-, Runtime-, Archiv- oder Nutzdaten und weiterhin keinen Push.

### 2026-08-02 — Additive REST-/GraphQL-Botidentitätsbindung für Receipt v3

- Diese Follow-up-Schicht basiert exakt auf
  `d96ac7d40a2216ecc27596db328c78b54b011390`. Der normative Task-3-Step-5-
  Lauf war vor Receipt-Erzeugung, Mergeable-Commit und jedem Remote-Write
  geschlossen abgebrochen: Der REST-Abruf des CodeRabbit-Actors lieferte
  `coderabbitai[bot]`, die GraphQL-Reviewkante für denselben Bot dagegen den
  normalisierten Login `coderabbitai`. Das alte Candidate-Filter verlangte
  fälschlich auch in GraphQL den REST-Login und erzeugte deshalb eine leere
  Kandidatenliste.
- Der read-only Livebeleg bindet beide API-Repräsentationen stabil. REST
  `/users/coderabbitai%5Bbot%5D` liefert Login `coderabbitai[bot]` und
  numerische ID `136622811`. GraphQL liefert für den Reviewauthor
  `__typename=Bot`, Login `coderabbitai`, `databaseId=136622811`, Node-ID
  `BOT_kgDOCCSy2w` und URL `https://github.com/apps/coderabbitai`. Die auf
  Parent `d96ac7d` freigebende Review-ID ist `4837973683`.
- Die paginierte Reviewquery fordert nun `__typename`, Actor-Login, Node-ID,
  URL und für `Bot` zusätzlich `databaseId` an. Ein Approvalkandidat muss auf
  dem unveränderten erwarteten Head liegen und gleichzeitig exakt Typ `Bot`,
  GraphQL-Login `coderabbitai`, die mit REST übereinstimmende numerische ID
  `136622811`, Node-ID `BOT_kgDOCCSy2w` und die feste App-URL besitzen. Der
  separate REST-Gate verlangt weiterhin exakt `coderabbitai[bot]` und
  `136622811`. Erst die Gleichheit der REST-ID mit GraphQL-`databaseId`
  autorisiert den Kandidaten.
- Receipt v3 bleibt schema- und konsumkompatibel: `review_author_login` wird
  weiterhin aus dem exakt geprüften REST-Actor als `coderabbitai[bot]`
  geschrieben, `review_author_id` bleibt `136622811`; Review-ID, Commit und
  `APPROVED` werden unverändert gebunden. Es gibt keine schwache
  Stringnormalisierung und keinen Fallback auf einen lediglich gleichnamigen
  Actor.
- TDD-Evidenz: Der neue Realitätsvertrag modellierte zuerst den echten
  REST-/GraphQL-Unterschied und lief am alten Gate rot, weil `__typename` und
  die stabile Botidentität fehlten. GREEN akzeptiert exakt den belegten Bot
  und verwirft separat eine fremde REST-ID, einen falschen REST-Login, einen
  gleichnamigen Bot mit fremder `databaseId`, einen gleichnamigen User, eine
  fremde Bot-Node-ID und eine fremde App-URL. Der Fokuslauf bestand `1/1`; der
  vollständige Rolloutvertrag entdeckte 56 Tests, führte 55 grün aus und
  übersprang genau die bekannte reale Root-/`runuser`-Probe.
- `make check` endete mit Exit 0: Applet-Runtime grün, Admin-UI `31/31`, SemVer
  `8/8`, Git-Object-Fallback `3/3`, Release-Publication `3/3`,
  Helper-Environment `7/7`, Applet-Sync `28/28`, Settings-Schema `15/15`,
  Story-Directives `31/31` und Rolloutvertrag erneut 55 grün plus ein
  erwarteter Skip. Ruff meldete „All checks passed“, Bandit High endete mit
  Exit 0, und der geänderte normative Task-3-Step-5-Block bestand `bash -n`
  sowie ShellCheck auf Error-Severity.
- Dieser Follow-up führte keinen Receipt-, Fetch-, Push-, PR-, Merge-,
  Installations-, Runtime-, Service-, Applet-, Archiv-, Pages-, DNS-,
  Cloudflare- oder Upstream-Write aus. Der einzige externe Befund war die
  ausdrücklich read-only erhobene API-Identität; sämtliche schreibenden
  Testfixtures blieben lokal und disposable.

### 2026-08-02 — Additive GraphQL-Actor-Schemakorrektur für den Reviewgate

- Diese zweite Follow-up-Schicht basiert exakt auf
  `3cb67c72db02dc42f8095a61cbba0386f61264ea`. Die root-authentifizierte,
  read-only ausgeführte Liveprobe des dort festgeschriebenen Querys brach mit
  `Field 'id' doesn't exist on type 'Actor'` bereits an der GitHub-GraphQL-
  Schemavalidierung ab. Es entstanden weder Receipt noch Remote-Write. Damit
  bleibt die zuvor dokumentierte REST-/GraphQL-Loginnormalisierung richtig;
  ausschließlich die Platzierung der botspezifischen GraphQL-Felder war noch
  ungültig.
- Der fehlerhafte Selektor
  `author{__typename login id url ... on Bot{databaseId}}` fragte Node-ID und
  URL auf der statischen `Actor`-Ebene ab. Die separat bereits erfolgreich
  gegen das reale Schema ausgeführte Form und nun normative Query lautet exakt
  `author{__typename login ... on Bot{id databaseId url}}`: Nur
  `__typename` und `login` bleiben auf `Actor`; Node-ID, numerische
  `databaseId` und App-URL werden ausschließlich im `Bot`-Fragment angefordert.
  Candidate-Filter, REST-ID-Kreuzbindung und Receipt-v3-Felder bleiben
  unverändert fail-closed.
- Der Vertragsregressionstest extrahiert jetzt den Author-Selektor aus
  `fetch_task3_reviews_page`, verlangt auf Actor-Ebene exakt
  `__typename login`, im Bot-Fragment exakt `id databaseId url` und genau
  einen Author-Selektor. RED zeigte am Parent explizit die unerlaubte
  Actor-Feldliste `['__typename', 'login', 'id', 'url']`; nach der
  Querykorrektur lief derselbe fokussierte Test `1/1` grün.
- Die vollständige `make check`-Matrix endete anschließend mit Exit 0:
  Applet-Runtime grün, Admin-UI `31/31`, SemVer `8/8`, Git-Object-Fallback
  `3/3`, Release-Publication `3/3`, Helper-Environment `7/7`, Applet-Sync
  `28/28`, Settings-Schema `15/15`, Story-Directives `31/31` und
  Rolloutvertrag 56 entdeckt, 55 grün ausgeführt sowie genau ein erwarteter
  Root-/`runuser`-Skip. Ruff und Bandit High endeten ohne Befund; der
  vollständige normative Task-3-Step-5-Block bestand `bash -n` und ShellCheck
  auf Error-Severity.
- Auch diese Korrektur führte keinen Receipt-, Fetch-, Push-, PR-, Merge-,
  Installations-, Runtime-, Service-, Applet-, Archiv-, Pages-, DNS-,
  Cloudflare- oder Upstream-Write aus. Die Tests verwendeten ausschließlich
  lokale, disposable Fixtures; die abschließende Liveprobe des korrigierten
  Querys bleibt dem getrennten root-authentifizierten Read-only-Lauf
  vorbehalten.

### 2026-08-02 — Additive Reviewgate-, Quiesce- und Step-10-CAS-Schließung

- Diese Ergänzung basiert exakt auf Parent
  `0007091f7482ae9657fb5c207d31628351ee58dc` und schließt die Rolloutanteile
  von CodeRabbit-Review `4838065930`, ohne ältere Belege zu ersetzen. Die
  vollständige Reviewseite und sämtliche Inline-Threads wurden gelesen.
- Die paginierte Reviewvalidierung verlangt `id`, `databaseId` und `url` nur
  noch für `__typename=Bot`, genau wie die normative GraphQL-Query. Ein
  gewöhnlicher `User` mit ausschließlich `__typename` und `login` ist deshalb
  ein gültiger Nichtkandidat; der einzig autorisierende CodeRabbit-Bot bleibt
  weiterhin strikt an Login, REST-ID, GraphQL-ID, Node-ID, App-URL, Approval
  und den exakten Head gebunden.
- `assert_canonical_origin` verwendet einen eigenen vollständig geleerten
  Prozesskontext mit deaktivierter System- und Global-Gitkonfiguration. Der
  ausführbare Vertrag bestand auch mit einer absichtlich vergifteten globalen
  `url.*.insteadOf`-Fixture und weist weiterhin zusätzliche Push-URLs zurück.
- `fail_closed_runtime` stoppt nach einem fehlgeschlagenen ersten
  Inaktivitätsnachweis gezielt den Generator, wiederholt den Nachweis und
  versucht danach die Runtime-Maske; der Rückgabestatus bleibt fehlgeschlagen.
  Der Step-10-Harness commitet das Target detached vom alten Commit, lässt
  `main` bis nach Lock-, Ancestry- und Old-main-Beweisen unverändert und führt
  erst dann die korrekte Old→Target-CAS aus. Die inverse vorbereitende
  `update-ref`-Operation ist entfernt.
- Der Rolloutvertrag bestand abschließend 58 entdeckt, 57 grün und ein
  erwarteter realer Root-Skip. Die vollständigen Step-5-, Step-9- und
  Step-10-Blöcke bestanden separat `bash -n` und ShellCheck auf
  Error-Severity. Sämtliche Proben blieben lokale disposable Fixtures; es gab
  keine Git-Remote-, Receipt-, Runtime-, Installations-, DNS-, Cloudflare- oder
  Upstream-Writes. Der Remediation-Agent las das öffentliche Review anonym;
  die Root-Reconciliation von PR und Threads verwendete den bereits vorhandenen
  authentifizierten `gh`-Kontext nur lesend. Kein Token wurde ausgegeben,
  exportiert oder neu gespeichert. Der unabhängige Root-Critical-Audit bestand
  zusätzlich mit 169 Python-Tests (168 grün, ein erwarteter Skip), Admin
  `33/33`, `git diff --check`, Ruff für alle geänderten
  Nichtbaseline-Pythonpfade und Bandit High ohne High-Finding.

### 2026-08-02 — Additive PR-4-CLOSED-Reconciliation und transaktionales 84-Pfad-Ownership-Gate

- Diese ausschließlich lokale Härtung beginnt auf dem exakten Generator-
  `main`-Merge `274b25c9e1f9ea97d3b060997ed5c425d2b30e9f` im neuen Branch
  `agent/pr4-closed-merge-reconcile`. Sie führt keinen Schritt des
  Rolloutplans aus und verändert weder GitHub noch Receipt, Runtime, Services,
  Applet, Archiv, Pages, DNS, Cloudflare oder Cinnamon-Upstream.
- PR 4 erhält keinen allgemeinen `CLOSED => verified`-Fallback, sondern einen
  einmaligen hart gebundenen Reconcilezweig. Er akzeptiert ausschließlich das
  vorhandene v3-Receipt im Zustand `remote_committed` oder `verified`, den
  exakten Main-Merge `274b25c9…`, Base `b00d824…`, Head `5aab1907…`, Baum
  `967a0b41…`, die geordneten Eltern, PR 4, Repository-ID, Actor-ID und das
  aktuelle CodeRabbit-Approval `4838199265` ohne offenen Thread.
- Jeder Reconcilelauf erhebt alle autorisierenden Informationen frisch:
  authentifizierter Actor, kanonisches Repository, beide Remote-Refs,
  GraphQL-PR, vollständige relevante paginierte Timeline, REST-PR, Compare-
  Ergebnis, unveränderliches Git-Commitobjekt und aktuelle Reviewkante. Der
  ungewöhnliche Livevertrag bindet GraphQL an `CLOSED`, `merged=false`,
  `mergeCommit=null`, `viewerCanReopen=false`, REST jedoch zusätzlich an den
  von GitHub gelieferten hypothetischen `merge_commit_sha`
  `01df605da0cd39f5bbcddfd2ebc9837d74f3f375`, `mergeable=true` und
  `mergeable_state=clean`.
- Der bereits genau einmal abgelehnte `PATCH state=open` ist als
  maschinenlesbarer Beleg
  `docs/superpowers/evidence/2026-08-02-pr4-reopen-422.json` mit Git-Blob
  `769dac62c3d3fa734945de5e83af4444fad1b9b3` versioniert. Request,
  HTTP-422-Fehlertupel und Objektbindung werden geprüft; der Request wird im
  Recoveryblock niemals wiederholt.
- Nur die vollständige Konjunktion darf `remote_committed -> verified`
  schreiben. Vor der anschließenden Bereinigung wird die gesamte Livebindung
  nochmals vollständig erhoben. Der einzige dort zulässige Remote-Write ist
  die exakte Lease-Löschung des restaurierten Feature-Refs; der Block enthält
  weder einen Main-Refspec noch `--atomic`, PR-State-Write oder irgendeinen
  Pfad zurück zum Main-Push. Ein Retry mit bereits fehlendem Feature-Ref ist
  ausschließlich beobachtend; jede andere Kombination bricht fail-closed ab.
- Das veraltete Ownership-Snapshot mit 450 Positionen autorisiert keinen
  Write mehr. Der neue Task-4-Vertrag bindet die aktuell read-only bestätigten
  84 `root:root`-Positionen als unveränderliche Pfad-/Typ-Allowlist mit
  SHA-256 `713307aef872976278c81ef74dd7ddf635767e7e4bbb3441941db2e17b2dc368`.
  Es gibt keinen Rebuild- oder Auditmodus, der diese Liste bei Drift ersetzt.
  Fremde Symlinks, Special Files, Submounts, zusätzliche/fehlende Positionen,
  abweichende Eigentümer und mehrfach verlinkte reguläre Dateien stoppen vor
  dem ersten Write; bereits korrekte venv-Symlinks werden nicht verfolgt oder
  verändert.
- Nach der vollständigen Vorprüfung öffnet Root jeden Zielpfad ausschließlich
  komponentenweise relativ zu einem kanonischen Directory-FD mit
  `O_NOFOLLOW`. Device, Inode, Typ, Linkzahl, UID und GID werden am offenen FD
  sofort, erneut nach vollständigem Binden und unmittelbar vor jedem
  `fchown` verglichen. Scheitert ein Write oder die Postcondition, werden alle
  bereits geänderten FDs in umgekehrter Reihenfolge auf `root:root`
  zurückgesetzt und verifiziert; ein unvollständiger Rollback ist ein eigener
  harter Fehler. Es gibt weder rekursiven/pfadbasierten `chown` noch
  `safe.directory`.
- TDD begann mit sieben fokussierten Verträgen: ein echter Failure und sechs
  erwartete fehlende Verträge; nach Implementierung bestanden `7/7`. Der
  spätere unabhängige Diffaudit fand die noch nicht unmittelbar am FD
  verglichene Linkzahl. Der neue fokussierte Test lief deshalb nochmals rot
  (`0/1`, `Exception not raised`) und nach Aufnahme von `st_nlink` in das
  Rebindtupel grün (`1/1`). Der vollständige Rolloutvertrag besteht nun aus 64
  Tests: 63 grün, genau ein erwarteter Root-/`runuser`-Skip.
- Die frische Abschlussmatrix unter UID/GID `1000:1000` bestand: Plattform
  `166/166`; `make check` Exit 0 einschließlich Admin `33/33`, Applet-Sync
  `39/39`, Settings-Schema `19/19` und Story-Directives `31/31`; Web `9/9`;
  Astro 0 Fehler, 0 Warnungen, 0 Hinweise. Hub und Archiv validierten jeweils
  823 Dateien, 818 HTML-Dokumente und 10.840 interne Links; ihre Baumhashes
  lauten `0acc6695654d3e82e450a3467d96995da89e59d954d00340d5a5028916ab1bb6`
  und `f6e682fa639f72863f8911bb2b94d416ba83e913613797334361e439308a91bd`.
  Task 3 Step 5 bestand `bash -n` und ShellCheck auf Warning-Level;
  `git diff --check`, JSON-Validierung, Ruff und Bandit High waren ebenfalls
  ohne Befund.

### 2026-08-02 — Additive Interpreter-, Signal- und Wiederanlaufschließung des Ownership-Gates

- Diese ausschließlich lokale Follow-up-Schicht basiert exakt auf
  `b0edc6714deae6032707339da5284818fcac8cd5`. Sie ändert weder den
  PR-4-Reconcilevertrag noch dessen Objektbindungen, sondern schließt zwei im
  unabhängigen Rootaudit verbliebene Grenzen des Task-4-Ownership-Gates.
- Der normative Heredoc wird nun ausschließlich als
  `/usr/bin/python3 -I -` gestartet. Noch vor `hashlib`, `json`, `os`,
  `signal`, `stat`, `pathlib` oder `typing` prüft das Programm selbst
  `sys.flags.isolated == 1` und `sys.flags.safe_path == 1`. Ein realer
  Hostile-CWD-Test mit einer schreibenden `hashlib.py` beweist sowohl für die
  normative Invokation als auch für den absichtlich unisolierten Negativlauf,
  dass das Fremdmodul niemals importiert wird; Invokation und Selbstprüfung
  sind damit gemeinsam regressionsgebunden.
- Die statische 84-Pfad-/Typ-Allowlist ist nun zugleich die einzige
  Recoveryquelle. Jeder Allowlisteintrag muss bei Eintritt exakt entweder
  `0:0` oder `1000:1000` gehören. Alle-Quelle ist der normale Erstlauf,
  Alle-Ziel ein idempotenter Wiederholungslauf und eine Mischung der
  definierte Wiederanlauf nach SIGKILL oder Stromverlust. Mischzustände werden
  ausschließlich zielwärts vervollständigt; ein dritter Besitzer, Pfad-/Typ-
  Drift oder zusätzlicher fremder Pfad stoppt fail-closed. Es gibt weiterhin
  weder Rebuild-/Lernmodus noch rekursiven oder pfadbasierten `chown`.
- Vor dem ersten `fchown` sind alle 84 offenen FDs samt Device, Inode, Typ,
  Linkzahl, Eintritts- und Zielbesitzer registriert. Der Rollback untersucht
  jeden dieser FDs in umgekehrter Reihenfolge: Eintrittsbesitz bleibt
  unverändert, nur `Eintritt=Quelle` plus `aktuell=Ziel` wird exakt auf den
  individuellen Eintrittsbesitzer restauriert; jeder dritte Zustand ergibt
  `rollback INCOMPLETE`, wird gemeldet und nicht überschrieben. Bereits vor dem
  Lauf zielrichtige Einträge werden daher auch bei einem Fehler nie auf Root
  zurückgesetzt.
- HUP, INT und TERM verwenden während der Transaktion einen minimalen
  Flaghandler. Prüfungen vor und unmittelbar nach jedem echten `fchown`, nach
  der Gesamtpostcondition und am unter blockierten Signalen liegenden
  Commitpunkt erzwingen den Rollback. Während des Rollbacks bleiben diese
  Signale blockiert. Ein vollständig behandeltes Signal endet mit
  `128 + Signalnummer` ohne Erfolgsausgabe. Vor dem finalen Entsperren werden
  die vorherigen Handler wiederhergestellt; eine gezielt direkt nach dem
  Pending-Snapshot eingereihte späte TERM-Probe wird deshalb nicht
  verschluckt. SIGKILL bleibt naturgemäß nicht abfangbar und wird durch den
  statischen Mischzustands-Wiederanlauf geschlossen.
- TDD startete mit fünf neuen Fokusverträgen `0/5`: Beide Hostile-CWD-Läufe
  importierten am Parent tatsächlich das Fremdmodul; die drei
  Ownershipverträge scheiterten am noch fehlenden statischen
  Mischzustandscapture. Nach Implementierung und Anpassung der bestehenden
  echten Rollbackprobe bestanden sechs relevante Verträge `6/6`. Der danach
  ergänzte Late-Signal-Test lief zunächst gezielt rot (`0/1`, vorheriger
  TERM-Handler nicht aufgerufen) und nach Schließung des Commitpunkts zusammen
  mit allen Fokusverträgen `7/7` grün.
- Die frische Abschlussmatrix unter UID/GID `1000:1000` bestand: Der
  Rolloutvertrag entdeckte 70 Tests, führte 69 grün aus und übersprang genau
  die bekannte reale Root-/`runuser`-Probe; Plattform `166/166`; vollständiges
  `make check` Exit 0; Web `9/9`; Astro 22 Dateien mit null Fehlern, Warnungen
  oder Hinweisen. Hub und Archiv validierten jeweils 823 Dateien, 818 HTML und
  10.840 interne Links mit den unveränderten Baumhashes
  `0acc6695654d3e82e450a3467d96995da89e59d954d00340d5a5028916ab1bb6`
  und `f6e682fa639f72863f8911bb2b94d416ba83e913613797334361e439308a91bd`.
  Der Ownership-Block bestand `bash -n` sowie ShellCheck auf Error-Severity;
  `git diff --check`, Ruff und Bandit High endeten ohne blockierenden Befund.
- Eine erneute ausschließlich lesende Probe gegen die echte Runtime erfasste
  exakt 84 statische Positionen, denselben Allowlistdigest, ausschließlich
  Eintrittsbesitz `0:0` und 84 erfolgreich descriptorgebundene Objekte. Die
  Writefunktion wurde nicht aufgerufen. Diese Follow-up-Schicht führte keinen
  Push, Fetch, Receipt-, Runtime-, Ownership-, Installations-, Service-,
  Applet-, Archiv-, Pages-, DNS-, Cloudflare- oder Upstream-Write aus und wird
  als eigener lokaler Commit auf dem genannten Parent übergeben.

### 2026-08-02 — Additive Offline-Buildbackend-, Recoveryketten- und Shared-Git-Schließung

- Diese ausschließlich lokale Follow-up-Schicht basiert exakt auf Commit
  `c84d957dee6206774a4d98689726dce38472e4b3` mit Baum
  `b251ed552f7eaf74e18dd0362b9e10db50a3001a`. Sie repariert den bei der
  einmalig freigegebenen Step-9-Ausführung sichtbar gewordenen Fehler im
  Ausführungsplan; sie wiederholt Step 9 nicht und nimmt selbst keinerlei
  Runtime-, Service-, Installations-, Netzwerk-, Git-Remote- oder
  Upstream-Änderung vor.
- Die eindeutige Fehlerursache war der bisherige Aufruf
  `pip --no-build-isolation --no-deps -e`: Die Runtime verwendet Python
  3.14.5 und pip 26.0.1, enthält aber kein importierbares `setuptools`.
  Deshalb schlugen sowohl das Vorwärtsinstallieren als auch der symmetrische
  Rollback mit `BackendUnavailable: Cannot import 'setuptools.build_meta'`
  fehl. Eine getrennte, read-only vorbereitete Probe bestätigte, dass die
  standardmäßige isolierte PEP-517-Buildumgebung funktioniert und die
  Runtime-Venv danach weiterhin kein `setuptools` enthält.
- Step 9 bindet das dafür benötigte Backend nun unveränderlich an
  `setuptools-83.0.0-py3-none-any.whl`, Größe `1008090` Byte, SHA-256
  `29b23c360f22f414dc7336bb39178cc7bcbf6021ed2733cde173f09dba19abb3`
  und die konkrete PyPI-Datei-URL. Die Constraintdatei enthält exakt
  `setuptools==83.0.0` plus LF und ist an SHA-256
  `4723b97f4d3f3c1d817e4896c0f7d59642e326ad891c7037482d2455b8a6bb4c`
  gebunden. Genau ein begrenzter `curl`-Versuch darf das Rad in die private
  Transaktionsablage holen; Größe, Digest, Modus, Eigentümer und atomare
  Hardlink-Publikation werden geprüft. Eine vorhandene korrekte Datei wird
  wiederverwendet, eine vorhandene korrupte Datei wird ohne erneuten Download
  fail-closed zurückgewiesen.
- Vorwärts- und Rückwärtsweg rufen dieselbe Funktion
  `install_editable_offline_bounded` auf. pip erhält die private Cache- und
  Tempablage, `--no-index`, `--find-links`, `--build-constraint`, `--no-deps`
  und `-e`; `--no-build-isolation` ist aus dem normativen Step 9 vollständig
  entfernt. Damit ist nur das einmalig hashgebundene Herunterladen des
  Buildbackends netzabhängig, während Vorwärtsinstallation und Rollback
  ausschließlich aus demselben gebundenen Wheelhouse bauen.
- Der Step-10-Vertrag führt exakt die produktiven Funktionen mit lokalen
  Fakes aus. Er beweist einen einzigen Download trotz zweier Aufrufe, die
  vollständige Offline-Umgebung des pip-Prozesses, die Benutzung der
  Constraintdatei, die Abwesenheit von `--no-build-isolation` und die
  fail-closed Ablehnung einer nachträglich korrupten Wheeldatei ohne zweiten
  Netzversuch. TDD begann mit fünf gezielt roten Verträgen und endete für
  denselben Fokus mit `5/5` grün.
- Die Recoveryquelle ist nicht auf den ersten unterbrochenen Versuch
  verkürzt. `INTERRUPTED_BARRIER_HISTORY` bindet die belegte Kette vom
  historischen Backup `HNkEdc` bis zum aktuellen Backup `f1iePQ`; das
  aktuelle Wurzelobjekt ist an Device `53` und Inode `8256518`, alle acht
  Prestate-Dateien sowie die drei Manifestdateien und deren Digests gebunden.
  Auch das private Payload-Verzeichnis `files` ist an Device `53`, Inode
  `8256538`, Modus `0700` und seine acht direkten Einträge gebunden. Die
  aktuelle Steuerbarriere verwendet die separat belegten Control- und
  Legacy-Symlinks für Service und Timer; jede Lücke, Umordnung oder
  Objektabweichung beendet die Recovery vor einem Write.
- Ein separater transaktionaler FD-Vertrag schloss die während der früheren
  Root-Ausführung entstandenen Eigentumsreste in der gemeinsam genutzten
  Git-Ablage und in diesem Agent-Worktree. Die Shared-Git-Allowlist umfasst
  exakt 16 Objekte mit Inventardigest
  `1567d717e89da2f2acaf88ea1c2d7cba6c7a4e5fa646ab4c3a94f0e008aa8bf0`;
  die Worktree-Allowlist exakt sieben `.pyc`-Objekte mit Digest
  `7c35636e7407ea0ce0edc52010a932e858dc749e0f0a0354fd3debe49ccb361a`.
  Das gemeinsam geprüfte Python-Heredoc einschließlich Abschluss-LF hat
  SHA-256
  `83f47a8a55971aaf72bd1e8fdde73e1a423d1d6e5d2221f763b98c33ed99bf54`.
  Beide Wurzeln werden vollständig vorgebunden, ausschließlich über
  `O_NOFOLLOW`-FDs geändert und bei jedem Fehler wurzelübergreifend in
  umgekehrter Reihenfolge restauriert.
- Transparenz zum Testlauf: Ein zunächst versehentlich als Root gestartetes
  `make check` wurde vor jeder Installations- oder Runtimeoperation sofort
  abgebrochen, hatte aber sechs vorhandene Worktree-Bytecodeobjekte ersetzt;
  zusammen mit einem bereits root-eigenen Rollout-Bytecodeobjekt ergab das
  genau die sieben statisch gebundenen Worktree-Einträge. Der anschließend
  ausdrücklich freigegebene kombinierte 16+7-Handoff lief einmalig und
  erfolgreich. Die unveränderte Runtime-Allowlist blieb dabei strikt
  ausgeschlossen; ihr 84-Pfad-Digest blieb
  `713307aef872976278c81ef74dd7ddf635767e7e4bbb3441941db2e17b2dc368`.
  Read-only Postconditions bestätigten in allen drei Wurzeln ausschließlich
  `teladi:teladi`, unveränderte Inodes und Digests sowie keine zusätzlichen
  fremden Einträge.
- Die frische Abschlussmatrix lief vollständig als UID/GID `1000:1000` mit
  isoliertem Python-Bytecodecache. `make check` endete mit Exit 0: Admin-UI
  `33/33`, SemVer `8/8`, Git-Fallback `3/3`, Release-Publication `3/3`,
  Helper `7/7`, Applet-Sync `39/39`, Settings-Schema `19/19`,
  Story-Directives `31/31` und Rolloutvertrag 81 entdeckt, 80 grün sowie
  genau ein erwarteter Root-/`runuser`-Skip. Die unabhängige Plattformmatrix
  bestand `166/166`; Web `9/9`; Astro prüfte 22 Dateien mit null Fehlern,
  Warnungen oder Hinweisen. Ruff, Bandit High und `git diff --check` waren
  ohne Befund. Ownership-Block, Step 9 und Step 10 bestanden jeweils separat
  `bash -n` und ShellCheck auf Error-Severity; die vollständigen extrahierten
  Step-9- und Step-10-Blöcke einschließlich Abschluss-LF haben SHA-256
  `aa5bd6035abae492348bfbef415089cb956b97fc14155810783eca66dcd8b4b6`
  beziehungsweise
  `f195437936a8e6af65a5c6198b7b75f0cc33c5dd0f707c45c06eaafa2c53c2a0`.
- Diese Schicht führte weder Step 9 noch einen Push, Fetch, Receipt-,
  Runtime-, Installations-, Service-, Applet-, Archiv-, Pages-, DNS-,
  Cloudflare- oder Upstream-Write aus. Sie verändert ausschließlich diesen
  versionierten Plan und seinen ausführbaren Vertragsregressionstest und wird
  als genau ein lokaler Commit unter dem Benutzer `teladi` übergeben.
