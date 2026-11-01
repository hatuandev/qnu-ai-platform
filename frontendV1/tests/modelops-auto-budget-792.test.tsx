// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
  BUDGET_SOURCE_LABELS,
  BUDGET_STATUS_LABELS,
  CapacityBadge,
  ConsumerModelBudgetNotice,
  describeDiagnosticFailure,
  formatTokenLimitValue,
  OperationalBudgetBadge,
  ProviderOperationalBudgetsSummary,
  resolveCapabilityBudgetState,
} from "@/features/modelops/capacity-badge";
import {
  buildClearTokenLimitsPatch,
  buildProviderPatch,
  draftFromProvider,
  EMPTY_CAPACITY_DRAFT,
  formValuesFromProvider,
  validateCapacityDraft,
} from "@/features/modelops/capacity-patch";
import { buildConnectionModelPayload } from "@/features/modelops/connections/api";
import { ImportModelsDialog } from "@/features/modelops/connections/import-models-dialog";
import { ModelForm } from "@/features/modelops/connections/model-form";
import { ModelTestModal } from "@/features/modelops/connections/model-test-modal";
import { CapacityPanel } from "@/features/modelops/provider-detail";
import { ProviderFormDialog } from "@/features/modelops/provider-form-dialog";
import type { Provider } from "@/features/modelops/types";

const state = vi.hoisted(() => ({
  createProvider: vi.fn(),
  updateProvider: vi.fn(),
  discover: vi.fn(),
  sync: vi.fn(),
  addConnectionModel: vi.fn(),
  runDiagnostic: vi.fn(),
  checks: [] as object[],
  canManage: true,
}));

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children }: { children: ReactNode }) => <span>{children}</span>,
}));

vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({
    sessionId: "sess_test",
    isAuthenticated: true,
    actor: {
      id: "user_1",
      email: "admin@qnu.edu.vn",
      display_name: "Admin",
      permissions: state.canManage
        ? ["ai.models.manage", "ai.keys.manage"]
        : ["ai.models.read"],
    },
  }),
  isModelAdmin: (actor?: { permissions?: string[] } | null) =>
    Boolean(actor?.permissions?.includes("ai.models.manage")),
}));

vi.mock("@/features/modelops/queries", () => ({
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
      {
        provider_type: "openai_compatible",
        label: "OpenAI Compatible",
        protocols: { chat: "openai" },
        responses_api: false,
      },
    ],
    isError: false,
  }),
}));

vi.mock("@/features/modelops/diagnostic-queries", () => ({
  useDiagnostics: () => ({ data: { checks: state.checks } }),
  useRunDiagnostic: () => ({
    isPending: false,
    mutateAsync: (kind: string) => state.runDiagnostic(kind),
  }),
}));

vi.mock("@/features/modelops/connections/api", async (original) => ({
  ...(await original<typeof import("@/features/modelops/connections/api")>()),
  useAddConnectionModel: () => ({
    isPending: false,
    isError: false,
    error: null,
    reset: vi.fn(),
    mutateAsync: (payload: unknown) => state.addConnectionModel(payload),
  }),
  useSyncConnectionCapacity: () => ({
    isPending: false,
    mutateAsync: (payload: unknown) => state.sync(payload),
  }),
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

function makeBaseProvider(overrides: Partial<Provider> = {}): Provider {
  return {
    id: "prov_test_792",
    parent_id: "conn_test_792",
    name: "QNU Chat Model",
    provider_type: "openai_compatible",
    base_url: "http://127.0.0.1:8000/v1",
    model_name: "qwen3-8b",
    capabilities: ["chat"],
    is_active: true,
    priority: 5,
    timeout_seconds: 30,
    token_limits: null,
    capacity_status: "unknown",
    capacity_basis: null,
    operational_budgets: {
      chat: {
        version: "qnu.operational-budget/v1",
        status: "provisional",
        token_limits: {
          context_window_tokens: 32768,
          max_input_tokens: 32768,
          max_output_tokens: 4096,
          ocr_page_input: null,
        },
        sources: {
          context_window_tokens: "application_default",
          max_input_tokens: "application_default",
          max_output_tokens: "application_default",
        },
        reason_code: null,
      },
    },
    embedding_dimension: null,
    embedding_dimension_status: "unknown",
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-01T00:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  state.checks = [];
  state.canManage = true;
  state.createProvider.mockResolvedValue(makeBaseProvider());
  state.updateProvider.mockResolvedValue(makeBaseProvider());
  state.addConnectionModel.mockResolvedValue(makeBaseProvider());
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ModelOps FE Auto-Budget & Optional Token Limits (Session 792)", () => {
  test("1. Creating provider/model without entering token_limits omits token_limits and never sends 0", async () => {
    render(<ProviderFormDialog open onOpenChange={vi.fn()} provider={null} />);

    // Advanced section is collapsed by default
    const advancedBtn = screen.getByRole("button", { name: /Nâng cao/i });
    expect(advancedBtn.getAttribute("aria-expanded")).toBe("false");

    fireEvent.change(screen.getByLabelText("Tên provider"), {
      target: { value: "QNU Local vLLM" },
    });
    fireEvent.change(screen.getByLabelText("Base URL"), {
      target: { value: "http://127.0.0.1:8000/v1" },
    });
    fireEvent.change(screen.getByLabelText("Model name"), {
      target: { value: "qwen3-8b" },
    });
    fireEvent.click(screen.getByRole("checkbox", { name: "Chat" }));

    fireEvent.click(screen.getByRole("button", { name: "Tạo provider" }));

    await waitFor(() => expect(state.createProvider).toHaveBeenCalledTimes(1));
    const payload = state.createProvider.mock.calls[0][0] as Record<
      string,
      unknown
    >;
    expect(payload.name).toBe("QNU Local vLLM");
    expect(payload.model_name).toBe("qwen3-8b");
    expect(payload.capabilities).toEqual(["chat"]);
    expect("token_limits" in payload).toBe(false);
    expect("embedding_dimension" in payload).toBe(false);
  });

  test("2 & 3. Discovery with ID only, partial metadata, and full metadata saves cleanly without fabricating limits", async () => {
    state.runDiagnostic.mockResolvedValue({
      id: "diag_792",
      kind: "discovery",
      outcome: "ok",
      configuration_status: "current",
      models: ["model-id-only", "model-partial", "model-full"],
      model_metadata: [
        {
          id: "model-id-only",
          context_window_tokens: null,
          max_output_tokens: null,
          embedding_dimension: null,
        },
        {
          id: "model-partial",
          context_window_tokens: 65536,
          max_output_tokens: null,
          embedding_dimension: null,
        },
        {
          id: "model-full",
          context_window_tokens: 131072,
          max_output_tokens: 16384,
          embedding_dimension: null,
        },
      ],
    });

    render(
      <ImportModelsDialog
        open
        onOpenChange={vi.fn()}
        connectionId="conn_test_792"
        connectionName="QNU Server"
        existingModels={[]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Lấy lại" }));
    await screen.findByText("model-id-only");
    await screen.findByText("Server chưa công bố giới hạn");
    await screen.findByText("Context 65.536");
    await screen.findByText("Context 131.072 · Đầu ra 16.384");

    // Select model-id-only (has no metadata) and model-full (has metadata)
    fireEvent.click(screen.getByRole("checkbox", { name: "model-id-only" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "model-full" }));
    fireEvent.click(screen.getByRole("button", { name: "Áp dụng" }));

    await waitFor(() =>
      expect(state.addConnectionModel).toHaveBeenCalledTimes(2),
    );
    // model-id-only must NOT send discovery_check_id (since metadata is all null) and must NOT send token_limits
    expect(state.addConnectionModel).toHaveBeenNthCalledWith(1, {
      model_name: "model-id-only",
      capabilities: ["chat"],
    });
    // model-full sends discovery_check_id without copying untrusted numbers into token_limits
    expect(state.addConnectionModel).toHaveBeenNthCalledWith(2, {
      model_name: "model-full",
      capabilities: ["chat"],
      discovery_check_id: "diag_792",
    });
  });

  test("4 & 7. Operational budgets (declared, provisional, blocked) and capacity statuses (unknown, configured, stale) render distinct labels and never show 0 or unlimited", () => {
    expect(formatTokenLimitValue(null)).toBe("Chưa công bố");
    expect(formatTokenLimitValue(undefined)).toBe("Chưa công bố");
    expect(formatTokenLimitValue(32768)).not.toContain("0 token");
    expect(formatTokenLimitValue(null)).not.toContain("unlimited");

    const provisionalProvider = makeBaseProvider();
    const { unmount } = render(
      <div>
        <CapacityBadge status={provisionalProvider.capacity_status} />
        <ProviderOperationalBudgetsSummary provider={provisionalProvider} />
      </div>,
    );
    expect(screen.getByText("Chưa công bố")).toBeDefined();
    expect(screen.getByText(BUDGET_STATUS_LABELS.provisional)).toBeDefined();
    expect(screen.queryByText("Đã kiểm chứng")).toBeNull();
    unmount();

    const declaredProvider = makeBaseProvider({
      capacity_status: "configured",
      capacity_basis: "operator_configured",
      token_limits: {
        context_window_tokens: 65536,
        max_input_tokens: 49152,
        max_output_tokens: 8192,
        ocr_page_input: null,
      },
      operational_budgets: {
        chat: {
          version: "qnu.operational-budget/v1",
          status: "declared",
          token_limits: {
            context_window_tokens: 65536,
            max_input_tokens: 49152,
            max_output_tokens: 8192,
            ocr_page_input: null,
          },
          sources: {
            context_window_tokens: "operator_configured",
            max_input_tokens: "operator_configured",
            max_output_tokens: "operator_configured",
          },
          reason_code: null,
        },
      },
    });
    const { unmount: unmount2 } = render(
      <div>
        <CapacityBadge
          status={declaredProvider.capacity_status}
          basis={declaredProvider.capacity_basis}
        />
        <ProviderOperationalBudgetsSummary provider={declaredProvider} />
      </div>,
    );
    expect(screen.getByText("Đã khai báo")).toBeDefined();
    expect(screen.getByText(BUDGET_STATUS_LABELS.declared)).toBeDefined();
    expect(screen.queryByText("Đã kiểm chứng")).toBeNull();
    unmount2();

    const staleProvider = makeBaseProvider({
      capacity_status: "stale",
      operational_budgets: {
        chat: {
          version: "qnu.operational-budget/v1",
          status: "blocked",
          token_limits: null,
          sources: {},
          reason_code: "model_token_limits_stale",
        },
      },
    });
    render(
      <div>
        <CapacityBadge status={staleProvider.capacity_status} />
        <OperationalBudgetBadge model={staleProvider} capability="chat" />
      </div>,
    );
    expect(screen.getByText("Cần cập nhật")).toBeDefined();
    expect(screen.getByText(BUDGET_STATUS_LABELS.blocked)).toBeDefined();
  });

  test("5. Manual custom model entry works when /models endpoint is unsupported or model is unlisted", async () => {
    render(
      <ModelForm
        open
        onOpenChange={vi.fn()}
        connectionId="conn_test_792"
        discoveredModels={[]}
        discoveryError="Endpoint không hỗ trợ /models"
      />,
    );

    expect(screen.getByText(/Endpoint không hỗ trợ \/models/)).toBeDefined();
    fireEvent.change(screen.getByLabelText("ID model trên server"), {
      target: { value: "custom-reranker-v2" },
    });
    fireEvent.click(screen.getByRole("checkbox", { name: "Rerank" }));
    fireEvent.click(screen.getByRole("button", { name: "Thêm model" }));

    await waitFor(() =>
      expect(state.addConnectionModel).toHaveBeenCalledTimes(1),
    );
    const submitted = state.addConnectionModel.mock.calls[0][0] as Record<
      string,
      unknown
    >;
    expect(submitted.model_name).toBe("custom-reranker-v2");
    expect(submitted.capabilities).toEqual(["rerank"]);
    expect("token_limits" in submitted).toBe(false);
    expect("discovery_check_id" in submitted).toBe(false);
  });

  test("6. Validation in Advanced section rejects <= 0, decimals, max_input > context, max_output > context, and partial OCR", () => {
    expect(
      validateCapacityDraft({
        ...EMPTY_CAPACITY_DRAFT,
        contextWindowTokens: "0",
      }),
    ).toContain("số nguyên dương");

    expect(
      validateCapacityDraft({
        ...EMPTY_CAPACITY_DRAFT,
        contextWindowTokens: "-100",
      }),
    ).toContain("số nguyên dương");

    expect(
      validateCapacityDraft({
        ...EMPTY_CAPACITY_DRAFT,
        contextWindowTokens: "1024.5",
      }),
    ).toContain("số nguyên dương");

    expect(
      validateCapacityDraft({
        ...EMPTY_CAPACITY_DRAFT,
        contextWindowTokens: "8192",
        maxInputTokens: "16384",
      }),
    ).toContain("max_input_tokens không được vượt context_window_tokens");

    expect(
      validateCapacityDraft({
        ...EMPTY_CAPACITY_DRAFT,
        contextWindowTokens: "8192",
        maxOutputTokens: "16384",
      }),
    ).toContain("max_output_tokens không được vượt context_window_tokens");

    expect(
      validateCapacityDraft({
        ...EMPTY_CAPACITY_DRAFT,
        maxOutputTokens: "4096",
        ocrMaxImageWidth: "1200",
      }),
    ).toContain("ocr_page_input cần đủ");
  });

  test("8, 9 & 10. Editing provider does NOT copy provisional operational_budgets into token_limits, preserves existing limits on rename/timeout edit, and clears with null after confirmation", async () => {
    const provisional = makeBaseProvider();
    // 8. draftFromProvider must leave fields empty when token_limits is null even if operational_budgets has 32768/4096
    const draft = draftFromProvider(provisional);
    expect(draft.contextWindowTokens).toBe("");
    expect(draft.maxInputTokens).toBe("");
    expect(draft.maxOutputTokens).toBe("");
    expect(
      buildProviderPatch(provisional, formValuesFromProvider(provisional)),
    ).toEqual({});

    // 9 & 10. Opening ProviderFormDialog on a declared model and changing model_name/timeout does not send token_limits: null
    const declared = makeBaseProvider({
      capacity_status: "configured",
      capacity_basis: "operator_configured",
      token_limits: {
        context_window_tokens: 65536,
        max_input_tokens: 32768,
        max_output_tokens: 8192,
        ocr_page_input: null,
      },
      operational_budgets: {
        chat: {
          version: "qnu.operational-budget/v1",
          status: "declared",
          token_limits: {
            context_window_tokens: 65536,
            max_input_tokens: 32768,
            max_output_tokens: 8192,
            ocr_page_input: null,
          },
          sources: {
            context_window_tokens: "operator_configured",
            max_input_tokens: "operator_configured",
            max_output_tokens: "operator_configured",
          },
          reason_code: null,
        },
      },
    });

    const { unmount } = render(
      <ProviderFormDialog open onOpenChange={vi.fn()} provider={declared} />,
    );
    fireEvent.change(screen.getByLabelText("Model name"), {
      target: { value: "qwen3-14b" },
    });
    fireEvent.change(screen.getByLabelText("Timeout (giây)"), {
      target: { value: "45" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu thay đổi" }));

    await waitFor(() => expect(state.updateProvider).toHaveBeenCalledTimes(1));
    const patch = state.updateProvider.mock.calls[0][1] as Record<
      string,
      unknown
    >;
    expect(patch.model_name).toBe("qwen3-14b");
    expect(patch.timeout_seconds).toBe(45);
    expect("token_limits" in patch).toBe(false);
    unmount();

    // Clearing declared limits via CapacityPanel requires confirmation and sends { token_limits: null }
    expect(buildClearTokenLimitsPatch()).toEqual({ token_limits: null });
    render(
      <CapacityPanel provider={declared} canManage={true} onEdit={vi.fn()} />,
    );
    expect(screen.getByText("Giới hạn đã biết của model")).toBeDefined();
    expect(screen.getByText("Ngân sách đang áp dụng")).toBeDefined();
    expect(
      screen.getAllByText(BUDGET_SOURCE_LABELS.operator_configured).length,
    ).toBeGreaterThan(0);

    fireEvent.click(
      screen.getByRole("button", { name: "Xóa khai báo giới hạn" }),
    );
    // Confirm dialog opens
    const confirmBtn = await screen.findByRole("button", {
      name: "Xác nhận xóa khai báo",
    });
    fireEvent.click(confirmBtn);

    await waitFor(() =>
      expect(state.updateProvider).toHaveBeenCalledWith("prov_test_792", {
        token_limits: null,
      }),
    );
  });

  test("11. buildConnectionModelPayload never allows discovery_check_id and manual token_limits simultaneously", () => {
    expect(() =>
      buildConnectionModelPayload({
        model_name: "qwen3-8b",
        capabilities: ["chat"],
        discovery_check_id: "diag_792",
        token_limits: {
          context_window_tokens: 32768,
          max_input_tokens: null,
          max_output_tokens: 4096,
          ocr_page_input: null,
        },
      }),
    ).toThrow(/Không gửi đồng thời/);

    const withDiscoveryOnly = buildConnectionModelPayload({
      model_name: "qwen3-8b",
      capabilities: ["chat"],
      discovery_check_id: "diag_792",
      token_limits: null,
      embedding_dimension: null,
    });
    expect(withDiscoveryOnly.discovery_check_id).toBe("diag_792");
    expect("token_limits" in withDiscoveryOnly).toBe(false);
    expect("embedding_dimension" in withDiscoveryOnly).toBe(false);
  });

  test("12. Server errors (429/quota, token budget, malformed response, timeout) are distinctly classified and rendered", async () => {
    expect(
      describeDiagnosticFailure({
        code: "provider_rate_limited",
        httpStatus: 429,
      }).category,
    ).toBe("quota_rate_limit");
    expect(
      describeDiagnosticFailure({
        code: "model_output_limit_exceeded",
        httpStatus: 422,
      }).category,
    ).toBe("token_budget");
    expect(
      describeDiagnosticFailure({
        code: "provider_response_malformed",
        httpStatus: 502,
      }).category,
    ).toBe("malformed_response");
    expect(
      describeDiagnosticFailure({
        code: "provider_timeout",
        httpStatus: 504,
      }).category,
    ).toBe("timeout");

    state.runDiagnostic.mockResolvedValueOnce({
      id: "diag_429",
      kind: "chat",
      outcome: "failed",
      configuration_status: "current",
      code: "provider_rate_limited",
      http_status: 429,
      detail: "Upstream returned 429 Too Many Requests",
      latency_ms: 120,
      tested_at: "2026-11-01T00:00:00Z",
    });

    render(
      <ModelTestModal
        open
        onOpenChange={vi.fn()}
        model={makeBaseProvider()}
        connectionName="QNU Server"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Chạy kiểm thử/i }));
    await screen.findByText(/Giới hạn tần suất hoặc vượt hạn mức/i);
  });

  test("13 & 14. Permissions hide edit/clear actions when lacking ai.models.manage, and API keys never leak in DOM", () => {
    const declared = makeBaseProvider({
      capacity_status: "configured",
      token_limits: {
        context_window_tokens: 65536,
        max_input_tokens: null,
        max_output_tokens: 8192,
        ocr_page_input: null,
      },
    });
    render(
      <CapacityPanel provider={declared} canManage={false} onEdit={vi.fn()} />,
    );
    expect(
      screen.queryByRole("button", { name: "Khai báo / cập nhật" }),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Xóa khai báo giới hạn" }),
    ).toBeNull();
    expect(document.body.innerHTML).not.toContain("sk-");
  });

  test("15. Consumers allow chat/rerank with capacity_status=unknown + provisional budget, and block stale, OCR missing bound, and embedding missing dimension", () => {
    const chatProvisional = makeBaseProvider({
      capacity_status: "unknown",
    });
    expect(
      resolveCapabilityBudgetState(chatProvisional, "chat").isBlocked,
    ).toBe(false);
    expect(resolveCapabilityBudgetState(chatProvisional, "chat").status).toBe(
      "provisional",
    );

    const staleModel = makeBaseProvider({
      capacity_status: "stale",
      operational_budgets: {
        chat: {
          version: "qnu.operational-budget/v1",
          status: "blocked",
          token_limits: null,
          sources: {},
          reason_code: "model_token_limits_stale",
        },
      },
    });
    expect(resolveCapabilityBudgetState(staleModel, "chat").isBlocked).toBe(
      true,
    );

    const ocrUnknown = makeBaseProvider({
      capabilities: ["ocr"],
      capacity_status: "unknown",
      operational_budgets: {
        ocr: {
          version: "qnu.operational-budget/v1",
          status: "blocked",
          token_limits: null,
          sources: {},
          reason_code: "model_input_budget_unknown",
        },
      },
    });
    expect(resolveCapabilityBudgetState(ocrUnknown, "ocr").isBlocked).toBe(
      true,
    );

    const embeddingUnknown = makeBaseProvider({
      capabilities: ["embedding"],
      embedding_dimension: null,
      embedding_dimension_status: "unknown",
      operational_budgets: {
        embedding: {
          version: "qnu.operational-budget/v1",
          status: "blocked",
          token_limits: null,
          sources: {},
          reason_code: "embedding_dimension_unknown",
        },
      },
    });
    expect(
      resolveCapabilityBudgetState(embeddingUnknown, "embedding").isBlocked,
    ).toBe(true);

    const { unmount } = render(
      <ConsumerModelBudgetNotice model={chatProvisional} capability="chat" />,
    );
    expect(screen.getByText(BUDGET_STATUS_LABELS.provisional)).toBeDefined();
    unmount();

    render(<ConsumerModelBudgetNotice model={ocrUnknown} capability="ocr" />);
    expect(screen.getByText(/Cần bổ sung thông tin \(OCR\)/)).toBeDefined();
  });
});
