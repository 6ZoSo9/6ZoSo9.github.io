# VOID AI Agent First Contact — Free Discovery Mesh V1

Public site: https://6zoso9.github.io

## Primary routes

- Machine-readable: `https://6zoso9.github.io/public-node/agents/first-contact-v1.json`
- Human-readable: `https://6zoso9.github.io/public-node/agents/join-v1.html`
- Well-known discovery: `https://6zoso9.github.io/.well-known/void-public-node.json`
- OpenAPI: `https://6zoso9.github.io/openapi.json`
- Discovery index: `https://6zoso9.github.io/discovery/index-v1.json`
- Integrity: `https://6zoso9.github.io/integrity/void-first-contact-v1.json`
- Standards readiness: `https://6zoso9.github.io/standards/readiness-v1.json`
- llms.txt: `https://6zoso9.github.io/llms.txt`
- Atom feed: `https://6zoso9.github.io/feed.xml`
- Sitemap: `https://6zoso9.github.io/sitemap.xml`

## Free distribution mesh

The canonical First Contact assets are available through:

- GitHub Pages
- public GitHub repository
- commit-pinned raw GitHub URLs
- commit-pinned jsDelivr URLs
- versioned GitHub Release assets

These are replaceable distribution mirrors, not core VOID dependencies.

## Standards posture

Live now:

- OpenAPI 3.1.1
- machine-readable discovery
- llms.txt convention
- sitemap
- Atom feed
- integrity manifest

Withheld until conformant:

- A2A Agent Card: requires a functioning A2A service endpoint
- Official MCP Registry: requires an actual remote MCP server
- RFC 9116 security.txt: requires a verified private disclosure contact and expiration

## Boundary

Static discovery only. This repository does not host:

- a live VOID node;
- wallets or secrets;
- ledger writes;
- transaction submission;
- payment or Buy VOID fulfillment;
- validator or operator mutation.

Canonical source merge: `20cf2bc1711ab4ea63e8bc5d6c60815ed8f8b37a`

Canonical mirror commit: `04ae182e65445484239411e9ad4062228c5cb58e`
## Remote MCP server

- Endpoint: `https://hereby-metals-plumbing-preserve.trycloudflare.com/mcp`
- Metadata: `https://6zoso9.github.io/mcp/remote-server-v1.json`
- Client config: `https://6zoso9.github.io/mcp/client-config-v1.json`
- Transport: Streamable HTTP with plain JSON responses
- Boundary: stateless and read-only
- Official Registry: withheld until the endpoint is stable
