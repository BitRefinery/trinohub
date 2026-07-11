# Contributing to TrinoHub

Thanks for your interest in TrinoHub! This project is an open-source, self-hosted
AWS control plane for running Trino SQL clusters from the browser. Contributions —
bug reports, features, docs, and code — are all welcome.

## TL;DR

1. **Found a bug or have an idea?** Open an issue using the templates. Good issues
   are the highest-leverage contribution.
2. **Want to write code?** Comment on the issue first so we can agree on the
   approach before you spend time on it.
3. Fork, branch, make a focused change, run the tests, open a PR.

> **Heads-up: some issues are worked by an automated agent.** A maintainer may
> label a triaged issue `agent:queued`, after which a scheduled Claude Code job
> may open a **draft** PR proposing a fix. A human always reviews and merges —
> nothing is auto-merged. If you're already working an issue, say so in a comment
> and we'll leave it to you.

## Development setup

TrinoHub is a FastAPI app (Python) that serves a static HTML/CSS/JS frontend. No
frontend build step.

```bash
git clone https://github.com/BitRefinery/trinohub.git
cd trinohub

# Create a virtualenv and install deps
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run the app (first launch shows the setup wizard)
.venv/bin/python -m uvicorn trinohub.api:app --host 0.0.0.0 --port 8000 --log-level warning
# open http://127.0.0.1:8000   (OpenAPI docs at /docs)
```

You do **not** need an AWS account to develop most of the app or to run the test
suites — the tests use in-memory AWS/Trino fakes. You only need real AWS to
actually provision clusters.

## Running the tests

Always use the project virtualenv — bare `python3` can silently skip the FastAPI
route tests if dependencies are missing.

```bash
.venv/bin/python -m unittest discover -s tests -v   # unit + API route tests
.venv/bin/python testing/run_e2e.py                 # end-to-end workflow suite (no AWS, no billing)
```

Both must pass before a PR can be merged. Add tests near the behavior you change
(e.g. focused methods in `tests/test_server.py` / `tests/test_api.py`).

## Coding style

- **Python:** 4-space indentation. Keep business logic in `trinohub/server.py`
  (`TrinoHubApp`) and HTTP wiring in `trinohub/api.py`.
- **Frontend (`web/`):** 2-space indentation; keep `app.js` browser-native
  (no bundler). Descriptive CSS class names.
- **Naming:** kebab-case for files and directories.
- Match the surrounding code's conventions rather than introducing new patterns.
- Keep commits small and imperative: `docs: add install guide`, `web: fix cluster form`.

## Security boundaries you must not break

These are load-bearing. PRs that weaken them won't be merged:

- **No static AWS credentials, ever.** The control plane authenticates via its EC2
  instance profile; cluster nodes use signed, per-cluster bootstrap tokens. Don't
  add stored access keys.
- **Ask Trino** (`/api/ask`): the LLM only emits SQL *text*, which
  `validate_read_only_sql` checks (SELECT-only, single statement) before it runs.
  Never give the model direct DB access; never log or return the LLM API key. The
  old `/api/assist/sql` endpoint stays removed.
- Don't commit secrets, real AWS account IDs, `*.pem`/`*.key`, tokens, or the
  SQLite DB. `.gitignore` already blocks the common ones — keep it that way.

## Scope / non-goals

To keep the project focused, these are **out of scope** unless discussed first:
multi-cloud, Kubernetes, BYO Terraform, and replicating any commercial managed-Trino
product's UI, copy, or trademarks. See the README's "Non-goals" section.

## Opening a pull request

1. Branch from `main`: `git checkout -b fix/short-description`.
2. Make the change + tests; run both suites above.
3. Push and open a PR using the template. Link the issue it closes.
4. A maintainer reviews. Please keep the PR responsive to review comments.

By contributing, you agree your contributions are licensed under the project's
[Apache License 2.0](LICENSE).
