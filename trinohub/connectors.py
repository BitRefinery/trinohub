"""Connector registry: one descriptor per supported catalog type.

Adding a JDBC data source is "add one entry to :data:`REGISTRY`" — its URL
shape, display label, Trino ``connector.name``, and whether it needs a stored
credential all live here as data, instead of being scattered across the
create/update/check guards in ``server.py`` and the node-config renderer in
``aws_checks.py``.

Glue-backed lakehouse catalogs share the ``kind="s3_glue"`` machinery and flow
through one normalizer (``Server.normalize_glue_catalog_config``) and renderer
(``AwsInspector.glue_catalog_properties``). S3 variants authenticate through the
node IAM role; GCS and ADLS Iceberg variants use a stored cross-cloud credential.
The descriptor selects ``connector_name``, ``table_format``, and ``storage_kind``.
Every JDBC type shares a single generic normalizer
(``Server.normalize_jdbc_catalog_config``) and a single generic ``.properties``
renderer (``AwsInspector.jdbc_catalog_properties``), both parameterized by the
descriptor. ``mongodb``, ``elasticsearch``, ``bigquery``, and ``gsheets`` each
have a bespoke ``kind`` with their own normalizer + renderer (``opensearch``
reuses the ``elasticsearch`` pair, parameterized by ``connector_name``).
``bigquery`` and ``gsheets`` are the cross-cloud types, whose stored credential is
a GCP service-account JSON key (``credential_kind="gcp_service_account"``) rather
than a DB password. ``generator`` types (``memory``/``blackhole``/``faker``) are
zero-config: no secret, no config, rendering only ``connector.name=<x>``.

This module is intentionally dependency-free (only ``re`` + ``dataclasses``) so
both ``server`` and ``aws_checks`` can import it without a cycle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectorType:
    type: str  # storage key, e.g. "postgresql"
    label: str  # UI display name
    requires_secret: bool  # gates the secret-store credential path
    # dispatch discriminator: s3_glue | jdbc | mongodb | elasticsearch | bigquery | gsheets | generator
    kind: str = "jdbc"
    # Shape of the stored credential. "password" is a plaintext DB password;
    # "gcp_service_account" is a service-account JSON key (validated as JSON, then
    # base64-rendered into bigquery.credentials-key). Both flow through the same
    # Secrets Manager put/get/delete path — only validation and render differ.
    credential_kind: str = "password"
    icon: str = "database"  # UI card icon hint
    connector_name: str | None = None  # Trino connector.name; None for non-JDBC
    table_format: str | None = None  # Glue-backed lakehouse: ICEBERG | DELTA | HIVE
    # Object storage used by Glue-backed lakehouse catalogs. GCS and ADLS use
    # the same Iceberg + Glue metadata path as S3, but require a stored secret
    # and different native-file-system properties at render time.
    storage_kind: str | None = None  # s3 | gcs | azure
    url_pattern: re.Pattern[str] | None = None  # JDBC URL; host captured as group 1
    url_help: str | None = None  # human-readable URL example for 400 messages
    requires_driver: bool = False  # driver JAR not bundled; operator must upload one
    plugin_dir: str | None = None  # Trino plugin subdir the uploaded JAR is copied into
    # Auth is optional for this type (e.g. Cassandra): a credential is stored only
    # when the operator supplies a username. requires_secret stays False (creation
    # never demands one), but when a username is present a password is required and
    # stored, and the catalog then renders only on the signed node path. Mutually
    # exclusive with requires_secret.
    optional_secret: bool = False

    @property
    def is_jdbc(self) -> bool:
        return self.kind == "jdbc"


# Host is always capture group 1 so the SSRF guard can extract it uniformly.
# PostgreSQL / Redshift / Oracle require a database path; MySQL / MariaDB /
# SingleStore / ClickHouse make it optional (it maps to a Trino schema);
# SQL Server uses ;key=value properties; Snowflake's host is the account.
_PG_URL = re.compile(r"jdbc:postgresql://([^/:?\s]+)(?::\d+)?/[^\s?]+(?:\?\S*)?")
_REDSHIFT_URL = re.compile(r"jdbc:redshift://([^/:?\s]+)(?::\d+)?/[^\s?]+(?:\?\S*)?")
_MYSQL_URL = re.compile(r"jdbc:mysql://([^/:?\s]+)(?::\d+)?(?:/[^\s?]*)?(?:\?\S*)?")
_MARIADB_URL = re.compile(r"jdbc:mariadb://([^/:?\s]+)(?::\d+)?(?:/[^\s?]*)?(?:\?\S*)?")
_SINGLESTORE_URL = re.compile(r"jdbc:singlestore://([^/:?\s]+)(?::\d+)?(?:/[^\s?]*)?(?:\?\S*)?")
_CLICKHOUSE_URL = re.compile(r"jdbc:clickhouse://([^/:?\s]+)(?::\d+)?(?:/[^\s?]*)?(?:\?\S*)?")
_SQLSERVER_URL = re.compile(r"jdbc:sqlserver://([^/:;?\s]+)(?::\d+)?(?:;\S*)?")
_ORACLE_URL = re.compile(r"jdbc:oracle:thin:@//([^/:?\s]+)(?::\d+)?/[^\s?]+")
_SNOWFLAKE_URL = re.compile(r"jdbc:snowflake://([^/:?\s]+)(?:/[^\s?]*)?(?:\?\S*)?")
# Druid speaks Avatica, so the broker host is nested inside the url= parameter
# rather than right after the scheme. Capture that host as group 1 so the SSRF
# guard still sees it; allow an optional trailing ;property=value list.
_DRUID_URL = re.compile(r"jdbc:avatica:remote:url=https?://([^/:?\s]+)(?::\d+)?/[^\s;]*(?:;\S*)?")
# MongoDB shares the connection-URL + user + password shape; the URL must NOT
# embed credentials (the @ is excluded), so the password stays in the secret store.
_MONGODB_URL = re.compile(r"(?:mongodb|mongodb\+srv)://([^/:?@\s]+)(?::\d+)?(?:,[^/?@\s]+)*(?:/[^\s?]*)?(?:\?\S*)?")


REGISTRY: dict[str, ConnectorType] = {
    "s3_glue": ConnectorType(
        type="s3_glue",
        label="S3 + Glue (Iceberg)",
        requires_secret=False,
        kind="s3_glue",
        icon="cloud",
        connector_name="iceberg",
        table_format="ICEBERG",
        storage_kind="s3",
    ),
    "gcs_glue": ConnectorType(
        type="gcs_glue",
        label="Google Cloud Storage + Glue (Iceberg)",
        requires_secret=True,
        kind="s3_glue",
        icon="cloud",
        connector_name="iceberg",
        table_format="ICEBERG",
        storage_kind="gcs",
        credential_kind="gcp_service_account",
    ),
    "adls_glue": ConnectorType(
        type="adls_glue",
        label="Azure Data Lake + Glue (Iceberg)",
        requires_secret=True,
        kind="s3_glue",
        icon="cloud",
        connector_name="iceberg",
        table_format="ICEBERG",
        storage_kind="azure",
        credential_kind="azure_storage_key",
    ),
    "delta_glue": ConnectorType(
        type="delta_glue",
        label="Delta Lake (S3 + Glue)",
        requires_secret=False,
        kind="s3_glue",
        icon="cloud",
        connector_name="delta_lake",
        table_format="DELTA",
        storage_kind="s3",
    ),
    "hive_glue": ConnectorType(
        type="hive_glue",
        label="Hive (S3 + Glue)",
        requires_secret=False,
        kind="s3_glue",
        icon="cloud",
        connector_name="hive",
        table_format="HIVE",
        storage_kind="s3",
    ),
    "hudi_glue": ConnectorType(
        type="hudi_glue",
        label="Hudi (S3 + Glue)",
        requires_secret=False,
        kind="s3_glue",
        icon="cloud",
        connector_name="hudi",
        table_format="HUDI",
        storage_kind="s3",
    ),
    "postgresql": ConnectorType(
        type="postgresql",
        label="PostgreSQL",
        requires_secret=True,
        connector_name="postgresql",
        url_pattern=_PG_URL,
        url_help="jdbc:postgresql://host[:port]/database",
    ),
    "mysql": ConnectorType(
        type="mysql",
        label="MySQL",
        requires_secret=True,
        connector_name="mysql",
        url_pattern=_MYSQL_URL,
        url_help="jdbc:mysql://host[:port][/database]",
    ),
    "redshift": ConnectorType(
        type="redshift",
        label="Amazon Redshift",
        requires_secret=True,
        connector_name="redshift",
        url_pattern=_REDSHIFT_URL,
        url_help="jdbc:redshift://host[:port]/database",
    ),
    "sqlserver": ConnectorType(
        type="sqlserver",
        label="SQL Server",
        requires_secret=True,
        connector_name="sqlserver",
        url_pattern=_SQLSERVER_URL,
        url_help="jdbc:sqlserver://host[:port][;property=value]",
    ),
    "mariadb": ConnectorType(
        type="mariadb",
        label="MariaDB",
        requires_secret=True,
        connector_name="mariadb",
        url_pattern=_MARIADB_URL,
        url_help="jdbc:mariadb://host[:port][/database]",
    ),
    "singlestore": ConnectorType(
        type="singlestore",
        label="SingleStore",
        requires_secret=True,
        connector_name="singlestore",
        url_pattern=_SINGLESTORE_URL,
        url_help="jdbc:singlestore://host[:port][/database]",
    ),
    "clickhouse": ConnectorType(
        type="clickhouse",
        label="ClickHouse",
        requires_secret=True,
        connector_name="clickhouse",
        url_pattern=_CLICKHOUSE_URL,
        url_help="jdbc:clickhouse://host[:port][/database]",
    ),
    "oracle": ConnectorType(
        type="oracle",
        label="Oracle",
        requires_secret=True,
        connector_name="oracle",
        url_pattern=_ORACLE_URL,
        url_help="jdbc:oracle:thin:@//host:port/service",
        # Oracle's JDBC driver is not redistributable, so Trino ships the oracle
        # connector without it. The operator uploads ojdbc; nodes drop it into
        # /opt/trino/plugin/oracle/ at boot.
        requires_driver=True,
        plugin_dir="oracle",
    ),
    "snowflake": ConnectorType(
        type="snowflake",
        label="Snowflake",
        requires_secret=True,
        connector_name="snowflake",
        url_pattern=_SNOWFLAKE_URL,
        url_help="jdbc:snowflake://account.snowflakecomputing.com",
    ),
    "druid": ConnectorType(
        type="druid",
        label="Apache Druid",
        requires_secret=True,
        connector_name="druid",
        url_pattern=_DRUID_URL,
        url_help="jdbc:avatica:remote:url=http://broker:8082/druid/v2/sql/avatica/",
    ),
    "mongodb": ConnectorType(
        type="mongodb",
        label="MongoDB",
        requires_secret=True,
        kind="mongodb",
        connector_name="mongodb",
        url_pattern=_MONGODB_URL,
        url_help="mongodb://host[:port][/database]",
    ),
    "elasticsearch": ConnectorType(
        type="elasticsearch",
        label="Elasticsearch",
        requires_secret=True,
        kind="elasticsearch",
        icon="search",
        connector_name="elasticsearch",
    ),
    "opensearch": ConnectorType(
        type="opensearch",
        label="OpenSearch",
        requires_secret=True,
        # OpenSearch is Elasticsearch's fork: identical config surface, just an
        # opensearch.* property prefix. It shares the elasticsearch normalizer +
        # renderer, parameterized by connector_name.
        kind="elasticsearch",
        icon="search",
        connector_name="opensearch",
    ),
    "cassandra": ConnectorType(
        type="cassandra",
        label="Apache Cassandra",
        # Cassandra auth is optional: a cluster may be open (no credentials) or use
        # PasswordAuthenticator. We store a credential only when a username is given.
        requires_secret=False,
        optional_secret=True,
        kind="cassandra",
        icon="database",
        connector_name="cassandra",
    ),
    "prometheus": ConnectorType(
        type="prometheus",
        label="Prometheus",
        # Like Cassandra, Prometheus auth is optional: an open server needs no
        # credentials, or HTTP basic auth can be enabled (user + password).
        requires_secret=False,
        optional_secret=True,
        kind="prometheus",
        icon="database",
        connector_name="prometheus",
    ),
    "memory": ConnectorType(
        type="memory",
        label="Memory (test tables)",
        requires_secret=False,
        kind="generator",
        connector_name="memory",
    ),
    "blackhole": ConnectorType(
        type="blackhole",
        label="Black Hole (sink)",
        requires_secret=False,
        kind="generator",
        connector_name="blackhole",
    ),
    "faker": ConnectorType(
        type="faker",
        label="Faker (synthetic data)",
        requires_secret=False,
        kind="generator",
        connector_name="faker",
    ),
    "bigquery": ConnectorType(
        type="bigquery",
        label="Google BigQuery",
        requires_secret=True,
        kind="bigquery",
        icon="cloud",
        connector_name="bigquery",
        # Cross-cloud: authenticated by a GCP service-account JSON key, not an AWS
        # IAM role or a DB password. The key is stored in Secrets Manager and
        # rendered as base64 into bigquery.credentials-key on the signed node path.
        credential_kind="gcp_service_account",
    ),
    "gsheets": ConnectorType(
        type="gsheets",
        label="Google Sheets",
        requires_secret=True,
        kind="gsheets",
        icon="cloud",
        connector_name="gsheets",
        # Same GCP service-account JSON key class as BigQuery; rendered as base64
        # into gsheets.credentials-key alongside gsheets.metadata-sheet-id.
        credential_kind="gcp_service_account",
    ),
}

# Derived membership sets, kept in sync with REGISTRY by construction.
CREDENTIALED_CATALOG_TYPES = frozenset(t for t, spec in REGISTRY.items() if spec.requires_secret)
# Types whose auth (and stored credential) is optional — present only when the
# operator supplies a username. Disjoint from CREDENTIALED_CATALOG_TYPES.
OPTIONAL_SECRET_CATALOG_TYPES = frozenset(t for t, spec in REGISTRY.items() if spec.optional_secret)
JDBC_CATALOG_TYPES = frozenset(t for t, spec in REGISTRY.items() if spec.is_jdbc)
DRIVER_REQUIRED_TYPES = frozenset(t for t, spec in REGISTRY.items() if spec.requires_driver)


# ---------------------------------------------------------------------------
# UI form schema (served by GET /api/connector-types)
#
# The registry is the single source of truth for the Add-Catalog form: the API
# derives each type's picker group, suggested name, and field list here so the
# browser never hand-maintains a parallel copy. Server-side validation in
# ``server.py`` remains authoritative; these schemas only drive form rendering.
# ---------------------------------------------------------------------------

# Picker group shown in the connector chooser, by dispatch kind.
_UI_GROUP_BY_KIND = {
    "s3_glue": "Object storage",
    "jdbc": "Databases",
    "mongodb": "Document & search",
    "elasticsearch": "Document & search",
    "cassandra": "Databases",
    "prometheus": "Databases",
    "bigquery": "Google Cloud",
    "gsheets": "Google Cloud",
    "generator": "Test & sample data",
}

# Suggested catalog name when starting a new catalog of each type.
_UI_DEFAULT_NAME = {
    "s3_glue": "analytics_s3",
    "gcs_glue": "analytics_gcs",
    "adls_glue": "analytics_adls",
    "delta_glue": "analytics_delta",
    "hive_glue": "analytics_hive",
    "hudi_glue": "analytics_hudi",
    "postgresql": "warehouse_pg",
    "mysql": "warehouse_mysql",
    "redshift": "warehouse_redshift",
    "sqlserver": "warehouse_sqlserver",
    "mariadb": "warehouse_mariadb",
    "singlestore": "warehouse_singlestore",
    "clickhouse": "warehouse_clickhouse",
    "oracle": "warehouse_oracle",
    "snowflake": "warehouse_snowflake",
    "druid": "warehouse_druid",
    "mongodb": "docs_mongo",
    "elasticsearch": "logs_es",
    "opensearch": "logs_os",
    "cassandra": "warehouse_cassandra",
    "prometheus": "metrics_prometheus",
    "bigquery": "warehouse_bigquery",
    "gsheets": "sheets",
    "memory": "scratch",
    "blackhole": "sink",
    "faker": "sample_data",
}

_TABLE_FORMAT_LABEL = {"ICEBERG": "Iceberg", "DELTA": "Delta Lake", "HIVE": "Hive", "HUDI": "Hudi"}


def _form_fields(spec: ConnectorType) -> list[dict[str, object]]:
    """Non-secret config fields the form should render for ``spec``."""
    kind = spec.kind
    if kind == "s3_glue":
        storage_kind = spec.storage_kind or "s3"
        warehouse = {
            "s3": ("S3 warehouse location", "s3://company-lakehouse/warehouse/"),
            "gcs": ("GCS warehouse location", "gs://company-lakehouse/warehouse/"),
            "azure": (
                "ADLS warehouse location",
                "abfss://warehouse@companylake.dfs.core.windows.net/iceberg/",
            ),
        }[storage_kind]
        fields: list[dict[str, object]] = [
            {"name": "glue_region", "label": "Glue region", "input": "region", "required": True, "default": "us-east-2"},
            {"name": "warehouse", "label": warehouse[0], "input": "text", "required": True,
             "placeholder": warehouse[1], "full_width": True},
            {"name": "default_schema", "label": "Default schema", "input": "text", "default": "default"},
            {"name": "table_format", "label": "Default table format", "input": "readonly",
             "value": _TABLE_FORMAT_LABEL.get(spec.table_format or "", spec.table_format or "")},
        ]
        if storage_kind == "gcs":
            fields.insert(2, {"name": "project_id", "label": "GCP project ID", "input": "text",
                              "required": True, "placeholder": "my-analytics-project"})
        # Hudi is query-only in Trino, so read/write access mode does not apply.
        if spec.connector_name != "hudi":
            fields.append({"name": "access_mode", "label": "Access mode", "input": "select",
                           "options": ["Read and write", "Read only"], "default": "Read and write"})
        return fields
    if kind in ("jdbc", "mongodb"):
        return [
            {"name": "connection_url", "label": "Connection URL", "input": "text", "required": True,
             "placeholder": spec.url_help, "help": spec.url_help, "full_width": True},
            {"name": "connection_user", "label": "Connection user", "input": "text", "required": True,
             "placeholder": "trino_reader"},
        ]
    if kind == "elasticsearch":
        return [
            {"name": "host", "label": "Host", "input": "text", "required": True,
             "placeholder": "search.internal.example.com"},
            {"name": "port", "label": "Port", "input": "number", "default": 9200},
            {"name": "connection_user", "label": "Connection user", "input": "text", "required": True,
             "placeholder": "trino_reader"},
            {"name": "default_schema", "label": "Default schema", "input": "text", "default": "default"},
        ]
    if kind == "bigquery":
        return [
            {"name": "project_id", "label": "Project ID", "input": "text", "required": True,
             "placeholder": "my-analytics-project"},
            {"name": "parent_project_id", "label": "Parent project ID (optional)", "input": "text",
             "placeholder": "data-owner-project"},
        ]
    if kind == "gsheets":
        return [
            {"name": "metadata_sheet_id", "label": "Metadata sheet ID", "input": "text", "required": True,
             "placeholder": "1a2B3c4D5e6F7g8H9i0J-kLmNoPqRsTuVwXyZ012345", "full_width": True},
        ]
    if kind == "cassandra":
        return [
            {"name": "contact_points", "label": "Contact points", "input": "text", "required": True,
             "placeholder": "10.0.0.1,10.0.0.2", "help": "Comma-separated node hostnames or IPs.",
             "full_width": True},
            {"name": "port", "label": "Native protocol port", "input": "number", "default": 9042},
            {"name": "connection_user", "label": "Connection user (optional)", "input": "text",
             "placeholder": "leave blank for an unauthenticated cluster"},
        ]
    if kind == "prometheus":
        return [
            {"name": "uri", "label": "Prometheus URL", "input": "text", "required": True,
             "placeholder": "http://prometheus.internal:9090", "full_width": True},
            {"name": "connection_user", "label": "Connection user (optional)", "input": "text",
             "placeholder": "leave blank for an unauthenticated server"},
        ]
    return []  # generator types take no configuration


def _credential_field(spec: ConnectorType) -> dict[str, object] | None:
    """The write-only secret field, if this type needs one."""
    if spec.requires_secret:
        if spec.credential_kind == "gcp_service_account":
            return {"name": "password", "label": "Service-account JSON key", "input": "textarea",
                    "required_on_create": True, "full_width": True}
        if spec.credential_kind == "azure_storage_key":
            return {"name": "password", "label": "Azure storage account key", "input": "password",
                    "required_on_create": True, "full_width": True}
        return {"name": "password", "label": "Connection password", "input": "password", "required_on_create": True}
    if spec.optional_secret:
        # Auth is optional: the password is required only when a username is set,
        # which the client enforces; on the schema it is never required on create.
        return {"name": "password", "label": "Connection password (if authenticated)",
                "input": "password", "required_on_create": False}
    return None


def connector_type_schema(spec: ConnectorType) -> dict[str, object]:
    return {
        "type": spec.type,
        "label": spec.label,
        "kind": spec.kind,
        "icon": spec.icon,
        "group": _UI_GROUP_BY_KIND.get(spec.kind, "Other"),
        "requires_secret": spec.requires_secret,
        "optional_secret": spec.optional_secret,
        "requires_driver": spec.requires_driver,
        "credential_kind": spec.credential_kind if (spec.requires_secret or spec.optional_secret) else None,
        "default_name": _UI_DEFAULT_NAME.get(spec.type, spec.type),
        "fields": _form_fields(spec),
        "credential": _credential_field(spec),
    }


def connector_types_catalog() -> list[dict[str, object]]:
    """Form schema for every registered connector type, in registry order."""
    return [connector_type_schema(spec) for spec in REGISTRY.values()]
