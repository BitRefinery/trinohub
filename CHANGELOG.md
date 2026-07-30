# Changelog

All notable changes to TrinoHub are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Each released section is what the GitHub Release for that tag publishes, so
write the entry before tagging — see [`docs/releasing.md`](docs/releasing.md).
Anything landing on `main` between releases goes under **Unreleased**.

## [Unreleased]

### Added

- **`get_query_result` MCP tool.** `run_query` stops polling after ~12s and
  returns `status: "running"` with a `query_id`; that id can now be redeemed to
  keep waiting, instead of stranding the caller.
- **OAuth discovery for MCP.** The server publishes RFC 9728 metadata at
  `/.well-known/oauth-protected-resource` (and the `/mcp`-suffixed form), and an
  unauthenticated `/mcp` call now answers with a `WWW-Authenticate` challenge
  pointing at it. Clients that discover authentication rather than accept a
  pasted token can connect; the configured SSO issuer is advertised as the
  authorization server.
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

[Unreleased]: https://github.com/BitRefinery/trinohub/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/BitRefinery/trinohub/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/BitRefinery/trinohub/releases/tag/v0.2.0
