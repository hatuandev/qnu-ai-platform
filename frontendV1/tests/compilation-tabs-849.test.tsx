// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { CompilationDetailPage } from "@/features/knowledge/compilation-detail-page";
import { CompilationEditorTab } from "@/features/knowledge/compilation-editor-tab";

const ports = vi.hoisted(() => ({
  session: 1,
  status: "completed",
  selective: false,
  incomplete: false,
  preview: vi.fn(),
  blocker: vi.fn(),
}));
vi.mock("@tanstack/react-router", () => ({
  Link: ({ children }: PropsWithChildren) => <span>{children}</span>,
  useNavigate: () => vi.fn(),
  useBlocker: (options: unknown) => {
    ports.blocker(options);
    return { status: "idle" };
  },
}));
vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({ sessionId: ports.session }),
}));
vi.mock("@/features/workspaces/queries", () => ({
  useCallerWorkspaceRole: () => ({
    role: { kind: "platform-admin" },
    isPending: false,
  }),
}));
vi.mock("@/features/knowledge/queries", () => ({
  useCollectionQuery: () => ({ data: { name: "Collection" } }),
}));
vi.mock("@/features/knowledge/compilation-review-tab", () => ({
  CompilationReviewTab: () => <p>Review progress</p>,
}));
vi.mock("@/features/knowledge/citation-drawer", () => ({
  CitationDrawer: () => null,
}));
vi.mock("@/features/knowledge/register-document-dialog", () => ({
  RegisterDocumentDialog: () => null,
}));
const content = (id: string) => ({
  title: `Document ${id}`,
  sections: [
    {
      heading: "First section",
      paragraphs: [{ text: "First paragraph", citations: ["ev-0"] }],
    },
  ],
  unknowns: [],
});
const citations = Object.fromEntries(
  Array.from({ length: 45 }, (_, i) => [
    `ev-${i}`,
    { filename: "Source.pdf", page: i + 1 },
  ]),
);
vi.mock("@/features/knowledge/compilation-queries", () => ({
  useCompilationRunQuery: (_w: string, _c: string, id: string) => ({
    data: {
      id,
      status: ports.status,
      selective_supplement: ports.selective,
      topic: "Topic",
      origin: "ai_compiler",
      generation: 1,
      usage_tokens: 1,
    },
  }),
  useCompilationDraftQuery: (_w: string, _c: string, id: string) => ({
    data: {
      ...content(id),
      sources: [],
      source_tables: [],
      citations,
      ...(ports.incomplete
        ? {
            supplement: {
              state: "incomplete",
              metadata: [],
              sections: [],
              incomplete_groups: [
                { index: 1, code: "compilation_draft_invalid" },
              ],
            },
          }
        : {}),
    },
  }),
  useEditContextQuery: (_w: string, _c: string, id: string) => ({
    data: {
      content: content(id),
      bundle_sha256: id,
      citations,
      source_tables: [],
      edit_count: 0,
    },
  }),
  useCompilationReviewsQuery: () => ({ data: [] }),
  useCreateEditPreviewMutation: () => ({
    mutateAsync: ports.preview,
    isPending: false,
  }),
  useAcceptEditMutation: () => ({ isPending: false }),
}));
const props = { workspaceId: "w", collectionId: "c", runId: "A" };
beforeEach(() => {
  ports.session = 1;
  ports.status = "completed";
  ports.selective = false;
  ports.incomplete = false;
  ports.preview.mockReset();
  ports.blocker.mockClear();
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
  vi.unstubAllGlobals();
});

test("shows the source draft early and reports incomplete AI after completion", () => {
  ports.status = "running";
  ports.selective = true;
  const view = render(<CompilationDetailPage {...props} />);
  expect(screen.getByText("First paragraph")).toBeTruthy();
  expect(
    screen.queryByRole("button", { name: "Đăng ký thành tài liệu biên soạn" }),
  ).toBeNull();
  ports.status = "completed";
  ports.incomplete = true;
  view.rerender(<CompilationDetailPage {...props} />);
  expect(screen.getByText("First paragraph")).toBeTruthy();
  expect(
    screen.getByText("Bản nháp đã sẵn sàng. Phần AI chưa hoàn tất."),
  ).toBeTruthy();
  expect(
    screen.getByRole("button", { name: "Đăng ký thành tài liệu biên soạn" }),
  ).toBeTruthy();
});

test("a tab is created on first visit and retains the editor DOM and unsaved text across other tabs", async () => {
  render(<CompilationDetailPage {...props} />);
  expect(screen.queryByLabelText(/Tiêu đề bản biên soạn/)).toBeNull();
  fireEvent.keyDown(
    screen.getByRole("tab", { name: "Chỉnh sửa bản biên soạn" }),
    { key: "Enter" },
  );
  const title = await screen.findByLabelText(/Tiêu đề bản biên soạn/);
  fireEvent.change(title, { target: { value: "Unsaved correction" } });
  fireEvent.keyDown(screen.getByRole("tab", { name: "Rà soát & Đánh giá" }), {
    key: "Enter",
  });
  expect(title.isConnected).toBe(true);
  expect(
    screen.queryByRole("textbox", { name: /Tiêu đề bản biên soạn/ }),
  ).toBeNull();
  fireEvent.keyDown(
    screen.getByRole("tab", { name: "Bản biên soạn & Dẫn chứng" }),
    { key: "Enter" },
  );
  fireEvent.keyDown(
    screen.getByRole("tab", { name: "Chỉnh sửa bản biên soạn" }),
    { key: "Enter" },
  );
  expect(screen.getByLabelText(/Tiêu đề bản biên soạn/)).toBe(title);
  expect((title as HTMLInputElement).value).toBe("Unsaved correction");
  expect(ports.preview).not.toHaveBeenCalled();
});

test("kept tabs reset on another run or auth session", async () => {
  const view = render(<CompilationDetailPage {...props} initialTab="edit" />);
  fireEvent.change(await screen.findByLabelText(/Tiêu đề bản biên soạn/), {
    target: { value: "Private draft" },
  });
  view.rerender(
    <CompilationDetailPage {...props} runId="B" initialTab="edit" />,
  );
  await waitFor(() =>
    expect(
      (screen.getByLabelText(/Tiêu đề bản biên soạn/) as HTMLInputElement)
        .value,
    ).toBe("Document B"),
  );
  fireEvent.change(screen.getByLabelText(/Tiêu đề bản biên soạn/), {
    target: { value: "Session draft" },
  });
  ports.session = 2;
  view.rerender(
    <CompilationDetailPage {...props} runId="B" initialTab="edit" />,
  );
  await waitFor(() =>
    expect(
      (screen.getByLabelText(/Tiêu đề bản biên soạn/) as HTMLInputElement)
        .value,
    ).toBe("Document B"),
  );
});

test("unsaved edits allow search-only tab navigation while leaving the page stays protected", async () => {
  render(<CompilationEditorTab {...props} canEdit />);
  fireEvent.change(await screen.findByLabelText(/Tiêu đề bản biên soạn/), {
    target: { value: "Unsaved" },
  });
  const options = ports.blocker.mock.lastCall?.[0] as {
    shouldBlockFn: (args: {
      current: { pathname: string };
      next: { pathname: string };
    }) => boolean;
    enableBeforeUnload: () => boolean;
  };
  expect(
    options.shouldBlockFn({
      current: { pathname: "/compilations/A" },
      next: { pathname: "/compilations/A" },
    }),
  ).toBe(false);
  expect(
    options.shouldBlockFn({
      current: { pathname: "/compilations/A" },
      next: { pathname: "/compilations/B" },
    }),
  ).toBe(true);
  expect(options.enableBeforeUnload()).toBe(true);
});

test("citation choices are mounted on demand, paginated and retained when changing page", async () => {
  render(<CompilationEditorTab {...props} canEdit />);
  await screen.findByLabelText(/Tiêu đề bản biên soạn/);
  expect(screen.queryByRole("checkbox")).toBeNull();
  fireEvent.keyDown(screen.getByRole("button", { name: "Thao tác đoạn 1.1" }), {
    key: "Enter",
  });
  fireEvent.click(
    await screen.findByRole("menuitem", { name: "Chọn dẫn chứng" }),
  );
  const dialog = await screen.findByRole("dialog", {
    name: "Dẫn chứng cho đoạn văn",
  });
  expect(within(dialog).getAllByRole("checkbox")).toHaveLength(20);
  expect(
    within(dialog).getAllByRole("checkbox")[0].getAttribute("data-state"),
  ).toBe("checked");
  fireEvent.click(within(dialog).getByRole("button", { name: "Trang sau" }));
  expect(within(dialog).getByText("Dẫn chứng 21 · Trang 21")).toBeTruthy();
  fireEvent.click(within(dialog).getAllByRole("checkbox")[0]);
  fireEvent.click(within(dialog).getByRole("button", { name: "Trang trước" }));
  expect(
    within(dialog).getAllByRole("checkbox")[0].getAttribute("data-state"),
  ).toBe("checked");
  expect(within(dialog).getByText("Đã chọn 2 dẫn chứng.")).toBeTruthy();
  fireEvent.click(within(dialog).getByRole("button", { name: "Xong" }));
  fireEvent.change(screen.getByLabelText(/Lý do/), {
    target: { value: "Evidence correction" },
  });
  ports.preview.mockImplementation(() => new Promise(() => {}));
  fireEvent.click(screen.getByRole("button", { name: /Xem trước thay đổi/ }));
  await waitFor(() =>
    expect(ports.preview).toHaveBeenCalledWith(
      expect.objectContaining({
        content: expect.objectContaining({
          sections: [
            {
              heading: "First section",
              paragraphs: [
                { text: "First paragraph", citations: ["ev-0", "ev-20"] },
              ],
            },
          ],
        }),
      }),
    ),
  );
});
