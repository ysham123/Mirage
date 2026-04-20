from pathlib import Path

from src.cli import main


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_validate_config_cli_succeeds_for_valid_files(tmp_path, capsys):
    mocks = _write(
        tmp_path / "mocks.yaml",
        "mocks:\n"
        "  - name: get_supplier\n"
        "    method: GET\n"
        "    path: /v1/suppliers/SUP-001\n"
        "    response:\n"
        "      status_code: 200\n"
        "      json:\n"
        "        supplier_id: SUP-001\n",
    )
    policies = _write(
        tmp_path / "policies.yaml",
        "policies:\n"
        "  - name: enforce_bid_limit\n"
        "    method: POST\n"
        "    path: /v1/submit_bid\n"
        "    field: bid_amount\n"
        "    operator: lte\n"
        "    value: 10000\n"
        "    message: Agents cannot submit bids above the approved threshold.\n",
    )

    exit_code = main(
        [
            "validate-config",
            "--mocks-path",
            str(mocks),
            "--policies-path",
            str(policies),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Mirage config valid." in output
    assert "Mocks: 1" in output
    assert "Policies: 1" in output


def test_validate_config_cli_fails_for_invalid_files(tmp_path, capsys):
    mocks = _write(tmp_path / "mocks.yaml", "mocks: []\n")
    policies = _write(
        tmp_path / "policies.yaml",
        "policies:\n"
        "  - name: broken_policy\n"
        "    field: bid_amount\n"
        "    operator: typo\n"
        "    message: bad op\n",
    )

    exit_code = main(
        [
            "validate-config",
            "--mocks-path",
            str(mocks),
            "--policies-path",
            str(policies),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Mirage config invalid:" in output
    assert "policies.yaml" in output
    assert "broken_policy" in output


def test_validate_config_cli_fails_for_malformed_yaml(tmp_path, capsys):
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

    exit_code = main(
        [
            "validate-config",
            "--mocks-path",
            str(mocks),
            "--policies-path",
            str(policies),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Mirage config invalid:" in output
    assert "invalid YAML" in output


def test_validate_config_cli_rejects_operator_value_type_mismatch(tmp_path, capsys):
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

    exit_code = main(
        [
            "validate-config",
            "--mocks-path",
            str(mocks),
            "--policies-path",
            str(policies),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "compare_bad_type" in output
    assert "numeric value" in output
