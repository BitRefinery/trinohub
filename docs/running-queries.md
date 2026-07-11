# Running queries

The **SQL editor** is where you write and run Trino SQL against a cluster.

## Choose your context

At the top of the editor, pick three things:

- **Cluster** — the Trino cluster that will execute your query. It must be
  *Running* (see **Understanding clusters**).
- **Catalog** — the data source, for example `tpch`, `tpcds`, or any catalog
  your admin configured (S3 + Glue, a database like PostgreSQL or Snowflake,
  MongoDB, Elasticsearch, and more).
- **Schema** — the schema within that catalog, for example `sf1`.

The **schema browser** on the left lists loaded catalogs, schemas, and tables.
Click a table to insert its fully-qualified name into the editor. The browser
and autocomplete are backed by a server-side metadata cache, so they keep
working from the last known schema **even when the cluster is suspended**.

## Write and run

Type your SQL in the editor. It has syntax highlighting, line numbers, and
autocomplete that's aware of your selected context (catalogs, schemas, tables,
columns, keywords, and functions).

There are three run modes:

- **Current** — run the statement your cursor is in.
- **Selected** — run only the text you've highlighted.
- **All** — run every statement, separated by semicolons, in order.

Click **Run** (or press `Ctrl`/`Cmd` + `Enter`). While a query runs you'll see
its status, elapsed time, and row count update live. Click **Cancel** to stop a
running query.

Click **Explain** to see the query **plan** without executing it — TrinoHub
wraps your statement in `EXPLAIN` and shows the result.

## Results, charts, and profile

The results card has three tabs:

- **Results** — your rows in a table.
- **Chart** — pick a chart type (bar, line, area, or pie) and the X and Y
  columns to visualize the result set.
- **Query profile** — the Trino query ID, timing, context, and row counts,
  plus, for a query that reached a running coordinator, an **execution detail**
  breakdown: coordinator state, queued/execution/CPU time, peak memory, splits,
  and a per-stage table.

> **Result limits:** the browser shows up to **1,000 rows or 10 MB**, whichever
> comes first. When a result is capped you'll see a notice. To get more rows,
> export to CSV.

## Exporting to CSV

Click **CSV** to download the result. CSV export streams a larger capped buffer
of **10,000 rows or 50 MB**. Use **Run CSV** to run and download in one step.

## Saving, sharing, and reusing queries

- **Save** stores the current query in your **Saved queries** library (search,
  sort, and reopen from the right rail).
- **Share** a saved query with a **role** at one of three levels — **view**,
  **view and run**, or **edit**. Shared queries appear in recipients' libraries
  labeled with the owner and their access level; only the owner can delete a
  shared query.
- The **Recent queries** rail and the **Query history** view list what you've
  run — open any entry to load it back into the editor.

## Tips

- **Find / Replace** — search and edit within the editor.
- **Format** — tidy up common `SELECT` clauses.
- **Commands** — open the command palette for editor tools and actions.
- **Global search** — press `Ctrl`/`Cmd` + `K` anywhere to search across
  clusters, catalogs, cached tables, saved queries, and notebooks; results are
  filtered to what your roles allow.
