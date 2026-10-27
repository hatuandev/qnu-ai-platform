// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import {
  clearAccessToken,
  getTokenState,
  setAccessToken,
} from "@/app/api/v1/session-token";
import type { CallerWorkspaceRole } from "@/app/auth/v1/permissions";
import { EvaluationForm } from "@/features/evaluation/evaluation-form";
import { EvaluationPage } from "@/features/evaluation/evaluation-page";
import { GoldPicker } from "@/features/evaluation/gold-picker";
import type {
  EvaluationRequest,
  IndexManifest,
} from "@/features/evaluation/types";
import type { IndexRun, SearchHit } from "@/features/knowledge/index-types";
import {
  EvidenceChunk,
  SearchEvidenceResults,
  SearchEvidenceSheet,
} from "@/features/knowledge/search-evidence";
import { BackupCreate } from "@/features/operations/backup-create";
import { BackupDetails } from "@/features/operations/backup-details";
import { MaintenanceDialog } from "@/features/operations/maintenance-dialog";
import { OperationsPage } from "@/features/operations/operations-page";
import { CleanupReceipt } from "@/features/operations/storage-panel";

const env = vi.hoisted(() => ({
  role: { kind: "member", role: "admin" } as CallerWorkspaceRole,
}));
vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({ sessionId: getTokenState().sessionId }),
}));
vi.mock("@/features/workspaces/queries", () => ({
  useCallerWorkspaceRole: () => ({ role: env.role, isPending: false }),
}));
vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children, to }: { children: ReactNode; to: string }) => (
    <a href="#synthetic-679" data-route={to}>
      {children}
    </a>
  ),
}));
const response = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
type Call = { path: string; body: Record<string, unknown>; key: string | null };
const clients: QueryClient[] = [];
let posts: Call[];
let gets: string[];
let mode: "ok" | "network-once" | "stale" | "denied" | "delayed";
let previewStatus: string;
let expiresAt: string;
let fileCount: number;
let pendingResponse: Promise<Response> | null;
let published: boolean;
let mismatchedPublication: boolean;
let mismatchSearch: boolean;
let failingEvaluation: boolean;
const hash = "a".repeat(64);
const hit: SearchHit = {
  chunk_id: "chunk",
  document_id: "doc",
  version_id: "version",
  publication_decision_id: "decision",
  score: 0.1234,
  kind: "paragraph",
  text: "Biểu phí thử nghiệm\nNội dung tổng hợp để kiểm tra, không phải tài liệu thực.",
  citations: {
    "ocr:block": {
      filename: "synthetic.pdf",
      page_number: 2,
      source_id: "source",
      revision_id: "revision",
    },
  },
  structure: {
    context: { title: "Biểu phí thử nghiệm", heading: "Mục A" },
    retrieval_metadata: [{ data_year: null }],
  },
};
const manifest: IndexManifest = {
  run_id: "run",
  generation: 3,
  chunks: [{ id: "chunk", text_sha256: hash }],
  inputs: [
    {
      document_id: "doc",
      version_id: "version",
      publication_decision_id: "decision",
    },
  ],
};
const run: IndexRun = {
  id: "run",
  workspace_id: "w",
  collection_id: "c",
  generation: 3,
  status: "completed",
  is_active: true,
  provider_id: "embedding",
  dimension: 3,
  input_sha256: hash,
  requested_at: "2026-10-27T00:00:00Z",
  dispatched_at: null,
  started_at: null,
  finished_at: null,
  attempt_count: 1,
  error_code: null,
  chunks_total: 1,
  manifest_sha256: hash,
};
const backup = {
  id: "backup",
  workspace_id: "w",
  status: "completed",
  created_at: "2026-10-27T00:00:00Z",
  finished_at: null,
  retain_until: null,
  sha256: hash,
  size_bytes: null,
  error_code: null,
};
function gc(status = previewStatus) {
  return {
    id: "gc",
    status,
    preview_sha256: hash,
    expires_at: expiresAt,
    files: Array.from({ length: fileCount }, (_, i) => ({
      id: `file-${i}`,
      bytes: 1024,
      modified_at: "2026-10-20T00:00:00Z",
    })),
    total_bytes: fileCount * 1024,
    result:
      status === "completed"
        ? {
            files: [{ id: "file-0", outcome: "absent" }],
            originals_and_raw_retained: true,
          }
        : null,
  };
}
beforeEach(() => {
  setAccessToken("synthetic-679-session");
  env.role = { kind: "member", role: "admin" };
  posts = [];
  gets = [];
  mode = "ok";
  previewStatus = "preview";
  expiresAt = new Date(Date.now() + 60000).toISOString();
  fileCount = 1;
  pendingResponse = null;
  published = true;
  mismatchedPublication = false;
  mismatchSearch = false;
  failingEvaluation = false;
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  Element.prototype.scrollIntoView = vi.fn();
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = vi.fn();
  Element.prototype.releasePointerCapture = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const path = new URL(url, "http://synthetic.invalid").pathname;
      if ((init?.method ?? "GET") !== "GET") {
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        posts.push({
          path,
          body,
          key: new Headers(init?.headers).get("Idempotency-Key"),
        });
        if (mode === "delayed" && pendingResponse) return pendingResponse;
        if (path.endsWith("/storage-cleanups/previews")) return response(gc());
        if (path.endsWith("/delete-preview"))
          return response({
            id: "operation",
            kind: "backup",
            job_id: "backup",
            action: "delete_backup",
            reason: body.reason,
            preview_sha256: hash,
            status: "preview",
            expires_at: expiresAt,
            dispatched_at: null,
          });
        if (
          path.endsWith("/storage-cleanups/actions") ||
          path.endsWith("/operations/actions")
        ) {
          if (mode === "network-once") {
            mode = "ok";
            throw new TypeError("Synthetic connection lost");
          }
          if (mode === "stale")
            return response(
              { code: "storage_cleanup_stale", detail: "Bản xem trước đã cũ" },
              409,
            );
          if (mode === "denied")
            return response(
              { code: "forbidden", detail: "Không có quyền" },
              403,
            );
          return response(
            path.endsWith("/operations/actions")
              ? { id: "operation", status: "dispatched", preview_sha256: hash }
              : gc("completed"),
          );
        }
        if (path.endsWith("/backups")) {
          if (mode === "network-once") {
            mode = "ok";
            throw new TypeError("Synthetic connection lost");
          }
          return response(backup, 202);
        }
        if (path.endsWith("/search"))
          return response({
            index_run_id: mismatchSearch ? "different-run" : "run",
            generation: 3,
            status: "results",
            hits: [hit],
            eligible_documents: 1,
            skipped_documents: [],
            trace: { manifest_sha256: hash },
          });
        if (path.endsWith("/retrieval-evaluations")) {
          if (failingEvaluation)
            return response(
              {
                code: "evaluation_snapshot_mismatch",
                detail: "Snapshot thay đổi",
              },
              409,
            );
          const request = body as EvaluationRequest;
          return response({
            schema_version: "qnu.retrieval-evaluation/v1",
            id: "eval",
            ...request,
            records: request.queries.flatMap((q) =>
              ["dense", "hybrid"].map((strategy) => ({
                query_id: q.id,
                group: q.group,
                strategy,
                status: "completed",
                ranked_ids: ["chunk"],
                metrics: {
                  hit_at_k: null,
                  annotated_recall_at_k: null,
                  mrr_at_k: null,
                  annotated_precision_at_k: null,
                  empty_gold: !q.gold_chunk_ids.length,
                  retrieved_count: 1,
                  answer_correctness: null,
                  answer_groundedness: null,
                },
              })),
            ),
            summary: {
              dense: {
                expected: 1,
                completed: 1,
                errors: 0,
                completed_only_metrics: {
                  hit_at_k: null,
                  annotated_recall_at_k: null,
                  mrr_at_k: null,
                  annotated_precision_at_k: null,
                },
                acceptance: "not_determined",
              },
            },
            answer_evaluation: "NOT RUN",
            publication_approval: false,
            timing_boundary: "shared",
          });
        }
        throw new Error(`Unexpected synthetic POST ${path}`);
      }
      gets.push(path);
      if (path.endsWith("/published") && mode === "denied")
        return response(
          { code: "forbidden", detail: "Quyền đọc nguồn đã bị thu hồi" },
          403,
        );
      if (path.endsWith("/published"))
        return published
          ? response({
              document: { id: "doc" },
              version: {
                id: mismatchedPublication ? "new-version" : "version",
              },
              decision: { id: "decision" },
              content: {},
            })
          : response(
              {
                code: "published_compilation_not_found",
                detail: "Không còn bản xuất bản",
              },
              404,
            );
      if (path.endsWith("/storage-cleanups/actions/gc")) return response(gc());
      if (path.endsWith("/backups/backup/verify"))
        return mode === "denied"
          ? response(
              { code: "backup_integrity_failed", detail: "Bản sao lưu hỏng" },
              409,
            )
          : response({ verified: true, objects: 2 });
      if (path.endsWith("/backups/backup")) return response(backup);
      if (path.endsWith("/operations/backups"))
        return response({ items: [backup], total: 1, limit: 20, offset: 0 });
      if (path.endsWith("/operations/retention"))
        return response({
          original_and_raw_evidence: "keep_forever",
          backup_default: "keep_forever",
          automatic_delete: false,
          eligible_backup_ids: [],
          requires_preview_and_acceptance: true,
        });
      if (path.endsWith("/indexing-runs/run/manifest"))
        return response(manifest);
      if (path.endsWith("/indexing-runs/run")) return response(run);
      if (path.endsWith("/indexing-runs")) return response([run]);
      if (path.endsWith("/modelops/catalog"))
        return response([
          {
            id: "reranker",
            name: "Synthetic reranker",
            model_name: "synthetic",
            capabilities: ["rerank"],
            default_capabilities: [],
          },
        ]);
      throw new Error(`Unexpected synthetic GET ${path}`);
    }),
  );
});
afterEach(() => {
  cleanup();
  for (const client of clients.splice(0)) client.clear();
  clearAccessToken();
  vi.unstubAllGlobals();
});
function show(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  clients.push(client);
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}
async function preview() {
  fireEvent.change(screen.getByLabelText("Lý do"), {
    target: { value: "Dọn tệp thử không tham chiếu" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Xem trước", exact: true }),
  );
  await screen.findByLabelText("Tệp trong bản xem trước");
}
const accepts = () =>
  posts.filter(
    (c) =>
      c.path.endsWith("/storage-cleanups/actions") ||
      c.path.endsWith("/operations/actions"),
  );
test("cleanup requires valid age, concrete preview and explicit confirmation", async () => {
  show(
    <MaintenanceDialog workspaceId="w" onClose={vi.fn()} onReceipt={vi.fn()} />,
  );
  fireEvent.change(screen.getByLabelText("Lý do"), {
    target: { value: "Reason" },
  });
  fireEvent.change(screen.getByLabelText("Tuổi tệp tối thiểu (giờ)"), {
    target: { value: "23" },
  });
  fireEvent.submit(
    screen.getByLabelText("Lý do").closest("form") as HTMLFormElement,
  );
  await screen.findByRole("alert");
  expect(posts).toHaveLength(0);
  fireEvent.change(screen.getByLabelText("Tuổi tệp tối thiểu (giờ)"), {
    target: { value: "24" },
  });
  await preview();
  const confirm = screen.getByRole("button", { name: "Xác nhận xóa" });
  expect(confirm.hasAttribute("disabled")).toBe(true);
  fireEvent.click(confirm);
  expect(accepts()).toHaveLength(0);
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(confirm);
  await waitFor(() => expect(accepts()).toHaveLength(1));
  expect(accepts()[0].body).toEqual({ preview_id: "gc", preview_sha256: hash });
});
test("ambiguous cleanup retry freezes approval and reuses same hash and key", async () => {
  mode = "network-once";
  const receipt = vi.fn();
  show(
    <MaintenanceDialog workspaceId="w" onClose={vi.fn()} onReceipt={receipt} />,
  );
  await preview();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Xác nhận xóa" }));
  await screen.findByRole("alert");
  expect(
    screen
      .getByRole("button", { name: "Xem trước lại" })
      .hasAttribute("disabled"),
  ).toBe(true);
  fireEvent.click(
    screen.getByRole("button", { name: "Thử lại cùng thao tác" }),
  );
  await waitFor(() => expect(accepts()).toHaveLength(2));
  expect(accepts()[1]).toEqual(accepts()[0]);
  expect(receipt).toHaveBeenCalledWith("gc");
});
test("stale cleanup preview clears approval and demands another preview", async () => {
  mode = "stale";
  show(
    <MaintenanceDialog workspaceId="w" onClose={vi.fn()} onReceipt={vi.fn()} />,
  );
  await preview();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Xác nhận xóa" }));
  await screen.findByText("Bản xem trước đã cũ");
  expect(screen.queryByRole("button", { name: "Xác nhận xóa" })).toBeNull();
  expect(screen.getByLabelText("Lý do")).toBeTruthy();
});
test("expired preview and empty inventory cannot be accepted", async () => {
  expiresAt = new Date(Date.now() - 1000).toISOString();
  fileCount = 0;
  show(
    <MaintenanceDialog workspaceId="w" onClose={vi.fn()} onReceipt={vi.fn()} />,
  );
  fireEvent.change(screen.getByLabelText("Lý do"), {
    target: { value: "Reason" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Xem trước", exact: true }),
  );
  await screen.findByText("Không có tệp đủ điều kiện để dọn.");
  fireEvent.click(screen.getByRole("checkbox"));
  expect(
    screen
      .getByRole("button", { name: "Xác nhận xóa" })
      .hasAttribute("disabled"),
  ).toBe(true);
  expect(accepts()).toHaveLength(0);
});
test("pending cleanup resumes the previously accepted action after remount", async () => {
  previewStatus = "pending";
  show(<CleanupReceipt workspaceId="w" id="gc" />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Tiếp tục dọn đã xác nhận" }),
  );
  await screen.findByText("Đã xóa: 0 · Đã vắng trước đó: 1");
  expect(accepts()[0].key).toBe("storage-cleanup:gc");
  expect(posts.some((p) => p.path.endsWith("/previews"))).toBe(false);
});
test("backup deletion uses its protected preview and does not claim synchronous removal", async () => {
  const close = vi.fn();
  show(
    <MaintenanceDialog
      workspaceId="w"
      backupId="backup"
      onClose={close}
      onReceipt={vi.fn()}
    />,
  );
  fireEvent.change(screen.getByLabelText("Lý do"), {
    target: { value: "Expired" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Xem trước", exact: true }),
  );
  await screen.findByText("Xóa bản sao lưu: backup");
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Xác nhận xóa" }));
  await waitFor(() => expect(close).toHaveBeenCalled());
  expect(accepts()[0].key).toBe("operations:operation");
  expect(screen.queryByText("Đã xóa thành công")).toBeNull();
});
test("backup create retries reuse the original retention and key after network loss", async () => {
  mode = "network-once";
  const created = vi.fn();
  show(<BackupCreate workspaceId="w" onCreated={created} />);
  fireEvent.change(screen.getByLabelText("Giữ tối thiểu (ngày)"), {
    target: { value: "7" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Tạo bản sao lưu" }));
  await screen.findByRole("alert");
  expect(
    screen.getByLabelText("Giữ tối thiểu (ngày)").hasAttribute("disabled"),
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Thử lại cùng yêu cầu" }));
  await waitFor(() => expect(created).toHaveBeenCalledWith("backup"));
  expect(posts[1]).toEqual(posts[0]);
  expect(posts[0].body).toEqual({ retention_days: 7 });
});
test("late backup result cannot update a logged out session", async () => {
  let finish!: (r: Response) => void;
  pendingResponse = new Promise((resolve) => {
    finish = resolve;
  });
  mode = "delayed";
  const created = vi.fn();
  show(<BackupCreate workspaceId="w" onCreated={created} />);
  fireEvent.click(screen.getByRole("button", { name: "Tạo bản sao lưu" }));
  await waitFor(() => expect(posts).toHaveLength(1));
  await act(async () => {
    clearAccessToken();
    finish(response(backup));
  });
  expect(created).not.toHaveBeenCalled();
});
test("backup unknown size stays unknown and integrity failure never becomes success", async () => {
  mode = "denied";
  show(<BackupDetails workspaceId="w" id="backup" />);
  await screen.findByText(/Chưa có số đo dung lượng/);
  fireEvent.click(screen.getByRole("button", { name: "Kiểm tra toàn vẹn" }));
  await screen.findByText("Bản sao lưu hỏng");
  expect(screen.queryByText(/Đã xác minh toàn vẹn/)).toBeNull();
});
test.each(["backups", "storage"] as const)(
  "reviewer cannot mount %s queries even via a direct URL",
  async (view) => {
    env.role = { kind: "member", role: "reviewer" };
    show(
      <OperationsPage
        workspaceId="w"
        search={{
          page: 1,
          pageSize: 20,
          view,
          cleanupActionId: "gc",
          backupId: "backup",
        }}
        onSearch={vi.fn()}
      />,
    );
    await screen.findByRole("alert");
    expect(gets).toHaveLength(0);
    expect(
      screen.queryByRole("button", { name: "Sao lưu", exact: true }),
    ).toBeNull();
  },
);
test("expired backups absent from retention eligibility do not expose deletion", async () => {
  show(
    <OperationsPage
      workspaceId="w"
      search={{ page: 1, pageSize: 20, view: "backups" }}
      onSearch={vi.fn()}
    />,
  );
  await screen.findByRole("button", { name: "Xem", exact: true });
  expect(screen.queryByRole("button", { name: "Xóa hết hạn" })).toBeNull();
});
test.each(["withdrawn", "replaced"])(
  "evidence inspector hides stale content when source is %s",
  async (state) => {
    published = state !== "withdrawn";
    mismatchedPublication = state === "replaced";
    show(
      <SearchEvidenceSheet
        workspaceId="w"
        collectionId="c"
        hit={hit}
        onClose={vi.fn()}
      />,
    );
    await screen.findByText(/Nguồn đã thay đổi hoặc bị thu hồi/);
    expect(screen.queryByText(hit.text)).toBeNull();
  },
);
test("evidence inspector shows full text and exact version route after publication verification", async () => {
  show(
    <SearchEvidenceSheet
      workspaceId="w"
      collectionId="c"
      hit={hit}
      onClose={vi.fn()}
    />,
  );
  await screen.findByText(/Nội dung tổng hợp để kiểm tra/);
  expect(screen.getByText("synthetic.pdf")).toBeTruthy();
  expect(
    screen
      .getByRole("link", { name: "Mở phiên bản nguồn" })
      .getAttribute("data-route"),
  ).toContain("versions/$versionId");
  expect(screen.queryByText(/12.34%/)).toBeNull();
});
test("structured table preserves spans and unknown page without inventing page zero", () => {
  const tableHit = {
    ...hit,
    citations: {},
    structure: {
      rows: [
        [{ text: "Tên nhóm", header: true, row_span: 1, col_span: 2 }],
        [{ text: "Tổng hợp", header: false, row_span: 2, col_span: 1 }],
      ],
    },
  };
  show(<EvidenceChunk hit={tableHit} />);
  expect(
    screen
      .getByRole("columnheader", { name: "Tên nhóm" })
      .getAttribute("colspan"),
  ).toBe("2");
  expect(
    screen.getByRole("cell", { name: "Tổng hợp" }).getAttribute("rowspan"),
  ).toBe("2");
  expect(screen.getByText("Trang chưa xác định")).toBeTruthy();
});
test("search shows individual skipped reasons and rank trace without percentage claims", () => {
  show(
    <SearchEvidenceResults
      workspaceId="w"
      collectionId="c"
      result={{
        index_run_id: "run",
        generation: 3,
        status: "results",
        hits: [hit],
        eligible_documents: 1,
        skipped_documents: [
          { document_id: "skipped", reason: "not_published" },
        ],
        trace: { ranking: { dense: [{ chunk_id: "chunk", score: 0.5 }] } },
      }}
    />,
  );
  expect(screen.getByText("not_published")).toBeTruthy();
  expect(screen.getByText("0.5")).toBeTruthy();
  expect(
    screen.getByRole("button", { name: "Xem đoạn và nguồn" }),
  ).toBeTruthy();
});
test("gold picker rejects candidates from a different index snapshot", async () => {
  mismatchSearch = true;
  const change = vi.fn();
  show(
    <GoldPicker
      workspaceId="w"
      collectionId="c"
      query="Synthetic query"
      manifest={manifest}
      manifestSha={hash}
      selected={[]}
      onChange={change}
      disabled={false}
    />,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Tìm đoạn làm đáp án chuẩn" }),
  );
  await screen.findByText(/Chỉ mục đã thay đổi hoặc kết quả khác snapshot/);
  expect(screen.queryByRole("checkbox")).toBeNull();
  expect(change).not.toHaveBeenCalled();
});
function fillEvaluation() {
  fireEvent.change(screen.getByLabelText("Phiên bản bộ nhãn"), {
    target: { value: "v1" },
  });
  fireEvent.change(screen.getByLabelText("Người gán nhãn"), {
    target: { value: "Synthetic reviewer" },
  });
  fireEvent.change(screen.getByLabelText("Nội dung câu hỏi"), {
    target: { value: "Biểu phí thử nghiệm?" },
  });
}
test("evaluation takes selected readable gold IDs and the pinned hash without manual IDs", async () => {
  show(
    <EvaluationForm
      workspaceId="w"
      collectionId="c"
      run={run}
      manifest={manifest}
    />,
  );
  fillEvaluation();
  fireEvent.click(
    screen.getByRole("button", { name: "Tìm đoạn làm đáp án chuẩn" }),
  );
  const list = await screen.findByRole("list", { name: "Đoạn gợi ý" });
  fireEvent.click(within(list).getByRole("checkbox"));
  fireEvent.click(
    screen.getByRole("button", { name: "Chạy đánh giá truy xuất" }),
  );
  await screen.findByRole("region", { name: "Báo cáo đánh giá" });
  const request = posts.find((p) =>
    p.path.endsWith("retrieval-evaluations"),
  )?.body;
  expect(request).toMatchObject({
    index_run_id: "run",
    manifest_sha256: hash,
    label_status: "draft_needs_human_check",
    queries: [
      {
        query: "Biểu phí thử nghiệm?",
        gold_chunk_ids: ["chunk"],
        document_ids: null,
      },
    ],
  });
  expect(screen.getByRole("button", { name: "Xuất JSON" })).toBeTruthy();
  expect(screen.getByText(/Chưa đánh giá độ đúng/)).toBeTruthy();
});
test("evaluation budget validation blocks invalid K and retains query text", async () => {
  show(
    <EvaluationForm
      workspaceId="w"
      collectionId="c"
      run={run}
      manifest={manifest}
    />,
  );
  fillEvaluation();
  fireEvent.change(screen.getByLabelText("Số đoạn ứng viên"), {
    target: { value: "2" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Chạy đánh giá truy xuất" }),
  );
  await screen.findByRole("alert");
  expect(posts).toHaveLength(0);
  expect(
    (screen.getByLabelText("Nội dung câu hỏi") as HTMLTextAreaElement).value,
  ).toBe("Biểu phí thử nghiệm?");
});
test("snapshot conflict is an error and produces no success report", async () => {
  failingEvaluation = true;
  show(
    <EvaluationForm
      workspaceId="w"
      collectionId="c"
      run={run}
      manifest={manifest}
    />,
  );
  fillEvaluation();
  fireEvent.click(
    screen.getByRole("button", { name: "Chạy đánh giá truy xuất" }),
  );
  await screen.findByText("Snapshot thay đổi");
  expect(screen.queryByRole("region", { name: "Báo cáo đánh giá" })).toBeNull();
});
test("evaluation permits explicit empty gold but shows unmeasured quality", async () => {
  show(
    <EvaluationForm
      workspaceId="w"
      collectionId="c"
      run={run}
      manifest={manifest}
    />,
  );
  fillEvaluation();
  fireEvent.click(
    screen.getByRole("button", { name: "Chạy đánh giá truy xuất" }),
  );
  await screen.findByRole("region", { name: "Báo cáo đánh giá" });
  expect(
    screen.getAllByText("Nhãn rỗng — không tính điểm chất lượng.").length,
  ).toBe(2);
  expect(screen.getAllByText("Chưa đo").length).toBeGreaterThan(0);
});
test("evaluation caps the editable question list at twenty", () => {
  show(
    <EvaluationForm
      workspaceId="w"
      collectionId="c"
      run={run}
      manifest={manifest}
    />,
  );
  for (let i = 1; i < 20; i++)
    fireEvent.click(screen.getByRole("button", { name: "Thêm câu hỏi" }));
  expect(screen.getAllByLabelText("Nội dung câu hỏi")).toHaveLength(20);
  expect(
    screen
      .getByRole("button", { name: "Thêm câu hỏi" })
      .hasAttribute("disabled"),
  ).toBe(true);
});
test("evaluation permission is checked before snapshot or model catalog reads", () => {
  env.role = { kind: "member", role: "reviewer" };
  show(
    <EvaluationPage
      workspaceId="w"
      collectionId="c"
      page={1}
      runId="run"
      onSearch={vi.fn()}
    />,
  );
  expect(screen.getByRole("alert")).toBeTruthy();
  expect(gets).toHaveLength(0);
  expect(posts).toHaveLength(0);
});

test("human reviewed labels require explicit acknowledgement and changing a label clears it", async () => {
  show(
    <EvaluationForm
      workspaceId="w"
      collectionId="c"
      run={run}
      manifest={manifest}
    />,
  );
  fillEvaluation();
  fireEvent.keyDown(screen.getByRole("combobox", { name: "Trạng thái nhãn" }), {
    key: " ",
  });
  fireEvent.click(
    await screen.findByRole("option", { name: "Đã được người rà soát" }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Chạy đánh giá truy xuất" }),
  );
  await screen.findByText(/Cần xác nhận đã rà soát nhãn/);
  expect(posts).toHaveLength(0);
  const ack = screen.getByRole("checkbox", { name: /Tôi đã đọc nguồn/ });
  fireEvent.click(ack);
  expect(ack.getAttribute("data-state")).toBe("checked");
  fireEvent.change(screen.getByLabelText("Nhóm (tùy chọn)"), {
    target: { value: "updated group" },
  });
  expect(ack.getAttribute("data-state")).toBe("unchecked");
  fireEvent.click(ack);
  fireEvent.click(
    screen.getByRole("button", { name: "Chạy đánh giá truy xuất" }),
  );
  await screen.findByRole("region", { name: "Báo cáo đánh giá" });
  expect(
    posts.find((p) => p.path.endsWith("retrieval-evaluations"))?.body
      .label_status,
  ).toBe("human_reviewed");
});
test("rerank selection carries the catalog provider id rather than a display label", async () => {
  show(
    <EvaluationForm
      workspaceId="w"
      collectionId="c"
      run={run}
      manifest={manifest}
    />,
  );
  fillEvaluation();
  fireEvent.click(
    screen.getByRole("checkbox", { name: "Đo thêm bước xếp hạng lại" }),
  );
  fireEvent.keyDown(
    screen.getByRole("combobox", { name: "Provider xếp hạng lại" }),
    { key: " " },
  );
  fireEvent.click(
    await screen.findByRole("option", {
      name: "Synthetic reranker · synthetic",
    }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Chạy đánh giá truy xuất" }),
  );
  await screen.findByRole("region", { name: "Báo cáo đánh giá" });
  expect(
    posts.find((p) => p.path.endsWith("retrieval-evaluations"))?.body,
  ).toMatchObject({ include_rerank: true, rerank_provider_id: "reranker" });
});
test("permission failure during cleanup acceptance stays an error with no success callback", async () => {
  mode = "denied";
  const close = vi.fn();
  show(
    <MaintenanceDialog workspaceId="w" onClose={close} onReceipt={vi.fn()} />,
  );
  await preview();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Xác nhận xóa" }));
  await screen.findByText("Không có quyền");
  expect(close).not.toHaveBeenCalled();
  expect(screen.queryByText(/Đã xóa: /)).toBeNull();
});
test("permission errors in source inspection do not render cached passage", async () => {
  mode = "denied";
  show(
    <SearchEvidenceSheet
      workspaceId="w"
      collectionId="c"
      hit={hit}
      onClose={vi.fn()}
    />,
  );
  await screen.findByText("Quyền đọc nguồn đã bị thu hồi");
  expect(screen.queryByText(hit.text)).toBeNull();
});
test("late evaluation response does not install a report after logout", async () => {
  let finish!: (r: Response) => void;
  pendingResponse = new Promise((resolve) => {
    finish = resolve;
  });
  mode = "delayed";
  show(
    <EvaluationForm
      workspaceId="w"
      collectionId="c"
      run={run}
      manifest={manifest}
    />,
  );
  fillEvaluation();
  fireEvent.click(
    screen.getByRole("button", { name: "Chạy đánh giá truy xuất" }),
  );
  await waitFor(() => expect(posts).toHaveLength(1));
  await act(async () => {
    clearAccessToken();
    finish(response({ id: "late-eval", summary: {}, records: [] }));
  });
  expect(screen.queryByRole("region", { name: "Báo cáo đánh giá" })).toBeNull();
});
test("gold controls have distinct accessible IDs for the same hit across questions", async () => {
  show(
    <>
      <GoldPicker
        workspaceId="w"
        collectionId="c"
        query="one"
        manifest={manifest}
        manifestSha={hash}
        selected={[]}
        onChange={vi.fn()}
        disabled={false}
      />
      <GoldPicker
        workspaceId="w"
        collectionId="c"
        query="two"
        manifest={manifest}
        manifestSha={hash}
        selected={[]}
        onChange={vi.fn()}
        disabled={false}
      />
    </>,
  );
  for (const button of screen.getAllByRole("button", {
    name: "Tìm đoạn làm đáp án chuẩn",
  }))
    fireEvent.click(button);
  await waitFor(() => expect(screen.getAllByRole("checkbox")).toHaveLength(2));
  const ids = screen.getAllByRole("checkbox").map((c) => c.id);
  expect(new Set(ids).size).toBe(2);
});
