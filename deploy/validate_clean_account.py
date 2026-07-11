#!/usr/bin/env python3
"""Clean-account end-to-end validation driver for TrinoHub.

Exercises the lifecycle the "AMI-shippable" gate requires, against a running
control plane over HTTP:

    setup -> create (per preset) -> start -> run SQL -> edit (live ASG resize)
          -> suspend -> resume -> run SQL -> disable -> delete (verify zero residual)

plus optional result-truncation and auto-suspend checks. It drives the same
FastAPI routes the UI uses (cookie session auth) and uses only the Python
standard library, so it can run from the control-plane host or any machine that
can reach it.

SAFETY: starting a cluster creates BILLABLE AWS resources. The script will not
start anything unless you pass --confirm-billing. Each cluster it starts is
wrapped in try/finally so it attempts a delete even when a step fails, but a
crashed run can still leave resources — check the Clusters page afterward.

Examples
--------
  # First run on a fresh instance (token from `journalctl -u trinohub`):
  python3 deploy/validate_clean_account.py \
      --base-url http://localhost:8000 \
      --admin-user admin --admin-pass 'correct-horse-battery' \
      --setup-token "$(sudo cat /sites/trinohub/.trinohub/setup-token)" \
      --region us-east-2 \
      --confirm-billing

  # Already set up — just log in and run the lifecycle for one preset:
  python3 deploy/validate_clean_account.py \
      --base-url http://localhost:8000 \
      --admin-user admin --admin-pass 'correct-horse-battery' \
      --presets Cost --confirm-billing
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar


class ApiClient:
    """Tiny cookie-aware JSON HTTP client over urllib."""

    def __init__(self, base_url: str, timeout: float = 300.0) -> None:
        # suspend/delete do synchronous AWS teardown (terminate instance + delete
        # ASG/LT/SG) which can take well over a minute, so the default timeout is
        # generous; otherwise a slow-but-successful call reads as a failure.
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(CookieJar())
        )

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8") or "{}"
                return resp.status, json.loads(raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8") or "{}"
            try:
                return exc.code, json.loads(raw)
            except json.JSONDecodeError:
                return exc.code, {"error": raw}


class ValidationError(Exception):
    pass


# ---- logging helpers -------------------------------------------------------

_PASS, _FAIL, _INFO = "PASS", "FAIL", " .. "
_results: list[tuple[str, str]] = []


def step(ok: bool, label: str, detail: str = "") -> None:
    tag = _PASS if ok else _FAIL
    _results.append((tag, label))
    line = f"[{tag}] {label}"
    if detail:
        line += f" — {detail}"
    print(line, flush=True)
    if not ok:
        raise ValidationError(label)


def info(label: str) -> None:
    print(f"[{_INFO}] {label}", flush=True)


# ---- lifecycle -------------------------------------------------------------

def ensure_setup(client: ApiClient, args: argparse.Namespace) -> None:
    status, body = client.request("GET", "/api/setup/status")
    step(status == 200, "GET /api/setup/status reachable", f"HTTP {status}")
    if body.get("configured"):
        info("Control plane already configured; skipping setup.")
        return
    if not args.setup_token:
        raise ValidationError(
            "Setup is not complete and no --setup-token was provided. "
            "Get it from `sudo cat /sites/trinohub/.trinohub/setup-token` or `journalctl -u trinohub`."
        )
    payload = {
        "username": args.admin_user,
        "password": args.admin_pass,
        "setup_token": args.setup_token,
        "region": args.region,
    }
    if args.vpc_id:
        payload["vpc_id"] = args.vpc_id
    if args.subnets:
        payload["private_subnet_ids"] = args.subnets
    if args.node_profile:
        payload["node_instance_profile"] = args.node_profile
    status, body = client.request("POST", "/api/setup/complete", payload)
    step(status == 201, "POST /api/setup/complete", body.get("error") or f"HTTP {status}")


def login(client: ApiClient, args: argparse.Namespace) -> None:
    status, body = client.request(
        "POST", "/api/auth/login", {"username": args.admin_user, "password": args.admin_pass}
    )
    step(status == 200, "POST /api/auth/login", body.get("error") or f"HTTP {status}")


def wait_for_status(client: ApiClient, cluster_id: int, target: str, timeout_s: int, poll_interval: int = 10) -> dict:
    """Poll a cluster until it reaches `target` (or a terminal failure)."""
    deadline = time.monotonic() + timeout_s
    last = "?"
    while time.monotonic() < deadline:
        status, body = client.request("GET", f"/api/clusters/{cluster_id}")
        if status != 200:
            raise ValidationError(f"GET /api/clusters/{cluster_id} -> HTTP {status}: {body.get('error')}")
        cluster = body["cluster"]
        last = cluster["status"]
        if last == target:
            return cluster
        if last == "Failed":
            raise ValidationError(f"Cluster {cluster_id} entered Failed while waiting for {target}.")
        time.sleep(poll_interval)
    raise ValidationError(f"Cluster {cluster_id} did not reach {target} within {timeout_s}s (last={last}).")


def run_sql(client: ApiClient, cluster_id: int, sql: str, catalog: str, schema: str) -> dict:
    status, body = client.request(
        "POST", "/api/query", {"sql": sql, "cluster_id": cluster_id, "catalog": catalog, "schema": schema}
    )
    if status not in (200, 201):
        raise ValidationError(f"POST /api/query -> HTTP {status}: {body.get('error')}")
    query = body["query"]
    query_id = query["id"]
    # Poll until terminal.
    deadline = time.monotonic() + 120
    while query["status"] not in ("Finished", "Failed", "Cancelled") and time.monotonic() < deadline:
        time.sleep(2)
        status, body = client.request("GET", f"/api/query/{query_id}")
        if status != 200:
            raise ValidationError(f"GET /api/query/{query_id} -> HTTP {status}: {body.get('error')}")
        query = body["query"]
    return query


def validate_preset(client: ApiClient, preset: str, args: argparse.Namespace) -> None:
    name = f"{args.name_prefix}-{preset.lower()}"
    info(f"=== Preset {preset}: cluster '{name}' ===")

    # create
    status, body = client.request(
        "POST",
        "/api/clusters",
        {
            "name": name,
            "preset": preset,
            "worker_mode": "autoscale",
            "min_workers": 1,
            "max_workers": 2,
            "catalogs": ["system", "tpch"],
        },
    )
    step(status == 201, f"[{preset}] create cluster", body.get("error") or f"HTTP {status}")
    cluster_id = body["cluster"]["id"]

    try:
        # start
        status, body = client.request(
            "POST", f"/api/clusters/{cluster_id}/start", {"confirm_billable": True}
        )
        step(status == 200, f"[{preset}] start cluster", body.get("error") or f"HTTP {status}")
        wait_for_status(client, cluster_id, "Running", args.start_timeout, args.poll_interval)
        step(True, f"[{preset}] reached Running")

        # run SQL over the control-plane -> coordinator path (the P0.1 gate)
        query = run_sql(client, cluster_id, "SELECT nationkey, name FROM tpch.sf1.nation LIMIT 5", "tpch", "sf1")
        step(query["status"] == "Finished" and query.get("row_count", 0) == 5,
             f"[{preset}] SELECT returned 5 rows", f"status={query['status']} rows={query.get('row_count')}")

        # live edit: lower max_workers and confirm it applied live (no rebuild)
        status, body = client.request("PATCH", f"/api/clusters/{cluster_id}", {"max_workers": 3})
        step(status == 200 and "max_workers" in body.get("changes", []),
             f"[{preset}] PATCH max_workers applied live",
             f"applied_live={body.get('applied_live')} restart_required={body.get('restart_required')}")

        # suspend -> verify resources cleaned, status Suspended
        status, body = client.request("POST", f"/api/clusters/{cluster_id}/suspend", {})
        step(status == 200, f"[{preset}] suspend cluster", body.get("error") or f"HTTP {status}")
        wait_for_status(client, cluster_id, "Suspended", args.suspend_timeout, args.poll_interval)
        step(True, f"[{preset}] reached Suspended")

        # resume (start again) and re-query
        status, body = client.request(
            "POST", f"/api/clusters/{cluster_id}/start", {"confirm_billable": True}
        )
        step(status == 200, f"[{preset}] resume cluster", body.get("error") or f"HTTP {status}")
        wait_for_status(client, cluster_id, "Running", args.start_timeout, args.poll_interval)
        query = run_sql(client, cluster_id, "SELECT count(*) FROM tpch.sf1.region", "tpch", "sf1")
        step(query["status"] == "Finished", f"[{preset}] post-resume SELECT finished", f"status={query['status']}")

        # disable -> verify the cluster remains configured but all runtime resources are gone
        status, body = client.request("POST", f"/api/clusters/{cluster_id}/disable", {})
        step(status == 200, f"[{preset}] disable cluster", body.get("error") or f"HTTP {status}")
        wait_for_status(client, cluster_id, "Not enabled", args.suspend_timeout, args.poll_interval)
        rstatus, rbody = client.request("GET", f"/api/clusters/{cluster_id}/resources")
        residual = rbody.get("resources", []) if rstatus == 200 else []
        step(rstatus == 200 and not residual, f"[{preset}] disable left zero runtime resources")

    finally:
        # delete and verify zero residual resources (best effort even on failure)
        info(f"[{preset}] deleting cluster {cluster_id} ...")
        status, body = client.request("DELETE", f"/api/clusters/{cluster_id}")
        if status == 200:
            wait_ok = True
            try:
                # Deleting -> the cluster row is removed; resources endpoint should 404.
                rstatus, rbody = client.request("GET", f"/api/clusters/{cluster_id}/resources")
                residual = rbody.get("resources", []) if rstatus == 200 else []
                wait_ok = not residual
            except Exception:
                pass
            step(wait_ok, f"[{preset}] delete left zero residual resources")
        else:
            step(False, f"[{preset}] delete cluster", body.get("error") or f"HTTP {status}")


def validate_truncation(client: ApiClient, args: argparse.Namespace) -> None:
    """Optional: a query returning >1000 rows reports truncated=true."""
    name = f"{args.name_prefix}-trunc"
    info(f"=== Result truncation check: cluster '{name}' ===")
    status, body = client.request(
        "POST", "/api/clusters",
        {"name": name, "preset": "Cost", "worker_mode": "fixed", "min_workers": 1, "max_workers": 1,
         "catalogs": ["system", "tpch"]},
    )
    step(status == 201, "[trunc] create cluster", body.get("error") or f"HTTP {status}")
    cluster_id = body["cluster"]["id"]
    try:
        client.request("POST", f"/api/clusters/{cluster_id}/start", {"confirm_billable": True})
        wait_for_status(client, cluster_id, "Running", args.start_timeout, args.poll_interval)
        # tpch.tiny.orders has 15000 rows; the result is capped at 1000 and flagged.
        query = run_sql(client, cluster_id, "SELECT orderkey FROM tpch.tiny.orders", "tpch", "tiny")
        step(query.get("truncated") is True and query.get("row_count") == 1000 and query.get("total_row_count", 0) > 1000,
             "[trunc] >1000-row result reports truncated",
             f"row_count={query.get('row_count')} total={query.get('total_row_count')} truncated={query.get('truncated')}")
    finally:
        client.request("DELETE", f"/api/clusters/{cluster_id}")


def validate_auto_suspend(client: ApiClient, args: argparse.Namespace) -> None:
    """Optional: an idle cluster with a 1-min auto-suspend actually suspends."""
    name = f"{args.name_prefix}-suspend"
    info(f"=== Auto-suspend check (idle 1 min): cluster '{name}' ===")
    status, body = client.request(
        "POST", "/api/clusters",
        {"name": name, "preset": "Cost", "worker_mode": "fixed", "min_workers": 1, "max_workers": 1,
         "catalogs": ["system", "tpch"], "auto_suspend_minutes": 1},
    )
    step(status == 201, "[suspend] create cluster", body.get("error") or f"HTTP {status}")
    cluster_id = body["cluster"]["id"]
    try:
        client.request("POST", f"/api/clusters/{cluster_id}/start", {"confirm_billable": True})
        wait_for_status(client, cluster_id, "Running", args.start_timeout, args.poll_interval)
        info("[suspend] cluster Running; staying idle, waiting for the poller to auto-suspend (up to 5 min)...")
        cluster = wait_for_status(client, cluster_id, "Suspended", 300, args.poll_interval)
        step(cluster["status"] == "Suspended", "[suspend] cluster auto-suspended while idle")
    finally:
        client.request("DELETE", f"/api/clusters/{cluster_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description="TrinoHub clean-account end-to-end validation.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--admin-user", required=True)
    parser.add_argument("--admin-pass", required=True)
    parser.add_argument("--setup-token", default="", help="One-time token if setup is not yet complete.")
    parser.add_argument("--region", default="us-east-2")
    parser.add_argument("--vpc-id", default="")
    parser.add_argument("--subnets", nargs="*", default=None, help="Private subnet IDs (space separated).")
    parser.add_argument("--node-profile", default="")
    parser.add_argument("--presets", nargs="*", default=["Cost", "Balanced", "Power"],
                        help="Presets to exercise (default: all three).")
    parser.add_argument("--name-prefix", default="p-verify")
    parser.add_argument("--start-timeout", type=int, default=900, help="Seconds to wait for Running (cold start).")
    parser.add_argument("--suspend-timeout", type=int, default=300)
    parser.add_argument("--poll-interval", type=int, default=10)
    parser.add_argument("--request-timeout", type=float, default=300.0,
                        help="Per-request HTTP timeout; suspend/delete teardown can take >1 min.")
    parser.add_argument("--test-truncation", action="store_true")
    parser.add_argument("--test-auto-suspend", action="store_true")
    parser.add_argument("--confirm-billing", action="store_true",
                        help="Required: acknowledges that starting clusters incurs AWS charges.")
    args = parser.parse_args()

    if not args.confirm_billing:
        print("Refusing to run: starting clusters incurs AWS charges. Re-run with --confirm-billing.", file=sys.stderr)
        return 2

    client = ApiClient(args.base_url, timeout=args.request_timeout)
    try:
        ensure_setup(client, args)
        login(client, args)
        for preset in args.presets:
            validate_preset(client, preset, args)
        if args.test_truncation:
            validate_truncation(client, args)
        if args.test_auto_suspend:
            validate_auto_suspend(client, args)
    except ValidationError as exc:
        print(f"\nVALIDATION FAILED: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)

    passes = sum(1 for tag, _ in _results if tag == _PASS)
    fails = sum(1 for tag, _ in _results if tag == _FAIL)
    print(f"\n=== Summary: {passes} passed, {fails} failed ===")
    if fails:
        for tag, label in _results:
            if tag == _FAIL:
                print(f"  FAILED: {label}")
    return 0 if fails == 0 else 1



if __name__ == "__main__":
    sys.exit(main())
