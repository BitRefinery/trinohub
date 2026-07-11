"""E2E scenario 08 — security and access controls.

Covers the app-layer protections that sit in front of the control plane:
authentication gating on protected routes, allowed-UI-CIDR enforcement (with
loopback and health-check exemptions), and the signed per-cluster node-config
bootstrap endpoint used by cluster nodes.
"""

import unittest

from testing.harness import E2EHarness


class SecurityAccessScenario(unittest.TestCase):
    def test_protected_routes_require_authentication(self):
        with E2EHarness() as h:
            for path in ("/api/clusters", "/api/catalogs", "/api/users", "/api/query-history"):
                resp = h.client.get(path)
                self.assertEqual(resp.status, 401, f"{path} should require auth")

    def test_health_endpoint_is_open(self):
        with E2EHarness() as h:
            resp = h.client.get("/api/health")
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.json, {"ok": True})

    def test_allowed_ui_cidr_blocks_outside_clients(self):
        # Restrict the UI to a private range; loopback stays exempt for health.
        with E2EHarness() as h:
            h.setup_admin(allowed_ui_cidrs=["10.0.0.0/8"])

            # A client outside the range is blocked at the middleware (403)...
            blocked = h.client.get("/api/me", client_ip="203.0.113.5")
            self.assertEqual(blocked.status, 403)
            self.assertIn("CIDR", blocked.json["error"])

            # ...but health is always reachable regardless of source IP.
            health = h.client.get("/api/health", client_ip="203.0.113.5")
            self.assertEqual(health.status, 200)

            # A client inside the allowed range is admitted.
            allowed = h.client.get("/api/me", client_ip="10.1.2.3")
            self.assertEqual(allowed.status, 200)

    def test_loopback_allowed_when_cidrs_configured(self):
        with E2EHarness() as h:
            h.setup_admin(allowed_ui_cidrs=["10.0.0.0/8"])
            # Default client IP is 127.0.0.1 (loopback) — must stay allowed.
            resp = h.client.get("/api/me")
            self.assertEqual(resp.status, 200)

    def test_node_config_requires_valid_bootstrap_token(self):
        with E2EHarness() as h:
            h.setup_admin()
            cluster = h.create_cluster("bootstrap", catalogs=["system"])
            # Starting mints the signed per-cluster bootstrap token.
            h.start_cluster(cluster["id"])

            # A bogus token is rejected (the node-config route is CIDR-exempt).
            bad = h.client.get(
                f"/api/node-config/{cluster['id']}?role=worker&token=not-a-real-token",
                client_ip="203.0.113.9",
            )
            self.assertNotEqual(bad.status, 200)


if __name__ == "__main__":
    unittest.main()
