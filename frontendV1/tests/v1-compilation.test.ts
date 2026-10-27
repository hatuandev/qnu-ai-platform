/**
 * Focused contract & unit tests for the Compilation module in frontendV1.
 *
 * Verifies:
 * - Compilation request schema validation (topic, ocr_run_ids, text_versions)
 * - Edit preview & Accept edit schemas
 * - Manual review request schema & auto: key rejection
 * - Idempotency key generation & validation
 * - Formatters for status, verdict, assessments, and errors
 * - Role permissions (admin, editor, reviewer, member)
 * - HTTP request builders with mocked fetch
 */

import assert from "node:assert/strict";
import { test } from "vitest";
import { ApiProblemError, createV1Client } from "../src/app/api/v1/client.ts";
import {
  createCompilationReview,
  createCompilationRun,
  getAutoReviewStatus,
  listCompilationRuns,
} from "../src/features/knowledge/compilation-requests.ts";
import {
  acceptEditSchema,
  compilationRequestSchema,
  editPreviewRequestSchema,
  formatAutoReviewStatus,
  formatCompilationError,
  formatCompilationOrigin,
  formatCompilationStatus,
  formatDraftAssessmentStatus,
  formatReviewVerdict,
  formatSourceAssessmentStatus,
  generateIdempotencyKey,
  manualReviewRequestSchema,
  validateReviewIdempotencyKey,
} from "../src/features/knowledge/compilation-schemas.ts";
import {
  canCreateOrEditCompilation,
  canReadCompilation,
  canReviewCompilation,
} from "../src/features/knowledge/permissions.ts";

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
    requests.push({
      method: init?.method ?? "GET",
      url: input,
      headers,
      body,
    });
    const res = handler({
      method: init?.method ?? "GET",
      url: input,
      headers,
      body,
    });
    return new Response(JSON.stringify(res.body ?? {}), {
      status: res.status ?? 200,
      headers: {
        "content-type": res.contentType ?? "application/json",
      },
    });
  };

  const client = createV1Client({
    baseUrl: "https://mock.platform",
    prefix: "/platform/v1alpha1",
    fetchImpl: fetchImpl as unknown as (
      input: string,
      init?: RequestInit,
    ) => Promise<Response>,
    getToken: () => "mock-jwt-token",
  });

  return { client, requests };
}

// ---------------------------------------------------------------------------
// 1. Zod Validation Schemas
// ---------------------------------------------------------------------------

test("compilationRequestSchema accepts valid payload", () => {
  const valid = {
    topic: "Chính sách học bổng tuyển sinh 2026",
    ocr_run_ids: ["ocr_1", "ocr_2"],
    text_versions: { ocr_1: 0, ocr_2: 1 },
    provider_id: null,
    max_output_tokens: 4096,
    structured_output: false,
    auto_review: true,
    review_provider_id: null,
    review_max_output_tokens: 8192,
    review_structured_output: false,
  };

  const parsed = compilationRequestSchema.parse(valid);
  assert.equal(parsed.topic, "Chính sách học bổng tuyển sinh 2026");
  assert.deepEqual(parsed.ocr_run_ids, ["ocr_1", "ocr_2"]);
  assert.equal(parsed.text_versions.ocr_1, 0);
  assert.equal(parsed.text_versions.ocr_2, 1);
});

test("compilationRequestSchema trims topic and rejects empty topic", () => {
  assert.throws(
    () =>
      compilationRequestSchema.parse({ topic: "   ", ocr_run_ids: ["ocr_1"] }),
    /Chủ đề biên soạn không được để trống/,
  );

  const parsed = compilationRequestSchema.parse({
    topic: "  Chủ đề hợp lệ  ",
    ocr_run_ids: ["ocr_1"],
  });
  assert.equal(parsed.topic, "Chủ đề hợp lệ");
});

test("compilationRequestSchema rejects empty ocr_run_ids or duplicate ids", () => {
  assert.throws(
    () => compilationRequestSchema.parse({ topic: "Test", ocr_run_ids: [] }),
    /Chọn ít nhất 1 lượt xử lý OCR/,
  );

  assert.throws(
    () =>
      compilationRequestSchema.parse({
        topic: "Test",
        ocr_run_ids: ["ocr_1", "ocr_1"],
      }),
    /Không được chọn trùng lượt OCR/,
  );
});

test("compilationRequestSchema rejects text_versions with keys outside ocr_run_ids", () => {
  assert.throws(
    () =>
      compilationRequestSchema.parse({
        topic: "Test",
        ocr_run_ids: ["ocr_1"],
        text_versions: { ocr_1: 0, ocr_foreign: 1 },
      }),
    /Phiên bản văn bản phải thuộc OCR đã chọn/,
  );
});

test("editPreviewRequestSchema validates expected_bundle_sha256 and content", () => {
  const validHex64 = "a".repeat(64);
  const validPayload = {
    expected_bundle_sha256: validHex64,
    reason: "Cập nhật tiêu đề theo công văn mới",
    content: {
      title: "Văn bản sửa đổi",
      sections: [
        {
          heading: "Phần 1: Căn cứ",
          paragraphs: [
            {
              text: "Căn cứ Quyết định số 123/QĐ-ĐHQG.",
              citations: ["ocr_1:ev_1"],
            },
          ],
        },
      ],
      unknowns: ["Chưa xác định thời gian áp dụng"],
    },
  };

  const parsed = editPreviewRequestSchema.parse(validPayload);
  assert.equal(parsed.expected_bundle_sha256, validHex64);
  assert.equal(
    parsed.content.sections[0].paragraphs[0].citations[0],
    "ocr_1:ev_1",
  );

  // Rejects invalid sha256
  assert.throws(
    () =>
      editPreviewRequestSchema.parse({
        ...validPayload,
        expected_bundle_sha256: "not-a-hex",
      }),
    /Bundle SHA-256 không hợp lệ/,
  );

  // Rejects empty reason
  assert.throws(
    () =>
      editPreviewRequestSchema.parse({
        ...validPayload,
        reason: "   ",
      }),
    /Lý do chỉnh sửa không được để trống/,
  );
});

test("acceptEditSchema requires 64-char hex preview_sha256", () => {
  const valid = {
    preview_id: "prev_123",
    preview_sha256: "f".repeat(64),
  };
  const parsed = acceptEditSchema.parse(valid);
  assert.equal(parsed.preview_id, "prev_123");

  assert.throws(
    () =>
      acceptEditSchema.parse({
        preview_id: "prev_123",
        preview_sha256: "short",
      }),
    /Preview SHA-256 không hợp lệ/,
  );
});

test("manualReviewRequestSchema defaults review_max_output_tokens to 8192", () => {
  const parsed = manualReviewRequestSchema.parse({});
  assert.equal(parsed.max_output_tokens, 8192);
  assert.equal(parsed.provider_id, undefined);
  assert.equal(parsed.structured_output, false);
});

// ---------------------------------------------------------------------------
// 2. Idempotency Key Rules
// ---------------------------------------------------------------------------

test("generateIdempotencyKey creates 8-128 char key", () => {
  const key = generateIdempotencyKey();
  assert.ok(key.startsWith("cmp_"));
  assert.ok(key.length >= 8 && key.length <= 128);
});

test("validateReviewIdempotencyKey rejects auto: prefix", () => {
  assert.equal(validateReviewIdempotencyKey("auto:review-123"), false);
  assert.equal(validateReviewIdempotencyKey("edit:preview-123"), false);
  assert.equal(validateReviewIdempotencyKey("manual-review-12345"), true);
  assert.equal(validateReviewIdempotencyKey("short"), false); // < 8 chars
});

// ---------------------------------------------------------------------------
// 3. Formatters
// ---------------------------------------------------------------------------

test("formatCompilationStatus maps all known statuses", () => {
  assert.equal(formatCompilationStatus("queued").label, "Đang chờ xếp lịch");
  assert.equal(formatCompilationStatus("running").label, "Đang biên soạn");
  assert.equal(formatCompilationStatus("completed").label, "Đã hoàn thành");
  assert.equal(formatCompilationStatus("failed").label, "Thất bại");
  assert.equal(formatCompilationStatus("uncertain").label, "Chưa chắc chắn");
  assert.equal(formatCompilationStatus("cancelled").label, "Đã hủy");
});

test("formatCompilationOrigin identifies AI vs human edit", () => {
  assert.equal(formatCompilationOrigin("compiler").label, "AI Biên soạn");
  assert.equal(
    formatCompilationOrigin("user_edit").label,
    "Người dùng chỉnh sửa",
  );
});

test("formatAutoReviewStatus maps auto-review states", () => {
  assert.equal(
    formatAutoReviewStatus("queued").label,
    "Đang chờ review tự động",
  );
  assert.equal(formatAutoReviewStatus("running").label, "Đang rà soát tự động");
  assert.equal(
    formatAutoReviewStatus("completed").label,
    "Đã hoàn thành review",
  );
  assert.equal(formatAutoReviewStatus("failed").label, "Review tự động lỗi");
  assert.equal(
    formatAutoReviewStatus("uncertain").label,
    "Review chưa chắc chắn",
  );
});

test("formatReviewVerdict maps verdicts", () => {
  assert.equal(
    formatReviewVerdict("needs_attention").label,
    "Có nội dung cần xem lại",
  );
  assert.equal(
    formatReviewVerdict("no_issues_detected").label,
    "Chưa phát hiện vấn đề",
  );
  assert.equal(formatReviewVerdict(null).label, "Chưa có kết luận");
});

test("formatSourceAssessmentStatus maps source assessments", () => {
  assert.equal(formatSourceAssessmentStatus("covered").label, "Đã phản ánh");
  assert.equal(
    formatSourceAssessmentStatus("omitted").label,
    "Có thể bỏ sót ý",
  );
  assert.equal(
    formatSourceAssessmentStatus("out_of_scope").label,
    "Ngoài phạm vi chủ đề",
  );
  assert.equal(
    formatSourceAssessmentStatus("uncertain").label,
    "Cần đối chiếu thêm",
  );
});

test("formatDraftAssessmentStatus maps draft assessments", () => {
  assert.equal(
    formatDraftAssessmentStatus("supported").label,
    "Có căn cứ nguồn",
  );
  assert.equal(
    formatDraftAssessmentStatus("contradicted").label,
    "Có thể diễn giải sai",
  );
  assert.equal(
    formatDraftAssessmentStatus("unsupported").label,
    "Chưa thấy căn cứ",
  );
  assert.equal(
    formatDraftAssessmentStatus("uncertain").label,
    "Cần đối chiếu thêm",
  );
});

test("formatCompilationError maps known error codes", () => {
  assert.equal(
    formatCompilationError("compilation_not_found"),
    "Không tìm thấy lượt biên soạn trong kho tri thức.",
  );
  assert.equal(
    formatCompilationError("compilation_draft_invalid"),
    "Mô hình trả bản nháp không đúng cấu trúc yêu cầu.",
  );
});

// ---------------------------------------------------------------------------
// 4. Permissions
// ---------------------------------------------------------------------------

test("canCreateOrEditCompilation only allows admin, editor, and platform-admin", () => {
  assert.equal(
    canCreateOrEditCompilation({ kind: "member", role: "admin" }),
    true,
  );
  assert.equal(
    canCreateOrEditCompilation({ kind: "member", role: "editor" }),
    true,
  );
  assert.equal(
    canCreateOrEditCompilation({ kind: "member", role: "reviewer" }),
    false,
  );
  assert.equal(
    canCreateOrEditCompilation({ kind: "member", role: "member" }),
    false,
  );
  assert.equal(canCreateOrEditCompilation({ kind: "none" }), false);
  assert.equal(canCreateOrEditCompilation(undefined), false);
  assert.equal(canCreateOrEditCompilation({ kind: "platform-admin" }), true);
});

test("canReviewCompilation allows reviewer in addition to admin and editor", () => {
  assert.equal(canReviewCompilation({ kind: "member", role: "admin" }), true);
  assert.equal(canReviewCompilation({ kind: "member", role: "editor" }), true);
  assert.equal(
    canReviewCompilation({ kind: "member", role: "reviewer" }),
    true,
  );
  assert.equal(canReviewCompilation({ kind: "member", role: "member" }), false);
  assert.equal(canReviewCompilation({ kind: "none" }), false);
  assert.equal(canReviewCompilation(undefined), false);
  assert.equal(canReviewCompilation({ kind: "platform-admin" }), true);
});

test("canReadCompilation allows all authenticated roles", () => {
  assert.equal(canReadCompilation({ kind: "member", role: "admin" }), true);
  assert.equal(canReadCompilation({ kind: "member", role: "editor" }), true);
  assert.equal(canReadCompilation({ kind: "member", role: "reviewer" }), true);
  assert.equal(canReadCompilation({ kind: "member", role: "member" }), true);
  assert.equal(canReadCompilation({ kind: "none" }), false);
  assert.equal(canReadCompilation(undefined), false);
  assert.equal(canReadCompilation({ kind: "platform-admin" }), true);
});

// ---------------------------------------------------------------------------
// 5. Request Builders & Idempotency Header
// ---------------------------------------------------------------------------

test("createCompilationRun sends Idempotency-Key and Bearer headers", async () => {
  const { client, requests } = mockServer(() => ({
    status: 201,
    body: {
      run: {
        id: "comp_run_1",
        workspace_id: "ws_1",
        collection_id: "col_1",
        generation: 1,
        origin: "llm_compiler",
        status: "queued",
        topic: "Topic 1",
        ocr_run_ids: ["ocr_1"],
        text_versions: { ocr_1: 0 },
        created_at: "2026-10-27T10:00:00Z",
      },
      created: true,
      dispatched: true,
    },
  }));

  const res = await createCompilationRun(
    client,
    "ws_1",
    "col_1",
    {
      topic: "Topic 1",
      ocr_run_ids: ["ocr_1"],
      text_versions: { ocr_1: 0 },
      provider_id: null,
      max_output_tokens: null,
      structured_output: false,
      auto_review: true,
      review_provider_id: null,
      review_max_output_tokens: 8192,
      review_structured_output: false,
    },
    "idemp-key-12345",
  );

  assert.equal(res.created, true);
  assert.equal(res.run.id, "comp_run_1");
  assert.equal(requests.length, 1);
  assert.equal(requests[0].method, "POST");
  assert.equal(requests[0].headers["idempotency-key"], "idemp-key-12345");
  assert.equal(requests[0].headers.authorization, "Bearer mock-jwt-token");
});

test("createCompilationReview throws if idempotency key starts with auto:", async () => {
  const { client } = mockServer(() => ({ status: 200 }));

  await assert.rejects(
    () =>
      createCompilationReview(
        client,
        "ws_1",
        "col_1",
        "comp_1",
        {
          provider_id: null,
          max_output_tokens: 8192,
          structured_output: false,
        },
        "auto:forbidden-key",
      ),
    /Idempotency-Key không hợp lệ/,
  );
});

test("getAutoReviewStatus returns notScheduled when 404 compilation_auto_review_not_found", async () => {
  const { client, requests } = mockServer(() => ({
    status: 404,
    body: {
      type: "https://platform.qnu.edu.vn/errors/compilation_auto_review_not_found",
      title: "Not Found",
      status: 404,
      detail: "Auto review was not requested or not scheduled yet",
    },
  }));

  const res = await getAutoReviewStatus(client, "ws_1", "col_1", "comp_run_1");
  assert.equal(res.notScheduled, true);
  assert.equal(requests.length, 1);
});

test("listCompilationRuns sends limit and query parameters properly", async () => {
  const { client, requests } = mockServer(() => ({
    status: 200,
    body: [
      {
        id: "comp_1",
        workspace_id: "ws_1",
        collection_id: "col_1",
        generation: 2,
        origin: "llm_compiler",
        status: "completed",
        topic: "Topic 2",
        ocr_run_ids: ["ocr_1"],
        text_versions: { ocr_1: 0 },
        created_at: "2026-10-27T10:00:00Z",
      },
    ],
  }));

  const runs = await listCompilationRuns(client, "ws_1", "col_1", 50);
  assert.equal(runs.length, 1);
  assert.equal(runs[0].id, "comp_1");
  assert.ok(requests[0].url.includes("limit=50"));
});

test("F6: unrelated 404 and provider failures are not treated as an absent automatic review", async () => {
  for (const [status, code] of [
    [404, "compilation_not_found"],
    [503, "compilation_auto_review_not_found"],
  ] as const) {
    const { client } = mockServer(() => ({
      status,
      body: { status, code, detail: "Synthetic error" },
    }));
    await assert.rejects(
      getAutoReviewStatus(client, "w", "c", "run"),
      (error) => error instanceof ApiProblemError && error.status === status,
    );
  }
  const { client } = mockServer(() => ({
    status: 404,
    body: {
      type: "https://errors.qnu.edu.vn/compilation_not_found",
      detail: "Missing run",
    },
  }));
  await assert.rejects(
    getAutoReviewStatus(client, "w", "c", "run"),
    (error) => error instanceof ApiProblemError && error.status === 404,
  );
});
