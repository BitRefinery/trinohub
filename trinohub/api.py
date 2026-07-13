from __future__ import annotations

import asyncio
import csv
import json
import os
import re
import sqlite3
from io import StringIO
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field

from .database import loads, row_to_dict
from .aws_checks import fetch_published_trino_versions
from .server import (
    DEFAULT_DB_PATH,
    DEFAULT_DOCS_DIR,
    DEFAULT_STATIC_DIR,
    NOTIFICATION_EVENTS,
    PRIVILEGE_MANAGE_CATALOGS,
    PRIVILEGE_MANAGE_CLUSTERS,
    PRIVILEGE_MANAGE_SECURITY,
    PRIVILEGE_MANAGE_SETTINGS,
    PRIVILEGE_MANAGE_USERS,
    SESSION_COOKIE,
    WIRE_HOLD_POLL_SECONDS,
    ApiError,
    TrinoHubApp,
)


class PayloadModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    def payload(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True)


class SetupCompleteRequest(PayloadModel):
    username: str
    password: str
    setup_token: str = ""
    email: str = ""
    # ``provider`` selects which cloud implementation to configure. The fields
    # below it are the AWS provider's config; a second provider adds its own and
    # the server routes them into setup_settings.provider_config_json by provider.
    provider: str = "aws"
    region: str | None = None
    vpc_id: str | None = None
    private_subnet_ids: list[str] | str | None = None
    cluster_security_group_id: str = ""
    node_instance_profile: str = "TrinoHubNodeRole"
    allowed_ui_cidrs: list[str] | str = Field(default_factory=list)
    allowed_instance_types: list[str] = Field(default_factory=list)
    # Explicit opt-in to an allowed_ui_cidrs list that excludes the caller's
    # own address (which would otherwise 403 them on the next request).
    confirm_lockout: bool = False


class AllowedUiCidrsRequest(PayloadModel):
    allowed_ui_cidrs: list[str] | str = Field(default_factory=list)
    confirm_lockout: bool = False


class AllowedInstanceTypesRequest(PayloadModel):
    instance_types: list[str] = Field(default_factory=list)


class ClusterBaseDomainRequest(PayloadModel):
    cluster_base_domain: str = ""


class LoginRequest(PayloadModel):
    username: str
    password: str


class UserCreateRequest(PayloadModel):
    username: str
    password: str = ""
    email: str = ""
    role: str = "user"
    roles: list[str] | None = None
    is_service: bool = False


class UserUpdateRequest(PayloadModel):
    role: str | None = None
    roles: list[str] | None = None
    password: str | None = None
    email: str | None = None
    is_active: bool | None = None


class RoleCreateRequest(PayloadModel):
    name: str
    description: str = ""
    privileges: list[str] = Field(default_factory=list)
    cluster_grants: list[str] = Field(default_factory=list)
    catalog_grants: list[str] = Field(default_factory=list)


class RoleUpdateRequest(PayloadModel):
    description: str | None = None
    privileges: list[str] | None = None
    cluster_grants: list[str] | None = None
    catalog_grants: list[str] | None = None


class OidcSettingsRequest(PayloadModel):
    enabled: bool | None = None
    issuer: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    group_claim: str | None = None
    group_role_mappings: dict[str, str] | None = None
    default_role: str | None = None
    password_login: str | None = None
    redirect_base: str | None = None


class SessionSettingsRequest(PayloadModel):
    session_hours: int


class ResultCacheSettingsRequest(PayloadModel):
    result_cache_ttl_minutes: int


class ApiTokenCreateRequest(PayloadModel):
    name: str
    user_id: int | None = None
    expires_days: int | None = None


class JobCreateRequest(PayloadModel):
    name: str
    sql: str
    cluster_id: int
    catalog: str = ""
    schema_name: str = Field(default="", alias="schema")
    schedule_type: str = "interval"
    interval_minutes: int | None = None
    cron_expression: str = ""
    run_as: str = ""


class JobUpdateRequest(PayloadModel):
    name: str | None = None
    sql: str | None = None
    catalog: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    schedule_type: str | None = None
    interval_minutes: int | None = None
    cron_expression: str | None = None
    enabled: bool | None = None


class ShareRequest(PayloadModel):
    role: str
    access: str = "view"


class NotificationSettingsRequest(PayloadModel):
    webhook_url: str | None = None
    events: list[str] | None = None


class AskTrinoSettingsRequest(PayloadModel):
    model: str = ""


class DataPolicyRequest(PayloadModel):
    role: str
    catalog: str
    schema_name: str = Field(default="", alias="schema")
    table: str = ""
    privileges: list[str] = Field(default_factory=lambda: ["SELECT"])
    allowed_columns: list[str] = Field(default_factory=list)
    denied_columns: list[str] = Field(default_factory=list)
    row_filter: str = ""
    column_masks: dict[str, str] = Field(default_factory=dict)


class EntityTagRequest(PayloadModel):
    entity: str
    tag: str


class TagPolicyRequest(PayloadModel):
    tag: str
    role: str
    effect: str = "deny"


class ClusterCreateRequest(PayloadModel):
    name: str
    instance_type: str = ""
    worker_mode: str = "autoscale"
    min_workers: int = 1
    max_workers: int = 1
    auto_suspend_minutes: int | None = None
    hostname: str = ""
    trino_version: str = ""
    accelerated: bool = False
    catalogs: list[str] = Field(default_factory=lambda: ["system", "tpch", "tpcds"])


class ClusterUpdateRequest(PayloadModel):
    worker_mode: str | None = None
    min_workers: int | None = None
    max_workers: int | None = None
    auto_suspend_minutes: int | None = None
    hostname: str | None = None
    accelerated: bool | None = None
    catalogs: list[str] | None = None
    # Keep-warm windows: [{days, start, end}] or strings like "mon-fri 08:00-18:00".
    uptime_schedule: list[Any] | None = None


class ClusterStartRequest(PayloadModel):
    confirm_billable: bool = False


class CatalogRequest(PayloadModel):
    name: str
    type: str = "s3_glue"
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    # Write-only: routed to the secret store on save, never echoed back in responses.
    password: str | None = None


class CatalogCheckRequest(CatalogRequest):
    cluster_id: int | None = None


class QueryRequest(PayloadModel):
    cluster_id: int
    sql: str
    catalog: str = ""
    schema_name: str = Field(default="", alias="schema")
    # True bypasses the result cache and always executes against the cluster.
    fresh: bool = False


class QueryTabCreateRequest(PayloadModel):
    name: str | None = None
    sql: str = ""
    cluster_id: int | None = None
    catalog: str = ""
    schema_name: str = Field(default="", alias="schema")
    run_mode: str = "current"
    position: int | None = None
    is_active: bool | None = None


class QueryTabUpdateRequest(PayloadModel):
    name: str | None = None
    sql: str | None = None
    cluster_id: int | None = None
    catalog: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    run_mode: str | None = None
    position: int | None = None
    is_active: bool | None = None


class SavedQueryCreateRequest(PayloadModel):
    name: str | None = None
    sql: str
    cluster_id: int | None = None
    catalog: str = ""
    schema_name: str = Field(default="", alias="schema")


class SavedQueryUpdateRequest(PayloadModel):
    name: str | None = None
    sql: str | None = None
    cluster_id: int | None = None
    catalog: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")


class NotebookCreateRequest(PayloadModel):
    name: str | None = None
    cluster_id: int | None = None
    catalog: str = ""
    schema_name: str = Field(default="", alias="schema")


class NotebookUpdateRequest(PayloadModel):
    name: str | None = None
    cluster_id: int | None = None
    catalog: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    position: int | None = None


class NotebookCellCreateRequest(PayloadModel):
    sql: str = ""
    cluster_id: int | None = None
    catalog: str = ""
    schema_name: str = Field(default="", alias="schema")
    view_pref: str = "table"
    chart_config: dict[str, Any] = Field(default_factory=dict)
    position: int | None = None


class NotebookCellUpdateRequest(PayloadModel):
    sql: str | None = None
    cluster_id: int | None = None
    catalog: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    view_pref: str | None = None
    chart_config: dict[str, Any] | None = None
    position: int | None = None
    last_query_id: int | None = None


class AskRequest(PayloadModel):
    question: str
    cluster_id: int | None = None
    catalog: str = ""
    schema_name: str = Field(default="", alias="schema")
    persona: str = "Analyst"
    history: list[dict[str, Any]] = Field(default_factory=list)


class HeaderAdapter:
    def __init__(self, request: Request) -> None:
        self.headers = request.headers


def load_dotenv_once() -> None:
    """Load KEY=VALUE pairs from a project-root .env into os.environ for keys that
    aren't already set. Dependency-free so the documented `uvicorn` run command
    picks up OPENROUTER_API_KEY without exporting it by hand."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def create_app(
    *,
    db_path: str | Path | None = None,
    static_dir: str | Path | None = None,
    control_app: TrinoHubApp | None = None,
    enable_health_poller: bool = True,
) -> FastAPI:
    load_dotenv_once()
    selected_db = Path(db_path or os.environ.get("TRINOHUB_DB", DEFAULT_DB_PATH))
    selected_static = Path(static_dir or os.environ.get("TRINOHUB_STATIC_DIR", DEFAULT_STATIC_DIR))
    selected_docs = Path(os.environ.get("TRINOHUB_DOCS_DIR", DEFAULT_DOCS_DIR))
    # Operators can force-disable the background poller (e.g. when running a
    # dedicated poller process). A host-local lock already prevents duplicate
    # pollers across multiple uvicorn workers.
    poller_enabled = enable_health_poller and os.environ.get("TRINOHUB_ENABLE_POLLER", "1") != "0"
    control = control_app or TrinoHubApp(
        db_path=selected_db,
        enable_health_poller=poller_enabled,
        # Live discovery of new Trino releases from Maven Central; the static
        # SUPPORTED_TRINO_VERSIONS list remains the offline fallback.
        trino_version_fetcher=fetch_published_trino_versions,
    )

    api = FastAPI(
        title="TrinoHub API",
        version="0.1.0",
        description="Control-plane API for TrinoHub cluster, catalog, user, setup, and query workflows.",
    )
    api.state.trinohub = control
    api.state.static_dir = selected_static
    api.state.docs_dir = selected_docs

    @api.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse({"error": exc.message}, status_code=exc.status)

    @api.exception_handler(sqlite3.IntegrityError)
    async def handle_integrity_error(_: Request, exc: sqlite3.IntegrityError) -> JSONResponse:
        return JSONResponse({"error": f"Database constraint failed: {exc}"}, status_code=409)

    @api.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        print(f"Unhandled error on {request.method} {request.url.path}: {type(exc).__name__}: {exc}")
        return JSONResponse({"error": "Internal server error."}, status_code=500)

    @api.middleware("http")
    async def enforce_allowed_ui_cidrs(request: Request, call_next):
        path = request.url.path
        # Native Trino wire endpoints (/v1/*) are reached through the Caddy gateway,
        # which already enforces the operator's allowed CIDRs; gating them again on
        # the UI-CIDR list (and returning a JSON 403 a Trino client can't read) is
        # both redundant and wrong, so they are exempt here like the TLS-ask hook.
        if (
            path not in {"/api/health", "/api/tls/authorize"}
            and not path.startswith("/api/node-config/")
            and not path.startswith("/v1/")
        ):
            remote_addr = request.client.host if request.client else ""
            forwarded_for = request.headers.get("x-forwarded-for", "")
            if not control.client_ip_allowed(remote_addr=remote_addr, forwarded_for=forwarded_for):
                return JSONResponse({"error": "Client IP is not in the allowed UI CIDR list."}, status_code=403)
        return await call_next(request)

    def current_user(request: Request) -> dict[str, Any] | None:
        return control.current_user(HeaderAdapter(request))

    def require_user(request: Request) -> dict[str, Any]:
        user = current_user(request)
        if not user:
            raise ApiError(401, "Authentication required.")
        return user

    def require_privilege(privilege: str):
        """Dependency factory: the session user must hold ``privilege``.

        This replaces the old binary ``require_admin`` gate — each admin surface
        now demands its specific privilege (MANAGE_CLUSTERS, MANAGE_CATALOGS,
        ...), so custom roles can delegate one area without the others.
        """

        def dependency(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
            return control.require_privilege(user, privilege)

        return dependency

    def user_is_operator(user: dict[str, Any]) -> bool:
        """Any management privilege marks the user as an operator for UI/docs
        gating (nav visibility, admin help topics)."""
        manage = {
            PRIVILEGE_MANAGE_USERS,
            PRIVILEGE_MANAGE_SECURITY,
            PRIVILEGE_MANAGE_CLUSTERS,
            PRIVILEGE_MANAGE_CATALOGS,
            PRIVILEGE_MANAGE_SETTINGS,
        }
        return bool(manage & control.user_privileges(user))

    def set_session_cookie(response: Response, token: str) -> None:
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=43200,
            httponly=True,
            samesite="lax",
            path="/",
        )

    @api.get("/api/health", tags=["health"])
    def health() -> dict[str, bool]:
        return {"ok": True}

    @api.get("/api/node-config/{cluster_id}", response_class=PlainTextResponse, include_in_schema=False)
    def node_config(
        cluster_id: int,
        role: str,
        token: str,
        instance_type: str = "",
    ) -> PlainTextResponse:
        script = control.node_config_script(
            cluster_id=cluster_id,
            role=role,
            token=token,
            instance_type=instance_type,
        )
        return PlainTextResponse(script, media_type="text/x-shellscript; charset=utf-8")

    @api.get("/api/setup/status", tags=["setup"])
    def setup_status(validate: bool = False, region: str | None = None) -> dict[str, Any]:
        query: dict[str, list[str]] = {"validate": ["1" if validate else "0"]}
        if region:
            query["region"] = [region]
        return control.setup_status(query)

    @api.post("/api/setup/complete", status_code=201, tags=["setup"])
    def complete_setup(payload: SetupCompleteRequest, request: Request, response: Response) -> dict[str, Any]:
        result, token = control.complete_setup(
            payload.payload(),
            remote_addr=request.client.host if request.client else "",
            forwarded_for=request.headers.get("x-forwarded-for", ""),
        )
        set_session_cookie(response, token)
        return result

    @api.post("/api/auth/login", tags=["auth"])
    def login(payload: LoginRequest, response: Response) -> dict[str, Any]:
        result, token = control.login(payload.payload())
        set_session_cookie(response, token)
        return result

    @api.post("/api/auth/logout", tags=["auth"])
    def logout(request: Request, response: Response) -> dict[str, bool]:
        result = control.logout(HeaderAdapter(request))
        response.delete_cookie(SESSION_COOKIE, path="/")
        return result

    @api.get("/api/auth/methods", tags=["auth"])
    def auth_methods() -> dict[str, Any]:
        # Pre-login surface for the sign-in screen: which methods to offer.
        oidc = control.public_oidc_settings()
        return {
            "password": True,
            "oidc": control.oidc_enabled(),
            "password_login": oidc.get("password_login", "all"),
        }

    @api.get("/api/auth/oidc/login", include_in_schema=False)
    def oidc_login(request: Request) -> RedirectResponse:
        redirect_uri = control.oidc_redirect_uri(str(request.base_url).rstrip("/"))
        return RedirectResponse(control.oidc_login_start(redirect_uri), status_code=302)

    @api.get("/api/auth/oidc/callback", include_in_schema=False)
    def oidc_callback(request: Request, code: str = "", state: str = "", error: str = "") -> Response:
        if error:
            return RedirectResponse(f"/?sso_error={error}", status_code=302)
        _, token = control.oidc_callback(code=code, state=state)
        response = RedirectResponse("/", status_code=302)
        set_session_cookie(response, token)
        return response

    @api.get("/api/sso/oidc", tags=["settings"])
    def get_oidc_settings(_: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS))) -> dict[str, Any]:
        return {"oidc": control.public_oidc_settings()}

    @api.put("/api/sso/oidc", tags=["settings"])
    def put_oidc_settings(
        payload: OidcSettingsRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS)),
    ) -> dict[str, Any]:
        return control.set_oidc_settings(payload.model_dump(by_alias=True, exclude_unset=True), actor)

    @api.get("/api/security/session", tags=["settings"])
    def get_session_settings(_: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS))) -> dict[str, Any]:
        return {"session_hours": control.session_hours()}

    @api.put("/api/security/session", tags=["settings"])
    def put_session_settings(
        payload: SessionSettingsRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS)),
    ) -> dict[str, Any]:
        return control.set_session_hours(payload.payload(), actor)

    @api.get("/api/query-cache", tags=["settings"])
    def get_result_cache_settings(
        _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS)),
    ) -> dict[str, Any]:
        return {"result_cache_ttl_minutes": control.result_cache_ttl_minutes()}

    @api.put("/api/query-cache", tags=["settings"])
    def put_result_cache_settings(
        payload: ResultCacheSettingsRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS)),
    ) -> dict[str, Any]:
        return control.set_result_cache_ttl(payload.payload(), actor)

    @api.get("/api/security/ui-cidrs", tags=["settings"])
    def get_ui_cidr_settings(
        _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS)),
    ) -> dict[str, Any]:
        return control.allowed_ui_cidrs_settings()

    @api.put("/api/security/ui-cidrs", tags=["settings"])
    def put_ui_cidr_settings(
        payload: AllowedUiCidrsRequest,
        request: Request,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS)),
    ) -> dict[str, Any]:
        return control.set_allowed_ui_cidrs(
            payload.payload(),
            actor,
            remote_addr=request.client.host if request.client else "",
            forwarded_for=request.headers.get("x-forwarded-for", ""),
        )

    @api.post("/api/auth/revoke-sessions", tags=["auth"])
    def revoke_sessions(response: Response, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        result = control.revoke_user_sessions(user)
        response.delete_cookie(SESSION_COOKIE, path="/")
        return result

    @api.get("/api/tokens", tags=["auth"])
    def list_api_tokens(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.list_api_tokens(user)

    @api.post("/api/tokens", status_code=201, tags=["auth"])
    def create_api_token(
        payload: ApiTokenCreateRequest, user: dict[str, Any] = Depends(require_user)
    ) -> dict[str, Any]:
        return control.create_api_token(payload.model_dump(by_alias=True, exclude_unset=True), user)

    @api.delete("/api/tokens/{token_id}", tags=["auth"])
    def delete_api_token(token_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.delete_api_token(token_id, user)

    @api.get("/api/me", tags=["auth"])
    def me(request: Request) -> dict[str, Any]:
        user = current_user(request)
        return {"user": control.decorate_user(user) if user else None}

    @api.get("/api/aws/status", tags=["aws"])
    def aws_status(
        region: str | None = None,
        _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS)),
    ) -> dict[str, Any]:
        return control.aws.full_status(region)

    @api.get("/api/users", tags=["users"])
    def list_users(_: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_USERS))) -> dict[str, Any]:
        return control.list_users()

    @api.post("/api/users", status_code=201, tags=["users"])
    def create_user(
        payload: UserCreateRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_USERS)),
    ) -> dict[str, Any]:
        return control.create_user(payload.model_dump(by_alias=True, exclude_unset=True), actor)

    @api.patch("/api/users/{user_id}", tags=["users"])
    def update_user(
        user_id: int,
        payload: UserUpdateRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_USERS)),
    ) -> dict[str, Any]:
        return control.update_user(user_id, payload.model_dump(by_alias=True, exclude_unset=True), actor)

    @api.get("/api/roles", tags=["security"])
    def list_roles(_: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.list_roles()

    @api.post("/api/roles", status_code=201, tags=["security"])
    def create_role(
        payload: RoleCreateRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY)),
    ) -> dict[str, Any]:
        return control.create_role(payload.payload(), actor)

    @api.patch("/api/roles/{role_id}", tags=["security"])
    def update_role(
        role_id: int,
        payload: RoleUpdateRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY)),
    ) -> dict[str, Any]:
        return control.update_role(role_id, payload.model_dump(by_alias=True, exclude_unset=True), actor)

    @api.delete("/api/roles/{role_id}", tags=["security"])
    def delete_role(
        role_id: int,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY)),
    ) -> dict[str, Any]:
        return control.delete_role(role_id, actor)

    # --- Fine-grained data security (Phase 6) --------------------------------

    @api.get("/api/data-policies", tags=["security"])
    def list_data_policies(_: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY))) -> dict[str, Any]:
        return control.list_data_policies()

    @api.post("/api/data-policies", status_code=201, tags=["security"])
    def create_data_policy(
        payload: DataPolicyRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY)),
    ) -> dict[str, Any]:
        return control.create_data_policy(payload.model_dump(by_alias=True, exclude_unset=True), actor)

    @api.delete("/api/data-policies/{policy_id}", tags=["security"])
    def delete_data_policy(
        policy_id: int,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY)),
    ) -> dict[str, Any]:
        return control.delete_data_policy(policy_id, actor)

    @api.get("/api/tags", tags=["security"])
    def list_entity_tags(_: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY))) -> dict[str, Any]:
        return control.list_entity_tags()

    @api.post("/api/tags", status_code=201, tags=["security"])
    def create_entity_tag(
        payload: EntityTagRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY)),
    ) -> dict[str, Any]:
        return control.create_entity_tag(payload.payload(), actor)

    @api.patch("/api/tags/{tag_id}", tags=["security"])
    def accept_entity_tag(
        tag_id: int,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY)),
    ) -> dict[str, Any]:
        return control.resolve_entity_tag(tag_id, True, actor)

    @api.delete("/api/tags/{tag_id}", tags=["security"])
    def reject_entity_tag(
        tag_id: int,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY)),
    ) -> dict[str, Any]:
        return control.resolve_entity_tag(tag_id, False, actor)

    @api.get("/api/tag-policies", tags=["security"])
    def list_tag_policies(_: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY))) -> dict[str, Any]:
        return control.list_tag_policies()

    @api.post("/api/tag-policies", status_code=201, tags=["security"])
    def create_tag_policy(
        payload: TagPolicyRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY)),
    ) -> dict[str, Any]:
        return control.create_tag_policy(payload.payload(), actor)

    @api.delete("/api/tag-policies/{policy_id}", tags=["security"])
    def delete_tag_policy(
        policy_id: int,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY)),
    ) -> dict[str, Any]:
        return control.delete_tag_policy(policy_id, actor)

    @api.post("/api/security/classify", tags=["security"])
    def run_pii_classifier(
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY)),
    ) -> dict[str, Any]:
        return control.run_pii_classifier(actor)

    @api.get("/api/clusters/{cluster_id}/access-rules", tags=["security"])
    def cluster_access_rules(
        cluster_id: int,
        _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY)),
    ) -> dict[str, Any]:
        with control.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            cluster = control.public_cluster(row)
        rules = control.render_access_control_rules(cluster)
        return {"cluster_id": cluster_id, "rules": json.loads(rules) if rules else None}

    @api.get("/api/security/audit", tags=["security"])
    def security_audit(
        limit: int = 200,
        _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SECURITY)),
    ) -> dict[str, Any]:
        return control.security_audit_entries(limit)

    @api.get("/api/preset-tiers", tags=["clusters"])
    def preset_tiers(
        region: str | None = None,
        _: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        return control.preset_tiers(region)

    @api.get("/api/instance-types", tags=["clusters"])
    def instance_types(
        region: str | None = None,
        _: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        return control.instance_type_options(region)

    @api.put("/api/instance-types", tags=["clusters"])
    def set_allowed_instance_types(
        payload: AllowedInstanceTypesRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS)),
    ) -> dict[str, Any]:
        return control.set_allowed_instance_types(payload.payload(), actor)

    @api.put("/api/cluster-base-domain", tags=["settings"])
    def set_cluster_base_domain(
        payload: ClusterBaseDomainRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS)),
    ) -> dict[str, Any]:
        return control.set_cluster_base_domain(payload.payload(), actor)

    # Called by the Caddy TLS gateway (on the same host) before it issues an
    # on-demand Let's Encrypt certificate: 200 authorizes the hostname, 404
    # refuses. Unauthenticated by design (Caddy cannot present a session) and
    # exempt from the allowed-CIDR middleware; it only reveals whether a name
    # belongs to a known cluster.
    @api.get("/api/tls/authorize", include_in_schema=False)
    def tls_authorize(domain: str = "") -> Response:
        if control.authorize_tls_domain(domain):
            return Response(status_code=200)
        raise ApiError(404, "Unknown TLS host.")

    @api.post("/api/tls/gateway/sync", tags=["settings"])
    def sync_tls_gateway(_: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS))) -> dict[str, Any]:
        ok, detail = control.sync_tls_gateway()
        return {"ok": ok, "detail": detail, "routes": control.cluster_tls_routes()}

    @api.get("/api/trino-versions", tags=["clusters"])
    def trino_versions(_: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.trino_version_options()

    @api.get("/api/clusters", tags=["clusters"])
    def list_clusters(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.list_clusters(user)

    @api.post("/api/clusters", status_code=201, tags=["clusters"])
    def create_cluster(
        payload: ClusterCreateRequest,
        admin: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS)),
    ) -> dict[str, Any]:
        # exclude_unset so the server can tell "field omitted" from "explicit
        # null/default" — e.g. accelerated clusters get a long auto-suspend
        # default only when the client didn't choose a value.
        return control.create_cluster(payload.model_dump(by_alias=True, exclude_unset=True), admin)

    @api.get("/api/clusters/{cluster_id}", tags=["clusters"])
    def get_cluster(cluster_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        control.require_cluster_access(user, cluster_id)
        with control.conn() as conn:
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            if not row:
                raise ApiError(404, "Cluster not found.")
            return {"cluster": control.public_cluster(row)}

    @api.patch("/api/clusters/{cluster_id}", tags=["clusters"])
    def update_cluster(
        cluster_id: int,
        payload: ClusterUpdateRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS)),
    ) -> dict[str, Any]:
        # exclude_unset so only fields the client actually sent are treated as
        # edits; an explicit ``auto_suspend_minutes: null`` still clears it.
        return control.update_cluster(cluster_id, payload.model_dump(by_alias=True, exclude_unset=True), actor)

    @api.delete("/api/clusters/{cluster_id}", tags=["clusters"])
    def delete_cluster(
        cluster_id: int,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS)),
    ) -> dict[str, Any]:
        return control.delete_cluster(cluster_id, actor)

    @api.get("/api/clusters/{cluster_id}/connection", tags=["clusters"])
    def cluster_connection(
        cluster_id: int,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        return control.cluster_connection_info(cluster_id, user)

    @api.get("/api/clusters/{cluster_id}/resources", tags=["clusters"])
    def cluster_resources(
        cluster_id: int, _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS))
    ) -> dict[str, Any]:
        return control.cluster_resources(cluster_id)

    @api.get("/api/clusters/{cluster_id}/metadata", tags=["clusters"])
    def cluster_metadata(
        cluster_id: int,
        catalog: str = "",
        schema: str = "",
        table: str = "",
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        return control.cluster_metadata(cluster_id, catalog=catalog, schema_name=schema, table=table, user=user)

    @api.post("/api/clusters/{cluster_id}/health", tags=["clusters"])
    def refresh_cluster_health(
        cluster_id: int, _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS))
    ) -> dict[str, Any]:
        return control.refresh_cluster_health(cluster_id)

    @api.post("/api/clusters/{cluster_id}/start", tags=["clusters"])
    def start_cluster(
        cluster_id: int,
        payload: ClusterStartRequest,
        _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS)),
    ) -> dict[str, Any]:
        return control.start_cluster(cluster_id, payload.payload())

    @api.post("/api/clusters/{cluster_id}/suspend", tags=["clusters"])
    def suspend_cluster(
        cluster_id: int, _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS))
    ) -> dict[str, Any]:
        return control.suspend_cluster(cluster_id)

    @api.post("/api/clusters/{cluster_id}/disable", tags=["clusters"])
    def disable_cluster(
        cluster_id: int, _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS))
    ) -> dict[str, Any]:
        return control.disable_cluster(cluster_id)

    @api.get("/api/clusters/{cluster_id}/events", tags=["clusters"])
    def cluster_events(
        cluster_id: int, _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS))
    ) -> dict[str, Any]:
        with control.conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM cluster_events
                WHERE cluster_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 200
                """,
                (cluster_id,),
            ).fetchall()
        return {
            "events": [
                {
                    **row_to_dict(row),
                    "metadata": loads(row["metadata_json"], {}),
                }
                for row in rows
            ]
        }

    @api.get("/api/clusters/{cluster_id}/scaling-events", tags=["clusters"])
    def scaling_events(
        cluster_id: int, _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS))
    ) -> dict[str, Any]:
        with control.conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM scaling_events
                WHERE cluster_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 200
                """,
                (cluster_id,),
            ).fetchall()
        return {"scaling_events": [row_to_dict(row) for row in rows]}

    @api.post("/api/clusters/{cluster_id}/autoscale/check", tags=["clusters"])
    def autoscale_check(
        cluster_id: int, _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS))
    ) -> dict[str, Any]:
        return control.autoscale_cluster_once(cluster_id)

    @api.post("/api/clusters/{cluster_id}/auto-suspend/check", tags=["clusters"])
    def auto_suspend_check(
        cluster_id: int, _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS))
    ) -> dict[str, Any]:
        return control.auto_suspend_cluster_once(cluster_id)

    @api.post("/api/autoscaling/poll", tags=["clusters"])
    def poll_autoscaling(_: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS))) -> dict[str, Any]:
        return {"results": control.poll_autoscaling_once()}

    @api.post("/api/auto-suspend/poll", tags=["clusters"])
    def poll_auto_suspend(_: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS))) -> dict[str, Any]:
        return {"results": control.poll_auto_suspend_once()}

    @api.get("/api/catalogs", tags=["catalogs"])
    def list_catalogs(_: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.list_catalogs()

    @api.post("/api/catalogs", status_code=201, tags=["catalogs"])
    def create_catalog(
        payload: CatalogRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CATALOGS)),
    ) -> dict[str, Any]:
        return control.create_catalog(payload.payload(), actor)

    @api.post("/api/catalogs/check", tags=["catalogs"])
    def check_catalog(
        payload: CatalogCheckRequest,
        user: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CATALOGS)),
    ) -> dict[str, Any]:
        return control.check_catalog(payload.payload(), user)

    @api.patch("/api/catalogs/{catalog_id}", tags=["catalogs"])
    def update_catalog(
        catalog_id: int,
        payload: CatalogRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CATALOGS)),
    ) -> dict[str, Any]:
        return control.update_catalog(catalog_id, payload.payload(), actor)

    @api.delete("/api/catalogs/{catalog_id}", tags=["catalogs"])
    def delete_catalog(
        catalog_id: int,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CATALOGS)),
    ) -> dict[str, Any]:
        return control.delete_catalog(catalog_id, actor)

    @api.get("/api/connector-types", tags=["catalogs"])
    def list_connector_types(_: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.list_connector_types()

    @api.get("/api/connector-drivers", tags=["catalogs"])
    def list_connector_drivers(_: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CATALOGS))) -> dict[str, Any]:
        return control.list_connector_drivers()

    @api.post("/api/connector-drivers/{connector_type}", status_code=201, tags=["catalogs"])
    async def upload_connector_driver(
        connector_type: str,
        request: Request,
        filename: str = "",
        admin: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CATALOGS)),
    ) -> dict[str, Any]:
        # The JAR arrives as the raw request body (no multipart dependency);
        # the browser posts the File object directly as the fetch body.
        data = await request.body()
        return control.store_connector_driver(connector_type, filename, data, admin)

    @api.delete("/api/connector-drivers/{connector_type}", tags=["catalogs"])
    def delete_connector_driver(
        connector_type: str, _: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CATALOGS))
    ) -> dict[str, Any]:
        return control.delete_connector_driver(connector_type)

    @api.get("/api/node-config/{cluster_id}/driver/{connector_type}", include_in_schema=False)
    def node_driver(cluster_id: int, connector_type: str, token: str) -> FileResponse:
        path, filename = control.node_driver_file(cluster_id, connector_type, token)
        return FileResponse(path, media_type="application/java-archive", filename=filename)

    @api.get("/api/query-tabs", tags=["queries"])
    def list_query_tabs(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.list_query_tabs(user)

    @api.post("/api/query-tabs", status_code=201, tags=["queries"])
    def create_query_tab(payload: QueryTabCreateRequest, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.create_query_tab(payload.payload(), user)

    @api.patch("/api/query-tabs/{tab_id}", tags=["queries"])
    def update_query_tab(
        tab_id: int,
        payload: QueryTabUpdateRequest,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        return control.update_query_tab(tab_id, payload.model_dump(by_alias=True, exclude_unset=True), user)

    @api.delete("/api/query-tabs/{tab_id}", tags=["queries"])
    def delete_query_tab(tab_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.delete_query_tab(tab_id, user)

    @api.get("/api/saved-queries", tags=["queries"])
    def list_saved_queries(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.list_saved_queries(user)

    @api.post("/api/saved-queries", status_code=201, tags=["queries"])
    def create_saved_query(payload: SavedQueryCreateRequest, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.create_saved_query(payload.payload(), user)

    @api.patch("/api/saved-queries/{query_id}", tags=["queries"])
    def update_saved_query(
        query_id: int,
        payload: SavedQueryUpdateRequest,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        return control.update_saved_query(query_id, payload.model_dump(by_alias=True, exclude_unset=True), user)

    @api.delete("/api/saved-queries/{query_id}", tags=["queries"])
    def delete_saved_query(query_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.delete_saved_query(query_id, user)

    @api.get("/api/notebooks", tags=["notebooks"])
    def list_notebooks(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.list_notebooks(user)

    @api.post("/api/notebooks", status_code=201, tags=["notebooks"])
    def create_notebook(payload: NotebookCreateRequest, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.create_notebook(payload.payload(), user)

    @api.patch("/api/notebooks/{notebook_id}", tags=["notebooks"])
    def update_notebook(
        notebook_id: int,
        payload: NotebookUpdateRequest,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        return control.update_notebook(notebook_id, payload.model_dump(by_alias=True, exclude_unset=True), user)

    @api.delete("/api/notebooks/{notebook_id}", tags=["notebooks"])
    def delete_notebook(notebook_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.delete_notebook(notebook_id, user)

    @api.get("/api/notebooks/{notebook_id}/cells", tags=["notebooks"])
    def list_notebook_cells(notebook_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.list_notebook_cells(notebook_id, user)

    @api.post("/api/notebooks/{notebook_id}/cells", status_code=201, tags=["notebooks"])
    def create_notebook_cell(
        notebook_id: int,
        payload: NotebookCellCreateRequest,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        return control.create_notebook_cell(notebook_id, payload.payload(), user)

    @api.patch("/api/notebooks/{notebook_id}/cells/{cell_id}", tags=["notebooks"])
    def update_notebook_cell(
        notebook_id: int,
        cell_id: int,
        payload: NotebookCellUpdateRequest,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        return control.update_notebook_cell(
            notebook_id, cell_id, payload.model_dump(by_alias=True, exclude_unset=True), user
        )

    @api.delete("/api/notebooks/{notebook_id}/cells/{cell_id}", tags=["notebooks"])
    def delete_notebook_cell(
        notebook_id: int,
        cell_id: int,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        return control.delete_notebook_cell(notebook_id, cell_id, user)

    # --- Scheduled SQL jobs (Phase 3) ---------------------------------------

    @api.get("/api/jobs", tags=["jobs"])
    def list_jobs(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.list_jobs(user)

    @api.post("/api/jobs", status_code=201, tags=["jobs"])
    def create_job(payload: JobCreateRequest, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.create_job(payload.model_dump(by_alias=True, exclude_unset=True), user)

    @api.patch("/api/jobs/{job_id}", tags=["jobs"])
    def update_job(
        job_id: int, payload: JobUpdateRequest, user: dict[str, Any] = Depends(require_user)
    ) -> dict[str, Any]:
        return control.update_job(job_id, payload.model_dump(by_alias=True, exclude_unset=True), user)

    @api.delete("/api/jobs/{job_id}", tags=["jobs"])
    def delete_job(job_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.delete_job(job_id, user)

    @api.post("/api/jobs/{job_id}/run", tags=["jobs"])
    def run_job(job_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.run_job_now(job_id, user)

    @api.get("/api/jobs/{job_id}/runs", tags=["jobs"])
    def job_runs(job_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.list_job_runs(job_id, user)

    # --- Sharing, autocomplete, search, query details (Phase 3) -------------

    @api.get("/api/saved-queries/{query_id}/shares", tags=["queries"])
    def saved_query_shares(query_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.list_entity_shares("saved_query", query_id, user)

    @api.post("/api/saved-queries/{query_id}/shares", status_code=201, tags=["queries"])
    def share_saved_query(
        query_id: int, payload: ShareRequest, user: dict[str, Any] = Depends(require_user)
    ) -> dict[str, Any]:
        return control.share_entity("saved_query", query_id, payload.payload(), user)

    @api.delete("/api/saved-queries/{query_id}/shares/{share_id}", tags=["queries"])
    def unshare_saved_query(
        query_id: int, share_id: int, user: dict[str, Any] = Depends(require_user)
    ) -> dict[str, Any]:
        return control.unshare_entity("saved_query", query_id, share_id, user)

    @api.get("/api/notebooks/{notebook_id}/shares", tags=["notebooks"])
    def notebook_shares(notebook_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.list_entity_shares("notebook", notebook_id, user)

    @api.post("/api/notebooks/{notebook_id}/shares", status_code=201, tags=["notebooks"])
    def share_notebook(
        notebook_id: int, payload: ShareRequest, user: dict[str, Any] = Depends(require_user)
    ) -> dict[str, Any]:
        return control.share_entity("notebook", notebook_id, payload.payload(), user)

    @api.delete("/api/notebooks/{notebook_id}/shares/{share_id}", tags=["notebooks"])
    def unshare_notebook(
        notebook_id: int, share_id: int, user: dict[str, Any] = Depends(require_user)
    ) -> dict[str, Any]:
        return control.unshare_entity("notebook", notebook_id, share_id, user)

    @api.get("/api/clusters/{cluster_id}/autocomplete", tags=["clusters"])
    def cluster_autocomplete(cluster_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.autocomplete_metadata(cluster_id, user)

    @api.get("/api/search", tags=["queries"])
    def global_search(q: str = "", user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.global_search(q, user)

    @api.get("/api/query/{query_id}/details", tags=["queries"])
    def query_details(query_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.query_details(query_id, user)

    # --- Observability & ops (Phase 5) ---------------------------------------

    @api.get("/metrics", response_class=PlainTextResponse, tags=["observability"])
    def prometheus_metrics(_: dict[str, Any] = Depends(require_user)) -> PlainTextResponse:
        # Scrape with an API token: Authorization: Bearer tht_...
        return PlainTextResponse(control.prometheus_metrics(), media_type="text/plain; version=0.0.4; charset=utf-8")

    @api.get("/api/clusters/{cluster_id}/stats", tags=["clusters"])
    def cluster_stats(
        cluster_id: int, hours: int = 24, user: dict[str, Any] = Depends(require_user)
    ) -> dict[str, Any]:
        return control.cluster_stats(cluster_id, hours=hours, user=user)

    @api.get("/api/notifications", tags=["settings"])
    def get_notifications(_: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS))) -> dict[str, Any]:
        return {"notifications": control.notification_settings(), "events": list(NOTIFICATION_EVENTS)}

    @api.put("/api/notifications", tags=["settings"])
    def put_notifications(
        payload: NotificationSettingsRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS)),
    ) -> dict[str, Any]:
        return control.set_notification_settings(payload.model_dump(by_alias=True, exclude_unset=True), actor)

    @api.get("/api/ask-settings", tags=["settings"])
    def get_ask_settings(_: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS))) -> dict[str, Any]:
        return {"ask_trino": control.ask_trino_settings()}

    @api.put("/api/ask-settings", tags=["settings"])
    def put_ask_settings(
        payload: AskTrinoSettingsRequest,
        actor: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS)),
    ) -> dict[str, Any]:
        return control.set_ask_trino_settings(payload.model_dump(by_alias=True, exclude_unset=True), actor)

    @api.get("/api/costs", tags=["clusters"])
    def monthly_costs(_: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_CLUSTERS))) -> dict[str, Any]:
        return control.monthly_costs()

    # --- MCP server (read-only SQL for AI clients) ---------------------------
    # Minimal Streamable-HTTP MCP endpoint (JSON-RPC 2.0 over POST). Auth is
    # the normal session/API-token layer, so tools act as the caller and
    # inherit their grants; SQL passes the validate_read_only_sql boundary.

    MCP_PROTOCOL_VERSION = "2025-03-26"
    MCP_TOOLS = [
        {
            "name": "list_clusters",
            "description": "List the Trino clusters you can query (id, name, status, catalogs).",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "browse_metadata",
            "description": "Browse catalogs, schemas, tables, and columns of a cluster. "
            "Omit catalog to list catalogs; add schema/table to drill down.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "cluster_id": {"type": "integer"},
                    "catalog": {"type": "string"},
                    "schema": {"type": "string"},
                    "table": {"type": "string"},
                },
                "required": ["cluster_id"],
            },
        },
        {
            "name": "run_query",
            "description": "Run one read-only SELECT statement on a cluster and return rows "
            "(display-capped). Any write or DDL statement is rejected. Identical re-runs "
            "within the result-cache window may be served from cache (cached=true in the "
            "response); pass fresh=true to force re-execution.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "cluster_id": {"type": "integer"},
                    "sql": {"type": "string"},
                    "catalog": {"type": "string"},
                    "schema": {"type": "string"},
                    "fresh": {"type": "boolean"},
                },
                "required": ["cluster_id", "sql"],
            },
        },
    ]

    def _mcp_call_tool(name: str, arguments: dict[str, Any], user: dict[str, Any]) -> Any:
        if name == "list_clusters":
            return control.list_clusters(user)
        if name == "browse_metadata":
            return control.cluster_metadata(
                int(arguments.get("cluster_id")),
                catalog=str(arguments.get("catalog") or ""),
                schema_name=str(arguments.get("schema") or ""),
                table=str(arguments.get("table") or ""),
                user=user,
            )
        if name == "run_query":
            return control.run_readonly_sql(arguments, user)
        raise ApiError(400, f"Unknown tool: {name}")

    @api.post("/mcp", include_in_schema=False)
    async def mcp_endpoint(request: Request) -> Response:
        user = require_user(request)
        try:
            message = await request.json()
        except Exception:
            return JSONResponse(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
                status_code=400,
            )
        if not isinstance(message, dict):
            return JSONResponse(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Batch requests are not supported"}},
                status_code=400,
            )
        method = message.get("method", "")
        message_id = message.get("id")
        if message_id is None:
            # Notification (e.g. notifications/initialized): acknowledge, no body.
            return Response(status_code=202)

        def reply(result: Any) -> JSONResponse:
            return JSONResponse({"jsonrpc": "2.0", "id": message_id, "result": result})

        if method == "initialize":
            return reply(
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "trinohub", "version": api.version},
                }
            )
        if method == "ping":
            return reply({})
        if method == "tools/list":
            return reply({"tools": MCP_TOOLS})
        if method == "tools/call":
            params = message.get("params") or {}
            try:
                result = _mcp_call_tool(
                    str(params.get("name", "")), params.get("arguments") or {}, user
                )
                content = [{"type": "text", "text": json.dumps(result, default=str)}]
                return reply({"content": content, "isError": False})
            except ApiError as exc:
                return reply({"content": [{"type": "text", "text": exc.message}], "isError": True})
        return JSONResponse(
            {"jsonrpc": "2.0", "id": message_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
        )

    @api.get("/api/query-history", tags=["queries"])
    def list_query_history(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.list_query_history(user)

    @api.post("/api/query", status_code=201, tags=["queries"])
    def create_query(payload: QueryRequest, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.create_query(payload.payload(), user)

    @api.post("/api/ask", tags=["ai"])
    def ask_trino(payload: AskRequest, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.ask_trino(payload.payload(), user)

    @api.get("/api/query/{query_id}", tags=["queries"])
    def get_query(query_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.get_query(query_id, user)

    @api.delete("/api/query/{query_id}", tags=["queries"])
    def cancel_query(query_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return control.cancel_query(query_id, user)

    @api.get("/api/query/{query_id}/csv", tags=["queries"])
    def query_csv(query_id: int, user: dict[str, Any] = Depends(require_user)) -> StreamingResponse:
        control.get_query(query_id, user)
        payload = control.query_csv_payload(query_id, user)

        def rows():
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow([column.get("name", "") for column in payload["columns"]])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            for row in payload["rows"]:
                writer.writerow(row)
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

        return StreamingResponse(
            rows(),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="trinohub-query-{query_id}.csv"',
                "X-TrinoHub-CSV-Rows": str(payload["download_row_count"]),
                "X-TrinoHub-CSV-Truncated": "true" if payload["download_truncated"] else "false",
            },
        )

    @api.get("/api/admin/readiness", tags=["admin"])
    def readiness(_: dict[str, Any] = Depends(require_privilege(PRIVILEGE_MANAGE_SETTINGS))) -> dict[str, Any]:
        with control.conn() as conn:
            counts = {
                table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ["clusters", "provider_resources", "query_runs", "cluster_events", "scaling_events", "sessions"]
            }
        return {
            "ok": counts["provider_resources"] == 0,
            "counts": counts,
            "static_dir": str(selected_static),
            "db_path": str(selected_db),
        }

    # In-app Support / documentation. Markdown lives in the repo-root docs/ dir
    # and is rendered client-side. Served under /api/help (NOT /docs, which is
    # FastAPI's Swagger UI). Admin topics are filtered from the manifest and
    # refused per-slug for non-admin users.
    HELP_SLUG_PATTERN = re.compile(r"^[a-z0-9-]+$")

    def load_help_manifest() -> dict[str, Any]:
        manifest_path = selected_docs / "manifest.json"
        if not manifest_path.is_file():
            return {"groups": []}
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            raise ApiError(500, "Documentation manifest is unavailable.") from None
        groups = data.get("groups", []) if isinstance(data, dict) else []
        return {"groups": groups}

    def help_admin_slugs(manifest: dict[str, Any]) -> set[str]:
        slugs: set[str] = set()
        for group in manifest["groups"]:
            if group.get("admin"):
                for topic in group.get("topics", []):
                    if topic.get("slug"):
                        slugs.add(topic["slug"])
        return slugs

    @api.get("/api/help/topics", tags=["help"])
    def help_topics(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        manifest = load_help_manifest()
        if user_is_operator(user):
            return manifest
        visible = [group for group in manifest["groups"] if not group.get("admin")]
        return {"groups": visible}

    @api.get("/api/help/topics/{slug}", tags=["help"])
    def help_topic(slug: str, user: dict[str, Any] = Depends(require_user)) -> PlainTextResponse:
        if not HELP_SLUG_PATTERN.fullmatch(slug):
            raise ApiError(404, "Documentation topic not found.")
        manifest = load_help_manifest()
        if slug in help_admin_slugs(manifest) and not user_is_operator(user):
            raise ApiError(403, "Admin documentation requires a management privilege.")
        target = selected_docs / f"{slug}.md"
        if not target.is_file():
            raise ApiError(404, "Documentation topic not found.")
        return PlainTextResponse(
            target.read_text(encoding="utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )

    def static_response(path: str) -> FileResponse:
        requested = "/index.html" if path in {"", "/"} else f"/{path.lstrip('/')}"
        relative = Path(requested.lstrip("/"))
        if ".." in relative.parts:
            raise ApiError(404, "Static file not found.")
        target = selected_static / relative
        if not target.is_file():
            raise ApiError(404, "Static file not found.")
        return FileResponse(target, headers={"Cache-Control": "no-store"})

    # --- Native Trino wire-protocol resume shim ------------------------------
    # The Caddy gateway routes a suspended/starting cluster's host here so a native
    # Trino client (CLI/JDBC/BI) waits for the cluster instead of getting a 503.
    # These routes are registered before the SPA catch-all so /v1/* is theirs, and
    # are exempt from the UI-CIDR middleware (gated by the gateway's own CIDRs).

    def _wire_result_response(result: dict[str, Any]) -> Response:
        kind = result.get("kind")
        if kind == "proxied":
            # Mirror the coordinator's response verbatim, preserving duplicate
            # headers (e.g. multiple Set-Cookie) via raw_headers.
            body = result["body"] or b""
            response = Response(content=body, status_code=result["status"])
            raw = [(k.encode("latin-1"), v.encode("latin-1")) for (k, v) in result["headers"]]
            raw.append((b"content-length", str(len(body)).encode("latin-1")))
            response.raw_headers = raw
            return response
        if kind == "no_route":
            return PlainTextResponse("No running cluster for this hostname.", status_code=503)
        # queued / failed: a synthetic Trino QueryResults JSON body.
        return JSONResponse(result["results"])

    @api.post("/v1/statement", include_in_schema=False)
    async def wire_statement(request: Request) -> Response:
        host = request.headers.get("host", "")
        body = await request.body()
        headers = list(request.headers.items())
        result = await run_in_threadpool(control.wire_submit_statement, host, body, headers)
        return _wire_result_response(result)

    @api.get("/v1/statement/resuming/{shim_id}/{seq}", include_in_schema=False)
    async def wire_resuming(shim_id: str, seq: int) -> Response:
        # Pace the client so it doesn't busy-loop the shim while the cluster starts.
        await asyncio.sleep(WIRE_HOLD_POLL_SECONDS)
        result = await run_in_threadpool(control.wire_poll_resuming, shim_id, seq)
        return _wire_result_response(result)

    @api.api_route("/v1/{path:path}", methods=["GET", "POST", "DELETE"], include_in_schema=False)
    async def wire_catch_all(path: str, request: Request) -> Response:
        host = request.headers.get("host", "")
        body = await request.body()
        headers = list(request.headers.items())
        path_qs = "/v1/" + path
        if request.url.query:
            path_qs += "?" + request.url.query
        result = await run_in_threadpool(
            control.wire_proxy, host, request.method, path_qs, headers, body
        )
        return _wire_result_response(result)

    @api.head("/", include_in_schema=False)
    @api.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return static_response("/")

    @api.head("/{asset_path:path}", include_in_schema=False)
    @api.get("/{asset_path:path}", include_in_schema=False)
    def static_asset(asset_path: str) -> FileResponse:
        if asset_path.startswith("api/"):
            raise ApiError(404, "API route not found.")
        return static_response(asset_path)

    return api


app = create_app()
