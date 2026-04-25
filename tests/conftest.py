from pathlib import Path
from textwrap import dedent

import pytest
from fastapi.testclient import TestClient

from mirage.engine import MirageEngine
from mirage.proxy import create_app

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCUREMENT_HARNESS_DIR = REPO_ROOT / "examples" / "procurement_harness"

DEFAULT_MOCKS = dedent(
    """
    mocks:
      - name: submit_bid
        method: POST
        path: /v1/submit_bid
        response:
          status_code: 200
          json:
            status: success
            message: Bid accepted into Mirage sandbox.
            transaction_id: trx_mock_12345
    """
).strip()

DEFAULT_POLICIES = dedent(
    """
    policies:
      - name: enforce_bid_limit
        method: POST
        path: /v1/submit_bid
        field: bid_amount
        operator: lte
        value: 10000
        message: Agents cannot submit bids above the approved threshold.
    """
).strip()


def write_mirage_config(
    root: Path,
    *,
    mocks_text: str = DEFAULT_MOCKS,
    policies_text: str = DEFAULT_POLICIES,
) -> tuple[Path, Path]:
    mocks_path = root / "mocks.yaml"
    policies_path = root / "policies.yaml"
    mocks_path.write_text(f"{mocks_text}\n", encoding="utf-8")
    policies_path.write_text(f"{policies_text}\n", encoding="utf-8")
    return mocks_path, policies_path


@pytest.fixture
def mirage_config_paths(tmp_path):
    mocks_path, policies_path = write_mirage_config(tmp_path)
    return {
        "mocks_path": mocks_path,
        "policies_path": policies_path,
        "artifact_root": tmp_path / "artifacts" / "traces",
    }


@pytest.fixture
def mirage_engine(mirage_config_paths):
    return MirageEngine(**mirage_config_paths)


@pytest.fixture
def proxy_client(mirage_engine):
    with TestClient(create_app(mirage_engine)) as client:
        yield client


@pytest.fixture
def procurement_harness_engine(tmp_path):
    return MirageEngine(
        mocks_path=PROCUREMENT_HARNESS_DIR / "mocks.yaml",
        policies_path=PROCUREMENT_HARNESS_DIR / "policies.yaml",
        artifact_root=tmp_path / "artifacts" / "traces",
    )


@pytest.fixture
def procurement_harness_client(procurement_harness_engine):
    with TestClient(create_app(procurement_harness_engine)) as client:
        yield client
