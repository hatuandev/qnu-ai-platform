import type {
  ConflictStrategy,
  ModelProvider,
  ProviderApiKey,
  ProviderBulkExportResponse,
  ProviderImportResponse,
  ProviderModelsTestResponse,
  ProviderPreset,
  ProviderSingleExportResponse,
  SystemModelDefaults,
  SystemModelDefaultsResponse,
  TokenQuota,
  UsageStatsResponse,
} from "@/types/modelops";
import { BASE_URL } from "./http-client";

export const modelopsApi = {
  async getModelProviders(): Promise<ModelProvider[]> {
    const res = await fetch(`${BASE_URL}/modelops/providers`);
    if (!res.ok) {
      throw new Error(
        `Không tải được danh sách nhà cung cấp mô hình (HTTP ${res.status}).`,
      );
    }
    const data = await res.json();
    if (!Array.isArray(data)) {
      return [];
    }
    return data.map((item, idx) => {
      const d = item as Record<string, unknown>;
      const rawModels = Array.isArray(d.models)
        ? (d.models as string[])
        : typeof d.model_name === "string" && d.model_name
          ? [d.model_name]
          : [];
      return {
        id: (d.id as string) || `prov_${idx + 1}`,
        name: (d.name as string) || "LLM Provider",
        code: (d.code as string) || (d.provider_type as string) || "llm",
        type: ((d.type as string) ||
          (d.provider_type as string) ||
          "openai") as ModelProvider["type"],
        is_active: typeof d.is_active === "boolean" ? d.is_active : true,
        circuit_breaker_status:
          (d.circuit_breaker_status as "CLOSED" | "OPEN" | "HALF_OPEN") ||
          "CLOSED",
        models: rawModels,
        model_name: (d.model_name as string) || undefined,
        api_base_url: (d.api_base_url as string) || undefined,
        api_key_masked: (d.api_key_masked as string) || undefined,
        account_id: (d.account_id as string) || undefined,
        latency_ms: typeof d.latency_ms === "number" ? d.latency_ms : 0,
        failure_rate: typeof d.failure_rate === "number" ? d.failure_rate : 0.0,
        priority: typeof d.priority === "number" ? d.priority : idx + 1,
        timeout_seconds:
          typeof d.timeout_seconds === "number" ? d.timeout_seconds : 15,
        keys_count: typeof d.keys_count === "number" ? d.keys_count : 0,
        api_keys: Array.isArray(d.api_keys)
          ? (d.api_keys as ProviderApiKey[])
          : [],
      };
    });
  },

  async getProviderPresets(): Promise<ProviderPreset[]> {
    try {
      const res = await fetch(`${BASE_URL}/modelops/presets`);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback
    }
    return [];
  },

  async seedDefaultProviders(overwrite = false): Promise<ModelProvider[]> {
    try {
      const res = await fetch(
        `${BASE_URL}/modelops/providers/seed-defaults?overwrite=${overwrite}`,
        {
          method: "POST",
        },
      );
      if (res.ok) {
        return await this.getModelProviders();
      }
    } catch {
      // Fallback
    }
    return await this.getModelProviders();
  },

  async createModelProvider(payload: {
    name: string;
    provider_type: string;
    model_name?: string;
    models?: string[];
    api_base_url?: string;
    api_key?: string;
    account_id?: string;
    priority?: number;
    timeout_seconds?: number;
    is_active?: boolean;
  }): Promise<ModelProvider> {
    const res = await fetch(`${BASE_URL}/modelops/providers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Thêm Provider thất bại");
    return await res.json();
  },

  async updateModelProvider(
    id: string,
    payload: Partial<{
      name: string;
      provider_type: string;
      model_name?: string;
      models?: string[];
      api_base_url?: string;
      api_key?: string;
      account_id?: string;
      priority?: number;
      timeout_seconds?: number;
      is_active?: boolean;
    }>,
  ): Promise<ModelProvider> {
    const res = await fetch(`${BASE_URL}/modelops/providers/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Cập nhật Provider thất bại");
    return await res.json();
  },

  async deleteModelProvider(id: string): Promise<{ deleted: boolean }> {
    const res = await fetch(`${BASE_URL}/modelops/providers/${id}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Xóa Provider thất bại");
    return await res.json();
  },

  async toggleModelProvider(
    id: string,
  ): Promise<{ id: string; is_active: boolean }> {
    const res = await fetch(`${BASE_URL}/modelops/providers/${id}/toggle`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Đổi trạng thái Provider thất bại");
    return await res.json();
  },

  async testModelProvider(
    id: string,
  ): Promise<{ success: boolean; latency_ms: number; message: string }> {
    const res = await fetch(`${BASE_URL}/modelops/providers/${id}/test`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Kiểm tra kết nối thất bại");
    return await res.json();
  },

  async testProviderModels(
    providerId: string,
    modelName?: string,
  ): Promise<ProviderModelsTestResponse> {
    const res = await fetch(
      `${BASE_URL}/modelops/providers/${providerId}/models/test`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(modelName ? { model_name: modelName } : {}),
      },
    );
    if (!res.ok) throw new Error("Kiểm tra mô hình của Provider thất bại");
    return await res.json();
  },

  async getProviderKeys(providerId: string): Promise<ProviderApiKey[]> {
    const res = await fetch(
      `${BASE_URL}/modelops/providers/${providerId}/keys`,
    );
    if (!res.ok) throw new Error("Không thể tải danh sách khóa API");
    return await res.json();
  },

  async addProviderKey(
    providerId: string,
    payload: {
      name: string;
      api_key: string;
      account_id?: string;
      priority?: number;
      quota_limit?: number;
    },
  ): Promise<ProviderApiKey> {
    const res = await fetch(
      `${BASE_URL}/modelops/providers/${providerId}/keys`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) throw new Error("Thêm khóa API vào nhóm thất bại");
    return await res.json();
  },

  async updateProviderKey(
    providerId: string,
    keyId: string,
    payload: Partial<{
      name: string;
      account_id: string | null;
      priority: number;
      is_active: boolean;
      status: string;
      quota_limit: number | null;
    }>,
  ): Promise<ProviderApiKey> {
    const res = await fetch(
      `${BASE_URL}/modelops/providers/${providerId}/keys/${keyId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) throw new Error("Cập nhật khóa API thất bại");
    return await res.json();
  },

  async toggleProviderKey(
    providerId: string,
    keyId: string,
    isActive: boolean,
  ): Promise<ProviderApiKey> {
    return this.updateProviderKey(providerId, keyId, { is_active: isActive });
  },

  async deleteProviderKey(
    providerId: string,
    keyId: string,
  ): Promise<{ success: boolean; deleted_id: string }> {
    const res = await fetch(
      `${BASE_URL}/modelops/providers/${providerId}/keys/${keyId}`,
      {
        method: "DELETE",
      },
    );
    if (!res.ok) throw new Error("Xóa khóa API thất bại");
    return await res.json();
  },

  async testProviderKey(
    providerId: string,
    keyId: string,
  ): Promise<{ success: boolean; latency_ms: number; message: string }> {
    const res = await fetch(
      `${BASE_URL}/modelops/providers/${providerId}/keys/${keyId}/test`,
      {
        method: "POST",
      },
    );
    if (!res.ok) throw new Error("Kiểm tra khóa thất bại");
    return await res.json();
  },

  async revealProviderKey(
    providerId: string,
    keyId: string,
  ): Promise<{ api_key: string }> {
    const res = await fetch(
      `${BASE_URL}/modelops/providers/${providerId}/keys/${keyId}/reveal`,
      { method: "POST" },
    );
    if (!res.ok) throw new Error("Không thể lấy giá trị khóa API");
    return await res.json();
  },

  async simulateKeyRotation(
    providerId: string,
    payload: {
      tokens_consumed?: number;
      trigger_rate_limit?: boolean;
      cooldown_seconds?: number;
    },
  ): Promise<{
    success: boolean;
    previous_key_id: string;
    previous_key_name: string;
    next_key_id: string | null;
    next_key_name: string | null;
    tokens_consumed: number;
    rate_limit_triggered: boolean;
    rotated: boolean;
    message: string;
  }> {
    const res = await fetch(
      `${BASE_URL}/modelops/providers/${providerId}/keys/simulate-rotation`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Mô phỏng xoay key thất bại");
    }
    return await res.json();
  },

  async getSystemModelDefaults(): Promise<SystemModelDefaultsResponse> {
    const res = await fetch(`${BASE_URL}/modelops/defaults`);
    if (!res.ok) throw new Error("Không thể tải cấu hình mô hình mặc định");
    return await res.json();
  },

  async updateSystemModelDefaults(
    payload: Partial<SystemModelDefaults>,
  ): Promise<SystemModelDefaultsResponse> {
    const res = await fetch(`${BASE_URL}/modelops/defaults`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Cập nhật cấu hình mô hình mặc định thất bại");
    return await res.json();
  },

  async setProviderModelAsDefault(
    providerId: string,
    role: "embedding" | "reranker" | "ocr",
    modelName: string,
  ): Promise<SystemModelDefaultsResponse> {
    const res = await fetch(
      `${BASE_URL}/modelops/providers/${providerId}/set-default`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role, model_name: modelName }),
      },
    );
    if (!res.ok) throw new Error("Đặt mô hình mặc định thất bại");
    return await res.json();
  },

  async getTokenQuota(tenantId = "tenant_qnu"): Promise<TokenQuota> {
    const res = await fetch(`${BASE_URL}/modelops/quotas/${tenantId}`);
    if (!res.ok) {
      throw new Error(
        `Không tải được thông tin hạn ngạch token (HTTP ${res.status}).`,
      );
    }
    const raw = await res.json();
    const d = raw as Record<string, unknown>;
    return {
      tenant_id: (d.tenant_id as string) || "tenant_qnu",
      total_tokens:
        typeof d.tokens_used === "number"
          ? d.tokens_used
          : typeof d.total_tokens === "number"
            ? d.total_tokens
            : 0,
      limit_tokens:
        typeof d.monthly_token_limit === "number"
          ? d.monthly_token_limit
          : typeof d.limit_tokens === "number"
            ? d.limit_tokens
            : 5000000,
      usd_cost:
        typeof d.cost_used_usd === "number"
          ? d.cost_used_usd
          : typeof d.usd_cost === "number"
            ? d.usd_cost
            : 0.0,
      reset_date: (d.reset_date as string) || "2026-10-01",
      provider_breakdown:
        (d.provider_breakdown as TokenQuota["provider_breakdown"]) || {
          openai_tokens: 0,
          gemini_tokens: 0,
          local_tokens: 0,
        },
    };
  },

  async getTokenQuotas(tenantId?: string): Promise<TokenQuota> {
    return this.getTokenQuota(tenantId);
  },

  async getModelOpsUsageStats(
    days = 30,
    tenantId?: string,
  ): Promise<UsageStatsResponse> {
    const params = new URLSearchParams({ days: String(days) });
    if (tenantId) params.append("tenant_id", tenantId);

    const res = await fetch(
      `${BASE_URL}/modelops/usage-stats?${params.toString()}`,
    );
    if (!res.ok) {
      throw new Error(`Không tải được thống kê sử dụng (HTTP ${res.status}).`);
    }
    return res.json();
  },

  async exportProvider(
    providerId: string,
    includeSecrets = true,
  ): Promise<ProviderSingleExportResponse> {
    const res = await fetch(
      `${BASE_URL}/modelops/providers/${providerId}/export?include_secrets=${includeSecrets}`,
    );
    if (!res.ok)
      throw new Error(`Xuất cấu hình Provider thất bại (HTTP ${res.status})`);
    return await res.json();
  },

  async exportAllProviders(
    includeSecrets = true,
  ): Promise<ProviderBulkExportResponse> {
    const res = await fetch(
      `${BASE_URL}/modelops/providers/export?include_secrets=${includeSecrets}`,
    );
    if (!res.ok)
      throw new Error(`Xuất toàn bộ Provider thất bại (HTTP ${res.status})`);
    return await res.json();
  },

  async importProviders(
    data: unknown,
    conflictStrategy: ConflictStrategy = "overwrite",
  ): Promise<ProviderImportResponse> {
    const res = await fetch(`${BASE_URL}/modelops/providers/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data, conflict_strategy: conflictStrategy }),
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(
        errJson.detail || `Nhập cấu hình thất bại (HTTP ${res.status})`,
      );
    }
    return await res.json();
  },
};
