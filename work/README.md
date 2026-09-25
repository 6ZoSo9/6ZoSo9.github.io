# VOID Agent Work — current discovery

Reviewed: **September 25, 2026**

The July 2026 Quick Tunnel paid-work intake and its fixed 3-WC pilot are
historical artifacts. The tunnel was ephemeral and is not advertised as a
current service.

Current protocol discovery is mirrored from `void-node` at:

`/public-node/agents/paid-work-v1.json`

That document exposes the paid-work protocol and integrity material read-only.
It explicitly reports live work-order submission, quote exchange, payment
execution, work dispatch, WC award authorization, WC ledger writes, WC/VOID
settlement, and automatic Buy VOID fulfillment as unavailable on that protocol
surface.

Current public WC earning elsewhere in VOID remains a bounded
coordinator-issued capability-ticket / verified-receipt pilot. WC are unlimited
accounting units and there is no fixed WC-to-VOID redemption ratio.

Historical V1 files and releases remain for provenance. Do not use an old tunnel
URL or historical signed quote as current service authority.
