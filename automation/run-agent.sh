#!/usr/bin/env bash
#
# run-agent.sh — daily "Claude works on triaged issues" job for TrinoHub.
#
# What it does, once per run:
#   1. Refreshes a DEDICATED clone of the repo (never your working checkout).
#   2. Finds open issues you've triaged with the `agent:queued` label.
#   3. For each (up to MAX_ISSUES), runs Claude Code headless on a fresh branch
#      to implement the issue, then runs the test suites.
#   4. If tests pass, pushes the branch and opens a **DRAFT** PR that closes the
#      issue, then relabels the issue `agent:in-review`.
#   5. If it can't (Claude errored or tests fail), labels the issue
#      `agent:blocked` and comments why. Nothing is ever merged automatically.
#
# YOU stay in control: an issue is only touched if YOU add `agent:queued`.
# Every result is a draft PR that you review and merge by hand.
#
# Requirements on the box:
#   - gh (GitHub CLI), authenticated with a token that can write to THIS repo only.
#   - claude (Claude Code CLI), authenticated (or ANTHROPIC_API_KEY exported).
#   - jq, git.
#
# SECURITY: run this as an unprivileged user, in a clone that contains NO secrets
# and NO AWS credentials. The agent runs with relaxed permissions so it can edit
# files and run tests unattended — treat the box as if the agent can run any
# command in that directory. See automation/README.md.

set -euo pipefail

# ---- Config (override via env or automation/agent.env) --------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="${AGENT_CONFIG:-"$SCRIPT_DIR/agent.env"}"
# shellcheck disable=SC1090
[ -f "$CONFIG_FILE" ] && source "$CONFIG_FILE"
RULES_FILE="${RULES_FILE:-"$SCRIPT_DIR/house-rules.md"}"

REPO="${REPO:?Set REPO=owner/trinohub in agent.env}"
WORKDIR="${WORKDIR:-"$HOME/.trinohub-agent/checkout"}"
LOGDIR="${LOGDIR:-"$HOME/.trinohub-agent/logs"}"
BASE_BRANCH="${BASE_BRANCH:-main}"
LABEL_QUEUED="${LABEL_QUEUED:-agent:queued}"
LABEL_INREVIEW="${LABEL_INREVIEW:-agent:in-review}"
LABEL_BLOCKED="${LABEL_BLOCKED:-agent:blocked}"
MAX_ISSUES="${MAX_ISSUES:-3}"
# BitRefinery is the only GitHub identity for this project; see house-rules.md.
GIT_AUTHOR_NAME_="${GIT_AUTHOR_NAME_:-BitRefinery}"
GIT_AUTHOR_EMAIL_="${GIT_AUTHOR_EMAIL_:-299273308+BitRefinery@users.noreply.github.com}"
CLAUDE_MODEL="${CLAUDE_MODEL:-}"            # e.g. claude-opus-4-8 ; empty = CLI default
TEST_CMD="${TEST_CMD:-.venv/bin/python -m unittest discover -s tests -v && .venv/bin/python testing/run_e2e.py}"

# The agent must work in a DEDICATED clone. If WORKDIR is the repository this
# script lives in (or anywhere inside it), an unattended run would rewrite the
# working checkout with `git reset --hard` and `git clean -fd`. Refuse instead.
WORKDIR_ABS="$(readlink -m "$WORKDIR")"
case "$WORKDIR_ABS" in
  "$REPO_ROOT" | "$REPO_ROOT"/*)
    echo "REFUSING TO RUN: WORKDIR ($WORKDIR_ABS) is inside this checkout ($REPO_ROOT)." >&2
    echo "The agent needs a dedicated clone; set WORKDIR to a path outside the repo." >&2
    exit 1
    ;;
esac

mkdir -p "$LOGDIR" "$(dirname "$WORKDIR")"
RUN_LOG="$LOGDIR/run-$(date -u +%Y%m%dT%H%M%SZ).log"
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

# Shared rules pasted into every prompt (authorship, branch protection, CI, docs).
if [ ! -f "$RULES_FILE" ]; then
  echo "Missing house rules file: $RULES_FILE" >&2
  exit 1
fi
HOUSE_RULES="$(sed "s|{{REPO}}|$REPO|g" "$RULES_FILE")"

# ---- Refresh the dedicated clone ------------------------------------------------
if [ ! -d "$WORKDIR/.git" ]; then
  log "Cloning $REPO into $WORKDIR"
  gh repo clone "$REPO" "$WORKDIR" -- --quiet
fi
cd "$WORKDIR"

# Pin the commit identity in the clone. There is deliberately no global git
# identity on the build box, so without this every commit fails with "unable to
# auto-detect email address" — and any address that *did* get inherited would
# misattribute the commit to a different GitHub account. See house-rules.md.
git config user.name "$GIT_AUTHOR_NAME_"
git config user.email "$GIT_AUTHOR_EMAIL_"

git fetch --quiet origin
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

# ---- Find triaged issues --------------------------------------------------------
mapfile -t ISSUES < <(
  gh issue list --repo "$REPO" --state open --label "$LABEL_QUEUED" \
    --json number,title,body,labels --limit 50 |
  jq -c --arg inreview "$LABEL_INREVIEW" \
    '.[] | select([.labels[].name] | index($inreview) | not)'
)

if [ "${#ISSUES[@]}" -eq 0 ]; then
  log "No issues labeled '$LABEL_QUEUED' to work. Done."
  exit 0
fi
log "Found ${#ISSUES[@]} queued issue(s); will process up to $MAX_ISSUES."

# ---- Work each issue ------------------------------------------------------------
count=0
for issue_json in "${ISSUES[@]}"; do
  [ "$count" -ge "$MAX_ISSUES" ] && { log "Hit MAX_ISSUES=$MAX_ISSUES; stopping."; break; }
  count=$((count + 1))

  num=$(jq -r '.number' <<<"$issue_json")
  title=$(jq -r '.title' <<<"$issue_json")
  body=$(jq -r '.body // ""' <<<"$issue_json")
  branch="agent/issue-${num}"
  log "=== Issue #$num: $title ==="

  git checkout --quiet "$BASE_BRANCH"
  git branch -D "$branch" >/dev/null 2>&1 || true
  git checkout --quiet -b "$branch"

  prompt="$(cat <<EOF
You are working on the open-source project TrinoHub (a FastAPI + boto3 AWS control
plane for Trino, with a static HTML/CSS/JS frontend in web/). You are resolving
ONE GitHub issue in a fresh branch. A human will review your work as a draft PR, so
be conservative and focused.

## GitHub issue #${num}: ${title}

${body}

## Your task
1. Read CONTRIBUTING.md and AGENTS.md-equivalent conventions in the repo, and the
   relevant files under trinohub/, web/, tests/, docs/.
2. Implement the smallest correct change that resolves the issue. Do NOT refactor
   unrelated code. Do NOT add out-of-scope features (see README "Non-goals").
3. NEVER weaken security boundaries: instance-profile auth only (no static AWS
   keys), keep validate_read_only_sql / the Ask Trino boundary intact, do not
   reintroduce /api/assist/sql, and never commit secrets.
4. Add or update tests near the changed behavior.
5. Run the test suites and make them pass:
   ${TEST_CMD}
6. Update docs/ if behavior changed.
7. Commit your work with a clear, imperative message. Do NOT push and do NOT open
   a PR — the wrapper script handles that.

## House rules (non-negotiable)

${HOUSE_RULES}

## Scope note for this job

The wrapper script pushes the branch and opens the draft PR for you, so you will
not normally run \`git push\` or \`gh pr create\` yourself. The rules above still
bind you: if you do touch the remote, the authorship, no-fork, and
never-bypass-branch-protection rules apply in full. Never merge a pull request —
this job never merges anything, and a human reviews every draft.

If the issue is unclear, under-specified, or you cannot make the tests pass, STOP,
do not fabricate a change, and end your reply with the exact line:
AGENT_BLOCKED: <one-line reason>
EOF
)"

  model_flag=()
  [ -n "$CLAUDE_MODEL" ] && model_flag=(--model "$CLAUDE_MODEL")

  set +e
  claude -p "$prompt" \
    --dangerously-skip-permissions \
    "${model_flag[@]}" \
    >>"$RUN_LOG" 2>&1
  claude_rc=$?
  set -e

  # Did the agent explicitly declare itself blocked?
  if grep -q "AGENT_BLOCKED:" "$RUN_LOG"; then
    reason=$(grep "AGENT_BLOCKED:" "$RUN_LOG" | tail -1 | sed 's/.*AGENT_BLOCKED: *//')
    log "Issue #$num blocked by agent: $reason"
    gh issue edit "$num" --repo "$REPO" --add-label "$LABEL_BLOCKED" --remove-label "$LABEL_QUEUED"
    gh issue comment "$num" --repo "$REPO" --body \
      "🤖 The automated agent couldn't complete this: **${reason}**. Un-label \`${LABEL_BLOCKED}\` and re-add \`${LABEL_QUEUED}\` after clarifying to retry."
    continue
  fi

  if [ "$claude_rc" -ne 0 ]; then
    log "Issue #$num: claude exited $claude_rc"
    gh issue edit "$num" --repo "$REPO" --add-label "$LABEL_BLOCKED" --remove-label "$LABEL_QUEUED"
    gh issue comment "$num" --repo "$REPO" --body \
      "🤖 The automated agent errored (exit $claude_rc) before producing a change. Left as \`${LABEL_BLOCKED}\` for a maintainer."
    continue
  fi

  # Make sure everything is committed (agent may have left staged/unstaged work).
  if ! git diff --quiet || ! git diff --cached --quiet; then
    git add -A
    git commit -q -m "agent: address #${num} — ${title}" || true
  fi

  if git diff --quiet "$BASE_BRANCH".."$branch"; then
    log "Issue #$num: no changes produced; skipping."
    gh issue edit "$num" --repo "$REPO" --add-label "$LABEL_BLOCKED" --remove-label "$LABEL_QUEUED"
    gh issue comment "$num" --repo "$REPO" --body \
      "🤖 The automated agent produced no changes. Left as \`${LABEL_BLOCKED}\`."
    continue
  fi

  # ---- Verify: tests must pass before we open a PR ------------------------------
  log "Issue #$num: running tests"
  set +e
  bash -lc "$TEST_CMD" >>"$RUN_LOG" 2>&1
  test_rc=$?
  set -e

  if [ "$test_rc" -ne 0 ]; then
    log "Issue #$num: tests FAILED (rc=$test_rc); opening draft PR flagged for a human."
    git push -q -u origin "$branch" --force-with-lease
    gh pr create --repo "$REPO" --draft --base "$BASE_BRANCH" --head "$branch" \
      --title "agent: [needs work] #${num} ${title}" \
      --body "🤖 Automated draft for #${num}. ⚠️ **Tests are failing** — see the run log. A maintainer must finish this.

Closes #${num}"
    gh issue edit "$num" --repo "$REPO" --add-label "$LABEL_INREVIEW" --remove-label "$LABEL_QUEUED"
    continue
  fi

  # ---- Success: push + draft PR -------------------------------------------------
  git push -q -u origin "$branch" --force-with-lease
  pr_url=$(gh pr create --repo "$REPO" --draft --base "$BASE_BRANCH" --head "$branch" \
    --title "agent: #${num} ${title}" \
    --body "🤖 Automated draft PR for #${num}. Tests passed locally in the agent run. Please review before merging.

Closes #${num}")
  log "Issue #$num: opened draft PR $pr_url"
  gh issue edit "$num" --repo "$REPO" --add-label "$LABEL_INREVIEW" --remove-label "$LABEL_QUEUED"
  gh issue comment "$num" --repo "$REPO" --body \
    "🤖 Opened a draft PR: $pr_url — a maintainer will review before merge."
done

log "Run complete. Processed $count issue(s). Log: $RUN_LOG"
