# VOID GitHub Pages mirror working agreement

Marker: `VOID_PAGES_MIRROR_WORKING_AGREEMENT_V2`

Reviewed: **September 25, 2026**

This repository is a static, replaceable discovery mirror for VOID Network. It is
not the source of truth for protocol, runtime, economic, validator, wallet, or
release state.

## Source of truth

- Canonical source: `6ZoSo9/void-node`.
- Refresh live `void-node/main` before changing current-state claims.
- Files listed in `mirror/source-bindings-v2.json` are copied byte-for-byte from
  the recorded `void-node` blobs. Do not hand-edit those mirrored files here.
- Pages-specific metadata may summarize current state, but it must not widen the
  authority or capability described by canonical source.

## Freshness

Runtime endpoints are current only when independently reverified and explicitly
published with a bounded verification time. An old `live_at_verification`
record is historical evidence, not present-tense availability.

Ephemeral Quick Tunnel URLs from July 2026 must never be promoted back to current
discovery merely because the old files still exist.

## Authority

This repository is static read-only distribution. A source or Pages change does
not authorize deployment of a VOID node, wallet/signer access, transaction
construction/signing/broadcast, Work Credit mutation, Buy VOID fulfillment,
validator activation, treasury/liquidity action, market activation, or funds
movement.

## Economic truth

- Work Credits are unlimited useful-work accounting units.
- There is no fixed WC-to-VOID conversion or redemption ratio.
- Public presale intake and production WC/VOID activation are coupled; neither
  may open alone.
- The current WC/VOID production candidate is `HOLD`.
- Historical fixed-award pilot artifacts may remain for provenance, but must be
  labeled historical and must not be presented as the current general WC policy.

## Git discipline

Use a bounded branch and draft PR. Keep current-state refreshes, historical
artifacts, and runtime activation separate. Do not force-push shared history.
Before merge, run the static mirror rehabilitation proof and ordinary diff
hygiene.

`PROTECT THE CORE`. `PROTECT THE TRUTH`.
