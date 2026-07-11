# TrinoHub clean-account validation gate

The "AMI-shippable" bar:

> Clean-account end-to-end: setup → create (each preset) → start → run SQL →
> autoscale → auto-suspend → resume → disable → delete, with zero manual SG edits.
> `python -m unittest discover -s tests` green.

This directory ships `validate_clean_account.py`, a stdlib-only driver that
exercises the scriptable parts of that gate against a running control plane.
Autoscale-under-load is observational and is covered as a manual step below.

## Prerequisites

- A fresh AWS account (or a clean VPC) with the control-plane instance running
  TrinoHub under the IAM role from `iam-control-plane-policy.json`, and a node
  instance profile attached to `iam-node-role-policy.json`.
- Source-credential storage: the control-plane policy grants Secrets Manager
  access (`CreateSecret`/`PutSecretValue`/`GetSecretValue`/`DescribeSecret`/
  `DeleteSecret`) scoped to `trinohub/catalog/*`. Credentialed catalogs (e.g.
  PostgreSQL) store their password in Secrets Manager — only the secret ARN is
  kept in TrinoHub's DB, and the password is resolved into the per-node config
  served over the token-authenticated `/api/node-config` endpoint, never embedded
  in EC2 user-data. The **node** instance profile needs no Secrets Manager access.
- The service is up: `systemctl status trinohub`, `GET /api/health` → `{"ok": true}`.
- The first-run **setup token** (only needed if setup is not yet complete):

  ```bash
  sudo cat /sites/trinohub/.trinohub/setup-token   # or: journalctl -u trinohub | grep "Setup token"
  ```

## 0. Unit suite (run first)

```bash
cd /sites/trinohub
.venv/bin/python -m unittest discover -s tests      # expect: OK
```

Bare `python3` skips the FastAPI route tests — use the `.venv` interpreter.

## 1. Automated lifecycle

> ⚠️ This launches **billable** EC2 capacity. Each cluster is deleted in a
> `finally` block, but a crash can still leave resources — check the Clusters
> page (and the EC2 console) afterward.

```bash
.venv/bin/python deploy/validate_clean_account.py \
    --base-url http://localhost:8000 \
    --admin-user admin --admin-pass '<password>' \
    --setup-token "$(sudo cat /sites/trinohub/.trinohub/setup-token)" \
    --region us-east-2 \
    --presets Cost Balanced Power \
    --test-truncation --test-auto-suspend \
    --confirm-billing
```

Per preset it verifies, **with zero manual SG edits**:

| Step | Check |
|------|-------|
| create | `POST /api/clusters` → 201; preset maps to a real instance type |
| start | `POST …/start` → 200, then status reaches `Running` (cold start, up to `--start-timeout`) |
| SQL | `SELECT … FROM tpch.sf1.nation LIMIT 5` returns 5 rows over the control-plane→coordinator path (the P0.1 gate) |
| edit | `PATCH …` raises `max_workers`; `applied_live` includes it (live ASG resize, no rebuild) |
| suspend | `POST …/suspend` → 200, status reaches `Suspended`, tracked resources cleaned |
| resume | `POST …/start` again → `Running`, a follow-up `SELECT` finishes |
| disable | `POST …/disable` → 200, status reaches `Not enabled`, tracked runtime resources cleaned |
| delete | `DELETE …` → 200, **zero residual resources** |

Optional flags:
- `--test-truncation` — runs a >1000-row query (`tpch.tiny.orders`) and asserts
  `truncated=true`, `row_count=1000`, `total_row_count>1000` (P1.4). The browser
  result cap is 1,000 rows or 10 MB; CSV retains a larger capped export buffer.
- `--test-auto-suspend` — creates a 1-min-auto-suspend cluster, leaves it idle,
  and waits for the poller to flip it to `Suspended` (P2.3). Adds several minutes
  of wall-clock.

A non-zero exit code or any `FAIL` line means the gate is not met; the summary
lists the failed steps.

## 2. Manual step — autoscale under load

The autoscaler reacts to live Trino queued-query / CPU pressure, which the driver
can't synthesize cheaply. To validate by hand:

1. Start an autoscale cluster (`min_workers=1`, `max_workers≥2`) and wait for `Running`.
2. From the Query page, submit several concurrent heavy queries, e.g.
   `SELECT count(*) FROM tpch.sf1000.lineitem` a few times in parallel.
3. Watch the cluster detail / `scaling_events`: within a couple of poll intervals
   the worker desired capacity should scale **up** toward `max_workers`.
4. Stop submitting; after the idle window the autoscaler should scale back **down**
   toward `min_workers`.
5. Suspend or delete the cluster when done.

## 3. Teardown sanity

After the run, confirm nothing is left billing:

- Clusters page shows no `p-verify-*` clusters.
- EC2 console: no running instances, launch templates, or Auto Scaling Groups
  tagged for those clusters; the managed node security groups are gone.

When 0, 1, and 2 all pass on a clean account, the validation gate is met.
