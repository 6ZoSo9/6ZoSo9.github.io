#!/usr/bin/env bash
set -euo pipefail

DISCOVERY="https://6zoso9.github.io/discovery/index-v1.json"
MCP_METADATA="https://6zoso9.github.io/mcp/remote-server-v1.json"
A2A_CATALOGUE="https://6zoso9.github.io/a2a/agent-v1.json"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1" >&2
    exit 1
  }
}

need curl
need python3

curl_resilient() {
  local error_file
  error_file="$(mktemp)"

  if curl "$@" 2>"$error_file"
  then
    rm -f -- "$error_file"
    return 0
  fi

  if curl --help all 2>/dev/null |
    grep -q -- '--doh-url'
  then
    if curl \
      --doh-url 'https://cloudflare-dns.com/dns-query' \
      "$@"
    then
      rm -f -- "$error_file"
      return 0
    fi
  fi

  cat -- "$error_file" >&2
  rm -f -- "$error_file"
  return 1
}

json_field() {
  python3 -c '
import json, sys
value = json.load(sys.stdin)
for part in sys.argv[1].split("."):
    value = value[part]
if not isinstance(value, str):
    raise SystemExit("requested field is not a string")
print(value)
' "$1"
}

fetch_json() {
  curl_resilient \
    --fail \
    --silent \
    --show-error \
    --location \
    --max-time 20 \
    --header 'Accept: application/json' \
    "$1"
}

MCP_ENDPOINT="$(fetch_json "$MCP_METADATA" | json_field endpoint)"
A2A_ENDPOINT="$(fetch_json "$A2A_CATALOGUE" | json_field endpoint)"
A2A_CARD="$(fetch_json "$A2A_CATALOGUE" | json_field agentCard)"

command_name="${1:-}"

case "$command_name" in
  discover)
    python3 - "$DISCOVERY" "$MCP_METADATA" "$A2A_CATALOGUE" \
      "$MCP_ENDPOINT" "$A2A_ENDPOINT" "$A2A_CARD" <<'PY'
import json, sys
print(json.dumps({
    "discoveryUrl": sys.argv[1],
    "mcpMetadataUrl": sys.argv[2],
    "a2aCatalogueUrl": sys.argv[3],
    "mcpEndpoint": sys.argv[4],
    "a2aEndpoint": sys.argv[5],
    "a2aAgentCard": sys.argv[6],
}, indent=2, sort_keys=True))
PY
    ;;

  a2a-card)
    fetch_json "$A2A_CARD"
    printf '\n'
    ;;

  a2a-ask)
    shift
    query="$*"
    test -n "$query" || {
      echo "ERROR: a2a-ask requires a query" >&2
      exit 2
    }

    body="$(
      python3 - "$query" <<'PY'
import json, sys, uuid
print(json.dumps({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "SendMessage",
    "params": {
        "message": {
            "messageId": str(uuid.uuid4()),
            "contextId": "void-shell-client",
            "role": "ROLE_USER",
            "parts": [{
                "text": sys.argv[1],
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
}, separators=(",", ":")))
PY
    )"

    curl_resilient \
      --fail \
      --silent \
      --show-error \
      --location \
      --max-time 20 \
      --header 'Content-Type: application/json' \
      --header 'Accept: application/json' \
      --header 'A2A-Version: 1.0' \
      --data-binary "$body" \
      "$A2A_ENDPOINT"
    printf '\n'
    ;;

  mcp-ping)
    body='{"jsonrpc":"2.0","id":1,"method":"ping"}'

    curl_resilient \
      --fail \
      --silent \
      --show-error \
      --location \
      --max-time 20 \
      --header 'Content-Type: application/json' \
      --header 'Accept: application/json, text/event-stream' \
      --header 'MCP-Protocol-Version: 2025-11-25' \
      --header 'Mcp-Method: ping' \
      --data-binary "$body" \
      "$MCP_ENDPOINT"
    printf '\n'
    ;;

  smoke)
    "$0" discover >/dev/null
    "$0" mcp-ping >/dev/null
    "$0" a2a-card >/dev/null
    "$0" a2a-ask "What is the current VOID chain head?" >/dev/null
    echo '{"status":"exact_green","mutationPerformed":false}'
    ;;

  *)
    cat >&2 <<'USAGE'
Usage:
  bash void-agent-client.sh discover
  bash void-agent-client.sh mcp-ping
  bash void-agent-client.sh a2a-card
  bash void-agent-client.sh a2a-ask <query>
  bash void-agent-client.sh smoke
USAGE
    exit 2
    ;;
esac
