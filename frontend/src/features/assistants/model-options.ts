import type { ModelProvider } from "@/types/modelops";

export interface AssistantModelOption {
  value: string;
  label: string;
  model: string;
  providerId: string;
  providerName: string;
}

export function buildAssistantModelOptions(
  providers: ModelProvider[],
  role: "chat" | "reranker",
  configured: { model?: string; providerId?: string }[] = [],
): AssistantModelOption[] {
  const options = providers
    .filter(
      (p) => p.is_active && (role === "reranker" || p.supports_chat !== false),
    )
    .flatMap((p) =>
      p.models
        .filter((m) => {
          const capability = p.model_capabilities?.[m];
          if (capability) return capability.probe_role === role;
          const kind = p.model_specs?.[m]?.type ?? "text";
          return role === "reranker"
            ? kind === "reranker"
            : [
                "text",
                "chat",
                "llm",
                "vision",
                "multimodal",
                "reasoning",
                "vision_ocr",
              ].includes(kind);
        })
        .map((model) => ({
          value: JSON.stringify([p.id, model]),
          label: `${model} (${p.name})`,
          providerId: p.id,
          providerName: p.name,
          model,
        })),
    );
  for (const saved of configured) {
    if (!saved.model) continue;
    const matches = options.filter(
      (m) =>
        m.model === saved.model &&
        (!saved.providerId || m.providerId === saved.providerId),
    );
    if (matches.length === 1) continue;
    const value = JSON.stringify([saved.providerId ?? "", saved.model]);
    if (options.some((m) => m.value === value)) continue;
    options.unshift({
      value,
      model: saved.model,
      providerId: saved.providerId ?? "",
      providerName: "Cấu hình đã lưu",
      label: `${saved.model} (Cấu hình đã lưu — cần kiểm tra)`,
    });
  }
  return options;
}

export function selectedModelValue(
  options: AssistantModelOption[],
  model?: string,
  providerId?: string,
): string {
  const matches = options.filter(
    (m) => m.model === model && (!providerId || m.providerId === providerId),
  );
  return matches.length === 1
    ? matches[0].value
    : (matches.find((m) => !m.providerId)?.value ?? "__none__");
}
