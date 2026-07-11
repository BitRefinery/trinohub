# Cluster domains & connections

Every cluster can hand out a **connection string** — a JDBC URL, ODBC string, or
CLI command — that a BI tool, notebook, or driver uses to reach Trino. Open it
from the **info** button (ⓘ) on any row of the **Clusters** view.

The address in that string depends on whether you've configured a **base
domain**. This page explains how the address is chosen, how to set the domain
up, and what DNS/TLS you own versus what TrinoHub renders for you.

## Why set a base domain?

A cluster's coordinator runs on an AWS instance whose **IP address is
ephemeral** — it changes every time the cluster is suspended and resumed, or a
node is replaced. An IP is fine for a quick internal test, but you would not want
to paste it into a dashboard that has to keep working next week.

A base domain gives every cluster a **stable hostname** derived from its name, so
the connection string never changes even as the underlying instances come and go.
This mirrors how hosted Trino platforms address clusters
(`<cluster-name>.trino.<their-domain>`).

## How the address is chosen

For each cluster, TrinoHub resolves the connection host in this order:

| Priority | Source | Example | Endpoint |
|---|---|---|---|
| 1 | Per-cluster **hostname override** | `analytics-prod.acme.internal` | HTTPS / 443 |
| 2 | Derived from the **base domain** | `<cluster-name>.trino.acme.internal` | HTTPS / 443 |
| 3 | Live **coordinator IP** (fallback) | `10.0.3.14` | HTTP / 8080 |

- A cluster named `lakehouse` with base domain `trino.acme.internal` is addressed
  as **`lakehouse.trino.acme.internal`**.
- A domain- or override-based host is assumed to be **secured with TLS** and is
  rendered on **port 443** with SSL enabled.
- The **coordinator IP** fallback is the raw internal endpoint (**HTTP, port
  8080**) and only exists while the cluster is *Running*. If there's no domain and
  no running coordinator, the popup shows a short hint instead of a broken string.

## Setting the base domain

In **Settings → Cluster connectivity**, enter your domain (for example
`trino.acme.internal`) and click **Save**. The value is normalized (lowercased,
trailing dot removed). Leave it blank to clear it and fall back to coordinator
IPs.

This is an account-wide setting and applies to every cluster at once.

## DNS: you own resolution

**TrinoHub renders the hostname; it does not create DNS records.** Setting a base
domain does not make `lakehouse.trino.acme.internal` resolve on its own — you have
to point DNS at your coordinators.

The simplest approach is a **wildcard record** for the base domain:

```
*.trino.acme.internal   →   your coordinators (or a load balancer in front of them)
```

so that every current and future cluster name resolves without per-cluster DNS
changes. In AWS this is typically a Route 53 record set in a private or public
hosted zone. Because clusters suspend/resume and replace nodes, point the record
at a **stable target** (an internal load balancer or an Elastic IP) rather than a
raw instance IP.

## TLS: the built-in Let's Encrypt gateway

Trino coordinators serve **plain HTTP on port 8080** inside your VPC, so a
`https://…:443` connection string needs something in front to terminate TLS.
TrinoHub can run that for you: a **Caddy** reverse proxy on the control-plane
instance that obtains **Let's Encrypt** certificates automatically and forwards
each `<cluster>.<base-domain>` to that cluster's coordinator. TrinoHub keeps the
proxy's routing in sync as clusters start, get replaced by autoscaling, and
suspend — you never edit its config by hand.

To enable it, the operator does a one-time setup on the control-plane instance:

1. **Install Caddy** (its standard package) and start it. TrinoHub talks to
   Caddy's local admin API at `127.0.0.1:2019` and pushes the config; it never
   needs the Caddyfile edited manually.
2. **Open the instance's security group** for inbound **80** (Let's Encrypt's
   HTTP-01 challenge — must be reachable from the public internet) and **443**
   (client connections). Port 8000 (the admin UI) is unchanged.
3. **Set the base domain** in Settings. From then on, TrinoHub pushes routes
   automatically; admins can force a refresh from **Settings** or
   `POST /api/tls/gateway/sync`.

Certificates are issued **on demand**: the first time a client connects to
`lakehouse.trino.acme.internal`, Caddy asks TrinoHub whether that name belongs to
a real cluster before requesting a certificate, so random hostnames can't trigger
issuance.

**Access is still restricted.** The gateway only accepts client connections from
your **allowed UI CIDRs** (the same ranges that gate the app) — everything else
is refused at the proxy. This matters because Trino coordinators have **no client
authentication of their own yet**, so the CIDR allow-list is what keeps a
TLS-exposed cluster from being an open, queryable endpoint. Keep those ranges
tight, and treat broadening them as granting query access.

Prefer to manage TLS yourself instead? Leave Caddy uninstalled and put your own
edge in front — an Application Load Balancer with an **ACM** certificate, or any
reverse proxy. (Note ACM certificates only attach to AWS load balancers and
CloudFront; they can't be installed on a self-run proxy, which is why the built-in
gateway uses Let's Encrypt.) Either way, until TLS is terminated, leave the base
domain blank and use the coordinator-IP fallback for internal HTTP testing.

## Per-cluster hostname override

Most clusters should just inherit the derived `<name>.<base-domain>` host. If one
cluster needs a specific name that doesn't follow the pattern — say a long-lived
production endpoint — set a **hostname** override on that cluster (in the create
or edit form). The override wins over the derived name and is also assumed to sit
behind TLS on port 443.

## The Connection info popup

The **info** button (ⓘ) on a cluster row opens a popup with copy-to-clipboard
fields, tailored to the resolved host:

- **JDBC URL** — e.g. `jdbc:trino://lakehouse.trino.acme.internal:443?user=you&SSL=true`
- **ODBC** — a `Driver={Trino ODBC Driver};Host=…;Port=…;SSL=…` connection string
- **CLI** — a ready-to-run `trino --server … --user …` command
- **Host**, **Port**, and **User** as individual fields

The **User** is your current TrinoHub username, so each person copies a string
scoped to themselves. The popup is available to everyone — analysts can grab a
connection string without admin access — while the base domain itself is
configured by admins.

## Worked example: `trinohub.org`

This walks through a real setup end to end. Substitute your own values — here the
domain is **`trinohub.org`** and the instance's public IP is
**`18.226.13.189`**. Each step notes whether you can verify it right away.

**1. Set the base domain.** In **Settings → Cluster connectivity**, enter
`trino.trinohub.org` and click **Save**. A cluster named `lakehouse` is now
addressed as **`lakehouse.trino.trinohub.org`**. Verify immediately: open the
cluster's **info** popup (ⓘ) — the **Host** field should read
`lakehouse.trino.trinohub.org`.

**2. Point DNS at your instance.** In your `trinohub.org` DNS zone (for example
AWS Route 53), add a **wildcard A record** so every cluster name resolves without
per-cluster changes:

```
*.trino.trinohub.org.   A   18.226.13.189
```

(Prefer not to use a wildcard? Add one record per cluster instead, e.g.
`lakehouse.trino.trinohub.org  A  18.226.13.189`.) In a multi-node deployment,
point the record at a load balancer rather than a single instance; for a
single-box test, the instance IP is fine.

**3. Verify DNS resolves** — testable as soon as the record propagates:

```
dig +short lakehouse.trino.trinohub.org
# → 18.226.13.189
```

**4. Terminate TLS with the built-in gateway.** Let TrinoHub run Let's Encrypt for
you (see *The built-in Let's Encrypt gateway* above). On the instance:

```
# install Caddy (Debian/Ubuntu shown; use your distro's package)
sudo apt install -y caddy

# open inbound 80 (Let's Encrypt challenge) and 443 (clients) on the
# instance's security group — e.g. with the AWS CLI:
aws ec2 authorize-security-group-ingress --group-id <control-plane-sg> \
  --ip-permissions IpProtocol=tcp,FromPort=80,ToPort=80,IpRanges='[{CidrIp=0.0.0.0/0}]'
aws ec2 authorize-security-group-ingress --group-id <control-plane-sg> \
  --ip-permissions IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges='[{CidrIp=0.0.0.0/0}]'
```

You don't write a Caddyfile — with the base domain set (step 1), TrinoHub already
pushed the routing to Caddy, mapping `lakehouse.trino.trinohub.org` to the
coordinator and gating clients to your allowed CIDRs. The certificate is issued
automatically on your first `https` connection. (Force a re-push any time with
`POST /api/tls/gateway/sync`.)

Because certs are issued via the HTTP-01 challenge on port 80, your wildcard
record from step 2 already points the right names at this instance — nothing more
to configure.

**5. Connect.** Copy the JDBC URL from the **info** popup into your client:

```
jdbc:trino://lakehouse.trino.trinohub.org:443?user=you&SSL=true
```

**Smoke-test Trino before TLS.** To confirm the coordinator is up before wiring
certificates, clear the base domain — the popup falls back to
`http://COORDINATOR_IP:8080`. That endpoint is a private VPC address, reachable
with the Trino CLI **from inside the VPC** (for example SSH'd onto the instance):

```
trino --server http://COORDINATOR_IP:8080 --user you
```

Once that works, set the base domain again and finish the TLS step so external
clients can connect over `https`.

## What TrinoHub does and does not do

- **Does:** derive a stable hostname per cluster, build correct JDBC/ODBC/CLI
  strings, fall back to the live coordinator IP when no domain is set, and — once
  you install Caddy — run a **Let's Encrypt TLS gateway** that issues certificates
  and routes each cluster hostname to its coordinator, gated to your allowed CIDRs.
- **Does not:** create or manage **DNS records** (you own the wildcard record),
  provision AWS load balancers, or add **Trino client authentication** (the CIDR
  allow-list is today's access control). Those remain yours to manage.

See also **Managing clusters** and **Settings & security**.
