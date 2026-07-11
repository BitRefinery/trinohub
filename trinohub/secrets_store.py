"""Pluggable storage for data-source credentials.

TrinoHub never persists a source password in its own metadata DB. Instead the
plaintext is written once to a secret backend (AWS Secrets Manager today) and
only an opaque reference (the secret ARN) is stored in the catalog config. The
control plane resolves the reference back to plaintext at node-config render
time and serves it over the token-authenticated ``/api/node-config`` endpoint.

The ``SecretStore`` protocol keeps that backend swappable: a future deployment
that runs off AWS could provide a Vault- or Postgres-backed implementation
without touching the catalog/credential plumbing.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable

SECRET_PREFIX = "trinohub/catalog/"


class SecretStoreError(Exception):
    """Raised when a secret cannot be stored, resolved, or deleted."""


@runtime_checkable
class SecretStore(Protocol):
    def put(self, key: str, value: str) -> str:
        """Store ``value`` for the logical ``key`` and return an opaque reference."""

    def get(self, ref: str) -> str:
        """Resolve a reference returned by :meth:`put` back to plaintext."""

    def delete(self, ref: str) -> None:
        """Remove the secret identified by ``ref``. Missing secrets are a no-op."""


class NullSecretStore:
    """Default when no secret backend is configured.

    Reads still fail loudly, but the important property is that ``put`` refuses
    rather than letting a credentialed catalog be created with nowhere safe to
    keep its password.
    """

    def put(self, key: str, value: str) -> str:
        raise SecretStoreError(
            "No secret backend is configured, so credentialed catalogs cannot be "
            "created. Configure AWS Secrets Manager access for the control plane."
        )

    def get(self, ref: str) -> str:
        raise SecretStoreError("No secret backend is configured; cannot resolve a credential.")

    def delete(self, ref: str) -> None:
        return None


class SecretsManagerStore:
    """Stores credentials in AWS Secrets Manager (KMS-encrypted, CloudTrail-audited).

    ``client_factory`` returns a boto3 ``secretsmanager`` client; it is called
    lazily so the store can be constructed even when AWS is unreachable (e.g. in
    tests that never exercise the credential path).
    """

    def __init__(self, client_factory: Callable[[], Any]) -> None:
        self._client_factory = client_factory

    def _client(self) -> Any:
        return self._client_factory()

    def put(self, key: str, value: str) -> str:
        name = f"{SECRET_PREFIX}{key}"
        client = self._client()
        try:
            response = client.create_secret(Name=name, SecretString=value)
            return str(response["ARN"])
        except Exception as exc:  # noqa: BLE001 - re-raised as SecretStoreError below
            if exc.__class__.__name__ != "ResourceExistsException":
                raise SecretStoreError(f"Could not store credential in Secrets Manager: {exc}") from exc
        # Secret already exists from a prior catalog of the same name: rotate it.
        try:
            client.put_secret_value(SecretId=name, SecretString=value)
            described = client.describe_secret(SecretId=name)
            return str(described["ARN"])
        except Exception as exc:  # noqa: BLE001
            raise SecretStoreError(f"Could not update credential in Secrets Manager: {exc}") from exc

    def get(self, ref: str) -> str:
        try:
            response = self._client().get_secret_value(SecretId=ref)
        except Exception as exc:  # noqa: BLE001
            raise SecretStoreError(f"Could not resolve credential from Secrets Manager: {exc}") from exc
        secret = response.get("SecretString")
        if secret is None:
            raise SecretStoreError("Secret has no string value.")
        return str(secret)

    def delete(self, ref: str) -> None:
        try:
            self._client().delete_secret(SecretId=ref, ForceDeleteWithoutRecovery=True)
        except Exception as exc:  # noqa: BLE001
            if exc.__class__.__name__ == "ResourceNotFoundException":
                return None
            raise SecretStoreError(f"Could not delete credential from Secrets Manager: {exc}") from exc
        return None
