#!/usr/bin/env python3
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone

ORIGIN = "https://6zoso9.github.io"
EXPECTED_SOURCE = "d4a8f43462be30699678a2da710c427e38768655"

def fetch(path):
    req = urllib.request.Request(
        ORIGIN + path,
        headers={"Accept": "application/json", "User-Agent": "void-pages-canary-v2"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        body = response.read(256 * 1024)
        if response.status != 200:
            raise RuntimeError(f"{path}: HTTP {response.status}")
        return body

observed = {}
for path in [
    "/current-state-v2.json",
    "/mirror/source-bindings-v2.json",
    "/public-node/agents/first-contact-v1.json",
    "/public-node/agents/capabilities-v1.json",
    "/discovery/index-v1.json",
]:
    body = fetch(path)
    observed[path] = {
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    if b"trycloudflare.com" in body and path in {
        "/current-state-v2.json",
        "/discovery/index-v1.json",
    }:
        raise RuntimeError(f"{path}: stale tunnel leaked into current discovery")

state = json.loads(fetch("/current-state-v2.json"))
first = json.loads(fetch("/public-node/agents/first-contact-v1.json"))
caps = json.loads(fetch("/public-node/agents/capabilities-v1.json"))

if state["source"]["commit"] != EXPECTED_SOURCE:
    raise RuntimeError("source commit drift")
if state["runtime_pointers"]["current_remote_mcp_endpoint"] is not None:
    raise RuntimeError("unexpected current MCP endpoint")
if state["runtime_pointers"]["current_remote_a2a_endpoint"] is not None:
    raise RuntimeError("unexpected current A2A endpoint")
if first["marker"] != "VOID_AI_AGENT_FIRST_CONTACT_V1":
    raise RuntimeError("first-contact marker mismatch")
if caps["marker"] != "VOID_AI_AGENT_CAPABILITY_NEGOTIATION_V1":
    raise RuntimeError("capabilities marker mismatch")

result = {
    "marker": "VOID_PUBLIC_PAGES_CANARY_V2",
    "observed_at_utc": datetime.now(timezone.utc).isoformat(),
    "origin": ORIGIN,
    "source_commit": EXPECTED_SOURCE,
    "status": "green",
    "mutation": False,
    "observed": observed,
}
out = json.dumps(result, indent=2, sort_keys=True)
if len(sys.argv) > 1:
    with open(sys.argv[1], "w", encoding="utf-8") as handle:
        handle.write(out + "\n")
print(out)
