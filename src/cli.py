from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

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


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
