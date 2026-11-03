// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ConnectionDetail } from "@/features/modelops/connections/connection-detail";

const state = vi.hoisted(() => ({
  apiType: "openai_compatible",
  add: vi.fn(),
  test: vi.fn(),
  checks: [] as Array<{
    key_id: string;
    outcome: string;
    configuration_status: string;
    detail: string;
    tested_at: string;
  }>,
  keys: [
    {
      id: "key-first",
      name: "First key",
      status: "active",
      priority: 1,
      masked_hint: "****1111",
    },
    {
      id: "key-second",
      name: "Second key",
      status: "active",
      priority: 2,
      masked_hint: "****2222",
    },
  ],
}));
vi.mock("@tanstack/react-router", () => ({
  Link: ({ children }: { children: React.ReactNode }) => (
    <a href="/providers">{children}</a>
  ),
  useNavigate: () => vi.fn(),
}));
vi.mock("@/features/modelops/connections/connection-form", () => ({
  ConnectionForm: () => null,
}));
vi.mock("@/features/modelops/connections/connection-key-modal", () => ({
  ConnectionKeyModal: () => null,
}));
vi.mock("@/features/modelops/connections/import-models-dialog", () => ({
  ImportModelsDialog: () => null,
}));
vi.mock("@/features/modelops/diagnostic-queries", () => ({
  useDiagnostics: () => ({ data: { checks: state.checks } }),
}));
vi.mock("@/features/modelops/connections/model-test-modal", () => ({
  ModelTestModal: () => null,
}));
vi.mock("@/features/modelops/connections/api", async (original) => ({
  ...(await original<typeof import("@/features/modelops/connections/api")>()),
  useConnection: () => ({
    data: {
      id: "conn-review",
      name: "Review",
      family: "custom",
      is_active: true,
      base_url: "https://example.test/v1",
      api_type: state.apiType,
    },
  }),
  useConnectionModels: () => ({ data: [] }),
  useConnectionKeys: () => ({ data: state.keys }),
  useDeleteConnection: () => ({ mutateAsync: vi.fn() }),
  useAddConnectionModel: () => ({ mutateAsync: state.add }),
  useDeleteConnectionModel: () => ({ mutateAsync: vi.fn() }),
  useDeleteConnectionKey: () => ({ mutateAsync: vi.fn() }),
  useTestConnection: () => ({ mutateAsync: state.test }),
}));
vi.stubGlobal(
  "matchMedia",
  vi.fn(() => ({
    matches: false,
    addEventListener() {},
    removeEventListener() {},
  })),
);
beforeEach(() => {
  state.apiType = "openai_compatible";
  state.checks = [];
  state.test.mockResolvedValue({ ok: true, detail: "Synthetic success" });
});

test("MinerU registers OCR without LLM discovery or chat endpoint", async () => {
  state.apiType = "mineru";
  state.add.mockResolvedValue({ id: "ocr-child" });
  render(<ConnectionDetail connectionId="conn-review" />);
  expect(screen.getByText("Dịch vụ OCR PDF")).toBeDefined();
  expect(screen.getByText("https://example.test/v1/tasks")).toBeDefined();
  expect(screen.queryByRole("button", { name: "Nhập từ /models" })).toBeNull();
  expect(screen.queryByText(/chat\/completions/)).toBeNull();
  fireEvent.change(
    screen.getByPlaceholderText("Tên dịch vụ OCR, ví dụ: mineru"),
    { target: { value: "mineru" } },
  );
  fireEvent.click(screen.getByRole("button", { name: "Thêm model" }));
  await waitFor(() =>
    expect(state.add).toHaveBeenCalledWith({
      model_name: "mineru",
      capabilities: ["ocr"],
    }),
  );
});

test("batch continues after a key fails and preserves each result", async () => {
  state.test.mockRejectedValueOnce(new Error("Synthetic failure"));
  render(<ConnectionDetail connectionId="conn-review" />);
  fireEvent.click(
    screen.getByRole("button", { name: "Kiểm tra kết nối lần lượt" }),
  );
  await waitFor(() => expect(state.test).toHaveBeenCalledTimes(2));
  expect(state.test.mock.calls.map((call) => call[0].key_id)).toEqual([
    "key-first",
    "key-second",
  ]);
  expect(screen.getByText("Lỗi: Synthetic failure")).toBeDefined();
  expect(screen.getByText("Đạt: Synthetic success")).toBeDefined();
});

test("inactive key is skipped by batch and cannot be tested individually", async () => {
  state.keys[1].status = "revoked";
  try {
    render(<ConnectionDetail connectionId="conn-review" />);
    expect(
      screen
        .getAllByRole("button", { name: "Kiểm tra", exact: true })[1]
        .hasAttribute("disabled"),
    ).toBe(true);
    fireEvent.click(
      screen.getByRole("button", { name: "Kiểm tra kết nối lần lượt" }),
    );
    await waitFor(() => expect(state.test).toHaveBeenCalledTimes(1));
    expect(state.test.mock.calls[0][0].key_id).toBe("key-first");
  } finally {
    state.keys[1].status = "active";
  }
});

test("saved per-key history is visible after loading the connection", () => {
  state.checks = [
    {
      key_id: "key-second",
      outcome: "ok",
      configuration_status: "current",
      detail: "Saved second-key result",
      tested_at: "2026-10-29T00:00:00Z",
    },
  ];
  render(<ConnectionDetail connectionId="conn-review" />);
  expect(screen.getByText(/Đạt: Saved second-key result/)).toBeDefined();
  expect(
    screen.getAllByText("Chưa có kết quả kiểm tra khóa này."),
  ).toHaveLength(1);
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("clicking second saved key sends its identity", async () => {
  render(<ConnectionDetail connectionId="conn-review" />);
  fireEvent.click(
    screen.getAllByRole("button", { name: "Kiểm tra", exact: true })[1],
  );
  await waitFor(() => expect(state.test).toHaveBeenCalledTimes(1));
  expect(state.test.mock.calls[0][0]).toEqual(
    expect.objectContaining({ key_id: "key-second" }),
  );
});

test("test keys sequentially covers both saved keys", async () => {
  render(<ConnectionDetail connectionId="conn-review" />);
  fireEvent.click(
    screen.getByRole("button", { name: "Kiểm tra kết nối lần lượt" }),
  );
  await waitFor(() => expect(state.test).toHaveBeenCalledTimes(2));
});

test("inactive key is not labelled active", () => {
  const previous = state.keys[1].status;
  state.keys[1].status = "suspended";
  try {
    render(<ConnectionDetail connectionId="conn-review" />);
    expect(screen.getAllByText("Đang hoạt động")).toHaveLength(1);
  } finally {
    state.keys[1].status = previous;
  }
});

test("unconnected round robin control is not presented as a working setting", () => {
  render(<ConnectionDetail connectionId="conn-review" />);
  expect(
    screen.getByText("Xoay khóa theo chính sách ModelOps của từng model."),
  ).toBeDefined();
  expect(
    screen
      .getAllByRole("switch")
      .every((control) => control.hasAttribute("disabled")),
  ).toBe(true);
});
