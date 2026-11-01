// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
  ConsumerModelBudgetNotice,
  describeDiagnosticFailure,
  resolveCapabilityBudgetState,
} from "@/features/modelops/capacity-badge";
import { CapacityPanel } from "@/features/modelops/provider-detail";
import { ProviderFormDialog } from "@/features/modelops/provider-form-dialog";
import type {
  CatalogItem,
  OperationalBudget,
  Provider,
  TokenLimits,
} from "@/features/modelops/types";

const state = vi.hoisted(() => ({
  createProvider: vi.fn(),
  updateProvider: vi.fn(),
  canManage: true,
}));

const declaredLimits: TokenLimits = {
  context_window_tokens: 131072,
  max_input_tokens: 7000,
  max_output_tokens: 16384,
  ocr_page_input: null,
};

function modelBudget(
  overrides: Partial<OperationalBudget> = {},
): OperationalBudget {
  return {
    version: "qnu.operational-budget/v1",
    status: "declared",
    token_limits: declaredLimits,
    sources: {
      context_window_tokens: "server_reported",
      max_input_tokens: "operator_configured",
      max_output_tokens: "server_reported",
    },
    reason_code: null,
    ...overrides,
  };
}

function savedProvider(overrides: Partial<Provider> = {}): Provider {
  return {
    id: "provider-795",
    name: "Saved model",
    provider_type: "openai_compatible",
    base_url: "https://provider.example.test/v1",
    model_name: "custom-model",
    capabilities: ["chat"],
    is_active: true,
    priority: 5,
    timeout_seconds: 30,
    token_limits: declaredLimits,
    capacity_basis: "server_reported",
    capacity_status: "configured",
    embedding_dimension: null,
    embedding_dimension_status: "unknown",
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-01T00:00:00Z",
    ...overrides,
  };
}

function knownLimitRow(label: string) {
  const section = screen
    .getByText("Giới hạn đã biết của model")
    .closest("section");
  if (!section) throw new Error("Missing known capacity section");
  const row = within(section).getByText(label).closest("div");
  if (!row) throw new Error(`Missing capacity row: ${label}`);
  return within(row);
}

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children }: { children: ReactNode }) => <span>{children}</span>,
}));

vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({
    sessionId: "sess_795",
    isAuthenticated: true,
    actor: {
      id: "admin_795",
      permissions: state.canManage
        ? ["ai.models.manage", "ai.keys.manage"]
        : ["ai.models.read"],
    },
  }),
  isModelAdmin: (actor?: { permissions?: string[] } | null) =>
    Boolean(actor?.permissions?.includes("ai.models.manage")),
}));

vi.mock("@/features/modelops/queries", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/modelops/queries")>()),
  useCreateProvider: () => ({
    isPending: false,
    mutateAsync: (payload: unknown) => state.createProvider(payload),
  }),
  useUpdateProvider: (id: string) => ({
    isPending: false,
    mutateAsync: (patch: unknown) => state.updateProvider(id, patch),
  }),
}));

vi.mock("@/features/modelops/resilience-queries", () => ({
  useTransportRegistry: () => ({
    data: [
      { provider_type: "openai_compatible", protocols: { chat: "openai" } },
    ],
    isError: false,
  }),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
});

beforeEach(() => {
  state.createProvider.mockReset();
  state.updateProvider.mockReset();
  state.canManage = true;
  queryClient.clear();
  vi.stubGlobal("matchMedia", () => ({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function wrap(ui: ReactNode) {
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

// =========================================================================
// P2-1: Wire real catalog budget data from BE to FE consumers
// =========================================================================
describe("P2-1: Catalog budget wiring, blocked notice, default fallback and missing_info", () => {
  test("blocked OCR model with operational_budgets displays Alert warning", () => {
    const ocrModel: CatalogItem = {
      id: "prov-ocr-1",
      name: "Qwen OCR Narrow",
      model_name: "qwen-vl-narrow",
      capabilities: ["ocr"],
      default_capabilities: ["ocr"],
      capacity_status: "unknown",
      capacity_basis: "server_reported",
      operational_budgets: {
        ocr: modelBudget({
          status: "blocked",
          token_limits: null,
          sources: {},
          reason_code: "model_input_budget_unknown",
        }),
      },
    };

    wrap(<ConsumerModelBudgetNotice model={ocrModel} capability="ocr" />);

    // Alert with status role is rendered for blocked capability
    expect(screen.getByRole("status")).toBeTruthy();
    expect(
      screen.getByText(/Chưa có thông số giới hạn trang ảnh OCR/),
    ).toBeTruthy();
    expect(screen.getByText("Cần bổ sung thông tin (OCR)")).toBeTruthy();
  });

  test("unconfigured model using defaultModel displays default indicator or estimated notice", () => {
    const defaultModel: CatalogItem = {
      id: "prov-chat-default",
      name: "Default Qwen 2.5",
      model_name: "qwen2.5-32b",
      capabilities: ["chat"],
      default_capabilities: ["chat"],
      capacity_status: "unknown",
      capacity_basis: null,
      operational_budgets: {
        chat: modelBudget({
          status: "provisional",
          token_limits: {
            context_window_tokens: 32768,
            max_input_tokens: null,
            max_output_tokens: 4096,
            ocr_page_input: null,
          },
          sources: {
            context_window_tokens: "application_default",
            max_output_tokens: "application_default",
          },
        }),
      },
    };

    wrap(
      <ConsumerModelBudgetNotice
        model={null}
        defaultModel={defaultModel}
        isDefaultSelection={true}
        capability="chat"
      />,
    );

    // Displays notification explaining the default model is in effect
    expect(screen.getByText(/\(Mặc định: Default Qwen 2.5\)/)).toBeTruthy();
    expect(screen.getByText(/Đang dùng ngân sách tạm tính/)).toBeTruthy();
  });

  test("model lacking both token_limits and model_metadata displays missing_info notice", () => {
    const bareModel: CatalogItem = {
      id: "prov-bare",
      name: "Bare Model",
      model_name: "bare-v1",
      capabilities: ["chat"],
      default_capabilities: ["chat"],
      capacity_status: "unknown",
      capacity_basis: "server_reported",
    };

    wrap(<ConsumerModelBudgetNotice model={bareModel} capability="chat" />);

    expect(screen.getByText("Chưa có thông tin")).toBeTruthy();
  });

  test("resolveCapabilityBudgetState extracts correct operational budget and reason", () => {
    const model: CatalogItem = {
      id: "prov-comp-1",
      name: "Compiler Model",
      model_name: "compiler-v1",
      capabilities: ["chat"],
      default_capabilities: ["chat"],
      capacity_status: "configured",
      capacity_basis: "server_reported",
      operational_budgets: {
        chat: modelBudget(),
      },
    };

    const resolved = resolveCapabilityBudgetState(model, "chat");
    expect(resolved.status).toBe("declared");
    expect(resolved.isBlocked).toBe(false);
    expect(resolved.budget?.token_limits?.max_output_tokens).toBe(16384);
  });
});

// =========================================================================
// P2-2: Confirmation dialog on clearing token limits in ProviderFormDialog
// =========================================================================
describe("P2-2: Confirmation on clearing token limits in ProviderFormDialog", () => {
  const existingProviderWithLimits = savedProvider({
    id: "prov-existing-1",
    name: "Existing LLM Provider",
    provider_type: "openai_compatible",
    base_url: "https://llm.example.com/v1",
    model_name: "existing-model",
    capabilities: ["chat"],
    token_limits: {
      context_window_tokens: 32768,
      max_input_tokens: null,
      max_output_tokens: null,
      ocr_page_input: null,
    },
    capacity_basis: "server_reported",
    capacity_status: "configured",
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-01T00:00:00Z",
  });

  test("clearing token limit inputs opens ConfirmDialog and does NOT call save immediately", async () => {
    wrap(
      <ProviderFormDialog
        open={true}
        onOpenChange={vi.fn()}
        provider={existingProviderWithLimits}
      />,
    );

    // Expand "Nâng cao" accordion
    fireEvent.click(screen.getByText(/Nâng cao \(Giới hạn token/));

    // Clear contextWindowTokens input
    const contextInput = screen.getByLabelText("context_window_tokens");
    fireEvent.change(contextInput, { target: { value: "" } });

    // Click "Lưu thay đổi"
    fireEvent.click(screen.getByRole("button", { name: "Lưu thay đổi" }));

    // Confirm dialog must appear
    await screen.findByText("Xóa giới hạn token đã khai báo?");
    expect(screen.getByRole("alertdialog")).toBeTruthy();

    // Must NOT have called updateProvider yet!
    expect(state.updateProvider).not.toHaveBeenCalled();
  });

  test("canceling confirm dialog retains form modal and keeps current draft values", async () => {
    wrap(
      <ProviderFormDialog
        open={true}
        onOpenChange={vi.fn()}
        provider={existingProviderWithLimits}
      />,
    );

    fireEvent.click(screen.getByText(/Nâng cao \(Giới hạn token/));
    const contextInput = screen.getByLabelText("context_window_tokens");
    fireEvent.change(contextInput, { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Lưu thay đổi" }));

    await screen.findByText("Xóa giới hạn token đã khai báo?");

    // Click "Hủy" on the confirm dialog
    fireEvent.click(screen.getByRole("button", { name: "Hủy" }));

    // Confirm dialog closes, but ProviderFormDialog remains open
    await waitFor(() => {
      expect(screen.queryByText("Xóa giới hạn token đã khai báo?")).toBeNull();
    });

    // Main form dialog is still here and input remains empty (draft preserved)
    expect(
      (screen.getByLabelText("context_window_tokens") as HTMLInputElement)
        .value,
    ).toBe("");
    expect(state.updateProvider).not.toHaveBeenCalled();
  });

  test("confirming clear limits executes updateProvider with token_limits: null and other fields preserved", async () => {
    state.updateProvider.mockResolvedValueOnce(undefined);

    wrap(
      <ProviderFormDialog
        open={true}
        onOpenChange={vi.fn()}
        provider={existingProviderWithLimits}
      />,
    );

    // Change provider name as well to verify multi-field patch preservation
    const nameInput = screen.getByLabelText("Tên provider");
    fireEvent.change(nameInput, { target: { value: "Updated Provider Name" } });

    fireEvent.click(screen.getByText(/Nâng cao \(Giới hạn token/));
    const contextInput = screen.getByLabelText("context_window_tokens");
    fireEvent.change(contextInput, { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Lưu thay đổi" }));

    await screen.findByText("Xóa giới hạn token đã khai báo?");

    // Click "Xác nhận xóa khai báo"
    fireEvent.click(
      screen.getByRole("button", { name: "Xác nhận xóa khai báo" }),
    );

    await waitFor(() => {
      expect(state.updateProvider).toHaveBeenCalledTimes(1);
    });

    // Verify payload sent: token_limits must be null, name and other fields preserved
    const [id, patch] = state.updateProvider.mock.calls[0] as [
      string,
      Record<string, unknown>,
    ];
    expect(id).toBe("prov-existing-1");
    expect(patch.token_limits).toBeNull();
    expect(patch.name).toBe("Updated Provider Name");
  });

  test("failed clear keeps the current draft but reopening discards the pending patch", async () => {
    const ui = (open: boolean) => (
      <QueryClientProvider client={queryClient}>
        <ProviderFormDialog
          open={open}
          provider={existingProviderWithLimits}
          onOpenChange={vi.fn()}
        />
      </QueryClientProvider>
    );
    const view = render(ui(true));
    fireEvent.change(screen.getByLabelText("Tên provider"), {
      target: { value: "Failed draft name" },
    });
    fireEvent.click(screen.getByText(/Nâng cao \(Giới hạn token/));
    fireEvent.change(screen.getByLabelText("context_window_tokens"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu thay đổi" }));
    await screen.findByRole("alertdialog");
    state.updateProvider.mockRejectedValueOnce(
      new Error("Synthetic persistence failure"),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Xác nhận xóa khai báo" }),
    );
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(
      (screen.getByLabelText("Tên provider") as HTMLInputElement).value,
    ).toBe("Failed draft name");
    expect(
      (screen.getByLabelText("context_window_tokens") as HTMLInputElement)
        .value,
    ).toBe("");

    view.rerender(ui(false));
    view.rerender(ui(true));
    expect(
      (screen.getByLabelText("Tên provider") as HTMLInputElement).value,
    ).toBe(existingProviderWithLimits.name);
    fireEvent.click(screen.getByText(/Nâng cao \(Giới hạn token/));
    fireEvent.click(
      screen.getByRole("button", { name: "Xóa khai báo giới hạn" }),
    );
    await screen.findByRole("alertdialog");
    state.updateProvider.mockResolvedValueOnce(existingProviderWithLimits);
    fireEvent.click(
      screen.getByRole("button", { name: "Xác nhận xóa khai báo" }),
    );
    await waitFor(() => expect(state.updateProvider).toHaveBeenCalledTimes(2));
    expect(state.updateProvider.mock.calls[1]).toEqual([
      existingProviderWithLimits.id,
      { token_limits: null },
    ]);
  });

  test("changing the edited model cannot carry another model's pending patch", async () => {
    const next = savedProvider({ id: "other-model", name: "Other model" });
    const ui = (provider: Provider) => (
      <QueryClientProvider client={queryClient}>
        <ProviderFormDialog open provider={provider} onOpenChange={vi.fn()} />
      </QueryClientProvider>
    );
    const view = render(ui(existingProviderWithLimits));
    fireEvent.change(screen.getByLabelText("Tên provider"), {
      target: { value: "Do not carry this name" },
    });
    fireEvent.click(screen.getByText(/Nâng cao \(Giới hạn token/));
    fireEvent.change(screen.getByLabelText("context_window_tokens"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu thay đổi" }));
    await screen.findByRole("alertdialog");
    view.rerender(ui(next));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    fireEvent.click(screen.getByText(/Nâng cao \(Giới hạn token/));
    fireEvent.click(
      screen.getByRole("button", { name: "Xóa khai báo giới hạn" }),
    );
    await screen.findByRole("alertdialog");
    state.updateProvider.mockResolvedValueOnce(next);
    fireEvent.click(
      screen.getByRole("button", { name: "Xác nhận xóa khai báo" }),
    );
    await waitFor(() => expect(state.updateProvider).toHaveBeenCalledTimes(1));
    expect(state.updateProvider).toHaveBeenCalledWith(next.id, {
      token_limits: null,
    });
  });
});

// =========================================================================
// P2-3: Error classifier mapping in describeDiagnosticFailure
// =========================================================================
describe("P2-3: Diagnostic failure classification (describeDiagnosticFailure)", () => {
  test("maps chat_output_truncated or finish_reason length to output_truncated", () => {
    const res1 = describeDiagnosticFailure({
      code: "chat_output_truncated",
      http_status: 200,
      detail: "Generation reached max output token limit",
    });
    expect(res1.category).toBe("output_truncated");
    expect(res1.title).toContain("bị cắt ngắn");

    const res2 = describeDiagnosticFailure({
      code: "model_output_truncated",
      detail: "finish_reason: length",
    });
    expect(res2.category).toBe("output_truncated");
  });

  test("maps invalid responses to malformed_response", () => {
    const codes = [
      "provider_response_invalid",
      "chat_response_invalid",
      "response_invalid",
      "malformed_json",
      "schema_validation_error",
    ];

    for (const code of codes) {
      const res = describeDiagnosticFailure({ code, http_status: 502 });
      expect(res.category).toBe("malformed_response");
      expect(res.title).toContain("không đúng định dạng");
    }
  });

  test("maps timeout and uncertainty to timeout category", () => {
    const res1 = describeDiagnosticFailure({
      code: "chat_provider_uncertain",
      http_status: 504,
    });
    expect(res1.category).toBe("timeout");

    const res2 = describeDiagnosticFailure({
      code: "request_timeout",
      http_status: 408,
    });
    expect(res2.category).toBe("timeout");
  });

  test("maps 502/503 without specific token code to unavailable", () => {
    const res = describeDiagnosticFailure({
      code: "bad_gateway",
      http_status: 502,
      detail: "Upstream gateway not reachable",
    });
    expect(res.category).toBe("unavailable");
  });

  test("maps generic 400/422 without token limits to general", () => {
    const res = describeDiagnosticFailure({
      code: "invalid_argument",
      http_status: 400,
      detail: "Invalid temperature parameter",
    });
    expect(res.category).toBe("general");
  });
});

// =========================================================================
// P2-4: Provenance per field in CapacityPanel
// =========================================================================
describe("P2-4: Provenance source per field in CapacityPanel", () => {
  test.each([true, false])(
    "OCR child values inherit ocr_page_input provenance (field_sources=%s)",
    (hasFieldSources) => {
      const limits: TokenLimits = {
        ...declaredLimits,
        ocr_page_input: {
          max_image_width: 1664,
          max_image_height: 2048,
          input_tokens_upper_bound: 2758,
          prompt_sha256: "a".repeat(64),
        },
      };
      const provider = savedProvider({
        capabilities: ["ocr"],
        token_limits: limits,
        field_sources: hasFieldSources
          ? {
              ocr_page_input: "operator_configured",
              context_window_tokens: "server_reported",
            }
          : {},
        operational_budgets: {
          ocr: modelBudget({
            token_limits: limits,
            sources: {
              ocr_page_input: "operator_configured",
              context_window_tokens: "server_reported",
            },
          }),
        },
      });
      wrap(<CapacityPanel provider={provider} />);
      expect(
        knownLimitRow("input_tokens_upper_bound").getByText(
          "Khai báo thủ công",
        ),
      ).toBeTruthy();
      expect(
        knownLimitRow("input_tokens_upper_bound").queryByText("Server công bố"),
      ).toBeNull();
      expect(
        knownLimitRow("context_window_tokens").getByText("Server công bố"),
      ).toBeTruthy();
    },
  );
  test("displays distinct provenance per field based on field_sources", () => {
    const providerWithMixedSources = savedProvider({
      id: "prov-mixed-1",
      name: "Mixed Source Provider",
      provider_type: "openai_compatible",
      base_url: "https://mixed.example.com/v1",
      model_name: "mixed-model-v1",
      capabilities: ["chat"],
      token_limits: {
        context_window_tokens: 131072,
        max_input_tokens: 122880,
        max_output_tokens: 8192,
        ocr_page_input: null,
      },
      capacity_basis: "server_reported",
      capacity_status: "configured",
      field_sources: {
        context_window_tokens: "server_reported",
        max_input_tokens: "server_reported",
        max_output_tokens: "operator_configured",
      },
      created_at: "2026-11-01T00:00:00Z",
      updated_at: "2026-11-01T00:00:00Z",
    });

    wrap(<CapacityPanel provider={providerWithMixedSources} />);

    // Context row displays "Server công bố"
    expect(
      knownLimitRow("context_window_tokens").getByText("Server công bố"),
    ).toBeTruthy();
    expect(
      knownLimitRow("context_window_tokens").getByText("131.072 token"),
    ).toBeTruthy();

    // Max output row displays "Khai báo thủ công"
    expect(
      knownLimitRow("max_output_tokens").getByText("Khai báo thủ công"),
    ).toBeTruthy();
  });

  test("falls back to operational_budgets source when field_sources is empty", () => {
    const providerWithBudgetSources = savedProvider({
      id: "prov-budget-sources",
      name: "Budget Sourced Provider",
      provider_type: "openai_compatible",
      base_url: "https://budget.example.com/v1",
      model_name: "budget-model",
      capabilities: ["chat"],
      token_limits: {
        context_window_tokens: 65536,
        max_input_tokens: 49152,
        max_output_tokens: 16384,
        ocr_page_input: null,
      },
      capacity_basis: "server_reported",
      capacity_status: "configured",
      operational_budgets: {
        chat: modelBudget({
          token_limits: {
            context_window_tokens: 65536,
            max_input_tokens: 49152,
            max_output_tokens: 16384,
            ocr_page_input: null,
          },
          sources: {
            context_window_tokens: "server_reported",
            max_input_tokens: "server_reported",
            max_output_tokens: "operator_configured",
          },
        }),
      },
      created_at: "2026-11-01T00:00:00Z",
      updated_at: "2026-11-01T00:00:00Z",
    });

    wrap(<CapacityPanel provider={providerWithBudgetSources} />);

    // Output row resolves operator_configured from chat budget sources
    expect(
      knownLimitRow("max_output_tokens").getByText("Khai báo thủ công"),
    ).toBeTruthy();
  });
});
