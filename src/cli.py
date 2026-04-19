from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

from src.config import validate_mirage_config
from src.httpx_client import MirageRunError, assert_mirage_run_clean, mirage_run_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mirage run summary and CI gating tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summarize_parser = subparsers.add_parser(
        "summarize-run",
        help="Print a human-readable summary for one Mirage run.",
    )
    _add_run_arguments(summarize_parser)

    gate_parser = subparsers.add_parser(
        "gate-run",
        help="Exit non-zero when a Mirage run is risky or missing.",
    )
    _add_run_arguments(gate_parser)

    validate_parser = subparsers.add_parser(
        "validate-config",
        help="Validate Mirage mocks/policies before starting the proxy or CI run.",
    )
    validate_parser.add_argument(
        "--mocks-path",
        type=Path,
        default=None,
        help="Optional mocks config path. Defaults to MIRAGE_MOCKS_PATH or repo-root mocks.yaml.",
    )
    validate_parser.add_argument(
        "--policies-path",
        type=Path,
        default=None,
        help="Optional policies config path. Defaults to MIRAGE_POLICIES_PATH or repo-root policies.yaml.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "summarize-run":
        summary = mirage_run_summary(args.run_id, artifact_root=args.artifact_root)
        print(summary.to_text())
        return 0

    if args.command == "gate-run":
        try:
            summary = assert_mirage_run_clean(args.run_id, artifact_root=args.artifact_root)
        except MirageRunError as exc:
            print(str(exc))
            return 1
        print(summary.to_text())
        return 0

    if args.command == "validate-config":
        mocks_path, policies_path = _resolve_config_paths(
            mocks_path=args.mocks_path,
            policies_path=args.policies_path,
        )
        try:
            summary = validate_mirage_config(mocks_path, policies_path)
        except (FileNotFoundError, OSError, ValueError) as exc:
            print(f"Mirage config invalid: {exc}")
            return 1
        print(summary.to_text())
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _add_run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-id", required=True, help="Stable Mirage run ID to summarize or gate.")
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=None,
        help="Optional Mirage trace directory override.",
    )


def _resolve_config_paths(
    *,
    mocks_path: Path | None,
    policies_path: Path | None,
) -> tuple[Path, Path]:
    root = Path(__file__).resolve().parent.parent
    return (
        mocks_path or Path(os.getenv("MIRAGE_MOCKS_PATH") or root / "mocks.yaml"),
        policies_path or Path(os.getenv("MIRAGE_POLICIES_PATH") or root / "policies.yaml"),
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
