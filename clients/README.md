# VOID Agent Client Kit V1 — historical distribution

The V1 Python, Node, and shell clients remain available as historical July 2026
release artifacts.

They were designed to resolve MCP and A2A endpoints from Pages metadata. The
September 25 rehabilitation intentionally publishes **no current MCP or A2A
endpoint**, because the old Cloudflare Quick Tunnels were ephemeral and have not
been reverified.

Do not treat a successful download of these clients as evidence that a remote MCP
or A2A service is currently available.

For current discovery use:

- `/current-state-v2.json`
- `/.well-known/void-public-node.json`
- `/public-node/agents/first-contact-v1.json`
- `/public-node/agents/capabilities-v1.json`

The immutable V1 release and commit-pinned distributions remain valid historical
artifacts.
