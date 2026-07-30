# Data products & query templates

The **Data products** screen is where you curate what an AI client sees. Both
things it manages answer the same question — *how does an agent find the right
data without guessing?* — from two directions:

- A **data product** describes where the good data is.
- A **query template** publishes one specific question as a callable tool.


Neither grants access to anything. A person or an agent still reads data through
their own cluster and catalog grants, so publishing a product documents data
without widening who can read it.

## Data products

A data product is a documented bundle of tables and views: a name, a one-line
summary, a longer description, an owner, tags, and a list of assets with a
description each.

Create one with **Create data product** and fill in:

- **Summary** — one line. This is what keyword search matches first, so write it the way someone would ask for the data ("Revenue and refunds by day" beats "Sales mart v2").
- **Cluster**, **catalog**, **schema** — where the data lives. Leave the cluster blank if the product isn't tied to one.
- **Assets** — one per line, as `name: description`. The description matters: search reaches into it, so a product is findable by what it publishes even when its own prose never says the word.

Use **Assets** on any row to see the full list, and the search box to try the
same keyword search an AI client would run.

### What an AI client sees

Connected MCP clients get two tools:

- `search_data_products` — keyword search across names, summaries, descriptions, tags, and assets.
- `get_data_product` — the full record for one product, including every asset with its description and view definition.

Products the caller has no cluster or catalog grant for are not listed at all.

## Query templates

A template publishes one parameterized query as a callable tool. The client
supplies typed values and **never writes SQL** — which is how you hand an agent a
specific question rather than the run of the warehouse.

Write the SQL with holes as `{{name}}`, then declare each one. Parameters are
entered one per line:

```
name type required|optional=default description
```

For example:

```
region string required Region code such as EU
since date required Earliest day to include
row_limit number optional=100 Maximum rows
```

against SQL like:

```sql
SELECT region, sum(amount) AS revenue
FROM sales
WHERE region = {{region}} AND day >= {{since}}
GROUP BY region
LIMIT {{row_limit}}
```

### Parameter types

| Type | Accepts | Rendered as |
| --- | --- | --- |
| `string` | any text | an escaped, quoted literal |
| `number` | digits, sign, decimal, exponent | the number itself |
| `boolean` | `true` or `false` | `true` / `false` |
| `date` | `YYYY-MM-DD` | `DATE '…'` |
| `identifier` | letters, digits, underscore | a quoted identifier |

Pick the narrowest type that fits. A value that doesn't match its declared type
is rejected before it reaches the SQL, so `number` is a real constraint and not
just documentation.

### Safety

- Values are validated by type and rendered as escaped literals — a caller cannot close a string and append their own clause.
- The finished statement still passes the same **read-only** check as every other MCP query, so even a template that somehow rendered something unexpected cannot write.
- A template whose SQL isn't read-only once filled in is **rejected when you save it**, so you find out immediately rather than when an agent calls it.
- **Disable** takes a template out of every client's tool list straight away, without deleting it.

## Who can publish

Creating, editing, and deleting products and templates needs the
**MANAGE_DATA_PRODUCTS** privilege. Anyone signed in can browse the catalogue and
run the templates their grants reach — curation is the privileged act, not
reading.
