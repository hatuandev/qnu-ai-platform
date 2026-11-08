// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import {
  clearAccessToken,
  getTokenState,
  setAccessToken,
} from "@/app/api/v1/session-token";
import { RevisionUploadDialog } from "@/features/knowledge/revision-upload-dialog";
import { DocumentReplacement } from "@/features/lifecycle/document-replacement";

const ports = vi.hoisted(() => ({ upload: vi.fn() }));
vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({ sessionId: getTokenState().sessionId }),
}));
vi.mock("@/features/knowledge/queries", () => ({
  useAddRevision: () => ({ mutateAsync: ports.upload, isPending: false }),
}));
vi.mock("@/components/admin/file-upload", () => ({
  FileUpload: ({
    onFilesChange,
  }: {
    onFilesChange: (files: File[]) => void;
  }) => (
    <button
      type="button"
      onClick={() =>
        onFilesChange([
          new File(["%PDF-synthetic"], "replacement.pdf", {
            type: "application/pdf",
          }),
        ])
      }
    >
      Chọn PDF thử
    </button>
  ),
}));
vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children }: { children: ReactNode }) => (
    <a href="#synthetic-sources">{children}</a>
  ),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
const clients: QueryClient[] = [];
beforeEach(() => {
  setAccessToken("synthetic-replacement-session");
  ports.upload.mockReset();
  ports.upload.mockResolvedValue({});
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
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify([
            { id: "draft", version_no: 3, status: "draft" },
            { id: "approved", version_no: 2, status: "approved" },
            { id: "published", version_no: 1, status: "published" },
          ]),
          { headers: { "Content-Type": "application/json" } },
        ),
    ),
  );
});
afterEach(() => {
  cleanup();
  for (const client of clients.splice(0)) client.clear();
  clearAccessToken();
  vi.unstubAllGlobals();
});
function mount(element: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
      mutations: { retry: false },
    },
  });
  clients.push(client);
  return render(
    <QueryClientProvider client={client}>{element}</QueryClientProvider>,
  );
}
test("revision upload defaults to staged mode, preserving the serving revision", async () => {
  mount(
    <RevisionUploadDialog
      workspaceId="w"
      collectionId="c"
      sourceId="s"
      open
      onOpenChange={vi.fn()}
    />,
  );
  expect(screen.getByRole("checkbox").getAttribute("data-state")).toBe(
    "checked",
  );
  fireEvent.click(screen.getByRole("button", { name: "Chọn PDF thử" }));
  fireEvent.click(screen.getByRole("button", { name: /^Tải lên$/ }));
  await waitFor(() => expect(ports.upload).toHaveBeenCalledTimes(1));
  expect(ports.upload.mock.calls[0][0]).toEqual(
    expect.objectContaining({
      staged: true,
      file: expect.any(File),
      idempotencyKey: expect.any(String),
    }),
  );
});
test("changing upload mode gives the new intent a new key, while a retry retains the old key", async () => {
  ports.upload.mockRejectedValue(new Error("Synthetic uncertain upload"));
  mount(
    <RevisionUploadDialog
      workspaceId="w"
      collectionId="c"
      sourceId="s"
      open
      onOpenChange={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Chọn PDF thử" }));
  const submit = screen.getByRole("button", { name: /^Tải lên$/ });
  fireEvent.click(submit);
  await waitFor(() => expect(ports.upload).toHaveBeenCalledTimes(1));
  fireEvent.click(submit);
  await waitFor(() => expect(ports.upload).toHaveBeenCalledTimes(2));
  expect(ports.upload.mock.calls[1][0].idempotencyKey).toBe(
    ports.upload.mock.calls[0][0].idempotencyKey,
  );
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(submit);
  await waitFor(() => expect(ports.upload).toHaveBeenCalledTimes(3));
  expect(ports.upload.mock.calls[2][0].staged).toBe(false);
  expect(ports.upload.mock.calls[2][0].idempotencyKey).not.toBe(
    ports.upload.mock.calls[0][0].idempotencyKey,
  );
});
test("changing source clears the selected replacement file instead of uploading it to the new source", async () => {
  const close = vi.fn();
  const view = mount(
    <RevisionUploadDialog
      workspaceId="w"
      collectionId="c"
      sourceId="source-one"
      open
      onOpenChange={close}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Chọn PDF thử" }));
  view.rerender(
    <QueryClientProvider client={clients[0]}>
      <RevisionUploadDialog
        workspaceId="w"
        collectionId="c"
        sourceId="source-two"
        open
        onOpenChange={close}
      />
    </QueryClientProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: /^Tải lên$/ }));
  await act(async () => {
    await Promise.resolve();
  });
  expect(ports.upload).not.toHaveBeenCalled();
});
test("only an approved version is selectable for replacement, never draft or published", async () => {
  mount(
    <DocumentReplacement
      workspaceId="w"
      collectionId="c"
      documentId="doc"
      title="Synthetic document"
    />,
  );
  const combo = await screen.findByRole("combobox", {
    name: "Phiên bản thay thế đã duyệt",
  });
  expect(
    screen
      .getByRole("button", { name: "Xem trước thay bản" })
      .hasAttribute("disabled"),
  ).toBe(true);
  fireEvent.keyDown(combo, { key: "ArrowDown" });
  expect(
    await screen.findByRole("option", { name: "Phiên bản 2 · Đã duyệt" }),
  ).toBeTruthy();
  expect(screen.queryByRole("option", { name: /Phiên bản 3/ })).toBeNull();
  expect(screen.queryByRole("option", { name: /Phiên bản 1/ })).toBeNull();
  expect(
    screen.getByText(
      /bản xuất bản hiện tại được giữ nguyên trong lúc chuẩn bị/,
    ),
  ).toBeTruthy();
});
