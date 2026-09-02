# Changelog

All notable changes to TrinoHub are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Each released section is what the GitHub Release for that tag publishes, so
write the entry before tagging — see [`docs/releasing.md`](docs/releasing.md).
Anything landing on `main` between releases goes under **Unreleased**.

## [Unreleased]

### Fixed

- **Importing `trinohub.api` no longer opens the database.** `app = create_app()`
  ran at module scope, so importing the module for its helpers — which the test
  suite does — constructed a full application against `TRINOHUB_DB`, creating
  tables and running the seeded-admin privilege sync. On a live control-plane
  host that meant running the tests wrote to the operator's real database. The
  ASGI app is now built lazily on attribute access, so `uvicorn trinohub.api:app`
  is unchanged while a plain import has no side effects.
- **Catalog connection details are no longer visible to every signed-in user.**
  `GET /api/catalogs` listed every catalog with its full config to any
  authenticated caller, regardless of catalog grants — disclosing database
  endpoints, connection usernames, Secrets Manager ARNs and the AWS account id
  to accounts that held no privileges at all. The Catalogs view is not
  admin-gated, so this was reachable in the UI and not only over the API. Stored
  passwords were never exposed (only the secret reference is persisted), but the
  surrounding infrastructure detail was. A caller without `MANAGE_CATALOGS` now
  sees only the catalogs they hold a grant for, and each config is reduced to an
  allow-list of harmless keys. **Upgrading is recommended for any install with
  non-admin accounts.**

### Added

- **The TLS gateway serves the TrinoHub UI at the base domain.** Setting a base
  domain already minted a Let's Encrypt certificate for it, but nothing was
  routed there, so the name answered with the "no running cluster" fallback. The
  base domain now proxies to the control plane, giving the UI an HTTPS hostname
  (`https://trino.example.com/`) while clusters keep their subdomains
  (`https://lakehouse.trino.example.com/`). The UI route sits behind the same
  allowed-UI-CIDR gate as the rest of the proxy, and a cluster whose hostname
  override *is* the base domain still wins the route.

## [0.4.0] - 2026-09-02

### Added

- **Data products.** A curated, documented bundle of tables and views with an
  owner, tags, and per-asset descriptions, managed from a new **Data products**
  nav view. AI clients find them by keyword through the `search_data_products`
  and `get_data_product` MCP tools, which is how an agent locates the right data
  instead of guessing from raw catalog metadata. Publishing a product describes
  data — it never widens who can read it, and products the caller has no
  cluster or catalog grant for are not listed.
- **Parameterized query templates.** An operator publishes named SQL with typed
  `{{placeholders}}`; MCP clients call it through `list_query_templates` /
  `run_query_template` supplying values only, never SQL. Values are validated by
  declared type (`string`, `number`, `boolean`, `date`, `identifier`) and
  rendered as escaped literals, and the finished statement still passes the
  read-only check. A template whose SQL isn't read-only once filled in is
  rejected when it is saved, not when an agent calls it.
- **`get_query_result` MCP tool.** `run_query` stops polling after ~12s and
  returns `status: "running"` with a `query_id`; that id can now be redeemed to
  keep waiting, instead of stranding the caller.
- **OAuth discovery for MCP.** The server publishes RFC 9728 metadata at
  `/.well-known/oauth-protected-resource` (and the `/mcp`-suffixed form), and an
  unauthenticated `/mcp` call now answers with a `WWW-Authenticate` challenge
  pointing at it. Clients that discover authentication rather than accept a
  pasted token can connect; the configured SSO issuer is advertised as the
  authorization server.
- **`MANAGE_DATA_PRODUCTS` privilege**, gating both curation surfaces above.
  The seeded `admin` role is now kept in sync with the full privilege list, so a
  database created before a privilege existed picks it up on startup.
- **MCP has its own documentation topic.** The MCP screen is visible to every
  user, but its documentation lived inside the admin-only **Automation & API**
  topic, so an analyst could open the screen and read nothing about it. **MCP**
  is now a top-level, non-admin docs group, rewritten against the server: all
  eight tools, what each one may run, and how `/mcp` is authenticated and
  firewalled. **Data products** is documented alongside it.
- **Installing on a host you manage yourself is documented.** The README now
  compares the three install paths — CloudFormation stack, your own host, local
  development — and walks through the apt/venv/systemd route, the instance
  profile the control plane needs, and how running off EC2 degrades.
- This changelog, backfilled to the first tagged release. Its section for a tag
  is published as that GitHub Release's body, so release notes are written once
  rather than auto-generated from PR titles.
- The running version is shown in the sidebar, linked to its release.
- A test asserts the CloudFormation `GitRef` default matches the package
  version, so the two cannot drift apart unnoticed.

### Changed

- **MCP clients can run `SHOW`, `DESCRIBE`, and `EXPLAIN`,** not only `SELECT`,
  which is what makes schema discovery and query-plan inspection possible.
  `EXPLAIN ANALYZE` stays refused because it executes the statement it explains,
  and `EXPLAIN` re-validates whatever follows it so a write cannot ride in
  behind the keyword. Ask Trino is unchanged and remains `SELECT`-only.
- **MCP query results are capped at 100 KB**, separately from the browser's
  1,000-row / 10 MB display cap. A tool result is read into a model's context
  rather than rendered in a table, so the old cap could swamp a client long
  before the data became useful. Trimmed results still report `truncated: true`.

### Fixed

- The unattended maintenance agent in `automation/` never ran: its systemd units
  were never installed, its service unit pointed at the wrong checkout path, it
  had no git identity on the build box, and a half-built virtualenv was never
  rebuilt. All four are fixed, and a release-preparation job runs alongside it.

### Upgrading

No migration or configuration change is required. The three new tables
(`query_templates`, `data_products`, `data_product_assets`) are created on
startup, and the seeded `admin` role picks up `MANAGE_DATA_PRODUCTS`
automatically. Back up `.trinohub/` before upgrading, and upgrade an existing
instance through SSM — see the [AWS upgrade guide](deploy/aws/README.md#updating).
New CloudFormation installations pin to the immutable `v0.4.0` release.

Four things to check afterwards:

- **Custom roles do not get the new privilege.** Only the system `admin` role is
  synced. Grant `MANAGE_DATA_PRODUCTS` under **Users → Roles** to any custom
  role whose members should publish data products or query templates. Reading a
  product needs no new privilege — the existing cluster and catalog grants still
  decide what a caller sees.
- **MCP tool results are now capped at 100 KB.** A client that relied on the old
  1,000-row / 10 MB limit will see `truncated: true` sooner. Narrow the query, or
  page through it with `run_query` and `get_query_result`.
- **The MCP tool surface is wider than `SELECT`.** If your review of MCP access
  assumed `SELECT`-only, note that `SHOW`, `DESCRIBE`, and `EXPLAIN` now reach
  metadata for any catalog the caller is already granted. Writes and
  `EXPLAIN ANALYZE` are still refused, and Ask Trino stays `SELECT`-only.
- **Behind a reverse proxy, set the SSO redirect base** if you want OAuth
  discovery to work. The new discovery documents and the `WWW-Authenticate`
  challenge take their URLs from that setting when it is configured
  (`PUT /api/sso/oidc`, `redirect_base`) and from the incoming request
  otherwise, which behind a proxy is the internal address a client cannot reach.

## [0.3.0] - 2026-07-29

### Added

- **MCP nav view.** A dedicated screen documenting how to connect an AI client:
  endpoint URL, transport, and auth header as copy-able fields; tabbed
  configuration for Claude Code, JSON-config clients, and `curl`; and an
  explicit list of what a connected client can and cannot do. The tool list is
  probed live from the control plane's own `tools/list`, so it cannot drift
  from the server.
- **Teradata JDBC connector**, with driver upload and connection checks.
- **Trino cross-cluster connector**, letting one cluster query another.
- **GCS and ADLS Iceberg storage** for catalogs.
- CloudFormation can now supply the Ask Trino OpenRouter key at install time.

### Changed

- **MCP tools return structured output.** Every tool declares an `outputSchema`
  and returns `structuredContent`, so hosts receive typed fields instead of
  re-parsing JSON out of a text block. A text block is still sent for older
  clients.
- **MCP protocol version is negotiated** rather than hardcoded. The server
  speaks revisions `2025-03-26`, `2025-06-18`, and `2025-11-25`, echoing the
  client's requested revision when supported and validating the
  `MCP-Protocol-Version` header on subsequent requests.
- MCP tools are annotated `readOnlyHint` / `destructiveHint: false`, so hosts
  can skip per-call confirmation prompts.
- An unauthenticated request to `/mcp` now answers with a
  `WWW-Authenticate: Bearer` challenge instead of a bare `401`.

### Fixed

- **`tools/call` no longer blocks the event loop.** `run_query` polls for up to
  ~12 seconds and was being called inline from an async handler, stalling the
  entire control plane — including the UI and the poller — for that long. It
  now runs in a threadpool.
- The **Scheduled jobs** nav item rendered a blank glyph because its `clock`
  icon was missing from the registry.

### Upgrading

No migration or configuration change is required. Existing MCP clients keep
working: the endpoint still answers `2025-03-26` for clients that request it,
and the text block in tool results is unchanged.

If you have restricted access with **Allowed UI CIDRs**, note that `/mcp` is
gated by that same allowlist — a remote MCP client must connect from an
allowed range. This was already true; the MCP screen now states it.

## [0.2.0] - 2026-07-20

First tagged release.

### Added

- **Query result caching.** Automatic, per-user caching of repeated read-only
  queries, with a configurable TTL and a **Run fresh** bypass. Cache status is
  shown in results, history, query profiles, Ask Trino, and MCP responses.
  Eligible cached results are served without waking an auto-suspended cluster.
- Automated, version-checked GitHub release workflow and a maintainer release
  checklist.

### Security

- Cached data is invalidated after user, role, policy, catalog, cluster, tag,
  and write mutations, so caching cannot outlive the grants it was read under.

### Upgrading

New CloudFormation installations pin to the immutable `v0.2.0` release.
Existing instances upgrade through SSM — see the
[AWS upgrade guide](deploy/aws/README.md#updating). Back up `.trinohub/`
first.

[Unreleased]: https://github.com/BitRefinery/trinohub/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/BitRefinery/trinohub/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/BitRefinery/trinohub/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/BitRefinery/trinohub/releases/tag/v0.2.0
