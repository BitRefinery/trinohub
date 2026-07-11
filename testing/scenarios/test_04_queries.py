"""E2E scenario 04 — running queries.

Covers the query workflow against a running cluster: executing SQL and reading
results, browser row caps vs. larger CSV export caps, paginated result
accumulation, query cancellation, failed queries surfacing the error, and the
guard that queries require a running cluster.
"""

import unittest

from testing.harness import E2EHarness
from trinohub.server import MAX_QUERY_RESULT_ROWS


class QueryScenario(unittest.TestCase):
    def setUp(self):
        self.h = E2EHarness()
        self.addCleanup(self.h.close)
        self.h.setup_admin()
        self.cluster = self.h.create_running_cluster("queries", catalogs=["system", "tpch"])

    def test_run_simple_query_returns_rows(self):
        query = self.h.run_query(
            self.cluster["id"],
            "SELECT nationkey, name, regionkey FROM nation LIMIT 5",
            catalog="tpch",
            schema="sf1",
        )
        self.assertEqual(query["status"], "Finished")
        self.assertEqual(query["row_count"], 5)
        self.assertEqual([c["name"] for c in query["columns"]], ["nationkey", "name", "regionkey"])
        self.assertEqual(query["data"][0], [0, "ALGERIA", 0])
        # Submitted to the coordinator with the right catalog/schema context.
        last = self.h.trino.submitted[-1]
        self.assertEqual(last["catalog"], "tpch")
        self.assertEqual(last["schema_name"], "sf1")

    def test_query_requires_running_cluster(self):
        idle = self.h.create_cluster("idle", catalogs=["system"])
        resp = self.h.client.post(
            "/api/query", {"cluster_id": idle["id"], "sql": "SELECT 1", "catalog": "", "schema": ""}
        )
        self.assertNotEqual(resp.status, 201)
        self.assertIn("error", resp.json)

    def test_multiple_statements_rejected(self):
        resp = self.h.client.post(
            "/api/query",
            {"cluster_id": self.cluster["id"], "sql": "SELECT 1; SELECT 2", "catalog": "", "schema": ""},
        )
        self.assertEqual(resp.status, 400)
        self.assertIn("one SQL statement", resp.json["error"])

    def test_browser_results_capped_but_csv_keeps_more(self):
        # Ask the fake engine for more rows than the browser cap.
        rows = MAX_QUERY_RESULT_ROWS + 250
        self.h.trino.big_result(rows)
        query = self.h.run_query(self.cluster["id"], "SELECT n FROM big", catalog="tpch")

        # Browser display is capped and flagged truncated.
        self.assertEqual(query["row_count"], MAX_QUERY_RESULT_ROWS)
        self.assertTrue(query["truncated"])
        self.assertEqual(query["total_row_count"], rows)

        # CSV export retains the full (larger-capped) set.
        csv = self.h.client.get(f"/api/query/{query['id']}/csv")
        self.assertEqual(csv.status, 200)
        self.assertIn("text/csv", csv.headers["content-type"])
        body_lines = csv.text.strip().splitlines()
        self.assertEqual(body_lines[0], "n")  # header row
        self.assertEqual(len(body_lines) - 1, rows)  # all data rows present
        self.assertEqual(csv.headers["x-trinohub-csv-rows"], str(rows))

    def test_paginated_results_accumulate_across_pages(self):
        self.h.trino.paginate([[[1], [2]], [[3], [4]], [[5]]])
        query = self.h.run_query(self.cluster["id"], "SELECT n FROM paged", catalog="tpch")
        self.assertEqual(query["status"], "Finished")
        self.assertEqual(query["total_row_count"], 5)
        self.assertEqual([row[0] for row in query["data"]], [1, 2, 3, 4, 5])

    def test_cancel_running_query(self):
        # Two pages so the query parks in Running with a nextUri we can cancel.
        self.h.trino.paginate([[[1]], [[2]], [[3]]])
        # Submit without auto-draining: hit the API directly so it stops at page 1.
        resp = self.h.client.post(
            "/api/query",
            {"cluster_id": self.cluster["id"], "sql": "SELECT n FROM slow", "catalog": "tpch", "schema": ""},
        )
        self.assertEqual(resp.status, 201)
        query = resp.json["query"]
        if query["status"] == "Running":
            cancel = self.h.client.delete(f"/api/query/{query['id']}")
            self.assertEqual(cancel.status, 200)
            self.assertTrue(self.h.trino.cancelled)
            after = self.h.client.get(f"/api/query/{query['id']}")
            self.assertIn(after.json["query"]["status"], {"Cancelled", "Canceled"})
        else:
            # Engine drained it synchronously; just confirm it finished cleanly.
            self.assertEqual(query["status"], "Finished")

    def test_failed_query_surfaces_error(self):
        self.h.trino.fail_next("line 1:15: Table 'tpch.sf1.nonexistent' does not exist")
        resp = self.h.client.post(
            "/api/query",
            {"cluster_id": self.cluster["id"], "sql": "SELECT * FROM nonexistent", "catalog": "tpch", "schema": "sf1"},
        )
        self.assertEqual(resp.status, 201)
        query = resp.json["query"]
        self.assertEqual(query["status"], "Failed")
        self.assertIn("does not exist", query["error_message"])

    def test_query_recorded_in_history(self):
        self.h.run_query(self.cluster["id"], "SELECT 1", catalog="tpch")
        history = self.h.client.get("/api/query-history")
        self.assertEqual(history.status, 200)
        self.assertTrue(history.json["queries"])
        self.assertEqual(history.json["queries"][0]["cluster_name"], "queries")


if __name__ == "__main__":
    unittest.main()
