// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { KnowledgeDetailPage } from "@/features/knowledge/knowledge-detail-page";

const state = vi.hoisted(() => ({
  moveSourceMutate: vi.fn(),
  role: { kind: "platform-admin" } as { kind: string; role?: string },
  movePending: false,
  sessionId: 1,
}));

vi.mock("@/app/auth/v1", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/app/auth/v1")>()),
  useV1Auth: () => ({
    isAuthenticated: true,
    sessionId: state.sessionId,
    actor: { roles: ["AI.Admin"] },
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
  useIndexRunsQuery: () => ({ data: [], isLoading: false, isError: false }),
  useRequestIndexMutation: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useSearchMutation: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock("@/features/knowledge/queries", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/features/knowledge/queries")>();
  return {
    ...actual,
    useCollectionQuery: () => ({
      data: { id: "col-1", name: "Kho tri thức Demo", source_count: 2 },
      isLoading: false,
    }),
    useFoldersQuery: () => ({
      data: [
        {
          id: "folder-1",
          collection_id: "col-1",
          parent_id: null,
          name: "Thư mục tài liệu",
          source_count: 0,
          subfolder_count: 0,
          created_at: "2026-11-01T00:00:00Z",
          updated_at: "2026-11-01T00:00:00Z",
        },
      ],
      isError: false,
      refetch: vi.fn(),
    }),
    useSourcesQuery: () => ({
      data: {
        items: [
          {
            id: "source-1",
            collection_id: "col-1",
            folder_id: null,
            title: "Bao_cao_2026.docx",
            file_name: "Bao_cao_2026.docx",
            content_type:
              "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            current_revision_no: 1,
            size_bytes: 1024,
            status: "processed",
            created_at: "2026-11-01T00:00:00Z",
          },
          {
            id: "source-in-folder",
            collection_id: "col-1",
            folder_id: "folder-1",
            title: "Tai_lieu_trong_thu_muc.pdf",
            file_name: "Tai_lieu_trong_thu_muc.pdf",
            content_type: "application/pdf",
            current_revision_no: 1,
            size_bytes: 2048,
            status: "processed",
            created_at: "2026-11-01T00:00:00Z",
          },
        ],
        meta: { total: 2 },
      },
      isError: false,
      refetch: vi.fn(),
    }),
    useSourceQuery: () => ({ data: undefined }),
    useRevisionsQuery: () => ({
      data: [{ id: "rev-1", revision_no: 1 }],
      isError: false,
      refetch: vi.fn(),
    }),
    useFolderImpactQuery: () => ({
      data: { source_count: 0, subfolder_count: 0 },
      isError: false,
      isPending: false,
      refetch: vi.fn(),
    }),
    useMoveSource: () => ({
      mutate: state.moveSourceMutate,
      isPending: state.movePending,
    }),
  };
});

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

beforeEach(() => {
  state.role = { kind: "platform-admin" };
  state.movePending = false;
  state.sessionId = 1;
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Knowledge Page Drag and Drop", () => {
  function transfer(sourceId = "source-1", type = "application/qnu-source-id") {
    const data: Record<string, string> = { [type]: sourceId };
    return {
      types: [type],
      getData: (key: string) => data[key] ?? "",
      setData: (key: string, value: string) => {
        data[key] = value;
      },
      dropEffect: "none",
      effectAllowed: "all",
    };
  }

  function dragTargets() {
    const document = screen
      .getByText("Bao_cao_2026.docx")
      .closest("[draggable]");
    const folder = screen.getByText("Thư mục tài liệu").closest(".group");
    if (!document || !folder) throw new Error("Missing drag targets");
    return { document, folder };
  }

  function renderPage() {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const pageElement = (workspaceId = "ws-1", knowledgeId = "col-1") => (
      <QueryClientProvider client={queryClient}>
        <KnowledgeDetailPage
          workspaceId={workspaceId}
          knowledgeId={knowledgeId}
          page={1}
          pageSize={20}
          onPageChange={vi.fn()}
          onPageSizeChange={vi.fn()}
        />
      </QueryClientProvider>
    );
    const result = render(pageElement());
    return {
      ...result,
      refresh: (workspaceId?: string, knowledgeId?: string) =>
        result.rerender(pageElement(workspaceId, knowledgeId)),
    };
  }

  it("renders documents with draggable attribute for privileged user", () => {
    renderPage();
    const docTitle = screen.getByText("Bao_cao_2026.docx");
    const docCard = docTitle.closest("[draggable]");
    expect(docCard).not.toBeNull();
    expect(docCard?.getAttribute("draggable")).toBe("true");
  });

  it.each(["text/plain", "application/qnu-source-id"])(
    "rejects an external %s drop without a local drag",
    (type) => {
      renderPage();
      const { folder } = dragTargets();
      const dataTransfer = transfer("source-1", type);
      fireEvent.dragOver(folder, { dataTransfer });
      expect(screen.queryByText("Thả để chuyển vào")).toBeNull();
      fireEvent.drop(folder, { dataTransfer });
      expect(state.moveSourceMutate).not.toHaveBeenCalled();
    },
  );

  it("rejects drops for read-only users", () => {
    state.role = { kind: "member", role: "viewer" };
    renderPage();
    const { document, folder } = dragTargets();
    const dataTransfer = transfer();
    fireEvent.dragStart(document, { dataTransfer });
    fireEvent.drop(folder, { dataTransfer });
    expect(state.moveSourceMutate).not.toHaveBeenCalled();
  });

  it.each(["permission", "pending", "session", "workspace", "collection"])(
    "rejects a local drag after %s changes",
    (change) => {
      const { refresh } = renderPage();
      const { document, folder } = dragTargets();
      const dataTransfer = transfer();
      fireEvent.dragStart(document, { dataTransfer });
      if (change === "permission")
        state.role = { kind: "member", role: "viewer" };
      if (change === "pending") state.movePending = true;
      if (change === "session") state.sessionId += 1;
      refresh(
        change === "workspace" ? "ws-2" : "ws-1",
        change === "collection" ? "col-2" : "col-1",
      );
      fireEvent.drop(folder, { dataTransfer });
      expect(state.moveSourceMutate).not.toHaveBeenCalled();
    },
  );

  it.each(["ended", "mismatched", "plain-text"])(
    "rejects a %s local drag",
    (mode) => {
      renderPage();
      const { document, folder } = dragTargets();
      const dataTransfer = transfer();
      fireEvent.dragStart(document, { dataTransfer });
      if (mode === "ended") fireEvent.dragEnd(document);
      if (mode === "mismatched")
        dataTransfer.setData("application/qnu-source-id", "source-in-folder");
      if (mode === "plain-text")
        dataTransfer.setData("application/qnu-source-id", "");
      fireEvent.drop(folder, { dataTransfer });
      expect(state.moveSourceMutate).not.toHaveBeenCalled();
    },
  );

  it("consumes a successful drag once", () => {
    renderPage();
    const { document, folder } = dragTargets();
    const dataTransfer = transfer();
    fireEvent.dragStart(document, { dataTransfer });
    fireEvent.drop(folder, { dataTransfer });
    fireEvent.drop(folder, { dataTransfer });
    expect(state.moveSourceMutate).toHaveBeenCalledTimes(1);
  });

  it("does not move a document back into the same folder", () => {
    renderPage();
    const document = screen
      .getByText("Tai_lieu_trong_thu_muc.pdf")
      .closest("[draggable]");
    const { folder } = dragTargets();
    if (!document) throw new Error("Missing document");
    const dataTransfer = transfer();
    fireEvent.dragStart(document, { dataTransfer });
    fireEvent.drop(folder, { dataTransfer });
    expect(state.moveSourceMutate).not.toHaveBeenCalled();
  });

  it("handles dragging file over folder and dropping it to trigger moveSource mutation", () => {
    renderPage();
    const folderText = screen.getByText("Thư mục tài liệu");
    const folderCard = folderText.closest(".group");
    expect(folderCard).not.toBeNull();

    // Drag start on document
    const docTitle = screen.getByText("Bao_cao_2026.docx");
    const docCard = docTitle.closest("[draggable]")!;

    const dataTransfer = {
      data: {} as Record<string, string>,
      setData(type: string, val: string) {
        this.data[type] = val;
      },
      getData(type: string) {
        return this.data[type] || "";
      },
      types: ["application/qnu-source-id", "text/plain"],
      dropEffect: "none",
      effectAllowed: "all",
    };

    fireEvent.dragStart(docCard, { dataTransfer });
    expect(dataTransfer.getData("application/qnu-source-id")).toBe("source-1");

    // Drag over folder
    fireEvent.dragOver(folderCard!, { dataTransfer });

    // Expect drop text indicator to appear
    expect(screen.getByText("Thả để chuyển vào")).toBeDefined();

    // Drop on folder
    fireEvent.drop(folderCard!, { dataTransfer });

    // Mutation should be invoked with targetFolderId
    expect(state.moveSourceMutate).toHaveBeenCalledWith(
      {
        sourceId: "source-1",
        targetFolderId: "folder-1",
      },
      expect.any(Object),
    );
  });

  it("shows drop-out zone and moves file to root when inside a subfolder", () => {
    renderPage();

    // Enter subfolder by clicking it
    const folderText = screen.getByText("Thư mục tài liệu");
    fireEvent.click(folderText);

    // Document to drag
    const docTitle = screen.getByText("Tai_lieu_trong_thu_muc.pdf");
    const docCard = docTitle.closest("[draggable]")!;

    const dataTransfer = {
      data: {} as Record<string, string>,
      setData(type: string, val: string) {
        this.data[type] = val;
      },
      getData(type: string) {
        return this.data[type] || "";
      },
      types: ["application/qnu-source-id", "text/plain"],
      dropEffect: "none",
      effectAllowed: "all",
    };

    // Start dragging file inside subfolder
    fireEvent.dragStart(docCard, { dataTransfer });

    // Gốc kho breadcrumb button serves as drop target (Google Drive style)
    const rootBreadcrumbBtn = screen.getByRole("button", { name: /Gốc kho/i });
    expect(rootBreadcrumbBtn).toBeDefined();

    // Drag over Gốc kho
    fireEvent.dragOver(rootBreadcrumbBtn, { dataTransfer });

    // Expect highlight ring to be applied without text change
    expect(rootBreadcrumbBtn.className).toContain("ring-primary");

    // Drop on Gốc kho
    fireEvent.drop(rootBreadcrumbBtn, { dataTransfer });

    // Mutation should be invoked with targetFolderId: null (move to root)
    expect(state.moveSourceMutate).toHaveBeenCalledWith(
      {
        sourceId: "source-in-folder",
        targetFolderId: null,
      },
      expect.any(Object),
    );
  });
});
