import { useQuery } from "@tanstack/react-query";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
    <Select value={value} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger
        aria-label="Mô hình embedding"
        className="w-full min-w-0 h-auto min-h-9 [&>span]:whitespace-normal [&>span]:text-left"
      >
        <SelectValue placeholder="Chọn Embedding từ ModelOps" />
      </SelectTrigger>
      <SelectContent className="max-w-[calc(100vw-2rem)]">
        {models.map((model) => (
          <SelectItem
            key={getEmbeddingKey(model)}
            value={getEmbeddingKey(model)}
            className="whitespace-normal break-words"
          >
            {model.model_name} · {model.provider_name}
            {model.dimension ? ` · ${model.dimension} chiều` : ""}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
