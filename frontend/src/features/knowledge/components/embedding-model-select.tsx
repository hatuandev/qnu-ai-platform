import { useQuery } from "@tanstack/react-query";
import { OptionSelect } from "@/components/admin/option-select";
import { apiClient } from "@/services/modelops-api";
import type { CollectionDataProcessingConfig } from "@/types/knowledge";
import type { ModelOption } from "@/types/modelops";

export const getEmbeddingKey = (model: ModelOption) =>
  `${model.provider_id}:${model.model_name}`;

export function useEmbeddingModels(enabled = true) {
  return useQuery({
    queryKey: ["system-model-defaults"],
    queryFn: () => apiClient.getSystemModelDefaults(),
    enabled,
    staleTime: 60000,
  });
}

export function getEmbeddingConfig(
  model: ModelOption,
): CollectionDataProcessingConfig {
  return {
    embedding_provider_id: model.provider_id,
    embedding_model: model.model_name,
    embedding_dimension: model.dimension || undefined,
  };
}

export function EmbeddingModelSelect({
  models,
  value,
  onChange,
  disabled = false,
}: {
  models: ModelOption[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <OptionSelect
      value={value}
      onValueChange={onChange}
      disabled={disabled}
      triggerProps={{ "aria-label": "Mô hình embedding" }}
      placeholder="Chọn Embedding từ ModelOps"
      options={models.map((model) => ({
        value: getEmbeddingKey(model),
        label: `${model.model_name} · ${model.provider_name}${model.dimension ? ` · ${model.dimension} chiều` : ""}`,
      }))}
    />
  );
}
