# Releasing TrinoHub

TrinoHub releases use semantic version tags. The package version and the default
CloudFormation `GitRef` must identify the same release.

## Prepare and verify

1. Merge the intended changes into `main` and pull it with `git pull --ff-only`.
2. Update `trinohub/__init__.py` and the `GitRef` default in
   `deploy/aws/cloudformation.yaml` to the new version.
3. Run the release gates:

   ```bash
   .venv/bin/python -m unittest discover -s tests -v
   .venv/bin/python testing/run_e2e.py
   .venv/bin/python -m py_compile \
     trinohub/api.py trinohub/server.py trinohub/aws_checks.py trinohub/database.py
   git diff --check
   ```

4. Push the release preparation commit to `main` and wait for the `tests`
   workflow to pass.

## Tag and publish

Create an annotated tag from the verified `main` commit:

```bash
git tag -a v0.2.0 -m "TrinoHub v0.2.0"
git push origin v0.2.0
```

The `release` workflow checks that the tag matches the package version, repeats
the automated test gates, and creates the GitHub Release with generated notes.
Never move or reuse a published release tag; prepare a patch release instead.

## Deploy

New CloudFormation installations should set `GitRef` to the release tag. Upgrade
an existing instance through SSM using the exact tagged checkout documented in
[`deploy/aws/README.md`](../deploy/aws/README.md#updating). Back up `.trinohub/`
before upgrading and verify both the systemd service and `/api/health` afterward.

The clean-account validation in [`deploy/VALIDATION.md`](../deploy/VALIDATION.md)
creates billable resources and is not part of the routine release gate. Run it
only with explicit billing approval.
