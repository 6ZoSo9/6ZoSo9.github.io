#!/usr/bin/env node
/**
 * Zero-dependency VOID MCP + A2A discovery and read-only client.
 * Requires Node.js 18+ for the built-in fetch implementation.
 */

import { randomUUID } from "node:crypto";
import https from "node:https";

const DEFAULT_DISCOVERY =
  "https://6zoso9.github.io/discovery/index-v1.json";
const DEFAULT_MCP_METADATA =
  "https://6zoso9.github.io/mcp/remote-server-v1.json";
const DEFAULT_A2A_CATALOGUE =
  "https://6zoso9.github.io/a2a/agent-v1.json";
const MCP_PROTOCOL_VERSION = "2025-11-25";
const A2A_PROTOCOL_VERSION = "1.0";

class ClientError extends Error {}

async function nativeFetchText(url, options = {}) {
  const {
    acceptedStatuses: _acceptedStatuses,
    ...requestOptions
  } = options;

  const response = await fetch(url, {
    redirect: "follow",
    signal: AbortSignal.timeout(20_000),
    headers: {
      "user-agent": "void-agent-client-node/1.0",
      accept: "application/json",
      ...(requestOptions.headers ?? {}),
    },
    ...requestOptions,
  });

  return {
    status: response.status,
    headers: Object.fromEntries(response.headers.entries()),
    text: await response.text(),
  };
}

async function dohAddresses(hostname) {
  const addresses = [];

  for (const [recordType, expectedType] of [
    ["A", 1],
    ["AAAA", 28],
  ]) {
    const url =
      "https://cloudflare-dns.com/dns-query?name=" +
      encodeURIComponent(hostname) +
      "&type=" +
      recordType;

    const response = await fetch(url, {
      signal: AbortSignal.timeout(20_000),
      headers: {
        accept: "application/dns-json",
        "user-agent": "void-agent-client-node-doh/1.0",
      },
    });

    if (!response.ok) {
      throw new ClientError(
        `Cloudflare DoH returned HTTP ${response.status}`,
      );
    }

    const value = await response.json();

    for (const answer of value.Answer ?? []) {
      if (
        answer &&
        answer.type === expectedType &&
        typeof answer.data === "string"
      ) {
        addresses.push(answer.data);
      }
    }
  }

  return [...new Set(addresses)].sort((left, right) => {
    const leftV6 = left.includes(":") ? 1 : 0;
    const rightV6 = right.includes(":") ? 1 : 0;
    return leftV6 - rightV6 || left.localeCompare(right);
  });
}

function requestTextViaAddress(url, options, address) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const body =
      options.body === undefined || options.body === null
        ? null
        : Buffer.from(String(options.body));

    const headers = {
      "user-agent": "void-agent-client-node/1.0",
      accept: "application/json",
      ...(options.headers ?? {}),
      host: parsed.host,
      connection: "close",
    };

    if (body !== null) {
      headers["content-length"] = String(body.length);
    }

    const request = https.request(
      {
        protocol: "https:",
        hostname: address,
        port: parsed.port || 443,
        servername: parsed.hostname,
        method: options.method ?? "GET",
        path: `${parsed.pathname}${parsed.search}`,
        headers,
        rejectUnauthorized: true,
        timeout: 20_000,
      },
      (response) => {
        const chunks = [];

        response.on("data", (chunk) => {
          chunks.push(Buffer.from(chunk));
        });

        response.on("end", () => {
          resolve({
            status: response.statusCode ?? 0,
            headers: response.headers,
            text: Buffer.concat(chunks).toString("utf8"),
          });
        });
      },
    );

    request.on("timeout", () => {
      request.destroy(new Error("request timeout"));
    });
    request.on("error", reject);

    if (body !== null) {
      request.write(body);
    }
    request.end();
  });
}

async function dohFetchText(url, options = {}) {
  const parsed = new URL(url);
  if (parsed.protocol !== "https:") {
    throw new ClientError(
      `DoH fallback supports HTTPS URLs only: ${url}`,
    );
  }

  const errors = [];

  for (const address of await dohAddresses(parsed.hostname)) {
    try {
      return await requestTextViaAddress(url, options, address);
    } catch (error) {
      errors.push(`${address}: ${error}`);
    }
  }

  throw new ClientError(
    `${options.method ?? "GET"} ${url} failed through all ` +
      `DoH addresses: ${JSON.stringify(errors)}`,
  );
}

async function fetchJson(url, options = {}) {
  let response;

  try {
    response = await nativeFetchText(url, options);
  } catch (_nativeError) {
    response = await dohFetchText(url, options);
  }

  const text = response.text;
  let value = null;

  if (text.length > 0) {
    try {
      value = JSON.parse(text);
    } catch (error) {
      throw new ClientError(`Invalid JSON from ${url}: ${error}`);
    }
  }

  const accepted = options.acceptedStatuses ?? [];
  const ok = response.status >= 200 && response.status < 300;

  if (!ok && !accepted.includes(response.status)) {
    throw new ClientError(
      `${options.method ?? "GET"} ${url} returned HTTP ` +
        `${response.status}: ${text.slice(0, 500)}`,
    );
  }

  return {
    status: response.status,
    headers: response.headers,
    value,
  };
}


async function resolveEndpoints() {
  const [discovery, mcp, a2a] = await Promise.all([
    fetchJson(DEFAULT_DISCOVERY),
    fetchJson(DEFAULT_MCP_METADATA),
    fetchJson(DEFAULT_A2A_CATALOGUE),
  ]);

  const mcpEndpoint = mcp.value?.endpoint;
  const a2aEndpoint = a2a.value?.endpoint;
  const a2aAgentCard = a2a.value?.agentCard;

  for (const [label, value] of Object.entries({
    mcpEndpoint,
    a2aEndpoint,
    a2aAgentCard,
  })) {
    if (typeof value !== "string" || !value.startsWith("https://")) {
      throw new ClientError(`${label} is not an HTTPS URL`);
    }
  }

  return {
    discoveryUrl: DEFAULT_DISCOVERY,
    mcpMetadataUrl: DEFAULT_MCP_METADATA,
    a2aCatalogueUrl: DEFAULT_A2A_CATALOGUE,
    mcpEndpoint,
    a2aEndpoint,
    a2aAgentCard,
    discovery: discovery.value,
    mcpMetadata: mcp.value,
    a2aCatalogue: a2a.value,
  };
}

async function mcpRequest(
  endpoint,
  { id, method, params = undefined, initialize = false },
) {
  const payload = { jsonrpc: "2.0", id, method };
  if (params !== undefined) payload.params = params;

  const headers = {
    "content-type": "application/json",
    accept: "application/json, text/event-stream",
    "mcp-method": method,
  };

  if (!initialize) {
    headers["mcp-protocol-version"] = MCP_PROTOCOL_VERSION;
  }

  const name = params?.name ?? params?.uri;
  if (typeof name === "string") headers["mcp-name"] = name;

  const response = await fetchJson(endpoint, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (response.value?.error) {
    throw new ClientError(
      `MCP ${method} error: ${JSON.stringify(response.value.error)}`,
    );
  }

  return response.value;
}

async function mcpInitialize(endpoint) {
  const response = await mcpRequest(endpoint, {
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: MCP_PROTOCOL_VERSION,
      capabilities: {},
      clientInfo: {
        name: "void-agent-client-node",
        version: "1.0.0",
      },
    },
    initialize: true,
  });

  if (response?.result?.protocolVersion !== MCP_PROTOCOL_VERSION) {
    throw new ClientError("MCP protocol version differs");
  }

  await fetchJson(endpoint, {
    method: "POST",
    acceptedStatuses: [202],
    headers: {
      "content-type": "application/json",
      accept: "application/json, text/event-stream",
      "mcp-protocol-version": MCP_PROTOCOL_VERSION,
      "mcp-method": "notifications/initialized",
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "notifications/initialized",
    }),
  });

  return response;
}

async function mcpTools(endpoint) {
  await mcpInitialize(endpoint);
  const response = await mcpRequest(endpoint, {
    id: 2,
    method: "tools/list",
    params: {},
  });
  const tools = response?.result?.tools;
  if (!Array.isArray(tools)) throw new ClientError("MCP tools array absent");
  return tools;
}

async function mcpResources(endpoint) {
  await mcpInitialize(endpoint);
  const response = await mcpRequest(endpoint, {
    id: 3,
    method: "resources/list",
    params: {},
  });
  const resources = response?.result?.resources;
  if (!Array.isArray(resources)) {
    throw new ClientError("MCP resources array absent");
  }
  return resources;
}

async function mcpCall(endpoint, tool) {
  await mcpInitialize(endpoint);
  const response = await mcpRequest(endpoint, {
    id: 4,
    method: "tools/call",
    params: {
      name: tool,
      arguments: {},
    },
  });
  return response?.result;
}

async function a2aCard(url) {
  return (await fetchJson(url)).value;
}

async function a2aRequest(endpoint, { id, method, params }) {
  const response = await fetchJson(endpoint, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      accept: "application/json",
      "a2a-version": A2A_PROTOCOL_VERSION,
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id,
      method,
      params,
    }),
  });

  if (response.value?.error) {
    throw new ClientError(
      `A2A ${method} error: ${JSON.stringify(response.value.error)}`,
    );
  }
  return response.value;
}

async function a2aAsk(endpoint, query) {
  const response = await a2aRequest(endpoint, {
    id: 10,
    method: "SendMessage",
    params: {
      message: {
        messageId: randomUUID(),
        contextId: "void-agent-client",
        role: "ROLE_USER",
        parts: [
          {
            text: query,
            mediaType: "text/plain",
          },
        ],
      },
      configuration: {
        acceptedOutputModes: ["text/plain", "application/json"],
      },
    },
  });
  return response?.result?.message;
}

async function a2aTasks(endpoint) {
  const response = await a2aRequest(endpoint, {
    id: 11,
    method: "ListTasks",
    params: {},
  });
  return response?.result;
}

async function smoke(endpoints) {
  const tools = await mcpTools(endpoints.mcpEndpoint);
  const resources = await mcpResources(endpoints.mcpEndpoint);
  const chainHead = await mcpCall(
    endpoints.mcpEndpoint,
    "void_get_chain_head",
  );
  const card = await a2aCard(endpoints.a2aAgentCard);
  const message = await a2aAsk(
    endpoints.a2aEndpoint,
    "What is the current VOID chain head?",
  );
  const tasks = await a2aTasks(endpoints.a2aEndpoint);

  const toolNames = tools.map((item) => item.name);
  const resourceUris = resources.map((item) => item.uri);

  if (!toolNames.includes("void_get_chain_head")) {
    throw new ClientError("Required MCP tool is absent");
  }
  if (!resourceUris.includes("void://chain/head")) {
    throw new ClientError("Required MCP resource is absent");
  }
  if (chainHead?.isError !== false) {
    throw new ClientError("MCP chain-head call returned an error");
  }
  if (card?.name !== "VOID Network Read-Only Agent") {
    throw new ClientError("A2A Agent Card name differs");
  }
  if (message?.role !== "ROLE_AGENT") {
    throw new ClientError("A2A direct-message role differs");
  }
  const taskKeys =
    tasks !== null &&
    typeof tasks === "object" &&
    !Array.isArray(tasks)
      ? Object.keys(tasks).sort()
      : [];

  if (
    !Array.isArray(tasks?.tasks) ||
    tasks.tasks.length !== 0 ||
    tasks.nextPageToken !== "" ||
    taskKeys.length !== 2 ||
    taskKeys[0] !== "nextPageToken" ||
    taskKeys[1] !== "tasks"
  ) {
    throw new ClientError("A2A task-list boundary differs");
  }

  return {
    status: "exact_green",
    mcpEndpoint: endpoints.mcpEndpoint,
    a2aEndpoint: endpoints.a2aEndpoint,
    a2aAgentCard: endpoints.a2aAgentCard,
    mcpTools: toolNames,
    mcpResources: resourceUris,
    mcpChainHeadRead: true,
    a2aDirectMessage: true,
    a2aTaskListEmpty: true,
    mutationPerformed: false,
  };
}

function usage() {
  console.error(
    [
      "Usage:",
      "  node void-agent-client.mjs discover",
      "  node void-agent-client.mjs mcp-tools",
      "  node void-agent-client.mjs mcp-resources",
      "  node void-agent-client.mjs mcp-call <tool>",
      "  node void-agent-client.mjs a2a-card",
      "  node void-agent-client.mjs a2a-ask <query>",
      "  node void-agent-client.mjs a2a-tasks",
      "  node void-agent-client.mjs smoke",
    ].join("\n"),
  );
}

async function main() {
  const [command, ...args] = process.argv.slice(2);
  if (!command) {
    usage();
    process.exitCode = 2;
    return;
  }

  const endpoints = await resolveEndpoints();
  let output;

  if (command === "discover") {
    output = Object.fromEntries(
      [
        "discoveryUrl",
        "mcpMetadataUrl",
        "a2aCatalogueUrl",
        "mcpEndpoint",
        "a2aEndpoint",
        "a2aAgentCard",
      ].map((key) => [key, endpoints[key]]),
    );
  } else if (command === "mcp-tools") {
    output = await mcpTools(endpoints.mcpEndpoint);
  } else if (command === "mcp-resources") {
    output = await mcpResources(endpoints.mcpEndpoint);
  } else if (command === "mcp-call" && args[0]) {
    output = await mcpCall(endpoints.mcpEndpoint, args[0]);
  } else if (command === "a2a-card") {
    output = await a2aCard(endpoints.a2aAgentCard);
  } else if (command === "a2a-ask" && args.length > 0) {
    output = await a2aAsk(endpoints.a2aEndpoint, args.join(" "));
  } else if (command === "a2a-tasks") {
    output = await a2aTasks(endpoints.a2aEndpoint);
  } else if (command === "smoke") {
    output = await smoke(endpoints);
  } else {
    usage();
    process.exitCode = 2;
    return;
  }

  console.log(JSON.stringify(output, null, 2));
}

main().catch((error) => {
  console.error(`ERROR: ${error.message ?? error}`);
  process.exitCode = 1;
});
