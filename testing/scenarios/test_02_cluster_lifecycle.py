"""E2E scenario 02 — full cluster lifecycle.

Walks a cluster through every state transition an operator drives:

    create -> start (billable confirm) -> running (health) -> suspend
          -> restart -> disable -> delete

and asserts the AWS-resource bookkeeping and cleanup that must accompany each
step (resources recorded on start, cleaned on suspend/disable, gone on delete).
"""

import unittest

from testing.harness import E2EHarness


class ClusterLifecycleScenario(unittest.TestCase):
    def setUp(self):
        self.h = E2EHarness()
        self.addCleanup(self.h.close)
        self.h.setup_admin()

    def _resource_types(self, cluster_id):
        resp = self.h.client.get(f"/api/clusters/{cluster_id}/resources")
        self.assertEqual(resp.status, 200)
        return sorted({r["type"] for r in resp.json["resources"]})

    def test_create_cluster_starts_not_enabled(self):
        cluster = self.h.create_cluster("analytics", catalogs=["system", "tpch"])
        self.assertEqual(cluster["status"], "Not enabled")
        self.assertEqual(cluster["catalogs"], ["system", "tpch"])

        listing = self.h.client.get("/api/clusters")
        self.assertEqual(listing.status, 200)
        self.assertEqual([c["name"] for c in listing.json["clusters"]], ["analytics"])

    def test_start_requires_billable_confirmation(self):
        cluster = self.h.create_cluster("guarded")
        unconfirmed = self.h.start_cluster(cluster["id"], confirm=False)
        self.assertEqual(unconfirmed.status, 409)
        self.assertIn("billable", unconfirmed.json["error"].lower())

        # Cluster stayed un-provisioned.
        current = self.h.client.get(f"/api/clusters/{cluster['id']}")
        self.assertEqual(current.json["cluster"]["status"], "Not enabled")

    def test_full_lifecycle_create_start_suspend_restart_disable_delete(self):
        cluster = self.h.create_cluster("lifecycle", catalogs=["system", "tpch"])
        cid = cluster["id"]

        # --- start -> Starting, resources recorded -----------------------
        start = self.h.start_cluster(cid)
        self.assertEqual(start.status, 200)
        self.assertEqual(start.json["cluster"]["status"], "Starting")
        self.assertEqual(
            self._resource_types(cid),
            ["auto_scaling_group", "coordinator_instance", "launch_template", "security_group"],
        )

        # --- health refresh -> Running -----------------------------------
        health = self.h.refresh_health(cid)
        self.assertEqual(health.json["cluster"]["status"], "Running")

        # --- suspend -> Suspended, runtime resources cleaned -------------
        suspend = self.h.suspend_cluster(cid)
        self.assertEqual(suspend.status, 200)
        self.assertEqual(suspend.json["cluster"]["status"], "Suspended")
        # Coordinator/ASG/launch-template torn down (security group may remain).
        self.assertNotIn("coordinator_instance", self._resource_types(cid))
        self.assertIn(("delete_asg", "trinohub-e2e-workers"), self.h.aws.cleanup_calls)

        # --- restart from suspended --------------------------------------
        restart = self.h.start_cluster(cid)
        self.assertEqual(restart.status, 200)
        self.assertEqual(restart.json["cluster"]["status"], "Starting")
        self.h.refresh_health(cid)

        # --- disable -> Not enabled --------------------------------------
        disable = self.h.disable_cluster(cid)
        self.assertEqual(disable.status, 200)
        self.assertEqual(disable.json["cluster"]["status"], "Not enabled")
        self.assertEqual(self._resource_types(cid), [])

        # --- delete -> gone ----------------------------------------------
        delete = self.h.delete_cluster(cid)
        self.assertEqual(delete.status, 200)
        self.assertTrue(delete.json["deleted"])
        gone = self.h.client.get(f"/api/clusters/{cid}")
        self.assertEqual(gone.status, 404)

    def test_update_cluster_worker_range_before_start(self):
        cluster = self.h.create_cluster("resize", worker_mode="autoscale", min_workers=1, max_workers=3)
        resp = self.h.client.patch(f"/api/clusters/{cluster['id']}", {"max_workers": 6})
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.json["cluster"]["max_workers"], 6)
        self.assertEqual(resp.json["changes"], ["max_workers"])

    def test_delete_running_capable_cluster_directly(self):
        cluster = self.h.create_running_cluster("ephemeral", catalogs=["system"])
        delete = self.h.delete_cluster(cluster["id"])
        self.assertTrue(delete.json["deleted"])
        # All AWS resources cleaned up as part of delete.
        self.assertIn(("delete_asg", "trinohub-e2e-workers"), self.h.aws.cleanup_calls)

    def test_cluster_events_recorded_through_lifecycle(self):
        cluster = self.h.create_running_cluster("audited", catalogs=["system"])
        events = self.h.client.get(f"/api/clusters/{cluster['id']}/events")
        self.assertEqual(events.status, 200)
        types = {e["event_type"] for e in events.json["events"]}
        self.assertIn("provisioning_started", types)
        self.assertIn("resources_created", types)
        self.assertIn("coordinator_ready", types)


if __name__ == "__main__":
    unittest.main()
