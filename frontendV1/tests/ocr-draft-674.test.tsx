// @vitest-environment jsdom
/**
 * Context674 F2 — a post-OCR draft must survive switching to the scan
 * comparison tab and back.
 *
 * Reproduced from `storage/artifacts/context674-review/ocr-draft.test.tsx`
 * (the review probe). The assertions are unchanged; only the router mock gained
 * `useBlocker`, because the container now blocks leaving the page with an
 * unsaved draft.
 */
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { clearAccessToken, setAccessToken } from "@/app/api/v1";
import { clearAllOcrDrafts } from "@/features/knowledge/ocr-draft-store";
import { OcrTabContainer } from "@/features/knowledge/ocr-tab-container";

const data = vi.hoisted(() => ({
  run: { id: "synthetic-ocr", status: "completed", generation: 1 },
  document: {
    run_id: "synthetic-ocr",
    version: 0,
    version_id: null,
    canonical_sha256: "0".repeat(64),
    original_sha256: "0".repeat(64),
    markdown_sha256: "1".repeat(64),
    units: [
      {
        evidence_id: "ev-1",
        text: "Văn bản OCR gốc",
        original_text: "Văn bản OCR gốc",
        page: 1,
        kind: "paragraph",
        row: null,
        column: null,
        bbox: {},
      },
    ],
    saved_at: null,
  },
}));

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  useBlocker: () => undefined,
}));
vi.mock("@/features/knowledge/ocr-queries", () => ({
  useProcessingRunsQuery: () => ({
    data: { items: [data.run], total: 1 },
    isPending: false,
    isError: false,
  }),
  useProcessingRunDetailQuery: (
    _workspaceId: string,
    _collectionId: string,
    _sourceId: string,
    _revisionId: string,
    runId: string | null,
  ) => ({
    // Echo the requested run so a second run is genuinely a different scope.
    data: runId ? { ...data.run, id: runId } : data.run,
    isPending: false,
    isError: false,
  }),
  useTextReviewQuery: () => ({
    data: data.document,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useSaveTextReviewMutation: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDetectCheckMutation: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock("@/features/modelops/queries", () => ({
  useCatalogQuery: () => ({ data: [], isPending: false, isError: false }),
}));
vi.mock("@/features/knowledge/ocr-comparison-view", () => ({
  OcrComparisonView: () => <div>Ảnh OCR thử</div>,
}));
vi.mock("@/features/knowledge/ocr-runs-list", () => ({
  OcrRunsList: () => <div>Lượt OCR thử</div>,
}));
vi.mock("@/features/knowledge/ocr-request-dialog", () => ({
  OcrRequestDialog: () => null,
}));
vi.mock("@/features/knowledge/ocr-artifacts-panel", () => ({
  OcrArtifactsPanel: () => null,
}));
vi.mock("sonner", () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn(), warning: vi.fn() },
}));

beforeEach(() => {
  setAccessToken("synthetic-ocr-session");
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  vi.spyOn(window, "confirm").mockReturnValue(false);
});
afterEach(() => {
  cleanup();
  clearAccessToken();
  clearAllOcrDrafts();
  vi.unstubAllGlobals();
});

function renderContainer() {
  return render(
    <OcrTabContainer
      workspaceId="w"
      collectionId="c"
      sourceId="s"
      revisionId="r"
      revisionNo={1}
      fileName="synthetic.pdf"
      contentType="application/pdf"
      canManage
      initialRunId={data.run.id}
      initialSubTab="review"
    />,
  );
}

test("opening the scan comparison tab must preserve an unsaved OCR draft or block the navigation", async () => {
  renderContainer();
  fireEvent.click(screen.getByRole("button", { name: "Chỉnh sửa" }));
  fireEvent.change(screen.getByPlaceholderText("Nhập nội dung chỉnh sửa..."), {
    target: { value: "Bản nháp người dùng đang sửa" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng vào nháp" }));
  expect(screen.getByText("Bản nháp người dùng đang sửa")).toBeTruthy();

  const comparison = screen.getByRole("tab", {
    name: "Đối chiếu ảnh & Văn bản",
  });
  fireEvent.mouseDown(comparison, { button: 0, ctrlKey: false });
  await waitFor(() => expect(screen.getByText("Ảnh OCR thử")).toBeTruthy());

  const review = screen.getByRole("tab", {
    name: /Rà soát & Sửa bản dẫn xuất/,
  });
  fireEvent.mouseDown(review, { button: 0, ctrlKey: false });
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Chỉnh sửa" })).toBeTruthy(),
  );
  expect(screen.queryByText("Bản nháp người dùng đang sửa")).not.toBeNull();
});

test("the draft is pinned to its OCR run and is not shown for another run", async () => {
  const { unmount } = renderContainer();
  fireEvent.click(screen.getByRole("button", { name: "Chỉnh sửa" }));
  fireEvent.change(screen.getByPlaceholderText("Nhập nội dung chỉnh sửa..."), {
    target: { value: "Bản nháp của lượt OCR thứ nhất" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng vào nháp" }));
  expect(screen.getByText("Bản nháp của lượt OCR thứ nhất")).toBeTruthy();
  unmount();

  // A different run id must not inherit the previous draft.
  render(
    <OcrTabContainer
      workspaceId="w"
      collectionId="c"
      sourceId="s"
      revisionId="r"
      revisionNo={1}
      fileName="synthetic.pdf"
      contentType="application/pdf"
      canManage
      initialRunId="synthetic-ocr-other-run"
      initialSubTab="review"
    />,
  );
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Chỉnh sửa" })).toBeTruthy(),
  );
  expect(screen.queryByText("Bản nháp của lượt OCR thứ nhất")).toBeNull();
});

test("logging out drops drafts that belong to the previous session", async () => {
  renderContainer();
  fireEvent.click(screen.getByRole("button", { name: "Chỉnh sửa" }));
  fireEvent.change(screen.getByPlaceholderText("Nhập nội dung chỉnh sửa..."), {
    target: { value: "Bản nháp thuộc phiên cũ" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng vào nháp" }));
  expect(screen.getByText("Bản nháp thuộc phiên cũ")).toBeTruthy();

  clearAccessToken();
  await waitFor(() =>
    expect(screen.queryByText("Bản nháp thuộc phiên cũ")).toBeNull(),
  );
});
