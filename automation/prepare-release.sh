#!/usr/bin/env bash
#
# prepare-release.sh — weekly "prepare a release" job for TrinoHub.
#
# What it does, once per run:
#   1. Refreshes a DEDICATED clone of the repo (never your working checkout).
#   2. Decides whether there is anything to release at all. If `main` is not
#      ahead of the latest tag, or `## [Unreleased]` in CHANGELOG.md has no
#      entries, it logs why and exits 0. A SKIPPED WEEK IS SUCCESS.
#   3. Runs Claude Code headless to perform the editorial half of
#      docs/releasing.md: pick the version, bump trinohub/__init__.py and the
#      CloudFormation GitRef, move [Unreleased] under a dated heading, add the
#      compare link, and write an Upgrading section if one is warranted.
#   4. Runs the release gates itself, deterministically, and refuses to propose
#      a release if any of them fail.
#   5. Pushes a `release/vX.Y.Z` branch and opens a **DRAFT** PR containing the
#      exact tag commands for a human to run after merging.
#
# WHAT IT DELIBERATELY DOES NOT DO:
#   - It never creates or pushes a tag. See "Why this stops before tagging" in
#     automation/README.md. Pushing a v* tag publishes a public GitHub Release
#     and a published tag must never be moved or reused.
#   - It never merges anything, and never runs deploy/VALIDATION.md, which
#     creates billable AWS resources.
#   - It never touches trinohub.org. That site is served from a different
#     machine and is not reachable from here; website-visible changes are
#     FLAGGED in the PR body, never attempted.

set -euo pipefail

# ---- Config (override via env or automation/agent.env) --------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="${AGENT_CONFIG:-"$SCRIPT_DIR/agent.env"}"
# shellcheck disable=SC1090
[ -f "$CONFIG_FILE" ] && source "$CONFIG_FILE"
RULES_FILE="${RULES_FILE:-"$SCRIPT_DIR/house-rules.md"}"

REPO="${REPO:?Set REPO=owner/trinohub in agent.env}"
# A SEPARATE clone from the issue agent: both jobs run on Friday and must not
# share a working tree.
WORKDIR="${RELEASE_WORKDIR:-"$HOME/.trinohub-agent/release-checkout"}"
LOGDIR="${LOGDIR:-"$HOME/.trinohub-agent/logs"}"
BASE_BRANCH="${BASE_BRANCH:-main}"
CLAUDE_MODEL="${CLAUDE_MODEL:-}"
RELEASE_VERSION="${RELEASE_VERSION:-}"   # optional explicit override, e.g. 0.4.0
GIT_AUTHOR_NAME_="${GIT_AUTHOR_NAME_:-BitRefinery}"
GIT_AUTHOR_EMAIL_="${GIT_AUTHOR_EMAIL_:-299273308+BitRefinery@users.noreply.github.com}"

# The four files docs/releasing.md names for the syntax gate.
PY_COMPILE_FILES="${PY_COMPILE_FILES:-trinohub/api.py trinohub/server.py trinohub/aws_checks.py trinohub/database.py}"

WORKDIR_ABS="$(readlink -m "$WORKDIR")"
case "$WORKDIR_ABS" in
  "$REPO_ROOT" | "$REPO_ROOT"/*)
    echo "REFUSING TO RUN: WORKDIR ($WORKDIR_ABS) is inside this checkout ($REPO_ROOT)." >&2
    echo "The release job needs a dedicated clone; set RELEASE_WORKDIR outside the repo." >&2
    exit 1
    ;;
esac

mkdir -p "$LOGDIR" "$(dirname "$WORKDIR")"
RUN_LOG="$LOGDIR/release-$(date -u +%Y%m%dT%H%M%SZ).log"
log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$RUN_LOG"; }

require() { command -v "$1" >/dev/null 2>&1 || { echo "Missing dependency: $1" >&2; exit 1; }; }
require gh; require claude; require jq; require git

# `python3 -m venv` needs ensurepip, which Debian/Ubuntu split into a separate
# package. Without it venv creation fails several steps into a run with a wall of
# stderr; check up front and name the fix.
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  echo "Missing ensurepip: 'python3 -m venv' cannot create the clone's venv." >&2
  echo "Install it, e.g.: sudo apt-get install -y python3.14-venv" >&2
  exit 1
fi

if [ ! -f "$RULES_FILE" ]; then
  echo "Missing house rules file: $RULES_FILE" >&2
  exit 1
fi
HOUSE_RULES="$(sed "s|{{REPO}}|$REPO|g" "$RULES_FILE")"

# Report a broken release gate somewhere a human will actually see it, without
# filing a duplicate every week.
report_blocked() {
  local title="$1" body="$2"
  local existing
  existing=$(gh issue list --repo "$REPO" --state open --search "$title in:title" \
    --json number --jq '.[0].number // empty' 2>/dev/null || true)
  if [ -n "$existing" ]; then
    log "Existing open issue #$existing already reports this; not filing a duplicate."
    gh issue comment "$existing" --repo "$REPO" --body "$body" >/dev/null 2>&1 || true
  else
    gh issue create --repo "$REPO" --title "$title" --body "$body" >/dev/null 2>&1 \
      && log "Filed an issue: $title" \
      || log "WARN: could not file an issue for: $title"
  fi
}

# ---- Refresh the dedicated clone ------------------------------------------------
if [ ! -d "$WORKDIR/.git" ]; then
  log "Cloning $REPO into $WORKDIR"
  gh repo clone "$REPO" "$WORKDIR" -- --quiet
fi
cd "$WORKDIR"

git config user.name "$GIT_AUTHOR_NAME_"
git config user.email "$GIT_AUTHOR_EMAIL_"

git fetch --quiet --tags --prune origin
git checkout --quiet "$BASE_BRANCH"
git reset --hard --quiet "origin/$BASE_BRANCH"
git clean -fdq -e .venv

# Ensure a WORKING venv for the tests (kept out of git). Checking only for
# .venv/bin/python is not enough: a venv creation that dies partway (no
# ensurepip, disk full) leaves a python binary with no pip and no dependencies,
# and every later run would skip recreation and fail the tests with import
# errors that look like the agent's fault. Stamp the requirements hash too, so a
# dependency added upstream triggers a reinstall instead of a stale venv.
REQ_STAMP=".venv/.requirements.sha256"
REQ_WANT="$(sha256sum requirements.txt | cut -d" " -f1)"
if [ ! -x ".venv/bin/python" ] || [ ! -x ".venv/bin/pip" ] \
   || [ "$(cat "$REQ_STAMP" 2>/dev/null || true)" != "$REQ_WANT" ]; then
  log "Building .venv (missing, incomplete, or requirements.txt changed)"
  rm -rf .venv
  python3 -m venv .venv
  if .venv/bin/pip install -q -r requirements.txt; then
    echo "$REQ_WANT" > "$REQ_STAMP"
  else
    log "WARN: pip install had issues"
  fi
fi
PY=".venv/bin/python"

# ---- Is there anything to release? ----------------------------------------------
LATEST_TAG="$(git tag --list 'v*' --sort=-v:refname | head -1)"
if [ -z "$LATEST_TAG" ]; then
  log "No v* tag exists yet; this job prepares follow-on releases only. Nothing to do."
  exit 0
fi

AHEAD="$(git rev-list --count "$LATEST_TAG..origin/$BASE_BRANCH")"
if [ "$AHEAD" -eq 0 ]; then
  log "NOTHING TO RELEASE: $BASE_BRANCH is not ahead of $LATEST_TAG. A skipped week is fine."
  exit 0
fi
log "$BASE_BRANCH is $AHEAD commit(s) ahead of $LATEST_TAG."

# The changelog must actually describe something. scripts/changelog_section.py
# exits non-zero when the section is missing or empty; additionally require at
# least one bullet, so a heading skeleton with no entries counts as empty.
if ! UNRELEASED="$($PY scripts/changelog_section.py Unreleased 2>>"$RUN_LOG")"; then
  log "NOTHING TO RELEASE: CHANGELOG.md has no usable [Unreleased] section. A skipped week is fine."
  exit 0
fi
if ! grep -q '^[[:space:]]*-[[:space:]]' <<<"$UNRELEASED"; then
  log "NOTHING TO RELEASE: [Unreleased] has headings but no entries. A skipped week is fine."
  exit 0
fi

# Don't stack release PRs: if last week's is still open, leave it alone.
OPEN_RELEASE_PR="$(gh pr list --repo "$REPO" --state open --json number,headRefName \
  --jq '[.[] | select(.headRefName | startswith("release/"))] | .[0].number // empty')"
if [ -n "$OPEN_RELEASE_PR" ]; then
  log "A release PR (#$OPEN_RELEASE_PR) is already open and unmerged. Not preparing another."
  exit 0
fi

CURRENT_VERSION="$($PY -c 'from trinohub import __version__; print(__version__)')"
log "Current package version: $CURRENT_VERSION (latest tag $LATEST_TAG)"

# A suggestion only — Claude may choose differently and justify it below. While
# the project is pre-1.0, a release containing new features takes a minor bump
# and anything else takes a patch bump.
if [ -n "$RELEASE_VERSION" ]; then
  SUGGESTED="$RELEASE_VERSION"
else
  SUGGESTED="$(
    UNRELEASED="$UNRELEASED" CURRENT="$CURRENT_VERSION" "$PY" - <<'PY'
import os
cur = os.environ["CURRENT"].split(".")
major, minor, patch = (int(p) for p in (cur + ["0", "0", "0"])[:3])
body = os.environ["UNRELEASED"]
added = any(line.strip().lower().startswith("### added") for line in body.splitlines())
removed = any(line.strip().lower().startswith("### removed") for line in body.splitlines())
if added or removed:
    minor, patch = minor + 1, 0
else:
    patch += 1
print(f"{major}.{minor}.{patch}")
PY
  )"
fi
log "Suggested next version: $SUGGESTED"

# ---- Hand the editorial half to Claude ------------------------------------------
BRANCH="release/prep-$(date -u +%Y%m%d)"
git branch -D "$BRANCH" >/dev/null 2>&1 || true
git checkout --quiet -b "$BRANCH"

prompt="$(cat <<EOF
You are preparing a release of the open-source project TrinoHub. You are working
in a dedicated clone on branch \`${BRANCH}\`, cut from \`${BASE_BRANCH}\`.

Follow **docs/releasing.md** exactly. Read it first — it is the spec for this task.

## Situation

- Latest published tag: **${LATEST_TAG}**
- \`${BASE_BRANCH}\` is **${AHEAD}** commit(s) ahead of it.
- Current package version: **${CURRENT_VERSION}**
- Suggested next version: **${SUGGESTED}** (mechanical suggestion: pre-1.0, a
  release with new features takes a minor bump, otherwise a patch bump). Use it
  unless the changelog contents clearly warrant otherwise; if you choose a
  different version, say why in your final summary.

Review the actual commits to understand what is shipping:

\`\`\`bash
git log --oneline ${LATEST_TAG}..${BASE_BRANCH}
\`\`\`

## Your task — the "Prepare" half of docs/releasing.md, and only that half

1. Set the chosen version in **\`trinohub/__init__.py\`** (\`__version__\`) **and**
   the **\`GitRef\`** default in **\`deploy/aws/cloudformation.yaml\`** (as
   \`vX.Y.Z\`). A test asserts these two agree — a stale GitRef fails CI.
2. In **CHANGELOG.md**, move the \`## [Unreleased]\` entries under a new
   \`## [x.y.z] - YYYY-MM-DD\` heading dated **today (UTC)**. Leave an empty
   \`## [Unreleased]\` section in place above it for future work.
3. Update the link-reference block at the bottom: point \`[Unreleased]\` at
   \`compare/vX.Y.Z...HEAD\` and add the \`[x.y.z]\` compare link against the
   previous tag. Match the existing format exactly.
4. Write an **\`### Upgrading\`** subsection inside the new release section **if
   and only if** the release needs a migration, a configuration change, or any
   manual step. Judge this from the actual diff — a database schema change, a
   new required setting or environment variable, a changed default, a removed
   endpoint, or anything an existing operator must do by hand. If none of that
   applies, omit the section rather than padding it. This text is published
   verbatim as the GitHub Release body, so write it for operators.
5. Tidy the release notes so they read as notes, not as a commit log, but do NOT
   invent entries and do NOT drop real ones.
6. Verify the notes extract cleanly:
   \`\`\`bash
   .venv/bin/python scripts/changelog_section.py v<chosen version>
   \`\`\`
7. Commit everything with the message \`release: prepare v<chosen version>\`.

## Hard limits — read these twice

- **DO NOT create a tag. DO NOT run \`git tag\` or \`git push --tags\`.**
  A human does that after reviewing and merging your PR. Pushing a \`v*\` tag
  publishes a public GitHub Release, and a published tag can never be moved or
  reused. Preparing the release is your whole job.
- **DO NOT push, and DO NOT open a PR** — the wrapper script does both.
- **DO NOT merge anything**, and do not touch \`${BASE_BRANCH}\` directly.
- **DO NOT run deploy/VALIDATION.md or any part of it.** It creates billable AWS
  resources and is explicitly not part of the release gate.
- **DO NOT attempt anything involving the trinohub.org website.** It is served
  from a different machine that is unreachable from here. If this release
  contains something the website should reflect, LIST IT in your final summary
  under a line beginning \`WEBSITE_FOLLOWUP:\` so it can be flagged for a human.
  Never try to rebuild, deploy, or edit the site.
- Do not make product changes. This is a release-preparation commit: version,
  changelog, and links. If you find a real bug, mention it in your summary and
  leave it alone.

## House rules (non-negotiable)

${HOUSE_RULES}

If you cannot prepare the release honestly — the changelog is incoherent, the
version is ambiguous, the gates fail for a reason you must not paper over — STOP,
make no further changes, and end your reply with the exact line:
AGENT_BLOCKED: <one-line reason>
EOF
)"

model_flag=()
[ -n "$CLAUDE_MODEL" ] && model_flag=(--model "$CLAUDE_MODEL")

CLAUDE_OUT="$LOGDIR/release-claude-$(date -u +%Y%m%dT%H%M%SZ).out"
set +e
claude -p "$prompt" --dangerously-skip-permissions "${model_flag[@]}" \
  > >(tee -a "$CLAUDE_OUT" >>"$RUN_LOG") 2>&1
claude_rc=$?
set -e

if grep -q "AGENT_BLOCKED:" "$CLAUDE_OUT" 2>/dev/null; then
  reason=$(grep "AGENT_BLOCKED:" "$CLAUDE_OUT" | tail -1 | sed 's/.*AGENT_BLOCKED: *//')
  log "Release preparation blocked: $reason"
  report_blocked "Release preparation blocked" \
    "The weekly release job stopped without preparing a release.

**Reason:** ${reason}

Log on the build box: \`${RUN_LOG}\`. Nothing was pushed and no tag was created."
  exit 1
fi

if [ "$claude_rc" -ne 0 ]; then
  log "Release preparation: claude exited $claude_rc"
  report_blocked "Release preparation blocked" \
    "The weekly release job's agent exited with status ${claude_rc} before preparing a release.

Log on the build box: \`${RUN_LOG}\`. Nothing was pushed and no tag was created."
  exit 1
fi

# Sweep up anything left uncommitted.
if ! git diff --quiet || ! git diff --cached --quiet; then
  git add -A
  git commit -q -m "release: prepare release" || true
fi

if git diff --quiet "$BASE_BRANCH".."$BRANCH"; then
  log "No changes produced; nothing to propose."
  exit 1
fi

# ---- Guard: the agent must not have tagged anything ------------------------------
NEW_TAGS="$(git tag --list 'v*' --sort=-v:refname | head -1)"
if [ "$NEW_TAGS" != "$LATEST_TAG" ]; then
  log "REFUSING TO CONTINUE: a new local tag ($NEW_TAGS) appeared. Tagging is a human step."
  report_blocked "Release preparation blocked" \
    "The weekly release job found an unexpected local tag (\`${NEW_TAGS}\`) after preparation. Nothing was pushed. Inspect \`${RUN_LOG}\` on the build box."
  exit 1
fi

# ---- Read back the version the agent actually chose ------------------------------
NEW_VERSION="$($PY -c 'from trinohub import __version__; print(__version__)')"
if [ "$NEW_VERSION" = "$CURRENT_VERSION" ]; then
  log "REFUSING TO CONTINUE: __version__ is still $CURRENT_VERSION; nothing was bumped."
  exit 1
fi
log "Prepared version: $NEW_VERSION"

RELEASE_BRANCH="release/v$NEW_VERSION"
git branch -M "$RELEASE_BRANCH"

# ---- Release gates (docs/releasing.md step 4) ------------------------------------
gate_failed=""
run_gate() {
  local name="$1"; shift
  log "gate: $name"
  if ! "$@" >>"$RUN_LOG" 2>&1; then
    log "GATE FAILED: $name"
    gate_failed="${gate_failed}${gate_failed:+, }${name}"
  fi
}

run_gate "unit tests"  $PY -m unittest discover -s tests
run_gate "e2e suite"   $PY testing/run_e2e.py
# shellcheck disable=SC2086
run_gate "py_compile"  $PY -m py_compile $PY_COMPILE_FILES
run_gate "whitespace"  git diff --check
run_gate "release notes extract" $PY scripts/changelog_section.py "v$NEW_VERSION"

if [ -n "$gate_failed" ]; then
  log "Release gates failed ($gate_failed). Not proposing a release."
  report_blocked "Release gates failing on $BASE_BRANCH" \
    "The weekly release job prepared **v${NEW_VERSION}** but the release gates failed, so no release was proposed.

**Failing gates:** ${gate_failed}

Nothing was pushed and no tag was created. Full log on the build box: \`${RUN_LOG}\`"
  exit 1
fi
log "All release gates passed."

# ---- Push the branch and open a DRAFT PR -----------------------------------------
WEBSITE_NOTE="$(grep -h '^WEBSITE_FOLLOWUP:' "$CLAUDE_OUT" 2>/dev/null | sed 's/^WEBSITE_FOLLOWUP: *//' || true)"
if [ -n "$WEBSITE_NOTE" ]; then
  WEBSITE_SECTION="$(printf '%s\n' "$WEBSITE_NOTE" | sed 's/^/- /')"
else
  WEBSITE_SECTION="- Nothing specific was flagged by the preparation run — check the notes yourself before publishing."
fi

git push -q -u origin "$RELEASE_BRANCH" --force-with-lease

pr_body="$(cat <<EOF
Automated **release preparation** for **v${NEW_VERSION}** (previous tag \`${LATEST_TAG}\`, ${AHEAD} commit(s)).

This PR is the *prepare* half of [\`docs/releasing.md\`](docs/releasing.md). It is a
draft on purpose: **no tag has been created and none will be by this job.**

## What ran

All release gates passed in the dedicated clone before this PR was opened:

- \`python -m unittest discover -s tests\`
- \`python testing/run_e2e.py\`
- \`python -m py_compile ${PY_COMPILE_FILES}\`
- \`git diff --check\`
- \`python scripts/changelog_section.py v${NEW_VERSION}\` (release notes extract cleanly)

\`deploy/VALIDATION.md\` was **not** run — it creates billable AWS resources and is
not part of the routine release gate.

## What a human does next

1. Review the changelog wording and the Upgrading section, if there is one — it is
   published verbatim as the GitHub Release body.
2. Confirm **v${NEW_VERSION}** is the right version for what is shipping.
3. Mark ready, let the \`tests\` check pass, and squash-merge.
4. **Then** tag the merged commit on \`${BASE_BRANCH}\` by hand:

   \`\`\`bash
   git checkout ${BASE_BRANCH} && git pull --ff-only
   git tag -a v${NEW_VERSION} -m "TrinoHub v${NEW_VERSION}"
   git push origin v${NEW_VERSION}
   \`\`\`

   Pushing that tag publishes the public GitHub Release. A published tag must
   never be moved or reused, which is why this step stays with a person.

## Website follow-up (flagged, not attempted)

trinohub.org is served from a different machine that this job cannot reach, so
nothing about the site has been changed. Worth reflecting there:

${WEBSITE_SECTION}
EOF
)"

pr_url=$(gh pr create --repo "$REPO" --draft --base "$BASE_BRANCH" --head "$RELEASE_BRANCH" \
  --title "release: prepare v${NEW_VERSION}" --body "$pr_body")

log "Opened draft release PR: $pr_url"
log "NO TAG WAS CREATED — tagging is a human step after this PR merges."
log "Run complete. Log: $RUN_LOG"
