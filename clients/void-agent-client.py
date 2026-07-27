#!/usr/bin/env python3
"""Zero-dependency VOID MCP + A2A discovery and read-only client."""

from __future__ import annotations

import argparse
import http.client
import json
import socket
import ssl
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any
from urllib.parse import quote, urlsplit

DEFAULT_DISCOVERY = "https://6zoso9.github.io/discovery/index-v1.json"
DEFAULT_MCP_METADATA = "https://6zoso9.github.io/mcp/remote-server-v1.json"
DEFAULT_A2A_CATALOGUE = "https://6zoso9.github.io/a2a/agent-v1.json"
MCP_PROTOCOL_VERSION = "2025-11-25"
A2A_PROTOCOL_VERSION = "1.0"
TIMEOUT_SECONDS = 20
MAX_BODY_BYTES = 4 * 1024 * 1024


class ClientError(RuntimeError):
    pass


def _doh_addresses(hostname: str) -> list[str]:
    addresses: list[str] = []

    for record_type, expected_type in (("A", 1), ("AAAA", 28)):
        connection = http.client.HTTPSConnection(
            "cloudflare-dns.com",
            443,
            timeout=TIMEOUT_SECONDS,
            context=ssl.create_default_context(),
        )
        route = (
            "/dns-query?name="
            + quote(hostname, safe="")
            + "&type="
            + record_type
        )

        try:
            connection.request(
                "GET",
                route,
                headers={
                    "Accept": "application/dns-json",
                    "User-Agent":
                        "void-agent-client-python-doh/1.0",
                    "Connection": "close",
                },
            )
            response = connection.getresponse()
            body = response.read(256 * 1024)
        except Exception as exc:
            raise ClientError(
                f"Cloudflare DoH {record_type} query failed: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        finally:
            connection.close()

        if response.status != 200:
            raise ClientError(
                f"Cloudflare DoH returned HTTP {response.status}"
            )

        try:
            value = json.loads(body.decode("utf-8"))
        except Exception as exc:
            raise ClientError(
                f"Cloudflare DoH returned invalid JSON: {exc}"
            ) from exc

        for answer in value.get("Answer") or []:
            if (
                isinstance(answer, dict)
                and answer.get("type") == expected_type
                and answer.get("data")
            ):
                addresses.append(str(answer["data"]))

    return sorted(
        set(addresses),
        key=lambda value: (":" in value, value),
    )


def _resolved_https_request(
    url: str,
    *,
    method: str,
    body: bytes | None,
    headers: dict[str, str],
) -> tuple[int, dict[str, str], bytes]:
    parsed = urlsplit(url)

    if parsed.scheme != "https" or not parsed.hostname:
        raise ClientError(
            f"DoH fallback supports HTTPS URLs only: {url}"
        )

    route = parsed.path or "/"
    if parsed.query:
        route += "?" + parsed.query

    request_body = body or b""
    request_headers = {
        "Host": parsed.netloc,
        "User-Agent": "void-agent-client-python/1.0",
        "Accept": "application/json",
        "Connection": "close",
        **headers,
    }
    request_headers["Content-Length"] = str(len(request_body))

    errors: list[str] = []

    for address in _doh_addresses(parsed.hostname):
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

            lines = [f"{method} {route} HTTP/1.1"]
            lines.extend(
                f"{key}: {value}"
                for key, value in request_headers.items()
            )
            lines.extend(["", ""])

            secure.sendall(
                "\r\n".join(lines).encode("ascii")
                + request_body
            )

            response = http.client.HTTPResponse(secure)
            response.begin()
            payload = response.read(MAX_BODY_BYTES + 1)
            response_headers = {
                key.lower(): value
                for key, value in response.getheaders()
            }

            if len(payload) > MAX_BODY_BYTES:
                raise ClientError(
                    f"response exceeds body limit: {url}"
                )

            return (
                response.status,
                response_headers,
                payload,
            )
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
        f"{method} {url} failed through all DoH addresses: "
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
        "User-Agent": "void-agent-client-python/1.0",
        "Accept": "application/json",
    }
    request_headers.update(headers or {})

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
        status, response_headers, payload = (
            _resolved_https_request(
                url,
                method=method,
                body=body,
                headers=request_headers,
            )
        )
    except Exception as exc:
        raise ClientError(
            f"{method} {url} failed: {type(exc).__name__}: {exc}"
        ) from exc

    if len(payload) > MAX_BODY_BYTES:
        raise ClientError(f"response exceeds body limit: {url}")

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
        raise ClientError(f"JSON root from {url} is not an object")

    return value


def post_json(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str],
    accepted_statuses: tuple[int, ...] = (200,),
) -> tuple[int, dict[str, str], dict[str, Any] | None]:
    raw = json.dumps(
        payload,
        separators=(",", ":"),
    ).encode("utf-8")

    status, response_headers, body = request_bytes(
        url,
        method="POST",
        body=raw,
        headers={
            "Content-Type": "application/json",
            **headers,
        },
    )

    if status not in accepted_statuses:
        preview = body.decode("utf-8", errors="replace")[:500]
        raise ClientError(
            f"POST {url} returned HTTP {status}: {preview}"
        )

    if not body:
        return status, response_headers, None

    try:
        value = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise ClientError(f"invalid JSON from {url}: {exc}") from exc

    if not isinstance(value, dict):
        raise ClientError(f"JSON-RPC response from {url} is not an object")

    return status, response_headers, value


def resolve_endpoints(
    *,
    discovery_url: str,
    mcp_metadata_url: str,
    a2a_catalogue_url: str,
) -> dict[str, Any]:
    discovery = get_json(discovery_url)
    mcp = get_json(mcp_metadata_url)
    a2a = get_json(a2a_catalogue_url)

    mcp_endpoint = mcp.get("endpoint")
    a2a_endpoint = a2a.get("endpoint")
    a2a_card = a2a.get("agentCard")

    if not isinstance(mcp_endpoint, str) or not mcp_endpoint.startswith(
        "https://"
    ):
        raise ClientError("MCP metadata does not contain an HTTPS endpoint")

    if not isinstance(a2a_endpoint, str) or not a2a_endpoint.startswith(
        "https://"
    ):
        raise ClientError("A2A catalogue does not contain an HTTPS endpoint")

    if not isinstance(a2a_card, str) or not a2a_card.startswith("https://"):
        raise ClientError("A2A catalogue does not contain an HTTPS Agent Card")

    return {
        "discoveryUrl": discovery_url,
        "mcpMetadataUrl": mcp_metadata_url,
        "a2aCatalogueUrl": a2a_catalogue_url,
        "mcpEndpoint": mcp_endpoint,
        "a2aEndpoint": a2a_endpoint,
        "a2aAgentCard": a2a_card,
        "discovery": discovery,
        "mcpMetadata": mcp,
        "a2aCatalogue": a2a,
    }


def mcp_request(
    endpoint: str,
    *,
    request_id: int,
    method: str,
    params: dict[str, Any] | None = None,
    initialize: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
    }
    if params is not None:
        payload["params"] = params

    headers = {
        "Accept": "application/json, text/event-stream",
        "Mcp-Method": method,
    }

    if not initialize:
        headers["MCP-Protocol-Version"] = MCP_PROTOCOL_VERSION

    if isinstance(params, dict):
        name = params.get("name") or params.get("uri")
        if isinstance(name, str):
            headers["Mcp-Name"] = name

    _, _, response = post_json(
        endpoint,
        payload,
        headers=headers,
    )

    if response is None:
        raise ClientError(f"MCP {method} returned an empty response")

    if "error" in response:
        raise ClientError(
            f"MCP {method} error: "
            + json.dumps(response["error"], sort_keys=True)
        )

    return response


def mcp_initialize(endpoint: str) -> dict[str, Any]:
    response = mcp_request(
        endpoint,
        request_id=1,
        method="initialize",
        params={
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {
                "name": "void-agent-client-python",
                "version": "1.0.0",
            },
        },
        initialize=True,
    )

    protocol = response.get("result", {}).get("protocolVersion")
    if protocol != MCP_PROTOCOL_VERSION:
        raise ClientError(
            f"MCP protocol differs: {protocol!r}"
        )

    # Stateless notification; 202 with no body is expected.
    post_json(
        endpoint,
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        },
        headers={
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
            "Mcp-Method": "notifications/initialized",
        },
        accepted_statuses=(202,),
    )

    return response


def mcp_list_tools(endpoint: str) -> list[dict[str, Any]]:
    mcp_initialize(endpoint)
    response = mcp_request(
        endpoint,
        request_id=2,
        method="tools/list",
        params={},
    )
    tools = response.get("result", {}).get("tools")
    if not isinstance(tools, list):
        raise ClientError("MCP tools/list did not return a tools array")
    return tools


def mcp_list_resources(endpoint: str) -> list[dict[str, Any]]:
    mcp_initialize(endpoint)
    response = mcp_request(
        endpoint,
        request_id=3,
        method="resources/list",
        params={},
    )
    resources = response.get("result", {}).get("resources")
    if not isinstance(resources, list):
        raise ClientError(
            "MCP resources/list did not return a resources array"
        )
    return resources


def mcp_call(endpoint: str, tool: str) -> dict[str, Any]:
    mcp_initialize(endpoint)
    response = mcp_request(
        endpoint,
        request_id=4,
        method="tools/call",
        params={
            "name": tool,
            "arguments": {},
        },
    )
    result = response.get("result")
    if not isinstance(result, dict):
        raise ClientError("MCP tools/call did not return an object")
    return result


def a2a_agent_card(card_url: str) -> dict[str, Any]:
    card = get_json(card_url)
    interfaces = card.get("supportedInterfaces")
    if not isinstance(interfaces, list) or not interfaces:
        raise ClientError("A2A Agent Card has no supported interface")
    return card


def a2a_request(
    endpoint: str,
    *,
    request_id: int,
    method: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    _, _, response = post_json(
        endpoint,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        },
        headers={
            "Accept": "application/json",
            "A2A-Version": A2A_PROTOCOL_VERSION,
        },
    )

    if response is None:
        raise ClientError(f"A2A {method} returned an empty response")

    if "error" in response:
        raise ClientError(
            f"A2A {method} error: "
            + json.dumps(response["error"], sort_keys=True)
        )

    return response


def a2a_ask(endpoint: str, query: str) -> dict[str, Any]:
    response = a2a_request(
        endpoint,
        request_id=10,
        method="SendMessage",
        params={
            "message": {
                "messageId": str(uuid.uuid4()),
                "contextId": "void-agent-client",
                "role": "ROLE_USER",
                "parts": [{
                    "text": query,
                    "mediaType": "text/plain",
                }],
            },
            "configuration": {
                "acceptedOutputModes": [
                    "text/plain",
                    "application/json",
                ]
            },
        },
    )

    message = response.get("result", {}).get("message")
    if not isinstance(message, dict):
        raise ClientError("A2A SendMessage did not return a direct message")
    return message


def a2a_list_tasks(endpoint: str) -> dict[str, Any]:
    response = a2a_request(
        endpoint,
        request_id=11,
        method="ListTasks",
        params={},
    )
    result = response.get("result")
    if not isinstance(result, dict):
        raise ClientError("A2A ListTasks did not return an object")
    return result


def run_smoke(endpoints: dict[str, Any]) -> dict[str, Any]:
    mcp_endpoint = endpoints["mcpEndpoint"]
    a2a_endpoint = endpoints["a2aEndpoint"]
    a2a_card_url = endpoints["a2aAgentCard"]

    tools = mcp_list_tools(mcp_endpoint)
    resources = mcp_list_resources(mcp_endpoint)
    chain_head = mcp_call(mcp_endpoint, "void_get_chain_head")
    card = a2a_agent_card(a2a_card_url)
    message = a2a_ask(
        a2a_endpoint,
        "What is the current VOID chain head?",
    )
    tasks = a2a_list_tasks(a2a_endpoint)

    tool_names = [item.get("name") for item in tools]
    resource_uris = [item.get("uri") for item in resources]

    if "void_get_chain_head" not in tool_names:
        raise ClientError("required MCP chain-head tool is absent")

    if "void://chain/head" not in resource_uris:
        raise ClientError("required MCP chain-head resource is absent")

    if chain_head.get("isError") is not False:
        raise ClientError("MCP chain-head tool returned an error")

    if card.get("name") != "VOID Network Read-Only Agent":
        raise ClientError("A2A Agent Card name differs")

    if message.get("role") != "ROLE_AGENT":
        raise ClientError("A2A direct response role differs")

    if tasks != {"tasks": [], "nextPageToken": ""}:
        raise ClientError("A2A task-list boundary differs")

    return {
        "status": "exact_green",
        "mcpEndpoint": mcp_endpoint,
        "a2aEndpoint": a2a_endpoint,
        "a2aAgentCard": a2a_card_url,
        "mcpTools": tool_names,
        "mcpResources": resource_uris,
        "mcpChainHeadRead": True,
        "a2aDirectMessage": True,
        "a2aTaskListEmpty": True,
        "mutationPerformed": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Discover and read VOID through public MCP and A2A endpoints."
        )
    )
    parser.add_argument(
        "--discovery-url",
        default=DEFAULT_DISCOVERY,
    )
    parser.add_argument(
        "--mcp-metadata-url",
        default=DEFAULT_MCP_METADATA,
    )
    parser.add_argument(
        "--a2a-catalogue-url",
        default=DEFAULT_A2A_CATALOGUE,
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )
    subparsers.add_parser("discover")
    subparsers.add_parser("mcp-tools")
    subparsers.add_parser("mcp-resources")

    call_parser = subparsers.add_parser("mcp-call")
    call_parser.add_argument("tool")

    subparsers.add_parser("a2a-card")
    ask_parser = subparsers.add_parser("a2a-ask")
    ask_parser.add_argument("query", nargs="+")
    subparsers.add_parser("a2a-tasks")
    subparsers.add_parser("smoke")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    endpoints = resolve_endpoints(
        discovery_url=args.discovery_url,
        mcp_metadata_url=args.mcp_metadata_url,
        a2a_catalogue_url=args.a2a_catalogue_url,
    )

    if args.command == "discover":
        output = {
            key: endpoints[key]
            for key in (
                "discoveryUrl",
                "mcpMetadataUrl",
                "a2aCatalogueUrl",
                "mcpEndpoint",
                "a2aEndpoint",
                "a2aAgentCard",
            )
        }
    elif args.command == "mcp-tools":
        output = mcp_list_tools(endpoints["mcpEndpoint"])
    elif args.command == "mcp-resources":
        output = mcp_list_resources(endpoints["mcpEndpoint"])
    elif args.command == "mcp-call":
        output = mcp_call(endpoints["mcpEndpoint"], args.tool)
    elif args.command == "a2a-card":
        output = a2a_agent_card(endpoints["a2aAgentCard"])
    elif args.command == "a2a-ask":
        output = a2a_ask(
            endpoints["a2aEndpoint"],
            " ".join(args.query),
        )
    elif args.command == "a2a-tasks":
        output = a2a_list_tasks(endpoints["a2aEndpoint"])
    elif args.command == "smoke":
        output = run_smoke(endpoints)
    else:
        raise ClientError(f"unsupported command: {args.command}")

    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ClientError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
