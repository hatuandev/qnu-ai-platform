import type { KnowledgeVectorGenerationResponse } from "@/types/knowledge";
import type { ModelProvider } from "@/types/modelops";

export function getGenerationLabel(
  generation: KnowledgeVectorGenerationResponse,
  providers: ModelProvider[] = [],
) {
  const provider = providers.find((item) => item.id === generation.provider_id);
  const state = generation.status === "active" ? "Đang dùng" : "Chưa dùng";
  return `${generation.embedding_model} · ${provider?.name || generation.provider_id} · ${generation.embedding_dimension}d · Bản ${generation.generation_epoch} (${state})`;
}

export function getProviderOrigin(provider?: ModelProvider) {
  if (!provider?.api_base_url) return "Chưa có địa chỉ máy chủ";
  try {
    const url = new URL(provider.api_base_url);
    return ["http:", "https:"].includes(url.protocol)
      ? url.origin
      : "Địa chỉ máy chủ không hợp lệ";
  } catch {
    return "Địa chỉ máy chủ không hợp lệ";
  }
}
