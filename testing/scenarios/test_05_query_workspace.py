"""E2E scenario 05 — query workspace (tabs + saved queries) and metadata.

Covers the editor-side workflow: the default query tab, creating/renaming/
deleting tabs (with the default-tab recreation guarantee), saving and editing
named queries, and browsing cluster catalog/schema/table metadata.
"""

import unittest

from testing.harness import E2EHarness


class QueryWorkspaceScenario(unittest.TestCase):
    def setUp(self):
        self.h = E2EHarness()
        self.addCleanup(self.h.close)
        self.h.setup_admin()
        self.cluster = self.h.create_running_cluster("workspace", catalogs=["system", "tpch"])

    # --- query tabs ------------------------------------------------------
    def test_default_tab_exists_and_tabs_are_editable(self):
        tabs = self.h.client.get("/api/query-tabs")
        self.assertEqual(tabs.status, 200)
        self.assertEqual(len(tabs.json["tabs"]), 1)
        self.assertTrue(tabs.json["tabs"][0]["is_active"])

        created = self.h.client.post(
            "/api/query-tabs",
            {"name": "scratch.sql", "sql": "SHOW CATALOGS", "catalog": "tpch", "schema": "sf1", "is_active": True},
        )
        self.assertEqual(created.status, 201)
        tab_id = created.json["tab"]["id"]

        renamed = self.h.client.patch(
            f"/api/query-tabs/{tab_id}", {"name": "renamed.sql", "sql": "SELECT 1"}
        )
        self.assertEqual(renamed.status, 200)
        self.assertEqual(renamed.json["tab"]["name"], "renamed.sql")
        self.assertEqual(renamed.json["tab"]["sql"], "SELECT 1")

        deleted = self.h.client.delete(f"/api/query-tabs/{tab_id}")
        self.assertEqual(deleted.status, 200)
        self.assertTrue(deleted.json["deleted"])

    def test_deleting_last_tab_recreates_a_default(self):
        tabs = self.h.client.get("/api/query-tabs").json["tabs"]
        for tab in tabs:
            self.h.client.delete(f"/api/query-tabs/{tab['id']}")
        remaining = self.h.client.get("/api/query-tabs")
        self.assertGreaterEqual(len(remaining.json["tabs"]), 1)

    # --- saved queries ---------------------------------------------------
    def test_save_edit_and_delete_named_query(self):
        created = self.h.client.post(
            "/api/saved-queries",
            {"name": "Nation count", "sql": "SELECT count(*) FROM tpch.sf1.nation", "catalog": "tpch", "schema": "sf1"},
        )
        self.assertEqual(created.status, 201)
        qid = created.json["query"]["id"]

        listing = self.h.client.get("/api/saved-queries")
        self.assertEqual(len(listing.json["queries"]), 1)

        edited = self.h.client.patch(f"/api/saved-queries/{qid}", {"name": "Renamed", "sql": "SELECT 1"})
        self.assertEqual(edited.status, 200)
        self.assertEqual(edited.json["query"]["name"], "Renamed")

        deleted = self.h.client.delete(f"/api/saved-queries/{qid}")
        self.assertTrue(deleted.json["deleted"])

    # --- metadata browsing ----------------------------------------------
    def test_browse_cluster_metadata(self):
        # Catalog list comes from the attached catalogs (no Trino call needed).
        catalogs = self.h.client.get(f"/api/clusters/{self.cluster['id']}/metadata")
        self.assertEqual(catalogs.status, 200)
        self.assertEqual([c["name"] for c in catalogs.json["catalogs"]], ["system", "tpch"])

        # Drilling into a catalog/schema queries the coordinator's metadata.
        schemas = self.h.client.get(
            f"/api/clusters/{self.cluster['id']}/metadata?catalog=tpch"
        )
        self.assertEqual(schemas.status, 200)

        tables = self.h.client.get(
            f"/api/clusters/{self.cluster['id']}/metadata?catalog=tpch&schema=sf1"
        )
        self.assertEqual(tables.status, 200)


if __name__ == "__main__":
    unittest.main()
