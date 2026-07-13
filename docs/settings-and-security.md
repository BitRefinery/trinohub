# Settings & security

The **Settings** view (admin only) shows how this TrinoHub instance is
configured, and the API references for integrators.

## AWS configuration

Settings displays the captured AWS context — region, VPC, node instance profile,
and the **allowed UI CIDRs** — along with the resolved preset tiers (the actual
instance types each preset maps to in your region). These values come from
first-run setup; AWS keys and secrets are never displayed.

## Cluster connectivity

The **Cluster connectivity** panel holds an account-wide **base domain** used to
build stable per-cluster connection strings — each cluster is addressed as
`<cluster-name>.<base-domain>` over HTTPS. TrinoHub only renders the hostname;
you own the wildcard DNS and TLS that make it resolve and connect. Leave it blank
to fall back to the coordinator's IP address. This feature has its own topic —
see **Cluster domains & connections**.

## Single sign-on, sessions, and API tokens

Settings also holds the identity and automation controls:

- **Single sign-on (OIDC)** — delegate authentication to Okta, Entra, Google,
  or a generic OIDC provider, with group-to-role mapping. See **Single sign-on
  (SSO)**.
- **Sessions** — set the browser session lifetime, and **sign out everywhere**
  to revoke your own active sessions.
- **API tokens** — long-lived bearer tokens for scripts and BI tools. See
  **Automation & API**.

## Result cache

The **Result cache** panel controls how long identical read-only re-runs are
served from the stored result set instead of re-executing on the cluster
(default **10 minutes**, maximum 24 hours, 0 disables). Cached results are
point-in-time snapshots, scoped per user, and never exceed the normal result
caps. See **Running queries → Cached results**.

## Notifications

The **Notifications** panel sends a JSON webhook (Slack-compatible) when
selected events occur: a cluster fails, suspends, or comes up; a scheduled job
fails after its retry; or a security-audit change happens. Paste a webhook URL,
pick the events, and save. Leave the URL blank to disable.

## API documentation

TrinoHub's control-plane API is a FastAPI app. From Settings you can open:

- **OpenAPI / Swagger UI** at `/docs` — interactive API reference.
- **OpenAPI schema** at `/openapi.json` — the machine-readable spec.

There is also a Prometheus **metrics** endpoint at `/metrics` and a read-only
**MCP** endpoint at `/mcp` — see **Automation & API**. (All of these are
separate from this in-app **Docs** section you're reading now.)

## Security model

TrinoHub is built to avoid storing secrets:

- **No AWS static credentials, ever.** The control plane authenticates with its
  EC2 **instance profile**, and passes a **node role** to cluster instances via
  `iam:PassRole`. The UI never shows AWS keys.
- **Data-source passwords live in AWS Secrets Manager.** When you save a catalog
  that needs a password, the plaintext is written to Secrets Manager and only
  the secret ARN is kept in the catalog config. Nodes resolve it at boot over
  the signed node-config channel — it never lands in EC2 user-data or the
  database. See **Catalogs & data sources**.
- **Allowed-UI-CIDR enforcement** at the application layer restricts who can
  reach the app. Loopback health and node-config traffic is exempt.
- **Signed, per-cluster bootstrap tokens** so each EC2 node can fetch only its
  own Trino configuration — and, when needed, its uploaded JDBC drivers.
- **Hashed passwords and http-only session cookies.** An expired or missing
  session returns you to the sign-in screen. API tokens are stored only as
  hashes and shown once.
- **Role-based access control** gates every screen and endpoint on the
  signed-in user's privileges and grants, and **fine-grained data policies**
  are enforced inside Trino itself. See **Users & roles** and **Data
  security**.
- **An append-only security audit log** records every user, role, grant,
  catalog, cluster, settings, token, and policy change.

## Uploaded connector drivers

Connectors whose JDBC driver isn't bundled (Oracle) accept an admin-uploaded
driver JAR. The bytes are held on the control-plane disk (not in the database),
and each node re-verifies the JAR's SHA-256 before Trino loads it, so a tampered
or truncated driver never runs. Uploads are admin-only and size-limited.

## Operational notes

State lives in a local SQLite database on the control-plane instance (users,
roles and grants, sessions and API tokens, clusters, catalogs, data policies,
scheduled jobs, query runs, utilization samples, events, the audit log, and AWS
resource mappings). Uploaded driver JARs are stored on disk alongside it.
Deleting a cluster terminates all of its tracked AWS resources, so treat
**Delete** as permanent.
