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

## Object storage — AWS Glue with S3, GCS, or ADLS

Query lakehouse tables through the AWS Glue Data Catalog. S3 access uses the
cluster's node IAM role; cross-cloud Google Cloud Storage (GCS) and Azure Data
Lake Storage Gen2 (ADLS) credentials are kept in AWS Secrets Manager.

- **S3 + Glue (Iceberg)** — Apache Iceberg tables.
- **Google Cloud Storage + Glue (Iceberg)** — Iceberg data under a `gs://`
  warehouse, authenticated with a GCP service-account JSON key.
- **Azure Data Lake + Glue (Iceberg)** — Iceberg data under an `abfss://`
  warehouse, authenticated with an Azure storage account key.
- **Delta Lake (S3 + Glue)** — Delta Lake tables.
- **Hive (S3 + Glue)** — plain Parquet/ORC/text tables via the Hive connector.
- **Hudi (S3 + Glue)** — Apache Hudi tables. Query-only (Trino reads Hudi but
  does not write it), so the access-mode setting doesn't apply.

Provide:

- **Name** — the catalog name analysts will use.
- **Glue region** — the AWS region of your Glue Data Catalog.
- **Warehouse** — an `s3://`, `gs://`, or
  `abfss://container@account.dfs.core.windows.net/` location matching the
  connector. GCS also requires its project ID.
- **Default schema** and **access mode** (read-only or read/write). The **table
  format** is fixed by the connector you picked.

Worker node IAM roles grant the S3 and Glue access — **TrinoHub never stores S3
access keys.** GCS and ADLS credentials are stored only as opaque secret
references in the catalog record and are resolved over the signed node-config
channel at cluster boot.

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

Some connectors ship without a bundled JDBC driver — **Oracle** is the current
example, because its driver isn't redistributable. When you select such a
connector, the form shows a **JDBC driver** panel:

- **Upload driver JAR** — upload the vendor's `.jar` (for Oracle, `ojdbc*.jar`).
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
