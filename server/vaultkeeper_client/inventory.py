from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import Any


def collect_inventory() -> dict[str, Any]:
    return {
        "os": {
            "id": _read_os_release_value("ID", "unknown"),
            "name": _read_os_release_value("PRETTY_NAME", "unknown"),
            "kernel": platform.release(),
            "architecture": platform.machine(),
        },
        "resources": {
            "cpu_count": os.cpu_count() or 0,
            "memory_total_kib": _read_memory_total_kib(),
            "root_total_kib": _read_root_disk_total_kib(),
            "root_available_kib": _read_root_disk_available_kib(),
        },
        "tools": {
            "python3": shutil.which("python3"),
            "mariadb": shutil.which("mariadb"),
            "rsync": shutil.which("rsync"),
        },
    }


def _read_os_release_value(key: str, default: str) -> str:
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        return default
    for line in os_release.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator == "" or name != key:
            continue
        return value.strip().strip('"')
    return default


def _read_memory_total_kib() -> int:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return 0
    for line in meminfo.read_text(encoding="utf-8").splitlines():
        if not line.startswith("MemTotal:"):
            continue
        parts = line.split()
        if len(parts) < 2:
            return 0
        return _parse_int(parts[1])
    return 0


def _read_root_disk_total_kib() -> int:
    usage = shutil.disk_usage("/")
    return usage.total // 1024


def _read_root_disk_available_kib() -> int:
    usage = shutil.disk_usage("/")
    return usage.free // 1024


def _parse_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0
