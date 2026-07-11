"""E2E scenario 03 — catalog management.

Covers adding, listing, editing, validating (live check against a running
cluster), and removing S3 + Glue catalogs, plus attaching a catalog to a
cluster and the guard rails (no static credentials, no editing built-ins,
cannot delete a catalog while it is attached to a cluster).
"""

import unittest

from testing.harness import E2EHarness


class CatalogScenario(unittest.TestCase):
    def setUp(self):
        self.h = E2EHarness()
        self.addCleanup(self.h.close)
        self.h.setup_admin()

    def _create_lake(self, name="lake", **config):
        return self.h.client.post(
            "/api/catalogs",
            {"name": name, "type": "s3_glue", "config": self.h.s3_glue_config(**config)},
        )

    def test_builtin_catalogs_are_listed(self):
        resp = self.h.client.get("/api/catalogs")
        self.assertEqual(resp.status, 200)
        names = {c["name"] for c in resp.json["catalogs"]}
        self.assertTrue({"system", "tpch", "tpcds"}.issubset(names))

    def test_add_edit_and_remove_s3_glue_catalog(self):
        created = self._create_lake("lake")
        self.assertEqual(created.status, 201)
        catalog = created.json["catalog"]
        self.assertEqual(catalog["name"], "lake")
        self.assertEqual(catalog["type"], "s3_glue")
        # warehouse path is normalised to end with a slash.
        self.assertTrue(catalog["config"]["warehouse"].endswith("/"))

        # Edit: switch to read-only access mode.
        edited = self.h.client.patch(
            f"/api/catalogs/{catalog['id']}",
            {"name": "lake", "type": "s3_glue", "config": self.h.s3_glue_config(access_mode="read_only")},
        )
        self.assertEqual(edited.status, 200)
        self.assertEqual(edited.json["catalog"]["config"]["access_mode"], "read_only")

        # Remove.
        deleted = self.h.client.delete(f"/api/catalogs/{catalog['id']}")
        self.assertEqual(deleted.status, 200)
        self.assertTrue(deleted.json["deleted"])
        names = {c["name"] for c in self.h.client.get("/api/catalogs").json["catalogs"]}
        self.assertNotIn("lake", names)

    def test_catalog_rejects_static_credentials(self):
        resp = self.h.client.post(
            "/api/catalogs",
            {
                "name": "insecure",
                "type": "s3_glue",
                "config": self.h.s3_glue_config(aws_secret_access_key="AKIAEXAMPLE"),
            },
        )
        self.assertEqual(resp.status, 400)
        self.assertIn("secret", resp.json["error"].lower())

    def test_builtin_catalog_cannot_be_edited(self):
        builtin = next(c for c in self.h.client.get("/api/catalogs").json["catalogs"] if c["name"] == "tpch")
        resp = self.h.client.patch(
            f"/api/catalogs/{builtin['id']}",
            {"name": "tpch", "type": "s3_glue", "config": self.h.s3_glue_config()},
        )
        self.assertEqual(resp.status, 400)

    def test_attach_catalog_to_cluster_and_block_delete_while_attached(self):
        self._create_lake("lake")
        cluster = self.h.create_cluster("withlake", catalogs=["system", "lake"])
        self.assertIn("lake", cluster["catalogs"])

        catalog = next(c for c in self.h.client.get("/api/catalogs").json["catalogs"] if c["name"] == "lake")
        blocked = self.h.client.delete(f"/api/catalogs/{catalog['id']}")
        self.assertEqual(blocked.status, 409)
        self.assertIn("attached", blocked.json["error"].lower())

    def test_live_check_against_running_cluster(self):
        self._create_lake("lake")
        cluster = self.h.create_running_cluster("checker", catalogs=["system", "lake"])

        resp = self.h.client.post(
            "/api/catalogs/check",
            {
                "name": "lake",
                "type": "s3_glue",
                "config": self.h.s3_glue_config(),
                "cluster_id": cluster["id"],
            },
        )
        self.assertEqual(resp.status, 200)
        self.assertTrue(resp.json["ok"])
        self.assertTrue(resp.json["live_check"]["checked"])
        self.assertTrue(resp.json["live_check"]["ok"])
        # The live check issues a real SHOW SCHEMAS against the fake coordinator.
        self.assertTrue(any("SHOW SCHEMAS" in s["sql_text"].upper() for s in self.h.trino.submitted))

    def test_create_cluster_rejects_unknown_catalog(self):
        resp = self.h.client.post(
            "/api/clusters",
            {"name": "bad", "instance_type": self.h.DEFAULT_INSTANCE_TYPE, "worker_mode": "fixed",
             "min_workers": 1, "max_workers": 1,
             "catalogs": ["system", "does_not_exist"]},
        )
        self.assertEqual(resp.status, 400)
        self.assertIn("does_not_exist", resp.json["error"])


if __name__ == "__main__":
    unittest.main()
