# TrinoHub end-to-end test suite

This directory holds the **end-to-end (E2E) workflow tests** for the TrinoHub
control plane. They exercise complete operator workflows — setup, cluster
lifecycle, queries, catalogs, scaling, suspend, users, and access control —
through the *real* FastAPI HTTP API, the same surface the browser UI uses.

Run this suite **at every release** (and before every production deploy) to
confirm the end-to-end workflows still hold together. It complements, but does
not replace, the focused unit/route tests under `../tests/`.

> No AWS calls are made and **no billable resources are launched**. The suite
> injects an in-memory fake AWS and fake Trino engine (see `harness.py`), so it
> is safe to run anywhere, anytime, with no credentials.

## Quick start

Always use the project virtualenv — bare `python3` may lack FastAPI and would
silently skip the route coverage.

```bash
# Run the whole suite with a release-friendly PASS/FAIL summary (release gate):
.venv/bin/python testing/run_e2e.py

# Verbose, per-test names:
.venv/bin/python testing/run_e2e.py -v

# Only some scenarios (by number or name substring):
.venv/bin/python testing/run_e2e.py 04 07
.venv/bin/python testing/run_e2e.py queries

# Or run via plain unittest (integrates with CI that already calls unittest):
.venv/bin/python -m unittest discover -s testing/scenarios -v
```

`run_e2e.py` exits non-zero if anything fails, so it can be wired straight into
a release pipeline.

## When to run it

| Stage                         | Command                                            |
| ----------------------------- | -------------------------------------------------- |
| Local, before pushing a change| `.venv/bin/python testing/run_e2e.py`              |
| New release candidate / tag   | `.venv/bin/python testing/run_e2e.py` (must PASS)  |
| Investigating one workflow    | `.venv/bin/python testing/run_e2e.py <filter>`     |
| Full automated check          | `.venv/bin/python -m unittest discover -s tests && .venv/bin/python testing/run_e2e.py` |

## What's covered

Each scenario module is a self-contained workflow. They are numbered so they run
in a sensible release-validation order.

| Module                                | Workflow exercised end-to-end                                                                 |
| ------------------------------------- | --------------------------------------------------------------------------------------------- |
| `test_01_setup_auth.py`               | First-run setup, admin creation, login/logout/session, setup-can-only-run-once, bad-credential reject |
| `test_02_cluster_lifecycle.py`        | Create → start (billable confirm) → running (health) → suspend → restart → disable → delete; AWS resource bookkeeping & cleanup at each step; cluster events |
| `test_03_catalogs.py`                 | Add/list/edit/remove S3+Glue catalogs, attach to cluster, live-check against a running cluster, no-static-credentials / no-edit-builtin / no-delete-while-attached guards |
| `test_04_queries.py`                  | Run queries & read results, browser row cap vs. larger CSV export cap, paginated result accumulation, query cancellation, failed-query error surfacing, running-cluster guard, query history |
| `test_05_query_workspace.py`          | Query tabs (default tab, create/rename/delete, last-tab recreation), saved queries (save/edit/delete), catalog/schema/table metadata browsing |
| `test_06_scaling_suspend.py`          | Autoscale up (queued queries), autoscale down (idle/low CPU), auto-suspend after idle window, autoscaling/auto-suspend poll endpoints |
| `test_07_users_rbac.py`               | Admin user management (create/list/promote/demote/deactivate/password reset), RBAC boundary (non-admin can query but not administer), last-admin protection |
| `test_08_security_access.py`          | Auth gating on protected routes, allowed-UI-CIDR enforcement (with loopback & health exemptions), signed node-config bootstrap token |

## How it works

`harness.py` provides `E2EHarness`, a context manager that spins up one
throwaway TrinoHub deployment per scenario:

- **Real app.** It builds the actual `TrinoHubApp` + FastAPI app and drives it
  over an in-process ASGI HTTP client (`HttpClient`) with cookie auth — so
  routing, validation, serialization, and the SQLite control-plane logic are
  all genuinely exercised.
- **`StatefulFakeAws`** replaces `AwsInspector`: it simulates the
  EC2/ASG/coordinator lifecycle in memory and records every cleanup call so
  suspend/disable/delete behavior can be asserted.
- **`FakeTrino`** replaces the coordinator's REST endpoint, returning
  Trino-shaped responses for the SQL the control plane issues. It can be steered
  per-test: `fail_next(...)`, `paginate([...])`, and `big_result(n)`.

Everything runs in a temp directory and is torn down automatically.

### Writing a new scenario

```python
import unittest
from testing.harness import E2EHarness

class MyScenario(unittest.TestCase):
    def setUp(self):
        self.h = E2EHarness()
        self.addCleanup(self.h.close)
        self.h.setup_admin()

    def test_something(self):
        cluster = self.h.create_running_cluster("demo", catalogs=["system", "tpch"])
        query = self.h.run_query(cluster["id"], "SELECT 1", catalog="tpch")
        self.assertEqual(query["status"], "Finished")
```

Add the file under `scenarios/` named `test_NN_*.py`; the runner and
`unittest discover` pick it up automatically. Useful harness helpers:
`setup_admin`, `login`/`logout`, `create_cluster`, `start_cluster`,
`refresh_health`, `create_running_cluster`, `suspend_cluster`,
`disable_cluster`, `delete_cluster`, `run_query`, and `s3_glue_config`. For
raw HTTP use `self.h.client.get/post/patch/delete`; to steer simulated AWS or
Trino use `self.h.aws` and `self.h.trino`.
