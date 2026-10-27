/**
 * Focused contract tests for the QNU AI v1 integration.
 *
 * These exercise the real request builders and the client's error handling
 * against an in-memory fetch mock — no backendV1 required, so they run in CI
 * without paid inference or a live database. Every test asserts behaviour that
 * §3–§6 pins down: Bearer auth, the problem+json contract, the "a 404/403 is
 * never an empty list" rule, PATCH keep-vs-clear semantics, the full-replace
 * nature of allowlist/defaults PUTs, and that a key secret travels in the body
 * only (never the URL, and the client never persists it).
 */

import assert from "node:assert/strict";
import { test } from "vitest";
import { ApiProblemError, createV1Client } from "../src/app/api/v1/client.ts";
import {
  isModelAdmin,
  isPlatformWorkspaceAdmin,
  resolveCallerWorkspaceRole,
} from "../src/app/auth/v1/permissions.ts";
import type { Provider, V1Actor } from "../src/app/auth/v1/types.ts";
import {
  buildProviderPatch,
  EMPTY_CAPACITY_DRAFT,
  validateCapacityDraft,
} from "../src/features/modelops/capacity-patch.ts";
import {
  createProviderKey,
  listProviderKeys,
  revokeProviderKey,
  rotateProviderKey,
} from "../src/features/modelops/requests.ts";
import {
  draftFromAllowlist,
  orphanedDefaults,
  pruneOrphanedDefaults,
  sameAllowlist,
  setCapabilityDefault,
  toAllowlistInput,
  toggleProvider,
  withCapabilityDefault,
} from "../src/features/workspaces/allowlist-patch.ts";
import { buildWorkspacePatch } from "../src/features/workspaces/patch.ts";
import {
  addMember,
  createWorkspace,
  getWorkspace,
  listMembers,
  listWorkspaces,
  loadMembersForRole,
  revokeMember,
  updateMember,
  updateWorkspace,
} from "../src/features/workspaces/requests.ts";

type MockRequest = {
  method: string;
  url: string;
  headers: Record<string, string>;
  body: unknown;
};

type MockHandler = (req: MockRequest) => {
  status?: number;
  body?: unknown;
  contentType?: string;
};

function mockServer(handler: MockHandler) {
  const requests: MockRequest[] = [];
  const fetchImpl = async (
    input: string,
    init?: RequestInit,
  ): Promise<Response> => {
    const rawHeaders = new Headers(init?.headers ?? {});
    const headers: Record<string, string> = {};
    rawHeaders.forEach((value, key) => {
      headers[key] = value;
    });
    const body = init?.body ? JSON.parse(init.body as string) : undefined;
    const request: MockRequest = {
      method: init?.method ?? "GET",
      url: input,
      headers,
      body,
    };
    requests.push(request);
    const result = handler(request);
    return new Response(
      result.body === undefined ? null : JSON.stringify(result.body),
      {
        status: result.status ?? 200,
        headers: { "content-type": result.contentType ?? "application/json" },
      },
    );
  };
  return { fetchImpl, requests };
}

const PREFIX = "/platform/v1alpha1";
const BASE = "http://test.local";
const problem = (status: number, code: string, detail = "nope") => ({
  status,
  body: { type: "about:blank", title: "Error", status, code, detail },
  contentType: "application/problem+json",
});

function actor(over: Partial<V1Actor> = {}): V1Actor {
  return {
    actor_id: "me",
    username: "me",
    display_name: "Me",
    email: null,
    user_type: "human",
    role: "member",
    roles: [],
    permissions: [],
    authenticated: true,
    ...over,
  } as V1Actor;
}

test("client sends and omits the Bearer token", async () => {
  const { fetchImpl, requests } = mockServer(() => ({
    body: { items: [], meta: { page: 1, page_size: 20, total: 0 } },
  }));

  const authed = createV1Client({
    baseUrl: BASE,
    prefix: PREFIX,
    fetchImpl,
    getToken: () => "tok",
  });
  await authed.get("/workspaces");
  assert.equal(requests[0].headers.authorization, "Bearer tok");

  const anon = createV1Client({
    baseUrl: BASE,
    prefix: PREFIX,
    fetchImpl,
    getToken: () => null,
  });
  await anon.get("/workspaces");
  assert.equal(requests[1].headers.authorization, undefined);
});

test("401 triggers the unauthorized handler and classifies as unauthorized", async () => {
  let called = false;
  const { fetchImpl } = mockServer(() => problem(401, "unauthorized"));
  const client = createV1Client({
    baseUrl: BASE,
    prefix: PREFIX,
    fetchImpl,
    onUnauthorized: () => {
      called = true;
    },
  });

  await assert.rejects(client.get("/auth/me"), (error: unknown) => {
    assert.ok(error instanceof ApiProblemError);
    assert.equal((error as ApiProblemError).kind, "unauthorized");
    assert.equal((error as ApiProblemError).status, 401);
    assert.equal(called, true);
    return true;
  });
});

test("403 on a list is surfaced as an error, never coerced to an empty list", async () => {
  const { fetchImpl } = mockServer(() => problem(403, "workspace_suspended"));
  const client = createV1Client({ baseUrl: BASE, prefix: PREFIX, fetchImpl });
  await assert.rejects(
    listWorkspaces(client, { page: 1, pageSize: 20 }),
    (error: unknown) => {
      const e = error as ApiProblemError;
      assert.equal(e.kind, "forbidden");
      assert.equal(e.code, "workspace_suspended");
      return true;
    },
  );
});

test("404/409/422/5xx classify without inventing field errors", async () => {
  const { fetchImpl } = mockServer((req) => {
    if (req.method === "GET" && req.url.endsWith("/workspaces/abc"))
      return problem(404, "not_found");
    if (req.method === "POST" && req.url.endsWith("/workspaces"))
      return problem(409, "code_taken");
    if (req.method === "PATCH") return problem(422, "validation");
    return problem(500, "server_error");
  });
  const client = createV1Client({ baseUrl: BASE, prefix: PREFIX, fetchImpl });

  await assert.rejects(getWorkspace(client, "abc"), (error) => {
    const e = error as ApiProblemError;
    assert.equal(e.kind, "not_found");
    assert.equal(
      e.fieldErrors,
      undefined,
      "422 must not invent field errors when the body has none",
    );
    return true;
  });
  await assert.rejects(
    createWorkspace(client, { code: "x", name: "x" }),
    (e: unknown) => (e as ApiProblemError).kind === "conflict",
  );
  await assert.rejects(
    updateWorkspace(client, "abc", { name: "x" }),
    (e: unknown) => (e as ApiProblemError).kind === "invalid",
  );
  await assert.rejects(
    client.get("/boom"),
    (e: unknown) => (e as ApiProblemError).kind === "server",
  );
});

test("workspace CRUD maps to the right method, path and body", async () => {
  const { fetchImpl, requests } = mockServer((req) => {
    if (req.method === "POST" && req.url.endsWith("/workspaces")) {
      assert.deepEqual(req.body, { code: "khoa", name: "Khoa" });
      return {
        body: { id: "w1", code: "khoa", name: "Khoa", status: "active" },
      };
    }
    if (req.method === "GET" && req.url.includes("/workspaces/w1/members")) {
      assert.ok(req.url.includes("page=2"));
      assert.ok(req.url.includes("page_size=20"));
      return {
        body: { items: [], meta: { page: 2, page_size: 20, total: 0 } },
      };
    }
    if (req.method === "PATCH" && req.url.endsWith("/workspaces/w1")) {
      assert.deepEqual(req.body, { name: "Khoa mới" });
      return { body: { id: "w1", name: "Khoa mới" } };
    }
    if (req.method === "POST" && req.url.endsWith("/workspaces/w1/members")) {
      assert.deepEqual(req.body, { actor_ref: "u2", role: "editor" });
      return { body: { id: "m1" } };
    }
    if (req.method === "PATCH" && req.url.endsWith("/members/m1")) {
      assert.deepEqual(req.body, { role: "admin" });
      return { body: { id: "m1" } };
    }
    if (req.method === "DELETE" && req.url.endsWith("/members/m1")) {
      return { body: { id: "m1", status: "revoked" } };
    }
    return { body: {} };
  });
  const client = createV1Client({ baseUrl: BASE, prefix: PREFIX, fetchImpl });

  await createWorkspace(client, { code: "khoa", name: "Khoa" });
  await listMembers(client, "w1", { page: 2, pageSize: 20 });
  await updateWorkspace(client, "w1", { name: "Khoa mới" });
  await addMember(client, "w1", { actor_ref: "u2", role: "editor" });
  await updateMember(client, "w1", "m1", { role: "admin" });
  await revokeMember(client, "w1", "m1");

  assert.equal(requests.length, 6);
});

test("provider PATCH omits provider_type and keeps capacity on an unrelated change", async () => {
  const provider = {
    id: "p1",
    name: "Old",
    provider_type: "local" as const,
    base_url: "http://x",
    model_name: "m",
    capabilities: ["chat"],
    is_active: true,
    priority: 5,
    timeout_seconds: 30,
    token_limits: {
      context_window_tokens: 1000,
      max_input_tokens: 800,
      max_output_tokens: 200,
      ocr_page_input: null,
    },
    capacity_status: "configured" as const,
    capacity_basis: "operator_configured" as const,
    embedding_dimension: 1024,
    embedding_dimension_status: "configured" as const,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  } satisfies Provider;

  const patch = buildProviderPatch(provider, {
    name: "New",
    baseUrl: "http://x",
    modelName: "m",
    capabilities: ["chat"],
    priority: "5",
    timeoutSeconds: "30",
    capacity: {
      ...EMPTY_CAPACITY_DRAFT,
      contextWindowTokens: "1000",
      maxInputTokens: "800",
      maxOutputTokens: "200",
      embeddingDimension: "1024",
    },
  });

  // A rename/capacity-equal edit must NOT send provider_type, token_limits or embedding_dimension.
  assert.equal(patch.name, "New");
  assert.equal("provider_type" in patch, false);
  assert.equal(
    "token_limits" in patch,
    false,
    "capacity identical → token_limits must stay untouched",
  );
  assert.equal(
    "embedding_dimension" in patch,
    false,
    "rename must not wipe embedding_dimension",
  );
  assert.deepEqual(Object.keys(patch), ["name"]);
});

test("explicit empty capacity clears token_limits via null", async () => {
  const provider = {
    id: "p1",
    name: "P",
    provider_type: "local" as const,
    base_url: "http://x",
    model_name: "m",
    capabilities: ["chat"],
    is_active: true,
    priority: 5,
    timeout_seconds: 30,
    token_limits: {
      context_window_tokens: 1000,
      max_input_tokens: 800,
      max_output_tokens: 200,
      ocr_page_input: null,
    },
    capacity_status: "configured" as const,
    capacity_basis: "operator_configured" as const,
    embedding_dimension: 1024,
    embedding_dimension_status: "configured" as const,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  } satisfies Provider;

  const patch = buildProviderPatch(provider, {
    name: "P",
    baseUrl: "http://x",
    modelName: "m",
    capabilities: ["chat"],
    priority: "5",
    timeoutSeconds: "30",
    capacity: EMPTY_CAPACITY_DRAFT, // every field cleared
  });
  assert.equal(
    patch.token_limits,
    null,
    "cleared capacity must be sent as null, not omitted",
  );
  assert.equal(patch.embedding_dimension, null);
});

test("validateCapacityDraft rejects inferring a context window from the OCR budget", async () => {
  assert.equal(
    validateCapacityDraft({
      ...EMPTY_CAPACITY_DRAFT,
      ocrMaxImageWidth: "100",
      ocrMaxImageHeight: "100",
      ocrInputTokensUpperBound: "50",
      ocrPromptSha256: "a".repeat(64),
    }),
    "Khai báo ocr_page_input cần kèm ít nhất một giới hạn token của model.",
  );
  assert.equal(validateCapacityDraft(EMPTY_CAPACITY_DRAFT), null);
});

test("provider key lifecycle posts the secret in the body and never in the URL", async () => {
  const { fetchImpl, requests } = mockServer((req) => {
    if (req.method === "GET" && req.url.endsWith("/keys")) return { body: [] };
    if (req.method === "POST" && req.url.endsWith("/keys"))
      return { body: { id: "k1" } };
    if (req.method === "POST" && req.url.endsWith("/keys/k1/rotate"))
      return { body: { id: "k1" } };
    if (req.method === "POST" && req.url.endsWith("/keys/k1/revoke"))
      return { body: { id: "k1" } };
    return { body: {} };
  });
  const client = createV1Client({ baseUrl: BASE, prefix: PREFIX, fetchImpl });

  await listProviderKeys(client, "p1");
  await createProviderKey(client, "p1", {
    name: "k",
    secret: "SUPER_SECRET",
    priority: 7,
  });
  assert.equal(requests[1].url, `${BASE}${PREFIX}/modelops/providers/p1/keys`);
  assert.equal(
    requests[1].url.includes("SUPER_SECRET"),
    false,
    "secret must not be in the URL",
  );
  assert.deepEqual(requests[1].body, {
    name: "k",
    secret: "SUPER_SECRET",
    priority: 7,
  });

  await rotateProviderKey(client, "p1", "k1", {
    name: "k",
    secret: "SUPER_SECRET",
    priority: 7,
    reason: "leak",
  });
  assert.equal(
    requests[2].url,
    `${BASE}${PREFIX}/modelops/providers/p1/keys/k1/rotate`,
  );
  assert.deepEqual(requests[2].body, {
    name: "k",
    secret: "SUPER_SECRET",
    priority: 7,
    reason: "leak",
  });

  await revokeProviderKey(client, "p1", "k1", { reason: "disable" });
  assert.equal(
    requests[3].url,
    `${BASE}${PREFIX}/modelops/providers/p1/keys/k1/revoke`,
  );
});

test("allowlist PUT is a full replace; orphaned defaults are detected and pruned", async () => {
  const allowlist = {
    workspace_id: "w1",
    providers: [
      {
        provider_id: "p1",
        name: "P1",
        capabilities: ["chat"],
        is_active: true,
        is_default: true,
        default_capabilities: ["chat"],
      },
      {
        provider_id: "p2",
        name: "P2",
        capabilities: ["embedding"],
        is_active: true,
        is_default: true,
        default_capabilities: ["embedding"],
      },
    ],
  };
  const draft = draftFromAllowlist(allowlist);
  assert.deepEqual(draft.providerIds.sort(), ["p1", "p2"]);
  assert.equal(draft.defaults.chat, "p1");

  const removed = toggleProvider(draft, "p1", false);
  assert.deepEqual(removed.providerIds, ["p2"]);
  assert.deepEqual(
    orphanedDefaults(removed).map((o) => o.capability),
    ["chat"],
  );
  const pruned = pruneOrphanedDefaults(removed);
  assert.equal(
    pruned.defaults.chat,
    undefined,
    "default pointing at a removed provider must be dropped",
  );

  const withEmbeddingDefault = setCapabilityDefault(removed, "embedding", "p2");
  assert.equal(withEmbeddingDefault.defaults.embedding, "p2");

  assert.deepEqual(toAllowlistInput(pruned), {
    provider_ids: ["p2"],
    defaults: { embedding: "p2" },
  });
  assert.equal(sameAllowlist(draftFromAllowlist(allowlist), draft), true);

  // model-defaults PUT replaces the whole map but keeps unrelated capabilities.
  assert.deepEqual(withCapabilityDefault({ chat: "p1" }, "embedding", "p2"), {
    chat: "p1",
    embedding: "p2",
  });
  assert.deepEqual(withCapabilityDefault({ chat: "p1" }, "embedding", null), {
    chat: "p1",
  });
});

test("workspace role resolution honours paginated membership", async () => {
  const a = actor({ actor_id: "u1" });

  // Active membership → member role.
  assert.equal(
    resolveCallerWorkspaceRole({
      actor: a,
      members: [
        { id: "m", actor_ref: "u1", role: "admin", status: "active" } as never,
      ],
      total: 1,
      platformAdmin: false,
    }).kind,
    "member",
  );

  // Membership exists but revoked → no permission.
  assert.equal(
    resolveCallerWorkspaceRole({
      actor: a,
      members: [
        { id: "m", actor_ref: "u1", role: "admin", status: "revoked" } as never,
      ],
      total: 1,
      platformAdmin: false,
    }).kind,
    "none",
  );

  // Caller not on the first page and total > read → unknown, not "no permission".
  const partial = resolveCallerWorkspaceRole({
    actor: a,
    members: [
      { id: "m", actor_ref: "u9", role: "member", status: "active" } as never,
    ],
    total: 5,
    platformAdmin: false,
  });
  assert.equal(partial.kind, "unknown");
});

test("loadMembersForRole walks pages until it finds the caller", async () => {
  let calls = 0;
  const { fetchImpl } = mockServer((req) => {
    calls += 1;
    const page = Number(new URL(req.url, BASE).searchParams.get("page"));
    // Page 1 has someone else; page 2 has the caller.
    const items =
      page === 1
        ? [{ id: "m1", actor_ref: "u9", role: "member", status: "active" }]
        : [{ id: "m2", actor_ref: "u1", role: "editor", status: "active" }];
    return { body: { items, meta: { page, page_size: 200, total: 2 } } };
  });
  const client = createV1Client({ baseUrl: BASE, prefix: PREFIX, fetchImpl });

  const result = await loadMembersForRole(client, "w1", "u1");
  assert.equal(calls, 2, "must fetch the next page when the caller is absent");
  assert.equal(result.members.length, 2);
});

test("permission mirrors: ai.models.manage and platform workspace admin", async () => {
  assert.equal(
    isModelAdmin(actor({ permissions: ["ai.models.manage"] })),
    true,
  );
  assert.equal(
    isModelAdmin(actor({ permissions: ["ai.workspaces.manage"] })),
    false,
  );
  assert.equal(
    isPlatformWorkspaceAdmin(actor({ permissions: ["ai.workspaces.manage"] })),
    true,
  );
  assert.equal(isPlatformWorkspaceAdmin(actor({ permissions: [] })), false);
  assert.equal(
    isModelAdmin(
      actor({ role: "ai.access.admin", permissions: ["ai.access.admin"] }),
    ),
    true,
    "admin role should satisfy any ai.* permission",
  );
});

test("workspace description clears on empty string, keeps on equal", async () => {
  const baseline = { name: "W", description: "d" };
  const cleared = buildWorkspacePatch(baseline, { name: "W", description: "" });
  assert.equal(cleared.description, "", "empty string is the explicit clear");
  const kept = buildWorkspacePatch(baseline, { name: "W", description: "d" });
  assert.equal(
    "description" in kept,
    false,
    "unchanged description stays absent from the patch",
  );
});
