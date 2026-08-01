from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from vaultkeeper_client import __version__
from vaultkeeper_client.inventory import collect_inventory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vaultkeeper",
        description="VaultKeeper remote client CLI.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "inventory",
        help="Print a local system inventory snapshot as JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "inventory":
        print(json.dumps(collect_inventory(), sort_keys=True))
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2
