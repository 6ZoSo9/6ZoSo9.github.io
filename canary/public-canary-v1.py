#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

MARKER = "VOID_PUBLIC_AGENT_CANARY_V1_EXACT_GREEN"
CLIENTS = {
    "python": [sys.executable, "clients/void-agent-client.py", "smoke"],
    "node": ["node", "clients/void-agent-client.mjs", "smoke"],
    "shell": ["bash", "clients/void-agent-client.sh", "smoke"],
}
CLIENT_PATHS = [
    Path("clients/void-agent-client.py"),
    Path("clients/void-agent-client.mjs"),
    Path("clients/void-agent-client.sh"),
]


class CanaryError(RuntimeError):
    pass


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command_version(args: list[str]) -> str:
    process = subprocess.run(
        args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if process.returncode != 0:
        raise CanaryError(f"version command failed: {' '.join(args)}")
    return process.stdout.strip().splitlines()[0]


def run_json_command(
    label: str,
    command: list[str],
) -> dict[str, Any]:
    process = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )

    if process.returncode != 0:
        raise CanaryError(
            f"{label} failed: "
            f"{(process.stderr or process.stdout).strip()}"
        )

    try:
        value = json.loads(process.stdout)
    except Exception as exc:
        raise CanaryError(
            f"{label} returned invalid JSON: {exc}"
        ) from exc

    if not isinstance(value, dict):
        raise CanaryError(
            f"{label} JSON root differs"
        )

    return value


def validate_https_endpoints(
    label: str,
    value: dict[str, Any],
) -> None:
    for key in (
        "mcpEndpoint",
        "a2aEndpoint",
        "a2aAgentCard",
    ):
        endpoint = value.get(key)

        if (
            not isinstance(endpoint, str)
            or not endpoint.startswith("https://")
        ):
            raise CanaryError(
                f"{label} {key} is not HTTPS"
            )


def run_client(
    label: str,
    command: list[str],
    *,
    require_endpoints: bool,
) -> dict[str, Any]:
    value = run_json_command(
        f"{label} client",
        command,
    )

    if value.get("status") != "exact_green":
        raise CanaryError(
            f"{label} client status differs"
        )

    if value.get("mutationPerformed") is not False:
        raise CanaryError(
            f"{label} mutation boundary differs"
        )

    if require_endpoints:
        validate_https_endpoints(
            label,
            value,
        )

    return value


def run_shell_discovery() -> dict[str, Any]:
    value = run_json_command(
        "shell stable discovery",
        [
            "bash",
            "clients/void-agent-client.sh",
            "discover",
        ],
    )

    validate_https_endpoints(
        "shell discovery",
        value,
    )

    for key in (
        "discoveryUrl",
        "mcpMetadataUrl",
        "a2aCatalogueUrl",
    ):
        url = value.get(key)

        if (
            not isinstance(url, str)
            or not url.startswith("https://")
        ):
            raise CanaryError(
                f"shell discovery {key} is not HTTPS"
            )

    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    python_smoke = run_client(
        "python",
        CLIENTS["python"],
        require_endpoints=True,
    )
    node_smoke = run_client(
        "node",
        CLIENTS["node"],
        require_endpoints=True,
    )
    shell_smoke = run_client(
        "shell",
        CLIENTS["shell"],
        require_endpoints=False,
    )
    shell_discovery = run_shell_discovery()

    shell_smoke = {
        **shell_smoke,
        "mcpEndpoint":
            shell_discovery["mcpEndpoint"],
        "a2aEndpoint":
            shell_discovery["a2aEndpoint"],
        "a2aAgentCard":
            shell_discovery["a2aAgentCard"],
        "endpointSource":
            "clients/void-agent-client.sh discover",
        "stableDiscovery":
            shell_discovery,
    }

    smokes = {
        "python": python_smoke,
        "node": node_smoke,
        "shell": shell_smoke,
    }

    endpoint_sets = {
        (
            value["mcpEndpoint"],
            value["a2aEndpoint"],
            value["a2aAgentCard"],
        )
        for value in smokes.values()
    }
    if len(endpoint_sets) != 1:
        raise CanaryError("client canaries resolved different endpoints")

    mcp_endpoint, a2a_endpoint, a2a_card = next(iter(endpoint_sets))

    clients = {}
    for path in CLIENT_PATHS:
        if not path.is_file():
            raise CanaryError(f"client file missing: {path}")
        clients[str(path)] = {
            "sha256": sha_file(path),
            "bytes": path.stat().st_size,
        }

    captured = dt.datetime.now(dt.timezone.utc)
    evidence = {
        "schema": "void-public-agent-canary-evidence-v1",
        "marker": MARKER,
        "status": "exact_green",
        "capturedAtUtc": captured.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repository": os.environ.get("GITHUB_REPOSITORY", "external"),
        "commit": os.environ.get("GITHUB_SHA", "external"),
        "workflow": os.environ.get("GITHUB_WORKFLOW", "external"),
        "workflowRef": os.environ.get("GITHUB_WORKFLOW_REF", "external"),
        "run": {
            "id": os.environ.get("GITHUB_RUN_ID", "external"),
            "number": os.environ.get("GITHUB_RUN_NUMBER", "external"),
            "attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "external"),
            "event": os.environ.get("GITHUB_EVENT_NAME", "external"),
            "ref": os.environ.get("GITHUB_REF", "external"),
        },
        "runner": {
            "os": os.environ.get("RUNNER_OS", platform.system()),
            "arch": os.environ.get("RUNNER_ARCH", platform.machine()),
            "name": os.environ.get("RUNNER_NAME", "external"),
            "python": command_version([sys.executable, "--version"]),
            "node": command_version(["node", "--version"]),
            "curl": command_version(["curl", "--version"]),
        },
        "resolvedEndpoints": {
            "mcp": mcp_endpoint,
            "a2a": a2a_endpoint,
            "a2aAgentCard": a2a_card,
        },
        "clients": clients,
        "smokes": smokes,
        "checks": {
            "pythonExactGreen": True,
            "nodeExactGreen": True,
            "shellExactGreen": True,
            "shellDiscoveryExact": True,
            "endpointAgreementExact": True,
            "publicHttpsOnly": True,
            "mutationPerformed": False,
            "walletLedgerTransactionPaymentPerformed": False,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"evidence={args.output}")
    print(f"evidence_sha256={sha_file(args.output)}")
    print(MARKER)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CanaryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
