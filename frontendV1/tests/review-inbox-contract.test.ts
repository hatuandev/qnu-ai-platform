import { describe, expect, test, vi } from "vitest";
import { inboxPaths, reviewSubmissionPaths } from "../src/app/api/v1/endpoints";
import { listInbox } from "../src/features/inbox/inbox-requests";
import {
  formatAllowedRoles,
  INBOX_KINDS,
  inboxTarget,
} from "../src/features/inbox/inbox-schemas";
import type { InboxItem } from "../src/features/inbox/inbox-types";
import {
  commitSubmission,
  listSubmissions,
} from "../src/features/knowledge/review-requests";
import {
  canCancelSubmission,
  canRequestSubmissionChanges,
  canSubmitForReview,
  formatReviewSubmissionError,
  isOpenSubmissionStatus,
  isSubmittableVersionStatus,
  submissionStatusLabel,
  submissionStatusVariant,
} from "../src/features/knowledge/review-schemas";

const WORKSPACE = "ws_demo";
const COLLECTION = "col_demo";

const EDITOR = { kind: "member", role: "editor" } as const;
const REVIEWER = { kind: "member", role: "reviewer" } as const;
const ADMIN = { kind: "member", role: "admin" } as const;
const PLAIN_MEMBER = { kind: "member", role: "member" } as const;
const PLATFORM_ADMIN = { kind: "platform-admin" } as const;

function fakeClient() {
  return {
    get: vi.fn().mockResolvedValue({ items: [], meta: {}, counts: {} }),
    post: vi.fn().mockResolvedValue({}),
  };
}

function inboxItem(overrides: Partial<InboxItem>): InboxItem {
  return {
    id: "review_pending:sub_1",
    kind: "review_pending",
    title: "Quy chế đào tạo",
    problem: "Chờ người duyệt",
    detail: "Bản đã chuẩn bị từ nguồn mới nhất",
    occurred_at: "2026-11-08T02:00:00Z",
    collection_id: COLLECTION,
    collection_name: "Văn bản học vụ",
    document_id: "doc_1",
    version_id: "ver_1",
    submission_id: "sub_1",
    source_id: null,
    allowed_roles: ["admin", "reviewer"],
    deep_path: `/workspaces/${WORKSPACE}/collections/${COLLECTION}/documents/doc_1/versions/ver_1`,
    ...overrides,
  };
}

describe("review handoff request contract", () => {
  test("paths stay scoped to the collection", () => {
    expect(reviewSubmissionPaths.submissions(WORKSPACE, COLLECTION)).toBe(
      `/workspaces/${WORKSPACE}/collections/${COLLECTION}/review-submissions`,
    );
    expect(reviewSubmissionPaths.previews(WORKSPACE, COLLECTION)).toBe(
      `/workspaces/${WORKSPACE}/collections/${COLLECTION}/review-submissions/previews`,
    );
    expect(
      reviewSubmissionPaths.submission(WORKSPACE, COLLECTION, "sub_1"),
    ).toBe(
      `/workspaces/${WORKSPACE}/collections/${COLLECTION}/review-submissions/sub_1`,
    );
    expect(inboxPaths.inbox(WORKSPACE)).toBe(`/workspaces/${WORKSPACE}/inbox`);
  });

  test("commit sends the preview and the idempotency key", async () => {
    const client = fakeClient();
    await commitSubmission(
      client as never,
      WORKSPACE,
      COLLECTION,
      { preview_id: "rprev_1", preview_sha256: "sha-preview" },
      "submission-key",
    );

    expect(client.post).toHaveBeenCalledWith(
      reviewSubmissionPaths.submissions(WORKSPACE, COLLECTION),
      { preview_id: "rprev_1", preview_sha256: "sha-preview" },
      expect.objectContaining({ idempotencyKey: "submission-key" }),
    );
  });

  test("list maps paging to the server page_size field", async () => {
    const client = fakeClient();
    await listSubmissions(client as never, WORKSPACE, COLLECTION, {
      document_id: "doc_1",
      version_id: "ver_1",
      page: 2,
      pageSize: 50,
    });

    expect(client.get).toHaveBeenCalledWith(
      reviewSubmissionPaths.submissions(WORKSPACE, COLLECTION),
      {
        searchParams: {
          status: undefined,
          document_id: "doc_1",
          version_id: "ver_1",
          page: 2,
          page_size: 50,
        },
        signal: undefined,
      },
    );
  });

  test("inbox list keeps filters and paging on the query string", async () => {
    const client = fakeClient();
    await listInbox(client as never, WORKSPACE, {
      kind: "review_pending",
      collectionId: COLLECTION,
      page: 3,
      pageSize: 10,
    });

    expect(client.get).toHaveBeenCalledWith(inboxPaths.inbox(WORKSPACE), {
      searchParams: {
        kind: "review_pending",
        collection_id: COLLECTION,
        page: 3,
        page_size: 10,
      },
      signal: undefined,
    });
  });
});

describe("review handoff capabilities", () => {
  test("editors and admins submit; reviewers do not need editor rights", () => {
    expect(canSubmitForReview(EDITOR)).toBe(true);
    expect(canSubmitForReview(ADMIN)).toBe(true);
    expect(canSubmitForReview(PLATFORM_ADMIN)).toBe(true);
    expect(canSubmitForReview(REVIEWER)).toBe(false);
    expect(canSubmitForReview(PLAIN_MEMBER)).toBe(false);
    expect(canSubmitForReview(null)).toBe(false);

    expect(canRequestSubmissionChanges(REVIEWER)).toBe(true);
    expect(canRequestSubmissionChanges(ADMIN)).toBe(true);
    expect(canRequestSubmissionChanges(EDITOR)).toBe(false);
    expect(canRequestSubmissionChanges(PLAIN_MEMBER)).toBe(false);
  });

  test("only the submitter or an admin withdraws an open request", () => {
    const base = { role: EDITOR, actorRef: "actor-editor" };
    expect(canCancelSubmission({ ...base, submittedBy: "actor-editor" })).toBe(
      true,
    );
    expect(canCancelSubmission({ ...base, submittedBy: "actor-other" })).toBe(
      false,
    );
    expect(
      canCancelSubmission({
        role: ADMIN,
        actorRef: "actor-admin",
        submittedBy: "actor-other",
      }),
    ).toBe(true);
    expect(
      canCancelSubmission({
        role: PLAIN_MEMBER,
        actorRef: "actor-member",
        submittedBy: "actor-editor",
      }),
    ).toBe(false);
    expect(
      canCancelSubmission({ role: EDITOR, actorRef: null, submittedBy: null }),
    ).toBe(false);
  });

  test("submission status labels never imply publication", () => {
    expect(isSubmittableVersionStatus("draft")).toBe(true);
    expect(isSubmittableVersionStatus("superseded")).toBe(true);
    expect(isSubmittableVersionStatus("withdrawn")).toBe(true);
    expect(isSubmittableVersionStatus("approved")).toBe(false);
    expect(isSubmittableVersionStatus("published")).toBe(false);

    expect(isOpenSubmissionStatus("pending")).toBe(true);
    expect(isOpenSubmissionStatus("changes_requested")).toBe(true);
    expect(isOpenSubmissionStatus("resolved")).toBe(false);
    expect(isOpenSubmissionStatus("cancelled")).toBe(false);

    expect(submissionStatusLabel("pending")).toBe("Chờ người duyệt");
    expect(submissionStatusLabel("changes_requested")).toBe("Đã yêu cầu sửa");
    expect(submissionStatusLabel("resolved")).toBe("Đã xử lý");
    expect(submissionStatusLabel("cancelled")).toBe("Đã rút");
    expect(submissionStatusVariant("pending")).toBe("info");
    expect(submissionStatusVariant("changes_requested")).toBe("warning");
  });

  test("server error codes map to actionable Vietnamese messages", () => {
    expect(
      formatReviewSubmissionError("review_submission_duplicate"),
    ).toContain("đã được gửi duyệt");
    expect(
      formatReviewSubmissionError("review_submission_changes_required"),
    ).toContain("chuẩn bị phiên bản mới");
    expect(formatReviewSubmissionError("review_preview_expired")).toContain(
      "hết hạn",
    );
    expect(formatReviewSubmissionError("unknown_code", "Lỗi gốc")).toBe(
      "Lỗi gốc",
    );
  });
});

describe("inbox projection", () => {
  test("kind order covers every server category", () => {
    expect([...INBOX_KINDS]).toEqual([
      "review_pending",
      "changes_requested",
      "awaiting_publish",
      "preparation_failed",
      "sync_incomplete",
    ]);
  });

  test("allowed group reads as a neutral queue when no owner is assigned", () => {
    expect(formatAllowedRoles([])).toBe("Chờ người duyệt");
    expect(formatAllowedRoles(["admin", "reviewer"])).toBe(
      "Quản trị đơn vị, Người duyệt",
    );
    expect(formatAllowedRoles(["auditor"])).toBe("auditor");
  });

  test("deep links use typed routes for versions, sources and sync", () => {
    expect(inboxTarget(WORKSPACE, inboxItem({}))).toEqual({
      to: "/workspaces/$workspaceId/collections/$collectionId/documents/$documentId/versions/$versionId",
      params: {
        workspaceId: WORKSPACE,
        collectionId: COLLECTION,
        documentId: "doc_1",
        versionId: "ver_1",
      },
    });

    expect(
      inboxTarget(
        WORKSPACE,
        inboxItem({
          kind: "preparation_failed",
          document_id: null,
          version_id: null,
          submission_id: null,
          source_id: "src_1",
        }),
      ),
    ).toEqual({
      to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
      params: {
        workspaceId: WORKSPACE,
        collectionId: COLLECTION,
        sourceId: "src_1",
      },
    });

    expect(
      inboxTarget(
        WORKSPACE,
        inboxItem({
          kind: "sync_incomplete",
          document_id: null,
          version_id: null,
          submission_id: null,
          source_id: null,
        }),
      ),
    ).toEqual({
      to: "/workspaces/$workspaceId/knowledge/$knowledgeId",
      params: { workspaceId: WORKSPACE, knowledgeId: COLLECTION },
      search: { page: 1, pageSize: 20, stage: "serving" },
    });
  });
});
