# Deploy TrinoHub on AWS (one stack)

`cloudformation.yaml` launches a working TrinoHub control plane: it creates the
IAM roles (instance-profile auth — **no static AWS keys**), a security group, and
an EC2 instance that installs and starts the app. From there you launch and manage
Trino clusters in the browser.

## What it creates

| Resource | Purpose |
|---|---|
| `TrinoHubControlPlaneRole` (+ instance profile) | The role the app runs as. Least-privilege EC2/ASG/CloudWatch/Secrets access + SSM Session Manager. |
| `TrinoHubNodeRole` (+ instance profile) | Passed to Trino cluster nodes for S3 + Glue (Iceberg) access, scoped to your warehouse bucket. |
| Security group | UI reachable only from the CIDR you pass. |
| EC2 instance (Ubuntu 24.04) | Runs `uvicorn trinohub.api:app` behind nginx via systemd. |

## Prerequisites

- An AWS account and permission to create IAM roles + EC2 (an admin/poweruser).
- A **VPC** and a **public subnet** (auto-assign public IP).
- Your **public IP** for the UI allowlist (`curl -s https://checkip.amazonaws.com`).

## Launch (console)

1. Save `cloudformation.yaml` (or use the raw GitHub URL).
2. CloudFormation → **Create stack** → **Upload a template file** → pick the file.
3. Fill parameters:
   - **VpcId / SubnetId** — your VPC and a public subnet.
   - **AllowedUiCidr** — `YOUR.IP.ADDR.ESS/32`.
   - **RepoUrl** — `https://github.com/BitRefinery/trinohub.git` (defaults there).
   - **WarehouseBucket** — your S3 bucket for Iceberg catalogs (or leave the
     placeholder and update the stack later).
   - **SshKeyName** — optional; leave blank (use Session Manager instead).
4. Acknowledge "This template creates IAM resources", **Create stack**.
5. When status is `CREATE_COMPLETE`, open the **Outputs** tab → **UiUrl**.

## Launch (CLI)

```bash
aws cloudformation deploy \
  --stack-name trinohub \
  --template-file cloudformation.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
      VpcId=vpc-xxxx SubnetId=subnet-xxxx \
      AllowedUiCidr="$(curl -s https://checkip.amazonaws.com)/32" \
      RepoUrl=https://github.com/BitRefinery/trinohub.git \
      WarehouseBucket=my-iceberg-bucket

aws cloudformation describe-stacks --stack-name trinohub \
  --query 'Stacks[0].Outputs' --output table
```

## First-run setup token

To stop a stranger from grabbing the first admin account, the wizard requires a
one-time token that's only printed on the box. Retrieve it **without SSH** via SSM
Session Manager:

1. EC2 → the `trinohub-control-plane` instance → **Connect** → **Session Manager** → **Connect**.
2. Run:
   ```bash
   sudo cat /opt/trinohub/app/.trinohub/setup-token
   # or:  sudo journalctl -u trinohub | grep "Setup token"
   ```
3. Paste it into the **Setup token** field of the wizard at the **UiUrl**.

(The instance may take ~2 minutes after `CREATE_COMPLETE` to finish installing.
If the page doesn't load yet, wait and retry.)

## After setup

- Complete the wizard (admin account, AWS region, the UI CIDR allowlist).
- Create your first cluster. Nodes take ~3–5 min to reach `Running` on first boot.
- Put **TLS in front** before exposing the UI beyond a trusted network — the
  shipped nginx config is HTTP only. Terminate TLS at an ALB or add certs to nginx.

## Updating

Push a new tag/commit, then update the stack with a new `GitRef`, or SSM in and:

```bash
cd /opt/trinohub/app && sudo -u trinohub git pull && sudo systemctl restart trinohub
```

## Teardown

Deleting the stack removes the instance, security group, and IAM roles. **It does
not terminate Trino clusters you created** — delete those from the TrinoHub UI
first (each cluster's Delete terminates all its tracked AWS resources), otherwise
they keep running and billing.

## Baking an AMI (optional, faster boot)

The stack installs at boot (~2 min). To ship a pre-baked AMI instead: launch once,
let it install, then **clean runtime state before imaging** — delete
`.trinohub/trinohub.sqlite3` (so it boots into first-run setup), remove logs and
`__pycache__`, and confirm no `.env`/keys are present. See `../README.md` →
"AMI cleanup". Then create an image from the instance and point a launch template
at it. Publishing to the AWS Marketplace is a separate, heavier process and is
out of scope for this guide.
