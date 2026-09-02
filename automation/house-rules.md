# House rules for unattended agent runs

Both `run-agent.sh` and `prepare-release.sh` paste this file into the prompt they
hand to Claude Code. It is the shared contract every unattended run works under.
`{{REPO}}` is substituted with the configured repository at run time.

## Authorship

- Every commit must be authored **`BitRefinery <299273308+BitRefinery@users.noreply.github.com>`**.
  Set it explicitly in the clone before committing — do not rely on inherited config:

  ```bash
  git config user.name  "BitRefinery"
  git config user.email "299273308+BitRefinery@users.noreply.github.com"
  ```

- BitRefinery is the **only** GitHub identity for this project. Never author or
  co-author as any other address. In particular, a personal address on the box
  belongs to a different account and would silently misattribute the commit.
- Do **not** add `Co-Authored-By:` trailers, `Generated with Claude Code` lines,
  or any other AI-attribution footer to commit messages or PR bodies. Public
  contributions are attributed to BitRefinery and nothing else.

## Branches and remotes

- **Never work from a fork.** Push branches directly to `{{REPO}}` and open the
  PR against that same repository. A PR from a fork is wrong for this project
  and cannot be fixed by editing it afterward.
- Confirm before pushing that `origin` points at `{{REPO}}`. If a write returns
  403 or 404 on a repository that plainly exists, the cause is a wrong GitHub
  identity, not a missing repository — stop and report it rather than retrying
  against some other remote.

## Branch protection is real — never bypass it

- `main` is protected and requires the **`tests`** status check to pass.
- **Never** pass `--admin` to `gh pr merge`, and never use any other flag or API
  call that bypasses a failing or pending required check.
- **Never** alter, disable, or "temporarily relax" branch protection — not with
  `gh api`, not through settings, not for a moment. If protection appears to be
  blocking legitimate work, stop and report it.
- Admin enforcement is currently off on this repository, which means a bypass
  would actually succeed. That is precisely why it is forbidden: the guardrail
  depends on this rule being followed, not on the API refusing you.

## Checking CI correctly after a force-push

A PR's rollup summary briefly keeps reporting the **previous** head after a
force-push, so a naive `gh pr checks` can report green for a commit you replaced.
Always resolve the current head SHA first and poll the check runs on that SHA:

```bash
H=$(gh pr view <N> --json headRefOid --jq .headRefOid)
gh api repos/{{REPO}}/commits/$H/check-runs \
  --jq '.check_runs[]|select(.name=="tests")|.status+"/"+(.conclusion//"-")'
```

Wait for `completed/success` on that SHA. Treat `queued` or `in_progress` as
"not yet known" and keep polling — never as a pass.

## Documentation

- A new `docs/*.md` file is **invisible to readers** until it is listed in
  `docs/manifest.json`. The in-app Docs viewer and the public docs site are both
  driven by that manifest. Adding the file alone is a silent no-op — add the
  topic to the manifest in the same change. A test enforces this, so skipping it
  fails CI.

## Tests are not an obstacle

- **Never weaken, skip, delete, or `@unittest.skip` a test to get to green**, and
  never loosen an assertion so a failure passes. A failing test is information.
- If a test fails and you cannot fix the underlying cause honestly, **stop** and
  report it as blocked. A blocked issue a human resolves is a good outcome; a
  green suite that no longer checks anything is not.
- Changing a test is legitimate only when the change itself intentionally and
  correctly changes the documented behavior the test asserts — and then the new
  assertion must be as strict as the old one.
