"""End-to-end test suite for the TrinoHub control plane.

See ``testing/README.md`` for how and when to run this suite. The package
exposes the reusable harness so scenario modules (and ad-hoc scripts) can spin
up a fully wired TrinoHub app driven through its real HTTP API, backed by an
in-memory fake AWS and fake Trino so no billable resources are launched.
"""

from .harness import E2EHarness, FakeTrino, StatefulFakeAws

__all__ = ["E2EHarness", "FakeTrino", "StatefulFakeAws"]
