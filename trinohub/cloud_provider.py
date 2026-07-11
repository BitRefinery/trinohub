"""The cloud-provider seam.

TrinoHub provisions self-managed Trino clusters on infrastructure it rents from a
cloud. Today the only implementation is AWS (``aws_checks.AwsInspector`` on EC2 +
Auto Scaling + Secrets Manager), but the control plane deliberately talks to that
infrastructure through a narrow, named surface so a second provider (Azure, GCP)
can be added as a new implementation rather than a fork of the whole app.

``CloudProvider`` is that surface: every infrastructure call ``server.py`` makes
goes through an object satisfying this protocol (injected as ``TrinoHubApp.aws``
and replaced by ``FakeAws`` in tests). The protocol is intentionally a structural
``Protocol`` -- ``AwsInspector`` does not subclass it; it simply implements the
members. That keeps the AWS engine free of an import cycle while still giving the
rest of the app a single, documented contract to code against.

Companion abstractions:

* ``secrets_store.SecretStore`` -- pluggable storage for data-source credentials
  (AWS Secrets Manager today; Vault/Key Vault/GCP Secret Manager later).

Notes for a future second provider:

* Every method takes ``region`` explicitly; a provider whose network model is not
  region-scoped (GCP VPCs are global) still receives it and may treat it as the
  compute region only.
* Resource identifiers returned in the ``dict`` payloads are opaque to the caller
  -- ``server.py`` persists them via ``provider_resources`` and hands them back to
  the same provider for teardown, so their shape (ARN vs Key Vault URI vs GCP
  resource name) never leaks into shared logic.
* The Trino-runtime helpers at the bottom (``trino_node_config_script``,
  ``coordinator_health``, ``trino_cluster_stats``) are provider-neutral today and
  only live behind this seam because they historically sat on ``AwsInspector``.
  They are the natural first candidates to extract into a separate ``TrinoRuntime``
  interface once a second provider lands; kept here for now so ``TrinoHubApp.aws``
  has one accurate type.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable

# Canonical provider identifiers. Persisted as the ``provider`` discriminator on
# ``setup_settings`` / ``provider_resources`` and used to select an implementation.
PROVIDER_AWS = "aws"
KNOWN_PROVIDERS = (PROVIDER_AWS,)


@runtime_checkable
class CloudProvider(Protocol):
    """The infrastructure surface the control plane depends on.

    ``runtime_checkable`` verifies member *presence* only (not signatures), which
    is enough for the ``isinstance`` guard used when wiring an implementation.
    """

    # Compute region this provider operates in (its default when a call omits one).
    region: str

    # -- Identity & account inspection -------------------------------------------------
    def metadata(self) -> dict[str, Any]:
        """Self-identifying facts about the control plane's own host/instance."""

    def control_plane_private_ip(self) -> str | None:
        """Private IP the provisioned nodes should reach the control plane on."""

    def clients(self, region: str | None = None) -> dict[str, Any]:
        """Return the provider's low-level SDK clients (used by the secret store)."""

    def full_status(self, region: str | None = None) -> dict[str, Any]:
        """Validate credentials and enumerate the networking the wizard needs."""

    # -- Capacity discovery ------------------------------------------------------------
    def available_instance_types(self, region: str, instance_types: list[str]) -> list[str]:
        """Filter a candidate machine-size list down to what is offerable here."""

    def dry_run_instance_launch(
        self,
        *,
        region: str,
        subnet_id: str,
        node_instance_profile: str,
        instance_type: str = "t3.small",
        image_id: str | None = None,
    ) -> dict[str, Any]:
        """Pre-flight a node launch (permission/quota probe) without creating one."""

    # -- Networking --------------------------------------------------------------------
    def ensure_managed_security_group(
        self, *, region: str, vpc_id: str, cluster_name: str
    ) -> dict[str, Any]:
        """Create/return the firewall grouping that wires nodes to the control plane."""

    def delete_security_group(self, *, region: str, group_id: str) -> dict[str, Any]:
        """Tear down a managed firewall grouping created for a cluster."""

    def cleanup_managed_security_group_rules(
        self, *, region: str, group_id: str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Remove the ingress rules this control plane added for a cluster."""

    # -- Node lifecycle ----------------------------------------------------------------
    def launch_coordinator_instance(
        self,
        *,
        region: str,
        subnet_id: str,
        security_group_ids: list[str],
        node_instance_profile: str,
        cluster: dict[str, Any],
        instance_type: str,
        image_id: str | None = None,
        control_plane_uri: str | None = None,
        cluster_id: int | None = None,
        bootstrap_token: str | None = None,
    ) -> dict[str, Any]:
        """Launch the single coordinator node for a cluster."""

    def create_worker_launch_template(
        self,
        *,
        region: str,
        security_group_ids: list[str],
        node_instance_profile: str,
        cluster: dict[str, Any],
        instance_type: str,
        image_id: str | None = None,
        coordinator_uri: str | None = None,
        control_plane_uri: str | None = None,
        cluster_id: int | None = None,
        bootstrap_token: str | None = None,
    ) -> dict[str, Any]:
        """Create the reusable template workers are launched from."""

    def create_worker_auto_scaling_group(
        self,
        *,
        region: str,
        subnet_ids: list[str],
        cluster: dict[str, Any],
        launch_template_id: str,
    ) -> dict[str, Any]:
        """Create the managed group that runs and scales the worker fleet."""

    def worker_auto_scaling_group(self, *, region: str, name: str) -> dict[str, Any]:
        """Describe the current state of a cluster's worker group."""

    def set_worker_desired_capacity(
        self,
        *,
        region: str,
        name: str,
        desired_capacity: int,
        min_size: int,
        max_size: int,
    ) -> dict[str, Any]:
        """Resize the worker fleet (autoscaling / manual scale / suspend to zero)."""

    def delete_worker_auto_scaling_group(self, *, region: str, name: str) -> dict[str, Any]:
        """Tear down a cluster's worker group."""

    def terminate_instances(self, *, region: str, instance_ids: list[str]) -> dict[str, Any]:
        """Terminate specific nodes (e.g. the coordinator) by id."""

    def delete_launch_template(self, *, region: str, launch_template_id: str) -> dict[str, Any]:
        """Delete a worker launch template during teardown."""

    def wait_for_cluster_instances_gone(
        self,
        *,
        region: str,
        cluster_name: str,
        timeout_seconds: int = 90,
        poll_seconds: int = 5,
    ) -> dict[str, Any]:
        """Block until a cluster's nodes have fully terminated (so SGs can be freed)."""

    # -- Metrics for autoscaling -------------------------------------------------------
    def worker_cpu_average(
        self,
        *,
        region: str,
        instance_ids: list[str],
        lookback_minutes: int = 5,
        period_seconds: int = 60,
    ) -> float | None:
        """Average worker CPU used to drive scale-up/scale-down decisions."""

    # -- Trino runtime (provider-neutral; see module docstring) ------------------------
    def trino_node_config_script(
        self,
        *,
        cluster: dict[str, Any],
        node_role: str,
        region: str,
        instance_type: str | None = None,
        coordinator_uri: str | None = None,
        secret_resolver: Callable[[str], str] | None = None,
        drivers: list[dict[str, Any]] | None = None,
        control_plane_uri: str | None = None,
        cluster_id: int | None = None,
        bootstrap_token: str | None = None,
    ) -> str:
        """Render the Trino node config a booting node fetches from the control plane."""

    def coordinator_health(
        self, *, coordinator_endpoint: str, timeout_seconds: int = 3
    ) -> dict[str, Any]:
        """Probe a coordinator's HTTP health endpoint."""

    def trino_cluster_stats(
        self, *, coordinator_endpoint: str, timeout_seconds: int = 3
    ) -> dict[str, Any]:
        """Read live query/queue stats from a coordinator for autoscaling."""
