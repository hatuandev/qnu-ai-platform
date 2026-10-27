/**
 * Focused contract & unit tests for Compiled Document Publication in frontendV1.
 *
 * Verifies:
 * - Document creation & version registration schemas
 * - Document key regex and slugifyKey utility
 * - Review gate acknowledgement & finding resolution schemas
 * - Decision preview & commit schemas
 * - Formatters for status, action, and RFC 7807 problem errors
 * - Role permissions (admin, editor, reviewer, member, platform-admin)
 * - HTTP request transport with Idempotency-Key headers and 404 handling
 */

import assert from "node:assert/strict";
import { test } from "vitest";
import { createV1Client } from "../src/app/api/v1/client.ts";
import {
  canApproveCompiledVersion,
  canPublishCompiledVersion,
  canReadCompiledDocuments,
  canRegisterCompiledDocument,
  canWithdrawCompiledVersion,
} from "../src/features/knowledge/permissions.ts";
import {
  commitDecision,
  createCompiledDocument,
  createCompiledVersion,
  createDecisionPreview,
  getCompiledDocument,
  getCompiledDocumentHistory,
  getCompiledVersion,
  getCompiledVersionDraft,
  getCompiledVersionReviewGate,
  getPublishedCompiledDocument,
  listCompiledDocuments,
  listCompiledVersions,
} from "../src/features/knowledge/publication-requests.ts";
import {
  createDocumentSchema,
  decisionCommitSchema,
  decisionPreviewSchema,
  findingResolutionSchema,
  formatDecisionAction,
  formatPublicationError,
  formatPublicationStatus,
  generatePublicationIdempotencyKey,
  registerVersionSchema,
  reviewAckSchema,
  slugifyKey,
} from "../src/features/knowledge/publication-schemas.ts";

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

test("createDocumentSchema accepts valid inputs and trims title", () => {
  const parsed = createDocumentSchema.parse({
    document_key: "chi-tieu-tuyen-sinh-2026",
    title: "  Chỉ tiêu tuyển sinh 2026  ",
    compilation_run_id: "cmp_test123",
  });
  assert.equal(parsed.document_key, "chi-tieu-tuyen-sinh-2026");
  assert.equal(parsed.title, "Chỉ tiêu tuyển sinh 2026");
  assert.equal(parsed.compilation_run_id, "cmp_test123");
});

test("createDocumentSchema rejects invalid document keys", () => {
  const invalidKeys = [
    "Chi-tieu", // uppercase
    "-chi-tieu", // starts with hyphen
    "_chi-tieu", // starts with underscore
    "chi tiêu", // spaces
    "chi@tieu", // special chars
    "", // empty
  ];
  for (const key of invalidKeys) {
    const res = createDocumentSchema.safeParse({
      document_key: key,
      title: "Tiêu đề hợp lệ",
      compilation_run_id: "cmp_1",
    });
    assert.equal(
      res.success,
      false,
      `Expected key "${key}" to fail validation`,
    );
  }
});

test("createDocumentSchema rejects empty or whitespace-only title", () => {
  const res = createDocumentSchema.safeParse({
    document_key: "valid-key",
    title: "   ",
    compilation_run_id: "cmp_1",
  });
  assert.equal(res.success, false);
});

test("registerVersionSchema validates compilation_run_id", () => {
  assert.equal(
    registerVersionSchema.safeParse({ compilation_run_id: "cmp_999" }).success,
    true,
  );
  assert.equal(
    registerVersionSchema.safeParse({ compilation_run_id: "" }).success,
    false,
  );
});

test("slugifyKey produces standard slug from Vietnamese title", () => {
  const slug = slugifyKey("Quy định Đào tạo & Khảo thí ĐH 2026!");
  assert.equal(slug, "quy-dinh-dao-tao-khao-thi-dh-2026");
});

test("findingResolutionSchema validates 64-hex ID and reason length bounds", () => {
  const validFindingId = "a".repeat(64);
  const parsed = findingResolutionSchema.parse({
    finding_id: validFindingId,
    decision: "accepted_risk",
    reason: "Số liệu này đã được phòng đào tạo xác minh bổ sung qua phụ lục 2.",
  });
  assert.equal(parsed.finding_id, validFindingId);
  assert.equal(parsed.decision, "accepted_risk");

  // Reason too short (<10 chars)
  const tooShort = findingResolutionSchema.safeParse({
    finding_id: validFindingId,
    decision: "accepted_risk",
    reason: "OK đúng",
  });
  assert.equal(tooShort.success, false);

  // Invalid decision value
  const badDecision = findingResolutionSchema.safeParse({
    finding_id: validFindingId,
    decision: "fixed_in_draft",
    reason: "Đã sửa trực tiếp vào bản nháp",
  });
  assert.equal(badDecision.success, false);
});

test("reviewAckSchema enforces confirmed_reviewed to be true", () => {
  const validHash = "b".repeat(64);
  const valid = {
    review_id: "rev_1",
    report_sha256: validHash,
    confirmed_reviewed: true,
    resolutions: [],
  };
  assert.equal(reviewAckSchema.safeParse(valid).success, true);

  const invalid = {
    ...valid,
    confirmed_reviewed: false,
  };
  assert.equal(reviewAckSchema.safeParse(invalid).success, false);
});

test("decisionPreviewSchema accepts valid approve, publish, withdraw actions", () => {
  for (const action of ["approve", "publish", "withdraw"] as const) {
    const res = decisionPreviewSchema.safeParse({
      action,
      reason: "Đã rà soát đầy đủ và thống nhất ban hành.",
    });
    assert.equal(res.success, true);
  }

  // Reject invalid action
  const bad = decisionPreviewSchema.safeParse({
    action: "reject",
    reason: "Không đồng ý",
  });
  assert.equal(bad.success, false);
});

test("decisionCommitSchema validates preview_id and SHA-256", () => {
  const validHash = "c".repeat(64);
  const valid = decisionCommitSchema.safeParse({
    preview_id: "pprev_123",
    preview_sha256: validHash,
  });
  assert.equal(valid.success, true);

  const invalid = decisionCommitSchema.safeParse({
    preview_id: "pprev_123",
    preview_sha256: "not-a-hash",
  });
  assert.equal(invalid.success, false);
});

// ---------------------------------------------------------------------------
// 2. Formatters
// ---------------------------------------------------------------------------

test("formatPublicationStatus returns descriptive labels", () => {
  assert.equal(formatPublicationStatus("draft").label, "Bản nháp");
  assert.equal(formatPublicationStatus("approved").label, "Đã duyệt");
  assert.equal(formatPublicationStatus("published").label, "Đang xuất bản");
  assert.equal(formatPublicationStatus("superseded").label, "Đã thay thế");
  assert.equal(formatPublicationStatus("withdrawn").label, "Đã thu hồi");
});

test("formatDecisionAction returns proper Vietnamese action texts", () => {
  assert.equal(formatDecisionAction("approve").label, "Duyệt phiên bản");
  assert.equal(formatDecisionAction("publish").label, "Xuất bản phiên bản");
  assert.equal(formatDecisionAction("withdraw").label, "Thu hồi phiên bản");
});

test("formatPublicationError handles RFC 7807 error codes properly", () => {
  assert.match(
    formatPublicationError("compiled_document_key_exists"),
    /Document key đã tồn tại/,
  );
  assert.match(
    formatPublicationError("compiled_run_registered"),
    /đã được đăng ký thành phiên bản/,
  );
  assert.match(
    formatPublicationError("publication_review_required"),
    /Cần có lượt rà soát/,
  );
  assert.match(
    formatPublicationError("publication_approval_required"),
    /phải được duyệt/,
  );
  assert.match(
    formatPublicationError("publication_preview_expired"),
    /đã hết hạn/,
  );
  assert.match(
    formatPublicationError("published_compilation_not_found"),
    /chưa có phiên bản nào đang xuất bản/,
  );
});

// ---------------------------------------------------------------------------
// 3. Permissions
// ---------------------------------------------------------------------------

test("canRegisterCompiledDocument allows admin and editor only", () => {
  assert.equal(
    canRegisterCompiledDocument({ kind: "member", role: "admin" }),
    true,
  );
  assert.equal(
    canRegisterCompiledDocument({ kind: "member", role: "editor" }),
    true,
  );
  assert.equal(
    canRegisterCompiledDocument({ kind: "member", role: "reviewer" }),
    false,
  );
  assert.equal(
    canRegisterCompiledDocument({ kind: "member", role: "member" }),
    false,
  );
  assert.equal(canRegisterCompiledDocument({ kind: "platform-admin" }), true);
  assert.equal(canRegisterCompiledDocument(null), false);
});

test("canApproveCompiledVersion allows admin and reviewer only", () => {
  assert.equal(
    canApproveCompiledVersion({ kind: "member", role: "admin" }),
    true,
  );
  assert.equal(
    canApproveCompiledVersion({ kind: "member", role: "reviewer" }),
    true,
  );
  assert.equal(
    canApproveCompiledVersion({ kind: "member", role: "editor" }),
    false,
  );
  assert.equal(
    canApproveCompiledVersion({ kind: "member", role: "member" }),
    false,
  );
  assert.equal(canApproveCompiledVersion({ kind: "platform-admin" }), true);
});

test("canPublishCompiledVersion allows admin only", () => {
  assert.equal(
    canPublishCompiledVersion({ kind: "member", role: "admin" }),
    true,
  );
  assert.equal(
    canPublishCompiledVersion({ kind: "member", role: "reviewer" }),
    false,
  );
  assert.equal(
    canPublishCompiledVersion({ kind: "member", role: "editor" }),
    false,
  );
  assert.equal(
    canPublishCompiledVersion({ kind: "member", role: "member" }),
    false,
  );
  assert.equal(canPublishCompiledVersion({ kind: "platform-admin" }), true);
});

test("canWithdrawCompiledVersion allows admin only", () => {
  assert.equal(
    canWithdrawCompiledVersion({ kind: "member", role: "admin" }),
    true,
  );
  assert.equal(
    canWithdrawCompiledVersion({ kind: "member", role: "reviewer" }),
    false,
  );
  assert.equal(
    canWithdrawCompiledVersion({ kind: "member", role: "editor" }),
    false,
  );
  assert.equal(canWithdrawCompiledVersion({ kind: "platform-admin" }), true);
});

test("canReadCompiledDocuments allows all workspace roles", () => {
  assert.equal(
    canReadCompiledDocuments({ kind: "member", role: "admin" }),
    true,
  );
  assert.equal(
    canReadCompiledDocuments({ kind: "member", role: "editor" }),
    true,
  );
  assert.equal(
    canReadCompiledDocuments({ kind: "member", role: "reviewer" }),
    true,
  );
  assert.equal(
    canReadCompiledDocuments({ kind: "member", role: "member" }),
    true,
  );
  assert.equal(canReadCompiledDocuments({ kind: "platform-admin" }), true);
  assert.equal(canReadCompiledDocuments(null), false);
});

test("generatePublicationIdempotencyKey generates key with prefix", () => {
  const key = generatePublicationIdempotencyKey("test");
  assert.match(key, /^test_[0-9a-f]{32}$/);
});

// ---------------------------------------------------------------------------
// 4. HTTP Requests Transport
// ---------------------------------------------------------------------------

test("createCompiledDocument sends Idempotency-Key and correct payload", async () => {
  const { client, requests } = mockServer((_req) => {
    return {
      status: 201,
      body: {
        document: { id: "cdoc_1", document_key: "test-doc", title: "Test Doc" },
        version: { id: "cver_1", version_no: 1, status: "draft" },
        created: true,
      },
    };
  });

  const res = await createCompiledDocument(
    client,
    "ws_1",
    "col_1",
    {
      document_key: "test-doc",
      title: "Test Doc",
      compilation_run_id: "cmp_1",
    },
    "idemp_key_123",
  );

  assert.equal(res.created, true);
  assert.equal(res.document.id, "cdoc_1");
  assert.equal(requests.length, 1);
  assert.equal(requests[0].method, "POST");
  assert.equal(
    requests[0].url,
    "https://mock.platform/platform/v1alpha1/workspaces/ws_1/collections/col_1/compiled-documents",
  );
  assert.equal(requests[0].headers["idempotency-key"], "idemp_key_123");
});

test("createCompiledVersion sends Idempotency-Key and target path", async () => {
  const { client, requests } = mockServer((_req) => {
    return {
      status: 201,
      body: {
        document: { id: "cdoc_1" },
        version: { id: "cver_2", version_no: 2, status: "draft" },
        created: true,
      },
    };
  });

  const res = await createCompiledVersion(
    client,
    "ws_1",
    "col_1",
    "cdoc_1",
    { compilation_run_id: "cmp_2" },
    "idemp_key_456",
  );

  assert.equal(res.version.version_no, 2);
  assert.equal(
    requests[0].url,
    "https://mock.platform/platform/v1alpha1/workspaces/ws_1/collections/col_1/compiled-documents/cdoc_1/versions",
  );
  assert.equal(requests[0].headers["idempotency-key"], "idemp_key_456");
});

test("commitDecision passes preview credentials and Idempotency-Key", async () => {
  const { client, requests } = mockServer((_req) => {
    return {
      status: 200,
      body: {
        id: "pdec_1",
        action: "publish",
        document_sequence: 3,
      },
    };
  });

  const res = await commitDecision(
    client,
    "ws_1",
    "col_1",
    "cdoc_1",
    "cver_1",
    {
      preview_id: "pprev_1",
      preview_sha256: "d".repeat(64),
    },
    "dec_key_789",
  );

  assert.equal(res.id, "pdec_1");
  assert.equal(res.action, "publish");
  assert.equal(
    requests[0].url,
    "https://mock.platform/platform/v1alpha1/workspaces/ws_1/collections/col_1/compiled-documents/cdoc_1/versions/cver_1/decisions",
  );
  assert.equal(requests[0].headers["idempotency-key"], "dec_key_789");
});

test("getPublishedCompiledDocument returns null on 404 published_compilation_not_found", async () => {
  const { client } = mockServer(() => {
    return {
      status: 404,
      body: {
        status: 404,
        code: "published_compilation_not_found",
        message: "Chưa có bản xuất bản",
      },
    };
  });

  const res = await getPublishedCompiledDocument(
    client,
    "ws_1",
    "col_1",
    "cdoc_1",
  );
  assert.equal(res, null);
});

test("listCompiledDocuments and getCompiledDocument transport properly", async () => {
  const { client, requests } = mockServer((req) => {
    if (req.url.endsWith("cdoc_1")) {
      return {
        status: 200,
        body: { id: "cdoc_1", document_key: "doc-1", title: "Doc 1" },
      };
    }
    return {
      status: 200,
      body: [{ id: "cdoc_1", document_key: "doc-1", title: "Doc 1" }],
    };
  });

  const list = await listCompiledDocuments(client, "ws_1", "col_1", 10, 5);
  assert.equal(list.length, 1);
  assert.match(requests[0].url, /limit=10/);
  assert.match(requests[0].url, /offset=5/);

  const doc = await getCompiledDocument(client, "ws_1", "col_1", "cdoc_1");
  assert.equal(doc.id, "cdoc_1");
});

test("createDecisionPreview, draft, review-gate and history transport properly", async () => {
  const { client, requests } = mockServer((_req) => {
    return {
      status: 200,
      body: { id: "item_1" },
    };
  });

  await createDecisionPreview(client, "ws_1", "col_1", "cdoc_1", "cver_1", {
    action: "approve",
    reason: "Reason",
  });
  assert.equal(requests[0].method, "POST");
  assert.match(requests[0].url, /decision-preview$/);

  await getCompiledVersionDraft(client, "ws_1", "col_1", "cdoc_1", "cver_1");
  assert.match(requests[1].url, /draft$/);

  await getCompiledVersionReviewGate(
    client,
    "ws_1",
    "col_1",
    "cdoc_1",
    "cver_1",
  );
  assert.match(requests[2].url, /review-gate$/);

  await getCompiledDocumentHistory(client, "ws_1", "col_1", "cdoc_1", 25, 0);
  assert.match(requests[3].url, /history\?limit=25&offset=0$/);

  await listCompiledVersions(client, "ws_1", "col_1", "cdoc_1", 20, 0);
  assert.match(requests[4].url, /versions\?limit=20&offset=0$/);

  await getCompiledVersion(client, "ws_1", "col_1", "cdoc_1", "cver_1");
  assert.match(requests[5].url, /versions\/cver_1$/);
});
