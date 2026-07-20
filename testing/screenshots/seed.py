"""Seed a fully-populated TrinoHub demo control plane for screenshots.

Reuses the end-to-end test harness (``testing/harness.py``): a real
:class:`TrinoHubApp` wired to an in-memory fake AWS and a fake Trino engine, so
no cloud resources are launched and no real coordinator is needed. On top of the
harness we:

* return richer, presentation-quality result sets for a handful of demo queries
  (revenue by region, monthly trend, orders by status);
* seed demo clusters, catalogs, query history, a notebook, scheduled jobs, and a
  couple of extra users;
* hand back the admin session token so a browser (see ``capture.py``) can drive
  the real UI.

Run ``capture.py`` to launch this against uvicorn and screenshot every view.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.harness import DEFAULT_STATIC_DIR, E2EHarness  # noqa: E402
from trinohub.server import SESSION_COOKIE  # noqa: E402

# ---------------------------------------------------------------------------
# Presentation-quality canned result sets
# ---------------------------------------------------------------------------
# Revenue by region — used for the "revenue, highest first" table + bar chart.
_REVENUE_BY_REGION = {
    "columns": [
        {"name": "region", "type": "varchar"},
        {"name": "revenue_usd", "type": "double"},
    ],
    "data": [
        ["North America", 4821773.44],
        ["Europe", 3910488.10],
        ["Asia Pacific", 2734901.87],
        ["Latin America", 1489220.55],
        ["Middle East", 812004.19],
    ],
}

# Monthly revenue trend — a numeric series that renders well as a line/bar chart.
_MONTHLY_TREND = {
    "columns": [
        {"name": "order_month", "type": "varchar"},
        {"name": "revenue_usd", "type": "double"},
    ],
    "data": [
        ["2026-01", 1024884.0],
        ["2026-02", 1173245.0],
        ["2026-03", 1298110.0],
        ["2026-04", 1244903.0],
        ["2026-05", 1402771.0],
        ["2026-06", 1587340.0],
    ],
}

# Orders by status — a small categorical breakdown.
_ORDERS_BY_STATUS = {
    "columns": [
        {"name": "order_status", "type": "varchar"},
        {"name": "orders", "type": "bigint"},
    ],
    "data": [
        ["Fulfilled", 48213],
        ["In progress", 6120],
        ["Pending", 3874],
    ],
}


def _demo_answer(sql_text: str) -> dict[str, Any] | None:
    """Return columns/data for a recognised demo query, else ``None``."""
    upper = " ".join(sql_text.upper().split())
    if "SALES_BY_REGION" in upper or ("REVENUE_USD" in upper and "REGION" in upper):
        return _REVENUE_BY_REGION
    if "MONTHLY_REVENUE" in upper or "ORDER_MONTH" in upper:
        return _MONTHLY_TREND
    if "ORDERS_BY_STATUS" in upper or ("ORDER_STATUS" in upper and "COUNT" in upper):
        return _ORDERS_BY_STATUS
    return None


def build_demo(region: str = "us-east-2") -> tuple[E2EHarness, dict[str, Any]]:
    """Build and fully seed a demo harness. Returns ``(harness, context)``.

    ``context`` carries the pieces ``capture.py`` needs: the ASGI ``app``, the
    admin ``session_token``, the session ``cookie_name``, and seeded ids.
    """
    h = E2EHarness(region=region)

    # Route recognised demo queries to the polished result sets; everything else
    # falls through to the harness's built-in tpch fake so the app still "runs".
    base_submit = h.trino.submit

    def submit(**kw: Any) -> dict[str, Any]:
        resp = base_submit(**kw)
        answer = _demo_answer(kw.get("sql_text", ""))
        if answer is not None and "error" not in resp:
            resp = {**resp, "columns": answer["columns"], "data": [list(r) for r in answer["data"]]}
        return resp

    h.control.submit_trino_query = lambda **kw: submit(**kw)

    # --- first-run setup + admin login ------------------------------------
    h.setup_admin()

    # --- a lakehouse (S3 + Glue) catalog on top of the built-ins ----------
    # Created before the clusters that attach it.
    h.client.post(
        "/api/catalogs",
        {"name": "lakehouse", "type": "s3_glue", "config": h.s3_glue_config()},
    )

    # --- demo clusters -----------------------------------------------------
    analytics = h.create_running_cluster(
        "analytics-prod",
        instance_type="r7i.2xlarge",
        worker_mode="autoscale",
        min_workers=2,
        max_workers=8,
        catalogs=["system", "tpch", "tpcds", "lakehouse"],
        auto_suspend_minutes=30,
    )
    h.create_running_cluster(
        "adhoc-explore",
        instance_type="r7i.xlarge",
        worker_mode="autoscale",
        min_workers=1,
        max_workers=4,
        catalogs=["system", "tpch"],
        auto_suspend_minutes=15,
    )
    # nightly-etl: created but never started -> shows as not-yet-enabled.
    h.create_cluster(
        "nightly-etl",
        instance_type="r7i.2xlarge",
        worker_mode="fixed",
        min_workers=4,
        max_workers=4,
        catalogs=["system", "tpcds", "lakehouse"],
    )

    # --- query history: run a spread of demo queries ----------------------
    cid = analytics["id"]
    for sql in (
        "SELECT region, revenue_usd FROM analytics.sales_by_region ORDER BY revenue_usd DESC",
        "SELECT order_month, revenue_usd FROM analytics.monthly_revenue ORDER BY order_month",
        "SELECT order_status, count(*) AS orders FROM tpch.sf1.orders GROUP BY order_status",
        "SELECT name FROM tpch.sf1.region",
        "SELECT count(*) FROM tpch.sf1.nation",
    ):
        h.run_query(cid, sql, catalog="tpch", schema="sf1")

    # --- a notebook with a table cell and a chart cell --------------------
    nb = h.client.post(
        "/api/notebooks",
        {"name": "Revenue review", "cluster_id": cid, "catalog": "tpch", "schema": "sf1"},
    ).json["notebook"]
    nb_id = nb["id"]
    # create_notebook seeds one empty cell; fill it (table) rather than add a
    # third, then append a chart cell.
    seeded = h.client.get(f"/api/notebooks/{nb_id}/cells").json["cells"]
    first_id = seeded[0]["id"]
    h.client.patch(
        f"/api/notebooks/{nb_id}/cells/{first_id}",
        {
            "sql": "SELECT region, revenue_usd FROM analytics.sales_by_region ORDER BY revenue_usd DESC",
            "cluster_id": cid,
            "catalog": "tpch",
            "schema": "sf1",
            "view_pref": "table",
        },
    )
    h.client.post(
        f"/api/notebooks/{nb_id}/cells",
        {
            "sql": "SELECT order_month, revenue_usd FROM analytics.monthly_revenue ORDER BY order_month",
            "cluster_id": cid,
            "catalog": "tpch",
            "schema": "sf1",
            "view_pref": "chart",
        },
    )

    # --- scheduled jobs ----------------------------------------------------
    h.client.post(
        "/api/jobs",
        {
            "name": "Nightly revenue rollup",
            "sql": "SELECT order_month, revenue_usd FROM analytics.monthly_revenue ORDER BY order_month",
            "cluster_id": cid,
            "catalog": "tpch",
            "schema": "sf1",
            "schedule_type": "cron",
            "cron_expression": "0 2 * * *",
        },
    )
    h.client.post(
        "/api/jobs",
        {
            "name": "Hourly freshness check",
            "sql": "SELECT count(*) FROM tpch.sf1.orders",
            "cluster_id": cid,
            "catalog": "tpch",
            "schema": "sf1",
            "schedule_type": "interval",
            "interval_minutes": 60,
        },
    )

    # --- a couple of extra users ------------------------------------------
    h.client.post(
        "/api/users",
        {"username": "dana", "password": "demo-password-9911", "email": "dana@example.com", "role": "user"},
    )
    h.client.post(
        "/api/users",
        {"username": "raj", "password": "demo-password-2277", "email": "raj@example.com", "role": "admin"},
    )

    # Admin session token that the browser will reuse (cookie is "name=value").
    token = h.client.cookie.split("=", 1)[1] if "=" in h.client.cookie else h.client.cookie

    context = {
        "app": h.app,
        "static_dir": str(DEFAULT_STATIC_DIR),
        "session_token": token,
        "cookie_name": SESSION_COOKIE,
        "notebook_id": nb_id,
        "cluster_id": cid,
    }
    return h, context


if __name__ == "__main__":  # smoke test the seed without a browser
    harness, ctx = build_demo()
    clusters = harness.client.get("/api/clusters").json["clusters"]
    print(f"seeded {len(clusters)} clusters:", [c["name"] + "/" + c["status"] for c in clusters])
    print("catalogs:", [c["name"] for c in harness.client.get("/api/catalogs").json["catalogs"]])
    hist = harness.client.get("/api/query-history").json
    print("history rows:", len(hist.get("queries", hist.get("history", []))))
    print("jobs:", [j["name"] for j in harness.client.get("/api/jobs").json.get("jobs", [])])
    print("session token len:", len(ctx["session_token"]))
    harness.close()
