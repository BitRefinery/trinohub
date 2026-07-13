# Automation & API

TrinoHub is fully drivable by API, so scripts, BI tools, and AI assistants can
do anything the UI does. Three surfaces matter: **API tokens**, the **MCP
server**, and the **Prometheus metrics** endpoint.

## API tokens

Every `/api/*` endpoint accepts a **bearer token** in place of a browser
session:

```
Authorization: Bearer tht_xxxxxxxx…
```

Create tokens from the **API tokens** panel in **Settings**. A token:

- Acts as **its user** and inherits that user's roles, grants, and data
  policies — so scope access by choosing whose token it is.
- Is shown **once** at creation and stored only as a hash; copy it then.
- Can have an optional expiry, and can be revoked at any time.

Any user can create tokens for themselves; users with `MANAGE_USERS` can mint
tokens for other users, including **service accounts** (token-only identities —
see **Users & roles**). Use a service account as the identity for unattended
automation.

## MCP server

TrinoHub exposes a **Model Context Protocol** endpoint at `/mcp` so AI clients
(Claude, Copilot, and other MCP hosts) can explore and query your data safely.
It speaks JSON-RPC over HTTP and authenticates with the same session or API
token as the rest of the API, so an MCP client acts as its user under that
user's grants.

Three tools are exposed:

- **list_clusters** — the clusters you can query.
- **browse_metadata** — drill through catalogs, schemas, tables, and columns.
- **run_query** — run **one read-only `SELECT`** and get the rows back.

`run_query` passes through the same read-only boundary as **Ask Trino**: any
write or DDL statement is rejected before it reaches Trino. An MCP client can
read your data but never modify it.

Identical re-runs inside the result-cache window may be served from the stored
result set; the response then carries `cached: true` and `result_cached_at`.
Pass `fresh: true` to force re-execution — useful when polling for change.

To connect, point your MCP host at `https://<your-trinohub-host>/mcp` with an
`Authorization: Bearer` header carrying an API token.

## Prometheus metrics

The control plane exports metrics in Prometheus format at `/metrics`, scraped
with an API token:

```
Authorization: Bearer tht_xxxxxxxx…
```

It publishes cluster lifecycle state, per-cluster utilization gauges (workers,
running/queued queries, CPU, and cache hit rate on accelerated clusters), and
counters for queries, autoscaling actions, and scheduled-job runs. Point your
Prometheus/Grafana or Datadog agent at it to dashboard and alert on TrinoHub
itself.

## OpenAPI

The full control-plane API has an interactive reference at `/docs` (Swagger UI)
and a machine-readable spec at `/openapi.json`, both linked from **Settings**.
