# Notebooks

**Notebooks** let you organize SQL into an ordered document of cells — similar
to Jupyter or Databricks, but scoped to Trino SQL. Each cell runs independently
and keeps its own result table and chart inline, which is ideal for iterative,
multi-step analysis.

## Create a notebook

1. Open **Notebooks** from the sidebar.
2. Click **New notebook** and give it a name.

A new notebook opens with one empty cell, ready to run.

## Set the notebook context

The bar at the top of an open notebook sets the **default** cluster, catalog,
and schema for every cell. Individual cells can override any of these — handy
when one cell needs a different catalog.

## Working with cells

Each cell is a small SQL editor with its own toolbar:

- **Run** — execute just this cell (or press `Ctrl`/`Cmd` + `Enter`). The result
  appears directly below the cell.
- **Table / Chart** — toggle how this cell's result is shown. In chart mode,
  pick the chart type and the X and Y columns.
- **Move up / Move down** — reorder cells.
- **CSV** — download this cell's result.
- **Delete** — remove the cell.

Use **Add cell** to append a new cell, and **Run all** to run every cell in
order, top to bottom (it stops if a cell fails).

## Per-cell context overrides

Each cell has optional **Cluster**, **Catalog**, and **Schema** fields. Leave
them on *Notebook default* to inherit the notebook's context, or set them to run
that specific cell somewhere else.

## Saving and sharing

Notebooks are saved automatically to your account — cells, their SQL, the chart
settings, and the table/chart preference all persist. Reopen a notebook later
and pick up where you left off.

**Share** a notebook with a **role** at **view**, **view and run**, or **edit**
level (the share button is on the notebook card). Recipients see it in their
notebook list labeled with the owner and access level; **view** and **run** are
read-only, **edit** lets them change cells, and only the owner can delete a
shared notebook.

> Result limits are the same as the SQL editor: each cell shows up to 1,000 rows
> or 10 MB in the browser, and charts plot up to the first 50 points.
