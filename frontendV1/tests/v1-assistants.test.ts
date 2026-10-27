/**
 * Contract and regression tests for AI Assistant domain in QNU AI Platform v1.
 */

import assert from "node:assert/strict";
import { test } from "vitest";
import { ApiProblemError, createV1Client } from "../src/app/api/v1/client.ts";
import type { CallerWorkspaceRole } from "../src/app/auth/v1/permissions.ts";
import { canManageAssistants } from "../src/features/assistants/permissions.ts";
import { assistantKeys } from "../src/features/assistants/queries.ts";
import {
  createAssistant,
  getAssistant,
  listAssistants,
  updateAssistant,
} from "../src/features/assistants/requests.ts";
import {
  assistantCreateSchema,
  assistantListSearchSchema,
  assistantUpdateSchema,
} from "../src/features/assistants/schemas.ts";
import type {
  Assistant,
  AssistantCreateInput,
  AssistantUpdateInput,
} from "../src/features/assistants/types.ts";

type RecordedCall = {
  url: string;
  method: string;
  headers: Headers;
  body: unknown;
};

function createMockFetch(
  handler: (call: RecordedCall) => Response | Promise<Response>,
) {
  const calls: RecordedCall[] = [];
  const fetchImpl = async (input: string, init?: RequestInit) => {
    let parsedBody: unknown = init?.body;
    if (typeof init?.body === "string") {
      try {
        parsedBody = JSON.parse(init.body);
      } catch {
        parsedBody = init.body;
      }
    }
    const call: RecordedCall = {
      url: input,
      method: init?.method ?? "GET",
      headers: new Headers(init?.headers),
      body: parsedBody,
    };
    calls.push(call);
    return handler(call);
  };
  return { calls, fetchImpl };
}

const mockAssistant: Assistant = {
  id: "ast-101",
  workspace_id: "ws-test",
  name: "Trợ lý Tuyển sinh",
  description: "Tư vấn hồ sơ và quy chế tuyển sinh 2026",
  persona: "Bạn là trợ lý tư vấn tuyển sinh đại học.",
  collection_id: "col-kb-1",
  chat_provider_id: "prov-chat-1",
  top_k: 5,
  history_turns: 3,
  max_output_tokens: 2048,
  is_active: true,
  revision: 2,
  created_by: "user-1",
  created_at: "2026-10-27T08:00:00Z",
  updated_at: "2026-10-27T08:30:00Z",
};

test("Assistant API: listAssistants returns raw array with limit and offset query params", async () => {
  const { calls, fetchImpl } = createMockFetch((call) => {
    if (
      call.method === "GET" &&
      call.url.includes("/workspaces/ws-test/assistants?limit=15&offset=30")
    ) {
      return new Response(JSON.stringify([mockAssistant]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response("Not Found", { status: 404 });
  });

  const client = createV1Client({
    baseUrl: "http://api.local",
    prefix: "/platform/v1alpha1",
    fetchImpl,
  });

  const list = await listAssistants(client, "ws-test", {
    limit: 15,
    offset: 30,
  });

  assert.equal(calls.length, 1);
  assert.equal(calls[0].method, "GET");
  assert.equal(
    calls[0].url,
    "http://api.local/platform/v1alpha1/workspaces/ws-test/assistants?limit=15&offset=30",
  );
  assert.equal(Array.isArray(list), true);
  assert.equal(list.length, 1);
  assert.equal(list[0].id, "ast-101");
  assert.equal(list[0].name, "Trợ lý Tuyển sinh");
});

test("Assistant API: getAssistant maps to GET detail endpoint", async () => {
  const { calls, fetchImpl } = createMockFetch((call) => {
    if (
      call.method === "GET" &&
      call.url ===
        "http://api.local/platform/v1alpha1/workspaces/ws-test/assistants/ast-101"
    ) {
      return new Response(JSON.stringify(mockAssistant), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response("Not Found", { status: 404 });
  });

  const client = createV1Client({
    baseUrl: "http://api.local",
    prefix: "/platform/v1alpha1",
    fetchImpl,
  });

  const result = await getAssistant(client, "ws-test", "ast-101");
  assert.equal(calls.length, 1);
  assert.equal(calls[0].method, "GET");
  assert.equal(result.id, "ast-101");
  assert.equal(result.collection_id, "col-kb-1");
});

test("Assistant API: createAssistant posts full config with trimmed name and non-null string defaults", async () => {
  const { calls, fetchImpl } = createMockFetch((call) => {
    if (
      call.method === "POST" &&
      call.url ===
        "http://api.local/platform/v1alpha1/workspaces/ws-test/assistants"
    ) {
      return new Response(
        JSON.stringify({
          ...mockAssistant,
          id: "ast-new",
          revision: 1,
        }),
        {
          status: 201,
          headers: { "Content-Type": "application/json" },
        },
      );
    }
    return new Response("Bad Request", { status: 400 });
  });

  const client = createV1Client({
    baseUrl: "http://api.local",
    prefix: "/platform/v1alpha1",
    fetchImpl,
  });

  const input: AssistantCreateInput = {
    name: "   Trợ lý Khảo thí 2026   ",
    description: "",
    persona: "",
    collection_id: "col-khao-thi",
    chat_provider_id: null,
    top_k: 5,
    history_turns: 3,
    max_output_tokens: 2048,
    is_active: true,
  };

  const created = await createAssistant(client, "ws-test", input);

  assert.equal(calls.length, 1);
  assert.equal(calls[0].method, "POST");
  const body = calls[0].body as Record<string, unknown>;
  assert.equal(body.name, "Trợ lý Khảo thí 2026");
  assert.equal(body.description, "");
  assert.equal(body.persona, "");
  assert.equal(body.collection_id, "col-khao-thi");
  assert.equal(body.chat_provider_id, null);
  assert.equal(body.top_k, 5);
  assert.equal(body.history_turns, 3);
  assert.equal(body.max_output_tokens, 2048);
  assert.equal(body.is_active, true);
  assert.equal(created.id, "ast-new");
});

test("Assistant API: updateAssistant sends all config fields plus expected_revision via PUT", async () => {
  const { calls, fetchImpl } = createMockFetch((call) => {
    if (
      call.method === "PUT" &&
      call.url ===
        "http://api.local/platform/v1alpha1/workspaces/ws-test/assistants/ast-101"
    ) {
      return new Response(
        JSON.stringify({
          ...mockAssistant,
          name: "Trợ lý Tuyển sinh Cập nhật",
          revision: 3,
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      );
    }
    return new Response("Bad Request", { status: 400 });
  });

  const client = createV1Client({
    baseUrl: "http://api.local",
    prefix: "/platform/v1alpha1",
    fetchImpl,
  });

  const updatePayload: AssistantUpdateInput = {
    name: "Trợ lý Tuyển sinh Cập nhật",
    description: "Cập nhật mô tả",
    persona: "Persona mới",
    collection_id: "col-kb-1", // Immutable, preserved
    chat_provider_id: "prov-chat-1",
    top_k: 8,
    history_turns: 4,
    max_output_tokens: 4096,
    is_active: true,
    expected_revision: 2,
  };

  const updated = await updateAssistant(
    client,
    "ws-test",
    "ast-101",
    updatePayload,
  );

  assert.equal(calls.length, 1);
  assert.equal(calls[0].method, "PUT");
  const body = calls[0].body as Record<string, unknown>;
  assert.equal(body.name, "Trợ lý Tuyển sinh Cập nhật");
  assert.equal(body.expected_revision, 2);
  assert.equal(body.collection_id, "col-kb-1");
  assert.equal(body.top_k, 8);
  assert.equal(body.history_turns, 4);
  assert.equal(body.max_output_tokens, 4096);
  assert.equal(updated.revision, 3);
});

test("Assistant API: Toggle active status preserves all existing fields and sends expected_revision", async () => {
  const { calls, fetchImpl } = createMockFetch((_call) => {
    return new Response(
      JSON.stringify({
        ...mockAssistant,
        is_active: false,
        revision: 3,
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  });

  const client = createV1Client({
    baseUrl: "http://api.local",
    prefix: "/platform/v1alpha1",
    fetchImpl,
  });

  // Toggle active: invert is_active while copying all other properties
  const togglePayload: AssistantUpdateInput = {
    name: mockAssistant.name,
    description: mockAssistant.description,
    persona: mockAssistant.persona,
    collection_id: mockAssistant.collection_id,
    chat_provider_id: mockAssistant.chat_provider_id,
    top_k: mockAssistant.top_k,
    history_turns: mockAssistant.history_turns,
    max_output_tokens: mockAssistant.max_output_tokens,
    is_active: !mockAssistant.is_active,
    expected_revision: mockAssistant.revision,
  };

  const res = await updateAssistant(
    client,
    mockAssistant.workspace_id,
    mockAssistant.id,
    togglePayload,
  );

  assert.equal(calls.length, 1);
  const sent = calls[0].body as Record<string, unknown>;
  assert.equal(sent.is_active, false);
  assert.equal(sent.expected_revision, 2);
  assert.equal(sent.name, mockAssistant.name);
  assert.equal(sent.description, mockAssistant.description);
  assert.equal(sent.persona, mockAssistant.persona);
  assert.equal(sent.collection_id, mockAssistant.collection_id);
  assert.equal(sent.chat_provider_id, mockAssistant.chat_provider_id);
  assert.equal(res.is_active, false);
  assert.equal(res.revision, 3);
});

test("Assistant API: Revision conflict (409) throws ApiProblemError with assistant_revision_conflict code", async () => {
  const { fetchImpl } = createMockFetch(() => {
    return new Response(
      JSON.stringify({
        type: "about:blank",
        title: "Conflict",
        status: 409,
        detail: "Cấu hình trợ lý đã thay đổi.",
        code: "assistant_revision_conflict",
      }),
      {
        status: 409,
        headers: { "Content-Type": "application/problem+json" },
      },
    );
  });

  const client = createV1Client({
    baseUrl: "http://api.local",
    prefix: "/platform/v1alpha1",
    fetchImpl,
  });

  await assert.rejects(
    async () => {
      await updateAssistant(client, "ws-test", "ast-101", {
        name: "Test Conflict",
        description: "",
        persona: "",
        collection_id: "col-1",
        chat_provider_id: null,
        top_k: 5,
        history_turns: 3,
        max_output_tokens: 2048,
        is_active: true,
        expected_revision: 1, // Stale revision
      });
    },
    (err: unknown) => {
      assert.ok(err instanceof ApiProblemError);
      assert.equal(err.status, 409);
      assert.equal(err.code, "assistant_revision_conflict");
      assert.equal(err.message, "Cấu hình trợ lý đã thay đổi.");
      return true;
    },
  );
});

test("Assistant API: Collection immutability conflict (409) throws ApiProblemError", async () => {
  const { fetchImpl } = createMockFetch(() => {
    return new Response(
      JSON.stringify({
        type: "about:blank",
        title: "Conflict",
        status: 409,
        detail: "Tạo trợ lý mới khi đổi kho tri thức.",
        code: "assistant_collection_immutable",
      }),
      {
        status: 409,
        headers: { "Content-Type": "application/problem+json" },
      },
    );
  });

  const client = createV1Client({
    baseUrl: "http://api.local",
    prefix: "/platform/v1alpha1",
    fetchImpl,
  });

  await assert.rejects(
    async () => {
      await updateAssistant(client, "ws-test", "ast-101", {
        name: "Test",
        description: "",
        persona: "",
        collection_id: "col-different",
        chat_provider_id: null,
        top_k: 5,
        history_turns: 3,
        max_output_tokens: 2048,
        is_active: true,
        expected_revision: 2,
      });
    },
    (err: unknown) => {
      assert.ok(err instanceof ApiProblemError);
      assert.equal(err.status, 409);
      assert.equal(err.code, "assistant_collection_immutable");
      return true;
    },
  );
});

test("Assistant Permissions: Only workspace admin or platform admin can manage assistants", () => {
  const platformAdmin: CallerWorkspaceRole = { kind: "platform-admin" };
  const wsAdmin: CallerWorkspaceRole = {
    kind: "member",
    role: "admin",
    member: {
      id: "mem-1",
      workspace_id: "ws-1",
      user_id: "u-1",
      role: "admin",
      status: "active",
      joined_at: "2026-10-01",
    },
  };
  const wsEditor: CallerWorkspaceRole = {
    kind: "member",
    role: "editor",
    member: {
      id: "mem-2",
      workspace_id: "ws-1",
      user_id: "u-2",
      role: "editor",
      status: "active",
      joined_at: "2026-10-01",
    },
  };
  const wsMember: CallerWorkspaceRole = {
    kind: "member",
    role: "member",
    member: {
      id: "mem-3",
      workspace_id: "ws-1",
      user_id: "u-3",
      role: "member",
      status: "active",
      joined_at: "2026-10-01",
    },
  };
  const unknownRole: CallerWorkspaceRole = { kind: "unknown" };

  assert.equal(canManageAssistants(platformAdmin), true);
  assert.equal(canManageAssistants(wsAdmin), true);
  // Editor and Member CANNOT create or update assistants
  assert.equal(canManageAssistants(wsEditor), false);
  assert.equal(canManageAssistants(wsMember), false);
  assert.equal(canManageAssistants(unknownRole), false);
});

test("Assistant Schemas: Validation rules for create, update and search", () => {
  // Name validation
  assert.throws(() =>
    assistantCreateSchema.parse({ name: "   ", collection_id: "col-1" }),
  );
  assert.throws(() =>
    assistantCreateSchema.parse({ name: "", collection_id: "col-1" }),
  );
  assert.throws(() =>
    assistantCreateSchema.parse({
      name: "a".repeat(161),
      collection_id: "col-1",
    }),
  );

  // Collection ID required
  assert.throws(() =>
    assistantCreateSchema.parse({ name: "Trợ lý", collection_id: "" }),
  );

  // Top K bounds (1 to 20)
  assert.throws(() =>
    assistantCreateSchema.parse({
      name: "Trợ lý",
      collection_id: "col-1",
      top_k: 0,
    }),
  );
  assert.throws(() =>
    assistantCreateSchema.parse({
      name: "Trợ lý",
      collection_id: "col-1",
      top_k: 21,
    }),
  );
  assert.throws(() =>
    assistantCreateSchema.parse({
      name: "Trợ lý",
      collection_id: "col-1",
      top_k: 2.5,
    }),
  );

  // History turns bounds (0 to 10)
  assert.throws(() =>
    assistantCreateSchema.parse({
      name: "Trợ lý",
      collection_id: "col-1",
      history_turns: -1,
    }),
  );
  assert.throws(() =>
    assistantCreateSchema.parse({
      name: "Trợ lý",
      collection_id: "col-1",
      history_turns: 11,
    }),
  );

  // Max output tokens (strictly positive integer, no arbitrary 8k cap)
  assert.throws(() =>
    assistantCreateSchema.parse({
      name: "Trợ lý",
      collection_id: "col-1",
      max_output_tokens: 0,
    }),
  );
  assert.throws(() =>
    assistantCreateSchema.parse({
      name: "Trợ lý",
      collection_id: "col-1",
      max_output_tokens: -10,
    }),
  );
  const largeTokens = assistantCreateSchema.parse({
    name: "Trợ lý",
    collection_id: "col-1",
    max_output_tokens: 65536,
  });
  assert.equal(largeTokens.max_output_tokens, 65536);

  // String defaults: never null
  const parsed = assistantCreateSchema.parse({
    name: "  Trợ lý Test  ",
    collection_id: "col-1",
  });
  assert.equal(parsed.name, "Trợ lý Test");
  assert.equal(parsed.description, "");
  assert.equal(parsed.persona, "");
  assert.equal(parsed.chat_provider_id, null);
  assert.equal(parsed.top_k, 5);
  assert.equal(parsed.history_turns, 3);
  assert.equal(parsed.max_output_tokens, 2048);
  assert.equal(parsed.is_active, true);

  // Update schema requires expected_revision >= 1
  assert.throws(() => assistantUpdateSchema.parse({ ...parsed }));
  assert.throws(() =>
    assistantUpdateSchema.parse({ ...parsed, expected_revision: 0 }),
  );
  assert.throws(() =>
    assistantUpdateSchema.parse({ ...parsed, expected_revision: -1 }),
  );
  const validUpdate = assistantUpdateSchema.parse({
    ...parsed,
    expected_revision: 1,
  });
  assert.equal(validUpdate.expected_revision, 1);

  // Search schema parses limit and offset with defaults
  const searchDefault = assistantListSearchSchema.parse({});
  assert.equal(searchDefault.limit, 20);
  assert.equal(searchDefault.offset, 0);

  const searchCustom = assistantListSearchSchema.parse({
    limit: "50",
    offset: "100",
  });
  assert.equal(searchCustom.limit, 50);
  assert.equal(searchCustom.offset, 100);
});

test("Assistant Queries: Scoped query keys adhere to session and workspace isolation", () => {
  const allKeys = assistantKeys.all(1234, "ws-99");
  assert.deepEqual(allKeys, ["v1", 1234, "workspaces", "ws-99", "assistants"]);

  const listKeys = assistantKeys.list(1234, "ws-99", { limit: 20, offset: 40 });
  assert.deepEqual(listKeys, [
    "v1",
    1234,
    "workspaces",
    "ws-99",
    "assistants",
    "list",
    20,
    40,
  ]);

  const detailKeys = assistantKeys.detail(1234, "ws-99", "ast-101");
  assert.deepEqual(detailKeys, [
    "v1",
    1234,
    "workspaces",
    "ws-99",
    "assistants",
    "detail",
    "ast-101",
  ]);
});
