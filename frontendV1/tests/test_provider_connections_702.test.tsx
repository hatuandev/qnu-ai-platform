// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ConnectionForm } from "@/features/modelops/connections/connection-form";
import { ConnectionList } from "@/features/modelops/connections/connection-list";
import { ModelForm } from "@/features/modelops/connections/model-form";

const state = vi.hoisted(() => ({
  save: vi.fn(),
  add: vi.fn(),
  reset: vi.fn(),
  refetch: vi.fn(),
  query: {
    data: [] as unknown[],
    isLoading: false,
    isError: false,
    isFetching: false,
    error: null as Error | null,
  },
}));
vi.mock("@/features/modelops/connections/api", async (importOriginal) => ({
  ...(await importOriginal<
    typeof import("@/features/modelops/connections/api")
  >()),
  useConnections: () => ({ ...state.query, refetch: state.refetch }),
  useSaveConnection: () => ({
    mutateAsync: state.save,
    reset: state.reset,
    isPending: false,
    isError: false,
  }),
  useAddConnectionModel: () => ({
    mutateAsync: state.add,
    reset: state.reset,
    isPending: false,
    isError: false,
  }),
}));
vi.stubGlobal(
  "matchMedia",
  vi.fn((media: string) => ({
    matches: false,
    media,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
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
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  state.query.data = [];
  state.query.isError = false;
  state.query.error = null;
});

test("provider form requires connection only, without a model or secret", async () => {
  const created = {
    id: "conn_qnu",
    name: "Server QNU",
    family: "custom",
    base_url: "http://127.0.0.1:8000/v1",
    timeout_seconds: 30,
    is_active: true,
  };
  state.save.mockResolvedValue(created);
  const onCreated = vi.fn();
  render(<ConnectionForm open onOpenChange={vi.fn()} onCreated={onCreated} />);
  expect(screen.queryByLabelText(/ID model/)).toBeNull();
  expect(screen.queryByLabelText(/API key/)).toBeNull();
  fireEvent.change(screen.getByLabelText("Tên hiển thị"), {
    target: { value: "Server QNU" },
  });
  fireEvent.change(screen.getByLabelText("Địa chỉ API"), {
    target: { value: created.base_url },
  });
  fireEvent.click(screen.getByRole("button", { name: "Lưu nhà cung cấp" }));
  await waitFor(() => expect(onCreated).toHaveBeenCalledWith(created));
  expect(state.save).toHaveBeenCalledWith({
    name: "Server QNU",
    family: "custom",
    base_url: created.base_url,
    timeout_seconds: 30,
  });
});

test("model is added within provider without re-entering endpoint or API key", async () => {
  state.add.mockResolvedValue({ id: "model_qnu" });
  render(
    <ModelForm
      open
      onOpenChange={vi.fn()}
      connectionId="conn_qnu"
      modelName="listed-model"
    />,
  );
  expect(screen.queryByLabelText("Địa chỉ API")).toBeNull();
  expect(
    (screen.getByLabelText("ID model trên server") as HTMLInputElement).value,
  ).toBe("listed-model");
  fireEvent.click(screen.getByLabelText("Chat"));
  fireEvent.click(screen.getByRole("button", { name: "Thêm model" }));
  await waitFor(() =>
    expect(state.add).toHaveBeenCalledWith({
      model_name: "listed-model",
      capabilities: ["chat"],
    }),
  );
});

test("provider list renders one provider card with several models", () => {
  const row = {
    id: "conn_qnu",
    name: "QNU Server",
    family: "qnu",
    base_url: "http://127.0.0.1:8000/v1",
    is_active: true,
    model_count: 4,
    active_keys_count: 1,
    total_keys_count: 1,
    last_probe_status: "untested",
  };
  state.query.data = [row];
  const onOpen = vi.fn();
  render(<ConnectionList onOpenProvider={onOpen} />);
  expect(screen.getByText("4 model")).toBeDefined();
  fireEvent.click(screen.getByRole("button", { name: "Mở nhà cung cấp" }));
  expect(onOpen).toHaveBeenCalledWith(row);
});

test("provider fetch failure is shown instead of an empty provider list", () => {
  state.query.isError = true;
  state.query.error = new Error("Synthetic backend error");
  render(<ConnectionList onOpenProvider={vi.fn()} />);
  expect(screen.getByText("Synthetic backend error")).toBeDefined();
  expect(screen.queryByText("Chưa có nhà cung cấp")).toBeNull();
});

test("MinerU is OCR and an active key does not imply a successful check", () => {
  state.query.data = [
    {
      id: "ocr-connection",
      name: "OCR service",
      api_type: "mineru",
      family: "custom",
      base_url: "https://example.test/mineru",
      model_count: 1,
      active_keys_count: 1,
      last_probe_status: "untested",
    },
  ];
  render(<ConnectionList onOpenProvider={vi.fn()} />);
  expect(screen.getByText("Dịch vụ OCR PDF")).toBeDefined();
  expect(screen.getByText("Chưa kiểm tra")).toBeDefined();
  expect(screen.getByText("1 khóa đang bật")).toBeDefined();
  expect(screen.queryByText("Trò chuyện")).toBeNull();
  expect(screen.queryByText(/Đã kết nối/)).toBeNull();
});
