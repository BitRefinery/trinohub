import base64
import hashlib
import json
import os
import tempfile
import unittest
import unittest.mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

from trinohub.aws_checks import TRINO_HTTP_PORT, TRINO_VERSION, AwsInspector
from trinohub.server import ApiError, TrinoHubApp


class FakeAws:
    def __init__(self):
        self.cleanup_calls = []
        self.health_calls = []
        self.scaling_calls = []
        self.worker_template_calls = []
        self.worker_asg = {
            "found": True,
            "name": "trinohub-test-cluster-workers",
            "desired_capacity": 1,
            "min_size": 1,
            "max_size": 3,
            "in_service_capacity": 1,
            "pending_capacity": 0,
            "instance_ids": ["i-worker-1"],
        }
        self.trino_stats = {
            "ok": True,
            "running_queries": 0,
            "queued_queries": 0,
            "active_workers": 1,
        }
        self.cpu_average = 10.0
        self.health_response = {
            "ok": True,
            "state": "running",
            "url": "http://10.0.1.10:8080/v1/info",
            "node_version": {"version": TRINO_VERSION},
        }

    def metadata(self):
        return {
            "available": True,
            "instance_id": "i-test",
            "role": "TrinoHubControlPlaneRole",
            "region": "us-east-2",
            "account_id": "123456789012",
        }

    def control_plane_private_ip(self):
        return "10.0.9.9"

    def full_status(self, region=None):
        return {
            "region": region or "us-east-2",
            "metadata": self.metadata(),
            "identity": {"Arn": "arn:aws:sts::123456789012:assumed-role/TrinoHubControlPlaneRole/i-test"},
            "network": {
                "vpcs": [{"vpc_id": "vpc-test", "cidr": "10.0.0.0/16", "is_default": False}],
                "subnets": [{"subnet_id": "subnet-test", "vpc_id": "vpc-test", "az": "us-east-2a"}],
                "security_groups": [{"group_id": "sg-test", "vpc_id": "vpc-test", "name": "default"}],
            },
            "checks": [{"name": "sts:GetCallerIdentity", "ok": True, "detail": "ok"}],
            "ok": True,
        }

    def dry_run_instance_launch(self, **kwargs):
        return {"ok": True, "code": "DryRunOperation", "detail": "Request would have succeeded."}

    def available_instance_types(self, region, instance_types):
        return list(instance_types)

    def trino_node_config_script(self, **kwargs):
        return AwsInspector(region=kwargs.get("region") or "us-east-2").trino_node_config_script(**kwargs)

    def ensure_managed_security_group(self, **kwargs):
        return {"group_id": "sg-managed", "created": True, "group_name": f"trinohub-{kwargs['cluster_name']}-nodes"}

    def launch_coordinator_instance(self, **kwargs):
        return {
            "instance_id": "i-coordinator",
            "image_id": "ami-test",
            "instance_type": kwargs["instance_type"],
            "private_ip_address": "10.0.1.10",
            "private_dns_name": "ip-10-0-1-10.us-east-2.compute.internal",
        }

    def create_worker_launch_template(self, **kwargs):
        self.worker_template_calls.append(kwargs)
        return {
            "launch_template_id": "lt-test",
            "launch_template_name": "trinohub-test-cluster-workers",
            "image_id": kwargs["image_id"],
            "instance_type": kwargs["instance_type"],
            "coordinator_uri": kwargs["coordinator_uri"],
        }

    def coordinator_health(self, **kwargs):
        self.health_calls.append(kwargs["coordinator_endpoint"])
        return dict(self.health_response)

    def trino_cluster_stats(self, **kwargs):
        return dict(self.trino_stats)

    def create_worker_auto_scaling_group(self, **kwargs):
        return {
            "auto_scaling_group_name": "trinohub-test-cluster-workers",
            "desired_capacity": kwargs["cluster"]["min_workers"],
            "min_size": kwargs["cluster"]["min_workers"],
            "max_size": kwargs["cluster"]["max_workers"],
        }

    def delete_worker_auto_scaling_group(self, **kwargs):
        self.cleanup_calls.append(("delete_asg", kwargs["name"]))
        return {"deleted": True, "resource_id": kwargs["name"]}

    def worker_auto_scaling_group(self, **kwargs):
        return dict(self.worker_asg)

    def set_worker_desired_capacity(self, **kwargs):
        self.scaling_calls.append(kwargs)
        self.worker_asg["desired_capacity"] = kwargs["desired_capacity"]
        return {"updated": True, **kwargs}

    def worker_cpu_average(self, **kwargs):
        return self.cpu_average

    def terminate_instances(self, **kwargs):
        self.cleanup_calls.append(("terminate_instances", tuple(kwargs["instance_ids"])))
        return {"terminated": kwargs["instance_ids"], "not_found": []}

    def delete_launch_template(self, **kwargs):
        self.cleanup_calls.append(("delete_launch_template", kwargs["launch_template_id"]))
        return {"deleted": True, "resource_id": kwargs["launch_template_id"]}

    def wait_for_cluster_instances_gone(self, **kwargs):
        self.cleanup_calls.append(("wait_for_instances", kwargs["cluster_name"]))
        return {"gone": True, "remaining_instance_ids": []}

    def cleanup_managed_security_group_rules(self, **kwargs):
        self.cleanup_calls.append(("cleanup_security_group_rules", kwargs["group_id"]))
        return {"revoked": [{"group_id": kwargs["group_id"]}], "missing": [], "failed": []}

    def delete_security_group(self, **kwargs):
        self.cleanup_calls.append(("delete_security_group", kwargs["group_id"]))
        return {"deleted": True, "resource_id": kwargs["group_id"]}


class FakeSecretStore:
    """In-memory SecretStore for tests: records puts/gets/deletes, no AWS."""

    def __init__(self):
        self.secrets = {}
        self.deleted = []

    def put(self, key, value):
        ref = f"arn:aws:secretsmanager:us-east-2:123456789012:secret:trinohub/catalog/{key}"
        self.secrets[ref] = value
        return ref

    def get(self, ref):
        return self.secrets[ref]

    def delete(self, ref):
        self.deleted.append(ref)
        self.secrets.pop(ref, None)


class SecurityGroupDependencyAws(FakeAws):
    def __init__(self):
        super().__init__()
        self.security_group_rules_cleaned = False

    def ensure_managed_security_group(self, **kwargs):
        result = super().ensure_managed_security_group(**kwargs)
        result.update(
            {
                "control_plane_ingress": {
                    "authorized": True,
                    "via": "security_group",
                    "group_ids": ["sg-control"],
                },
                "node_to_control_plane_ingress": {
                    "authorized": True,
                    "target_group_ids": ["sg-control"],
                    "node_group_id": result["group_id"],
                    "port": 8000,
                },
            }
        )
        return result

    def cleanup_managed_security_group_rules(self, **kwargs):
        self.security_group_rules_cleaned = True
        return super().cleanup_managed_security_group_rules(**kwargs)

    def delete_security_group(self, **kwargs):
        if kwargs["group_id"] == "sg-managed" and not self.security_group_rules_cleaned:
            raise RuntimeError("DependencyViolation")
        return super().delete_security_group(**kwargs)


class ServerModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # Most tests exercise behavior after setup; the first-run token gate has
        # its own dedicated tests below, so disable it here.
        self.app = TrinoHubApp(
            db_path=Path(self.tmp.name) / "test.sqlite3", aws=FakeAws(), require_setup_token=False
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_login_rate_limit_locks_after_repeated_failures(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        for _ in range(5):
            with self.assertRaises(ApiError) as ctx:
                self.app.login({"username": "admin", "password": "wrong-password"})
            self.assertEqual(ctx.exception.status, 401)
        # The 6th attempt is rejected before the password is even checked.
        with self.assertRaises(ApiError) as ctx:
            self.app.login({"username": "admin", "password": "wrong-password"})
        self.assertEqual(ctx.exception.status, 429)

    def test_login_success_clears_failure_counter(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        for _ in range(4):
            with self.assertRaises(ApiError):
                self.app.login({"username": "admin", "password": "wrong-password"})
        result, token = self.app.login({"username": "admin", "password": "correct-horse-password"})
        self.assertTrue(token)
        # After a clean login the counter resets, so failures can accumulate again.
        with self.assertRaises(ApiError) as ctx:
            self.app.login({"username": "admin", "password": "wrong-password"})
        self.assertEqual(ctx.exception.status, 401)

    def test_connection_enables_wal_and_busy_timeout(self):
        with self.app.conn() as conn:
            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        self.assertEqual(journal_mode.lower(), "wal")
        self.assertEqual(busy_timeout, 5000)

    def test_setup_creates_admin_and_settings(self):
        result, token = self.app.complete_setup(
            {
                "username": "admin",
                "email": "admin@example.com",
                "password": "correct-horse-password",
                "node_instance_profile": "TrinoHubNodeRole",
            }
        )
        self.assertTrue(token)
        self.assertEqual(result["user"]["role"], "admin")
        self.assertEqual(result["setup"]["vpc_id"], "vpc-test")
        self.assertEqual(result["setup"]["private_subnet_ids"], ["subnet-test"])

    def test_setup_normalizes_and_enforces_allowed_ui_cidrs(self):
        result, _ = self.app.complete_setup(
            {
                "username": "admin",
                "password": "correct-horse-password",
                "allowed_ui_cidrs": ["203.0.113.4", "2001:db8::/64"],
            }
        )

        self.assertEqual(result["setup"]["allowed_ui_cidrs"], ["203.0.113.4/32", "2001:db8::/64"])
        self.assertTrue(self.app.client_ip_allowed(remote_addr="203.0.113.4"))
        self.assertTrue(self.app.client_ip_allowed(remote_addr="127.0.0.1"))
        self.assertTrue(self.app.client_ip_allowed(remote_addr="127.0.0.1", forwarded_for="203.0.113.4"))
        self.assertFalse(self.app.client_ip_allowed(remote_addr="198.51.100.5"))
        # Do not trust a spoofed X-Forwarded-For header from a direct non-loopback peer.
        self.assertFalse(self.app.client_ip_allowed(remote_addr="198.51.100.5", forwarded_for="203.0.113.4"))

    def test_setup_rejects_invalid_allowed_ui_cidr(self):
        with self.assertRaises(ApiError) as context:
            self.app.complete_setup(
                {
                    "username": "admin",
                    "password": "correct-horse-password",
                    "allowed_ui_cidrs": ["not-a-cidr"],
                }
            )

        self.assertEqual(context.exception.status, 400)

    def test_setup_rejects_allowed_ui_cidrs_that_lock_out_requester(self):
        payload = {
            "username": "admin",
            "password": "correct-horse-password",
            "allowed_ui_cidrs": ["203.0.113.4/32"],
        }
        with self.assertRaises(ApiError) as context:
            self.app.complete_setup(payload, remote_addr="198.51.100.5")
        self.assertEqual(context.exception.status, 400)
        self.assertIn("198.51.100.5", context.exception.message)
        self.assertIsNone(self.app.setup_row())

        # Behind the loopback proxy the X-Forwarded-For hop is what gets judged.
        with self.assertRaises(ApiError):
            self.app.complete_setup(payload, remote_addr="127.0.0.1", forwarded_for="198.51.100.5")

        # A requester inside the list sails through.
        result, _ = self.app.complete_setup(payload, remote_addr="203.0.113.4")
        self.assertEqual(result["setup"]["allowed_ui_cidrs"], ["203.0.113.4/32"])

    def test_setup_lockout_guard_honors_confirm_and_loopback(self):
        # Explicit confirm_lockout applies the list even though it excludes the caller.
        result, _ = self.app.complete_setup(
            {
                "username": "admin",
                "password": "correct-horse-password",
                "allowed_ui_cidrs": ["203.0.113.4/32"],
                "confirm_lockout": True,
            },
            remote_addr="198.51.100.5",
        )
        self.assertEqual(result["setup"]["allowed_ui_cidrs"], ["203.0.113.4/32"])

    def test_setup_lockout_guard_skips_loopback_requester(self):
        # A loopback caller (host access) can always get back in, so no guard.
        result, _ = self.app.complete_setup(
            {
                "username": "admin",
                "password": "correct-horse-password",
                "allowed_ui_cidrs": ["203.0.113.4/32"],
            },
            remote_addr="127.0.0.1",
        )
        self.assertEqual(result["setup"]["allowed_ui_cidrs"], ["203.0.113.4/32"])

    def test_set_allowed_ui_cidrs_requires_completed_setup(self):
        with self.assertRaises(ApiError) as context:
            self.app.set_allowed_ui_cidrs({"allowed_ui_cidrs": ["203.0.113.4/32"]})
        self.assertEqual(context.exception.status, 409)

    def test_set_allowed_ui_cidrs_updates_and_guards_lockout(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        self.assertTrue(self.app.client_ip_allowed(remote_addr="198.51.100.5"))

        # A list excluding the requester is refused and nothing changes.
        with self.assertRaises(ApiError) as context:
            self.app.set_allowed_ui_cidrs(
                {"allowed_ui_cidrs": ["203.0.113.4/32"]}, remote_addr="198.51.100.5"
            )
        self.assertEqual(context.exception.status, 400)
        self.assertTrue(self.app.client_ip_allowed(remote_addr="198.51.100.5"))

        # A list including the requester applies, normalized, and gates others.
        result = self.app.set_allowed_ui_cidrs(
            {"allowed_ui_cidrs": ["198.51.100.5", "2001:db8::/64"]}, remote_addr="198.51.100.5"
        )
        self.assertEqual(result["allowed_ui_cidrs"], ["198.51.100.5/32", "2001:db8::/64"])
        self.assertTrue(self.app.client_ip_allowed(remote_addr="198.51.100.5"))
        self.assertFalse(self.app.client_ip_allowed(remote_addr="203.0.113.4"))

        # confirm_lockout is the explicit escape hatch.
        result = self.app.set_allowed_ui_cidrs(
            {"allowed_ui_cidrs": ["203.0.113.4/32"], "confirm_lockout": True},
            remote_addr="198.51.100.5",
        )
        self.assertEqual(result["allowed_ui_cidrs"], ["203.0.113.4/32"])
        self.assertFalse(self.app.client_ip_allowed(remote_addr="198.51.100.5"))

        # Clearing the list reopens app-level access (the SG still gates).
        result = self.app.set_allowed_ui_cidrs({"allowed_ui_cidrs": []}, remote_addr="203.0.113.4")
        self.assertEqual(result["allowed_ui_cidrs"], [])
        self.assertTrue(self.app.client_ip_allowed(remote_addr="198.51.100.5"))

    def test_setup_rejects_failed_aws_validation(self):
        def failed_status(region=None):
            status = FakeAws().full_status(region)
            status["ok"] = False
            status["checks"] = [{"name": "iam:PassRole", "ok": False, "detail": "AccessDenied"}]
            return status

        self.app.aws.full_status = failed_status
        with self.assertRaises(ApiError) as context:
            self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})

        self.assertEqual(context.exception.status, 400)
        self.assertIn("iam:PassRole", context.exception.message)

    def test_cluster_record_after_setup(self):
        self.app.complete_setup(
            {
                "username": "admin",
                "password": "correct-horse-password",
                "allowed_instance_types": ["r7i.2xlarge"],
            }
        )
        with self.app.conn() as conn:
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        result = self.app.create_cluster(
            {
                "name": "test-cluster",
                "instance_type": "r7i.2xlarge",
                "worker_mode": "autoscale",
                "min_workers": 1,
                "max_workers": 3,
                "catalogs": ["system", "tpch"],
            },
            user,
        )
        self.assertEqual(result["cluster"]["status"], "Not enabled")
        self.assertEqual(result["cluster"]["instance_type"], "r7i.2xlarge")
        self.assertEqual(result["cluster"]["catalogs"], ["system", "tpch"])

    def _admin_and_cluster(self, hostname=""):
        """Complete setup, create one 'lakehouse' cluster, return (admin, id)."""
        self.app.complete_setup(
            {
                "username": "admin",
                "password": "correct-horse-password",
                "allowed_instance_types": ["r7i.2xlarge"],
            }
        )
        with self.app.conn() as conn:
            admin = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        result = self.app.create_cluster(
            {"name": "lakehouse", "instance_type": "r7i.2xlarge", "hostname": hostname},
            admin,
        )
        return admin, result["cluster"]["id"]

    def _attach_coordinator(self, cluster_id, private_ip="10.0.1.10"):
        with self.app.conn() as conn:
            conn.execute(
                """
                INSERT INTO provider_resources
                  (cluster_id, provider, resource_type, resource_id, region, metadata_json, created_at)
                VALUES (?, 'aws', 'coordinator_instance', 'i-coordinator', 'us-east-2', ?, ?)
                """,
                (cluster_id, json.dumps({"private_ip_address": private_ip}), "2020-01-01T00:00:00+00:00"),
            )

    def test_connection_info_uses_base_domain(self):
        admin, cluster_id = self._admin_and_cluster()
        self.app.set_cluster_base_domain({"cluster_base_domain": "Trino.Acme.Internal."})
        info = self.app.cluster_connection_info(cluster_id, admin)
        self.assertTrue(info["resolvable"])
        self.assertEqual(info["trino_version"], TRINO_VERSION)
        self.assertEqual(info["via"], "domain")
        # Domain is normalized (lowercased, trailing dot stripped) and prefixed by name.
        self.assertEqual(info["host"], "lakehouse.trino.acme.internal")
        self.assertEqual(info["port"], 443)
        self.assertEqual(info["scheme"], "https")
        self.assertTrue(info["tls"])
        self.assertEqual(info["user"], "admin")
        self.assertEqual(info["jdbc_url"], "jdbc:trino://lakehouse.trino.acme.internal:443?user=admin&SSL=true")
        self.assertIn("SSL=1", info["odbc"])
        self.assertIn("https://lakehouse.trino.acme.internal:443", info["cli"])
        # Coordinator web UI link inherits the resolved host/scheme/port.
        self.assertEqual(info["web_ui"], "https://lakehouse.trino.acme.internal:443/ui/")

    def test_connection_info_hostname_override_wins(self):
        admin, cluster_id = self._admin_and_cluster(hostname="analytics-prod.acme.internal")
        self.app.set_cluster_base_domain({"cluster_base_domain": "trino.acme.internal"})
        info = self.app.cluster_connection_info(cluster_id, admin)
        self.assertEqual(info["via"], "override")
        self.assertEqual(info["host"], "analytics-prod.acme.internal")
        self.assertEqual(info["port"], 443)

    def test_connection_info_falls_back_to_coordinator_ip(self):
        admin, cluster_id = self._admin_and_cluster()
        self._attach_coordinator(cluster_id)
        info = self.app.cluster_connection_info(cluster_id, admin)
        self.assertTrue(info["resolvable"])
        self.assertEqual(info["via"], "coordinator_ip")
        self.assertEqual(info["host"], "10.0.1.10")
        self.assertEqual(info["port"], TRINO_HTTP_PORT)
        self.assertEqual(info["scheme"], "http")
        self.assertFalse(info["tls"])
        self.assertNotIn("SSL=true", info["jdbc_url"])
        self.assertIn("SSL=0", info["odbc"])
        self.assertEqual(info["web_ui"], f"http://10.0.1.10:{TRINO_HTTP_PORT}/ui/")

    def test_connection_info_not_resolvable_without_domain_or_coordinator(self):
        admin, cluster_id = self._admin_and_cluster()
        info = self.app.cluster_connection_info(cluster_id, admin)
        self.assertFalse(info["resolvable"])
        self.assertIn("hint", info)
        self.assertNotIn("jdbc_url", info)
        self.assertNotIn("web_ui", info)

    def test_set_cluster_base_domain_rejects_invalid(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.assertRaises(ApiError) as ctx:
            self.app.set_cluster_base_domain({"cluster_base_domain": "not a domain!"})
        self.assertEqual(ctx.exception.status, 400)

    def _set_cluster_status(self, cluster_id, status):
        with self.app.conn() as conn:
            conn.execute("UPDATE clusters SET status = ? WHERE id = ?", (status, cluster_id))

    def test_tls_routes_running_cluster_points_at_coordinator(self):
        _, cluster_id = self._admin_and_cluster()
        self.app.set_cluster_base_domain({"cluster_base_domain": "trino.acme.internal"})
        # Not enabled, no coordinator, not resumable -> no upstream (gateway 503s).
        self.assertEqual(self.app.cluster_tls_routes(), {})
        self._attach_coordinator(cluster_id, private_ip="10.0.1.10")
        # A coordinator resource alone isn't enough; only a Running cluster routes
        # straight to Trino.
        self._set_cluster_status(cluster_id, "Running")
        self.assertEqual(
            self.app.cluster_tls_routes(),
            {"lakehouse.trino.acme.internal": "10.0.1.10:8080"},
        )

    def test_tls_routes_use_hostname_override(self):
        _, cluster_id = self._admin_and_cluster(hostname="analytics.example.com")
        self.app.set_cluster_base_domain({"cluster_base_domain": "trino.acme.internal"})
        self._attach_coordinator(cluster_id, private_ip="10.0.1.11")
        self._set_cluster_status(cluster_id, "Running")
        self.assertEqual(self.app.cluster_tls_routes(), {"analytics.example.com": "10.0.1.11:8080"})

    def test_tls_routes_resuming_and_suspended_hosts_point_at_shim(self):
        from trinohub.tls_gateway import SHIM_UPSTREAM

        _, cluster_id = self._admin_and_cluster()
        self.app.set_cluster_base_domain({"cluster_base_domain": "trino.acme.internal"})
        host = "lakehouse.trino.acme.internal"
        # Starting: coordinator may exist but isn't answering yet -> shim, never the
        # half-booted coordinator IP.
        self._attach_coordinator(cluster_id, private_ip="10.0.1.10")
        self._set_cluster_status(cluster_id, "Starting")
        self.assertEqual(self.app.cluster_tls_routes(), {host: SHIM_UPSTREAM})
        # Auto-suspended (resumable) -> shim so a query resumes it.
        with self.app.conn() as conn:
            conn.execute(
                "UPDATE clusters SET status = 'Suspended', auto_suspend_minutes = 15 WHERE id = ?",
                (cluster_id,),
            )
        self.assertEqual(self.app.cluster_tls_routes(), {host: SHIM_UPSTREAM})
        # Manually suspended (no auto) -> no route (gateway 503s, unchanged).
        with self.app.conn() as conn:
            conn.execute(
                "UPDATE clusters SET status = 'Suspended', auto_suspend_minutes = NULL WHERE id = ?",
                (cluster_id,),
            )
        self.assertEqual(self.app.cluster_tls_routes(), {})

    def test_authorize_tls_domain(self):
        self._admin_and_cluster()
        # Inactive until a base domain is set.
        self.assertFalse(self.app.authorize_tls_domain("lakehouse.trino.acme.internal"))
        self.app.set_cluster_base_domain({"cluster_base_domain": "trino.acme.internal"})
        self.assertTrue(self.app.authorize_tls_domain("trino.acme.internal"))
        self.assertTrue(self.app.authorize_tls_domain("lakehouse.trino.acme.internal"))
        # Case/trailing-dot normalized.
        self.assertTrue(self.app.authorize_tls_domain("LAKEHOUSE.trino.acme.internal."))
        # A made-up subdomain or a foreign domain is refused (no cert minted).
        self.assertFalse(self.app.authorize_tls_domain("evil.trino.acme.internal"))
        self.assertFalse(self.app.authorize_tls_domain("lakehouse.other.example"))

    def test_build_caddyfile_renders_routes_and_cidr_gate(self):
        from trinohub.tls_gateway import build_caddyfile

        conf = build_caddyfile(
            "trino.acme.internal",
            ["203.0.113.4/32"],
            {"lakehouse.trino.acme.internal": "10.0.1.10:8080"},
        )
        self.assertIn("*.trino.acme.internal, trino.acme.internal {", conf)
        self.assertIn("on_demand", conf)
        # HTTP/3 disabled: operators only open TCP 443, so QUIC/UDP would stall browsers.
        self.assertIn("protocols h1 h2", conf)
        self.assertIn("@blocked not remote_ip 203.0.113.4/32", conf)
        self.assertIn("@c0 host lakehouse.trino.acme.internal", conf)
        self.assertIn("reverse_proxy @c0 10.0.1.10:8080", conf)

    def test_build_caddyfile_without_cidrs_allows_all(self):
        from trinohub.tls_gateway import build_caddyfile

        conf = build_caddyfile("trino.acme.internal", [], {})
        self.assertNotIn("@blocked", conf)
        self.assertIn("No running cluster for this hostname.", conf)

    def test_build_caddyfile_adds_override_host_as_site(self):
        from trinohub.tls_gateway import build_caddyfile

        conf = build_caddyfile("trino.acme.internal", [], {"analytics.example.com": "10.0.1.11:8080"})
        self.assertIn("analytics.example.com {", conf)

    def test_create_cluster_defaults_and_pins_trino_version(self):
        from trinohub.aws_checks import SUPPORTED_TRINO_VERSIONS, TRINO_VERSION

        admin, cluster_id = self._admin_and_cluster()
        # Default cluster gets the current default version.
        with self.app.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
        self.assertEqual(self.app.public_cluster(row)["trino_version"], TRINO_VERSION)

        # An explicit supported version is persisted and surfaced.
        older = SUPPORTED_TRINO_VERSIONS[-1]
        result = self.app.create_cluster(
            {"name": "pinned", "instance_type": "r7i.2xlarge", "trino_version": older}, admin
        )
        self.assertEqual(result["cluster"]["trino_version"], older)

    def test_create_cluster_rejects_unsupported_trino_version(self):
        admin, _ = self._admin_and_cluster()
        with self.assertRaises(ApiError) as ctx:
            self.app.create_cluster(
                {"name": "badver", "instance_type": "r7i.2xlarge", "trino_version": "123"}, admin
            )
        self.assertEqual(ctx.exception.status, 400)

    def test_trino_version_options_lists_supported_newest_first(self):
        from trinohub.aws_checks import SUPPORTED_TRINO_VERSIONS, TRINO_VERSION

        # No fetcher configured (the unit-test default): static list only.
        options = self.app.trino_version_options()
        self.assertEqual(options["versions"], list(SUPPORTED_TRINO_VERSIONS))
        self.assertEqual(options["default"], TRINO_VERSION)

    def test_trino_version_discovery_merges_caches_and_falls_back(self):
        from trinohub.aws_checks import SUPPORTED_TRINO_VERSIONS

        calls = []

        def fake_fetch():
            calls.append(1)
            return ["501", "500"]

        self.app._trino_version_fetcher = fake_fetch
        self.app._trino_versions_cache = None
        options = self.app.trino_version_options()
        # Discovered versions merge ahead of the static list; newest is default.
        self.assertEqual(options["versions"][:2], ["501", "500"])
        self.assertEqual(options["default"], "501")
        for version in SUPPORTED_TRINO_VERSIONS:
            self.assertIn(version, options["versions"])
        # Second call is served from cache.
        self.app.trino_version_options()
        self.assertEqual(len(calls), 1)

        # A failing fetcher falls back to the static list.
        def broken_fetch():
            raise OSError("network down")

        self.app._trino_version_fetcher = broken_fetch
        self.app._trino_versions_cache = None
        fallback = self.app.trino_version_options()
        self.assertEqual(fallback["versions"], list(SUPPORTED_TRINO_VERSIONS))

    def test_create_cluster_accepts_discovered_trino_version(self):
        admin, _ = self._admin_and_cluster()
        self.app._trino_version_fetcher = lambda: ["501"]
        self.app._trino_versions_cache = None
        result = self.app.create_cluster(
            {"name": "bleeding-edge", "instance_type": "r7i.2xlarge", "trino_version": "501"},
            admin,
        )
        self.assertEqual(result["cluster"]["trino_version"], "501")

    def test_fetch_published_trino_versions_parses_floors_and_caps(self):
        from trinohub import aws_checks
        from trinohub.aws_checks import (
            MAX_OFFERED_TRINO_VERSIONS,
            MIN_OFFERED_TRINO_VERSION,
            fetch_published_trino_versions,
        )

        releases = [{"tag_name": str(v)} for v in range(400, 493)]  # includes pre-floor releases
        releases.append({"tag_name": "493", "prerelease": True})  # skipped
        releases.append({"tag_name": "494-rc1"})  # non-numeric tag skipped
        payload = json.dumps(releases)

        class FakeResponse:
            def read(self):
                return payload.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        with unittest.mock.patch.object(
            aws_checks.urllib.request, "urlopen", return_value=FakeResponse()
        ):
            versions = fetch_published_trino_versions()
        self.assertEqual(len(versions), MAX_OFFERED_TRINO_VERSIONS)
        self.assertEqual(versions[0], "492")
        self.assertTrue(all(int(v) >= MIN_OFFERED_TRINO_VERSION for v in versions))
        # Newest first, strictly descending.
        self.assertEqual(versions, sorted(versions, key=int, reverse=True))

    def test_presets_resolve_to_distinct_instance_sizes(self):
        from trinohub.aws_checks import INSTANCE_MEMORY_GB

        cost = self.app.resolve_instance_type("us-east-2", "Cost")
        balanced = self.app.resolve_instance_type("us-east-2", "Balanced")
        power = self.app.resolve_instance_type("us-east-2", "Power")
        self.assertNotEqual(cost, power)
        self.assertLess(INSTANCE_MEMORY_GB[cost], INSTANCE_MEMORY_GB[balanced])
        self.assertLess(INSTANCE_MEMORY_GB[balanced], INSTANCE_MEMORY_GB[power])

    def test_resolve_instance_type_prefers_first_available_candidate(self):
        # The top preference (m7i.large) is not offered; fall back to the next.
        self.app.aws.available_instance_types = lambda region, types: [t for t in types if t != "m7i.large"]
        self.assertEqual(self.app.resolve_instance_type("us-east-2", "Cost"), "m6i.large")

    def test_resolve_instance_type_rejects_when_none_available(self):
        self.app.aws.available_instance_types = lambda region, types: []
        with self.assertRaises(ApiError) as context:
            self.app.resolve_instance_type("ap-south-2", "Power")
        self.assertEqual(context.exception.status, 400)
        self.assertIn("ap-south-2", context.exception.message)

    def test_resolve_instance_type_tolerates_discovery_error(self):
        def boom(region, types):
            raise RuntimeError("throttled")

        self.app.aws.available_instance_types = boom
        self.assertEqual(self.app.resolve_instance_type("us-east-2", "Cost"), "m7i.large")

    def test_preset_tiers_exposes_resolved_instance_types(self):
        result = self.app.preset_tiers("us-east-2")
        self.assertEqual(result["region"], "us-east-2")
        presets = {tier["preset"]: tier for tier in result["tiers"]}
        self.assertEqual(set(presets), {"Cost", "Balanced", "Power"})
        self.assertLess(presets["Cost"]["memory_gib"], presets["Power"]["memory_gib"])
        for tier in result["tiers"]:
            self.assertTrue(tier["instance_type"])
            self.assertGreater(tier["hourly_usd"], 0)

    def test_preset_tiers_falls_back_when_none_offered(self):
        # A region with no offerings still yields labelled tiers (top candidate)
        # so the Create/Settings UI never shows a blank instance type.
        self.app.aws.available_instance_types = lambda region, types: []
        result = self.app.preset_tiers("ap-south-2")
        presets = {tier["preset"]: tier["instance_type"] for tier in result["tiers"]}
        self.assertEqual(presets["Cost"], "m7i.large")
        self.assertEqual(presets["Power"], "m7i.2xlarge")

    def _setup_admin(self, allowed=("r7i.2xlarge",)):
        self.app.complete_setup(
            {
                "username": "admin",
                "password": "correct-horse-password",
                "allowed_instance_types": list(allowed),
            }
        )
        with self.app.conn() as conn:
            return dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())

    def test_create_cluster_rejects_unavailable_instance_type(self):
        user = self._setup_admin()
        self.app.aws.available_instance_types = lambda region, types: []
        with self.assertRaises(ApiError) as context:
            self.app.create_cluster(
                {
                    "name": "no-capacity",
                    "instance_type": "r7i.2xlarge",
                    "worker_mode": "fixed",
                    "min_workers": 1,
                    "max_workers": 1,
                    "catalogs": ["system"],
                },
                user,
            )
        self.assertEqual(context.exception.status, 400)

    def test_create_cluster_requires_enabled_instance_type(self):
        # No instance types enabled in Settings → cluster creation is blocked.
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.app.conn() as conn:
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        with self.assertRaises(ApiError) as context:
            self.app.create_cluster(
                {"name": "no-types", "instance_type": "r7i.2xlarge", "worker_mode": "fixed", "min_workers": 1, "max_workers": 1, "catalogs": ["system"]},
                user,
            )
        self.assertEqual(context.exception.status, 400)

    def test_create_cluster_rejects_instance_type_outside_allowlist(self):
        user = self._setup_admin(allowed=["r7i.2xlarge"])
        with self.assertRaises(ApiError) as context:
            self.app.create_cluster(
                {"name": "off-list", "instance_type": "r5.xlarge", "worker_mode": "fixed", "min_workers": 1, "max_workers": 1, "catalogs": ["system"]},
                user,
            )
        self.assertEqual(context.exception.status, 400)

    def test_start_cluster_launches_selected_instance(self):
        user = self._setup_admin(allowed=["r7i.4xlarge"])
        cluster = self.app.create_cluster(
            {
                "name": "power-cluster",
                "instance_type": "r7i.4xlarge",
                "worker_mode": "fixed",
                "min_workers": 1,
                "max_workers": 1,
                "catalogs": ["system"],
            },
            user,
        )["cluster"]
        self.app.start_cluster(cluster["id"], {"confirm_billable": True})
        self.assertEqual(self.app.aws.worker_template_calls[-1]["instance_type"], "r7i.4xlarge")

    def test_legacy_preset_cluster_still_launches(self):
        # Clusters created under the old preset model (instance_type blank) keep
        # launching by resolving their preset.
        self._setup_admin()
        with self.app.conn() as conn:
            conn.execute(
                """
                INSERT INTO clusters
                  (name, status, preset, instance_type, region, worker_mode, min_workers, max_workers,
                   auto_suspend_minutes, catalogs_json, owner_user_id, created_at, updated_at)
                VALUES ('legacy', 'Not enabled', 'Power', '', 'us-east-2', 'fixed', 1, 1, NULL, '["system"]', 1, '2020', '2020')
                """
            )
            cluster_id = conn.execute("SELECT id FROM clusters WHERE name = 'legacy'").fetchone()[0]
        self.app.start_cluster(cluster_id, {"confirm_billable": True})
        self.assertEqual(self.app.aws.worker_template_calls[-1]["instance_type"], "m7i.2xlarge")

    def test_setup_persists_allowed_instance_types(self):
        result, _ = self.app.complete_setup(
            {
                "username": "admin",
                "password": "correct-horse-password",
                "allowed_instance_types": ["m6i.2xlarge", "r7i.xlarge"],
            }
        )
        # Stored in canonical (curated) order regardless of input order.
        self.assertEqual(result["setup"]["allowed_instance_types"], ["r7i.xlarge", "m6i.2xlarge"])

    def test_setup_rejects_unknown_allowed_instance_type(self):
        with self.assertRaises(ApiError) as context:
            self.app.complete_setup(
                {
                    "username": "admin",
                    "password": "correct-horse-password",
                    "allowed_instance_types": ["not-a-real-type"],
                }
            )
        self.assertEqual(context.exception.status, 400)

    def test_instance_type_options_lists_curated_types_with_flags(self):
        self._setup_admin(allowed=["r7i.2xlarge"])
        result = self.app.instance_type_options()
        types = result["instance_types"]
        # The curated list is memory-optimized R-family, a couple of M types,
        # NVMe instance-store types for accelerated clusters, and a small
        # t3.large for testing.
        from trinohub.server import POPULAR_TRINO_INSTANCE_TYPES

        self.assertEqual(len(types), len(POPULAR_TRINO_INSTANCE_TYPES))
        self.assertIn("t3.large", [option["instance_type"] for option in types])
        self.assertIn("i4i.2xlarge", [option["instance_type"] for option in types])
        self.assertEqual(result["allowed_instance_types"], ["r7i.2xlarge"])
        first = types[0]
        self.assertIn("instance_type", first)
        self.assertGreater(first["vcpu"], 0)
        self.assertGreater(first["memory_gib"], 0)
        self.assertTrue(all(option["available"] for option in types))  # FakeAws offers all
        allowed_flags = {opt["instance_type"]: opt["allowed"] for opt in types}
        self.assertTrue(allowed_flags["r7i.2xlarge"])
        self.assertFalse(allowed_flags["r5.xlarge"])

    def test_instance_type_options_marks_unavailable_in_region(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        self.app.aws.available_instance_types = lambda region, types: []
        result = self.app.instance_type_options("ap-south-2")
        self.assertTrue(all(not option["available"] for option in result["instance_types"]))

    def test_set_allowed_instance_types_persists_and_orders(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        result = self.app.set_allowed_instance_types({"instance_types": ["r5.2xlarge", "r7i.xlarge"]})
        self.assertEqual(result["setup"]["allowed_instance_types"], ["r7i.xlarge", "r5.2xlarge"])
        self.assertEqual(self.app.allowed_instance_types(), ["r7i.xlarge", "r5.2xlarge"])

    def test_set_allowed_instance_types_rejects_unknown(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.assertRaises(ApiError) as context:
            self.app.set_allowed_instance_types({"instance_types": ["c5.42xlarge"]})
        self.assertEqual(context.exception.status, 400)

    def test_set_allowed_instance_types_rejects_unavailable_in_region(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        self.app.aws.available_instance_types = lambda region, types: []
        with self.assertRaises(ApiError) as context:
            self.app.set_allowed_instance_types({"instance_types": ["r7i.2xlarge"]})
        self.assertEqual(context.exception.status, 400)

    def test_set_allowed_instance_types_requires_setup(self):
        with self.assertRaises(ApiError) as context:
            self.app.set_allowed_instance_types({"instance_types": ["r7i.2xlarge"]})
        self.assertEqual(context.exception.status, 409)

    def test_set_allowed_instance_types_can_clear(self):
        self.app.complete_setup(
            {"username": "admin", "password": "correct-horse-password", "allowed_instance_types": ["r7i.2xlarge"]}
        )
        self.app.set_allowed_instance_types({"instance_types": []})
        self.assertEqual(self.app.allowed_instance_types(), [])

    def test_update_cluster_persists_worker_range_when_not_running(self):
        cluster = self.create_test_cluster()
        result = self.app.update_cluster(cluster["id"], {"max_workers": 5})
        self.assertEqual(result["cluster"]["max_workers"], 5)
        self.assertEqual(result["changes"], ["max_workers"])
        self.assertEqual(result["applied_live"], [])
        self.assertFalse(result["restart_required"])
        # No AWS sizing call because the cluster has no live ASG.
        self.assertEqual(self.app.aws.scaling_calls, [])

    def test_update_cluster_applies_worker_max_live_on_running_autoscale(self):
        cluster = self.create_running_autoscale_cluster()
        result = self.app.update_cluster(cluster["id"], {"max_workers": 7})
        self.assertIn("max_workers", result["applied_live"])
        self.assertEqual(result["cluster"]["status"], "Running")
        self.assertEqual(result["cluster"]["max_workers"], 7)
        last_call = self.app.aws.scaling_calls[-1]
        self.assertEqual(last_call["max_size"], 7)
        self.assertEqual(last_call["min_size"], 1)
        # Desired is clamped into the new range (FakeAws reports desired 1).
        self.assertEqual(last_call["desired_capacity"], 1)

    def test_update_cluster_lowering_max_scales_in_running_cluster(self):
        cluster = self.create_running_autoscale_cluster()
        # FakeAws reports a running desired capacity of 1; raise it, then cap it.
        self.app.aws.worker_asg["desired_capacity"] = 3
        result = self.app.update_cluster(cluster["id"], {"max_workers": 2})
        self.assertEqual(self.app.aws.scaling_calls[-1]["desired_capacity"], 2)
        self.assertTrue(result["cluster"]["max_workers"] == 2)

    def test_update_cluster_catalogs_require_restart_when_running(self):
        cluster = self.create_running_autoscale_cluster()
        result = self.app.update_cluster(cluster["id"], {"catalogs": ["system", "tpcds"]})
        self.assertEqual(result["cluster"]["catalogs"], ["system", "tpcds"])
        self.assertTrue(result["restart_required"])
        self.assertEqual(result["restart_required_fields"], ["catalogs"])
        self.assertEqual(result["applied_live"], [])
        self.assertEqual(self.app.aws.scaling_calls, [])

    def test_update_cluster_auto_suspend_applies_live(self):
        cluster = self.create_running_autoscale_cluster()
        result = self.app.update_cluster(cluster["id"], {"auto_suspend_minutes": 30})
        self.assertEqual(result["cluster"]["auto_suspend_minutes"], 30)
        self.assertIn("auto_suspend_minutes", result["applied_live"])
        self.assertFalse(result["restart_required"])

    def test_update_cluster_rejects_invalid_worker_range(self):
        cluster = self.create_test_cluster()
        with self.assertRaises(ApiError) as context:
            self.app.update_cluster(cluster["id"], {"min_workers": 5, "max_workers": 2})
        self.assertEqual(context.exception.status, 400)

    def test_update_cluster_rejects_unknown_catalog_without_persisting(self):
        cluster = self.create_test_cluster()
        with self.assertRaises(ApiError) as context:
            self.app.update_cluster(cluster["id"], {"catalogs": ["system", "ghost"]})
        self.assertEqual(context.exception.status, 400)
        with self.app.conn() as conn:
            row = conn.execute("SELECT catalogs_json FROM clusters WHERE id = ?", (cluster["id"],)).fetchone()
        self.assertNotIn("ghost", row["catalogs_json"])

    def test_update_cluster_rejected_during_transitional_state(self):
        cluster = self.create_test_cluster()
        with self.app.conn() as conn:
            conn.execute("UPDATE clusters SET status = 'Creating' WHERE id = ?", (cluster["id"],))
        with self.assertRaises(ApiError) as context:
            self.app.update_cluster(cluster["id"], {"max_workers": 4})
        self.assertEqual(context.exception.status, 409)

    def test_update_cluster_no_changes_is_noop(self):
        cluster = self.create_test_cluster()
        result = self.app.update_cluster(
            cluster["id"], {"max_workers": cluster["max_workers"], "min_workers": cluster["min_workers"]}
        )
        self.assertEqual(result["changes"], [])
        self.assertFalse(result["restart_required"])

    def _admin_and_user(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        member = self.app.create_user({"username": "member", "password": "member-password-123", "role": "user"})["user"]
        return member

    def test_update_user_deactivate_blocks_login(self):
        member = self._admin_and_user()
        self.app.login({"username": "member", "password": "member-password-123"})
        result = self.app.update_user(member["id"], {"is_active": False})
        self.assertFalse(result["user"]["is_active"])
        with self.assertRaises(ApiError) as context:
            self.app.login({"username": "member", "password": "member-password-123"})
        self.assertEqual(context.exception.status, 401)

    def test_update_user_deactivate_revokes_sessions(self):
        member = self._admin_and_user()
        self.app.login({"username": "member", "password": "member-password-123"})
        with self.app.conn() as conn:
            before = conn.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (member["id"],)).fetchone()[0]
        self.assertEqual(before, 1)
        self.app.update_user(member["id"], {"is_active": False})
        with self.app.conn() as conn:
            after = conn.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (member["id"],)).fetchone()[0]
        self.assertEqual(after, 0)

    def test_update_user_password_reset_revokes_sessions_and_changes_login(self):
        member = self._admin_and_user()
        self.app.login({"username": "member", "password": "member-password-123"})
        self.app.update_user(member["id"], {"password": "brand-new-password-9"})
        with self.app.conn() as conn:
            sessions = conn.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (member["id"],)).fetchone()[0]
        self.assertEqual(sessions, 0)
        with self.assertRaises(ApiError):
            self.app.login({"username": "member", "password": "member-password-123"})
        _, token = self.app.login({"username": "member", "password": "brand-new-password-9"})
        self.assertTrue(token)

    def test_update_user_promote_to_admin(self):
        member = self._admin_and_user()
        result = self.app.update_user(member["id"], {"role": "admin"})
        self.assertEqual(result["user"]["role"], "admin")

    def test_update_user_cannot_deactivate_last_admin(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.app.conn() as conn:
            admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()[0]
        with self.assertRaises(ApiError) as context:
            self.app.update_user(admin_id, {"is_active": False})
        self.assertEqual(context.exception.status, 409)

    def test_update_user_cannot_demote_last_admin(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.app.conn() as conn:
            admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()[0]
        with self.assertRaises(ApiError) as context:
            self.app.update_user(admin_id, {"role": "user"})
        self.assertEqual(context.exception.status, 409)

    def test_update_user_can_demote_admin_when_another_exists(self):
        member = self._admin_and_user()
        self.app.update_user(member["id"], {"role": "admin"})
        with self.app.conn() as conn:
            admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()[0]
        # A second active admin now exists, so demoting the original is allowed.
        result = self.app.update_user(admin_id, {"role": "user"})
        self.assertEqual(result["user"]["role"], "user")

    def test_update_user_rejects_invalid_role(self):
        member = self._admin_and_user()
        with self.assertRaises(ApiError) as context:
            self.app.update_user(member["id"], {"role": "superuser"})
        self.assertEqual(context.exception.status, 400)

    def test_update_user_not_found(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.assertRaises(ApiError) as context:
            self.app.update_user(99999, {"role": "user"})
        self.assertEqual(context.exception.status, 404)

    def test_cluster_catalogs_are_normalized(self):
        user = self._setup_admin()

        result = self.app.create_cluster(
            {
                "name": "catalog-test",
                "instance_type": "r7i.2xlarge",
                "worker_mode": "fixed",
                "min_workers": 1,
                "max_workers": 1,
                "catalogs": ["tpch", "tpch", "tpcds"],
            },
            user,
        )

        self.assertEqual(result["cluster"]["catalogs"], ["system", "tpch", "tpcds"])

    def test_cluster_rejects_invalid_catalog_names(self):
        user = self._setup_admin()

        with self.assertRaises(ApiError) as context:
            self.app.create_cluster(
                {
                    "name": "catalog-test",
                    "instance_type": "r7i.2xlarge",
                    "worker_mode": "fixed",
                    "min_workers": 1,
                    "max_workers": 1,
                    "catalogs": ["System"],
                },
                user,
            )

        self.assertEqual(context.exception.status, 400)

    def test_create_s3_glue_catalog_normalizes_config(self):
        result = self.app.create_catalog(
            {
                "name": "analytics_s3",
                "type": "s3_glue",
                "config": {
                    "glue_region": "us-east-2",
                    "warehouse": "s3://company-lakehouse/warehouse",
                    "default_schema": "analytics",
                    "access_mode": "read_only",
                },
            }
        )

        self.assertEqual(result["catalog"]["type"], "s3_glue")
        self.assertEqual(result["catalog"]["config"]["warehouse"], "s3://company-lakehouse/warehouse/")
        self.assertEqual(result["catalog"]["config"]["s3_region"], "us-east-2")
        self.assertEqual(result["catalog"]["config"]["file_format"], "PARQUET")
        self.assertEqual(result["catalog"]["config"]["table_format"], "ICEBERG")

    def test_create_delta_and_hive_glue_catalogs_derive_table_format(self):
        # Delta Lake, Hive, and Hudi reuse the S3/Glue form and IAM auth (no secret);
        # the table format is fixed by the catalog type, not accepted from the client.
        for catalog_type, expected_format in (("delta_glue", "DELTA"), ("hive_glue", "HIVE"), ("hudi_glue", "HUDI")):
            with self.subTest(catalog_type=catalog_type):
                result = self.app.create_catalog(
                    {
                        "name": f"lake_{catalog_type}",
                        "type": catalog_type,
                        "config": {
                            "glue_region": "us-east-2",
                            "warehouse": "s3://company-lakehouse/warehouse",
                            # A stray client-supplied table_format must not override the type.
                            "table_format": "ICEBERG",
                            "access_mode": "read_write",
                        },
                    }
                )
                self.assertEqual(result["catalog"]["type"], catalog_type)
                self.assertEqual(result["catalog"]["config"]["table_format"], expected_format)
                self.assertEqual(result["catalog"]["config"]["warehouse"], "s3://company-lakehouse/warehouse/")
                # No credential path: nothing is stored in Secrets Manager.
                self.assertNotIn("password_secret_ref", result["catalog"]["config"])

    def test_create_catalog_rejects_static_credentials(self):
        with self.assertRaises(ApiError) as context:
            self.app.create_catalog(
                {
                    "name": "analytics_s3",
                    "type": "s3_glue",
                    "config": {
                        "glue_region": "us-east-2",
                        "warehouse": "s3://company-lakehouse/warehouse/",
                        "aws_access_key": "AKIA...",
                    },
                }
            )

        self.assertEqual(context.exception.status, 400)
        self.assertIn("Do not store AWS access keys", context.exception.message)

    def test_create_postgresql_catalog_stores_only_secret_ref(self):
        self.app.secret_store = FakeSecretStore()
        result = self.app.create_catalog(
            {
                "name": "warehouse_pg",
                "type": "postgresql",
                "config": {
                    "connection_url": "jdbc:postgresql://db.internal.example.com:5432/warehouse",
                    "connection_user": "analyst",
                },
                "password": "s3cr3t-pw",
            }
        )

        config = result["catalog"]["config"]
        # Only the ARN reference is persisted; the plaintext lives in the secret store.
        self.assertTrue(config["password_secret_ref"].startswith("arn:aws:secretsmanager:"))
        self.assertNotIn("password", config)
        self.assertEqual(self.app.secret_store.secrets[config["password_secret_ref"]], "s3cr3t-pw")

        # The plaintext password must not appear anywhere in the stored row.
        with self.app.conn() as conn:
            row = conn.execute("SELECT config_json FROM catalogs WHERE name = 'warehouse_pg'").fetchone()
        self.assertNotIn("s3cr3t-pw", row["config_json"])

        # GET /api/catalogs must never echo the password either.
        listed = json.dumps(self.app.list_catalogs())
        self.assertNotIn("s3cr3t-pw", listed)

    def test_create_postgresql_catalog_requires_password(self):
        self.app.secret_store = FakeSecretStore()
        with self.assertRaises(ApiError) as context:
            self.app.create_catalog(
                {
                    "name": "warehouse_pg",
                    "type": "postgresql",
                    "config": {
                        "connection_url": "jdbc:postgresql://db.internal.example.com:5432/warehouse",
                        "connection_user": "analyst",
                    },
                }
            )
        self.assertEqual(context.exception.status, 400)
        self.assertIn("require a non-empty password", context.exception.message)

    def test_create_postgresql_catalog_fails_without_secret_backend(self):
        from trinohub.secrets_store import NullSecretStore

        self.app.secret_store = NullSecretStore()
        with self.assertRaises(ApiError) as context:
            self.app.create_catalog(
                {
                    "name": "warehouse_pg",
                    "type": "postgresql",
                    "config": {
                        "connection_url": "jdbc:postgresql://db.internal.example.com:5432/warehouse",
                        "connection_user": "analyst",
                    },
                    "password": "s3cr3t-pw",
                }
            )
        self.assertEqual(context.exception.status, 400)
        self.assertIn("No secret backend", context.exception.message)
        # Nothing should have been persisted when the secret could not be stored.
        with self.app.conn() as conn:
            self.assertIsNone(conn.execute("SELECT 1 FROM catalogs WHERE name = 'warehouse_pg'").fetchone())

    def test_postgresql_catalog_rejects_secrets_in_config(self):
        self.app.secret_store = FakeSecretStore()
        with self.assertRaises(ApiError) as context:
            self.app.create_catalog(
                {
                    "name": "warehouse_pg",
                    "type": "postgresql",
                    "config": {
                        "connection_url": "jdbc:postgresql://db.internal.example.com:5432/warehouse",
                        "connection_user": "analyst",
                        "connection_password": "leaked",
                    },
                    "password": "s3cr3t-pw",
                }
            )
        self.assertEqual(context.exception.status, 400)
        self.assertIn("Do not store passwords", context.exception.message)

    def test_postgresql_catalog_rejects_ssrf_metadata_host(self):
        self.app.secret_store = FakeSecretStore()
        with self.assertRaises(ApiError) as context:
            self.app.create_catalog(
                {
                    "name": "warehouse_pg",
                    "type": "postgresql",
                    "config": {
                        "connection_url": "jdbc:postgresql://169.254.169.254:5432/warehouse",
                        "connection_user": "analyst",
                    },
                    "password": "s3cr3t-pw",
                }
            )
        self.assertEqual(context.exception.status, 400)
        self.assertIn("not allowed", context.exception.message)

    def test_delete_postgresql_catalog_removes_secret(self):
        self.app.secret_store = FakeSecretStore()
        created = self.app.create_catalog(
            {
                "name": "warehouse_pg",
                "type": "postgresql",
                "config": {
                    "connection_url": "jdbc:postgresql://db.internal.example.com:5432/warehouse",
                    "connection_user": "analyst",
                },
                "password": "s3cr3t-pw",
            }
        )["catalog"]
        ref = created["config"]["password_secret_ref"]

        self.app.delete_catalog(created["id"])

        self.assertIn(ref, self.app.secret_store.deleted)

    def test_postgresql_catalog_password_rendered_only_in_signed_node_config(self):
        self.app.secret_store = FakeSecretStore()
        self.app.complete_setup(
            {"username": "admin", "password": "correct-horse-password", "allowed_instance_types": ["r7i.2xlarge"]}
        )
        self.app.create_catalog(
            {
                "name": "warehouse_pg",
                "type": "postgresql",
                "config": {
                    "connection_url": "jdbc:postgresql://db.internal.example.com:5432/warehouse",
                    "connection_user": "analyst",
                },
                "password": "s3cr3t-pw",
            }
        )
        with self.app.conn() as conn:
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        cluster = self.app.create_cluster(
            {
                "name": "pg-cluster",
                "instance_type": "r7i.2xlarge",
                "worker_mode": "fixed",
                "min_workers": 1,
                "max_workers": 1,
                "catalogs": ["system", "warehouse_pg"],
            },
            user,
        )["cluster"]
        self.app.start_cluster(cluster["id"], {"confirm_billable": True})
        token = self.app.aws.worker_template_calls[-1]["bootstrap_token"]

        script = self.app.node_config_script(
            cluster_id=cluster["id"], role="worker", token=token, instance_type="m7i.large"
        )
        self.assertIn("cat >/etc/trino/catalog/warehouse_pg.properties", script)
        self.assertIn("connector.name=postgresql", script)
        self.assertIn("connection-url=jdbc:postgresql://db.internal.example.com:5432/warehouse", script)
        self.assertIn("connection-user=analyst", script)
        self.assertIn("connection-password=s3cr3t-pw", script)

    def test_jdbc_batch_catalogs_render_their_connector_name(self):
        # MySQL / Redshift / SQL Server are registry variants of the PostgreSQL
        # reference connector: each must validate its own URL shape, store only a
        # secret reference, and render the right connector.name + credential into
        # the signed node-config (and never into plain user-data).
        cases = [
            ("mysql", "jdbc:mysql://db.internal.example.com:3306"),
            ("redshift", "jdbc:redshift://rs.internal.example.com:5439/warehouse"),
            ("sqlserver", "jdbc:sqlserver://db.internal.example.com:1433;databaseName=warehouse"),
            ("mariadb", "jdbc:mariadb://db.internal.example.com:3306/warehouse"),
            ("singlestore", "jdbc:singlestore://db.internal.example.com:3306"),
            ("clickhouse", "jdbc:clickhouse://db.internal.example.com:8123/warehouse"),
            ("snowflake", "jdbc:snowflake://acme.snowflakecomputing.com"),
            ("druid", "jdbc:avatica:remote:url=http://broker.internal.example.com:8082/druid/v2/sql/avatica/"),
            # Oracle is covered separately — it requires an uploaded driver first.
        ]
        for catalog_type, connection_url in cases:
            with self.subTest(catalog_type=catalog_type), tempfile.TemporaryDirectory() as tmp:
                app = TrinoHubApp(
                    db_path=Path(tmp) / "test.sqlite3", aws=FakeAws(), require_setup_token=False
                )
                app.secret_store = FakeSecretStore()
                app.complete_setup(
                    {"username": "admin", "password": "correct-horse-password", "allowed_instance_types": ["r7i.2xlarge"]}
                )
                name = f"warehouse_{catalog_type}"
                created = app.create_catalog(
                    {
                        "name": name,
                        "type": catalog_type,
                        "config": {"connection_url": connection_url, "connection_user": "analyst"},
                        "password": "s3cr3t-pw",
                    }
                )["catalog"]
                config = created["config"]
                self.assertEqual(config["connector_name"], catalog_type)
                self.assertTrue(config["password_secret_ref"].startswith("arn:aws:secretsmanager:"))
                self.assertNotIn("password", config)

                with app.conn() as conn:
                    user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
                cluster = app.create_cluster(
                    {
                        "name": f"{catalog_type}-cluster",
                        "instance_type": "r7i.2xlarge",
                        "worker_mode": "fixed",
                        "min_workers": 1,
                        "max_workers": 1,
                        "catalogs": ["system", name],
                    },
                    user,
                )["cluster"]
                app.start_cluster(cluster["id"], {"confirm_billable": True})
                token = app.aws.worker_template_calls[-1]["bootstrap_token"]
                script = app.node_config_script(
                    cluster_id=cluster["id"], role="worker", token=token, instance_type="m7i.large"
                )
                self.assertIn(f"cat >/etc/trino/catalog/{name}.properties", script)
                self.assertIn(f"connector.name={catalog_type}", script)
                self.assertIn(f"connection-url={connection_url}", script)
                self.assertIn("connection-password=s3cr3t-pw", script)

    def test_jdbc_catalog_rejects_wrong_url_scheme(self):
        # A redshift catalog must reject a postgres-shaped URL — each type only
        # accepts its own JDBC scheme.
        self.app.secret_store = FakeSecretStore()
        with self.assertRaises(ApiError) as context:
            self.app.create_catalog(
                {
                    "name": "warehouse_rs",
                    "type": "redshift",
                    "config": {
                        "connection_url": "jdbc:postgresql://db.internal.example.com:5432/warehouse",
                        "connection_user": "analyst",
                    },
                    "password": "s3cr3t-pw",
                }
            )
        self.assertEqual(context.exception.status, 400)
        self.assertIn("jdbc:redshift://", context.exception.message)

    def test_jdbc_catalog_rejects_ssrf_metadata_host(self):
        # The SSRF guard applies to every JDBC type, not just postgres.
        self.app.secret_store = FakeSecretStore()
        with self.assertRaises(ApiError) as context:
            self.app.create_catalog(
                {
                    "name": "warehouse_my",
                    "type": "mysql",
                    "config": {
                        "connection_url": "jdbc:mysql://169.254.169.254:3306/warehouse",
                        "connection_user": "analyst",
                    },
                    "password": "s3cr3t-pw",
                }
            )
        self.assertEqual(context.exception.status, 400)
        self.assertIn("not allowed", context.exception.message)

    def test_druid_catalog_ssrf_guard_reads_nested_broker_host(self):
        # Druid's broker host is nested inside the Avatica url= parameter, so the
        # SSRF guard only protects it if the URL regex captures that host. Point it
        # at the metadata IP and confirm it's still rejected.
        self.app.secret_store = FakeSecretStore()
        with self.assertRaises(ApiError) as context:
            self.app.create_catalog(
                {
                    "name": "warehouse_druid",
                    "type": "druid",
                    "config": {
                        "connection_url": "jdbc:avatica:remote:url=http://169.254.169.254:8082/druid/v2/sql/avatica/",
                        "connection_user": "analyst",
                    },
                    "password": "s3cr3t-pw",
                }
            )
        self.assertEqual(context.exception.status, 400)
        self.assertIn("not allowed", context.exception.message)

    def _node_config_with_catalog(self, app, name, payload_type, config, password):
        app.secret_store = FakeSecretStore()
        app.complete_setup(
            {"username": "admin", "password": "correct-horse-password", "allowed_instance_types": ["r7i.2xlarge"]}
        )
        app.create_catalog({"name": name, "type": payload_type, "config": config, "password": password})
        with app.conn() as conn:
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        cluster = app.create_cluster(
            {
                "name": f"{payload_type}-cluster",
                "instance_type": "r7i.2xlarge",
                "worker_mode": "fixed",
                "min_workers": 1,
                "max_workers": 1,
                "catalogs": ["system", name],
            },
            user,
        )["cluster"]
        app.start_cluster(cluster["id"], {"confirm_billable": True})
        token = app.aws.worker_template_calls[-1]["bootstrap_token"]
        return app.node_config_script(cluster_id=cluster["id"], role="worker", token=token, instance_type="m7i.large")

    def test_mongodb_catalog_injects_credentials_only_in_signed_node_config(self):
        self.app.secret_store = FakeSecretStore()
        created = self.app.create_catalog(
            {
                "name": "docs_mongo",
                "type": "mongodb",
                "config": {
                    "connection_url": "mongodb://mongo.internal.example.com:27017/app",
                    "connection_user": "reader",
                },
                "password": "s3cr3t-pw",
            }
        )["catalog"]
        # Stored config holds no password and no embedded creds in the URL.
        self.assertNotIn("password", created["config"])
        self.assertNotIn("@", created["config"]["connection_url"])
        self.assertTrue(created["config"]["password_secret_ref"].startswith("arn:aws:secretsmanager:"))

        script = self._node_config_with_catalog(
            TrinoHubApp(db_path=Path(tempfile.mkdtemp()) / "t.sqlite3", aws=FakeAws(), require_setup_token=False),
            "docs_mongo",
            "mongodb",
            {"connection_url": "mongodb://mongo.internal.example.com:27017/app", "connection_user": "reader"},
            "s3cr3t-pw",
        )
        # Credentials are injected into mongodb.connection-url at render time.
        self.assertIn("connector.name=mongodb", script)
        self.assertIn("mongodb.connection-url=mongodb://reader:s3cr3t-pw@mongo.internal.example.com:27017/app", script)

    def test_mongodb_catalog_rejects_url_with_embedded_credentials(self):
        self.app.secret_store = FakeSecretStore()
        with self.assertRaises(ApiError) as context:
            self.app.create_catalog(
                {
                    "name": "docs_mongo",
                    "type": "mongodb",
                    "config": {
                        "connection_url": "mongodb://reader:leak@mongo.internal.example.com:27017/app",
                        "connection_user": "reader",
                    },
                    "password": "s3cr3t-pw",
                }
            )
        self.assertEqual(context.exception.status, 400)

    def test_elasticsearch_catalog_renders_password_auth_in_signed_node_config(self):
        self.app.secret_store = FakeSecretStore()
        created = self.app.create_catalog(
            {
                "name": "logs_es",
                "type": "elasticsearch",
                "config": {
                    "host": "es.internal.example.com",
                    "port": 9200,
                    "connection_user": "reader",
                    "default_schema": "default",
                },
                "password": "s3cr3t-pw",
            }
        )["catalog"]
        self.assertEqual(created["config"]["connector_name"], "elasticsearch")
        self.assertNotIn("password", created["config"])

        script = self._node_config_with_catalog(
            TrinoHubApp(db_path=Path(tempfile.mkdtemp()) / "t.sqlite3", aws=FakeAws(), require_setup_token=False),
            "logs_es",
            "elasticsearch",
            {"host": "es.internal.example.com", "port": 9200, "connection_user": "reader", "default_schema": "default"},
            "s3cr3t-pw",
        )
        self.assertIn("connector.name=elasticsearch", script)
        self.assertIn("elasticsearch.host=es.internal.example.com", script)
        self.assertIn("elasticsearch.port=9200", script)
        self.assertIn("elasticsearch.security=PASSWORD", script)
        self.assertIn("elasticsearch.auth.user=reader", script)
        self.assertIn("elasticsearch.auth.password=s3cr3t-pw", script)

    def test_elasticsearch_catalog_rejects_ssrf_host(self):
        self.app.secret_store = FakeSecretStore()
        with self.assertRaises(ApiError) as context:
            self.app.create_catalog(
                {
                    "name": "logs_es",
                    "type": "elasticsearch",
                    "config": {"host": "169.254.169.254", "port": 9200, "connection_user": "reader"},
                    "password": "s3cr3t-pw",
                }
            )
        self.assertEqual(context.exception.status, 400)
        self.assertIn("not allowed", context.exception.message)

    def test_create_bigquery_catalog_stores_only_credential_ref(self):
        self.app.secret_store = FakeSecretStore()
        key = json.dumps(
            {
                "type": "service_account",
                "project_id": "my-analytics-project",
                "private_key": "-----BEGIN PRIVATE KEY-----\nMIIsecret\n-----END PRIVATE KEY-----\n",
                "client_email": "trino@my-analytics-project.iam.gserviceaccount.com",
            }
        )
        result = self.app.create_catalog(
            {
                "name": "warehouse_bigquery",
                "type": "bigquery",
                "config": {"project_id": "my-analytics-project", "parent_project_id": "data-owner-project"},
                "password": key,
            }
        )
        config = result["catalog"]["config"]
        self.assertEqual(config["connector_name"], "bigquery")
        self.assertEqual(config["project_id"], "my-analytics-project")
        self.assertEqual(config["parent_project_id"], "data-owner-project")
        self.assertTrue(config["password_secret_ref"].startswith("arn:aws:secretsmanager:"))
        # The plaintext key never touches the metadata row or the API response.
        with self.app.conn() as conn:
            row = conn.execute("SELECT config_json FROM catalogs WHERE name = 'warehouse_bigquery'").fetchone()
        self.assertNotIn("PRIVATE KEY", row["config_json"])
        self.assertNotIn("MIIsecret", json.dumps(self.app.list_catalogs()))
        self.assertEqual(self.app.secret_store.secrets[config["password_secret_ref"]], key)

    def test_bigquery_catalog_rejects_invalid_service_account_key(self):
        self.app.secret_store = FakeSecretStore()
        for bad_key in ("not json at all", json.dumps({"type": "authorized_user"})):
            with self.subTest(bad_key=bad_key):
                with self.assertRaises(ApiError) as context:
                    self.app.create_catalog(
                        {
                            "name": "warehouse_bigquery",
                            "type": "bigquery",
                            "config": {"project_id": "my-analytics-project"},
                            "password": bad_key,
                        }
                    )
                self.assertEqual(context.exception.status, 400)
        # A rejected key must not leave a catalog or a secret behind.
        with self.app.conn() as conn:
            self.assertIsNone(conn.execute("SELECT 1 FROM catalogs WHERE name = 'warehouse_bigquery'").fetchone())
        self.assertEqual(self.app.secret_store.secrets, {})

    def test_bigquery_catalog_rejects_bad_project_id(self):
        self.app.secret_store = FakeSecretStore()
        with self.assertRaises(ApiError) as context:
            self.app.create_catalog(
                {
                    "name": "warehouse_bigquery",
                    "type": "bigquery",
                    "config": {"project_id": "Bad_Project_ID"},
                    "password": json.dumps(
                        {"type": "service_account", "project_id": "x", "private_key": "k", "client_email": "e"}
                    ),
                }
            )
        self.assertEqual(context.exception.status, 400)
        self.assertIn("project_id", context.exception.message)

    def test_bigquery_catalog_renders_credentials_key_only_in_signed_node_config(self):
        key = json.dumps(
            {
                "type": "service_account",
                "project_id": "my-analytics-project",
                "private_key": "-----BEGIN PRIVATE KEY-----\nMIIsecret\n-----END PRIVATE KEY-----\n",
                "client_email": "trino@my-analytics-project.iam.gserviceaccount.com",
            }
        )
        script = self._node_config_with_catalog(
            TrinoHubApp(db_path=Path(tempfile.mkdtemp()) / "t.sqlite3", aws=FakeAws(), require_setup_token=False),
            "warehouse_bigquery",
            "bigquery",
            {"project_id": "my-analytics-project"},
            key,
        )
        self.assertIn("connector.name=bigquery", script)
        self.assertIn("bigquery.project-id=my-analytics-project", script)
        expected_b64 = base64.b64encode(key.encode("utf-8")).decode("ascii")
        self.assertIn(f"bigquery.credentials-key={expected_b64}", script)
        # The raw key only appears base64-encoded; its plaintext must not leak.
        self.assertNotIn("BEGIN PRIVATE KEY", script)
        self.assertNotIn("MIIsecret", script)

    def test_opensearch_catalog_renders_opensearch_prefix_in_signed_node_config(self):
        # OpenSearch reuses the Elasticsearch machinery, parameterized by
        # connector_name: same fields, opensearch.* property prefix.
        self.app.secret_store = FakeSecretStore()
        created = self.app.create_catalog(
            {
                "name": "logs_os",
                "type": "opensearch",
                "config": {
                    "host": "os.internal.example.com",
                    "port": 9200,
                    "connection_user": "reader",
                    "default_schema": "default",
                },
                "password": "s3cr3t-pw",
            }
        )["catalog"]
        self.assertEqual(created["config"]["connector_name"], "opensearch")
        self.assertNotIn("password", created["config"])

        script = self._node_config_with_catalog(
            TrinoHubApp(db_path=Path(tempfile.mkdtemp()) / "t.sqlite3", aws=FakeAws(), require_setup_token=False),
            "logs_os",
            "opensearch",
            {"host": "os.internal.example.com", "port": 9200, "connection_user": "reader", "default_schema": "default"},
            "s3cr3t-pw",
        )
        self.assertIn("connector.name=opensearch", script)
        self.assertIn("opensearch.host=os.internal.example.com", script)
        self.assertIn("opensearch.security=PASSWORD", script)
        self.assertIn("opensearch.auth.user=reader", script)
        self.assertIn("opensearch.auth.password=s3cr3t-pw", script)
        # The elasticsearch prefix must not leak into an opensearch catalog.
        self.assertNotIn("elasticsearch.host", script)

    def test_generator_catalogs_render_connector_name_only(self):
        # memory / blackhole / faker are zero-config, no-secret built-in generators.
        for catalog_type in ("memory", "blackhole", "faker"):
            with self.subTest(catalog_type=catalog_type):
                created = self.app.create_catalog(
                    {"name": f"gen_{catalog_type}", "type": catalog_type, "config": {}}
                )["catalog"]
                self.assertEqual(created["config"], {"connector_name": catalog_type})
                self.assertNotIn("password_secret_ref", created["config"])
                aws = AwsInspector(region="us-east-2")
                script = aws.trino_user_data(
                    cluster={
                        "name": "c",
                        "catalogs": ["system", f"gen_{catalog_type}"],
                        "catalog_configs": [
                            {"name": f"gen_{catalog_type}", "type": catalog_type, "enabled": True,
                             "config": {"connector_name": catalog_type}}
                        ],
                    },
                    node_role="worker",
                    region="us-east-2",
                    coordinator_uri="http://10.0.1.10:8080",
                )
                self.assertIn(f"cat >/etc/trino/catalog/gen_{catalog_type}.properties", script)
                self.assertIn(f"connector.name={catalog_type}", script)

    def test_generator_catalog_rejects_configuration(self):
        with self.assertRaises(ApiError) as context:
            self.app.create_catalog({"name": "gen_memory", "type": "memory", "config": {"host": "x"}})
        self.assertEqual(context.exception.status, 400)
        self.assertIn("takes no configuration", context.exception.message)

    def test_cassandra_unauthenticated_catalog_stores_no_secret_and_renders_in_user_data(self):
        # An open Cassandra cluster has no credential, so it may render straight into
        # EC2 user-data like the no-secret S3/Glue and generator families.
        created = self.app.create_catalog(
            {
                "name": "nosql_open",
                "type": "cassandra",
                "config": {"contact_points": "10.0.0.1, 10.0.0.2", "port": 9042},
            }
        )["catalog"]
        self.assertEqual(created["config"]["connector_name"], "cassandra")
        self.assertEqual(created["config"]["contact_points"], "10.0.0.1,10.0.0.2")
        self.assertNotIn("connection_user", created["config"])
        self.assertNotIn("password_secret_ref", created["config"])

        aws = AwsInspector(region="us-east-2")
        script = aws.trino_user_data(
            cluster={
                "name": "c",
                "catalogs": ["system", "nosql_open"],
                "catalog_configs": [dict(created, enabled=True)],
            },
            node_role="worker",
            region="us-east-2",
            coordinator_uri="http://10.0.1.10:8080",
        )
        self.assertIn("connector.name=cassandra", script)
        self.assertIn("cassandra.contact-points=10.0.0.1,10.0.0.2", script)
        self.assertIn("cassandra.native-protocol-port=9042", script)
        self.assertNotIn("cassandra.username", script)
        self.assertNotIn("cassandra.password", script)

    def test_cassandra_authenticated_catalog_requires_password(self):
        self.app.secret_store = FakeSecretStore()
        with self.assertRaises(ApiError) as context:
            self.app.create_catalog(
                {
                    "name": "nosql_auth",
                    "type": "cassandra",
                    "config": {"contact_points": "db1.internal.example.com", "connection_user": "cassandra"},
                }
            )
        self.assertEqual(context.exception.status, 400)
        self.assertIn("non-empty password", context.exception.message)

    def test_cassandra_authenticated_password_only_in_signed_node_config(self):
        self.app.secret_store = FakeSecretStore()
        created = self.app.create_catalog(
            {
                "name": "nosql_auth",
                "type": "cassandra",
                "config": {"contact_points": "db1.internal.example.com", "connection_user": "cassandra"},
                "password": "s3cr3t-pw",
            }
        )["catalog"]
        # Only the secret ref is persisted; the password never touches the row.
        self.assertTrue(created["config"]["password_secret_ref"].startswith("arn:aws:secretsmanager:"))
        self.assertNotIn("password", [k for k in created["config"] if k != "password_secret_ref"])

        aws = AwsInspector(region="us-east-2")
        props = aws.cassandra_catalog_properties(created, secret_resolver=lambda ref: "resolved-pw")
        self.assertIn("cassandra.username=cassandra", props)
        self.assertIn("cassandra.password=resolved-pw", props)
        # The embedded (no control-plane) user-data path must refuse to inline it, so
        # the password can never land in EC2 user-data.
        with self.assertRaises(RuntimeError):
            aws.trino_user_data(
                cluster={
                    "name": "c",
                    "catalogs": ["system", "nosql_auth"],
                    "catalog_configs": [dict(created, enabled=True)],
                },
                node_role="worker",
                region="us-east-2",
            )

    def test_cassandra_dropping_user_deletes_stored_secret(self):
        self.app.secret_store = FakeSecretStore()
        created = self.app.create_catalog(
            {
                "name": "nosql_auth",
                "type": "cassandra",
                "config": {"contact_points": "db1.internal.example.com", "connection_user": "cassandra"},
                "password": "s3cr3t-pw",
            }
        )["catalog"]
        old_ref = created["config"]["password_secret_ref"]
        # Removing the connection user turns the catalog unauthenticated; its stored
        # credential should be cleaned up.
        updated = self.app.update_catalog(
            created["id"],
            {"type": "cassandra", "config": {"contact_points": "db1.internal.example.com"}},
        )["catalog"]
        self.assertNotIn("connection_user", updated["config"])
        self.assertNotIn("password_secret_ref", updated["config"])
        self.assertIn(old_ref, self.app.secret_store.deleted)

    def test_cassandra_rejects_ssrf_contact_point(self):
        with self.assertRaises(ApiError) as context:
            self.app.create_catalog(
                {"name": "nosql_bad", "type": "cassandra", "config": {"contact_points": "db1.example.com,169.254.169.254"}}
            )
        self.assertEqual(context.exception.status, 400)
        self.assertIn("not allowed", context.exception.message)

    def test_prometheus_unauthenticated_catalog_stores_no_secret_and_renders_in_user_data(self):
        created = self.app.create_catalog(
            {"name": "metrics_open", "type": "prometheus", "config": {"uri": "http://prom.internal:9090"}}
        )["catalog"]
        self.assertEqual(created["config"]["connector_name"], "prometheus")
        self.assertEqual(created["config"]["uri"], "http://prom.internal:9090")
        self.assertNotIn("connection_user", created["config"])
        self.assertNotIn("password_secret_ref", created["config"])

        aws = AwsInspector(region="us-east-2")
        script = aws.trino_user_data(
            cluster={
                "name": "c",
                "catalogs": ["system", "metrics_open"],
                "catalog_configs": [dict(created, enabled=True)],
            },
            node_role="worker",
            region="us-east-2",
            coordinator_uri="http://10.0.1.10:8080",
        )
        self.assertIn("connector.name=prometheus", script)
        self.assertIn("prometheus.uri=http://prom.internal:9090", script)
        self.assertNotIn("prometheus.auth.user", script)
        self.assertNotIn("prometheus.auth.password", script)

    def test_prometheus_basic_auth_password_only_in_signed_node_config(self):
        self.app.secret_store = FakeSecretStore()
        created = self.app.create_catalog(
            {
                "name": "metrics_auth",
                "type": "prometheus",
                "config": {"uri": "https://prom.example.com/", "connection_user": "obs"},
                "password": "s3cr3t-pw",
            }
        )["catalog"]
        self.assertTrue(created["config"]["password_secret_ref"].startswith("arn:aws:secretsmanager:"))

        aws = AwsInspector(region="us-east-2")
        props = aws.prometheus_catalog_properties(created, secret_resolver=lambda ref: "resolved-pw")
        self.assertIn("prometheus.auth.user=obs", props)
        self.assertIn("prometheus.auth.password=resolved-pw", props)
        # The embedded (no control-plane) user-data path must refuse to inline it.
        with self.assertRaises(RuntimeError):
            aws.trino_user_data(
                cluster={
                    "name": "c",
                    "catalogs": ["system", "metrics_auth"],
                    "catalog_configs": [dict(created, enabled=True)],
                },
                node_role="worker",
                region="us-east-2",
            )

    def test_prometheus_rejects_non_http_uri_and_ssrf(self):
        for bad in ({"uri": "ftp://prom"}, {"uri": "notaurl"}, {"uri": "http://169.254.169.254"}):
            with self.subTest(config=bad):
                with self.assertRaises(ApiError) as context:
                    self.app.create_catalog({"name": "metrics_bad", "type": "prometheus", "config": bad})
                self.assertEqual(context.exception.status, 400)

    def test_create_gsheets_catalog_stores_only_credential_ref(self):
        self.app.secret_store = FakeSecretStore()
        key = json.dumps(
            {
                "type": "service_account",
                "project_id": "my-analytics-project",
                "private_key": "-----BEGIN PRIVATE KEY-----\nMIIsecret\n-----END PRIVATE KEY-----\n",
                "client_email": "trino@my-analytics-project.iam.gserviceaccount.com",
            }
        )
        result = self.app.create_catalog(
            {
                "name": "sheets",
                "type": "gsheets",
                "config": {"metadata_sheet_id": "1a2B3c4D5e6F7g8H9i0J-kLmNoPqRsTuVwXyZ012345"},
                "password": key,
            }
        )
        config = result["catalog"]["config"]
        self.assertEqual(config["connector_name"], "gsheets")
        self.assertEqual(config["metadata_sheet_id"], "1a2B3c4D5e6F7g8H9i0J-kLmNoPqRsTuVwXyZ012345")
        self.assertTrue(config["password_secret_ref"].startswith("arn:aws:secretsmanager:"))
        with self.app.conn() as conn:
            row = conn.execute("SELECT config_json FROM catalogs WHERE name = 'sheets'").fetchone()
        self.assertNotIn("PRIVATE KEY", row["config_json"])

    def test_gsheets_catalog_rejects_bad_sheet_id_and_bad_key(self):
        self.app.secret_store = FakeSecretStore()
        valid_key = json.dumps(
            {"type": "service_account", "project_id": "p", "private_key": "k", "client_email": "e"}
        )
        with self.assertRaises(ApiError) as ctx1:
            self.app.create_catalog(
                {"name": "sheets", "type": "gsheets", "config": {"metadata_sheet_id": "short"}, "password": valid_key}
            )
        self.assertEqual(ctx1.exception.status, 400)
        self.assertIn("metadata_sheet_id", ctx1.exception.message)
        with self.assertRaises(ApiError) as ctx2:
            self.app.create_catalog(
                {
                    "name": "sheets",
                    "type": "gsheets",
                    "config": {"metadata_sheet_id": "1a2B3c4D5e6F7g8H9i0J-kLmNoPqRsTuVwXyZ012345"},
                    "password": "not a service account",
                }
            )
        self.assertEqual(ctx2.exception.status, 400)

    def test_gsheets_catalog_renders_credentials_key_only_in_signed_node_config(self):
        key = json.dumps(
            {
                "type": "service_account",
                "project_id": "my-analytics-project",
                "private_key": "-----BEGIN PRIVATE KEY-----\nMIIsecret\n-----END PRIVATE KEY-----\n",
                "client_email": "trino@my-analytics-project.iam.gserviceaccount.com",
            }
        )
        script = self._node_config_with_catalog(
            TrinoHubApp(db_path=Path(tempfile.mkdtemp()) / "t.sqlite3", aws=FakeAws(), require_setup_token=False),
            "sheets",
            "gsheets",
            {"metadata_sheet_id": "1a2B3c4D5e6F7g8H9i0J-kLmNoPqRsTuVwXyZ012345"},
            key,
        )
        self.assertIn("connector.name=gsheets", script)
        self.assertIn("gsheets.metadata-sheet-id=1a2B3c4D5e6F7g8H9i0J-kLmNoPqRsTuVwXyZ012345", script)
        expected_b64 = base64.b64encode(key.encode("utf-8")).decode("ascii")
        self.assertIn(f"gsheets.credentials-key={expected_b64}", script)
        self.assertNotIn("BEGIN PRIVATE KEY", script)
        self.assertNotIn("MIIsecret", script)

    def test_list_connector_types_exposes_registry_form_schema(self):
        from trinohub.connectors import REGISTRY

        result = self.app.list_connector_types()
        by_type = {c["type"]: c for c in result["connector_types"]}
        # Every registered type is described exactly once, in registry order.
        self.assertEqual([c["type"] for c in result["connector_types"]], list(REGISTRY))

        # JDBC reference: credentialed, Databases group, URL + user fields, password.
        pg = by_type["postgresql"]
        self.assertEqual(pg["group"], "Databases")
        self.assertTrue(pg["requires_secret"])
        self.assertEqual([f["name"] for f in pg["fields"]], ["connection_url", "connection_user"])
        self.assertEqual(pg["credential"]["input"], "password")

        # S3/Glue: no credential; table format is a fixed read-only field.
        iceberg = by_type["s3_glue"]
        self.assertEqual(iceberg["group"], "Object storage")
        self.assertIsNone(iceberg["credential"])
        table_field = next(f for f in iceberg["fields"] if f["name"] == "table_format")
        self.assertEqual(table_field["input"], "readonly")
        self.assertEqual(table_field["value"], "Iceberg")
        self.assertIn("access_mode", [f["name"] for f in iceberg["fields"]])

        # Hudi is query-only: no access-mode field.
        self.assertNotIn("access_mode", [f["name"] for f in by_type["hudi_glue"]["fields"]])

        # Generators: zero-config, no secret.
        memory = by_type["memory"]
        self.assertEqual(memory["group"], "Test & sample data")
        self.assertEqual(memory["fields"], [])
        self.assertIsNone(memory["credential"])

        # GCP credential class surfaces as a textarea for BigQuery and Sheets.
        for gcp_type in ("bigquery", "gsheets"):
            self.assertEqual(by_type[gcp_type]["credential"]["input"], "textarea")
            self.assertEqual(by_type[gcp_type]["credential_kind"], "gcp_service_account")
        self.assertEqual([f["name"] for f in by_type["gsheets"]["fields"]], ["metadata_sheet_id"])

        # Cassandra: optional auth — not required, but the credential field is still
        # offered (never required on create) and the config carries an optional user.
        cassandra = by_type["cassandra"]
        self.assertFalse(cassandra["requires_secret"])
        self.assertTrue(cassandra["optional_secret"])
        self.assertEqual([f["name"] for f in cassandra["fields"]], ["contact_points", "port", "connection_user"])
        self.assertEqual(cassandra["credential"]["input"], "password")
        self.assertFalse(cassandra["credential"]["required_on_create"])

        # Prometheus: also optional auth — a single URI + optional user, optional credential.
        prometheus = by_type["prometheus"]
        self.assertTrue(prometheus["optional_secret"])
        self.assertEqual([f["name"] for f in prometheus["fields"]], ["uri", "connection_user"])
        self.assertFalse(prometheus["credential"]["required_on_create"])

    def test_upload_connector_driver_stores_metadata_and_file(self):
        jar = b"PK\x03\x04" + b"\x00" * 200
        result = self.app.store_connector_driver("oracle", "ojdbc11.jar", jar, {"username": "admin"})
        driver = result["driver"]
        self.assertEqual(driver["connector_type"], "oracle")
        self.assertEqual(driver["filename"], "ojdbc11.jar")
        self.assertEqual(driver["size_bytes"], len(jar))
        self.assertEqual(driver["sha256"], hashlib.sha256(jar).hexdigest())
        self.assertEqual(driver["uploaded_by"], "admin")
        self.assertTrue((self.app.drivers_dir() / "oracle.jar").exists())
        self.assertEqual(len(self.app.list_connector_drivers()["drivers"]), 1)
        # Re-upload replaces the row and hash.
        jar2 = b"PK\x03\x04" + b"\x01" * 300
        self.app.store_connector_driver("oracle", "ojdbc11.jar", jar2, {"username": "admin"})
        self.assertEqual(self.app.connector_driver("oracle")["sha256"], hashlib.sha256(jar2).hexdigest())
        self.assertEqual(len(self.app.list_connector_drivers()["drivers"]), 1)

    def test_upload_connector_driver_rejects_non_jar_and_wrong_type(self):
        with self.assertRaises(ApiError) as ctx:
            self.app.store_connector_driver("oracle", "x.jar", b"not a zip archive", {"username": "admin"})
        self.assertEqual(ctx.exception.status, 400)
        self.assertIn("must be a .jar", ctx.exception.message)
        # A connector that bundles its own driver cannot accept an upload.
        with self.assertRaises(ApiError) as ctx2:
            self.app.store_connector_driver("postgresql", "pg.jar", b"PK\x03\x04\x00", {"username": "admin"})
        self.assertIn("does not require", ctx2.exception.message)

    def test_oracle_cluster_start_requires_driver_then_node_config_installs_it(self):
        app = TrinoHubApp(db_path=Path(tempfile.mkdtemp()) / "t.sqlite3", aws=FakeAws(), require_setup_token=False)
        app.secret_store = FakeSecretStore()
        app.complete_setup(
            {"username": "admin", "password": "correct-horse-password", "allowed_instance_types": ["r7i.2xlarge"]}
        )
        app.create_catalog(
            {
                "name": "warehouse_oracle",
                "type": "oracle",
                "config": {
                    "connection_url": "jdbc:oracle:thin:@//db.internal.example.com:1521/warehouse",
                    "connection_user": "reader",
                },
                "password": "s3cr3t-pw",
            }
        )
        with app.conn() as conn:
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        cluster = app.create_cluster(
            {
                "name": "oracle-cluster",
                "instance_type": "r7i.2xlarge",
                "worker_mode": "fixed",
                "min_workers": 1,
                "max_workers": 1,
                "catalogs": ["system", "warehouse_oracle"],
            },
            user,
        )["cluster"]
        # Starting fails fast until the driver is uploaded.
        with self.assertRaises(ApiError) as ctx:
            app.start_cluster(cluster["id"], {"confirm_billable": True})
        self.assertEqual(ctx.exception.status, 400)
        self.assertIn("driver uploaded", ctx.exception.message.lower())

        jar = b"PK\x03\x04" + b"\x00" * 256
        app.store_connector_driver("oracle", "ojdbc11.jar", jar, {"username": "admin"})
        app.start_cluster(cluster["id"], {"confirm_billable": True})
        token = app.aws.worker_template_calls[-1]["bootstrap_token"]
        script = app.node_config_script(cluster_id=cluster["id"], role="worker", token=token, instance_type="m7i.large")
        sha = hashlib.sha256(jar).hexdigest()
        self.assertIn('install -d -m 0755 "/opt/trino/plugin/oracle"', script)
        self.assertIn(f"/api/node-config/{cluster['id']}/driver/oracle?token=", script)
        self.assertIn('--output "/opt/trino/plugin/oracle/ojdbc11.jar"', script)
        self.assertIn(f"{sha}  /opt/trino/plugin/oracle/ojdbc11.jar", script)

    def test_trino_cross_cluster_catalog_requires_plugin_then_renders(self):
        # The Trino-to-Trino connector (trinodb/trino#30290) federates a remote
        # cluster over JDBC. It is not in a stock Trino release, so — like Oracle —
        # a cluster using it cannot start until the plugin JAR is uploaded, and it
        # then renders the standard JDBC connector.name=trino block on the signed
        # node path (never into plain user-data).
        app = TrinoHubApp(db_path=Path(tempfile.mkdtemp()) / "t.sqlite3", aws=FakeAws(), require_setup_token=False)
        app.secret_store = FakeSecretStore()
        app.complete_setup(
            {"username": "admin", "password": "correct-horse-password", "allowed_instance_types": ["r7i.2xlarge"]}
        )
        connection_url = "jdbc:trino://analytics.trino.example.com:443/hive?SSL=true"
        created = app.create_catalog(
            {
                "name": "remote_trino",
                "type": "trino",
                "config": {"connection_url": connection_url, "connection_user": "federator"},
                "password": "s3cr3t-pw",
            }
        )["catalog"]
        self.assertEqual(created["config"]["connector_name"], "trino")
        self.assertNotIn("password", created["config"])
        with app.conn() as conn:
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        cluster = app.create_cluster(
            {
                "name": "federation-cluster",
                "instance_type": "r7i.2xlarge",
                "worker_mode": "fixed",
                "min_workers": 1,
                "max_workers": 1,
                "catalogs": ["system", "remote_trino"],
            },
            user,
        )["cluster"]
        # Starting fails fast until the connector plugin JAR is uploaded.
        with self.assertRaises(ApiError) as ctx:
            app.start_cluster(cluster["id"], {"confirm_billable": True})
        self.assertEqual(ctx.exception.status, 400)
        self.assertIn("driver uploaded", ctx.exception.message.lower())

        jar = b"PK\x03\x04" + b"\x00" * 256
        app.store_connector_driver("trino", "trino-trino.jar", jar, {"username": "admin"})
        app.start_cluster(cluster["id"], {"confirm_billable": True})
        token = app.aws.worker_template_calls[-1]["bootstrap_token"]
        script = app.node_config_script(cluster_id=cluster["id"], role="worker", token=token, instance_type="m7i.large")
        self.assertIn("connector.name=trino", script)
        self.assertIn(f"connection-url={connection_url}", script)
        self.assertIn("connection-user=federator", script)
        self.assertIn("connection-password=s3cr3t-pw", script)
        self.assertIn('install -d -m 0755 "/opt/trino/plugin/trino"', script)
        self.assertIn('--output "/opt/trino/plugin/trino/trino-trino.jar"', script)

    def test_trino_catalog_rejects_non_trino_url_scheme(self):
        # A trino catalog only accepts jdbc:trino:// URLs.
        self.app.secret_store = FakeSecretStore()
        with self.assertRaises(ApiError) as ctx:
            self.app.create_catalog(
                {
                    "name": "remote_trino",
                    "type": "trino",
                    "config": {
                        "connection_url": "jdbc:postgresql://db.internal.example.com:5432/warehouse",
                        "connection_user": "federator",
                    },
                    "password": "s3cr3t-pw",
                }
            )
        self.assertEqual(ctx.exception.status, 400)
        self.assertIn("jdbc:trino://", ctx.exception.message)

    def test_node_driver_file_enforces_token_and_attachment(self):
        app = TrinoHubApp(db_path=Path(tempfile.mkdtemp()) / "t.sqlite3", aws=FakeAws(), require_setup_token=False)
        app.secret_store = FakeSecretStore()
        app.complete_setup(
            {"username": "admin", "password": "correct-horse-password", "allowed_instance_types": ["r7i.2xlarge"]}
        )
        app.store_connector_driver("oracle", "ojdbc11.jar", b"PK\x03\x04" + b"\x00" * 64, {"username": "admin"})
        app.create_catalog(
            {
                "name": "warehouse_oracle",
                "type": "oracle",
                "config": {
                    "connection_url": "jdbc:oracle:thin:@//db.internal.example.com:1521/warehouse",
                    "connection_user": "reader",
                },
                "password": "pw",
            }
        )
        with app.conn() as conn:
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        cluster = app.create_cluster(
            {
                "name": "oracle-cluster",
                "instance_type": "r7i.2xlarge",
                "worker_mode": "fixed",
                "min_workers": 1,
                "max_workers": 1,
                "catalogs": ["system", "warehouse_oracle"],
            },
            user,
        )["cluster"]
        app.start_cluster(cluster["id"], {"confirm_billable": True})
        token = app.aws.worker_template_calls[-1]["bootstrap_token"]
        with self.assertRaises(ApiError):
            app.node_driver_file(cluster["id"], "oracle", "bogus-token")
        path, filename = app.node_driver_file(cluster["id"], "oracle", token)
        self.assertEqual(filename, "ojdbc11.jar")
        self.assertTrue(path.exists())
        # A connector not attached to the cluster is refused even with a valid token.
        with self.assertRaises(ApiError) as ctx:
            app.node_driver_file(cluster["id"], "mysql", token)
        self.assertEqual(ctx.exception.status, 404)

    def test_cluster_rejects_unknown_custom_catalog(self):
        user = self._setup_admin()

        with self.assertRaises(ApiError) as context:
            self.app.create_cluster(
                {
                    "name": "catalog-test",
                    "instance_type": "r7i.2xlarge",
                    "worker_mode": "fixed",
                    "min_workers": 1,
                    "max_workers": 1,
                    "catalogs": ["system", "analytics_s3"],
                },
                user,
            )

        self.assertEqual(context.exception.status, 400)
        self.assertIn("Unknown catalog: analytics_s3", context.exception.message)

    def test_start_cluster_passes_custom_catalog_configs_to_aws(self):
        self.app.complete_setup(
            {"username": "admin", "password": "correct-horse-password", "allowed_instance_types": ["r7i.2xlarge"]}
        )
        self.app.create_catalog(
            {
                "name": "analytics_s3",
                "type": "s3_glue",
                "config": {
                    "glue_region": "us-east-2",
                    "warehouse": "s3://company-lakehouse/warehouse/",
                    "default_schema": "analytics",
                    "access_mode": "read_write",
                },
            }
        )
        with self.app.conn() as conn:
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        cluster = self.app.create_cluster(
            {
                "name": "catalog-test",
                "instance_type": "r7i.2xlarge",
                "worker_mode": "fixed",
                "min_workers": 1,
                "max_workers": 1,
                "catalogs": ["system", "tpch", "analytics_s3"],
            },
            user,
        )["cluster"]

        self.app.start_cluster(cluster["id"], {"confirm_billable": True})

        catalog_configs = self.app.aws.worker_template_calls[-1]["cluster"]["catalog_configs"]
        self.assertEqual(catalog_configs[0]["name"], "analytics_s3")
        self.assertEqual(catalog_configs[0]["config"]["warehouse"], "s3://company-lakehouse/warehouse/")

    def test_start_cluster_mints_signed_node_config_token(self):
        cluster = self.create_test_cluster()

        self.app.start_cluster(cluster["id"], {"confirm_billable": True})

        worker_call = self.app.aws.worker_template_calls[-1]
        token = worker_call["bootstrap_token"]
        self.assertEqual(worker_call["control_plane_uri"], "http://10.0.9.9:8000")
        script = self.app.node_config_script(
            cluster_id=cluster["id"],
            role="worker",
            token=token,
            instance_type="m7i.large",
        )
        self.assertIn("cat >/etc/trino/catalog/tpch.properties", script)
        self.assertIn("discovery.uri=http://10.0.1.10:8080", script)
        # Coordinator sits behind the Caddy gateway, which injects X-Forwarded-*;
        # without this Trino answers 406 to every proxied request.
        self.assertIn("http-server.process-forwarded=true", script)
        with self.assertRaises(ApiError) as context:
            self.app.node_config_script(cluster_id=cluster["id"], role="worker", token="bad-token")
        self.assertEqual(context.exception.status, 403)

    def test_start_cluster_requires_billable_confirmation(self):
        cluster = self.create_test_cluster()
        with self.assertRaises(ApiError) as context:
            self.app.start_cluster(cluster["id"], {})
        self.assertEqual(context.exception.status, 409)
        self.assertIn("billable AWS resources", context.exception.message)

    def test_start_cluster_records_aws_resources(self):
        cluster = self.create_test_cluster()
        result = self.app.start_cluster(cluster["id"], {"confirm_billable": True})

        self.assertFalse(result["dry_run"])
        self.assertEqual(result["cluster"]["status"], "Starting")
        self.assertEqual(
            sorted(resource["type"] for resource in result["resources"]),
            ["auto_scaling_group", "coordinator_instance", "launch_template", "security_group"],
        )
        resource_ids = {resource["resource_id"] for resource in result["resources"]}
        self.assertEqual(resource_ids, {"sg-managed", "i-coordinator", "lt-test", "trinohub-test-cluster-workers"})

    def test_start_cluster_passes_coordinator_uri_to_workers(self):
        cluster = self.create_test_cluster()
        self.app.start_cluster(cluster["id"], {"confirm_billable": True})

        self.assertEqual(self.app.aws.worker_template_calls[-1]["coordinator_uri"], "http://10.0.1.10:8080")
        with self.app.conn() as conn:
            row = conn.execute(
                """
                SELECT metadata_json FROM provider_resources
                WHERE cluster_id = ? AND resource_type = 'coordinator_instance'
                """,
                (cluster["id"],),
            ).fetchone()
        self.assertEqual(json.loads(row["metadata_json"])["private_ip_address"], "10.0.1.10")

    def test_refresh_cluster_health_marks_running(self):
        cluster = self.create_test_cluster()
        self.app.start_cluster(cluster["id"], {"confirm_billable": True})

        result = self.app.refresh_cluster_health(cluster["id"])

        self.assertTrue(result["health"]["ok"])
        self.assertEqual(result["cluster"]["status"], "Running")
        self.assertEqual(self.app.aws.health_calls[-1], "10.0.1.10")
        with self.app.conn() as conn:
            event_count = conn.execute(
                "SELECT COUNT(*) FROM cluster_events WHERE cluster_id = ? AND event_type = 'coordinator_ready'",
                (cluster["id"],),
            ).fetchone()[0]
        self.assertEqual(event_count, 1)

    def test_refresh_cluster_health_keeps_starting_when_unreachable(self):
        cluster = self.create_test_cluster()
        self.app.start_cluster(cluster["id"], {"confirm_billable": True})
        self.app.aws.health_response = {
            "ok": False,
            "state": "unreachable",
            "detail": "timed out",
        }

        result = self.app.refresh_cluster_health(cluster["id"])

        self.assertFalse(result["health"]["ok"])
        self.assertEqual(result["cluster"]["status"], "Starting")

    def test_suspend_cluster_cleans_runtime_resources(self):
        cluster = self.create_test_cluster()
        self.app.start_cluster(cluster["id"], {"confirm_billable": True})

        result = self.app.suspend_cluster(cluster["id"])

        self.assertEqual(result["cluster"]["status"], "Suspended")
        with self.app.conn() as conn:
            remaining = conn.execute("SELECT COUNT(*) FROM provider_resources WHERE cluster_id = ?", (cluster["id"],)).fetchone()[0]
        self.assertEqual(remaining, 0)
        self.assertIn(("terminate_instances", ("i-coordinator",)), self.app.aws.cleanup_calls)
        self.assertIn(("delete_launch_template", "lt-test"), self.app.aws.cleanup_calls)

    def test_disable_cluster_cleans_runtime_resources_and_marks_not_enabled(self):
        cluster = self.create_test_cluster()
        self.app.start_cluster(cluster["id"], {"confirm_billable": True})

        result = self.app.disable_cluster(cluster["id"])

        self.assertEqual(result["cluster"]["status"], "Not enabled")
        with self.app.conn() as conn:
            remaining = conn.execute("SELECT COUNT(*) FROM provider_resources WHERE cluster_id = ?", (cluster["id"],)).fetchone()[0]
            tokens = conn.execute("SELECT COUNT(*) FROM cluster_bootstrap_tokens WHERE cluster_id = ?", (cluster["id"],)).fetchone()[0]
        self.assertEqual(remaining, 0)
        self.assertEqual(tokens, 0)
        self.assertIn(("terminate_instances", ("i-coordinator",)), self.app.aws.cleanup_calls)

    def test_delete_cluster_removes_record_and_resources(self):
        cluster = self.create_test_cluster()
        self.app.start_cluster(cluster["id"], {"confirm_billable": True})

        result = self.app.delete_cluster(cluster["id"])

        self.assertTrue(result["deleted"])
        with self.app.conn() as conn:
            cluster_count = conn.execute("SELECT COUNT(*) FROM clusters WHERE id = ?", (cluster["id"],)).fetchone()[0]
            resource_count = conn.execute("SELECT COUNT(*) FROM provider_resources WHERE cluster_id = ?", (cluster["id"],)).fetchone()[0]
        self.assertEqual(cluster_count, 0)
        self.assertEqual(resource_count, 0)

    def test_delete_cluster_revokes_managed_security_group_rules_first(self):
        self.app.aws = SecurityGroupDependencyAws()
        cluster = self.create_test_cluster()
        self.app.start_cluster(cluster["id"], {"confirm_billable": True})

        result = self.app.delete_cluster(cluster["id"])

        self.assertTrue(result["deleted"])
        cleanup_index = self.app.aws.cleanup_calls.index(("cleanup_security_group_rules", "sg-managed"))
        delete_index = self.app.aws.cleanup_calls.index(("delete_security_group", "sg-managed"))
        self.assertLess(cleanup_index, delete_index)
        with self.app.conn() as conn:
            cluster_count = conn.execute("SELECT COUNT(*) FROM clusters WHERE id = ?", (cluster["id"],)).fetchone()[0]
            resource_count = conn.execute("SELECT COUNT(*) FROM provider_resources WHERE cluster_id = ?", (cluster["id"],)).fetchone()[0]
        self.assertEqual(cluster_count, 0)
        self.assertEqual(resource_count, 0)

    def test_start_allows_existing_security_group_record(self):
        cluster = self.create_test_cluster()
        with self.app.conn() as conn:
            conn.execute(
                """
                INSERT INTO provider_resources (cluster_id, resource_type, resource_id, region, metadata_json, created_at)
                VALUES (?, 'security_group', 'sg-managed', 'us-east-2', '{"managed":true}', '2026-01-01T00:00:00+00:00')
                """,
                (cluster["id"],),
            )

        result = self.app.start_cluster(cluster["id"], {"confirm_billable": True})

        self.assertEqual(result["cluster"]["status"], "Starting")

    def test_autoscaler_scales_up_when_queries_are_queued_for_two_intervals(self):
        cluster = self.create_running_autoscale_cluster()
        now = datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc)
        self.app.aws.trino_stats = {"ok": True, "running_queries": 1, "queued_queries": 1, "active_workers": 1}
        self.app.aws.cpu_average = 20.0

        first = self.app.autoscale_cluster_once(cluster["id"], now=now)
        second = self.app.autoscale_cluster_once(cluster["id"], now=now + timedelta(seconds=30))

        self.assertEqual(first["action"], "hold")
        self.assertEqual(second["action"], "scale")
        self.assertEqual(second["direction"], "up")
        self.assertEqual(second["from_workers"], 1)
        self.assertEqual(second["to_workers"], 2)
        self.assertEqual(self.app.aws.scaling_calls[-1]["desired_capacity"], 2)
        with self.app.conn() as conn:
            event = conn.execute(
                "SELECT direction, from_workers, to_workers, reason FROM scaling_events WHERE cluster_id = ?",
                (cluster["id"],),
            ).fetchone()
        self.assertEqual(dict(event)["direction"], "up")

    def test_autoscaler_scales_up_when_cpu_is_high_for_three_intervals(self):
        cluster = self.create_running_autoscale_cluster()
        now = datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc)
        self.app.aws.trino_stats = {"ok": True, "running_queries": 1, "queued_queries": 0, "active_workers": 1}
        self.app.aws.cpu_average = 80.0

        self.app.autoscale_cluster_once(cluster["id"], now=now)
        self.app.autoscale_cluster_once(cluster["id"], now=now + timedelta(seconds=30))
        result = self.app.autoscale_cluster_once(cluster["id"], now=now + timedelta(seconds=60))

        self.assertEqual(result["action"], "scale")
        self.assertEqual(result["direction"], "up")
        self.assertIn("Average worker CPU", result["reason"])

    def test_autoscaler_scales_down_after_idle_low_cpu_window(self):
        cluster = self.create_running_autoscale_cluster()
        now = datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc)
        self.app.aws.worker_asg["desired_capacity"] = 2
        self.app.aws.worker_asg["in_service_capacity"] = 2
        self.app.aws.worker_asg["instance_ids"] = ["i-worker-1", "i-worker-2"]
        self.app.aws.trino_stats = {"ok": True, "running_queries": 0, "queued_queries": 0, "active_workers": 2}
        self.app.aws.cpu_average = 10.0
        self.app._persist_autoscale_state(
            cluster["id"], {"queued_intervals": 0, "cpu_high_intervals": 0, "idle_low_since": now - timedelta(seconds=601)}
        )

        result = self.app.autoscale_cluster_once(cluster["id"], now=now)

        self.assertEqual(result["action"], "scale")
        self.assertEqual(result["direction"], "down")
        self.assertEqual(result["from_workers"], 2)
        self.assertEqual(result["to_workers"], 1)

    def test_autoscaler_respects_scale_up_cooldown(self):
        cluster = self.create_running_autoscale_cluster()
        now = datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc)
        self.app.aws.trino_stats = {"ok": True, "running_queries": 1, "queued_queries": 1, "active_workers": 1}
        self.app._persist_autoscale_state(
            cluster["id"], {"queued_intervals": 1, "cpu_high_intervals": 0, "idle_low_since": None}
        )
        with self.app.conn() as conn:
            conn.execute(
                """
                INSERT INTO scaling_events (cluster_id, direction, from_workers, to_workers, reason, created_at)
                VALUES (?, 'up', 1, 2, 'recent scale', ?)
                """,
                (cluster["id"], (now - timedelta(seconds=60)).isoformat(timespec="seconds")),
            )

        result = self.app.autoscale_cluster_once(cluster["id"], now=now)

        self.assertEqual(result["action"], "hold")
        self.assertEqual(result["reason"], "Scale-up cooldown is active.")
        self.assertEqual(self.app.aws.scaling_calls, [])

    def test_auto_suspend_suspends_idle_cluster_after_interval(self):
        cluster = self.create_running_auto_suspend_cluster(minutes=15)
        now = datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc)
        self.app.aws.trino_stats = {"ok": True, "running_queries": 0, "queued_queries": 0, "active_workers": 1}

        first = self.app.auto_suspend_cluster_once(cluster["id"], now=now)
        second = self.app.auto_suspend_cluster_once(cluster["id"], now=now + timedelta(minutes=15, seconds=1))

        self.assertEqual(first["action"], "hold")
        self.assertEqual(second["action"], "suspend")
        with self.app.conn() as conn:
            row = conn.execute("SELECT status FROM clusters WHERE id = ?", (cluster["id"],)).fetchone()
            remaining = conn.execute("SELECT COUNT(*) FROM provider_resources WHERE cluster_id = ?", (cluster["id"],)).fetchone()[0]
            event_count = conn.execute(
                "SELECT COUNT(*) FROM cluster_events WHERE cluster_id = ? AND event_type = 'auto_suspend_started'",
                (cluster["id"],),
            ).fetchone()[0]
        self.assertEqual(row["status"], "Suspended")
        self.assertEqual(remaining, 0)
        self.assertEqual(event_count, 1)
        self.assertIn(("terminate_instances", ("i-coordinator",)), self.app.aws.cleanup_calls)

    def test_auto_suspend_fires_across_a_service_restart(self):
        # P2.3: the idle clock is persisted, so a restart between the first idle
        # observation and the suspend deadline must not reset it.
        cluster = self.create_running_auto_suspend_cluster(minutes=15)
        start = datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc)

        first = self.app.auto_suspend_cluster_once(cluster["id"], now=start)
        self.assertEqual(first["action"], "hold")

        # Simulate a service restart: a brand-new app on the same DB has no
        # in-memory timer state, only what was persisted.
        db_path = self.app.db_path
        restarted = TrinoHubApp(db_path=db_path, aws=FakeAws())
        result = restarted.auto_suspend_cluster_once(
            cluster["id"], now=start + timedelta(minutes=15, seconds=1)
        )

        self.assertEqual(result["action"], "suspend")
        with restarted.conn() as conn:
            status = conn.execute("SELECT status FROM clusters WHERE id = ?", (cluster["id"],)).fetchone()["status"]
        self.assertEqual(status, "Suspended")

    def test_starting_a_cluster_clears_stale_timer_state(self):
        # A stale idle clock from a prior run must not survive into a fresh start
        # (which would otherwise trigger an instant suspend on resume).
        cluster = self.create_running_auto_suspend_cluster(minutes=15)
        self.app._persist_auto_suspend_state(
            cluster["id"], datetime(2020, 1, 1, tzinfo=timezone.utc)
        )
        # Suspend, then start again — the timer row should be gone.
        self.app.suspend_cluster(cluster["id"])
        with self.app.conn() as conn:
            rows = conn.execute(
                "SELECT COUNT(*) FROM cluster_timer_state WHERE cluster_id = ?", (cluster["id"],)
            ).fetchone()[0]
        self.assertEqual(rows, 0)

    def test_auto_suspend_holds_when_local_query_is_active(self):
        cluster = self.create_running_auto_suspend_cluster(minutes=15)
        now = datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc)
        self.app.aws.trino_stats = {"ok": True, "running_queries": 0, "queued_queries": 0, "active_workers": 1}
        self.app._persist_auto_suspend_state(cluster["id"], now - timedelta(minutes=16))
        with self.app.conn() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
            conn.execute(
                """
                INSERT INTO query_runs
                  (user_id, cluster_id, sql_text, status, elapsed_ms, row_count, created_at, updated_at)
                VALUES (?, ?, 'SELECT 1', 'Running', 0, 0, ?, ?)
                """,
                (user["id"], cluster["id"], now.isoformat(timespec="seconds"), now.isoformat(timespec="seconds")),
            )

        result = self.app.auto_suspend_cluster_once(cluster["id"], now=now)

        self.assertEqual(result["action"], "hold")
        self.assertEqual(result["reason"], "Cluster still has active or queued query work.")
        with self.app.conn() as conn:
            row = conn.execute("SELECT status FROM clusters WHERE id = ?", (cluster["id"],)).fetchone()
        self.assertEqual(row["status"], "Running")

    def test_query_against_auto_suspended_cluster_queues_and_resumes(self):
        cluster = self.create_test_cluster(auto_suspend_minutes=15)
        with self.app.conn() as conn:
            conn.execute("UPDATE clusters SET status = 'Suspended' WHERE id = ?", (cluster["id"],))
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())

        # The query is queued (not failed) and the cluster is resumed underneath it.
        result = self.app.create_query({"cluster_id": cluster["id"], "sql": "SELECT 1"}, user)
        self.assertEqual(result["query"]["status"], "Queued")
        self.assertTrue(result["query"]["pending_cluster_start"])

        with self.app.conn() as conn:
            row = conn.execute("SELECT status FROM clusters WHERE id = ?", (cluster["id"],)).fetchone()
            resource_count = conn.execute("SELECT COUNT(*) FROM provider_resources WHERE cluster_id = ?", (cluster["id"],)).fetchone()[0]
        self.assertEqual(row["status"], "Starting")
        self.assertEqual(resource_count, 4)

    def test_pending_query_dispatches_once_cluster_is_running(self):
        cluster = self.create_test_cluster(auto_suspend_minutes=15)
        with self.app.conn() as conn:
            conn.execute("UPDATE clusters SET status = 'Suspended' WHERE id = ?", (cluster["id"],))
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())

        result = self.app.create_query({"cluster_id": cluster["id"], "sql": "SELECT 1"}, user)
        query_id = result["query"]["id"]
        self.assertEqual(result["query"]["status"], "Queued")

        # Coordinator answers the health check: cluster flips Starting -> Running and
        # the queued query dispatches to Trino on the next poll.
        submitted = []

        def submit(**kwargs):
            submitted.append(kwargs)
            return {
                "id": "20260617_000001_00001_test",
                "columns": [{"name": "n", "type": "integer"}],
                "data": [[1]],
            }

        self.app.submit_trino_query = submit
        polled = self.app.get_query(query_id, user)

        self.assertEqual(polled["query"]["status"], "Finished")
        self.assertFalse(polled["query"]["pending_cluster_start"])
        self.assertEqual(polled["query"]["data"], [[1]])
        self.assertEqual(len(submitted), 1)
        self.assertEqual(submitted[0]["sql_text"], "SELECT 1")
        with self.app.conn() as conn:
            row = conn.execute("SELECT status FROM clusters WHERE id = ?", (cluster["id"],)).fetchone()
        self.assertEqual(row["status"], "Running")

    # --- Native Trino wire-protocol resume shim ------------------------------

    def _suspended_wire_cluster(self):
        """A Suspended, auto-suspend cluster with a base domain set; returns
        (cluster, host)."""
        cluster = self.create_test_cluster(auto_suspend_minutes=15)
        self.app.set_cluster_base_domain({"cluster_base_domain": "trino.acme.internal"})
        with self.app.conn() as conn:
            conn.execute("UPDATE clusters SET status = 'Suspended' WHERE id = ?", (cluster["id"],))
        return cluster, "test-cluster.trino.acme.internal"

    @staticmethod
    def _shim_id_from(results):
        return results["nextUri"].split("/")[-2]

    def test_wire_submit_resumes_suspended_and_returns_queued(self):
        cluster, host = self._suspended_wire_cluster()

        result = self.app.wire_submit_statement(
            host, b"SELECT 1", [("host", host), ("x-trino-user", "admin")]
        )

        self.assertEqual(result["kind"], "queued")
        self.assertEqual(result["results"]["stats"]["state"], "QUEUED")
        self.assertTrue(result["results"]["id"])
        self.assertTrue(result["results"]["infoUri"])
        self.assertIn(f"https://{host}/v1/statement/resuming/", result["results"]["nextUri"])
        with self.app.conn() as conn:
            row = conn.execute("SELECT status FROM clusters WHERE id = ?", (cluster["id"],)).fetchone()
            resources = conn.execute("SELECT COUNT(*) FROM provider_resources WHERE cluster_id = ?", (cluster["id"],)).fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM wire_pending WHERE cluster_id = ?", (cluster["id"],)).fetchone()[0]
        self.assertEqual(row["status"], "Starting")
        self.assertEqual(resources, 4)
        self.assertEqual(pending, 1)

    def test_wire_concurrent_submits_launch_cluster_once(self):
        cluster, host = self._suspended_wire_cluster()

        self.app.wire_submit_statement(host, b"SELECT 1", [("host", host)])
        # Second query arrives while the cluster is already Starting: it should hold
        # too, but must not launch a second coordinator.
        second = self.app.wire_submit_statement(host, b"SELECT 2", [("host", host)])

        self.assertEqual(second["kind"], "queued")
        with self.app.conn() as conn:
            coordinators = conn.execute(
                "SELECT COUNT(*) FROM provider_resources WHERE cluster_id = ? AND resource_type = 'coordinator_instance'",
                (cluster["id"],),
            ).fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM wire_pending WHERE cluster_id = ?", (cluster["id"],)).fetchone()[0]
        self.assertEqual(coordinators, 1)
        self.assertEqual(pending, 2)

    def test_start_cluster_is_idempotent_under_concurrent_claim(self):
        cluster, _ = self._suspended_wire_cluster()
        self.app.start_cluster(cluster["id"], {"confirm_billable": True})
        # A racing claim (status already Starting) is rejected rather than launching
        # a duplicate set of AWS resources.
        with self.assertRaises(ApiError) as ctx:
            self.app.start_cluster(cluster["id"], {"confirm_billable": True})
        self.assertEqual(ctx.exception.status, 409)

    def test_wire_poll_holds_then_hands_off_to_coordinator(self):
        cluster, host = self._suspended_wire_cluster()
        submit = self.app.wire_submit_statement(host, b"SELECT 1", [("host", host)])
        shim_id = self._shim_id_from(submit["results"])

        # Coordinator not up yet -> another QUEUED holding response.
        self.app.aws.health_response = {**self.app.aws.health_response, "ok": False}
        held = self.app.wire_poll_resuming(shim_id, 2)
        self.assertEqual(held["kind"], "queued")
        self.assertEqual(held["results"]["stats"]["state"], "QUEUED")

        # Coordinator answers: the capture is replayed to Trino and handed off.
        self.app.aws.health_response = {**self.app.aws.health_response, "ok": True}
        forwarded = {}

        def fake_forward(**kwargs):
            forwarded.update(kwargs)
            return 200, [("content-type", "application/json")], b'{"id":"q1","stats":{"state":"RUNNING"}}'

        self.app._forward_to_coordinator = fake_forward
        handed = self.app.wire_poll_resuming(shim_id, 3)

        self.assertEqual(handed["kind"], "proxied")
        self.assertEqual(handed["status"], 200)
        self.assertIn(b"RUNNING", handed["body"])
        self.assertEqual(forwarded["method"], "POST")
        self.assertEqual(forwarded["path_qs"], "/v1/statement")
        with self.app.conn() as conn:
            pending = conn.execute("SELECT COUNT(*) FROM wire_pending WHERE shim_id = ?", (shim_id,)).fetchone()[0]
            status = conn.execute("SELECT status FROM clusters WHERE id = ?", (cluster["id"],)).fetchone()["status"]
        self.assertEqual(pending, 0)
        self.assertEqual(status, "Running")

    def test_wire_poll_times_out_into_failed_result(self):
        _, host = self._suspended_wire_cluster()
        submit = self.app.wire_submit_statement(host, b"SELECT 1", [("host", host)])
        shim_id = self._shim_id_from(submit["results"])
        # Age the capture past the resume ceiling.
        with self.app.conn() as conn:
            conn.execute(
                "UPDATE wire_pending SET created_at = ? WHERE shim_id = ?",
                ("2000-01-01T00:00:00+00:00", shim_id),
            )

        result = self.app.wire_poll_resuming(shim_id, 5)

        self.assertEqual(result["kind"], "failed")
        self.assertEqual(result["results"]["stats"]["state"], "FAILED")
        self.assertIn("error", result["results"])
        self.assertTrue(result["results"]["error"]["message"])
        with self.app.conn() as conn:
            pending = conn.execute("SELECT COUNT(*) FROM wire_pending WHERE shim_id = ?", (shim_id,)).fetchone()[0]
        self.assertEqual(pending, 0)

    def test_wire_capture_preserves_trino_headers_and_drops_hop_by_hop(self):
        _, host = self._suspended_wire_cluster()
        submit = self.app.wire_submit_statement(
            host,
            b"SELECT 1",
            [
                ("host", host),
                ("content-length", "8"),
                ("connection", "keep-alive"),
                ("x-trino-user", "amy"),
                ("x-trino-session", "query_max_run_time=1h"),
                ("authorization", "Bearer sekret"),
            ],
        )
        shim_id = self._shim_id_from(submit["results"])
        capture = self.app._load_wire_capture(shim_id)
        stored = {k.lower(): v for k, v in json.loads(capture["headers_json"])}

        self.assertEqual(capture["sql_body"], b"SELECT 1")
        self.assertEqual(stored.get("x-trino-session"), "query_max_run_time=1h")
        self.assertEqual(stored.get("authorization"), "Bearer sekret")
        # Hop-by-hop / host-specific headers are not persisted.
        self.assertNotIn("host", stored)
        self.assertNotIn("content-length", stored)
        self.assertNotIn("connection", stored)

    def test_wire_proxy_forwards_to_coordinator(self):
        cluster, user = self.create_running_cluster()
        self.app.set_cluster_base_domain({"cluster_base_domain": "trino.acme.internal"})
        host = "test-cluster.trino.acme.internal"
        forwarded = {}

        def fake_forward(**kwargs):
            forwarded.update(kwargs)
            return 200, [("content-type", "application/json")], b'{"ok":true}'

        self.app._forward_to_coordinator = fake_forward
        result = self.app.wire_proxy(
            host, "GET", "/v1/statement/executing/q/slug/1", [("host", host)], b""
        )

        self.assertEqual(result["kind"], "proxied")
        self.assertEqual(forwarded["method"], "GET")
        self.assertEqual(forwarded["path_qs"], "/v1/statement/executing/q/slug/1")

    def test_wire_submit_unknown_host_has_no_route(self):
        self._suspended_wire_cluster()
        result = self.app.wire_submit_statement(
            "nope.trino.acme.internal", b"SELECT 1", [("host", "nope.trino.acme.internal")]
        )
        self.assertEqual(result["kind"], "no_route")

    def test_create_query_executes_trino_and_stores_results(self):
        cluster, user = self.create_running_cluster()
        submitted = []

        def submit(**kwargs):
            submitted.append(kwargs)
            return {
                "id": "20260617_000001_00001_test",
                "columns": [{"name": "nationkey", "type": "integer"}, {"name": "name", "type": "varchar"}],
                "data": [[0, "ALGERIA"]],
            }

        self.app.submit_trino_query = submit

        result = self.app.create_query(
            {
                "cluster_id": cluster["id"],
                "catalog": "tpch",
                "schema": "sf1",
                "sql": "SELECT nationkey, name FROM nation LIMIT 1",
            },
            user,
        )

        self.assertEqual(result["query"]["status"], "Finished")
        self.assertEqual(result["query"]["trino_query_id"], "20260617_000001_00001_test")
        self.assertEqual(result["query"]["columns"][0]["name"], "nationkey")
        self.assertEqual(result["query"]["data"], [[0, "ALGERIA"]])
        self.assertEqual(submitted[0]["coordinator_endpoint"], "10.0.1.10")
        self.assertEqual(submitted[0]["catalog"], "tpch")
        self.assertEqual(submitted[0]["schema_name"], "sf1")

    def test_query_captures_cluster_name_and_survives_deletion(self):
        # Roadmap B2: history must show a real cluster name (captured at run
        # time) instead of "#null" once the cluster is deleted.
        cluster, user = self.create_running_cluster()
        self.app.submit_trino_query = lambda **kwargs: {
            "id": "20260617_000001_00002_test",
            "columns": [{"name": "n", "type": "integer"}],
            "data": [[1]],
        }
        result = self.app.create_query({"cluster_id": cluster["id"], "sql": "SELECT 1"}, user)
        self.assertEqual(result["query"]["cluster_name"], cluster["name"])

        with self.app.conn() as conn:
            conn.execute("DELETE FROM clusters WHERE id = ?", (cluster["id"],))
        history = self.app.list_query_history(user)["queries"]
        self.assertTrue(history)
        self.assertIsNone(history[0]["cluster_id"])
        self.assertEqual(history[0]["cluster_name"], cluster["name"])

    def test_create_query_rejects_multiple_statements(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = lambda **kwargs: submitted.append(kwargs)

        with self.assertRaises(ApiError) as context:
            self.app.create_query({"cluster_id": cluster["id"], "sql": "SELECT 1; SELECT 2"}, user)

        self.assertEqual(context.exception.status, 400)
        self.assertIn("one SQL statement", context.exception.message)
        self.assertEqual(submitted, [])

    def test_create_query_allows_semicolons_inside_literals_and_comments(self):
        cluster, user = self.create_running_cluster()
        submitted = []

        def submit(**kwargs):
            submitted.append(kwargs)
            return {
                "id": "semicolon-query",
                "columns": [{"name": "semi", "type": "varchar"}],
                "data": [[";"]],
            }

        self.app.submit_trino_query = submit

        result = self.app.create_query(
            {
                "cluster_id": cluster["id"],
                "sql": "SELECT ';' AS semi -- still one statement;\n",
            },
            user,
        )

        self.assertEqual(result["query"]["status"], "Finished")
        self.assertEqual(submitted[0]["sql_text"], "SELECT ';' AS semi -- still one statement;")

    def test_create_query_polls_trino_next_uri(self):
        cluster, user = self.create_running_cluster()
        fetched = []

        self.app.submit_trino_query = lambda **kwargs: {
            "id": "query-with-next",
            "nextUri": "http://trino.example/v1/statement/next",
        }

        def fetch(next_uri):
            fetched.append(next_uri)
            return {
                "id": "query-with-next",
                "columns": [{"name": "answer", "type": "integer"}],
                "data": [[42]],
            }

        self.app.fetch_trino_next = fetch

        result = self.app.create_query(
            {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT 42"},
            user,
        )

        self.assertEqual(result["query"]["status"], "Finished")
        self.assertEqual(result["query"]["data"], [[42]])
        self.assertEqual(fetched, ["http://trino.example/v1/statement/next"])

    def test_query_results_truncated_over_max_rows(self):
        cluster, user = self.create_running_cluster()
        self.app.submit_trino_query = lambda **kwargs: {
            "id": "big-query",
            "columns": [{"name": "n", "type": "integer"}],
            "data": [[i] for i in range(1001)],
        }
        result = self.app.create_query(
            {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT n FROM big"},
            user,
        )
        query = result["query"]
        self.assertTrue(query["truncated"])
        self.assertEqual(query["total_row_count"], 1001)
        self.assertEqual(query["row_count"], 1000)
        self.assertEqual(len(query["data"]), 1000)

    def test_query_results_not_truncated_under_max_rows(self):
        cluster, user = self.create_running_cluster()
        self.app.submit_trino_query = lambda **kwargs: {
            "id": "small-query",
            "columns": [{"name": "n", "type": "integer"}],
            "data": [[1], [2], [3]],
        }
        result = self.app.create_query(
            {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT n FROM small"},
            user,
        )
        query = result["query"]
        self.assertFalse(query["truncated"])
        self.assertEqual(query["total_row_count"], 3)
        self.assertEqual(query["row_count"], 3)

    def test_query_truncation_accumulates_across_pages(self):
        cluster, user = self.create_running_cluster()
        self.app.submit_trino_query = lambda **kwargs: {
            "id": "paged-query",
            "columns": [{"name": "n", "type": "integer"}],
            "data": [[i] for i in range(600)],
            "nextUri": "http://trino.example/v1/statement/next",
        }
        self.app.fetch_trino_next = lambda next_uri: {
            "id": "paged-query",
            "data": [[i] for i in range(600, 1200)],
        }
        result = self.app.create_query(
            {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT n FROM paged"},
            user,
        )
        query = result["query"]
        self.assertTrue(query["truncated"])
        self.assertEqual(query["total_row_count"], 1200)
        self.assertEqual(query["row_count"], 1000)

    def test_query_download_retains_more_rows_than_browser_cap(self):
        cluster, user = self.create_running_cluster()
        self.app.submit_trino_query = lambda **kwargs: {
            "id": "download-query",
            "columns": [{"name": "n", "type": "integer"}],
            "data": [[i] for i in range(1200)],
        }

        result = self.app.create_query(
            {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT n FROM big"},
            user,
        )

        query = result["query"]
        self.assertTrue(query["truncated"])
        self.assertFalse(query["download_truncated"])
        self.assertEqual(query["row_count"], 1000)
        self.assertEqual(query["download_row_count"], 1200)
        payload = self.app.query_csv_payload(query["id"], user)
        self.assertEqual(len(payload["rows"]), 1200)

    def _canned_submit(self, submitted, data=None):
        def submit(**kwargs):
            submitted.append(kwargs)
            return {
                "id": f"cache-query-{len(submitted)}",
                "columns": [{"name": "n", "type": "integer"}],
                "data": data if data is not None else [[1], [2]],
            }

        return submit

    def test_query_cache_serves_identical_rerun_without_trino(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        base = {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT n FROM t"}

        first = self.app.create_query(dict(base), user)["query"]
        self.assertFalse(first["cache_hit"])

        second = self.app.create_query(dict(base), user)["query"]

        self.assertEqual(len(submitted), 1)  # the re-run never reached Trino
        self.assertTrue(second["cache_hit"])
        self.assertEqual(second["status"], "Finished")
        self.assertEqual(second["data"], [[1], [2]])
        self.assertEqual(second["cached_from_query_id"], first["id"])
        self.assertEqual(second["result_cached_at"], first["updated_at"])
        self.assertNotEqual(second["id"], first["id"])
        # Both the fresh run and the cache-served run appear in history.
        self.assertEqual(len(self.app.list_query_history(user)["queries"]), 2)

    def test_query_cache_normalizes_whitespace_comments_and_case(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        self.app.create_query(
            {
                "cluster_id": cluster["id"],
                "catalog": "tpch",
                "schema": "sf1",
                "sql": "SELECT n\n  FROM t -- daily refresh",
            },
            user,
        )
        result = self.app.create_query(
            {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "select  n from t"},
            user,
        )["query"]
        self.assertEqual(len(submitted), 1)
        self.assertTrue(result["cache_hit"])

    def test_query_cache_misses_on_different_sql_or_context(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        base = {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT 1"}
        self.app.create_query(dict(base), user)
        self.app.create_query(dict(base, sql="SELECT 2"), user)
        self.app.create_query(dict(base, schema="sf100"), user)
        self.app.create_query(dict(base, catalog="tpcds"), user)
        self.assertEqual(len(submitted), 4)

    def test_query_cache_expires_after_ttl(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        base = {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT 1"}
        first = self.app.create_query(dict(base), user)["query"]
        # Age the source run past the (default 10 minute) TTL.
        with self.app.conn() as conn:
            conn.execute(
                "UPDATE query_runs SET updated_at = '2020-01-01T00:00:00+00:00' WHERE id = ?",
                (first["id"],),
            )
        second = self.app.create_query(dict(base), user)["query"]
        self.assertEqual(len(submitted), 2)
        self.assertFalse(second["cache_hit"])

    def test_query_cache_is_scoped_per_user(self):
        cluster, user = self.create_running_cluster()
        other = self.app.create_user(
            {"username": "analyst", "password": "correct-horse-password", "role": "user"}
        )["user"]
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        base = {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT 1"}
        self.app.create_query(dict(base), user)
        result = self.app.create_query(dict(base), other)["query"]
        # Another user re-running the same SQL executes for real: cache entries
        # never cross user boundaries.
        self.assertEqual(len(submitted), 2)
        self.assertFalse(result["cache_hit"])

    def test_query_cache_fresh_flag_bypasses_cache(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        base = {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT 1"}
        self.app.create_query(dict(base), user)
        result = self.app.create_query(dict(base, fresh=True), user)["query"]
        self.assertEqual(len(submitted), 2)
        self.assertFalse(result["cache_hit"])

    def test_query_cache_disabled_when_ttl_zero(self):
        cluster, user = self.create_running_cluster()
        self.app.set_result_cache_ttl({"result_cache_ttl_minutes": 0}, user)
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        base = {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT 1"}
        self.app.create_query(dict(base), user)
        result = self.app.create_query(dict(base), user)["query"]
        self.assertEqual(len(submitted), 2)
        self.assertFalse(result["cache_hit"])

    def test_query_cache_skips_non_select_statements(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        base = {"cluster_id": cluster["id"], "sql": "SHOW SCHEMAS"}
        self.app.create_query(dict(base), user)
        result = self.app.create_query(dict(base), user)["query"]
        self.assertEqual(len(submitted), 2)
        self.assertFalse(result["cache_hit"])

    def test_query_cache_skips_failed_runs(self):
        cluster, user = self.create_running_cluster()
        submitted = []

        def submit(**kwargs):
            submitted.append(kwargs)
            if len(submitted) == 1:
                return {"id": "failed-query", "error": {"message": "Table not found"}}
            return {"id": "ok-query", "columns": [{"name": "n", "type": "integer"}], "data": [[1]]}

        self.app.submit_trino_query = submit
        base = {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT 1"}
        first = self.app.create_query(dict(base), user)["query"]
        self.assertEqual(first["status"], "Failed")
        second = self.app.create_query(dict(base), user)["query"]
        self.assertEqual(len(submitted), 2)
        self.assertFalse(second["cache_hit"])

    def test_cached_run_csv_reuses_download_buffer(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted, data=[[i] for i in range(1200)])
        base = {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT n FROM big"}
        self.app.create_query(dict(base), user)
        cached = self.app.create_query(dict(base), user)["query"]
        self.assertTrue(cached["cache_hit"])
        self.assertTrue(cached["truncated"])
        self.assertEqual(cached["row_count"], 1000)
        payload = self.app.query_csv_payload(cached["id"], user)
        self.assertEqual(len(payload["rows"]), 1200)
        # CSV export of the cache-served run never re-executed the query.
        self.assertEqual(len(submitted), 1)

    def test_query_cache_hit_on_suspended_cluster_serves_without_resume(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        base = {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT 1"}
        self.app.create_query(dict(base), user)

        with self.app.conn() as conn:
            conn.execute(
                "UPDATE clusters SET status = 'Suspended', auto_suspend_minutes = 15 WHERE id = ?",
                (cluster["id"],),
            )

        def refuse_resume(*args, **kwargs):
            raise AssertionError("A cache hit must not resume the cluster.")

        self.app.start_cluster = refuse_resume
        result = self.app.create_query(dict(base), user)["query"]
        self.assertTrue(result["cache_hit"])
        self.assertEqual(result["status"], "Finished")
        self.assertEqual(len(submitted), 1)
        with self.app.conn() as conn:
            status = conn.execute("SELECT status FROM clusters WHERE id = ?", (cluster["id"],)).fetchone()[0]
        self.assertEqual(status, "Suspended")

    def test_set_result_cache_ttl_validates_and_persists(self):
        with self.assertRaises(ApiError) as context:
            self.app.set_result_cache_ttl({"result_cache_ttl_minutes": 5})
        self.assertEqual(context.exception.status, 409)

        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        self.assertEqual(self.app.result_cache_ttl_minutes(), 10)  # default
        self.assertEqual(
            self.app.set_result_cache_ttl({"result_cache_ttl_minutes": 30})["result_cache_ttl_minutes"], 30
        )
        self.assertEqual(self.app.result_cache_ttl_minutes(), 30)
        self.assertEqual(
            self.app.set_result_cache_ttl({"result_cache_ttl_minutes": 0})["result_cache_ttl_minutes"], 0
        )
        for bad in (-1, 100000, "abc", None):
            with self.assertRaises(ApiError) as context:
                self.app.set_result_cache_ttl({"result_cache_ttl_minutes": bad})
            self.assertEqual(context.exception.status, 400)

    def test_query_cache_hits_across_leading_comments(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        base = {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1"}
        self.app.create_query(dict(base, sql="SELECT 1"), user)
        result = self.app.create_query(dict(base, sql="-- refreshed hourly\nSELECT 1"), user)["query"]
        self.assertEqual(len(submitted), 1)
        self.assertTrue(result["cache_hit"])

    def test_query_cache_not_served_for_disabled_cluster(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        base = {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT 1"}
        self.app.create_query(dict(base), user)

        with self.app.conn() as conn:
            conn.execute("UPDATE clusters SET status = 'Not enabled' WHERE id = ?", (cluster["id"],))

        # Disabling a cluster cuts off its data: the warm cache must not answer.
        with self.assertRaises(ApiError) as context:
            self.app.create_query(dict(base), user)
        self.assertEqual(context.exception.status, 409)
        self.assertEqual(len(submitted), 1)

    def test_query_cache_flushed_by_security_audit_mutations(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        base = {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT 1"}
        self.app.create_query(dict(base), user)

        # Any role/policy/tag/user/catalog/cluster mutation invalidates cached
        # results produced under the old rules.
        self.app.audit(user, "policy.create", "role=analysts catalog=tpch")

        result = self.app.create_query(dict(base), user)["query"]
        self.assertEqual(len(submitted), 2)
        self.assertFalse(result["cache_hit"])

    def test_query_cache_invalidated_by_own_write_statement(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        base = {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1"}
        self.app.create_query(dict(base, sql="SELECT n FROM t"), user)
        # A non-read-only statement from the same user on the same cluster
        # expires their cached entries there.
        self.app.create_query(dict(base, sql="DELETE FROM t WHERE bad = true"), user)
        result = self.app.create_query(dict(base, sql="SELECT n FROM t"), user)["query"]
        self.assertEqual(len(submitted), 3)
        self.assertFalse(result["cache_hit"])

    def test_scheduled_jobs_never_consume_the_cache(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        job = self.app.create_job(
            {
                "name": "watcher",
                "sql": "SELECT count(*) FROM tpch.sf1.nation",
                "cluster_id": cluster["id"],
                "schedule_type": "interval",
                "interval_minutes": 5,
            },
            user,
        )["job"]

        self.app.run_job_now(job["id"], user)
        self.assertEqual(len(submitted), 1)
        # The job's run seeds the cache: an interactive re-run of the same SQL hits.
        interactive = self.app.create_query(
            {"cluster_id": cluster["id"], "sql": "SELECT count(*) FROM tpch.sf1.nation"}, user
        )["query"]
        self.assertTrue(interactive["cache_hit"])
        self.assertEqual(len(submitted), 1)
        # But the job itself always executes for real.
        self.app.run_job_now(job["id"], user)
        self.assertEqual(len(submitted), 2)

    def test_run_readonly_sql_reports_cache_and_supports_fresh(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        base = {"cluster_id": cluster["id"], "sql": "SELECT n FROM t"}
        self.app.create_query(dict(base), user)

        cached = self.app.run_readonly_sql(dict(base), user)
        self.assertTrue(cached["cached"])
        self.assertTrue(cached["result_cached_at"])
        self.assertEqual(len(submitted), 1)

        fresh = self.app.run_readonly_sql(dict(base, fresh=True), user)
        self.assertFalse(fresh["cached"])
        self.assertEqual(len(submitted), 2)

    def test_cached_run_has_no_trino_query_id(self):
        cluster, user = self.create_running_cluster()
        submitted = []
        self.app.submit_trino_query = self._canned_submit(submitted)
        base = {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT 1"}
        first = self.app.create_query(dict(base), user)["query"]
        self.assertTrue(first["trino_query_id"])
        cached = self.app.create_query(dict(base), user)["query"]
        # The cache-served run never reached a coordinator; pointing the query
        # profile at the source's Trino execution would mislabel its stats.
        self.assertEqual(cached["trino_query_id"], "")

    def test_query_tabs_are_user_owned_and_persist_context(self):
        user = self._setup_admin()
        cluster = self.app.create_cluster(
            {
                "name": "tab-cluster",
                "instance_type": "r7i.2xlarge",
                "worker_mode": "fixed",
                "min_workers": 1,
                "max_workers": 1,
                "catalogs": ["system", "tpch"],
            },
            user,
        )["cluster"]

        initial = self.app.list_query_tabs(user)["tabs"]
        self.assertEqual(len(initial), 1)
        self.assertTrue(initial[0]["is_active"])
        self.assertEqual(initial[0]["catalog"], "tpch")

        created = self.app.create_query_tab(
            {
                "name": "scratch.sql",
                "sql": "SHOW CATALOGS;",
                "cluster_id": cluster["id"],
                "catalog": "tpch",
                "schema": "sf1",
                "run_mode": "selected",
                "is_active": True,
            },
            user,
        )["tab"]
        self.assertEqual(created["name"], "scratch.sql")
        self.assertEqual(created["cluster_id"], cluster["id"])
        self.assertEqual(created["run_mode"], "selected")
        self.assertTrue(created["is_active"])

        updated = self.app.update_query_tab(
            created["id"],
            {"name": "renamed.sql", "sql": "SELECT 1;", "schema": "sf10", "run_mode": "all"},
            user,
        )["tab"]
        self.assertEqual(updated["name"], "renamed.sql")
        self.assertEqual(updated["sql"], "SELECT 1;")
        self.assertEqual(updated["schema"], "sf10")
        self.assertEqual(updated["run_mode"], "all")

        tabs = self.app.list_query_tabs(user)["tabs"]
        self.assertEqual(sum(1 for tab in tabs if tab["is_active"]), 1)

    def test_query_tabs_list_by_persisted_position(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.app.conn() as conn:
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())

        first = self.app.list_query_tabs(user)["tabs"][0]
        second = self.app.create_query_tab({"name": "second.sql", "sql": "SELECT 2;"}, user)["tab"]
        third = self.app.create_query_tab({"name": "third.sql", "sql": "SELECT 3;"}, user)["tab"]

        self.app.update_query_tab(third["id"], {"position": 0}, user)
        self.app.update_query_tab(first["id"], {"position": 1}, user)
        self.app.update_query_tab(second["id"], {"position": 2}, user)

        tabs = self.app.list_query_tabs(user)["tabs"]
        self.assertEqual([tab["name"] for tab in tabs], ["third.sql", "query-1.sql", "second.sql"])
        self.assertEqual([tab["position"] for tab in tabs], [0, 1, 2])

    def test_cluster_metadata_queries_information_schema_without_history(self):
        cluster, _ = self.create_running_cluster()
        calls = []

        def fake_submit(**kwargs):
            calls.append(kwargs["sql_text"])
            return {
                "id": "metadata-query",
                "columns": [{"name": "schema_name", "type": "varchar"}],
                "data": [["information_schema"], ["sf1"]],
            }

        self.app.submit_trino_query = fake_submit
        result = self.app.cluster_metadata(cluster["id"], catalog="tpch")

        self.assertEqual([schema["name"] for schema in result["schemas"]], ["information_schema", "sf1"])
        self.assertIn('"tpch".information_schema.schemata', calls[0])
        with self.app.conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM query_runs").fetchone()[0]
        self.assertEqual(count, 0)

    def test_cluster_metadata_escapes_schema_and_table_literals(self):
        cluster, _ = self.create_running_cluster()
        calls = []

        def fake_submit(**kwargs):
            calls.append(kwargs["sql_text"])
            return {
                "id": "metadata-query",
                "columns": [{"name": "column_name", "type": "varchar"}],
                "data": [["orderkey", "bigint", "NO", None]],
            }

        self.app.submit_trino_query = fake_submit
        result = self.app.cluster_metadata(cluster["id"], catalog="tpch", schema_name="sf'1", table="orders")

        self.assertEqual(result["columns"][0]["name"], "orderkey")
        self.assertIn("table_schema = 'sf''1'", calls[0])
        self.assertIn("table_name = 'orders'", calls[0])

    def test_deleting_last_query_tab_recreates_default(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.app.conn() as conn:
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())

        tab = self.app.list_query_tabs(user)["tabs"][0]
        result = self.app.delete_query_tab(tab["id"], user)

        self.assertTrue(result["deleted"])
        self.assertEqual(len(result["tabs"]), 1)
        self.assertEqual(result["tabs"][0]["name"], "query-1.sql")
        self.assertTrue(result["tabs"][0]["is_active"])

    def test_saved_queries_are_user_owned_and_editable(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.app.conn() as conn:
            admin = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        other = self.app.create_user({"username": "analyst", "password": "correct-horse-password", "role": "user"})["user"]

        created = self.app.create_saved_query(
            {"name": "Nation count", "sql": "SELECT count(*) FROM tpch.sf1.nation", "catalog": "tpch", "schema": "sf1"},
            admin,
        )["query"]
        self.assertEqual(created["name"], "Nation count")
        self.assertEqual(created["catalog"], "tpch")

        updated = self.app.update_saved_query(created["id"], {"name": "Nation count v2", "sql": "SELECT 1"}, admin)[
            "query"
        ]
        self.assertEqual(updated["name"], "Nation count v2")
        self.assertEqual(updated["sql"], "SELECT 1")

        self.assertEqual(len(self.app.list_saved_queries(admin)["queries"]), 1)
        self.assertEqual(self.app.list_saved_queries(other)["queries"], [])
        with self.assertRaises(ApiError) as context:
            self.app.update_saved_query(created["id"], {"name": "stolen"}, other)
        self.assertEqual(context.exception.status, 404)

        deleted = self.app.delete_saved_query(created["id"], admin)
        self.assertTrue(deleted["deleted"])
        self.assertEqual(self.app.list_saved_queries(admin)["queries"], [])

    def test_notebooks_are_user_owned_and_editable(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.app.conn() as conn:
            admin = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        other = self.app.create_user(
            {"username": "analyst", "password": "correct-horse-password", "role": "user"}
        )["user"]

        created = self.app.create_notebook(
            {"name": "Sales exploration", "catalog": "tpch", "schema": "sf1"}, admin
        )["notebook"]
        self.assertEqual(created["name"], "Sales exploration")
        self.assertEqual(created["catalog"], "tpch")
        # New notebooks are seeded with one empty cell so they open runnable.
        self.assertEqual(len(self.app.list_notebook_cells(created["id"], admin)["cells"]), 1)

        updated = self.app.update_notebook(created["id"], {"name": "Sales exploration v2"}, admin)["notebook"]
        self.assertEqual(updated["name"], "Sales exploration v2")

        self.assertEqual(len(self.app.list_notebooks(admin)["notebooks"]), 1)
        self.assertEqual(self.app.list_notebooks(other)["notebooks"], [])
        with self.assertRaises(ApiError) as context:
            self.app.update_notebook(created["id"], {"name": "stolen"}, other)
        self.assertEqual(context.exception.status, 404)
        with self.assertRaises(ApiError) as context:
            self.app.list_notebook_cells(created["id"], other)
        self.assertEqual(context.exception.status, 404)

        deleted = self.app.delete_notebook(created["id"], admin)
        self.assertTrue(deleted["deleted"])
        self.assertEqual(self.app.list_notebooks(admin)["notebooks"], [])

    def test_notebook_list_reports_cell_counts(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.app.conn() as conn:
            admin = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        notebook = self.app.create_notebook({"name": "Counted"}, admin)["notebook"]
        self.app.create_notebook_cell(notebook["id"], {"sql": "SELECT 1"}, admin)
        listed = self.app.list_notebooks(admin)["notebooks"][0]
        # One seeded cell plus the explicit one.
        self.assertEqual(listed["cell_count"], 2)

    def test_notebook_cell_last_query_id_round_trips_and_is_validated(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.app.conn() as conn:
            admin = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        other = self.app.create_user(
            {"username": "analyst", "password": "correct-horse-password", "role": "user"}
        )["user"]
        notebook = self.app.create_notebook({"name": "Restorable"}, admin)["notebook"]
        cell = self.app.list_notebook_cells(notebook["id"], admin)["cells"][0]
        self.assertIsNone(cell["last_query_id"])

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.app.conn() as conn:
            mine = conn.execute(
                """
                INSERT INTO query_runs
                  (user_id, cluster_id, sql_text, status, elapsed_ms, row_count, created_at, updated_at)
                VALUES (?, NULL, 'SELECT 1', 'Finished', 0, 0, ?, ?)
                """,
                (admin["id"], now, now),
            ).lastrowid
            theirs = conn.execute(
                """
                INSERT INTO query_runs
                  (user_id, cluster_id, sql_text, status, elapsed_ms, row_count, created_at, updated_at)
                VALUES (?, NULL, 'SELECT 2', 'Finished', 0, 0, ?, ?)
                """,
                (other["id"], now, now),
            ).lastrowid

        updated = self.app.update_notebook_cell(
            notebook["id"], cell["id"], {"last_query_id": mine}, admin
        )["cell"]
        self.assertEqual(updated["last_query_id"], mine)

        cleared = self.app.update_notebook_cell(
            notebook["id"], cell["id"], {"last_query_id": None}, admin
        )["cell"]
        self.assertIsNone(cleared["last_query_id"])

        # Another user's query and a nonexistent query are both rejected.
        with self.assertRaises(ApiError) as context:
            self.app.update_notebook_cell(notebook["id"], cell["id"], {"last_query_id": theirs}, admin)
        self.assertEqual(context.exception.status, 400)
        with self.assertRaises(ApiError) as context:
            self.app.update_notebook_cell(notebook["id"], cell["id"], {"last_query_id": 999999}, admin)
        self.assertEqual(context.exception.status, 400)

    def test_notebook_name_length_is_validated(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.app.conn() as conn:
            admin = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        with self.assertRaises(ApiError) as context:
            self.app.create_notebook({"name": "x" * 121}, admin)
        self.assertEqual(context.exception.status, 400)

    def test_notebook_cells_crud_and_ordering(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.app.conn() as conn:
            admin = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        notebook = self.app.create_notebook({"name": "Analysis"}, admin)["notebook"]

        first = self.app.list_notebook_cells(notebook["id"], admin)["cells"][0]
        second = self.app.create_notebook_cell(
            notebook["id"], {"sql": "SELECT 2", "catalog": "tpch", "schema": "sf1"}, admin
        )["cell"]
        third = self.app.create_notebook_cell(
            notebook["id"],
            {"sql": "SELECT 3", "view_pref": "chart", "chart_config": {"type": "bar", "x": "a", "y": "b"}},
            admin,
        )["cell"]

        # Per-cell context overrides and chart config round-trip through JSON.
        self.assertEqual(second["catalog"], "tpch")
        self.assertEqual(third["view_pref"], "chart")
        self.assertEqual(third["chart_config"], {"type": "bar", "x": "a", "y": "b"})

        self.app.update_notebook_cell(notebook["id"], third["id"], {"position": 0}, admin)
        self.app.update_notebook_cell(notebook["id"], first["id"], {"position": 1}, admin)
        self.app.update_notebook_cell(notebook["id"], second["id"], {"position": 2}, admin)

        cells = self.app.list_notebook_cells(notebook["id"], admin)["cells"]
        self.assertEqual([cell["id"] for cell in cells], [third["id"], first["id"], second["id"]])
        self.assertEqual([cell["position"] for cell in cells], [0, 1, 2])

        deleted = self.app.delete_notebook_cell(notebook["id"], second["id"], admin)
        self.assertTrue(deleted["deleted"])
        self.assertEqual(len(self.app.list_notebook_cells(notebook["id"], admin)["cells"]), 2)

    def test_deleting_notebook_cascades_cells(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.app.conn() as conn:
            admin = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        notebook = self.app.create_notebook({"name": "Doomed"}, admin)["notebook"]
        self.app.create_notebook_cell(notebook["id"], {"sql": "SELECT 1"}, admin)

        self.app.delete_notebook(notebook["id"], admin)
        with self.app.conn() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM notebook_cells WHERE notebook_id = ?", (notebook["id"],)
            ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_deleting_cluster_nulls_notebook_references(self):
        cluster, user = self.create_running_cluster()
        notebook = self.app.create_notebook({"name": "Bound", "cluster_id": cluster["id"]}, user)["notebook"]
        cell = self.app.create_notebook_cell(
            notebook["id"], {"sql": "SELECT 1", "cluster_id": cluster["id"]}, user
        )["cell"]
        self.assertEqual(notebook["cluster_id"], cluster["id"])
        self.assertEqual(cell["cluster_id"], cluster["id"])

        with self.app.conn() as conn:
            conn.execute("DELETE FROM clusters WHERE id = ?", (cluster["id"],))

        refreshed = self.app.list_notebooks(user)["notebooks"][0]
        refreshed_cell = self.app.list_notebook_cells(notebook["id"], user)["cells"][1]
        self.assertIsNone(refreshed["cluster_id"])
        self.assertIsNone(refreshed_cell["cluster_id"])

    def test_query_result_truncated_by_byte_cap(self):
        cluster, user = self.create_running_cluster()
        now = "2026-01-01T00:00:00+00:00"
        with self.app.conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO query_runs (user_id, cluster_id, sql_text, status, created_at, updated_at)
                VALUES (?, ?, 'SELECT big_payload', 'Queued', ?, ?)
                """,
                (user["id"], cluster["id"], now, now),
            )
            row = dict(conn.execute("SELECT * FROM query_runs WHERE id = ?", (cursor.lastrowid,)).fetchone())
            updated = self.app.apply_trino_response(
                conn,
                row,
                {
                    "id": "big-payload",
                    "columns": [{"name": "payload", "type": "varchar"}],
                    "data": [["x" * 100], ["y" * 100]],
                },
                max_bytes=80,
            )

        self.assertTrue(updated["truncated"])
        self.assertLess(updated["row_count"], updated["total_row_count"])
        self.assertLessEqual(updated["result_bytes"], 80)

    def test_cancel_running_query_calls_trino_delete(self):
        cluster, user = self.create_running_cluster()
        cancelled = []

        self.app.submit_trino_query = lambda **kwargs: {
            "id": "query-to-cancel",
            "nextUri": "http://trino.example/v1/statement/next",
        }
        self.app.fetch_trino_next = lambda next_uri: {
            "id": "query-to-cancel",
            "nextUri": next_uri,
        }

        def cancel(next_uri):
            cancelled.append(next_uri)
            return {"cancelled_remote": True, "status": 204}

        self.app.cancel_trino_query = cancel

        created = self.app.create_query(
            {"cluster_id": cluster["id"], "catalog": "tpch", "schema": "sf1", "sql": "SELECT * FROM nation"},
            user,
        )
        self.assertEqual(created["query"]["status"], "Running")

        result = self.app.cancel_query(created["query"]["id"], user)

        self.assertEqual(result["query"]["status"], "Cancelled")
        self.assertEqual(cancelled, ["http://trino.example/v1/statement/next"])

    def test_create_query_requires_running_cluster(self):
        cluster = self.create_test_cluster()
        with self.app.conn() as conn:
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())

        with self.assertRaises(ApiError) as context:
            self.app.create_query({"cluster_id": cluster["id"], "sql": "SELECT 1"}, user)

        self.assertEqual(context.exception.status, 409)
        self.assertIn("must be Running", context.exception.message)

    def test_provisioning_failure_surfaces_aws_error(self):
        # A botocore-style AWS error is actionable, so it reaches the admin.
        cluster = self.create_test_cluster()

        class FakeClientError(Exception):
            pass

        FakeClientError.__module__ = "botocore.exceptions"

        def boom_aws(**kwargs):
            raise FakeClientError("An error occurred (InsufficientInstanceCapacity) when calling RunInstances")

        self.app.aws.launch_coordinator_instance = boom_aws
        with self.assertRaises(ApiError) as ctx:
            self.app.start_cluster(cluster["id"], {"confirm_billable": True})
        self.assertEqual(ctx.exception.status, 500)
        self.assertIn("InsufficientInstanceCapacity", ctx.exception.message)
        with self.app.conn() as conn:
            status = conn.execute("SELECT status FROM clusters WHERE id = ?", (cluster["id"],)).fetchone()["status"]
            events = conn.execute(
                "SELECT COUNT(*) FROM cluster_events WHERE cluster_id = ? AND event_type = 'provisioning_failed'",
                (cluster["id"],),
            ).fetchone()[0]
        self.assertEqual(status, "Failed")
        self.assertEqual(events, 1)

    def test_provisioning_failure_hides_unexpected_internal_error(self):
        cluster = self.create_test_cluster()

        def boom(**kwargs):
            raise RuntimeError("secret internal detail from /opt/app/guts")

        self.app.aws.launch_coordinator_instance = boom
        with self.assertRaises(ApiError) as ctx:
            self.app.start_cluster(cluster["id"], {"confirm_billable": True})
        self.assertEqual(ctx.exception.status, 500)
        self.assertNotIn("secret internal detail", ctx.exception.message)
        self.assertIn("unexpected internal error", ctx.exception.message)
        # The full detail is still recorded server-side in the cluster event.
        with self.app.conn() as conn:
            event = conn.execute(
                """
                SELECT message FROM cluster_events
                WHERE cluster_id = ? AND event_type = 'provisioning_failed'
                """,
                (cluster["id"],),
            ).fetchone()["message"]
        self.assertIn("secret internal detail", event)

    def test_check_catalog_without_running_attached_cluster_validates_config(self):
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        with self.app.conn() as conn:
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())

        result = self.app.check_catalog(
            {
                "name": "analytics_s3",
                "type": "s3_glue",
                "config": {
                    "glue_region": "us-east-2",
                    "warehouse": "s3://company-lakehouse/warehouse",
                    "access_mode": "read_only",
                },
            },
            user,
        )

        self.assertTrue(result["ok"])
        self.assertFalse(result["live_check"]["checked"])
        self.assertEqual(result["config"]["warehouse"], "s3://company-lakehouse/warehouse/")

    def create_test_cluster(self, *, auto_suspend_minutes=None):
        self.app.complete_setup(
            {
                "username": "admin",
                "password": "correct-horse-password",
                "allowed_instance_types": ["r7i.2xlarge"],
            }
        )
        with self.app.conn() as conn:
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
        payload = {
            "name": "test-cluster",
            "instance_type": "r7i.2xlarge",
            "worker_mode": "autoscale",
            "min_workers": 1,
            "max_workers": 3,
            "catalogs": ["system", "tpch"],
        }
        if auto_suspend_minutes is not None:
            payload["auto_suspend_minutes"] = auto_suspend_minutes
        result = self.app.create_cluster(payload, user)
        return result["cluster"]

    def create_running_cluster(self):
        cluster = self.create_test_cluster()
        with self.app.conn() as conn:
            conn.execute("UPDATE clusters SET status = 'Running' WHERE id = ?", (cluster["id"],))
            conn.execute(
                """
                INSERT INTO provider_resources (cluster_id, resource_type, resource_id, region, metadata_json, created_at)
                VALUES (?, 'coordinator_instance', 'i-coordinator', 'us-east-2', ?, '2026-01-01T00:00:00+00:00')
                """,
                (cluster["id"], json.dumps({"private_ip_address": "10.0.1.10"})),
            )
            user = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster["id"],)).fetchone()
            updated_cluster = self.app.public_cluster(row)
        return updated_cluster, user

    def create_running_autoscale_cluster(self):
        cluster = self.create_test_cluster()
        self.app.start_cluster(cluster["id"], {"confirm_billable": True})
        result = self.app.refresh_cluster_health(cluster["id"])
        return result["cluster"]

    def create_running_auto_suspend_cluster(self, *, minutes):
        cluster = self.create_test_cluster(auto_suspend_minutes=minutes)
        self.app.start_cluster(cluster["id"], {"confirm_billable": True})
        result = self.app.refresh_cluster_health(cluster["id"])
        return result["cluster"]


class AwsBootstrapTests(unittest.TestCase):
    def test_trino_user_data_installs_and_configures_built_in_catalogs(self):
        aws = AwsInspector(region="us-east-2")
        script = aws.trino_user_data(
            cluster={"name": "test-cluster", "catalogs": ["system", "tpch", "tpcds"]},
            node_role="worker",
            region="us-east-2",
            coordinator_uri="http://10.0.1.10:8080",
        )

        self.assertIn(f'TRINO_VERSION="{TRINO_VERSION}"', script)
        self.assertIn("apt-get install -y temurin-25-jdk", script)
        self.assertIn("https://github.com/trinodb/trino/releases/download/${TRINO_VERSION}/trino-server-${TRINO_VERSION}.tar.gz", script)
        self.assertIn("coordinator=false", script)
        self.assertIn("discovery.uri=http://10.0.1.10:8080", script)
        self.assertIn("cat >/etc/trino/catalog/tpch.properties", script)
        self.assertIn("connector.name=tpch", script)
        self.assertIn("cat >/etc/trino/catalog/tpcds.properties", script)
        self.assertIn("connector.name=tpcds", script)
        self.assertIn("The system catalog is built into Trino", script)
        self.assertNotIn("/etc/trino/catalog/system.properties", script)
        self.assertIn("systemctl enable --now trino", script)

    def test_trino_user_data_pins_selected_version(self):
        aws = AwsInspector(region="us-east-2")
        script = aws.trino_user_data(
            cluster={"name": "test-cluster", "catalogs": ["system"], "trino_version": "480"},
            node_role="coordinator",
            region="us-east-2",
        )
        # The pinned version drives the install dir and download URL.
        self.assertIn('TRINO_VERSION="480"', script)
        self.assertIn("/opt/trino-server-480", script)

    def test_resolve_trino_version_falls_back_for_missing_or_bad_values(self):
        from trinohub.aws_checks import resolve_trino_version

        self.assertEqual(resolve_trino_version({"trino_version": "479"}), "479")
        self.assertEqual(resolve_trino_version({}), TRINO_VERSION)
        self.assertEqual(resolve_trino_version({"trino_version": ""}), TRINO_VERSION)
        # Non-numeric input is refused (never interpolated into the URL/shell).
        self.assertEqual(resolve_trino_version({"trino_version": "480; rm -rf /"}), TRINO_VERSION)

    def test_trino_user_data_configures_s3_glue_iceberg_catalog(self):
        aws = AwsInspector(region="us-east-2")
        script = aws.trino_user_data(
            cluster={
                "name": "test-cluster",
                "catalogs": ["system", "analytics_s3"],
                "catalog_configs": [
                    {
                        "name": "analytics_s3",
                        "type": "s3_glue",
                        "enabled": True,
                        "config": {
                            "glue_region": "us-east-2",
                            "s3_region": "us-east-2",
                            "warehouse": "s3://company-lakehouse/warehouse/",
                            "file_format": "PARQUET",
                            "access_mode": "read_only",
                        },
                    }
                ],
            },
            node_role="worker",
            region="us-east-2",
            coordinator_uri="http://10.0.1.10:8080",
        )

        self.assertIn("cat >/etc/trino/catalog/analytics_s3.properties", script)
        self.assertIn("connector.name=iceberg", script)
        self.assertIn("iceberg.catalog.type=glue", script)
        self.assertIn("hive.metastore.glue.region=us-east-2", script)
        self.assertIn("hive.metastore.glue.default-warehouse-dir=s3://company-lakehouse/warehouse/", script)
        self.assertIn("fs.s3.enabled=true", script)
        self.assertIn("s3.region=us-east-2", script)
        self.assertIn("iceberg.file-format=PARQUET", script)
        self.assertIn("iceberg.security=READ_ONLY", script)

    def test_trino_user_data_configures_delta_and_hive_glue_catalogs(self):
        # Delta Lake and Hive share the S3/Glue IAM path but render a different
        # connector.name, the Hive-style metastore selector, and their own
        # read-only security key. No credential is ever involved.
        cases = {
            "delta_glue": {
                "connector": "connector.name=delta_lake",
                "security": "delta.security=READ_ONLY",
            },
            "hive_glue": {
                "connector": "connector.name=hive",
                "security": "hive.security=read-only",
                "extra": "hive.storage-format=PARQUET",
            },
        }
        for catalog_type, expected in cases.items():
            with self.subTest(catalog_type=catalog_type):
                aws = AwsInspector(region="us-east-2")
                script = aws.trino_user_data(
                    cluster={
                        "name": "test-cluster",
                        "catalogs": ["system", "lake"],
                        "catalog_configs": [
                            {
                                "name": "lake",
                                "type": catalog_type,
                                "enabled": True,
                                "config": {
                                    "glue_region": "us-east-2",
                                    "s3_region": "us-east-2",
                                    "warehouse": "s3://company-lakehouse/warehouse/",
                                    "file_format": "PARQUET",
                                    "access_mode": "read_only",
                                },
                            }
                        ],
                    },
                    node_role="worker",
                    region="us-east-2",
                    coordinator_uri="http://10.0.1.10:8080",
                )
                self.assertIn("cat >/etc/trino/catalog/lake.properties", script)
                self.assertIn(expected["connector"], script)
                self.assertIn("hive.metastore=glue", script)
                self.assertIn("hive.metastore.glue.region=us-east-2", script)
                self.assertIn(
                    "hive.metastore.glue.default-warehouse-dir=s3://company-lakehouse/warehouse/", script
                )
                self.assertIn("fs.s3.enabled=true", script)
                self.assertIn("s3.region=us-east-2", script)
                self.assertIn(expected["security"], script)
                if "extra" in expected:
                    self.assertIn(expected["extra"], script)
                # These are Iceberg-only keys and must not leak into Delta/Hive.
                self.assertNotIn("iceberg.catalog.type=glue", script)
                self.assertNotIn("connector.name=iceberg", script)

    def test_trino_user_data_configures_hudi_glue_catalog(self):
        # Hudi shares the Glue metastore block but is query-only in Trino: no
        # security key, no storage-format, no writes.
        aws = AwsInspector(region="us-east-2")
        script = aws.trino_user_data(
            cluster={
                "name": "test-cluster",
                "catalogs": ["system", "lake"],
                "catalog_configs": [
                    {
                        "name": "lake",
                        "type": "hudi_glue",
                        "enabled": True,
                        "config": {
                            "glue_region": "us-east-2",
                            "s3_region": "us-east-2",
                            "warehouse": "s3://company-lakehouse/warehouse/",
                            "file_format": "PARQUET",
                            "access_mode": "read_only",
                        },
                    }
                ],
            },
            node_role="worker",
            region="us-east-2",
            coordinator_uri="http://10.0.1.10:8080",
        )
        self.assertIn("connector.name=hudi", script)
        self.assertIn("hive.metastore=glue", script)
        self.assertIn("hive.metastore.glue.default-warehouse-dir=s3://company-lakehouse/warehouse/", script)
        self.assertIn("fs.s3.enabled=true", script)
        # Hudi is query-only: none of the write-oriented keys should appear.
        self.assertNotIn("hudi.security", script)
        self.assertNotIn("hive.security", script)
        self.assertNotIn("hive.storage-format", script)

    def test_trino_user_data_fetches_signed_node_config_when_available(self):
        aws = AwsInspector(region="us-east-2")
        script = aws.trino_user_data(
            cluster={"name": "test-cluster", "catalogs": ["system", "tpch"]},
            node_role="worker",
            region="us-east-2",
            instance_type="m7i.large",
            control_plane_uri="http://10.0.9.9:8000",
            cluster_id=7,
            bootstrap_token="node-token",
        )

        self.assertIn("/api/node-config/7?role=worker&token=node-token&instance_type=m7i.large", script)
        self.assertIn("curl --fail --location --retry 12", script)
        self.assertNotIn("cat >/etc/trino/catalog/tpch.properties", script)

    def test_credentialed_catalog_never_embedded_in_user_data(self):
        aws = AwsInspector(region="us-east-2")
        cluster = {
            "name": "test-cluster",
            "catalogs": ["system", "warehouse_pg"],
            "catalog_configs": [
                {
                    "name": "warehouse_pg",
                    "type": "postgresql",
                    "enabled": True,
                    "config": {
                        "connector_name": "postgresql",
                        "connection_url": "jdbc:postgresql://db.internal.example.com:5432/warehouse",
                        "connection_user": "analyst",
                        "password_secret_ref": "arn:aws:secretsmanager:us-east-2:1:secret:trinohub/catalog/warehouse_pg",
                    },
                }
            ],
        }
        # Signed path: user-data only curls the node-config endpoint — no catalog inlined.
        signed = aws.trino_user_data(
            cluster=cluster,
            node_role="worker",
            region="us-east-2",
            control_plane_uri="http://10.0.9.9:8000",
            cluster_id=7,
            bootstrap_token="node-token",
        )
        self.assertIn("/api/node-config/7", signed)
        self.assertNotIn("warehouse_pg.properties", signed)
        # Embedded path (no control plane URI) must refuse to inline a credentialed catalog,
        # so a password can never land in EC2 user-data.
        with self.assertRaises(RuntimeError):
            aws.trino_user_data(cluster=cluster, node_role="worker", region="us-east-2")

    def test_jdbc_catalog_properties_render_resolved_password(self):
        aws = AwsInspector(region="us-east-2")
        props = aws.jdbc_catalog_properties(
            {
                "name": "warehouse_pg",
                "config": {
                    "connector_name": "postgresql",
                    "connection_url": "jdbc:postgresql://db.internal.example.com:5432/warehouse",
                    "connection_user": "analyst",
                    "password_secret_ref": "arn:secret",
                },
            },
            secret_resolver=lambda ref: "resolved-pw",
        )
        self.assertIn("connector.name=postgresql", props)
        self.assertIn("connection-url=jdbc:postgresql://db.internal.example.com:5432/warehouse", props)
        self.assertIn("connection-user=analyst", props)
        self.assertIn("connection-password=resolved-pw", props)

    def test_trino_user_data_scales_query_memory_with_instance_size(self):
        aws = AwsInspector(region="us-east-2")
        cluster = {"name": "test-cluster", "catalogs": ["system"]}
        small = aws.trino_user_data(
            cluster=cluster, node_role="coordinator", region="us-east-2", instance_type="m7i.large"
        )
        large = aws.trino_user_data(
            cluster=cluster, node_role="coordinator", region="us-east-2", instance_type="m7i.2xlarge"
        )
        # 8 GiB instance: heap 5 GiB (pinned via -Xmx), headroom 1, per-node 3 (1 GiB slack).
        self.assertIn("-Xmx5G", small)
        self.assertIn("query.max-memory-per-node=3GB", small)
        # 32 GiB instance: heap 22 GiB, headroom 6, per-node 15 (1 GiB slack).
        self.assertIn("-Xmx22G", large)
        self.assertIn("query.max-memory-per-node=15GB", large)
        self.assertIn("memory.heap-headroom-per-node=6GB", large)
        # The heap is pinned explicitly, not derived from available RAM at boot.
        self.assertNotIn("MaxRAMPercentage", large)

    def test_trino_memory_settings_respect_heap_budget(self):
        from trinohub.aws_checks import trino_memory_settings

        for instance_type in ("m7i.large", "m7i.xlarge", "m7i.2xlarge"):
            settings = trino_memory_settings(instance_type)
            # query.max-memory-per-node + heap-headroom must stay STRICTLY below the
            # pinned heap, so Trino's startup memory check passes with margin.
            self.assertLess(
                settings["query_max_memory_per_node_gb"] + settings["heap_headroom_gb"],
                settings["heap_gb"],
            )
            # -Xmx must equal the heap the settings are sized against.
            self.assertLessEqual(settings["heap_gb"], int(settings["ram_gb"] * 0.7))

    def test_default_key_name_is_none_without_env(self):
        # No hardcoded "key1": a clean account attaches no SSH key by default.
        os.environ.pop("TRINOHUB_SSH_KEY_NAME", None)
        aws = AwsInspector(region="us-east-2")
        described = []
        aws.clients = lambda region=None: {
            "ec2": type("E", (), {"describe_key_pairs": lambda self, **kw: described.append(kw) or {"KeyPairs": []}})()
        }
        self.assertIsNone(aws.default_key_name("us-east-2"))
        self.assertEqual(described, [])  # never even queried AWS

    def test_default_key_name_uses_configured_key_when_present(self):
        os.environ["TRINOHUB_SSH_KEY_NAME"] = "ops-breakglass"
        self.addCleanup(os.environ.pop, "TRINOHUB_SSH_KEY_NAME", None)
        aws = AwsInspector(region="us-east-2")
        aws.clients = lambda region=None: {
            "ec2": type(
                "E", (), {"describe_key_pairs": lambda self, **kw: {"KeyPairs": [{"KeyName": "ops-breakglass"}]}}
            )()
        }
        self.assertEqual(aws.default_key_name("us-east-2"), "ops-breakglass")

    def test_default_key_name_none_when_configured_key_missing(self):
        os.environ["TRINOHUB_SSH_KEY_NAME"] = "does-not-exist"
        self.addCleanup(os.environ.pop, "TRINOHUB_SSH_KEY_NAME", None)
        aws = AwsInspector(region="us-east-2")
        aws.clients = lambda region=None: {
            "ec2": type("E", (), {"describe_key_pairs": lambda self, **kw: {"KeyPairs": []}})()
        }
        self.assertIsNone(aws.default_key_name("us-east-2"))


class TrinoClusterStatsTests(unittest.TestCase):
    """trino_cluster_stats parses /v1/query (Trino 481 has no /v1/cluster)."""

    class _FakeResp:
        def __init__(self, body):
            self._body = body.encode("utf-8")

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def test_counts_running_and_queued_from_query_list(self):
        aws = AwsInspector(region="us-east-2")
        captured = []
        query_payload = json.dumps([
            {"state": "RUNNING"}, {"state": "RUNNING"},
            {"state": "QUEUED"},
            {"state": "FINISHED"}, {"state": "FAILED"},
        ])

        def fake_urlopen(request, timeout=None):
            captured.append((request.full_url, request.get_header("X-trino-user")))
            if request.full_url.endswith("/v1/query"):
                return self._FakeResp(query_payload)
            if request.full_url.endswith("/v1/node"):
                return self._FakeResp(json.dumps([{"nodeId": "coordinator"}, {"nodeId": "worker-1"}]))
            if request.full_url.endswith("/v1/memory"):
                return self._FakeResp(json.dumps({"pools": {"general": {"reservedBytes": 123, "maxBytes": 456}}}))
            return self._FakeResp("{}")

        with unittest.mock.patch("trinohub.aws_checks.urllib.request.urlopen", fake_urlopen):
            stats = aws.trino_cluster_stats(coordinator_endpoint="10.0.0.5")

        self.assertTrue(stats["ok"])
        query_calls = [call for call in captured if call[0].endswith("/v1/query")]
        self.assertEqual(len(query_calls), 1)
        self.assertEqual(query_calls[0][1], "trinohub")  # header required or Trino 401s
        self.assertEqual(stats["running_queries"], 2)
        self.assertEqual(stats["queued_queries"], 1)  # FINISHED/FAILED not counted
        self.assertEqual(stats["active_workers"], 2)
        self.assertEqual(stats["reserved_memory"], 123)
        self.assertEqual(stats["memory"]["max_bytes"], 456)

    def test_idle_cluster_reports_zero(self):
        aws = AwsInspector(region="us-east-2")
        with unittest.mock.patch(
            "trinohub.aws_checks.urllib.request.urlopen",
            lambda request, timeout=None: self._FakeResp("[]"),
        ):
            stats = aws.trino_cluster_stats(coordinator_endpoint="10.0.0.5")
        self.assertTrue(stats["ok"])
        self.assertEqual(stats["running_queries"], 0)
        self.assertEqual(stats["queued_queries"], 0)

    def test_unreachable_endpoint_reports_not_ok(self):
        aws = AwsInspector(region="us-east-2")

        def boom(request, timeout=None):
            raise OSError("connection refused")

        with unittest.mock.patch("trinohub.aws_checks.urllib.request.urlopen", boom):
            stats = aws.trino_cluster_stats(coordinator_endpoint="10.0.0.5")
        self.assertFalse(stats["ok"])
        self.assertEqual(stats["state"], "unreachable")


class AsgRecreateRaceTests(unittest.TestCase):
    """The worker ASG launch waits out a still-deleting same-named ASG (resume race)."""

    def _inspector_with_asg(self, asg_client):
        aws = AwsInspector(region="us-east-2")
        aws.clients = lambda region=None: {"autoscaling": asg_client}
        return aws

    @staticmethod
    def _already_exists():
        from botocore.exceptions import ClientError

        return ClientError(
            {"Error": {"Code": "AlreadyExists", "Message": "pending delete"}},
            "CreateAutoScalingGroup",
        )

    def test_create_retries_until_pending_delete_clears(self):
        calls = {"n": 0}
        outer = self

        class FakeAsg:
            def create_auto_scaling_group(self, **kwargs):
                calls["n"] += 1
                if calls["n"] < 3:  # AlreadyExists on the first two attempts
                    raise outer._already_exists()
                return {}

        aws = self._inspector_with_asg(FakeAsg())
        with unittest.mock.patch("trinohub.aws_checks.time.sleep") as sleep:
            result = aws.create_worker_auto_scaling_group(
                region="us-east-2",
                subnet_ids=["subnet-1"],
                cluster={"name": "demo", "min_workers": 1, "max_workers": 2},
                launch_template_id="lt-1",
            )
        self.assertEqual(result["auto_scaling_group_name"], "trinohub-demo-workers")
        self.assertEqual(calls["n"], 3)
        self.assertEqual(sleep.call_count, 2)  # waited between the two retries

    def test_create_raises_other_errors_immediately(self):
        from botocore.exceptions import ClientError

        class FakeAsg:
            def create_auto_scaling_group(self, **kwargs):
                raise ClientError(
                    {"Error": {"Code": "ValidationError", "Message": "bad subnet"}},
                    "CreateAutoScalingGroup",
                )

        aws = self._inspector_with_asg(FakeAsg())
        with unittest.mock.patch("trinohub.aws_checks.time.sleep"):
            with self.assertRaises(ClientError):
                aws.create_worker_auto_scaling_group(
                    region="us-east-2",
                    subnet_ids=["subnet-1"],
                    cluster={"name": "demo", "min_workers": 1, "max_workers": 2},
                    launch_template_id="lt-1",
                )


class FakeEc2Client:
    def __init__(self, existing_groups=None):
        self._existing = existing_groups or []
        self.authorize_calls = []
        self.created_group = None

    def describe_security_groups(self, **kwargs):
        return {"SecurityGroups": self._existing}

    def create_security_group(self, **kwargs):
        self.created_group = kwargs
        return {"GroupId": "sg-managed-new"}

    def create_tags(self, **kwargs):
        return {}

    def authorize_security_group_ingress(self, **kwargs):
        self.authorize_calls.append(kwargs)
        return {}


class ControlPlaneIngressTests(unittest.TestCase):
    def setUp(self):
        self.inspector = AwsInspector(region="us-east-2")
        self.ec2 = FakeEc2Client()
        self.inspector.clients = lambda region=None: {"ec2": self.ec2}

    def test_ingress_uses_control_plane_security_group(self):
        self.inspector.control_plane_security_group_ids = lambda: ["sg-control"]
        self.inspector.control_plane_private_ip = lambda: "10.0.9.9"

        result = self.inspector.ensure_managed_security_group(
            region="us-east-2", vpc_id="vpc-test", cluster_name="demo"
        )

        ingress = result["control_plane_ingress"]
        self.assertTrue(ingress["authorized"])
        self.assertEqual(ingress["via"], "security_group")
        # The self-referencing rule plus a TCP 8080 rule from the control-plane SG.
        port_rules = [
            permission
            for call in self.ec2.authorize_calls
            for permission in call["IpPermissions"]
            if permission.get("FromPort") == TRINO_HTTP_PORT
        ]
        self.assertEqual(len(port_rules), 1)
        self.assertEqual(port_rules[0]["UserIdGroupPairs"][0]["GroupId"], "sg-control")

    def test_ingress_falls_back_to_private_ip(self):
        self.inspector.control_plane_security_group_ids = lambda: []
        self.inspector.control_plane_private_ip = lambda: "10.0.9.9"

        result = self.inspector.ensure_managed_security_group(
            region="us-east-2", vpc_id="vpc-test", cluster_name="demo"
        )

        ingress = result["control_plane_ingress"]
        self.assertTrue(ingress["authorized"])
        self.assertEqual(ingress["via"], "cidr")
        self.assertEqual(ingress["cidr"], "10.0.9.9/32")
        cidr_rules = [
            permission
            for call in self.ec2.authorize_calls
            for permission in call["IpPermissions"]
            if permission.get("FromPort") == TRINO_HTTP_PORT
        ]
        self.assertEqual(cidr_rules[0]["IpRanges"][0]["CidrIp"], "10.0.9.9/32")

    def test_ingress_reports_when_network_undiscoverable(self):
        self.inspector.control_plane_security_group_ids = lambda: []
        self.inspector.control_plane_private_ip = lambda: None

        result = self.inspector.ensure_managed_security_group(
            region="us-east-2", vpc_id="vpc-test", cluster_name="demo"
        )

        self.assertFalse(result["control_plane_ingress"]["authorized"])


class BootstrapTokenTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # Default require_setup_token=True: the first-run gate is active.
        self.app = TrinoHubApp(db_path=Path(self.tmp.name) / "gate.sqlite3", aws=FakeAws())

    def tearDown(self):
        self.tmp.cleanup()

    def _payload(self, **extra):
        base = {"username": "admin", "password": "correct-horse-password"}
        base.update(extra)
        return base

    def test_setup_token_file_is_minted_and_locked_down(self):
        self.assertTrue(self.app.setup_token_path.exists())
        mode = self.app.setup_token_path.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_complete_setup_rejects_missing_or_wrong_token(self):
        with self.assertRaises(ApiError) as ctx:
            self.app.complete_setup(self._payload())
        self.assertEqual(ctx.exception.status, 403)

        with self.assertRaises(ApiError) as ctx:
            self.app.complete_setup(self._payload(setup_token="not-the-token"))
        self.assertEqual(ctx.exception.status, 403)

    def test_complete_setup_succeeds_with_token_and_spends_it(self):
        token = self.app.setup_token_path.read_text().strip()
        result, session = self.app.complete_setup(self._payload(setup_token=token))
        self.assertEqual(result["user"]["role"], "admin")
        self.assertTrue(session)
        # The one-time token is consumed: file gone and DB row cleared.
        self.assertFalse(self.app.setup_token_path.exists())
        with self.app.conn() as conn:
            remaining = conn.execute("SELECT COUNT(*) FROM bootstrap_token").fetchone()[0]
        self.assertEqual(remaining, 0)

    def test_deleting_token_file_regenerates_a_fresh_token(self):
        first = self.app.setup_token_path.read_text().strip()
        self.app.setup_token_path.unlink()
        self.app.ensure_bootstrap_token()
        second = self.app.setup_token_path.read_text().strip()
        self.assertNotEqual(first, second)
        # The stale (first) token no longer works; the new one does.
        with self.assertRaises(ApiError):
            self.app.complete_setup(self._payload(setup_token=first))
        result, _ = self.app.complete_setup(self._payload(setup_token=second))
        self.assertEqual(result["user"]["role"], "admin")


class PaginatedDiscoveryEc2:
    """Fake EC2 client whose describe-* operations span multiple pages."""

    def __init__(self, pages_by_key):
        self._pages_by_key = pages_by_key

    def can_paginate(self, operation):
        return True

    def get_paginator(self, operation):
        result_key, pages = {
            "describe_vpcs": ("Vpcs", self._pages_by_key.get("Vpcs", [])),
            "describe_subnets": ("Subnets", self._pages_by_key.get("Subnets", [])),
            "describe_security_groups": ("SecurityGroups", self._pages_by_key.get("SecurityGroups", [])),
        }[operation]
        return _FakePaginator(result_key, pages)


class _FakePaginator:
    def __init__(self, result_key, pages):
        self._result_key = result_key
        self._pages = pages

    def paginate(self, **kwargs):
        for page in self._pages:
            yield {self._result_key: page}


class DiscoveryPaginationTests(unittest.TestCase):
    def test_full_status_collects_every_page(self):
        inspector = AwsInspector(region="us-east-2")
        ec2 = PaginatedDiscoveryEc2(
            {
                # Two pages of VPCs, one of subnets, one of SGs.
                "Vpcs": [
                    [{"VpcId": "vpc-1", "CidrBlock": "10.0.0.0/16", "IsDefault": True}],
                    [{"VpcId": "vpc-2", "CidrBlock": "10.1.0.0/16", "IsDefault": False}],
                ],
                "Subnets": [
                    [
                        {"SubnetId": "subnet-1", "VpcId": "vpc-1", "AvailabilityZone": "us-east-2a",
                         "CidrBlock": "10.0.1.0/24", "MapPublicIpOnLaunch": True},
                    ],
                ],
                "SecurityGroups": [
                    [{"GroupId": "sg-1", "VpcId": "vpc-1", "GroupName": "default"}],
                ],
            }
        )

        class _Stub:
            def get_caller_identity(self):
                return {"UserId": "u", "Account": "1", "Arn": "arn:aws:iam::1:user/x"}

            def describe_auto_scaling_groups(self, **kwargs):
                return {"AutoScalingGroups": []}

            def list_metrics(self, **kwargs):
                return {"Metrics": []}

        stub = _Stub()
        inspector.clients = lambda region=None: {
            "ec2": ec2, "sts": stub, "autoscaling": stub, "cloudwatch": stub,
        }
        inspector.metadata = lambda: {"available": False}

        status = inspector.full_status(region="us-east-2")
        vpc_ids = [v["vpc_id"] for v in status["network"]["vpcs"]]
        self.assertEqual(vpc_ids, ["vpc-1", "vpc-2"])
        self.assertEqual(len(status["network"]["subnets"]), 1)
        self.assertEqual(len(status["network"]["security_groups"]), 1)


class AskTrinoSqlGuardTests(unittest.TestCase):
    """The validation/parsing helpers are the safety boundary around LLM SQL."""

    def test_validate_accepts_select_and_with(self):
        from trinohub.server import validate_read_only_sql

        self.assertEqual(validate_read_only_sql("SELECT 1"), "SELECT 1")
        self.assertEqual(
            validate_read_only_sql("with t as (select 1) select * from t"),
            "with t as (select 1) select * from t",
        )
        # A trailing semicolon is tolerated and stripped.
        self.assertEqual(validate_read_only_sql("SELECT 1;"), "SELECT 1")

    def test_validate_rejects_non_select_and_mutations(self):
        from trinohub.server import validate_read_only_sql

        for bad in [
            "DROP TABLE t",
            "UPDATE t SET a = 1",
            "DELETE FROM t",
            "INSERT INTO t VALUES (1)",
            "CREATE TABLE t (a int)",
            "ALTER TABLE t ADD COLUMN b int",
            "TRUNCATE TABLE t",
            "",
        ]:
            with self.assertRaises(ApiError) as ctx:
                validate_read_only_sql(bad)
            self.assertEqual(ctx.exception.status, 400)

    def test_validate_rejects_multiple_statements(self):
        from trinohub.server import validate_read_only_sql

        with self.assertRaises(ApiError) as ctx:
            validate_read_only_sql("SELECT 1; SELECT 2")
        self.assertEqual(ctx.exception.status, 400)

    def test_validate_does_not_flag_keywords_inside_string_literals(self):
        from trinohub.server import validate_read_only_sql

        # "delete" lives inside a string literal, so the statement is still valid.
        statement = "SELECT name FROM t WHERE note = 'please delete this row'"
        self.assertEqual(validate_read_only_sql(statement), statement)

    def test_parse_llm_json_handles_markdown_wrapped_and_fallback(self):
        from trinohub.server import parse_llm_json

        wrapped = parse_llm_json('Here you go:\n```json\n{"explanation": "hi", "sql": "SELECT 1", "chartType": "bar"}\n```')
        self.assertEqual(wrapped["sql"], "SELECT 1")
        self.assertEqual(wrapped["chartType"], "bar")

        plain = parse_llm_json("just some prose, no json")
        self.assertEqual(plain["explanation"], "just some prose, no json")
        self.assertIsNone(plain["sql"])


class AskTrinoOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = TrinoHubApp(
            db_path=Path(self.tmp.name) / "ask.sqlite3", aws=FakeAws(), require_setup_token=False
        )
        self.user = {"id": 1, "username": "admin", "role": "admin"}

    def tearDown(self):
        self.tmp.cleanup()

    def test_clarifying_question_short_circuits_execution(self):
        clarifying = {
            "explanation": "",
            "sql": None,
            "chartType": "none",
            "clarifyingQuestion": {
                "question": "Which catalog?",
                "options": ["tpch", "tpcds"],
                "optionType": "catalog",
            },
        }
        self.app.call_ask_llm = lambda *a, **k: json.dumps(clarifying)
        # Execution must not be reached when a clarifying question is returned.
        self.app.create_query = lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not run"))
        result = self.app.ask_trino({"question": "show revenue", "cluster_id": None}, self.user)
        self.assertIsNotNone(result["clarifyingQuestion"])
        self.assertEqual(result["clarifyingQuestion"]["options"], ["tpch", "tpcds"])
        self.assertIsNone(result["sql"])

    def test_denylisted_sql_is_rejected_before_execution(self):
        self.app.call_ask_llm = lambda *a, **k: json.dumps({"explanation": "", "sql": "DROP TABLE t", "chartType": "none"})
        self.app.create_query = lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not run"))
        with self.assertRaises(ApiError) as ctx:
            self.app.ask_trino({"question": "drop it", "cluster_id": 1}, self.user)
        self.assertEqual(ctx.exception.status, 400)

    def test_select_runs_and_passes_results_through(self):
        self.app.call_ask_llm = lambda *a, **k: json.dumps(
            {"explanation": "Top nations by value.", "sql": "SELECT name, total FROM t", "chartType": "bar"}
        )
        finished = {
            "query": {
                "id": 7,
                "status": "Finished",
                "columns": [{"name": "name", "type": "varchar"}, {"name": "total", "type": "bigint"}],
                "data": [["France", 100], ["Germany", 80]],
                "row_count": 2,
                "total_row_count": 2,
                "truncated": False,
                "error_message": None,
            }
        }
        self.app.create_query = lambda payload, user: finished
        result = self.app.ask_trino({"question": "top nations", "cluster_id": 1}, self.user)
        self.assertEqual(result["sql"], "SELECT name, total FROM t")
        self.assertEqual(result["chartType"], "bar")
        self.assertEqual(result["rows"], [["France", 100], ["Germany", 80]])
        self.assertEqual(result["row_count"], 2)
        self.assertIsNone(result["error"])

    def test_missing_api_key_raises_503(self):
        saved = {key: os.environ.pop(key, None) for key in ("ASK_TRINO_API_KEY", "OPENROUTER_API_KEY")}
        try:
            with self.assertRaises(ApiError) as ctx:
                self.app.call_ask_llm("system", [], "question")
            self.assertEqual(ctx.exception.status, 503)
        finally:
            for key, value in saved.items():
                if value is not None:
                    os.environ[key] = value


class RbacTests(unittest.TestCase):
    """Phase 1: roles, privileges, data-access grants, and the audit log."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = TrinoHubApp(
            db_path=Path(self.tmp.name) / "test.sqlite3", aws=FakeAws(), require_setup_token=False
        )
        self.app.complete_setup(
            {
                "username": "admin",
                "password": "correct-horse-password",
                "allowed_instance_types": ["r7i.2xlarge"],
            }
        )
        self.admin = self._user("admin")

    def tearDown(self):
        self.tmp.cleanup()

    def _user(self, username):
        with self.app.conn() as conn:
            return dict(conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone())

    def test_seeded_roles_and_setup_admin_membership(self):
        roles = {role["name"]: role for role in self.app.list_roles()["roles"]}
        self.assertTrue(roles["admin"]["is_system"])
        self.assertTrue(roles["user"]["is_system"])
        self.assertEqual(sorted(roles["admin"]["privileges"]), sorted(self.app.list_roles()["privileges"]))
        self.assertEqual(roles["user"]["privileges"], [])
        # Both seeded roles keep the historical everyone-can-query default.
        self.assertEqual(roles["user"]["cluster_grants"], ["*"])
        self.assertEqual(roles["user"]["catalog_grants"], ["*"])
        decorated = self.app.decorate_user(self.admin)
        self.assertEqual(decorated["roles"], ["admin"])
        self.assertIn("MANAGE_SECURITY", decorated["privileges"])

    def test_custom_role_scopes_cluster_and_catalog_access(self):
        cluster = self.app.create_cluster(
            {"name": "granted", "instance_type": "r7i.2xlarge"}, self.admin
        )["cluster"]
        other = self.app.create_cluster(
            {"name": "forbidden", "instance_type": "r7i.2xlarge"}, self.admin
        )["cluster"]
        self.app.create_role(
            {
                "name": "analysts",
                "privileges": [],
                "cluster_grants": [str(cluster["id"])],
                "catalog_grants": ["tpch"],
            },
            self.admin,
        )
        self.app.create_user({"username": "dana", "password": "pw-123456789", "roles": ["analysts"]}, self.admin)
        dana = self._user("dana")

        self.assertTrue(self.app.user_can_use_cluster(dana, cluster["id"]))
        self.assertFalse(self.app.user_can_use_cluster(dana, other["id"]))
        self.assertTrue(self.app.user_can_use_catalog(dana, "tpch"))
        self.assertTrue(self.app.user_can_use_catalog(dana, "system"))
        self.assertFalse(self.app.user_can_use_catalog(dana, "tpcds"))

        # Query submission enforces both gates.
        with self.assertRaises(ApiError) as ctx:
            self.app.create_query({"cluster_id": other["id"], "sql": "SELECT 1"}, dana)
        self.assertEqual(ctx.exception.status, 403)
        with self.assertRaises(ApiError) as ctx:
            self.app.create_query(
                {"cluster_id": cluster["id"], "sql": "SELECT 1", "catalog": "tpcds"}, dana
            )
        self.assertEqual(ctx.exception.status, 403)

        # Metadata browsing and the cluster list are filtered the same way.
        with self.assertRaises(ApiError):
            self.app.cluster_metadata(other["id"], user=dana)
        listed = self.app.list_clusters(dana)["clusters"]
        self.assertEqual([c["id"] for c in listed], [cluster["id"]])
        visible_catalogs = [c["name"] for c in self.app.cluster_metadata(cluster["id"], user=dana)["catalogs"]]
        self.assertIn("tpch", visible_catalogs)
        self.assertNotIn("tpcds", visible_catalogs)
        # Admins see everything.
        self.assertEqual(len(self.app.list_clusters(self.admin)["clusters"]), 2)

    def test_privilege_enforcement_and_history_visibility(self):
        self.app.create_user({"username": "ops", "password": "pw-123456789", "roles": ["user"]}, self.admin)
        ops = self._user("ops")
        with self.assertRaises(ApiError) as ctx:
            self.app.require_privilege(ops, "MANAGE_CLUSTERS")
        self.assertEqual(ctx.exception.status, 403)
        self.app.require_privilege(self.admin, "MANAGE_CLUSTERS")

        # A custom operator role delegates one area without the others.
        self.app.create_role({"name": "cluster-ops", "privileges": ["MANAGE_CLUSTERS"]}, self.admin)
        self.app.update_user(ops["id"], {"roles": ["user", "cluster-ops"]}, self.admin)
        ops = self._user("ops")
        self.app.require_privilege(ops, "MANAGE_CLUSTERS")
        with self.assertRaises(ApiError):
            self.app.require_privilege(ops, "MANAGE_USERS")
        self.assertFalse(self.app.has_privilege(ops, "VIEW_ALL_QUERY_HISTORY"))

    def test_role_mutation_guardrails(self):
        roles = {role["name"]: role for role in self.app.list_roles()["roles"]}
        with self.assertRaises(ApiError) as ctx:
            self.app.delete_role(roles["admin"]["id"], self.admin)
        self.assertEqual(ctx.exception.status, 409)
        with self.assertRaises(ApiError) as ctx:
            self.app.update_role(roles["admin"]["id"], {"privileges": []}, self.admin)
        self.assertEqual(ctx.exception.status, 409)
        with self.assertRaises(ApiError) as ctx:
            self.app.create_role({"name": "bad", "privileges": ["NOT_A_PRIVILEGE"]}, self.admin)
        self.assertEqual(ctx.exception.status, 400)
        with self.assertRaises(ApiError) as ctx:
            self.app.create_role({"name": "admin"}, self.admin)
        self.assertEqual(ctx.exception.status, 409)
        # The seeded user role can be narrowed (e.g. drop its wildcard grants).
        result = self.app.update_role(roles["user"]["id"], {"cluster_grants": []}, self.admin)
        self.assertEqual(result["role"]["cluster_grants"], [])

    def test_last_security_holder_protection(self):
        with self.assertRaises(ApiError) as ctx:
            self.app.update_user(self.admin["id"], {"is_active": False}, self.admin)
        self.assertEqual(ctx.exception.status, 409)
        self.assertIn("last active admin", ctx.exception.message.lower())
        with self.assertRaises(ApiError) as ctx:
            self.app.update_user(self.admin["id"], {"roles": ["user"]}, self.admin)
        self.assertEqual(ctx.exception.status, 409)

        # With a second security holder the same edits pass.
        self.app.create_user({"username": "backup", "password": "pw-123456789", "roles": ["admin"]}, self.admin)
        result = self.app.update_user(self.admin["id"], {"roles": ["user"]}, self.admin)
        self.assertEqual(result["user"]["roles"], ["user"])

        # Deleting a custom role can also not orphan MANAGE_SECURITY.
        backup = self._user("backup")
        self.app.create_role({"name": "security", "privileges": ["MANAGE_SECURITY"]}, backup)
        self.app.update_user(backup["id"], {"roles": ["security"]}, backup)
        role_id = next(r["id"] for r in self.app.list_roles()["roles"] if r["name"] == "security")
        with self.assertRaises(ApiError) as ctx:
            self.app.delete_role(role_id, backup)
        self.assertEqual(ctx.exception.status, 409)

    def test_audit_log_records_admin_mutations(self):
        self.app.create_user({"username": "dana", "password": "pw-123456789"}, self.admin)
        self.app.create_role({"name": "analysts"}, self.admin)
        self.app.create_catalog(
            {
                "name": "lake",
                "type": "s3_glue",
                "config": {"glue_region": "us-east-2", "warehouse": "s3://bucket/wh/"},
            },
            self.admin,
        )
        self.app.create_cluster({"name": "audited", "instance_type": "r7i.2xlarge"}, self.admin)
        actions = [entry["action"] for entry in self.app.security_audit_entries()["entries"]]
        for expected in ("setup.complete", "user.create", "role.create", "catalog.create", "cluster.create"):
            self.assertIn(expected, actions)
        newest = self.app.security_audit_entries()["entries"][0]
        self.assertEqual(newest["actor_username"], "admin")

    def test_query_history_and_cancel_privileges(self):
        self.app.create_user({"username": "dana", "password": "pw-123456789", "roles": ["user"]}, self.admin)
        dana = self._user("dana")
        cluster = self.app.create_cluster({"name": "hist", "instance_type": "r7i.2xlarge"}, self.admin)["cluster"]
        with self.app.conn() as conn:
            conn.execute(
                """
                INSERT INTO query_runs (user_id, cluster_id, cluster_name, sql_text, status, created_at, updated_at)
                VALUES (?, ?, 'hist', 'SELECT 1', 'Finished', ?, ?)
                """,
                (self.admin["id"], cluster["id"], utc_now_str(), utc_now_str()),
            )
        # Dana sees only her own (empty) history; the admin sees all.
        self.assertEqual(self.app.list_query_history(dana)["queries"], [])
        self.assertEqual(len(self.app.list_query_history(self.admin)["queries"]), 1)
        # Dana can neither view nor cancel the admin's query.
        query = {"user_id": self.admin["id"]}
        with self.assertRaises(ApiError):
            self.app.require_query_access(query, dana)
        with self.assertRaises(ApiError):
            self.app.require_query_access(query, dana, "CANCEL_ANY_QUERY")
        self.app.require_query_access(query, self.admin)


def utc_now_str():
    from trinohub.database import utc_now

    return utc_now()


class FakeRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}


class EnterpriseAuthTests(unittest.TestCase):
    """Phase 2: API tokens, service accounts, session hardening, OIDC SSO."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = TrinoHubApp(
            db_path=Path(self.tmp.name) / "test.sqlite3", aws=FakeAws(), require_setup_token=False
        )
        self.app.complete_setup({"username": "admin", "password": "correct-horse-password"})
        self.admin = self._user("admin")

    def tearDown(self):
        self.tmp.cleanup()

    def _user(self, username):
        with self.app.conn() as conn:
            return dict(conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone())

    def test_api_token_lifecycle_and_bearer_auth(self):
        result = self.app.create_api_token({"name": "ci"}, self.admin)
        token = result["token"]
        self.assertTrue(token.startswith("tht_"))
        self.assertEqual(result["api_token"]["username"], "admin")

        authed = self.app.current_user(FakeRequest({"Authorization": f"Bearer {token}"}))
        self.assertEqual(authed["username"], "admin")
        # Wrong or truncated tokens authenticate nobody.
        self.assertIsNone(self.app.current_user(FakeRequest({"Authorization": "Bearer tht_nope"})))

        tokens = self.app.list_api_tokens(self.admin)["tokens"]
        self.assertEqual([t["name"] for t in tokens], ["ci"])
        self.app.delete_api_token(tokens[0]["id"], self.admin)
        self.assertIsNone(self.app.current_user(FakeRequest({"Authorization": f"Bearer {token}"})))

    def test_api_token_visibility_and_cross_user_minting(self):
        self.app.create_user({"username": "dana", "password": "pw-123456789", "roles": ["user"]}, self.admin)
        dana = self._user("dana")
        mine = self.app.create_api_token({"name": "dana-token"}, dana)
        # Dana sees only her token; the admin (MANAGE_USERS) sees all.
        self.app.create_api_token({"name": "admin-token"}, self.admin)
        self.assertEqual([t["name"] for t in self.app.list_api_tokens(dana)["tokens"]], ["dana-token"])
        self.assertEqual(len(self.app.list_api_tokens(self.admin)["tokens"]), 2)
        # Dana cannot mint for the admin, nor delete the admin's token.
        with self.assertRaises(ApiError):
            self.app.create_api_token({"name": "sneaky", "user_id": self.admin["id"]}, dana)
        admin_token_id = next(
            t["id"] for t in self.app.list_api_tokens(self.admin)["tokens"] if t["name"] == "admin-token"
        )
        with self.assertRaises(ApiError):
            self.app.delete_api_token(admin_token_id, dana)
        self.app.delete_api_token(mine["api_token"]["id"], dana)

    def test_service_accounts_cannot_password_login(self):
        created = self.app.create_user(
            {"username": "ci-bot", "is_service": True, "roles": ["user"]}, self.admin
        )["user"]
        self.assertTrue(created["is_service"])
        with self.assertRaises(ApiError) as ctx:
            self.app.login({"username": "ci-bot", "password": "anything-at-all"})
        self.assertEqual(ctx.exception.status, 401)
        # But an admin-minted token authenticates as the service account.
        bot = self._user("ci-bot")
        token = self.app.create_api_token({"name": "bot", "user_id": bot["id"]}, self.admin)["token"]
        authed = self.app.current_user(FakeRequest({"Authorization": f"Bearer {token}"}))
        self.assertEqual(authed["username"], "ci-bot")

    def test_session_hours_configurable(self):
        self.assertEqual(self.app.session_hours(), 12)
        self.app.set_session_hours({"session_hours": 2}, self.admin)
        self.assertEqual(self.app.session_hours(), 2)
        with self.assertRaises(ApiError):
            self.app.set_session_hours({"session_hours": 0}, self.admin)
        with self.assertRaises(ApiError):
            self.app.set_session_hours({"session_hours": 9999}, self.admin)
        with self.app.conn() as conn:
            token = self.app.create_session(conn, self.admin["id"])
            row = conn.execute(
                "SELECT created_at, expires_at FROM sessions ORDER BY id DESC LIMIT 1"
            ).fetchone()
        created = datetime.fromisoformat(row["created_at"])
        expires = datetime.fromisoformat(row["expires_at"])
        self.assertEqual((expires - created).total_seconds(), 2 * 3600)

    def test_revoke_user_sessions(self):
        with self.app.conn() as conn:
            self.app.create_session(conn, self.admin["id"])
            self.app.create_session(conn, self.admin["id"])
        result = self.app.revoke_user_sessions(self.admin)
        self.assertGreaterEqual(result["revoked"], 2)
        with self.app.conn() as conn:
            remaining = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE user_id = ?", (self.admin["id"],)
            ).fetchone()[0]
        self.assertEqual(remaining, 0)

    # --- OIDC ---------------------------------------------------------------

    def _configure_oidc(self, **overrides):
        payload = {
            "enabled": True,
            "issuer": "https://idp.example.com",
            "client_id": "trinohub",
            "client_secret": "s3cret",
            "group_role_mappings": {"data-eng": "admin"},
            "default_role": "user",
        }
        payload.update(overrides)
        self.app.set_oidc_settings(payload, self.admin)
        self.app._oidc_discovery_cache = (
            float("inf"),
            "https://idp.example.com",
            {
                "issuer": "https://idp.example.com",
                "authorization_endpoint": "https://idp.example.com/authorize",
                "token_endpoint": "https://idp.example.com/token",
            },
        )

    @staticmethod
    def _id_token(claims):
        header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b"=").decode()
        body = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
        return f"{header}.{body}.signature"

    def _run_callback(self, claims_overrides=None, nonce=None):
        url = self.app.oidc_login_start("https://hub.example.com/api/auth/oidc/callback")
        state = url.split("state=")[1].split("&")[0]
        real_nonce = self.app._oidc_states[state]["nonce"]
        claims = {
            "iss": "https://idp.example.com",
            "aud": "trinohub",
            "exp": datetime.now(timezone.utc).timestamp() + 300,
            "nonce": nonce if nonce is not None else real_nonce,
            "preferred_username": "Dana@Example.com",
            "email": "dana@example.com",
            "groups": ["data-eng"],
        }
        claims.update(claims_overrides or {})
        self.app._oidc_http_json = lambda *a, **k: {"id_token": self._id_token(claims)}
        return self.app.oidc_callback(code="auth-code", state=state)

    def test_oidc_settings_validation(self):
        with self.assertRaises(ApiError):
            self.app.set_oidc_settings(
                {"enabled": True, "issuer": "http://insecure", "client_id": "x", "client_secret": "y"},
                self.admin,
            )
        with self.assertRaises(ApiError):
            self.app.set_oidc_settings(
                {
                    "enabled": True,
                    "issuer": "https://idp.example.com",
                    "client_id": "x",
                    "client_secret": "y",
                    "group_role_mappings": {"g": "not-a-role"},
                },
                self.admin,
            )
        # The public view never leaks the secret.
        self._configure_oidc()
        public = self.app.public_oidc_settings()
        self.assertNotIn("client_secret", public)
        self.assertTrue(public["client_secret_set"])

    def test_oidc_callback_provisions_user_and_maps_groups(self):
        self._configure_oidc()
        user, session_token = self._run_callback()
        self.assertEqual(user["username"], "dana@example.com")
        self.assertEqual(user["roles"], ["admin"])  # data-eng -> admin mapping
        self.assertTrue(session_token)
        # A second login reuses the account and keeps roles in sync with the IdP.
        user2, _ = self._run_callback(claims_overrides={"groups": []})
        self.assertEqual(user2["id"], user["id"])
        self.assertEqual(user2["roles"], ["user"])  # falls back to default_role
        # SSO-provisioned users cannot password-login (no usable password).
        with self.assertRaises(ApiError):
            self.app.login({"username": "dana@example.com", "password": "whatever-pass"})

    def test_oidc_callback_rejects_bad_claims(self):
        self._configure_oidc()
        for overrides, description in (
            ({"iss": "https://evil.example.com"}, "issuer"),
            ({"aud": "someone-else"}, "audience"),
            ({"exp": datetime.now(timezone.utc).timestamp() - 10}, "expiry"),
        ):
            with self.subTest(description):
                with self.assertRaises(ApiError) as ctx:
                    self._run_callback(claims_overrides=overrides)
                self.assertEqual(ctx.exception.status, 401)
        with self.assertRaises(ApiError):
            self._run_callback(nonce="wrong-nonce")
        # A reused/unknown state is rejected outright.
        with self.assertRaises(ApiError) as ctx:
            self.app.oidc_callback(code="auth-code", state="bogus-state")
        self.assertEqual(ctx.exception.status, 400)

    def test_password_login_policy_operators_only(self):
        self._configure_oidc(password_login="operators_only")
        self.app.create_user({"username": "dana", "password": "pw-123456789", "roles": ["user"]}, self.admin)
        with self.assertRaises(ApiError) as ctx:
            self.app.login({"username": "dana", "password": "pw-123456789"})
        self.assertEqual(ctx.exception.status, 403)
        # Operators keep break-glass password access.
        result, token = self.app.login({"username": "admin", "password": "correct-horse-password"})
        self.assertTrue(token)


class QueryPlatformTests(unittest.TestCase):
    """Phase 3: scheduled jobs, sharing, metadata cache, autocomplete, search."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = TrinoHubApp(
            db_path=Path(self.tmp.name) / "test.sqlite3", aws=FakeAws(), require_setup_token=False
        )
        self.app.complete_setup(
            {
                "username": "admin",
                "password": "correct-horse-password",
                "allowed_instance_types": ["r7i.2xlarge"],
            }
        )
        self.admin = self._user("admin")
        self.cluster = self.app.create_cluster(
            {"name": "platform", "instance_type": "r7i.2xlarge"}, self.admin
        )["cluster"]

    def tearDown(self):
        self.tmp.cleanup()

    def _user(self, username):
        with self.app.conn() as conn:
            return dict(conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone())

    def _make_user(self, username, roles=("user",)):
        self.app.create_user(
            {"username": username, "password": "pw-123456789", "roles": list(roles)}, self.admin
        )
        return self._user(username)

    # --- cron -----------------------------------------------------------------

    def test_cron_parsing_and_next_run(self):
        from trinohub.server import next_cron_run

        base = datetime(2026, 7, 7, 10, 30, tzinfo=timezone.utc)  # a Tuesday
        self.assertEqual(next_cron_run("*/15 * * * *", base).isoformat(), "2026-07-07T10:45:00+00:00")
        self.assertEqual(next_cron_run("0 3 * * *", base).isoformat(), "2026-07-08T03:00:00+00:00")
        # Sunday=0: next Sunday after Tue 2026-07-07 is 2026-07-12.
        self.assertEqual(next_cron_run("30 6 * * 0", base).isoformat(), "2026-07-12T06:30:00+00:00")
        self.assertEqual(next_cron_run("0 0 1 * *", base).isoformat(), "2026-08-01T00:00:00+00:00")
        with self.assertRaises(ValueError):
            next_cron_run("not a cron", base)
        with self.assertRaises(ValueError):
            next_cron_run("99 * * * *", base)

    # --- scheduled jobs ---------------------------------------------------------

    def test_job_crud_and_validation(self):
        job = self.app.create_job(
            {
                "name": "nightly-count",
                "sql": "SELECT count(*) FROM tpch.sf1.nation",
                "cluster_id": self.cluster["id"],
                "schedule_type": "cron",
                "cron_expression": "0 3 * * *",
            },
            self.admin,
        )["job"]
        self.assertTrue(job["enabled"])
        self.assertTrue(job["next_run_at"])
        self.assertEqual(job["run_as_username"], "admin")

        with self.assertRaises(ApiError):
            self.app.create_job(
                {"name": "bad", "sql": "SELECT 1", "cluster_id": self.cluster["id"],
                 "schedule_type": "interval", "interval_minutes": 1},
                self.admin,
            )
        with self.assertRaises(ApiError):
            self.app.create_job(
                {"name": "bad", "sql": "SELECT 1; SELECT 2", "cluster_id": self.cluster["id"],
                 "schedule_type": "interval", "interval_minutes": 30},
                self.admin,
            )
        with self.assertRaises(ApiError):
            self.app.create_job(
                {"name": "bad", "sql": "SELECT 1", "cluster_id": self.cluster["id"],
                 "schedule_type": "cron", "cron_expression": "bogus"},
                self.admin,
            )

        updated = self.app.update_job(job["id"], {"enabled": False}, self.admin)["job"]
        self.assertFalse(updated["enabled"])
        self.app.delete_job(job["id"], self.admin)
        with self.assertRaises(ApiError):
            self.app.update_job(job["id"], {"enabled": True}, self.admin)

    def test_job_run_as_requires_manage_users(self):
        dana = self._make_user("dana")
        with self.assertRaises(ApiError) as ctx:
            self.app.create_job(
                {"name": "sneaky", "sql": "SELECT 1", "cluster_id": self.cluster["id"],
                 "schedule_type": "interval", "interval_minutes": 30, "run_as": "admin"},
                dana,
            )
        self.assertEqual(ctx.exception.status, 403)
        # The admin can delegate to a service account.
        self.app.create_user({"username": "ci-bot", "is_service": True, "roles": ["user"]}, self.admin)
        job = self.app.create_job(
            {"name": "delegated", "sql": "SELECT 1", "cluster_id": self.cluster["id"],
             "schedule_type": "interval", "interval_minutes": 30, "run_as": "ci-bot"},
            self.admin,
        )["job"]
        self.assertEqual(job["run_as_username"], "ci-bot")

    def test_job_visibility_scoped_to_creator(self):
        dana = self._make_user("dana")
        self.app.create_job(
            {"name": "admins-job", "sql": "SELECT 1", "cluster_id": self.cluster["id"],
             "schedule_type": "interval", "interval_minutes": 30},
            self.admin,
        )
        self.assertEqual(self.app.list_jobs(dana)["jobs"], [])
        self.assertEqual(len(self.app.list_jobs(self.admin)["jobs"]), 1)
        # Non-creators without MANAGE_CLUSTERS can't touch it either.
        job_id = self.app.list_jobs(self.admin)["jobs"][0]["id"]
        with self.assertRaises(ApiError):
            self.app.update_job(job_id, {"enabled": False}, dana)

    def test_due_job_fires_and_records_failed_run_on_stopped_cluster(self):
        job = self.app.create_job(
            {"name": "due", "sql": "SELECT 1", "cluster_id": self.cluster["id"],
             "schedule_type": "interval", "interval_minutes": 30},
            self.admin,
        )["job"]
        with self.app.conn() as conn:
            conn.execute(
                "UPDATE scheduled_jobs SET next_run_at = ? WHERE id = ?",
                ("2000-01-01T00:00:00+00:00", job["id"]),
            )
        fired = self.app.poll_scheduled_jobs_once()
        self.assertEqual(len(fired), 1)
        runs = self.app.list_job_runs(job["id"], self.admin)["runs"]
        self.assertEqual(len(runs), 1)
        # The cluster is 'Not enabled', so submission fails and is recorded.
        self.assertEqual(runs[0]["status"], "Failed")
        self.assertTrue(runs[0]["error"])
        refreshed = next(j for j in self.app.list_jobs(self.admin)["jobs"] if j["id"] == job["id"])
        self.assertEqual(refreshed["last_status"], "Failed")
        self.assertGreater(refreshed["next_run_at"], "2020-01-01")
        # Not due any more: a second poll fires nothing.
        self.assertEqual(self.app.poll_scheduled_jobs_once(), [])

    # --- sharing ----------------------------------------------------------------

    def test_saved_query_sharing_levels(self):
        self.app.create_role({"name": "analysts"}, self.admin)
        dana = self._make_user("dana", roles=("analysts",))
        saved = self.app.create_saved_query(
            {"name": "Shared numbers", "sql": "SELECT 1"}, self.admin
        )["query"]

        # Before sharing, Dana sees nothing.
        self.assertEqual(self.app.list_saved_queries(dana)["queries"], [])
        self.app.share_entity("saved_query", saved["id"], {"role": "analysts", "access": "view"}, self.admin)
        listed = self.app.list_saved_queries(dana)["queries"]
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["shared_access"], "view")
        self.assertEqual(listed[0]["owner_username"], "admin")
        # View access cannot edit or delete.
        with self.assertRaises(ApiError):
            self.app.update_saved_query(saved["id"], {"name": "hijacked"}, dana)
        with self.assertRaises(ApiError):
            self.app.delete_saved_query(saved["id"], dana)
        # Upgrade to edit: rename works, delete stays owner-only.
        self.app.share_entity("saved_query", saved["id"], {"role": "analysts", "access": "edit"}, self.admin)
        self.app.update_saved_query(saved["id"], {"name": "co-edited"}, dana)
        with self.assertRaises(ApiError) as ctx:
            self.app.delete_saved_query(saved["id"], dana)
        self.assertEqual(ctx.exception.status, 403)
        # Only the owner manages shares.
        with self.assertRaises(ApiError):
            self.app.share_entity("saved_query", saved["id"], {"role": "analysts", "access": "view"}, dana)
        shares = self.app.list_entity_shares("saved_query", saved["id"], self.admin)["shares"]
        self.assertEqual(len(shares), 1)
        self.app.unshare_entity("saved_query", saved["id"], shares[0]["id"], self.admin)
        self.assertEqual(self.app.list_saved_queries(dana)["queries"], [])

    def test_notebook_sharing(self):
        self.app.create_role({"name": "analysts"}, self.admin)
        dana = self._make_user("dana", roles=("analysts",))
        notebook = self.app.create_notebook({"name": "Metrics"}, self.admin)["notebook"]
        self.assertEqual(len(self.app.list_notebooks(dana)["notebooks"]), 0)
        self.app.share_entity("notebook", notebook["id"], {"role": "analysts", "access": "view"}, self.admin)
        shared = self.app.list_notebooks(dana)["notebooks"]
        self.assertEqual(len(shared), 1)
        self.assertEqual(shared[0]["shared_access"], "view")
        # Read cells OK; adding a cell needs edit.
        self.app.list_notebook_cells(notebook["id"], dana)
        with self.assertRaises(ApiError):
            self.app.create_notebook_cell(notebook["id"], {"sql": "SELECT 2"}, dana)
        self.app.share_entity("notebook", notebook["id"], {"role": "analysts", "access": "edit"}, self.admin)
        self.app.create_notebook_cell(notebook["id"], {"sql": "SELECT 2"}, dana)

    # --- metadata cache, autocomplete, search ------------------------------------

    def _seed_cache(self):
        self.app._cache_tables(
            self.cluster["id"], "tpch", "sf1", [{"name": "nation", "type": "TABLE"}, {"name": "region", "type": "TABLE"}]
        )
        self.app._cache_columns(
            self.cluster["id"], "tpch", "sf1", "nation",
            [{"name": "nationkey", "type": "bigint"}, {"name": "name", "type": "varchar"}],
        )

    def test_metadata_cache_fallback_when_suspended(self):
        self._seed_cache()
        self.app.update_cluster_status(self.cluster["id"], "Suspended", "test")
        result = self.app.cluster_metadata(self.cluster["id"], catalog="tpch", user=self.admin)
        self.assertTrue(result["cached"])
        self.assertEqual(result["schemas"], [{"name": "sf1"}])
        tables = self.app.cluster_metadata(
            self.cluster["id"], catalog="tpch", schema_name="sf1", user=self.admin
        )
        self.assertEqual([t["name"] for t in tables["tables"]], ["nation", "region"])
        columns = self.app.cluster_metadata(
            self.cluster["id"], catalog="tpch", schema_name="sf1", table="nation", user=self.admin
        )
        self.assertEqual([c["name"] for c in columns["columns"]], ["nationkey", "name"])
        # Nothing cached for an unknown catalog: the original 409 remains.
        with self.assertRaises(ApiError):
            self.app.cluster_metadata(self.cluster["id"], catalog="tpcds", user=self.admin)

    def test_autocomplete_filters_by_catalog_grant(self):
        self._seed_cache()
        self.app._cache_tables(self.cluster["id"], "tpcds", "sf1", [{"name": "store_sales", "type": "TABLE"}])
        self.app.create_role(
            {"name": "tpch-only", "cluster_grants": ["*"], "catalog_grants": ["tpch"]}, self.admin
        )
        dana = self._make_user("dana", roles=("tpch-only",))
        tables = self.app.autocomplete_metadata(self.cluster["id"], dana)["tables"]
        self.assertEqual({t["catalog"] for t in tables}, {"tpch"})
        nation = next(t for t in tables if t["table"] == "nation")
        self.assertEqual(nation["columns"], ["nationkey", "name"])
        # Admins see everything cached.
        all_tables = self.app.autocomplete_metadata(self.cluster["id"], self.admin)["tables"]
        self.assertEqual({t["catalog"] for t in all_tables}, {"tpch", "tpcds"})

    def test_global_search_scopes_results(self):
        self._seed_cache()
        saved = self.app.create_saved_query({"name": "nation counts", "sql": "SELECT 1"}, self.admin)["query"]
        results = self.app.global_search("nation", self.admin)["results"]
        types = {r["type"] for r in results}
        self.assertIn("saved_query", types)
        self.assertIn("table", types)
        # Another user without shares sees the table (wildcard grants) but not
        # the admin's private saved query.
        dana = self._make_user("dana")
        dana_types = {r["type"] for r in self.app.global_search("nation", dana)["results"]}
        self.assertNotIn("saved_query", dana_types)
        self.assertIn("table", dana_types)
        # Short queries return nothing.
        self.assertEqual(self.app.global_search("n", self.admin)["results"], [])

    def test_query_details_requires_trino_query(self):
        with self.assertRaises(ApiError):
            self.app.query_details(9999, self.admin)


class ObservabilityTests(unittest.TestCase):
    """Phase 5: uptime windows, stats sampling, Prometheus, notifications, costs."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = TrinoHubApp(
            db_path=Path(self.tmp.name) / "test.sqlite3", aws=FakeAws(), require_setup_token=False
        )
        self.app.complete_setup(
            {
                "username": "admin",
                "password": "correct-horse-password",
                "allowed_instance_types": ["r7i.2xlarge"],
            }
        )
        self.admin = self._user("admin")
        self.cluster = self.app.create_cluster(
            {"name": "obs", "instance_type": "r7i.2xlarge", "auto_suspend_minutes": 15}, self.admin
        )["cluster"]

    def tearDown(self):
        self.tmp.cleanup()

    def _user(self, username):
        with self.app.conn() as conn:
            return dict(conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone())

    def _attach_resources(self):
        with self.app.conn() as conn:
            self.app.record_provider_resource(
                conn,
                cluster_id=self.cluster["id"],
                resource_type="coordinator_instance",
                resource_id="i-coordinator",
                region="us-east-2",
                metadata={"private_ip": "10.0.1.10"},
            )
            self.app.record_provider_resource(
                conn,
                cluster_id=self.cluster["id"],
                resource_type="auto_scaling_group",
                resource_id="trinohub-obs-workers",
                region="us-east-2",
                metadata={},
            )

    def test_uptime_schedule_normalization_and_window_check(self):
        result = self.app.update_cluster(
            self.cluster["id"], {"uptime_schedule": ["mon-fri 08:00-18:00"]}, self.admin
        )
        windows = result["cluster"]["uptime_schedule"]
        self.assertEqual(windows, [{"days": [0, 1, 2, 3, 4], "start": "08:00", "end": "18:00"}])
        cluster = result["cluster"]
        tuesday_noon = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)
        saturday_noon = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        tuesday_night = datetime(2026, 7, 7, 20, 0, tzinfo=timezone.utc)
        self.assertTrue(self.app.in_uptime_window(cluster, tuesday_noon))
        self.assertFalse(self.app.in_uptime_window(cluster, saturday_noon))
        self.assertFalse(self.app.in_uptime_window(cluster, tuesday_night))
        for bad in (["always"], [{"days": [9], "start": "08:00", "end": "18:00"}], ["mon 18:00-08:00"]):
            with self.assertRaises(ApiError):
                self.app.update_cluster(self.cluster["id"], {"uptime_schedule": bad}, self.admin)

    def test_auto_suspend_holds_inside_uptime_window(self):
        self.app.update_cluster(
            self.cluster["id"], {"uptime_schedule": ["mon-sun 00:00-23:59"]}, self.admin
        )
        self.app.update_cluster_status(self.cluster["id"], "Running", "test")
        result = self.app.auto_suspend_cluster_once(self.cluster["id"])
        self.assertEqual(result["action"], "hold")
        self.assertIn("keep-warm", result["reason"])

    def test_stats_sampling_and_chart_feed(self):
        self._attach_resources()
        self.app.update_cluster_status(self.cluster["id"], "Running", "test")
        written = self.app.sample_cluster_stats_once()
        self.assertEqual(written, 1)
        stats = self.app.cluster_stats(self.cluster["id"], hours=1, user=self.admin)
        self.assertEqual(len(stats["samples"]), 1)
        sample = stats["samples"][0]
        self.assertEqual(sample["active_workers"], 1)  # FakeAws trino_stats
        self.assertEqual(sample["desired_capacity"], 1)
        self.assertEqual(sample["avg_worker_cpu"], 10.0)

    def test_prometheus_metrics_exposition(self):
        self._attach_resources()
        self.app.update_cluster_status(self.cluster["id"], "Running", "test")
        self.app.sample_cluster_stats_once()
        text = self.app.prometheus_metrics()
        self.assertIn('trinohub_cluster_status{cluster="obs",status="Running"} 1', text)
        self.assertIn('trinohub_cluster_active_workers{cluster="obs"} 1', text)
        self.assertIn("# TYPE trinohub_queries_total counter", text)

    def test_notification_settings_and_lifecycle_hook(self):
        with self.assertRaises(ApiError):
            self.app.set_notification_settings({"webhook_url": "ftp://nope"}, self.admin)
        with self.assertRaises(ApiError):
            self.app.set_notification_settings(
                {"webhook_url": "https://hooks.example.com/x", "events": ["bogus"]}, self.admin
            )
        self.app.set_notification_settings(
            {"webhook_url": "https://hooks.example.com/x", "events": ["cluster_failed", "job_failed"]},
            self.admin,
        )
        self.assertEqual(
            self.app.notification_settings(),
            {"webhook_url": "https://hooks.example.com/x", "events": ["cluster_failed", "job_failed"]},
        )
        sent = []
        self.app.notify = lambda event, title, detail=None: sent.append((event, title))
        self.app.update_cluster_status(self.cluster["id"], "Failed", "provisioning blew up")
        self.assertEqual(sent[-1][0], "cluster_failed")
        self.assertIn("obs", sent[-1][1])
        # Same-status updates don't re-notify.
        sent.clear()
        self.app.update_cluster_status(self.cluster["id"], "Failed", "still failed")
        self.assertEqual(sent, [])

    def test_ask_trino_settings_model_override(self):
        from trinohub.server import ASK_TRINO_DEFAULT_MODEL

        # No override stored: falls back to the built-in default model.
        settings = self.app.ask_trino_settings()
        self.assertEqual(settings["model"], "")
        self.assertEqual(settings["effective_model"], ASK_TRINO_DEFAULT_MODEL)
        # Reject a malformed model id (spaces / punctuation).
        with self.assertRaises(ApiError):
            self.app.set_ask_trino_settings({"model": "not a model!"}, self.admin)
        # A pasted OpenRouter model id becomes the effective model.
        self.app.set_ask_trino_settings({"model": "openai/gpt-4o-mini"}, self.admin)
        updated = self.app.ask_trino_settings()
        self.assertEqual(updated["model"], "openai/gpt-4o-mini")
        self.assertEqual(updated["effective_model"], "openai/gpt-4o-mini")
        # Blank clears the override back to the default.
        self.app.set_ask_trino_settings({"model": ""}, self.admin)
        self.assertEqual(self.app.ask_trino_settings()["effective_model"], ASK_TRINO_DEFAULT_MODEL)

    def test_monthly_costs_from_events(self):
        now = datetime.now(timezone.utc)
        with self.app.conn() as conn:
            for event_type, hours_ago in (("running", 10), ("suspended", 4)):
                conn.execute(
                    """
                    INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                    VALUES (?, ?, '', '{}', ?)
                    """,
                    (
                        self.cluster["id"],
                        event_type,
                        (now - timedelta(hours=hours_ago)).isoformat(timespec="seconds"),
                    ),
                )
        costs = self.app.monthly_costs()
        entry = next(c for c in costs["clusters"] if c["cluster_id"] == self.cluster["id"])
        # 6 running hours × (1 coordinator + 1 worker) × r7i.2xlarge rate.
        self.assertAlmostEqual(entry["running_hours_30d"], 6.0, places=1)
        expected = round(6.0 * 0.5292 * 2, 2)
        self.assertAlmostEqual(entry["cost_30d_usd"], expected, delta=0.1)
        self.assertGreaterEqual(costs["total_30d_usd"], entry["cost_30d_usd"])


class FineGrainedSecurityTests(unittest.TestCase):
    """Phase 6: data policies, tags/ABAC, PII classifier, rules rendering."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = TrinoHubApp(
            db_path=Path(self.tmp.name) / "test.sqlite3", aws=FakeAws(), require_setup_token=False
        )
        self.app.complete_setup(
            {
                "username": "admin",
                "password": "correct-horse-password",
                "allowed_instance_types": ["r7i.2xlarge"],
            }
        )
        self.admin = self._user("admin")
        self.cluster = self.app.create_cluster(
            {"name": "secure", "instance_type": "r7i.2xlarge"}, self.admin
        )["cluster"]
        self.app.create_role({"name": "analysts"}, self.admin)
        self.app.create_user(
            {"username": "dana", "password": "pw-123456789", "roles": ["analysts"]}, self.admin
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _user(self, username):
        with self.app.conn() as conn:
            return dict(conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone())

    def test_no_policies_means_no_rules_file(self):
        self.assertIsNone(self.app.render_access_control_rules(self.cluster))
        script = self.app.aws.trino_node_config_script(
            cluster={"name": "secure", "catalogs": ["system", "tpch"]},
            node_role="worker",
            region="us-east-2",
            access_control_rules=None,
        )
        self.assertNotIn("access-control.name=file", script)

    def test_policy_validation(self):
        with self.assertRaises(ApiError):
            self.app.create_data_policy({"role": "nope", "catalog": "tpch"}, self.admin)
        with self.assertRaises(ApiError):
            self.app.create_data_policy({"role": "analysts", "catalog": "Bad Catalog!"}, self.admin)
        with self.assertRaises(ApiError):
            self.app.create_data_policy(
                {"role": "analysts", "catalog": "tpch", "table": "nation"}, self.admin
            )  # table without schema
        with self.assertRaises(ApiError):
            self.app.create_data_policy(
                {"role": "analysts", "catalog": "tpch", "privileges": ["DROP"]}, self.admin
            )

    def test_rules_rendering_with_policies_and_masks(self):
        self.app.create_data_policy(
            {
                "role": "analysts",
                "catalog": "tpch",
                "schema": "sf1",
                "table": "customer",
                "privileges": ["SELECT"],
                "denied_columns": ["phone"],
                "row_filter": "nationkey = 1",
                "column_masks": {"name": "substr(name, 1, 1)"},
            },
            self.admin,
        )
        rules = json.loads(self.app.render_access_control_rules(self.cluster))
        tables = rules["tables"]
        # information_schema + system stay open.
        self.assertTrue(any(rule.get("schema") == "information_schema" for rule in tables))
        policy_rule = next(rule for rule in tables if rule.get("filter"))
        self.assertIn("dana", policy_rule["user"])
        self.assertEqual(policy_rule["catalog"], "tpch")
        self.assertEqual(policy_rule["privileges"], ["SELECT"])
        self.assertEqual(policy_rule["filter"], "nationkey = 1")
        column_names = {entry["name"]: entry for entry in policy_rule["columns"]}
        self.assertFalse(column_names["phone"].get("allow", True))
        self.assertEqual(column_names["name"]["mask"], "substr(name, 1, 1)")
        # A catch-all keeps unrestricted users (the admin) fully able: a
        # negative lookahead excludes exactly the restricted members.
        catch_all = tables[-1]
        self.assertTrue(catch_all["user"].startswith("(?!"))
        self.assertIn("dana", catch_all["user"])  # inside the lookahead
        self.assertIn("SELECT", catch_all["privileges"])
        # Catalog rules mirror role grants (both seeded roles hold wildcards).
        self.assertTrue(any(rule.get("catalog") == ".*" for rule in rules["catalogs"]))
        # And the node config now carries the files.
        with self.app.conn() as conn:
            token = self.app.create_cluster_bootstrap_token(conn, self.cluster["id"])
        rendered = self.app.node_config_script(
            cluster_id=self.cluster["id"], role="coordinator", token=token, instance_type="r7i.2xlarge"
        )
        self.assertIn("access-control.name=file", rendered)
        self.assertIn("rules.json", rendered)
        self.assertIn("nationkey = 1", rendered)

    def test_allow_list_expands_from_metadata_cache(self):
        self.app._cache_columns(
            self.cluster["id"], "tpch", "sf1", "customer",
            [{"name": "custkey"}, {"name": "name"}, {"name": "phone"}],
        )
        self.app.create_data_policy(
            {
                "role": "analysts",
                "catalog": "tpch",
                "schema": "sf1",
                "table": "customer",
                "allowed_columns": ["custkey"],
            },
            self.admin,
        )
        rules = json.loads(self.app.render_access_control_rules(self.cluster))
        policy_rule = next(rule for rule in rules["tables"] if rule.get("table"))
        denied = {entry["name"] for entry in policy_rule["columns"] if entry.get("allow") is False}
        self.assertEqual(denied, {"name", "phone"})

    def test_tags_abac_and_classifier(self):
        # Manual tag + deny policy → column entry in the rules.
        self.app.create_entity_tag({"entity": "tpch.sf1.customer.phone", "tag": "pii-phone"}, self.admin)
        self.app.create_tag_policy({"tag": "pii-phone", "role": "analysts", "effect": "deny"}, self.admin)
        rules = json.loads(self.app.render_access_control_rules(self.cluster))
        tag_rule = next(
            rule for rule in rules["tables"]
            if rule.get("table") == "customer" and rule.get("columns")
        )
        self.assertEqual(tag_rule["columns"], [{"name": "phone", "allow": False}])

        # Classifier proposes tags from cached column names; accept flow works.
        self.app._cache_columns(
            self.cluster["id"], "tpch", "sf1", "users",
            [{"name": "email_address"}, {"name": "custkey"}],
        )
        result = self.app.run_pii_classifier(self.admin)
        self.assertGreaterEqual(result["proposed"], 1)
        proposed = [tag for tag in result["tags"] if tag["status"] == "proposed"]
        self.assertTrue(any(tag["entity"].endswith("email_address") and tag["tag"] == "pii-email" for tag in proposed))
        tag_id = proposed[0]["id"]
        accepted = self.app.resolve_entity_tag(tag_id, True, self.admin)
        self.assertTrue(any(tag["id"] == tag_id and tag["status"] == "accepted" for tag in accepted["tags"]))
        # Rejecting removes a proposal outright.
        still_proposed = [tag for tag in accepted["tags"] if tag["status"] == "proposed"]
        if still_proposed:
            after = self.app.resolve_entity_tag(still_proposed[0]["id"], False, self.admin)
            self.assertFalse(any(tag["id"] == still_proposed[0]["id"] for tag in after["tags"]))


class AcceleratedClusterTests(unittest.TestCase):
    """Phase 4: accelerated clusters cache hot S3 data on local NVMe."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = TrinoHubApp(
            db_path=Path(self.tmp.name) / "test.sqlite3", aws=FakeAws(), require_setup_token=False
        )
        self.app.complete_setup(
            {
                "username": "admin",
                "password": "correct-horse-password",
                "allowed_instance_types": ["r7i.2xlarge", "i4i.2xlarge", "i3en.2xlarge"],
            }
        )
        with self.app.conn() as conn:
            self.admin = dict(conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone())

    def tearDown(self):
        self.tmp.cleanup()

    def _glue_cluster(self, *, accelerated, instance_type="i4i.2xlarge", catalog_types=("s3_glue",)):
        """A cluster dict shaped like node_config_script's input, with one
        Glue-family catalog per requested type (named lake0, lake1, ...)."""
        catalog_configs = [
            {
                "name": f"lake{index}",
                "type": catalog_type,
                "enabled": True,
                "config": {
                    "glue_region": "us-east-2",
                    "s3_region": "us-east-2",
                    "warehouse": "s3://company-lakehouse/warehouse/",
                    "file_format": "PARQUET",
                    "access_mode": "read_only",
                },
            }
            for index, catalog_type in enumerate(catalog_types)
        ]
        return {
            "name": "cache-cluster",
            "accelerated": accelerated,
            "catalogs": ["system", "tpch"] + [c["name"] for c in catalog_configs],
            "catalog_configs": catalog_configs,
        }

    def test_create_accelerated_rejects_ebs_only_instance_type(self):
        with self.assertRaises(ApiError) as ctx:
            self.app.create_cluster(
                {
                    "name": "warm",
                    "instance_type": "r7i.2xlarge",
                    "worker_mode": "fixed",
                    "accelerated": True,
                },
                self.admin,
            )
        self.assertEqual(ctx.exception.status, 409)
        self.assertIn("i4i.2xlarge", ctx.exception.message)

    def test_create_accelerated_rejects_autoscaling(self):
        with self.assertRaises(ApiError) as ctx:
            self.app.create_cluster(
                {
                    "name": "warm",
                    "instance_type": "i4i.2xlarge",
                    "worker_mode": "autoscale",
                    "accelerated": True,
                },
                self.admin,
            )
        self.assertEqual(ctx.exception.status, 409)
        self.assertIn("fixed", ctx.exception.message)

    def test_create_accelerated_defaults_long_auto_suspend(self):
        result = self.app.create_cluster(
            {
                "name": "warm",
                "instance_type": "i4i.2xlarge",
                "worker_mode": "fixed",
                "accelerated": True,
            },
            self.admin,
        )
        cluster = result["cluster"]
        self.assertTrue(cluster["accelerated"])
        self.assertEqual(cluster["auto_suspend_minutes"], 240)

        # An explicit choice (including "never") is honored.
        explicit = self.app.create_cluster(
            {
                "name": "warm-never",
                "instance_type": "i4i.2xlarge",
                "worker_mode": "fixed",
                "accelerated": True,
                "auto_suspend_minutes": None,
            },
            self.admin,
        )
        self.assertIsNone(explicit["cluster"]["auto_suspend_minutes"])

    def test_update_toggles_accelerated_with_validation(self):
        created = self.app.create_cluster(
            {"name": "warm", "instance_type": "i4i.2xlarge", "worker_mode": "fixed"},
            self.admin,
        )["cluster"]
        self.assertFalse(created["accelerated"])

        result = self.app.update_cluster(created["id"], {"accelerated": True})
        self.assertIn("accelerated", result["changes"])
        self.assertTrue(result["cluster"]["accelerated"])
        # Not running, so no restart is needed yet.
        self.assertFalse(result["restart_required"])

        # Switching an accelerated cluster back to autoscaling is rejected.
        with self.assertRaises(ApiError) as ctx:
            self.app.update_cluster(created["id"], {"worker_mode": "autoscale"})
        self.assertEqual(ctx.exception.status, 409)

        # On a running cluster the toggle requires a restart to take effect.
        self.app.update_cluster_status(created["id"], "Running", "test")
        result = self.app.update_cluster(created["id"], {"accelerated": False})
        self.assertIn("accelerated", result["restart_required_fields"])

    def test_update_rejects_accelerated_on_ebs_only_cluster(self):
        created = self.app.create_cluster(
            {"name": "plain", "instance_type": "r7i.2xlarge", "worker_mode": "fixed"},
            self.admin,
        )["cluster"]
        with self.assertRaises(ApiError) as ctx:
            self.app.update_cluster(created["id"], {"accelerated": True})
        self.assertEqual(ctx.exception.status, 409)

    def test_instance_type_options_expose_instance_store(self):
        options = {o["instance_type"]: o for o in self.app.instance_type_options()["instance_types"]}
        self.assertTrue(options["i4i.2xlarge"]["has_instance_store"])
        self.assertEqual(options["i4i.2xlarge"]["instance_store_gb"], 1875)
        self.assertFalse(options["r7i.2xlarge"]["has_instance_store"])
        self.assertEqual(options["r7i.2xlarge"]["instance_store_gb"], 0)

    def test_node_config_renders_fs_cache_for_glue_catalogs(self):
        aws = AwsInspector(region="us-east-2")
        script = aws.trino_node_config_script(
            cluster=self._glue_cluster(accelerated=True, catalog_types=("s3_glue", "delta_glue")),
            node_role="worker",
            region="us-east-2",
            instance_type="i4i.2xlarge",
            coordinator_uri="http://10.0.1.10:8080",
        )
        # Both cacheable catalogs get distinct directories and an even split of
        # the 90% disk budget.
        self.assertIn("fs.cache.enabled=true", script)
        self.assertIn("fs.cache.directories=/mnt/trino-cache/disk0/lake0", script)
        self.assertIn("fs.cache.directories=/mnt/trino-cache/disk0/lake1", script)
        self.assertEqual(script.count("fs.cache.max-disk-usage-percentages=45"), 2)
        # The bootstrap formats and mounts the instance-store disks by device ID.
        self.assertIn("nvme-Amazon_EC2_NVMe_Instance_Storage_", script)
        self.assertIn("mkfs.xfs", script)
        self.assertIn('install -d -m 0750 "$cache_directory"', script)

    def test_node_config_renders_cache_on_coordinator_too(self):
        aws = AwsInspector(region="us-east-2")
        script = aws.trino_node_config_script(
            cluster=self._glue_cluster(accelerated=True),
            node_role="coordinator",
            region="us-east-2",
            instance_type="i4i.2xlarge",
        )
        self.assertIn("fs.cache.enabled=true", script)
        self.assertIn("mkfs.xfs", script)

    def test_node_config_skips_cache_for_hudi_and_non_glue(self):
        aws = AwsInspector(region="us-east-2")
        script = aws.trino_node_config_script(
            cluster=self._glue_cluster(accelerated=True, catalog_types=("hudi_glue",)),
            node_role="worker",
            region="us-east-2",
            instance_type="i4i.2xlarge",
            coordinator_uri="http://10.0.1.10:8080",
        )
        # Hudi has no upstream cache support: no fs.cache properties and no
        # mount block (nothing to cache on this cluster).
        self.assertNotIn("fs.cache.enabled", script)
        self.assertNotIn("mkfs.xfs", script)

    def test_node_config_no_cache_without_accelerated_flag(self):
        aws = AwsInspector(region="us-east-2")
        script = aws.trino_node_config_script(
            cluster=self._glue_cluster(accelerated=False),
            node_role="worker",
            region="us-east-2",
            instance_type="i4i.2xlarge",
            coordinator_uri="http://10.0.1.10:8080",
        )
        self.assertNotIn("fs.cache.enabled", script)
        self.assertNotIn("mkfs.xfs", script)

    def test_node_config_no_cache_on_ebs_only_instance_type(self):
        aws = AwsInspector(region="us-east-2")
        script = aws.trino_node_config_script(
            cluster=self._glue_cluster(accelerated=True),
            node_role="worker",
            region="us-east-2",
            instance_type="r7i.2xlarge",
            coordinator_uri="http://10.0.1.10:8080",
        )
        self.assertNotIn("fs.cache.enabled", script)

    def test_node_config_renders_one_directory_per_disk(self):
        aws = AwsInspector(region="us-east-2")
        script = aws.trino_node_config_script(
            cluster=self._glue_cluster(accelerated=True),
            node_role="worker",
            region="us-east-2",
            instance_type="i3en.2xlarge",
            coordinator_uri="http://10.0.1.10:8080",
        )
        self.assertIn(
            "fs.cache.directories=/mnt/trino-cache/disk0/lake0,/mnt/trino-cache/disk1/lake0",
            script,
        )
        self.assertIn("fs.cache.max-disk-usage-percentages=90,90", script)

    def test_signed_node_config_includes_cache_for_accelerated_cluster(self):
        # End-to-end through the control plane: DB-backed cluster + catalog.
        self.app.create_catalog(
            {
                "name": "lake",
                "type": "s3_glue",
                "config": {
                    "glue_region": "us-east-2",
                    "warehouse": "s3://company-lakehouse/warehouse/",
                },
            }
        )
        cluster = self.app.create_cluster(
            {
                "name": "warm",
                "instance_type": "i4i.2xlarge",
                "worker_mode": "fixed",
                "accelerated": True,
                "catalogs": ["system", "lake"],
            },
            self.admin,
        )["cluster"]
        with self.app.conn() as conn:
            token = self.app.create_cluster_bootstrap_token(conn, cluster["id"])
        script = self.app.node_config_script(
            cluster_id=cluster["id"], role="coordinator", token=token, instance_type="i4i.2xlarge"
        )
        self.assertIn("fs.cache.enabled=true", script)
        self.assertIn("fs.cache.directories=/mnt/trino-cache/disk0/lake", script)
        self.assertIn("fs.cache.max-disk-usage-percentages=90", script)


if __name__ == "__main__":
    unittest.main()
