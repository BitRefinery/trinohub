# Getting started

Welcome to **TrinoHub** — a self-hosted control plane for running
[Trino](https://trino.io) SQL clusters on AWS, straight from your browser.
Admins provision and operate clusters and data catalogs; analysts pick a
cluster, write SQL, and pull results.

## Signing in

Open TrinoHub in your browser and sign in with the username and password your
administrator created for you, or with **Sign in with SSO** if your admin has
configured single sign-on. If this is a brand-new installation, you'll see the
**First-run setup** wizard instead — see the admin guide for that.

Sessions are kept in a secure, http-only cookie. If your session expires you'll
be returned to the sign-in screen; just log in again.

## The workspace

The left sidebar is your main navigation. What you see depends on your role:

- **Clusters** — the Trino clusters available to you, with their status.
- **Catalogs** — the data sources (databases) you can query.
- **SQL editor** — write and run SQL, view results, and export.
- **Notebooks** — organize SQL into ordered cells with inline charts.
- **Ask Trino** — describe what you want in plain English and get SQL to review.
- **Query history** — your recent queries and their outcomes.
- **Scheduled jobs** — run SQL on a schedule.
- **Docs** — this documentation.

Press `Ctrl`/`Cmd` + `K` anywhere for **global search** across clusters,
catalogs, tables, saved queries, and notebooks.

Management areas (**Users**, **Settings**, cluster creation and lifecycle
actions) appear only when your roles carry the matching privileges.

## Roles

Access is governed by **roles**, and you can hold more than one. Two ship
built-in:

- **admin** — full access: setup, clusters, catalogs, users, security, and
  settings.
- **user** — pick a cluster and catalog, run SQL, watch query status, cancel
  your own queries, download results, and browse your own history.

Admins can also create **custom roles** that delegate specific areas and scope
access to particular clusters and catalogs — see **Users & roles**.

## Light & dark mode

Use the theme toggle in the top bar to switch between light and dark. Your
choice is remembered on this device.

## Where to next

- New to running SQL here? Read **Running queries**.
- Want multi-step analysis with charts? Read **Notebooks**.
- Curious what a cluster's status means? Read **Understanding clusters**.
