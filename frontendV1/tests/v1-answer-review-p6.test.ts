/**
 * Contract tests for assistant answer tests (plan P6.3/P6.5).
 * These records are human answer reviews; they never write retrieval gold.
 */

import assert from "node:assert/strict";
import { test } from "vitest";
import { createV1Client } from "../src/app/api/v1/client.ts";
import type { CallerWorkspaceRole } from "../src/app/auth/v1/permissions.ts";
import { formatAnswerReviewError } from "../src/features/answer-review/format.ts";
import { canLabelAnswerReviews } from "../src/features/answer-review/permissions.ts";
import { answerReviewKeys } from "../src/features/answer-review/queries.ts";
import {
  createAnswerReview,
  labelAnswerReviewItem,
  listAnswerReviews,
} from "../src/features/answer-review/requests.ts";
import type { AnswerReview } from "../src/features/answer-review/types.ts";

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

const mockReview: AnswerReview = {
  id: "arv-1",
  workspace_id: "ws-test",
  collection_id: "col-kb-1",
  assistant_id: "ast-101",
  assistant_revision: 3,
  requested_by: "user-1",
  question_count: 2,
  status: "completed",
  error_code: null,
  created_at: "2026-11-08T08:00:00Z",
  finished_at: "2026-11-08T08:00:05Z",
  items: [
    {
      id: "avi-1",
      review_id: "arv-1",
      ordinal: 0,
      question: "Câu 1",
      status: "answered",
      error_code: null,
      result: null,
      index_run_id: "idx-run-1",
      generation: 4,
      label: null,
      label_note: null,
      labelled_by: null,
      labelled_at: null,
      created_at: "2026-11-08T08:00:00Z",
      finished_at: "2026-11-08T08:00:02Z",
    },
  ],
};

function buildClient(
  fetchImpl: (input: string, init?: RequestInit) => Promise<Response>,
) {
  return createV1Client({
    baseUrl: "http://api.local",
    prefix: "/platform/v1alpha1",
    fetchImpl,
  });
}

test("Answer review API: list uses the assistant-scoped endpoint with paging", async () => {
  const { calls, fetchImpl } = createMockFetch(
    () =>
      new Response(JSON.stringify([mockReview]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
  );

  const reviews = await listAnswerReviews(
    buildClient(fetchImpl),
    "ws-test",
    "ast-101",
    { limit: 5, offset: 10 },
  );

  assert.equal(calls.length, 1);
  assert.equal(calls[0].method, "GET");
  assert.equal(
    calls[0].url,
    "http://api.local/platform/v1alpha1/workspaces/ws-test/assistants/ast-101/answer-reviews?limit=5&offset=10",
  );
  assert.equal(reviews[0].assistant_revision, 3);
  assert.equal(reviews[0].items[0].generation, 4);
});

test("Answer review API: create sends trimmed questions with an idempotency key", async () => {
  const { calls, fetchImpl } = createMockFetch(
    () =>
      new Response(JSON.stringify(mockReview), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
  );

  const review = await createAnswerReview(
    buildClient(fetchImpl),
    "ws-test",
    "ast-101",
    { questions: ["  Câu 1  ", "Câu 2"] },
    "review-key-1",
  );

  assert.equal(calls.length, 1);
  assert.equal(calls[0].method, "POST");
  assert.equal(
    calls[0].url,
    "http://api.local/platform/v1alpha1/workspaces/ws-test/assistants/ast-101/answer-reviews",
  );
  assert.equal(calls[0].headers.get("Idempotency-Key"), "review-key-1");
  assert.deepEqual((calls[0].body as { questions: string[] }).questions, [
    "Câu 1",
    "Câu 2",
  ]);
  assert.equal(review.id, "arv-1");
});

test("Answer review API: labelling sends the label and trimmed note via PUT", async () => {
  const labelled: AnswerReview = {
    ...mockReview,
    items: [
      {
        ...mockReview.items[0],
        label: "wrong_year",
        label_note: "Năm 2025",
        labelled_by: "user-1",
        labelled_at: "2026-11-08T08:05:00Z",
      },
    ],
  };
  const { calls, fetchImpl } = createMockFetch(
    () =>
      new Response(JSON.stringify(labelled), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
  );

  const result = await labelAnswerReviewItem(
    buildClient(fetchImpl),
    "ws-test",
    "ast-101",
    "arv-1",
    "avi-1",
    { label: "wrong_year", note: "  Năm 2025  " },
  );

  assert.equal(calls.length, 1);
  assert.equal(calls[0].method, "PUT");
  assert.equal(
    calls[0].url,
    "http://api.local/platform/v1alpha1/workspaces/ws-test/assistants/ast-101/answer-reviews/arv-1/items/avi-1",
  );
  assert.deepEqual(calls[0].body, {
    label: "wrong_year",
    note: "Năm 2025",
  });
  assert.equal(result.items[0].label, "wrong_year");
});

test("Answer review permissions: only admin, editor, reviewer or platform admin label", () => {
  const platformAdmin: CallerWorkspaceRole = { kind: "platform-admin" };
  const admin: CallerWorkspaceRole = { kind: "member", role: "admin" };
  const editor: CallerWorkspaceRole = { kind: "member", role: "editor" };
  const reviewer: CallerWorkspaceRole = { kind: "member", role: "reviewer" };
  const member: CallerWorkspaceRole = { kind: "member", role: "member" };
  const unknown: CallerWorkspaceRole = { kind: "unknown" };
  const none: CallerWorkspaceRole = { kind: "none" };

  assert.equal(canLabelAnswerReviews(platformAdmin), true);
  assert.equal(canLabelAnswerReviews(admin), true);
  assert.equal(canLabelAnswerReviews(editor), true);
  assert.equal(canLabelAnswerReviews(reviewer), true);
  assert.equal(canLabelAnswerReviews(member), false);
  assert.equal(canLabelAnswerReviews(unknown), false);
  assert.equal(canLabelAnswerReviews(none), false);
});

test("Answer review keys: isolated by session, workspace and assistant", () => {
  assert.deepEqual(answerReviewKeys.root(1234, "ws-99", "ast-1"), [
    "v1",
    1234,
    "workspaces",
    "ws-99",
    "assistants",
    "answer-reviews",
    "ast-1",
  ]);
  assert.deepEqual(answerReviewKeys.list(1234, "ws-99", "ast-1"), [
    "v1",
    1234,
    "workspaces",
    "ws-99",
    "assistants",
    "answer-reviews",
    "ast-1",
    "list",
  ]);
});

test("Answer review errors: published-source and model failures stay distinct", () => {
  assert.match(
    formatAnswerReviewError("assistant_no_published_sources"),
    /tài liệu xuất bản/,
  );
  assert.match(
    formatAnswerReviewError("chat_provider_unavailable"),
    /lỗi hạ tầng/,
  );
  assert.equal(
    formatAnswerReviewError("unknown_code", "Thông báo dự phòng"),
    "Thông báo dự phòng",
  );
});
