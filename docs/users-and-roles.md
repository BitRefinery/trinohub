# Users & roles

Admins manage accounts and access from the **Users** view: a table of users
with their email, roles, and status, plus panels for **roles** and **data
security**.

## Users

- **Create user** — add an account with a username, email, one or more roles,
  and an initial password. You can also create a **service account** (see
  below), which has no password and authenticates only with API tokens.
- **Edit** — change a user's roles, or reset their password. A user can hold
  **several roles at once**; their effective access is the union of them.
- **Enable / disable** — deactivate an account to block sign-in without
  deleting it. Resetting a password or deactivating a user revokes their
  active sessions immediately.

## Roles and privileges

TrinoHub uses **custom roles**. Each role carries a set of coarse
**privileges** and a set of **data-access grants**. Two system roles ship
built-in and cannot be deleted:

- **admin** — holds every privilege and can use every cluster and catalog.
- **user** — holds no management privileges but (by default) can query every
  cluster and catalog.

Create your own roles from the **Roles** panel to delegate specific areas. The
privileges are:

| Privilege | Grants |
|---|---|
| `MANAGE_USERS` | Create/edit users and roles' membership |
| `MANAGE_SECURITY` | Manage roles, grants, data policies, and view the audit log |
| `MANAGE_CLUSTERS` | Create, start, edit, suspend, and delete clusters; scheduled-job admin |
| `MANAGE_CATALOGS` | Create, edit, and delete catalogs and connector drivers |
| `MANAGE_SETTINGS` | Change instance types, base domain, SSO, sessions, notifications |
| `VIEW_ALL_QUERY_HISTORY` | See every user's query history, not just your own |
| `CANCEL_ANY_QUERY` | Cancel queries owned by other users |

A user with any management privilege sees the corresponding admin screens; a
user with none sees only the query surfaces.

## Data-access grants

Each role grants access to specific **clusters** and **catalogs** (or `*` for
all). A user can only query a cluster their roles grant, and only browse or
query a catalog their roles grant — enforced on every query, on metadata
browsing, on connection info, and in Ask Trino. The seeded roles carry `*`
grants, so an unmodified install behaves as before: everyone can query
everything until you narrow it.

To scope a team to one lakehouse, for example, create an `analysts` role
granting just that cluster and its catalog, and assign it instead of the
built-in `user` role.

## Service accounts

A **service account** is a user with no usable password — it signs in only
through **API tokens** (see **Automation & API**). Use one as the identity for
scripts, BI tools, and scheduled jobs so automation isn't tied to a person's
login. Give it exactly the roles the automation needs.

## Fine-grained data security

Below the catalog level — table, column, and row restrictions, masking, tags,
and PII classification — lives in its own topic. See **Data security**.

## Safeguards

TrinoHub protects against locking yourself out: any change (removing a role,
deactivating a user, editing a role's privileges) is rejected if it would
leave **no active user holding `MANAGE_SECURITY`**. Make sure a second
security admin exists before changing the primary admin's access.

## The security audit log

Every security-relevant change — user and role edits, grants, catalog and
cluster mutations, settings changes, token and policy activity — is recorded
in an append-only **security audit log**, shown read-only at the bottom of
**Settings**. Each entry records who did what, when, and the before/after
detail.

## Authentication notes

Passwords are stored **hashed** (PBKDF2), never in plain text. Sessions use a
secure, http-only cookie and are tracked server-side, so disabling a user or
resetting a password takes effect immediately. For single sign-on, see **Single
sign-on (SSO)**.
