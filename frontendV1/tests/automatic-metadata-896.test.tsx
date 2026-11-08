// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { v1Client } from "@/app/api/v1";
import { RegisterDocumentDialog } from "@/features/knowledge/register-document-dialog";

const state = vi.hoisted(() => ({ session: 896 }));
vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({ sessionId: state.session }),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn() } }));
const information = {
  rules_version: "test/v2",
  sha256: "a".repeat(64),
  annotations: [
    {
      target: "paragraph:0:0",
      values: { data_year: 2026 },
      evidence: [{ citation: "ocr:ev", quote: "Mùa tuyển sinh 2026" }],
    },
  ],
};
const props = {
  workspaceId: "ws",
  collectionId: "col",
  compilationRunId: "cmp",
  defaultTitle: "Tuyển sinh",
  isOpen: true,
  onClose: vi.fn(),
  onSuccess: vi.fn(),
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
  state.session = 896;
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.scrollIntoView = () => {};
  Element.prototype.releasePointerCapture = () => {};
  vi.spyOn(v1Client, "get").mockImplementation(
    async (path) =>
      (path.includes("registration-metadata") ? information : []) as never,
  );
  vi.spyOn(v1Client, "post").mockResolvedValue({
    document: { id: "doc" },
    version: { id: "version", version_no: 1 },
    created: true,
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const view = render(
    <QueryClientProvider client={client}>
      <RegisterDocumentDialog {...props} />
    </QueryClientProvider>,
  );
  return {
    ...view,
    client,
    rerenderDialog: (runId = "cmp") =>
      view.rerender(
        <QueryClientProvider client={client}>
          <RegisterDocumentDialog {...props} compilationRunId={runId} />
        </QueryClientProvider>,
      ),
  };
}

test("one create action saves the server preview without selecting metadata", async () => {
  mount();
  const create = screen.getByRole("button", { name: "Tạo tài liệu" });
  await waitFor(() => expect(create.hasAttribute("disabled")).toBe(false));
  expect(screen.queryByRole("checkbox")).toBeNull();
  expect(screen.queryByText("Xác nhận metadata theo nguồn")).toBeNull();
  expect(screen.queryByText("Thông tin tài liệu")).toBeNull();
  expect(screen.queryByText("Năm dữ liệu 2026")).toBeNull();
  expect(screen.queryByRole("radio")).toBeNull();
  fireEvent.click(create);
  await waitFor(() => expect(v1Client.post).toHaveBeenCalledTimes(1));
  const [, body, options] = vi.mocked(v1Client.post).mock.calls[0];
  expect(body).toEqual({
    document_key: "tuyen-sinh",
    title: "Tuyển sinh",
    compilation_run_id: "cmp",
    automatic_metadata_sha256: information.sha256,
  });
  expect(options?.idempotencyKey).toMatch(/^pub_cmp_/);
});

test("no grounded information still allows registration without inventing values", async () => {
  vi.mocked(v1Client.get).mockImplementation(
    async (path) =>
      (path.includes("registration-metadata")
        ? { ...information, annotations: [] }
        : []) as never,
  );
  mount();
  const create = screen.getByRole("button", { name: "Tạo tài liệu" });
  await waitFor(() => expect(create.hasAttribute("disabled")).toBe(false));
  expect(screen.queryByText("Thông tin tài liệu")).toBeNull();
  fireEvent.click(create);
  await waitFor(() => expect(v1Client.post).toHaveBeenCalledTimes(1));
  expect(vi.mocked(v1Client.post).mock.calls[0][1]).not.toHaveProperty(
    "retrieval_metadata",
  );
});

test("read errors block submit and reload only the preview, never create a document", async () => {
  let broken = true;
  vi.mocked(v1Client.get).mockImplementation(async (path) => {
    if (!path.includes("registration-metadata")) return [] as never;
    if (broken) throw new Error("offline");
    return information as never;
  });
  mount();
  expect(await screen.findByText("Chưa chuẩn bị được tài liệu.")).toBeTruthy();
  const create = screen.getByRole("button", { name: "Tạo tài liệu" });
  expect(create.hasAttribute("disabled")).toBe(true);
  expect(v1Client.post).not.toHaveBeenCalled();
  broken = false;
  fireEvent.click(screen.getByRole("button", { name: "Tải lại" }));
  await waitFor(() => expect(create.hasAttribute("disabled")).toBe(false));
  expect(v1Client.post).not.toHaveBeenCalled();
});

test("preview cache is bound to login session and selected compiler run", async () => {
  const view = mount();
  await waitFor(() =>
    expect(
      screen
        .getByRole("button", { name: "Tạo tài liệu" })
        .hasAttribute("disabled"),
    ).toBe(false),
  );
  state.session = 897;
  view.rerenderDialog("cmp-next");
  await waitFor(() =>
    expect(
      vi
        .mocked(v1Client.get)
        .mock.calls.some(([path]) =>
          path.endsWith("/registration-metadata/cmp-next"),
        ),
    ).toBe(true),
  );
  const keys = view.client
    .getQueryCache()
    .getAll()
    .filter((q) => q.queryKey.includes("registration-metadata"))
    .map((q) => q.queryKey);
  expect(keys).toHaveLength(2);
  expect(keys[0]).toContain(896);
  expect(keys[1]).toContain(897);
  expect(keys[1]).toContain("cmp-next");
});

test("existing targets enable version registration with automatic source information", async () => {
  vi.mocked(v1Client.get).mockImplementation(
    async (path) =>
      (path.includes("registration-metadata")
        ? information
        : [
            {
              id: "doc-target",
              title: "Tài liệu đã có",
              document_key: "tai-lieu",
            },
          ]) as never,
  );
  mount();
  fireEvent.click(
    await screen.findByRole("radio", { name: /Thêm phiên bản mới/ }),
  );
  const submit = screen.getByRole("button", { name: "Thêm phiên bản" });
  expect(submit.hasAttribute("disabled")).toBe(true);
  fireEvent.keyDown(screen.getByRole("combobox"), { key: "ArrowDown" });
  fireEvent.click(
    await screen.findByRole("option", { name: /Tài liệu đã có/ }),
  );
  await waitFor(() => expect(submit.hasAttribute("disabled")).toBe(false));
  fireEvent.click(submit);
  await waitFor(() => expect(v1Client.post).toHaveBeenCalledTimes(1));
  const [path, body] = vi.mocked(v1Client.post).mock.calls[0];
  expect(path).toBe(
    "/workspaces/ws/collections/col/compiled-documents/doc-target/versions",
  );
  expect(body).toEqual({
    compilation_run_id: "cmp",
    automatic_metadata_sha256: information.sha256,
  });
});

test("document-list failure is visible and can be reloaded without a write", async () => {
  let broken = true;
  vi.mocked(v1Client.get).mockImplementation(async (path) => {
    if (path.includes("registration-metadata")) return information as never;
    if (broken) throw new Error("offline");
    return [
      { id: "doc-target", title: "Tài liệu đã có", document_key: "tai-lieu" },
    ] as never;
  });
  mount();
  await screen.findByText(/Chưa tải được danh sách tài liệu/);
  expect(screen.queryByRole("radio")).toBeNull();
  broken = false;
  fireEvent.click(screen.getByRole("button", { name: "Tải lại danh sách" }));
  expect(
    await screen.findByRole("radio", { name: /Thêm phiên bản mới/ }),
  ).toBeTruthy();
  expect(v1Client.post).not.toHaveBeenCalled();
});

test("a removed destination cannot receive a stale version submission", async () => {
  let documents = [
    { id: "doc-target", title: "Tài liệu đã có", document_key: "tai-lieu" },
  ];
  vi.mocked(v1Client.get).mockImplementation(
    async (path) =>
      (path.includes("registration-metadata")
        ? information
        : documents) as never,
  );
  const view = mount();
  fireEvent.click(
    await screen.findByRole("radio", { name: /Thêm phiên bản mới/ }),
  );
  fireEvent.keyDown(screen.getByRole("combobox"), { key: "ArrowDown" });
  fireEvent.click(
    await screen.findByRole("option", { name: /Tài liệu đã có/ }),
  );
  documents = [];
  await view.client.invalidateQueries();
  await waitFor(() => expect(screen.queryByRole("radio")).toBeNull());
  const create = screen.getByRole("button", { name: "Tạo tài liệu" });
  await waitFor(() => expect(create.hasAttribute("disabled")).toBe(false));
  fireEvent.click(create);
  await waitFor(() => expect(v1Client.post).toHaveBeenCalledTimes(1));
  expect(vi.mocked(v1Client.post).mock.calls[0][0]).toBe(
    "/workspaces/ws/collections/col/compiled-documents",
  );
});
