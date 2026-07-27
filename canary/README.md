# VOID Public Agent Canary V1

[![VOID Public Agent Canary V1](https://github.com/6ZoSo9/6ZoSo9.github.io/actions/workflows/void-public-agent-canary-v1.yml/badge.svg?branch=main)](https://github.com/6ZoSo9/6ZoSo9.github.io/actions/workflows/void-public-agent-canary-v1.yml)

Independent, secretless verification of VOID's public MCP and A2A surfaces
from a fresh GitHub-hosted Ubuntu 24.04 runner.

## Proof boundary

- Python, Node, and shell client smoke canaries.
- Stable discovery resolves the current public MCP and A2A endpoints.
- All three clients must resolve the same HTTPS endpoints.
- Workflow permission is exactly `contents: read`.
- No repository write, secret, credential, wallet, ledger, transaction,
  payment, validator, or operator mutation.

## Triggers

- Relevant pushes to `main`.
- Manual workflow dispatch.
- Every six hours at minute 37 UTC.

Scheduled workflows in public repositories may be disabled after 60 days
without repository activity. Push and manual triggers remain available.

## External reproduction

```bash
git clone https://github.com/6ZoSo9/6ZoSo9.github.io.git
cd 6ZoSo9.github.io
python3 canary/public-canary-v1.py \
  --output void-public-agent-canary-evidence-v1.json
sha256sum void-public-agent-canary-evidence-v1.json
```

Use the repository's `VOID Agent Integration Report` issue form to publish
redacted external results. Never include secrets or private infrastructure.
