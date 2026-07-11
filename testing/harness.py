"""Reusable end-to-end test harness for TrinoHub.

The harness wires together the *real* FastAPI application (auth, routing,
validation, serialization, SQLite control-plane logic) and drives it through
HTTP — the same surface the browser UI uses — while replacing only the two
external dependencies that would otherwise cost money or require a live cluster:

* :class:`StatefulFakeAws` stands in for ``trinohub.aws_checks.AwsInspector``.
  It simulates the EC2/ASG/coordinator lifecycle in memory and records every
  cleanup call so suspend/disable/delete flows can be asserted. No AWS API is
  ever contacted and no billable resources are launched.
* :class:`FakeTrino` stands in for the coordinator's REST ``/v1/statement``
  endpoint. It returns Trino-shaped responses for the SQL the control plane
  issues (``SELECT``, ``SHOW``, ``information_schema`` metadata, counts), with
  hooks for pagination, large result sets, query failure, and cancellation.

Scenario modules use :class:`E2EHarness` as a context manager::

    with E2EHarness() as h:
        h.setup_admin()
        cluster = h.create_running_cluster("analytics")
        body = h.run_query(cluster["id"], "SELECT * FROM tpch.sf1.nation")

Everything runs in a throwaway temp directory and is torn down automatically.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATIC_DIR = REPO_ROOT / "web"

# Imported lazily-but-eagerly so a clear error is raised by the runner if the
# FastAPI dependencies are missing from the active interpreter.
from trinohub.api import create_app  # noqa: E402
from trinohub.aws_checks import TRINO_VERSION, AwsInspector  # noqa: E402
from trinohub.server import TrinoHubApp  # noqa: E402


# ---------------------------------------------------------------------------
# Fake AWS
# ---------------------------------------------------------------------------
class StatefulFakeAws:
    """In-memory stand-in for :class:`AwsInspector`.

    Tracks the resources the control plane believes it created so cleanup
    behavior (suspend/disable/delete) can be asserted, and exposes mutable
    ``trino_stats`` / ``cpu_average`` / ``health_response`` so autoscaling and
    auto-suspend scenarios can steer the simulated cluster.
    """

    def __init__(self, *, region: str = "us-east-2") -> None:
        self.region = region
        # Records of mutating calls, for assertions.
        self.cleanup_calls: list[tuple[str, Any]] = []
        self.scaling_calls: list[dict[str, Any]] = []
        self.worker_template_calls: list[dict[str, Any]] = []
        self.launch_calls: list[dict[str, Any]] = []
        self.health_calls: list[str] = []
        self._coordinator_seq = 0

        self.worker_asg = {
            "found": True,
            "name": "trinohub-e2e-workers",
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

    # --- identity / validation -------------------------------------------
    def metadata(self) -> dict[str, Any]:
        return {
            "available": True,
            "instance_id": "i-control",
            "role": "TrinoHubControlPlaneRole",
            "region": self.region,
            "account_id": "123456789012",
        }

    def control_plane_private_ip(self) -> str:
        return "10.0.9.9"

    def full_status(self, region: str | None = None) -> dict[str, Any]:
        return {
            "region": region or self.region,
            "metadata": self.metadata(),
            "identity": {
                "Arn": "arn:aws:sts::123456789012:assumed-role/TrinoHubControlPlaneRole/i-control"
            },
            "network": {
                "vpcs": [{"vpc_id": "vpc-e2e", "cidr": "10.0.0.0/16", "is_default": False}],
                "subnets": [
                    {"subnet_id": "subnet-e2e-a", "vpc_id": "vpc-e2e", "az": f"{self.region}a"},
                    {"subnet_id": "subnet-e2e-b", "vpc_id": "vpc-e2e", "az": f"{self.region}b"},
                ],
                "security_groups": [
                    {"group_id": "sg-e2e", "vpc_id": "vpc-e2e", "name": "default"}
                ],
            },
            "checks": [{"name": "sts:GetCallerIdentity", "ok": True, "detail": "ok"}],
            "ok": True,
        }

    def dry_run_instance_launch(self, **kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "code": "DryRunOperation", "detail": "Request would have succeeded."}

    def available_instance_types(self, region: str, instance_types: list[str]) -> list[str]:
        return list(instance_types)

    def trino_node_config_script(self, **kwargs: Any) -> str:
        return AwsInspector(region=kwargs.get("region") or self.region).trino_node_config_script(**kwargs)

    # --- provisioning -----------------------------------------------------
    def ensure_managed_security_group(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "group_id": "sg-managed",
            "created": True,
            "group_name": f"trinohub-{kwargs['cluster_name']}-nodes",
        }

    def launch_coordinator_instance(self, **kwargs: Any) -> dict[str, Any]:
        self.launch_calls.append(kwargs)
        self._coordinator_seq += 1
        ip = f"10.0.1.{10 + self._coordinator_seq}"
        return {
            "instance_id": f"i-coordinator-{self._coordinator_seq}",
            "image_id": "ami-e2e",
            "instance_type": kwargs["instance_type"],
            "private_ip_address": ip,
            "private_dns_name": f"ip-{ip.replace('.', '-')}.{self.region}.compute.internal",
        }

    def create_worker_launch_template(self, **kwargs: Any) -> dict[str, Any]:
        self.worker_template_calls.append(kwargs)
        return {
            "launch_template_id": "lt-e2e",
            "launch_template_name": "trinohub-e2e-workers",
            "image_id": kwargs["image_id"],
            "instance_type": kwargs["instance_type"],
            "coordinator_uri": kwargs["coordinator_uri"],
        }

    def create_worker_auto_scaling_group(self, **kwargs: Any) -> dict[str, Any]:
        cluster = kwargs["cluster"]
        self.worker_asg["min_size"] = cluster["min_workers"]
        self.worker_asg["max_size"] = cluster["max_workers"]
        self.worker_asg["desired_capacity"] = cluster["min_workers"]
        return {
            "auto_scaling_group_name": "trinohub-e2e-workers",
            "desired_capacity": cluster["min_workers"],
            "min_size": cluster["min_workers"],
            "max_size": cluster["max_workers"],
        }

    # --- health / stats / scaling ----------------------------------------
    def coordinator_health(self, **kwargs: Any) -> dict[str, Any]:
        self.health_calls.append(kwargs["coordinator_endpoint"])
        return dict(self.health_response)

    def trino_cluster_stats(self, **kwargs: Any) -> dict[str, Any]:
        return dict(self.trino_stats)

    def worker_auto_scaling_group(self, **kwargs: Any) -> dict[str, Any]:
        return dict(self.worker_asg)

    def set_worker_desired_capacity(self, **kwargs: Any) -> dict[str, Any]:
        self.scaling_calls.append(kwargs)
        self.worker_asg["desired_capacity"] = kwargs["desired_capacity"]
        return {"updated": True, **kwargs}

    def worker_cpu_average(self, **kwargs: Any) -> float:
        return self.cpu_average

    # --- cleanup ----------------------------------------------------------
    def delete_worker_auto_scaling_group(self, **kwargs: Any) -> dict[str, Any]:
        self.cleanup_calls.append(("delete_asg", kwargs["name"]))
        return {"deleted": True, "resource_id": kwargs["name"]}

    def terminate_instances(self, **kwargs: Any) -> dict[str, Any]:
        self.cleanup_calls.append(("terminate_instances", tuple(kwargs["instance_ids"])))
        return {"terminated": kwargs["instance_ids"], "not_found": []}

    def delete_launch_template(self, **kwargs: Any) -> dict[str, Any]:
        self.cleanup_calls.append(("delete_launch_template", kwargs["launch_template_id"]))
        return {"deleted": True, "resource_id": kwargs["launch_template_id"]}

    def wait_for_cluster_instances_gone(self, **kwargs: Any) -> dict[str, Any]:
        self.cleanup_calls.append(("wait_for_instances", kwargs["cluster_name"]))
        return {"gone": True, "remaining_instance_ids": []}

    def delete_security_group(self, **kwargs: Any) -> dict[str, Any]:
        self.cleanup_calls.append(("delete_security_group", kwargs["group_id"]))
        return {"deleted": True, "resource_id": kwargs["group_id"]}


# ---------------------------------------------------------------------------
# Fake Trino
# ---------------------------------------------------------------------------
# A tiny TPC-H-flavoured dataset so SELECTs return believable, deterministic
# rows. Only the columns the suite reads are populated.
_NATIONS = [
    (0, "ALGERIA", 0),
    (1, "ARGENTINA", 1),
    (2, "BRAZIL", 1),
    (3, "CANADA", 1),
    (4, "EGYPT", 4),
    (5, "ETHIOPIA", 0),
    (6, "FRANCE", 3),
    (7, "GERMANY", 3),
    (8, "INDIA", 2),
    (9, "INDONESIA", 2),
]
_REGIONS = [
    (0, "AFRICA"),
    (1, "AMERICA"),
    (2, "ASIA"),
    (3, "EUROPE"),
    (4, "MIDDLE EAST"),
]


class FakeTrino:
    """Deterministic in-memory Trino REST stand-in.

    Plugged into :class:`TrinoHubApp` by replacing ``submit_trino_query``,
    ``fetch_trino_next``, and ``cancel_trino_query``. Returns the documented
    Trino REST shape: ``{"id", "columns", "data", "nextUri"?, "error"?}``.

    Behaviour can be steered per-test:

    * ``fail_next(message)``  -> the next ``submit`` returns a Trino error.
    * ``paginate(pages)``     -> the next ``submit`` is served across pages via
      ``nextUri`` so multi-page accumulation/cancellation can be exercised.
    * ``big_result(rows)``    -> the next ``submit`` returns ``rows`` generated
      rows (single integer column ``n``) to exercise row/byte caps and CSV.
    """

    def __init__(self) -> None:
        self.submitted: list[dict[str, Any]] = []
        self.cancelled: list[str] = []
        self._query_seq = 0
        self._fail_message: str | None = None
        self._pages: list[list[list[Any]]] | None = None
        self._big_rows: int | None = None
        self._page_store: dict[str, dict[str, Any]] = {}

    # --- test steering ----------------------------------------------------
    def fail_next(self, message: str = "line 1:8: Table not found") -> None:
        self._fail_message = message

    def paginate(self, pages: list[list[list[Any]]]) -> None:
        self._pages = [list(page) for page in pages]

    def big_result(self, rows: int) -> None:
        self._big_rows = rows

    # --- control-plane facing methods ------------------------------------
    def submit(
        self,
        *,
        coordinator_endpoint: str,
        sql_text: str,
        username: str,
        catalog: str,
        schema_name: str,
    ) -> dict[str, Any]:
        self.submitted.append(
            {
                "coordinator_endpoint": coordinator_endpoint,
                "sql_text": sql_text,
                "username": username,
                "catalog": catalog,
                "schema_name": schema_name,
            }
        )
        self._query_seq += 1
        query_id = f"20260627_{self._query_seq:06d}_00001_e2e"

        if self._fail_message is not None:
            message, self._fail_message = self._fail_message, None
            return {"id": query_id, "error": {"message": message, "errorName": "TABLE_NOT_FOUND"}}

        if self._big_rows is not None:
            rows, self._big_rows = self._big_rows, None
            return {
                "id": query_id,
                "columns": [{"name": "n", "type": "integer"}],
                "data": [[i] for i in range(rows)],
            }

        if self._pages is not None:
            pages, self._pages = self._pages, None
            return self._start_pagination(query_id, pages)

        return self._answer(query_id, sql_text, catalog, schema_name)

    def fetch_next(self, next_uri: str) -> dict[str, Any]:
        state = self._page_store.get(next_uri)
        if state is None:
            return {"id": "unknown", "columns": [], "data": []}
        return self._serve_page(state)

    def cancel(self, next_uri: str) -> dict[str, Any]:
        self.cancelled.append(next_uri)
        self._page_store.pop(next_uri, None)
        return {"cancelled_remote": True, "status": 200}

    # --- pagination plumbing ---------------------------------------------
    def _start_pagination(self, query_id: str, pages: list[list[list[Any]]]) -> dict[str, Any]:
        columns = [{"name": "n", "type": "integer"}]
        state = {"id": query_id, "columns": columns, "pages": pages, "index": 0}
        first = pages[0] if pages else []
        state["index"] = 1
        response: dict[str, Any] = {"id": query_id, "columns": columns, "data": first}
        if len(pages) > 1:
            uri = f"http://fake/v1/next/{query_id}/1"
            self._page_store[uri] = state
            response["nextUri"] = uri
        return response

    def _serve_page(self, state: dict[str, Any]) -> dict[str, Any]:
        idx = state["index"]
        pages = state["pages"]
        data = pages[idx] if idx < len(pages) else []
        state["index"] = idx + 1
        response: dict[str, Any] = {
            "id": state["id"],
            "columns": state["columns"],
            "data": data,
        }
        if state["index"] < len(pages):
            uri = f"http://fake/v1/next/{state['id']}/{state['index']}"
            self._page_store[uri] = state
            response["nextUri"] = uri
        return response

    # --- canned answers ---------------------------------------------------
    def _answer(self, query_id: str, sql_text: str, catalog: str, schema_name: str) -> dict[str, Any]:
        sql = " ".join(sql_text.strip().rstrip(";").split())
        upper = sql.upper()

        def result(columns: list[dict[str, str]], data: list[list[Any]]) -> dict[str, Any]:
            return {"id": query_id, "columns": columns, "data": data}

        if upper == "SELECT 1" or upper.startswith("SELECT 1 "):
            return result([{"name": "_col0", "type": "integer"}], [[1]])

        if upper.startswith("SHOW CATALOGS"):
            cols = [{"name": "Catalog", "type": "varchar"}]
            return result(cols, [["system"], ["tpch"], ["tpcds"]])

        if upper.startswith("SHOW SCHEMAS"):
            cols = [{"name": "Schema", "type": "varchar"}]
            return result(cols, [["information_schema"], ["sf1"], ["tiny"]])

        if upper.startswith("SHOW TABLES"):
            cols = [{"name": "Table", "type": "varchar"}]
            return result(cols, [["customer"], ["nation"], ["orders"], ["region"]])

        if "INFORMATION_SCHEMA.SCHEMATA" in upper:
            cols = [{"name": "schema_name", "type": "varchar"}]
            return result(cols, [["information_schema"], ["sf1"], ["tiny"]])

        if "INFORMATION_SCHEMA.TABLES" in upper:
            cols = [{"name": "table_name", "type": "varchar"}]
            return result(cols, [["customer"], ["nation"], ["orders"], ["region"]])

        if "INFORMATION_SCHEMA.COLUMNS" in upper:
            cols = [
                {"name": "column_name", "type": "varchar"},
                {"name": "data_type", "type": "varchar"},
            ]
            return result(cols, [["nationkey", "integer"], ["name", "varchar"], ["regionkey", "integer"]])

        # NATION is checked before REGION: a "nation" query also contains the
        # substring "REGION" (via the regionkey column), so the more specific
        # table must win.
        if "COUNT(*)" in upper and "NATION" in upper:
            return result([{"name": "_col0", "type": "bigint"}], [[len(_NATIONS)]])

        if "COUNT(*)" in upper and "REGION" in upper:
            return result([{"name": "_col0", "type": "bigint"}], [[len(_REGIONS)]])

        if "NATION" in upper and "SELECT" in upper:
            cols = [
                {"name": "nationkey", "type": "integer"},
                {"name": "name", "type": "varchar"},
                {"name": "regionkey", "type": "integer"},
            ]
            return result(cols, [list(r) for r in self._limit(_NATIONS, sql)])

        if "REGION" in upper and "SELECT" in upper:
            cols = [{"name": "regionkey", "type": "integer"}, {"name": "name", "type": "varchar"}]
            return result(cols, [list(r) for r in self._limit(_REGIONS, sql)])

        # Default: a single scalar so unknown-but-valid SQL still "runs".
        return result([{"name": "_col0", "type": "integer"}], [[1]])

    @staticmethod
    def _limit(rows: list[tuple[Any, ...]], sql: str) -> list[tuple[Any, ...]]:
        upper = sql.upper()
        if " LIMIT " in upper:
            try:
                n = int(upper.rsplit(" LIMIT ", 1)[1].split()[0])
                return rows[:n]
            except (ValueError, IndexError):
                return rows
        return rows


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------
class Response:
    """Lightweight HTTP response wrapper returned by :class:`HttpClient`."""

    def __init__(self, status: int, headers: dict[str, str], body: Any, raw: bytes) -> None:
        self.status = status
        self.headers = headers
        self.json = body if isinstance(body, (dict, list)) else None
        self.text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(body)
        self.raw = raw

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class HttpClient:
    """Cookie-aware in-process ASGI client driving the real FastAPI app."""

    def __init__(self, app: Any, *, client_ip: str = "127.0.0.1") -> None:
        self.app = app
        self.cookie = ""
        self.client_ip = client_ip

    def request(
        self,
        method: str,
        path: str,
        payload: Any = None,
        *,
        headers: dict[str, str] | None = None,
        client_ip: str | None = None,
    ) -> Response:
        return asyncio.run(self._request(method, path, payload, headers or {}, client_ip))

    # convenience verbs
    def get(self, path: str, **kw: Any) -> Response:
        return self.request("GET", path, None, **kw)

    def post(self, path: str, payload: Any = None, **kw: Any) -> Response:
        return self.request("POST", path, payload if payload is not None else {}, **kw)

    def patch(self, path: str, payload: Any = None, **kw: Any) -> Response:
        return self.request("PATCH", path, payload if payload is not None else {}, **kw)

    def delete(self, path: str, payload: Any = None, **kw: Any) -> Response:
        return self.request("DELETE", path, payload if payload is not None else {}, **kw)

    async def _request(
        self,
        method: str,
        path: str,
        payload: Any,
        extra_headers: dict[str, str],
        client_ip: str | None,
    ) -> Response:
        parsed = urlparse(path)
        body = json.dumps(payload).encode("utf-8") if payload is not None else b""
        headers = [(b"host", b"testserver")]
        if body:
            headers.append((b"content-type", b"application/json"))
            headers.append((b"content-length", str(len(body)).encode("ascii")))
        if self.cookie:
            headers.append((b"cookie", self.cookie.encode("utf-8")))
        for key, value in extra_headers.items():
            headers.append((key.lower().encode("latin1"), value.encode("latin1")))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": parsed.path,
            "raw_path": parsed.path.encode("ascii"),
            "query_string": (parsed.query or "").encode("ascii"),
            "headers": headers,
            "client": (client_ip or self.client_ip, 12345),
            "server": ("testserver", 80),
        }
        events: list[dict[str, Any]] = []
        sent = False

        async def receive() -> dict[str, Any]:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            # Block forever after the body is delivered. Returning
            # ``http.disconnect`` here would trip Starlette's disconnect listener
            # and cancel StreamingResponse bodies (e.g. CSV export) before they
            # are sent. This pending receive is cancelled when the app completes.
            await asyncio.Event().wait()
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            events.append(message)

        await self.app(scope, receive, send)

        status = next(e["status"] for e in events if e["type"] == "http.response.start")
        resp_headers = {
            k.decode("latin1").lower(): v.decode("latin1")
            for e in events
            if e["type"] == "http.response.start"
            for k, v in e.get("headers", [])
        }
        raw = b"".join(e.get("body", b"") for e in events if e["type"] == "http.response.body")
        if "set-cookie" in resp_headers:
            self.cookie = resp_headers["set-cookie"].split(";", 1)[0]
        try:
            parsed_body = json.loads(raw.decode("utf-8")) if raw else None
        except (json.JSONDecodeError, UnicodeDecodeError):
            parsed_body = None
        return Response(status, resp_headers, parsed_body, raw)


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------
class E2EHarness:
    """One self-contained TrinoHub deployment for an end-to-end scenario.

    Use as a context manager. ``aws`` and ``trino`` are the injected fakes;
    ``client`` is the cookie-aware HTTP client. The helper methods below cover
    the common workflow steps so scenarios stay readable.
    """

    ADMIN_USER = "admin"
    ADMIN_PASSWORD = "correct-horse-battery-staple"

    def __init__(self, *, region: str = "us-east-2", client_ip: str = "127.0.0.1") -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="trinohub-e2e-")
        self.db_path = Path(self._tmp.name) / "e2e.sqlite3"
        self.aws = StatefulFakeAws(region=region)
        self.trino = FakeTrino()
        self.control = TrinoHubApp(
            db_path=self.db_path,
            aws=self.aws,
            require_setup_token=False,
            enable_health_poller=False,
        )
        # Route the control plane's Trino calls into the fake engine.
        self.control.submit_trino_query = lambda **kw: self.trino.submit(**kw)
        self.control.fetch_trino_next = self.trino.fetch_next
        self.control.cancel_trino_query = self.trino.cancel
        self.app = create_app(
            control_app=self.control,
            static_dir=DEFAULT_STATIC_DIR,
            enable_health_poller=False,
        )
        self.client = HttpClient(self.app, client_ip=client_ip)

    def __enter__(self) -> "E2EHarness":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        self._tmp.cleanup()

    # --- workflow helpers -------------------------------------------------
    #: Enabled after setup so cluster creation works out of the box — mirrors
    #: the "enable at least one node instance type" step a real admin performs.
    DEFAULT_INSTANCE_TYPES = ["r7i.xlarge", "r7i.2xlarge"]
    DEFAULT_INSTANCE_TYPE = DEFAULT_INSTANCE_TYPES[0]

    def setup_admin(self, **overrides: Any) -> Response:
        """Complete first-run setup, creating the admin and logging it in."""
        payload = {
            "username": self.ADMIN_USER,
            "password": self.ADMIN_PASSWORD,
            "node_instance_profile": "TrinoHubNodeRole",
        }
        payload.update(overrides)
        resp = self.client.post("/api/setup/complete", payload)
        if not resp.ok:
            raise AssertionError(f"setup failed: {resp.status} {resp.text}")
        enable = self.client.request(
            "PUT",
            "/api/instance-types",
            payload={"instance_types": list(self.DEFAULT_INSTANCE_TYPES)},
        )
        if not enable.ok:
            raise AssertionError(f"enabling instance types failed: {enable.status} {enable.text}")
        return resp

    def login(self, username: str, password: str) -> Response:
        return self.client.post("/api/auth/login", {"username": username, "password": password})

    def logout(self) -> Response:
        return self.client.post("/api/auth/logout", {})

    def create_cluster(
        self,
        name: str,
        *,
        instance_type: str | None = None,
        worker_mode: str = "autoscale",
        min_workers: int = 1,
        max_workers: int = 3,
        catalogs: list[str] | None = None,
        auto_suspend_minutes: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "instance_type": instance_type or self.DEFAULT_INSTANCE_TYPE,
            "worker_mode": worker_mode,
            "min_workers": min_workers,
            "max_workers": max_workers,
            "catalogs": catalogs if catalogs is not None else ["system", "tpch", "tpcds"],
        }
        if auto_suspend_minutes is not None:
            payload["auto_suspend_minutes"] = auto_suspend_minutes
        resp = self.client.post("/api/clusters", payload)
        if not resp.ok:
            raise AssertionError(f"create_cluster failed: {resp.status} {resp.text}")
        return resp.json["cluster"]

    def start_cluster(self, cluster_id: int, *, confirm: bool = True) -> Response:
        return self.client.post(f"/api/clusters/{cluster_id}/start", {"confirm_billable": confirm})

    def refresh_health(self, cluster_id: int) -> Response:
        return self.client.post(f"/api/clusters/{cluster_id}/health", {})

    def create_running_cluster(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """Create a cluster and drive it all the way to ``Running``."""
        cluster = self.create_cluster(name, **kwargs)
        start = self.start_cluster(cluster["id"])
        if not start.ok:
            raise AssertionError(f"start failed: {start.status} {start.text}")
        health = self.refresh_health(cluster["id"])
        if not health.ok:
            raise AssertionError(f"health refresh failed: {health.status} {health.text}")
        return health.json["cluster"]

    def suspend_cluster(self, cluster_id: int) -> Response:
        return self.client.post(f"/api/clusters/{cluster_id}/suspend", {})

    def disable_cluster(self, cluster_id: int) -> Response:
        return self.client.post(f"/api/clusters/{cluster_id}/disable", {})

    def delete_cluster(self, cluster_id: int) -> Response:
        return self.client.delete(f"/api/clusters/{cluster_id}", {})

    def run_query(
        self,
        cluster_id: int,
        sql: str,
        *,
        catalog: str = "",
        schema: str = "",
    ) -> dict[str, Any]:
        payload = {"cluster_id": cluster_id, "sql": sql, "catalog": catalog, "schema": schema}
        resp = self.client.post("/api/query", payload)
        if not resp.ok:
            raise AssertionError(f"query failed: {resp.status} {resp.text}")
        return resp.json["query"]

    # --- s3/glue catalog config helper -----------------------------------
    @staticmethod
    def s3_glue_config(**overrides: Any) -> dict[str, Any]:
        config = {
            "glue_region": "us-east-2",
            "s3_region": "us-east-2",
            "warehouse": "s3://trinohub-e2e-warehouse/",
            "default_schema": "default",
            "table_format": "ICEBERG",
            "file_format": "PARQUET",
            "access_mode": "read_write",
        }
        config.update(overrides)
        return config
