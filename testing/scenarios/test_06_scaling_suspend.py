"""E2E scenario 06 — autoscaling and auto-suspend.

The control plane scales workers based on queued queries / CPU over successive
intervals, and auto-suspends an idle cluster after its configured window. Both
are time-sensitive, so the deterministic assertions drive the control methods
with an injected ``now`` (the harness exposes ``h.control``), while the public
poll/check endpoints are exercised for reachability through the real API.
"""

import unittest
from datetime import datetime, timedelta, timezone

from testing.harness import E2EHarness

NOW = datetime(2026, 6, 27, 12, 0, tzinfo=timezone.utc)


class ScalingAndSuspendScenario(unittest.TestCase):
    def setUp(self):
        self.h = E2EHarness()
        self.addCleanup(self.h.close)
        self.h.setup_admin()

    def test_autoscale_up_when_queries_stay_queued(self):
        cluster = self.h.create_running_cluster(
            "scale-up", worker_mode="autoscale", min_workers=1, max_workers=3
        )
        self.h.aws.trino_stats = {"ok": True, "running_queries": 1, "queued_queries": 1, "active_workers": 1}
        self.h.aws.cpu_average = 20.0

        first = self.h.control.autoscale_cluster_once(cluster["id"], now=NOW)
        second = self.h.control.autoscale_cluster_once(cluster["id"], now=NOW + timedelta(seconds=30))

        self.assertEqual(first["action"], "hold")
        self.assertEqual(second["action"], "scale")
        self.assertEqual(second["direction"], "up")
        self.assertEqual(second["to_workers"], 2)
        self.assertEqual(self.h.aws.scaling_calls[-1]["desired_capacity"], 2)

        # The scaling event is queryable through the API.
        events = self.h.client.get(f"/api/clusters/{cluster['id']}/scaling-events")
        self.assertEqual(events.status, 200)
        self.assertEqual(events.json["scaling_events"][0]["direction"], "up")

    def test_autoscale_down_after_idle_low_cpu(self):
        cluster = self.h.create_running_cluster(
            "scale-down", worker_mode="autoscale", min_workers=1, max_workers=3
        )
        self.h.aws.worker_asg.update(
            {"desired_capacity": 2, "in_service_capacity": 2, "instance_ids": ["i-worker-1", "i-worker-2"]}
        )
        self.h.aws.trino_stats = {"ok": True, "running_queries": 0, "queued_queries": 0, "active_workers": 2}
        self.h.aws.cpu_average = 10.0
        self.h.control._persist_autoscale_state(
            cluster["id"],
            {"queued_intervals": 0, "cpu_high_intervals": 0, "idle_low_since": NOW - timedelta(seconds=601)},
        )

        result = self.h.control.autoscale_cluster_once(cluster["id"], now=NOW)
        self.assertEqual(result["action"], "scale")
        self.assertEqual(result["direction"], "down")
        self.assertEqual(result["to_workers"], 1)

    def test_auto_suspend_after_idle_window(self):
        cluster = self.h.create_running_cluster(
            "idle-suspend", worker_mode="autoscale", min_workers=1, max_workers=2, auto_suspend_minutes=15
        )
        self.h.aws.trino_stats = {"ok": True, "running_queries": 0, "queued_queries": 0, "active_workers": 1}

        first = self.h.control.auto_suspend_cluster_once(cluster["id"], now=NOW)
        second = self.h.control.auto_suspend_cluster_once(
            cluster["id"], now=NOW + timedelta(minutes=15, seconds=1)
        )

        self.assertEqual(first["action"], "hold")
        self.assertEqual(second["action"], "suspend")

        current = self.h.client.get(f"/api/clusters/{cluster['id']}")
        self.assertEqual(current.json["cluster"]["status"], "Suspended")
        self.assertIn(("delete_asg", "trinohub-e2e-workers"), self.h.aws.cleanup_calls)

    def test_poll_endpoints_are_reachable(self):
        self.h.create_running_cluster("polled", worker_mode="autoscale", min_workers=1, max_workers=2)
        autoscale = self.h.client.post("/api/autoscaling/poll", {})
        self.assertEqual(autoscale.status, 200)
        self.assertIn("results", autoscale.json)

        suspend = self.h.client.post("/api/auto-suspend/poll", {})
        self.assertEqual(suspend.status, 200)
        self.assertIn("results", suspend.json)


if __name__ == "__main__":
    unittest.main()
