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

Ask Trino calls an LLM provider from the control plane to draft SQL. It's off
until you give it an API key. The key lives in the **server environment** — it
is **never logged and never returned to the browser** — so it can't be set from
the UI. If the feature is unconfigured, the assistant is unavailable and the
rest of TrinoHub is unaffected.

### Enable it

1. **Get an API key.** By default Ask Trino talks to
   [OpenRouter](https://openrouter.ai) — create an account and an API key there.
   (To use a different OpenAI-compatible provider, see the overrides below.)
2. **Give the key to the control plane.** Set `OPENROUTER_API_KEY` (or the alias
   `ASK_TRINO_API_KEY`) in the server environment. The simplest way is a `.env`
   file in the project root — the app loads it automatically on start:

   ```dotenv
   # .env (project root; never commit this file)
   OPENROUTER_API_KEY=sk-or-your-key-here
   ```

   Alternatively, export it wherever the control plane runs (systemd unit,
   container env, etc.). See `.env.example` for a template.
3. **Restart the control plane** so it picks up the new environment.
4. Open **Ask Trino** from the sidebar — it's now live.

#### On an AWS (CloudFormation) deploy

The stack in `deploy/aws/cloudformation.yaml` can wire the key in for you — pass
**one** of these parameters (both optional; you can also add them later with a
stack update):

- `OpenRouterApiKey` — the key itself. Quickest, but the value is stored in the
  instance's EC2 user-data, so anyone with `ec2:DescribeInstanceAttribute` in the
  account can read it. Fine for trials; prefer the secret below for production.
- `OpenRouterSecretArn` — the ARN of a Secrets Manager secret holding the key
  (a raw string, or JSON with an `OPENROUTER_API_KEY` field). The key never
  appears in user-data, and the stack grants the control-plane role read access
  to exactly that secret. Takes precedence if both are set.

Either way, boot writes the key to the control plane's `.env` and the assistant
comes up enabled. To create the secret first:

```bash
aws secretsmanager create-secret --name trinohub/openrouter \
  --secret-string sk-or-your-key-here
# then pass its ARN as OpenRouterSecretArn
```

### Model and provider (optional)

- **Model** — the default is `openai/gpt-4o-mini`. Change it in
  **Settings → Ask Trino** (paste any model id from `openrouter.ai/models`, e.g.
  `anthropic/claude-sonnet-4.5`), or set `ASK_TRINO_MODEL` in the environment.
- **Provider** — point at any OpenAI-compatible chat-completions endpoint with
  `ASK_TRINO_API_BASE` (default:
  `https://openrouter.ai/api/v1/chat/completions`).

If a request fails with *"Ask Trino is not configured"*, the key isn't set in
the server environment; if the provider *"rejected the API key,"* check the key
value and, if you overrode it, the model id and API base.
