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
const saveRequest = vi.hoisted(() => vi.fn());

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
  useSaveTextReviewMutation: () => ({
    mutateAsync: saveRequest,
    isPending: false,
  }),
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
  saveRequest.mockReset();
  saveRequest.mockResolvedValue({});
  data.document = {
    ...data.document,
    version: 0,
    canonical_sha256: "0".repeat(64),
    units: [{ ...data.document.units[0], text: "Văn bản OCR gốc" }],
  };
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

test("editing after a server refresh must retain the OCR conflict until explicit consent", async () => {
  const view = renderContainer();
  fireEvent.click(screen.getByRole("button", { name: "Chỉnh sửa" }));
  fireEvent.change(screen.getByPlaceholderText("Nhập nội dung chỉnh sửa..."), {
    target: { value: "Synthetic initial local correction" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng vào nháp" }));
  data.document = {
    ...data.document,
    version: 1,
    canonical_sha256: "2".repeat(64),
    units: [{ ...data.document.units[0], text: "Synthetic newer server text" }],
  };
  view.rerender(
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
  expect(
    screen.getByText(/Bản nháp thuộc phiên bản v0 nhưng server đã/),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Chỉnh sửa" }));
  fireEvent.change(screen.getByPlaceholderText("Nhập nội dung chỉnh sửa..."), {
    target: { value: "Synthetic second local correction" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng vào nháp" }));
  expect(
    screen.queryByText(/Bản nháp thuộc phiên bản v0 nhưng server đã/),
  ).not.toBeNull();
});

test("a server refresh while save confirmation is open cannot submit the stale draft", async () => {
  const view = renderContainer();
  fireEvent.click(screen.getByRole("button", { name: "Chỉnh sửa" }));
  fireEvent.change(screen.getByPlaceholderText("Nhập nội dung chỉnh sửa..."), {
    target: { value: "Synthetic pending correction" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng vào nháp" }));
  fireEvent.click(screen.getByRole("button", { name: "Lưu (1 thay đổi)" }));
  expect(
    screen
      .getByRole("button", { name: "Xác nhận lưu v1" })
      .hasAttribute("disabled"),
  ).toBe(false);
  data.document = {
    ...data.document,
    version: 1,
    canonical_sha256: "2".repeat(64),
    units: [{ ...data.document.units[0], text: "Synthetic server update" }],
  };
  view.rerender(
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
  const confirm = screen.getByRole("button", { name: "Xác nhận lưu v2" });
  expect(confirm.hasAttribute("disabled")).toBe(true);
  fireEvent.click(confirm);
  expect(saveRequest).not.toHaveBeenCalled();
});

test("explicit rebase permits saving with exactly the new version and hash", async () => {
  const view = renderContainer();
  fireEvent.click(screen.getByRole("button", { name: "Chỉnh sửa" }));
  fireEvent.change(screen.getByPlaceholderText("Nhập nội dung chỉnh sửa..."), {
    target: { value: "Synthetic corrected text" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng vào nháp" }));
  data.document = {
    ...data.document,
    version: 1,
    canonical_sha256: "2".repeat(64),
    units: [{ ...data.document.units[0], text: "Synthetic server update" }],
  };
  view.rerender(
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
  vi.mocked(window.confirm).mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng nháp lên v1" }));
  fireEvent.click(screen.getByRole("button", { name: "Lưu (1 thay đổi)" }));
  fireEvent.click(screen.getByRole("button", { name: "Xác nhận lưu v2" }));
  await waitFor(() =>
    expect(saveRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        body: {
          expected_version: 1,
          expected_sha256: "2".repeat(64),
          changes: [
            {
              evidence_id: "ev-1",
              before: "Synthetic server update",
              after: "Synthetic corrected text",
            },
          ],
        },
      }),
    ),
  );
});
