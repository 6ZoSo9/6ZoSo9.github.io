#!/usr/bin/env node

import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const ORIGIN = "https://6zoso9.github.io";
const INDEXNOW_KEY = "12ec1f1fd6f9a1fc5ce96324bcca44d5";
const INDEXNOW_FILE = `${INDEXNOW_KEY}.txt`;
const AUTHENTICITY_SHA256 =
  "597c451a349728c4713e1ac2ce9ca5478a80378bfc12cf0ca1ce4138e82ea692";

const REQUIRED_URLS = Object.freeze([
  `${ORIGIN}/`,
  `${ORIGIN}/public-node/`,
  `${ORIGIN}/public-node/agents/first-contact-v1.json`,
  `${ORIGIN}/public-node/agents/join-v1.html`,
  `${ORIGIN}/public-node/agents/discovery-v1.json`,
  `${ORIGIN}/public-node/agents/capabilities-v1.json`,
  `${ORIGIN}/public-node/agents/authentication-v1.json`,
  `${ORIGIN}/.well-known/void-public-node.json`,
  `${ORIGIN}/.well-known/void-agent-discovery.json`,
  `${ORIGIN}/.well-known/void-agent-authentication.json`,
  `${ORIGIN}/.well-known/void-agent-intake-capability-v1.json`,
  `${ORIGIN}/.well-known/void-network-authenticity.json`,
  `${ORIGIN}/discovery/`,
  `${ORIGIN}/discovery/index-v1.json`,
  `${ORIGIN}/discovery/void-datanet-dataset-v1.jsonld`,
]);

const PRESERVED_SITEMAP_URLS = Object.freeze([
  `${ORIGIN}/`,
  `${ORIGIN}/public-node/agents/join-v1.html`,
  `${ORIGIN}/public-node/agents/first-contact-v1.json`,
  `${ORIGIN}/.well-known/void-public-node.json`,
  `${ORIGIN}/openapi.json`,
  `${ORIGIN}/llms.txt`,
  `${ORIGIN}/llms-full.txt`,
  `${ORIGIN}/feed.xml`,
  `${ORIGIN}/discovery/index-v1.json`,
  `${ORIGIN}/integrity/void-first-contact-v1.json`,
  `${ORIGIN}/standards/readiness-v1.json`,
  `${ORIGIN}/clients/README.md`,
  `${ORIGIN}/clients/manifest-v1.json`,
  `${ORIGIN}/clients/void-agent-client.py`,
  `${ORIGIN}/clients/void-agent-client.mjs`,
  `${ORIGIN}/clients/void-agent-client.sh`,
  `${ORIGIN}/canary/README.md`,
  `${ORIGIN}/canary/spec-v1.json`,
  `${ORIGIN}/canary/public-canary-v1.py`,
  `${ORIGIN}/work/README.md`,
  `${ORIGIN}/work/live-v1.json`,
  `${ORIGIN}/work/catalog-v1.json`,
  `${ORIGIN}/work/review-policy-v1.json`,
  `${ORIGIN}/work/openapi.json`,
  `${ORIGIN}/work/submission-signing-v1.json`,
  `${ORIGIN}/work/worker-example-v1.json`,
  `${ORIGIN}/work/void-paid-work-client.py`,
  `${ORIGIN}/work/manifest-v1.json`,
]);

function read(relative) {
  return fs.readFileSync(path.join(ROOT, relative), "utf8");
}

function json(relative) {
  return JSON.parse(read(relative));
}

function sha256(relative) {
  return crypto.createHash("sha256").update(fs.readFileSync(path.join(ROOT, relative))).digest("hex");
}

function sameOriginPath(value) {
  assert.equal(typeof value, "string");
  assert.equal(value.startsWith("/"), true, `${value} must be origin-relative`);
  assert.equal(value.startsWith("//"), false, `${value} must not be protocol-relative`);
}

const discoveryWellKnown = json(".well-known/void-agent-discovery.json");
const authenticationWellKnown = json(".well-known/void-agent-authentication.json");
const intake = json(".well-known/void-agent-intake-capability-v1.json");
const authenticity = json(".well-known/void-network-authenticity.json");
const discovery = json("public-node/agents/discovery-v1.json");
const capabilities = json("public-node/agents/capabilities-v1.json");
const authentication = json("public-node/agents/authentication-v1.json");
const dataset = json("discovery/void-datanet-dataset-v1.jsonld");
const pagesManifest = json("pages-manifest-v1.json");

for (const document of [
  discoveryWellKnown,
  authenticationWellKnown,
  intake,
  authenticity,
  discovery,
  capabilities,
  authentication,
]) {
  assert.equal(document.network.name, "VOID Mainnet-0");
  assert.equal(document.network.chain_id, 2050);
}

assert.equal(discoveryWellKnown.marker, "VOID_AI_AGENT_WELL_KNOWN_ENTRYPOINT_V1");
assert.equal(discoveryWellKnown.protocol, "void-agent-discovery-well-known/1");
assert.equal(discoveryWellKnown.authority.default, "read_only");
assert.equal(discoveryWellKnown.authority.mutation_authority_granted, false);
assert.equal(discoveryWellKnown.authority.payment_authority_granted, false);
assert.equal(discoveryWellKnown.authority.work_credit_authority_granted, false);
assert.equal(discoveryWellKnown.distribution.core_dependency, false);
assert.equal(discoveryWellKnown.distribution.replaceable, true);
sameOriginPath(discoveryWellKnown.canonical_discovery);
sameOriginPath(discoveryWellKnown.first_contact);
sameOriginPath(discoveryWellKnown.network_authenticity);

assert.equal(authenticationWellKnown.marker, "VOID_AI_AGENT_AUTHENTICATION_WELL_KNOWN_V1");
assert.equal(authenticationWellKnown.authenticated_routes_active, false);
assert.equal(authenticationWellKnown.verifier_runtime_active, false);
assert.equal(authenticationWellKnown.mutation_authority_granted, false);
sameOriginPath(authenticationWellKnown.canonical_authentication_contract);

assert.equal(intake.marker, "VOID_AGENT_INTAKE_CAPABILITY_V1");
assert.equal(intake.status, "static_operator_review_intake_discovery");
assert.equal(intake.authority.live_http_submission_endpoint, false);
assert.equal(intake.authority.operator_review_required, true);
assert.equal(intake.authority.automatic_work_dispatch, false);
assert.equal(intake.authority.payment_execution, false);
assert.equal(intake.authority.canonical_wc_ledger_credit_automatic, false);
assert.equal(intake.authority.mutation_authority_granted, false);
for (const value of Object.values(intake.surfaces)) sameOriginPath(value);

assert.equal(authenticity.marker, "VOID_OFFICIAL_NETWORK_AUTHENTICITY_WELL_KNOWN_V1");
assert.equal(authenticity.verification.algorithm, "Ed25519");
assert.equal(authenticity.authority.verification_only, true);
assert.equal(authenticity.authority.mutation_authority_granted, false);
assert.equal(authenticity.safety.private_key_present, false);
assert.equal(sha256(".well-known/void-network-authenticity.json"), AUTHENTICITY_SHA256);

assert.equal(discovery.marker, "VOID_AI_AGENT_DISCOVERY_CONTRACT_WALL_V1");
assert.equal(discovery.distribution.mode, "static_public_mirror");
assert.equal(discovery.distribution.core_dependency, false);
assert.equal(discovery.authority.default, "read_only");
assert.deepEqual(discovery.authority.granted_http_methods, ["GET", "HEAD"]);
assert.equal(discovery.authority.mutation_authority_granted, false);
assert.equal(discovery.authority.payment_authority_granted, false);
assert.equal(discovery.authority.wallet_or_signer_access, false);
assert.equal(discovery.authority.work_credit_write_authority, false);
for (const value of Object.values(discovery.entrypoints)) sameOriginPath(value);

assert.equal(capabilities.marker, "VOID_AI_AGENT_CAPABILITY_NEGOTIATION_V1");
assert.equal(capabilities.authority.default, "not_granted");
assert.equal(capabilities.authority.authentication_active, false);
assert.equal(capabilities.authority.payment_submission_active, false);
assert.equal(capabilities.authority.work_credit_awards_active, false);
assert.equal(capabilities.authority.buy_void_automatic_fulfillment_active, false);
assert.equal(capabilities.authority.mutation_authority_granted, false);
assert.equal(capabilities.negotiation.default_result, "not_granted");
assert.equal(capabilities.negotiation.request_submission_enabled, false);
for (const capability of capabilities.capabilities) {
  assert.equal(capability.enabled, true);
  assert.equal(capability.access, "anonymous");
  assert.equal(capability.http_methods.every((method) => ["GET", "HEAD"].includes(method)), true);
  for (const value of capability.paths) sameOriginPath(value);
}

assert.equal(authentication.marker, "VOID_AI_AGENT_AUTHENTICATION_CONTRACT_V1");
assert.equal(authentication.status, "contract_discovery_only");
assert.equal(authentication.runtime.verifier_active, false);
assert.equal(authentication.runtime.authenticated_routes_active, false);
assert.equal(authentication.runtime.request_submission_active, false);
assert.equal(authentication.runtime.credential_collection_active, false);
assert.equal(authentication.authority.mutation_authority_granted, false);
assert.equal(authentication.authority.payment_authority_granted, false);
assert.equal(authentication.authority.work_credit_authority_granted, false);
assert.equal(authentication.authority.wallet_or_signer_access, false);

assert.equal(dataset["@context"], "https://schema.org");
assert.equal(dataset["@type"], "Dataset");
assert.equal(dataset.url, `${ORIGIN}/discovery/`);
assert.equal(dataset.sameAs, `${ORIGIN}/public-node/`);
assert.equal(dataset.isAccessibleForFree, true);
assert.equal(dataset.dateModified, "2026-07-31");
assert.equal(dataset.distribution.length, 3);
for (const item of dataset.distribution) {
  assert.equal(item["@type"], "DataDownload");
  assert.equal(new URL(item.contentUrl).origin, ORIGIN);
}

const landing = read("discovery/index.html");
const embeddedMatch = landing.match(/<script type="application\/ld\+json">\s*([\s\S]*?)\s*<\/script>/u);
assert.ok(embeddedMatch, "discovery landing omitted Dataset JSON-LD");
assert.deepEqual(JSON.parse(embeddedMatch[1]), dataset);
assert.match(landing, /grants no wallet, signer, payment, Work Credit, validator, operator, ledger, or runtime mutation authority/);
assert.doesNotMatch(landing, /<form\b/iu);
assert.doesNotMatch(landing, /\bfetch\s*\(/u);

const publicNode = read("public-node/index.html");
for (const relative of [
  "/.well-known/void-public-node.json",
  "/.well-known/void-agent-discovery.json",
  "/.well-known/void-network-authenticity.json",
  "/public-node/agents/first-contact-v1.json",
  "/public-node/agents/capabilities-v1.json",
  "/discovery/",
]) {
  assert.match(publicNode, new RegExp(relative.replaceAll("/", "\\/")));
}
assert.doesNotMatch(publicNode, /<form\b/iu);
assert.doesNotMatch(publicNode, /\bfetch\s*\(/u);

const robots = read("robots.txt").trimEnd().split("\n");
assert.deepEqual(robots, [
  "# VOID_FREE_DISCOVERY_PAGES_INTEGRATION_V1",
  "# Crawling policy is guidance, not an authorization boundary.",
  "User-agent: *",
  "Allow: /",
  "Disallow: /admin/",
  "Disallow: /internal/",
  "Disallow: /operator/",
  "Disallow: /private/",
  "Disallow: /debug/",
  "Disallow: /metrics",
  `Sitemap: ${ORIGIN}/sitemap.xml`,
]);

const sitemap = read("sitemap.xml");
const sitemapUrls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/gu)].map((match) => match[1]);
assert.equal(sitemapUrls.length, new Set(sitemapUrls).size, "sitemap URLs must be unique");
for (const url of [...PRESERVED_SITEMAP_URLS, ...REQUIRED_URLS]) {
  assert.equal(sitemapUrls.includes(url), true, `sitemap omitted ${url}`);
}

assert.match(INDEXNOW_KEY, /^[A-Za-z0-9-]{8,128}$/u);
assert.equal(read(INDEXNOW_FILE), `${INDEXNOW_KEY}\n`);

const integration = pagesManifest.free_discovery_pages_integration_v1;
assert.equal(integration.marker, "VOID_FREE_DISCOVERY_PAGES_INTEGRATION_V1");
assert.equal(integration.origin, ORIGIN);
assert.equal(integration.source_commit, "b9b8189347a12bfe0528f980f4edb7dffd3e6e1a");
assert.equal(integration.indexnow_key_location, `${ORIGIN}/${INDEXNOW_FILE}`);
assert.equal(integration.live_submission, false);
assert.equal(integration.provider_account_mutation, false);
assert.equal(integration.payment_method_collection, false);
assert.equal(integration.payment_execution, false);
assert.equal(integration.wallet_or_signer_access, false);
for (const [relative, expected] of Object.entries(integration.files)) {
  assert.equal(sha256(relative), expected, `manifest hash mismatch: ${relative}`);
}

const workflow = read(".github/workflows/void-free-discovery-pages-integration-v1.yml");
assert.match(workflow, /^permissions:\n  contents: read$/mu);
assert.match(workflow, /runs-on: ubuntu-24\.04/u);
assert.match(workflow, /timeout-minutes: 5/u);
assert.match(workflow, /actions\/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8/u);
assert.doesNotMatch(workflow, /pull-requests:\s*write/u);
assert.doesNotMatch(workflow, /contents:\s*write/u);

console.log("VOID_FREE_DISCOVERY_PAGES_INTEGRATION_V1_PROOF_GREEN");
console.log("origin=https://6zoso9.github.io");
console.log("static_discovery_only=true");
console.log("existing_sitemap_inventory_preserved=true");
console.log("signed_network_authenticity_bytes_exact=true");
console.log("indexnow_key_public_at_deployment=true");
console.log("network_calls=false");
console.log("live_submission=false");
console.log("provider_account_mutation=false");
console.log("payment_method_collection=false");
console.log("payment_execution=false");
console.log("wallet_or_signer_access=false");
console.log("fund_movement=false");
