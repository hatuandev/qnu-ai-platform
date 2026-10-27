/**
 * Contract and regression tests for Conversations and Chat domain in QNU AI Platform v1.
 */

import assert from "node:assert/strict";
import { test } from "vitest";
import { ApiProblemError, createV1Client } from "../src/app/api/v1/client.ts";
import { conversationsQueryKeys } from "../src/features/conversations/queries.ts";
import {
  createConversation,
  getConversation,
  getTurn,
  listConversations,
  listTurns,
  sendTurn,
  updateConversation,
} from "../src/features/conversations/requests.ts";
import {
  conversationCreateSchema,
  conversationListSearchSchema,
  conversationUpdateSchema,
  expectedTurnNoSchema,
  formatConversationError,
  generateIdempotencyKey,
  turnQuestionSchema,
  turnRequestSchema,
} from "../src/features/conversations/schemas.ts";
import type {
  Conversation,
  TurnResponse,
} from "../src/features/conversations/types.ts";

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

const mockConversation: Conversation = {
  id: "cnv_test_123",
  workspace_id: "ws_456",
  collection_id: "col_789",
  assistant_id: "ast_abc",
  assistant_revision: 1,
  owner_ref: "usr_alice",
  title: "Tư vấn tuyển sinh ngành CNTT",
  status: "active",
  document_ids: null,
  last_turn_no: 2,
  created_at: "2026-10-27T08:00:00Z",
  updated_at: "2026-10-27T08:15:00Z",
};

const mockTurn: TurnResponse = {
  id: "trn_001",
  conversation_id: "cnv_test_123",
  turn_no: 1,
  question: "Chỉ tiêu ngành Công nghệ thông tin năm nay là bao nhiêu?",
  resolved_question: null,
  history_turn_ids: [],
  status: "completed",
  error_code: null,
  result: {
    id: "ans_999",
    status: "answered",
    reason: null,
    answer: "Chỉ tiêu ngành CNTT là 150 sinh viên.",
    statements: [
      {
        text: "Chỉ tiêu ngành CNTT năm 2026 là 150 sinh viên.",
        evidence_ids: ["E1"],
      },
    ],
    sources: [
      {
        evidence_id: "E1",
        chunk_id: "chk_001",
        document_id: "doc_101",
        version_id: "ver_202",
        publication_decision_id: "pub_303",
        score: 0.95,
        kind: "table",
        text: "Bảng chỉ tiêu tuyển sinh 2026: Ngành CNTT: 150 chỉ tiêu",
        citations: { page: 3, table: 1 },
        structure: null,
      },
    ],
    index_run_id: "idx_555",
    generation: 1,
    trace: {
      prompt_version: "v1.0",
      total_tokens: 450,
      model_name: "Qwen3.5-9B",
    },
  },
  rewrite_trace: null,
  source_status: "current",
  created_at: "2026-10-27T08:05:00Z",
  finished_at: "2026-10-27T08:05:02Z",
};

test("Conversation API: listConversations returns raw array with limit and offset query params", async () => {
  const { calls, fetchImpl } = createMockFetch((call) => {
    assert.match(
      call.url,
      /\/platform\/v1alpha1\/workspaces\/ws_456\/conversations\?limit=20&offset=0/,
    );
    assert.equal(call.method, "GET");
    return new Response(JSON.stringify([mockConversation]), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });

  const client = createV1Client({
    fetchImpl,
    getToken: () => "mock-token",
  });

  const result = await listConversations(client, "ws_456", {
    limit: 20,
    offset: 0,
  });

  assert.equal(calls.length, 1);
  assert.equal(Array.isArray(result), true);
  assert.equal(result.length, 1);
  assert.equal(result[0].id, "cnv_test_123");
  assert.equal(result[0].last_turn_no, 2);
});

test("Conversation API: getConversation maps to GET detail endpoint", async () => {
  const { calls, fetchImpl } = createMockFetch((call) => {
    assert.match(
      call.url,
      /\/platform\/v1alpha1\/workspaces\/ws_456\/conversations\/cnv_test_123$/,
    );
    assert.equal(call.method, "GET");
    return new Response(JSON.stringify(mockConversation), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });

  const client = createV1Client({
    fetchImpl,
    getToken: () => "mock-token",
  });

  const conv = await getConversation(client, "ws_456", "cnv_test_123");

  assert.equal(calls.length, 1);
  assert.equal(conv.id, "cnv_test_123");
  assert.equal(conv.title, "Tư vấn tuyển sinh ngành CNTT");
});

test("Conversation API: createConversation posts assistant_id and title", async () => {
  const { calls, fetchImpl } = createMockFetch((call) => {
    assert.match(
      call.url,
      /\/platform\/v1alpha1\/workspaces\/ws_456\/conversations$/,
    );
    assert.equal(call.method, "POST");
    const body = call.body as Record<string, unknown>;
    assert.equal(body.assistant_id, "ast_abc");
    assert.equal(body.title, "Cuộc trò chuyện mới");
    // Verify document_ids, owner_ref, history, provider_id are NOT sent
    assert.equal(body.owner_ref, undefined);
    assert.equal(body.history, undefined);

    return new Response(JSON.stringify(mockConversation), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    });
  });

  const client = createV1Client({
    fetchImpl,
    getToken: () => "mock-token",
  });

  const created = await createConversation(client, "ws_456", {
    assistant_id: "ast_abc",
    title: "  Cuộc trò chuyện mới  ",
  });

  assert.equal(calls.length, 1);
  assert.equal(created.id, "cnv_test_123");
});

test("Conversation API: updateConversation sends title and status via PUT", async () => {
  const { calls, fetchImpl } = createMockFetch((call) => {
    assert.match(
      call.url,
      /\/platform\/v1alpha1\/workspaces\/ws_456\/conversations\/cnv_test_123$/,
    );
    assert.equal(call.method, "PUT");
    const body = call.body as Record<string, unknown>;
    assert.equal(body.title, "Tiêu đề đã đổi");
    assert.equal(body.status, "archived");

    return new Response(
      JSON.stringify({
        ...mockConversation,
        title: "Tiêu đề đã đổi",
        status: "archived",
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  });

  const client = createV1Client({
    fetchImpl,
    getToken: () => "mock-token",
  });

  const updated = await updateConversation(client, "ws_456", "cnv_test_123", {
    title: "  Tiêu đề đã đổi  ",
    status: "archived",
  });

  assert.equal(calls.length, 1);
  assert.equal(updated.title, "Tiêu đề đã đổi");
  assert.equal(updated.status, "archived");
});

test("Conversation API: listTurns returns raw array with limit and offset query params", async () => {
  const { calls, fetchImpl } = createMockFetch((call) => {
    assert.match(
      call.url,
      /\/platform\/v1alpha1\/workspaces\/ws_456\/conversations\/cnv_test_123\/turns\?limit=50&offset=0/,
    );
    assert.equal(call.method, "GET");
    return new Response(JSON.stringify([mockTurn]), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });

  const client = createV1Client({
    fetchImpl,
    getToken: () => "mock-token",
  });

  const turns = await listTurns(client, "ws_456", "cnv_test_123", {
    limit: 50,
    offset: 0,
  });

  assert.equal(calls.length, 1);
  assert.equal(Array.isArray(turns), true);
  assert.equal(turns.length, 1);
  assert.equal(turns[0].turn_no, 1);
  assert.equal(turns[0].status, "completed");
});

test("Conversation API: getTurn maps to GET single turn endpoint", async () => {
  const { calls, fetchImpl } = createMockFetch((call) => {
    assert.match(
      call.url,
      /\/platform\/v1alpha1\/workspaces\/ws_456\/conversations\/cnv_test_123\/turns\/trn_001$/,
    );
    assert.equal(call.method, "GET");
    return new Response(JSON.stringify(mockTurn), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });

  const client = createV1Client({
    fetchImpl,
    getToken: () => "mock-token",
  });

  const turn = await getTurn(client, "ws_456", "cnv_test_123", "trn_001");

  assert.equal(calls.length, 1);
  assert.equal(turn.id, "trn_001");
  assert.equal(turn.result?.status, "answered");
});

test("Conversation API: sendTurn sends question, expected_turn_no and Idempotency-Key header", async () => {
  const idempotencyKey = "uuid-test-key-12345";
  const { calls, fetchImpl } = createMockFetch((call) => {
    assert.match(
      call.url,
      /\/platform\/v1alpha1\/workspaces\/ws_456\/conversations\/cnv_test_123\/turns$/,
    );
    assert.equal(call.method, "POST");
    assert.equal(call.headers.get("Idempotency-Key"), idempotencyKey);
    const body = call.body as Record<string, unknown>;
    assert.equal(body.question, "Học phí ngành CNTT là bao nhiêu?");
    assert.equal(body.expected_turn_no, 2);

    return new Response(
      JSON.stringify({
        ...mockTurn,
        turn_no: 3,
        question: "Học phí ngành CNTT là bao nhiêu?",
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  });

  const client = createV1Client({
    fetchImpl,
    getToken: () => "mock-token",
  });

  const turn = await sendTurn(
    client,
    "ws_456",
    "cnv_test_123",
    {
      question: "  Học phí ngành CNTT là bao nhiêu?  ",
      expected_turn_no: 2,
    },
    idempotencyKey,
  );

  assert.equal(calls.length, 1);
  assert.equal(turn.turn_no, 3);
});

test("Conversation API: Sequence conflict (409) throws ApiProblemError with conversation_sequence_conflict", async () => {
  const { fetchImpl } = createMockFetch(() => {
    return new Response(
      JSON.stringify({
        type: "https://httpstatuses.com/409",
        title: "Conflict",
        status: 409,
        detail: "Lịch sử đã thay đổi; tải lại hội thoại.",
        code: "conversation_sequence_conflict",
      }),
      {
        status: 409,
        headers: { "Content-Type": "application/problem+json" },
      },
    );
  });

  const client = createV1Client({
    fetchImpl,
    getToken: () => "mock-token",
  });

  await assert.rejects(
    async () => {
      await sendTurn(
        client,
        "ws_456",
        "cnv_test_123",
        {
          question: "Câu hỏi test",
          expected_turn_no: 1, // out of sync
        },
        "key-123",
      );
    },
    (err: unknown) => {
      assert(err instanceof ApiProblemError);
      assert.equal(err.status, 409);
      assert.equal(err.code, "conversation_sequence_conflict");
      return true;
    },
  );
});

test("Conversation API: Error formatting handles all backend error codes honestly", () => {
  assert.equal(
    formatConversationError("conversation_busy"),
    "Hội thoại đang xử lý một lượt hỏi khác. Vui lòng đợi lượt hiện tại hoàn tất.",
  );
  assert.equal(
    formatConversationError("conversation_sequence_conflict"),
    "Lịch sử hội thoại đã thay đổi; vui lòng làm mới để cập nhật số thứ tự lượt hỏi mới nhất.",
  );
  assert.equal(
    formatConversationError("idempotency_conflict"),
    "Khóa Idempotency-Key đã được sử dụng cho câu hỏi khác. Vui lòng thử lại với lượt mới.",
  );
  assert.equal(
    formatConversationError("conversation_assistant_changed"),
    "Cấu hình trợ lý đã thay đổi; cần tạo hội thoại mới để áp dụng cấu hình mới nhất.",
  );
  assert.equal(
    formatConversationError("assistant_inactive"),
    "Trợ lý AI này đã tạm dừng hoạt động; không thể gửi câu hỏi mới.",
  );
  assert.equal(
    formatConversationError("conversation_archived"),
    "Hội thoại đã được lưu trữ. Mở lại hội thoại để tiếp tục trò chuyện.",
  );
  assert.equal(
    formatConversationError("answer_evidence_changed"),
    "Nguồn tài liệu chứng minh đã thay đổi; câu trả lời cũ không còn hiệu lực.",
  );
});

test("Conversation Schemas: validates title, question and expected_turn_no", () => {
  // Title validation
  assert.throws(() => {
    conversationUpdateSchema.parse({ title: "", status: "active" });
  });
  assert.throws(() => {
    conversationUpdateSchema.parse({
      title: "a".repeat(161),
      status: "active",
    });
  });
  const validUpdate = conversationUpdateSchema.parse({
    title: "  Hội thoại hợp lệ  ",
    status: "active",
  });
  assert.equal(validUpdate.title, "Hội thoại hợp lệ");
  assert.equal(validUpdate.status, "active");

  // Question validation
  assert.throws(() => {
    turnRequestSchema.parse({ question: "", expected_turn_no: 0 });
  });
  assert.throws(() => {
    turnRequestSchema.parse({
      question: "a".repeat(8001),
      expected_turn_no: 0,
    });
  });
  assert.throws(() => {
    turnRequestSchema.parse({ question: "Hợp lệ", expected_turn_no: -1 });
  });
  const validTurn = turnRequestSchema.parse({
    question: "  Hỏi đáp hợp lệ  ",
    expected_turn_no: 5,
  });
  assert.equal(validTurn.question, "Hỏi đáp hợp lệ");
  assert.equal(validTurn.expected_turn_no, 5);

  // Create schema validation
  assert.throws(() => {
    conversationCreateSchema.parse({ assistant_id: "", title: "Ok" });
  });
  const validCreate = conversationCreateSchema.parse({
    assistant_id: "ast_123",
  });
  assert.equal(validCreate.title, "Hội thoại mới");

  // Single field schemas
  assert.equal(expectedTurnNoSchema.parse(0), 0);
  assert.equal(turnQuestionSchema.parse("  Câu hỏi  "), "Câu hỏi");

  // Search defaults
  const parsedSearch = conversationListSearchSchema.parse({});
  assert.equal(parsedSearch.limit, 20);
  assert.equal(parsedSearch.offset, 0);

  // Idempotency key generation
  const key = generateIdempotencyKey();
  assert(key.length >= 1 && key.length <= 128);
  assert.match(key, /^[A-Za-z0-9_.:-]+$/);
});

test("Conversation Queries: Scoped query keys adhere to session and workspace isolation", () => {
  const sessionId = 42;
  const workspaceId = "ws_test";
  const conversationId = "cnv_test";

  const rootKey = conversationsQueryKeys.root(sessionId, workspaceId);
  assert.deepEqual(rootKey, [
    "v1",
    42,
    "workspaces",
    "ws_test",
    "conversations",
  ]);

  const detailKey = conversationsQueryKeys.detail(
    sessionId,
    workspaceId,
    conversationId,
  );
  assert.deepEqual(detailKey, [
    "v1",
    42,
    "workspaces",
    "ws_test",
    "conversations",
    "detail",
    "cnv_test",
  ]);

  const turnsKey = conversationsQueryKeys.turns(
    sessionId,
    workspaceId,
    conversationId,
    { limit: 50, offset: 0 },
  );
  assert.deepEqual(turnsKey, [
    "v1",
    42,
    "workspaces",
    "ws_test",
    "conversations",
    "detail",
    "cnv_test",
    "turns",
    { limit: 50, offset: 0 },
  ]);
});
