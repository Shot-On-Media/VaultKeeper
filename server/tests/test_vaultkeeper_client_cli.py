from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vaultkeeper_client.cli import main


def test_client_inventory_outputs_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["inventory"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["os"]["kernel"]
    assert payload["os"]["architecture"]
    assert isinstance(payload["resources"]["cpu_count"], int)
    assert isinstance(payload["resources"]["memory_total_kib"], int)
    assert "python3" in payload["tools"]


def test_client_version_command() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "vaultkeeper_client", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.startswith("vaultkeeper ")


def test_client_executable_shim() -> None:
    result = subprocess.run(
        ["bin/vaultkeeper", "inventory"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["tools"]["python3"] is not None


def test_client_filesystem_snapshot_streams_compressed_artifact(
    capfdbinary: pytest.CaptureFixture[bytes],
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source"
    source_path.mkdir()
    (source_path / "alpha.txt").write_text("alpha", encoding="utf-8")

    exit_code = main(["filesystem-snapshot", str(source_path)])

    captured = capfdbinary.readouterr()
    assert exit_code == 0
    assert captured.out
    assert json.loads(captured.err.decode("utf-8")) == {
        "file_count": 1,
        "source_bytes": 5,
    }


def test_client_mariadb_snapshot_streams_compressed_dump(
    capfdbinary: pytest.CaptureFixture[bytes],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run(
        command: list[str],
        check: bool,
        env: dict[str, str],
        stdout: object,
        stderr: int,
    ) -> subprocess.CompletedProcess[str]:
        _ = (command, check, env, stderr)
        assert hasattr(stdout, "write")
        stdout.write(b"CREATE DATABASE `customer`;\n")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("vaultkeeper_client.snapshots.subprocess.run", fake_run)

    exit_code = main(
        [
            "mariadb-snapshot",
            "--host",
            "127.0.0.1",
            "--port",
            "3306",
            "--user",
            "vaultkeeper",
            "--password",
            "vaultkeeper",
            "--database",
            "customer",
        ]
    )

    _ = tmp_path
    captured = capfdbinary.readouterr()
    assert exit_code == 0
    assert captured.out
    assert json.loads(captured.err.decode("utf-8")) == {"source_bytes": 28}
