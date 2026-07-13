from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http import cookies
from pathlib import Path
from typing import Any, Callable, Protocol

from .aws_checks import (
    DEFAULT_INSTANCE_HOURLY_USD,
    DEFAULT_INSTANCE_MEMORY_GB,
    DEFAULT_INSTANCE_VCPU,
    INSTANCE_HOURLY_USD,
    INSTANCE_MEMORY_GB,
    INSTANCE_STORE_GB,
    INSTANCE_VCPU,
    SUPPORTED_TRINO_VERSIONS,
    TRINO_HTTP_PORT,
    TRINO_VERSION,
    AwsInspector,
    instance_store_disks,
)
from .cloud_provider import PROVIDER_AWS, CloudProvider
from .tls_gateway import SHIM_UPSTREAM, build_caddyfile, push_config
from .connectors import (
    CREDENTIALED_CATALOG_TYPES,
    DRIVER_REQUIRED_TYPES,
    OPTIONAL_SECRET_CATALOG_TYPES,
    REGISTRY,
    ConnectorType,
    connector_types_catalog,
)
from .database import BUILT_IN_CATALOGS, connect, dumps, init_db, loads, public_user, row_to_dict, utc_now
from .secrets_store import SecretsManagerStore, SecretStore, SecretStoreError
from .security import hash_password, new_session_token, token_hash, verify_password


def provider_config(setup: dict[str, Any]) -> dict[str, Any]:
    """Provider-specific setup settings (the ``provider_config_json`` blob).

    For AWS this holds ``vpc_id``, ``private_subnet_ids``,
    ``cluster_security_group_id`` and ``node_instance_profile``; a second provider
    stores its own network/identity shape here without a schema change. Callers
    read individual keys with ``.get`` so a partially configured provider degrades
    gracefully.
    """
    return loads(setup.get("provider_config_json", "{}"), {}) or {}


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / ".trinohub" / "trinohub.sqlite3"
DEFAULT_STATIC_DIR = ROOT / "web"
DEFAULT_DOCS_DIR = ROOT / "docs"
SESSION_COOKIE = "trinohub_session"
# Each preset maps to an ordered list of candidate instance types: a modern
# M-family general-purpose type first, with prior-generation fallbacks for
# regions where the newest type is not yet offered. Coordinator and workers use
# the same type. Resolved against the region at create/start time so an
# unavailable type surfaces as a validation error instead of a launch failure.
PRESET_INSTANCE_CANDIDATES = {
    "Cost": ["m7i.large", "m6i.large", "m5.large"],
    "Balanced": ["m7i.xlarge", "m6i.xlarge", "m5.xlarge"],
    "Power": ["m7i.2xlarge", "m6i.2xlarge", "m5.2xlarge"],
}
# Curated, memory-optimized EC2 instance types offered by the Settings instance
# picker. Trino is memory-bound, so this favors the R-family (with a couple of
# general-purpose M types). Admins enable a subset of these in Settings
# (allowed_instance_types); clusters are then created against one of the enabled
# types. Ordered for display: largest family first, then size within family.
POPULAR_TRINO_INSTANCE_TYPES = [
    "r7i.xlarge", "r7i.2xlarge", "r7i.4xlarge",
    "r6i.xlarge", "r6i.2xlarge",
    "r5.xlarge", "r5.2xlarge", "r5.4xlarge",
    "m7i.2xlarge", "m6i.2xlarge",
    # NVMe instance-store types for accelerated (warm-cache) clusters. i4i is
    # the recommended default tier: same 8 GiB/vCPU shape as the R family with
    # Nitro SSDs for the Trino file system cache. r6id is the budget cache tier
    # and i3en the max-cache-per-dollar tier.
    "i4i.large", "i4i.xlarge", "i4i.2xlarge", "i4i.4xlarge",
    "r6id.xlarge", "r6id.2xlarge",
    "i3en.xlarge", "i3en.2xlarge",
    # Small, cheap burstable node for kicking the tyres / demos — not for real
    # workloads (Trino is memory-bound; prefer the R-family above in production).
    "t3.large",
]
# Accelerated clusters default to a long auto-suspend: the instance-store cache
# is wiped on suspend (instances terminate), so every resume starts cold and an
# aggressive idle timeout would throw the warm cache away repeatedly.
ACCELERATED_DEFAULT_AUTO_SUSPEND_MINUTES = 4 * 60
TERMINAL_QUERY_STATUSES = {"Finished", "Failed", "Cancelled"}
# A query submitted to a suspended cluster waits (status stays "Queued") while the
# cluster resumes, then dispatches to Trino automatically. Vendor cluster starts
# typically take one to five minutes; cap the wait generously so a genuinely stuck
# resume fails the query instead of polling forever.
QUERY_CLUSTER_START_TIMEOUT_SECONDS = 15 * 60

# Native Trino wire-protocol resume shim. Hop-by-hop / connection-specific headers
# are stripped when we capture a client's request and when we relay a coordinator's
# response — everything else (all X-Trino-* session/prepared-statement/transaction
# state, Authorization, cookies) is passed through verbatim so real JDBC/BI clients
# keep working across the resume handoff. Header names are compared lowercased.
WIRE_HOP_BY_HOP_HEADERS = frozenset(
    {
        "host",
        "content-length",
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)
# How long a wire query holds in QUEUED while its cluster resumes before we give up.
WIRE_RESUME_TIMEOUT_SECONDS = QUERY_CLUSTER_START_TIMEOUT_SECONDS
# Server-side pause per holding poll so native clients don't busy-loop the shim
# (real Trino queued/executing endpoints long-poll ~1s before responding).
WIRE_HOLD_POLL_SECONDS = 1.0
BUILT_IN_CATALOG_NAMES = {name for name, _, _ in BUILT_IN_CATALOGS}
CATALOG_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_]{1,62}")
AWS_REGION_PATTERN = re.compile(r"[a-z]{2}(?:-gov)?-[a-z]+-\d")
S3_WAREHOUSE_PATTERN = re.compile(r"s3://[a-z0-9][a-z0-9.-]{1,61}[a-z0-9](?:/[^\s]*)?")
SCHEMA_NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")
JDBC_USER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]{0,127}")
# Hostname or IP literal for non-URL connectors (e.g. Elasticsearch host field).
HOST_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-]{0,253}")
# GCP project IDs: 6-30 chars, lowercase letter start, letters/digits/hyphens,
# not ending in a hyphen. https://cloud.google.com/resource-manager/docs/creating-managing-projects
GCP_PROJECT_PATTERN = re.compile(r"[a-z][a-z0-9-]{4,28}[a-z0-9]")
# Google Sheets spreadsheet IDs are URL-safe base64-ish tokens (letters, digits,
# hyphen, underscore), ~44 chars in practice; bound loosely to catch paste errors.
GSHEET_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{20,120}")
# Connector descriptors (supported types, JDBC URL shapes, which need a secret
# or an uploaded driver) live in connectors.REGISTRY; CREDENTIALED_CATALOG_TYPES
# and DRIVER_REQUIRED_TYPES are imported from there.
# Uploaded connector-driver JARs are capped so a single upload can't exhaust the
# control-plane disk; ojdbc and peers are a few MB, so 200 MB is generous.
MAX_DRIVER_UPLOAD_BYTES = 200 * 1024 * 1024
AUTOSCALE_INTERVAL_SECONDS = 30
AUTOSCALE_QUEUED_SCALE_UP_INTERVALS = 2
AUTOSCALE_CPU_SCALE_UP_INTERVALS = 3
AUTOSCALE_SCALE_UP_COOLDOWN_SECONDS = 180
AUTOSCALE_SCALE_DOWN_COOLDOWN_SECONDS = 600
AUTOSCALE_IDLE_SCALE_DOWN_SECONDS = 600
AUTOSCALE_CPU_HIGH_THRESHOLD = 75.0
AUTOSCALE_CPU_LOW_THRESHOLD = 25.0
AUTO_SUSPEND_MAX_MINUTES = 24 * 60

# How long a successful Trino-release discovery result is served from cache,
# and how soon a failed attempt is retried.
TRINO_VERSION_REFRESH_SECONDS = 6 * 60 * 60
TRINO_VERSION_RETRY_SECONDS = 15 * 60
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 900
MAX_QUERY_RESULT_ROWS = 1000
MAX_QUERY_RESULT_BYTES = 10 * 1024 * 1024
MAX_QUERY_DOWNLOAD_ROWS = 10_000
MAX_QUERY_DOWNLOAD_BYTES = 50 * 1024 * 1024
# Result cache (issue #1): identical read-only re-runs within the TTL are served
# from the stored capped result set instead of contacting the cluster. Entries
# are scoped per user; 0 disables serving from cache.
DEFAULT_RESULT_CACHE_TTL_MINUTES = 10
MAX_RESULT_CACHE_TTL_MINUTES = 24 * 60
CONTROL_PLANE_NODE_CONFIG_PORT = 8000
MAX_METADATA_ROWS = 1000
MAX_METADATA_PAGES = 20
DEFAULT_QUERY_TAB_SQL = """SELECT nationkey, name, regionkey
FROM tpch.sf1.nation
ORDER BY nationkey
LIMIT 10;"""
MAX_QUERY_TAB_NAME_LENGTH = 80
MAX_SAVED_QUERY_NAME_LENGTH = 120
MAX_NOTEBOOK_NAME_LENGTH = 120
QUERY_TAB_RUN_MODES = {"current", "selected", "all"}
NOTEBOOK_CELL_VIEWS = {"table", "chart"}

# --- Ask Trino (natural-language analytics assistant) -----------------------
# The LLM only ever emits SQL as text; TrinoHub validates it (SELECT-only) and
# runs it through the normal query path. The model never gets database access.
ASK_TRINO_DEFAULT_API_BASE = "https://openrouter.ai/api/v1/chat/completions"
ASK_TRINO_DEFAULT_MODEL = "openai/gpt-4o-mini"  # override in Settings → Ask Trino or ASK_TRINO_MODEL
ASK_TRINO_TIMEOUT_SECONDS = 60
ASK_TRINO_MAX_TOKENS = 2048
ASK_TRINO_HISTORY_MAX = 20  # turns of chat history sent back to the model
ASK_TRINO_SCHEMA_TABLE_LIMIT = 60  # tables described in the schema prompt block
ASK_TRINO_MAX_POLLS = 30  # ~12s of polling for the generated query to finish
ASK_TRINO_CHART_TYPES = {"bar", "line", "pie", "none"}
# Word-boundary denylist applied to the generated SQL after string literals and
# comments are masked out. Any match rejects the statement before execution.
ASK_TRINO_SQL_DENYLIST = (
    "insert", "update", "delete", "drop", "create", "alter", "truncate",
    "merge", "grant", "revoke", "call", "comment", "analyze", "refresh",
    "exec", "execute", "set", "reset", "use", "prepare", "deallocate",
)

# --- RBAC ----------------------------------------------------------------
# Coarse privileges enforced in the API layer. Each maps to an area TrinoHub
# previously gated on the binary admin bit; roles carry a set of them.
PRIVILEGE_MANAGE_USERS = "MANAGE_USERS"
PRIVILEGE_MANAGE_SECURITY = "MANAGE_SECURITY"
PRIVILEGE_MANAGE_CLUSTERS = "MANAGE_CLUSTERS"
PRIVILEGE_MANAGE_CATALOGS = "MANAGE_CATALOGS"
PRIVILEGE_MANAGE_SETTINGS = "MANAGE_SETTINGS"
PRIVILEGE_VIEW_ALL_QUERY_HISTORY = "VIEW_ALL_QUERY_HISTORY"
PRIVILEGE_CANCEL_ANY_QUERY = "CANCEL_ANY_QUERY"
ALL_PRIVILEGES = (
    PRIVILEGE_MANAGE_USERS,
    PRIVILEGE_MANAGE_SECURITY,
    PRIVILEGE_MANAGE_CLUSTERS,
    PRIVILEGE_MANAGE_CATALOGS,
    PRIVILEGE_MANAGE_SETTINGS,
    PRIVILEGE_VIEW_ALL_QUERY_HISTORY,
    PRIVILEGE_CANCEL_ANY_QUERY,
)
ROLE_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_-]{1,62}")
GRANT_WILDCARD = "*"
MAX_AUDIT_LOG_LIMIT = 500

# --- Enterprise auth (Phase 2) -------------------------------------------
# Long-lived bearer tokens for headless API access. The prefix makes leaked
# tokens greppable/scannable and lets current_user short-circuit cheaply.
API_TOKEN_PREFIX = "tht_"
MAX_API_TOKEN_NAME_LENGTH = 80
DEFAULT_SESSION_HOURS = 12
MAX_SESSION_HOURS = 7 * 24
# OIDC login round-trip state (browser → IdP → callback) is held in memory;
# entries expire quickly and a control-plane restart just means re-clicking
# "Sign in with SSO" (same trade-off as the in-memory login rate limiter).
OIDC_STATE_TTL_SECONDS = 600
OIDC_HTTP_TIMEOUT_SECONDS = 10
OIDC_DISCOVERY_CACHE_SECONDS = 3600
OIDC_PASSWORD_LOGIN_POLICIES = {"all", "operators_only"}
MANAGEMENT_PRIVILEGES = frozenset(
    {
        PRIVILEGE_MANAGE_USERS,
        PRIVILEGE_MANAGE_SECURITY,
        PRIVILEGE_MANAGE_CLUSTERS,
        PRIVILEGE_MANAGE_CATALOGS,
        PRIVILEGE_MANAGE_SETTINGS,
    }
)

# --- Query platform (Phase 3) ----------------------------------------------
SHARE_ACCESS_LEVELS = ("view", "run", "edit")
SHAREABLE_ENTITY_TYPES = ("saved_query", "notebook")
JOB_SCHEDULE_TYPES = ("interval", "cron")
JOB_MIN_INTERVAL_MINUTES = 5
JOB_MAX_INTERVAL_MINUTES = 7 * 24 * 60
MAX_JOB_NAME_LENGTH = 120
MAX_JOB_RUNS_LISTED = 50
# How many pages the job finalizer pumps per tick per running job query.
JOB_ADVANCE_MAX_PAGES = 5
AUTOCOMPLETE_TABLE_LIMIT = 2000
SEARCH_RESULT_LIMIT = 40

# --- Observability & ops (Phase 5) ------------------------------------------
STATS_RETENTION_DAYS = 7
STATS_MAX_POINTS = 500
NOTIFICATION_EVENTS = (
    "cluster_failed",
    "cluster_suspended",
    "cluster_running",
    "job_failed",
    "security",
)
NOTIFY_TIMEOUT_SECONDS = 5
COST_WINDOW_DAYS = 30
UPTIME_DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
UPTIME_WINDOW_PATTERN = re.compile(r"([0-2]\d):([0-5]\d)-([0-2]\d):([0-5]\d)")

# --- Fine-grained data security (Phase 6) -----------------------------------
DATA_POLICY_PRIVILEGES = ("SELECT", "INSERT", "DELETE", "UPDATE")
TAG_POLICY_EFFECTS = ("deny", "mask")
TAG_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_-]{0,62}")
COLUMN_NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_$]{0,127}")
# Entity paths are catalog.schema.table or catalog.schema.table.column.
ENTITY_PATH_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,62}(\.[A-Za-z0-9_$]{1,128}){2,3}")
# Simple, high-signal column-name heuristics for the PII classifier.
PII_COLUMN_PATTERNS: tuple[tuple[str, str], ...] = (
    ("pii-email", r"e?[-_]?mail"),
    ("pii-phone", r"phone|mobile|msisdn"),
    ("pii-ssn", r"\bssn\b|social[-_]?security"),
    ("pii-name", r"(first|last|full|middle|sur|given)[-_]?name"),
    ("pii-address", r"address|street|zip[-_]?code|postal"),
    ("pii-dob", r"birth[-_]?(date|day)|\bdob\b"),
    ("pii-card", r"credit[-_]?card|card[-_]?number|\bpan\b"),
    ("pii-ip", r"ip[-_]?addr"),
    ("sensitive-salary", r"salary|compensation|wage"),
)


def parse_cron_field(field: str, low: int, high: int) -> set[int]:
    """One cron field → the set of matching values. Supports ``*``, ``*/n``,
    numbers, ranges (``a-b``), steps on ranges (``a-b/n``), and comma lists."""
    values: set[int] = set()
    for part in field.split(","):
        part = part.strip()
        if not part:
            raise ValueError("empty cron field element")
        step = 1
        if "/" in part:
            part, step_text = part.split("/", 1)
            step = int(step_text)
            if step < 1:
                raise ValueError("cron step must be >= 1")
        if part == "*":
            start, end = low, high
        elif "-" in part:
            start_text, end_text = part.split("-", 1)
            start, end = int(start_text), int(end_text)
        else:
            start = end = int(part)
        if start < low or end > high or start > end:
            raise ValueError(f"cron value out of range {low}-{high}: {part}")
        values.update(range(start, end + 1, step))
    return values


def parse_cron_expression(expression: str) -> dict[str, set[int]]:
    """Parse a 5-field cron expression (minute hour day-of-month month
    day-of-week; Sunday = 0 or 7). Raises ValueError on malformed input."""
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError("cron expressions have 5 fields: minute hour day month weekday")
    minute, hour, dom, month, dow = fields
    parsed = {
        "minute": parse_cron_field(minute, 0, 59),
        "hour": parse_cron_field(hour, 0, 23),
        "dom": parse_cron_field(dom, 1, 31),
        "month": parse_cron_field(month, 1, 12),
        "dow": {value % 7 for value in parse_cron_field(dow, 0, 7)},
        # Standard cron rule: when BOTH day-of-month and day-of-week are
        # restricted, a day matches if EITHER does.
        "dom_restricted": dom != "*",
        "dow_restricted": dow != "*",
    }
    return parsed


def next_cron_run(expression: str, after: datetime) -> datetime:
    """The first minute strictly after ``after`` matching the expression
    (UTC). Searches up to 366 days ahead."""
    cron = parse_cron_expression(expression)
    candidate = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(366):
        day = candidate.date()
        dom_ok = day.day in cron["dom"]
        dow_ok = (day.weekday() + 1) % 7 in cron["dow"]  # Python Monday=0 → cron Sunday=0
        if cron["dom_restricted"] and cron["dow_restricted"]:
            day_ok = dom_ok or dow_ok
        else:
            day_ok = dom_ok and dow_ok
        if day.month in cron["month"] and day_ok:
            start_hour = candidate.hour if day == candidate.date() else 0
            for hour in sorted(cron["hour"]):
                if hour < start_hour:
                    continue
                start_minute = candidate.minute if (day == candidate.date() and hour == candidate.hour) else 0
                for minute in sorted(cron["minute"]):
                    if minute < start_minute:
                        continue
                    return candidate.replace(hour=hour, minute=minute)
        candidate = (candidate + timedelta(days=1)).replace(hour=0, minute=0)
    raise ValueError("cron expression never matches within a year")


def mask_sql_for_scanning(sql_text: str) -> str:
    """Blank out string literals and comments so keyword scans don't false-positive
    on data values or commented-out text."""
    text = re.sub(r"'(?:[^']|'')*'", "''", sql_text)
    text = re.sub(r"--[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return text


def normalize_sql_for_cache(sql_text: str) -> str:
    """Canonical form of a statement for result-cache keying.

    Comments are dropped and runs of whitespace outside quoted regions collapse to
    a single space, so cosmetic reformatting of the same query still hits the
    cache. Text outside quotes is lowercased (keywords and unquoted identifiers
    are case-insensitive in Trino); string literals and quoted identifiers are
    kept byte-exact because their case is significant.
    """
    out: list[str] = []
    state = "normal"
    i = 0
    length = len(sql_text)
    while i < length:
        ch = sql_text[i]
        nxt = sql_text[i + 1] if i + 1 < length else ""
        if state == "normal":
            if ch == "-" and nxt == "-":
                state = "line_comment"
                i += 2
                continue
            if ch == "/" and nxt == "*":
                state = "block_comment"
                i += 2
                continue
            if ch in {"'", '"'}:
                state = "string" if ch == "'" else "quoted_ident"
                out.append(ch)
                i += 1
                continue
            if ch.isspace():
                if out and out[-1] != " ":
                    out.append(" ")
                i += 1
                continue
            out.append(ch.lower())
            i += 1
            continue
        if state == "line_comment":
            if ch == "\n":
                state = "normal"
                if out and out[-1] != " ":
                    out.append(" ")
            i += 1
            continue
        if state == "block_comment":
            if ch == "*" and nxt == "/":
                state = "normal"
                if out and out[-1] != " ":
                    out.append(" ")
                i += 2
                continue
            i += 1
            continue
        out.append(ch)
        if state == "string" and ch == "'":
            if nxt == "'":  # escaped quote stays inside the literal
                out.append(nxt)
                i += 2
                continue
            state = "normal"
        elif state == "quoted_ident" and ch == '"':
            state = "normal"
        i += 1
    return "".join(out).strip()


def is_cacheable_sql(statement: str) -> bool:
    """Only read-only statements may produce or consume cache entries."""
    match = re.match(r"\s*([a-zA-Z]+)", statement)
    return bool(match) and match.group(1).lower() in {"select", "with"}


def query_cache_key(
    user_id: Any, cluster_id: Any, catalog: str, schema_name: str, normalized_sql: str
) -> str:
    """Result-cache key over an already-normalized statement. Includes the user
    id so a cached result is only ever served back to the user whose run
    produced it — cache reuse can never widen who sees a result set."""
    material = "\n".join([str(user_id), str(cluster_id), catalog, schema_name, normalized_sql])
    return token_hash(material)


def validate_read_only_sql(sql_text: str) -> str:
    """Return a single, validated read-only statement or raise ApiError(400).

    Enforces: non-empty, exactly one statement, starts with SELECT/WITH, and no
    denylisted keyword. This is the safety boundary around LLM-generated SQL.
    """
    text = (sql_text or "").strip().rstrip(";").strip()
    if not text:
        raise ApiError(400, "The assistant did not return any SQL to run.")
    statements = split_sql_statements(text)
    if len(statements) != 1:
        raise ApiError(400, "Only one read-only SQL statement can run per question.")
    statement = statements[0]
    keyword_match = re.match(r"\s*([a-zA-Z]+)", statement)
    keyword = (keyword_match.group(1) if keyword_match else "").lower()
    if keyword not in {"select", "with"}:
        raise ApiError(400, "Only read-only SELECT queries are allowed.")
    scanned = mask_sql_for_scanning(statement).lower()
    for word in ASK_TRINO_SQL_DENYLIST:
        if re.search(rf"\b{word}\b", scanned):
            raise ApiError(400, f"The generated SQL contains a disallowed keyword: {word}.")
    return statement


def parse_llm_json(content: str) -> dict[str, Any]:
    """Parse the model's reply into a dict. Models sometimes wrap JSON in prose or
    markdown fences, so fall back to the first ``{...}`` block, then to treating the
    whole reply as a plain-text explanation."""
    text = (content or "").strip()
    if not text:
        return {"explanation": "", "sql": None, "chartType": "none"}
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
    return {"explanation": text, "sql": None, "chartType": "none"}


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def split_sql_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    statement_start = 0
    state = "normal"
    index = 0
    while index < len(sql_text):
        char = sql_text[index]
        next_char = sql_text[index + 1] if index + 1 < len(sql_text) else ""

        if state == "line-comment":
            if char == "\n":
                state = "normal"
            index += 1
            continue
        if state == "block-comment":
            if char == "*" and next_char == "/":
                state = "normal"
                index += 2
            else:
                index += 1
            continue
        if state == "single-quote":
            if char == "'" and next_char == "'":
                index += 2
            elif char == "'":
                state = "normal"
                index += 1
            else:
                index += 1
            continue
        if state == "double-quote":
            if char == '"' and next_char == '"':
                index += 2
            elif char == '"':
                state = "normal"
                index += 1
            else:
                index += 1
            continue

        if char == "-" and next_char == "-":
            state = "line-comment"
            index += 2
        elif char == "/" and next_char == "*":
            state = "block-comment"
            index += 2
        elif char == "'":
            state = "single-quote"
            index += 1
        elif char == '"':
            state = "double-quote"
            index += 1
        elif char == ";":
            statement = sql_text[statement_start:index].strip()
            if statement:
                statements.append(statement)
            statement_start = index + 1
            index += 1
        else:
            index += 1

    last = sql_text[statement_start:].strip()
    if last:
        statements.append(last)
    return statements


class _Headers(Protocol):
    def get(self, key: str, default: str = ...) -> str | None: ...


class RequestLike(Protocol):
    """Minimal request shape the auth helpers need.

    The FastAPI adapter (``trinohub.api``) is the only caller; it passes a thin
    adapter exposing ``headers.get("Cookie")``. Kept as a Protocol so the auth
    helpers don't depend on any particular web framework.
    """

    headers: _Headers


class TrinoHubApp:
    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        aws: CloudProvider | None = None,
        *,
        enable_health_poller: bool = False,
        require_setup_token: bool = True,
        secret_store: SecretStore | None = None,
        trino_version_fetcher: Callable[[], list[str]] | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        # The infrastructure engine, reached only through the CloudProvider seam.
        # ``aws`` is the AWS implementation today; a second provider drops in here.
        self.aws: CloudProvider = aws or AwsInspector()
        # Source credentials live in a secret backend, never in the metadata DB.
        # Default to AWS Secrets Manager using the control plane's own boto3 creds.
        self.secret_store: SecretStore = secret_store or SecretsManagerStore(
            client_factory=lambda: self.aws.clients()["secretsmanager"]
        )
        init_db(self.db_path)
        self._seed_rbac()
        # Live Trino-release discovery (None = static SUPPORTED_TRINO_VERSIONS
        # only, which keeps unit tests and air-gapped deployments off the
        # network). create_app wires in the Maven Central fetcher.
        self._trino_version_fetcher = trino_version_fetcher
        self._trino_versions_cache: tuple[float, list[str]] | None = None
        self._health_poller_started = False
        self._owner_username_cache: dict[Any, str] = {}
        self._login_failures: dict[str, list[float]] = {}
        self._login_lock = threading.Lock()
        # OIDC login round-trip state + discovery-document cache (see Phase 2).
        self._oidc_states: dict[str, dict[str, Any]] = {}
        self._oidc_lock = threading.Lock()
        self._oidc_discovery_cache: tuple[float, str, dict[str, Any]] | None = None
        self._require_setup_token = require_setup_token
        if require_setup_token:
            self.ensure_bootstrap_token()
        if enable_health_poller:
            self.start_health_poller()

    @property
    def setup_token_path(self) -> Path:
        return self.db_path.parent / "setup-token"

    def ensure_bootstrap_token(self) -> None:
        """Mint a one-time setup token while first-run setup is pending.

        The hash is stored in the DB (authority for verification); the plaintext
        is written to a root-only file and printed to the log so an operator with
        host access — but not a network attacker — can complete setup. No-op once
        setup is complete; the stale token is cleaned up then.
        """
        if self.setup_row():
            self._clear_bootstrap_token()
            return
        # Self-heal if the plaintext file was deleted to rotate the token.
        if not self.setup_token_path.exists():
            with self.conn() as conn:
                conn.execute("DELETE FROM bootstrap_token WHERE id = 1")
        token = new_session_token()
        with self.conn() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO bootstrap_token (id, token_hash, created_at) VALUES (1, ?, ?)",
                (token_hash(token), utc_now()),
            )
            won = cursor.rowcount == 1
        if won:
            try:
                self.setup_token_path.parent.mkdir(parents=True, exist_ok=True)
                self.setup_token_path.write_text(token + "\n")
                self.setup_token_path.chmod(0o600)
            except OSError:
                pass
            printed = token
        else:
            try:
                printed = self.setup_token_path.read_text().strip()
            except OSError:
                printed = "(see " + str(self.setup_token_path) + ")"
        print(
            "TrinoHub first-run setup is pending. Setup token: "
            f"{printed}  (also at {self.setup_token_path}). "
            "Provide it as 'setup_token' to POST /api/setup/complete."
        )

    def _clear_bootstrap_token(self) -> None:
        with self.conn() as conn:
            conn.execute("DELETE FROM bootstrap_token WHERE id = 1")
        try:
            self.setup_token_path.unlink()
        except OSError:
            pass

    def _verify_setup_token(self, provided: Any) -> None:
        if not self._require_setup_token:
            return
        with self.conn() as conn:
            row = conn.execute("SELECT token_hash FROM bootstrap_token WHERE id = 1").fetchone()
        if not row:
            raise ApiError(403, "Setup token is unavailable; check the service logs.")
        token = str(provided or "")
        if not token or not hmac.compare_digest(token_hash(token), row["token_hash"]):
            raise ApiError(403, "A valid setup_token is required to complete first-run setup.")

    def conn(self) -> sqlite3.Connection:
        return connect(self.db_path)

    @staticmethod
    def _safe_aws_error(exc: Exception) -> str:
        """A message safe to return to an authenticated admin.

        botocore ``ClientError``/``BotoCoreError`` messages are operator-facing
        and describe the actual AWS condition (capacity, permissions, quotas), so
        we surface them. Anything else may carry internal implementation detail,
        so we stay generic and rely on the recorded cluster event + server log.
        """
        if (type(exc).__module__ or "").startswith("botocore"):
            return str(exc)
        return "an unexpected internal error (check the service logs)."

    def current_user(self, request: RequestLike) -> dict[str, Any] | None:
        # Headless clients authenticate with a long-lived API token:
        # ``Authorization: Bearer tht_...`` (see create_api_token).
        authorization = request.headers.get("Authorization", "") or request.headers.get("authorization", "")
        if authorization.startswith("Bearer "):
            bearer = self.user_for_api_token(authorization[len("Bearer "):].strip())
            if bearer:
                return bearer
        header = request.headers.get("Cookie", "")
        parsed = cookies.SimpleCookie()
        parsed.load(header)
        if SESSION_COOKIE not in parsed:
            return None
        digest = token_hash(parsed[SESSION_COOKIE].value)
        now = utc_now()
        with self.conn() as conn:
            row = conn.execute(
                """
                SELECT users.* FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token_hash = ? AND sessions.expires_at > ? AND users.is_active = 1
                """,
                (digest, now),
            ).fetchone()
            return row_to_dict(row)

    def user_for_api_token(self, token: str) -> dict[str, Any] | None:
        if not token.startswith(API_TOKEN_PREFIX):
            return None
        digest = token_hash(token)
        now = utc_now()
        with self.conn() as conn:
            row = conn.execute(
                """
                SELECT users.*, api_tokens.id AS token_id, api_tokens.last_used_at AS token_last_used
                FROM api_tokens
                JOIN users ON users.id = api_tokens.user_id
                WHERE api_tokens.token_hash = ?
                  AND (api_tokens.expires_at IS NULL OR api_tokens.expires_at > ?)
                  AND users.is_active = 1
                """,
                (digest, now),
            ).fetchone()
            if not row:
                return None
            user = row_to_dict(row)
            token_id = user.pop("token_id")
            last_used = user.pop("token_last_used")
            # Coarse last-used tracking (minute granularity keeps writes rare).
            if not last_used or last_used[:16] != now[:16]:
                conn.execute("UPDATE api_tokens SET last_used_at = ? WHERE id = ?", (now, token_id))
        return user

    def require_user(self, request: RequestLike) -> dict[str, Any]:
        user = self.current_user(request)
        if not user:
            raise ApiError(401, "Authentication required.")
        return user

    def require_admin(self, request: RequestLike) -> dict[str, Any]:
        user = self.require_user(request)
        if user["role"] != "admin":
            raise ApiError(403, "Admin role required.")
        return user

    # --- RBAC: roles, privileges, and data-access grants --------------------

    def _seed_rbac(self) -> None:
        """Seed the system ``admin``/``user`` roles and backfill membership.

        ``admin`` carries every privilege; ``user`` carries none. Both get
        wildcard cluster/catalog grants so a pre-RBAC database behaves exactly
        as before: everyone can query everything until an admin narrows it.
        Users without any role rows (pre-RBAC records) are enrolled in the
        seeded role matching their legacy ``users.role`` column. Idempotent.
        """
        now = utc_now()
        with self.conn() as conn:
            for name, description, privileges in (
                ("admin", "Full administrative access (system role).", list(ALL_PRIVILEGES)),
                ("user", "Query access without administrative privileges (system role).", []),
            ):
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO roles (name, description, is_system, privileges_json, created_at, updated_at)
                    VALUES (?, ?, 1, ?, ?, ?)
                    """,
                    (name, description, dumps(privileges), now, now),
                )
                if cursor.rowcount:
                    role_id = conn.execute("SELECT id FROM roles WHERE name = ?", (name,)).fetchone()["id"]
                    for grant_type in ("cluster", "catalog"):
                        conn.execute(
                            "INSERT OR IGNORE INTO role_grants (role_id, grant_type, target, created_at) VALUES (?, ?, ?, ?)",
                            (role_id, grant_type, GRANT_WILDCARD, now),
                        )
            conn.execute(
                """
                INSERT OR IGNORE INTO user_roles (user_id, role_id)
                SELECT users.id, roles.id FROM users JOIN roles ON roles.name = users.role
                WHERE users.id NOT IN (SELECT user_id FROM user_roles)
                """
            )

    def user_role_rows(self, conn: sqlite3.Connection, user_id: Any) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT roles.* FROM roles
            JOIN user_roles ON user_roles.role_id = roles.id
            WHERE user_roles.user_id = ?
            ORDER BY roles.name
            """,
            (user_id,),
        ).fetchall()
        return [row_to_dict(row) for row in rows]

    def user_privileges(self, user: dict[str, Any]) -> set[str]:
        with self.conn() as conn:
            roles = self.user_role_rows(conn, user["id"])
        if not roles:
            # Pre-RBAC record (e.g. inserted directly): the legacy role column
            # is the whole story.
            return set(ALL_PRIVILEGES) if user.get("role") == "admin" else set()
        privileges: set[str] = set()
        for role in roles:
            privileges.update(loads(role["privileges_json"], []))
        return privileges

    def has_privilege(self, user: dict[str, Any], privilege: str) -> bool:
        return privilege in self.user_privileges(user)

    def require_privilege(self, user: dict[str, Any], privilege: str) -> dict[str, Any]:
        if not self.has_privilege(user, privilege):
            raise ApiError(403, f"The {privilege} privilege is required.")
        return user

    def user_grant_targets(self, user: dict[str, Any], grant_type: str) -> set[str]:
        with self.conn() as conn:
            roles = self.user_role_rows(conn, user["id"])
            if not roles:
                # Pre-RBAC record: preserve the historical everyone-can-query default.
                return {GRANT_WILDCARD}
            marks = ",".join("?" * len(roles))
            rows = conn.execute(
                f"SELECT DISTINCT target FROM role_grants WHERE grant_type = ? AND role_id IN ({marks})",
                (grant_type, *[role["id"] for role in roles]),
            ).fetchall()
        return {row["target"] for row in rows}

    def user_can_use_cluster(self, user: dict[str, Any], cluster_id: Any) -> bool:
        targets = self.user_grant_targets(user, "cluster")
        return GRANT_WILDCARD in targets or str(cluster_id) in targets

    def require_cluster_access(self, user: dict[str, Any], cluster_id: Any) -> None:
        if not self.user_can_use_cluster(user, cluster_id):
            raise ApiError(403, "You do not have access to this cluster. Ask an admin for a cluster grant.")

    def user_can_use_catalog(self, user: dict[str, Any], catalog_name: str) -> bool:
        # ``system`` is cluster metadata, not data — always browsable.
        if not catalog_name or catalog_name == "system":
            return True
        targets = self.user_grant_targets(user, "catalog")
        return GRANT_WILDCARD in targets or catalog_name in targets

    def require_catalog_access(self, user: dict[str, Any], catalog_name: str) -> None:
        if not self.user_can_use_catalog(user, catalog_name):
            raise ApiError(403, f"You do not have access to catalog {catalog_name}. Ask an admin for a catalog grant.")

    def decorate_user(self, user: dict[str, Any]) -> dict[str, Any]:
        """public_user plus the RBAC surface the UI needs (roles + privileges)."""
        public = public_user(user)
        with self.conn() as conn:
            roles = self.user_role_rows(conn, user["id"])
        if roles:
            public["roles"] = [role["name"] for role in roles]
            privileges: set[str] = set()
            for role in roles:
                privileges.update(loads(role["privileges_json"], []))
        else:
            public["roles"] = [user.get("role") or "user"]
            privileges = set(ALL_PRIVILEGES) if user.get("role") == "admin" else set()
        public["privileges"] = sorted(privileges)
        return public

    def audit(
        self,
        actor: dict[str, Any] | None,
        action: str,
        target: str = "",
        detail: dict[str, Any] | None = None,
    ) -> None:
        with self.conn() as conn:
            conn.execute(
                """
                INSERT INTO security_audit_log (actor_user_id, actor_username, action, target, detail_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    actor.get("id") if actor else None,
                    (actor or {}).get("username", "") or "",
                    action,
                    target,
                    dumps(detail or {}),
                    utc_now(),
                ),
            )
            # Mutations to who-can-see-what (roles, policies, tags, users) or to
            # what-data-is-behind-a-name (catalogs, clusters) must not be
            # outlived by cached results produced under the old rules. These are
            # rare admin actions, so flushing the whole result cache is cheap.
            if action.split(".")[0] in {"role", "policy", "tag", "tag_policy", "user", "catalog", "cluster"}:
                conn.execute("UPDATE query_runs SET cache_key = '' WHERE cache_key != ''")
        # Security-sensitive mutations can also fan out to the webhook channel.
        if action.split(".")[0] in {"user", "role", "settings", "token"}:
            actor_name = (actor or {}).get("username") or "system"
            self.notify("security", f"{actor_name}: {action} {target}".strip(), detail or {})

    def security_audit_entries(self, limit: int = 200) -> dict[str, Any]:
        limit = max(1, min(int(limit or 200), MAX_AUDIT_LOG_LIMIT))
        with self.conn() as conn:
            rows = conn.execute(
                "SELECT * FROM security_audit_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return {
            "entries": [
                {
                    "id": row["id"],
                    "actor_user_id": row["actor_user_id"],
                    "actor_username": row["actor_username"],
                    "action": row["action"],
                    "target": row["target"],
                    "detail": loads(row["detail_json"], {}),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
        }

    def _security_holder_count(self, conn: sqlite3.Connection) -> int:
        """Active users who hold MANAGE_SECURITY, as the DB stands right now
        (called inside a mutation's transaction to validate the end state).
        Legacy admin users without role rows count as holders."""
        via_roles = conn.execute(
            """
            SELECT COUNT(DISTINCT users.id) FROM users
            JOIN user_roles ON user_roles.user_id = users.id
            JOIN roles ON roles.id = user_roles.role_id
            WHERE users.is_active = 1 AND roles.privileges_json LIKE ?
            """,
            (f'%"{PRIVILEGE_MANAGE_SECURITY}"%',),
        ).fetchone()[0]
        legacy = conn.execute(
            """
            SELECT COUNT(*) FROM users
            WHERE is_active = 1 AND role = 'admin'
              AND id NOT IN (SELECT user_id FROM user_roles)
            """
        ).fetchone()[0]
        return int(via_roles) + int(legacy)

    def _require_security_holder_remains(self, conn: sqlite3.Connection) -> None:
        if self._security_holder_count(conn) < 1:
            raise ApiError(
                409,
                "Cannot remove the last active admin (no other user would hold the MANAGE_SECURITY privilege).",
            )

    def _normalize_privileges(self, raw: Any) -> list[str]:
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise ApiError(400, "privileges must be a list.")
        requested = {str(item).strip().upper() for item in raw if str(item).strip()}
        unknown = requested - set(ALL_PRIVILEGES)
        if unknown:
            raise ApiError(400, f"Unknown privileges: {', '.join(sorted(unknown))}. Valid: {', '.join(ALL_PRIVILEGES)}.")
        return [privilege for privilege in ALL_PRIVILEGES if privilege in requested]

    def _normalize_grant_targets(self, raw: Any, grant_type: str) -> list[str]:
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise ApiError(400, f"{grant_type}_grants must be a list.")
        targets: list[str] = []
        for value in raw:
            target = str(value).strip()
            if not target:
                continue
            if target != GRANT_WILDCARD:
                if grant_type == "cluster" and not target.isdigit():
                    raise ApiError(400, "cluster grants must be cluster ids or '*'.")
                if grant_type == "catalog" and not CATALOG_NAME_PATTERN.fullmatch(target):
                    raise ApiError(400, "catalog grants must be catalog names or '*'.")
            if target not in targets:
                targets.append(target)
        return targets

    def public_role(self, conn: sqlite3.Connection, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        grants = conn.execute(
            "SELECT grant_type, target FROM role_grants WHERE role_id = ? ORDER BY grant_type, target",
            (row["id"],),
        ).fetchall()
        member_count = conn.execute(
            "SELECT COUNT(*) FROM user_roles WHERE role_id = ?", (row["id"],)
        ).fetchone()[0]
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "is_system": bool(row["is_system"]),
            "privileges": loads(row["privileges_json"], []),
            "cluster_grants": [g["target"] for g in grants if g["grant_type"] == "cluster"],
            "catalog_grants": [g["target"] for g in grants if g["grant_type"] == "catalog"],
            "member_count": member_count,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_roles(self) -> dict[str, Any]:
        with self.conn() as conn:
            rows = conn.execute("SELECT * FROM roles ORDER BY is_system DESC, name").fetchall()
            return {"roles": [self.public_role(conn, row) for row in rows], "privileges": list(ALL_PRIVILEGES)}

    def _replace_role_grants(self, conn: sqlite3.Connection, role_id: int, grant_type: str, targets: list[str]) -> None:
        now = utc_now()
        conn.execute("DELETE FROM role_grants WHERE role_id = ? AND grant_type = ?", (role_id, grant_type))
        for target in targets:
            conn.execute(
                "INSERT INTO role_grants (role_id, grant_type, target, created_at) VALUES (?, ?, ?, ?)",
                (role_id, grant_type, target, now),
            )

    def create_role(self, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip().lower()
        if not ROLE_NAME_PATTERN.fullmatch(name):
            raise ApiError(400, "Role names are 2-63 lowercase letters, digits, hyphens, or underscores.")
        description = str(payload.get("description", "")).strip()
        privileges = self._normalize_privileges(payload.get("privileges"))
        cluster_grants = self._normalize_grant_targets(payload.get("cluster_grants"), "cluster")
        catalog_grants = self._normalize_grant_targets(payload.get("catalog_grants"), "catalog")
        now = utc_now()
        with self.conn() as conn:
            existing = conn.execute("SELECT id FROM roles WHERE name = ?", (name,)).fetchone()
            if existing:
                raise ApiError(409, f"A role named {name} already exists.")
            cursor = conn.execute(
                """
                INSERT INTO roles (name, description, is_system, privileges_json, created_at, updated_at)
                VALUES (?, ?, 0, ?, ?, ?)
                """,
                (name, description, dumps(privileges), now, now),
            )
            role_id = cursor.lastrowid
            self._replace_role_grants(conn, role_id, "cluster", cluster_grants)
            self._replace_role_grants(conn, role_id, "catalog", catalog_grants)
            row = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
            result = {"role": self.public_role(conn, row)}
        self.audit(actor, "role.create", name, {"privileges": privileges, "cluster_grants": cluster_grants, "catalog_grants": catalog_grants})
        return result

    def update_role(self, role_id: int, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
            if not row:
                raise ApiError(404, "Role not found.")
            current = self.public_role(conn, row)

            changed: dict[str, Any] = {}
            description = current["description"]
            if "description" in payload:
                description = str(payload["description"]).strip()
                if description != current["description"]:
                    changed["description"] = description
            # The seeded admin role is the safety anchor: its privileges and
            # wildcard grants are immutable so an account can't lock itself out.
            locked = current["is_system"] and current["name"] == "admin"
            privileges = current["privileges"]
            if "privileges" in payload:
                privileges = self._normalize_privileges(payload["privileges"])
                if privileges != current["privileges"]:
                    if locked:
                        raise ApiError(409, "The admin role's privileges cannot be changed.")
                    changed["privileges"] = privileges
            cluster_grants = current["cluster_grants"]
            if "cluster_grants" in payload:
                cluster_grants = self._normalize_grant_targets(payload["cluster_grants"], "cluster")
                if cluster_grants != current["cluster_grants"]:
                    if locked:
                        raise ApiError(409, "The admin role's grants cannot be changed.")
                    changed["cluster_grants"] = cluster_grants
            catalog_grants = current["catalog_grants"]
            if "catalog_grants" in payload:
                catalog_grants = self._normalize_grant_targets(payload["catalog_grants"], "catalog")
                if catalog_grants != current["catalog_grants"]:
                    if locked:
                        raise ApiError(409, "The admin role's grants cannot be changed.")
                    changed["catalog_grants"] = catalog_grants

            if not changed:
                return {"role": current, "changes": []}

            conn.execute(
                "UPDATE roles SET description = ?, privileges_json = ?, updated_at = ? WHERE id = ?",
                (description, dumps(privileges), utc_now(), role_id),
            )
            if "cluster_grants" in changed:
                self._replace_role_grants(conn, role_id, "cluster", cluster_grants)
            if "catalog_grants" in changed:
                self._replace_role_grants(conn, role_id, "catalog", catalog_grants)
            # Dropping MANAGE_SECURITY from this role must leave someone holding it.
            if "privileges" in changed:
                self._require_security_holder_remains(conn)
            updated = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
            result = {"role": self.public_role(conn, updated), "changes": sorted(changed)}
        self.audit(actor, "role.update", current["name"], {"changed": sorted(changed)})
        return result

    def delete_role(self, role_id: int, actor: dict[str, Any] | None = None) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
            if not row:
                raise ApiError(404, "Role not found.")
            if row["is_system"]:
                raise ApiError(409, "System roles cannot be deleted.")
            name = row["name"]
            conn.execute("DELETE FROM roles WHERE id = ?", (role_id,))
            self._require_security_holder_remains(conn)
        self.audit(actor, "role.delete", name)
        return {"ok": True}

    def _set_user_roles(self, conn: sqlite3.Connection, user_id: int, role_names: list[str]) -> list[str]:
        """Replace a user's role memberships; returns the canonical name list."""
        names: list[str] = []
        role_ids: list[int] = []
        for raw in role_names:
            name = str(raw).strip().lower()
            if not name or name in names:
                continue
            role = conn.execute("SELECT id FROM roles WHERE name = ?", (name,)).fetchone()
            if not role:
                raise ApiError(400, f"Unknown role: {name}.")
            names.append(name)
            role_ids.append(role["id"])
        if not role_ids:
            raise ApiError(400, "Users need at least one role.")
        conn.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
        for role_id in role_ids:
            conn.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, role_id))
        # Keep the legacy shortcut column meaningful: 'admin' if the seeded
        # admin role is held, else 'user'.
        conn.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            ("admin" if "admin" in names else "user", user_id),
        )
        return names

    # --- API tokens (headless bearer auth) -----------------------------------

    def public_api_token(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "user_id": row["user_id"],
            "username": row["username"] if "username" in row.keys() else "",
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
            "last_used_at": row["last_used_at"],
        }

    def list_api_tokens(self, user: dict[str, Any]) -> dict[str, Any]:
        """A user sees their own tokens; MANAGE_USERS holders see all."""
        see_all = self.has_privilege(user, PRIVILEGE_MANAGE_USERS)
        where = "" if see_all else "WHERE api_tokens.user_id = ?"
        params = () if see_all else (user["id"],)
        with self.conn() as conn:
            rows = conn.execute(
                f"""
                SELECT api_tokens.*, users.username AS username FROM api_tokens
                JOIN users ON users.id = api_tokens.user_id
                {where}
                ORDER BY api_tokens.created_at DESC
                """,
                params,
            ).fetchall()
        return {"tokens": [self.public_api_token(row) for row in rows]}

    def create_api_token(self, payload: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip()
        if not name or len(name) > MAX_API_TOKEN_NAME_LENGTH:
            raise ApiError(400, f"Token name is required (max {MAX_API_TOKEN_NAME_LENGTH} characters).")
        target_user_id = payload.get("user_id")
        if target_user_id in (None, "", actor["id"]):
            target_user_id = actor["id"]
        else:
            # Minting a token that acts as somebody else is user management.
            self.require_privilege(actor, PRIVILEGE_MANAGE_USERS)
            try:
                target_user_id = int(target_user_id)
            except (TypeError, ValueError):
                raise ApiError(400, "user_id must be an integer.") from None
        expires_at = None
        if payload.get("expires_days") not in (None, ""):
            try:
                days = int(payload["expires_days"])
            except (TypeError, ValueError):
                raise ApiError(400, "expires_days must be an integer.") from None
            if days < 1 or days > 3650:
                raise ApiError(400, "expires_days must be between 1 and 3650.")
            expires_at = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds")
        token = API_TOKEN_PREFIX + new_session_token()
        now = utc_now()
        with self.conn() as conn:
            target = conn.execute("SELECT * FROM users WHERE id = ?", (target_user_id,)).fetchone()
            if not target or not target["is_active"]:
                raise ApiError(404, "Target user not found or inactive.")
            cursor = conn.execute(
                """
                INSERT INTO api_tokens (name, token_hash, user_id, created_by, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, token_hash(token), target_user_id, actor["username"], now, expires_at),
            )
            row = conn.execute(
                """
                SELECT api_tokens.*, users.username AS username FROM api_tokens
                JOIN users ON users.id = api_tokens.user_id WHERE api_tokens.id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
            public = self.public_api_token(row)
        self.audit(actor, "token.create", name, {"user": public["username"], "expires_at": expires_at})
        # The plaintext token is returned exactly once and never stored.
        return {"token": token, "api_token": public}

    def delete_api_token(self, token_id: int, actor: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute(
                """
                SELECT api_tokens.*, users.username AS username FROM api_tokens
                JOIN users ON users.id = api_tokens.user_id WHERE api_tokens.id = ?
                """,
                (token_id,),
            ).fetchone()
            if not row:
                raise ApiError(404, "Token not found.")
            if row["user_id"] != actor["id"] and not self.has_privilege(actor, PRIVILEGE_MANAGE_USERS):
                raise ApiError(404, "Token not found.")
            conn.execute("DELETE FROM api_tokens WHERE id = ?", (token_id,))
            name = row["name"]
        self.audit(actor, "token.delete", name)
        return {"deleted": True}

    def revoke_user_sessions(self, user: dict[str, Any]) -> dict[str, Any]:
        """Force re-auth everywhere: drop every browser session for this user."""
        with self.conn() as conn:
            deleted = conn.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],)).rowcount
        self.audit(user, "session.revoke_all", user["username"], {"sessions": deleted})
        return {"revoked": deleted}

    def session_hours(self) -> int:
        setup = self.setup_row()
        raw = setup.get("session_hours") if setup else None
        try:
            hours = int(raw) if raw is not None else DEFAULT_SESSION_HOURS
        except (TypeError, ValueError):
            hours = DEFAULT_SESSION_HOURS
        return min(max(hours, 1), MAX_SESSION_HOURS)

    def set_session_hours(self, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        setup = self.setup_row()
        if not setup:
            raise ApiError(409, "Complete setup before configuring sessions.")
        raw = payload.get("session_hours")
        try:
            hours = int(raw)
        except (TypeError, ValueError):
            raise ApiError(400, "session_hours must be an integer.") from None
        if hours < 1 or hours > MAX_SESSION_HOURS:
            raise ApiError(400, f"session_hours must be between 1 and {MAX_SESSION_HOURS}.")
        with self.conn() as conn:
            conn.execute("UPDATE setup_settings SET session_hours = ? WHERE id = 1", (hours,))
        self.audit(actor, "settings.session_hours", str(hours))
        return {"session_hours": hours}

    def result_cache_ttl_minutes(self) -> int:
        setup = self.setup_row()
        raw = setup.get("result_cache_ttl_minutes") if setup else None
        try:
            minutes = int(raw) if raw is not None else DEFAULT_RESULT_CACHE_TTL_MINUTES
        except (TypeError, ValueError):
            minutes = DEFAULT_RESULT_CACHE_TTL_MINUTES
        return min(max(minutes, 0), MAX_RESULT_CACHE_TTL_MINUTES)

    def set_result_cache_ttl(self, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        setup = self.setup_row()
        if not setup:
            raise ApiError(409, "Complete setup before configuring the result cache.")
        raw = payload.get("result_cache_ttl_minutes")
        try:
            minutes = int(raw)
        except (TypeError, ValueError):
            raise ApiError(400, "result_cache_ttl_minutes must be an integer.") from None
        if minutes < 0 or minutes > MAX_RESULT_CACHE_TTL_MINUTES:
            raise ApiError(
                400,
                f"result_cache_ttl_minutes must be between 0 (disabled) and {MAX_RESULT_CACHE_TTL_MINUTES}.",
            )
        with self.conn() as conn:
            conn.execute("UPDATE setup_settings SET result_cache_ttl_minutes = ? WHERE id = 1", (minutes,))
        self.audit(actor, "settings.result_cache_ttl", str(minutes))
        return {"result_cache_ttl_minutes": minutes}

    def allowed_ui_cidrs_settings(self) -> dict[str, Any]:
        setup = self.setup_row()
        return {"allowed_ui_cidrs": loads(setup["allowed_ui_cidrs"], []) if setup else []}

    def set_allowed_ui_cidrs(
        self,
        payload: dict[str, Any],
        actor: dict[str, Any] | None = None,
        *,
        remote_addr: str | None = None,
        forwarded_for: str | None = None,
    ) -> dict[str, Any]:
        setup = self.setup_row()
        if not setup:
            raise ApiError(409, "Complete setup before configuring the UI allowlist.")
        cidrs = self.normalize_allowed_ui_cidrs(payload.get("allowed_ui_cidrs"))
        self._guard_ui_cidr_lockout(
            cidrs,
            remote_addr=remote_addr,
            forwarded_for=forwarded_for,
            confirmed=payload.get("confirm_lockout") is True,
        )
        with self.conn() as conn:
            conn.execute("UPDATE setup_settings SET allowed_ui_cidrs = ? WHERE id = 1", (dumps(cidrs),))
        self.audit(actor, "settings.allowed_ui_cidrs", ", ".join(cidrs) or "(unrestricted)")
        # The TLS gateway mirrors the UI allowlist into its Caddy config.
        self._sync_tls_gateway_safe()
        return {"allowed_ui_cidrs": cidrs}

    # --- OIDC SSO -------------------------------------------------------------
    # Confidential-client authorization-code flow implemented on the stdlib.
    # The ID token arrives straight from the token endpoint over TLS with
    # client authentication, so per OIDC Core §3.1.3.7 the TLS channel stands
    # in for local signature verification; issuer/audience/expiry/nonce are
    # all still validated below.

    def oidc_settings(self) -> dict[str, Any]:
        setup = self.setup_row()
        return loads(setup.get("oidc_config_json", "{}"), {}) if setup else {}

    def oidc_enabled(self) -> bool:
        config = self.oidc_settings()
        return bool(config.get("enabled") and config.get("issuer") and config.get("client_id"))

    def public_oidc_settings(self) -> dict[str, Any]:
        config = self.oidc_settings()
        return {
            "enabled": bool(config.get("enabled")),
            "issuer": config.get("issuer", ""),
            "client_id": config.get("client_id", ""),
            "client_secret_set": bool(config.get("client_secret")),
            "group_claim": config.get("group_claim", "groups"),
            "group_role_mappings": config.get("group_role_mappings", {}),
            "default_role": config.get("default_role", "user"),
            "password_login": config.get("password_login", "all"),
            "redirect_base": config.get("redirect_base", ""),
        }

    def set_oidc_settings(self, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        setup = self.setup_row()
        if not setup:
            raise ApiError(409, "Complete setup before configuring SSO.")
        current = self.oidc_settings()
        enabled = bool(payload.get("enabled", current.get("enabled", False)))
        issuer = str(payload.get("issuer", current.get("issuer", ""))).strip().rstrip("/")
        if enabled and not issuer.startswith("https://"):
            raise ApiError(400, "issuer must be an https:// URL.")
        client_id = str(payload.get("client_id", current.get("client_id", ""))).strip()
        # A blank secret keeps the stored one so edits don't require re-entry.
        client_secret = str(payload.get("client_secret") or "") or current.get("client_secret", "")
        if enabled and (not client_id or not client_secret):
            raise ApiError(400, "client_id and client_secret are required to enable SSO.")
        group_claim = str(payload.get("group_claim", current.get("group_claim", "groups"))).strip() or "groups"
        mappings_raw = payload.get("group_role_mappings", current.get("group_role_mappings", {}))
        if not isinstance(mappings_raw, dict):
            raise ApiError(400, "group_role_mappings must be an object of {idp-group: role-name}.")
        default_role = str(payload.get("default_role", current.get("default_role", "user"))).strip().lower() or "user"
        password_login = str(payload.get("password_login", current.get("password_login", "all"))).strip()
        if password_login not in OIDC_PASSWORD_LOGIN_POLICIES:
            raise ApiError(400, f"password_login must be one of: {', '.join(sorted(OIDC_PASSWORD_LOGIN_POLICIES))}.")
        redirect_base = str(payload.get("redirect_base", current.get("redirect_base", ""))).strip().rstrip("/")
        with self.conn() as conn:
            # Validate role names against existing roles so logins never
            # reference a role that silently doesn't exist.
            known = {row["name"] for row in conn.execute("SELECT name FROM roles").fetchall()}
            mappings = {}
            for group, role in mappings_raw.items():
                role_name = str(role).strip().lower()
                if role_name not in known:
                    raise ApiError(400, f"Unknown role in group mapping: {role_name}.")
                mappings[str(group).strip()] = role_name
            if default_role not in known:
                raise ApiError(400, f"Unknown default_role: {default_role}.")
            config = {
                "enabled": enabled,
                "issuer": issuer,
                "client_id": client_id,
                "client_secret": client_secret,
                "group_claim": group_claim,
                "group_role_mappings": mappings,
                "default_role": default_role,
                "password_login": password_login,
                "redirect_base": redirect_base,
            }
            conn.execute("UPDATE setup_settings SET oidc_config_json = ? WHERE id = 1", (dumps(config),))
        self._oidc_discovery_cache = None
        self.audit(actor, "settings.oidc", issuer, {"enabled": enabled, "password_login": password_login})
        return {"oidc": self.public_oidc_settings()}

    def _oidc_http_json(self, url: str, data: bytes | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        request = urllib.request.Request(url, data=data, headers={"Accept": "application/json", **(headers or {})})
        with urllib.request.urlopen(request, timeout=OIDC_HTTP_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8", "replace"))

    def oidc_discovery(self) -> dict[str, Any]:
        config = self.oidc_settings()
        issuer = str(config.get("issuer", "")).rstrip("/")
        if not issuer:
            raise ApiError(409, "OIDC is not configured.")
        now = time.monotonic()
        cached = self._oidc_discovery_cache
        if cached and cached[1] == issuer and now < cached[0]:
            return cached[2]
        document = self._oidc_http_json(f"{issuer}/.well-known/openid-configuration")
        for key in ("authorization_endpoint", "token_endpoint", "issuer"):
            if not document.get(key):
                raise ApiError(502, f"OIDC discovery document is missing {key}.")
        self._oidc_discovery_cache = (now + OIDC_DISCOVERY_CACHE_SECONDS, issuer, document)
        return document

    def _prune_oidc_states(self) -> None:
        cutoff = time.monotonic() - OIDC_STATE_TTL_SECONDS
        with self._oidc_lock:
            for state in [s for s, meta in self._oidc_states.items() if meta["created"] < cutoff]:
                self._oidc_states.pop(state, None)

    def oidc_login_start(self, redirect_uri: str) -> str:
        """Mint state+nonce and build the provider authorization URL."""
        if not self.oidc_enabled():
            raise ApiError(409, "OIDC SSO is not enabled.")
        self._prune_oidc_states()
        config = self.oidc_settings()
        document = self.oidc_discovery()
        state = new_session_token()
        nonce = new_session_token()
        with self._oidc_lock:
            self._oidc_states[state] = {"nonce": nonce, "redirect_uri": redirect_uri, "created": time.monotonic()}
        from urllib.parse import urlencode

        query = urlencode(
            {
                "response_type": "code",
                "client_id": config["client_id"],
                "redirect_uri": redirect_uri,
                "scope": "openid email profile",
                "state": state,
                "nonce": nonce,
            }
        )
        separator = "&" if "?" in document["authorization_endpoint"] else "?"
        return f"{document['authorization_endpoint']}{separator}{query}"

    def oidc_redirect_uri(self, request_base: str) -> str:
        config = self.oidc_settings()
        base = (config.get("redirect_base") or request_base).rstrip("/")
        return f"{base}/api/auth/oidc/callback"

    @staticmethod
    def _decode_jwt_claims(id_token: str) -> dict[str, Any]:
        try:
            payload_part = id_token.split(".")[1]
            padded = payload_part + "=" * (-len(payload_part) % 4)
            import base64 as _base64

            return json.loads(_base64.urlsafe_b64decode(padded).decode("utf-8", "replace"))
        except (IndexError, ValueError):
            raise ApiError(502, "The identity provider returned a malformed ID token.") from None

    def oidc_callback(self, *, code: str, state: str) -> tuple[dict[str, Any], str]:
        """Exchange the code, validate claims, provision the user, mint a session."""
        if not self.oidc_enabled():
            raise ApiError(409, "OIDC SSO is not enabled.")
        with self._oidc_lock:
            meta = self._oidc_states.pop(state, None)
        if not meta or meta["created"] < time.monotonic() - OIDC_STATE_TTL_SECONDS:
            raise ApiError(400, "Login attempt expired or was tampered with. Try signing in again.")
        config = self.oidc_settings()
        document = self.oidc_discovery()
        from urllib.parse import urlencode

        body = urlencode(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": meta["redirect_uri"],
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
            }
        ).encode("ascii")
        try:
            tokens = self._oidc_http_json(
                document["token_endpoint"], data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except (urllib.error.URLError, OSError) as exc:
            raise ApiError(502, f"Token exchange with the identity provider failed: {exc}.") from None
        id_token = str(tokens.get("id_token") or "")
        if not id_token:
            raise ApiError(502, "The identity provider did not return an ID token.")
        claims = self._decode_jwt_claims(id_token)

        # Claim validation (issuer, audience, expiry, nonce) — the token came
        # over the authenticated TLS channel, so this completes OIDC validation.
        if str(claims.get("iss", "")).rstrip("/") != str(document["issuer"]).rstrip("/"):
            raise ApiError(401, "ID token issuer mismatch.")
        audience = claims.get("aud")
        audiences = audience if isinstance(audience, list) else [audience]
        if config["client_id"] not in audiences:
            raise ApiError(401, "ID token audience mismatch.")
        expiry = claims.get("exp")
        if not isinstance(expiry, (int, float)) or datetime.now(timezone.utc).timestamp() >= expiry:
            raise ApiError(401, "ID token is expired.")
        if claims.get("nonce") != meta["nonce"]:
            raise ApiError(401, "ID token nonce mismatch.")

        username = str(claims.get("preferred_username") or claims.get("email") or claims.get("sub") or "").strip().lower()
        if not username:
            raise ApiError(502, "The ID token carries no usable username claim.")
        email = str(claims.get("email") or "")
        groups = claims.get(config.get("group_claim", "groups")) or []
        if not isinstance(groups, list):
            groups = [groups]
        mappings = config.get("group_role_mappings", {})
        role_names = sorted({mappings[str(g)] for g in groups if str(g) in mappings})
        if not role_names:
            role_names = [config.get("default_role", "user")]

        now = utc_now()
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if row and not row["is_active"]:
                raise ApiError(403, "This account is deactivated.")
            if row:
                user_id = row["id"]
                if email and email != row["email"]:
                    conn.execute("UPDATE users SET email = ?, updated_at = ? WHERE id = ?", (email, now, user_id))
            else:
                # Just-in-time provisioning: SSO users have no usable password.
                cursor = conn.execute(
                    """
                    INSERT INTO users (username, email, password_hash, role, is_active, created_at, updated_at)
                    VALUES (?, ?, '!', 'user', 1, ?, ?)
                    """,
                    (username, email, now, now),
                )
                user_id = cursor.lastrowid
            # The IdP's groups are authoritative on every login.
            self._set_user_roles(conn, user_id, role_names)
            self._require_security_holder_remains(conn)
            user = row_to_dict(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
            token = self.create_session(conn, user_id)
        self.audit(user, "login.oidc", username, {"roles": role_names, "provisioned": row is None})
        return self.decorate_user(user), token

    # --- Query sharing (Phase 3) ---------------------------------------------

    def _user_role_ids(self, conn: sqlite3.Connection, user: dict[str, Any]) -> list[int]:
        return [role["id"] for role in self.user_role_rows(conn, user["id"])]

    def _shared_access(
        self, conn: sqlite3.Connection, entity_type: str, entity_id: int, user: dict[str, Any]
    ) -> str | None:
        """Highest access level the user's roles grant on an entity, or None."""
        role_ids = self._user_role_ids(conn, user)
        if not role_ids:
            return None
        marks = ",".join("?" * len(role_ids))
        rows = conn.execute(
            f"SELECT access FROM entity_shares WHERE entity_type = ? AND entity_id = ? AND role_id IN ({marks})",
            (entity_type, entity_id, *role_ids),
        ).fetchall()
        if not rows:
            return None
        held = {row["access"] for row in rows}
        for level in reversed(SHARE_ACCESS_LEVELS):
            if level in held:
                return level
        return None

    def _entity_owner_row(self, conn: sqlite3.Connection, entity_type: str, entity_id: int) -> sqlite3.Row:
        table = {"saved_query": "saved_queries", "notebook": "notebooks"}[entity_type]
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (entity_id,)).fetchone()
        if not row:
            raise ApiError(404, "Not found.")
        return row

    def list_entity_shares(self, entity_type: str, entity_id: int, user: dict[str, Any]) -> dict[str, Any]:
        if entity_type not in SHAREABLE_ENTITY_TYPES:
            raise ApiError(400, "This entity type cannot be shared.")
        with self.conn() as conn:
            row = self._entity_owner_row(conn, entity_type, entity_id)
            if row["user_id"] != user["id"] and self._shared_access(conn, entity_type, entity_id, user) is None:
                raise ApiError(404, "Not found.")
            shares = conn.execute(
                """
                SELECT entity_shares.*, roles.name AS role_name FROM entity_shares
                JOIN roles ON roles.id = entity_shares.role_id
                WHERE entity_type = ? AND entity_id = ?
                ORDER BY roles.name
                """,
                (entity_type, entity_id),
            ).fetchall()
        return {
            "shares": [
                {
                    "id": share["id"],
                    "role": share["role_name"],
                    "access": share["access"],
                    "created_at": share["created_at"],
                }
                for share in shares
            ]
        }

    def share_entity(
        self, entity_type: str, entity_id: int, payload: dict[str, Any], user: dict[str, Any]
    ) -> dict[str, Any]:
        if entity_type not in SHAREABLE_ENTITY_TYPES:
            raise ApiError(400, "This entity type cannot be shared.")
        access = str(payload.get("access", "view")).strip()
        if access not in SHARE_ACCESS_LEVELS:
            raise ApiError(400, f"access must be one of: {', '.join(SHARE_ACCESS_LEVELS)}.")
        role_name = str(payload.get("role", "")).strip().lower()
        now = utc_now()
        with self.conn() as conn:
            row = self._entity_owner_row(conn, entity_type, entity_id)
            if row["user_id"] != user["id"]:
                raise ApiError(403, "Only the owner can manage sharing.")
            role = conn.execute("SELECT id FROM roles WHERE name = ?", (role_name,)).fetchone()
            if not role:
                raise ApiError(400, f"Unknown role: {role_name}.")
            conn.execute(
                """
                INSERT INTO entity_shares (entity_type, entity_id, role_id, access, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id, role_id) DO UPDATE SET access = excluded.access
                """,
                (entity_type, entity_id, role["id"], access, user["id"], now),
            )
        return self.list_entity_shares(entity_type, entity_id, user)

    def unshare_entity(self, entity_type: str, entity_id: int, share_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            row = self._entity_owner_row(conn, entity_type, entity_id)
            if row["user_id"] != user["id"]:
                raise ApiError(403, "Only the owner can manage sharing.")
            conn.execute(
                "DELETE FROM entity_shares WHERE id = ? AND entity_type = ? AND entity_id = ?",
                (share_id, entity_type, entity_id),
            )
        return self.list_entity_shares(entity_type, entity_id, user)

    # --- Scheduled SQL jobs (Phase 3) ------------------------------------------

    def public_job(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "sql": row["sql_text"],
            "cluster_id": row["cluster_id"],
            "catalog": row["catalog"],
            "schema": row["schema_name"],
            "run_as_user_id": row["run_as_user_id"],
            "run_as_username": self._owner_username(row["run_as_user_id"]),
            "schedule_type": row["schedule_type"],
            "interval_minutes": row["interval_minutes"],
            "cron_expression": row["cron_expression"],
            "enabled": bool(row["enabled"]),
            "next_run_at": row["next_run_at"],
            "last_run_at": row["last_run_at"],
            "last_status": row["last_status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _job_for_user(self, conn: sqlite3.Connection, job_id: int, user: dict[str, Any]) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM scheduled_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise ApiError(404, "Job not found.")
        if row["created_by"] != user["id"] and not self.has_privilege(user, PRIVILEGE_MANAGE_CLUSTERS):
            raise ApiError(404, "Job not found.")
        return row

    def _normalize_job_schedule(self, payload: dict[str, Any], current: dict[str, Any] | None = None) -> dict[str, Any]:
        schedule_type = str(payload.get("schedule_type", (current or {}).get("schedule_type", "interval")))
        if schedule_type not in JOB_SCHEDULE_TYPES:
            raise ApiError(400, "schedule_type must be interval or cron.")
        interval_minutes = payload.get("interval_minutes", (current or {}).get("interval_minutes"))
        cron_expression = str(payload.get("cron_expression", (current or {}).get("cron_expression", "")) or "").strip()
        if schedule_type == "interval":
            try:
                interval_minutes = int(interval_minutes)
            except (TypeError, ValueError):
                raise ApiError(400, "interval_minutes is required for interval schedules.") from None
            if interval_minutes < JOB_MIN_INTERVAL_MINUTES or interval_minutes > JOB_MAX_INTERVAL_MINUTES:
                raise ApiError(
                    400,
                    f"interval_minutes must be between {JOB_MIN_INTERVAL_MINUTES} and {JOB_MAX_INTERVAL_MINUTES}.",
                )
            cron_expression = ""
        else:
            interval_minutes = None
            try:
                next_cron_run(cron_expression, datetime.now(timezone.utc))
            except ValueError as exc:
                raise ApiError(400, f"Invalid cron expression: {exc}.") from None
        return {
            "schedule_type": schedule_type,
            "interval_minutes": interval_minutes,
            "cron_expression": cron_expression,
        }

    def _job_next_run(self, schedule: dict[str, Any], reference: datetime | None = None) -> str:
        now = reference or datetime.now(timezone.utc)
        if schedule["schedule_type"] == "interval":
            target = now + timedelta(minutes=int(schedule["interval_minutes"]))
        else:
            target = next_cron_run(schedule["cron_expression"], now)
        return target.isoformat(timespec="seconds")

    def create_job(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip()
        if not name or len(name) > MAX_JOB_NAME_LENGTH:
            raise ApiError(400, f"Job name is required (max {MAX_JOB_NAME_LENGTH} characters).")
        sql_text = str(payload.get("sql", "")).strip()
        statements = split_sql_statements(sql_text)
        if len(statements) != 1:
            raise ApiError(400, "Jobs run exactly one SQL statement.")
        sql_text = statements[0]
        try:
            cluster_id = int(payload.get("cluster_id"))
        except (TypeError, ValueError):
            raise ApiError(400, "cluster_id is required.") from None
        catalog = str(payload.get("catalog") or "").strip()
        schema_name = str(payload.get("schema") or payload.get("schema_name") or "").strip()
        schedule = self._normalize_job_schedule(payload)
        run_as = str(payload.get("run_as") or "").strip()
        now = utc_now()
        with self.conn() as conn:
            cluster = conn.execute("SELECT id FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not cluster:
                raise ApiError(404, "Cluster not found.")
            if run_as and run_as != user["username"]:
                # Running as another identity (service account) is delegation.
                self.require_privilege(user, PRIVILEGE_MANAGE_USERS)
                run_row = conn.execute(
                    "SELECT * FROM users WHERE username = ? AND is_active = 1", (run_as,)
                ).fetchone()
                if not run_row:
                    raise ApiError(404, f"run_as user {run_as} not found or inactive.")
                run_as_user_id = run_row["id"]
            else:
                run_as_user_id = user["id"]
            cursor = conn.execute(
                """
                INSERT INTO scheduled_jobs
                  (name, sql_text, cluster_id, catalog, schema_name, run_as_user_id, created_by,
                   schedule_type, interval_minutes, cron_expression, enabled, next_run_at,
                   created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    name,
                    sql_text,
                    cluster_id,
                    catalog,
                    schema_name,
                    run_as_user_id,
                    user["id"],
                    schedule["schedule_type"],
                    schedule["interval_minutes"],
                    schedule["cron_expression"],
                    self._job_next_run(schedule),
                    now,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM scheduled_jobs WHERE id = ?", (cursor.lastrowid,)).fetchone()
        self.audit(user, "job.create", name, {"cluster_id": cluster_id, "run_as": self._owner_username(run_as_user_id)})
        return {"job": self.public_job(row)}

    def list_jobs(self, user: dict[str, Any]) -> dict[str, Any]:
        see_all = self.has_privilege(user, PRIVILEGE_MANAGE_CLUSTERS)
        where = "" if see_all else "WHERE created_by = ?"
        params = () if see_all else (user["id"],)
        with self.conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM scheduled_jobs {where} ORDER BY created_at DESC", params
            ).fetchall()
        return {"jobs": [self.public_job(row) for row in rows]}

    def update_job(self, job_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            row = self._job_for_user(conn, job_id, user)
            current = self.public_job(row)
            updates: dict[str, Any] = {}
            if "name" in payload:
                name = str(payload["name"]).strip()
                if not name or len(name) > MAX_JOB_NAME_LENGTH:
                    raise ApiError(400, "Invalid job name.")
                updates["name"] = name
            if "sql" in payload:
                statements = split_sql_statements(str(payload["sql"]).strip())
                if len(statements) != 1:
                    raise ApiError(400, "Jobs run exactly one SQL statement.")
                updates["sql_text"] = statements[0]
            if "catalog" in payload:
                updates["catalog"] = str(payload["catalog"] or "").strip()
            if "schema" in payload or "schema_name" in payload:
                updates["schema_name"] = str(payload.get("schema") or payload.get("schema_name") or "").strip()
            if "enabled" in payload:
                updates["enabled"] = 1 if bool(payload["enabled"]) else 0
            if any(key in payload for key in ("schedule_type", "interval_minutes", "cron_expression")):
                schedule = self._normalize_job_schedule(
                    payload,
                    {
                        "schedule_type": row["schedule_type"],
                        "interval_minutes": row["interval_minutes"],
                        "cron_expression": row["cron_expression"],
                    },
                )
                updates.update(
                    schedule_type=schedule["schedule_type"],
                    interval_minutes=schedule["interval_minutes"],
                    cron_expression=schedule["cron_expression"],
                    next_run_at=self._job_next_run(schedule),
                )
            elif updates.get("enabled") == 1 and not row["enabled"]:
                # Re-enabling reschedules from now rather than firing immediately.
                schedule = {
                    "schedule_type": row["schedule_type"],
                    "interval_minutes": row["interval_minutes"],
                    "cron_expression": row["cron_expression"],
                }
                updates["next_run_at"] = self._job_next_run(schedule)
            if not updates:
                return {"job": current, "changes": []}
            updates["updated_at"] = utc_now()
            assignments = ", ".join(f"{key} = ?" for key in updates)
            conn.execute(
                f"UPDATE scheduled_jobs SET {assignments} WHERE id = ?", (*updates.values(), job_id)
            )
            updated = conn.execute("SELECT * FROM scheduled_jobs WHERE id = ?", (job_id,)).fetchone()
        return {"job": self.public_job(updated), "changes": sorted(updates)}

    def delete_job(self, job_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            row = self._job_for_user(conn, job_id, user)
            conn.execute("DELETE FROM scheduled_jobs WHERE id = ?", (job_id,))
        self.audit(user, "job.delete", row["name"])
        return {"deleted": True}

    def list_job_runs(self, job_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            self._job_for_user(conn, job_id, user)
            rows = conn.execute(
                """
                SELECT r.*, q.status AS query_status, q.error_message AS query_error, q.elapsed_ms
                FROM scheduled_job_runs r
                LEFT JOIN query_runs q ON q.id = r.query_id
                WHERE r.job_id = ?
                ORDER BY r.id DESC LIMIT ?
                """,
                (job_id, MAX_JOB_RUNS_LISTED),
            ).fetchall()
        return {
            "runs": [
                {
                    "id": row["id"],
                    "query_id": row["query_id"],
                    "attempt": row["attempt"],
                    "status": row["status"],
                    "error": row["error"] or (row["query_error"] or ""),
                    "elapsed_ms": row["elapsed_ms"],
                    "started_at": row["started_at"],
                    "finished_at": row["finished_at"],
                }
                for row in rows
            ]
        }

    def run_job_now(self, job_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            row = self._job_for_user(conn, job_id, user)
        run_id = self._execute_job(row_to_dict(row), attempt=1)
        return {"run_id": run_id}

    def _execute_job(self, job: dict[str, Any], *, attempt: int) -> int:
        """Submit one execution of a job through the normal query path, as the
        job's run_as user (whose grants apply). Failures to even submit are
        recorded as failed runs rather than raised."""
        now = utc_now()
        with self.conn() as conn:
            run_as = conn.execute(
                "SELECT * FROM users WHERE id = ? AND is_active = 1", (job["run_as_user_id"],)
            ).fetchone()
        query_id = None
        status, error = "Running", ""
        if not run_as:
            status, error = "Failed", "The job's run-as user no longer exists or is inactive."
        else:
            try:
                result = self.create_query(
                    {
                        "cluster_id": job["cluster_id"],
                        "sql": job["sql_text"],
                        "catalog": job["catalog"],
                        "schema": job["schema_name"],
                        # Jobs exist to observe fresh data on a schedule; a job
                        # with an interval inside the cache TTL must never be
                        # served its own previous snapshot.
                        "fresh": True,
                    },
                    row_to_dict(run_as),
                )
                query_id = result["query"]["id"]
            except ApiError as exc:
                status, error = "Failed", exc.message
        with self.conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scheduled_job_runs (job_id, query_id, attempt, status, error, started_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (job["id"], query_id, attempt, status, error, now, now if status == "Failed" else None),
            )
            run_id = cursor.lastrowid
            conn.execute(
                "UPDATE scheduled_jobs SET last_run_at = ?, last_status = ? WHERE id = ?",
                (now, status, job["id"]),
            )
        if status == "Failed":
            # Submission failures never retry, so they are final.
            self.notify("job_failed", f"Scheduled job {job['name']} failed to submit: {error}", {"job": job["name"]})
        return run_id

    def poll_scheduled_jobs_once(self) -> list[dict[str, Any]]:
        """One scheduler tick: fire due jobs, then pump/finalize running runs."""
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat(timespec="seconds")
        fired: list[dict[str, Any]] = []
        with self.conn() as conn:
            due = [
                row_to_dict(row)
                for row in conn.execute(
                    "SELECT * FROM scheduled_jobs WHERE enabled = 1 AND next_run_at IS NOT NULL AND next_run_at <= ?",
                    (now,),
                ).fetchall()
            ]
        for job in due:
            schedule = {
                "schedule_type": job["schedule_type"],
                "interval_minutes": job["interval_minutes"],
                "cron_expression": job["cron_expression"],
            }
            with self.conn() as conn:
                conn.execute(
                    "UPDATE scheduled_jobs SET next_run_at = ? WHERE id = ?",
                    (self._job_next_run(schedule, now_dt), job["id"]),
                )
            run_id = self._execute_job(job, attempt=1)
            fired.append({"job_id": job["id"], "run_id": run_id})
        self._finalize_job_runs()
        return fired

    def _finalize_job_runs(self) -> None:
        """Advance in-flight job queries and settle their run records; a run
        whose query failed on attempt 1 is retried exactly once."""
        with self.conn() as conn:
            running = [
                row_to_dict(row)
                for row in conn.execute(
                    """
                    SELECT r.*, j.run_as_user_id FROM scheduled_job_runs r
                    JOIN scheduled_jobs j ON j.id = r.job_id
                    WHERE r.status = 'Running'
                    """
                ).fetchall()
            ]
        for run in running:
            if not run["query_id"]:
                continue
            with self.conn() as conn:
                run_as = conn.execute("SELECT * FROM users WHERE id = ?", (run["run_as_user_id"],)).fetchone()
            if not run_as:
                continue
            try:
                result = self.advance_query_run(run["query_id"], row_to_dict(run_as), max_pages=JOB_ADVANCE_MAX_PAGES)
                query = result["query"]
            except ApiError:
                continue
            if query["status"] not in TERMINAL_QUERY_STATUSES:
                continue
            finished = utc_now()
            status = "Succeeded" if query["status"] == "Finished" else "Failed"
            error = query.get("error_message") or ""
            with self.conn() as conn:
                conn.execute(
                    "UPDATE scheduled_job_runs SET status = ?, error = ?, finished_at = ? WHERE id = ?",
                    (status, error, finished, run["id"]),
                )
                conn.execute(
                    "UPDATE scheduled_jobs SET last_status = ? WHERE id = ?", (status, run["job_id"])
                )
                job_row = conn.execute("SELECT * FROM scheduled_jobs WHERE id = ?", (run["job_id"],)).fetchone()
            if status == "Failed" and run["attempt"] == 1 and job_row:
                self._execute_job(row_to_dict(job_row), attempt=2)
            elif status == "Failed" and job_row:
                # The retry failed too — this run is final.
                self.notify(
                    "job_failed",
                    f"Scheduled job {job_row['name']} failed after retry: {error}",
                    {"job": job_row["name"]},
                )

    # --- Metadata cache, autocomplete & global search (Phase 3) ---------------

    def _cache_tables(
        self, cluster_id: int, catalog: str, schema_name: str, tables: list[dict[str, Any]]
    ) -> None:
        now = utc_now()
        with self.conn() as conn:
            for table in tables:
                conn.execute(
                    """
                    INSERT INTO metadata_cache (cluster_id, catalog, schema_name, table_name, table_type, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(cluster_id, catalog, schema_name, table_name)
                    DO UPDATE SET table_type = excluded.table_type, updated_at = excluded.updated_at
                    """,
                    (cluster_id, catalog, schema_name, table["name"], table.get("type", "TABLE"), now),
                )

    def _cache_columns(
        self, cluster_id: int, catalog: str, schema_name: str, table: str, columns: list[dict[str, Any]]
    ) -> None:
        now = utc_now()
        with self.conn() as conn:
            conn.execute(
                """
                INSERT INTO metadata_cache (cluster_id, catalog, schema_name, table_name, columns_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(cluster_id, catalog, schema_name, table_name)
                DO UPDATE SET columns_json = excluded.columns_json, updated_at = excluded.updated_at
                """,
                (cluster_id, catalog, schema_name, table, dumps(columns), now),
            )

    def _cached_metadata(
        self, cluster_id: int, catalog: str, schema_name: str, table: str, result: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Serve the schema browser from the metadata cache when the cluster
        can't answer live. Returns None when nothing useful is cached."""
        with self.conn() as conn:
            if not schema_name:
                rows = conn.execute(
                    "SELECT DISTINCT schema_name FROM metadata_cache WHERE cluster_id = ? AND catalog = ? ORDER BY schema_name",
                    (cluster_id, catalog),
                ).fetchall()
                if not rows:
                    return None
                result["schemas"] = [{"name": row["schema_name"]} for row in rows]
            elif not table:
                rows = conn.execute(
                    """
                    SELECT table_name, table_type FROM metadata_cache
                    WHERE cluster_id = ? AND catalog = ? AND schema_name = ? ORDER BY table_name
                    """,
                    (cluster_id, catalog, schema_name),
                ).fetchall()
                if not rows:
                    return None
                result["tables"] = [{"name": row["table_name"], "type": row["table_type"]} for row in rows]
            else:
                row = conn.execute(
                    """
                    SELECT columns_json FROM metadata_cache
                    WHERE cluster_id = ? AND catalog = ? AND schema_name = ? AND table_name = ?
                    """,
                    (cluster_id, catalog, schema_name, table),
                ).fetchone()
                columns = loads(row["columns_json"], []) if row else []
                if not columns:
                    return None
                result["columns"] = columns
        result["cached"] = True
        return result

    def autocomplete_metadata(self, cluster_id: int, user: dict[str, Any]) -> dict[str, Any]:
        """Editor autocomplete feed: every cached table (+columns) on catalogs
        the user may use, cheap enough to ship to the browser wholesale."""
        self.require_cluster_access(user, cluster_id)
        with self.conn() as conn:
            rows = conn.execute(
                """
                SELECT catalog, schema_name, table_name, columns_json FROM metadata_cache
                WHERE cluster_id = ? ORDER BY catalog, schema_name, table_name LIMIT ?
                """,
                (cluster_id, AUTOCOMPLETE_TABLE_LIMIT),
            ).fetchall()
        tables = [
            {
                "catalog": row["catalog"],
                "schema": row["schema_name"],
                "table": row["table_name"],
                "columns": [column.get("name") for column in loads(row["columns_json"], [])],
            }
            for row in rows
            if self.user_can_use_catalog(user, row["catalog"])
        ]
        return {"tables": tables}

    def global_search(self, query_text: str, user: dict[str, Any]) -> dict[str, Any]:
        """Cmd+K search across clusters, catalogs, saved queries, notebooks,
        and cached table metadata — filtered by the caller's grants."""
        needle = str(query_text or "").strip().lower()
        if len(needle) < 2:
            return {"results": []}
        like = f"%{needle}%"
        results: list[dict[str, Any]] = []
        with self.conn() as conn:
            for row in conn.execute(
                "SELECT * FROM clusters WHERE lower(name) LIKE ? ORDER BY name LIMIT ?", (like, SEARCH_RESULT_LIMIT)
            ).fetchall():
                if self.user_can_use_cluster(user, row["id"]):
                    results.append(
                        {"type": "cluster", "id": row["id"], "title": row["name"], "subtitle": f"Cluster · {row['status']}", "view": "clusters"}
                    )
            for row in conn.execute(
                "SELECT * FROM catalogs WHERE lower(name) LIKE ? ORDER BY name LIMIT ?", (like, SEARCH_RESULT_LIMIT)
            ).fetchall():
                if self.user_can_use_catalog(user, row["name"]):
                    results.append(
                        {"type": "catalog", "id": row["id"], "title": row["name"], "subtitle": f"Catalog · {row['type']}", "view": "catalogs"}
                    )
            role_ids = self._user_role_ids(conn, user)
            marks = ",".join("?" * len(role_ids)) if role_ids else "NULL"
            for row in conn.execute(
                f"""
                SELECT DISTINCT sq.* FROM saved_queries sq
                LEFT JOIN entity_shares es
                  ON es.entity_type = 'saved_query' AND es.entity_id = sq.id AND es.role_id IN ({marks})
                WHERE (sq.user_id = ? OR es.id IS NOT NULL)
                  AND (lower(sq.name) LIKE ? OR lower(sq.sql_text) LIKE ?)
                ORDER BY sq.updated_at DESC LIMIT ?
                """,
                (*role_ids, user["id"], like, like, SEARCH_RESULT_LIMIT),
            ).fetchall():
                results.append(
                    {"type": "saved_query", "id": row["id"], "title": row["name"], "subtitle": "Saved query", "view": "sql"}
                )
            for row in conn.execute(
                f"""
                SELECT DISTINCT n.* FROM notebooks n
                LEFT JOIN entity_shares es
                  ON es.entity_type = 'notebook' AND es.entity_id = n.id AND es.role_id IN ({marks})
                WHERE (n.user_id = ? OR es.id IS NOT NULL) AND lower(n.name) LIKE ?
                ORDER BY n.updated_at DESC LIMIT ?
                """,
                (*role_ids, user["id"], like, SEARCH_RESULT_LIMIT),
            ).fetchall():
                results.append(
                    {"type": "notebook", "id": row["id"], "title": row["name"], "subtitle": "Notebook", "view": "notebooks"}
                )
            for row in conn.execute(
                """
                SELECT m.*, c.name AS cluster_name FROM metadata_cache m
                JOIN clusters c ON c.id = m.cluster_id
                WHERE lower(m.table_name) LIKE ? OR lower(m.schema_name) LIKE ?
                ORDER BY m.catalog, m.schema_name, m.table_name LIMIT ?
                """,
                (like, like, SEARCH_RESULT_LIMIT),
            ).fetchall():
                if self.user_can_use_cluster(user, row["cluster_id"]) and self.user_can_use_catalog(user, row["catalog"]):
                    results.append(
                        {
                            "type": "table",
                            "id": row["id"],
                            "title": f"{row['catalog']}.{row['schema_name']}.{row['table_name']}",
                            "subtitle": f"Table · {row['cluster_name']}",
                            "view": "sql",
                            "cluster_id": row["cluster_id"],
                        }
                    )
        return {"results": results[: SEARCH_RESULT_LIMIT * 2]}

    # --- Observability & ops (Phase 5) -------------------------------------------

    def normalize_uptime_schedule(self, raw: Any) -> list[dict[str, Any]]:
        """Keep-warm windows: [{"days": [0-6 Mon-Sun], "start": "HH:MM",
        "end": "HH:MM"}, ...] (UTC). Also accepts human strings like
        "mon-fri 08:00-18:00" or "sat,sun 10:00-16:00"."""
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise ApiError(400, "uptime_schedule must be a list of windows.")
        windows: list[dict[str, Any]] = []
        for entry in raw:
            if isinstance(entry, str):
                entry = self._parse_uptime_window_text(entry)
                if entry is None:
                    continue
            if not isinstance(entry, dict):
                raise ApiError(400, "Each uptime window is an object or a string like 'mon-fri 08:00-18:00'.")
            days = entry.get("days")
            if not isinstance(days, list) or not days:
                raise ApiError(400, "Each uptime window needs a non-empty days list (0=Mon .. 6=Sun).")
            try:
                days = sorted({int(day) for day in days})
            except (TypeError, ValueError):
                raise ApiError(400, "Uptime window days must be integers 0-6.") from None
            if any(day < 0 or day > 6 for day in days):
                raise ApiError(400, "Uptime window days must be integers 0-6.")
            start = str(entry.get("start", "")).strip()
            end = str(entry.get("end", "")).strip()
            if not UPTIME_WINDOW_PATTERN.fullmatch(f"{start}-{end}") or start >= end:
                raise ApiError(400, "Uptime windows need start < end as HH:MM (UTC), e.g. 08:00-18:00.")
            windows.append({"days": days, "start": start, "end": end})
        return windows

    @staticmethod
    def _parse_uptime_window_text(text: str) -> dict[str, Any] | None:
        """'mon-fri 08:00-18:00' / 'sat,sun 10:00-16:00' → a window dict."""
        cleaned = text.strip().lower()
        if not cleaned:
            return None
        parts = cleaned.split()
        if len(parts) != 2:
            raise ApiError(400, f"Uptime windows look like 'mon-fri 08:00-18:00' — check: {text}.")
        day_part, time_part = parts
        days: set[int] = set()
        for chunk in day_part.split(","):
            if "-" in chunk:
                start_name, end_name = chunk.split("-", 1)
                try:
                    start_index = UPTIME_DAY_NAMES.index(start_name)
                    end_index = UPTIME_DAY_NAMES.index(end_name)
                except ValueError:
                    raise ApiError(400, f"Unknown day in uptime window: {chunk}.") from None
                if start_index > end_index:
                    raise ApiError(400, f"Day ranges run Mon→Sun: {chunk}.")
                days.update(range(start_index, end_index + 1))
            else:
                try:
                    days.add(UPTIME_DAY_NAMES.index(chunk))
                except ValueError:
                    raise ApiError(400, f"Unknown day in uptime window: {chunk}.") from None
        match = UPTIME_WINDOW_PATTERN.fullmatch(time_part)
        if not match:
            raise ApiError(400, f"Uptime window times look like 08:00-18:00 — check: {text}.")
        start = f"{match.group(1)}:{match.group(2)}"
        end = f"{match.group(3)}:{match.group(4)}"
        return {"days": sorted(days), "start": start, "end": end}

    def in_uptime_window(self, cluster: dict[str, Any], now: datetime | None = None) -> bool:
        windows = cluster.get("uptime_schedule") or []
        if not windows:
            return False
        moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        day = moment.weekday()  # Monday=0, matching the stored day indexes
        clock = moment.strftime("%H:%M")
        return any(
            day in window.get("days", []) and window.get("start", "") <= clock < window.get("end", "")
            for window in windows
        )

    # -- utilization samples --

    def sample_cluster_stats_once(self) -> int:
        """One poller tick of utilization sampling for every Running cluster;
        also prunes samples past the retention window. Returns samples written."""
        now = utc_now()
        written = 0
        with self.conn() as conn:
            clusters = [
                self.public_cluster(row)
                for row in conn.execute("SELECT * FROM clusters WHERE status = 'Running'").fetchall()
            ]
        for cluster in clusters:
            with self.conn() as conn:
                coordinator = conn.execute(
                    """
                    SELECT * FROM provider_resources
                    WHERE cluster_id = ? AND resource_type = 'coordinator_instance'
                    ORDER BY id DESC LIMIT 1
                    """,
                    (cluster["id"],),
                ).fetchone()
                asg_row = conn.execute(
                    """
                    SELECT * FROM provider_resources
                    WHERE cluster_id = ? AND resource_type = 'auto_scaling_group'
                    ORDER BY id DESC LIMIT 1
                    """,
                    (cluster["id"],),
                ).fetchone()
            if not coordinator:
                continue
            endpoint = self.coordinator_endpoint(row_to_dict(coordinator))
            try:
                stats = self.aws.trino_cluster_stats(coordinator_endpoint=endpoint)
            except Exception:
                continue
            if not stats.get("ok"):
                continue
            desired = None
            cpu = None
            if asg_row:
                try:
                    asg = self.aws.worker_auto_scaling_group(
                        region=cluster["region"], name=asg_row["resource_id"]
                    )
                    if asg.get("found"):
                        desired = int(asg["desired_capacity"])
                        cpu = self.aws.worker_cpu_average(
                            region=cluster["region"], instance_ids=asg.get("instance_ids", [])
                        )
                except Exception:
                    pass
            cache_hit_rate = (
                self._sample_cache_hit_rate(endpoint) if cluster.get("accelerated") else None
            )
            with self.conn() as conn:
                conn.execute(
                    """
                    INSERT INTO cluster_stats_samples
                      (cluster_id, sampled_at, running_queries, queued_queries, active_workers,
                       desired_capacity, avg_worker_cpu, cache_hit_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cluster["id"],
                        now,
                        int(stats.get("running_queries") or 0),
                        int(stats.get("queued_queries") or 0),
                        int(stats.get("active_workers") or 0),
                        desired,
                        cpu,
                        cache_hit_rate,
                    ),
                )
            written += 1
        cutoff = (datetime.now(timezone.utc) - timedelta(days=STATS_RETENTION_DAYS)).isoformat(timespec="seconds")
        with self.conn() as conn:
            conn.execute("DELETE FROM cluster_stats_samples WHERE sampled_at < ?", (cutoff,))
        return written

    def _sample_cache_hit_rate(self, coordinator_endpoint: str) -> float | None:
        """Best-effort Alluxio file-system-cache hit rate from the built-in jmx
        catalog (attached automatically to accelerated clusters). Column names
        vary across Trino versions, so hits/misses are matched by name."""
        try:
            columns, rows = self._run_trino_query_with_columns(
                coordinator_endpoint,
                'SELECT * FROM jmx.current."io.trino.filesystem.alluxio:*"',
            )
        except Exception:
            return None
        hits = misses = 0.0
        found = False
        for index, column in enumerate(columns):
            name = str(column).lower()
            is_hit = "hit" in name and "count" in name
            is_miss = "miss" in name and "count" in name
            if not (is_hit or is_miss):
                continue
            for row in rows:
                try:
                    value = float(row[index] or 0)
                except (TypeError, ValueError, IndexError):
                    continue
                if is_hit:
                    hits += value
                else:
                    misses += value
                found = True
        if not found or hits + misses <= 0:
            return None
        return round(hits / (hits + misses), 4)

    def _run_trino_query_with_columns(
        self, coordinator_endpoint: str, sql_text: str
    ) -> tuple[list[str], list[list[Any]]]:
        """Like run_trino_metadata_query but keeps column names."""
        response = self.submit_trino_query(
            coordinator_endpoint=coordinator_endpoint,
            sql_text=sql_text,
            username="trinohub-metrics",
            catalog="",
            schema_name="",
        )
        columns: list[str] = []
        rows: list[list[Any]] = []
        pages = 0
        while True:
            error = response.get("error") or {}
            if error:
                raise ApiError(502, f"Trino metrics query failed: {error.get('message') or 'unknown error'}")
            if response.get("columns") and not columns:
                columns = [str(column.get("name", "")) for column in response["columns"]]
            rows.extend(response.get("data") or [])
            next_uri = response.get("nextUri")
            if not next_uri or pages >= MAX_METADATA_PAGES:
                break
            pages += 1
            response = self.fetch_trino_next(next_uri)
        return columns, rows

    def cluster_stats(self, cluster_id: int, *, hours: int = 24, user: dict[str, Any] | None = None) -> dict[str, Any]:
        if user is not None:
            self.require_cluster_access(user, cluster_id)
        hours = min(max(int(hours or 24), 1), STATS_RETENTION_DAYS * 24)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="seconds")
        with self.conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM cluster_stats_samples
                WHERE cluster_id = ? AND sampled_at >= ?
                ORDER BY sampled_at
                """,
                (cluster_id, cutoff),
            ).fetchall()
        samples = [
            {
                "sampled_at": row["sampled_at"],
                "running_queries": row["running_queries"],
                "queued_queries": row["queued_queries"],
                "active_workers": row["active_workers"],
                "desired_capacity": row["desired_capacity"],
                "avg_worker_cpu": row["avg_worker_cpu"],
                "cache_hit_rate": row["cache_hit_rate"],
            }
            for row in rows
        ]
        # Downsample evenly so charts stay light no matter the window.
        if len(samples) > STATS_MAX_POINTS:
            step = len(samples) / STATS_MAX_POINTS
            samples = [samples[int(index * step)] for index in range(STATS_MAX_POINTS)]
        return {"cluster_id": cluster_id, "hours": hours, "samples": samples}

    # -- Prometheus metrics --

    def prometheus_metrics(self) -> str:
        """Control-plane metrics in Prometheus text exposition format. Scrape
        with an API token: Authorization: Bearer tht_...  Gauges come from the
        latest utilization sample per cluster; counters from the event tables."""
        lines: list[str] = []

        def metric(name: str, help_text: str, metric_type: str, values: list[tuple[str, Any]]) -> None:
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} {metric_type}")
            for labels, value in values:
                lines.append(f"{name}{labels} {value}")

        with self.conn() as conn:
            clusters = [self.public_cluster(row) for row in conn.execute("SELECT * FROM clusters").fetchall()]
            status_values = [
                (f'{{cluster="{c["name"]}",status="{c["status"]}"}}', 1) for c in clusters
            ]
            latest: dict[int, sqlite3.Row] = {}
            for row in conn.execute(
                """
                SELECT s.* FROM cluster_stats_samples s
                JOIN (SELECT cluster_id, MAX(id) AS max_id FROM cluster_stats_samples GROUP BY cluster_id) m
                  ON m.max_id = s.id
                """
            ).fetchall():
                latest[row["cluster_id"]] = row
            query_counts = conn.execute(
                "SELECT status, COUNT(*) AS n FROM query_runs GROUP BY status"
            ).fetchall()
            scaling_counts = conn.execute(
                "SELECT direction, COUNT(*) AS n FROM scaling_events GROUP BY direction"
            ).fetchall()
            job_counts = conn.execute(
                "SELECT status, COUNT(*) AS n FROM scheduled_job_runs GROUP BY status"
            ).fetchall()

        metric("trinohub_cluster_status", "Cluster lifecycle state (1 per cluster).", "gauge", status_values)
        names = {c["id"]: c["name"] for c in clusters}
        for field, help_text in (
            ("active_workers", "Trino workers active in the cluster."),
            ("running_queries", "Queries currently running."),
            ("queued_queries", "Queries currently queued."),
            ("avg_worker_cpu", "Average worker CPU percent (CloudWatch)."),
            ("cache_hit_rate", "File-system cache hit rate (accelerated clusters)."),
        ):
            values = [
                (f'{{cluster="{names[cid]}"}}', row[field])
                for cid, row in latest.items()
                if cid in names and row[field] is not None
            ]
            if values:
                metric(f"trinohub_cluster_{field}", help_text, "gauge", values)
        metric(
            "trinohub_queries_total",
            "Queries submitted through the control plane, by final status.",
            "counter",
            [(f'{{status="{row["status"]}"}}', row["n"]) for row in query_counts],
        )
        metric(
            "trinohub_scaling_events_total",
            "Autoscaler actions taken, by direction.",
            "counter",
            [(f'{{direction="{row["direction"]}"}}', row["n"]) for row in scaling_counts],
        )
        metric(
            "trinohub_job_runs_total",
            "Scheduled-job runs, by status.",
            "counter",
            [(f'{{status="{row["status"]}"}}', row["n"]) for row in job_counts],
        )
        return "\n".join(lines) + "\n"

    # -- notifications --

    def notification_settings(self) -> dict[str, Any]:
        setup = self.setup_row()
        config = loads(setup.get("notification_config_json", "{}"), {}) if setup else {}
        return {
            "webhook_url": config.get("webhook_url", ""),
            "events": [event for event in config.get("events", []) if event in NOTIFICATION_EVENTS],
        }

    def set_notification_settings(self, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        setup = self.setup_row()
        if not setup:
            raise ApiError(409, "Complete setup before configuring notifications.")
        current = self.notification_settings()
        webhook_url = str(payload.get("webhook_url", current["webhook_url"])).strip()
        if webhook_url and not webhook_url.startswith(("https://", "http://")):
            raise ApiError(400, "webhook_url must be an http(s) URL.")
        events = payload.get("events", current["events"])
        if not isinstance(events, list):
            raise ApiError(400, "events must be a list.")
        unknown = {str(event) for event in events} - set(NOTIFICATION_EVENTS)
        if unknown:
            raise ApiError(400, f"Unknown events: {', '.join(sorted(unknown))}. Valid: {', '.join(NOTIFICATION_EVENTS)}.")
        config = {"webhook_url": webhook_url, "events": [str(event) for event in events]}
        with self.conn() as conn:
            conn.execute("UPDATE setup_settings SET notification_config_json = ? WHERE id = 1", (dumps(config),))
        self.audit(actor, "settings.notifications", webhook_url and "webhook", {"events": config["events"]})
        return {"notifications": self.notification_settings()}

    def ask_trino_settings(self) -> dict[str, Any]:
        """Ask Trino model config. The operator pastes an OpenRouter model id in
        the Settings view; it overrides ASK_TRINO_MODEL / the built-in default.
        The API key lives only in the server environment and is never returned."""
        setup = self.setup_row()
        config = loads(setup.get("ask_trino_config_json", "{}"), {}) if setup else {}
        stored_model = str(config.get("model") or "").strip()
        env_model = os.environ.get("ASK_TRINO_MODEL", "").strip()
        api_key = os.environ.get("ASK_TRINO_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
        return {
            "model": stored_model,
            "effective_model": stored_model or env_model or ASK_TRINO_DEFAULT_MODEL,
            "default_model": ASK_TRINO_DEFAULT_MODEL,
            "key_configured": bool(api_key),
        }

    def set_ask_trino_settings(self, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        setup = self.setup_row()
        if not setup:
            raise ApiError(409, "Complete setup before configuring Ask Trino.")
        model = str(payload.get("model", "")).strip()
        if len(model) > 200:
            raise ApiError(400, "model must be 200 characters or fewer.")
        # OpenRouter model ids look like "vendor/model" (optionally ":variant").
        # A blank value clears the override and falls back to the env/default.
        if model and not re.fullmatch(r"[A-Za-z0-9._:/\-]+", model):
            raise ApiError(400, "model may only contain letters, numbers, and . _ : / - characters.")
        config = {"model": model}
        with self.conn() as conn:
            conn.execute("UPDATE setup_settings SET ask_trino_config_json = ? WHERE id = 1", (dumps(config),))
        self.audit(actor, "settings.ask_trino", model or "(default)")
        return {"ask_trino": self.ask_trino_settings()}

    def notify(self, event: str, title: str, detail: dict[str, Any] | None = None) -> None:
        """Fire-and-forget webhook notification (Slack-compatible ``text``
        field plus structured detail). Never blocks or raises: observability
        must not take down lifecycle paths."""
        config = self.notification_settings()
        if not config["webhook_url"] or event not in config["events"]:
            return
        body = json.dumps(
            {"text": f"[TrinoHub] {title}", "event": event, "detail": detail or {}},
            separators=(",", ":"),
        ).encode("utf-8")

        def send() -> None:
            try:
                request = urllib.request.Request(
                    config["webhook_url"], data=body, headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(request, timeout=NOTIFY_TIMEOUT_SECONDS).close()
            except Exception as exc:
                print(f"Notification webhook failed: {type(exc).__name__}: {exc}")

        threading.Thread(target=send, name="trinohub-notify", daemon=True).start()

    # -- cost visibility --

    def monthly_costs(self) -> dict[str, Any]:
        """Approximate spend per cluster over the last 30 days, reconstructed
        from status-transition events: running periods × (1 coordinator +
        min_workers) × the on-demand rate. Visibility, not billing."""
        window_start = datetime.now(timezone.utc) - timedelta(days=COST_WINDOW_DAYS)
        now = datetime.now(timezone.utc)
        results = []
        total = 0.0
        with self.conn() as conn:
            clusters = [self.public_cluster(row) for row in conn.execute("SELECT * FROM clusters").fetchall()]
            for cluster in clusters:
                events = conn.execute(
                    """
                    SELECT event_type, created_at FROM cluster_events
                    WHERE cluster_id = ? ORDER BY created_at, id
                    """,
                    (cluster["id"],),
                ).fetchall()
                running_since: datetime | None = None
                running_seconds = 0.0
                for event in events:
                    try:
                        moment = datetime.fromisoformat(event["created_at"])
                    except ValueError:
                        continue
                    if event["event_type"] == "running":
                        if running_since is None:
                            running_since = moment
                    elif event["event_type"] in {"suspended", "suspending", "not_enabled", "failed", "deleting", "disabled"}:
                        if running_since is not None:
                            start = max(running_since, window_start)
                            if moment > start:
                                running_seconds += (moment - start).total_seconds()
                            running_since = None
                if running_since is not None:
                    start = max(running_since, window_start)
                    if now > start:
                        running_seconds += (now - start).total_seconds()
                instance_type = cluster["instance_type"] or ""
                rate = INSTANCE_HOURLY_USD.get(instance_type, DEFAULT_INSTANCE_HOURLY_USD)
                nodes = 1 + int(cluster["min_workers"] or 1)
                hours = running_seconds / 3600
                cost = hours * rate * nodes
                total += cost
                results.append(
                    {
                        "cluster_id": cluster["id"],
                        "name": cluster["name"],
                        "status": cluster["status"],
                        "instance_type": instance_type,
                        "hourly_usd_per_node": rate,
                        "nodes_estimate": nodes,
                        "running_hours_30d": round(hours, 1),
                        "cost_30d_usd": round(cost, 2),
                    }
                )
        results.sort(key=lambda item: item["cost_30d_usd"], reverse=True)
        return {"window_days": COST_WINDOW_DAYS, "clusters": results, "total_30d_usd": round(total, 2)}

    # --- Fine-grained data security (Phase 6) ------------------------------------
    # Per-role table/column/row policies rendered into Trino's file-based
    # system access control at node bootstrap. Control-plane checks (Phase 1
    # grants) gate the API; these rules gate the engine itself, so they also
    # cover native wire-protocol clients.

    def public_data_policy(self, conn: sqlite3.Connection, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        role = conn.execute("SELECT name FROM roles WHERE id = ?", (row["role_id"],)).fetchone()
        return {
            "id": row["id"],
            "role_id": row["role_id"],
            "role": role["name"] if role else "",
            "catalog": row["catalog"],
            "schema": row["schema_name"],
            "table": row["table_name"],
            "privileges": loads(row["privileges_json"], []),
            "allowed_columns": loads(row["allowed_columns_json"], []),
            "denied_columns": loads(row["denied_columns_json"], []),
            "row_filter": row["row_filter"],
            "column_masks": loads(row["column_masks_json"], {}),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _normalize_columns(self, raw: Any, label: str) -> list[str]:
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise ApiError(400, f"{label} must be a list of column names.")
        columns = []
        for value in raw:
            name = str(value).strip()
            if not name:
                continue
            if not COLUMN_NAME_PATTERN.fullmatch(name):
                raise ApiError(400, f"Invalid column name in {label}: {name}.")
            if name not in columns:
                columns.append(name)
        return columns

    def list_data_policies(self) -> dict[str, Any]:
        with self.conn() as conn:
            rows = conn.execute(
                "SELECT * FROM data_policies ORDER BY catalog, schema_name, table_name, id"
            ).fetchall()
            return {"policies": [self.public_data_policy(conn, row) for row in rows]}

    def create_data_policy(self, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        role_name = str(payload.get("role", "")).strip().lower()
        catalog = str(payload.get("catalog", "")).strip()
        if not CATALOG_NAME_PATTERN.fullmatch(catalog):
            raise ApiError(400, "catalog is required (lowercase name).")
        schema_name = str(payload.get("schema") or payload.get("schema_name") or "").strip()
        table_name = str(payload.get("table") or payload.get("table_name") or "").strip()
        if table_name and not schema_name:
            raise ApiError(400, "schema is required when table is set.")
        privileges_raw = payload.get("privileges") or ["SELECT"]
        if not isinstance(privileges_raw, list):
            raise ApiError(400, "privileges must be a list.")
        privileges = [str(p).upper() for p in privileges_raw]
        unknown = set(privileges) - set(DATA_POLICY_PRIVILEGES)
        if unknown:
            raise ApiError(400, f"Unknown privileges: {', '.join(sorted(unknown))}. Valid: {', '.join(DATA_POLICY_PRIVILEGES)}.")
        allowed_columns = self._normalize_columns(payload.get("allowed_columns"), "allowed_columns")
        denied_columns = self._normalize_columns(payload.get("denied_columns"), "denied_columns")
        row_filter = str(payload.get("row_filter") or "").strip()
        masks_raw = payload.get("column_masks") or {}
        if not isinstance(masks_raw, dict):
            raise ApiError(400, "column_masks must be an object of {column: SQL expression}.")
        column_masks = {}
        for column, expression in masks_raw.items():
            if not COLUMN_NAME_PATTERN.fullmatch(str(column)):
                raise ApiError(400, f"Invalid masked column name: {column}.")
            column_masks[str(column)] = str(expression).strip() or "NULL"
        now = utc_now()
        with self.conn() as conn:
            role = conn.execute("SELECT id FROM roles WHERE name = ?", (role_name,)).fetchone()
            if not role:
                raise ApiError(400, f"Unknown role: {role_name}.")
            cursor = conn.execute(
                """
                INSERT INTO data_policies
                  (role_id, catalog, schema_name, table_name, privileges_json,
                   allowed_columns_json, denied_columns_json, row_filter, column_masks_json,
                   created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    role["id"],
                    catalog,
                    schema_name,
                    table_name,
                    dumps(privileges),
                    dumps(allowed_columns),
                    dumps(denied_columns),
                    row_filter,
                    dumps(column_masks),
                    now,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM data_policies WHERE id = ?", (cursor.lastrowid,)).fetchone()
            result = {"policy": self.public_data_policy(conn, row)}
        self.audit(actor, "policy.create", f"{role_name}:{catalog}.{schema_name or '*'}.{table_name or '*'}")
        return result

    def delete_data_policy(self, policy_id: int, actor: dict[str, Any] | None = None) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM data_policies WHERE id = ?", (policy_id,)).fetchone()
            if not row:
                raise ApiError(404, "Policy not found.")
            policy = self.public_data_policy(conn, row)
            conn.execute("DELETE FROM data_policies WHERE id = ?", (policy_id,))
        self.audit(actor, "policy.delete", f"{policy['role']}:{policy['catalog']}.{policy['schema'] or '*'}.{policy['table'] or '*'}")
        return {"deleted": True}

    # -- tags & ABAC --

    def list_entity_tags(self) -> dict[str, Any]:
        with self.conn() as conn:
            rows = conn.execute("SELECT * FROM entity_tags ORDER BY entity, tag").fetchall()
        return {"tags": [dict(row_to_dict(row)) for row in rows]}

    def create_entity_tag(self, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        entity = str(payload.get("entity", "")).strip()
        tag = str(payload.get("tag", "")).strip().lower()
        if not ENTITY_PATH_PATTERN.fullmatch(entity):
            raise ApiError(400, "entity must be catalog.schema.table or catalog.schema.table.column.")
        if not TAG_NAME_PATTERN.fullmatch(tag):
            raise ApiError(400, "tags are lowercase letters, digits, hyphens, underscores.")
        now = utc_now()
        with self.conn() as conn:
            conn.execute(
                """
                INSERT INTO entity_tags (entity, tag, status, source, created_at)
                VALUES (?, ?, 'accepted', 'manual', ?)
                ON CONFLICT(entity, tag) DO UPDATE SET status = 'accepted'
                """,
                (entity, tag, now),
            )
        self.audit(actor, "tag.create", f"{entity}#{tag}")
        return self.list_entity_tags()

    def resolve_entity_tag(self, tag_id: int, accept: bool, actor: dict[str, Any] | None = None) -> dict[str, Any]:
        """Accept or reject a (classifier-proposed) tag."""
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM entity_tags WHERE id = ?", (tag_id,)).fetchone()
            if not row:
                raise ApiError(404, "Tag not found.")
            if accept:
                conn.execute("UPDATE entity_tags SET status = 'accepted' WHERE id = ?", (tag_id,))
            else:
                conn.execute("DELETE FROM entity_tags WHERE id = ?", (tag_id,))
        self.audit(actor, "tag.accept" if accept else "tag.reject", f"{row['entity']}#{row['tag']}")
        return self.list_entity_tags()

    def list_tag_policies(self) -> dict[str, Any]:
        with self.conn() as conn:
            rows = conn.execute(
                """
                SELECT tag_policies.*, roles.name AS role_name FROM tag_policies
                JOIN roles ON roles.id = tag_policies.role_id
                ORDER BY tag, role_name
                """
            ).fetchall()
        return {
            "policies": [
                {"id": row["id"], "tag": row["tag"], "role": row["role_name"], "effect": row["effect"]}
                for row in rows
            ]
        }

    def create_tag_policy(self, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        tag = str(payload.get("tag", "")).strip().lower()
        role_name = str(payload.get("role", "")).strip().lower()
        effect = str(payload.get("effect", "deny")).strip()
        if not TAG_NAME_PATTERN.fullmatch(tag):
            raise ApiError(400, "Invalid tag name.")
        if effect not in TAG_POLICY_EFFECTS:
            raise ApiError(400, f"effect must be one of: {', '.join(TAG_POLICY_EFFECTS)}.")
        now = utc_now()
        with self.conn() as conn:
            role = conn.execute("SELECT id FROM roles WHERE name = ?", (role_name,)).fetchone()
            if not role:
                raise ApiError(400, f"Unknown role: {role_name}.")
            conn.execute(
                """
                INSERT OR IGNORE INTO tag_policies (tag, role_id, effect, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (tag, role["id"], effect, now),
            )
        self.audit(actor, "tag_policy.create", f"{tag}->{role_name}:{effect}")
        return self.list_tag_policies()

    def delete_tag_policy(self, policy_id: int, actor: dict[str, Any] | None = None) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM tag_policies WHERE id = ?", (policy_id,)).fetchone()
            if not row:
                raise ApiError(404, "Tag policy not found.")
            conn.execute("DELETE FROM tag_policies WHERE id = ?", (policy_id,))
        self.audit(actor, "tag_policy.delete", row["tag"])
        return self.list_tag_policies()

    def run_pii_classifier(self, actor: dict[str, Any] | None = None) -> dict[str, Any]:
        """Scan cached column metadata for PII-shaped column names and propose
        tags (status='proposed'). Admins accept or reject them in the UI."""
        proposed = 0
        with self.conn() as conn:
            rows = conn.execute("SELECT catalog, schema_name, table_name, columns_json FROM metadata_cache").fetchall()
            now = utc_now()
            for row in rows:
                for column in loads(row["columns_json"], []):
                    name = str(column.get("name", ""))
                    lowered = name.lower()
                    for tag, pattern in PII_COLUMN_PATTERNS:
                        if re.search(pattern, lowered):
                            entity = f"{row['catalog']}.{row['schema_name']}.{row['table_name']}.{name}"
                            cursor = conn.execute(
                                """
                                INSERT OR IGNORE INTO entity_tags (entity, tag, status, source, created_at)
                                VALUES (?, ?, 'proposed', 'classifier', ?)
                                """,
                                (entity, tag, now),
                            )
                            proposed += cursor.rowcount
        self.audit(actor, "classifier.run", "", {"proposed": proposed})
        return {"proposed": proposed, **self.list_entity_tags()}

    # -- rules rendering --

    def _role_member_regex(self, conn: sqlite3.Connection, role_id: int) -> str | None:
        rows = conn.execute(
            """
            SELECT users.username FROM users
            JOIN user_roles ON user_roles.user_id = users.id
            WHERE user_roles.role_id = ? AND users.is_active = 1
            """,
            (role_id,),
        ).fetchall()
        if not rows:
            return None
        return "(" + "|".join(re.escape(row["username"]) for row in rows) + ")"

    def render_access_control_rules(self, cluster: dict[str, Any]) -> str | None:
        """The cluster's Trino file-based access-control rules (JSON), or None
        when no fine-grained policies exist (engine stays wide open and no
        access-control files are written — today's behavior).

        Restriction model: users whose roles carry data policies are limited
        to the union of those policies; everyone else falls through to a
        catch-all allow. Catalog visibility mirrors the Phase 1 role grants so
        wire-protocol clients get the same catalog gate as the API. Tag
        policies append column deny/mask entries for tagged columns.
        """
        with self.conn() as conn:
            policies = conn.execute("SELECT * FROM data_policies ORDER BY id").fetchall()
            tag_rows = conn.execute(
                """
                SELECT entity_tags.entity, tag_policies.role_id, tag_policies.effect
                FROM tag_policies
                JOIN entity_tags ON entity_tags.tag = tag_policies.tag AND entity_tags.status = 'accepted'
                """
            ).fetchall()
            if not policies and not tag_rows:
                return None

            table_rules: list[dict[str, Any]] = []
            restricted_regexes: list[str] = []

            # information_schema and system data stay readable for everyone —
            # clients break without them.
            table_rules.append({"schema": "information_schema", "privileges": ["SELECT"]})
            table_rules.append({"catalog": "(system|jmx)", "privileges": ["SELECT"]})

            def column_entries(policy: dict[str, Any]) -> list[dict[str, Any]]:
                entries: list[dict[str, Any]] = []
                for column in policy["denied_columns"]:
                    entries.append({"name": column, "allow": False})
                for column, expression in policy["column_masks"].items():
                    entries.append({"name": column, "mask": expression})
                return entries

            for row in policies:
                policy = self.public_data_policy(conn, row)
                member_regex = self._role_member_regex(conn, row["role_id"])
                if member_regex is None:
                    continue
                restricted_regexes.append(member_regex)
                rule: dict[str, Any] = {"user": member_regex, "catalog": re.escape(policy["catalog"])}
                if policy["schema"]:
                    rule["schema"] = re.escape(policy["schema"])
                if policy["table"]:
                    rule["table"] = re.escape(policy["table"])
                rule["privileges"] = policy["privileges"]
                entries = column_entries(policy)
                if policy["allowed_columns"]:
                    # Allow-list semantics: Trino's file rules are deny-based
                    # per column, so allow-lists rely on the reader knowing the
                    # table's other columns from the metadata cache.
                    cached = self._cached_column_names(
                        conn, policy["catalog"], policy["schema"], policy["table"]
                    )
                    for column in cached:
                        if column not in policy["allowed_columns"] and not any(
                            entry["name"] == column for entry in entries
                        ):
                            entries.append({"name": column, "allow": False})
                if entries:
                    rule["columns"] = entries
                if policy["row_filter"]:
                    rule["filter"] = policy["row_filter"]
                table_rules.append(rule)

            # Tag policies: deny or NULL-mask tagged columns for the role, on
            # top of whatever access path grants the table.
            for tag_row in tag_rows:
                parts = str(tag_row["entity"]).split(".")
                if len(parts) != 4:
                    continue  # table-level tags carry no column effect
                catalog, schema_name, table_name, column = parts
                member_regex = self._role_member_regex(conn, tag_row["role_id"])
                if member_regex is None:
                    continue
                entry = {"name": column, "allow": False} if tag_row["effect"] == "deny" else {"name": column, "mask": "NULL"}
                table_rules.append(
                    {
                        "user": member_regex,
                        "catalog": re.escape(catalog),
                        "schema": re.escape(schema_name),
                        "table": re.escape(table_name),
                        "privileges": ["SELECT"],
                        "columns": [entry],
                    }
                )

            # Users restricted by policies get nothing beyond their rules; every
            # other user falls through to full access.
            if restricted_regexes:
                table_rules.append(
                    {
                        "user": "(?!" + "|".join(f"{regex}$" for regex in restricted_regexes) + ").*",
                        "privileges": list(DATA_POLICY_PRIVILEGES) + ["OWNERSHIP"],
                    }
                )
            else:
                table_rules.append({"privileges": list(DATA_POLICY_PRIVILEGES) + ["OWNERSHIP"]})

            # Catalog visibility mirrors the Phase 1 role grants so wire
            # clients can't browse catalogs the API would refuse.
            catalog_rules: list[dict[str, Any]] = [{"catalog": "(system|jmx)", "allow": "all"}]
            grant_rows = conn.execute(
                "SELECT role_id, target FROM role_grants WHERE grant_type = 'catalog'"
            ).fetchall()
            for grant in grant_rows:
                member_regex = self._role_member_regex(conn, grant["role_id"])
                if member_regex is None:
                    continue
                catalog_rules.append(
                    {
                        "user": member_regex,
                        "catalog": ".*" if grant["target"] == GRANT_WILDCARD else re.escape(grant["target"]),
                        "allow": "all",
                    }
                )
            # No fallthrough allow: a user with no catalog grant sees nothing,
            # which matches the control-plane behavior.

        rules = {
            "catalogs": catalog_rules,
            "schemas": [{"owner": False}],
            "tables": table_rules,
        }
        return json.dumps(rules, indent=2, sort_keys=True)

    def _cached_column_names(
        self, conn: sqlite3.Connection, catalog: str, schema_name: str, table_name: str
    ) -> list[str]:
        row = conn.execute(
            """
            SELECT columns_json FROM metadata_cache
            WHERE catalog = ? AND schema_name = ? AND table_name = ?
            ORDER BY updated_at DESC LIMIT 1
            """,
            (catalog, schema_name, table_name),
        ).fetchone()
        return [str(column.get("name", "")) for column in loads(row["columns_json"], [])] if row else []

    # --- MCP server (Phase 7 differentiator) --------------------------------------

    def run_readonly_sql(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        """Run one SELECT through the normal query path and poll it to a
        terminal state. The same validate_read_only_sql boundary as Ask Trino:
        callers (MCP clients) can never mutate data."""
        sql_text = validate_read_only_sql(str(payload.get("sql") or ""))
        result = self.create_query(
            {
                "cluster_id": payload.get("cluster_id"),
                "sql": sql_text,
                "catalog": str(payload.get("catalog") or ""),
                "schema": str(payload.get("schema") or ""),
                "fresh": bool(payload.get("fresh")),
            },
            user,
        )
        query = result["query"]
        polls = 0
        while query["status"] not in TERMINAL_QUERY_STATUSES and polls < ASK_TRINO_MAX_POLLS:
            polls += 1
            time.sleep(0.4)
            query = self.advance_query_run(query["id"], user, max_pages=5)["query"]
        return {
            "status": query["status"],
            "columns": [column.get("name") for column in query.get("columns") or []],
            "rows": query.get("data") or [],
            "row_count": query.get("row_count"),
            "truncated": bool(query.get("truncated")),
            "error": query.get("error_message") or None,
            "query_id": query["id"],
            # Callers polling for change need to know a result was served from
            # the cache (and can pass fresh=true to force re-execution).
            "cached": bool(query.get("cache_hit")),
            "result_cached_at": query.get("result_cached_at") or None,
        }

    # --- Query details (Phase 3) -----------------------------------------------

    def query_details(self, query_id: int, user: dict[str, Any]) -> dict[str, Any]:
        """Live execution detail for a query from the coordinator's
        /v1/query/{id} endpoint: state, headline stats, and a stage summary."""
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone()
            if not row:
                raise ApiError(404, "Query not found.")
            query = row_to_dict(row)
            self.require_query_access(query, user)
            if not query["trino_query_id"]:
                raise ApiError(409, "This query has no Trino query id (it never reached a coordinator).")
            coordinator = conn.execute(
                """
                SELECT * FROM provider_resources
                WHERE cluster_id = ? AND resource_type = 'coordinator_instance'
                ORDER BY id DESC LIMIT 1
                """,
                (query["cluster_id"],),
            ).fetchone()
            if not coordinator:
                raise ApiError(409, "The query's cluster has no running coordinator.")
            endpoint = self.coordinator_endpoint(row_to_dict(coordinator))
        url = f"http://{endpoint}:{TRINO_HTTP_PORT}/v1/query/{query['trino_query_id']}"
        try:
            request = urllib.request.Request(url, headers={"X-Trino-User": "trinohub-details"})
            with urllib.request.urlopen(request, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8", "replace"))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise ApiError(502, f"Could not fetch query details from the coordinator: {exc}.") from None

        stats = payload.get("queryStats") or {}
        stages: list[dict[str, Any]] = []

        def walk_stage(stage: dict[str, Any]) -> None:
            stage_stats = stage.get("stageStats") or {}
            stages.append(
                {
                    "stage_id": stage.get("stageId", ""),
                    "state": stage.get("state", ""),
                    "tasks": stage_stats.get("totalTasks"),
                    "input_rows": stage_stats.get("processedInputPositions"),
                    "input_bytes": stage_stats.get("processedInputDataSize"),
                    "cpu_time": stage_stats.get("totalCpuTime"),
                    "memory": stage_stats.get("userMemoryReservation"),
                }
            )
            for child in stage.get("subStages") or []:
                walk_stage(child)

        if payload.get("outputStage"):
            walk_stage(payload["outputStage"])
        return {
            "query_id": query_id,
            "trino_query_id": query["trino_query_id"],
            "state": payload.get("state", ""),
            "stats": {
                "elapsed_time": stats.get("elapsedTime"),
                "queued_time": stats.get("queuedTime"),
                "execution_time": stats.get("executionTime"),
                "cpu_time": stats.get("totalCpuTime"),
                "total_rows": stats.get("processedInputPositions") or stats.get("rawInputPositions"),
                "total_bytes": stats.get("processedInputDataSize") or stats.get("rawInputDataSize"),
                "peak_memory": stats.get("peakUserMemoryReservation"),
                "total_splits": stats.get("totalDrivers"),
                "completed_splits": stats.get("completedDrivers"),
            },
            "stages": stages,
            "error": (payload.get("errorInfo") or {}).get("message") if payload.get("errorInfo") else None,
        }

    def setup_row(self) -> dict[str, Any] | None:
        with self.conn() as conn:
            return row_to_dict(conn.execute("SELECT * FROM setup_settings WHERE id = 1").fetchone())

    def setup_status(self, query: dict[str, list[str]]) -> dict[str, Any]:
        setup = self.setup_row()
        validate = query.get("validate", ["0"])[0] == "1"
        aws_status: dict[str, Any] = {"metadata": self.aws.metadata()}
        if validate or not setup:
            region = query.get("region", [setup["region"] if setup else None])[0]
            aws_status = self.aws.full_status(region)
        return {
            "configured": bool(setup),
            "setup": self.public_setup(setup) if setup else None,
            "aws": aws_status,
        }

    def public_setup(self, setup: dict[str, Any] | None) -> dict[str, Any] | None:
        if not setup:
            return None
        config = provider_config(setup)
        return {
            "provider": setup.get("provider") or PROVIDER_AWS,
            "region": setup["region"],
            # AWS provider config, flattened onto the response for the current UI.
            "vpc_id": config.get("vpc_id", ""),
            "private_subnet_ids": config.get("private_subnet_ids", []),
            "cluster_security_group_id": config.get("cluster_security_group_id", ""),
            "node_instance_profile": config.get("node_instance_profile", ""),
            "allowed_ui_cidrs": loads(setup["allowed_ui_cidrs"], []),
            "allowed_instance_types": loads(setup.get("allowed_instance_types", "[]"), []),
            "cluster_base_domain": setup.get("cluster_base_domain", "") or "",
            "provider_identity": loads(setup["provider_identity"], {}),
            "provider_validation": loads(setup["provider_validation"], {}),
            "completed_at": setup["completed_at"],
        }

    def normalize_allowed_ui_cidrs(self, raw_value: Any) -> list[str]:
        if isinstance(raw_value, str):
            raw_value = [item.strip() for item in raw_value.split(",")]
        if raw_value is None:
            raw_value = []
        if not isinstance(raw_value, list):
            raise ApiError(400, "allowed_ui_cidrs must be a list of CIDR ranges.")
        normalized: list[str] = []
        for value in raw_value:
            text = str(value).strip()
            if not text:
                continue
            if "/" not in text:
                try:
                    address = ipaddress.ip_address(text)
                except ValueError:
                    raise ApiError(400, f"Invalid allowed UI CIDR: {text}.") from None
                text = f"{text}/32" if address.version == 4 else f"{text}/128"
            try:
                network = ipaddress.ip_network(text, strict=False)
            except ValueError:
                raise ApiError(400, f"Invalid allowed UI CIDR: {text}.") from None
            rendered = str(network)
            if rendered not in normalized:
                normalized.append(rendered)
        return normalized

    @staticmethod
    def _effective_client_ip(
        *, remote_addr: str | None, forwarded_for: str | None = None
    ) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
        """The address the UI-CIDR gate judges: the direct peer, except that a
        loopback peer (the nginx/Caddy front) is unwrapped to the first
        X-Forwarded-For hop. A non-loopback peer's XFF is untrusted spoofable
        input and ignored. None when no parseable address is available."""
        remote_text = str(remote_addr or "").strip()
        if not remote_text:
            return None
        try:
            remote_address = ipaddress.ip_address(remote_text)
        except ValueError:
            return None
        candidate = remote_text
        if forwarded_for and remote_address.is_loopback:
            candidate = forwarded_for.split(",", 1)[0].strip() or remote_text
        try:
            return ipaddress.ip_address(candidate)
        except ValueError:
            return None

    @staticmethod
    def _ip_in_cidrs(address: ipaddress.IPv4Address | ipaddress.IPv6Address, cidrs: list[str]) -> bool:
        for cidr in cidrs:
            try:
                if address in ipaddress.ip_network(str(cidr), strict=False):
                    return True
            except ValueError:
                continue
        return False

    def client_ip_allowed(self, *, remote_addr: str | None, forwarded_for: str | None = None) -> bool:
        setup = self.setup_row()
        cidrs = loads(setup["allowed_ui_cidrs"], []) if setup else []
        if not cidrs:
            return True
        address = self._effective_client_ip(remote_addr=remote_addr, forwarded_for=forwarded_for)
        if address is None:
            return False
        if address.is_loopback:
            return True
        return self._ip_in_cidrs(address, cidrs)

    def _guard_ui_cidr_lockout(
        self,
        cidrs: list[str],
        *,
        remote_addr: str | None,
        forwarded_for: str | None,
        confirmed: bool,
    ) -> None:
        """Refuse an allowed-UI-CIDR list that would 403 the requester's own IP
        on their very next request. An empty list restricts nothing, loopback
        callers can always reach the app from the host, and ``confirmed`` is
        the explicit escape hatch for intentionally excluding yourself (e.g.
        configuring the allowlist for a different network than you're on).
        Callers without transport context (tests, scripts driving the model
        directly) pass neither address and skip the check."""
        if not cidrs or confirmed:
            return
        if remote_addr is None and forwarded_for is None:
            return
        address = self._effective_client_ip(remote_addr=remote_addr, forwarded_for=forwarded_for)
        if address is None or address.is_loopback:
            return
        if not self._ip_in_cidrs(address, cidrs):
            suffix = "/32" if address.version == 4 else "/128"
            raise ApiError(
                400,
                f"allowed_ui_cidrs would lock you out: your address {address} is not in the list. "
                f"Add {address}{suffix}, or resend with confirm_lockout=true to apply it anyway.",
            )

    def complete_setup(
        self,
        payload: dict[str, Any],
        *,
        remote_addr: str | None = None,
        forwarded_for: str | None = None,
    ) -> tuple[dict[str, Any], str]:
        if self.setup_row():
            raise ApiError(409, "Setup is already complete.")
        self._verify_setup_token(payload.get("setup_token"))

        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", ""))
        email = str(payload.get("email", "")).strip()
        if not username:
            raise ApiError(400, "username is required.")
        if not password:
            raise ApiError(400, "password is required.")

        aws_status = self.aws.full_status(payload.get("region") or None)
        if not aws_status.get("ok"):
            failed = [
                str(check.get("name") or check.get("service") or "AWS check")
                for check in aws_status.get("checks", [])
                if not check.get("ok")
            ]
            detail = ", ".join(failed) if failed else "one or more AWS checks failed"
            raise ApiError(400, f"AWS validation failed: {detail}.")
        region = str(payload.get("region") or aws_status.get("region") or "us-east-2")
        vpcs = aws_status.get("network", {}).get("vpcs", [])
        subnets = aws_status.get("network", {}).get("subnets", [])

        vpc_id = str(payload.get("vpc_id") or (vpcs[0]["vpc_id"] if vpcs else ""))
        subnet_ids = payload.get("private_subnet_ids") or [
            subnet["subnet_id"] for subnet in subnets if not vpc_id or subnet["vpc_id"] == vpc_id
        ]
        if isinstance(subnet_ids, str):
            subnet_ids = [item.strip() for item in subnet_ids.split(",") if item.strip()]
        if not vpc_id:
            raise ApiError(400, "vpc_id is required.")
        if not subnet_ids:
            raise ApiError(400, "private_subnet_ids is required.")

        node_profile = str(payload.get("node_instance_profile") or "TrinoHubNodeRole").strip()
        allowed_ui_cidrs = self.normalize_allowed_ui_cidrs(payload.get("allowed_ui_cidrs") or [])
        self._guard_ui_cidr_lockout(
            allowed_ui_cidrs,
            remote_addr=remote_addr,
            forwarded_for=forwarded_for,
            confirmed=payload.get("confirm_lockout") is True,
        )

        dry_run = self.aws.dry_run_instance_launch(
            region=region,
            subnet_id=subnet_ids[0],
            node_instance_profile=node_profile,
        )
        validation = dict(aws_status)
        validation["launch_dry_run"] = dry_run
        if not dry_run.get("ok"):
            raise ApiError(400, f"EC2 launch dry run failed: {dry_run.get('detail')}")

        now = utc_now()
        with self.conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (username, email, password_hash, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, 'admin', 1, ?, ?)
                """,
                (username, email, hash_password(password), now, now),
            )
            user_id = cursor.lastrowid
            self._set_user_roles(conn, user_id, ["admin"])
            aws_config = {
                "vpc_id": vpc_id,
                "private_subnet_ids": subnet_ids,
                "cluster_security_group_id": str(payload.get("cluster_security_group_id") or ""),
                "node_instance_profile": node_profile,
            }
            conn.execute(
                """
                INSERT INTO setup_settings
                  (id, provider, region, provider_config_json, allowed_ui_cidrs,
                   provider_identity, provider_validation, allowed_instance_types, completed_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    PROVIDER_AWS,
                    region,
                    dumps(aws_config),
                    dumps(allowed_ui_cidrs),
                    dumps(aws_status.get("identity", {})),
                    dumps(validation),
                    dumps(self._normalize_allowed_instance_types(payload.get("allowed_instance_types"))),
                    now,
                ),
            )
            user = row_to_dict(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
            token = self.create_session(conn, user_id)

        # Setup is now complete; the one-time bootstrap token is spent.
        self._clear_bootstrap_token()
        self.audit(user, "setup.complete", username)
        return {"user": self.decorate_user(user), "setup": self.public_setup(self.setup_row())}, token

    def create_session(self, conn: sqlite3.Connection, user_id: int) -> str:
        token = new_session_token()
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=self.session_hours())
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token_hash(token), user_id, now.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds")),
        )
        return token

    def login(self, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", ""))
        self.check_login_rate_limit(username)
        with self.conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? AND is_active = 1",
                (username,),
            ).fetchone()
            is_service = bool(row["is_service"]) if row and "is_service" in row.keys() else False
            if not row or is_service or not verify_password(password, row["password_hash"]):
                self.record_login_failure(username)
                raise ApiError(401, "Invalid username or password.")
            self.clear_login_failures(username)
        # SSO password-login policy: operators (any MANAGE_* privilege) keep
        # break-glass password access; everyone else must use the IdP.
        candidate = row_to_dict(row)
        if self.oidc_settings().get("password_login") == "operators_only":
            if not (MANAGEMENT_PRIVILEGES & self.user_privileges(candidate)):
                raise ApiError(403, "Password login is disabled for this account. Sign in with SSO.")
        with self.conn() as conn:
            token = self.create_session(conn, int(row["id"]))
            user = row_to_dict(row)
        return {"user": self.decorate_user(user)}, token

    def check_login_rate_limit(self, username: str) -> None:
        if not username:
            return
        now = time.monotonic()
        with self._login_lock:
            recent = [t for t in self._login_failures.get(username, []) if now - t < LOGIN_WINDOW_SECONDS]
            self._login_failures[username] = recent
            if len(recent) >= LOGIN_MAX_FAILURES:
                raise ApiError(429, "Too many failed login attempts. Try again later.")

    def record_login_failure(self, username: str) -> None:
        if not username:
            return
        now = time.monotonic()
        with self._login_lock:
            recent = [t for t in self._login_failures.get(username, []) if now - t < LOGIN_WINDOW_SECONDS]
            recent.append(now)
            self._login_failures[username] = recent

    def clear_login_failures(self, username: str) -> None:
        with self._login_lock:
            self._login_failures.pop(username, None)

    def logout(self, request: RequestLike) -> dict[str, Any]:
        header = request.headers.get("Cookie", "")
        parsed = cookies.SimpleCookie()
        parsed.load(header)
        if SESSION_COOKIE in parsed:
            with self.conn() as conn:
                conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(parsed[SESSION_COOKIE].value),))
        return {"ok": True}

    def list_users(self) -> dict[str, Any]:
        with self.conn() as conn:
            rows = [row_to_dict(row) for row in conn.execute("SELECT * FROM users ORDER BY username").fetchall()]
        return {"users": [self.decorate_user(row) for row in rows]}

    def create_user(self, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", ""))
        role = str(payload.get("role", "user"))
        if role not in {"admin", "user"}:
            raise ApiError(400, "role must be admin or user.")
        # ``roles`` (a list of role names) supersedes the legacy binary
        # ``role`` field when present; the legacy field keeps old clients working.
        role_names = payload.get("roles")
        if role_names is None:
            role_names = [role]
        if not isinstance(role_names, list):
            raise ApiError(400, "roles must be a list of role names.")
        is_service = bool(payload.get("is_service", False))
        if not username:
            raise ApiError(400, "username is required.")
        if not password and not is_service:
            raise ApiError(400, "username and password are required.")
        # Service accounts have no usable password: they authenticate only via
        # API tokens ('!' can never be produced by hash_password).
        password_hash = "!" if is_service else hash_password(password)
        now = utc_now()
        with self.conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (username, email, password_hash, role, is_active, is_service, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (username, str(payload.get("email", "")), password_hash, role, 1 if is_service else 0, now, now),
            )
            user_id = cursor.lastrowid
            assigned = self._set_user_roles(conn, user_id, role_names)
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            user = row_to_dict(row)
        self.audit(actor, "user.create", username, {"roles": assigned, "is_service": is_service})
        return {"user": self.decorate_user(user)}

    def update_user(self, user_id: int, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row:
                raise ApiError(404, "User not found.")
            current = self.decorate_user(row_to_dict(row))

        role_names: list[str] | None = None
        if "roles" in payload:
            if not isinstance(payload["roles"], list):
                raise ApiError(400, "roles must be a list of role names.")
            role_names = payload["roles"]
        elif "role" in payload:
            role = str(payload["role"])
            if role not in {"admin", "user"}:
                raise ApiError(400, "role must be admin or user.")
            role_names = [role]
        is_active = current["is_active"]
        if "is_active" in payload:
            if not isinstance(payload["is_active"], bool):
                raise ApiError(400, "is_active must be a boolean.")
            is_active = payload["is_active"]
        email = current["email"]
        if "email" in payload:
            email = str(payload["email"]).strip()
        new_password_hash = None
        if "password" in payload:
            password = str(payload["password"])
            if not password:
                raise ApiError(400, "password cannot be empty.")
            new_password_hash = hash_password(password)

        changed: dict[str, Any] = {}
        if role_names is not None:
            requested = sorted({str(name).strip().lower() for name in role_names if str(name).strip()})
            if requested != sorted(current["roles"]):
                changed["roles"] = role_names
        if is_active != current["is_active"]:
            changed["is_active"] = is_active
        if email != current["email"]:
            changed["email"] = email
        if new_password_hash is not None:
            changed["password"] = True

        if not changed:
            return {"user": current, "changes": []}

        now = utc_now()
        with self.conn() as conn:
            conn.execute(
                "UPDATE users SET is_active = ?, email = ?, updated_at = ? WHERE id = ?",
                (1 if is_active else 0, email, now, user_id),
            )
            if new_password_hash is not None:
                conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, user_id))
            if "roles" in changed:
                changed["roles"] = self._set_user_roles(conn, user_id, role_names or [])
            # Generalized last-admin protection: the change must leave at least
            # one active MANAGE_SECURITY holder. Raising rolls back the
            # transaction, so a violating edit never lands.
            if "roles" in changed or "is_active" in changed:
                self._require_security_holder_remains(conn)
            # Revoke active sessions when access is curtailed or credentials change,
            # forcing a fresh login under the new state.
            if (not is_active) or (new_password_hash is not None):
                conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            updated = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            user = row_to_dict(updated)
        result_user = self.decorate_user(user)
        detail: dict[str, Any] = {"changed": sorted(changed)}
        if "roles" in changed:
            detail["roles"] = changed["roles"]
        self.audit(actor, "user.update", current["username"], detail)
        return {"user": result_user, "changes": sorted(changed)}

    def list_clusters(self, user: dict[str, Any] | None = None) -> dict[str, Any]:
        with self.conn() as conn:
            rows = conn.execute("SELECT * FROM clusters ORDER BY created_at DESC").fetchall()
            clusters = [self.public_cluster(row) for row in rows]
        if user is not None and not self.has_privilege(user, PRIVILEGE_MANAGE_CLUSTERS):
            # Non-operators only see the clusters their roles grant access to.
            clusters = [cluster for cluster in clusters if self.user_can_use_cluster(user, cluster["id"])]
        return {"clusters": clusters}

    def _owner_username(self, user_id: Any) -> str:
        """Username for a cluster owner id, cached (usernames are immutable)."""
        if user_id is None:
            return ""
        cached = self._owner_username_cache.get(user_id)
        if cached is not None:
            return cached
        with self.conn() as conn:
            row = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        username = row["username"] if row else ""
        self._owner_username_cache[user_id] = username
        return username

    def public_cluster(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "status": row["status"],
            "preset": row["preset"],
            "instance_type": row["instance_type"],
            "region": row["region"],
            "worker_mode": row["worker_mode"],
            "min_workers": row["min_workers"],
            "max_workers": row["max_workers"],
            "auto_suspend_minutes": row["auto_suspend_minutes"],
            "hostname": (row["hostname"] if "hostname" in row.keys() else "") or "",
            # Effective version: fall back to the current default for records that
            # predate per-cluster version pinning.
            "trino_version": (row["trino_version"] if "trino_version" in row.keys() else "") or TRINO_VERSION,
            "accelerated": bool(row["accelerated"] if "accelerated" in row.keys() else 0),
            "uptime_schedule": loads(
                row["uptime_schedule_json"] if "uptime_schedule_json" in row.keys() else "[]", []
            ),
            "catalogs": loads(row["catalogs_json"], []),
            "owner_user_id": row["owner_user_id"],
            "owner_username": self._owner_username(row["owner_user_id"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def resource_rows(self, conn: sqlite3.Connection, cluster_id: int) -> list[dict[str, Any]]:
        rows = conn.execute(
            "SELECT * FROM provider_resources WHERE cluster_id = ? ORDER BY resource_type, id",
            (cluster_id,),
        ).fetchall()
        return [row_to_dict(row) for row in rows]

    def public_resource(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "type": row["resource_type"],
            "resource_id": row["resource_id"],
            "region": row["region"],
            "metadata": loads(row["metadata_json"], {}),
            "created_at": row["created_at"],
        }

    def create_cluster_bootstrap_token(self, conn: sqlite3.Connection, cluster_id: int) -> str:
        token = new_session_token()
        now = utc_now()
        conn.execute("DELETE FROM cluster_bootstrap_tokens WHERE cluster_id = ?", (cluster_id,))
        conn.execute(
            """
            INSERT INTO cluster_bootstrap_tokens (cluster_id, token_hash, created_at)
            VALUES (?, ?, ?)
            """,
            (cluster_id, token_hash(token), now),
        )
        return token

    def clear_cluster_bootstrap_token(self, cluster_id: int) -> None:
        with self.conn() as conn:
            conn.execute("DELETE FROM cluster_bootstrap_tokens WHERE cluster_id = ?", (cluster_id,))

    def verify_cluster_bootstrap_token(self, conn: sqlite3.Connection, cluster_id: int, token: str) -> None:
        row = conn.execute(
            "SELECT token_hash FROM cluster_bootstrap_tokens WHERE cluster_id = ?",
            (cluster_id,),
        ).fetchone()
        if not row or not token or not hmac.compare_digest(token_hash(token), row["token_hash"]):
            raise ApiError(403, "A valid node bootstrap token is required.")

    def node_config_script(
        self,
        *,
        cluster_id: int,
        role: str,
        token: str,
        instance_type: str = "",
    ) -> str:
        if role not in {"coordinator", "worker"}:
            raise ApiError(400, "role must be coordinator or worker.")
        with self.conn() as conn:
            self.verify_cluster_bootstrap_token(conn, cluster_id, token)
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            cluster = self.public_cluster(row)
            cluster["catalog_configs"] = self.catalog_configs_for_cluster(conn, cluster["catalogs"])
            drivers = self.catalog_driver_descriptors(conn, cluster["catalog_configs"])
            coordinator_uri = None
            if role == "worker":
                coordinator = conn.execute(
                    """
                    SELECT * FROM provider_resources
                    WHERE cluster_id = ? AND resource_type = 'coordinator_instance'
                    ORDER BY id DESC LIMIT 1
                    """,
                    (cluster_id,),
                ).fetchone()
                if coordinator:
                    coordinator_endpoint = self.coordinator_endpoint(row_to_dict(coordinator))
                    coordinator_uri = f"http://{coordinator_endpoint}:{TRINO_HTTP_PORT}"
        control_plane_ip = self.aws.control_plane_private_ip() if hasattr(self.aws, "control_plane_private_ip") else None
        control_plane_uri = f"http://{control_plane_ip}:{CONTROL_PLANE_NODE_CONFIG_PORT}" if control_plane_ip else None
        return self.aws.trino_node_config_script(
            cluster=cluster,
            node_role=role,
            region=cluster["region"],
            instance_type=instance_type or self.cluster_instance_type(cluster),
            coordinator_uri=coordinator_uri,
            secret_resolver=self.secret_store.get,
            drivers=drivers,
            control_plane_uri=control_plane_uri,
            cluster_id=cluster_id,
            bootstrap_token=token,
            access_control_rules=self.render_access_control_rules(cluster),
        )

    def record_provider_resource(
        self,
        conn: sqlite3.Connection,
        *,
        cluster_id: int,
        resource_type: str,
        resource_id: str,
        region: str,
        metadata: dict[str, Any] | None = None,
        provider: str = PROVIDER_AWS,
    ) -> None:
        now = utc_now()
        conn.execute(
            """
            INSERT INTO provider_resources
              (cluster_id, provider, resource_type, resource_id, region, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(resource_type, resource_id) DO UPDATE SET
              cluster_id = excluded.cluster_id,
              provider = excluded.provider,
              region = excluded.region,
              metadata_json = excluded.metadata_json
            """,
            (cluster_id, provider, resource_type, resource_id, region, dumps(metadata or {}), now),
        )

    def cluster_resources(self, cluster_id: int) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            return {
                "cluster": self.public_cluster(row),
                "resources": [self.public_resource(resource) for resource in self.resource_rows(conn, cluster_id)],
            }

    def delete_resource_record(self, resource_db_id: int) -> None:
        with self.conn() as conn:
            conn.execute("DELETE FROM provider_resources WHERE id = ?", (resource_db_id,))

    def cleanup_tracked_resources(
        self,
        cluster: dict[str, Any],
        resources: list[dict[str, Any]],
        *,
        strict_security_groups: bool,
    ) -> dict[str, Any]:
        deleted: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []

        def remember(action: str, resource: dict[str, Any], detail: dict[str, Any] | None = None) -> None:
            deleted.append(
                {
                    "action": action,
                    "type": resource["resource_type"],
                    "resource_id": resource["resource_id"],
                    "detail": detail or {},
                }
            )
            self.delete_resource_record(int(resource["id"]))

        def fail(resource: dict[str, Any], exc: Exception) -> None:
            failed.append(
                {
                    "type": resource["resource_type"],
                    "resource_id": resource["resource_id"],
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

        for resource in [item for item in resources if item["resource_type"] == "auto_scaling_group"]:
            try:
                detail = self.aws.delete_worker_auto_scaling_group(
                    region=resource["region"],
                    name=resource["resource_id"],
                )
                remember("delete_auto_scaling_group", resource, detail)
            except Exception as exc:
                fail(resource, exc)

        instance_resources = [item for item in resources if item["resource_type"] == "coordinator_instance"]
        for region in sorted({resource["region"] for resource in instance_resources}):
            region_resources = [resource for resource in instance_resources if resource["region"] == region]
            try:
                detail = self.aws.terminate_instances(
                    region=region,
                    instance_ids=[resource["resource_id"] for resource in region_resources],
                )
                for resource in region_resources:
                    remember("terminate_instance", resource, detail)
            except Exception as exc:
                for resource in region_resources:
                    fail(resource, exc)

        for resource in [item for item in resources if item["resource_type"] == "launch_template"]:
            try:
                detail = self.aws.delete_launch_template(
                    region=resource["region"],
                    launch_template_id=resource["resource_id"],
                )
                remember("delete_launch_template", resource, detail)
            except Exception as exc:
                fail(resource, exc)

        if any(item["type"] in {"auto_scaling_group", "coordinator_instance"} for item in deleted):
            try:
                wait_result = self.aws.wait_for_cluster_instances_gone(
                    region=cluster["region"],
                    cluster_name=cluster["name"],
                )
                deleted.append({"action": "wait_for_instances", "type": "instance", "resource_id": "*", "detail": wait_result})
            except Exception as exc:
                failed.append({"type": "instance", "resource_id": "*", "error": f"{type(exc).__name__}: {exc}"})

        for resource in [item for item in resources if item["resource_type"] == "security_group"]:
            metadata = loads(resource["metadata_json"], {})
            is_managed = bool(metadata.get("managed"))
            if not is_managed:
                skipped.append(
                    {
                        "action": "skip_unmanaged_security_group",
                        "type": resource["resource_type"],
                        "resource_id": resource["resource_id"],
                    }
                )
                self.delete_resource_record(int(resource["id"]))
                continue
            try:
                rule_cleanup: dict[str, Any] = {}
                if hasattr(self.aws, "cleanup_managed_security_group_rules"):
                    rule_cleanup = self.aws.cleanup_managed_security_group_rules(
                        region=resource["region"],
                        group_id=resource["resource_id"],
                        metadata=metadata,
                    )
                detail = self.aws.delete_security_group(region=resource["region"], group_id=resource["resource_id"])
                if rule_cleanup:
                    detail["rule_cleanup"] = rule_cleanup
                remember("delete_security_group", resource, detail)
            except Exception as exc:
                if strict_security_groups:
                    fail(resource, exc)
                else:
                    skipped.append(
                        {
                            "action": "security_group_cleanup_pending",
                            "type": resource["resource_type"],
                            "resource_id": resource["resource_id"],
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )

        return {"deleted": deleted, "skipped": skipped, "failed": failed}

    def resolve_instance_type(self, region: str, preset: str) -> str:
        """Legacy preset → instance type resolution, kept for clusters created
        before the Settings instance allowlist (those store a preset, not an
        explicit instance_type). New clusters bypass this via cluster_instance_type."""
        candidates = PRESET_INSTANCE_CANDIDATES.get(preset)
        if not candidates:
            raise ApiError(400, "preset must be Cost, Balanced, or Power.")
        try:
            available = set(self.aws.available_instance_types(region, candidates))
        except Exception as exc:
            # A discovery hiccup should not block the operation; fall back to the
            # top preference and let the actual launch report any real problem.
            print(f"Instance-type availability check failed for {preset} in {region}: {type(exc).__name__}: {exc}")
            return candidates[0]
        for candidate in candidates:
            if candidate in available:
                return candidate
        raise ApiError(
            400,
            f"No instance type for the {preset} preset is available in {region} "
            f"(tried {', '.join(candidates)}). Try a different region or preset.",
        )

    def preset_tiers(self, region: str | None = None) -> dict[str, Any]:
        """Resolve each preset to the instance type a cluster would actually
        launch, so the Create-cluster and Settings views display the real
        AWS-resolved tier instead of a hardcoded fallback (see roadmap B1)."""
        setup = self.setup_row()
        resolved_region = region or (setup["region"] if setup else None) or self.aws.region
        tiers = []
        for preset in ("Cost", "Balanced", "Power"):
            try:
                instance_type = self.resolve_instance_type(resolved_region, preset)
            except ApiError:
                # None offered in-region right now: still surface the top
                # candidate so the UI shows a meaningful tier label.
                instance_type = PRESET_INSTANCE_CANDIDATES[preset][0]
            tiers.append(
                {
                    "preset": preset,
                    "instance_type": instance_type,
                    "memory_gib": INSTANCE_MEMORY_GB.get(instance_type, DEFAULT_INSTANCE_MEMORY_GB),
                    "hourly_usd": INSTANCE_HOURLY_USD.get(instance_type, DEFAULT_INSTANCE_HOURLY_USD),
                }
            )
        return {"region": resolved_region, "tiers": tiers}

    def allowed_instance_types(self) -> list[str]:
        """The admin-enabled instance types clusters may be created against."""
        setup = self.setup_row()
        return loads(setup.get("allowed_instance_types", "[]"), []) if setup else []

    def _normalize_allowed_instance_types(self, raw: Any) -> list[str]:
        """Validate a set of picker selections, returned in canonical order.

        Each entry must be one of the curated POPULAR_TRINO_INSTANCE_TYPES;
        duplicates are dropped and the result follows the curated ordering so the
        stored allowlist is stable regardless of selection order.
        """
        if raw is None:
            return []
        if isinstance(raw, str):
            raw = [raw]
        try:
            requested = {str(item).strip() for item in raw if str(item).strip()}
        except TypeError:
            raise ApiError(400, "instance_types must be a list of instance type names.")
        unknown = requested - set(POPULAR_TRINO_INSTANCE_TYPES)
        if unknown:
            raise ApiError(400, f"Not selectable instance types: {', '.join(sorted(unknown))}.")
        return [itype for itype in POPULAR_TRINO_INSTANCE_TYPES if itype in requested]

    def cluster_instance_type(self, cluster: dict[str, Any]) -> str:
        """The instance type a cluster launches on.

        New clusters store an explicit ``instance_type`` chosen from the Settings
        allowlist. Legacy clusters created under the old preset model fall back to
        resolving their ``preset`` so they keep launching unchanged.
        """
        explicit = str(cluster.get("instance_type") or "").strip()
        if explicit:
            return explicit
        return self.resolve_instance_type(cluster["region"], cluster["preset"])

    def instance_type_options(self, region: str | None = None) -> dict[str, Any]:
        """Curated memory-optimized instance types for the Settings allowlist and
        the Create-cluster picker, with per-region availability and the
        currently-enabled set (``allowed``)."""
        setup = self.setup_row()
        resolved_region = region or (setup["region"] if setup else None) or self.aws.region
        allowed = set(self.allowed_instance_types())
        try:
            offered = set(self.aws.available_instance_types(resolved_region, POPULAR_TRINO_INSTANCE_TYPES))
        except Exception as exc:
            # A discovery hiccup should not blank the picker; show every option.
            print(f"Instance-type listing failed in {resolved_region}: {type(exc).__name__}: {exc}")
            offered = set(POPULAR_TRINO_INSTANCE_TYPES)
        options = [
            {
                "instance_type": itype,
                "family": itype.split(".")[0],
                "vcpu": INSTANCE_VCPU.get(itype, DEFAULT_INSTANCE_VCPU),
                "memory_gib": INSTANCE_MEMORY_GB.get(itype, DEFAULT_INSTANCE_MEMORY_GB),
                "hourly_usd": INSTANCE_HOURLY_USD.get(itype, DEFAULT_INSTANCE_HOURLY_USD),
                "has_instance_store": itype in INSTANCE_STORE_GB,
                "instance_store_gb": INSTANCE_STORE_GB.get(itype, 0),
                "available": itype in offered,
                "allowed": itype in allowed,
            }
            for itype in POPULAR_TRINO_INSTANCE_TYPES
        ]
        return {
            "region": resolved_region,
            "allowed_instance_types": [itype for itype in POPULAR_TRINO_INSTANCE_TYPES if itype in allowed],
            "instance_types": options,
        }

    def set_allowed_instance_types(self, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        """Persist the admin-curated allowlist of cluster instance types."""
        setup = self.setup_row()
        if not setup:
            raise ApiError(409, "Complete setup before choosing instance types.")
        instance_types = self._normalize_allowed_instance_types(payload.get("instance_types"))
        if instance_types:
            region = setup["region"]
            try:
                offered = set(self.aws.available_instance_types(region, instance_types))
            except Exception as exc:
                # Don't block the choice on a transient discovery error; the
                # launch path surfaces any real capacity problem at start time.
                print(f"Instance-type availability check failed in {region}: {type(exc).__name__}: {exc}")
                offered = set(instance_types)
            unavailable = [itype for itype in instance_types if itype not in offered]
            if unavailable:
                raise ApiError(400, f"Not offered in {region}: {', '.join(unavailable)}.")
        with self.conn() as conn:
            conn.execute(
                "UPDATE setup_settings SET allowed_instance_types = ? WHERE id = 1",
                (dumps(instance_types),),
            )
        self.audit(actor, "settings.instance_types", "", {"instance_types": instance_types})
        return {"setup": self.public_setup(self.setup_row())}

    def normalize_cluster_hostname(self, raw_value: Any) -> str:
        """Validate and canonicalize a hostname/domain (lowercased, no trailing
        dot). Empty is allowed and means "unset". Shared by the per-cluster
        override and the account-wide base domain."""
        host = str(raw_value or "").strip().lower().rstrip(".")
        if host and not HOST_NAME_PATTERN.fullmatch(host):
            raise ApiError(400, "hostname must be a valid domain name (letters, digits, dots, hyphens).")
        return host

    def set_cluster_base_domain(self, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        """Persist the account-wide base domain used to derive per-cluster
        connection hostnames as ``<cluster-name>.<base-domain>``. TrinoHub only
        renders the name; the operator owns the wildcard DNS that resolves it.
        An empty value clears it and the connect popup falls back to the live
        coordinator IP."""
        setup = self.setup_row()
        if not setup:
            raise ApiError(409, "Complete setup before configuring a cluster base domain.")
        domain = self.normalize_cluster_hostname(payload.get("cluster_base_domain"))
        with self.conn() as conn:
            conn.execute(
                "UPDATE setup_settings SET cluster_base_domain = ? WHERE id = 1",
                (domain,),
            )
        # Domain change rewrites every cluster's hostname, so refresh the gateway.
        self._sync_tls_gateway_safe()
        self.audit(actor, "settings.cluster_base_domain", domain)
        return {"setup": self.public_setup(self.setup_row())}

    def available_trino_versions(self) -> list[str]:
        """Trino versions the control plane will offer and accept, newest
        first: the union of releases discovered live (when a fetcher is
        configured) and the static fallback list. Discovery results are cached;
        failures fall back silently to the static list and retry sooner."""
        now = time.monotonic()
        if self._trino_versions_cache and now < self._trino_versions_cache[0]:
            return self._trino_versions_cache[1]
        discovered: list[str] = []
        expiry = now + TRINO_VERSION_REFRESH_SECONDS
        if self._trino_version_fetcher is not None:
            try:
                discovered = self._trino_version_fetcher()
            except Exception as exc:
                print(f"Trino version discovery failed: {type(exc).__name__}: {exc}")
                expiry = now + TRINO_VERSION_RETRY_SECONDS
        merged = sorted({int(v) for v in [*discovered, *SUPPORTED_TRINO_VERSIONS]}, reverse=True)
        versions = [str(v) for v in merged]
        self._trino_versions_cache = (expiry, versions)
        return versions

    def trino_version_options(self) -> dict[str, Any]:
        """Trino versions offered on the Create-cluster screen (newest first)."""
        versions = self.available_trino_versions()
        return {"versions": versions, "default": versions[0]}

    def create_cluster(self, payload: dict[str, Any], owner: dict[str, Any]) -> dict[str, Any]:
        setup = self.setup_row()
        if not setup:
            raise ApiError(409, "Complete setup before creating clusters.")
        name = str(payload.get("name", "")).strip()
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9-]{1,62}", name):
            raise ApiError(400, "name must be 2-63 alphanumeric or hyphen characters.")
        instance_type = str(payload.get("instance_type", "")).strip()
        allowed = self.allowed_instance_types()
        if not allowed:
            raise ApiError(400, "No instance types are enabled. An admin must add at least one in Settings.")
        if not instance_type:
            raise ApiError(400, "instance_type is required.")
        if instance_type not in allowed:
            raise ApiError(400, f"{instance_type} is not an enabled instance type. Choose one of: {', '.join(allowed)}.")
        # Validate the chosen type is offered in the region now, so an unavailable
        # type fails fast here rather than at start.
        try:
            offered = set(self.aws.available_instance_types(setup["region"], [instance_type]))
        except Exception as exc:
            print(f"Instance-type availability check failed for {instance_type} in {setup['region']}: {type(exc).__name__}: {exc}")
            offered = {instance_type}
        if instance_type not in offered:
            raise ApiError(400, f"{instance_type} is not available in {setup['region']} right now. Try another type.")
        worker_mode = str(payload.get("worker_mode", "autoscale"))
        if worker_mode not in {"autoscale", "fixed"}:
            raise ApiError(400, "worker_mode must be autoscale or fixed.")
        min_workers = int(payload.get("min_workers", 1))
        max_workers = int(payload.get("max_workers", min_workers))
        if min_workers < 1 or max_workers < min_workers:
            raise ApiError(400, "worker range is invalid.")
        accelerated = bool(payload.get("accelerated", False))
        if accelerated:
            self.require_accelerated_capable(instance_type, worker_mode)
        if accelerated and "auto_suspend_minutes" not in payload:
            # Cache is wiped on suspend, so accelerated clusters default to a
            # long idle timeout instead of the usual aggressive one.
            auto_suspend_minutes: int | None = ACCELERATED_DEFAULT_AUTO_SUSPEND_MINUTES
        else:
            auto_suspend_minutes = self.normalize_auto_suspend_minutes(payload.get("auto_suspend_minutes"))
        hostname = self.normalize_cluster_hostname(payload.get("hostname"))
        offered_versions = self.available_trino_versions()
        trino_version = str(payload.get("trino_version") or "").strip() or offered_versions[0]
        if trino_version not in offered_versions:
            raise ApiError(400, f"trino_version must be one of: {', '.join(offered_versions)}.")
        catalogs = self.normalize_catalogs(payload.get("catalogs") or ["system", "tpch", "tpcds"])
        now = utc_now()
        with self.conn() as conn:
            self.require_known_catalogs(conn, catalogs)
            cursor = conn.execute(
                """
                INSERT INTO clusters
                  (name, status, preset, instance_type, region, worker_mode, min_workers, max_workers,
                   auto_suspend_minutes, hostname, trino_version, accelerated, catalogs_json,
                   owner_user_id, created_at, updated_at)
                VALUES (?, 'Not enabled', '', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    instance_type,
                    setup["region"],
                    worker_mode,
                    min_workers,
                    max_workers,
                    auto_suspend_minutes,
                    hostname,
                    trino_version,
                    1 if accelerated else 0,
                    dumps(catalogs),
                    owner["id"],
                    now,
                    now,
                ),
            )
            conn.execute(
                """
                INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                VALUES (?, 'created', 'Cluster record created', ?, ?)
                """,
                (cursor.lastrowid, dumps({"aws_resources_created": False}), now),
            )
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cursor.lastrowid,)).fetchone()
            cluster = self.public_cluster(row)
        self.audit(owner, "cluster.create", name, {"instance_type": instance_type, "accelerated": accelerated})
        return {"cluster": cluster}

    def require_accelerated_capable(self, instance_type: str, worker_mode: str) -> None:
        """Guardrails for the accelerated (warm-cache) toggle.

        The Trino file system cache needs dedicated local NVMe on every node, so
        only instance-store types qualify. Autoscaling is also rejected: scale
        events reshuffle the consistent-hash split placement and dilute the
        cache, so v1 mirrors the vendor and requires a fixed worker count.
        """
        if instance_store_disks(instance_type) < 1:
            nvme_types = [itype for itype in POPULAR_TRINO_INSTANCE_TYPES if itype in INSTANCE_STORE_GB]
            raise ApiError(
                409,
                f"Accelerated clusters need an instance type with local NVMe storage; "
                f"{instance_type} is EBS-only. Choose one of: {', '.join(nvme_types)}.",
            )
        if worker_mode != "fixed":
            raise ApiError(
                409,
                "Accelerated clusters require worker_mode=fixed: autoscaling reshuffles "
                "cached data across workers and defeats the cache.",
            )

    def normalize_auto_suspend_minutes(self, raw_value: Any) -> int | None:
        if raw_value is None or raw_value == "":
            return None
        try:
            minutes = int(raw_value)
        except (TypeError, ValueError):
            raise ApiError(400, "auto_suspend_minutes must be a positive integer or null.") from None
        if minutes < 1 or minutes > AUTO_SUSPEND_MAX_MINUTES:
            raise ApiError(400, "auto_suspend_minutes must be between 1 and 1440 minutes.")
        return minutes

    def normalize_catalogs(self, raw_catalogs: Any) -> list[str]:
        if isinstance(raw_catalogs, str):
            raw_catalogs = [item.strip() for item in raw_catalogs.split(",")]
        if not isinstance(raw_catalogs, list):
            raise ApiError(400, "catalogs must be a list of catalog names.")
        catalogs: list[str] = []
        for value in raw_catalogs:
            name = str(value).strip()
            if not name:
                continue
            if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", name):
                raise ApiError(400, "catalogs must contain lowercase letters, numbers, and underscores only.")
            if name not in catalogs:
                catalogs.append(name)
        if "system" not in catalogs:
            catalogs.insert(0, "system")
        return catalogs

    def _coerce_worker_count(self, payload: dict[str, Any], key: str, current: int) -> int:
        if key not in payload:
            return current
        try:
            return int(payload[key])
        except (TypeError, ValueError):
            raise ApiError(400, f"{key} must be an integer.") from None

    def update_cluster(self, cluster_id: int, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        # Editing is only safe in steady states. Transitional states (Creating,
        # Starting, Suspending, Deleting, Scaling, Updating) are rejected so we
        # never race the provisioning/teardown paths or the autoscaler.
        editable_states = {"Not enabled", "Running", "Suspended", "Failed"}
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            current = self.public_cluster(row)
        if current["status"] not in editable_states:
            raise ApiError(409, f"Cluster cannot be edited while status is {current['status']}.")

        # Resolve the new field values, defaulting to the current ones.
        worker_mode = current["worker_mode"]
        if "worker_mode" in payload:
            worker_mode = str(payload["worker_mode"])
            if worker_mode not in {"autoscale", "fixed"}:
                raise ApiError(400, "worker_mode must be autoscale or fixed.")
        min_workers = self._coerce_worker_count(payload, "min_workers", current["min_workers"])
        max_workers = self._coerce_worker_count(payload, "max_workers", current["max_workers"])
        if min_workers < 1 or max_workers < min_workers:
            raise ApiError(400, "worker range is invalid.")
        auto_suspend_minutes = current["auto_suspend_minutes"]
        if "auto_suspend_minutes" in payload:
            auto_suspend_minutes = self.normalize_auto_suspend_minutes(payload["auto_suspend_minutes"])
        catalogs = current["catalogs"]
        if "catalogs" in payload:
            catalogs = self.normalize_catalogs(payload["catalogs"])
        hostname = current["hostname"]
        if "hostname" in payload:
            hostname = self.normalize_cluster_hostname(payload["hostname"])
        accelerated = current["accelerated"]
        if "accelerated" in payload:
            accelerated = bool(payload["accelerated"])
        if accelerated:
            self.require_accelerated_capable(self.cluster_instance_type(current), worker_mode)
        uptime_schedule = current["uptime_schedule"]
        if "uptime_schedule" in payload:
            uptime_schedule = self.normalize_uptime_schedule(payload["uptime_schedule"])

        changed: dict[str, Any] = {}
        if accelerated != current["accelerated"]:
            changed["accelerated"] = accelerated
        if uptime_schedule != current["uptime_schedule"]:
            changed["uptime_schedule"] = uptime_schedule
        if worker_mode != current["worker_mode"]:
            changed["worker_mode"] = worker_mode
        if min_workers != current["min_workers"]:
            changed["min_workers"] = min_workers
        if max_workers != current["max_workers"]:
            changed["max_workers"] = max_workers
        if auto_suspend_minutes != current["auto_suspend_minutes"]:
            changed["auto_suspend_minutes"] = auto_suspend_minutes
        if catalogs != current["catalogs"]:
            changed["catalogs"] = catalogs
        if hostname != current["hostname"]:
            changed["hostname"] = hostname

        if not changed:
            return {
                "cluster": current,
                "changes": [],
                "applied_live": [],
                "restart_required": False,
                "restart_required_fields": [],
            }

        # Validate referenced catalogs exist before mutating anything.
        if "catalogs" in changed:
            with self.conn() as conn:
                self.require_known_catalogs(conn, catalogs)

        asg_fields = sorted({"worker_mode", "min_workers", "max_workers"} & set(changed))
        is_running = current["status"] == "Running"
        applied_live: list[str] = []
        restart_required_fields: list[str] = []

        # Apply Auto Scaling Group sizing to the live cluster BEFORE persisting, so
        # a failed AWS call leaves the DB unchanged and the edit can be retried.
        if asg_fields and is_running:
            if self._apply_worker_sizing_live(
                cluster_id,
                region=current["region"],
                min_workers=min_workers,
                max_workers=max_workers,
            ):
                applied_live.extend(asg_fields)

        now = utc_now()
        with self.conn() as conn:
            conn.execute(
                """
                UPDATE clusters
                SET worker_mode = ?, min_workers = ?, max_workers = ?,
                    auto_suspend_minutes = ?, catalogs_json = ?, hostname = ?,
                    accelerated = ?, uptime_schedule_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    worker_mode,
                    min_workers,
                    max_workers,
                    auto_suspend_minutes,
                    dumps(catalogs),
                    hostname,
                    1 if accelerated else 0,
                    dumps(uptime_schedule),
                    now,
                    cluster_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                VALUES (?, 'updated', 'Cluster configuration updated.', ?, ?)
                """,
                (cluster_id, dumps({"changed": sorted(changed)}), now),
            )
            updated = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            result_cluster = self.public_cluster(updated)

        # auto_suspend_minutes is read from the DB by the poller each cycle,
        # and so are keep-warm uptime windows.
        if "auto_suspend_minutes" in changed:
            applied_live.append("auto_suspend_minutes")
        if "uptime_schedule" in changed:
            applied_live.append("uptime_schedule")
        # Catalogs are baked into the launch template + coordinator user-data, so a
        # running cluster must be suspended and started again to pick them up.
        if "catalogs" in changed and is_running:
            restart_required_fields.append("catalogs")
        # The cache mount + fs.cache.* properties render at node bootstrap, so
        # toggling acceleration also needs a restart to take effect.
        if "accelerated" in changed and is_running:
            restart_required_fields.append("accelerated")

        self.audit(actor, "cluster.update", current["name"], {"changed": sorted(changed)})
        return {
            "cluster": result_cluster,
            "changes": sorted(changed),
            "applied_live": sorted(applied_live),
            "restart_required": bool(restart_required_fields),
            "restart_required_fields": sorted(restart_required_fields),
        }

    def _apply_worker_sizing_live(
        self, cluster_id: int, *, region: str, min_workers: int, max_workers: int
    ) -> bool:
        """Push min/max/desired to a running cluster's worker ASG.

        Returns True if the live ASG was reconfigured, False if there is no ASG to
        update (changes will then take effect at next start). Raises ApiError on an
        AWS failure, after reverting the transient ``Updating`` status.
        """
        with self.conn() as conn:
            asg_row = conn.execute(
                """
                SELECT * FROM provider_resources
                WHERE cluster_id = ? AND resource_type = 'auto_scaling_group'
                ORDER BY id DESC LIMIT 1
                """,
                (cluster_id,),
            ).fetchone()
            if not asg_row:
                return False
            asg_resource = row_to_dict(asg_row)

        self.update_cluster_status(cluster_id, "Updating", "Applying worker sizing changes to the Auto Scaling Group.")
        try:
            asg = self.aws.worker_auto_scaling_group(region=region, name=asg_resource["resource_id"])
            current_desired = int(asg.get("desired_capacity") or min_workers) if asg.get("found") else min_workers
            new_desired = max(min_workers, min(max_workers, current_desired))
            self.aws.set_worker_desired_capacity(
                region=region,
                name=asg_resource["resource_id"],
                desired_capacity=new_desired,
                min_size=min_workers,
                max_size=max_workers,
            )
        except Exception as exc:
            print(f"Failed to apply worker sizing for cluster {cluster_id}: {type(exc).__name__}: {exc}")
            self.update_cluster_status(cluster_id, "Running", "Reverted after failing to apply worker sizing changes.")
            raise ApiError(502, "Failed to apply worker sizing changes to AWS. No changes were saved.") from None

        with self.conn() as conn:
            metadata = loads(asg_resource["metadata_json"], {})
            metadata.update({"desired_capacity": new_desired, "min_size": min_workers, "max_size": max_workers})
            conn.execute(
                "UPDATE provider_resources SET metadata_json = ? WHERE id = ?",
                (dumps(metadata), asg_resource["id"]),
            )
        self.update_cluster_status(cluster_id, "Running", "Worker sizing changes applied.")
        return True

    def update_cluster_status(self, cluster_id: int, status: str, message: str) -> dict[str, Any]:
        now = utc_now()
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            previous_status = row["status"]
            conn.execute("UPDATE clusters SET status = ?, updated_at = ? WHERE id = ?", (status, now, cluster_id))
            conn.execute(
                """
                INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                VALUES (?, ?, ?, '{}', ?)
                """,
                (cluster_id, status.lower().replace(" ", "_"), message, now),
            )
            updated = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            cluster = self.public_cluster(updated)
        # Lifecycle notifications for the states operators care about.
        if status != previous_status and status in {"Failed", "Suspended", "Running"}:
            event = {"Failed": "cluster_failed", "Suspended": "cluster_suspended", "Running": "cluster_running"}[status]
            self.notify(event, f"Cluster {cluster['name']} is now {status}: {message}", {"cluster": cluster["name"]})
        return {"cluster": cluster}

    def start_cluster(self, cluster_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("confirm_billable") is not True:
            raise ApiError(
                409,
                "Starting a cluster creates billable AWS resources. Retry with confirm_billable=true after explicit user confirmation.",
            )
        setup = self.setup_row()
        if not setup:
            raise ApiError(409, "Setup is incomplete.")
        cfg = provider_config(setup)
        subnet_ids = cfg.get("private_subnet_ids", [])
        if not subnet_ids:
            raise ApiError(409, "No subnet is configured.")

        with self.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            cluster = self.public_cluster(row)
            resources = self.resource_rows(conn, cluster_id)
            blocking_resources = [resource for resource in resources if resource["resource_type"] != "security_group"]
            if blocking_resources:
                types = ", ".join(sorted({resource["resource_type"] for resource in blocking_resources}))
                raise ApiError(409, f"Cluster still has tracked runtime resources ({types}); suspend or delete it before starting again.")
            if cluster["status"] in {"Creating", "Starting", "Running", "Scaling", "Deleting"}:
                raise ApiError(409, f"Cluster cannot be started while status is {cluster['status']}.")
            cluster["catalog_configs"] = self.catalog_configs_for_cluster(conn, cluster["catalogs"])
            # Fail fast if an attached connector needs a driver JAR that hasn't
            # been uploaded, rather than letting nodes fail to boot Trino.
            self.catalog_driver_descriptors(conn, cluster["catalog_configs"])
            now = utc_now()
            # Atomically claim the start: only one caller can flip this exact status
            # to Creating, so several resume triggers racing on the same cluster —
            # e.g. a burst of native wire queries hitting a suspended host at once —
            # launch AWS resources exactly once. Losers get a 409 and back off.
            claimed = conn.execute(
                "UPDATE clusters SET status = 'Creating', updated_at = ? WHERE id = ? AND status = ?",
                (now, cluster_id, cluster["status"]),
            ).rowcount
            if not claimed:
                raise ApiError(409, "Cluster start is already in progress.")
            bootstrap_token = self.create_cluster_bootstrap_token(conn, cluster_id)
            conn.execute(
                """
                INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                VALUES (?, 'provisioning_started', 'AWS provisioning started after billable resource confirmation.', '{}', ?)
                """,
                (cluster_id, now),
            )

        region = setup["region"]
        instance_type = self.cluster_instance_type(cluster)
        configured_security_group_id = str(cfg.get("cluster_security_group_id") or "").strip()
        control_plane_ip = self.aws.control_plane_private_ip() if hasattr(self.aws, "control_plane_private_ip") else None
        control_plane_uri = (
            f"http://{control_plane_ip}:{CONTROL_PLANE_NODE_CONFIG_PORT}"
            if control_plane_ip
            else None
        )
        image_id: str | None = None

        try:
            managed_sg = self.aws.ensure_managed_security_group(
                region=region,
                vpc_id=cfg.get("vpc_id", ""),
                cluster_name=cluster["name"],
            )
            security_group_ids = [managed_sg["group_id"]]
            if configured_security_group_id and configured_security_group_id not in security_group_ids:
                security_group_ids.append(configured_security_group_id)

            with self.conn() as conn:
                self.record_provider_resource(
                    conn,
                    cluster_id=cluster_id,
                    resource_type="security_group",
                    resource_id=managed_sg["group_id"],
                    region=region,
                    metadata={"managed": True, **managed_sg},
                )
                if configured_security_group_id and configured_security_group_id != managed_sg["group_id"]:
                    self.record_provider_resource(
                        conn,
                        cluster_id=cluster_id,
                        resource_type="security_group",
                        resource_id=configured_security_group_id,
                        region=region,
                        metadata={"managed": False, "source": "setup_settings"},
                    )

            coordinator = self.aws.launch_coordinator_instance(
                region=region,
                subnet_id=subnet_ids[0],
                security_group_ids=security_group_ids,
                node_instance_profile=cfg.get("node_instance_profile", ""),
                cluster=cluster,
                instance_type=instance_type,
                image_id=image_id,
                control_plane_uri=control_plane_uri,
                cluster_id=cluster_id,
                bootstrap_token=bootstrap_token,
            )
            image_id = coordinator.get("image_id")
            coordinator_host = coordinator.get("private_ip_address") or coordinator.get("private_dns_name")
            coordinator_uri = f"http://{coordinator_host}:{TRINO_HTTP_PORT}" if coordinator_host else None
            with self.conn() as conn:
                self.record_provider_resource(
                    conn,
                    cluster_id=cluster_id,
                    resource_type="coordinator_instance",
                    resource_id=coordinator["instance_id"],
                    region=region,
                    metadata=coordinator,
                )

            launch_template = self.aws.create_worker_launch_template(
                region=region,
                security_group_ids=security_group_ids,
                node_instance_profile=cfg.get("node_instance_profile", ""),
                cluster=cluster,
                instance_type=instance_type,
                image_id=image_id,
                coordinator_uri=coordinator_uri,
                control_plane_uri=control_plane_uri,
                cluster_id=cluster_id,
                bootstrap_token=bootstrap_token,
            )
            with self.conn() as conn:
                self.record_provider_resource(
                    conn,
                    cluster_id=cluster_id,
                    resource_type="launch_template",
                    resource_id=launch_template["launch_template_id"],
                    region=region,
                    metadata=launch_template,
                )

            auto_scaling_group = self.aws.create_worker_auto_scaling_group(
                region=region,
                subnet_ids=subnet_ids,
                cluster=cluster,
                launch_template_id=launch_template["launch_template_id"],
            )
            with self.conn() as conn:
                self.record_provider_resource(
                    conn,
                    cluster_id=cluster_id,
                    resource_type="auto_scaling_group",
                    resource_id=auto_scaling_group["auto_scaling_group_name"],
                    region=region,
                    metadata=auto_scaling_group,
                )
                now = utc_now()
                conn.execute("UPDATE clusters SET status = 'Starting', updated_at = ? WHERE id = ?", (now, cluster_id))
                # Fresh launch/resume: drop any persisted idle/autoscale timers so a
                # stale idle clock from a prior run can't trigger an instant suspend.
                conn.execute("DELETE FROM cluster_timer_state WHERE cluster_id = ?", (cluster_id,))
                conn.execute(
                    """
                    INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                    VALUES (?, 'resources_created', 'AWS resources created; cluster nodes are starting.', ?, ?)
                    """,
                    (
                        cluster_id,
                        dumps(
                            {
                                "coordinator_instance_id": coordinator["instance_id"],
                                "launch_template_id": launch_template["launch_template_id"],
                                "auto_scaling_group_name": auto_scaling_group["auto_scaling_group_name"],
                                "security_group_ids": security_group_ids,
                                "signed_node_config": bool(control_plane_uri),
                            }
                        ),
                        now,
                    ),
                )
                updated = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
                resources = [self.public_resource(resource) for resource in self.resource_rows(conn, cluster_id)]
            # Coordinator IP is now known: add this cluster's upstream to the gateway.
            self._sync_tls_gateway_safe()
            return {
                "dry_run": False,
                "message": "AWS resources created; cluster nodes are starting.",
                "cluster": self.public_cluster(updated),
                "resources": resources,
            }
        except Exception as exc:
            now = utc_now()
            with self.conn() as conn:
                conn.execute("UPDATE clusters SET status = 'Failed', updated_at = ? WHERE id = ?", (now, cluster_id))
                conn.execute("DELETE FROM cluster_bootstrap_tokens WHERE cluster_id = ?", (cluster_id,))
                conn.execute(
                    """
                    INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                    VALUES (?, 'provisioning_failed', ?, ?, ?)
                    """,
                    (cluster_id, f"AWS provisioning failed: {type(exc).__name__}: {exc}", dumps({"error": str(exc)}), now),
                )
            if isinstance(exc, ApiError):
                raise
            # Full detail is captured in the cluster event above and the server log;
            # surface AWS/boto errors (actionable, e.g. InsufficientInstanceCapacity)
            # but don't leak internal exception text for unexpected failures.
            print(f"AWS provisioning failed for cluster {cluster_id}: {type(exc).__name__}: {exc}")
            raise ApiError(500, f"AWS provisioning failed: {self._safe_aws_error(exc)}") from exc

    def coordinator_endpoint(self, resource: dict[str, Any]) -> str:
        metadata = loads(resource["metadata_json"], {})
        return str(
            metadata.get("private_ip_address")
            or metadata.get("private_dns_name")
            or metadata.get("public_ip_address")
            or metadata.get("public_dns_name")
            or resource["resource_id"]
        )

    def cluster_connection_info(self, cluster_id: int, user: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build the client connection details (JDBC/ODBC/CLI) for one cluster,
        used by the per-cluster "Connection info" popup.

        Host resolution, most to least preferred:
          1. the cluster's explicit ``hostname`` override, else
          2. ``<cluster-name>.<base-domain>`` when a base domain is configured, else
          3. the live coordinator IP (only present while the cluster is running).
        A domain/override host is assumed to sit behind operator-managed TLS
        (https/443); the bare coordinator IP is the internal http/8080 endpoint.
        When none of the three resolve (no domain and no running coordinator),
        ``resolvable`` is False and the popup shows a hint instead of strings."""
        if user is not None:
            self.require_cluster_access(user, cluster_id)
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            cluster = self.public_cluster(row)
            setup = self.setup_row()
            base_domain = (setup.get("cluster_base_domain") if setup else "") or ""
            override = cluster.get("hostname") or ""
            coordinator_ip = ""
            coordinator = conn.execute(
                """
                SELECT * FROM provider_resources
                WHERE cluster_id = ? AND resource_type = 'coordinator_instance'
                ORDER BY id DESC LIMIT 1
                """,
                (cluster_id,),
            ).fetchone()
            if coordinator:
                coordinator_ip = self.coordinator_endpoint(row_to_dict(coordinator))

        user_name = ""
        if user:
            user_name = str(user.get("username") or user.get("email") or "").strip()

        if override:
            host, tls, via = override, True, "override"
        elif base_domain:
            host, tls, via = f"{cluster['name']}.{base_domain}", True, "domain"
        elif coordinator_ip:
            host, tls, via = coordinator_ip, False, "coordinator_ip"
        else:
            return {
                "cluster_id": cluster_id,
                "cluster_name": cluster["name"],
                "trino_version": cluster.get("trino_version") or "",
                "resolvable": False,
                "hint": (
                    "No address yet. Set a cluster base domain in Settings, or start "
                    "the cluster to get a coordinator address."
                ),
            }

        scheme = "https" if tls else "http"
        port = 443 if tls else TRINO_HTTP_PORT
        user_query = f"?user={user_name}" if user_name else ""
        jdbc = f"jdbc:trino://{host}:{port}{user_query}"
        if tls:
            jdbc += ("&" if user_query else "?") + "SSL=true"
        # Password-style auth (LDAP) only makes sense over TLS; plain-HTTP
        # endpoints authenticate by username alone.
        odbc_auth = "LDAP Authentication" if tls else "No Authentication"
        odbc = (
            f"Driver={{Trino ODBC Driver}};Host={host};Port={port};"
            f"AuthenticationType={{{odbc_auth}}};SSL={'1' if tls else '0'}"
        )
        cli = f"trino --server {scheme}://{host}:{port}" + (f" --user {user_name}" if user_name else "")
        return {
            "cluster_id": cluster_id,
            "cluster_name": cluster["name"],
            "trino_version": cluster.get("trino_version") or "",
            "resolvable": True,
            "via": via,
            "host": host,
            "port": port,
            "scheme": scheme,
            "tls": tls,
            "user": user_name,
            "jdbc_url": jdbc,
            "odbc": odbc,
            "cli": cli,
            # Direct link to the coordinator's built-in Trino web UI. Same host/port
            # as the client endpoint (the Caddy gateway proxies /ui through to the
            # coordinator), so it inherits TLS when a domain/override is set.
            "web_ui": f"{scheme}://{host}:{port}/ui/",
        }

    # --- Let's Encrypt TLS gateway -------------------------------------------
    # A Caddy reverse proxy on the control plane terminates TLS for cluster
    # hostnames and forwards to coordinators. See trinohub/tls_gateway.py.

    def cluster_tls_routes(self) -> dict[str, str]:
        """Map each addressable cluster hostname to its gateway upstream.

        A running cluster's host points straight at its coordinator (``ip:8080``).
        A cluster that is resuming or auto-suspended — i.e. it will serve queries
        once it starts — points instead at the wire-protocol resume shim on the
        control-plane app, which triggers the resume and holds the client until the
        coordinator is ready. Clusters that cannot serve a query (Failed, Not
        enabled, manually suspended, mid-delete) get no route, so the gateway
        returns a friendly 503 for their name."""
        setup = self.setup_row()
        base_domain = (setup.get("cluster_base_domain") if setup else "") or ""
        if not base_domain:
            return {}
        routes: dict[str, str] = {}
        with self.conn() as conn:
            for row in conn.execute("SELECT * FROM clusters").fetchall():
                cluster = self.public_cluster(row)
                host = cluster["hostname"] or f"{cluster['name']}.{base_domain}"
                status = cluster["status"]
                if status in {"Running", "Scaling"}:
                    coordinator = conn.execute(
                        """
                        SELECT * FROM provider_resources
                        WHERE cluster_id = ? AND resource_type = 'coordinator_instance'
                        ORDER BY id DESC LIMIT 1
                        """,
                        (cluster["id"],),
                    ).fetchone()
                    ip = self.coordinator_endpoint(row_to_dict(coordinator)) if coordinator else ""
                    if ip:
                        routes[host] = f"{ip}:{TRINO_HTTP_PORT}"
                elif status in {"Creating", "Starting"} or (
                    status == "Suspended" and cluster["auto_suspend_minutes"] is not None
                ):
                    # Not serving yet, but a query should resume it and wait — hand
                    # the host to the shim rather than 503 the client.
                    routes[host] = SHIM_UPSTREAM
        return routes

    def cluster_for_host(self, host: str) -> dict[str, Any] | None:
        """Resolve an inbound gateway hostname to its cluster row (as a public
        dict), matching either the derived ``<name>.<base-domain>`` or an explicit
        ``hostname`` override. Returns None for the bare base domain or an unknown
        host."""
        host = (host or "").strip().lower().rstrip(".")
        if ":" in host:  # strip any :port the client sent in the Host header
            host = host.split(":", 1)[0]
        if not host:
            return None
        setup = self.setup_row()
        base_domain = (setup.get("cluster_base_domain") if setup else "") or ""
        if not base_domain or host == base_domain:
            return None
        with self.conn() as conn:
            rows = conn.execute("SELECT * FROM clusters").fetchall()
        for row in rows:
            override = (row["hostname"] or "").strip().lower()
            derived = f"{str(row['name']).lower()}.{base_domain}"
            if host == derived or (override and host == override):
                return self.public_cluster(row)
        return None

    def authorize_tls_domain(self, domain: str) -> bool:
        """Caddy's on-demand-TLS gate: only mint a certificate for the base
        domain or a hostname that belongs to a known cluster (derived name or
        explicit override). A cert may be issued before the cluster is running,
        so the name is ready when it starts."""
        domain = (domain or "").strip().lower().rstrip(".")
        if not domain:
            return False
        setup = self.setup_row()
        base_domain = (setup.get("cluster_base_domain") if setup else "") or ""
        if not base_domain:
            return False
        if domain == base_domain:
            return True
        return self.cluster_for_host(domain) is not None

    def sync_tls_gateway(self) -> tuple[bool, str]:
        """Render the current gateway config and push it to Caddy. Best-effort:
        inactive (no base domain) or Caddy-down both return without raising, so
        cluster operations never fail because the gateway isn't up."""
        setup = self.setup_row()
        base_domain = (setup.get("cluster_base_domain") if setup else "") or ""
        if not base_domain:
            return False, "No base domain set; TLS gateway inactive."
        allowed_cidrs = loads(setup["allowed_ui_cidrs"], []) if setup else []
        caddyfile = build_caddyfile(base_domain, allowed_cidrs, self.cluster_tls_routes())
        ok, detail = push_config(caddyfile)
        if not ok:
            print(f"TLS gateway sync skipped: {detail}")
        return ok, detail

    def _sync_tls_gateway_safe(self) -> None:
        """Fire-and-forget gateway sync for lifecycle hooks; never propagates."""
        try:
            self.sync_tls_gateway()
        except Exception as exc:  # pragma: no cover - defensive
            print(f"TLS gateway sync error: {type(exc).__name__}: {exc}")

    # --- Native Trino wire-protocol resume shim ------------------------------
    # A native Trino client (CLI/JDBC/BI) that queries a suspended cluster reaches
    # the control-plane app here (the gateway routes not-yet-serving cluster hosts
    # to us). We speak just enough of the Trino client protocol to (1) resume the
    # cluster, (2) hold the client in a synthetic QUEUED state while it starts, and
    # (3) replay its original request to the coordinator once it is ready — so a
    # query submitted to a suspended cluster starts the cluster and is processed,
    # instead of failing.

    @staticmethod
    def _filter_wire_headers(headers: list[tuple[str, str]]) -> list[tuple[str, str]]:
        return [(k, v) for (k, v) in headers if k.lower() not in WIRE_HOP_BY_HOP_HEADERS]

    def _wire_scheme_host(self, host: str) -> tuple[str, str]:
        clean = (host or "").split(":", 1)[0].strip().lower()
        return "https", clean

    def _synthetic_queued_results(self, host: str, shim_id: str, seq: int) -> dict[str, Any]:
        """A valid Trino ``QueryResults`` body with no rows that keeps the client
        polling our holding URI. ``id``/``infoUri``/``stats`` must be present or the
        JDBC driver rejects the response before it follows ``nextUri``."""
        scheme, clean_host = self._wire_scheme_host(host)
        query_id = f"trinohub_resume_{shim_id}"
        return {
            "id": query_id,
            "infoUri": f"{scheme}://{clean_host}/ui/query.html?{query_id}",
            "nextUri": f"{scheme}://{clean_host}/v1/statement/resuming/{shim_id}/{seq + 1}",
            "stats": {
                "state": "QUEUED",
                "queued": True,
                "scheduled": False,
                "nodes": 0,
                "totalSplits": 0,
                "queuedSplits": 0,
                "runningSplits": 0,
                "completedSplits": 0,
                "cpuTimeMillis": 0,
                "wallTimeMillis": 0,
                "queuedTimeMillis": 0,
                "elapsedTimeMillis": 0,
                "processedRows": 0,
                "processedBytes": 0,
                "peakMemoryBytes": 0,
                "spilledBytes": 0,
            },
            "warnings": [],
        }

    def _synthetic_failed_results(self, host: str, shim_id: str, message: str) -> dict[str, Any]:
        """A valid terminal FAILED ``QueryResults`` (well-formed ``error`` object so
        clients surface the message rather than NPE)."""
        scheme, clean_host = self._wire_scheme_host(host)
        query_id = f"trinohub_resume_{shim_id}"
        return {
            "id": query_id,
            "infoUri": f"{scheme}://{clean_host}/ui/query.html?{query_id}",
            "stats": {"state": "FAILED", "queued": False, "scheduled": False, "nodes": 0},
            "error": {
                "message": message,
                "errorCode": 65536,
                "errorName": "GENERIC_INTERNAL_ERROR",
                "errorType": "INTERNAL_ERROR",
                "failureInfo": {"type": "io.trino.spi.TrinoException", "message": message},
            },
            "warnings": [],
        }

    def _wire_resumable_cluster(self, host: str) -> dict[str, Any] | None:
        """The cluster behind a gateway host if it is one the shim should serve
        (running, resuming, or auto-suspended), else None."""
        cluster = self.cluster_for_host(host)
        if not cluster:
            return None
        status = cluster["status"]
        if status in {"Running", "Scaling", "Creating", "Starting"}:
            return cluster
        if status == "Suspended" and cluster["auto_suspend_minutes"] is not None:
            return cluster
        return None

    def _coordinator_endpoint_for(self, cluster_id: int) -> str | None:
        with self.conn() as conn:
            coordinator = conn.execute(
                """
                SELECT * FROM provider_resources
                WHERE cluster_id = ? AND resource_type = 'coordinator_instance'
                ORDER BY id DESC LIMIT 1
                """,
                (cluster_id,),
            ).fetchone()
        if not coordinator:
            return None
        return self.coordinator_endpoint(row_to_dict(coordinator)) or None

    def _forward_to_coordinator(
        self,
        *,
        endpoint: str,
        host: str,
        method: str,
        path_qs: str,
        headers: list[tuple[str, str]],
        body: bytes,
    ) -> tuple[int, list[tuple[str, str]], bytes]:
        """Relay a request to the coordinator's HTTP port and return its raw
        ``(status, headers, body)`` unparsed — Trino's own 4xx/5xx responses are
        meaningful to the client, so nothing is raised on error status."""
        _, clean_host = self._wire_scheme_host(host)
        url = f"http://{endpoint}:{TRINO_HTTP_PORT}{path_qs}"
        out_headers = self._filter_wire_headers(headers)
        # Tell the coordinator (which runs http-server.process-forwarded=true) the
        # external host/scheme so the nextUri/infoUri it emits point back through
        # the gateway, not at its internal IP.
        out_headers = [
            (k, v)
            for (k, v) in out_headers
            if k.lower() not in {"x-forwarded-host", "x-forwarded-proto", "x-forwarded-for"}
        ]
        out_headers.append(("X-Forwarded-Host", clean_host))
        out_headers.append(("X-Forwarded-Proto", "https"))
        request = urllib.request.Request(
            url, data=body if body else None, method=method.upper()
        )
        for key, value in out_headers:
            request.add_header(key, value)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                resp_headers = list(response.headers.items())
                return response.status, self._filter_wire_headers(resp_headers), response.read()
        except urllib.error.HTTPError as exc:
            resp_headers = list(exc.headers.items()) if exc.headers else []
            return exc.code, self._filter_wire_headers(resp_headers), exc.read()

    def wire_submit_statement(
        self, host: str, body: bytes, headers: list[tuple[str, str]]
    ) -> dict[str, Any]:
        """Handle ``POST /v1/statement`` for a not-yet-serving cluster host.

        Returns one of:
        - ``{"kind": "queued", "results": <dict>}`` — resume triggered, client holds;
        - ``{"kind": "proxied", "status", "headers", "body"}`` — cluster already
          Running, request forwarded straight through;
        - ``{"kind": "no_route"}`` — host is unknown/not resumable (caller 503s)."""
        cluster = self._wire_resumable_cluster(host)
        if not cluster:
            return {"kind": "no_route"}

        if cluster["status"] in {"Running", "Scaling"}:
            endpoint = self._coordinator_endpoint_for(cluster["id"])
            if endpoint:
                status, resp_headers, resp_body = self._forward_to_coordinator(
                    endpoint=endpoint, host=host, method="POST",
                    path_qs="/v1/statement", headers=headers, body=body,
                )
                return {"kind": "proxied", "status": status, "headers": resp_headers, "body": resp_body}
            # Racing with a suspend that dropped the coordinator; fall through to hold.

        # Trigger the resume (idempotent; a burst of queries resumes the cluster
        # once) and capture the request so we can replay it when Trino is up.
        if cluster["status"] == "Suspended":
            try:
                self.start_cluster(cluster["id"], {"confirm_billable": True})
            except ApiError:
                # Already claimed by a concurrent trigger / the poller — fine, hold.
                pass
        shim_id = self._store_wire_capture(cluster["id"], host, body, headers)
        return {"kind": "queued", "results": self._synthetic_queued_results(host, shim_id, seq=1)}

    def wire_poll_resuming(self, shim_id: str, seq: int) -> dict[str, Any]:
        """Handle a holding poll of ``/v1/statement/resuming/{shim_id}/{seq}``.

        Returns ``{"kind": "queued"|"failed", "results": <dict>}`` while starting or
        on timeout, or ``{"kind": "proxied", ...}`` once the query has been handed
        off to the coordinator."""
        capture = self._load_wire_capture(shim_id)
        if not capture:
            # Unknown/expired holding id: return a terminal failure the client can
            # surface rather than a dangling poll.
            return {"kind": "failed", "results": self._synthetic_failed_results("", shim_id, "This query is no longer being tracked; run it again.")}

        host = capture["host"]
        cluster_id = int(capture["cluster_id"])

        if self.elapsed_ms(capture["created_at"]) > WIRE_RESUME_TIMEOUT_SECONDS * 1000:
            self._delete_wire_capture(shim_id)
            return {"kind": "failed", "results": self._synthetic_failed_results(host, shim_id, "The cluster did not finish starting in time; run the query again.")}

        cluster = self.cluster_for_host(host)
        status = cluster["status"] if cluster else None
        if status == "Starting":
            try:
                cluster = self.refresh_cluster_health(cluster_id)["cluster"]
                status = cluster["status"]
            except ApiError:
                pass

        if status in {"Creating", "Starting", "Suspended"}:
            return {"kind": "queued", "results": self._synthetic_queued_results(host, shim_id, seq)}
        if status not in {"Running", "Scaling"}:
            self._delete_wire_capture(shim_id)
            return {"kind": "failed", "results": self._synthetic_failed_results(host, shim_id, f"The cluster is {status or 'unavailable'} and cannot run the query.")}

        endpoint = self._coordinator_endpoint_for(cluster_id)
        if not endpoint:
            return {"kind": "queued", "results": self._synthetic_queued_results(host, shim_id, seq)}

        # Cluster is up: replay the captured statement to the coordinator and hand
        # the client onto the real query. Flip the gateway route to the coordinator
        # so subsequent polls (and new clients) go direct.
        status_code, resp_headers, resp_body = self._forward_to_coordinator(
            endpoint=endpoint, host=host, method="POST", path_qs="/v1/statement",
            headers=loads(capture["headers_json"], []), body=capture["sql_body"],
        )
        self._delete_wire_capture(shim_id)
        self._sync_tls_gateway_safe()
        return {"kind": "proxied", "status": status_code, "headers": resp_headers, "body": resp_body}

    def wire_proxy(
        self, host: str, method: str, path_qs: str, headers: list[tuple[str, str]], body: bytes
    ) -> dict[str, Any]:
        """Forward any other ``/v1/**`` request (e.g. a client polling a
        coordinator-issued nextUri that still resolves to us during the brief
        route-flip window) straight to the cluster's coordinator."""
        cluster = self.cluster_for_host(host)
        if not cluster:
            return {"kind": "no_route"}
        endpoint = self._coordinator_endpoint_for(cluster["id"])
        if not endpoint:
            return {"kind": "no_route"}
        status_code, resp_headers, resp_body = self._forward_to_coordinator(
            endpoint=endpoint, host=host, method=method, path_qs=path_qs, headers=headers, body=body,
        )
        return {"kind": "proxied", "status": status_code, "headers": resp_headers, "body": resp_body}

    def _store_wire_capture(
        self, cluster_id: int, host: str, body: bytes, headers: list[tuple[str, str]]
    ) -> str:
        shim_id = secrets.token_urlsafe(18)
        _, clean_host = self._wire_scheme_host(host)
        with self.conn() as conn:
            conn.execute(
                """
                INSERT INTO wire_pending (shim_id, cluster_id, host, sql_body, headers_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (shim_id, cluster_id, clean_host, body, dumps(self._filter_wire_headers(headers)), utc_now()),
            )
        return shim_id

    def _load_wire_capture(self, shim_id: str) -> dict[str, Any] | None:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM wire_pending WHERE shim_id = ?", (shim_id,)).fetchone()
        return row_to_dict(row) if row else None

    def _delete_wire_capture(self, shim_id: str) -> None:
        with self.conn() as conn:
            conn.execute("DELETE FROM wire_pending WHERE shim_id = ?", (shim_id,))

    def expire_wire_captures(self) -> None:
        """Sweep holding rows past the resume timeout. Captures can hold client
        credentials, so we don't let them linger beyond their useful window."""
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=WIRE_RESUME_TIMEOUT_SECONDS)).isoformat(timespec="seconds")
        with self.conn() as conn:
            conn.execute("DELETE FROM wire_pending WHERE created_at < ?", (cutoff,))

    def refresh_cluster_health(self, cluster_id: int) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            cluster = self.public_cluster(row)
            coordinator = conn.execute(
                """
                SELECT * FROM provider_resources
                WHERE cluster_id = ? AND resource_type = 'coordinator_instance'
                ORDER BY id DESC LIMIT 1
                """,
                (cluster_id,),
            ).fetchone()
            if not coordinator:
                return {
                    "cluster": cluster,
                    "health": {"ok": False, "state": "missing", "detail": "No coordinator instance is tracked."},
                }
            resource = row_to_dict(coordinator)
            endpoint = self.coordinator_endpoint(resource)

        health = self.aws.coordinator_health(coordinator_endpoint=endpoint)
        if health.get("ok") and cluster["status"] != "Running":
            now = utc_now()
            with self.conn() as conn:
                conn.execute("UPDATE clusters SET status = 'Running', updated_at = ? WHERE id = ?", (now, cluster_id))
                conn.execute(
                    """
                    INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                    VALUES (?, 'coordinator_ready', 'Trino coordinator responded to health check.', ?, ?)
                    """,
                    (cluster_id, dumps(health), now),
                )
                updated = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
                cluster = self.public_cluster(updated)
            # The cluster just became Running: flip its gateway route from the
            # resume shim straight to the coordinator so new clients (and any wire
            # query mid-handoff) reach Trino directly.
            self._sync_tls_gateway_safe()
        return {"cluster": cluster, "health": health}

    def poll_starting_clusters_once(self) -> None:
        with self.conn() as conn:
            rows = conn.execute("SELECT id FROM clusters WHERE status = 'Starting' ORDER BY updated_at").fetchall()
            cluster_ids = [int(row["id"]) for row in rows]
        for cluster_id in cluster_ids:
            try:
                self.refresh_cluster_health(cluster_id)
            except Exception:
                continue

    def poll_autoscaling_once(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        now = now or datetime.now(timezone.utc)
        with self.conn() as conn:
            rows = conn.execute(
                """
                SELECT id FROM clusters
                WHERE status = 'Running' AND worker_mode = 'autoscale'
                ORDER BY updated_at
                """
            ).fetchall()
            cluster_ids = [int(row["id"]) for row in rows]

        results: list[dict[str, Any]] = []
        for cluster_id in cluster_ids:
            try:
                results.append(self.autoscale_cluster_once(cluster_id, now=now))
            except Exception as exc:
                results.append({"cluster_id": cluster_id, "action": "error", "error": f"{type(exc).__name__}: {exc}"})
        return results

    def poll_auto_suspend_once(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        now = now or datetime.now(timezone.utc)
        with self.conn() as conn:
            rows = conn.execute(
                """
                SELECT id FROM clusters
                WHERE status = 'Running' AND auto_suspend_minutes IS NOT NULL
                ORDER BY updated_at
                """
            ).fetchall()
            cluster_ids = [int(row["id"]) for row in rows]

        results: list[dict[str, Any]] = []
        for cluster_id in cluster_ids:
            try:
                results.append(self.auto_suspend_cluster_once(cluster_id, now=now))
            except Exception as exc:
                results.append({"cluster_id": cluster_id, "action": "error", "error": f"{type(exc).__name__}: {exc}"})
        # Persisted timer rows are scoped per cluster and reset on
        # start/suspend/delete (delete cascades), so no in-memory sweep is needed.
        return results

    @staticmethod
    def _parse_state_datetime(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None

    def _upsert_timer_state(self, cluster_id: int, **fields: Any) -> None:
        """Persist only the named timer columns for a cluster (UPSERT).

        Other columns are left untouched on conflict, so the autoscaler and
        auto-suspend subsystems can each write their own fields independently.
        """
        columns = ["cluster_id", *fields.keys(), "updated_at"]
        values = [cluster_id, *fields.values(), utc_now()]
        placeholders = ",".join("?" for _ in columns)
        updates = ",".join(f"{name}=excluded.{name}" for name in (*fields.keys(), "updated_at"))
        with self.conn() as conn:
            conn.execute(
                f"INSERT INTO cluster_timer_state ({','.join(columns)}) VALUES ({placeholders}) "
                f"ON CONFLICT(cluster_id) DO UPDATE SET {updates}",
                values,
            )

    def _clear_timer_state(self, cluster_id: int) -> None:
        with self.conn() as conn:
            conn.execute("DELETE FROM cluster_timer_state WHERE cluster_id = ?", (cluster_id,))

    def _load_auto_suspend_state(self, cluster_id: int) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute(
                "SELECT auto_suspend_idle_since FROM cluster_timer_state WHERE cluster_id = ?",
                (cluster_id,),
            ).fetchone()
        idle_since = self._parse_state_datetime(row["auto_suspend_idle_since"]) if row else None
        return {"idle_since": idle_since}

    def _persist_auto_suspend_state(self, cluster_id: int, idle_since: datetime | None) -> None:
        self._upsert_timer_state(
            cluster_id,
            auto_suspend_idle_since=idle_since.isoformat() if isinstance(idle_since, datetime) else None,
        )

    def _load_autoscale_state(self, cluster_id: int) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute(
                """
                SELECT autoscale_queued_intervals, autoscale_cpu_high_intervals, autoscale_idle_low_since
                FROM cluster_timer_state WHERE cluster_id = ?
                """,
                (cluster_id,),
            ).fetchone()
        if not row:
            return {"queued_intervals": 0, "cpu_high_intervals": 0, "idle_low_since": None}
        return {
            "queued_intervals": int(row["autoscale_queued_intervals"] or 0),
            "cpu_high_intervals": int(row["autoscale_cpu_high_intervals"] or 0),
            "idle_low_since": self._parse_state_datetime(row["autoscale_idle_low_since"]),
        }

    def _persist_autoscale_state(self, cluster_id: int, state: dict[str, Any]) -> None:
        idle_low_since = state.get("idle_low_since")
        self._upsert_timer_state(
            cluster_id,
            autoscale_queued_intervals=int(state.get("queued_intervals") or 0),
            autoscale_cpu_high_intervals=int(state.get("cpu_high_intervals") or 0),
            autoscale_idle_low_since=idle_low_since.isoformat() if isinstance(idle_low_since, datetime) else None,
        )

    def auto_suspend_cluster_once(self, cluster_id: int, *, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            cluster = self.public_cluster(row)
            if cluster["status"] != "Running" or cluster["auto_suspend_minutes"] is None:
                self._persist_auto_suspend_state(cluster_id, None)
                return {"cluster_id": cluster_id, "action": "skip", "reason": "Cluster is not a running auto-suspend cluster."}
            if self.in_uptime_window(cluster, now):
                # Keep-warm window: the cluster stays up regardless of idleness.
                self._persist_auto_suspend_state(cluster_id, None)
                return {"cluster_id": cluster_id, "action": "hold", "reason": "Inside a keep-warm uptime window."}
            coordinator = conn.execute(
                """
                SELECT * FROM provider_resources
                WHERE cluster_id = ? AND resource_type = 'coordinator_instance'
                ORDER BY id DESC LIMIT 1
                """,
                (cluster_id,),
            ).fetchone()
            local_active_queries = self.active_query_count(conn, cluster_id)
            if not coordinator:
                self._persist_auto_suspend_state(cluster_id, None)
                return {"cluster_id": cluster_id, "action": "hold", "reason": "Missing coordinator instance."}
            coordinator_endpoint = self.coordinator_endpoint(row_to_dict(coordinator))

        idle_target_seconds = int(cluster["auto_suspend_minutes"]) * 60
        trino_stats = self.aws.trino_cluster_stats(coordinator_endpoint=coordinator_endpoint)
        if not trino_stats.get("ok"):
            self._persist_auto_suspend_state(cluster_id, None)
            return {
                "cluster_id": cluster_id,
                "action": "hold",
                "reason": "Trino cluster stats unavailable.",
                "trino_stats": trino_stats,
            }

        signals = {
            "queued_queries": int(trino_stats.get("queued_queries") or 0),
            "running_queries": int(trino_stats.get("running_queries") or 0),
            "active_workers": int(trino_stats.get("active_workers") or 0),
            "local_active_queries": local_active_queries,
        }
        busy = signals["queued_queries"] > 0 or signals["running_queries"] > 0 or local_active_queries > 0
        state = self._load_auto_suspend_state(cluster_id)
        if busy:
            self._persist_auto_suspend_state(cluster_id, None)
            return {
                "cluster_id": cluster_id,
                "action": "hold",
                "reason": "Cluster still has active or queued query work.",
                "signals": signals,
            }

        idle_since = state.get("idle_since")
        if not isinstance(idle_since, datetime):
            idle_since = now
            self._persist_auto_suspend_state(cluster_id, now)
            idle_seconds = 0
        else:
            idle_seconds = max(0, int((now - idle_since).total_seconds()))

        if idle_seconds < idle_target_seconds:
            return {
                "cluster_id": cluster_id,
                "action": "hold",
                "reason": f"Cluster has been idle for {idle_seconds} of {idle_target_seconds} required seconds.",
                "signals": signals,
            }

        reason = f"Cluster stayed idle for {idle_seconds} seconds; auto-suspend interval is {cluster['auto_suspend_minutes']} minutes."
        with self.conn() as conn:
            conn.execute(
                """
                INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                VALUES (?, 'auto_suspend_started', ?, ?, ?)
                """,
                (cluster_id, reason, dumps({"signals": signals, "idle_seconds": idle_seconds}), now.isoformat(timespec="seconds")),
            )
        suspend_result = self.suspend_cluster(cluster_id)
        self._persist_auto_suspend_state(cluster_id, None)
        return {"cluster_id": cluster_id, "action": "suspend", "reason": reason, "signals": signals, "suspend": suspend_result}

    def active_query_count(self, conn: sqlite3.Connection, cluster_id: int) -> int:
        terminal_statuses = sorted(TERMINAL_QUERY_STATUSES)
        placeholders = ",".join("?" for _ in terminal_statuses)
        row = conn.execute(
            f"SELECT COUNT(*) FROM query_runs WHERE cluster_id = ? AND status NOT IN ({placeholders})",
            (cluster_id, *terminal_statuses),
        ).fetchone()
        return int(row[0])

    def autoscale_cluster_once(self, cluster_id: int, *, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            cluster = self.public_cluster(row)
            if cluster["status"] != "Running" or cluster["worker_mode"] != "autoscale":
                return {"cluster_id": cluster_id, "action": "skip", "reason": "Cluster is not a running autoscale cluster."}
            coordinator = conn.execute(
                """
                SELECT * FROM provider_resources
                WHERE cluster_id = ? AND resource_type = 'coordinator_instance'
                ORDER BY id DESC LIMIT 1
                """,
                (cluster_id,),
            ).fetchone()
            asg_row = conn.execute(
                """
                SELECT * FROM provider_resources
                WHERE cluster_id = ? AND resource_type = 'auto_scaling_group'
                ORDER BY id DESC LIMIT 1
                """,
                (cluster_id,),
            ).fetchone()
            latest_scale = self.latest_scaling_event_at(conn, cluster_id)
            if not coordinator or not asg_row:
                return {"cluster_id": cluster_id, "action": "hold", "reason": "Missing coordinator or worker Auto Scaling Group."}
            coordinator_endpoint = self.coordinator_endpoint(row_to_dict(coordinator))
            asg_resource = row_to_dict(asg_row)

        asg = self.aws.worker_auto_scaling_group(region=cluster["region"], name=asg_resource["resource_id"])
        if not asg.get("found"):
            return {"cluster_id": cluster_id, "action": "hold", "reason": "Worker Auto Scaling Group was not found."}
        trino_stats = self.aws.trino_cluster_stats(coordinator_endpoint=coordinator_endpoint)
        if not trino_stats.get("ok"):
            return {
                "cluster_id": cluster_id,
                "action": "hold",
                "reason": "Trino cluster stats unavailable.",
                "trino_stats": trino_stats,
            }
        cpu_average = self.aws.worker_cpu_average(region=cluster["region"], instance_ids=asg.get("instance_ids", []))
        signals = {
            "desired_capacity": int(asg["desired_capacity"]),
            "min_size": int(asg["min_size"]),
            "max_size": int(asg["max_size"]),
            "in_service_capacity": int(asg["in_service_capacity"]),
            "pending_capacity": int(asg["pending_capacity"]),
            "unhealthy_capacity": int(asg.get("unhealthy_capacity") or 0),
            "instance_ids": asg.get("instance_ids", []),
            "queued_queries": int(trino_stats.get("queued_queries") or 0),
            "running_queries": int(trino_stats.get("running_queries") or 0),
            "active_workers": int(trino_stats.get("active_workers") or 0),
            "avg_worker_cpu": cpu_average,
            "worker_health": trino_stats.get("worker_health") or {},
            "reserved_memory": trino_stats.get("reserved_memory"),
            "memory": trino_stats.get("memory") or {},
        }
        state = self._load_autoscale_state(cluster_id)
        decision = self.autoscaling_decision(cluster, signals, state, latest_scale_at=latest_scale, now=now)
        if decision["action"] == "hold":
            # The decision mutated the interval counters / idle clock; persist them
            # so they survive a restart and keep accumulating toward a threshold.
            self._persist_autoscale_state(cluster_id, state)
            return {"cluster_id": cluster_id, **decision, "signals": signals}

        update = self.aws.set_worker_desired_capacity(
            region=cluster["region"],
            name=asg_resource["resource_id"],
            desired_capacity=int(decision["to_workers"]),
            min_size=int(cluster["min_workers"]),
            max_size=int(cluster["max_workers"]),
        )
        now_text = now.isoformat(timespec="seconds")
        metadata = loads(asg_resource["metadata_json"], {})
        metadata.update(
            {
                "desired_capacity": int(decision["to_workers"]),
                "min_size": int(cluster["min_workers"]),
                "max_size": int(cluster["max_workers"]),
                "last_autoscale": {"reason": decision["reason"], "at": now_text, "signals": signals},
            }
        )
        with self.conn() as conn:
            conn.execute(
                """
                INSERT INTO scaling_events (cluster_id, direction, from_workers, to_workers, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cluster_id,
                    decision["direction"],
                    int(decision["from_workers"]),
                    int(decision["to_workers"]),
                    decision["reason"],
                    now_text,
                ),
            )
            conn.execute(
                """
                INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    cluster_id,
                    f"autoscale_{decision['direction']}",
                    f"Autoscaler changed worker desired capacity from {decision['from_workers']} to {decision['to_workers']}.",
                    dumps({"decision": decision, "signals": signals, "aws": update}),
                    now_text,
                ),
            )
            conn.execute("UPDATE provider_resources SET metadata_json = ? WHERE id = ?", (dumps(metadata), asg_resource["id"]))
        # A scaling action just fired; reset the interval counters / idle clock so
        # the cooldown governs the next move. (The cooldown itself is derived from
        # scaling_events in the DB, so it already survives a restart.)
        state["queued_intervals"] = 0
        state["cpu_high_intervals"] = 0
        state["idle_low_since"] = None
        self._persist_autoscale_state(cluster_id, state)
        return {"cluster_id": cluster_id, **decision, "signals": signals, "aws": update}

    def autoscaling_decision(
        self,
        cluster: dict[str, Any],
        signals: dict[str, Any],
        state: dict[str, Any],
        *,
        latest_scale_at: datetime | None,
        now: datetime,
    ) -> dict[str, Any]:
        queued_queries = int(signals.get("queued_queries") or 0)
        running_queries = int(signals.get("running_queries") or 0)
        desired = int(signals.get("desired_capacity") or 0)
        min_workers = int(cluster["min_workers"])
        max_workers = int(cluster["max_workers"])
        avg_cpu = signals.get("avg_worker_cpu")

        state["queued_intervals"] = int(state.get("queued_intervals") or 0) + 1 if queued_queries > 0 else 0
        high_cpu = avg_cpu is not None and float(avg_cpu) >= AUTOSCALE_CPU_HIGH_THRESHOLD
        state["cpu_high_intervals"] = int(state.get("cpu_high_intervals") or 0) + 1 if high_cpu else 0

        low_idle = (
            queued_queries == 0
            and running_queries == 0
            and avg_cpu is not None
            and float(avg_cpu) < AUTOSCALE_CPU_LOW_THRESHOLD
        )
        if low_idle:
            state["idle_low_since"] = state.get("idle_low_since") or now
        else:
            state["idle_low_since"] = None
        idle_low_since = state.get("idle_low_since")
        idle_low_seconds = (
            max(0, int((now - idle_low_since).total_seconds()))
            if isinstance(idle_low_since, datetime)
            else 0
        )

        cooldown_age = self.seconds_since_latest_scale(latest_scale_at, now)
        if desired < max_workers and state["queued_intervals"] >= AUTOSCALE_QUEUED_SCALE_UP_INTERVALS:
            if cooldown_age is None or cooldown_age >= AUTOSCALE_SCALE_UP_COOLDOWN_SECONDS:
                return {
                    "action": "scale",
                    "direction": "up",
                    "from_workers": desired,
                    "to_workers": min(max_workers, desired + 1),
                    "reason": f"Queued queries persisted for {state['queued_intervals']} autoscale intervals.",
                }
            return {"action": "hold", "reason": "Scale-up cooldown is active."}

        if desired < max_workers and state["cpu_high_intervals"] >= AUTOSCALE_CPU_SCALE_UP_INTERVALS:
            if cooldown_age is None or cooldown_age >= AUTOSCALE_SCALE_UP_COOLDOWN_SECONDS:
                return {
                    "action": "scale",
                    "direction": "up",
                    "from_workers": desired,
                    "to_workers": min(max_workers, desired + 1),
                    "reason": f"Average worker CPU stayed above {AUTOSCALE_CPU_HIGH_THRESHOLD:.0f}% for {state['cpu_high_intervals']} autoscale intervals.",
                }
            return {"action": "hold", "reason": "Scale-up cooldown is active."}

        if desired > min_workers and idle_low_seconds >= AUTOSCALE_IDLE_SCALE_DOWN_SECONDS:
            if cooldown_age is None or cooldown_age >= AUTOSCALE_SCALE_DOWN_COOLDOWN_SECONDS:
                return {
                    "action": "scale",
                    "direction": "down",
                    "from_workers": desired,
                    "to_workers": max(min_workers, desired - 1),
                    "reason": f"Cluster stayed idle with worker CPU below {AUTOSCALE_CPU_LOW_THRESHOLD:.0f}% for {idle_low_seconds} seconds.",
                }
            return {"action": "hold", "reason": "Scale-down cooldown is active."}

        return {"action": "hold", "reason": "Autoscale thresholds were not met."}

    def latest_scaling_event_at(self, conn: sqlite3.Connection, cluster_id: int) -> datetime | None:
        row = conn.execute(
            "SELECT created_at FROM scaling_events WHERE cluster_id = ? ORDER BY created_at DESC LIMIT 1",
            (cluster_id,),
        ).fetchone()
        if not row:
            return None
        try:
            return datetime.fromisoformat(row["created_at"])
        except ValueError:
            return None

    def seconds_since_latest_scale(self, latest_scale_at: datetime | None, now: datetime) -> int | None:
        if latest_scale_at is None:
            return None
        return max(0, int((now - latest_scale_at).total_seconds()))

    def acquire_poller_lock(self) -> bool:
        """Take a host-local advisory lock so only one process runs the poller.

        Returns True if this process won the lock. The file descriptor is kept open
        for the process lifetime; the OS releases the lock automatically on exit.
        """
        import fcntl
        import os

        lock_path = self.db_path.parent / "trinohub-poller.lock"
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        self._poller_lock_fd = lock_fd
        return True

    def start_health_poller(self, interval_seconds: int = AUTOSCALE_INTERVAL_SECONDS) -> None:
        if self._health_poller_started:
            return
        if not self.acquire_poller_lock():
            # Another process already runs the poller. Avoid duplicate autoscalers
            # making conflicting scaling decisions under multi-worker deployments.
            return
        self._health_poller_started = True

        def poll_loop() -> None:
            while True:
                self.poll_starting_clusters_once()
                self.poll_autoscaling_once()
                self.poll_auto_suspend_once()
                # Keep the TLS gateway's upstreams current as coordinators start,
                # get replaced by autoscaling, or suspend.
                self._sync_tls_gateway_safe()
                # Drop any wire-resume captures that have outlived their window.
                try:
                    self.expire_wire_captures()
                except Exception:  # pragma: no cover - defensive
                    pass
                # Fire due scheduled SQL jobs and settle in-flight job runs.
                try:
                    self.poll_scheduled_jobs_once()
                except Exception as exc:  # pragma: no cover - defensive
                    print(f"Scheduled-job poll failed: {type(exc).__name__}: {exc}")
                # Persist a utilization sample per running cluster (charts,
                # Prometheus) and prune samples past retention.
                try:
                    self.sample_cluster_stats_once()
                except Exception as exc:  # pragma: no cover - defensive
                    print(f"Stats sampling failed: {type(exc).__name__}: {exc}")
                time.sleep(interval_seconds)

        thread = threading.Thread(target=poll_loop, name="trinohub-health-poller", daemon=True)
        thread.start()

    def suspend_cluster(self, cluster_id: int) -> dict[str, Any]:
        now = utc_now()
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            cluster = self.public_cluster(row)
            resources = self.resource_rows(conn, cluster_id)
            conn.execute("UPDATE clusters SET status = 'Suspending', updated_at = ? WHERE id = ?", (now, cluster_id))
            conn.execute(
                """
                INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                VALUES (?, 'suspending', 'Suspending cluster and cleaning up tracked runtime resources.', '{}', ?)
                """,
                (cluster_id, now),
            )

        cleanup = self.cleanup_tracked_resources(cluster, resources, strict_security_groups=False)
        fatal_failures = [
            failure for failure in cleanup["failed"] if failure["type"] != "security_group"
        ]
        status = "Failed" if fatal_failures else "Suspended"
        message = (
            "Suspend cleanup failed for one or more runtime resources."
            if fatal_failures
            else "Cluster suspended and tracked runtime resources were cleaned up."
        )
        now = utc_now()
        with self.conn() as conn:
            conn.execute("UPDATE clusters SET status = ?, updated_at = ? WHERE id = ?", (status, now, cluster_id))
            # Drop persisted idle/autoscale timers; the next start begins fresh.
            conn.execute("DELETE FROM cluster_timer_state WHERE cluster_id = ?", (cluster_id,))
            conn.execute("DELETE FROM cluster_bootstrap_tokens WHERE cluster_id = ?", (cluster_id,))
            conn.execute(
                """
                INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (cluster_id, "suspend_cleanup", message, dumps(cleanup), now),
            )
            updated = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
        if fatal_failures:
            raise ApiError(500, message)
        # Coordinator is gone: refresh the gateway's upstreams.
        self._sync_tls_gateway_safe()
        return {"cluster": self.public_cluster(updated), "cleanup": cleanup, "message": message}

    def disable_cluster(self, cluster_id: int) -> dict[str, Any]:
        now = utc_now()
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            cluster = self.public_cluster(row)
            resources = self.resource_rows(conn, cluster_id)
            conn.execute("UPDATE clusters SET status = 'Suspending', updated_at = ? WHERE id = ?", (now, cluster_id))
            conn.execute(
                """
                INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                VALUES (?, 'disabling', 'Disabling cluster and cleaning up tracked runtime resources.', '{}', ?)
                """,
                (cluster_id, now),
            )

        cleanup = self.cleanup_tracked_resources(cluster, resources, strict_security_groups=False)
        fatal_failures = [failure for failure in cleanup["failed"] if failure["type"] != "security_group"]
        status = "Failed" if fatal_failures else "Not enabled"
        message = (
            "Disable cleanup failed for one or more runtime resources."
            if fatal_failures
            else "Cluster disabled and tracked runtime resources were cleaned up."
        )
        now = utc_now()
        with self.conn() as conn:
            conn.execute("UPDATE clusters SET status = ?, updated_at = ? WHERE id = ?", (status, now, cluster_id))
            conn.execute("DELETE FROM cluster_timer_state WHERE cluster_id = ?", (cluster_id,))
            conn.execute("DELETE FROM cluster_bootstrap_tokens WHERE cluster_id = ?", (cluster_id,))
            conn.execute(
                """
                INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                VALUES (?, 'disable_cleanup', ?, ?, ?)
                """,
                (cluster_id, message, dumps(cleanup), now),
            )
            updated = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
        if fatal_failures:
            raise ApiError(500, message)
        # Coordinator is gone: refresh the gateway's upstreams.
        self._sync_tls_gateway_safe()
        return {"cluster": self.public_cluster(updated), "cleanup": cleanup, "message": message}

    def delete_cluster(self, cluster_id: int, actor: dict[str, Any] | None = None) -> dict[str, Any]:
        now = utc_now()
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            cluster = self.public_cluster(row)
            resources = self.resource_rows(conn, cluster_id)
            conn.execute("UPDATE clusters SET status = 'Deleting', updated_at = ? WHERE id = ?", (now, cluster_id))
            conn.execute(
                """
                INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                VALUES (?, 'deleting', 'Deleting cluster and all tracked TrinoHub resources.', '{}', ?)
                """,
                (cluster_id, now),
            )

        cleanup = self.cleanup_tracked_resources(cluster, resources, strict_security_groups=True)
        if cleanup["failed"]:
            now = utc_now()
            with self.conn() as conn:
                conn.execute("UPDATE clusters SET status = 'Failed', updated_at = ? WHERE id = ?", (now, cluster_id))
                conn.execute("DELETE FROM cluster_bootstrap_tokens WHERE cluster_id = ?", (cluster_id,))
                conn.execute(
                    """
                    INSERT INTO cluster_events (cluster_id, event_type, message, metadata_json, created_at)
                    VALUES (?, 'delete_failed', 'Delete cleanup failed for one or more tracked resources.', ?, ?)
                    """,
                    (cluster_id, dumps(cleanup), now),
                )
            raise ApiError(500, "Delete cleanup failed for one or more tracked resources.")

        with self.conn() as conn:
            conn.execute("DELETE FROM clusters WHERE id = ?", (cluster_id,))
        # Cluster is gone: remove its hostname from the gateway.
        self._sync_tls_gateway_safe()
        self.audit(actor, "cluster.delete", cluster["name"])
        return {"deleted": True, "cluster": cluster, "cleanup": cleanup}

    def list_catalogs(self) -> dict[str, Any]:
        with self.conn() as conn:
            rows = conn.execute("SELECT * FROM catalogs ORDER BY name").fetchall()
            return {"catalogs": [self.public_catalog(row) for row in rows]}

    def list_connector_types(self) -> dict[str, Any]:
        # Registry-derived form schema for the Add-Catalog UI. The browser builds
        # its connector picker + form from this instead of hand-maintaining a
        # parallel copy of every type.
        return {"connector_types": connector_types_catalog()}

    def public_catalog(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "config": loads(row["config_json"], {}),
            "enabled": bool(row["enabled"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def create_catalog(self, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip()
        catalog_type = str(payload.get("type", "s3_glue"))
        if not CATALOG_NAME_PATTERN.fullmatch(name):
            raise ApiError(400, "catalog name must be lowercase letters, numbers, or underscores.")
        if name in BUILT_IN_CATALOG_NAMES:
            raise ApiError(400, "built-in catalog names cannot be reused.")
        config = self.normalize_catalog_config(catalog_type, payload.get("config", {}))
        now = utc_now()
        with self.conn() as conn:
            if conn.execute("SELECT 1 FROM catalogs WHERE name = ?", (name,)).fetchone():
                raise ApiError(400, f"A catalog named {name} already exists.")
            # Store the credential only after the name is known to be free, so a
            # rejected create never leaves an orphaned secret behind.
            if catalog_type in CREDENTIALED_CATALOG_TYPES:
                config["password_secret_ref"] = self.store_catalog_password(
                    name, catalog_type, payload.get("password")
                )
            elif catalog_type in OPTIONAL_SECRET_CATALOG_TYPES and config.get("connection_user"):
                # Optional auth: a username was supplied, so a password is required
                # and stored. Without a username the catalog is unauthenticated and
                # keeps no secret.
                config["password_secret_ref"] = self.store_catalog_password(
                    name, catalog_type, payload.get("password")
                )
            cursor = conn.execute(
                """
                INSERT INTO catalogs (name, type, config_json, enabled, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (name, catalog_type, dumps(config), now, now),
            )
            row = conn.execute("SELECT * FROM catalogs WHERE id = ?", (cursor.lastrowid,)).fetchone()
            result = {"catalog": self.public_catalog(row)}
        self.audit(actor, "catalog.create", name, {"type": catalog_type})
        return result

    def check_catalog(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip()
        catalog_type = str(payload.get("type", "s3_glue"))
        if not CATALOG_NAME_PATTERN.fullmatch(name):
            raise ApiError(400, "catalog name must be lowercase letters, numbers, or underscores.")
        if name in BUILT_IN_CATALOG_NAMES:
            raise ApiError(400, "Use the built-in catalog directly; only custom catalogs need checking.")
        config = self.normalize_catalog_config(catalog_type, payload.get("config", {}))

        cluster_id = payload.get("cluster_id")
        checked_cluster: dict[str, Any] | None = None
        with self.conn() as conn:
            if cluster_id:
                try:
                    normalized_cluster_id = int(cluster_id)
                except (TypeError, ValueError):
                    raise ApiError(400, "cluster_id must be an integer.") from None
                row = conn.execute("SELECT * FROM clusters WHERE id = ?", (normalized_cluster_id,)).fetchone()
                checked_cluster = self.public_cluster(row) if row else None
            else:
                rows = conn.execute("SELECT * FROM clusters WHERE status = 'Running' ORDER BY updated_at DESC").fetchall()
                for row in rows:
                    candidate = self.public_cluster(row)
                    if name in candidate["catalogs"]:
                        checked_cluster = candidate
                        break

        result: dict[str, Any] = {
            "ok": True,
            "config": config,
            "live_check": {
                "checked": False,
                "reason": "No running cluster with this catalog attached.",
            },
        }
        if not checked_cluster:
            return result
        if checked_cluster["status"] != "Running":
            result["live_check"] = {
                "checked": False,
                "cluster_id": checked_cluster["id"],
                "reason": f"Cluster is {checked_cluster['status']}, not Running.",
            }
            return result
        if name not in checked_cluster["catalogs"]:
            result["live_check"] = {
                "checked": False,
                "cluster_id": checked_cluster["id"],
                "reason": "The selected cluster does not have this catalog attached.",
            }
            return result

        query = self.create_query(
            {
                "cluster_id": checked_cluster["id"],
                "catalog": name,
                "sql": f"SHOW SCHEMAS FROM {name}",
            },
            user,
        )["query"]
        result["live_check"] = {
            "checked": True,
            "cluster_id": checked_cluster["id"],
            "query_id": query["id"],
            "status": query["status"],
            "ok": query["status"] == "Finished",
            "error_message": query["error_message"],
            "row_count": query["row_count"],
        }
        result["ok"] = bool(result["live_check"]["ok"])
        return result

    def update_catalog(self, catalog_id: int, payload: dict[str, Any], actor: dict[str, Any] | None = None) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM catalogs WHERE id = ?", (catalog_id,)).fetchone()
            if not row:
                raise ApiError(404, "Catalog not found.")
            catalog = self.public_catalog(row)
            if catalog["type"] == "builtin":
                raise ApiError(400, "Built-in catalogs cannot be edited.")

            name = str(payload.get("name", catalog["name"])).strip()
            if name != catalog["name"]:
                if not CATALOG_NAME_PATTERN.fullmatch(name):
                    raise ApiError(400, "catalog name must be lowercase letters, numbers, or underscores.")
                if name in BUILT_IN_CATALOG_NAMES:
                    raise ApiError(400, "built-in catalog names cannot be reused.")
                self.require_catalog_not_attached(conn, catalog["name"])
            catalog_type = str(payload.get("type", catalog["type"]))
            config = self.normalize_catalog_config(catalog_type, payload.get("config", catalog["config"]))
            old_ref = catalog["config"].get("password_secret_ref")
            if catalog_type in CREDENTIALED_CATALOG_TYPES:
                password = payload.get("password")
                if isinstance(password, str) and password:
                    config["password_secret_ref"] = self.store_catalog_password(name, catalog_type, password)
                elif old_ref:
                    config["password_secret_ref"] = old_ref
                else:
                    raise ApiError(400, f"{catalog_type} catalogs require a password.")
            elif catalog_type in OPTIONAL_SECRET_CATALOG_TYPES and config.get("connection_user"):
                # Optional auth with a username set: reuse the stored secret unless a
                # new password was supplied. Dropping the username (handled below via
                # the unreferenced-secret cleanup) removes the credential entirely.
                password = payload.get("password")
                if isinstance(password, str) and password:
                    config["password_secret_ref"] = self.store_catalog_password(name, catalog_type, password)
                elif old_ref:
                    config["password_secret_ref"] = old_ref
                else:
                    raise ApiError(400, f"{catalog_type} catalogs with a connection_user require a password.")
            # Clean up a credential that is no longer referenced (type changed away,
            # or the secret moved under a renamed catalog).
            new_ref = config.get("password_secret_ref")
            if old_ref and old_ref != new_ref:
                try:
                    self.secret_store.delete(old_ref)
                except SecretStoreError:
                    pass
            enabled = 1 if bool(payload.get("enabled", catalog["enabled"])) else 0
            now = utc_now()
            conn.execute(
                """
                UPDATE catalogs
                SET name = ?, type = ?, config_json = ?, enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (name, catalog_type, dumps(config), enabled, now, catalog_id),
            )
            updated = conn.execute("SELECT * FROM catalogs WHERE id = ?", (catalog_id,)).fetchone()
            result = {"catalog": self.public_catalog(updated)}
        self.audit(actor, "catalog.update", name, {"type": catalog_type})
        return result

    def delete_catalog(self, catalog_id: int, actor: dict[str, Any] | None = None) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM catalogs WHERE id = ?", (catalog_id,)).fetchone()
            if not row:
                raise ApiError(404, "Catalog not found.")
            catalog = self.public_catalog(row)
            if catalog["type"] == "builtin":
                raise ApiError(400, "Built-in catalogs cannot be deleted.")
            self.require_catalog_not_attached(conn, catalog["name"])
            conn.execute("DELETE FROM catalogs WHERE id = ?", (catalog_id,))
            ref = catalog["config"].get("password_secret_ref")
            if ref:
                try:
                    self.secret_store.delete(ref)
                except SecretStoreError:
                    pass
        self.audit(actor, "catalog.delete", catalog["name"])
        return {"deleted": True, "catalog": catalog}

    # ---- Connector driver JARs -------------------------------------------------
    # Some connectors (Oracle) ship without a bundled JDBC driver. An admin
    # uploads the JAR once; it is held on the control-plane disk and every node
    # fetches it (SHA-256 verified) into the Trino plugin dir at boot.

    def drivers_dir(self) -> Path:
        path = self.db_path.parent / "drivers"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def public_driver(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        return {
            "connector_type": row["connector_type"],
            "filename": row["filename"],
            "sha256": row["sha256"],
            "size_bytes": row["size_bytes"],
            "uploaded_by": row["uploaded_by"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_connector_drivers(self) -> dict[str, Any]:
        with self.conn() as conn:
            rows = conn.execute("SELECT * FROM connector_drivers ORDER BY connector_type").fetchall()
        return {"drivers": [self.public_driver(row) for row in rows]}

    def connector_driver(self, connector_type: str) -> dict[str, Any] | None:
        with self.conn() as conn:
            row = conn.execute(
                "SELECT * FROM connector_drivers WHERE connector_type = ?", (connector_type,)
            ).fetchone()
        return self.public_driver(row) if row else None

    def store_connector_driver(self, connector_type: str, filename: str, data: bytes, user: dict[str, Any]) -> dict[str, Any]:
        if connector_type not in DRIVER_REQUIRED_TYPES:
            raise ApiError(400, f"{connector_type} does not require an uploaded driver.")
        if not isinstance(data, (bytes, bytearray)) or not data:
            raise ApiError(400, "Driver file is empty.")
        if len(data) > MAX_DRIVER_UPLOAD_BYTES:
            raise ApiError(400, f"Driver exceeds the {MAX_DRIVER_UPLOAD_BYTES // (1024 * 1024)} MB limit.")
        # JARs are ZIP archives; reject anything that isn't one before it lands on
        # a node classpath. (PK\x03\x04 = local file header; PK\x05\x06 = empty zip.)
        if data[:4] not in (b"PK\x03\x04", b"PK\x05\x06"):
            raise ApiError(400, "Driver must be a .jar file.")
        safe_name = os.path.basename(str(filename)).strip() or f"{connector_type}-driver.jar"
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}\.jar", safe_name):
            raise ApiError(400, "Driver filename must be a simple *.jar name.")
        sha256 = hashlib.sha256(data).hexdigest()
        now = utc_now()
        # Store on disk under a per-connector name; the DB row is the source of
        # truth for the current filename/hash.
        target = self.drivers_dir() / f"{connector_type}.jar"
        tmp = target.with_suffix(".jar.tmp")
        tmp.write_bytes(data)
        tmp.replace(target)
        with self.conn() as conn:
            conn.execute(
                """
                INSERT INTO connector_drivers (connector_type, filename, sha256, size_bytes, uploaded_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(connector_type) DO UPDATE SET
                    filename = excluded.filename,
                    sha256 = excluded.sha256,
                    size_bytes = excluded.size_bytes,
                    uploaded_by = excluded.uploaded_by,
                    updated_at = excluded.updated_at
                """,
                (connector_type, safe_name, sha256, len(data), user.get("username"), now, now),
            )
            row = conn.execute(
                "SELECT * FROM connector_drivers WHERE connector_type = ?", (connector_type,)
            ).fetchone()
        return {"driver": self.public_driver(row)}

    def delete_connector_driver(self, connector_type: str) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute(
                "SELECT * FROM connector_drivers WHERE connector_type = ?", (connector_type,)
            ).fetchone()
            if not row:
                raise ApiError(404, "No driver uploaded for that connector.")
            driver = self.public_driver(row)
            conn.execute("DELETE FROM connector_drivers WHERE connector_type = ?", (connector_type,))
        try:
            (self.drivers_dir() / f"{connector_type}.jar").unlink(missing_ok=True)
        except OSError:
            pass
        return {"deleted": True, "driver": driver}

    def node_driver_file(self, cluster_id: int, connector_type: str, token: str) -> tuple[Path, str]:
        """Resolve an uploaded driver JAR for a node, authorized by the cluster's
        bootstrap token and gated on the connector actually being attached."""
        with self.conn() as conn:
            self.verify_cluster_bootstrap_token(conn, cluster_id, token)
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            cluster = self.public_cluster(row)
            attached_types = {
                cat["type"] for cat in self.catalog_configs_for_cluster(conn, cluster["catalogs"])
            }
            if connector_type not in attached_types:
                raise ApiError(404, "That connector is not attached to this cluster.")
            driver = conn.execute(
                "SELECT * FROM connector_drivers WHERE connector_type = ?", (connector_type,)
            ).fetchone()
        if not driver:
            raise ApiError(404, "No driver uploaded for that connector.")
        path = self.drivers_dir() / f"{connector_type}.jar"
        if not path.exists():
            raise ApiError(404, "Driver file is missing on the control plane.")
        return path, driver["filename"]

    def catalog_driver_descriptors(self, conn: sqlite3.Connection, catalog_configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Driver-install descriptors for attached catalogs, raising if a
        driver-required connector has no uploaded JAR (so a node never boots
        Trino with a missing driver)."""
        descriptors: list[dict[str, Any]] = []
        seen: set[str] = set()
        for catalog in catalog_configs:
            catalog_type = catalog.get("type")
            spec = REGISTRY.get(catalog_type)
            if not spec or not spec.requires_driver or catalog_type in seen:
                continue
            seen.add(catalog_type)
            row = conn.execute(
                "SELECT * FROM connector_drivers WHERE connector_type = ?", (catalog_type,)
            ).fetchone()
            if not row:
                raise ApiError(
                    400,
                    f"The {spec.label} connector needs its JDBC driver uploaded before a "
                    f"cluster using catalog '{catalog.get('name')}' can start.",
                )
            descriptors.append(
                {
                    "connector_type": catalog_type,
                    "plugin_dir": spec.plugin_dir or catalog_type,
                    "filename": row["filename"],
                    "sha256": row["sha256"],
                }
            )
        return descriptors

    def normalize_catalog_config(self, catalog_type: str, raw_config: Any) -> dict[str, Any]:
        spec = REGISTRY.get(catalog_type)
        if spec is None:
            raise ApiError(400, f"Unsupported catalog type: {catalog_type}.")
        if spec.kind == "s3_glue":
            return self.normalize_glue_catalog_config(spec, raw_config)
        # JDBC and MongoDB share the connection-URL + user + password shape.
        if spec.kind in ("jdbc", "mongodb"):
            return self.normalize_jdbc_catalog_config(spec, raw_config)
        if spec.kind == "elasticsearch":
            return self.normalize_elasticsearch_catalog_config(spec, raw_config)
        if spec.kind == "bigquery":
            return self.normalize_bigquery_catalog_config(raw_config)
        if spec.kind == "gsheets":
            return self.normalize_gsheets_catalog_config(raw_config)
        if spec.kind == "cassandra":
            return self.normalize_cassandra_catalog_config(spec, raw_config)
        if spec.kind == "prometheus":
            return self.normalize_prometheus_catalog_config(spec, raw_config)
        if spec.kind == "generator":
            return self.normalize_generator_catalog_config(spec, raw_config)
        raise ApiError(400, f"Unsupported catalog type: {catalog_type}.")

    def store_catalog_password(self, name: str, catalog_type: str, password: Any) -> str:
        spec = REGISTRY.get(catalog_type)
        credential_kind = spec.credential_kind if spec else "password"
        if not isinstance(password, str) or not password:
            noun = "service-account key" if credential_kind == "gcp_service_account" else "password"
            raise ApiError(400, f"{catalog_type} catalogs require a non-empty {noun}.")
        if credential_kind == "gcp_service_account":
            self.validate_gcp_service_account_key(password)
        try:
            return self.secret_store.put(name, password)
        except SecretStoreError as exc:
            raise ApiError(400, str(exc)) from exc

    def validate_gcp_service_account_key(self, raw: str) -> None:
        """Reject anything that isn't a GCP service-account JSON key before it is
        stored — catching a paste error here beats a cryptic Trino boot failure."""
        try:
            doc = json.loads(raw)
        except (ValueError, TypeError):
            raise ApiError(400, "BigQuery credentials must be the service-account JSON key.") from None
        if not isinstance(doc, dict) or doc.get("type") != "service_account":
            raise ApiError(400, 'BigQuery credentials must be a service-account key ("type": "service_account").')
        for field in ("private_key", "client_email", "project_id"):
            if not doc.get(field):
                raise ApiError(400, f"Service-account key is missing required field '{field}'.")

    def reject_ssrf_host(self, host: str) -> None:
        """Block credential URLs that point at loopback or cloud-metadata endpoints."""
        if host.lower() in {"localhost", "metadata.google.internal"}:
            raise ApiError(400, "connection_url host is not allowed.")
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return  # A hostname, not an IP literal — allowed (e.g. an RDS endpoint).
        if ip.is_loopback or ip.is_link_local:
            raise ApiError(400, "connection_url host is not allowed.")

    def normalize_jdbc_catalog_config(self, spec: ConnectorType, raw_config: Any) -> dict[str, Any]:
        if not isinstance(raw_config, dict):
            raise ApiError(400, "catalog config must be an object.")
        for key in raw_config:
            lowered = str(key).lower()
            if "secret" in lowered or "password" in lowered or "access_key" in lowered or "access-key" in lowered:
                raise ApiError(400, "Do not store passwords or secrets in catalog config; use the password field.")
        connection_url = str(raw_config.get("connection_url", "")).strip()
        connection_user = str(raw_config.get("connection_user", "")).strip()
        match = spec.url_pattern.fullmatch(connection_url)
        if not match:
            raise ApiError(400, f"connection_url must be a {spec.url_help} URL.")
        self.reject_ssrf_host(match.group(1))
        if not JDBC_USER_PATTERN.fullmatch(connection_user):
            raise ApiError(400, "connection_user must be a valid database username.")
        return {
            "connector_name": spec.connector_name,
            "connection_url": connection_url,
            "connection_user": connection_user,
        }

    def normalize_elasticsearch_catalog_config(self, spec: ConnectorType, raw_config: Any) -> dict[str, Any]:
        # Shared by Elasticsearch and its OpenSearch fork — identical config, only
        # the connector.name and property prefix differ (both taken from the spec).
        if not isinstance(raw_config, dict):
            raise ApiError(400, "catalog config must be an object.")
        for key in raw_config:
            lowered = str(key).lower()
            if "secret" in lowered or "password" in lowered or "access_key" in lowered or "access-key" in lowered:
                raise ApiError(400, "Do not store passwords or secrets in catalog config; use the password field.")
        host = str(raw_config.get("host", "")).strip()
        port = str(raw_config.get("port") or "9200").strip()
        connection_user = str(raw_config.get("connection_user", "")).strip()
        default_schema = str(raw_config.get("default_schema") or "default").strip()
        if not HOST_NAME_PATTERN.fullmatch(host):
            raise ApiError(400, "host must be a valid hostname or IP address.")
        self.reject_ssrf_host(host)
        if not port.isdigit() or not (1 <= int(port) <= 65535):
            raise ApiError(400, "port must be between 1 and 65535.")
        if not JDBC_USER_PATTERN.fullmatch(connection_user):
            raise ApiError(400, "connection_user must be a valid username.")
        if not SCHEMA_NAME_PATTERN.fullmatch(default_schema):
            raise ApiError(400, "default_schema must be alphanumeric or underscore characters.")
        return {
            "connector_name": spec.connector_name,
            "host": host,
            "port": int(port),
            "connection_user": connection_user,
            "default_schema": default_schema,
        }

    def normalize_cassandra_catalog_config(self, spec: ConnectorType, raw_config: Any) -> dict[str, Any]:
        # Cassandra: one or more contact points (comma-separated hosts/IPs), a
        # native-protocol port, and OPTIONAL auth. A username is only kept when
        # given; the password (required alongside a username) is routed through the
        # secret path by create/update, never stored here.
        if not isinstance(raw_config, dict):
            raise ApiError(400, "catalog config must be an object.")
        for key in raw_config:
            lowered = str(key).lower()
            if "secret" in lowered or "password" in lowered or "access_key" in lowered or "access-key" in lowered:
                raise ApiError(400, "Do not store passwords or secrets in catalog config; use the password field.")
        raw_points = str(raw_config.get("contact_points", "")).strip()
        hosts = [h.strip() for h in raw_points.split(",") if h.strip()]
        if not hosts:
            raise ApiError(400, "contact_points must list at least one Cassandra node host.")
        for host in hosts:
            if not HOST_NAME_PATTERN.fullmatch(host):
                raise ApiError(400, "each contact point must be a valid hostname or IP address.")
            self.reject_ssrf_host(host)
        port = str(raw_config.get("port") or "9042").strip()
        if not port.isdigit() or not (1 <= int(port) <= 65535):
            raise ApiError(400, "port must be between 1 and 65535.")
        config: dict[str, Any] = {
            "connector_name": spec.connector_name,
            "contact_points": ",".join(hosts),
            "port": int(port),
        }
        connection_user = str(raw_config.get("connection_user") or "").strip()
        if connection_user:
            if not JDBC_USER_PATTERN.fullmatch(connection_user):
                raise ApiError(400, "connection_user must be a valid username.")
            config["connection_user"] = connection_user
        return config

    def normalize_prometheus_catalog_config(self, spec: ConnectorType, raw_config: Any) -> dict[str, Any]:
        # Prometheus: a single HTTP(S) endpoint URL and OPTIONAL basic auth. Like
        # Cassandra, a username (if given) requires a password, routed through the
        # secret path by create/update and never stored here.
        if not isinstance(raw_config, dict):
            raise ApiError(400, "catalog config must be an object.")
        for key in raw_config:
            lowered = str(key).lower()
            if "secret" in lowered or "password" in lowered or "access_key" in lowered or "access-key" in lowered:
                raise ApiError(400, "Do not store passwords or secrets in catalog config; use the password field.")
        uri = str(raw_config.get("uri", "")).strip()
        match = re.fullmatch(r"https?://([^/:?\s]+)(?::\d+)?(?:/\S*)?", uri)
        if not match:
            raise ApiError(400, "uri must be an http:// or https:// Prometheus URL (e.g. http://prometheus.internal:9090).")
        self.reject_ssrf_host(match.group(1))
        config: dict[str, Any] = {"connector_name": spec.connector_name, "uri": uri}
        connection_user = str(raw_config.get("connection_user") or "").strip()
        if connection_user:
            if not JDBC_USER_PATTERN.fullmatch(connection_user):
                raise ApiError(400, "connection_user must be a valid username.")
            config["connection_user"] = connection_user
        return config

    def normalize_generator_catalog_config(self, spec: ConnectorType, raw_config: Any) -> dict[str, Any]:
        # memory / blackhole / faker take no configuration. Accept an empty object
        # (or none) and reject any stray keys so a typo can't be silently ignored.
        if raw_config in (None, {}):
            return {"connector_name": spec.connector_name}
        if not isinstance(raw_config, dict):
            raise ApiError(400, "catalog config must be an object.")
        extra = [k for k in raw_config if str(k) != "connector_name"]
        if extra:
            raise ApiError(400, f"The {spec.label} connector takes no configuration.")
        return {"connector_name": spec.connector_name}

    def normalize_gsheets_catalog_config(self, raw_config: Any) -> dict[str, Any]:
        if not isinstance(raw_config, dict):
            raise ApiError(400, "catalog config must be an object.")
        for key in raw_config:
            lowered = str(key).lower()
            if "secret" in lowered or "password" in lowered or "credential" in lowered or "private_key" in lowered:
                raise ApiError(400, "Do not store the service-account key in catalog config; use the credentials field.")
        metadata_sheet_id = str(raw_config.get("metadata_sheet_id", "")).strip()
        if not GSHEET_ID_PATTERN.fullmatch(metadata_sheet_id):
            raise ApiError(400, "metadata_sheet_id must be a Google Sheets spreadsheet ID.")
        return {"connector_name": "gsheets", "metadata_sheet_id": metadata_sheet_id}

    def normalize_bigquery_catalog_config(self, raw_config: Any) -> dict[str, Any]:
        if not isinstance(raw_config, dict):
            raise ApiError(400, "catalog config must be an object.")
        for key in raw_config:
            lowered = str(key).lower()
            if "secret" in lowered or "password" in lowered or "credential" in lowered or "private_key" in lowered:
                raise ApiError(400, "Do not store the service-account key in catalog config; use the credentials field.")
        project_id = str(raw_config.get("project_id", "")).strip()
        parent_project_id = str(raw_config.get("parent_project_id") or "").strip()
        if not GCP_PROJECT_PATTERN.fullmatch(project_id):
            raise ApiError(400, "project_id must be a valid GCP project ID (e.g. my-analytics-project).")
        config = {"connector_name": "bigquery", "project_id": project_id}
        # parent_project_id is optional: the project that holds the datasets, when
        # different from the billing project. Omitted -> BigQuery uses project_id.
        if parent_project_id:
            if not GCP_PROJECT_PATTERN.fullmatch(parent_project_id):
                raise ApiError(400, "parent_project_id must be a valid GCP project ID.")
            config["parent_project_id"] = parent_project_id
        return config

    def normalize_glue_catalog_config(self, spec: ConnectorType, raw_config: Any) -> dict[str, Any]:
        # Shared validator for the S3/Glue family (Iceberg / Delta Lake / Hive).
        # They differ only in the rendered connector.name + security key; the config
        # surface (Glue region, S3 warehouse, access mode) is identical. The table
        # format is fixed by the catalog type, not accepted from the client.
        if not isinstance(raw_config, dict):
            raise ApiError(400, "catalog config must be an object.")
        for key in raw_config:
            lowered = str(key).lower()
            if "secret" in lowered or "access_key" in lowered or "access-key" in lowered:
                raise ApiError(400, "Do not store AWS access keys or secrets in TrinoHub catalog configuration.")

        glue_region = str(raw_config.get("glue_region", "")).strip()
        s3_region = str(raw_config.get("s3_region") or glue_region).strip()
        warehouse = str(raw_config.get("warehouse", "")).strip()
        default_schema = str(raw_config.get("default_schema") or "default").strip()
        file_format = str(raw_config.get("file_format") or "PARQUET").strip().upper()
        access_mode = str(raw_config.get("access_mode") or "read_write").strip()

        if not AWS_REGION_PATTERN.fullmatch(glue_region):
            raise ApiError(400, "glue_region must be an AWS region such as us-east-2.")
        if not AWS_REGION_PATTERN.fullmatch(s3_region):
            raise ApiError(400, "s3_region must be an AWS region such as us-east-2.")
        if not S3_WAREHOUSE_PATTERN.fullmatch(warehouse):
            raise ApiError(400, "warehouse must be an s3:// bucket path.")
        if not warehouse.endswith("/"):
            warehouse = f"{warehouse}/"
        if not SCHEMA_NAME_PATTERN.fullmatch(default_schema):
            raise ApiError(400, "default_schema must be alphanumeric or underscore characters.")
        if file_format not in {"PARQUET", "ORC", "AVRO"}:
            raise ApiError(400, "file_format must be PARQUET, ORC, or AVRO.")
        if access_mode not in {"read_write", "read_only"}:
            raise ApiError(400, "access_mode must be read_write or read_only.")

        return {
            "glue_region": glue_region,
            "s3_region": s3_region,
            "warehouse": warehouse,
            "default_schema": default_schema,
            "table_format": spec.table_format,
            "file_format": file_format,
            "access_mode": access_mode,
        }

    def require_known_catalogs(self, conn: sqlite3.Connection, catalog_names: list[str]) -> None:
        configured = {row["name"]: row for row in self.catalog_rows_by_name(conn, catalog_names).values()}
        missing = [name for name in catalog_names if name not in configured and name not in BUILT_IN_CATALOG_NAMES]
        disabled = [name for name in catalog_names if name in configured and not bool(configured[name]["enabled"])]
        if missing:
            raise ApiError(400, f"Unknown catalog: {', '.join(missing)}.")
        if disabled:
            raise ApiError(400, f"Disabled catalog: {', '.join(disabled)}.")

    def catalog_configs_for_cluster(self, conn: sqlite3.Connection, catalog_names: list[str]) -> list[dict[str, Any]]:
        self.require_known_catalogs(conn, catalog_names)
        custom_names = [name for name in catalog_names if name not in BUILT_IN_CATALOG_NAMES]
        catalogs_by_name = {
            name: self.public_catalog(row)
            for name, row in self.catalog_rows_by_name(conn, custom_names).items()
        }
        return [catalogs_by_name[name] for name in custom_names]

    def catalog_rows_by_name(self, conn: sqlite3.Connection, catalog_names: list[str]) -> dict[str, sqlite3.Row]:
        if not catalog_names:
            return {}
        placeholders = ",".join("?" for _ in catalog_names)
        rows = conn.execute(f"SELECT * FROM catalogs WHERE name IN ({placeholders})", catalog_names).fetchall()
        return {row["name"]: row for row in rows}

    def require_catalog_not_attached(self, conn: sqlite3.Connection, catalog_name: str) -> None:
        attached_clusters = []
        rows = conn.execute("SELECT name, catalogs_json FROM clusters ORDER BY name").fetchall()
        for row in rows:
            if catalog_name in loads(row["catalogs_json"], []):
                attached_clusters.append(row["name"])
        if attached_clusters:
            raise ApiError(409, f"Catalog is attached to cluster(s): {', '.join(attached_clusters)}.")

    def list_query_tabs(self, user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            rows = conn.execute(
                "SELECT * FROM query_tabs WHERE user_id = ? ORDER BY position, id",
                (user["id"],),
            ).fetchall()
            if not rows:
                self.create_default_query_tab(conn, user)
            self.ensure_active_query_tab(conn, user["id"])
            rows = conn.execute(
                "SELECT * FROM query_tabs WHERE user_id = ? ORDER BY position, id",
                (user["id"],),
            ).fetchall()
            return {"tabs": [self.public_query_tab(row) for row in rows]}

    def create_query_tab(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            count = int(
                conn.execute("SELECT COUNT(*) FROM query_tabs WHERE user_id = ?", (user["id"],)).fetchone()[0]
            )
            position = self.next_query_tab_position(conn, user["id"])
            name = self.normalize_query_tab_name(payload.get("name") or f"query-{position + 1}.sql")
            sql_text = str(payload.get("sql", payload.get("sql_text", "")))
            cluster_id = self.normalize_query_tab_cluster_id(conn, payload.get("cluster_id"))
            catalog = self.normalize_query_tab_catalog(payload.get("catalog", "tpch" if not count else ""))
            schema_name = self.normalize_query_tab_schema(
                payload.get("schema", payload.get("schema_name", "sf1" if not count else ""))
            )
            run_mode = self.normalize_query_tab_run_mode(payload.get("run_mode", "current"))
            is_active = 1 if bool(payload.get("is_active", count == 0)) else 0
            if is_active:
                conn.execute("UPDATE query_tabs SET is_active = 0 WHERE user_id = ?", (user["id"],))
            now = utc_now()
            cursor = conn.execute(
                """
                INSERT INTO query_tabs
                  (user_id, name, sql_text, cluster_id, catalog, schema_name, run_mode, position, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user["id"], name, sql_text, cluster_id, catalog, schema_name, run_mode, position, is_active, now, now),
            )
            self.ensure_active_query_tab(conn, user["id"])
            row = conn.execute("SELECT * FROM query_tabs WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return {"tab": self.public_query_tab(row)}

    def update_query_tab(self, tab_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            row = self.query_tab_for_user(conn, tab_id, user)
            updates: dict[str, Any] = {}
            if "name" in payload:
                updates["name"] = self.normalize_query_tab_name(payload["name"])
            if "sql" in payload:
                updates["sql_text"] = str(payload["sql"])
            elif "sql_text" in payload:
                updates["sql_text"] = str(payload["sql_text"])
            if "cluster_id" in payload:
                updates["cluster_id"] = self.normalize_query_tab_cluster_id(conn, payload.get("cluster_id"))
            if "catalog" in payload:
                updates["catalog"] = self.normalize_query_tab_catalog(payload.get("catalog", ""))
            if "schema" in payload:
                updates["schema_name"] = self.normalize_query_tab_schema(payload.get("schema", ""))
            elif "schema_name" in payload:
                updates["schema_name"] = self.normalize_query_tab_schema(payload.get("schema_name", ""))
            if "position" in payload:
                updates["position"] = self.normalize_query_tab_position(payload.get("position"))
            if "run_mode" in payload:
                updates["run_mode"] = self.normalize_query_tab_run_mode(payload.get("run_mode"))
            if "is_active" in payload:
                updates["is_active"] = 1 if bool(payload.get("is_active")) else 0

            if not updates:
                return {"tab": self.public_query_tab(row)}
            if updates.get("is_active"):
                conn.execute("UPDATE query_tabs SET is_active = 0 WHERE user_id = ?", (user["id"],))

            updates["updated_at"] = utc_now()
            assignments = ", ".join(f"{name} = ?" for name in updates)
            values = list(updates.values())
            values.append(tab_id)
            conn.execute(f"UPDATE query_tabs SET {assignments} WHERE id = ?", values)
            self.ensure_active_query_tab(conn, user["id"])
            updated = conn.execute("SELECT * FROM query_tabs WHERE id = ?", (tab_id,)).fetchone()
            return {"tab": self.public_query_tab(updated)}

    def delete_query_tab(self, tab_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            row = self.query_tab_for_user(conn, tab_id, user)
            deleted = self.public_query_tab(row)
            conn.execute("DELETE FROM query_tabs WHERE id = ?", (tab_id,))
            remaining = conn.execute(
                "SELECT * FROM query_tabs WHERE user_id = ? ORDER BY position, id",
                (user["id"],),
            ).fetchall()
            if not remaining:
                self.create_default_query_tab(conn, user)
            self.ensure_active_query_tab(conn, user["id"])
            tabs = conn.execute(
                "SELECT * FROM query_tabs WHERE user_id = ? ORDER BY position, id",
                (user["id"],),
            ).fetchall()
            return {"deleted": True, "tab": deleted, "tabs": [self.public_query_tab(tab) for tab in tabs]}

    def create_default_query_tab(self, conn: sqlite3.Connection, user: dict[str, Any]) -> sqlite3.Row:
        now = utc_now()
        cursor = conn.execute(
            """
            INSERT INTO query_tabs
              (user_id, name, sql_text, cluster_id, catalog, schema_name, run_mode, position, is_active, created_at, updated_at)
            VALUES (?, 'query-1.sql', ?, NULL, 'tpch', 'sf1', 'current', 0, 1, ?, ?)
            """,
            (user["id"], DEFAULT_QUERY_TAB_SQL, now, now),
        )
        return conn.execute("SELECT * FROM query_tabs WHERE id = ?", (cursor.lastrowid,)).fetchone()

    def ensure_active_query_tab(self, conn: sqlite3.Connection, user_id: int) -> None:
        active = conn.execute(
            "SELECT id FROM query_tabs WHERE user_id = ? AND is_active = 1 ORDER BY position, id",
            (user_id,),
        ).fetchall()
        if len(active) > 1:
            keep_id = active[0]["id"]
            conn.execute(
                "UPDATE query_tabs SET is_active = CASE WHEN id = ? THEN 1 ELSE 0 END WHERE user_id = ?",
                (keep_id, user_id),
            )
        elif not active:
            first = conn.execute(
                "SELECT id FROM query_tabs WHERE user_id = ? ORDER BY position, id LIMIT 1",
                (user_id,),
            ).fetchone()
            if first:
                conn.execute("UPDATE query_tabs SET is_active = 1 WHERE id = ?", (first["id"],))

    def next_query_tab_position(self, conn: sqlite3.Connection, user_id: int) -> int:
        row = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS position FROM query_tabs WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return int(row["position"] if row else 0)

    def query_tab_for_user(self, conn: sqlite3.Connection, tab_id: int, user: dict[str, Any]) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM query_tabs WHERE id = ? AND user_id = ?", (tab_id, user["id"])).fetchone()
        if not row:
            raise ApiError(404, "Query tab not found.")
        return row

    def normalize_query_tab_name(self, value: Any) -> str:
        name = str(value or "").strip()
        if not name:
            raise ApiError(400, "tab name is required.")
        if any(char in name for char in "\r\n\t"):
            raise ApiError(400, "tab name cannot contain control characters.")
        if len(name) > MAX_QUERY_TAB_NAME_LENGTH:
            raise ApiError(400, f"tab name must be {MAX_QUERY_TAB_NAME_LENGTH} characters or less.")
        return name

    def normalize_query_tab_cluster_id(self, conn: sqlite3.Connection, value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            cluster_id = int(value)
        except (TypeError, ValueError):
            raise ApiError(400, "cluster_id must be an integer.") from None
        if not conn.execute("SELECT 1 FROM clusters WHERE id = ?", (cluster_id,)).fetchone():
            raise ApiError(400, "cluster_id does not match a saved cluster.")
        return cluster_id

    def normalize_query_tab_catalog(self, value: Any) -> str:
        catalog = str(value or "").strip()
        if catalog and not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", catalog):
            raise ApiError(400, "catalog must be lowercase letters, numbers, or underscores.")
        return catalog

    def normalize_query_tab_schema(self, value: Any) -> str:
        schema_name = str(value or "").strip()
        if schema_name and not SCHEMA_NAME_PATTERN.fullmatch(schema_name):
            raise ApiError(400, "schema must be alphanumeric or underscore characters.")
        return schema_name

    def normalize_query_tab_position(self, value: Any) -> int:
        try:
            position = int(value)
        except (TypeError, ValueError):
            raise ApiError(400, "position must be an integer.") from None
        if position < 0:
            raise ApiError(400, "position must be zero or greater.")
        return position

    def normalize_query_tab_run_mode(self, value: Any) -> str:
        run_mode = str(value or "current").strip().lower()
        if run_mode not in QUERY_TAB_RUN_MODES:
            raise ApiError(400, "run_mode must be current, selected, or all.")
        return run_mode

    def public_query_tab(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "name": row["name"],
            "sql": row["sql_text"],
            "cluster_id": row["cluster_id"],
            "catalog": row["catalog"],
            "schema": row["schema_name"],
            "run_mode": row["run_mode"],
            "position": row["position"],
            "is_active": bool(row["is_active"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_saved_queries(self, user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            own = conn.execute(
                "SELECT * FROM saved_queries WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
                (user["id"],),
            ).fetchall()
            queries = [self.public_saved_query(row) for row in own]
            role_ids = self._user_role_ids(conn, user)
            if role_ids:
                marks = ",".join("?" * len(role_ids))
                shared = conn.execute(
                    f"""
                    SELECT sq.*, users.username AS owner_username, MAX(es.access) AS shared_access
                    FROM saved_queries sq
                    JOIN entity_shares es ON es.entity_type = 'saved_query' AND es.entity_id = sq.id
                    JOIN users ON users.id = sq.user_id
                    WHERE es.role_id IN ({marks}) AND sq.user_id != ?
                    GROUP BY sq.id
                    ORDER BY sq.updated_at DESC
                    """,
                    (*role_ids, user["id"]),
                ).fetchall()
                for row in shared:
                    entry = self.public_saved_query(row)
                    entry["shared_access"] = self._shared_access(conn, "saved_query", row["id"], user)
                    entry["owner_username"] = row["owner_username"]
                    queries.append(entry)
            return {"queries": queries}

    def create_saved_query(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        sql_text = str(payload.get("sql", payload.get("sql_text", ""))).strip()
        if not sql_text:
            raise ApiError(400, "sql is required.")
        with self.conn() as conn:
            name = self.normalize_saved_query_name(payload.get("name") or self.saved_query_name_from_sql(sql_text))
            cluster_id = self.normalize_query_tab_cluster_id(conn, payload.get("cluster_id"))
            catalog = self.normalize_query_tab_catalog(payload.get("catalog", ""))
            schema_name = self.normalize_query_tab_schema(payload.get("schema", payload.get("schema_name", "")))
            now = utc_now()
            cursor = conn.execute(
                """
                INSERT INTO saved_queries
                  (user_id, name, sql_text, cluster_id, catalog, schema_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user["id"], name, sql_text, cluster_id, catalog, schema_name, now, now),
            )
            row = conn.execute("SELECT * FROM saved_queries WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return {"query": self.public_saved_query(row)}

    def update_saved_query(self, query_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            row = self.saved_query_for_user(conn, query_id, user, write=True)
            updates: dict[str, Any] = {}
            if "name" in payload:
                updates["name"] = self.normalize_saved_query_name(payload["name"])
            if "sql" in payload:
                sql_text = str(payload["sql"]).strip()
                if not sql_text:
                    raise ApiError(400, "sql is required.")
                updates["sql_text"] = sql_text
            elif "sql_text" in payload:
                sql_text = str(payload["sql_text"]).strip()
                if not sql_text:
                    raise ApiError(400, "sql is required.")
                updates["sql_text"] = sql_text
            if "cluster_id" in payload:
                updates["cluster_id"] = self.normalize_query_tab_cluster_id(conn, payload.get("cluster_id"))
            if "catalog" in payload:
                updates["catalog"] = self.normalize_query_tab_catalog(payload.get("catalog", ""))
            if "schema" in payload:
                updates["schema_name"] = self.normalize_query_tab_schema(payload.get("schema", ""))
            elif "schema_name" in payload:
                updates["schema_name"] = self.normalize_query_tab_schema(payload.get("schema_name", ""))
            if not updates:
                return {"query": self.public_saved_query(row)}
            updates["updated_at"] = utc_now()
            assignments = ", ".join(f"{name} = ?" for name in updates)
            values = list(updates.values()) + [query_id]
            conn.execute(f"UPDATE saved_queries SET {assignments} WHERE id = ?", values)
            updated = conn.execute("SELECT * FROM saved_queries WHERE id = ?", (query_id,)).fetchone()
            return {"query": self.public_saved_query(updated)}

    def delete_saved_query(self, query_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            row = self.saved_query_for_user(conn, query_id, user, write=True)
            if row["user_id"] != user["id"]:
                raise ApiError(403, "Only the owner can delete a shared saved query.")
            query = self.public_saved_query(row)
            conn.execute("DELETE FROM saved_queries WHERE id = ?", (query_id,))
            return {"deleted": True, "query": query}

    def saved_query_for_user(
        self, conn: sqlite3.Connection, query_id: int, user: dict[str, Any], *, write: bool = False
    ) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM saved_queries WHERE id = ?", (query_id,)).fetchone()
        if row and row["user_id"] == user["id"]:
            return row
        if row:
            access = self._shared_access(conn, "saved_query", query_id, user)
            if access is not None and (not write or access == "edit"):
                return row
        raise ApiError(404, "Saved query not found.")

    def normalize_saved_query_name(self, value: Any) -> str:
        name = str(value or "").strip()
        if not name:
            raise ApiError(400, "saved query name is required.")
        if any(char in name for char in "\r\n\t"):
            raise ApiError(400, "saved query name cannot contain control characters.")
        if len(name) > MAX_SAVED_QUERY_NAME_LENGTH:
            raise ApiError(400, f"saved query name must be {MAX_SAVED_QUERY_NAME_LENGTH} characters or less.")
        return name

    def saved_query_name_from_sql(self, sql_text: str) -> str:
        first_line = re.sub(r"\s+", " ", sql_text.strip()).strip()
        if not first_line:
            return "Saved query"
        return first_line[:MAX_SAVED_QUERY_NAME_LENGTH]

    def public_saved_query(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "name": row["name"],
            "sql": row["sql_text"],
            "cluster_id": row["cluster_id"],
            "catalog": row["catalog"],
            "schema": row["schema_name"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # --- Notebooks -------------------------------------------------------
    # Notebooks are an ordered document of SQL cells. CRUD mirrors saved_queries
    # / query_tabs; cells reuse the existing /api/query execution path. Ownership
    # is funneled through *_for_user helpers so sharing can be added later by
    # relaxing only those checks.

    def list_notebooks(self, user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            role_ids = self._user_role_ids(conn, user)
            marks = ",".join("?" * len(role_ids)) if role_ids else "NULL"
            rows = conn.execute(
                f"""
                SELECT n.*, COUNT(c.id) AS cell_count, users.username AS owner_username
                FROM notebooks n
                LEFT JOIN notebook_cells c ON c.notebook_id = n.id
                LEFT JOIN entity_shares es
                  ON es.entity_type = 'notebook' AND es.entity_id = n.id AND es.role_id IN ({marks})
                JOIN users ON users.id = n.user_id
                WHERE n.user_id = ? OR es.id IS NOT NULL
                GROUP BY n.id
                ORDER BY n.position, n.id
                """,
                (*role_ids, user["id"]),
            ).fetchall()
            notebooks = []
            for row in rows:
                notebook = self.public_notebook(row)
                notebook["cell_count"] = row["cell_count"]
                if row["user_id"] != user["id"]:
                    notebook["shared_access"] = self._shared_access(conn, "notebook", row["id"], user)
                    notebook["owner_username"] = row["owner_username"]
                notebooks.append(notebook)
            return {"notebooks": notebooks}

    def create_notebook(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            position = self.next_notebook_position(conn, user["id"])
            name = self.normalize_notebook_name(payload.get("name") or f"Notebook {position + 1}")
            cluster_id = self.normalize_query_tab_cluster_id(conn, payload.get("cluster_id"))
            catalog = self.normalize_query_tab_catalog(payload.get("catalog", ""))
            schema_name = self.normalize_query_tab_schema(
                payload.get("schema", payload.get("schema_name", ""))
            )
            now = utc_now()
            cursor = conn.execute(
                """
                INSERT INTO notebooks
                  (user_id, name, cluster_id, catalog, schema_name, position, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user["id"], name, cluster_id, catalog, schema_name, position, now, now),
            )
            notebook_id = cursor.lastrowid
            # Seed one empty cell so a new notebook opens runnable.
            conn.execute(
                """
                INSERT INTO notebook_cells
                  (notebook_id, position, sql_text, cluster_id, catalog, schema_name,
                   view_pref, chart_config_json, created_at, updated_at)
                VALUES (?, 0, '', NULL, '', '', 'table', '{}', ?, ?)
                """,
                (notebook_id, now, now),
            )
            row = conn.execute("SELECT * FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
            return {"notebook": self.public_notebook(row)}

    def update_notebook(self, notebook_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            row = self.notebook_for_user(conn, notebook_id, user, write=True)
            updates: dict[str, Any] = {}
            if "name" in payload:
                updates["name"] = self.normalize_notebook_name(payload["name"])
            if "cluster_id" in payload:
                updates["cluster_id"] = self.normalize_query_tab_cluster_id(conn, payload.get("cluster_id"))
            if "catalog" in payload:
                updates["catalog"] = self.normalize_query_tab_catalog(payload.get("catalog", ""))
            if "schema" in payload:
                updates["schema_name"] = self.normalize_query_tab_schema(payload.get("schema", ""))
            elif "schema_name" in payload:
                updates["schema_name"] = self.normalize_query_tab_schema(payload.get("schema_name", ""))
            if "position" in payload:
                updates["position"] = self.normalize_query_tab_position(payload.get("position"))
            if not updates:
                return {"notebook": self.public_notebook(row)}
            updates["updated_at"] = utc_now()
            assignments = ", ".join(f"{name} = ?" for name in updates)
            values = list(updates.values()) + [notebook_id]
            conn.execute(f"UPDATE notebooks SET {assignments} WHERE id = ?", values)
            updated = conn.execute("SELECT * FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
            return {"notebook": self.public_notebook(updated)}

    def delete_notebook(self, notebook_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            row = self.notebook_for_user(conn, notebook_id, user, write=True)
            if row["user_id"] != user["id"]:
                raise ApiError(403, "Only the owner can delete a shared notebook.")
            notebook = self.public_notebook(row)
            # notebook_cells cascade via ON DELETE CASCADE.
            conn.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))
            return {"deleted": True, "notebook": notebook}

    def list_notebook_cells(self, notebook_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            self.notebook_for_user(conn, notebook_id, user)
            rows = conn.execute(
                "SELECT * FROM notebook_cells WHERE notebook_id = ? ORDER BY position, id",
                (notebook_id,),
            ).fetchall()
            return {"cells": [self.public_notebook_cell(row) for row in rows]}

    def create_notebook_cell(self, notebook_id: int, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            self.notebook_for_user(conn, notebook_id, user, write=True)
            position = self.next_notebook_cell_position(conn, notebook_id)
            sql_text = str(payload.get("sql", payload.get("sql_text", ""))).strip()
            cluster_id = self.normalize_query_tab_cluster_id(conn, payload.get("cluster_id"))
            catalog = self.normalize_query_tab_catalog(payload.get("catalog", ""))
            schema_name = self.normalize_query_tab_schema(
                payload.get("schema", payload.get("schema_name", ""))
            )
            view_pref = self.normalize_notebook_cell_view(payload.get("view_pref", "table"))
            chart_config = dumps(payload.get("chart_config") or {})
            now = utc_now()
            cursor = conn.execute(
                """
                INSERT INTO notebook_cells
                  (notebook_id, position, sql_text, cluster_id, catalog, schema_name,
                   view_pref, chart_config_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (notebook_id, position, sql_text, cluster_id, catalog, schema_name,
                 view_pref, chart_config, now, now),
            )
            row = conn.execute("SELECT * FROM notebook_cells WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return {"cell": self.public_notebook_cell(row)}

    def update_notebook_cell(
        self, notebook_id: int, cell_id: int, payload: dict[str, Any], user: dict[str, Any]
    ) -> dict[str, Any]:
        with self.conn() as conn:
            row = self.notebook_cell_for_user(conn, notebook_id, cell_id, user, write=True)
            updates: dict[str, Any] = {}
            if "sql" in payload:
                updates["sql_text"] = str(payload["sql"]).strip()
            elif "sql_text" in payload:
                updates["sql_text"] = str(payload["sql_text"]).strip()
            if "cluster_id" in payload:
                updates["cluster_id"] = self.normalize_query_tab_cluster_id(conn, payload.get("cluster_id"))
            if "catalog" in payload:
                updates["catalog"] = self.normalize_query_tab_catalog(payload.get("catalog", ""))
            if "schema" in payload:
                updates["schema_name"] = self.normalize_query_tab_schema(payload.get("schema", ""))
            elif "schema_name" in payload:
                updates["schema_name"] = self.normalize_query_tab_schema(payload.get("schema_name", ""))
            if "position" in payload:
                updates["position"] = self.normalize_query_tab_position(payload.get("position"))
            if "view_pref" in payload:
                updates["view_pref"] = self.normalize_notebook_cell_view(payload.get("view_pref"))
            if "chart_config" in payload:
                updates["chart_config_json"] = dumps(payload.get("chart_config") or {})
            if "last_query_id" in payload:
                updates["last_query_id"] = self.normalize_cell_last_query_id(
                    conn, payload.get("last_query_id"), user
                )
            if not updates:
                return {"cell": self.public_notebook_cell(row)}
            updates["updated_at"] = utc_now()
            assignments = ", ".join(f"{name} = ?" for name in updates)
            values = list(updates.values()) + [cell_id]
            conn.execute(f"UPDATE notebook_cells SET {assignments} WHERE id = ?", values)
            updated = conn.execute("SELECT * FROM notebook_cells WHERE id = ?", (cell_id,)).fetchone()
            return {"cell": self.public_notebook_cell(updated)}

    def delete_notebook_cell(self, notebook_id: int, cell_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            row = self.notebook_cell_for_user(conn, notebook_id, cell_id, user, write=True)
            cell = self.public_notebook_cell(row)
            conn.execute("DELETE FROM notebook_cells WHERE id = ?", (cell_id,))
            return {"deleted": True, "cell": cell}

    def normalize_cell_last_query_id(
        self, conn: sqlite3.Connection, raw_value: Any, user: dict[str, Any]
    ) -> int | None:
        if raw_value is None or raw_value == "":
            return None
        try:
            query_id = int(raw_value)
        except (TypeError, ValueError):
            raise ApiError(400, "last_query_id must be an integer or null.") from None
        row = conn.execute("SELECT user_id FROM query_runs WHERE id = ?", (query_id,)).fetchone()
        if not row or row["user_id"] != user["id"]:
            raise ApiError(400, "last_query_id must reference one of your queries.")
        return query_id

    def next_notebook_position(self, conn: sqlite3.Connection, user_id: int) -> int:
        row = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS position FROM notebooks WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return int(row["position"])

    def next_notebook_cell_position(self, conn: sqlite3.Connection, notebook_id: int) -> int:
        row = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS position FROM notebook_cells WHERE notebook_id = ?",
            (notebook_id,),
        ).fetchone()
        return int(row["position"])

    def notebook_for_user(
        self, conn: sqlite3.Connection, notebook_id: int, user: dict[str, Any], *, write: bool = False
    ) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
        if row and row["user_id"] == user["id"]:
            return row
        if row:
            access = self._shared_access(conn, "notebook", notebook_id, user)
            if access is not None and (not write or access == "edit"):
                return row
        raise ApiError(404, "Notebook not found.")

    def notebook_cell_for_user(
        self,
        conn: sqlite3.Connection,
        notebook_id: int,
        cell_id: int,
        user: dict[str, Any],
        *,
        write: bool = False,
    ) -> sqlite3.Row:
        # Cell access follows the notebook's (owner or share level).
        self.notebook_for_user(conn, notebook_id, user, write=write)
        row = conn.execute(
            "SELECT * FROM notebook_cells WHERE id = ? AND notebook_id = ?",
            (cell_id, notebook_id),
        ).fetchone()
        if not row:
            raise ApiError(404, "Notebook cell not found.")
        return row

    def normalize_notebook_name(self, value: Any) -> str:
        name = str(value or "").strip()
        if not name:
            raise ApiError(400, "notebook name is required.")
        if any(char in name for char in "\r\n\t"):
            raise ApiError(400, "notebook name cannot contain control characters.")
        if len(name) > MAX_NOTEBOOK_NAME_LENGTH:
            raise ApiError(400, f"notebook name must be {MAX_NOTEBOOK_NAME_LENGTH} characters or less.")
        return name

    def normalize_notebook_cell_view(self, value: Any) -> str:
        view = str(value or "table").strip().lower()
        if view not in NOTEBOOK_CELL_VIEWS:
            raise ApiError(400, "view_pref must be table or chart.")
        return view

    def public_notebook(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "name": row["name"],
            "cluster_id": row["cluster_id"],
            "catalog": row["catalog"],
            "schema": row["schema_name"],
            "position": row["position"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def public_notebook_cell(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "notebook_id": row["notebook_id"],
            "position": row["position"],
            "sql": row["sql_text"],
            "cluster_id": row["cluster_id"],
            "catalog": row["catalog"],
            "schema": row["schema_name"],
            "view_pref": row["view_pref"],
            "chart_config": loads(row["chart_config_json"], {}),
            "last_query_id": row["last_query_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def cluster_metadata(
        self,
        cluster_id: int,
        *,
        catalog: str = "",
        schema_name: str = "",
        table: str = "",
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if user is not None:
            self.require_cluster_access(user, cluster_id)
            if catalog:
                self.require_catalog_access(user, catalog)
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            cluster = self.public_cluster(row)
            catalog_rows = self.catalog_rows_by_name(conn, cluster["catalogs"])
            coordinator = None
            if catalog:
                coordinator = conn.execute(
                    """
                    SELECT * FROM provider_resources
                    WHERE cluster_id = ? AND resource_type = 'coordinator_instance'
                    ORDER BY id DESC LIMIT 1
                    """,
                    (cluster_id,),
                ).fetchone()

        catalog_details = [
            {
                "name": name,
                "type": catalog_rows[name]["type"] if name in catalog_rows else "builtin",
                "enabled": bool(catalog_rows[name]["enabled"]) if name in catalog_rows else True,
            }
            for name in cluster["catalogs"]
            # Only surface the catalogs the caller may actually use.
            if user is None or self.user_can_use_catalog(user, name)
        ]
        result: dict[str, Any] = {
            "cluster": {
                "id": cluster["id"],
                "name": cluster["name"],
                "status": cluster["status"],
            },
            "catalogs": catalog_details,
            "schemas": [],
            "tables": [],
            "columns": [],
            "truncated": False,
        }
        if not catalog:
            return result
        if catalog not in cluster["catalogs"]:
            raise ApiError(400, "Catalog is not attached to this cluster.")
        if table and not schema_name:
            raise ApiError(400, "schema is required when table is specified.")
        if cluster["status"] != "Running" or not coordinator:
            # Suspended/stopped cluster: fall back to the metadata cache so the
            # schema browser, autocomplete, and search keep working.
            cached = self._cached_metadata(cluster_id, catalog, schema_name, table, result)
            if cached is not None:
                return cached
            if cluster["status"] != "Running":
                raise ApiError(
                    409, f"Cluster must be Running to load live metadata. Current status: {cluster['status']}."
                )
            raise ApiError(409, "Cluster has no tracked coordinator instance.")

        endpoint = self.coordinator_endpoint(row_to_dict(coordinator))
        quoted_catalog = self.trino_identifier(catalog)
        if not schema_name and not table:
            rows, truncated = self.run_trino_metadata_query(
                endpoint,
                f"SELECT schema_name FROM {quoted_catalog}.information_schema.schemata ORDER BY schema_name",
            )
            result["schemas"] = [{"name": str(row[0])} for row in rows if row]
            result["truncated"] = truncated
            return result

        schema_literal = self.trino_string_literal(schema_name)
        if not table:
            rows, truncated = self.run_trino_metadata_query(
                endpoint,
                (
                    f"SELECT table_name, table_type FROM {quoted_catalog}.information_schema.tables "
                    f"WHERE table_schema = {schema_literal} ORDER BY table_name"
                ),
            )
            result["tables"] = [
                {"name": str(row[0]), "type": str(row[1] if len(row) > 1 else "TABLE")}
                for row in rows
                if row
            ]
            result["truncated"] = truncated
            self._cache_tables(cluster_id, catalog, schema_name, result["tables"])
            return result

        table_literal = self.trino_string_literal(table)
        rows, truncated = self.run_trino_metadata_query(
            endpoint,
            (
                f"SELECT column_name, data_type, is_nullable, column_default "
                f"FROM {quoted_catalog}.information_schema.columns "
                f"WHERE table_schema = {schema_literal} AND table_name = {table_literal} "
                f"ORDER BY ordinal_position"
            ),
        )
        result["columns"] = [
            {
                "name": str(row[0]),
                "type": str(row[1] if len(row) > 1 else ""),
                "nullable": str(row[2] if len(row) > 2 else "").upper() == "YES",
                "default": row[3] if len(row) > 3 else None,
            }
            for row in rows
            if row
        ]
        result["truncated"] = truncated
        self._cache_columns(cluster_id, catalog, schema_name, table, result["columns"])
        return result

    def run_trino_metadata_query(self, coordinator_endpoint: str, sql_text: str) -> tuple[list[list[Any]], bool]:
        response = self.submit_trino_query(
            coordinator_endpoint=coordinator_endpoint,
            sql_text=sql_text,
            username="trinohub-metadata",
            catalog="",
            schema_name="",
        )
        rows: list[list[Any]] = []
        truncated = False
        pages = 0
        while True:
            error = response.get("error") or {}
            if error:
                raise ApiError(502, f"Trino metadata query failed: {error.get('message') or 'unknown error'}")
            for row in response.get("data") or []:
                if len(rows) >= MAX_METADATA_ROWS:
                    truncated = True
                    continue
                rows.append(row)
            next_uri = response.get("nextUri")
            if not next_uri:
                return rows, truncated
            pages += 1
            if pages > MAX_METADATA_PAGES:
                raise ApiError(502, "Trino metadata query did not finish within the page limit.")
            response = self.fetch_trino_next(next_uri)

    @staticmethod
    def trino_identifier(value: str) -> str:
        text = str(value or "")
        if not text or "\x00" in text:
            raise ApiError(400, "Invalid Trino identifier.")
        return '"' + text.replace('"', '""') + '"'

    @staticmethod
    def trino_string_literal(value: str) -> str:
        text = str(value or "")
        if "\x00" in text:
            raise ApiError(400, "Invalid Trino string literal.")
        return "'" + text.replace("'", "''") + "'"

    def create_query(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        sql_text = str(payload.get("sql", "")).strip()
        if not sql_text:
            raise ApiError(400, "sql is required.")
        statements = split_sql_statements(sql_text)
        if not statements:
            raise ApiError(400, "sql is required.")
        if len(statements) > 1:
            raise ApiError(400, "Submit one SQL statement per query request.")
        sql_text = statements[0]
        cluster_id = payload.get("cluster_id")
        if cluster_id is None:
            raise ApiError(400, "cluster_id is required.")
        try:
            cluster_id = int(cluster_id)
        except (TypeError, ValueError):
            raise ApiError(400, "cluster_id must be an integer.")

        catalog = str(payload.get("catalog") or "").strip()
        schema_name = str(payload.get("schema") or "").strip()
        if catalog and not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", catalog):
            raise ApiError(400, "catalog must be lowercase letters, numbers, or underscores.")
        if schema_name and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", schema_name):
            raise ApiError(400, "schema must be alphanumeric or underscore characters.")

        # Data-access grants: the caller needs USE access to the cluster and,
        # when a session catalog is set, to that catalog.
        self.require_cluster_access(user, cluster_id)
        if catalog:
            self.require_catalog_access(user, catalog)

        now = utc_now()
        auto_resume_cluster = False
        endpoint = None
        # Keying on the normalized statement (not the raw text) also decides
        # eligibility, so a leading comment can't mask the SELECT keyword.
        normalized_sql = normalize_sql_for_cache(sql_text)
        cache_key = (
            query_cache_key(user["id"], cluster_id, catalog, schema_name, normalized_sql)
            if is_cacheable_sql(normalized_sql)
            else ""
        )
        cache_ttl = self.result_cache_ttl_minutes() if cache_key else 0
        use_cache = bool(cache_key) and cache_ttl > 0 and not payload.get("fresh")
        with self.conn() as conn:
            cluster_row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not cluster_row:
                raise ApiError(404, "Cluster not found.")
            cluster = self.public_cluster(cluster_row)
            # Cached results are only served while the cluster is in a state
            # that would accept the query anyway (Running, or auto-suspended
            # and about to resume). A disabled, failed, or manually suspended
            # cluster keeps rejecting re-runs even when a cached result
            # exists — disabling a cluster must cut off its data.
            status_accepts_sql = cluster["status"] == "Running" or (
                cluster["status"] == "Suspended" and cluster["auto_suspend_minutes"] is not None
            )
            if use_cache and status_accepts_sql:
                # A hit is served straight from the stored capped result set —
                # no coordinator round-trip, and a suspended cluster stays
                # suspended instead of resuming for a repeat query.
                source = self._cached_result_source(conn, cache_key, cache_ttl, user["id"])
                if source is not None:
                    cached_run = self._insert_cached_run(
                        conn, source, user, cluster, sql_text, catalog, schema_name, now
                    )
                    return {"query": self.public_query(cached_run)}
            if cluster["status"] == "Running":
                coordinator = conn.execute(
                    """
                    SELECT * FROM provider_resources
                    WHERE cluster_id = ? AND resource_type = 'coordinator_instance'
                    ORDER BY id DESC LIMIT 1
                    """,
                    (cluster_id,),
                ).fetchone()
                if not coordinator:
                    raise ApiError(409, "Cluster has no tracked coordinator instance.")
                endpoint = self.coordinator_endpoint(row_to_dict(coordinator))
            elif cluster["status"] == "Suspended" and cluster["auto_suspend_minutes"] is not None:
                # The cluster auto-suspended while idle. Rather than failing the query,
                # queue it and resume the cluster; it dispatches to Trino automatically
                # once the cluster is Running (the client polls /api/query/{id}).
                auto_resume_cluster = True
            else:
                raise ApiError(409, f"Cluster must be Running before it can accept SQL. Current status: {cluster['status']}.")

            cursor = conn.execute(
                """
                INSERT INTO query_runs
                  (user_id, cluster_id, cluster_name, sql_text, status, catalog, schema_name,
                   pending_cluster_start, cache_key, elapsed_ms, row_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'Queued', ?, ?, ?, ?, 0, 0, ?, ?)
                """,
                (
                    user["id"], cluster_id, cluster["name"], sql_text, catalog, schema_name,
                    1 if auto_resume_cluster else 0, cache_key, now, now,
                ),
            )
            query_id = int(cursor.lastrowid)
            if not cache_key:
                # A non-read-only statement may change data this user has
                # cached results for; expire their entries on this cluster so
                # a follow-up SELECT re-executes instead of showing
                # pre-write rows.
                conn.execute(
                    "UPDATE query_runs SET cache_key = '' WHERE user_id = ? AND cluster_id = ? AND cache_key != ''",
                    (user["id"], cluster_id),
                )

        if auto_resume_cluster:
            # Kick off the resume outside the DB transaction (it launches AWS
            # resources), then hand the still-Queued query back so the client can
            # poll until the cluster is Running and the query dispatches.
            self._resume_cluster_for_query(cluster_id, query_id)
            with self.conn() as conn:
                queued = conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone()
            return {"query": self.public_query(queued)}

        try:
            response = self.submit_trino_query(
                coordinator_endpoint=endpoint,
                sql_text=sql_text,
                username=str(user["username"]),
                catalog=catalog,
                schema_name=schema_name,
            )
            with self.conn() as conn:
                row = conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone()
                self.apply_trino_response(conn, row_to_dict(row), response)
            return self.advance_query_run(query_id, user, max_pages=2)
        except Exception as exc:
            message = exc.message if isinstance(exc, ApiError) else f"{type(exc).__name__}: {exc}"
            with self.conn() as conn:
                row = conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone()
                elapsed_ms = self.elapsed_ms(row["created_at"]) if row else 0
                conn.execute(
                    """
                    UPDATE query_runs
                    SET status = 'Failed', error_message = ?, elapsed_ms = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (message, elapsed_ms, utc_now(), query_id),
                )
                updated = conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone()
            return {"query": self.public_query(updated)}

    def list_query_history(self, user: dict[str, Any]) -> dict[str, Any]:
        see_all = self.has_privilege(user, PRIVILEGE_VIEW_ALL_QUERY_HISTORY)
        where = "" if see_all else "WHERE query_runs.user_id = ?"
        params = () if see_all else (user["id"],)
        with self.conn() as conn:
            rows = conn.execute(
                f"""
                SELECT query_runs.*, users.username AS username, users.role AS user_role
                FROM query_runs
                LEFT JOIN users ON users.id = query_runs.user_id
                {where}
                ORDER BY query_runs.created_at DESC LIMIT 100
                """,
                params,
            ).fetchall()
            return {"queries": [self.public_query(row) for row in rows]}

    def get_query(self, query_id: int, user: dict[str, Any]) -> dict[str, Any]:
        return self.advance_query_run(query_id, user, max_pages=5)

    def cancel_query(self, query_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone()
            if not row:
                raise ApiError(404, "Query not found.")
            query = row_to_dict(row)
            self.require_query_access(query, user, PRIVILEGE_CANCEL_ANY_QUERY)
            next_uri = query["next_uri"]

        cancel_detail = {"cancelled_remote": False}
        if query["status"] not in TERMINAL_QUERY_STATUSES and next_uri:
            cancel_detail = self.cancel_trino_query(next_uri)

        with self.conn() as conn:
            row = conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone()
            elapsed_ms = self.elapsed_ms(row["created_at"])
            conn.execute(
                """
                UPDATE query_runs
                SET status = 'Cancelled', next_uri = '', elapsed_ms = ?, updated_at = ?
                WHERE id = ?
                """,
                (elapsed_ms, utc_now(), query_id),
            )
            updated = conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone()
        return {"query": self.public_query(updated), "cancel": cancel_detail}

    def _resume_cluster_for_query(self, cluster_id: int, query_id: int) -> None:
        """Resume an auto-suspended cluster on behalf of a queued query.

        If the resume can't be kicked off for a real reason (e.g. AWS provisioning
        error), fail the query so the client stops polling. If it fails only because
        the cluster is already transitioning — a race with the health poller or a
        concurrent query that already triggered the resume — leave the query queued;
        it dispatches once the cluster reaches Running."""
        try:
            self.start_cluster(cluster_id, {"confirm_billable": True})
        except ApiError as exc:
            with self.conn() as conn:
                row = conn.execute("SELECT status FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
                status = row["status"] if row else None
                if status in {"Creating", "Starting", "Running", "Scaling"}:
                    return
                self._fail_query(conn, query_id, f"Cluster could not be resumed: {exc.message}")

    def _fail_query(self, conn: sqlite3.Connection, query_id: int, message: str) -> None:
        row = conn.execute("SELECT created_at FROM query_runs WHERE id = ?", (query_id,)).fetchone()
        elapsed_ms = self.elapsed_ms(row["created_at"]) if row else 0
        conn.execute(
            """
            UPDATE query_runs
            SET status = 'Failed', pending_cluster_start = 0, error_message = ?,
                elapsed_ms = ?, updated_at = ?
            WHERE id = ?
            """,
            (message, elapsed_ms, utc_now(), query_id),
        )

    def dispatch_pending_query(self, query: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        """Advance a query that is waiting for its cluster to resume from suspend.

        Called on every poll of a ``pending_cluster_start`` query. While the cluster
        is still coming up the query stays Queued; once the coordinator is reachable
        the query is submitted to Trino for real. A stuck resume fails the query after
        ``QUERY_CLUSTER_START_TIMEOUT_SECONDS`` so the client isn't left polling."""
        query_id = int(query["id"])
        cluster_id = query["cluster_id"]
        with self.conn() as conn:
            cluster_row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not cluster_row:
                self._fail_query(conn, query_id, "Cluster not found.")
                return row_to_dict(conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone())
            cluster = self.public_cluster(cluster_row)

        # Nudge a Starting cluster toward Running directly, so dispatch doesn't have
        # to wait for the next background health-poller tick.
        if cluster["status"] == "Starting":
            try:
                cluster = self.refresh_cluster_health(cluster_id)["cluster"]
            except ApiError:
                pass

        if cluster["status"] in {"Creating", "Starting", "Scaling"}:
            if self.elapsed_ms(query["created_at"]) > QUERY_CLUSTER_START_TIMEOUT_SECONDS * 1000:
                with self.conn() as conn:
                    self._fail_query(conn, query_id, "Cluster did not finish starting in time; try the query again.")
                    return row_to_dict(conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone())
            return query  # still resuming — stay Queued and keep polling

        if cluster["status"] != "Running":
            with self.conn() as conn:
                self._fail_query(conn, query_id, f"Cluster is {cluster['status']} and cannot run the query.")
                return row_to_dict(conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone())

        # Cluster is Running: dispatch the queued SQL to Trino for real.
        with self.conn() as conn:
            coordinator = conn.execute(
                """
                SELECT * FROM provider_resources
                WHERE cluster_id = ? AND resource_type = 'coordinator_instance'
                ORDER BY id DESC LIMIT 1
                """,
                (cluster_id,),
            ).fetchone()
            if not coordinator:
                self._fail_query(conn, query_id, "Cluster has no tracked coordinator instance.")
                return row_to_dict(conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone())
            endpoint = self.coordinator_endpoint(row_to_dict(coordinator))

        try:
            response = self.submit_trino_query(
                coordinator_endpoint=endpoint,
                sql_text=query["sql_text"],
                username=str(user["username"]),
                catalog=query["catalog"],
                schema_name=query["schema_name"],
            )
        except Exception as exc:
            message = exc.message if isinstance(exc, ApiError) else f"{type(exc).__name__}: {exc}"
            with self.conn() as conn:
                self._fail_query(conn, query_id, message)
                return row_to_dict(conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone())

        with self.conn() as conn:
            conn.execute("UPDATE query_runs SET pending_cluster_start = 0 WHERE id = ?", (query_id,))
            row = conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone()
            return self.apply_trino_response(conn, row_to_dict(row), response)

    def advance_query_run(self, query_id: int, user: dict[str, Any], *, max_pages: int) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone()
            if not row:
                raise ApiError(404, "Query not found.")
            query = row_to_dict(row)
            self.require_query_access(query, user)

        if query.get("pending_cluster_start"):
            query = self.dispatch_pending_query(query, user)

        pages = 0
        while query["status"] not in TERMINAL_QUERY_STATUSES and query["next_uri"] and pages < max_pages:
            response = self.fetch_trino_next(query["next_uri"])
            with self.conn() as conn:
                row = conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone()
                query = self.apply_trino_response(conn, row_to_dict(row), response)
            pages += 1

        with self.conn() as conn:
            updated = conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone()
            return {"query": self.public_query(updated)}

    def require_query_access(
        self, query: dict[str, Any], user: dict[str, Any], privilege: str = PRIVILEGE_VIEW_ALL_QUERY_HISTORY
    ) -> None:
        """Owners always have access; others need the given privilege
        (VIEW_ALL_QUERY_HISTORY to inspect, CANCEL_ANY_QUERY to cancel)."""
        if query["user_id"] != user["id"] and not self.has_privilege(user, privilege):
            raise ApiError(404, "Query not found.")

    def _cached_result_source(
        self, conn: sqlite3.Connection, cache_key: str, ttl_minutes: int, user_id: Any
    ) -> dict[str, Any] | None:
        """Most recent successful run for this cache key whose results are still
        inside the TTL window. Only fresh runs (cache_hit = 0) are sources, so a
        chain of hits can never extend a result set's lifetime past the TTL.

        The user id is part of the cache key already, but it is also an explicit
        predicate here so the per-user boundary holds structurally even if the
        key material is ever changed."""
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=ttl_minutes)).isoformat(
            timespec="seconds"
        )
        row = conn.execute(
            """
            SELECT * FROM query_runs
            WHERE cache_key = ? AND user_id = ? AND cache_hit = 0 AND status = 'Finished'
              AND error_message = '' AND updated_at >= ?
            ORDER BY updated_at DESC LIMIT 1
            """,
            (cache_key, user_id, cutoff),
        ).fetchone()
        return row_to_dict(row)

    def _insert_cached_run(
        self,
        conn: sqlite3.Connection,
        source: dict[str, Any],
        user: dict[str, Any],
        cluster: dict[str, Any],
        sql_text: str,
        catalog: str,
        schema_name: str,
        now: str,
    ) -> sqlite3.Row:
        """Record a cache-served run as its own history row, copying the source's
        capped result buffers so display and CSV export keep working without ever
        re-executing the query. trino_query_id stays empty — this run never
        reached a coordinator, and copying the source's id would make the query
        profile fetch execution details for a different run."""
        cursor = conn.execute(
            """
            INSERT INTO query_runs
              (user_id, cluster_id, cluster_name, sql_text, status,
               catalog, schema_name, columns_json, data_json, download_data_json,
               elapsed_ms, row_count, total_row_count, download_row_count,
               truncated, download_truncated, result_bytes, cache_hit,
               cached_from_query_id, result_cached_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'Finished', ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """,
            (
                user["id"],
                cluster["id"],
                cluster["name"],
                sql_text,
                catalog,
                schema_name,
                source["columns_json"],
                source["data_json"],
                source["download_data_json"],
                source["row_count"],
                source["total_row_count"],
                source["download_row_count"],
                source["truncated"],
                source["download_truncated"],
                source["result_bytes"],
                source["id"],
                source["updated_at"],
                now,
                now,
            ),
        )
        return conn.execute("SELECT * FROM query_runs WHERE id = ?", (cursor.lastrowid,)).fetchone()

    def rows_with_limits(
        self,
        existing_data: list[Any],
        incoming_data: list[Any],
        *,
        max_rows: int,
        max_bytes: int,
    ) -> tuple[list[Any], int, bool]:
        data = list(existing_data[:max_rows])
        byte_count = len(dumps(data).encode("utf-8"))
        limited = len(existing_data) > len(data) or byte_count > max_bytes
        if byte_count > max_bytes:
            data = []
            byte_count = len(dumps(data).encode("utf-8"))
            limited = True
        for row in incoming_data:
            if len(data) >= max_rows:
                limited = True
                continue
            row_bytes = len(dumps(row).encode("utf-8")) + 1
            if byte_count + row_bytes > max_bytes:
                limited = True
                continue
            data.append(row)
            byte_count += row_bytes
        return data, byte_count, limited

    def apply_trino_response(
        self,
        conn: sqlite3.Connection,
        query: dict[str, Any],
        response: dict[str, Any],
        *,
        max_rows: int = MAX_QUERY_RESULT_ROWS,
        max_bytes: int = MAX_QUERY_RESULT_BYTES,
        max_download_rows: int = MAX_QUERY_DOWNLOAD_ROWS,
        max_download_bytes: int = MAX_QUERY_DOWNLOAD_BYTES,
    ) -> dict[str, Any]:
        columns = response.get("columns") or loads(query["columns_json"], [])
        existing_data = loads(query["data_json"], [])
        existing_download_data = loads(query.get("download_data_json", ""), [])
        incoming_data = response.get("data") or []
        # row_count/data_json hold only the rows we retain (capped at max_rows),
        # while total_row_count accumulates every row Trino has returned so the
        # truncation flag and count stay accurate across paginated responses.
        prior_total = int(query["total_row_count"] or 0)
        total_row_count = prior_total + len(incoming_data)
        data, result_bytes, display_limited = self.rows_with_limits(
            existing_data,
            incoming_data,
            max_rows=max_rows,
            max_bytes=max_bytes,
        )
        download_data, _, download_limited = self.rows_with_limits(
            existing_download_data,
            incoming_data,
            max_rows=max_download_rows,
            max_bytes=max_download_bytes,
        )
        truncated = display_limited or total_row_count > len(data)
        download_truncated = download_limited or total_row_count > len(download_data)
        error = response.get("error") or {}
        status = "Failed" if error else ("Running" if response.get("nextUri") else "Finished")
        error_message = str(error.get("message") or "")
        elapsed_ms = self.elapsed_ms(query["created_at"])
        conn.execute(
            """
            UPDATE query_runs
            SET status = ?, trino_query_id = ?, next_uri = ?, columns_json = ?,
                data_json = ?, download_data_json = ?, elapsed_ms = ?, row_count = ?,
                total_row_count = ?, download_row_count = ?, truncated = ?,
                download_truncated = ?, result_bytes = ?, error_message = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                str(response.get("id") or query["trino_query_id"] or ""),
                str(response.get("nextUri") or ""),
                dumps(columns),
                dumps(data),
                dumps(download_data),
                elapsed_ms,
                len(data),
                total_row_count,
                len(download_data),
                1 if truncated else 0,
                1 if download_truncated else 0,
                result_bytes,
                error_message,
                utc_now(),
                query["id"],
            ),
        )
        row = conn.execute("SELECT * FROM query_runs WHERE id = ?", (query["id"],)).fetchone()
        return row_to_dict(row)

    def query_csv_payload(self, query_id: int, user: dict[str, Any]) -> dict[str, Any]:
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM query_runs WHERE id = ?", (query_id,)).fetchone()
            if not row:
                raise ApiError(404, "Query not found.")
            query = row_to_dict(row)
            self.require_query_access(query, user)
        return {
            "columns": loads(query["columns_json"], []),
            "rows": loads(query.get("download_data_json", ""), []) or loads(query["data_json"], []),
            "download_truncated": bool(query.get("download_truncated")),
            "download_row_count": int(query.get("download_row_count") or query.get("row_count") or 0),
        }

    def elapsed_ms(self, created_at: str) -> int:
        try:
            created = datetime.fromisoformat(created_at)
            return max(0, int((datetime.now(timezone.utc) - created).total_seconds() * 1000))
        except ValueError:
            return 0

    def submit_trino_query(
        self,
        *,
        coordinator_endpoint: str,
        sql_text: str,
        username: str,
        catalog: str,
        schema_name: str,
    ) -> dict[str, Any]:
        url = f"http://{coordinator_endpoint}:{TRINO_HTTP_PORT}/v1/statement"
        headers = {
            "Content-Type": "text/plain; charset=utf-8",
            "X-Trino-User": username or "trinohub",
            "X-Trino-Source": "TrinoHub",
        }
        if catalog:
            headers["X-Trino-Catalog"] = catalog
        if schema_name:
            headers["X-Trino-Schema"] = schema_name
        request = urllib.request.Request(url, data=sql_text.encode("utf-8"), headers=headers, method="POST")
        return self.trino_json_request(request)

    def fetch_trino_next(self, next_uri: str) -> dict[str, Any]:
        request = urllib.request.Request(next_uri, headers={"X-Trino-Source": "TrinoHub"}, method="GET")
        return self.trino_json_request(request)

    def cancel_trino_query(self, next_uri: str) -> dict[str, Any]:
        request = urllib.request.Request(next_uri, headers={"X-Trino-Source": "TrinoHub"}, method="DELETE")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return {"cancelled_remote": True, "status": response.status}
        except urllib.error.HTTPError as exc:
            if exc.code in {404, 410}:
                return {"cancelled_remote": False, "status": exc.code, "not_found": True}
            raise

    def trino_json_request(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ApiError(exc.code, f"Trino request failed: {detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise ApiError(502, f"Trino coordinator is unreachable: {exc.reason}") from exc
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise ApiError(502, "Trino returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise ApiError(502, "Trino returned an invalid response.")
        return payload

    def public_query(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        keys = set(row.keys())
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "username": row["username"] if "username" in keys else "",
            "user_role": row["user_role"] if "user_role" in keys else "",
            "cluster_id": row["cluster_id"],
            "cluster_name": row["cluster_name"] if "cluster_name" in keys else "",
            "sql": row["sql_text"],
            "status": row["status"],
            "trino_query_id": row["trino_query_id"],
            "catalog": row["catalog"],
            "schema": row["schema_name"],
            "columns": loads(row["columns_json"], []),
            "data": loads(row["data_json"], []),
            "elapsed_ms": row["elapsed_ms"],
            "row_count": row["row_count"],
            "total_row_count": row["total_row_count"],
            "download_row_count": row["download_row_count"],
            "truncated": bool(row["truncated"]),
            "download_truncated": bool(row["download_truncated"]),
            "result_bytes": row["result_bytes"],
            "error_message": row["error_message"],
            "pending_cluster_start": bool(row["pending_cluster_start"]) if "pending_cluster_start" in keys else False,
            "cache_hit": bool(row["cache_hit"]) if "cache_hit" in keys else False,
            "cached_from_query_id": row["cached_from_query_id"] if "cached_from_query_id" in keys else None,
            "result_cached_at": row["result_cached_at"] if "result_cached_at" in keys else "",
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # --- Ask Trino: natural-language analytics assistant --------------------
    # The model is given a schema-rich prompt and returns strict JSON
    # {explanation, sql, chartType, clarifyingQuestion?}. We validate the SQL,
    # run it through create_query (reusing caps + history), and return the
    # rendered result. The model never connects to Trino itself.

    def ask_trino(self, payload: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        question = str(payload.get("question") or "").strip()
        if not question:
            raise ApiError(400, "Ask a question to get started.")
        cluster_id = payload.get("cluster_id")
        if cluster_id is not None:
            try:
                cluster_id = int(cluster_id)
            except (TypeError, ValueError):
                raise ApiError(400, "cluster_id must be an integer.")
        catalog = str(payload.get("catalog") or "").strip()
        schema_name = str(payload.get("schema") or "").strip()
        persona = str(payload.get("persona") or "Analyst").strip() or "Analyst"
        history = self.normalize_ask_history(payload.get("history"))

        # Same data-access gates as the SQL editor: Ask Trino reads schema
        # context and runs the generated SQL through the normal query path.
        if cluster_id is not None:
            self.require_cluster_access(user, cluster_id)
        if catalog:
            self.require_catalog_access(user, catalog)

        context = self.ask_context(cluster_id, catalog, schema_name)
        system_prompt = self.build_ask_system_prompt(persona, catalog, schema_name, context)
        content = self.call_ask_llm(system_prompt, history, question)
        parsed = parse_llm_json(content)

        chart_type = str(parsed.get("chartType") or "none").strip().lower()
        if chart_type not in ASK_TRINO_CHART_TYPES:
            chart_type = "none"
        result: dict[str, Any] = {
            "explanation": str(parsed.get("explanation") or "").strip(),
            "sql": None,
            "chartType": chart_type,
            "clarifyingQuestion": None,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "truncated": False,
            "query_id": None,
            "status": None,
            "pending_cluster_start": False,
            "error": None,
        }

        sql = parsed.get("sql")
        sql_text = str(sql).strip() if sql else ""
        clarifying = parsed.get("clarifyingQuestion")
        if isinstance(clarifying, dict) and not sql_text:
            result["clarifyingQuestion"] = self.sanitize_clarifying_question(clarifying)
            return result
        if not sql_text:
            if not result["explanation"]:
                result["explanation"] = "I couldn't turn that into a query. Try rephrasing your question."
            return result

        statement = validate_read_only_sql(sql_text)
        result["sql"] = statement
        if cluster_id is None:
            result["error"] = "Pick a running cluster to run the generated SQL."
            return result

        try:
            run = self.create_query(
                {"cluster_id": cluster_id, "catalog": catalog, "schema": schema_name, "sql": statement},
                user,
            )
        except ApiError as exc:
            result["error"] = exc.message
            return result

        query = run.get("query", {})
        query_id = query.get("id")
        result["query_id"] = query_id
        status = query.get("status")
        polls = 0
        while status in {"Queued", "Running"} and query_id is not None and polls < ASK_TRINO_MAX_POLLS:
            polls += 1
            time.sleep(0.4)
            try:
                query = self.get_query(query_id, user).get("query", {})
            except ApiError:
                break
            status = query.get("status")

        if status == "Failed":
            result["error"] = query.get("error_message") or "The query failed to run."
        result["status"] = status
        result["cached"] = bool(query.get("cache_hit"))
        result["result_cached_at"] = query.get("result_cached_at") or None
        # The cluster was auto-suspended: create_query queued the SQL and kicked off
        # a resume. Surface that so the browser can show "Starting cluster" and keep
        # polling the query until the cluster is Running and it dispatches.
        result["pending_cluster_start"] = bool(query.get("pending_cluster_start"))
        result["columns"] = query.get("columns", [])
        result["rows"] = query.get("data", [])
        result["row_count"] = query.get("total_row_count") or query.get("row_count") or len(result["rows"])
        result["truncated"] = bool(query.get("truncated"))
        return result

    @staticmethod
    def normalize_ask_history(history: Any) -> list[dict[str, str]]:
        if not isinstance(history, list):
            return []
        turns: list[dict[str, str]] = []
        for item in history:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").lower()
            role = "assistant" if role in {"ai", "assistant"} else "user"
            text = str(item.get("text") or item.get("content") or "").strip()
            if text:
                turns.append({"role": role, "content": text[:4000]})
        return turns[-ASK_TRINO_HISTORY_MAX:]

    @staticmethod
    def sanitize_clarifying_question(clarifying: dict[str, Any]) -> dict[str, Any]:
        options = clarifying.get("options")
        clean_options = [str(opt).strip() for opt in options if str(opt).strip()] if isinstance(options, list) else []
        return {
            "question": str(clarifying.get("question") or "Could you clarify your question?").strip(),
            "options": clean_options[:12],
            "optionType": str(clarifying.get("optionType") or "custom").strip() or "custom",
            "includeAllOption": bool(clarifying.get("includeAllOption")),
        }

    def ask_context(self, cluster_id: int | None, catalog: str, schema_name: str) -> dict[str, Any]:
        """Best-effort metadata for the prompt. Never raises — a cluster that is not
        Running just yields an empty schema block (the model can still answer)."""
        context: dict[str, Any] = {
            "cluster_name": "",
            "status": "",
            "catalogs": [],
            "schemas": [],
            "schema_block": "",
        }
        if cluster_id is None:
            return context
        try:
            meta = self.cluster_metadata(cluster_id)
        except ApiError:
            return context
        context["cluster_name"] = meta["cluster"]["name"]
        context["status"] = meta["cluster"]["status"]
        context["catalogs"] = [str(c["name"]) for c in meta.get("catalogs", [])]
        if catalog:
            try:
                cat_meta = self.cluster_metadata(cluster_id, catalog=catalog)
                context["schemas"] = [str(s["name"]) for s in cat_meta.get("schemas", [])]
            except ApiError:
                pass
        if catalog and schema_name:
            context["schema_block"] = self.ask_schema_block(cluster_id, catalog, schema_name)
        return context

    def ask_schema_block(self, cluster_id: int, catalog: str, schema_name: str) -> str:
        """A compact `table (col type, ...)` listing for the selected schema, built
        from a single information_schema.columns query."""
        try:
            with self.conn() as conn:
                coordinator = conn.execute(
                    """
                    SELECT * FROM provider_resources
                    WHERE cluster_id = ? AND resource_type = 'coordinator_instance'
                    ORDER BY id DESC LIMIT 1
                    """,
                    (cluster_id,),
                ).fetchone()
            if not coordinator:
                return ""
            endpoint = self.coordinator_endpoint(row_to_dict(coordinator))
            quoted_catalog = self.trino_identifier(catalog)
            schema_literal = self.trino_string_literal(schema_name)
            rows, _ = self.run_trino_metadata_query(
                endpoint,
                (
                    f"SELECT table_name, column_name, data_type "
                    f"FROM {quoted_catalog}.information_schema.columns "
                    f"WHERE table_schema = {schema_literal} ORDER BY table_name, ordinal_position"
                ),
            )
        except ApiError:
            return ""
        tables: dict[str, list[str]] = {}
        for row in rows:
            if len(row) < 3:
                continue
            tables.setdefault(str(row[0]), []).append(f"{row[1]} {row[2]}")
        lines: list[str] = []
        for index, (table_name, columns) in enumerate(tables.items()):
            if index >= ASK_TRINO_SCHEMA_TABLE_LIMIT:
                lines.append("- … (more tables omitted)")
                break
            lines.append(f"- {catalog}.{schema_name}.{table_name} ({', '.join(columns)})")
        return "\n".join(lines)

    def build_ask_system_prompt(
        self, persona: str, catalog: str, schema_name: str, context: dict[str, Any]
    ) -> str:
        catalogs = ", ".join(context.get("catalogs") or []) or "(none attached)"
        schemas = ", ".join(context.get("schemas") or []) or "(unknown — ask the user)"
        schema_block = context.get("schema_block") or "(schema not loaded — ask a clarifying question if you need table names)"
        selected = []
        if catalog:
            selected.append(f"catalog `{catalog}`")
        if schema_name:
            selected.append(f"schema `{schema_name}`")
        selected_text = ", ".join(selected) if selected else "no catalog/schema selected yet"
        return (
            f"You are Ask Trino, a focused analytics assistant for the TrinoHub data platform. "
            f"You help a {persona} answer business questions by writing Trino SQL. "
            f"You ONLY answer questions about querying this data — you are not a general assistant.\n\n"
            f"Today's date is {utc_now()[:10]}. Resolve relative dates (yesterday, last 7 days) against it.\n\n"
            f"Connection context: cluster '{context.get('cluster_name') or 'unknown'}' "
            f"(status: {context.get('status') or 'unknown'}); {selected_text}.\n"
            f"Available catalogs: {catalogs}.\n"
            f"Schemas in the selected catalog: {schemas}.\n"
            f"Tables in the selected schema:\n{schema_block}\n\n"
            f"Rules for the SQL you generate:\n"
            f"- Trino SQL dialect only. Fully-qualify every table as catalog.schema.table.\n"
            f"- Read-only: a single SELECT (optionally starting with WITH). Never INSERT, UPDATE, "
            f"DELETE, CREATE, DROP, ALTER, or any other statement. No semicolons or multiple statements.\n"
            f"- Add a sensible LIMIT (default 100) unless the question is an aggregate that returns few rows.\n"
            f"- Prefer explicit column lists and clear aliases for readability.\n\n"
            f"If the question is ambiguous (e.g. it needs a specific schema, table, or time range you cannot "
            f"infer), return a clarifyingQuestion instead of guessing. Only offer options that come from the "
            f"context above (real catalog/schema names) — never invent names.\n\n"
            f"Respond with ONLY a JSON object, no markdown fences, in exactly this shape:\n"
            f'{{"explanation": "natural-language answer describing what the query returns", '
            f'"sql": "SELECT ... or null", '
            f'"chartType": "bar | line | pie | none", '
            f'"clarifyingQuestion": {{"question": "...", "options": ["..."], '
            f'"optionType": "catalog | schema | date_range | custom", "includeAllOption": false}} or null}}\n'
            f"Pick chartType by the result shape: a category + one numeric column → bar; a time series → line; "
            f"parts of a whole → pie; otherwise none. Set sql to null when you return a clarifyingQuestion."
        )

    def call_ask_llm(
        self, system_prompt: str, history: list[dict[str, str]], question: str
    ) -> str:
        api_key = os.environ.get("ASK_TRINO_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ApiError(
                503,
                "Ask Trino is not configured. Set OPENROUTER_API_KEY (or ASK_TRINO_API_KEY) to enable the assistant.",
            )
        api_base = os.environ.get("ASK_TRINO_API_BASE", ASK_TRINO_DEFAULT_API_BASE)
        # Operator-chosen model (Settings) wins over ASK_TRINO_MODEL / the default.
        model = self.ask_trino_settings()["effective_model"]
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": question})
        body = json.dumps(
            {
                "model": model,
                "messages": messages,
                "max_tokens": ASK_TRINO_MAX_TOKENS,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            api_base,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "X-Title": "TrinoHub Ask Trino",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=ASK_TRINO_TIMEOUT_SECONDS) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            # Surface something actionable but never echo the request (it
            # carries the API key). Map the common provider statuses to what
            # an operator can actually do about them.
            if exc.code in (401, 403):
                hint = (
                    "The AI provider rejected the API key. Check OPENROUTER_API_KEY "
                    "(or ASK_TRINO_API_KEY) in the server environment."
                )
            elif exc.code == 404:
                hint = (
                    f"The AI provider does not recognise the model '{model}'. "
                    "Set a valid OpenRouter model id in Settings → Ask Trino."
                )
            elif exc.code == 429:
                hint = "The AI provider is rate-limiting requests. Try again in a moment."
            elif exc.code >= 500:
                hint = "The AI provider is having trouble right now. Try again in a moment."
            else:
                hint = f"The assistant request failed (HTTP {exc.code})."
            raise ApiError(502, hint) from exc
        except urllib.error.URLError as exc:
            raise ApiError(502, f"The assistant endpoint is unreachable: {exc.reason}") from exc
        try:
            data = json.loads(raw)
            return str(data["choices"][0]["message"]["content"])
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise ApiError(502, "The assistant returned an unexpected response.") from exc
