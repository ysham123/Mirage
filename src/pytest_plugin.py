"""Pytest fixture for Mirage integration tests.

Usage in a downstream repo's ``conftest.py``:

    from src.pytest_plugin import mirage_session  # re-export as a fixture

Then any test can request ``mirage_session`` and get a ``MirageSession`` that:

- derives a stable run_id from the test's nodeid
- tears down by calling ``assert_clean()``, so any risky action fails the test
"""

from __future__ import annotations

import re

import pytest

from src.httpx_client import MirageSession


_RUN_ID_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


@pytest.fixture
def mirage_session(request: pytest.FixtureRequest):
    run_id = _run_id_from_nodeid(request.node.nodeid)
    session = MirageSession(run_id=run_id)
    with session:
        yield session
        session.assert_clean()


def _run_id_from_nodeid(nodeid: str) -> str:
    return _RUN_ID_SAFE.sub("-", nodeid).strip("-") or "mirage-test"
