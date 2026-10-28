// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { DiagnosticCheck } from "@/features/modelops/diagnostic-queries";
import { ProviderDiagnosticsPanel } from "@/features/modelops/diagnostics-panel";
import type { Provider } from "@/features/modelops/types";

const state = vi.hoisted(() => ({
  admin: true,
  sessionId: 1,
  checks: [] as DiagnosticCheck[],
  pending: false,
  mutate: vi.fn(),
}));
vi.mock("@/app/auth/v1", () => ({
  isModelAdmin: () => state.admin,
  useV1Auth: () => ({
    isAuthenticated: true,
    actor: {},
    sessionId: state.sessionId,
  }),
}));
vi.mock("@/features/modelops/diagnostic-queries", () => ({
  useDiagnostics: () => ({ data: { checks: state.checks } }),
  useRunDiagnostic: () => ({
    mutate: state.mutate,
    isPending: state.pending,
    variables: "chat",
  }),
}));
vi.mock("@/features/modelops/provider-form-dialog", () => ({
  ProviderFormDialog: ({ suggestedModel }: { suggestedModel: string }) => (
    <div role="dialog">{suggestedModel}</div>
  ),
}));

const provider = {
  id: "p1",
  model_name: "model1",
  capabilities: ["chat"],
  is_active: true,
} as Provider;

function check(patch: Partial<DiagnosticCheck> = {}): DiagnosticCheck {
  return {
    id: "check-1",
    kind: "chat",
    outcome: "ok",
    configuration_status: "current",
    tested_at: "2026-10-28T05:00:00Z",
    latency_ms: 123,
    code: "diagnostic_ok",
    detail: "Chat cơ bản hợp lệ",
    http_status: 200,
    retry_after: null,
    requested_model: "model1",
    observed_model: null,
    observed_dimension: null,
    total_tokens: null,
    models: [],
    ...patch,
  };
}

beforeEach(() => {
  state.admin = true;
  state.checks = [];
  state.pending = false;
  state.sessionId = 1;
  state.mutate.mockClear();
  // Radix Select browser APIs absent in jsdom.
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};
  Element.prototype.scrollIntoView = () => {};
});
afterEach(cleanup);

test("admin actions use the requested capability and do not run on mount", () => {
  render(<ProviderDiagnosticsPanel provider={provider} />);
  expect(state.mutate).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Lấy danh sách model" }));
  expect(state.mutate).toHaveBeenLastCalledWith("discovery");
  fireEvent.click(screen.getByRole("button", { name: "Thử Chat" }));
  expect(state.mutate).toHaveBeenLastCalledWith("chat");
});

test("disabled provider cannot send a check", () => {
  render(
    <ProviderDiagnosticsPanel provider={{ ...provider, is_active: false }} />,
  );
  const button = screen.getByRole("button", { name: "Thử Chat" });
  expect(button.hasAttribute("disabled")).toBe(true);
  fireEvent.click(button);
  expect(state.mutate).not.toHaveBeenCalled();
});

test("a stale success is marked for recheck and cannot supply a model picker", () => {
  state.checks = [
    check({
      kind: "discovery",
      configuration_status: "stale",
      models: ["old-model"],
    }),
  ];
  render(<ProviderDiagnosticsPanel provider={provider} />);
  expect(screen.getByText("Cần thử lại")).toBeTruthy();
  expect(screen.queryByText("Thử thành công")).toBeNull();
  expect(screen.queryByRole("combobox")).toBeNull();
});

test("auth failure, latency and upstream retry time are visible instead of an empty state", () => {
  state.checks = [
    check({
      outcome: "failed",
      code: "provider_auth_failed",
      http_status: 401,
      detail: "Server từ chối khóa hoặc quyền truy cập.",
      retry_after: "2026-10-28T05:01:00Z",
    }),
  ];
  render(<ProviderDiagnosticsPanel provider={provider} />);
  expect(screen.getByText("Thử thất bại")).toBeTruthy();
  expect(screen.getByText(/HTTP 401/)).toBeTruthy();
  expect(screen.getByText("123 ms")).toBeTruthy();
  expect(screen.getByText(/Server đề nghị thử lại/)).toBeTruthy();
  expect(screen.queryByText("Chưa có lần kiểm tra nào.")).toBeNull();
});

test("discovery stays distinct from inference and choosing a model opens an editable draft", async () => {
  state.checks = [check({ kind: "discovery", models: ["new-model"] })];
  render(<ProviderDiagnosticsPanel provider={provider} />);
  expect(screen.getByText(/chưa có nghĩa đã chạy thử thành công/)).toBeTruthy();
  const trigger = screen.getByRole("combobox", { name: "Model trên server" });
  fireEvent.keyDown(trigger, { key: "ArrowDown" });
  fireEvent.click(await screen.findByRole("option", { name: "new-model" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Sửa cấu hình" }));
  expect(screen.getByRole("dialog").textContent).toBe("new-model");
  expect(state.mutate).not.toHaveBeenCalled();
});

test("view-only actors do not see admin diagnostics controls", () => {
  state.admin = false;
  render(<ProviderDiagnosticsPanel provider={provider} />);
  expect(screen.queryByRole("button")).toBeNull();
});

test("pending checks prevent double-submit without manufacturing progress", () => {
  state.pending = true;
  render(<ProviderDiagnosticsPanel provider={provider} />);
  expect(screen.getByRole("status").textContent).toContain("Đang chờ server");
  expect(screen.queryByRole("progressbar")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Thử Chat" }));
  expect(state.mutate).not.toHaveBeenCalled();
});
