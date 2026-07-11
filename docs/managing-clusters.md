# Managing clusters

Admins create and operate Trino clusters from the **Clusters** view. Each
cluster is a coordinator plus workers, provisioned as tagged AWS resources
(`ManagedBy=TrinoHub`, `TrinoHubCluster=<name>`).

## Creating a cluster

Click **Create cluster** and fill in the form:

- **Name** — a unique, human-friendly identifier.
- **Instance type** — pick from the types an admin has enabled in **Settings**.
  Coordinator and workers use the same instance type.
- **Accelerated (warm cache)** — optionally cache hot S3 data on node-local
  NVMe for Hive/Iceberg/Delta catalogs. Requires an NVMe instance type and a
  fixed worker count; see **Accelerated clusters**.
- **Worker strategy** — either a **fixed** worker count or **Trino-aware
  autoscaling** with a min and max.
- **Auto-suspend** — how long the cluster may sit idle before its nodes are torn
  down (for example 15 / 30 / 60 minutes, or never).
- **Catalogs** — the data sources attached to this cluster. Built-ins are always
  available; each configured data catalog has its own checkbox, so you attach
  whichever subset this cluster should query.

If you attach a catalog whose connector needs an uploaded JDBC driver (for
example Oracle), upload that driver first — otherwise starting the cluster fails
fast with a clear message. See **Catalogs & data sources**.

A sticky **review / cost** panel summarizes the coordinator, workers, autoscaler,
and catalogs. Starting a cluster launches billable AWS resources, so you'll
confirm before it provisions.

## Lifecycle actions

From the table or a cluster's detail page:

- **Start / Resume** — bring a cluster up to *Running*.
- **Suspend** — tear down nodes but keep the definition.
- **Disable** — explicitly take a cluster out of service.
- **Edit** — change worker range, auto-suspend, catalogs, acceleration, or
  keep-warm uptime windows.
- **Delete** — **terminate all tracked AWS resources** for that cluster.

The detail page shows metric tiles (active workers, running queries, CPU,
auto-suspend), a **utilization chart** of the last 24 hours (worker CPU,
running queries, and worker count, from samples the poller persists), a
resource diagram, recent scaling events, and an estimated hourly plus 30-day
cost.

## Keep-warm uptime windows

An **uptime window** suppresses auto-suspend during set hours, so a cluster
stays warm for known busy periods regardless of idleness. Set them in the edit
dialog, one per line, in UTC — for example `mon-fri 08:00-18:00` or
`sat,sun 10:00-16:00`. Outside those windows, normal auto-suspend applies.

## Cost visibility

TrinoHub estimates spend from cluster activity — hourly from the instance type
and node count, and a **30-day total** reconstructed from each cluster's
running periods. This is visibility, not billing; actual charges come from AWS.
The cluster detail cost tile shows both, and `GET /api/costs` returns the
per-cluster breakdown for operators.

## Connecting clients

The **info** button (ⓘ) on a cluster row opens a **Connection info** popup with
copy-ready JDBC, ODBC, and CLI strings for that cluster. The host in those
strings is a stable DNS name when you've configured a base domain, or the live
coordinator IP otherwise. To give clusters durable hostnames for BI tools and
drivers, see **Cluster domains & connections**.

## How autoscaling works

TrinoHub's autoscaler is **Trino-aware**, not a raw CPU policy. It polls running
clusters every 30 seconds for worker health, running and queued queries, and CPU:

- **Scale up** by one worker when queued queries persist for 2 intervals, or
  average CPU exceeds 75% for 3 intervals — within `max` and a 3-minute cooldown.
- **Scale down** by one worker when there are no queued or running queries and
  CPU stays below 25% for 10 minutes — within `min` and a 10-minute cooldown.

## Auto-suspend and cold starts

When a cluster is idle past its auto-suspend interval, its nodes are torn down to
save money. The next query automatically resumes the cluster first. That cold
start re-downloads Java and Trino on each node and typically takes **3–5
minutes**.
