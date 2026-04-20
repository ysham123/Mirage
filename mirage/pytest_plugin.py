"""Pytest fixture for Mirage integration tests.

Usage in a downstream repo's ``conftest.py``:

    from mirage.pytest_plugin import mirage_session  # re-export as a fixture

Then any test can request ``mirage_session`` and get a ``MirageSession`` that:

- derives a stable run_id from the test's nodeid
- tears down by calling ``assert_clean()``, so any risky action fails the test

Optional override in the downstream repo:

    @pytest.fixture
    def mirage_session_options(tmp_path):
        return {
            "base_url": "http://127.0.0.1:8000",
            "artifact_root": tmp_path / "artifacts" / "traces",
            "auto_assert": False,
        }
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

import pytest

from .httpx_client import MirageSession


_RUN_ID_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


@pytest.fixture
def mirage_session_options() -> dict[str, Any]:
    """Override this fixture downstream to customize MirageSession kwargs.

    Supported keys are MirageSession constructor kwargs plus ``auto_assert``.
    ``run_id`` defaults to a sanitized version of the test nodeid.
    """

    return {}


@pytest.fixture
def mirage_session(
    request: pytest.FixtureRequest,
    mirage_session_options: Mapping[str, Any] | None,
):
    if mirage_session_options is None:
        options: dict[str, Any] = {}
    elif isinstance(mirage_session_options, Mapping):
        options = dict(mirage_session_options)
    else:
        raise TypeError("mirage_session_options must return a mapping or None.")

    auto_assert = _coerce_auto_assert(options.pop("auto_assert", True))
    run_id = str(options.pop("run_id", _run_id_from_nodeid(request.node.nodeid)))
    session = MirageSession(run_id=run_id, **options)
    with session:
        yield session
        if auto_assert:
            session.assert_clean()


def _run_id_from_nodeid(nodeid: str) -> str:
    return _RUN_ID_SAFE.sub("-", nodeid).strip("-") or "mirage-test"


def _coerce_auto_assert(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    raise TypeError("mirage_session_options['auto_assert'] must be a bool.")
