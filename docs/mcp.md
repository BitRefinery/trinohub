# MCP server

TrinoHub exposes a **Model Context Protocol** endpoint at `/mcp` so AI clients
(Claude, Copilot, and other MCP hosts) can explore and query your data safely.
It speaks JSON-RPC over the Streamable HTTP transport and authenticates with the
same session or API token as the rest of the API, so an MCP client acts as its
user under that user's grants.

Protocol revisions `2025-03-26`, `2025-06-18`, and `2025-11-25` are supported;
the version is negotiated at `initialize` and `2025-06-18` is offered to clients
that ask for anything else. From `2025-06-18` onwards a client echoes the
negotiated revision in an `MCP-Protocol-Version` header, which is validated on
every later request.

## Tools

Eight tools, in four groups.

### Discovery

- **list_clusters** — the clusters you can query, with status and catalogs.
- **browse_metadata** — drill through catalogs, schemas, tables, and columns.

### Query

- **run_query** — run **one read-only statement** on a cluster and get the rows
  back.
- **get_query_result** — keep waiting on a query that is still running.
  `run_query` stops polling after about 12 seconds and returns
  `status: "running"` with a `query_id`; pass that id here and repeat until the
  status is no longer `running`, instead of losing the query.

### Query templates

- **list_query_templates** — the curated, parameterized queries you can run,
  with each one's declared parameters.
- **run_query_template** — run one by name, supplying **typed values only,
  never SQL**.

Disabled templates, and templates on clusters you have no grant for, are left
out of the list — for an agent this list is the menu of what it may do, so it
must not advertise a call that will fail. See **Data products & query
templates**.

### Data products

- **search_data_products** — keyword search across names, summaries,
  descriptions, tags, and assets. This is how an agent finds the right data
  instead of guessing from raw catalog metadata.
- **get_data_product** — the full record for one product, including every asset
  with its description and view definition.

Products you have no cluster or catalog grant for are not listed at all.
Publishing a product **describes** data; it never widens who can read it.

## What a client may run

Every statement an MCP client submits — typed directly into `run_query` or
rendered from a template — passes the same read-only boundary before it reaches
Trino:

- **`SELECT`** (and `WITH`), against a keyword denylist.
- **`SHOW`**, **`DESCRIBE`** / **`DESC`** — schema discovery.
- **`EXPLAIN`** — query-plan inspection.
- Exactly **one** statement per call, so a second one cannot be smuggled in
  behind a semicolon.

Anything else — every write and every DDL statement — is rejected with a 400.

`EXPLAIN ANALYZE` is refused, in both the `EXPLAIN ANALYZE …` and
`EXPLAIN (ANALYZE) …` forms, because it *executes* the statement it explains.
Plain `EXPLAIN` re-validates whatever follows it, so a write cannot ride in
behind the keyword either.

**Ask Trino** does not share this widening and stays `SELECT`-only: the model
there emits SQL as text, so it can only ever emit a query.

## Results

Tool results are capped at **100 KB**, separately from the browser's 1,000-row /
10 MB display cap. A tool result is read into a model's context rather than
rendered in a table, so the browser's cap would swamp a client long before the
data became useful. Rows are dropped until the payload fits — measured per row,
so one enormous row cannot smuggle the whole budget past the check — and a
trimmed result still reports `truncated: true`.

Each tool declares an `outputSchema` and returns its result as
`structuredContent`, so the model gets typed fields rather than having to parse
JSON out of a text block. The text block is still sent for older clients.

All eight tools are annotated `readOnlyHint: true` and `destructiveHint: false`,
so hosts can skip their per-call confirmation prompts.

Identical re-runs inside the result-cache window may be served from the stored
result set; the response then carries `cached: true` and `result_cached_at`.
Pass `fresh: true` to force re-execution — useful when polling for change.

## Connecting

The **MCP** screen in the nav has everything needed to connect: the endpoint URL,
ready-to-paste config for Claude Code / JSON-config clients / `curl`, and the live
tool list read from this control plane's own `tools/list` — so what you see is
what a connected client gets.

To connect, point your MCP host at `https://<your-trinohub-host>/mcp` with an
`Authorization: Bearer` header carrying an API token. With Claude Code:

```
claude mcp add --transport http trinohub https://<your-trinohub-host>/mcp \
  --header "Authorization: Bearer tht_xxxxxxxx…"
```

Any user can create a token for themselves from the **API tokens** panel in
**Settings** — see **Automation & API**. The token carries your own roles,
grants, and data policies, so a connected client sees exactly what you see and
nothing more. For unattended use, an admin can issue a token for a **service
account** instead.

### Clients that discover authentication

Hosts that expect to *discover* how to authenticate, rather than accept a pasted
token, can connect too. TrinoHub publishes [RFC 9728][rfc9728] protected-resource
metadata at:

```
/.well-known/oauth-protected-resource
/.well-known/oauth-protected-resource/mcp
```

Both are unauthenticated by design — discovery has to work before a client holds
a credential. When SSO is configured, the issuer is advertised as the
authorization server; otherwise the resource is still described, so a client can
at least report what it needs. See **Single sign-on (SSO)**.

A request to `/mcp` without a valid token gets a `401` carrying a
`WWW-Authenticate: Bearer` challenge with a `resource_metadata` pointer at that
URL, which is how a client learns where to send the user.

[rfc9728]: https://www.rfc-editor.org/rfc/rfc9728

### Network access

If you have restricted access with **Allowed UI CIDRs**, note that `/mcp` is
gated by that same allowlist — a remote MCP client must connect from an allowed
range. See **Settings & security**.
