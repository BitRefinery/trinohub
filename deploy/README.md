# TrinoHub Deployment Artifacts

These files run the FastAPI control plane with a local virtual environment and put nginx in front of the app.

For a clean-account end-to-end validation (the "AMI-shippable" gate), see `VALIDATION.md` and the `validate_clean_account.py` driver in this directory.

## systemd

1.  Confirm `/sites/trinohub` is owned by the service user, or edit `User=` and `Group=` in `trinohub.service`.
2.  Create or refresh the local runtime environment:

    ```bash
    sudo apt-get update
    sudo apt-get install -y python3-venv python3-pip
    cd /sites/trinohub
    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
    ```

    `python3-venv` and `python3-pip` are only needed to build or refresh `.venv`. The systemd service runs from `.venv` and does not require system-wide Python packages.

3.  Install the service:

    ```bash
    sudo cp /sites/trinohub/deploy/trinohub.service /etc/systemd/system/trinohub.service
    sudo systemctl daemon-reload
    sudo systemctl enable --now trinohub
    sudo systemctl status trinohub
    ```

The service binds the app to `0.0.0.0:8000` so the EC2 security group allowlist remains the network boundary and the app is reachable without a separate local-only development process.

FastAPI serves the UI, `/api/*` JSON routes, `/docs`, and `/openapi.json` from the same process.

### UI CIDR allowlist

During first-run setup, `allowed_ui_cidrs` is normalized and stored in SQLite. If one or more ranges are configured, the app rejects UI/API requests whose direct client IP is outside the allowlist. Loopback traffic is always allowed for local health checks and nginx-to-app proxying. `X-Forwarded-For` is trusted only from loopback peers, so direct clients cannot spoof their way through the application check. Keep the EC2 security group allowlist narrow as the primary boundary; the app check is a second layer.

### First-run setup token

To stop a network attacker from winning the "first admin" race on a freshly exposed instance, `/api/setup/complete` requires a one-time **setup token** until setup is done. On first boot (while setup is pending) the control plane mints the token, prints it to the service log, and writes it to a root-only file:

```bash
sudo journalctl -u trinohub | grep "Setup token"
# or
sudo cat /sites/trinohub/.trinohub/setup-token
```

Paste it into the **Setup token** field of the setup wizard (or include `"setup_token": "…"` in the `POST /api/setup/complete` body). The token is consumed once setup completes. To rotate it before setup, delete the file — the next start mints a fresh one.

### Background poller

The control plane runs a background loop (health, autoscaling, auto-suspend) inside the app process. The shipped unit runs a single uvicorn process, which is the intended deployment. If you scale to multiple workers, a host-local advisory lock (`/sites/trinohub/.trinohub/trinohub-poller.lock`) ensures only one process runs the poller, so workers do not make conflicting scaling decisions. Set `TRINOHUB_ENABLE_POLLER=0` to disable the poller in a process (for example, to run a dedicated poller elsewhere).

The poller's idle/autoscale timers are persisted to the database (`cluster_timer_state`), so a control-plane restart does not reset the auto-suspend idle clock — clusters still suspend on schedule across restarts.

### Cold start on resume

Suspending a cluster terminates its coordinator and workers. Starting or resuming a cluster launches fresh EC2 instances that download the JDK and Trino on first boot, so a started cluster typically takes **~3–5 minutes** to reach `Running`. The UI shows a "resuming" hint on clusters in the `Starting` state and auto-refreshes their status. (A pre-baked node AMI to shorten this is post-MVP per the PRD.)

### Node bootstrap config

Starting a cluster mints a per-cluster bootstrap token and embeds it in EC2 user data. Coordinator and worker nodes use that signed URL to fetch `/api/node-config/<cluster_id>` from the control plane on port `8000`, then write Trino config locally. SQLite stores only the token hash, and suspend/disable/delete clear the token. The managed node security group authorizes nodes to reach the control plane for this private config fetch.

If the control-plane private IP cannot be discovered, user data falls back to embedding the generated node config directly so startup still works in constrained environments.

### Query result caps

The browser result table stores at most 1,000 rows or 10 MB per query. CSV download uses the backend `/api/query/:id/csv` stream and retains a larger MVP export buffer: up to 10,000 rows or 50 MB. The CSV response includes `X-TrinoHub-CSV-Rows` and `X-TrinoHub-CSV-Truncated` headers.

### Cluster disable

`POST /api/clusters/:id/disable` cleans up tracked runtime resources and leaves the cluster record in `Not enabled` so configuration can be edited and started later. `Suspend` marks the stopped cluster `Suspended`; `Disable` is the stronger "off but keep the definition" operation.

### Optional SSH access to nodes

TrinoHub does not need SSH — the control plane reaches coordinators over HTTP. By default, launched nodes get **no** EC2 key pair. For break-glass SSH, set `TRINOHUB_SSH_KEY_NAME` (e.g. in `trinohub.service`) to the name of an existing EC2 key pair in the cluster's region; it is attached only if that key actually exists, otherwise nodes launch without a key.

## nginx

1.  Install nginx if needed:

    ```bash
    sudo apt-get update
    sudo apt-get install -y nginx
    ```

2.  Enable the site:

    ```bash
    sudo cp /sites/trinohub/deploy/nginx-trinohub.conf /etc/nginx/sites-available/trinohub
    sudo ln -sfn /etc/nginx/sites-available/trinohub /etc/nginx/sites-enabled/trinohub
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t
    sudo systemctl reload nginx
    ```

Keep the EC2 security group allowlist narrow. Add TLS before opening the UI beyond a private or trusted network.

## IAM

TrinoHub uses instance profiles only; it never stores static AWS credentials. Two
roles are involved.

### Control-plane role

Attach `deploy/iam-control-plane-policy.json` to the role used by the control-plane
EC2 instance profile (the PRD names this `TrinoHubControlPlaneRole`). The policy is
least-privilege, derived from the exact API calls the app makes:

- **Discovery (read):** `sts:GetCallerIdentity`; `ec2:Describe*` for VPCs, subnets,
  security groups, images, key pairs, instances; `autoscaling:DescribeAutoScalingGroups`;
  `cloudwatch:ListMetrics` and `cloudwatch:GetMetricStatistics` (autoscaler signals).
- **Cluster compute (write):** `ec2:RunInstances`, `TerminateInstances`, `CreateTags`,
  `Create/DeleteSecurityGroup`, `Authorize/RevokeSecurityGroupIngress`,
  `Create/DeleteLaunchTemplate`; `autoscaling:Create/Update/DeleteAutoScalingGroup`.
- **`iam:PassRole`** scoped to the node role, conditioned on
  `iam:PassedToService = ec2.amazonaws.com` — required to launch nodes and create the
  worker launch template with the node instance profile.
- **`iam:CreateServiceLinkedRole`** for `autoscaling.amazonaws.com` — needed the first
  time an Auto Scaling Group is created in the account.

Replace `ACCOUNT_ID` (and the node role name, if you changed it from `TrinoHubNodeRole`)
before attaching. The `Resource: "*"` entries cover EC2/AutoScaling/CloudWatch actions
that do not support resource-level scoping for describe calls; you can tighten the
mutating actions later with `aws:RequestTag`/`aws:ResourceTag` conditions on
`ManagedBy=TrinoHub`.

### Node role

Attach `deploy/iam-node-role-policy.json` to `TrinoHubNodeRole` (the instance profile
passed to coordinator and worker nodes). It grants S3 + Glue access for Iceberg
catalogs and is scoped to a single warehouse bucket:

- Replace `WAREHOUSE_BUCKET`, `REGION`, and `ACCOUNT_ID`.
- For `read_only` catalogs, drop the write actions (`s3:PutObject`, `s3:DeleteObject`,
  and the Glue `Create*`/`Update*`/`Delete*` actions).
- The node role's **trust policy** must allow `ec2.amazonaws.com` to assume it
  (`sts:AssumeRole`); that is separate from this permissions policy.

TrinoHub does not store S3 access keys — node access comes entirely from this role.

## AMI cleanup

Before checking this source into GitHub or creating a reusable AMI, keep runtime state and secrets out of the image:

- Do not include private keys, `.env` files, `.trinohub/`, Python caches, or local logs.
- Remove active sessions from `.trinohub/trinohub.sqlite3` if reusing the current configured database.
- Delete `.trinohub/trinohub.sqlite3` before imaging if the AMI should boot into first-run setup.
- Keep AWS access through instance profiles only; do not add static AWS credentials.
