# TrinoHub issue agent

A scheduled job that lets **Claude Code work your triaged GitHub issues once a
day** and open **draft** pull requests for you to review. Nothing is ever merged
automatically, and only issues **you** approve are touched.

```
you label an issue  ──►  daily cron runs run-agent.sh  ──►  draft PR (Closes #N)
   agent:queued              (headless Claude Code)           you review + merge
```

## The control loop (how "with my direction" works)

1. Someone files an issue (bug / feature) via the templates.
2. **You triage it.** If you want the agent to attempt it, add the label
   **`agent:queued`**. (Optionally sharpen the issue body first — that's your
   "direction". The agent reads the whole issue.)
3. The daily run picks up every open `agent:queued` issue (up to `MAX_ISSUES`),
   works each on its own branch, runs the tests, and:
   - ✅ tests pass → pushes the branch, opens a **draft PR** that `Closes #N`,
     relabels the issue `agent:in-review`, and comments the PR link.
   - ⚠️ tests fail → still opens a draft PR titled `[needs work]` so you can pick
     it up, relabels `agent:in-review`.
   - 🚫 agent can't do it / no change → labels `agent:blocked` and comments why.
4. **You review the draft PR** and merge (or push more commits / close it).

Because the trigger is a label you apply, unattended runs never surprise you.

## One-time setup

On the machine that will run the job (a small always-on box or your workstation):

```bash
# 1. Dependencies
#    - GitHub CLI:   https://cli.github.com/
#    - Claude Code:  https://docs.claude.com/claude-code   (npm i -g @anthropic-ai/claude-code)
#    - jq, git, python3-venv

# 2. Authenticate gh with a token scoped to THIS repo only (contents + PRs + issues).
#    Prefer a fine-grained PAT limited to owner/trinohub, not your whole account.
gh auth login

# 3. Authenticate Claude Code (interactive `claude` once, or export ANTHROPIC_API_KEY).

# 4. Create the label scheme in the repo
cd automation
REPO=BitRefinery/trinohub ./labels.sh

# 5. Configure
cp agent.env.example agent.env
$EDITOR agent.env          # set REPO=BitRefinery/trinohub

# 6. Dry run against a test issue you've labeled agent:queued
bash run-agent.sh
```

## Schedule it

**Option A — systemd timer (recommended):**

```bash
mkdir -p ~/.config/systemd/user
cp trinohub-agent.service trinohub-agent.timer ~/.config/systemd/user/
# edit the paths in the .service if your clone isn't at ~/trinohub
systemctl --user daemon-reload
systemctl --user enable --now trinohub-agent.timer
loginctl enable-linger "$USER"     # so the timer runs when you're logged out
systemctl --user list-timers        # confirm next run
```

**Option B — cron:**

```cron
15 9 * * *  cd $HOME/trinohub/automation && /usr/bin/env bash run-agent.sh >> $HOME/.trinohub-agent/cron.log 2>&1
```

## Guardrails & safety

This job runs an AI agent **unattended with relaxed permissions** so it can edit
files and run tests without prompting. Contain it:

- **Dedicated clone, no secrets.** The agent works in `WORKDIR`
  (`~/.trinohub-agent/checkout` by default), *not* your dev checkout. Keep no
  `.env`, `*.pem`, or AWS credentials on that box.
- **Least-privilege GitHub token.** Use a fine-grained PAT limited to the single
  repo with Contents + Pull requests + Issues write. It can open PRs but the repo
  should require review before merge (see below).
- **No auto-merge.** PRs are always drafts. Turn on branch protection for `main`
  requiring a review, so even a misconfigured token can't merge.
- **Human trigger only.** The agent ignores everything except issues you labeled
  `agent:queued`. It never acts on new issues on its own.
- **Caps.** `MAX_ISSUES` bounds work per run; the systemd unit has a 1-hour
  timeout. Logs land in `~/.trinohub-agent/logs/`.
- **Prompt-injection awareness.** Issue text is untrusted input. The agent prompt
  forbids weakening security boundaries, but you are the backstop: read every
  diff before merging, especially changes to auth, IAM, or `validate_read_only_sql`.

## Tuning

Everything is env-configurable in `agent.env` — model, `MAX_ISSUES`, the test
command, branch names. See `agent.env.example`.
