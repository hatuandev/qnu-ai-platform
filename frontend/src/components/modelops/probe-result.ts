import type {
  ModelProvider,
  SingleModelTestResult,
  SystemModelDefaults,
} from "@/types/modelops";

export function getConfiguredCapabilities(
  provider: Pick<ModelProvider, "id" | "model_capabilities" | "model_specs">,
  model: string,
  defaults?: SystemModelDefaults,
) {
  const config = provider.model_capabilities?.[model];
  const declared = provider.model_specs?.[model]?.type;
  const declaredRole =
    declared === "chat" ||
    declared === "embedding" ||
    declared === "reranker" ||
    declared === "ocr"
      ? declared
      : undefined;
  const role =
    config?.probe_role ??
    declaredRole ??
    (defaults?.default_embedding_provider_id === provider.id &&
    defaults.default_embedding_model === model
      ? "embedding"
      : defaults?.default_reranker_provider_id === provider.id &&
          defaults.default_reranker_model === model
        ? "reranker"
        : defaults?.default_ocr_provider_id === provider.id &&
            defaults.default_ocr_model === model
          ? "ocr"
          : "chat");
  return {
    hasVision: config?.vision ?? false,
    hasReasoning: config?.reasoning ?? false,
    isOcr: role === "ocr",
    isEmbedding: role === "embedding",
    isReranker: role === "reranker",
    isChat: role === "chat",
    capabilityLabel: config
      ? role
      : "Vai trò chưa khai báo; kiểm tra Chat mặc định",
  };
}

export function formatProbeStatus(result: SingleModelTestResult): string {
  if (result.success) {
    if (result.verification_scope === "health") return "Dịch vụ phản hồi";
    if (result.verification_scope === "catalogue") return "Có trong danh mục";
    return "Đã kiểm chứng";
  }
  if (result.error_code === "MODEL_OUTPUT_BUDGET_EXHAUSTED")
    return "Chưa đủ token";
  if (result.error_code === "PROVIDER_TIMEOUT") return "Hết thời gian";
  if (result.http_status === 401 || result.http_status === 403)
    return "Lỗi xác thực";
  if (result.status === "rate_limited") return "Giới hạn tốc độ";
  if (result.status === "temporarily_overloaded") return "Tạm bận";
  if (result.status === "payment_required") return "Cần credits";
  if (result.status === "deprecated") return "Ngừng cung cấp";
  if (result.status === "unavailable") return "Không tìm thấy";
  return "Chưa kiểm chứng";
}

export function formatProbeDetail(result: SingleModelTestResult): string {
  return `${formatProbeStatus(result)}${result.http_status ? ` · HTTP ${result.http_status}` : ""}: ${result.message}`;
}
