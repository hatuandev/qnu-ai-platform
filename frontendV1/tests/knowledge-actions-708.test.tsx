// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { FolderDeleteDialog } from "@/features/knowledge/folder-delete-dialog";
import { KnowledgeDetailPage } from "@/features/knowledge/knowledge-detail-page";
import { StageOcrPanel } from "@/features/knowledge/stage-ocr-panel";

const state = vi.hoisted(() => ({
  role: { kind: "platform-admin" } as { kind: string; role?: string },
  sourcesError: false,
  foldersError: false,
  impactError: false,
  impactCount: 0,
  revisionsError: false,
  refetch: vi.fn(),
  remove: vi.fn(),
}));
vi.mock("@/app/auth/v1", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/app/auth/v1")>()),
  useV1Auth: () => ({
    isAuthenticated: true,
    sessionId: 1,
    actor:
      state.role.kind === "platform-admin"
        ? { roles: ["AI.Admin"] }
        : { roles: [] },
  }),
}));
vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children, to }: { children: ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));
vi.mock("@/features/workspaces/queries", () => ({
  useCallerWorkspaceRole: () => ({ role: state.role, isPending: false }),
}));
vi.mock("@/features/knowledge/compilation-queries", async (importOriginal) => ({
  ...(await importOriginal<
    typeof import("@/features/knowledge/compilation-queries")
  >()),
  useCompilationRunsQuery: () => ({
    data: [],
    isLoading: false,
    isError: false,
  }),
  useCreateCompilationMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));
vi.mock("@/features/knowledge/publication-queries", () => ({
  useCompiledDocumentsQuery: () => ({
    data: [],
    isLoading: false,
    isError: false,
  }),
}));
vi.mock("@/features/knowledge/index-queries", async (importOriginal) => ({
  ...(await importOriginal<
    typeof import("@/features/knowledge/index-queries")
  >()),
  useIndexRunsQuery: () => ({
    data: [],
    isLoading: false,
    isError: false,
  }),
  useRequestIndexMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useSearchMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));
vi.mock("@/features/knowledge/queries", () => ({
  useCollectionQuery: () => ({
    data: { id: "c", name: "Kho thử", source_count: 1 },
    isLoading: false,
  }),
  useFoldersQuery: () => ({
    data: [],
    isError: state.foldersError,
    error: new Error("Folder unavailable"),
    refetch: state.refetch,
  }),
  useSourcesQuery: () => ({
    data: {
      items: [
        {
          id: "s",
          title: "Tài liệu thử",
          file_name: "sample.pdf",
          content_type: "application/pdf",
          current_revision_no: 1,
          size_bytes: 42,
          status: "uploaded",
          created_at: "2026-10-29T00:00:00Z",
        },
      ],
      meta: { total: 1 },
    },
    isError: state.sourcesError,
    error: new Error("Source unavailable"),
    refetch: state.refetch,
  }),
  useSourceQuery: () => ({ data: undefined }),
  useRevisionsQuery: () => ({
    data: state.revisionsError
      ? undefined
      : [{ id: "revision-1", revision_no: 1 }],
    isError: state.revisionsError,
    error: new Error("Revision unavailable"),
    refetch: state.refetch,
  }),
  useFolderImpactQuery: () => ({
    data: state.impactError
      ? undefined
      : { source_count: state.impactCount, subfolder_count: 0 },
    isError: state.impactError,
    isPending: false,
    refetch: state.refetch,
  }),
  useDeleteFolder: () => ({ mutateAsync: state.remove, isPending: false }),
}));
vi.mock("@/features/knowledge/source-upload-dialog", () => ({
  SourceUploadDialog: () => null,
}));
vi.mock("@/features/knowledge/source-rename-dialog", () => ({
  SourceRenameDialog: () => null,
}));
vi.mock("@/features/knowledge/folder-form-dialog", () => ({
  FolderFormDialog: () => null,
}));
vi.mock("@/features/knowledge/folder-move-dialog", () => ({
  FolderMoveDialog: () => null,
}));
vi.mock("@/features/knowledge/collection-form-dialog", () => ({
  CollectionFormDialog: () => null,
}));
vi.mock("@/features/lifecycle/action-dialog", () => ({
  LifecycleActionDialog: ({
    target,
  }: {
    target: { action: string; resource_id: string };
  }) => (
    <div role="dialog">
      {target.action}:{target.resource_id}
    </div>
  ),
}));
vi.mock("@/features/knowledge/ocr-request-dialog", () => ({
  OcrRequestDialog: () => null,
}));
vi.mock("@/features/knowledge/ocr-tab-container", () => ({
  OcrTabContainer: () => null,
}));

beforeEach(() => {
  vi.stubGlobal("matchMedia", () => ({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
  vi.stubGlobal("PointerEvent", MouseEvent);
  state.role = { kind: "platform-admin" };
  state.sourcesError = state.foldersError = state.impactError = false;
  state.impactCount = 0;
  state.revisionsError = false;
});
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});
afterEach(() => {
  cleanup();
  queryClient.clear();
  vi.clearAllMocks();
});
function page(
  stage: "files" | "compiler" | "publication" | "serving" = "files",
) {
  return render(
    <QueryClientProvider client={queryClient}>
      <KnowledgeDetailPage
        workspaceId="w"
        knowledgeId="c"
        onPageChange={vi.fn()}
        onPageSizeChange={vi.fn()}
        activeStage={stage}
      />
    </QueryClientProvider>,
  );
}

test("source menu exposes recoverable delete for admin with exact source target", () => {
  page();
  fireEvent.pointerDown(
    screen.getByRole("button", { name: "Thao tác: Tài liệu thử" }),
    { button: 0, ctrlKey: false, pointerType: "mouse" },
  );
  fireEvent.click(screen.getByRole("menuitem", { name: /Xóa/ }));
  expect(screen.getByRole("dialog").textContent).toContain("delete:s");
});

test("member source menu keeps read actions without delete", () => {
  state.role = { kind: "member", role: "member" };
  page();
  fireEvent.pointerDown(
    screen.getByRole("button", { name: "Thao tác: Tài liệu thử" }),
    { button: 0, ctrlKey: false, pointerType: "mouse" },
  );
  expect(screen.queryByRole("menuitem", { name: /Xóa/ })).toBeNull();
  expect(screen.getByRole("menuitem", { name: /chi tiết/i })).toBeTruthy();
});

test.each(["compiler", "publication", "serving"] as const)(
  "stage %s displays its embedded working panel",
  async (stage) => {
    page(stage);
    if (stage === "compiler") {
      expect(
        await screen.findByText("Chưa có lượt biên soạn nào"),
      ).toBeTruthy();
    } else if (stage === "publication") {
      expect(await screen.findByText(/Chưa có tài liệu/)).toBeTruthy();
    } else {
      expect(await screen.findByText("Chỉ mục & Tìm kiếm")).toBeTruthy();
    }
  },
);

test("folder error is visible rather than displayed as an empty directory", () => {
  state.foldersError = true;
  page();
  expect(screen.getByText("Folder unavailable")).toBeTruthy();
});

test("OCR source failure is reported instead of an empty or cached document list", () => {
  state.sourcesError = true;
  render(<StageOcrPanel workspaceId="w" collectionId="c" canManage />);
  expect(screen.getByText("Source unavailable")).toBeTruthy();
});

test.each(["failure", "nonempty"])(
  "folder deletion is blocked on impact %s",
  (kind) => {
    state.impactError = kind === "failure";
    state.impactCount = kind === "nonempty" ? 1 : 0;
    render(
      <FolderDeleteDialog
        open
        onOpenChange={vi.fn()}
        workspaceId="w"
        collectionId="c"
        folder={{ id: "f", name: "Thư mục" } as never}
      />,
    );
    expect(
      (
        screen.getByRole("button", {
          name: "Xác nhận xóa",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
  },
);

test("table view has the same document management menu", () => {
  page();
  fireEvent.click(
    screen.getByRole("button", { name: "Xem dạng danh sách bảng" }),
  );
  fireEvent.pointerDown(
    screen.getByRole("button", { name: "Thao tác: Tài liệu thử" }),
    { button: 0, ctrlKey: false, pointerType: "mouse" },
  );
  expect(screen.getByRole("menuitem", { name: "Tải xuống" })).toBeTruthy();
  expect(screen.getByRole("menuitem", { name: /Xóa/ })).toBeTruthy();
});

test("editor may archive sources but cannot delete them", () => {
  state.role = { kind: "member", role: "editor" };
  page();
  fireEvent.pointerDown(
    screen.getByRole("button", { name: "Thao tác: Tài liệu thử" }),
    { button: 0, ctrlKey: false, pointerType: "mouse" },
  );
  expect(screen.getByRole("menuitem", { name: "Lưu trữ" })).toBeTruthy();
  expect(screen.queryByRole("menuitem", { name: "Xóa" })).toBeNull();
});

test("quick OCR reports revision fetch errors in a closeable dialog", () => {
  state.revisionsError = true;
  render(<StageOcrPanel workspaceId="w" collectionId="c" canManage />);
  fireEvent.click(screen.getByRole("button", { name: "Chạy OCR" }));
  expect(screen.getByText("Revision unavailable")).toBeTruthy();
  expect(
    screen.getAllByRole("button", { name: "Đóng", exact: true })[0],
  ).toBeTruthy();
});

test("returning from a controlled OCR selection clears the studio", () => {
  const select = vi.fn();
  const view = render(
    <StageOcrPanel
      workspaceId="w"
      collectionId="c"
      canManage
      selectedSourceId="s"
      onSelectSourceId={select}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Danh sách OCR" }));
  expect(select).toHaveBeenCalledWith(null);
  view.rerender(
    <StageOcrPanel
      workspaceId="w"
      collectionId="c"
      canManage
      selectedSourceId={null}
      onSelectSourceId={select}
    />,
  );
  expect(screen.queryByRole("button", { name: "Danh sách OCR" })).toBeNull();
  expect(screen.getByRole("button", { name: "Chạy OCR" })).toBeTruthy();
});
