import os
from pathlib import Path
import subprocess
import sys

from demo_ui.server import create_demo_app
from mirage import MirageSession
from mirage.cli import main
from mirage.httpx_client import create_mirage_client
from mirage.pytest_plugin import mirage_session
from mirage.proxy import create_app
from src.engine import MirageEngine


def test_public_package_exports_mirage_session():
    assert MirageSession.__name__ == "MirageSession"


def test_public_modules_are_importable():
    assert callable(main)
    assert callable(create_mirage_client)
    assert callable(mirage_session)
    assert callable(create_app)


def test_engine_prefers_local_config_from_working_directory(monkeypatch, tmp_path):
    mocks_path = tmp_path / "mocks.yaml"
    policies_path = tmp_path / "policies.yaml"
    mocks_path.write_text("mocks: []\n", encoding="utf-8")
    policies_path.write_text("policies: []\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    engine = MirageEngine()

    assert engine.mocks_path == mocks_path
    assert engine.policies_path == policies_path
    assert engine.trace_store.artifact_root == tmp_path / "artifacts" / "traces"


def test_engine_falls_back_to_bundled_defaults_outside_repo(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    engine = MirageEngine()

    assert engine.mocks_path.exists()
    assert engine.policies_path.exists()
    assert engine.mocks_path.name == "mocks.yaml"
    assert engine.policies_path.name == "policies.yaml"
    assert engine.trace_store.artifact_root == tmp_path / "artifacts" / "traces"


def test_public_package_is_not_coupled_to_top_level_src_name(tmp_path):
    fake_src = tmp_path / "src"
    fake_src.mkdir()
    (fake_src / "__init__.py").write_text("", encoding="utf-8")

    repo_root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(tmp_path), str(repo_root)])

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from mirage import MirageSession; "
                "from mirage.cli import main; "
                "from mirage.proxy import create_app; "
                "print(MirageSession.__name__); "
                "print(callable(main)); "
                "print(callable(create_app))"
            ),
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "MirageSession" in result.stdout


def test_demo_ui_server_is_importable_from_public_runtime():
    assert callable(create_demo_app)
