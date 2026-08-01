from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from vaultkeeper_client import __version__
from vaultkeeper_client.inventory import collect_inventory
from vaultkeeper_client.snapshots import (
    print_snapshot_metadata,
    stream_filesystem_snapshot,
    stream_mariadb_snapshot,
)


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
    filesystem_parser = subparsers.add_parser(
        "filesystem-snapshot",
        help="Write a compressed filesystem snapshot to stdout.",
    )
    filesystem_parser.add_argument("source_path")
    mariadb_parser = subparsers.add_parser(
        "mariadb-snapshot",
        help="Write a compressed MariaDB dump to stdout.",
    )
    mariadb_parser.add_argument("--host", required=True)
    mariadb_parser.add_argument("--port", default=3306, type=int)
    mariadb_parser.add_argument("--user", required=True)
    mariadb_parser.add_argument("--password", required=True)
    mariadb_parser.add_argument("--database", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "inventory":
        print(json.dumps(collect_inventory(), sort_keys=True))
        return 0
    if args.command == "filesystem-snapshot":
        source_path = Path(args.source_path)
        if not source_path.is_absolute() or not source_path.is_dir():
            parser.error("source_path must be an absolute directory")
        metadata = stream_filesystem_snapshot(source_path, sys.stdout.buffer)
        print_snapshot_metadata(metadata)
        return 0
    if args.command == "mariadb-snapshot":
        metadata = stream_mariadb_snapshot(
            host=args.host,
            port=args.port,
            user=args.user,
            password=args.password,
            database_name=args.database,
            output=sys.stdout.buffer,
        )
        print_snapshot_metadata(metadata)
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2
