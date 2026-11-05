// @vitest-environment jsdom
/**
 * Behavioral & real-artifact tests for "Xem tệp gốc" (Original File Preview via
 * `docx-preview` and `react-pdf`) alongside "Đối chiếu OCR" in `SourceDetailPage`
 * and `OcrComparisonView`.
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
import JSZip from "jszip";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearAccessToken, setAccessToken } from "@/app/api/v1";
import { clearAllOcrDrafts } from "@/features/knowledge/ocr-draft-store";
import type {
  DetectionResponse,
  ProcessingRunDetailResponse,
  ProcessingRunResponse,
  ReviewDocument,
} from "@/features/knowledge/ocr-types";
import {
  DocxOriginalViewer,
  PdfOriginalViewer,
  sanitizeDocxPreviewContainer,
} from "@/features/knowledge/original-file-preview";
import { SourceDetailPage } from "@/features/knowledge/source-detail-page";

const mocks = vi.hoisted(() => ({
  navigate: vi.fn(),
  detectMutateAsync: vi.fn(),
  saveMutateAsync: vi.fn(),
  requestRunMutateAsync: vi.fn(),
  readRenderedPdfBlob: vi.fn(),
  useRevisionContentBlobMock: vi.fn(),
  role: "editor" as "viewer" | "editor" | "admin",
  revisions: [
    {
      id: "rev-1",
      revision_no: 1,
      file_name: "quy-che-dao-tao.docx",
      mime_type:
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      file_size: 84200,
      processing_status: "completed",
    },
  ] as Array<{
    id: string;
    revision_no: number;
    file_name: string;
    mime_type: string;
    file_size: number;
    processing_status: string;
  }>,
  runs: [] as ProcessingRunResponse[],
  runDetail: null as ProcessingRunDetailResponse | null,
  docData: null as ReviewDocument | null,
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
    data: [],
    isPending: false,
    isError: false,
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
      current_revision_id: mocks.revisions[0]?.id ?? "rev-1",
      active_revision_no: mocks.revisions[0]?.revision_no ?? 1,
    },
    isPending: false,
    isError: false,
  }),
  useRevisionsQuery: () => ({
    data: mocks.revisions,
    isPending: false,
    isError: false,
  }),
}));

vi.mock("@/features/knowledge/ocr-requests", () => ({
  downloadReviewDocumentBlob: vi.fn(),
  downloadReviewMarkdownBlob: vi.fn(),
  downloadRunBundleBlob: vi.fn(),
  readRenderedPdfBlob: (...args: unknown[]) =>
    mocks.readRenderedPdfBlob(...args),
}));

vi.mock("@/features/knowledge/ocr-queries", () => ({
  useProcessingRunsQuery: () => ({
    data: {
      items: mocks.runs,
      total: mocks.runs.length,
    },
    isPending: false,
    isError: false,
  }),
  useProcessingRunDetailQuery: () => ({
    data: mocks.runDetail ?? undefined,
    isPending: false,
    isError: false,
  }),
  useTextReviewQuery: () => ({
    data: mocks.docData ?? undefined,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
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
    blobUrl:
      mocks.runDetail?.status === "completed" ? "blob:ocr-page-img" : null,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  useRevisionContentBlob: (...args: unknown[]) =>
    mocks.useRevisionContentBlobMock(...args),
  usePageRawText: () => ({
    rawText: "Raw text",
    isLoading: false,
    error: null,
  }),
}));

vi.mock("react-pdf", () => ({
  pdfjs: {
    GlobalWorkerOptions: { workerSrc: "" },
  },
  Document: ({
    file,
    onLoadSuccess,
    children,
  }: {
    file: string;
    onLoadSuccess?: (info: { numPages: number }) => void;
    children: React.ReactNode;
  }) => {
    return (
      <div
        data-testid="mock-react-pdf-document"
        data-file={file}
        ref={(el) => {
          if (el && !el.dataset.loaded) {
            el.dataset.loaded = "true";
            onLoadSuccess?.({ numPages: 3 });
          }
        }}
      >
        {children}
      </div>
    );
  },
  Page: ({
    pageNumber,
    width,
    renderTextLayer,
  }: {
    pageNumber: number;
    width?: number;
    renderTextLayer?: boolean;
  }) => (
    <div
      data-testid="mock-react-pdf-page"
      data-page-number={pageNumber}
      data-width={width}
      data-text-layer={String(Boolean(renderTextLayer))}
    >
      {renderTextLayer ? (
        <div className="react-pdf__Page__textContent">
          <span>
            Trường Đại học Quy Nhơn - Văn bản lớp chữ PDF gốc trang {pageNumber}
          </span>
        </div>
      ) : null}
      <canvas data-testid="mock-react-pdf-canvas" />
    </div>
  ),
}));

vi.mock("@/features/knowledge/compilation-dialog", () => ({
  CompilationDialog: () => null,
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

/**
 * Builds a genuine OpenXML `.docx` ZIP Blob containing:
 * - 2 sections (`<w:sectPr>`)
 * - Footer (`word/footer1.xml`)
 * - A table (`<w:tbl>`) with rows and cells
 */
async function createRealMultiSectionDocxBlob(
  section1Title = "PHẦN I: QUY ĐỊNH CHUNG ĐẠI HỌC QUY NHƠN",
  section2Title = "PHẦN II: BẢNG ĐIỂM CHUẨN TRÚNG TUYỂN 2026",
): Promise<Blob> {
  const zip = new JSZip();

  zip.file(
    "[Content_Types].xml",
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
</Types>`,
  );

  zip.file(
    "_rels/.rels",
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>`,
  );

  zip.file(
    "word/_rels/document.xml.rels",
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdFooter1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
</Relationships>`,
  );

  zip.file(
    "word/footer1.xml",
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:p>
    <w:r>
      <w:t>Chân trang: Trường Đại học Quy Nhơn - Tài liệu kiểm thử nhiều section</w:t>
    </w:r>
  </w:p>
</w:ftr>`,
  );

  zip.file(
    "word/document.xml",
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    <w:p>
      <w:r><w:t>${section1Title}</w:t></w:r>
      <w:pPr>
        <w:sectPr>
          <w:pgSz w:w="11906" w:h="16838"/>
        </w:sectPr>
      </w:pPr>
    </w:p>
    <w:p>
      <w:r><w:t>${section2Title}</w:t></w:r>
    </w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Mã ngành</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Tên ngành đào tạo</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>7480201</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Công nghệ thông tin</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
    <w:sectPr>
      <w:footerReference w:type="default" r:id="rIdFooter1"/>
      <w:pgSz w:w="11906" w:h="16838"/>
    </w:sectPr>
  </w:body>
</w:document>`,
  );

  const uint8 = await zip.generateAsync({ type: "uint8array" });
  return new Blob([uint8], {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
}

function buildCompletedRun(): {
  run: ProcessingRunResponse;
  detail: ProcessingRunDetailResponse;
  doc: ReviewDocument;
} {
  const run: ProcessingRunResponse = {
    id: "run-1",
    status: "completed",
    generation: 1,
    page_count: 2,
    pages_total: 2,
    created_at: "2026-11-03T08:00:00Z",
  };
  const detail: ProcessingRunDetailResponse = {
    ...run,
    pages: [
      {
        page_number: 1,
        status: "completed",
        has_rendered_image: true,
        used_ocr: true,
        has_tables: false,
      },
      {
        page_number: 2,
        status: "completed",
        has_rendered_image: true,
        used_ocr: true,
        has_tables: true,
      },
    ],
  };
  const doc: ReviewDocument = {
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
        text: "Đoạn văn trang 1 có tọa độ thật.",
        original_text: "Đoạn văn trang 1 có tọa độ thật.",
        page: 1,
        kind: "paragraph",
        row: null,
        column: null,
        bbox: { x0: 0.1, y0: 0.2, x1: 0.85, y1: 0.28 },
      },
      {
        evidence_id: "ev-p2-cell",
        text: "Điểm chuẩn trúng tuyền năm 2026.",
        original_text: "Điểm chuẩn trúng tuyền năm 2026.",
        page: 2,
        kind: "table_cell",
        row: 1,
        column: 1,
        bbox: { x0: 0.15, y0: 0.4, x1: 0.6, y1: 0.48 },
      },
    ],
  };
  return { run, detail, doc };
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
  setAccessToken("session-token-original-preview");
  mocks.role = "editor";
  mocks.revisions = [
    {
      id: "rev-1",
      revision_no: 1,
      file_name: "quy-che-dao-tao.docx",
      mime_type:
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      file_size: 84200,
      processing_status: "completed",
    },
  ];
  mocks.runs = [];
  mocks.runDetail = null;
  mocks.docData = null;
  mocks.checkDetails = {};
  mocks.readRenderedPdfBlob.mockReset();
  mocks.useRevisionContentBlobMock.mockReset();

  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  cleanup();
  clearAccessToken();
  clearAllOcrDrafts();
  vi.unstubAllGlobals();
});

describe("Original File Preview (Xem tệp gốc) & Two-Pane OCR Comparison", () => {
  it("1. Renders a real multi-section DOCX (with footer & table) via docx-preview renderAsync and sanitizes external resources", async () => {
    const docxBlob = await createRealMultiSectionDocxBlob();

    render(
      <DocxOriginalViewer
        blob={docxBlob}
        revisionKey="src-1:rev-1"
        zoomPercent={100}
        zoomMode="fit-width"
      />,
    );

    // Must show independent scroll container
    expect(screen.getByTestId("docx-original-scroll-container")).toBeTruthy();

    // Wait for docx-preview's real renderAsync() to populate sections, table, and footer
    const renderTarget = screen.getByTestId("docx-original-render-target");
    await waitFor(() => {
      expect(renderTarget.textContent).toContain(
        "PHẦN I: QUY ĐỊNH CHUNG ĐẠI HỌC QUY NHƠN",
      );
    });
    expect(renderTarget.textContent).toContain(
      "PHẦN II: BẢNG ĐIỂM CHUẨN TRÚNG TUYỂN 2026",
    );
    expect(renderTarget.textContent).toContain("Công nghệ thông tin");
    expect(renderTarget.textContent).toContain(
      "Chân trang: Trường Đại học Quy Nhơn",
    );
    expect(renderTarget.querySelectorAll("table").length).toBeGreaterThan(0);

    // Verify sanitizeDocxPreviewContainer blocks external network requests and scopes CSS
    const dirtyContainer = document.createElement("div");
    dirtyContainer.innerHTML = `
      <style>body { background: url('https://evil.example.com/bg.png'); color: red; }</style>
      <img src="https://evil.example.com/tracker.png" alt="ext" />
      <img src="data:image/png;base64,iVBORw0KGgo=" alt="inline" />
      <script>window.__pwned = true;</script>
      <iframe src="https://evil.example.com/frame"></iframe>
      <a href="javascript:alert(1)">bad link</a>
    `;
    const result = sanitizeDocxPreviewContainer(dirtyContainer);
    expect(result.blockedExternalCount).toBeGreaterThanOrEqual(5);
    expect(dirtyContainer.querySelector("script")).toBeNull();
    expect(dirtyContainer.querySelector("iframe")).toBeNull();
    const extImg = dirtyContainer.querySelector('img[alt="ext"]');
    expect(extImg?.getAttribute("src")).toBeNull();
    expect(extImg?.getAttribute("data-blocked-external-resource")).toBe("true");
    const safeImg = dirtyContainer.querySelector('img[alt="inline"]');
    expect(safeImg?.getAttribute("src")).toContain("data:image/png");
    expect(dirtyContainer.querySelector("style")?.textContent).not.toContain(
      "https://evil.example.com",
    );
  });

  it.each([false, true])(
    "2. Opens DOCX directly without an OCR comparison (native completed: %s)",
    async (completed) => {
      if (completed) {
        const { run, detail, doc } = buildCompletedRun();
        detail.pages = detail.pages.map((page) => ({
          ...page,
          used_ocr: false,
        }));
        mocks.runs = [run];
        mocks.runDetail = detail;
        mocks.docData = doc;
      }
      const docxBlob = await createRealMultiSectionDocxBlob();
      mocks.useRevisionContentBlobMock.mockReturnValue({
        blob: docxBlob,
        blobUrl: "blob:docx-rev-1",
        contentType:
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        fileName: "quy-che-dao-tao.docx",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      // Unprocessed state: runs = [], runDetail = null
      renderWithQuery(
        <SourceDetailPage
          workspaceId="ws-1"
          collectionId="col-1"
          sourceId="src-1"
          search={{ page: 1 }}
          onSearchChange={vi.fn()}
        />,
      );

      // In unprocessed state, original file preview is active by default alongside 'Bắt đầu bóc tách ngay'
      expect(await screen.findByTestId("docx-original-viewer")).toBeTruthy();
      expect(screen.queryByTestId("left-pane-mode-ocr")).toBeNull();
      if (!completed) {
        expect(
          screen.getByText(/Tài liệu đã được lưu trữ an toàn/i),
        ).toBeTruthy();
      }

      await waitFor(() => {
        expect(
          screen.getByTestId("docx-original-render-target").textContent,
        ).toContain("PHẦN I: QUY ĐỊNH CHUNG ĐẠI HỌC QUY NHƠN");
      });

      // Must NEVER call readRenderedPdfBlob / Gotenberg when previewing Word original file
      expect(mocks.readRenderedPdfBlob).not.toHaveBeenCalled();
    },
  );

  it("3. Defaults to 'Đối chiếu OCR' when extracted, shows 'Bản dàn trang từ DOCX', and switches back from 'Xem tệp gốc' to 'Đối chiếu OCR' when locating a unit", async () => {
    const docxBlob = await createRealMultiSectionDocxBlob();
    const { run, detail, doc } = buildCompletedRun();
    mocks.runs = [run];
    mocks.runDetail = detail;
    mocks.docData = doc;
    mocks.checkDetails["chk-1"] = {
      id: "chk-1",
      status: "completed",
      version: 0,
      canonical_sha256: "a".repeat(64),
      checked_evidence_ids: ["ev-p2-cell"],
      error_code: null,
      usage_id: null,
      created_at: "2026-11-03T08:10:00Z",
      suggestions: [
        {
          evidence_id: "ev-p2-cell",
          original: "tuyền",
          replacement: "tuyển",
          start: 17,
          end: 22,
          context_before: "Điểm chuẩn trúng ",
          context_after: " năm 2026.",
          reason: "Sai dấu hỏi/ngã",
        },
      ],
      withheld_suggestions: [],
    };
    mocks.useRevisionContentBlobMock.mockReturnValue({
      blob: docxBlob,
      blobUrl: "blob:docx-rev-1",
      contentType:
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      fileName: "quy-che-dao-tao.docx",
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    const onSearchChange = vi.fn();
    renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 1, checkId: "chk-1" }}
        onSearchChange={onSearchChange}
      />,
    );

    // Default mode for completed extraction must be 'Đối chiếu OCR'
    expect(
      screen.getByTestId("left-pane-mode-ocr").getAttribute("aria-pressed"),
    ).toBe("true");
    expect(screen.getByText("Bản dàn trang từ DOCX")).toBeTruthy();

    // User switches to 'Xem tệp gốc' to read the Word file
    fireEvent.click(screen.getByTestId("left-pane-mode-original"));
    expect(
      screen
        .getByTestId("left-pane-mode-original")
        .getAttribute("aria-pressed"),
    ).toBe("true");
    await waitFor(() => {
      expect(screen.getByTestId("docx-original-viewer")).toBeTruthy();
    });

    // Now user clicks 'Đối chiếu trên trang' on the suggestion from page 2
    const locateBtns = await screen.findAllByRole("button", {
      name: /Đối chiếu trên trang/i,
    });
    fireEvent.click(locateBtns[0]);

    // Left pane must automatically switch back to 'Đối chiếu OCR', navigate to page 2, and highlight bbox!
    await waitFor(() => {
      expect(
        screen.getByTestId("left-pane-mode-ocr").getAttribute("aria-pressed"),
      ).toBe("true");
      expect(screen.getByTestId("ocr-bbox-highlight")).toBeTruthy();
    });
    expect(onSearchChange).toHaveBeenCalledWith(
      expect.objectContaining({ page: 2 }),
    );
  });

  it("Opens directly extracted Word in its original viewer without a page image", async () => {
    const docxBlob = await createRealMultiSectionDocxBlob();
    const { run, detail, doc } = buildCompletedRun();
    const word = { ...run, pagination: "document" as const };
    mocks.runs = [word];
    mocks.runDetail = {
      ...detail,
      ...word,
      page_count: 1,
      pages_total: 1,
      pages: [{ ...detail.pages[0], has_rendered_image: false }],
    };
    mocks.docData = { ...doc, units: [{ ...doc.units[0], bbox: {} }] };
    mocks.useRevisionContentBlobMock.mockReturnValue({
      blob: docxBlob,
      blobUrl: "blob:docx-rev-1",
      contentType: mocks.revisions[0].mime_type,
      fileName: mocks.revisions[0].file_name,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 1 }}
        onSearchChange={vi.fn()}
      />,
    );

    expect(await screen.findByTestId("docx-original-viewer")).toBeTruthy();
    expect(screen.queryByTestId("left-pane-mode-ocr")).toBeNull();
    expect(mocks.readRenderedPdfBlob).not.toHaveBeenCalled();
  });

  it("4. Renders PDF original file with selectable text layer via react-pdf and supports permission error & revision switching", async () => {
    mocks.revisions = [
      {
        id: "rev-pdf-1",
        revision_no: 1,
        file_name: "thong-bao-tuyen-sinh.pdf",
        mime_type: "application/pdf",
        file_size: 120000,
        processing_status: "completed",
      },
      {
        id: "rev-pdf-2",
        revision_no: 2,
        file_name: "thong-bao-tuyen-sinh-v2.pdf",
        mime_type: "application/pdf",
        file_size: 125000,
        processing_status: "completed",
      },
    ];
    const { run, detail, doc } = buildCompletedRun();
    detail.pages[0].used_ocr = false;
    mocks.runs = [run];
    mocks.runDetail = detail;
    mocks.docData = doc;

    mocks.useRevisionContentBlobMock.mockImplementation(
      (
        _w: string,
        _c: string,
        _s: string,
        revisionId: string,
        enabled: boolean,
      ) => {
        if (!enabled) {
          return {
            blob: null,
            blobUrl: null,
            contentType: null,
            fileName: null,
            isLoading: false,
            error: null,
            refetch: vi.fn(),
          };
        }
        if (revisionId === "rev-forbidden") {
          return {
            blob: null,
            blobUrl: null,
            contentType: null,
            fileName: null,
            isLoading: false,
            error:
              "Bạn không có quyền truy cập tệp gốc của phiên bản này (403).",
            refetch: vi.fn(),
          };
        }
        return {
          blob: new Blob(["%PDF-1.7"], { type: "application/pdf" }),
          blobUrl: `blob:pdf-${revisionId}`,
          contentType: "application/pdf",
          fileName: "thong-bao-tuyen-sinh.pdf",
          isLoading: false,
          error: null,
          refetch: vi.fn(),
        };
      },
    );

    const { rerender } = renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 1, revisionId: "rev-pdf-1" }}
        onSearchChange={vi.fn()}
      />,
    );

    // The native text PDF opens directly in the original viewer.
    expect(screen.queryByTestId("left-pane-mode-ocr")).toBeNull();
    const pdfViewer = await screen.findByTestId("pdf-original-viewer");
    expect(
      within(pdfViewer)
        .getByTestId("mock-react-pdf-document")
        .getAttribute("data-file"),
    ).toBe("blob:pdf-rev-pdf-1");

    const pdfPage = within(pdfViewer).getByTestId("mock-react-pdf-page");
    expect(pdfPage.getAttribute("data-text-layer")).toBe("true");
    expect(pdfViewer.textContent).toContain(
      "Trường Đại học Quy Nhơn - Văn bản lớp chữ PDF gốc trang 1",
    );
    fireEvent.click(screen.getByRole("button", { name: "Trang sau" }));
    expect(
      screen.getByTestId("left-pane-mode-ocr").getAttribute("aria-pressed"),
    ).toBe("true");
    fireEvent.click(screen.getByRole("button", { name: "Trang trước" }));
    expect(screen.queryByTestId("left-pane-mode-ocr")).toBeNull();

    // Switch revision to rev-pdf-2 -> must immediately display rev-pdf-2 and never retain stale rev-pdf-1
    rerender(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <SourceDetailPage
          workspaceId="ws-1"
          collectionId="col-1"
          sourceId="src-1"
          search={{ page: 1, revisionId: "rev-pdf-2" }}
          onSearchChange={vi.fn()}
        />
      </QueryClientProvider>,
    );
    expect(screen.queryByTestId("left-pane-mode-ocr")).toBeNull();
    await waitFor(() => {
      expect(
        screen.getByTestId("mock-react-pdf-document").getAttribute("data-file"),
      ).toBe("blob:pdf-rev-pdf-2");
    });

    // Test permission error (403) state
    mocks.revisions = [
      {
        id: "rev-forbidden",
        revision_no: 3,
        file_name: "mat.pdf",
        mime_type: "application/pdf",
        file_size: 1000,
        processing_status: "failed",
      },
    ];
    rerender(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <SourceDetailPage
          workspaceId="ws-1"
          collectionId="col-1"
          sourceId="src-1"
          search={{ page: 1, revisionId: "rev-forbidden" }}
          onSearchChange={vi.fn()}
        />
      </QueryClientProvider>,
    );
    expect(screen.queryByTestId("left-pane-mode-ocr")).toBeNull();
    expect(await screen.findByText("Không tải được tệp gốc")).toBeTruthy();
    expect(
      screen.getByText(
        /Bạn không có quyền truy cập tệp gốc của phiên bản này \(403\)/i,
      ),
    ).toBeTruthy();
  });

  it("5. Renders PdfOriginalViewer directly with zoom controls and page clamping", async () => {
    const onPageChange = vi.fn();
    const onTotalPagesDetected = vi.fn();

    render(
      <PdfOriginalViewer
        blobUrl="blob:pdf-direct-test"
        revisionKey="src-1:rev-1"
        pageNumber={5}
        onPageChange={onPageChange}
        onTotalPagesDetected={onTotalPagesDetected}
        zoomPercent={125}
        zoomMode="custom"
      />,
    );

    const viewer = await screen.findByTestId("pdf-original-viewer");
    expect(viewer).toBeTruthy();
    expect(onTotalPagesDetected).toHaveBeenCalledWith(3);
    // Since pageNumber=5 > numPages=3, it clamps and calls onPageChange(3)
    await waitFor(() => {
      expect(onPageChange).toHaveBeenCalledWith(3);
    });
  });

  it("6. Allows opening 'Xem tệp gốc' when extraction failed (status === 'failed') for both DOCX and scanned PDF", async () => {
    mocks.revisions = [
      {
        id: "rev-scan-pdf",
        revision_no: 1,
        file_name: "hoc-ba-scan.pdf",
        mime_type: "application/pdf",
        file_size: 540000,
        processing_status: "failed",
      },
    ];
    const failedRun: ProcessingRunResponse = {
      id: "run-failed-1",
      status: "failed",
      generation: 1,
      page_count: 0,
      pages_total: 2,
      error_code: "ocr_provider_unavailable",
      error_detail: "Dịch vụ OCR tạm thời không phản hồi",
      created_at: "2026-11-03T08:15:00Z",
    };
    mocks.runs = [failedRun];
    mocks.runDetail = {
      ...failedRun,
      pages: [],
    };
    mocks.useRevisionContentBlobMock.mockReturnValue({
      blob: new Blob(["%PDF-1.7-scanned"], { type: "application/pdf" }),
      blobUrl: "blob:scanned-pdf-rev-1",
      contentType: "application/pdf",
      fileName: "hoc-ba-scan.pdf",
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 1 }}
        onSearchChange={vi.fn()}
      />,
    );

    // Failed extraction leaves the original directly available.
    expect(
      screen.getAllByText(/Bóc tách chưa thành công/i).length,
    ).toBeGreaterThan(0);
    expect(screen.queryByTestId("left-pane-mode-ocr")).toBeNull();

    // Scanned PDF renders via PdfOriginalViewer canvas
    const pdfViewer = await screen.findByTestId("pdf-original-viewer");
    expect(within(pdfViewer).getByTestId("mock-react-pdf-canvas")).toBeTruthy();
  });

  it("7. Discards stale DOCX render output when switching revisions rapidly", async () => {
    const blobRev1 = await createRealMultiSectionDocxBlob(
      "NỘI DUNG CŨ PHIÊN BẢN 1",
      "BẢNG CŨ V1",
    );
    const blobRev2 = await createRealMultiSectionDocxBlob(
      "NỘI DUNG MỚI PHIÊN BẢN 2",
      "BẢNG MỚI V2",
    );

    const { rerender } = render(
      <DocxOriginalViewer
        blob={blobRev1}
        revisionKey="src-1:rev-1"
        zoomPercent={100}
        zoomMode="fit-width"
      />,
    );

    // Immediately switch to rev-2 before rev-1 finishes
    rerender(
      <DocxOriginalViewer
        blob={blobRev2}
        revisionKey="src-1:rev-2"
        zoomPercent={100}
        zoomMode="fit-width"
      />,
    );

    const target = screen.getByTestId("docx-original-render-target");
    await waitFor(() => {
      expect(target.textContent).toContain("NỘI DUNG MỚI PHIÊN BẢN 2");
    });
    expect(target.textContent).not.toContain("NỘI DUNG CŨ PHIÊN BẢN 1");
  });

  it("8. Preserves focused unit and bbox highlight across mobile pane switch", () => {
    const { run, detail, doc } = buildCompletedRun();
    mocks.runs = [run];
    mocks.runDetail = detail;
    mocks.docData = doc;

    renderWithQuery(
      <SourceDetailPage
        workspaceId="ws-1"
        collectionId="col-1"
        sourceId="src-1"
        search={{ page: 1 }}
        onSearchChange={vi.fn()}
      />,
    );

    // Focus unit on page 1, switch mobile tabs (Ảnh trang 1 <-> Văn bản) -> focused unit & bbox remain intact
    fireEvent.click(screen.getByRole("button", { name: /^Đoạn văn 1$/i }));
    expect(screen.getByTestId("ocr-bbox-highlight")).toBeTruthy();

    const mobileTabs = screen.getByRole("tablist", {
      name: /Chuyển vùng hiển thị trên màn hình nhỏ/i,
    });
    fireEvent.click(
      within(mobileTabs).getByRole("tab", { name: /Ảnh trang 1/i }),
    );
    expect(screen.getByTestId("ocr-bbox-highlight")).toBeTruthy();
    fireEvent.click(within(mobileTabs).getByRole("tab", { name: /Văn bản/i }));
    expect(screen.getByText(/Đang đối chiếu: Đoạn văn 1/i)).toBeTruthy();
  });
});
