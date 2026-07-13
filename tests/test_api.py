import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

try:
    from trinohub.api import create_app
    from trinohub.server import TrinoHubApp
except ModuleNotFoundError:
    create_app = None
    TrinoHubApp = None


class ApiFakeAws:
    def metadata(self):
        return {
            "available": True,
            "instance_id": "i-test",
            "role": "TrinoHubControlPlaneRole",
            "region": "us-east-2",
            "account_id": "123456789012",
        }

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


class AsgiClient:
    def __init__(self, app):
        self.app = app
        self.cookie = ""

    def request(self, method, path, payload=None, host="testserver"):
        return asyncio.run(self._request(method, path, payload, host))

    async def _request(self, method, path, payload, host="testserver"):
        parsed = urlparse(path)
        raw_path = parsed.path
        raw_query = parsed.query
        if isinstance(payload, (bytes, bytearray)):
            body = bytes(payload)
            content_type = b"application/octet-stream"
        else:
            body = json.dumps(payload or {}).encode("utf-8") if payload is not None else b""
            content_type = b"application/json"
        headers = [(b"host", host.encode("latin-1"))]
        if body:
            headers.append((b"content-type", content_type))
            headers.append((b"content-length", str(len(body)).encode("ascii")))
        if self.cookie:
            headers.append((b"cookie", self.cookie.encode("utf-8")))
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": raw_path,
            "raw_path": raw_path.encode("ascii"),
            "query_string": (raw_query or "").encode("ascii"),
            "headers": headers,
            "client": ("testclient", 123),
            "server": ("testserver", 80),
        }
        events = []
        sent_request = False

        async def receive():
            nonlocal sent_request
            if not sent_request:
                sent_request = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            events.append(message)

        await self.app(scope, receive, send)
        status = next(event["status"] for event in events if event["type"] == "http.response.start")
        response_headers = {
            key.decode("latin1").lower(): value.decode("latin1")
            for event in events
            if event["type"] == "http.response.start"
            for key, value in event.get("headers", [])
        }
        response_body = b"".join(event.get("body", b"") for event in events if event["type"] == "http.response.body")
        if "set-cookie" in response_headers:
            self.cookie = response_headers["set-cookie"].split(";", 1)[0]
        if not response_body:
            parsed_body = None
        else:
            try:
                parsed_body = json.loads(response_body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                try:
                    parsed_body = response_body.decode("utf-8")
                except UnicodeDecodeError:
                    parsed_body = response_body  # binary payload (e.g. a driver JAR)
        return status, response_headers, parsed_body


@unittest.skipIf(create_app is None, "FastAPI dependencies are not installed")
class FastApiRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        control = TrinoHubApp(
            db_path=Path(self.tmp.name) / "api.sqlite3", aws=ApiFakeAws(), require_setup_token=False
        )
        self.control = control
        self.client = AsgiClient(create_app(control_app=control, static_dir=Path("web"), enable_health_poller=False))

    def tearDown(self):
        self.tmp.cleanup()

    def test_openapi_and_health_are_available(self):
        status, _, body = self.client.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"ok": True})

        status, _, body = self.client.request("GET", "/openapi.json")
        self.assertEqual(status, 200)
        self.assertIn("/api/clusters", body["paths"])
        self.assertIn("/api/clusters/{cluster_id}/disable", body["paths"])
        self.assertIn("/api/clusters/{cluster_id}/metadata", body["paths"])
        self.assertIn("/api/catalogs/check", body["paths"])
        self.assertIn("/api/query-tabs", body["paths"])
        self.assertIn("/api/query-tabs/{tab_id}", body["paths"])
        self.assertIn("/api/saved-queries", body["paths"])
        self.assertIn("/api/saved-queries/{query_id}", body["paths"])
        self.assertIn("/api/notebooks", body["paths"])
        self.assertIn("/api/notebooks/{notebook_id}", body["paths"])
        self.assertIn("/api/notebooks/{notebook_id}/cells", body["paths"])
        self.assertIn("/api/notebooks/{notebook_id}/cells/{cell_id}", body["paths"])
        self.assertIn("/api/help/topics", body["paths"])
        self.assertIn("/api/help/topics/{slug}", body["paths"])
        self.assertIn("/api/query/{query_id}/csv", body["paths"])
        self.assertIn("/api/preset-tiers", body["paths"])
        self.assertIn("/api/instance-types", body["paths"])
        self.assertIn("/api/ask", body["paths"])
        self.assertNotIn("/api/assist/sql", body["paths"])

    def test_wire_statement_route_is_public_and_reaches_shim(self):
        # The native Trino wire endpoint takes a raw body, forwards the client's
        # Host header, needs no session, and isn't swallowed by the SPA catch-all.
        captured = {}

        def fake_submit(host, body, headers):
            captured["host"] = host
            captured["body"] = body
            return {"kind": "queued", "results": {"id": "q", "stats": {"state": "QUEUED"}, "nextUri": "n"}}

        self.control.wire_submit_statement = fake_submit
        status, headers, body = self.client.request(
            "POST", "/v1/statement", b"SELECT 1", host="lakehouse.trino.acme.internal"
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["stats"]["state"], "QUEUED")
        self.assertEqual(captured["host"], "lakehouse.trino.acme.internal")
        self.assertEqual(captured["body"], b"SELECT 1")

    def test_wire_statement_unknown_host_returns_503_not_401(self):
        # No cluster for this host -> a plain 503 (like the gateway), never an auth
        # error: proves /v1 bypasses session auth and the UI-CIDR middleware.
        status, _, body = self.client.request(
            "POST", "/v1/statement", b"SELECT 1", host="ghost.example"
        )
        self.assertEqual(status, 503)
        self.assertIn("No running cluster", body)

    def test_wire_catch_all_route_proxies(self):
        def fake_proxy(host, method, path_qs, headers, body):
            return {"kind": "proxied", "status": 200, "headers": [("content-type", "application/json")], "body": b'{"ok":1}'}

        self.control.wire_proxy = fake_proxy
        status, _, body = self.client.request(
            "GET", "/v1/statement/executing/q/slug/1", host="lakehouse.trino.acme.internal"
        )
        self.assertEqual(status, 200)
        self.assertEqual(body, {"ok": 1})

    def test_ui_cidr_settings_route_updates_allowlist(self):
        # Settings privilege required: unauthenticated callers get a 401.
        status, _, _ = self.client.request(
            "PUT", "/api/security/ui-cidrs", {"allowed_ui_cidrs": ["203.0.113.4/32"]}
        )
        self.assertEqual(status, 401)

        status, _, _ = self.client.request(
            "POST",
            "/api/setup/complete",
            {"username": "admin", "password": "correct-horse-password", "node_instance_profile": "TrinoHubNodeRole"},
        )
        self.assertEqual(status, 201)

        status, _, body = self.client.request("GET", "/api/security/ui-cidrs")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"allowed_ui_cidrs": []})

        status, _, body = self.client.request(
            "PUT", "/api/security/ui-cidrs", {"allowed_ui_cidrs": ["203.0.113.4", "2001:db8::/64"]}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["allowed_ui_cidrs"], ["203.0.113.4/32", "2001:db8::/64"])

        # The middleware now enforces the list; this test client's peer address
        # ("testclient") is outside it, so the very next request is refused.
        status, _, body = self.client.request("GET", "/api/security/ui-cidrs")
        self.assertEqual(status, 403)
        self.assertIn("allowed UI CIDR", body["error"])

    def test_result_cache_settings_routes(self):
        # Settings privilege required: unauthenticated callers get a 401.
        status, _, _ = self.client.request("PUT", "/api/query-cache", {"result_cache_ttl_minutes": 30})
        self.assertEqual(status, 401)

        status, _, _ = self.client.request(
            "POST",
            "/api/setup/complete",
            {"username": "admin", "password": "correct-horse-password", "node_instance_profile": "TrinoHubNodeRole"},
        )
        self.assertEqual(status, 201)

        status, _, body = self.client.request("GET", "/api/query-cache")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"result_cache_ttl_minutes": 10})

        status, _, body = self.client.request("PUT", "/api/query-cache", {"result_cache_ttl_minutes": 30})
        self.assertEqual(status, 200)
        self.assertEqual(body, {"result_cache_ttl_minutes": 30})

        status, _, body = self.client.request("GET", "/api/query-cache")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"result_cache_ttl_minutes": 30})

        status, _, body = self.client.request("PUT", "/api/query-cache", {"result_cache_ttl_minutes": -5})
        self.assertEqual(status, 400)
        self.assertIn("result_cache_ttl_minutes", body["error"])

    def test_preset_tiers_route_requires_auth_and_resolves(self):
        status, _, body = self.client.request("GET", "/api/preset-tiers")
        self.assertEqual(status, 401)

        status, _, _ = self.client.request(
            "POST",
            "/api/setup/complete",
            {"username": "admin", "password": "correct-horse-password", "node_instance_profile": "TrinoHubNodeRole"},
        )
        self.assertEqual(status, 201)

        status, _, body = self.client.request("GET", "/api/preset-tiers")
        self.assertEqual(status, 200)
        presets = {tier["preset"] for tier in body["tiers"]}
        self.assertEqual(presets, {"Cost", "Balanced", "Power"})

    def test_instance_type_allowlist_routes(self):
        # Read endpoint is auth-gated; the PUT allowlist endpoint is admin-gated.
        status, _, _ = self.client.request("GET", "/api/instance-types")
        self.assertEqual(status, 401)

        status, _, _ = self.client.request(
            "POST",
            "/api/setup/complete",
            {"username": "admin", "password": "correct-horse-password", "node_instance_profile": "TrinoHubNodeRole"},
        )
        self.assertEqual(status, 201)

        status, _, body = self.client.request("GET", "/api/instance-types")
        self.assertEqual(status, 200)
        from trinohub.server import POPULAR_TRINO_INSTANCE_TYPES

        self.assertEqual(len(body["instance_types"]), len(POPULAR_TRINO_INSTANCE_TYPES))
        self.assertIn("t3.large", [opt["instance_type"] for opt in body["instance_types"]])
        self.assertEqual(body["allowed_instance_types"], [])

        status, _, body = self.client.request(
            "PUT", "/api/instance-types", {"instance_types": ["r5.2xlarge", "r7i.xlarge"]}
        )
        self.assertEqual(status, 200)
        # Canonical (curated) order, regardless of request order.
        self.assertEqual(body["setup"]["allowed_instance_types"], ["r7i.xlarge", "r5.2xlarge"])

        # The selection is reflected on the next read, with per-type allowed flags.
        status, _, body = self.client.request("GET", "/api/instance-types")
        self.assertEqual(body["allowed_instance_types"], ["r7i.xlarge", "r5.2xlarge"])
        flags = {opt["instance_type"]: opt["allowed"] for opt in body["instance_types"]}
        self.assertTrue(flags["r7i.xlarge"])
        self.assertFalse(flags["m6i.2xlarge"])

        # An unknown type is rejected.
        status, _, _ = self.client.request(
            "PUT", "/api/instance-types", {"instance_types": ["bogus.type"]}
        )
        self.assertEqual(status, 400)

        # Clearing the allowlist is allowed.
        status, _, body = self.client.request("PUT", "/api/instance-types", {"instance_types": []})
        self.assertEqual(status, 200)
        self.assertEqual(body["setup"]["allowed_instance_types"], [])

    def test_cluster_workflow_routes_use_cookie_auth(self):
        status, _, body = self.client.request("GET", "/api/clusters")
        self.assertEqual(status, 401)
        self.assertEqual(body["error"], "Authentication required.")

        status, _, body = self.client.request(
            "POST",
            "/api/setup/complete",
            {
                "username": "admin",
                "password": "correct-horse-password",
                "node_instance_profile": "TrinoHubNodeRole",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["user"]["role"], "admin")

        # Enable an instance type before clusters can be created.
        status, _, _ = self.client.request(
            "PUT", "/api/instance-types", {"instance_types": ["r7i.2xlarge"]}
        )
        self.assertEqual(status, 200)

        status, _, body = self.client.request("GET", "/api/clusters")
        self.assertEqual(status, 200)
        self.assertEqual(body["clusters"], [])

        status, _, body = self.client.request(
            "POST",
            "/api/clusters",
            {
                "name": "api-cluster",
                "instance_type": "r7i.2xlarge",
                "worker_mode": "fixed",
                "min_workers": 1,
                "max_workers": 1,
                "catalogs": ["system", "tpch"],
            },
        )
        self.assertEqual(status, 201)
        cluster_id = body["cluster"]["id"]
        self.assertEqual(body["cluster"]["instance_type"], "r7i.2xlarge")

        status, _, body = self.client.request("GET", f"/api/clusters/{cluster_id}")
        self.assertEqual(status, 200)
        self.assertEqual(body["cluster"]["name"], "api-cluster")

        status, _, body = self.client.request("GET", f"/api/clusters/{cluster_id}/metadata")
        self.assertEqual(status, 200)
        self.assertEqual([catalog["name"] for catalog in body["catalogs"]], ["system", "tpch"])

        # PATCH only touches the fields sent; max_workers should change while the
        # untouched worker_mode is preserved.
        status, _, body = self.client.request(
            "PATCH", f"/api/clusters/{cluster_id}", {"max_workers": 4}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["cluster"]["max_workers"], 4)
        self.assertEqual(body["cluster"]["worker_mode"], "fixed")
        self.assertEqual(body["changes"], ["max_workers"])

    def test_cluster_connection_route_derives_host_from_base_domain(self):
        # Auth required.
        status, _, _ = self.client.request("GET", "/api/clusters/1/connection")
        self.assertEqual(status, 401)

        status, _, _ = self.client.request(
            "POST",
            "/api/setup/complete",
            {"username": "admin", "password": "correct-horse-password"},
        )
        self.assertEqual(status, 201)
        status, _, _ = self.client.request(
            "PUT", "/api/instance-types", {"instance_types": ["r7i.2xlarge"]}
        )
        self.assertEqual(status, 200)

        # Set the account base domain, then it should surface on setup status.
        status, _, body = self.client.request(
            "PUT", "/api/cluster-base-domain", {"cluster_base_domain": "trino.acme.internal"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["setup"]["cluster_base_domain"], "trino.acme.internal")

        status, _, body = self.client.request(
            "POST", "/api/clusters", {"name": "lakehouse", "instance_type": "r7i.2xlarge"}
        )
        self.assertEqual(status, 201)
        cluster_id = body["cluster"]["id"]

        status, _, body = self.client.request("GET", f"/api/clusters/{cluster_id}/connection")
        self.assertEqual(status, 200)
        self.assertTrue(body["resolvable"])
        self.assertEqual(body["host"], "lakehouse.trino.acme.internal")
        self.assertEqual(body["port"], 443)
        self.assertIn("SSL=true", body["jdbc_url"])
        self.assertEqual(body["user"], "admin")

        # The Caddy on-demand-TLS gate authorizes known cluster hostnames and
        # refuses everything else — and needs no auth cookie (Caddy can't send one).
        status, _, _ = self.client.request(
            "GET", "/api/tls/authorize?domain=lakehouse.trino.acme.internal"
        )
        self.assertEqual(status, 200)
        status, _, _ = self.client.request("GET", "/api/tls/authorize?domain=evil.trino.acme.internal")
        self.assertEqual(status, 404)

    def test_trino_versions_route_and_create_with_version(self):
        status, _, _ = self.client.request(
            "POST", "/api/setup/complete", {"username": "admin", "password": "correct-horse-password"}
        )
        self.assertEqual(status, 201)
        status, _, _ = self.client.request(
            "PUT", "/api/instance-types", {"instance_types": ["r7i.2xlarge"]}
        )
        self.assertEqual(status, 200)

        status, _, body = self.client.request("GET", "/api/trino-versions")
        self.assertEqual(status, 200)
        self.assertTrue(body["versions"])
        self.assertEqual(body["default"], body["versions"][0])
        older = body["versions"][-1]

        status, _, body = self.client.request(
            "POST", "/api/clusters", {"name": "verpin", "instance_type": "r7i.2xlarge", "trino_version": older}
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["cluster"]["trino_version"], older)

        # The version rides along in the cluster list too (for the table column).
        status, _, body = self.client.request("GET", "/api/clusters")
        self.assertEqual(status, 200)
        self.assertEqual(body["clusters"][0]["trino_version"], older)

    def test_user_patch_route_deactivates(self):
        status, _, _ = self.client.request(
            "POST",
            "/api/setup/complete",
            {"username": "admin", "password": "correct-horse-password", "node_instance_profile": "TrinoHubNodeRole"},
        )
        self.assertEqual(status, 201)
        status, _, body = self.client.request(
            "POST",
            "/api/users",
            {"username": "member", "password": "member-password-123", "role": "user"},
        )
        self.assertEqual(status, 201)
        member_id = body["user"]["id"]

        status, _, body = self.client.request("PATCH", f"/api/users/{member_id}", {"is_active": False})
        self.assertEqual(status, 200)
        self.assertFalse(body["user"]["is_active"])
        self.assertEqual(body["changes"], ["is_active"])

    def test_query_tab_routes_use_cookie_auth(self):
        status, _, body = self.client.request("GET", "/api/query-tabs")
        self.assertEqual(status, 401)
        self.assertEqual(body["error"], "Authentication required.")

        status, _, _ = self.client.request(
            "POST",
            "/api/setup/complete",
            {"username": "admin", "password": "correct-horse-password", "node_instance_profile": "TrinoHubNodeRole"},
        )
        self.assertEqual(status, 201)

        status, _, body = self.client.request("GET", "/api/query-tabs")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["tabs"]), 1)
        self.assertTrue(body["tabs"][0]["is_active"])

        status, _, body = self.client.request(
            "POST",
            "/api/query-tabs",
            {
                "name": "scratch.sql",
                "sql": "SHOW CATALOGS;",
                "catalog": "tpch",
                "schema": "sf1",
                "run_mode": "selected",
                "is_active": True,
            },
        )
        self.assertEqual(status, 201)
        tab_id = body["tab"]["id"]
        self.assertEqual(body["tab"]["name"], "scratch.sql")
        self.assertEqual(body["tab"]["run_mode"], "selected")
        self.assertTrue(body["tab"]["is_active"])

        status, _, body = self.client.request(
            "PATCH",
            f"/api/query-tabs/{tab_id}",
            {"name": "renamed.sql", "sql": "SELECT 1;", "run_mode": "all"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["tab"]["name"], "renamed.sql")
        self.assertEqual(body["tab"]["sql"], "SELECT 1;")
        self.assertEqual(body["tab"]["run_mode"], "all")

        status, _, body = self.client.request("DELETE", f"/api/query-tabs/{tab_id}", {})
        self.assertEqual(status, 200)
        self.assertTrue(body["deleted"])
        self.assertGreaterEqual(len(body["tabs"]), 1)

    def test_saved_query_routes_use_cookie_auth(self):
        status, _, body = self.client.request("GET", "/api/saved-queries")
        self.assertEqual(status, 401)
        self.assertEqual(body["error"], "Authentication required.")

        status, _, _ = self.client.request(
            "POST",
            "/api/setup/complete",
            {"username": "admin", "password": "correct-horse-password", "node_instance_profile": "TrinoHubNodeRole"},
        )
        self.assertEqual(status, 201)

        status, _, body = self.client.request(
            "POST",
            "/api/saved-queries",
            {"name": "Nation count", "sql": "SELECT count(*) FROM tpch.sf1.nation", "catalog": "tpch", "schema": "sf1"},
        )
        self.assertEqual(status, 201)
        query_id = body["query"]["id"]
        self.assertEqual(body["query"]["name"], "Nation count")

        status, _, body = self.client.request("GET", "/api/saved-queries")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["queries"]), 1)

        status, _, body = self.client.request(
            "PATCH",
            f"/api/saved-queries/{query_id}",
            {"name": "Renamed", "sql": "SELECT 1"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["query"]["name"], "Renamed")
        self.assertEqual(body["query"]["sql"], "SELECT 1")

        status, _, body = self.client.request("DELETE", f"/api/saved-queries/{query_id}", {})
        self.assertEqual(status, 200)
        self.assertTrue(body["deleted"])

    def test_notebook_routes_use_cookie_auth(self):
        status, _, body = self.client.request("GET", "/api/notebooks")
        self.assertEqual(status, 401)
        self.assertEqual(body["error"], "Authentication required.")

        status, _, _ = self.client.request(
            "POST",
            "/api/setup/complete",
            {"username": "admin", "password": "correct-horse-password", "node_instance_profile": "TrinoHubNodeRole"},
        )
        self.assertEqual(status, 201)

        status, _, body = self.client.request(
            "POST",
            "/api/notebooks",
            {"name": "Exploration", "catalog": "tpch", "schema": "sf1"},
        )
        self.assertEqual(status, 201)
        notebook_id = body["notebook"]["id"]
        self.assertEqual(body["notebook"]["name"], "Exploration")

        status, _, body = self.client.request("GET", "/api/notebooks")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["notebooks"]), 1)

        status, _, body = self.client.request("PATCH", f"/api/notebooks/{notebook_id}", {"name": "Renamed"})
        self.assertEqual(status, 200)
        self.assertEqual(body["notebook"]["name"], "Renamed")

        status, _, body = self.client.request(
            "POST",
            f"/api/notebooks/{notebook_id}/cells",
            {"sql": "SELECT 1", "view_pref": "chart", "chart_config": {"type": "bar", "x": "a", "y": "b"}},
        )
        self.assertEqual(status, 201)
        cell_id = body["cell"]["id"]
        self.assertEqual(body["cell"]["view_pref"], "chart")
        self.assertEqual(body["cell"]["chart_config"], {"type": "bar", "x": "a", "y": "b"})

        status, _, body = self.client.request("GET", f"/api/notebooks/{notebook_id}/cells")
        self.assertEqual(status, 200)
        # One seeded cell + the one created above.
        self.assertEqual(len(body["cells"]), 2)

        status, _, body = self.client.request(
            "PATCH", f"/api/notebooks/{notebook_id}/cells/{cell_id}", {"sql": "SELECT 2"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["cell"]["sql"], "SELECT 2")

        status, _, body = self.client.request("DELETE", f"/api/notebooks/{notebook_id}/cells/{cell_id}", {})
        self.assertEqual(status, 200)
        self.assertTrue(body["deleted"])

        status, _, body = self.client.request("DELETE", f"/api/notebooks/{notebook_id}", {})
        self.assertEqual(status, 200)
        self.assertTrue(body["deleted"])

    def test_help_routes_require_auth_and_serve_markdown(self):
        status, _, body = self.client.request("GET", "/api/help/topics")
        self.assertEqual(status, 401)
        self.assertEqual(body["error"], "Authentication required.")

        status, _, _ = self.client.request(
            "POST",
            "/api/setup/complete",
            {"username": "admin", "password": "correct-horse-password", "node_instance_profile": "TrinoHubNodeRole"},
        )
        self.assertEqual(status, 201)

        status, _, body = self.client.request("GET", "/api/help/topics")
        self.assertEqual(status, 200)
        group_ids = {group["id"] for group in body["groups"]}
        self.assertIn("everyone", group_ids)
        self.assertIn("admins", group_ids)

        status, _, body = self.client.request("GET", "/api/help/topics/getting-started")
        self.assertEqual(status, 200)
        self.assertIn("# Getting started", body)

        # Unknown topic (valid slug, no file) and an invalid slug both 404.
        status, _, _ = self.client.request("GET", "/api/help/topics/unknown-topic")
        self.assertEqual(status, 404)
        status, _, _ = self.client.request("GET", "/api/help/topics/bad.slug")
        self.assertEqual(status, 404)

    def test_help_admin_topics_hidden_from_users(self):
        status, _, _ = self.client.request(
            "POST",
            "/api/setup/complete",
            {"username": "admin", "password": "correct-horse-password", "node_instance_profile": "TrinoHubNodeRole"},
        )
        self.assertEqual(status, 201)
        status, _, _ = self.client.request(
            "POST",
            "/api/users",
            {"username": "member", "password": "member-password-123", "role": "user"},
        )
        self.assertEqual(status, 201)

        # Switch the session to the query user.
        status, _, _ = self.client.request(
            "POST",
            "/api/auth/login",
            {"username": "member", "password": "member-password-123"},
        )
        self.assertEqual(status, 200)

        status, _, body = self.client.request("GET", "/api/help/topics")
        self.assertEqual(status, 200)
        group_ids = {group["id"] for group in body["groups"]}
        self.assertIn("everyone", group_ids)
        self.assertNotIn("admins", group_ids)

        # A query user may read everyone topics but not admin topics.
        status, _, _ = self.client.request("GET", "/api/help/topics/getting-started")
        self.assertEqual(status, 200)
        status, _, body = self.client.request("GET", "/api/help/topics/managing-clusters")
        self.assertEqual(status, 403)

    def test_connector_types_endpoint_returns_form_schema(self):
        # Requires an authenticated user (like GET /api/catalogs), not admin.
        status, _, _ = self.client.request("GET", "/api/connector-types")
        self.assertEqual(status, 401)

        status, _, _ = self.client.request(
            "POST",
            "/api/setup/complete",
            {"username": "admin", "password": "correct-horse-password", "node_instance_profile": "TrinoHubNodeRole"},
        )
        self.assertEqual(status, 201)

        status, _, body = self.client.request("GET", "/api/connector-types")
        self.assertEqual(status, 200)
        types = {c["type"] for c in body["connector_types"]}
        self.assertIn("postgresql", types)
        self.assertIn("hudi_glue", types)
        self.assertIn("gsheets", types)

    def test_static_index_is_served_without_cache(self):
        status, headers, body = self.client.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertIn("TrinoHub", body)

    def test_connector_driver_routes_require_admin_and_accept_raw_jar(self):
        jar = b"PK\x03\x04" + b"\x00" * 128

        # Admin-gated: no session yet.
        status, _, _ = self.client.request("GET", "/api/connector-drivers")
        self.assertEqual(status, 401)

        status, _, body = self.client.request(
            "POST",
            "/api/setup/complete",
            {"username": "admin", "password": "correct-horse-password", "node_instance_profile": "TrinoHubNodeRole"},
        )
        self.assertEqual(status, 201)

        # Raw JAR bytes as the request body (no multipart).
        status, _, body = self.client.request(
            "POST", "/api/connector-drivers/oracle?filename=ojdbc11.jar", jar
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["driver"]["filename"], "ojdbc11.jar")

        status, _, body = self.client.request("GET", "/api/connector-drivers")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["drivers"]), 1)

        # Non-JAR payload rejected.
        status, _, _ = self.client.request(
            "POST", "/api/connector-drivers/oracle?filename=x.jar", b"not a zip"
        )
        self.assertEqual(status, 400)

        status, _, body = self.client.request("DELETE", "/api/connector-drivers/oracle")
        self.assertEqual(status, 200)
        status, _, body = self.client.request("GET", "/api/connector-drivers")
        self.assertEqual(len(body["drivers"]), 0)


    def test_mcp_endpoint_speaks_json_rpc(self):
        # Unauthenticated calls are refused.
        status, _, _ = self.client.request(
            "POST", "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        )
        self.assertEqual(status, 401)

        status, _, _ = self.client.request(
            "POST",
            "/api/setup/complete",
            {"username": "admin", "password": "correct-horse-password", "node_instance_profile": "TrinoHubNodeRole"},
        )
        self.assertEqual(status, 201)

        status, _, body = self.client.request(
            "POST", "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["result"]["serverInfo"]["name"], "trinohub")
        self.assertIn("tools", body["result"]["capabilities"])

        # Notifications get a bodyless 202.
        status, _, _ = self.client.request(
            "POST", "/mcp", {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        self.assertEqual(status, 202)

        status, _, body = self.client.request(
            "POST", "/mcp", {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        )
        names = {tool["name"] for tool in body["result"]["tools"]}
        self.assertEqual(names, {"list_clusters", "browse_metadata", "run_query"})

        status, _, body = self.client.request(
            "POST",
            "/mcp",
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "list_clusters", "arguments": {}}},
        )
        self.assertEqual(status, 200)
        self.assertFalse(body["result"]["isError"])
        self.assertIn("clusters", body["result"]["content"][0]["text"])

        # Write SQL is rejected by the read-only boundary (as a tool error).
        status, _, body = self.client.request(
            "POST",
            "/mcp",
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
             "params": {"name": "run_query", "arguments": {"cluster_id": 1, "sql": "DROP TABLE x"}}},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["result"]["isError"])

        status, _, body = self.client.request(
            "POST", "/mcp", {"jsonrpc": "2.0", "id": 5, "method": "no/such"}
        )
        self.assertEqual(body["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
