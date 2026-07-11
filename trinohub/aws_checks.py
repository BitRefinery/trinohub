from __future__ import annotations

import base64
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from urllib.parse import quote

from .connectors import REGISTRY, ConnectorType


IMDS_BASE = "http://169.254.169.254/latest"
# Static fallback for the Trino versions offered in the Create-cluster picker,
# newest first. The first entry is the default for new clusters and the
# fallback for older cluster records that predate per-cluster version pinning.
# Node bootstrap downloads the chosen version's release tarball from GitHub.
# The control plane normally *discovers* newer releases live from Maven Central
# (see fetch_published_trino_versions); this list keeps air-gapped or offline
# deployments working and pins the floor of what discovery will offer.
SUPPORTED_TRINO_VERSIONS = ["482", "481", "480", "479"]
TRINO_VERSION = SUPPORTED_TRINO_VERSIONS[0]
TRINO_HTTP_PORT = 8080

# Discovery source: the GitHub releases API for trinodb/trino — the same place
# node bootstrap downloads the server tarball from, so anything listed here is
# installable. (Maven Central is NOT usable: trino-server publishing there
# stopped at 476.) Unauthenticated GitHub API calls are rate-limited to
# 60/hour/IP, which the control plane's multi-hour cache stays far under.
TRINO_RELEASES_URL = "https://api.github.com/repos/trinodb/trino/releases?per_page=25"
# Discovery never offers anything older than the static floor, and caps the
# picker to a manageable number of recent releases.
MIN_OFFERED_TRINO_VERSION = int(SUPPORTED_TRINO_VERSIONS[-1])
MAX_OFFERED_TRINO_VERSIONS = 8


def fetch_published_trino_versions(timeout_seconds: float = 5.0) -> list[str]:
    """Numeric Trino releases published on GitHub, newest first, floored at
    MIN_OFFERED_TRINO_VERSION and capped at MAX_OFFERED_TRINO_VERSIONS.
    Raises on network or parse failure; callers fall back to the static list."""
    request = urllib.request.Request(
        TRINO_RELEASES_URL,
        headers={"User-Agent": "TrinoHub", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        releases = json.loads(response.read().decode("utf-8", "replace"))
    published = {
        int(tag)
        for release in releases
        for tag in [str(release.get("tag_name") or "").strip()]
        if re.fullmatch(r"[0-9]{1,6}", tag) and not release.get("draft") and not release.get("prerelease")
    }
    offered = sorted((v for v in published if v >= MIN_OFFERED_TRINO_VERSION), reverse=True)
    return [str(v) for v in offered[:MAX_OFFERED_TRINO_VERSIONS]]


def resolve_trino_version(cluster: dict[str, Any]) -> str:
    """The Trino version to install for a cluster: its pinned ``trino_version``
    if set (any all-digit release number, so clusters pinned to a now-dropped
    version keep booting), else the current default. The digit check also keeps
    the value safe to interpolate into the download URL and shell script."""
    candidate = str(cluster.get("trino_version") or "").strip()
    return candidate if re.fullmatch(r"[0-9]{1,6}", candidate) else TRINO_VERSION

# A suspended/deleted worker ASG is removed asynchronously by AWS (it lingers in
# "pending delete"). Recreating the same name during that window fails, so the
# launch path waits this long, polling at the shorter interval, for it to clear.
ASG_RECREATE_WAIT_SECONDS = 180
ASG_RECREATE_POLL_SECONDS = 10

# System memory (GiB) for the instance types TrinoHub launches, used to size the
# Trino query-memory pools so a Power cluster actually uses its extra RAM. The
# JVM heap itself is sized relative to RAM via MaxRAMPercentage (see jvm.config),
# so only the absolute query.max-memory* values need this table.
INSTANCE_MEMORY_GB = {
    "m7i.large": 8, "m6i.large": 8, "m5.large": 8,
    "m7i.xlarge": 16, "m6i.xlarge": 16, "m5.xlarge": 16,
    "m7i.2xlarge": 32, "m6i.2xlarge": 32, "m5.2xlarge": 32,
    # Memory-optimized R-family types offered by the Settings instance picker.
    # Trino is memory-bound, so these are the community-recommended node types.
    "r7i.xlarge": 32, "r6i.xlarge": 32, "r5.xlarge": 32,
    "r7i.2xlarge": 64, "r6i.2xlarge": 64, "r5.2xlarge": 64,
    "r7i.4xlarge": 128, "r5.4xlarge": 128,
    # NVMe instance-store types for accelerated (file-system-cache) clusters.
    "i4i.large": 16, "i4i.xlarge": 32, "i4i.2xlarge": 64, "i4i.4xlarge": 128,
    "r6id.xlarge": 32, "r6id.2xlarge": 64,
    "i3en.xlarge": 32, "i3en.2xlarge": 64,
    # Legacy / fallback types kept for older cluster records.
    "t2.large": 8, "t3.large": 8, "t3.small": 2,
}
DEFAULT_INSTANCE_MEMORY_GB = 8

# Local NVMe instance-store capacity (GB) for the accelerated-cluster types.
# Only types listed here can host the Trino file system cache: the cache needs
# dedicated non-root SSD on every node (coordinator included), which the
# EBS-only families above don't have. i4i is the recommended default tier
# (same 8 GiB/vCPU shape as the R family, AWS Nitro SSDs); r6id is the budget
# tier and i3en the max-GB-per-dollar tier for cache-heavy workloads.
INSTANCE_STORE_GB = {
    "i4i.large": 468, "i4i.xlarge": 937, "i4i.2xlarge": 1875, "i4i.4xlarge": 3750,
    "r6id.xlarge": 237, "r6id.2xlarge": 474,
    "i3en.xlarge": 2500, "i3en.2xlarge": 5000,
}
# Number of physical instance-store disks; used to render one cache directory
# per disk. Types not listed have a single disk.
INSTANCE_STORE_DISKS = {"i3en.2xlarge": 2}
# Portion of each cache disk the Trino file system cache may fill, split
# evenly across the cached catalogs on a cluster (fs.cache eviction keeps each
# catalog's share under its limit). The remainder is slack for XFS metadata.
INSTANCE_STORE_CACHE_BUDGET_PCT = 90
# Instance-store devices are mounted here by the node bootstrap, one
# subdirectory per disk (disk0, disk1, ...), then one per catalog below that.
TRINO_CACHE_MOUNT_ROOT = "/mnt/trino-cache"


def instance_store_disks(instance_type: str) -> int:
    """Local NVMe disk count for an instance type; 0 = EBS-only (no cache)."""
    if instance_type not in INSTANCE_STORE_GB:
        return 0
    return INSTANCE_STORE_DISKS.get(instance_type, 1)

# vCPU count per instance type, used only for the Settings instance-picker labels.
INSTANCE_VCPU = {
    "m7i.large": 2, "m6i.large": 2, "m5.large": 2,
    "m7i.xlarge": 4, "m6i.xlarge": 4, "m5.xlarge": 4,
    "m7i.2xlarge": 8, "m6i.2xlarge": 8, "m5.2xlarge": 8,
    "r7i.xlarge": 4, "r6i.xlarge": 4, "r5.xlarge": 4,
    "r7i.2xlarge": 8, "r6i.2xlarge": 8, "r5.2xlarge": 8,
    "r7i.4xlarge": 16, "r5.4xlarge": 16,
    "i4i.large": 2, "i4i.xlarge": 4, "i4i.2xlarge": 8, "i4i.4xlarge": 16,
    "r6id.xlarge": 4, "r6id.2xlarge": 8,
    "i3en.xlarge": 4, "i3en.2xlarge": 8,
    "t2.large": 2, "t3.large": 2, "t3.small": 2,
}
DEFAULT_INSTANCE_VCPU = 2

# Approximate on-demand USD/hour (us-east-2, Linux). Used only for the cost
# estimate tiles in the UI; treated as indicative, never billed against. Keep in
# sync with PRESET_INSTANCE_CANDIDATES so every resolvable preset has a price.
INSTANCE_HOURLY_USD = {
    "m7i.large": 0.1008, "m6i.large": 0.0960, "m5.large": 0.0960,
    "m7i.xlarge": 0.2016, "m6i.xlarge": 0.1920, "m5.xlarge": 0.1920,
    "m7i.2xlarge": 0.4032, "m6i.2xlarge": 0.3840, "m5.2xlarge": 0.3840,
    "r7i.xlarge": 0.2646, "r6i.xlarge": 0.2520, "r5.xlarge": 0.2520,
    "r7i.2xlarge": 0.5292, "r6i.2xlarge": 0.5040, "r5.2xlarge": 0.5040,
    "r7i.4xlarge": 1.0584, "r5.4xlarge": 1.0080,
    "i4i.large": 0.172, "i4i.xlarge": 0.343, "i4i.2xlarge": 0.686, "i4i.4xlarge": 1.373,
    "r6id.xlarge": 0.3024, "r6id.2xlarge": 0.6048,
    "i3en.xlarge": 0.452, "i3en.2xlarge": 0.904,
    "t2.large": 0.0928, "t3.large": 0.0832, "t3.small": 0.0208,
}
DEFAULT_INSTANCE_HOURLY_USD = 0.10


def _paginate(client: Any, operation: str, result_key: str) -> list[dict[str, Any]]:
    """Collect every page of a boto3 describe-* call.

    Uses the operation's paginator so large accounts aren't capped at a single
    MaxResults page. Falls back to a single un-paginated call for clients that
    don't expose a paginator (e.g. test fakes).
    """
    try:
        can_paginate = client.can_paginate(operation)
    except Exception:  # fakes may not implement can_paginate
        can_paginate = False
    if not can_paginate:
        return getattr(client, operation)().get(result_key, [])
    items: list[dict[str, Any]] = []
    for page in client.get_paginator(operation).paginate():
        items.extend(page.get(result_key, []))
    return items


def trino_memory_settings(instance_type: str) -> dict[str, int]:
    """Derive Trino JVM heap + query-memory settings (in GiB) from an instance type.

    The JVM heap is pinned explicitly in jvm.config (``-Xmx``/``-Xms`` = ``heap_gb``)
    rather than via ``MaxRAMPercentage`` of *available* RAM, so the heap is
    deterministic and matches the value these query-memory settings are sized
    against. Trino refuses to start unless
    ``query.max-memory-per-node + memory.heap-headroom-per-node <= max heap``;
    sizing per-node to consume the *entire* heap (the previous behaviour) left no
    slack and failed on larger instances where actual free RAM was below nominal.
    We therefore keep that sum strictly below the heap with a safety margin.
    """
    ram_gb = INSTANCE_MEMORY_GB.get(instance_type, DEFAULT_INSTANCE_MEMORY_GB)
    heap_gb = max(2, int(ram_gb * 0.7))
    headroom_gb = max(1, int(heap_gb * 0.3))
    # Reserve headroom plus >=1 GiB of slack so query.max-memory-per-node +
    # heap-headroom stays comfortably under the heap (Trino's startup check).
    per_node_gb = max(1, heap_gb - headroom_gb - 1)
    return {
        "ram_gb": ram_gb,
        "heap_gb": heap_gb,
        "heap_headroom_gb": headroom_gb,
        "query_max_memory_per_node_gb": per_node_gb,
        "query_max_memory_gb": per_node_gb * 2,
    }


@dataclass
class AwsCheck:
    name: str
    ok: bool
    detail: str


class AwsInspector:
    def __init__(self, region: str | None = None) -> None:
        self.region = region or self.metadata().get("region") or "us-east-2"

    def _imds_token(self) -> str:
        try:
            request = urllib.request.Request(
                f"{IMDS_BASE}/api/token",
                method="PUT",
                headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
            )
            with urllib.request.urlopen(request, timeout=2) as response:
                return response.read().decode("utf-8")
        except Exception:
            return ""

    def _imds_get(self, path: str, token: str) -> str:
        if not token:
            return ""
        try:
            request = urllib.request.Request(f"{IMDS_BASE}{path}", headers={"X-aws-ec2-metadata-token": token})
            with urllib.request.urlopen(request, timeout=2) as response:
                return response.read().decode("utf-8")
        except Exception:
            return ""

    def metadata(self) -> dict[str, Any]:
        token = self._imds_token()
        if not token:
            return {"available": False}

        def get_text(path: str) -> str:
            return self._imds_get(path, token)

        identity_raw = get_text("/dynamic/instance-identity/document")
        identity = {}
        if identity_raw:
            try:
                identity = json.loads(identity_raw)
            except json.JSONDecodeError:
                identity = {}
        return {
            "available": True,
            "instance_id": get_text("/meta-data/instance-id"),
            "role": get_text("/meta-data/iam/security-credentials/"),
            "region": identity.get("region", ""),
            "account_id": identity.get("accountId", ""),
        }

    def control_plane_security_group_ids(self) -> list[str]:
        """Security groups attached to the control-plane instance, via IMDS."""
        token = self._imds_token()
        if not token:
            return []
        macs = [
            mac.strip().strip("/")
            for mac in self._imds_get("/meta-data/network/interfaces/macs/", token).splitlines()
            if mac.strip()
        ]
        group_ids: list[str] = []
        for mac in macs:
            raw = self._imds_get(f"/meta-data/network/interfaces/macs/{mac}/security-group-ids", token)
            for group_id in raw.splitlines():
                group_id = group_id.strip()
                if group_id and group_id not in group_ids:
                    group_ids.append(group_id)
        return group_ids

    def control_plane_private_ip(self) -> str | None:
        token = self._imds_token()
        if not token:
            return None
        ip = self._imds_get("/meta-data/local-ipv4", token).strip()
        return ip or None

    def clients(self, region: str | None = None) -> dict[str, Any]:
        import boto3

        selected_region = region or self.region
        return {
            "sts": boto3.client("sts", region_name=selected_region),
            "ec2": boto3.client("ec2", region_name=selected_region),
            "autoscaling": boto3.client("autoscaling", region_name=selected_region),
            "cloudwatch": boto3.client("cloudwatch", region_name=selected_region),
            "secretsmanager": boto3.client("secretsmanager", region_name=selected_region),
        }

    def full_status(self, region: str | None = None) -> dict[str, Any]:
        selected_region = region or self.region
        clients = self.clients(selected_region)
        checks: list[dict[str, Any]] = []
        identity: dict[str, Any] = {}
        network: dict[str, Any] = {"vpcs": [], "subnets": [], "security_groups": []}

        def run(name: str, fn):
            try:
                detail = fn()
                checks.append({"name": name, "ok": True, "detail": detail})
            except Exception as exc:
                checks.append({"name": name, "ok": False, "detail": f"{type(exc).__name__}: {exc}"})

        def check_identity() -> str:
            nonlocal identity
            raw_identity = clients["sts"].get_caller_identity()
            identity = {
                "UserId": raw_identity.get("UserId", ""),
                "Account": raw_identity.get("Account", ""),
                "Arn": raw_identity.get("Arn", ""),
            }
            return identity.get("Arn", "")

        def check_vpcs() -> str:
            data = _paginate(clients["ec2"], "describe_vpcs", "Vpcs")
            network["vpcs"] = [
                {"vpc_id": item["VpcId"], "cidr": item.get("CidrBlock", ""), "is_default": item.get("IsDefault", False)}
                for item in data
            ]
            return f"{len(data)} VPCs visible"

        def check_subnets() -> str:
            data = _paginate(clients["ec2"], "describe_subnets", "Subnets")
            network["subnets"] = [
                {
                    "subnet_id": item["SubnetId"],
                    "vpc_id": item["VpcId"],
                    "az": item["AvailabilityZone"],
                    "cidr": item["CidrBlock"],
                    "public_ip_default": bool(item.get("MapPublicIpOnLaunch")),
                }
                for item in data
            ]
            return f"{len(data)} subnets visible"

        def check_security_groups() -> str:
            data = _paginate(clients["ec2"], "describe_security_groups", "SecurityGroups")
            network["security_groups"] = [
                {"group_id": item["GroupId"], "vpc_id": item.get("VpcId", ""), "name": item.get("GroupName", "")}
                for item in data
            ]
            return f"{len(data)} security groups visible"

        run("sts:GetCallerIdentity", check_identity)
        run("ec2:DescribeVpcs", check_vpcs)
        run("ec2:DescribeSubnets", check_subnets)
        run("ec2:DescribeSecurityGroups", check_security_groups)
        run(
            "autoscaling:DescribeAutoScalingGroups",
            lambda: f"{len(clients['autoscaling'].describe_auto_scaling_groups(MaxRecords=20)['AutoScalingGroups'])} groups visible",
        )
        run(
            "cloudwatch:ListMetrics",
            lambda: f"{len(clients['cloudwatch'].list_metrics(Namespace='AWS/EC2').get('Metrics', []))} EC2 metrics returned",
        )

        return {
            "region": selected_region,
            "metadata": self.metadata(),
            "identity": identity,
            "network": network,
            "checks": checks,
            "ok": all(check["ok"] for check in checks),
        }

    def latest_ubuntu_ami(self, region: str | None = None) -> str:
        ec2 = self.clients(region)["ec2"]
        images = ec2.describe_images(
            Owners=["099720109477"],
            Filters=[
                {"Name": "name", "Values": ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]},
                {"Name": "state", "Values": ["available"]},
                {"Name": "architecture", "Values": ["x86_64"]},
                {"Name": "root-device-type", "Values": ["ebs"]},
                {"Name": "virtualization-type", "Values": ["hvm"]},
            ],
        )["Images"]
        images.sort(key=lambda item: item["CreationDate"], reverse=True)
        if not images:
            raise RuntimeError("No Ubuntu 24.04 AMI found.")
        return images[0]["ImageId"]

    def available_instance_types(self, region: str, instance_types: list[str]) -> list[str]:
        """Return the subset of ``instance_types`` offered in ``region``.

        Preserves the input order so callers can treat the result as a
        preference-ordered list.
        """
        ec2 = self.clients(region)["ec2"]
        offered: set[str] = set()
        paginator = ec2.get_paginator("describe_instance_type_offerings")
        for page in paginator.paginate(
            LocationType="region",
            Filters=[{"Name": "instance-type", "Values": list(instance_types)}],
        ):
            for offering in page.get("InstanceTypeOfferings", []):
                offered.add(offering["InstanceType"])
        return [item for item in instance_types if item in offered]

    def dry_run_instance_launch(
        self,
        *,
        region: str,
        subnet_id: str,
        node_instance_profile: str,
        instance_type: str = "t3.small",
        image_id: str | None = None,
    ) -> dict[str, Any]:
        from botocore.exceptions import ClientError

        ami = image_id or self.latest_ubuntu_ami(region)
        ec2 = self.clients(region)["ec2"]
        try:
            ec2.run_instances(
                ImageId=ami,
                InstanceType=instance_type,
                MinCount=1,
                MaxCount=1,
                SubnetId=subnet_id,
                IamInstanceProfile={"Name": node_instance_profile},
                TagSpecifications=[
                    {
                        "ResourceType": "instance",
                        "Tags": [
                            {"Key": "ManagedBy", "Value": "TrinoHub"},
                            {"Key": "TrinoHubDryRun", "Value": "true"},
                        ],
                    }
                ],
                DryRun=True,
            )
            return {"ok": True, "detail": "Unexpected success without DryRunOperation", "image_id": ami}
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            message = exc.response.get("Error", {}).get("Message", "")
            return {"ok": code == "DryRunOperation", "code": code, "detail": message, "image_id": ami}

    def ensure_managed_security_group(self, *, region: str, vpc_id: str, cluster_name: str) -> dict[str, Any]:
        from botocore.exceptions import ClientError

        ec2 = self.clients(region)["ec2"]
        group_name = f"trinohub-{cluster_name}-nodes"
        existing = ec2.describe_security_groups(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
                {"Name": "group-name", "Values": [group_name]},
            ]
        ).get("SecurityGroups", [])
        if existing:
            group_id = existing[0]["GroupId"]
            created = False
            ec2.create_tags(
                Resources=[group_id],
                Tags=[
                    {"Key": "Name", "Value": group_name},
                    {"Key": "ManagedBy", "Value": "TrinoHub"},
                    {"Key": "TrinoHubCluster", "Value": cluster_name},
                ],
            )
        else:
            response = ec2.create_security_group(
                GroupName=group_name,
                Description=f"TrinoHub managed nodes for {cluster_name}",
                VpcId=vpc_id,
                TagSpecifications=[
                    {
                        "ResourceType": "security-group",
                        "Tags": [
                            {"Key": "Name", "Value": group_name},
                            {"Key": "ManagedBy", "Value": "TrinoHub"},
                            {"Key": "TrinoHubCluster", "Value": cluster_name},
                        ],
                    }
                ],
            )
            group_id = response["GroupId"]
            created = True
        try:
            ec2.authorize_security_group_ingress(
                GroupId=group_id,
                IpPermissions=[
                    {
                        "IpProtocol": "-1",
                        "UserIdGroupPairs": [{"GroupId": group_id, "Description": "TrinoHub cluster node traffic"}],
                    }
                ],
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code != "InvalidPermission.Duplicate":
                raise
        control_plane_ingress = self.authorize_control_plane_ingress(ec2, group_id)
        node_to_control_plane_ingress = self.authorize_nodes_to_control_plane(ec2, group_id)
        return {
            "group_id": group_id,
            "created": created,
            "group_name": group_name,
            "control_plane_ingress": control_plane_ingress,
            "node_to_control_plane_ingress": node_to_control_plane_ingress,
        }

    def authorize_control_plane_ingress(self, ec2: Any, group_id: str) -> dict[str, Any]:
        """Allow the control-plane instance to reach the coordinator HTTP port.

        The node security group only permits traffic from itself, so the control
        plane (a separate instance) cannot poll health or submit SQL unless it is
        explicitly allowed. Prefer the control-plane security group(s); fall back to
        its private IP /32 when the security group reference is unusable (for example
        across VPCs).
        """
        from botocore.exceptions import ClientError

        def attempt(ip_permissions: list[dict[str, Any]]) -> tuple[bool, str | None]:
            try:
                ec2.authorize_security_group_ingress(GroupId=group_id, IpPermissions=ip_permissions)
                return True, None
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code == "InvalidPermission.Duplicate":
                    return True, "duplicate"
                return False, code

        port_range = {"IpProtocol": "tcp", "FromPort": TRINO_HTTP_PORT, "ToPort": TRINO_HTTP_PORT}

        security_group_ids = self.control_plane_security_group_ids()
        if security_group_ids:
            ok, note = attempt(
                [
                    {
                        **port_range,
                        "UserIdGroupPairs": [
                            {"GroupId": sg_id, "Description": "TrinoHub control plane to coordinator"}
                            for sg_id in security_group_ids
                        ],
                    }
                ]
            )
            if ok:
                return {"authorized": True, "via": "security_group", "group_ids": security_group_ids, "note": note}

        private_ip = self.control_plane_private_ip()
        if private_ip:
            cidr = f"{private_ip}/32"
            ok, note = attempt(
                [
                    {
                        **port_range,
                        "IpRanges": [{"CidrIp": cidr, "Description": "TrinoHub control plane to coordinator"}],
                    }
                ]
            )
            if ok:
                return {"authorized": True, "via": "cidr", "cidr": cidr, "note": note}

        return {
            "authorized": False,
            "reason": "Control-plane network not discoverable via IMDS; allow TCP "
            f"{TRINO_HTTP_PORT} from the control plane to the node security group manually.",
        }

    def authorize_nodes_to_control_plane(
        self,
        ec2: Any,
        node_group_id: str,
        *,
        port: int = 8000,
    ) -> dict[str, Any]:
        """Allow cluster nodes to fetch signed config from the control plane."""
        from botocore.exceptions import ClientError

        control_plane_group_ids = self.control_plane_security_group_ids()
        if not control_plane_group_ids:
            return {
                "authorized": False,
                "reason": "Control-plane security group not discoverable via IMDS; allow node SG access manually.",
            }

        authorized: list[str] = []
        duplicates: list[str] = []
        failed: list[dict[str, str]] = []
        for target_group_id in control_plane_group_ids:
            try:
                ec2.authorize_security_group_ingress(
                    GroupId=target_group_id,
                    IpPermissions=[
                        {
                            "IpProtocol": "tcp",
                            "FromPort": port,
                            "ToPort": port,
                            "UserIdGroupPairs": [
                                {
                                    "GroupId": node_group_id,
                                    "Description": "TrinoHub nodes fetch signed config",
                                }
                            ],
                        }
                    ],
                )
                authorized.append(target_group_id)
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code == "InvalidPermission.Duplicate":
                    duplicates.append(target_group_id)
                else:
                    failed.append({"group_id": target_group_id, "code": code})
        return {
            "authorized": bool(authorized or duplicates),
            "target_group_ids": control_plane_group_ids,
            "node_group_id": node_group_id,
            "port": port,
            "duplicates": duplicates,
            "failed": failed,
        }

    def trino_environment_name(self, cluster_name: str) -> str:
        normalized = re.sub(r"[^a-z0-9_]+", "_", cluster_name.lower()).strip("_")
        if not normalized or not normalized[0].isalnum():
            normalized = f"trinohub_{normalized}"
        return normalized[:64]

    def fs_cache_catalog_names(
        self,
        catalogs: list[str],
        catalog_configs: list[dict[str, Any]] | None,
    ) -> list[str]:
        """Attached catalogs eligible for the Trino file system cache: the
        S3/Glue family (Hive, Iceberg, Delta Lake) minus Hudi, which upstream
        does not support caching for."""
        names = []
        for catalog in catalog_configs or []:
            name = str(catalog.get("name", ""))
            if name not in catalogs or not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", name):
                continue
            if not catalog.get("enabled", True):
                continue
            spec = REGISTRY.get(catalog.get("type"))
            if spec is None or spec.kind != "s3_glue":
                continue
            if (spec.connector_name or "iceberg") == "hudi":
                continue
            names.append(name)
        return names

    def fs_cache_layout(
        self,
        catalogs: list[str],
        catalog_configs: list[dict[str, Any]] | None,
        cache_disks: int,
    ) -> dict[str, dict[str, Any]]:
        """Per-catalog fs.cache.* layout for an accelerated cluster.

        Each cacheable catalog gets its own directory on every instance-store
        disk (upstream requires distinct directories per catalog), and the
        disk-usage budget is split evenly across the cached catalogs so their
        combined caches never fill the disk.
        """
        if cache_disks < 1:
            return {}
        cached = self.fs_cache_catalog_names(catalogs, catalog_configs)
        if not cached:
            return {}
        usage_pct = max(1, INSTANCE_STORE_CACHE_BUDGET_PCT // len(cached))
        return {
            name: {
                "directories": [
                    f"{TRINO_CACHE_MOUNT_ROOT}/disk{disk}/{name}" for disk in range(cache_disks)
                ],
                "usage_pct": usage_pct,
            }
            for name in cached
        }

    def catalog_config_files(
        self,
        catalogs: list[str],
        catalog_configs: list[dict[str, Any]] | None = None,
        secret_resolver: Callable[[str], str] | None = None,
        cache_disks: int = 0,
    ) -> dict[str, str]:
        configs = {}
        cache_layout = self.fs_cache_layout(catalogs, catalog_configs, cache_disks)
        if cache_layout:
            # Accelerated clusters carry the built-in jmx connector so the
            # control plane can sample AlluxioCacheStats hit/miss metrics.
            configs["jmx"] = "connector.name=jmx\n"
        if "tpch" in catalogs:
            configs["tpch"] = "connector.name=tpch\n"
        if "tpcds" in catalogs:
            configs["tpcds"] = "connector.name=tpcds\n"
        for catalog in catalog_configs or []:
            name = str(catalog.get("name", ""))
            if name not in catalogs or not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", name):
                continue
            if not catalog.get("enabled", True):
                continue
            spec = REGISTRY.get(catalog.get("type"))
            if spec is None:
                continue
            if spec.kind == "s3_glue":
                configs[name] = self.glue_catalog_properties(catalog, spec, fs_cache=cache_layout.get(name))
            elif spec.kind == "jdbc":
                configs[name] = self.jdbc_catalog_properties(catalog, secret_resolver)
            elif spec.kind == "mongodb":
                configs[name] = self.mongodb_catalog_properties(catalog, secret_resolver)
            elif spec.kind == "elasticsearch":
                configs[name] = self.elasticsearch_catalog_properties(catalog, secret_resolver)
            elif spec.kind == "bigquery":
                configs[name] = self.bigquery_catalog_properties(catalog, secret_resolver)
            elif spec.kind == "gsheets":
                configs[name] = self.gsheets_catalog_properties(catalog, secret_resolver)
            elif spec.kind == "cassandra":
                configs[name] = self.cassandra_catalog_properties(catalog, secret_resolver)
            elif spec.kind == "prometheus":
                configs[name] = self.prometheus_catalog_properties(catalog, secret_resolver)
            elif spec.kind == "generator":
                configs[name] = self.generator_catalog_properties(catalog)
        return configs

    def _require_resolved_secret(
        self, catalog: dict[str, Any], secret_resolver: Callable[[str], str] | None
    ) -> str:
        secret_ref = str(catalog.get("config", {}).get("password_secret_ref") or "")
        if not secret_ref or secret_resolver is None:
            # Credentialed catalogs only render on the signed node-config path, where
            # the control plane resolves the secret. They must never be embedded into
            # EC2 user-data with a plaintext (or missing) password.
            raise RuntimeError(
                f"Catalog {catalog.get('name')} requires the signed node-config bootstrap "
                "to resolve its credential; the control plane URI must be configured."
            )
        return secret_resolver(secret_ref)

    def mongodb_catalog_properties(
        self, catalog: dict[str, Any], secret_resolver: Callable[[str], str] | None
    ) -> str:
        config = catalog.get("config", {})
        connection_url = str(config["connection_url"])  # mongodb://host[:port][/db], no creds
        connection_user = str(config["connection_user"])
        password = self._require_resolved_secret(catalog, secret_resolver)
        # MongoDB authenticates via credentials embedded in the connection URL, so
        # inject them after the scheme at render time (URL-encoded). The stored
        # config never contains the password.
        scheme, _, rest = connection_url.partition("://")
        auth_url = f"{scheme}://{quote(connection_user, safe='')}:{quote(password, safe='')}@{rest}"
        lines = [
            "connector.name=mongodb",
            f"mongodb.connection-url={auth_url}",
        ]
        return "\n".join(lines) + "\n"

    def elasticsearch_catalog_properties(
        self, catalog: dict[str, Any], secret_resolver: Callable[[str], str] | None
    ) -> str:
        config = catalog.get("config", {})
        # Elasticsearch and OpenSearch share this renderer; the property prefix and
        # connector.name are the stored connector_name (elasticsearch | opensearch).
        prefix = str(config.get("connector_name") or "elasticsearch")
        password = self._require_resolved_secret(catalog, secret_resolver)
        lines = [
            f"connector.name={prefix}",
            f"{prefix}.host={config['host']}",
            f"{prefix}.port={config.get('port', 9200)}",
            f"{prefix}.default-schema-name={config.get('default_schema', 'default')}",
            f"{prefix}.security=PASSWORD",
            f"{prefix}.auth.user={config['connection_user']}",
            f"{prefix}.auth.password={password}",
        ]
        return "\n".join(lines) + "\n"

    def bigquery_catalog_properties(
        self, catalog: dict[str, Any], secret_resolver: Callable[[str], str] | None
    ) -> str:
        config = catalog.get("config", {})
        credentials_json = self._require_resolved_secret(catalog, secret_resolver)
        # BigQuery authenticates with a service-account JSON key. Trino accepts it
        # base64-encoded inline via bigquery.credentials-key, so the key never lands
        # on disk as a separate file and stays inside the signed node-config payload.
        key_b64 = base64.b64encode(credentials_json.encode("utf-8")).decode("ascii")
        lines = [
            "connector.name=bigquery",
            f"bigquery.project-id={config['project_id']}",
            f"bigquery.credentials-key={key_b64}",
        ]
        if config.get("parent_project_id"):
            lines.append(f"bigquery.parent-project-id={config['parent_project_id']}")
        return "\n".join(lines) + "\n"

    def gsheets_catalog_properties(
        self, catalog: dict[str, Any], secret_resolver: Callable[[str], str] | None
    ) -> str:
        config = catalog.get("config", {})
        credentials_json = self._require_resolved_secret(catalog, secret_resolver)
        key_b64 = base64.b64encode(credentials_json.encode("utf-8")).decode("ascii")
        lines = [
            "connector.name=gsheets",
            f"gsheets.credentials-key={key_b64}",
            f"gsheets.metadata-sheet-id={config['metadata_sheet_id']}",
        ]
        return "\n".join(lines) + "\n"

    def cassandra_catalog_properties(
        self, catalog: dict[str, Any], secret_resolver: Callable[[str], str] | None
    ) -> str:
        config = catalog.get("config", {})
        lines = [
            "connector.name=cassandra",
            f"cassandra.contact-points={config['contact_points']}",
            f"cassandra.native-protocol-port={config.get('port', 9042)}",
        ]
        connection_user = str(config.get("connection_user") or "")
        if connection_user:
            # Authenticated cluster: resolve the password on the signed node path so
            # it never lands in EC2 user-data. Unauthenticated Cassandra has no
            # secret and renders on either path (like the S3/Glue family).
            password = self._require_resolved_secret(catalog, secret_resolver)
            lines.append(f"cassandra.username={connection_user}")
            lines.append(f"cassandra.password={password}")
        return "\n".join(lines) + "\n"

    def prometheus_catalog_properties(
        self, catalog: dict[str, Any], secret_resolver: Callable[[str], str] | None
    ) -> str:
        config = catalog.get("config", {})
        lines = [
            "connector.name=prometheus",
            f"prometheus.uri={config['uri']}",
        ]
        connection_user = str(config.get("connection_user") or "")
        if connection_user:
            # Basic-auth server: resolve the password on the signed node path only,
            # so it never lands in EC2 user-data. An open server has no secret and
            # renders on either path.
            password = self._require_resolved_secret(catalog, secret_resolver)
            lines.append(f"prometheus.auth.user={connection_user}")
            lines.append(f"prometheus.auth.password={password}")
        return "\n".join(lines) + "\n"

    def generator_catalog_properties(self, catalog: dict[str, Any]) -> str:
        # memory / blackhole / faker are zero-config: connector.name is the whole
        # file. No secret, no reachability, nothing to inject.
        connector_name = str(catalog.get("config", {}).get("connector_name") or "")
        return f"connector.name={connector_name}\n"

    def jdbc_catalog_properties(
        self, catalog: dict[str, Any], secret_resolver: Callable[[str], str] | None
    ) -> str:
        config = catalog.get("config", {})
        connector_name = str(config.get("connector_name") or "postgresql")
        connection_url = str(config["connection_url"])
        connection_user = str(config["connection_user"])
        secret_ref = str(config.get("password_secret_ref") or "")
        if not secret_ref or secret_resolver is None:
            # Credentialed catalogs only render on the signed node-config path, where
            # the control plane resolves the secret. They must never be embedded into
            # EC2 user-data with a plaintext (or missing) password.
            raise RuntimeError(
                f"Catalog {catalog.get('name')} requires the signed node-config bootstrap "
                "to resolve its credential; the control plane URI must be configured."
            )
        password = secret_resolver(secret_ref)
        lines = [
            f"connector.name={connector_name}",
            f"connection-url={connection_url}",
            f"connection-user={connection_user}",
            f"connection-password={password}",
        ]
        return "\n".join(lines) + "\n"

    def glue_catalog_properties(
        self,
        catalog: dict[str, Any],
        spec: ConnectorType,
        fs_cache: dict[str, Any] | None = None,
    ) -> str:
        # S3/Glue family renderer: Iceberg, Delta Lake, and Hive share the Glue
        # metastore + s3.* block and differ only in connector.name, the metastore
        # selector, and each connector's own read-only security key.
        config = catalog.get("config", {})
        connector_name = spec.connector_name or "iceberg"
        glue_region = str(config["glue_region"])
        s3_region = str(config.get("s3_region") or glue_region)
        warehouse = str(config["warehouse"])
        file_format = str(config.get("file_format") or "PARQUET").upper()
        read_only = str(config.get("access_mode") or "read_write") == "read_only"

        lines = [f"connector.name={connector_name}"]
        if connector_name == "iceberg":
            # Iceberg selects Glue via iceberg.catalog.type; Hive/Delta use hive.metastore.
            lines.append("iceberg.catalog.type=glue")
        else:
            lines.append("hive.metastore=glue")
        lines += [
            f"hive.metastore.glue.region={glue_region}",
            f"hive.metastore.glue.default-warehouse-dir={warehouse}",
            "fs.s3.enabled=true",
            f"s3.region={s3_region}",
        ]
        if connector_name == "iceberg":
            lines.append(f"iceberg.file-format={file_format}")
            lines.append(f"iceberg.security={'READ_ONLY' if read_only else 'ALLOW_ALL'}")
        elif connector_name == "delta_lake":
            lines.append(f"delta.security={'READ_ONLY' if read_only else 'ALLOW_ALL'}")
        elif connector_name == "hive":
            lines.append(f"hive.storage-format={file_format}")
            lines.append(f"hive.security={'read-only' if read_only else 'allow-all'}")
        # hudi is query-only in Trino: no writes, so no security/storage-format key.
        if fs_cache:
            # Accelerated cluster: cache hot S3 pages on the node-local NVMe
            # disks mounted by the bootstrap script. One value per directory.
            directories = list(fs_cache["directories"])
            usage = str(fs_cache["usage_pct"])
            lines += [
                "fs.cache.enabled=true",
                f"fs.cache.directories={','.join(directories)}",
                f"fs.cache.max-disk-usage-percentages={','.join([usage] * len(directories))}",
            ]
        return "\n".join(lines) + "\n"

    def default_key_name(self, region: str) -> str | None:
        """SSH key pair to attach to launched nodes, if one is configured.

        TrinoHub needs no SSH for normal operation — the control plane reaches
        coordinators over HTTP. Operators who want break-glass SSH set
        ``TRINOHUB_SSH_KEY_NAME`` to an existing EC2 key-pair name; it is attached
        only if that key actually exists in the region. Unset (the default) means
        no key, so a clean account launches without silently inheriting some
        pre-existing key pair.
        """
        import os

        configured = os.environ.get("TRINOHUB_SSH_KEY_NAME", "").strip()
        if not configured:
            return None
        try:
            key_pairs = self.clients(region)["ec2"].describe_key_pairs(KeyNames=[configured]).get("KeyPairs", [])
        except Exception:
            return None
        return configured if key_pairs else None

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
        access_control_rules: str | None = None,
    ) -> str:
        """Cluster-specific Trino config fetched by nodes via a signed URL."""
        trino_version = resolve_trino_version(cluster)
        memory = trino_memory_settings(instance_type or "")
        catalogs = [
            str(catalog)
            for catalog in cluster.get("catalogs", [])
            if re.fullmatch(r"[a-z][a-z0-9_]{0,62}", str(catalog))
        ]
        environment = self.trino_environment_name(str(cluster["name"]))
        discovery_uri = coordinator_uri or f"http://127.0.0.1:{TRINO_HTTP_PORT}"
        include_coordinator = "false"
        coordinator_flag = "true" if node_role == "coordinator" else "false"
        accelerated = bool(cluster.get("accelerated"))
        cache_disks = instance_store_disks(instance_type or "") if accelerated else 0
        cache_layout = self.fs_cache_layout(catalogs, cluster.get("catalog_configs", []), cache_disks)
        catalog_files = self.catalog_config_files(
            catalogs,
            cluster.get("catalog_configs", []),
            secret_resolver=secret_resolver,
            cache_disks=cache_disks,
        )
        catalog_commands = "\n".join(
            f"cat >/etc/trino/catalog/{name}.properties <<'EOF'\n{content}EOF"
            for name, content in catalog_files.items()
        )
        # Connectors whose driver JAR is not bundled (e.g. Oracle): download the
        # operator-uploaded JAR into the Trino plugin dir and verify its SHA-256
        # before Trino starts. `set -euo pipefail` aborts the boot if the hash
        # does not match, so a tampered or truncated driver never loads.
        driver_commands = ""
        if drivers and control_plane_uri and cluster_id and bootstrap_token:
            base = control_plane_uri.rstrip("/")
            blocks = []
            for driver in drivers:
                plugin_dir = str(driver["plugin_dir"])
                filename = str(driver["filename"])
                connector_type = str(driver["connector_type"])
                sha256 = str(driver["sha256"])
                dest = f"/opt/trino/plugin/{plugin_dir}/{filename}"
                url = f"{base}/api/node-config/{cluster_id}/driver/{connector_type}?token={bootstrap_token}"
                blocks.append(
                    f'install -d -m 0755 "/opt/trino/plugin/{plugin_dir}"\n'
                    f'curl --fail --location --retry 12 --retry-delay 10 "{url}" --output "{dest}"\n'
                    f'echo "{sha256}  {dest}" | sha256sum -c -\n'
                    f'chown -R "$TRINO_USER:$TRINO_USER" "/opt/trino/plugin/{plugin_dir}"'
                )
            driver_commands = "\n".join(blocks)
        # Accelerated clusters mount the local NVMe instance-store disks that back
        # the Trino file system cache. Runs on every node (the coordinator needs
        # read/write cache directories too, per upstream docs). Devices are matched
        # by the EC2 instance-storage ID prefix so EBS volumes are never touched.
        # Instance store attaches empty on every boot, so this always reformats and
        # the cache starts cold after a suspend/resume cycle.
        cache_commands = ""
        if cache_layout:
            cache_directories = " ".join(
                f'"{directory}"'
                for layout in cache_layout.values()
                for directory in layout["directories"]
            )
            cache_commands = f"""CACHE_ROOT="{TRINO_CACHE_MOUNT_ROOT}"
declare -A TRINOHUB_SEEN_CACHE_DEVICES
cache_disk_index=0
for link in /dev/disk/by-id/nvme-Amazon_EC2_NVMe_Instance_Storage_*; do
  [ -e "$link" ] || continue
  device="$(readlink -f "$link")"
  [ -n "${{TRINOHUB_SEEN_CACHE_DEVICES[$device]:-}}" ] && continue
  TRINOHUB_SEEN_CACHE_DEVICES[$device]=1
  mount_point="$CACHE_ROOT/disk${{cache_disk_index}}"
  install -d -m 0755 "$mount_point"
  if ! mountpoint -q "$mount_point"; then
    mkfs.xfs -f "$device"
    mount -o noatime "$device" "$mount_point"
  fi
  cache_disk_index=$((cache_disk_index + 1))
done
if [ "$cache_disk_index" -eq 0 ]; then
  echo "WARNING: accelerated cluster but no instance-store NVMe device found; cache falls back to the root disk." >&2
fi
for cache_directory in {cache_directories}; do
  install -d -m 0750 "$cache_directory"
done
chown -R "$TRINO_USER:$TRINO_USER" "$CACHE_ROOT"
"""
        # Fine-grained data policies: render Trino's file-based system access
        # control. Absent policies, no files are written and the engine stays
        # open (control-plane grants still gate the API).
        access_control_commands = ""
        if access_control_rules:
            access_control_commands = f"""cat >/etc/trino/rules.json <<'EOF'
{access_control_rules}
EOF
cat >/etc/trino/access-control.properties <<'EOF'
access-control.name=file
security.config-file=/etc/trino/rules.json
EOF"""
        enabled_catalogs = "\n".join(catalogs)
        return f"""#!/bin/bash
set -euo pipefail
TRINO_USER="${{TRINO_USER:-trino}}"
TRINO_INSTALL_DIR="${{TRINO_INSTALL_DIR:-/opt/trino-server-{trino_version}}}"

install -d -m 0755 /etc/trinohub
cat >/etc/trinohub/node.env <<'EOF'
TRINOHUB_CLUSTER={cluster["name"]}
TRINOHUB_NODE_ROLE={node_role}
TRINOHUB_REGION={region}
TRINOHUB_CATALOGS={",".join(catalogs)}
TRINOHUB_DISCOVERY_URI={discovery_uri}
EOF

cat >/etc/trinohub/enabled-catalogs <<'EOF'
{enabled_catalogs}
EOF

NODE_ID="$(cat /sys/devices/virtual/dmi/id/product_uuid 2>/dev/null || cat /etc/machine-id)"
cat >/etc/trino/node.properties <<EOF
node.environment={environment}
node.id=${{NODE_ID}}
node.data-dir=/var/lib/trino
EOF

cat >/etc/trino/jvm.config <<'EOF'
-server
-Xms{memory["heap_gb"]}G
-Xmx{memory["heap_gb"]}G
-XX:G1HeapRegionSize=32M
-XX:+ExplicitGCInvokesConcurrent
-XX:+ExitOnOutOfMemoryError
-XX:+HeapDumpOnOutOfMemoryError
-XX:-OmitStackTraceInFastThrow
-XX:ReservedCodeCacheSize=512M
-Djdk.attach.allowAttachSelf=true
-Djdk.nio.maxCachedBufferSize=2000000
--add-modules=jdk.incubator.vector
EOF

cat >/etc/trino/config.properties <<'EOF'
coordinator={coordinator_flag}
node-scheduler.include-coordinator={include_coordinator}
http-server.http.port={TRINO_HTTP_PORT}
# Trust proxy-set forwarded headers: the coordinator sits behind the control-plane
# Caddy gateway, which terminates TLS and injects X-Forwarded-For/-Proto. Without
# this, Trino returns HTTP 406 for any request carrying those headers.
http-server.process-forwarded=true
discovery.uri={discovery_uri}
query.max-memory={memory["query_max_memory_gb"]}GB
query.max-memory-per-node={memory["query_max_memory_per_node_gb"]}GB
memory.heap-headroom-per-node={memory["heap_headroom_gb"]}GB
EOF

# The system catalog is built into Trino and is automatically available as "system".
{catalog_commands}

{access_control_commands}

{driver_commands}

{cache_commands}

chown -R "$TRINO_USER:$TRINO_USER" /etc/trino /var/lib/trino /var/log/trino "$TRINO_INSTALL_DIR"
"""

    def trino_user_data(
        self,
        *,
        cluster: dict[str, Any],
        node_role: str,
        region: str,
        instance_type: str | None = None,
        coordinator_uri: str | None = None,
        control_plane_uri: str | None = None,
        cluster_id: int | None = None,
        bootstrap_token: str | None = None,
    ) -> str:
        trino_version = resolve_trino_version(cluster)
        if control_plane_uri and cluster_id and bootstrap_token:
            config_url = (
                f"{control_plane_uri.rstrip('/')}/api/node-config/{cluster_id}"
                f"?role={node_role}&token={bootstrap_token}&instance_type={instance_type or ''}"
            )
            config_commands = f"""TRINOHUB_CONFIG_URL="{config_url}"
curl --fail --location --retry 12 --retry-delay 10 "$TRINOHUB_CONFIG_URL" --output /tmp/trinohub-node-config.sh
chmod 0600 /tmp/trinohub-node-config.sh
bash /tmp/trinohub-node-config.sh
rm -f /tmp/trinohub-node-config.sh
"""
        else:
            config_commands = self.trino_node_config_script(
                cluster=cluster,
                node_role=node_role,
                region=region,
                instance_type=instance_type,
                coordinator_uri=coordinator_uri,
            )

        return f"""#!/bin/bash
set -euo pipefail

TRINO_VERSION="{trino_version}"
TRINO_INSTALL_DIR="/opt/trino-server-${{TRINO_VERSION}}"
TRINO_LINK="/opt/trino"
TRINO_USER="trino"
TRINO_PORT="{TRINO_HTTP_PORT}"
TRINO_ARCHIVE_URL="https://github.com/trinodb/trino/releases/download/${{TRINO_VERSION}}/trino-server-${{TRINO_VERSION}}.tar.gz"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y apt-transport-https curl gpg tar wget
wget -qO - https://packages.adoptium.net/artifactory/api/gpg/key/public | gpg --dearmor >/etc/apt/trusted.gpg.d/adoptium.gpg
echo "deb https://packages.adoptium.net/artifactory/deb $(awk -F= '/^VERSION_CODENAME/{{print$2}}' /etc/os-release) main" >/etc/apt/sources.list.d/adoptium.list
apt-get update
apt-get install -y temurin-25-jdk

if ! id -u "$TRINO_USER" >/dev/null 2>&1; then
  useradd --system --home-dir /var/lib/trino --shell /usr/sbin/nologin "$TRINO_USER"
fi

install -d -m 0755 /opt /etc/trino/catalog /etc/trinohub
install -d -o "$TRINO_USER" -g "$TRINO_USER" -m 0750 /var/lib/trino /var/log/trino

if [ ! -d "$TRINO_INSTALL_DIR" ]; then
  curl --fail --location --retry 5 --retry-delay 5 \
    "$TRINO_ARCHIVE_URL" \
    --output "/tmp/trino-server-${{TRINO_VERSION}}.tar.gz"
  tar -xzf "/tmp/trino-server-${{TRINO_VERSION}}.tar.gz" -C /opt
fi
ln -sfn "$TRINO_INSTALL_DIR" "$TRINO_LINK"
rm -rf "$TRINO_LINK/etc"
ln -sfn /etc/trino "$TRINO_LINK/etc"

{config_commands}

cat >/etc/systemd/system/trino.service <<'EOF'
[Unit]
Description=Trino query engine
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
User=trino
Group=trino
ExecStart=/opt/trino/bin/launcher start
ExecStop=/opt/trino/bin/launcher stop
ExecReload=/opt/trino/bin/launcher restart
Restart=on-failure
RestartSec=10
LimitNOFILE=131072
LimitNPROC=128000

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now trino

cat >/var/log/trinohub-bootstrap.log <<'EOF'
TrinoHub bootstrap completed.
Trino is managed by systemd unit trino.service.
EOF
"""

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
        ec2 = self.clients(region)["ec2"]
        ami = image_id or self.latest_ubuntu_ami(region)
        launch_args: dict[str, Any] = {}
        key_name = self.default_key_name(region)
        if key_name:
            launch_args["KeyName"] = key_name
        response = ec2.run_instances(
            ImageId=ami,
            InstanceType=instance_type,
            MinCount=1,
            MaxCount=1,
            SubnetId=subnet_id,
            SecurityGroupIds=security_group_ids,
            IamInstanceProfile={"Name": node_instance_profile},
            UserData=self.trino_user_data(
                cluster=cluster,
                node_role="coordinator",
                region=region,
                instance_type=instance_type,
                control_plane_uri=control_plane_uri,
                cluster_id=cluster_id,
                bootstrap_token=bootstrap_token,
            ),
            **launch_args,
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": self.cluster_tags(cluster["name"], Name=f"trinohub-{cluster['name']}-coordinator")
                    + [{"Key": "TrinoHubNodeRole", "Value": "coordinator"}],
                },
                {
                    "ResourceType": "volume",
                    "Tags": self.cluster_tags(cluster["name"], Name=f"trinohub-{cluster['name']}-coordinator-root"),
                },
            ],
        )
        instance = response["Instances"][0]
        return {
            "instance_id": instance["InstanceId"],
            "image_id": ami,
            "instance_type": instance_type,
            "private_ip_address": instance.get("PrivateIpAddress", ""),
            "private_dns_name": instance.get("PrivateDnsName", ""),
            "key_name": instance.get("KeyName", ""),
        }

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
        ec2 = self.clients(region)["ec2"]
        ami = image_id or self.latest_ubuntu_ami(region)
        name = f"trinohub-{cluster['name']}-workers"
        key_name = self.default_key_name(region)
        user_data = base64.b64encode(
            self.trino_user_data(
                cluster=cluster,
                node_role="worker",
                region=region,
                instance_type=instance_type,
                coordinator_uri=coordinator_uri,
                control_plane_uri=control_plane_uri,
                cluster_id=cluster_id,
                bootstrap_token=bootstrap_token,
            ).encode("utf-8")
        ).decode("ascii")
        response = ec2.create_launch_template(
            LaunchTemplateName=name,
            LaunchTemplateData={
                "ImageId": ami,
                "InstanceType": instance_type,
                "IamInstanceProfile": {"Name": node_instance_profile},
                "SecurityGroupIds": security_group_ids,
                "UserData": user_data,
                **({"KeyName": key_name} if key_name else {}),
                "TagSpecifications": [
                    {
                        "ResourceType": "instance",
                        "Tags": self.cluster_tags(cluster["name"], Name=f"trinohub-{cluster['name']}-worker")
                        + [{"Key": "TrinoHubNodeRole", "Value": "worker"}],
                    },
                    {
                        "ResourceType": "volume",
                        "Tags": self.cluster_tags(cluster["name"], Name=f"trinohub-{cluster['name']}-worker-root"),
                    },
                ],
            },
            TagSpecifications=[
                {
                    "ResourceType": "launch-template",
                    "Tags": self.cluster_tags(cluster["name"], Name=name),
                }
            ],
        )
        template = response["LaunchTemplate"]
        return {
            "launch_template_id": template["LaunchTemplateId"],
            "launch_template_name": template["LaunchTemplateName"],
            "image_id": ami,
            "instance_type": instance_type,
            "coordinator_uri": coordinator_uri,
            "key_name": key_name or "",
        }

    def coordinator_health(self, *, coordinator_endpoint: str, timeout_seconds: int = 3) -> dict[str, Any]:
        if not coordinator_endpoint:
            return {"ok": False, "state": "unknown", "detail": "Coordinator endpoint is not known yet."}
        url = f"http://{coordinator_endpoint}:{TRINO_HTTP_PORT}/v1/info"
        try:
            with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body) if body else {}
        except Exception as exc:
            return {"ok": False, "state": "unreachable", "url": url, "detail": f"{type(exc).__name__}: {exc}"}
        starting = bool(data.get("starting", True))
        return {
            "ok": not starting,
            "state": "starting" if starting else "running",
            "url": url,
            "node_version": data.get("nodeVersion", {}),
            "environment": data.get("environment", ""),
        }

    def trino_optional_json(self, *, coordinator_endpoint: str, path: str, timeout_seconds: int = 3) -> Any | None:
        url = f"http://{coordinator_endpoint}:{TRINO_HTTP_PORT}{path}"
        try:
            request = urllib.request.Request(url, headers={"X-Trino-User": "trinohub"})
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except Exception:
            return None

    def trino_node_health(self, *, coordinator_endpoint: str, timeout_seconds: int = 3) -> dict[str, Any]:
        data = self.trino_optional_json(
            coordinator_endpoint=coordinator_endpoint,
            path="/v1/node",
            timeout_seconds=timeout_seconds,
        )

        def count(value: Any) -> int:
            if isinstance(value, list):
                return len(value)
            if isinstance(value, dict):
                return len(value)
            if isinstance(value, int):
                return value
            return 0

        if data is None:
            return {"ok": False, "active_workers": 0, "inactive_workers": 0}
        if isinstance(data, list):
            return {"ok": True, "active_workers": len(data), "inactive_workers": 0}
        if isinstance(data, dict):
            active = count(data.get("activeNodes") or data.get("active_nodes") or data.get("nodes"))
            inactive = count(data.get("inactiveNodes") or data.get("inactive_nodes"))
            return {"ok": True, "active_workers": active, "inactive_workers": inactive}
        return {"ok": False, "active_workers": 0, "inactive_workers": 0}

    def trino_memory_stats(self, *, coordinator_endpoint: str, timeout_seconds: int = 3) -> dict[str, Any]:
        data = self.trino_optional_json(
            coordinator_endpoint=coordinator_endpoint,
            path="/v1/memory",
            timeout_seconds=timeout_seconds,
        )
        if not isinstance(data, dict):
            return {"ok": False, "reserved_bytes": None, "max_bytes": None}
        pools = data.get("pools") or data.get("memoryPools") or {}
        values = pools.values() if isinstance(pools, dict) else pools if isinstance(pools, list) else []
        reserved = 0
        maximum = 0
        found = False
        for pool in values:
            if not isinstance(pool, dict):
                continue
            reserved += int(pool.get("reservedBytes") or pool.get("reserved_bytes") or 0)
            maximum += int(pool.get("maxBytes") or pool.get("max_bytes") or 0)
            found = True
        return {
            "ok": found,
            "reserved_bytes": reserved if found else None,
            "max_bytes": maximum if found else None,
        }

    def trino_cluster_stats(self, *, coordinator_endpoint: str, timeout_seconds: int = 3) -> dict[str, Any]:
        """Query-activity signals used by auto-suspend and autoscale.

        Trino 481 has no unauthenticated ``/v1/cluster`` summary (it 404s), so we
        list queries via ``/v1/query`` — which requires an ``X-Trino-User`` header
        — and collect optional node/memory snapshots from ``/v1/node`` and
        ``/v1/memory``. Autoscale still treats query pressure and CloudWatch CPU as
        the primary scaling signals, but node health and memory are persisted with
        each sample for the cluster detail view and future tuning.
        """
        if not coordinator_endpoint:
            return {"ok": False, "state": "unknown", "detail": "Coordinator endpoint is not known yet."}
        url = f"http://{coordinator_endpoint}:{TRINO_HTTP_PORT}/v1/query"
        try:
            request = urllib.request.Request(url, headers={"X-Trino-User": "trinohub"})
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body) if body else []
        except Exception as exc:
            return {"ok": False, "state": "unreachable", "url": url, "detail": f"{type(exc).__name__}: {exc}"}
        queries = data if isinstance(data, list) else []
        running = sum(1 for q in queries if q.get("state") == "RUNNING")
        queued = sum(1 for q in queries if q.get("state") == "QUEUED")
        node_health = self.trino_node_health(coordinator_endpoint=coordinator_endpoint, timeout_seconds=timeout_seconds)
        memory = self.trino_memory_stats(coordinator_endpoint=coordinator_endpoint, timeout_seconds=timeout_seconds)
        return {
            "ok": True,
            "url": url,
            "running_queries": running,
            "queued_queries": queued,
            "blocked_queries": 0,
            "active_workers": int(node_health.get("active_workers") or 0),
            "worker_health": node_health,
            "running_drivers": 0,
            "reserved_memory": memory.get("reserved_bytes"),
            "memory": memory,
        }

    def create_worker_auto_scaling_group(
        self,
        *,
        region: str,
        subnet_ids: list[str],
        cluster: dict[str, Any],
        launch_template_id: str,
    ) -> dict[str, Any]:
        from botocore.exceptions import ClientError

        autoscaling = self.clients(region)["autoscaling"]
        name = f"trinohub-{cluster['name']}-workers"
        create_kwargs = dict(
            AutoScalingGroupName=name,
            LaunchTemplate={"LaunchTemplateId": launch_template_id, "Version": "$Latest"},
            MinSize=int(cluster["min_workers"]),
            MaxSize=int(cluster["max_workers"]),
            DesiredCapacity=int(cluster["min_workers"]),
            VPCZoneIdentifier=",".join(subnet_ids),
            HealthCheckType="EC2",
            Tags=[
                {"Key": key, "Value": value, "PropagateAtLaunch": True}
                for key, value in {
                    "Name": name,
                    "ManagedBy": "TrinoHub",
                    "TrinoHubCluster": cluster["name"],
                    "TrinoHubNodeRole": "worker",
                }.items()
            ],
        )
        # A recent suspend/delete tears the ASG down, but AWS removes it
        # asynchronously and leaves it "pending delete" for a short window.
        # Recreating the same-named ASG during that window raises AlreadyExists
        # (e.g. on a quick suspend→resume), so wait for the old one to clear and
        # retry rather than failing the resume.
        deadline = time.monotonic() + ASG_RECREATE_WAIT_SECONDS
        while True:
            try:
                autoscaling.create_auto_scaling_group(**create_kwargs)
                break
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code == "AlreadyExists" and time.monotonic() < deadline:
                    time.sleep(ASG_RECREATE_POLL_SECONDS)
                    continue
                raise
        return {
            "auto_scaling_group_name": name,
            "desired_capacity": int(cluster["min_workers"]),
            "min_size": int(cluster["min_workers"]),
            "max_size": int(cluster["max_workers"]),
        }

    def delete_worker_auto_scaling_group(self, *, region: str, name: str) -> dict[str, Any]:
        from botocore.exceptions import ClientError

        autoscaling = self.clients(region)["autoscaling"]
        try:
            autoscaling.update_auto_scaling_group(
                AutoScalingGroupName=name,
                MinSize=0,
                DesiredCapacity=0,
            )
            autoscaling.delete_auto_scaling_group(AutoScalingGroupName=name, ForceDelete=True)
            return {"deleted": True, "resource_id": name}
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            message = exc.response.get("Error", {}).get("Message", "")
            if code == "ValidationError" and "not found" in message.lower():
                return {"deleted": False, "not_found": True, "resource_id": name}
            raise

    def worker_auto_scaling_group(self, *, region: str, name: str) -> dict[str, Any]:
        autoscaling = self.clients(region)["autoscaling"]
        groups = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[name]).get("AutoScalingGroups", [])
        if not groups:
            return {"found": False, "name": name}
        group = groups[0]
        instances = group.get("Instances", [])
        return {
            "found": True,
            "name": name,
            "desired_capacity": int(group.get("DesiredCapacity") or 0),
            "min_size": int(group.get("MinSize") or 0),
            "max_size": int(group.get("MaxSize") or 0),
            "in_service_capacity": sum(1 for instance in instances if instance.get("LifecycleState") == "InService"),
            "pending_capacity": sum(1 for instance in instances if instance.get("LifecycleState") == "Pending"),
            "unhealthy_capacity": sum(
                1
                for instance in instances
                if instance.get("HealthStatus") and instance.get("HealthStatus") != "Healthy"
            ),
            "instance_ids": [instance["InstanceId"] for instance in instances if instance.get("InstanceId")],
        }

    def set_worker_desired_capacity(
        self,
        *,
        region: str,
        name: str,
        desired_capacity: int,
        min_size: int,
        max_size: int,
    ) -> dict[str, Any]:
        autoscaling = self.clients(region)["autoscaling"]
        autoscaling.update_auto_scaling_group(
            AutoScalingGroupName=name,
            MinSize=int(min_size),
            MaxSize=int(max_size),
            DesiredCapacity=int(desired_capacity),
        )
        return {
            "updated": True,
            "name": name,
            "desired_capacity": int(desired_capacity),
            "min_size": int(min_size),
            "max_size": int(max_size),
        }

    def worker_cpu_average(
        self,
        *,
        region: str,
        instance_ids: list[str],
        lookback_minutes: int = 5,
        period_seconds: int = 60,
    ) -> float | None:
        if not instance_ids:
            return None
        cloudwatch = self.clients(region)["cloudwatch"]
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=lookback_minutes)
        averages: list[float] = []
        for instance_id in instance_ids:
            response = cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start,
                EndTime=end,
                Period=period_seconds,
                Statistics=["Average"],
            )
            datapoints = response.get("Datapoints", [])
            if datapoints:
                averages.extend(float(point["Average"]) for point in datapoints if "Average" in point)
        if not averages:
            return None
        return sum(averages) / len(averages)

    def terminate_instances(self, *, region: str, instance_ids: list[str]) -> dict[str, Any]:
        from botocore.exceptions import ClientError

        if not instance_ids:
            return {"terminated": [], "not_found": []}
        ec2 = self.clients(region)["ec2"]
        try:
            ec2.terminate_instances(InstanceIds=instance_ids)
            return {"terminated": instance_ids, "not_found": []}
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in {"InvalidInstanceID.NotFound", "InvalidInstanceID.Malformed"}:
                return {"terminated": [], "not_found": instance_ids}
            raise

    def delete_launch_template(self, *, region: str, launch_template_id: str) -> dict[str, Any]:
        from botocore.exceptions import ClientError

        ec2 = self.clients(region)["ec2"]
        try:
            ec2.delete_launch_template(LaunchTemplateId=launch_template_id)
            return {"deleted": True, "resource_id": launch_template_id}
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in {"InvalidLaunchTemplateId.NotFound", "InvalidLaunchTemplateId.Malformed"}:
                return {"deleted": False, "not_found": True, "resource_id": launch_template_id}
            raise

    def wait_for_cluster_instances_gone(
        self,
        *,
        region: str,
        cluster_name: str,
        timeout_seconds: int = 90,
        poll_seconds: int = 5,
    ) -> dict[str, Any]:
        ec2 = self.clients(region)["ec2"]
        deadline = time.time() + timeout_seconds
        last_ids: list[str] = []
        while True:
            response = ec2.describe_instances(
                Filters=[
                    {"Name": "tag:ManagedBy", "Values": ["TrinoHub"]},
                    {"Name": "tag:TrinoHubCluster", "Values": [cluster_name]},
                    {
                        "Name": "instance-state-name",
                        "Values": ["pending", "running", "stopping", "stopped", "shutting-down"],
                    },
                ]
            )
            last_ids = [
                instance["InstanceId"]
                for reservation in response.get("Reservations", [])
                for instance in reservation.get("Instances", [])
            ]
            if not last_ids:
                return {"gone": True, "remaining_instance_ids": []}
            if time.time() >= deadline:
                return {"gone": False, "remaining_instance_ids": last_ids}
            time.sleep(poll_seconds)

    def delete_security_group(self, *, region: str, group_id: str) -> dict[str, Any]:
        from botocore.exceptions import ClientError

        ec2 = self.clients(region)["ec2"]
        try:
            ec2.delete_security_group(GroupId=group_id)
            return {"deleted": True, "resource_id": group_id}
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in {"InvalidGroup.NotFound", "InvalidGroupId.Malformed"}:
                return {"deleted": False, "not_found": True, "resource_id": group_id}
            raise

    def cleanup_managed_security_group_rules(
        self,
        *,
        region: str,
        group_id: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Revoke TrinoHub-created SG references before deleting a node SG."""
        from botocore.exceptions import ClientError

        ec2 = self.clients(region)["ec2"]
        revoked: list[dict[str, Any]] = []
        missing: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []

        def revoke(label: str, target_group_id: str, ip_permissions: list[dict[str, Any]]) -> None:
            if not ip_permissions:
                return
            try:
                ec2.revoke_security_group_ingress(GroupId=target_group_id, IpPermissions=ip_permissions)
                revoked.append({"rule": label, "group_id": target_group_id})
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                detail = {"rule": label, "group_id": target_group_id, "code": code}
                if code in {"InvalidPermission.NotFound", "InvalidGroup.NotFound", "InvalidGroupId.Malformed"}:
                    missing.append(detail)
                else:
                    failed.append(detail)

        revoke(
            "node_self_ingress",
            group_id,
            [
                {
                    "IpProtocol": "-1",
                    "UserIdGroupPairs": [{"GroupId": group_id}],
                }
            ],
        )

        control_plane_ingress = metadata.get("control_plane_ingress") or {}
        port_range = {"IpProtocol": "tcp", "FromPort": TRINO_HTTP_PORT, "ToPort": TRINO_HTTP_PORT}
        if control_plane_ingress.get("via") == "security_group":
            group_ids = [value for value in control_plane_ingress.get("group_ids") or [] if value]
            if group_ids:
                revoke(
                    "control_plane_to_coordinator",
                    group_id,
                    [
                        {
                            **port_range,
                            "UserIdGroupPairs": [{"GroupId": source_group_id} for source_group_id in group_ids],
                        }
                    ],
                )
        elif control_plane_ingress.get("via") == "cidr" and control_plane_ingress.get("cidr"):
            revoke(
                "control_plane_to_coordinator",
                group_id,
                [
                    {
                        **port_range,
                        "IpRanges": [{"CidrIp": control_plane_ingress["cidr"]}],
                    }
                ],
            )

        node_to_control_plane = metadata.get("node_to_control_plane_ingress") or {}
        node_group_id = node_to_control_plane.get("node_group_id") or group_id
        node_config_port = int(node_to_control_plane.get("port") or 8000)
        for target_group_id in node_to_control_plane.get("target_group_ids") or []:
            if not target_group_id:
                continue
            revoke(
                "nodes_to_control_plane",
                target_group_id,
                [
                    {
                        "IpProtocol": "tcp",
                        "FromPort": node_config_port,
                        "ToPort": node_config_port,
                        "UserIdGroupPairs": [{"GroupId": node_group_id}],
                    }
                ],
            )

        return {"revoked": revoked, "missing": missing, "failed": failed}

    def cluster_tags(self, cluster_name: str, **extra: str) -> list[dict[str, str]]:
        tags = {
            "ManagedBy": "TrinoHub",
            "TrinoHubCluster": cluster_name,
            **extra,
        }
        return [{"Key": key, "Value": value} for key, value in tags.items()]
