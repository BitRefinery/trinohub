# TrinoHub automation

Two scheduled jobs run headless Claude Code against this repository. Both open
**draft** pull requests and **neither merges anything, ever**.

| Job | Script | Cadence | Produces |
|---|---|---|---|
| **Issue agent** | `run-agent.sh` | Mon, Wed, Fri 09:15 | A draft PR per `agent:queued` issue |
| **Release preparation** | `prepare-release.sh` | Fri 17:00 | A draft `release/vX.Y.Z` PR — **never a tag** |

```
you label an issue  ──►  Mon/Wed/Fri run  ──►  draft PR (Closes #N)
   agent:queued            (headless Claude Code)      you review + merge
```

> ### Two things must be true or nothing happens
>
> 1. **The systemd units must actually be installed.** The `.service` and
>    `.timer` files in this directory are templates — copying them into
>    `~/.config/systemd/user/` and enabling the timers is a manual step. An
>    un-installed timer produces no output and no error; it simply never runs.
>    Check with `systemctl --user list-timers`.
> 2. **At least one open issue must carry the `agent:queued` label.** That label
>    is the entire opt-in gate. With none applied, every run finds no work and
>    exits cleanly — which looks identical to a run that never happened. Check
>    with `gh issue list --label agent:queued`.
>
> Both jobs were dormant for two months because neither of these was true.

## The control loop (how "with my direction" works)

1. Someone files an issue (bug / feature) via the templates.
2. **You triage it.** If you want the agent to attempt it, add the label
   **`agent:queued`**. (Optionally sharpen the issue body first — that's your
   "direction". The agent reads the whole issue.)
3. The next scheduled run picks up every open `agent:queued` issue (up to
   `MAX_ISSUES`), works each on its own branch, runs the tests, and:
   - ✅ tests pass → pushes the branch, opens a **draft PR** that `Closes #N`,
     relabels the issue `agent:in-review`, and comments the PR link.
   - ⚠️ tests fail → still opens a draft PR titled `[needs work]` so you can pick
     it up, relabels `agent:in-review`.
   - 🚫 agent can't do it / no change → labels `agent:blocked` and comments why.
4. **You review the draft PR** and merge (or push more commits / close it).

Because the trigger is a label you apply, unattended runs never surprise you.

## One-time setup

On the machine that will run the jobs:

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
cd /sites/trinohub/automation
REPO=BitRefinery/trinohub ./labels.sh

# 5. Configure
cp agent.env.example agent.env
$EDITOR agent.env          # set REPO=BitRefinery/trinohub

# 6. Dry run. With no issue labeled agent:queued this exits 0 having done
#    nothing, which is the correct behaviour on an empty queue.
bash run-agent.sh
```

## Schedule it

The units are **user** units, not system units. Everything the jobs need is
user-scoped — the `claude` binary in `~/.local/bin`, its credentials in
`~/.claude`, the `gh` token in `~/.config/gh` — and neither job needs any
privilege, so there is nothing to gain from `/etc/systemd/system` and root.

```bash
mkdir -p ~/.config/systemd/user
cp /sites/trinohub/automation/trinohub-agent.{service,timer}   ~/.config/systemd/user/
cp /sites/trinohub/automation/trinohub-release.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now trinohub-agent.timer
systemctl --user enable --now trinohub-release.timer

# REQUIRED. Without lingering, the user manager stops when you log out and the
# timers do not fire on an unattended box.
loginctl enable-linger "$USER"

systemctl --user list-timers        # confirm both timers and their next run
```

The units reference **absolute paths** under `/sites/trinohub`, not `%h`-relative
ones. The checkout is not under the home directory, and the earlier
`%h/trinohub/automation` would have resolved to a path that does not exist. If
you relocate the repo, edit the paths in both `.service` files.

Trigger a run by hand at any time:

```bash
systemctl --user start trinohub-agent.service
journalctl --user -u trinohub-agent -f
```

### Cadence

The issue agent runs **`Mon,Wed,Fri`** rather than `*/2` day-of-month. A `*/2`
expression counts from the 1st of each month, so it fires on the 31st and then
again on the 1st — double-firing across every 31-day month boundary. A weekday
list has no such seam. Both timers keep `Persistent=true` (catch up after the
box was off) and a randomized delay.

## The release job

`prepare-release.sh` runs every Friday and performs the *prepare* half of
[`docs/releasing.md`](../docs/releasing.md):

- Refreshes its **own** clone (`RELEASE_WORKDIR`), separate from the issue
  agent's — both jobs run on Friday and must not share a working tree.
- **Stops if there is nothing to release.** If `main` is not ahead of the latest
  tag, or `## [Unreleased]` in `CHANGELOG.md` has no entries, it logs why and
  exits 0. **A skipped week is success, not failure.** It also stands down if a
  previous `release/*` PR is still open.
- Bumps `trinohub/__init__.py` **and** the `GitRef` default in
  `deploy/aws/cloudformation.yaml` — a test asserts the two agree.
- Moves `[Unreleased]` under a dated heading, adds the compare link, and writes
  an **Upgrading** section when the release needs a migration or manual step.
- Runs the gates: `unittest discover -s tests`, `testing/run_e2e.py`,
  `py_compile` on the four files `docs/releasing.md` names, `git diff --check`,
  and a release-notes extraction check. If any fail it proposes nothing and
  files an issue instead.
- Opens a **draft** `release/vX.Y.Z` PR containing the exact tag commands.

It **never** runs [`deploy/VALIDATION.md`](../deploy/VALIDATION.md) — that
creates billable AWS resources and is not part of the routine gate.

### Why this stops before tagging

The job prepares everything and stops before `git push --tags`. Three reasons:

1. **A tag is the only irreversible artifact in the process.** `docs/releasing.md`
   is explicit that a published tag must never be moved or reused. An automated
   tag on a bad release burns that version number permanently; the only remedy is
   a patch release.
2. **Pushing a `v*` tag publishes a public GitHub Release** whose body is the
   changelog section verbatim. That is an outward-facing publish, which is not
   something an unattended job should do on its own.
3. **It could not tag correctly even if it wanted to.** The tag must be created
   from the verified commit on `main`, but the preparation lands on a branch that
   a human has to review and merge first. At the moment the job finishes, the
   commit worth tagging does not exist on `main` yet.

So the job hands you a reviewed-ready PR and the two commands to run after
merging. Consistent with the rest of this directory: the machine prepares, the
human decides.

### The website is flagged, never touched

trinohub.org is served from a **different machine** and is not reachable from the
build box. The release job never attempts to rebuild or deploy the site. Anything
the site should reflect is listed under "Website follow-up" in the PR body for a
human to carry over.

## Guardrails & safety

These jobs run an AI agent **unattended with relaxed permissions** so it can edit
files and run tests without prompting. Contain it:

- **Dedicated clones, no secrets.** Each job works in its own `WORKDIR`, *not*
  your dev checkout. Both scripts **refuse to start** if `WORKDIR` resolves
  inside this repository, and both `.service` units additionally mark
  `/sites/trinohub` `ReadOnlyPaths`, so a misconfigured `agent.env` cannot damage
  the working tree even if the script's own guard were bypassed. Keep no `.env`,
  `*.pem`, or AWS credentials on that box.
- **Pinned commit identity.** There is deliberately no global git identity on the
  build box, so both scripts set `user.name`/`user.email` in their clone
  explicitly. Every commit is authored `BitRefinery`; see
  [`house-rules.md`](house-rules.md).
- **Least-privilege GitHub token.** Use a fine-grained PAT limited to the single
  repo with Contents + Pull requests + Issues write.
- **No auto-merge.** PRs are always drafts. `main` requires the `tests` check;
  the prompt forbids bypassing it with `--admin` or altering branch protection.
- **Human trigger only.** The issue agent ignores everything except issues you
  labeled `agent:queued`.
- **Caps.** `MAX_ISSUES` bounds work per run; both units have a 1-hour timeout.
  Logs land in `~/.trinohub-agent/logs/`.
- **Prompt-injection awareness.** Issue text is untrusted input. The agent prompt
  forbids weakening security boundaries, but you are the backstop: read every
  diff before merging, especially changes to auth, IAM, or `validate_read_only_sql`.

## House rules

[`house-rules.md`](house-rules.md) is pasted into the prompt of **both** jobs. It
covers authorship, never working from a fork, never bypassing branch protection,
polling CI on the current head SHA after a force-push, listing new `docs/*.md`
files in `docs/manifest.json`, and never weakening a test to reach green. Edit it
once and both jobs pick it up.

## Tuning

Everything is env-configurable in `agent.env` — model, `MAX_ISSUES`, the test
command, clone locations, branch names. See `agent.env.example`.
