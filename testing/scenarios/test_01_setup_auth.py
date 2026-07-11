"""E2E scenario 01 — first-run setup, authentication, and session lifecycle.

Covers the very first things an operator does with a fresh TrinoHub:
complete setup (which creates the admin + AWS settings and logs them in),
inspect the session, log out, and log back in. Also guards the negative cases
that protect the install (setup can only run once; bad credentials rejected).
"""

import unittest

from testing.harness import E2EHarness


class SetupAndAuthScenario(unittest.TestCase):
    def setUp(self):
        self.h = E2EHarness()
        self.addCleanup(self.h.close)

    def test_first_run_setup_creates_admin_and_aws_settings(self):
        # Before setup, the API reports an incomplete install.
        status = self.h.client.get("/api/setup/status")
        self.assertEqual(status.status, 200)
        self.assertFalse(status.json["configured"])

        resp = self.h.setup_admin()
        self.assertEqual(resp.status, 201)
        self.assertEqual(resp.json["user"]["role"], "admin")
        self.assertEqual(resp.json["user"]["username"], "admin")

        # Setup is now complete and persisted (region/vpc/subnets from AWS).
        status = self.h.client.get("/api/setup/status")
        self.assertTrue(status.json["configured"])

        setup = resp.json["setup"]
        self.assertEqual(setup["region"], "us-east-2")
        self.assertEqual(setup["vpc_id"], "vpc-e2e")
        self.assertIn("subnet-e2e-a", setup["private_subnet_ids"])

    def test_setup_cannot_run_twice(self):
        self.h.setup_admin()
        second = self.h.client.post(
            "/api/setup/complete",
            {"username": "intruder", "password": "another-strong-pass", "node_instance_profile": "TrinoHubNodeRole"},
        )
        self.assertEqual(second.status, 409)

    def test_session_cookie_authenticates_me_endpoint(self):
        self.h.setup_admin()
        me = self.h.client.get("/api/me")
        self.assertEqual(me.status, 200)
        self.assertEqual(me.json["user"]["username"], "admin")

    def test_logout_then_login_again(self):
        self.h.setup_admin()

        logout = self.h.logout()
        self.assertEqual(logout.status, 200)

        # The cleared cookie means we are anonymous again.
        self.h.client.cookie = ""
        anon = self.h.client.get("/api/me")
        self.assertIsNone(anon.json["user"])

        good = self.h.login(self.h.ADMIN_USER, self.h.ADMIN_PASSWORD)
        self.assertEqual(good.status, 200)
        me = self.h.client.get("/api/me")
        self.assertEqual(me.json["user"]["username"], "admin")

    def test_login_rejects_wrong_password(self):
        self.h.setup_admin()
        self.h.logout()
        self.h.client.cookie = ""

        bad = self.h.login(self.h.ADMIN_USER, "definitely-wrong")
        self.assertEqual(bad.status, 401)


if __name__ == "__main__":
    unittest.main()
