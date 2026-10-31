// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ProviderResiliencePanel } from "@/features/modelops/resilience-panel";
import type {
  ExecutionObservation,
  PolicyResponse,
  ResiliencePolicy,
  Transport,
} from "@/features/modelops/resilience-queries";
import type { Provider } from "@/features/modelops/types";

const state = vi.hoisted(() => ({
  admin: true,
  session: 1,
  pending: false,
  loading: false,
  error: null as Error | null,
  saved: null as PolicyResponse | null,
  registry: [] as Transport[],
  providers: [] as Provider[],
  executions: [] as ExecutionObservation[],
  save: vi.fn(),
}));
vi.mock("@/app/auth/v1", () => ({
  isModelAdmin: () => state.admin,
  useV1Auth: () => ({ actor: {}, sessionId: state.session }),
}));
vi.mock("@/features/modelops/queries", () => ({
  useProvidersQuery: () => ({ data: state.providers }),
}));
vi.mock("@/features/modelops/resilience-queries", async (original) => {
  const actual = await original<object>();
  return {
    ...actual,
    useResilience: () => ({
      data: state.loading ? null : state.saved,
      isError: Boolean(state.error),
      error: state.error,
      refetch: vi.fn(),
    }),
    useTransportRegistry: () => ({ data: state.registry }),
    useExecutions: () => ({ data: state.executions, refetch: vi.fn() }),
    useSaveResilience: () => ({
      mutateAsync: state.save,
      isPending: state.pending,
    }),
  };
});

const provider = {
  id: "p1",
  name: "Primary",
  provider_type: "local",
  model_name: "m1",
  capabilities: ["chat"],
  is_active: true,
  updated_at: "date",
} as Provider;
const defaults: ResiliencePolicy = {
  key_pool_enabled: false,
  retry_owner: "qnu",
  max_key_attempts: 1,
  auth_cooldown_seconds: 300,
  rate_cooldown_seconds: 30,
  fallbacks: {},
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
  state.admin = true;
  state.session = 1;
  state.pending = false;
  state.error = null;
  state.loading = false;
  state.executions = [];
  state.saved = {
    provider_id: "p1",
    status: "default",
    policy: structuredClone(defaults),
    routing_phase: "before_dispatch",
    explicit_provider_is_pinned: true,
    embedding_model_fallback: false,
  };
  state.providers = [
    provider,
    { ...provider, id: "p2", name: "Backup", model_name: "m2" },
    { ...provider, id: "p3", name: "Disabled", is_active: false },
  ];
  state.registry = [
    {
      provider_type: "local",
      label: "Local",
      protocols: { chat: "chat_completions" },
      discovery: true,
      streaming: false,
      responses_api: false,
      tools: false,
      image_input: [],
      multi_item_input: [],
      metadata_basis: "adapter_contract",
      structured_output: "request_supported_provider_unverified",
    },
  ];
  state.save.mockReset().mockResolvedValue(state.saved);
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};
  Element.prototype.scrollIntoView = () => {};
});
afterEach(cleanup);

test("policy never runs or saves on mount and explains pinning and unsupported transport", () => {
  render(<ProviderResiliencePanel provider={provider} />);
  expect(state.save).not.toHaveBeenCalled();
  expect(screen.getByText(/Responses API: chưa hỗ trợ/)).toBeTruthy();
  expect(screen.getByText(/Không đổi model embedding/)).toBeTruthy();
  expect(
    screen
      .getByRole("switch", { name: "Dùng nhóm khóa" })
      .getAttribute("aria-checked"),
  ).toBe("false");
  expect(
    screen.getByLabelText("Tối đa lượt gọi").hasAttribute("disabled"),
  ).toBe(true);
});

test("gateway owns retries so switching to it resets attempts to one", async () => {
  render(<ProviderResiliencePanel provider={provider} />);
  fireEvent.click(screen.getByRole("switch", { name: "Dùng nhóm khóa" }));
  fireEvent.change(screen.getByLabelText("Tối đa lượt gọi"), {
    target: { value: "3" },
  });
  fireEvent.keyDown(
    screen.getByRole("combobox", { name: "Bên quản lý thử lại" }),
    { key: "ArrowDown" },
  );
  fireEvent.click(
    await screen.findByRole("option", { name: "Gateway / 9router" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Lưu chính sách" }));
  await waitFor(() =>
    expect(state.save).toHaveBeenCalledWith(
      expect.objectContaining({
        key_pool_enabled: true,
        retry_owner: "gateway",
        max_key_attempts: 1,
      }),
    ),
  );
  expect(await screen.findByText("Đã lưu chính sách.")).toBeTruthy();
});

test("waiting for completion is explicit and preserves the other policy values", async () => {
  render(<ProviderResiliencePanel provider={provider} />);
  const wait = screen.getByRole("switch", { name: "Chờ model xử lý xong" });
  expect(wait.getAttribute("aria-checked")).toBe("false");
  expect(state.save).not.toHaveBeenCalled();
  fireEvent.click(wait);
  fireEvent.click(screen.getByRole("button", { name: "Lưu chính sách" }));
  await waitFor(() =>
    expect(state.save).toHaveBeenCalledWith(
      expect.objectContaining({
        wait_for_completion: true,
        key_pool_enabled: false,
      }),
    ),
  );
});

test("ordered task fallback saves IDs and excludes inactive and primary providers", async () => {
  render(<ProviderResiliencePanel provider={provider} />);
  fireEvent.keyDown(
    screen.getByRole("combobox", { name: "Compiler dự phòng 1" }),
    { key: "ArrowDown" },
  );
  expect(screen.queryByRole("option", { name: /Disabled/ })).toBeNull();
  expect(screen.queryByRole("option", { name: /Primary/ })).toBeNull();
  fireEvent.click(await screen.findByRole("option", { name: "Backup · m2" }));
  fireEvent.click(screen.getByRole("button", { name: "Lưu chính sách" }));
  await waitFor(() =>
    expect(state.save).toHaveBeenCalledWith(
      expect.objectContaining({ fallbacks: { compiler: ["p2"] } }),
    ),
  );
});

test("provider and session changes discard drafts", () => {
  const view = render(<ProviderResiliencePanel provider={provider} />);
  fireEvent.click(screen.getByRole("switch", { name: "Dùng nhóm khóa" }));
  state.session = 2;
  view.rerender(<ProviderResiliencePanel provider={provider} />);
  expect(
    screen
      .getByRole("switch", { name: "Dùng nhóm khóa" })
      .getAttribute("aria-checked"),
  ).toBe("false");
  fireEvent.click(screen.getByRole("switch", { name: "Dùng nhóm khóa" }));
  view.rerender(
    <ProviderResiliencePanel provider={{ ...provider, id: "p2" }} />,
  );
  expect(
    screen
      .getByRole("switch", { name: "Dùng nhóm khóa" })
      .getAttribute("aria-checked"),
  ).toBe("false");
});

test("stale, pending, error, loading and unauthorized states stay truthful", () => {
  if (state.saved) state.saved.status = "stale";
  const view = render(<ProviderResiliencePanel provider={provider} />);
  expect(screen.getByText(/Chính sách cũ đang ngừng áp dụng/)).toBeTruthy();
  state.pending = true;
  view.rerender(<ProviderResiliencePanel provider={provider} />);
  expect(
    screen
      .getByRole("button", { name: "Lưu chính sách" })
      .hasAttribute("disabled"),
  ).toBe(true);
  state.error = new Error("Cannot load policy");
  view.rerender(<ProviderResiliencePanel provider={provider} />);
  expect(screen.queryByRole("switch")).toBeNull();
  state.error = null;
  state.loading = true;
  view.rerender(<ProviderResiliencePanel provider={provider} />);
  expect(screen.queryByRole("button", { name: "Lưu chính sách" })).toBeNull();
  state.admin = false;
  view.rerender(<ProviderResiliencePanel provider={provider} />);
  expect(view.container.textContent).toBe("");
});

test("attempt history keeps unknown token usage distinct from measured zero", () => {
  const observed: ExecutionObservation = {
    id: "a1",
    created_at: "2026-10-28T07:00:00Z",
    call_id: "call-1",
    usage_id: "usage-1",
    capability: "chat",
    model_name: "m1",
    key_id: "key-1",
    code: "chat_provider_auth_failed",
    upstream_status: 401,
    attempt: 1,
    latency_ms: 45,
    total_tokens: null,
  };
  state.executions = [
    observed,
    {
      ...observed,
      id: "a2",
      code: "ok",
      upstream_status: null,
      attempt: 2,
      total_tokens: 0,
    },
  ];
  render(<ProviderResiliencePanel provider={provider} />);
  expect(screen.getByText(/Chưa biết token/)).toBeTruthy();
  expect(screen.getByText(/0 token/)).toBeTruthy();
  expect(screen.getByText(/HTTP 401/)).toBeTruthy();
  expect(screen.getByText("Thành công")).toBeTruthy();
  expect(screen.getAllByText(/usage-1/)).toHaveLength(2);
});

test("invalid cooldown cannot be saved and has a visible field error", async () => {
  render(<ProviderResiliencePanel provider={provider} />);
  fireEvent.change(screen.getByLabelText("Nghỉ khi sai khóa (giây)"), {
    target: { value: "-1" },
  });
  await waitFor(() =>
    expect(
      screen
        .getByRole("button", { name: "Lưu chính sách" })
        .hasAttribute("disabled"),
    ).toBe(true),
  );
  expect(
    screen.getByText("Nhập số nguyên trong khoảng cho phép."),
  ).toBeTruthy();
  expect(state.save).not.toHaveBeenCalled();
});
