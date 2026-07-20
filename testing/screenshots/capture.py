"""Capture README screenshots by driving the real TrinoHub UI.

Launches the seeded demo control plane (see ``seed.py``) under uvicorn, then
drives Google Chrome via Playwright to screenshot every product view at a
retina 1440x900 viewport (2880x1800 output). No cloud resources, no real Trino.

Usage::

    .venv/bin/python testing/screenshots/capture.py            # all views
    .venv/bin/python testing/screenshots/capture.py clusters   # only matching

Output goes to ``testing/screenshots/out/`` for review; promote the good ones
into ``docs/images/`` yourself (the README references those paths).
"""

from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import uvicorn  # noqa: E402
from playwright.sync_api import Page, sync_playwright  # noqa: E402

from testing.screenshots.seed import build_demo  # noqa: E402

HOST = "127.0.0.1"
PORT = 8010  # avoid clashing with a real dev server on 8000
BASE = f"http://{HOST}:{PORT}"
OUT_DIR = REPO_ROOT / "testing" / "screenshots" / "out"
VIEWPORT = {"width": 1440, "height": 900}
SCALE = 2


def _wait_port(host: str, port: int, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"server did not open {host}:{port} within {timeout}s")


def _serve(app: object) -> uvicorn.Server:
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    _wait_port(HOST, PORT)
    return server


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def _load_app(page: Page) -> None:
    """Load the SPA shell and wait for the nav to be ready."""
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_selector('nav .nav-item[data-view-target="clusters"]', state="visible", timeout=15000)


def _goto_view(page: Page, target: str, view_id: str) -> None:
    page.click(f'nav .nav-item[data-view-target="{target}"]')
    page.wait_for_selector(f"#view-{view_id}.active", timeout=15000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(600)  # let charts/tables settle


def _shot(page: Page, name: str, *, full_page: bool = False) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUT_DIR / name), full_page=full_page)
    print(f"  captured {name}")


# ---------------------------------------------------------------------------
# Per-view capture routines
# ---------------------------------------------------------------------------
def cap_login(page: Page) -> None:
    # No session cookie on this context -> login screen.
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_selector("#loginForm", state="visible", timeout=15000)
    page.wait_for_timeout(400)
    _shot(page, "01-login.png")


def cap_clusters(page: Page) -> None:
    _load_app(page)
    _goto_view(page, "clusters", "clusters")
    _shot(page, "02-clusters.png")


def cap_cluster_detail(page: Page) -> None:
    _load_app(page)
    _goto_view(page, "clusters", "clusters")
    # Open the running analytics cluster (richer detail than a disabled one).
    page.locator("#view-clusters tr", has_text="analytics-prod").locator(
        "[data-open-cluster]"
    ).first.click()
    page.wait_for_selector("#view-cluster-detail.active", timeout=15000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(800)
    _shot(page, "03-cluster-detail.png")


def cap_create_cluster(page: Page) -> None:
    _load_app(page)
    _goto_view(page, "clusters", "clusters")
    page.click("#openCreateCluster")
    page.wait_for_selector("#view-create.active", timeout=15000)
    page.wait_for_timeout(600)
    _shot(page, "04-create-cluster.png")


def cap_catalogs(page: Page) -> None:
    _load_app(page)
    _goto_view(page, "catalogs", "catalogs")
    _shot(page, "05-catalogs.png")


def cap_sql_editor(page: Page) -> None:
    _load_app(page)
    _goto_view(page, "sql", "sql")
    # Pick the running analytics cluster + tpch/sf1, type a query, run it.
    page.select_option("#queryCluster", label="analytics-prod - Running")
    page.wait_for_timeout(500)
    try:
        page.select_option("#queryCatalog", value="tpch")
        page.wait_for_timeout(300)
        page.select_option("#querySchema", value="sf1")
    except Exception:
        pass
    page.wait_for_timeout(300)
    _set_editor(page, "SELECT region, revenue_usd\nFROM analytics.sales_by_region\nORDER BY revenue_usd DESC")
    page.click("#runQuery")
    # Wait for results to render.
    page.wait_for_timeout(2500)
    _shot(page, "06-sql-editor.png")


def cap_history(page: Page) -> None:
    _load_app(page)
    _goto_view(page, "history", "history")
    _shot(page, "07-query-history.png")


def cap_users(page: Page) -> None:
    _load_app(page)
    _goto_view(page, "users", "users")
    _shot(page, "08-users.png")


def cap_settings(page: Page) -> None:
    _load_app(page)
    _goto_view(page, "settings", "settings")
    _shot(page, "09-settings.png")


def cap_notebook(page: Page) -> None:
    _load_app(page)
    _goto_view(page, "notebooks", "notebooks")
    # Open the seeded notebook if a list is shown.
    opened = page.query_selector(".notebook-list-item, [data-open-notebook]")
    if opened:
        opened.click()
        page.wait_for_selector("text=Run all", timeout=15000)
        page.wait_for_timeout(600)
    # Run all cells so tables + charts render.
    page.get_by_role("button", name="Run all").click()
    page.wait_for_timeout(3000)
    _shot(page, "11-notebook.png", full_page=True)


def cap_jobs(page: Page) -> None:
    _load_app(page)
    _goto_view(page, "jobs", "jobs")
    _shot(page, "13-scheduled-jobs.png")


def cap_docs(page: Page) -> None:
    _load_app(page)
    _goto_view(page, "docs", "docs")
    _shot(page, "14-docs.png")


def _set_editor(page: Page, sql: str) -> None:
    """Set the SQL editor content, handling CodeMirror or a plain textarea."""
    # Try CodeMirror first.
    cm = page.query_selector(".CodeMirror")
    if cm:
        page.evaluate(
            "(sql) => { const el = document.querySelector('.CodeMirror'); if (el && el.CodeMirror) el.CodeMirror.setValue(sql); }",
            sql,
        )
        return
    ta = page.query_selector("#view-sql textarea")
    if ta:
        ta.fill(sql)


CAPTURES = {
    "login": cap_login,
    "clusters": cap_clusters,
    "cluster-detail": cap_cluster_detail,
    "create-cluster": cap_create_cluster,
    "catalogs": cap_catalogs,
    "sql-editor": cap_sql_editor,
    "history": cap_history,
    "users": cap_users,
    "settings": cap_settings,
    "notebook": cap_notebook,
    "jobs": cap_jobs,
    "docs": cap_docs,
}


def main(argv: list[str]) -> int:
    wanted = [a for a in argv if not a.startswith("-")]
    names = [n for n in CAPTURES if not wanted or any(w in n for w in wanted)]

    harness, ctx = build_demo()
    print(f"serving demo on {BASE} ...")
    _serve(ctx["app"])

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        try:
            # Authenticated context for every view except the login screen.
            authed = browser.new_context(viewport=VIEWPORT, device_scale_factor=SCALE)
            authed.add_cookies(
                [{"name": ctx["cookie_name"], "value": ctx["session_token"], "url": BASE}]
            )
            anon = browser.new_context(viewport=VIEWPORT, device_scale_factor=SCALE)

            for name in names:
                print(f"[{name}]")
                context = anon if name == "login" else authed
                page = context.new_page()
                try:
                    CAPTURES[name](page)
                except Exception as exc:  # keep going; one bad view != all bad
                    print(f"  FAILED {name}: {exc}")
                finally:
                    page.close()
        finally:
            browser.close()

    harness.close()
    print(f"\nDone. Review images in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
