# Accelerated clusters (warm NVMe cache)

Accelerated clusters keep hot S3 data on node-local NVMe disks using Trino's
built-in file system cache, so repeated scans of the same tables read from
local SSD instead of S3. This is TrinoHub's open-source answer to proprietary
"warp speed" data caching.

## How it works

- Workers cache the file pages they read (1 MB pages) on local NVMe, and the
  scheduler routes work for a given file to the nodes that already hold it.
- The cache applies to **Hive, Iceberg, and Delta Lake** catalogs. Hudi is not
  supported upstream, and JDBC/other connectors don't read from S3 at all.
- Each cached catalog gets its own cache directory, and the disk budget is
  split evenly across them. Cached data expires after 7 days by default.
- The coordinator caches too — every node in an accelerated cluster needs
  local NVMe.

## Instance types

The regular r/m-family types are EBS-only and cannot host the cache. Enable
one of the NVMe instance-store types in Settings → Node instance types:

| Family | Shape | Local NVMe | Role |
|---|---|---|---|
| **i4i** (recommended) | same 8 GiB RAM/vCPU as the R family | 468 GB (large) – 3,750 GB (4xlarge) | Default accelerated tier: Nitro SSDs, wide availability |
| r6id | same shape as r6i | 237–474 GB | Budget cache tier (~20% over r6i) |
| i3en | 8 GiB/vCPU | 2,500–5,000 GB | Max cache capacity per dollar |

Expect roughly a 20–36% per-node premium over the equivalent EBS-only type.

## When it pays off

Caching helps when the same S3 data is scanned repeatedly — dashboards, BI
tools, iterative ad-hoc analysis over hot tables. It does little for one-shot
queries or workloads that scan different data every time; in that case the
premium buys nothing and a regular cluster is the better choice.

## Interactions to know about

- **Suspend wipes the cache.** Instance-store disks are erased when nodes
  terminate, so every resume starts cold. Accelerated clusters therefore
  default to a 4-hour auto-suspend; pick "Never" for latency-critical
  workloads that must always be warm.
- **Fixed workers required.** Autoscaling reshuffles which node caches which
  file and dilutes the cache, so accelerated clusters use a fixed worker
  count.
- **Toggling acceleration needs a restart.** The cache disks and catalog
  properties are configured when nodes boot, so changes apply on the next
  cluster start.
