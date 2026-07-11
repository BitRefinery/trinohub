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
