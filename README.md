# VOID Network static discovery mirror

Public site: https://6zoso9.github.io

Reviewed: **September 25, 2026**

This repository is a static, replaceable discovery mirror for VOID Network. The
canonical protocol and current-state source of truth is
[6ZoSo9/void-node](https://github.com/6ZoSo9/void-node).

## Current routes

- Current mirror state: `/current-state-v2.json`
- Machine First Contact: `/public-node/agents/first-contact-v1.json`
- Agent discovery: `/.well-known/void-agent-discovery.json`
- Public-node discovery: `/.well-known/void-public-node.json`
- Capability contract: `/public-node/agents/capabilities-v1.json`
- Authentication contract: `/public-node/agents/authentication-v1.json`
- Public utility catalog: `/public-node/agents/public-utility-v1.json`
- Paid-work protocol discovery: `/public-node/agents/paid-work-v1.json`
- Source bindings: `/mirror/source-bindings-v2.json`
- LLM index: `/llms.txt`

The core agent contracts above are mirrored byte-for-byte from
`void-node/main` at the source commit recorded in `current-state-v2.json`.

## Current boundary

VOID Mainnet-0 is live, but this Pages repository is static. It grants no wallet,
signer, transaction, Work Credit write, Buy VOID fulfillment, validator,
treasury, market-activation, or funds authority.

Public Work Credit earning exists as a bounded coordinator-ticket/verified-receipt
pilot. There is no fixed WC-to-VOID redemption ratio. Public presale intake and
production WC/VOID activation are coupled and currently remain `HOLD`.

There is no official stable VOID node release as of this review.

## Historical July services

The July 2026 MCP, A2A, live gateway, and paid-work Quick Tunnel records remain in
this repository for provenance. Their tunnel URLs were ephemeral and are **not
current live endpoints** unless a later bounded verification explicitly republishes
them.

Historical GitHub Releases remain immutable project history; they are not current
runtime availability claims.

## Maintenance

See `AGENTS.md`. Current mirror contracts are source-bound through
`mirror/source-bindings-v2.json` and verified by the rehabilitation proof.
