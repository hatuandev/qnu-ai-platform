// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { ConnectionDetail } from "@/features/modelops/connections/connection-detail";
import type { Provider } from "@/features/modelops/types";

const state = vi.hoisted(() => ({ save: vi.fn(), model: {} as Provider }));
vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children }: { children: ReactNode }) => <span>{children}</span>,
}));
vi.mock("@/features/modelops/queries", () => ({
  useCreateProvider: () => ({ isPending: false }),
  useUpdateProvider: (id: string) => ({
    isPending: false,
    mutateAsync: (patch: unknown) => state.save(id, patch),
  }),
}));
vi.mock("@/features/modelops/resilience-queries", () => ({
  useTransportRegistry: () => ({ data: [] }),
}));
vi.mock("@/features/modelops/diagnostic-queries", () => ({
  useDiagnostics: () => ({ data: { checks: [] } }),
}));
vi.mock("@/features/modelops/connections/api", async (original) => ({
  ...(await original<typeof import("@/features/modelops/connections/api")>()),
  useConnection: () => ({
    data: {
      id: "conn_test",
      name: "Synthetic server",
      family: "custom",
      base_url: "http://127.0.0.1:8000/v1",
      is_active: true,
    },
  }),
  useConnectionModels: () => ({ data: [state.model] }),
  useConnectionKeys: () => ({ data: [] }),
  useDeleteConnection: () => ({}),
  useAddConnectionModel: () => ({}),
  useDeleteConnectionModel: () => ({}),
  useDeleteConnectionKey: () => ({}),
  useTestConnection: () => ({}),
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
vi.mock("@/features/modelops/connections/model-test-modal", () => ({
  ModelTestModal: () => null,
}));
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
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function openModel(capabilities: string[] = ["chat"]) {
  state.model = {
    id: "model_test",
    parent_id: "conn_test",
    name: "Synthetic model",
    provider_type: "openai_compatible",
    base_url: "http://127.0.0.1:8000/v1",
    model_name: "synthetic-model",
    capabilities,
    is_active: true,
    priority: 5,
    timeout_seconds: 30,
    token_limits: null,
    capacity_status: "unknown",
    capacity_basis: null,
    embedding_dimension: null,
    embedding_dimension_status: "unknown",
    created_at: "2026-10-30T00:00:00Z",
    updated_at: "2026-10-30T00:00:00Z",
  };
  state.save.mockResolvedValue({ ...state.model });
  render(<ConnectionDetail connectionId="conn_test" />);
  fireEvent.click(screen.getByTitle("Cấu hình model và giới hạn xử lý"));
}
function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}
function save() {
  fireEvent.click(screen.getByRole("button", { name: "Lưu thay đổi" }));
}

test("child model editor saves capacity on the selected model without changing connection or capabilities", async () => {
  openModel(["chat", "rerank"]);
  expect(screen.getByRole("heading", { name: "Cấu hình model" })).toBeDefined();
  expect((screen.getByLabelText("Base URL") as HTMLInputElement).disabled).toBe(
    true,
  );
  fill("context_window_tokens", "16000");
  fill("max_output_tokens", "4000");
  save();
  await waitFor(() =>
    expect(state.save).toHaveBeenCalledWith("model_test", {
      token_limits: {
        context_window_tokens: 16000,
        max_input_tokens: null,
        max_output_tokens: 4000,
        ocr_page_input: null,
      },
    }),
  );
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
});

test("embedding dimension can be declared without fabricating token limits", async () => {
  openModel(["embedding"]);
  fill("embedding_dimension", "1024");
  save();
  await waitFor(() =>
    expect(state.save).toHaveBeenCalledWith("model_test", {
      embedding_dimension: 1024,
    }),
  );
});

test("partial OCR budget is rejected before saving", async () => {
  openModel(["ocr"]);
  fill("max_output_tokens", "4000");
  fill("max_image_width", "1000");
  save();
  await waitFor(() =>
    expect(screen.getByRole("alert").textContent).toContain(
      "ocr_page_input cần đủ",
    ),
  );
  expect(state.save).not.toHaveBeenCalled();
});

test("complete OCR page declaration is saved with token limits and prompt identity", async () => {
  openModel(["ocr"]);
  fill("max_output_tokens", "4000");
  fill("max_image_width", "1000");
  fill("max_image_height", "1500");
  fill("input_tokens_upper_bound", "2000");
  fill("prompt_sha256", "a".repeat(64));
  save();
  await waitFor(() =>
    expect(state.save).toHaveBeenCalledWith("model_test", {
      token_limits: {
        context_window_tokens: null,
        max_input_tokens: null,
        max_output_tokens: 4000,
        ocr_page_input: {
          max_image_width: 1000,
          max_image_height: 1500,
          input_tokens_upper_bound: 2000,
          prompt_sha256: "a".repeat(64),
        },
      },
    }),
  );
});
