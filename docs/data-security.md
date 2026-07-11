# Data security

Beyond who can *reach* a cluster or catalog (see **Users & roles**), TrinoHub
enforces **fine-grained data policies** — table, column, and row-level rules
per role. These are rendered into Trino's own file-based access control, so
they apply to **every** client, including native JDBC/ODBC and CLI connections,
not just the web UI.

Manage all of this from the **Data security** panels in the **Users** view
(requires `MANAGE_SECURITY`).

## How restriction works

Policies are **role-scoped and additive within a role, restrictive across the
account**:

- A user whose roles carry **no** data policies keeps full access.
- A user whose roles carry **any** data policy is limited to exactly the union
  of those policies (plus `information_schema` and the `system`/`jmx`
  catalogs, which stay readable so clients work).

So you grant restricted access by putting a user in a role that *has* policies;
unrestricted users fall through to a catch-all.

> **Policies apply when a cluster (re)starts.** The rules are written into each
> node's Trino config at boot, so create or change policies and then start (or
> suspend and resume) the cluster for them to take effect.

## Data policies

Create a policy for a role with:

- **Scope** — a catalog, optionally a schema, optionally a table. Blank schema
  or table means "all".
- **Privileges** — any of `SELECT`, `INSERT`, `UPDATE`, `DELETE`.
- **Denied columns** — columns the role cannot read from the matching table.
- **Allowed columns** — an allow-list; every other known column is denied.
- **Row filter** — a SQL boolean expression; the role only sees rows where it
  is true (for example `region = 'EU'`).
- **Column masks** — replace a column's value with an expression per role, for
  example `email = substr(email, 1, 3) || '…'`. Use `NULL` to blank it.

## Tags and attribute-based policies (ABAC)

Instead of naming columns table-by-table, you can **tag** entities and write
policies against the tag:

1. **Tag an entity** — a path like `lake.crm.users.email` gets a tag such as
   `pii-email`. (Tags can also cover a whole table.)
2. **Create a tag policy** — for a given tag and role, choose **deny column**
   or **mask with NULL**. Every column carrying that tag is then denied or
   masked for that role's members.

This keeps the intent ("analysts never see PII-email columns") in one place as
new tables arrive.

## PII classification

Click **Scan for PII** to run the built-in classifier over the cached column
metadata. It matches column names against high-signal patterns (email, phone,
SSN, name, address, date of birth, card number, IP, salary) and **proposes**
tags for review — it never applies them automatically.

Proposed tags appear with a *proposed* status; **Accept** promotes a tag to
active, or **Reject** discards it. Only accepted tags feed tag policies.

> The classifier reads TrinoHub's **metadata cache**, which fills as users
> browse a running cluster's schemas. Browse the tables you want scanned (or
> use autocomplete/the schema browser against them) first, so their columns
> are cached.

## Previewing the rendered rules

Every change is reflected in the access-control rules a cluster will apply.
Admins can preview the exact `rules.json` for a cluster at
`GET /api/clusters/{id}/access-rules` (see the OpenAPI docs) to confirm what
the engine will enforce before restarting.
