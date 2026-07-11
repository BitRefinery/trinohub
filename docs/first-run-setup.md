# First-run setup

The first time TrinoHub starts on a fresh instance, it shows a **5-step setup
wizard** instead of the sign-in screen. Completing it creates the first admin
and configures AWS access.

## Before you start

TrinoHub authenticates to AWS using the **EC2 instance profile** of the control
plane (it never stores AWS access keys). Make sure the instance has the control
plane role attached and that the node role exists so clusters can be launched
via `iam:PassRole`.

## The setup token

To prevent a network attacker from winning the "first admin" race on a freshly
exposed instance, setup requires a one-time **setup token**. TrinoHub prints it
to the service log and writes it to a root-only file on the instance when it
starts up unconfigured. You'll paste it during the Admin step.

## The five steps

1. **Status** — checks the instance profile, confirms the local database is
   ready, and shows your UI network status.
2. **Admin** — create the first administrator (username, email, password) and
   provide the setup token.
3. **AWS** — choose the region, confirm the control-plane role, set the node
   instance profile, and run validation (STS identity plus EC2 / Auto Scaling
   permission checks).
4. **Network** — select the VPC, private subnets, and security group, and set
   the **allowed UI CIDRs** that may reach the app.
5. **Review** — confirm everything and finish.

A readiness checklist on the right tracks IAM, the control plane, and (later)
coordinator/worker health. Setup is gated on full AWS validation plus an EC2
launch dry-run, so a green finish means you can actually provision clusters.

## After setup

Once an admin exists, the wizard disappears and TrinoHub shows the normal
sign-in screen. From there you can create users, clusters, and catalogs.
