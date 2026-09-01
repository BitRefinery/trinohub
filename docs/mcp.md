# MCP server

TrinoHub exposes a **Model Context Protocol** endpoint at `/mcp` so AI clients
(Claude, Copilot, and other MCP hosts) can explore and query your data safely.
It speaks JSON-RPC over the Streamable HTTP transport and authenticates with the
same session or API token as the rest of the API, so an MCP client acts as its
user under that user's grants.

Protocol revisions `2025-03-26`, `2025-06-18`, and `2025-11-25` are supported;
the version is negotiated at `initialize` and `2025-06-18` is offered to clients
that ask for anything else.

## Tools

Three tools are exposed:

- **list_clusters** — the clusters you can query.
- **browse_metadata** — drill through catalogs, schemas, tables, and columns.
- **run_query** — run **one read-only `SELECT`** and get the rows back.

`run_query` passes through the same read-only boundary as **Ask Trino**: any
write or DDL statement is rejected before it reaches Trino. An MCP client can
read your data but never modify it. All three tools are annotated
`readOnlyHint`, so hosts can skip their per-call confirmation prompts.

Each tool declares an `outputSchema` and returns its result as
`structuredContent` — the model gets typed fields rather than having to parse
JSON out of a text block. The text block is still sent for older clients.

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

Requests without a valid token get a `401` with a
`WWW-Authenticate: Bearer` challenge.

Any user can create a token for themselves from the **API tokens** panel in
**Settings** — see **Automation & API**. The token carries your own roles,
grants, and data policies, so a connected client sees exactly what you see and
nothing more. For unattended use, an admin can issue a token for a **service
account** instead.
