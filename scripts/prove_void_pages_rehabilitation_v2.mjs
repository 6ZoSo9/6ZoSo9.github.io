#!/usr/bin/env node
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (p) => fs.readFileSync(path.join(ROOT, p));
const text = (p) => read(p).toString("utf8");
const json = (p) => JSON.parse(text(p));

function gitBlobSha(relative) {
  const body = read(relative);
  const header = Buffer.from(`blob ${body.length}\0`, "utf8");
  return crypto.createHash("sha1").update(header).update(body).digest("hex");
}

const state = json("current-state-v2.json");
const bindings = json("mirror/source-bindings-v2.json");

assert.equal(state.marker, "VOID_PAGES_CURRENT_STATE_V2");
assert.equal(state.source.repository, "6ZoSo9/void-node");
assert.equal(state.source.commit, "d4a8f43462be30699678a2da710c427e38768655");
assert.equal(state.mirror.role, "static_replaceable_discovery_mirror");
assert.equal(state.mirror.dynamic_api, false);
assert.equal(state.runtime_pointers.current_remote_mcp_endpoint, null);
assert.equal(state.runtime_pointers.current_remote_a2a_endpoint, null);
assert.equal(state.runtime_pointers.current_paid_work_submission_endpoint, null);
assert.equal(state.economics.wc_unlimited_accounting_units, true);
assert.equal(state.economics.fixed_wc_void_conversion, false);
assert.equal(state.economics.wc_void_protocol_void_inventory, "10000000");
assert.equal(state.economics.wc_void_protocol_wc_seed, "0");
assert.equal(state.economics.presale_wc_void_coupled_launch, true);
assert.equal(state.capabilities.production_wc_void_market, "guarded_hold");
assert.equal(state.capabilities.public_presale_intake, "guarded_hold");
assert.equal(state.capabilities.stable_node_release, "not_published");

assert.equal(bindings.marker, "VOID_PAGES_SOURCE_BINDINGS_V2");
assert.equal(bindings.source_commit, state.source.commit);
assert.ok(Array.isArray(bindings.bindings) && bindings.bindings.length >= 20);
for (const binding of bindings.bindings) {
  assert.match(binding.source_blob_sha, /^[0-9a-f]{40}$/);
  assert.equal(fs.existsSync(path.join(ROOT, binding.target_path)), true, `missing mirror target ${binding.target_path}`);
  assert.equal(gitBlobSha(binding.target_path), binding.source_blob_sha, `source blob drift: ${binding.target_path}`);
}

for (const relative of [
  "README.md",
  "index.html",
  "llms.txt",
  "llms-full.txt",
  "current-state-v2.json",
  "discovery/index-v1.json",
  ".well-known/void-agent-intake-capability-v1.json",
]) {
  assert.doesNotMatch(text(relative), /trycloudflare\.com/i, `current surface contains stale tunnel: ${relative}`);
}

const mcp = json("mcp/remote-server-v1.json");
assert.equal(mcp.current, false);
assert.equal(mcp.endpoint, null);
assert.equal(mcp.status, "historical_unverified");

const a2a = json("a2a/agent-v1.json");
assert.equal(a2a.current, false);
assert.equal(a2a.endpoint, null);
assert.equal(a2a.status, "historical_unverified");

const gateway = json("live/gateway-pointer-v1.json");
assert.equal(gateway.current, false);
assert.equal(gateway.public_base, null);

const work = json("work/live-v1.json");
assert.equal(work.current, false);
assert.equal(work.public_base, null);
assert.equal(work.live_submission_available, false);
assert.equal(work.canonical_wc_ledger_credit_automatic, false);
assert.equal(work.void_settlement_automatic, false);

const paidWork = json("public-node/agents/paid-work-v1.json");
assert.equal(paidWork.marker, "VOID_AGENT_PAID_WORK_RUNTIME_DISCOVERY_V1");
assert.equal(paidWork.runtime_capabilities.live_work_order_submission, "unavailable");
assert.equal(paidWork.runtime_capabilities.live_wc_ledger_write, "unavailable");
assert.equal(paidWork.runtime_capabilities.wc_to_void_settlement, "unavailable");
assert.equal(paidWork.runtime_capabilities.buy_void_auto_fulfillment, "unavailable");

assert.match(text("AGENTS.md"), /static, replaceable discovery mirror/);
assert.match(text("AGENTS.md"), /No fixed WC-to-VOID conversion or redemption ratio exists/);
assert.match(text("README.md"), /Historical July services/);

for (const workflowPath of [
  ".github/workflows/void-free-discovery-pages-integration-v1.yml",
  ".github/workflows/void-public-agent-canary-v1.yml",
]) {
  const workflow = text(workflowPath);
  assert.match(workflow, /^permissions:\n  contents: read$/mu);
  assert.doesNotMatch(workflow, /contents:\s*write/);
}

console.log("VOID_PAGES_REHABILITATION_V2_PROOF_GREEN");
console.log(`source_commit=${state.source.commit}`);
console.log(`source_bindings=${bindings.bindings.length}`);
console.log("static_mirror=true");
console.log("stale_quick_tunnels_current=false");
console.log("fixed_wc_void_conversion=false");
console.log("presale_wc_void_coupled_hold=true");
console.log("network_calls=false");
console.log("mutation=false");
