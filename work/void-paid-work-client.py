#!/usr/bin/env python3
"""Zero-dependency client for VOID Agent Paid Work Intake V1."""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import json
from pathlib import Path
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import quote, urlsplit

DEFAULT_METADATA = "https://6zoso9.github.io/work/live-v1.json"
TIMEOUT_SECONDS = 20
MAX_BODY_BYTES = 2 * 1024 * 1024


class ClientError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _doh_query(
    provider: str,
    hostname: str,
    record_type: str,
) -> dict[str, Any]:
    if provider == "cloudflare":
        provider_host = "cloudflare-dns.com"
        route = (
            "/dns-query?name="
            + quote(hostname, safe="")
            + "&type="
            + record_type
        )
        headers = {
            "Accept": "application/dns-json",
            "User-Agent": "void-paid-work-client-doh-cloudflare/1",
            "Connection": "close",
        }
    elif provider == "google":
        provider_host = "dns.google"
        route = (
            "/resolve?name="
            + quote(hostname, safe="")
            + "&type="
            + record_type
        )
        headers = {
            "Accept": "application/json",
            "User-Agent": "void-paid-work-client-doh-google/1",
            "Connection": "close",
        }
    else:
        raise ClientError(f"unsupported DNS provider: {provider}")

    connection = http.client.HTTPSConnection(
        provider_host,
        443,
        timeout=TIMEOUT_SECONDS,
        context=ssl.create_default_context(),
    )

    try:
        connection.request("GET", route, headers=headers)
        response = connection.getresponse()
        body = response.read(256 * 1024)
    except Exception as exc:
        raise ClientError(
            f"{provider} DNS query failed: {type(exc).__name__}: {exc}"
        ) from exc
    finally:
        connection.close()

    if response.status != 200:
        raise ClientError(
            f"{provider} DNS query returned HTTP {response.status}"
        )

    try:
        value = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise ClientError(
            f"{provider} DNS query returned invalid JSON: {exc}"
        ) from exc

    if not isinstance(value, dict):
        raise ClientError(f"{provider} DNS response root differs")

    return value


def _resolve_provider(
    provider: str,
    hostname: str,
    record_type: str,
    *,
    visited: set[tuple[str, str]],
    depth: int,
) -> list[str]:
    normalized = hostname.rstrip(".").lower()
    key = (normalized, record_type)

    if key in visited:
        return []

    if depth > 8:
        raise ClientError("DNS CNAME chain exceeded depth")

    visited.add(key)
    value = _doh_query(provider, normalized, record_type)

    if value.get("Status") not in (0, None):
        return []

    expected = 1 if record_type == "A" else 28
    addresses: list[str] = []
    aliases: list[str] = []

    for answer in value.get("Answer") or []:
        if not isinstance(answer, dict):
            continue

        data = answer.get("data")

        if not isinstance(data, str):
            continue

        if answer.get("type") == expected:
            addresses.append(data.rstrip("."))
        elif answer.get("type") == 5:
            aliases.append(data.rstrip("."))

    for alias in aliases:
        addresses.extend(
            _resolve_provider(
                provider,
                alias,
                record_type,
                visited=visited,
                depth=depth + 1,
            )
        )

    return addresses


def doh_addresses(hostname: str) -> list[str]:
    addresses: list[str] = []

    for provider in ("cloudflare", "google"):
        for record_type in ("A", "AAAA"):
            try:
                addresses.extend(
                    _resolve_provider(
                        provider,
                        hostname,
                        record_type,
                        visited=set(),
                        depth=0,
                    )
                )
            except ClientError:
                pass

    return sorted(
        set(addresses),
        key=lambda value: (":" in value, value),
    )


def _explicit_https(
    url: str,
    *,
    method: str,
    body: bytes | None,
    headers: dict[str, str],
) -> tuple[int, dict[str, str], bytes]:
    parsed = urlsplit(url)

    if parsed.scheme != "https" or not parsed.hostname:
        raise ClientError("DNS fallback supports HTTPS only")

    route = parsed.path or "/"

    if parsed.query:
        route += "?" + parsed.query

    payload = body or b""
    errors: list[str] = []

    for address in doh_addresses(parsed.hostname):
        secure = None

        try:
            raw = socket.create_connection(
                (address, parsed.port or 443),
                timeout=TIMEOUT_SECONDS,
            )
            secure = ssl.create_default_context().wrap_socket(
                raw,
                server_hostname=parsed.hostname,
            )
            request_headers = {
                "Host": parsed.netloc,
                "User-Agent": "void-paid-work-client/1",
                "Accept": "application/json",
                "Connection": "close",
                **headers,
                "Content-Length": str(len(payload)),
            }
            lines = [f"{method} {route} HTTP/1.1"]
            lines.extend(
                f"{key}: {value}"
                for key, value in request_headers.items()
            )
            lines.extend(["", ""])
            secure.sendall(
                "\r\n".join(lines).encode("ascii") + payload
            )
            response = http.client.HTTPResponse(secure)
            response.begin()
            response_body = response.read(MAX_BODY_BYTES + 1)
            response_headers = {
                key.lower(): value
                for key, value in response.getheaders()
            }

            if len(response_body) > MAX_BODY_BYTES:
                raise ClientError("response exceeds body limit")

            return response.status, response_headers, response_body
        except Exception as exc:
            errors.append(
                f"{address}: {type(exc).__name__}: {exc}"
            )
        finally:
            if secure is not None:
                try:
                    secure.close()
                except Exception:
                    pass

    raise ClientError(
        f"{method} {url} failed through all DNS fallback addresses: "
        + json.dumps(errors)
    )


def request_bytes(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    request_headers = {
        "User-Agent": "void-paid-work-client/1",
        "Accept": "application/json",
        **(headers or {}),
    }
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers=request_headers,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=TIMEOUT_SECONDS,
        ) as response:
            payload = response.read(MAX_BODY_BYTES + 1)
            status = response.status
            response_headers = {
                key.lower(): value
                for key, value in response.headers.items()
            }
    except urllib.error.HTTPError as exc:
        payload = exc.read(MAX_BODY_BYTES + 1)
        status = exc.code
        response_headers = {
            key.lower(): value
            for key, value in exc.headers.items()
        }
    except urllib.error.URLError:
        status, response_headers, payload = _explicit_https(
            url,
            method=method,
            body=body,
            headers=request_headers,
        )
    except Exception as exc:
        raise ClientError(
            f"{method} {url} failed: {type(exc).__name__}: {exc}"
        ) from exc

    if len(payload) > MAX_BODY_BYTES:
        raise ClientError("response exceeds body limit")

    return status, response_headers, payload


def get_json(url: str) -> dict[str, Any]:
    status, _, body = request_bytes(url)

    if status != 200:
        raise ClientError(f"GET {url} returned HTTP {status}")

    try:
        value = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise ClientError(f"invalid JSON from {url}: {exc}") from exc

    if not isinstance(value, dict):
        raise ClientError(f"JSON root from {url} differs")

    return value


def post_json(
    url: str,
    value: dict[str, Any],
) -> dict[str, Any]:
    status, _, body = request_bytes(
        url,
        method="POST",
        body=canonical_bytes(value),
        headers={"Content-Type": "application/json"},
    )

    try:
        response = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise ClientError(f"invalid JSON from {url}: {exc}") from exc

    if status != 200:
        raise ClientError(
            f"POST {url} returned HTTP {status}: "
            + json.dumps(response, sort_keys=True)
        )

    if not isinstance(response, dict):
        raise ClientError(f"JSON response root from {url} differs")

    return response


def resolve_metadata(metadata_url: str) -> dict[str, Any]:
    metadata = get_json(metadata_url)

    required = (
        "catalog",
        "quote",
        "submit",
        "status_template",
        "service_public_key",
        "service_key_fingerprint_sha256",
    )

    for key in required:
        if not isinstance(metadata.get(key), str):
            raise ClientError(f"metadata field is absent: {key}")

    for key in (
        "catalog",
        "quote",
        "submit",
        "service_public_key",
    ):
        if not metadata[key].startswith("https://"):
            raise ClientError(f"metadata URL is not HTTPS: {key}")

    return metadata


def openssl(
    args: list[str],
    *,
    input_bytes: bytes | None = None,
    allowed: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[bytes]:
    process = subprocess.run(
        ["openssl", *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
    )

    if process.returncode not in allowed:
        raise ClientError(
            process.stderr.decode("utf-8", errors="replace").strip()
            or "OpenSSL operation failed"
        )

    return process


def public_key_fingerprint(public_key: Path) -> str:
    result = openssl(
        [
            "pkey",
            "-pubin",
            "-in",
            str(public_key),
            "-outform",
            "DER",
        ]
    )
    return sha_bytes(result.stdout)


def generate_key(directory: Path) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    private_key = directory / "agent-ed25519-private.pem"
    public_key = directory / "agent-ed25519-public.pem"

    if private_key.exists() or public_key.exists():
        raise ClientError("key output path already exists")

    openssl(
        [
            "genpkey",
            "-algorithm",
            "ED25519",
            "-out",
            str(private_key),
        ]
    )
    openssl(
        [
            "pkey",
            "-in",
            str(private_key),
            "-pubout",
            "-out",
            str(public_key),
        ]
    )
    os.chmod(private_key, 0o600)
    os.chmod(public_key, 0o644)

    return {
        "private_key": str(private_key),
        "public_key": str(public_key),
        "public_key_fingerprint_sha256": (
            public_key_fingerprint(public_key)
        ),
    }


def download_service_key(
    metadata: dict[str, Any],
) -> Path:
    status, _, body = request_bytes(metadata["service_public_key"])

    if status != 200:
        raise ClientError("service public key download failed")

    temporary = tempfile.NamedTemporaryFile(
        prefix="void-paid-work-service-public-",
        suffix=".pem",
        delete=False,
    )
    temporary.write(body)
    temporary.flush()
    temporary.close()
    path = Path(temporary.name)

    actual = public_key_fingerprint(path)

    if actual != metadata["service_key_fingerprint_sha256"]:
        path.unlink(missing_ok=True)
        raise ClientError("service public key fingerprint differs")

    return path


def verify_service_signature(
    public_key: Path,
    payload: dict[str, Any],
    signature_base64: str,
) -> None:
    try:
        signature = base64.b64decode(
            signature_base64,
            validate=True,
        )
    except Exception as exc:
        raise ClientError("service signature is invalid base64") from exc

    with tempfile.TemporaryDirectory(
        prefix="void-paid-work-signature-"
    ) as directory:
        directory_path = Path(directory)
        payload_path = directory_path / "payload.bin"
        signature_path = directory_path / "signature.bin"
        payload_path.write_bytes(canonical_bytes(payload))
        signature_path.write_bytes(signature)

        process = openssl(
            [
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(public_key),
                "-rawin",
                "-in",
                str(payload_path),
                "-sigfile",
                str(signature_path),
            ],
            allowed=(0, 1),
        )

    if process.returncode != 0:
        raise ClientError("service signature verification failed")


def quote(
    metadata: dict[str, Any],
    *,
    agent_id: str,
    public_key: Path,
) -> dict[str, Any]:
    response = post_json(
        metadata["quote"],
        {
            "task_id": metadata["public_task_id"],
            "agent_id": agent_id,
            "agent_public_key_pem": public_key.read_text(
                encoding="utf-8"
            ),
        },
    )
    signature = response.get("service_signature_base64")

    if not isinstance(signature, str):
        raise ClientError("quote service signature is absent")

    signed = {
        key: response[key]
        for key in (
            "schema",
            "task_id",
            "agent_id",
            "agent_key_fingerprint_sha256",
            "bucket_start_utc",
            "expires_at_utc",
            "award_wc",
            "award_type",
            "operator_approval_required",
            "canonical_wc_ledger_credit_automatic",
            "quote_policy_version",
            "quote_id",
            "submission_nonce",
        )
    }
    service_key = download_service_key(metadata)

    try:
        verify_service_signature(service_key, signed, signature)
    finally:
        service_key.unlink(missing_ok=True)

    return response


def sign_payload(
    private_key: Path,
    value: dict[str, Any],
) -> str:
    with tempfile.TemporaryDirectory(
        prefix="void-paid-work-agent-signing-"
    ) as directory:
        payload_path = Path(directory) / "payload.bin"
        payload_path.write_bytes(canonical_bytes(value))
        result = openssl(
            [
                "pkeyutl",
                "-sign",
                "-inkey",
                str(private_key),
                "-rawin",
                "-in",
                str(payload_path),
            ]
        )

    return base64.b64encode(result.stdout).decode("ascii")


def submit(
    metadata: dict[str, Any],
    *,
    agent_id: str,
    private_key: Path,
    public_key: Path,
    evidence_file: Path,
) -> dict[str, Any]:
    evidence = get_local_json(evidence_file)
    current_quote = quote(
        metadata,
        agent_id=agent_id,
        public_key=public_key,
    )
    evidence_sha = sha_bytes(canonical_bytes(evidence))
    fingerprint = public_key_fingerprint(public_key)

    if (
        current_quote["agent_key_fingerprint_sha256"]
        != fingerprint
    ):
        raise ClientError("quote agent-key fingerprint differs")

    signing_payload = {
        "schema": "void-agent-paid-work-submission-signing-v1",
        "quote_id": current_quote["quote_id"],
        "task_id": current_quote["task_id"],
        "agent_id": agent_id,
        "agent_key_fingerprint_sha256": fingerprint,
        "submission_nonce": current_quote["submission_nonce"],
        "evidence_sha256": evidence_sha,
    }
    signature = sign_payload(private_key, signing_payload)

    receipt = post_json(
        metadata["submit"],
        {
            "quote_id": current_quote["quote_id"],
            "agent_id": agent_id,
            "agent_public_key_pem": public_key.read_text(
                encoding="utf-8"
            ),
            "evidence": evidence,
            "signature_base64": signature,
        },
    )

    receipt_signature = receipt.get("service_signature_base64")

    if not isinstance(receipt_signature, str):
        raise ClientError("receipt service signature is absent")

    receipt_core = {
        key: receipt[key]
        for key in (
            "schema",
            "submission_id",
            "quote_id",
            "task_id",
            "agent_id",
            "agent_key_fingerprint_sha256",
            "evidence_sha256",
            "received_at_utc",
            "status",
            "award_wc_if_approved",
            "award_type",
            "canonical_wc_ledger_credit_automatic",
        )
    }
    service_key = download_service_key(metadata)

    try:
        verify_service_signature(
            service_key,
            receipt_core,
            receipt_signature,
        )
    finally:
        service_key.unlink(missing_ok=True)

    return receipt


def get_local_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ClientError(f"cannot read evidence JSON: {exc}") from exc

    if not isinstance(value, dict):
        raise ClientError("evidence JSON root must be an object")

    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--metadata",
        default=DEFAULT_METADATA,
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser("discover")
    subparsers.add_parser("catalog")

    key_parser = subparsers.add_parser("generate-key")
    key_parser.add_argument("directory", type=Path)

    quote_parser = subparsers.add_parser("quote")
    quote_parser.add_argument("--agent-id", required=True)
    quote_parser.add_argument("--public-key", type=Path, required=True)

    submit_parser = subparsers.add_parser("submit")
    submit_parser.add_argument("--agent-id", required=True)
    submit_parser.add_argument("--private-key", type=Path, required=True)
    submit_parser.add_argument("--public-key", type=Path, required=True)
    submit_parser.add_argument("--evidence", type=Path, required=True)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("submission_id")

    args = parser.parse_args()
    metadata = resolve_metadata(args.metadata)

    if args.command == "discover":
        output = metadata
    elif args.command == "catalog":
        output = get_json(metadata["catalog"])
    elif args.command == "generate-key":
        output = generate_key(args.directory)
    elif args.command == "quote":
        output = quote(
            metadata,
            agent_id=args.agent_id,
            public_key=args.public_key,
        )
    elif args.command == "submit":
        output = submit(
            metadata,
            agent_id=args.agent_id,
            private_key=args.private_key,
            public_key=args.public_key,
            evidence_file=args.evidence,
        )
    elif args.command == "status":
        output = get_json(
            metadata["status_template"].replace(
                "{submission_id}",
                args.submission_id,
            )
        )
    else:
        raise ClientError("unsupported command")

    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ClientError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
