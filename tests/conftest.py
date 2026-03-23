# Pytest configuration and fixtures for Mirage engine tests.
import pytest

from src.engine import MirageEngine


@pytest.fixture
def mirage_engine(tmp_path):
    return MirageEngine(artifact_root=tmp_path / "traces")
