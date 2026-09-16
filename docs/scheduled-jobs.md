# Scheduled jobs

The **Scheduled jobs** view runs a SQL statement on a cluster automatically, on
a schedule — for daily rollups, table maintenance, refreshes, and other
recurring work.

## Creating a job

Click **Create job** and set:

- **Name** — a label for the job.
- **SQL** — exactly **one** statement to run each time.
- **Cluster** — where it runs. If the cluster is suspended when the job fires,
  the run is recorded as failed (start the cluster, or give it a keep-warm
  uptime window — see **Managing clusters**).
- **Schedule** — either **every N minutes** (minimum 5) or a **cron
  expression** (standard five fields: minute, hour, day-of-month, month,
  day-of-week, in UTC). For example `0 3 * * *` runs at 03:00 every day.

- **Email results to** (optional) — usernames to send each run's result to.
  See **Email digests** below.

## How runs work

A background scheduler checks every 30 seconds and fires any due job. Each run
submits your SQL through the normal query path, so it obeys the same access
control as an interactive query. If a run **fails, it is retried once**; if the
retry also fails, the run is marked failed and — when notifications are
configured — a message is sent (see **Settings & security**).

## Managing jobs

From the table you can:

- **Runs** — open the run history for a job (start time, attempt, status,
  elapsed, and any error).
- **Run now** — trigger the job immediately without waiting for its schedule.
- **Pause / Resume** — stop and restart scheduling without deleting the job.
- **Delete** — remove the job and its run history.

## Running as another identity

By default a job runs as **you**, with your grants. If you have the
`MANAGE_USERS` privilege you can set **run as** to another user — typically a
**service account** — so the job's access is tied to an automation identity
rather than a personal login. See **Users & roles**.

## Email digests

Give a job **recipients** and it becomes a digest: every time it fires, the
job runs **once per recipient, as that recipient**, and emails each person their
own result. Because each run uses the recipient's own grants, data policies
and row filters apply per person — a store manager whose role filters to their
store receives only that store's rows, even though everyone shares one job.
The run-as setting is ignored for digests.

Rules:

- A digest must be a **read-only** statement (`SELECT`/`WITH`), since it runs
  under other people's identities.
- Recipients must be active, non-service users with an email address. Adding
  anyone other than yourself requires `MANAGE_USERS`.
- The email shows up to 50 rows inline, the row count, and — when a public URL
  is configured — a link that opens the query in the recipient's
  **Query history**.
- A failed run is retried once for that recipient only. Delivery failures are
  recorded on the run (**Runs → Email**) and sent to the notification webhook
  as `job_failed`; they never stop the scheduler.

Email must be enabled in **Settings → Email** first (see **Settings &
security**).
