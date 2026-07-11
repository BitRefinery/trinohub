"""Let's Encrypt TLS gateway for cluster connections.

TrinoHub does not terminate TLS itself. Instead the control-plane instance runs a
dedicated **Caddy** reverse proxy that:

* obtains Let's Encrypt certificates **on demand** for ``<cluster>.<base-domain>``
  hostnames (asking us first, so only real cluster names get a cert),
* restricts inbound clients to the operator's **allowed UI CIDRs**, and
* forwards each cluster hostname to that cluster's coordinator on plain HTTP:8080.

This module owns only the *config*: it renders a Caddyfile from the current
cluster/coordinator map and pushes it to Caddy's local admin API. Caddy itself is
installed and run by the operator (see the "Cluster domains & connections" doc).
Everything here is best-effort — if Caddy isn't running, cluster operations must
still succeed, so callers ignore failures.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request

# Caddy's local admin API (its default). Config is pushed here as a Caddyfile.
CADDY_ADMIN_URL = os.environ.get("TRINOHUB_TLS_ADMIN_API", "http://127.0.0.1:2019")
# Where Caddy's on-demand-TLS "ask" hook and clients are told to reach us. The
# ask endpoint is called by Caddy on the same host before it issues a cert.
TLS_ASK_URL = os.environ.get("TRINOHUB_TLS_ASK_URL", "http://127.0.0.1:8000/api/tls/authorize")
# Coordinators serve plain HTTP here; the proxy is the only TLS hop.
COORDINATOR_HTTP_PORT = 8080
# Suspended/starting clusters have no coordinator to proxy to, so their host is
# routed to the control-plane app instead, which speaks just enough of the Trino
# wire protocol to resume the cluster and hold the client until it is ready.
SHIM_UPSTREAM = os.environ.get("TRINOHUB_WIRE_SHIM_UPSTREAM", "127.0.0.1:8000")


def build_caddyfile(
    base_domain: str,
    allowed_cidrs: list[str],
    routes: dict[str, str],
    *,
    ask_url: str = TLS_ASK_URL,
    admin_addr: str = "127.0.0.1:2019",
) -> str:
    """Render the Caddy config for the gateway.

    ``routes`` maps a fully-qualified cluster hostname to its coordinator
    ``ip:port`` upstream. ``allowed_cidrs`` empty means "allow all" (matching the
    app's own allowed-UI-CIDR semantics). All inputs are pre-validated
    (hostnames, IPs, CIDRs), so direct interpolation is safe.
    """
    # Site addresses: the wildcard covers every derived cluster name; explicit
    # override hostnames outside the base domain are added alongside it.
    site_names = [f"*.{base_domain}", base_domain]
    for host in routes:
        if host != base_domain and not host.endswith(f".{base_domain}") and host not in site_names:
            site_names.append(host)

    lines: list[str] = []
    lines.append("{")
    lines.append(f"\tadmin {admin_addr}")
    # Serve HTTP/1.1 + HTTP/2 only, not HTTP/3. Operators are told to open TCP
    # 443 (see the cluster-domains doc); HTTP/3 is QUIC over UDP 443, so browsers
    # that latch onto Caddy's Alt-Svc advertisement would stall on dropped UDP.
    lines.append("\tservers {")
    lines.append("\t\tprotocols h1 h2")
    lines.append("\t}")
    lines.append("\ton_demand_tls {")
    lines.append(f"\t\task {ask_url}")
    lines.append("\t}")
    lines.append("}")
    lines.append("")
    lines.append(f"{', '.join(site_names)} {{")
    lines.append("\ttls {")
    lines.append("\t\ton_demand")
    lines.append("\t}")
    # `route` preserves directive order: deny by IP first, then host routing,
    # then a friendly fallback for hostnames with no running coordinator.
    lines.append("\troute {")
    if allowed_cidrs:
        lines.append(f"\t\t@blocked not remote_ip {' '.join(allowed_cidrs)}")
        lines.append('\t\trespond @blocked "Forbidden: your address is not permitted." 403')
    for index, (host, upstream) in enumerate(sorted(routes.items())):
        lines.append(f"\t\t@c{index} host {host}")
        lines.append(f"\t\treverse_proxy @c{index} {upstream}")
    lines.append('\t\trespond "No running cluster for this hostname." 503')
    lines.append("\t}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def push_config(caddyfile: str, *, admin_url: str = CADDY_ADMIN_URL, timeout: float = 2.0) -> tuple[bool, str]:
    """Push a Caddyfile to Caddy's admin API (best-effort).

    Returns ``(ok, detail)``. A connection error (Caddy not installed/running)
    returns ``(False, ...)`` rather than raising, so cluster operations never
    fail because the gateway is down.
    """
    request = urllib.request.Request(
        f"{admin_url}/load",
        data=caddyfile.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "text/caddyfile"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300, f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        return False, f"Caddy rejected config: HTTP {exc.code} {exc.read()[:200]!r}"
    except (urllib.error.URLError, OSError) as exc:
        return False, f"Caddy admin API unreachable at {admin_url}: {exc}"
