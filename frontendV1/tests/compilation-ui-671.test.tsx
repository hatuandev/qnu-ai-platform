// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { CompilationEditorTab } from "../src/features/knowledge/compilation-editor-tab";
import { CompilationReviewTab } from "../src/features/knowledge/compilation-review-tab";
import { ReviewGateDialog } from "../src/features/knowledge/review-gate-dialog";

const ports = vi.hoisted(() => ({
  preview: vi.fn(),
  accept: vi.fn(),
  download: vi.fn(),
  autoReview: {
    data: {
      notScheduled: true,
      status: "none",
      review_id: null as string | null,
    },
  },
}));
vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  useBlocker: () => ({ status: "idle" }),
}));
vi.mock("@/app/auth/v1", () => ({ useV1Auth: () => ({ sessionId: 1 }) }));
vi.mock("@/features/modelops/queries", () => ({
  useCatalogQuery: () => ({ data: [] }),
}));
vi.mock("@/features/knowledge/compilation-requests", () => ({
  downloadCompilationReviewMarkdownBlob: ports.download,
}));
const content = (id: string) => ({
  title: `Document ${id}`,
  sections: [
    {
      heading: "Section",
      paragraphs: [{ text: "Original paragraph", citations: ["ocr:ev"] }],
    },
  ],
  unknowns: [],
});
const finding = {
  direction: "source_to_draft",
  status: "omitted",
  explanation: "Missing admission condition",
  suggested_action: "Restore the condition",
  sources: [{ id: "s1", text: "Source condition", page: 1 }],
  draft_excerpts: [],
};
const report = {
  review_id: "r1",
  verdict: "needs_attention",
  summary: { finding_count: 1 },
  findings: [finding],
  source_assessments: [],
  draft_assessments: [],
  limits: [],
};
const gateData = {
  review_id: "r1",
  report_sha256: "a".repeat(64),
  verdict: "needs_attention",
  findings: [{ finding_id: "b".repeat(64), finding }],
};
vi.mock("@/features/knowledge/compilation-queries", () => ({
  useEditContextQuery: (_w: string, _c: string, id: string) => ({
    data: {
      content: content(id),
      bundle_sha256: id.padEnd(64, "a"),
      citations: { "ocr:ev": {} },
      source_tables: [],
      edit_count: 0,
    },
  }),
  useCompilationReviewsQuery: () => ({ data: [] }),
  useCreateEditPreviewMutation: () => ({
    mutateAsync: ports.preview,
    isPending: false,
  }),
  useAcceptEditMutation: () => ({
    mutateAsync: ports.accept,
    isPending: false,
  }),
  useAutoReviewQuery: () => ports.autoReview,
  useCompilationReviewQuery: () => ({
    data: { id: "r1", status: "completed", provider_id: "model" },
  }),
  useCompilationReviewReportQuery: () => ({ data: report }),
  useCreateReviewMutation: () => ({ isPending: false }),
}));
vi.mock("@/features/knowledge/publication-queries", () => ({
  useCompiledVersionReviewGateQuery: () => ({ data: gateData }),
  useDecisionPreviewMutation: () => ({
    mutateAsync: ports.preview,
    isPending: false,
  }),
}));
const props = {
  workspaceId: "w",
  collectionId: "c",
  runId: "A",
  canEdit: true,
};
beforeEach(() => {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  ports.autoReview.data = {
    notScheduled: true,
    status: "none",
    review_id: null,
  };
  ports.preview.mockResolvedValue({
    preview_id: "p",
    preview_sha256: "a".repeat(64),
    expires_at: "2099-01-01",
    before: content("B"),
    after: content("B"),
    reason: "A review change",
  });
});
afterEach(cleanup);

test("F1: switching to another run cannot submit the previous draft with the new hash", async () => {
  const view = render(<CompilationEditorTab {...props} />);
  fireEvent.change(await screen.findByLabelText(/Tiêu đề bản biên soạn/), {
    target: { value: "A edited" },
  });
  view.rerender(<CompilationEditorTab {...props} runId="B" />);
  await waitFor(() =>
    expect(
      (screen.getByLabelText(/Tiêu đề bản biên soạn/) as HTMLInputElement)
        .value,
    ).toBe("Document B"),
  );
  fireEvent.change(screen.getByLabelText(/Lý do/), {
    target: { value: "A review change" },
  });
  fireEvent.click(screen.getByRole("button", { name: /Xem trước thay đổi/ }));
  await waitFor(() =>
    expect(ports.preview).toHaveBeenCalledWith(
      expect.objectContaining({
        content: expect.objectContaining({ title: "Document B" }),
      }),
    ),
  );
});

test("F4: changing a section heading retains its DOM node, focus and caret", async () => {
  render(<CompilationEditorTab {...props} />);
  const input = (await screen.findByPlaceholderText(
    "Tiêu đề mục...",
  )) as HTMLInputElement;
  input.focus();
  fireEvent.change(input, { target: { value: "Section X" } });
  expect(screen.getByPlaceholderText("Tiêu đề mục...")).toBe(input);
  expect(document.activeElement).toBe(input);
  expect(input.value).toBe("Section X");
});

test("F1: a preview from a previous workspace cannot open in the newly selected workspace", async () => {
  let resolvePreview: (value: unknown) => void = () => {};
  ports.preview.mockReturnValue(
    new Promise((resolve) => {
      resolvePreview = resolve;
    }),
  );
  const view = render(<CompilationEditorTab {...props} />);
  fireEvent.change(await screen.findByLabelText(/Lý do/), {
    target: { value: "Review change" },
  });
  fireEvent.click(screen.getByRole("button", { name: /Xem trước thay đổi/ }));
  await waitFor(() => expect(ports.preview).toHaveBeenCalled());
  view.rerender(
    <CompilationEditorTab {...props} workspaceId="other-workspace" />,
  );
  resolvePreview({
    preview_id: "old-preview",
    preview_sha256: "a".repeat(64),
    expires_at: "2099-01-01",
    before: content("A"),
    after: content("A"),
  });
  await waitFor(() =>
    expect((screen.getByLabelText(/Lý do/) as HTMLInputElement).value).toBe(""),
  );
  expect(screen.queryByRole("dialog")).toBeNull();
});

test("F6: an automatic review is shown even before the list refreshes", async () => {
  ports.autoReview.data = {
    notScheduled: false,
    status: "completed",
    review_id: "r1",
  };
  render(<CompilationReviewTab {...props} canReview={false} />);
  expect(await screen.findByText("Missing admission condition")).toBeTruthy();
  ports.download.mockRejectedValue(new Error("synthetic download failure"));
  fireEvent.click(screen.getByRole("button", { name: /Tải Markdown báo cáo/ }));
  await waitFor(() => expect(ports.download).toHaveBeenCalled());
  expect(ports.download.mock.calls[0][0]).toEqual(
    expect.objectContaining({ requestBlob: expect.any(Function) }),
  );
});

test("New publication: human reviewers can read the actual finding and source excerpt", async () => {
  render(
    <ReviewGateDialog
      workspaceId="w"
      collectionId="c"
      documentId="d"
      versionId="v"
      versionNo={1}
      retrievalMetadata={[]}
      retrievalMetadataSha256={""}
      isOpen
      onClose={() => {}}
      onPreviewSuccess={() => {}}
    />,
  );
  expect(await screen.findByText("Missing admission condition")).toBeTruthy();
  expect(screen.getByText("Source condition")).toBeTruthy();
  expect(screen.getByText("Restore the condition")).toBeTruthy();
});

test("completed AI review leads to human editing without automatically saving changes", async () => {
  ports.autoReview.data = {
    notScheduled: false,
    status: "completed",
    review_id: "r1",
  };
  const edit = vi.fn();
  render(<CompilationReviewTab {...props} canReview={false} onEdit={edit} />);
  expect(
    await screen.findByText("Người dùng kiểm tra trước khi duyệt"),
  ).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "Xem và chỉnh sửa bản biên soạn" }),
  );
  expect(edit).toHaveBeenCalledTimes(1);
  expect(ports.preview).not.toHaveBeenCalled();
  expect(ports.accept).not.toHaveBeenCalled();
});

test("a viewer can read the review but has no transition to editing", async () => {
  ports.autoReview.data = {
    notScheduled: false,
    status: "completed",
    review_id: "r1",
  };
  render(<CompilationReviewTab {...props} canReview={false} />);
  expect(await screen.findByText("Missing admission condition")).toBeTruthy();
  expect(
    screen.queryByRole("button", { name: "Xem và chỉnh sửa bản biên soạn" }),
  ).toBeNull();
});

test("a kept inactive review tab does not leave its request dialog over another tab", async () => {
  const view = render(<CompilationReviewTab {...props} canReview />);
  fireEvent.click(
    screen.getByRole("button", { name: "Yêu cầu Review thủ công" }),
  );
  expect(await screen.findByRole("dialog")).toBeTruthy();
  view.rerender(<CompilationReviewTab {...props} canReview isActive={false} />);
  expect(screen.queryByRole("dialog")).toBeNull();
});

test("human compiler edits require preview then explicit save of the new version", async () => {
  ports.accept.mockResolvedValue({ run: { id: "child" }, created: true });
  const onChild = vi.fn();
  render(<CompilationEditorTab {...props} onNavigateToChild={onChild} />);
  fireEvent.change(await screen.findByLabelText(/Tiêu đề bản biên soạn/), {
    target: { value: "Corrected title" },
  });
  fireEvent.change(screen.getByLabelText(/Lý do/), {
    target: { value: "Corrected after reading the evidence" },
  });
  expect(ports.accept).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: /Xem trước thay đổi/ }));
  await screen.findByRole("dialog");
  expect(ports.preview).toHaveBeenCalledWith(
    expect.objectContaining({
      expected_bundle_sha256: "A".padEnd(64, "a"),
      content: expect.objectContaining({ title: "Corrected title" }),
    }),
  );
  expect(ports.accept).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Xác nhận tạo bản mới" }));
  await waitFor(() => expect(onChild).toHaveBeenCalledWith("child"));
  expect(ports.accept).toHaveBeenCalledWith(
    expect.objectContaining({
      input: {
        preview_id: "p",
        preview_sha256: "a".repeat(64),
      },
    }),
  );
});
