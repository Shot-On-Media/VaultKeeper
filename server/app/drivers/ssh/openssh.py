from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass


@dataclass(frozen=True)
class SSHHostKeyResult:
    fingerprint_sha256: str
    known_hosts_entry: str


@dataclass(frozen=True)
class SSHCommandResult:
    exit_code: int
    stdout: str
    stderr: str


class OpenSSHDriver:
    def scan_host_key(
        self,
        hostname: str,
        port: int,
        timeout_seconds: int = 10,
    ) -> SSHHostKeyResult:
        scan = subprocess.run(
            ["ssh-keyscan", "-p", str(port), "-T", str(timeout_seconds), hostname],
            check=False,
            capture_output=True,
            text=True,
        )
        known_hosts_entry = scan.stdout.strip()
        if scan.returncode != 0 or known_hosts_entry == "":
            raise RuntimeError(scan.stderr.strip() or "SSH host key scan failed.")

        fingerprint = subprocess.run(
            ["ssh-keygen", "-l", "-f", "-"],
            input=known_hosts_entry,
            check=False,
            capture_output=True,
            text=True,
        )
        if fingerprint.returncode != 0:
            raise RuntimeError(
                fingerprint.stderr.strip() or "SSH host key fingerprint failed."
            )
        fingerprint_sha256 = self._parse_sha256_fingerprint(fingerprint.stdout)
        return SSHHostKeyResult(
            fingerprint_sha256=fingerprint_sha256,
            known_hosts_entry=known_hosts_entry,
        )

    def run_checked_command(
        self,
        hostname: str,
        port: int,
        username: str,
        host_key: SSHHostKeyResult,
        command: list[str],
        timeout_seconds: int = 10,
    ) -> SSHCommandResult:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as known_hosts:
            known_hosts.write(host_key.known_hosts_entry + "\n")
            known_hosts.flush()
            result = subprocess.run(
                [
                    "ssh",
                    "-p",
                    str(port),
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "StrictHostKeyChecking=yes",
                    "-o",
                    f"UserKnownHostsFile={known_hosts.name}",
                    f"{username}@{hostname}",
                    *command,
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        return SSHCommandResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def _parse_sha256_fingerprint(self, output: str) -> str:
        for line in output.splitlines():
            parts = line.split()
            for part in parts:
                if part.startswith("SHA256:"):
                    return part
        raise RuntimeError("SSH host key fingerprint was not found.")
