from pathlib import Path

import pytest

from mirage.config import MirageConfigError, load_mirage_config
from mirage.engine import MirageEngine


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_policy_invalid_operator_points_at_file_entry_and_field(tmp_path):
    mocks = _write(tmp_path / "mocks.yaml", "mocks: []\n")
    policies = _write(
        tmp_path / "policies.yaml",
        "policies:\n"
        "  - name: broken_policy\n"
        "    field: bid_amount\n"
        "    operator: typo\n"
        "    message: bad op\n",
    )

    with pytest.raises(MirageConfigError) as exc_info:
        load_mirage_config(mocks, policies)

    message = str(exc_info.value)
    assert "policies.yaml" in message
    assert "policies[0]" in message
    assert "broken_policy" in message
    assert "operator" in message
    assert "Example of a valid entry" in message


def test_mock_missing_required_field_points_at_file_entry_and_field(tmp_path):
    mocks = _write(
        tmp_path / "mocks.yaml",
        "mocks:\n"
        "  - name: get_thing\n"
        "    path: /v1/thing\n"
        "    response:\n"
        "      status_code: 200\n"
        "      json: {}\n",
    )
    policies = _write(tmp_path / "policies.yaml", "policies: []\n")

    with pytest.raises(MirageConfigError) as exc_info:
        load_mirage_config(mocks, policies)

    message = str(exc_info.value)
    assert "mocks.yaml" in message
    assert "mocks[0]" in message
    assert "get_thing" in message
    assert "method" in message


def test_missing_file_surfaces_file_not_found(tmp_path):
    missing = tmp_path / "does_not_exist.yaml"
    policies = _write(tmp_path / "policies.yaml", "policies: []\n")

    with pytest.raises(FileNotFoundError):
        load_mirage_config(missing, policies)


def test_engine_turns_config_error_into_config_error_outcome(tmp_path):
    mocks = _write(tmp_path / "mocks.yaml", "mocks: []\n")
    policies = _write(
        tmp_path / "policies.yaml",
        "policies:\n"
        "  - name: broken_policy\n"
        "    field: bid_amount\n"
        "    operator: typo\n"
        "    message: bad op\n",
    )

    engine = MirageEngine(
        mocks_path=mocks,
        policies_path=policies,
        artifact_root=tmp_path / "artifacts" / "traces",
    )
    result = engine.handle_request(
        method="POST",
        path="/v1/submit_bid",
        payload={"bid_amount": 1},
        run_id="config-error-run",
    )

    assert result.outcome == "config_error"
    assert result.policy_passed is False
    assert "policies.yaml" in result.message
    assert "broken_policy" in result.message


def test_malformed_yaml_raises_mirage_config_error(tmp_path):
    mocks = _write(tmp_path / "mocks.yaml", "mocks: []\n")
    policies = _write(
        tmp_path / "policies.yaml",
        "policies:\n"
        "  - name: broken_policy\n"
        "    field: bid_amount\n"
        "    operator: lte\n"
        "    value: [oops\n"
        "    message: malformed yaml\n",
    )

    with pytest.raises(MirageConfigError) as exc_info:
        load_mirage_config(mocks, policies)

    assert "invalid YAML" in str(exc_info.value)


def test_policy_type_validation_rejects_invalid_expected_type(tmp_path):
    mocks = _write(tmp_path / "mocks.yaml", "mocks: []\n")
    policies = _write(
        tmp_path / "policies.yaml",
        "policies:\n"
        "  - name: compare_bad_type\n"
        "    field: bid_amount\n"
        "    operator: lte\n"
        "    value: high\n"
        "    message: bad compare\n",
    )

    with pytest.raises(MirageConfigError) as exc_info:
        load_mirage_config(mocks, policies)

    message = str(exc_info.value)
    assert "compare_bad_type" in message
    assert "numeric value" in message


def test_engine_turns_malformed_yaml_into_config_error(tmp_path):
    mocks = _write(tmp_path / "mocks.yaml", "mocks: []\n")
    policies = _write(
        tmp_path / "policies.yaml",
        "policies:\n"
        "  - name: broken_policy\n"
        "    field: bid_amount\n"
        "    operator: lte\n"
        "    value: [oops\n"
        "    message: malformed yaml\n",
    )

    engine = MirageEngine(
        mocks_path=mocks,
        policies_path=policies,
        artifact_root=tmp_path / "artifacts" / "traces",
    )
    result = engine.handle_request(
        method="POST",
        path="/v1/submit_bid",
        payload={"bid_amount": 1},
        run_id="malformed-yaml-run",
    )

    assert result.outcome == "config_error"
    assert "invalid YAML" in (result.message or "")
