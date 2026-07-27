# VOID Agent Client Kit V1

Connect to VOID without installing a node.

The clients resolve the current MCP and A2A endpoints from stable GitHub Pages
metadata each time they run. Ephemeral Quick Tunnel rotations therefore do not
require redistributing the clients.

Each client uses normal DNS first. If a newly issued Quick Tunnel hostname has
not reached the local resolver yet, it falls back to Cloudflare
DNS-over-HTTPS while preserving the original TLS hostname and certificate
verification.

## Python 3 standard-library client

```bash
python3 void-agent-client.py discover
python3 void-agent-client.py mcp-tools
python3 void-agent-client.py mcp-call void_get_chain_head
python3 void-agent-client.py a2a-ask "Is VOID ready?"
python3 void-agent-client.py smoke
```

## Node.js 18+ zero-package client

```bash
node void-agent-client.mjs discover
node void-agent-client.mjs mcp-tools
node void-agent-client.mjs mcp-call void_get_chain_head
node void-agent-client.mjs a2a-ask "Show VOID network health"
node void-agent-client.mjs smoke
```

## Paste-safe shell client

Requires `curl` and Python 3 for JSON field extraction.

```bash
bash void-agent-client.sh discover
bash void-agent-client.sh mcp-ping
bash void-agent-client.sh a2a-card
bash void-agent-client.sh a2a-ask "What is the current chain head?"
bash void-agent-client.sh smoke
```

## Stable discovery

- Discovery: `https://6zoso9.github.io/discovery/index-v1.json`
- MCP metadata: `https://6zoso9.github.io/mcp/remote-server-v1.json`
- A2A catalogue: `https://6zoso9.github.io/a2a/agent-v1.json`

## Immutable jsDelivr distribution

- Python: `https://cdn.jsdelivr.net/gh/6ZoSo9/6ZoSo9.github.io@void-agent-client-kit-v1/clients/void-agent-client.py`
- Node ESM: `https://cdn.jsdelivr.net/gh/6ZoSo9/6ZoSo9.github.io@void-agent-client-kit-v1/clients/void-agent-client.mjs`
- Shell: `https://cdn.jsdelivr.net/gh/6ZoSo9/6ZoSo9.github.io@void-agent-client-kit-v1/clients/void-agent-client.sh`
- Manifest: `https://cdn.jsdelivr.net/gh/6ZoSo9/6ZoSo9.github.io@void-agent-client-kit-v1/clients/manifest-v1.json`
- Integrity: `https://cdn.jsdelivr.net/gh/6ZoSo9/6ZoSo9.github.io@void-agent-client-kit-v1/clients/integrity-v1.json`

## Boundary

These clients are read-only. They expose no wallet, ledger, transaction,
payment, validator mutation, operator mutation, secret, or arbitrary proxy
operation. The smoke command performs discovery and read canaries only.
