"""E2E scenario 07 — user management and role-based access control.

Covers the admin user-management workflow (create, list, change role, reset
password, deactivate) and the RBAC boundary: a non-admin "user" can log in,
list clusters, and run queries, but cannot perform admin-only actions
(create cluster/catalog/user). Also guards the last-admin protections.
"""

import unittest

from testing.harness import E2EHarness

MEMBER_PASSWORD = "member-strong-password-1"


class UsersAndRbacScenario(unittest.TestCase):
    def setUp(self):
        self.h = E2EHarness()
        self.addCleanup(self.h.close)
        self.h.setup_admin()

    def _create_member(self, username="member", role="user"):
        return self.h.client.post(
            "/api/users", {"username": username, "password": MEMBER_PASSWORD, "role": role}
        )

    def test_admin_creates_and_lists_users(self):
        created = self._create_member()
        self.assertEqual(created.status, 201)
        self.assertEqual(created.json["user"]["role"], "user")

        listing = self.h.client.get("/api/users")
        self.assertEqual(listing.status, 200)
        usernames = {u["username"] for u in listing.json["users"]}
        self.assertEqual(usernames, {"admin", "member"})

    def test_promote_demote_and_deactivate(self):
        member_id = self._create_member().json["user"]["id"]

        promoted = self.h.client.patch(f"/api/users/{member_id}", {"role": "admin"})
        self.assertEqual(promoted.json["user"]["role"], "admin")

        demoted = self.h.client.patch(f"/api/users/{member_id}", {"role": "user"})
        self.assertEqual(demoted.json["user"]["role"], "user")

        deactivated = self.h.client.patch(f"/api/users/{member_id}", {"is_active": False})
        self.assertFalse(deactivated.json["user"]["is_active"])

    def test_password_reset_changes_login(self):
        member_id = self._create_member().json["user"]["id"]
        self.h.client.patch(f"/api/users/{member_id}", {"password": "brand-new-password-9"})

        # The old password no longer works; the new one does.
        self.h.logout()
        self.h.client.cookie = ""
        old = self.h.login("member", MEMBER_PASSWORD)
        self.assertEqual(old.status, 401)
        new = self.h.login("member", "brand-new-password-9")
        self.assertEqual(new.status, 200)

    def test_cannot_deactivate_last_admin(self):
        admin_id = next(
            u["id"] for u in self.h.client.get("/api/users").json["users"] if u["username"] == "admin"
        )
        resp = self.h.client.patch(f"/api/users/{admin_id}", {"is_active": False})
        self.assertEqual(resp.status, 409)
        self.assertIn("last active admin", resp.json["error"].lower())

    def test_non_admin_cannot_perform_admin_actions(self):
        self._create_member()
        self.h.logout()
        self.h.client.cookie = ""
        self.assertEqual(self.h.login("member", MEMBER_PASSWORD).status, 200)

        # Allowed for a normal user: read clusters.
        self.assertEqual(self.h.client.get("/api/clusters").status, 200)

        # Forbidden: creating clusters, catalogs, users.
        self.assertEqual(
            self.h.client.post(
                "/api/clusters",
                {"name": "nope", "preset": "Cost", "worker_mode": "fixed", "min_workers": 1, "max_workers": 1,
                 "catalogs": ["system"]},
            ).status,
            403,
        )
        self.assertEqual(
            self.h.client.post(
                "/api/catalogs",
                {"name": "nope", "type": "s3_glue", "config": self.h.s3_glue_config()},
            ).status,
            403,
        )
        self.assertEqual(
            self.h.client.post("/api/users", {"username": "x", "password": "y-strong-pass-1", "role": "user"}).status,
            403,
        )

    def test_non_admin_can_run_queries(self):
        # Admin provisions a running cluster, then a member runs a query on it.
        cluster = self.h.create_running_cluster("shared", catalogs=["system", "tpch"])
        self._create_member()
        self.h.logout()
        self.h.client.cookie = ""
        self.h.login("member", MEMBER_PASSWORD)

        query = self.h.run_query(cluster["id"], "SELECT 1", catalog="tpch")
        self.assertEqual(query["status"], "Finished")


if __name__ == "__main__":
    unittest.main()
