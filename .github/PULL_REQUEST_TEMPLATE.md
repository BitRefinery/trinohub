<!--
Thanks for contributing to TrinoHub! Keep PRs focused — one logical change each.
If this PR was opened by the automated agent, a maintainer will review before merge.
-->

## What & why

<!-- What does this change and what problem does it solve? -->

Closes #<!-- issue number -->

## How I tested

- [ ] `.venv/bin/python -m unittest discover -s tests -v` passes
- [ ] `.venv/bin/python testing/run_e2e.py` passes (no AWS / no billing)
- [ ] Manually verified the affected UI/API path

## Checklist

- [ ] Change is scoped to one thing; no unrelated refactors
- [ ] No secrets, real AWS account IDs, or private hostnames in the diff
- [ ] Kept the security boundaries intact (instance-profile auth only; `validate_read_only_sql` for Ask Trino; no `/api/assist/sql`)
- [ ] Updated `docs/` if behavior changed
