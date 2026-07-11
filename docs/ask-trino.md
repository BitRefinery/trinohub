# Ask Trino

**Ask Trino** turns a plain-English question into Trino SQL you can review and
run. It's an assistant, not an autopilot: it only ever produces SQL *text* — it
never connects to your clusters or data itself.

## How it works

1. Open **Ask Trino** from the sidebar and set the context on the left rail —
   the **cluster**, **catalog**, and **schema** you want the query to target,
   plus an optional **persona** that tunes the assistant's style.
2. Type what you want in plain language (or start from a **suggested** prompt).
3. The assistant replies with a SQL statement and a short explanation.
4. Review the SQL, then send it to the **SQL editor** to run it like any other
   query — with the same cluster, catalog, and result limits.

## Safety

- The assistant **only emits SQL as text.** It has no connection to Trino or your
  data; nothing runs until you choose to run it.
- Generated SQL is validated as **read-only** — a single `SELECT` statement — 
  before it can run through the normal query path. Statements that try to write
  or run multiple commands are rejected.
- Always read the SQL before running it. Treat the assistant as a fast first
  draft, not a guarantee of correctness.

## Configuration (admins)

Ask Trino calls an LLM provider configured on the control plane. The API key is
read from the server environment; it is **never logged and never returned to the
browser.** If the feature is unconfigured, the assistant is unavailable and the
rest of TrinoHub is unaffected.
