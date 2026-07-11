#!/usr/bin/env python
"""Release-time end-to-end runner for the TrinoHub control plane.

Run the full end-to-end scenario suite and print a release-friendly summary.
Use this as a release gate: it exits non-zero if any scenario fails.

Usage (always use the project virtualenv so FastAPI route coverage is exercised
rather than silently skipped)::

    .venv/bin/python testing/run_e2e.py            # run everything
    .venv/bin/python testing/run_e2e.py -v         # verbose, per-test names
    .venv/bin/python testing/run_e2e.py 04 07      # only scenarios 04 and 07
    .venv/bin/python testing/run_e2e.py queries    # name substring match

No AWS calls are made and no billable resources are launched: the suite injects
an in-memory fake AWS and fake Trino (see ``testing/harness.py``).
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCENARIOS_DIR = REPO_ROOT / "testing" / "scenarios"


def _preflight() -> None:
    """Fail loudly if the interpreter cannot import the app under test.

    Bare ``python3`` often lacks FastAPI; in that case the suite would import
    but skip the route coverage. We refuse to run a hollow pass.
    """
    try:
        import fastapi  # noqa: F401
        import trinohub.api  # noqa: F401
    except ModuleNotFoundError as exc:
        sys.stderr.write(
            f"\nERROR: cannot import the application ({exc}).\n"
            "Run with the project virtualenv:\n"
            "    .venv/bin/python testing/run_e2e.py\n\n"
        )
        raise SystemExit(2)


def _load(filters: list[str]) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    discovered = loader.discover(start_dir=str(SCENARIOS_DIR), pattern="test_*.py", top_level_dir=str(REPO_ROOT))
    if not filters:
        return discovered

    selected = unittest.TestSuite()

    def walk(suite: unittest.TestSuite) -> None:
        for item in suite:
            if isinstance(item, unittest.TestSuite):
                walk(item)
            else:
                name = item.id().lower()
                if any(f.lower() in name for f in filters):
                    selected.addTest(item)

    walk(discovered)
    return selected


def main(argv: list[str]) -> int:
    args = [a for a in argv if a not in ("-v", "--verbose")]
    verbosity = 2 if len(args) != len(argv) else 1

    _preflight()
    suite = _load(args)
    count = suite.countTestCases()
    if count == 0:
        sys.stderr.write("No scenarios matched the given filters.\n")
        return 2

    print(f"TrinoHub end-to-end suite — running {count} scenario test(s)\n")
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    elapsed = time.monotonic() - started

    print("\n" + "=" * 64)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(
        f"  ran {result.testsRun}  |  passed {passed}  |  "
        f"failed {len(result.failures)}  |  errors {len(result.errors)}  |  "
        f"skipped {len(result.skipped)}  |  {elapsed:.1f}s"
    )
    print("  RESULT:", "PASS ✅" if result.wasSuccessful() else "FAIL ❌")
    print("=" * 64)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
