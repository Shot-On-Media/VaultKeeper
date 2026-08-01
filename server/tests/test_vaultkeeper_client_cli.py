from __future__ import annotations

import json
import subprocess
import sys

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
