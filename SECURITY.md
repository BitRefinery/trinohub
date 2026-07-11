# Security Policy

TrinoHub provisions real AWS infrastructure and handles credentials-adjacent
material (session cookies, signed bootstrap tokens, IAM roles). We take security
reports seriously.

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Report privately via **GitHub Private Vulnerability Reporting**: go to the
repository's **Security → Advisories → Report a vulnerability**, or
<https://github.com/BitRefinery/trinohub/security/advisories/new>.

Please include:

- A description of the issue and its impact.
- Steps to reproduce or a proof-of-concept.
- Affected version / commit and how you're running it (CloudFormation, local, etc.).

## What to expect

- We aim to acknowledge reports within **72 hours**.
- We'll work with you on a fix and a coordinated disclosure timeline.
- We're happy to credit you in the release notes unless you'd prefer to remain anonymous.

This is a volunteer-maintained open-source project, so we can't offer a paid bug
bounty, but responsible disclosure is genuinely appreciated.

## Scope notes

High-value areas to scrutinize:

- The instance-profile / IAM trust model (the control plane must never need static keys).
- Signed per-cluster bootstrap tokens and the `/api/node-config/<cluster_id>` path.
- `validate_read_only_sql` and the Ask Trino boundary (LLM must never touch the DB directly).
- Session handling, allowed-UI-CIDR enforcement, and the setup-token flow.

## Please don't

- Don't run automated scanners against infrastructure you don't own.
- Don't test against a deployment that isn't yours without written permission.
