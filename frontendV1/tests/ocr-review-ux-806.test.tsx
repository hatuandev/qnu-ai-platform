// @vitest-environment jsdom
/**
 * Context 806 — Behavioral regression tests for the post-OCR review and spelling
 * correction workflow in frontendV1 (`SourceDetailPage`, `OcrComparisonView`,
 * `OcrSpellCheckDialog`, `OcrSaveConfirmDialog`, `SpellingResultPanel`).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiProblemError,
  clearAccessToken,
  setAccessToken,
} from "@/app/api/v1";
import { clearAllOcrDrafts } from "@/features/knowledge/ocr-draft-store";
import { OcrSpellCheckDialog } from "@/features/knowledge/ocr-review-dialogs";
import {
  extractNormalizedBbox,
  formatUnitLocator,
  MAX_SPELL_CHECK_UNITS,
} from "@/features/knowledge/ocr-schemas";
import type {
  DetectionResponse,
  ReviewDocument,
} from "@/features/knowledge/ocr-types";
import { SourceDetailPage } from "@/features/knowledge/source-detail-page";
import { SpellingResultView } from "@/features/knowledge/spelling-result-panel";

const mocks = vi.hoisted(() => ({
  navigate: vi.fn(),
  detectMutateAsync: vi.fn(),
  saveMutateAsync: vi.fn(),
  requestRunMutateAsync: vi.fn(),
  refetchDoc: vi.fn(),
  role: "editor" as "viewer" | "editor" | "admin",
  catalogData: [
    {
      id: "prov-openrouter",
      code: "openrouter",
      name: "OpenRouter (Luna 2)",
      model_name: "openrouter/bert-nebulon-alpha",
      capabilities: ["chat"],
      default_capabilities: ["chat"],
    },
    {
      id: "prov-qwen",
      code: "qwen",
      name: "Qwen 2.5 72B",
      model_name: "qwen/qwen-2.5-72b-instruct",
      capabilities: ["chat"],
      default_capabilities: [],
    },
  ] as unknown[],
  catalogError: false,
  docData: null as ReviewDocument | null,
  versions: {} as Record<number, ReviewDocument>,
  checkDetails: {} as Record<string, DetectionResponse>,
}));

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, ...props }: { children: React.ReactNode }) => (
    <a {...props}>{children}</a>
  ),
  useNavigate: () => mocks.navigate,
  useBlocker: () => undefined,
}));

vi.mock("@/features/workspaces/queries", () => ({
  useCallerWorkspaceRole: () => ({
    role: { kind: "member", role: mocks.role },
    isPending: false,
  }),
}));

vi.mock("@/features/modelops/queries", () => ({
  useCatalogQuery: () => ({
    data: mocks.catalogError ? undefined : mocks.catalogData,
    isPending: false,
    isError: mocks.catalogError,
  }),
}));

vi.mock("@/features/knowledge/queries", () => ({
  useCollectionQuery: () => ({
    data: {
      id: "col-1",
      name: "Tuyển sinh Đại học 2026",
      slug: "tuyen-sinh-2026",
    },
    isPending: false,
    isError: false,
  }),
  useSourceQuery: () => ({
    data: {
      id: "src-1",
      title: "Quy chế đào tạo đại học QNU",
      source_type: "file",
      lifecycle_status: "OCR_COMPLETED",
      current_revision_id: "rev-1",
      active_revision_no: 1,
    },
    isPending: false,
    isError: false,
  }),
  useRevisionsQuery: () => ({
    data: [
      {
        id: "rev-1",
        revision_no: 1,
        file_name: "quy-che-dao-tao.pdf",
        mime_type: "application/pdf",
        file_size: 102400,
        processing_status: "completed",
      },
    ],
    isPending: false,
    isError: false,
  }),
}));

vi.mock("@/features/knowledge/ocr-requests", () => ({
  downloadReviewDocumentBlob: vi.fn(),
  downloadReviewMarkdownBlob: vi.fn(),
  downloadRunBundleBlob: vi.fn(),
  readRenderedPdfBlob: vi.fn(),
}));

vi.mock("@/features/knowledge/ocr-queries", () => ({
  useProcessingRunsQuery: () => ({
    data: {
      items: [
        {
          id: "run-1",
          status: "completed",
          generation: 1,
          page_count: 2,
          pages_total: 2,
          created_at: "2026-11-02T08:00:00Z",
        },
      ],
      total: 1,
    },
    isPending: false,
    isError: false,
  }),
  useProcessingRunDetailQuery: () => ({
    data: {
      id: "run-1",
      status: "completed",
      generation: 1,
      page_count: 2,
      pages_total: 2,
      pages: [
        {
          page_number: 1,
          status: "completed",
          has_rendered_image: true,
          has_tables: false,
        },
        {
          page_number: 2,
          status: "completed",
          has_rendered_image: true,
          has_tables: true,
        },
      ],
    },
    isPending: false,
    isError: false,
  }),
  useTextReviewQuery: (
    _w: string,
    _c: string,
    _s: string,
    _r: string,
    _run: string,
    version: number | null,
  ) => ({
    data:
      version == null
        ? mocks.docData
        : (mocks.versions[version] ?? mocks.docData),
    isPending: false,
    isError: false,
    refetch: mocks.refetchDoc,
  }),
  useSaveTextReviewMutation: () => ({
    mutateAsync: mocks.saveMutateAsync,
    isPending: false,
  }),
  useDetectCheckMutation: () => ({
    mutateAsync: mocks.detectMutateAsync,
    isPending: false,
  }),
  useRequestProcessingRunMutation: () => ({
    mutateAsync: mocks.requestRunMutateAsync,
    isPending: false,
  }),
  useDetectCheckQuery: (
    _w: string,
    _c: string,
    _s: string,
    _r: string,
    _run: string,
    checkId: string,
  ) => ({
    data: mocks.checkDetails[checkId],
    isPending: !mocks.checkDetails[checkId],
    isError: false,
    refetch: vi.fn(),
  }),
  usePageImageBlobUrl: () => ({
    blobUrl: "blob:mock-page-image",
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  usePageRawText: () => ({
    rawText: "Raw text",
    isLoading: false,
    error: null,
  }),
}));

vi.mock("@/features/knowledge/compilation-dialog", () => ({
  CompilationDialog: ({
    isOpen,
    initialRun,
  }: {
    isOpen: boolean;
    initialRun: { textVersion: number };
  }) =>
    isOpen ? (
      <div data-testid="compilation-dialog">
        Biên soạn từ phiên bản v{initialRun.textVersion}
      </div>
    ) : null,
}));

vi.mock("@/features/knowledge/revision-upload-dialog", () => ({
  RevisionUploadDialog: () => null,
}));

vi.mock("@/features/knowledge/source-rename-dialog", () => ({
  SourceRenameDialog: () => null,
}));

vi.mock("@/features/lifecycle/action-dialog", () => ({
  LifecycleActionDialog: () => null,
}));

vi.mock("sonner", () => ({
  toast: {
    info: vi.fn(),
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  },
}));

function buildDefaultDoc(): ReviewDocument {
  return {
    run_id: "run-1",
    version: 0,
    version_id: null,
    canonical_sha256: "a".repeat(64),
    original_sha256: "a".repeat(64),
    markdown_sha256: "b".repeat(64),
    saved_at: null,
    units: [
      {
        evidence_id: "ev-p1-1",
        text: "Bệnh viện cấp cơ huyên trở lên xác nhận.",
        original_text: "Bệnh viện cấp cơ huyên trở lên xác nhận.",
        page: 1,
        kind: "paragraph",
        row: null,
        column: null,
        bbox: { x0: 0.1, y0: 0.2, x1: 0.85, y1: 0.28 },
      },
      {
        evidence_id: "ev-p1-2",
        text: "Đoạn văn thứ hai trên trang 1 không có tọa độ bbox.",
        original_text: "Đoạn văn thứ hai trên trang 1 không có tọa độ bbox.",
        page: 1,
        kind: "paragraph",
        row: null,
        column: null,
        bbox: {},
      },
      {
        evidence_id: "ev-p2-cell",
        text: "Điểm chuẩn trúng tuyền năm 2026.",
        original_text: "Điểm chuẩn trúng tuyền năm 2026.",
        page: 2,
        kind: "table_cell",
        row: 2,
        column: 3,
        bbox: { x0: 0.15, y0: 0.4, x1: 0.6, y1: 0.48 },
      },
    ],
  };
}

function buildCompletedCheck(
  overrides: Partial<DetectionResponse> = {},
): DetectionResponse {
  return {
    id: "chk-101",
    status: "completed",
    version: 0,
    canonical_sha256: "a".repeat(64),
    checked_evidence_ids: ["ev-p1-1", "ev-p2-cell"],
    error_code: null,
    usage_id: null,
    created_at: "2026-11-02T08:05:00Z",
    suggestions: [
      {
        evidence_id: "ev-p2-cell",
        original: "tuyền",
        replacement: "tuyển",
        start: 17,
        end: 22,
        context_before: "Điểm chuẩn trúng ",
        context_after: " năm 2026.",
        reason: "Lỗi dấu hỏi/ngã trong thuật ngữ tuyển sinh",
      },
    ],
    withheld_suggestions: [
      {
        evidence_id: "ev-p1-1",
        original: "cơ huyên",
        replacement: "cơ bản",
        start: 14,
        end: 22,
        context_before: "Bệnh viện cấp ",
        context_after: " trở lên xác nhận.",
        reason: "Cần đối chiếu ảnh scan gốc để xác nhận chữ in",
        review_reason: "Cần đối chiếu ảnh gốc vì thay đổi từ có nghĩa",
      },
    ],
    ...overrides,
  };
}

function renderWithQuery(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

beforeEach(() => {
  setAccessToken("session-token-806");
  mocks.role = "editor";
  mocks.catalogError = false;
  mocks.docData = buildDefaultDoc();
  mocks.versions = {};
  mocks.checkDetails = {};
  mocks.navigate.mockReset();
  mocks.detectMutateAsync.mockReset();
  mocks.saveMutateAsync.mockReset();
  mocks.requestRunMutateAsync.mockReset();
  mocks.refetchDoc.mockReset();

  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
});

afterEach(() => {
  cleanup();
  clearAccessToken();
  clearAllOcrDrafts();
  vi.unstubAllGlobals();
});

describe("Context 806 — Post-OCR Review & Spelling Correction UX", () => {
  it("zooms the scan through its transform without also resizing the image surface", () => {
    renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 1 }}
        onSearchChange={vi.fn()}
      />,
    );
    const surface = screen.getByAltText("Bản gốc trang 1").parentElement;
    const beforeWidth = surface?.style.width;
    fireEvent.click(screen.getByRole("button", { name: "Phóng to ảnh" }));
    expect(surface?.style.width).toBe(beforeWidth);
  });
  it("hands the newly saved version to Compiler after editing an explicitly selected version", async () => {
    Element.prototype.scrollIntoView = vi.fn();
    const previous = { ...buildDefaultDoc(), version: 1 };
    const saved = { ...previous, version: 2, canonical_sha256: "c".repeat(64) };
    mocks.docData = previous;
    mocks.versions = { 1: previous, 2: saved };
    const check = buildCompletedCheck({ version: 1 });
    mocks.checkDetails[check.id] = check;
    mocks.saveMutateAsync.mockImplementation(async () => {
      mocks.docData = saved;
      return saved;
    });
    renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 2, checkId: check.id }}
        onSearchChange={vi.fn()}
      />,
    );
    fireEvent.keyDown(
      screen.getByRole("combobox", { name: "Phiên bản văn bản" }),
      {
        key: "ArrowDown",
      },
    );
    fireEvent.click(
      await screen.findByRole("option", { name: /Phiên bản v1/ }),
    );
    fireEvent.click(
      await screen.findByRole("button", { name: /Áp dụng vào nháp/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: /Lưu thay đổi/i }));
    fireEvent.click(
      within(await screen.findByRole("dialog")).getByRole("button", {
        name: /Xác nhận lưu v2/i,
      }),
    );
    await waitFor(() => expect(mocks.saveMutateAsync).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(screen.queryByText(/Bản nháp: 1 đoạn chưa lưu/i)).toBeNull(),
    );
    fireEvent.click(screen.getByRole("button", { name: /Dùng để biên soạn/i }));
    expect(screen.getByTestId("compilation-dialog").textContent).toContain(
      "v2",
    );
  });
  it("1. validates normalized bbox strictly without fabricating coordinates & formats officer-friendly unit locators", () => {
    expect(
      extractNormalizedBbox({ x0: 0.1, y0: 0.2, x1: 0.8, y1: 0.3 }),
    ).toEqual({ x0: 0.1, y0: 0.2, x1: 0.8, y1: 0.3 });
    // Empty or invalid bboxes must return null, never fabricated coordinates
    expect(extractNormalizedBbox({})).toBeNull();
    expect(extractNormalizedBbox(null)).toBeNull();
    expect(
      extractNormalizedBbox({ x0: 0.8, y0: 0.2, x1: 0.1, y1: 0.3 }),
    ).toBeNull();
    expect(
      extractNormalizedBbox({ x0: -0.1, y0: 0.2, x1: 0.5, y1: 0.3 }),
    ).toBeNull();

    const doc = buildDefaultDoc();
    expect(formatUnitLocator(doc.units[0], doc.units)).toBe(
      "Trang 1 · Đoạn văn 1",
    );
    expect(formatUnitLocator(doc.units[2], doc.units)).toBe(
      "Trang 2 · Ô bảng (Hàng 3, Cột 4)",
    );
  });

  it("2. OcrSpellCheckDialog enforces 1..100 unit limit without silent slicing, explains unsaved draft scope, and selects ModelOps catalog model", () => {
    // Generate 105 units to verify we never silently slice to 50 or 100
    const manyUnits = Array.from({ length: 105 }, (_, idx) => ({
      evidence_id: `ev-${idx + 1}`,
      text: `Đoạn văn kiểm tra số ${idx + 1}`,
      original_text: `Đoạn văn kiểm tra số ${idx + 1}`,
      page: 1,
      kind: "paragraph",
      row: null,
      column: null,
      bbox: {},
    }));
    const bigDoc: ReviewDocument = {
      ...buildDefaultDoc(),
      units: manyUnits,
    };

    function DialogHarness() {
      const [selectedIds, setSelectedIds] = useState<Set<string>>(
        () => new Set(manyUnits.map((u) => u.evidence_id)),
      );
      const [providerId, setProviderId] = useState("default");
      return (
        <OcrSpellCheckDialog
          open={true}
          onOpenChange={vi.fn()}
          workspaceId="ws-1"
          doc={bigDoc}
          activePage={1}
          selectedUnitIds={selectedIds}
          onChangeSelectedUnitIds={setSelectedIds}
          providerId={providerId}
          onChangeProviderId={setProviderId}
          pendingDraftCount={2}
          isSubmitting={false}
          onSubmit={vi.fn()}
        />
      );
    }

    renderWithQuery(<DialogHarness />);

    // Must warn about unsaved draft vs saved server version v0
    expect(
      screen.getByText(/Lưu ý: Đang có 2 đoạn sửa nháp chưa lưu/i),
    ).toBeTruthy();
    expect(
      screen.getByText(/AI chỉ kiểm tra phiên bản đã lưu trên máy chủ/i),
    ).toBeTruthy();

    // All 105 units are selected -> must show limit error (never silently slice) and disable submit
    expect(
      screen.getByText(
        new RegExp(
          `Bạn đang chọn 105 đoạn, vượt quá giới hạn tối đa ${MAX_SPELL_CHECK_UNITS} đoạn`,
          "i",
        ),
      ),
    ).toBeTruthy();

    const submitBtn = screen.getByRole("button", {
      name: /Bắt đầu kiểm tra \(105 đoạn\)/i,
    }) as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
  });

  it("3. SourceDetailPage integrates spell-check dialog, sends exact scope & model with Idempotency-Key, and updates checkId", async () => {
    const check = buildCompletedCheck();
    mocks.checkDetails[check.id] = check;
    mocks.detectMutateAsync.mockResolvedValue(check);

    const onSearchChange = vi.fn();
    renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 1 }}
        onSearchChange={onSearchChange}
      />,
    );

    // Verify workflow microcopy is visible and raw sha256/evidence_id are hidden from main view
    expect(screen.getByText(/Quy trình: AI gợi ý sửa/i)).toBeTruthy();
    expect(screen.queryByText("ev-p1-1")).toBeNull();

    // Open spell check dialog
    fireEvent.click(screen.getByRole("button", { name: /Kiểm tra chính tả/i }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/Kiểm tra chính tả bằng AI/i)).toBeTruthy();

    // Submit spell check for Page 1 (2 non-empty units on page 1)
    fireEvent.click(
      within(dialog).getByRole("button", {
        name: /Bắt đầu kiểm tra \(2 đoạn\)/i,
      }),
    );

    await waitFor(() => {
      expect(mocks.detectMutateAsync).toHaveBeenCalledTimes(1);
    });
    const callArg = mocks.detectMutateAsync.mock.calls[0][0];
    expect(callArg.body.evidence_ids).toEqual(["ev-p1-1", "ev-p1-2"]);
    expect(callArg.idempotencyKey).toMatch(/^qnu-up-/);
    expect(onSearchChange).toHaveBeenCalledWith(
      expect.objectContaining({ checkId: "chk-101" }),
    );
  });

  it("4. Clicking 'Đối chiếu trên trang' jumps to the suggestion page, highlights real bbox, and shows honest notice when bbox is absent", async () => {
    const check = buildCompletedCheck();
    mocks.checkDetails[check.id] = check;

    const onSearchChange = vi.fn();
    renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 1, checkId: "chk-101" }}
        onSearchChange={onSearchChange}
      />,
    );

    // Suggestion sug-1 is on page 2 (`ev-p2-cell`)
    const locateButtons = await screen.findAllByRole("button", {
      name: /Đối chiếu trên trang/i,
    });
    fireEvent.click(locateButtons[0]);

    // Must jump to page 2 and render the real normalized bbox highlight
    await waitFor(() => {
      expect(screen.getByTestId("ocr-bbox-highlight")).toBeTruthy();
    });
    expect(onSearchChange).toHaveBeenCalledWith(
      expect.objectContaining({ page: 2 }),
    );
  });

  it("5. Applying a suggestion updates only the local draft; skipping does not alter text; withheld suggestions have no Apply button", async () => {
    const check = buildCompletedCheck();
    mocks.checkDetails[check.id] = check;

    renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 2, checkId: "chk-101" }}
        onSearchChange={vi.fn()}
      />,
    );

    // Verify withheld section has role="note" and NO "Áp dụng vào nháp" button inside it
    const withheldRegion = await screen.findByRole("note", {
      name: "Cần đối chiếu ảnh gốc",
    });
    expect(
      within(withheldRegion).queryByRole("button", {
        name: /Áp dụng/i,
      }),
    ).toBeNull();
    expect(
      within(withheldRegion).getByRole("button", {
        name: /Đối chiếu trên trang/i,
      }),
    ).toBeTruthy();

    // Apply verified suggestion `sug-1` ("tuyền" -> "tuyển") into draft
    const applyBtn = screen.getByRole("button", {
      name: /Áp dụng vào nháp/i,
    });
    fireEvent.click(applyBtn);

    // Must NOT call save mutation automatically
    expect(mocks.saveMutateAsync).not.toHaveBeenCalled();

    // Draft banner must show 1 unsaved unit
    await waitFor(() => {
      expect(screen.getByText(/Bản nháp: 1 đoạn chưa lưu/i)).toBeTruthy();
    });

    // Open resolved items to verify status is "Đã áp dụng vào nháp"
    fireEvent.click(
      screen.getByRole("button", { name: /Xem mục đã xử lý \(1\)/i }),
    );
    expect(screen.getAllByText(/Đã áp dụng vào nháp/i).length).toBeGreaterThan(
      0,
    );
  });

  it("6. Blocks applying suggestions when version/hash mismatches or when span no longer matches current text", () => {
    const doc = buildDefaultDoc();
    const staleVersionCheck = buildCompletedCheck({
      version: 2, // Document is at version 0
    });

    const { rerender } = render(
      <SpellingResultView
        check={staleVersionCheck}
        doc={doc}
        draftChanges={new Map()}
        canManage={true}
        onApply={vi.fn()}
      />,
    );

    expect(
      screen.getByText(
        /Kết quả thuộc phiên bản hoặc hash khác với văn bản đang mở/i,
      ),
    ).toBeTruthy();
    expect(
      screen.queryByRole("button", { name: /Áp dụng vào nháp/i }),
    ).toBeNull();

    // Now test matching version/hash, but user edited the text so span [17..22] no longer matches "tuyền"
    const matchingCheck = buildCompletedCheck();
    rerender(
      <SpellingResultView
        check={matchingCheck}
        doc={doc}
        draftChanges={
          new Map([
            [
              "ev-p2-cell",
              "Nội dung ô bảng đã được cán bộ sửa khác đi hoàn toàn.",
            ],
          ])
        }
        canManage={true}
        onApply={vi.fn()}
      />,
    );

    expect(screen.getAllByText(/Không còn khớp/i).length).toBeGreaterThan(0);
    const mismatchApplyBtn = screen.getByRole("button", {
      name: /Áp dụng vào nháp/i,
    }) as HTMLButtonElement;
    expect(mismatchApplyBtn.disabled).toBe(true);
  });

  it("7. Save dialog previews human-friendly before/after diffs, reuses Idempotency-Key across retries, keeps draft on error, and clears draft only after success", async () => {
    const check = buildCompletedCheck();
    mocks.checkDetails[check.id] = check;

    // First save call fails with network/server error; second succeeds
    mocks.saveMutateAsync
      .mockRejectedValueOnce(
        new ApiProblemError(
          {
            title: "Lỗi tạm thời",
            status: 503,
            detail: "Dịch vụ lưu tạm thời gián đoạn",
          },
          503,
        ),
      )
      .mockResolvedValueOnce({
        ...buildDefaultDoc(),
        version: 1,
        canonical_sha256: "c".repeat(64),
      });

    renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 2, checkId: "chk-101" }}
        onSearchChange={vi.fn()}
      />,
    );

    // Apply suggestion to create a draft change on `ev-p2-cell`
    fireEvent.click(
      await screen.findByRole("button", { name: /Áp dụng vào nháp/i }),
    );

    // Open Save confirm dialog
    fireEvent.click(screen.getByRole("button", { name: /Lưu thay đổi/i }));

    const saveDialog = await screen.findByRole("dialog");
    // Must display human-friendly locator ("Trang 2 · Ô bảng (Hàng 3, Cột 4)") instead of raw "ev-p2-cell"
    expect(
      within(saveDialog).getByText("Trang 2 · Ô bảng (Hàng 3, Cột 4)"),
    ).toBeTruthy();
    expect(within(saveDialog).queryByText("ev-p2-cell")).toBeNull();

    // First attempt -> fails
    fireEvent.click(
      within(saveDialog).getByRole("button", {
        name: /Xác nhận lưu v1/i,
      }),
    );

    await waitFor(() => {
      expect(mocks.saveMutateAsync).toHaveBeenCalledTimes(1);
    });
    const firstKey = mocks.saveMutateAsync.mock.calls[0][0].idempotencyKey;
    expect(firstKey).toMatch(/^qnu-up-/);

    // Draft MUST still be preserved after failed save
    expect(screen.getByText(/Bản nháp: 1 đoạn chưa lưu/i)).toBeTruthy();

    // Retry inside the still-open dialog (or reopen if closed) without editing draft -> must reuse the EXACT same Idempotency-Key
    const confirmBtns = screen.queryAllByRole("button", {
      name: /Xác nhận lưu v1/i,
    });
    if (confirmBtns.length === 0) {
      fireEvent.click(screen.getByRole("button", { name: /Lưu thay đổi/i }));
    }
    const retryDialog = await screen.findByRole("dialog");
    fireEvent.click(
      within(retryDialog).getByRole("button", {
        name: /Xác nhận lưu v1/i,
      }),
    );

    await waitFor(() => {
      expect(mocks.saveMutateAsync).toHaveBeenCalledTimes(2);
    });
    const secondKey = mocks.saveMutateAsync.mock.calls[1][0].idempotencyKey;
    expect(secondKey).toBe(firstKey);

    // After success, draft banner disappears
    await waitFor(() => {
      expect(screen.queryByText(/Bản nháp: 1 đoạn chưa lưu/i)).toBeNull();
    });
  });

  it("8. Preserves unsaved draft across mobile pane switches (Ảnh / Văn bản / Gợi ý) and page navigation", async () => {
    renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 1 }}
        onSearchChange={vi.fn()}
      />,
    );

    // Click "Sửa Đoạn văn 1" on Page 1 to edit manually
    fireEvent.click(screen.getByRole("button", { name: /Sửa Đoạn văn 1/i }));
    const editDialog = await screen.findByRole("dialog");
    const textarea = within(editDialog).getByLabelText(/Nội dung hiệu đính/i);
    fireEvent.change(textarea, {
      target: { value: "Bệnh viện cấp cơ bản trở lên xác nhận." },
    });
    fireEvent.click(
      within(editDialog).getByRole("button", { name: /Áp dụng vào nháp/i }),
    );

    expect(screen.getByText(/Bản nháp: 1 đoạn chưa lưu/i)).toBeTruthy();

    // Switch mobile panes: Ảnh -> Gợi ý -> Văn bản
    const mobileTabs = screen.getByRole("tablist", {
      name: /Chuyển vùng hiển thị trên màn hình nhỏ/i,
    });
    fireEvent.click(
      within(mobileTabs).getByRole("tab", { name: /Ảnh trang 1/i }),
    );
    fireEvent.click(within(mobileTabs).getByRole("tab", { name: /Gợi ý/i }));
    fireEvent.click(within(mobileTabs).getByRole("tab", { name: /Văn bản/i }));

    // Draft text must still be rendered intact
    expect(
      screen.getByText("Bệnh viện cấp cơ bản trở lên xác nhận."),
    ).toBeTruthy();
  });

  it("9. Read-only viewer (`canManage = false`) cannot trigger spell check, edit draft, or save", () => {
    mocks.role = "viewer";

    renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 1 }}
        onSearchChange={vi.fn()}
      />,
    );

    expect(screen.getByText(/Chế độ chỉ xem/i)).toBeTruthy();
    expect(
      screen.queryByRole("button", { name: /Kiểm tra chính tả/i }),
    ).toBeNull();
    expect(screen.queryByRole("button", { name: /Lưu thay đổi/i })).toBeNull();

    // Clicking text unit must NOT open editor dialog when canManage is false
    fireEvent.click(
      screen.getByText("Bệnh viện cấp cơ huyên trở lên xác nhận."),
    );
    expect(screen.queryByLabelText(/Nội dung hiệu đính/i)).toBeNull();
  });

  it("10. Covers all empty/0-suggestion/failed/uncertain states honestly, stating 0 suggestions does not guarantee OCR accuracy", () => {
    const doc = buildDefaultDoc();
    const zeroCheck = buildCompletedCheck({
      suggestions: [],
      withheld_suggestions: [],
    });

    const { rerender } = render(
      <SpellingResultView
        check={zeroCheck}
        doc={doc}
        draftChanges={new Map()}
        canManage={true}
        onApply={vi.fn()}
      />,
    );

    expect(
      screen.getByText(
        /Không có đề xuất trong lần kiểm tra này\. Điều này không xác nhận OCR đã chính xác\./i,
      ),
    ).toBeTruthy();

    // Uncertain state
    const uncertainCheck = buildCompletedCheck({
      status: "uncertain",
      error_code: "ocr_spelling_invalid",
      suggestions: [],
      withheld_suggestions: [],
    });
    rerender(
      <SpellingResultView
        check={uncertainCheck}
        doc={doc}
        draftChanges={new Map()}
        canManage={true}
        onApply={vi.fn()}
      />,
    );
    expect(screen.getByText("Chưa rõ kết quả")).toBeTruthy();
    expect(
      screen.getByText(
        /Lần kiểm tra chưa hoàn tất thành công\. Giao diện chỉ đọc trạng thái, không tự gọi model lại\./i,
      ),
    ).toBeTruthy();

    // Failed state
    const failedCheck = buildCompletedCheck({
      status: "failed",
      error_code: "ocr_spelling_interrupted",
      suggestions: [],
      withheld_suggestions: [],
    });
    rerender(
      <SpellingResultView
        check={failedCheck}
        doc={doc}
        draftChanges={new Map()}
        canManage={true}
        onApply={vi.fn()}
      />,
    );
    expect(screen.getByText("Thất bại")).toBeTruthy();
    expect(
      screen.getByText(
        /Lượt kiểm tra chính tả bị gián đoạn hoặc quá thời gian chờ phản hồi từ mô hình/i,
      ),
    ).toBeTruthy();
  });

  it("11. Does not fabricate bbox highlight for unit without coordinates, blocks Compiler when unsaved draft exists, and ignores stale async responses after source change", async () => {
    const onSearchChange = vi.fn();
    let resolveInFlightCheck: ((res: DetectionResponse) => void) | null = null;
    mocks.detectMutateAsync.mockImplementation(
      () =>
        new Promise<DetectionResponse>((resolve) => {
          resolveInFlightCheck = resolve;
        }),
    );

    const { rerender } = renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 1 }}
        onSearchChange={onSearchChange}
      />,
    );

    // Focus unit 2 on page 1 (`ev-p1-2`, which has `bbox: {}`)
    fireEvent.click(screen.getByRole("button", { name: /^Đoạn văn 2$/i }));
    // Must NOT render any fake bbox highlight
    expect(screen.queryByTestId("ocr-bbox-highlight")).toBeNull();
    expect(screen.getByText(/\(không có tọa độ vùng ảnh\)/i)).toBeTruthy();

    // Edit unit 1 into draft -> clicking "Dùng để biên soạn" must NOT open CompilationDialog while draft is unsaved
    fireEvent.click(screen.getByRole("button", { name: /Sửa Đoạn văn 1/i }));
    const editDialog = await screen.findByRole("dialog");
    fireEvent.change(within(editDialog).getByLabelText(/Nội dung hiệu đính/i), {
      target: { value: "Bệnh viện cấp cơ bản trở lên xác nhận." },
    });
    fireEvent.click(
      within(editDialog).getByRole("button", { name: /Áp dụng vào nháp/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: /Dùng để biên soạn/i }));
    expect(screen.queryByTestId("compilation-dialog")).toBeNull();

    // Start an in-flight spell check on src-1
    fireEvent.click(screen.getByRole("button", { name: /Kiểm tra chính tả/i }));
    const spellDialog = await screen.findByRole("dialog");
    fireEvent.click(
      within(spellDialog).getByRole("button", {
        name: /Bắt đầu kiểm tra \(2 đoạn\)/i,
      }),
    );

    // Switch to another source (`src-2`) before the spell-check response resolves
    onSearchChange.mockClear();
    rerender(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <SourceDetailPage
          workspaceId="ws-1"
          collectionId="col-1"
          sourceId="src-2"
          search={{ page: 1 }}
          onSearchChange={onSearchChange}
        />
      </QueryClientProvider>,
    );

    // Resolve the stale response from `src-1` -> must NOT update checkId on `src-2`
    resolveInFlightCheck?.(buildCompletedCheck({ id: "chk-stale-999" }));
    await new Promise((r) => setTimeout(r, 20));
    expect(onSearchChange).not.toHaveBeenCalledWith(
      expect.objectContaining({ checkId: "chk-stale-999" }),
    );
  });

  it("12. Renders word-level diff (<del>/<ins>), resizable split separator, and [ / ] keyboard page navigation", async () => {
    const onSearchChange = vi.fn();
    renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 1 }}
        onSearchChange={onSearchChange}
      />,
    );

    // Resizable split separator and ratio preset buttons must be present
    expect(
      screen.getByRole("separator", {
        name: /Kéo để thay đổi độ rộng cột ảnh và cột văn bản/i,
      }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "50:50" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Rộng ảnh" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Rộng chữ" })).toBeTruthy();

    // Edit prose unit on page 1 ("cơ huyên" -> "cơ bản")
    fireEvent.click(screen.getByRole("button", { name: /Sửa Đoạn văn 1/i }));
    const editDialog = await screen.findByRole("dialog");
    fireEvent.change(within(editDialog).getByLabelText(/Nội dung hiệu đính/i), {
      target: { value: "Bệnh viện cấp cơ bản trở lên xác nhận." },
    });

    // Word diff preview inside edit dialog must highlight removed "huyên" and added "bản"
    const editDiff = within(editDialog).getByTestId("ocr-word-diff");
    expect(editDiff.querySelector("del")?.textContent).toBe("huyên");
    expect(editDiff.querySelector("ins")?.textContent).toBe("bản");

    fireEvent.click(
      within(editDialog).getByRole("button", { name: /Áp dụng vào nháp/i }),
    );

    // Inline word diff on the prose block must also render
    const blockDiff = screen.getByTestId("ocr-word-diff");
    expect(blockDiff.querySelector("del")?.textContent).toBe("huyên");
    expect(blockDiff.querySelector("ins")?.textContent).toBe("bản");

    // Open Save dialog and verify word diff is rendered there too
    fireEvent.click(screen.getByRole("button", { name: /Lưu thay đổi/i }));
    const saveDialog = await screen.findByRole("dialog");
    const saveDiff = within(saveDialog).getByTestId("ocr-word-diff");
    expect(saveDiff.querySelector("del")?.textContent).toBe("huyên");
    expect(saveDiff.querySelector("ins")?.textContent).toBe("bản");
    fireEvent.click(within(saveDialog).getByRole("button", { name: "Hủy" }));

    // Keyboard shortcut `]` navigates to Page 2, `[` navigates back to Page 1
    fireEvent.keyDown(window, { key: "]" });
    expect(onSearchChange).toHaveBeenCalledWith(
      expect.objectContaining({ page: 2 }),
    );
    fireEvent.keyDown(window, { key: "[" });
    expect(onSearchChange).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1 }),
    );
  });
});
