# Understanding clusters

A **cluster** is a Trino coordinator plus its workers, running on AWS. If you
only run queries you don't manage clusters, but you do choose which one runs
your queries, so it helps to understand their state.

## The clusters view

The **Clusters** view is a searchable, filterable table showing each cluster's
name, status, instance type, region, worker count, autoscaling, auto-suspend
setting, and owner. Click a row to open its detail page (metrics, utilization,
and recent scaling events).

## What the statuses mean

| Status | Meaning |
|---|---|
| Not enabled | Defined but never started; no AWS resources running. |
| Creating | Initial AWS resources are being provisioned. |
| Starting | Nodes are booting (see cold start below). |
| Running | Ready to accept queries. |
| Scaling | Adding or removing workers automatically. |
| Suspending | Shutting down idle nodes. |
| Suspended | Idle; no nodes running. A query will resume it first. |
| Updating | Applying configuration changes. |
| Failed | Something went wrong; an admin needs to look. |
| Deleting | All tracked AWS resources are being torn down. |

## Picking a cluster

To run a query the cluster must be **Running**. In the SQL editor and notebooks,
the cluster selector lists the clusters your roles grant you access to.

## Cold starts

To save money, clusters can **auto-suspend** when idle. The first query against
a suspended cluster automatically **resumes** it. Because each node re-downloads
Java and Trino on first boot, this "cold start" typically takes **3–5 minutes**.
The UI tells you when a cluster is resuming — just wait for it to reach
*Running*, then run your query.

If a cluster is autoscaling, it adds workers when queries queue up and removes
them when things go quiet, so performance adjusts to demand automatically.

## Connecting other tools

Besides the built-in SQL editor and notebooks, you can point an external client —
a BI tool, driver, or the Trino CLI — at a cluster. Click the **info** button (ⓘ)
on a cluster row to open its **Connection info** popup, then copy the ready-made
JDBC URL, ODBC string, or CLI command. Each string is scoped to your username. If
the fields aren't available yet, an admin may still need to set up a cluster
domain or start the cluster.
