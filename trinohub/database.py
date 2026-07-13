from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL DEFAULT '',
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
  is_active INTEGER NOT NULL DEFAULT 1,
  is_service INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  token_hash TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

-- RBAC: custom roles carrying a set of coarse privileges (see server.py
-- ALL_PRIVILEGES). The seeded ``admin``/``user`` roles are is_system=1 and
-- keep pre-RBAC databases working unchanged; users.role remains as the legacy
-- shortcut and is kept in sync for the seeded roles.
CREATE TABLE IF NOT EXISTS roles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL DEFAULT '',
  is_system INTEGER NOT NULL DEFAULT 0,
  privileges_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_roles (
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);

-- Data-access grants attached to roles: which clusters/catalogs a role's
-- members may query and browse. ``target`` is a cluster id (as text) or a
-- catalog name; '*' grants everything of that type.
CREATE TABLE IF NOT EXISTS role_grants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  grant_type TEXT NOT NULL CHECK (grant_type IN ('cluster', 'catalog')),
  target TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (role_id, grant_type, target)
);

-- Long-lived bearer tokens for headless API access (scripts, BI tools,
-- Terraform-style automation). Only the SHA-256 hash is stored; the plaintext
-- token is shown once at creation. A token authenticates as its user (often a
-- service-account user) and inherits that user's roles/grants.
CREATE TABLE IF NOT EXISTS api_tokens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_by TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  expires_at TEXT,
  last_used_at TEXT
);

-- Recurring SQL jobs (Phase 3). Each execution submits through the normal
-- create_query path as ``run_as_user_id`` (often a service account), so the
-- run inherits that user's cluster/catalog grants. One retry on failure.
CREATE TABLE IF NOT EXISTS scheduled_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  sql_text TEXT NOT NULL,
  cluster_id INTEGER NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
  catalog TEXT NOT NULL DEFAULT '',
  schema_name TEXT NOT NULL DEFAULT '',
  run_as_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
  schedule_type TEXT NOT NULL CHECK (schedule_type IN ('interval', 'cron')),
  interval_minutes INTEGER,
  cron_expression TEXT NOT NULL DEFAULT '',
  enabled INTEGER NOT NULL DEFAULT 1,
  next_run_at TEXT,
  last_run_at TEXT,
  last_status TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduled_job_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id INTEGER NOT NULL REFERENCES scheduled_jobs(id) ON DELETE CASCADE,
  query_id INTEGER REFERENCES query_runs(id) ON DELETE SET NULL,
  attempt INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL,
  error TEXT NOT NULL DEFAULT '',
  started_at TEXT NOT NULL,
  finished_at TEXT
);

-- Sharing saved queries and notebooks with roles (Phase 3). ``access`` is
-- ordered view < run < edit; owners implicitly hold edit.
CREATE TABLE IF NOT EXISTS entity_shares (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('saved_query', 'notebook')),
  entity_id INTEGER NOT NULL,
  role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  access TEXT NOT NULL CHECK (access IN ('view', 'run', 'edit')),
  created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
  created_at TEXT NOT NULL,
  UNIQUE (entity_type, entity_id, role_id)
);

-- Server-side table/column metadata cache, filled opportunistically as users
-- browse live clusters. Powers editor autocomplete, global search, and the
-- schema browser fallback when a cluster is suspended.
CREATE TABLE IF NOT EXISTS metadata_cache (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cluster_id INTEGER NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
  catalog TEXT NOT NULL,
  schema_name TEXT NOT NULL,
  table_name TEXT NOT NULL,
  table_type TEXT NOT NULL DEFAULT 'TABLE',
  columns_json TEXT NOT NULL DEFAULT '[]',
  updated_at TEXT NOT NULL,
  UNIQUE (cluster_id, catalog, schema_name, table_name)
);

-- Time-series utilization samples (Phase 5), written by the background poller
-- for every Running cluster and pruned after a retention window. Powers the
-- cluster-detail charts and the Prometheus /metrics endpoint.
CREATE TABLE IF NOT EXISTS cluster_stats_samples (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cluster_id INTEGER NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
  sampled_at TEXT NOT NULL,
  running_queries INTEGER,
  queued_queries INTEGER,
  active_workers INTEGER,
  desired_capacity INTEGER,
  avg_worker_cpu REAL,
  cache_hit_rate REAL
);
CREATE INDEX IF NOT EXISTS idx_cluster_stats_samples
  ON cluster_stats_samples (cluster_id, sampled_at);

-- Fine-grained data policies (Phase 6): per-role grants below catalog level,
-- rendered into Trino's file-based system access control at node bootstrap.
-- Semantics: a user whose roles carry ANY policy is restricted to the union
-- of those policies (plus system schemas); users in policy-free roles keep
-- full access. Empty schema/table = all. allowed/denied columns, a row
-- filter, and per-column mask expressions apply to matching tables.
CREATE TABLE IF NOT EXISTS data_policies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  catalog TEXT NOT NULL,
  schema_name TEXT NOT NULL DEFAULT '',
  table_name TEXT NOT NULL DEFAULT '',
  privileges_json TEXT NOT NULL DEFAULT '["SELECT"]',
  allowed_columns_json TEXT NOT NULL DEFAULT '[]',
  denied_columns_json TEXT NOT NULL DEFAULT '[]',
  row_filter TEXT NOT NULL DEFAULT '',
  column_masks_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- Entity tags (catalog.schema.table.column paths). The PII classifier
-- proposes tags; admins accept them. Tag policies act on accepted tags only.
CREATE TABLE IF NOT EXISTS entity_tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity TEXT NOT NULL,
  tag TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'accepted' CHECK (status IN ('proposed', 'accepted')),
  source TEXT NOT NULL DEFAULT 'manual',
  created_at TEXT NOT NULL,
  UNIQUE (entity, tag)
);

-- ABAC: columns carrying ``tag`` are denied or masked (NULL) for the role.
CREATE TABLE IF NOT EXISTS tag_policies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tag TEXT NOT NULL,
  role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  effect TEXT NOT NULL DEFAULT 'deny' CHECK (effect IN ('deny', 'mask')),
  created_at TEXT NOT NULL,
  UNIQUE (tag, role_id, effect)
);

-- Append-only record of security-relevant admin mutations (who/what/when,
-- with a before/after detail blob). Never updated or deleted by the app.
CREATE TABLE IF NOT EXISTS security_audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_user_id INTEGER,
  actor_username TEXT NOT NULL DEFAULT '',
  action TEXT NOT NULL,
  target TEXT NOT NULL DEFAULT '',
  detail_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);

-- First-run setup, generalized across cloud providers. ``provider`` is the
-- discriminator (see cloud_provider.KNOWN_PROVIDERS); ``region`` and the
-- allowed-* policies are provider-neutral, so they stay top-level. Everything
-- that only makes sense for one provider (AWS: vpc_id, private_subnet_ids,
-- cluster_security_group_id, node_instance_profile) lives in the
-- ``provider_config_json`` blob so a second provider adds its own shape without
-- a schema change. ``provider_identity``/``provider_validation`` hold the
-- "who am I authed as" + credential-validation result for whichever provider.
CREATE TABLE IF NOT EXISTS setup_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  provider TEXT NOT NULL DEFAULT 'aws',
  region TEXT NOT NULL,
  provider_config_json TEXT NOT NULL DEFAULT '{}',
  allowed_ui_cidrs TEXT NOT NULL,
  provider_identity TEXT NOT NULL,
  provider_validation TEXT NOT NULL,
  allowed_instance_types TEXT NOT NULL DEFAULT '[]',
  cluster_base_domain TEXT NOT NULL DEFAULT '',
  completed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS catalogs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  type TEXT NOT NULL,
  config_json TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clusters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  preset TEXT NOT NULL DEFAULT '',
  instance_type TEXT NOT NULL DEFAULT '',
  region TEXT NOT NULL,
  worker_mode TEXT NOT NULL,
  min_workers INTEGER NOT NULL,
  max_workers INTEGER NOT NULL,
  auto_suspend_minutes INTEGER,
  hostname TEXT NOT NULL DEFAULT '',
  trino_version TEXT NOT NULL DEFAULT '',
  accelerated INTEGER NOT NULL DEFAULT 0,
  catalogs_json TEXT NOT NULL,
  owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS query_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  cluster_id INTEGER REFERENCES clusters(id) ON DELETE SET NULL,
  cluster_name TEXT NOT NULL DEFAULT '',
  sql_text TEXT NOT NULL,
  status TEXT NOT NULL,
  trino_query_id TEXT NOT NULL DEFAULT '',
  next_uri TEXT NOT NULL DEFAULT '',
  catalog TEXT NOT NULL DEFAULT '',
  schema_name TEXT NOT NULL DEFAULT '',
  columns_json TEXT NOT NULL DEFAULT '[]',
  data_json TEXT NOT NULL DEFAULT '[]',
  download_data_json TEXT NOT NULL DEFAULT '[]',
  elapsed_ms INTEGER NOT NULL DEFAULT 0,
  row_count INTEGER NOT NULL DEFAULT 0,
  total_row_count INTEGER NOT NULL DEFAULT 0,
  download_row_count INTEGER NOT NULL DEFAULT 0,
  truncated INTEGER NOT NULL DEFAULT 0,
  download_truncated INTEGER NOT NULL DEFAULT 0,
  result_bytes INTEGER NOT NULL DEFAULT 0,
  error_message TEXT NOT NULL DEFAULT '',
  pending_cluster_start INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS query_tabs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  sql_text TEXT NOT NULL DEFAULT '',
  cluster_id INTEGER REFERENCES clusters(id) ON DELETE SET NULL,
  catalog TEXT NOT NULL DEFAULT '',
  schema_name TEXT NOT NULL DEFAULT '',
  run_mode TEXT NOT NULL DEFAULT 'current',
  position INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS saved_queries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  sql_text TEXT NOT NULL,
  cluster_id INTEGER REFERENCES clusters(id) ON DELETE SET NULL,
  catalog TEXT NOT NULL DEFAULT '',
  schema_name TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- Jupyter/Databricks-style notebooks: an ordered document of SQL cells. The
-- notebook holds the default execution context; each cell may override it. Cells
-- reuse the existing /api/query path, so no results are persisted here.
CREATE TABLE IF NOT EXISTS notebooks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  cluster_id INTEGER REFERENCES clusters(id) ON DELETE SET NULL,
  catalog TEXT NOT NULL DEFAULT '',
  schema_name TEXT NOT NULL DEFAULT '',
  position INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notebook_cells (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  notebook_id INTEGER NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
  position INTEGER NOT NULL DEFAULT 0,
  sql_text TEXT NOT NULL DEFAULT '',
  cluster_id INTEGER REFERENCES clusters(id) ON DELETE SET NULL,
  catalog TEXT NOT NULL DEFAULT '',
  schema_name TEXT NOT NULL DEFAULT '',
  view_pref TEXT NOT NULL DEFAULT 'table',
  chart_config_json TEXT NOT NULL DEFAULT '{}',
  -- Last query_runs row this cell produced, so reopening a notebook can
  -- restore the cell's results instead of an empty placeholder.
  last_query_id INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cluster_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cluster_id INTEGER REFERENCES clusters(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  message TEXT NOT NULL,
  metadata_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scaling_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cluster_id INTEGER REFERENCES clusters(id) ON DELETE CASCADE,
  direction TEXT NOT NULL,
  from_workers INTEGER NOT NULL,
  to_workers INTEGER NOT NULL,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Cloud resources the control plane provisions for a cluster (coordinator
-- instance, worker launch template, auto scaling group, security group, ...),
-- tracked so teardown can find and delete exactly what was created. Generalized
-- across providers via the ``provider`` discriminator; ``resource_id`` is opaque
-- (EC2 id / ARN / Azure resource id / GCP resource name) and only ever handed
-- back to the same provider.
CREATE TABLE IF NOT EXISTS provider_resources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cluster_id INTEGER REFERENCES clusters(id) ON DELETE CASCADE,
  provider TEXT NOT NULL DEFAULT 'aws',
  resource_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  region TEXT NOT NULL,
  metadata_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (resource_type, resource_id)
);

-- First-run bootstrap token. While setup is incomplete, the control plane mints
-- a one-time token (printed to the log + written to a root-only file) that must
-- be presented to /api/setup/complete, so a network attacker can't win the
-- first-admin race on a freshly exposed instance. Only the hash is stored.
CREATE TABLE IF NOT EXISTS bootstrap_token (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  token_hash TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Per-cluster signed bootstrap URLs for EC2 node startup. The plaintext token is
-- embedded only in EC2 user data; SQLite stores the hash used to authorize
-- /api/node-config/:cluster_id while a cluster is starting/running.
CREATE TABLE IF NOT EXISTS cluster_bootstrap_tokens (
  cluster_id INTEGER PRIMARY KEY REFERENCES clusters(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Persisted autoscaler / auto-suspend timers so idle counters survive a service
-- restart (otherwise frequent restarts reset the clocks and auto-suspend never
-- fires). One row per cluster; columns default so each subsystem can upsert only
-- its own fields without clobbering the other's.
CREATE TABLE IF NOT EXISTS cluster_timer_state (
  cluster_id INTEGER PRIMARY KEY REFERENCES clusters(id) ON DELETE CASCADE,
  auto_suspend_idle_since TEXT,
  autoscale_queued_intervals INTEGER NOT NULL DEFAULT 0,
  autoscale_cpu_high_intervals INTEGER NOT NULL DEFAULT 0,
  autoscale_idle_low_since TEXT,
  updated_at TEXT NOT NULL
);

-- Operator-uploaded JDBC driver JARs for connectors whose driver cannot be
-- bundled (e.g. Oracle, for licensing reasons). The JAR bytes live on the
-- control-plane disk under <db_dir>/drivers/; SQLite stores only metadata and
-- the SHA-256 that each node re-verifies after downloading the driver into its
-- Trino plugin directory at boot. One row per connector type (re-upload
-- replaces).
CREATE TABLE IF NOT EXISTS connector_drivers (
  connector_type TEXT PRIMARY KEY,
  filename TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  uploaded_by TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- A native Trino wire query (CLI/JDBC/BI) that arrives at a suspended cluster's
-- gateway host is held here while the cluster resumes, then replayed to the
-- coordinator. Each row captures one client's initial POST /v1/statement: the SQL
-- body and the full request header set (which can include Authorization/session
-- state, so rows are short-lived and swept on a TTL). One row per in-flight
-- wire query, keyed by an opaque shim id embedded in the holding nextUri.
CREATE TABLE IF NOT EXISTS wire_pending (
  shim_id TEXT PRIMARY KEY,
  cluster_id INTEGER NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
  host TEXT NOT NULL,
  sql_body BLOB NOT NULL,
  headers_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);
"""


BUILT_IN_CATALOGS = (
    ("system", "builtin", {"description": "Cluster metadata"}),
    ("tpch", "builtin", {"description": "TPC-H sample data"}),
    ("tpcds", "builtin", {"description": "TPC-DS sample data"}),
)


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        result = super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return result


MIGRATIONS = {
    "query_runs": {
        "cluster_name": "TEXT NOT NULL DEFAULT ''",
        "trino_query_id": "TEXT NOT NULL DEFAULT ''",
        "next_uri": "TEXT NOT NULL DEFAULT ''",
        "catalog": "TEXT NOT NULL DEFAULT ''",
        "schema_name": "TEXT NOT NULL DEFAULT ''",
        "columns_json": "TEXT NOT NULL DEFAULT '[]'",
        "data_json": "TEXT NOT NULL DEFAULT '[]'",
        "download_data_json": "TEXT NOT NULL DEFAULT '[]'",
        "total_row_count": "INTEGER NOT NULL DEFAULT 0",
        "download_row_count": "INTEGER NOT NULL DEFAULT 0",
        "truncated": "INTEGER NOT NULL DEFAULT 0",
        "download_truncated": "INTEGER NOT NULL DEFAULT 0",
        "result_bytes": "INTEGER NOT NULL DEFAULT 0",
        "pending_cluster_start": "INTEGER NOT NULL DEFAULT 0",
        # Result cache (issue #1). ``cache_key`` is set on fresh cacheable runs
        # (sha256 over user/cluster/catalog/schema/normalized SQL); cache-served
        # runs carry ``cache_hit`` plus a pointer to the source run and the time
        # its results were produced.
        "cache_key": "TEXT NOT NULL DEFAULT ''",
        "cache_hit": "INTEGER NOT NULL DEFAULT 0",
        "cached_from_query_id": "INTEGER",
        "result_cached_at": "TEXT NOT NULL DEFAULT ''",
    },
    "query_tabs": {
        "run_mode": "TEXT NOT NULL DEFAULT 'current'",
    },
    "notebook_cells": {
        "last_query_id": "INTEGER",
    },
    "clusters": {
        "instance_type": "TEXT NOT NULL DEFAULT ''",
        "hostname": "TEXT NOT NULL DEFAULT ''",
        "trino_version": "TEXT NOT NULL DEFAULT ''",
        "accelerated": "INTEGER NOT NULL DEFAULT 0",
        # Keep-warm windows during which auto-suspend is suppressed.
        "uptime_schedule_json": "TEXT NOT NULL DEFAULT '[]'",
    },
    "setup_settings": {
        "cluster_base_domain": "TEXT NOT NULL DEFAULT ''",
        # OIDC SSO provider config (issuer, client id/secret ref, group->role
        # mapping, password-login policy). Empty object = SSO disabled.
        "oidc_config_json": "TEXT NOT NULL DEFAULT '{}'",
        # Browser session lifetime; NULL/absent falls back to the 12 h default.
        "session_hours": "INTEGER",
        # Notification channel config (webhook URL + subscribed events).
        "notification_config_json": "TEXT NOT NULL DEFAULT '{}'",
        # Ask Trino assistant config (the OpenRouter model id operators paste in).
        # Empty object = fall back to ASK_TRINO_MODEL env / built-in default.
        "ask_trino_config_json": "TEXT NOT NULL DEFAULT '{}'",
        # Result-cache TTL in minutes; NULL falls back to the 10-minute default,
        # 0 disables serving cached results.
        "result_cache_ttl_minutes": "INTEGER",
    },
    "users": {
        # Service accounts authenticate only via API tokens, never a password.
        "is_service": "INTEGER NOT NULL DEFAULT 0",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def loads(value: str, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL lets the background poller write while readers/queries proceed; the
    # busy timeout makes brief write contention retry instead of failing with
    # "database is locked".
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db(db_path: str | Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        apply_migrations(conn)
        now = utc_now()
        for name, catalog_type, config in BUILT_IN_CATALOGS:
            conn.execute(
                """
                INSERT OR IGNORE INTO catalogs
                  (name, type, config_json, enabled, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (name, catalog_type, dumps(config), now, now),
            )


def apply_migrations(conn: sqlite3.Connection) -> None:
    _migrate_provider_generalization(conn)
    for table, columns in MIGRATIONS.items():
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, definition in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return row is not None


def _migrate_provider_generalization(conn: sqlite3.Connection) -> None:
    """Migrate a pre-multi-cloud database to the provider-generalized schema.

    Two structural changes, both idempotent:

    * ``setup_settings`` had AWS-specific top-level columns (``vpc_id``,
      ``private_subnet_ids``, ``cluster_security_group_id``,
      ``node_instance_profile``) plus ``aws_identity``/``aws_validation``. The AWS
      columns move into a ``provider_config_json`` blob under a ``provider``
      discriminator; the identity/validation columns are renamed to
      ``provider_*``. Detected by the presence of the old ``vpc_id`` column.
    * The ``aws_resources`` table becomes ``provider_resources`` with a
      ``provider`` column. Its rows are copied over (tagged ``aws``) and the old
      table dropped. ``CREATE TABLE IF NOT EXISTS`` in SCHEMA has already created
      the empty ``provider_resources`` table by the time this runs.
    """
    if _table_exists(conn, "setup_settings") and "vpc_id" in _table_columns(conn, "setup_settings"):
        old = conn.execute("SELECT * FROM setup_settings WHERE id = 1").fetchone()
        conn.execute("ALTER TABLE setup_settings RENAME TO setup_settings_old")
        conn.executescript(_SETUP_SETTINGS_DDL)
        if old is not None:
            provider_config = dumps(
                {
                    "vpc_id": old["vpc_id"],
                    "private_subnet_ids": loads(old["private_subnet_ids"], []),
                    "cluster_security_group_id": old["cluster_security_group_id"],
                    "node_instance_profile": old["node_instance_profile"],
                }
            )
            conn.execute(
                """
                INSERT INTO setup_settings
                  (id, provider, region, provider_config_json, allowed_ui_cidrs,
                   provider_identity, provider_validation, allowed_instance_types, completed_at)
                VALUES (1, 'aws', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    old["region"],
                    provider_config,
                    old["allowed_ui_cidrs"],
                    old["aws_identity"],
                    old["aws_validation"],
                    old["allowed_instance_types"] if "allowed_instance_types" in old.keys() else "[]",
                    old["completed_at"],
                ),
            )
        conn.execute("DROP TABLE setup_settings_old")

    if _table_exists(conn, "aws_resources"):
        conn.execute(
            """
            INSERT OR IGNORE INTO provider_resources
              (id, cluster_id, provider, resource_type, resource_id, region, metadata_json, created_at)
            SELECT id, cluster_id, 'aws', resource_type, resource_id, region, metadata_json, created_at
            FROM aws_resources
            """
        )
        conn.execute("DROP TABLE aws_resources")


# The current setup_settings definition, extracted from SCHEMA so the migration
# above can recreate the table with an identical shape.
_SETUP_SETTINGS_DDL = """
CREATE TABLE setup_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  provider TEXT NOT NULL DEFAULT 'aws',
  region TEXT NOT NULL,
  provider_config_json TEXT NOT NULL DEFAULT '{}',
  allowed_ui_cidrs TEXT NOT NULL,
  provider_identity TEXT NOT NULL,
  provider_validation TEXT NOT NULL,
  allowed_instance_types TEXT NOT NULL DEFAULT '[]',
  cluster_base_domain TEXT NOT NULL DEFAULT '',
  completed_at TEXT NOT NULL
);
"""


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def public_user(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    keys = row.keys() if isinstance(row, sqlite3.Row) else row
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "is_service": bool(row["is_service"] if "is_service" in keys else 0),
        "created_at": row["created_at"],
    }
