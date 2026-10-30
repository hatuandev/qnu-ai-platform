// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ImportModelsDialog } from "@/features/modelops/connections/import-models-dialog";

const state = vi.hoisted(() => ({
  discover: vi.fn(),
  sync: vi.fn(),
  add: vi.fn(),
  checks: [] as object[],
}));
vi.mock("@/features/modelops/diagnostic-queries", () => ({
  useDiagnostics: () => ({ data: { checks: state.checks } }),
  useRunDiagnostic: () => ({ isPending: false, mutateAsync: state.discover }),
}));
vi.mock("@/features/modelops/connections/api", () => ({
  useAddConnectionModel: () => ({ mutateAsync: state.add }),
  useSyncConnectionCapacity: () => ({ mutateAsync: state.sync }),
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
const check = {
  id: "diag_current",
  kind: "discovery",
  outcome: "ok",
  configuration_status: "current",
  models: ["server-chat"],
  model_metadata: [
    {
      id: "server-chat",
      context_window_tokens: 131072,
      max_output_tokens: 16384,
      embedding_dimension: null,
    },
  ],
};
beforeEach(() => {
  state.checks = [];
  state.discover.mockResolvedValue(check);
  state.sync.mockResolvedValue([]);
  state.add.mockResolvedValue({ id: "new_model" });
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
function show(existingModels: string[] = []) {
  return render(
    <ImportModelsDialog
      open
      onOpenChange={vi.fn()}
      connectionId="conn_test"
      connectionName="Test server"
      existingModels={existingModels}
    />,
  );
}

test("shows server limits before an explicit sync of registered models", async () => {
  show(["server-chat"]);
  fireEvent.click(screen.getByRole("button", { name: "Lấy lại" }));
  await screen.findByText("Context 131.072 · Đầu ra 16.384");
  expect(state.sync).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("checkbox", { name: "server-chat" }));
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng" }));
  await waitFor(() =>
    expect(state.sync).toHaveBeenCalledWith({
      check_id: "diag_current",
      model_names: ["server-chat"],
    }),
  );
  expect(state.add).not.toHaveBeenCalled();
});

test("imports new models using the saved discovery ID, without copying untrusted values", async () => {
  show();
  fireEvent.click(screen.getByRole("button", { name: "Lấy lại" }));
  await screen.findByText("server-chat");
  fireEvent.click(screen.getByRole("checkbox", { name: "server-chat" }));
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng" }));
  await waitFor(() =>
    expect(state.add).toHaveBeenCalledWith({
      model_name: "server-chat",
      capabilities: ["chat"],
      discovery_check_id: "diag_current",
    }),
  );
});

test("ignores stale cached discovery and exposes sync failure", async () => {
  state.checks = [{ ...check, configuration_status: "stale" }];
  state.sync.mockRejectedValue(
    new Error("Giới hạn server mâu thuẫn cấu hình đã lưu."),
  );
  show(["server-chat"]);
  expect(screen.queryByText("Context 131.072 · Đầu ra 16.384")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Lấy lại" }));
  await screen.findByText("server-chat");
  fireEvent.click(screen.getByRole("checkbox", { name: "server-chat" }));
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng" }));
  await screen.findByRole("alert");
  expect(screen.getByRole("alert").textContent).toContain("mâu thuẫn");
});

test("missing metadata is unknown and cannot overwrite existing capacity", async () => {
  state.discover.mockResolvedValue({ ...check, model_metadata: [] });
  show(["server-chat"]);
  fireEvent.click(screen.getByRole("button", { name: "Lấy lại" }));
  await screen.findByText("Server chưa công bố giới hạn");
  expect(
    screen.getByRole("checkbox").getAttribute("data-disabled"),
  ).not.toBeNull();
  expect(state.sync).not.toHaveBeenCalled();
});
