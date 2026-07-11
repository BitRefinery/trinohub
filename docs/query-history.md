# Query history

The **Query history** view lists your recent query runs so you can review,
re-run, or save past work.

## What you'll see

Each row shows:

- **Status** — Finished, Failed, Running, or Cancelled.
- **Query** — the SQL that ran (truncated; open the row for the full text).
- **Cluster** — where it ran. The cluster name is captured at run time, so it
  still shows even if the cluster was later deleted.
- **User** — who ran it. You see your own history; users with the
  `VIEW_ALL_QUERY_HISTORY` privilege see everyone's.
- **Elapsed** and **Rows** — how long it took and how many rows came back.

## Filtering

Narrow the list by:

- **Status** — for example only failed or only finished queries.
- **Date** — today or the last 7 days.
- **Role** — admins can filter by admin vs. user activity.

## The detail panel

Click any row to open its details: the full SQL, the catalog/schema context,
timing, and the Trino query ID — plus, when the query ran on a still-running
coordinator, an **execution breakdown** with per-stage rows, splits, and
memory. From there you can copy the SQL, open it in the **SQL editor**, or save
it to your **Saved queries** library to reuse later.
