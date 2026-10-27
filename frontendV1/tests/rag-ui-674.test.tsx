// @vitest-environment jsdom
/**
 * UI regressions for the Context674 hand-off: cancelled turns (F4), publication
 * read failures (F3), verification presentation (G3) and the metadata
 * acknowledgement required by the approval gate (G2).
 */

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ChatMessageItem } from "@/features/conversations/chat-message-item";
import { CompiledDocumentDetailPage } from "@/features/knowledge/compiled-document-detail-page";
import { ReviewGateDialog } from "@/features/knowledge/review-gate-dialog";
import type { RetrievalAnnotation } from "@/features/rag/types";

const previewMutateAsync = vi.hoisted(() => vi.fn());
const reviewGateRefetch = vi.hoisted(() => vi.fn());

// Stable references: react-query keeps `data` identity between renders, and the
// dialog resets its form in an effect keyed on that data.
const reviewGateData = {
  review_id: "review_fixture",
  report_sha256: "b".repeat(64),
  bundle_sha256: "c".repeat(64),
  verdict: "no_issues_detected" as const,
  findings: [] as never[],
};
const reviewGateQueryResult = {
  isLoading: false,
  isError: false,
  refetch: reviewGateRefetch,
  data: reviewGateData,
};
const compiledDocumentQueryResult = {
  isPending: false,
  isError: false,
  data: {
    id: "doc",
    title: "Synthetic document",
    document_key: "doc",
    change_sequence: 1,
    created_by: "synthetic-user",
    created_at: "2026-10-27T00:00:00Z",
  },
};
const emptyListResult = { data: [], isLoading: false, isError: false };
const failedPublishedQueryResult = {
  data: undefined,
  isLoading: false,
  isError: true,
  error: {
    status: 503,
    code: "storage_unavailable",
    message: "Synthetic unavailable storage",
  },
};
const previewMutationResult = {
  isPending: false,
  mutateAsync: previewMutateAsync,
};

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    className,
  }: {
    children: React.ReactNode;
    className?: string;
  }) => (
    <a href="#review-fixture" className={className}>
      {children}
    </a>
  ),
}));

vi.mock("@/features/workspaces/queries", () => ({
  useCallerWorkspaceRole: () => ({ role: "admin", isPending: false }),
}));

vi.mock("@/features/knowledge/queries", () => ({
  useCollectionQuery: () => ({ data: { name: "Synthetic collection" } }),
}));

vi.mock("@/features/knowledge/publication-queries", () => ({
  useCompiledDocumentQuery: () => compiledDocumentQueryResult,
  useCompiledVersionsQuery: () => emptyListResult,
  useCompiledDocumentHistoryQuery: () => emptyListResult,
  usePublishedCompiledDocumentQuery: () => failedPublishedQueryResult,
  useCompiledVersionReviewGateQuery: () => reviewGateQueryResult,
  useDecisionPreviewMutation: () => previewMutationResult,
}));

beforeEach(() => {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  previewMutateAsync.mockReset();
  reviewGateRefetch.mockReset();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const baseTurn = {
  id: "synthetic-turn",
  turn_no: 1,
  question: "Câu hỏi thử",
  created_at: "2026-10-27T00:00:00Z",
  finished_at: "2026-10-27T00:00:01Z",
  status: "completed",
  source_status: "current",
  error_code: null,
};

test("F4: a cancelled turn explains the cancellation instead of showing an empty answer", () => {
  render(
    <ChatMessageItem
      turn={
        {
          ...baseTurn,
          status: "cancelled",
          result: null,
          error_code: "operation_cancelled",
        } as never
      }
      onOpenCitation={vi.fn()}
    />,
  );

  expect(screen.queryByText(/đã bị hủy/i)).not.toBeNull();
  // A cancelled turn must not offer "retry with the same key" as if it failed.
  expect(screen.queryByText(/Thử lại với cùng khóa/i)).toBeNull();
});

test("G3: observe-mode unsupported findings stay visible next to the answer", () => {
  render(
    <ChatMessageItem
      turn={
        {
          ...baseTurn,
          result: {
            id: "answer",
            status: "answered",
            statements: [
              {
                text: "Nội dung chưa được nguồn hỗ trợ.",
                evidence_ids: ["E1"],
              },
            ],
            sources: [{ evidence_id: "E1" }],
            trace: {
              verification: {
                mode: "observe",
                status: "unsupported",
                findings: [
                  {
                    statement_index: 0,
                    status: "unsupported",
                    reason: "Không có căn cứ.",
                  },
                ],
              },
            },
          },
        } as never
      }
      onOpenCitation={vi.fn()}
    />,
  );

  expect(screen.getByText("Nội dung chưa được nguồn hỗ trợ.")).toBeTruthy();
  expect(screen.queryByRole("alert")).not.toBeNull();
  expect(screen.queryByText("Không có căn cứ.")).not.toBeNull();
});

test("G3: an enforce-blocked turn reports the verification cause, not a connection error", () => {
  render(
    <ChatMessageItem
      turn={
        {
          ...baseTurn,
          result: {
            id: "answer",
            status: "insufficient_evidence",
            reason: "answer_not_supported",
            statements: [],
            sources: [{ evidence_id: "E1" }],
            trace: {
              verification: {
                mode: "enforce",
                status: "unsupported",
                findings: [
                  {
                    statement_index: 0,
                    status: "unsupported",
                    reason: "Câu 1 không có trích đoạn tương ứng.",
                    quotes: [{ evidence_id: "E1", quote: "Trích đoạn nguồn" }],
                  },
                ],
              },
            },
          },
        } as never
      }
      onOpenCitation={vi.fn()}
    />,
  );

  expect(screen.queryByText("Câu trả lời không được phát hành")).not.toBeNull();
  expect(
    screen.queryByText(/không được nguồn trích dẫn hỗ trợ/i),
  ).not.toBeNull();
  // The blocked state names itself a verification result and must not be
  // presented as a transport failure.
  expect(
    screen.queryAllByText(/Đây là kết quả kiểm chứng, không phải lỗi kết nối/i)
      .length,
  ).toBeGreaterThan(0);
  expect(screen.queryByText(/Không kết nối được/i)).toBeNull();
  expect(screen.queryByText(/Không nhận được phản hồi từ máy chủ/i)).toBeNull();
});

test("G3: a supported verdict is described as an automatic check, not a guarantee", () => {
  render(
    <ChatMessageItem
      turn={
        {
          ...baseTurn,
          result: {
            id: "answer",
            status: "answered",
            statements: [{ text: "Câu trả lời.", evidence_ids: ["E1"] }],
            sources: [{ evidence_id: "E1" }],
            trace: {
              verification: {
                mode: "observe",
                status: "supported",
                // Judge usage missing on purpose: unknown must stay unknown.
                findings: [
                  { statement_index: 0, status: "supported", reason: "ok" },
                ],
              },
            },
          },
        } as never
      }
      onOpenCitation={vi.fn()}
    />,
  );

  expect(screen.queryByText(/không phải bảo đảm tuyệt đối/i)).not.toBeNull();
  // Missing judge usage is unknown, never a measured 0.
  expect(screen.queryByText(/Token kiểm chứng: 0/)).toBeNull();
  expect(screen.queryByText(/Token kiểm chứng: không rõ/)).not.toBeNull();
});

test("F3: a failed publication fetch must not claim the document has no publication", () => {
  render(
    <CompiledDocumentDetailPage
      workspaceId="w"
      collectionId="c"
      documentId="doc"
    />,
  );

  expect(
    screen.queryByText(/Tài liệu chưa có phiên bản nào đang xuất bản/),
  ).toBeNull();
  expect(
    screen.queryByText(/Không đọc được trạng thái xuất bản/i),
  ).not.toBeNull();
});

const annotation: RetrievalAnnotation = {
  target: "paragraph:0:1",
  values: { data_year: 2026, program: "Kỹ thuật phần mềm" },
  evidence: [
    {
      citation: "run_1:ev_9",
      quote: "Năm 2026, ngành Kỹ thuật phần mềm",
    },
  ],
};
const METADATA_SHA = "d".repeat(64);

function renderReviewGate() {
  return render(
    <ReviewGateDialog
      workspaceId="w"
      collectionId="c"
      documentId="d"
      versionId="v"
      versionNo={1}
      retrievalMetadata={[annotation]}
      retrievalMetadataSha256={METADATA_SHA}
      isOpen
      onClose={() => {}}
      onPreviewSuccess={() => {}}
    />,
  );
}

test("G2: approving a version with metadata is blocked until the metadata is acknowledged", async () => {
  previewMutateAsync.mockResolvedValue({ id: "preview_1" });
  renderReviewGate();

  // The evidence behind every declared value is on screen for review.
  expect(
    screen.queryByText("Năm 2026, ngành Kỹ thuật phần mềm"),
  ).not.toBeNull();
  expect(screen.queryByText(/paragraph:0:1/)).not.toBeNull();

  fireEvent.change(screen.getByLabelText(/Lý do quyết định duyệt/i), {
    target: { value: "Đã đối chiếu báo cáo rà soát và metadata." },
  });
  fireEvent.click(
    screen.getByRole("checkbox", {
      name: /báo cáo rà soát của phiên bản này/i,
    }),
  );

  const submit = screen.getByRole("button", { name: /Xem trước duyệt/i });
  // Report acknowledged, metadata still not: the gate must stay closed.
  expect((submit as HTMLButtonElement).disabled).toBe(true);
  expect(previewMutateAsync).not.toHaveBeenCalled();

  fireEvent.click(
    screen.getByRole("checkbox", { name: /metadata truy xuất cùng căn cứ/i }),
  );

  await waitFor(() =>
    expect((submit as HTMLButtonElement).disabled).toBe(false),
  );

  fireEvent.click(submit);

  await waitFor(() => expect(previewMutateAsync).toHaveBeenCalledTimes(1));
  const payload = previewMutateAsync.mock.calls[0][0];
  expect(payload.input.review_ack.confirmed_reviewed).toBe(true);
  // The digest is the backend's; the reviewer never types or copies it.
  expect(payload.input.review_ack.retrieval_metadata_sha256).toBe(METADATA_SHA);
});
