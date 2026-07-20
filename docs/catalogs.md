# Catalogs & data sources

A **catalog** is a data source that clusters can query. The **Catalogs** view
shows a card grid of configured catalogs alongside an editor for adding new
ones. Click **Add catalog** to open the connector picker, choose a source, and
fill in the form.

## Built-in catalogs

These are enabled by default and need no configuration:

- **system** — Trino's own cluster metadata.
- **tpch** — the TPC-H benchmark dataset (great for trying things out).
- **tpcds** — the TPC-DS decision-support dataset.

## Object storage — S3 + AWS Glue

Query lakehouse tables on S3 through the AWS Glue Data Catalog, authenticated by
the cluster's node IAM role. Three table formats are available as separate
connectors in the picker, all sharing the same form:

- **S3 + Glue (Iceberg)** — Apache Iceberg tables.
- **Delta Lake (S3 + Glue)** — Delta Lake tables.
- **Hive (S3 + Glue)** — plain Parquet/ORC/text tables via the Hive connector.
- **Hudi (S3 + Glue)** — Apache Hudi tables. Query-only (Trino reads Hudi but
  does not write it), so the access-mode setting doesn't apply.

Provide:

- **Name** — the catalog name analysts will use.
- **Glue region** — the AWS region of your Glue Data Catalog.
- **S3 warehouse** — the S3 location for table data.
- **Default schema** and **access mode** (read-only or read/write). The **table
  format** is fixed by the connector you picked.

Worker node IAM roles grant the S3 and Glue access — **TrinoHub never stores S3
access keys.**

## Relational databases (JDBC)

TrinoHub supports a range of JDBC sources. Pick one from the connector picker
and provide a **connection URL**, **connection user**, and **password**:

| Connector | Connection URL example |
|---|---|
| PostgreSQL | `jdbc:postgresql://host:5432/database` |
| MySQL | `jdbc:mysql://host:3306` |
| MariaDB | `jdbc:mariadb://host:3306` |
| Amazon Redshift | `jdbc:redshift://host:5439/database` |
| SQL Server | `jdbc:sqlserver://host:1433;databaseName=db` |
| Oracle | `jdbc:oracle:thin:@//host:1521/service` |
| ClickHouse | `jdbc:clickhouse://host:8123` |
| SingleStore | `jdbc:singlestore://host:3306` |
| Snowflake | `jdbc:snowflake://account.snowflakecomputing.com` |
| Apache Druid | `jdbc:avatica:remote:url=http://broker:8082/druid/v2/sql/avatica/` |

## Cross-cluster federation (Trino → Trino)

The **Trino** connector federates a *remote* Trino cluster as a catalog, so one
cluster can query another without copying data. Provide a
`jdbc:trino://host[:port][/catalog][?SSL=true]` connection URL, a connection
user, and a password (the remote cluster's credentials). It is read-only and
pushes down projections, `LIMIT`, and selected predicates, aggregations, and
joins to the remote cluster.

This connector is **not bundled in a stock Trino release** — it arrives via
[trinodb/trino#30290](https://github.com/trinodb/trino/pull/30290). Like Oracle,
you must upload its plugin JAR before a cluster using it can start (see
[Uploading a connector plugin](#uploading-a-jdbc-driver-oracle) below); upload
the connector's **self-contained (shaded) plugin JAR**, which nodes drop into
`/opt/trino/plugin/trino/` at boot. Because the connector is pre-release, pin it
to a build tested against your Trino version — cross-version compatibility
between the local and remote clusters is not guaranteed.

## Document & search stores

- **MongoDB** — a `mongodb://host:27017/database` connection URL (without
  embedded credentials), plus a user and password.
- **Elasticsearch** — host, port, connection user, and default schema, with
  password authentication.
- **OpenSearch** — the same host/port/user/schema form as Elasticsearch, with
  password authentication.

## Google Cloud — BigQuery & Sheets

**Google BigQuery** is a cross-cloud source: clusters run in AWS but query
BigQuery in Google Cloud. Provide:

- **Project ID** — the GCP project that runs and bills the queries.
- **Parent project ID** *(optional)* — the project that owns the datasets, when
  different from the billing project.
- **Service-account JSON key** — the full service-account key file, pasted in.

The key is validated as a `service_account` JSON document, then stored in AWS
Secrets Manager exactly like a password (see below). At node boot the control
plane resolves it and renders it as a base64 `bigquery.credentials-key` into the
signed node-config — the key never lands in EC2 user-data or the catalog config.
Clusters need outbound HTTPS to `bigquery.googleapis.com`.

**Google Sheets** uses the same service-account credential class. Provide the
**metadata sheet ID** (the spreadsheet that maps table names to sheets) and the
service-account JSON key; the key is stored and rendered exactly as for BigQuery
(base64 `gsheets.credentials-key`). Share the target sheets with the service
account's email.

## Test & sample data (no configuration)

Three zero-configuration connectors are available for testing and demos — pick
one from the picker and just name it, no credentials or endpoints:

- **Memory** — tables held in cluster memory (non-persistent).
- **Black Hole** — accepts and discards writes; a sink for load testing.
- **Faker** — generates synthetic rows on read.

## How credentials are stored

For any source that needs a password, **TrinoHub never stores the plaintext in
its own database.** When you save the catalog:

1. The password is written once to **AWS Secrets Manager**; only the secret's
   ARN reference is kept in the catalog config.
2. At node boot, the control plane resolves the secret and delivers the
   `.properties` file over the signed, token-authed node-config channel — the
   password never appears in EC2 user-data or the catalog config.

The connection URL must not embed credentials, and configs are rejected if they
contain password/secret-like keys. Password fields are **write-only**: they are
never echoed back, so on edit you can leave the field blank to keep the stored
secret.

## Uploading a JDBC driver (Oracle)

Some connectors ship without a bundled JAR — **Oracle** needs the vendor JDBC
driver (not redistributable), and the **Trino** cross-cluster connector needs
its whole plugin JAR (not yet in a stock release). When you select such a
connector, the form shows a **JDBC driver** panel:

- **Upload driver JAR** — upload the `.jar` (for Oracle, the vendor's
  `ojdbc*.jar`; for Trino, the connector's shaded plugin JAR).
  It's held on the control plane and its SHA-256 is recorded.
- At boot, each cluster node downloads the driver into Trino's plugin directory
  and **verifies the SHA-256** before starting.
- **Remove** deletes the stored driver.

You must upload the driver **before** starting a cluster that uses the catalog —
starting one without it fails fast with a clear message. Because drivers install
at node boot, **restart a running cluster to apply** a new or changed driver.

## Check config

Use **Check config** to validate a catalog against a running, attached cluster.
It runs a live `SHOW SCHEMAS` so you can confirm connectivity and permissions
before relying on it. **Save catalog** persists the configuration.

> JDBC and other network sources must be reachable from the cluster's VPC,
> subnet, and security group. If a check fails to connect, verify network
> routing and security-group rules to the data source.

## Attaching catalogs to clusters

Catalogs are attached to a cluster when you create or edit it — each configured
data catalog has its own checkbox, so you can attach any subset. A cluster can
only query the catalogs attached to it.
