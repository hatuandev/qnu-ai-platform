/**
 * Plan P6.7: a chat failure must never be presented as "the knowledge base has
 * no data" when the real cause is permission, model infrastructure, a
 * clarifying question or a verification stop.
 */

import assert from "node:assert/strict";
import { test } from "vitest";
import {
  classifyConversationFailure,
  formatConversationError,
} from "../src/features/conversations/schemas.ts";
import { describeAnswerReason } from "../src/features/rag/types.ts";

test("Conversation failures: clarification, permission, infrastructure and verification stay distinct", () => {
  assert.equal(
    classifyConversationFailure("conversation_clarification_required"),
    "clarification",
  );
  assert.equal(
    classifyConversationFailure("answer_scope_clarification_required"),
    "clarification",
  );
  assert.equal(
    classifyConversationFailure("workspace_forbidden"),
    "permission",
  );
  assert.equal(
    classifyConversationFailure("workspace_suspended"),
    "permission",
  );
  assert.equal(
    classifyConversationFailure("chat_provider_unavailable"),
    "infrastructure",
  );
  assert.equal(
    classifyConversationFailure("conversation_route_invalid"),
    "infrastructure",
  );
  assert.equal(
    classifyConversationFailure("conversation_history_limit"),
    "state",
  );
  assert.equal(
    classifyConversationFailure("answer_not_supported"),
    "verification",
  );
  assert.equal(
    classifyConversationFailure("conversation_not_found"),
    "not_found",
  );
  assert.equal(classifyConversationFailure("operation_cancelled"), "cancelled");
  assert.equal(classifyConversationFailure("brand_new_code"), "unknown");
  assert.equal(classifyConversationFailure(null), "unknown");
});

test("Conversation failures: each category keeps its own honest copy", () => {
  const clarification = formatConversationError(
    "conversation_clarification_required",
  );
  const infrastructure = formatConversationError("chat_provider_unavailable");
  const permission = formatConversationError("workspace_forbidden");
  const verification = formatConversationError("answer_not_supported");

  assert.match(clarification, /hỏi lại đầy đủ/);
  assert.match(clarification, /không phải lỗi kết nối/);
  assert.match(infrastructure, /lỗi hạ tầng/);
  assert.match(infrastructure, /không phải kết quả/);
  assert.match(permission, /quyền truy cập/);
  assert.match(verification, /không được nguồn trích dẫn hỗ trợ/);

  assert.notEqual(clarification, infrastructure);
  assert.notEqual(infrastructure, permission);
  assert.notEqual(verification, infrastructure);
});

test("Conversation failures: no-evidence result text differs from transport failures", () => {
  const noMatch = describeAnswerReason("no_match");
  const infrastructure = formatConversationError("chat_provider_unavailable");

  assert.match(noMatch, /không khớp/);
  assert.doesNotMatch(noMatch, /hạ tầng/);
  assert.doesNotMatch(infrastructure, /không khớp/);
});

test("Conversation failures: model switch and history limit explain the next step", () => {
  assert.match(
    formatConversationError("chat_provider_changed"),
    /cấu hình model đã thay đổi/i,
  );
  assert.match(
    formatConversationError("conversation_history_limit"),
    /ngân sách ngữ cảnh/,
  );
  assert.equal(
    formatConversationError("unknown_code", "Thông báo dự phòng"),
    "Thông báo dự phòng",
  );
});
