import type { AssistantEditForm } from "@/components/assistants/types";
import type { AssistantLifecycleConfig } from "@/types/assistants";
import type { AssistantModelOption } from "./model-options.ts";

function uniqueProvider(options: AssistantModelOption[], model: string) {
  const matches = options.filter((m) => m.model === model);
  return matches.length === 1 ? matches[0].providerId : null;
}

export function buildAssistantPolicyUpdate(
  current: AssistantLifecycleConfig,
  value: AssistantEditForm,
  options: AssistantModelOption[],
): Pick<AssistantLifecycleConfig, "model_policy" | "knowledge_policy"> {
  return {
    model_policy: {
      ...current.model_policy,
      primary_model: value.primary_model || null,
      fallback_model: value.fallback_model || null,
      preferred_provider_id:
        value.preferred_provider_id ||
        uniqueProvider(options, value.primary_model),
      fallback_provider_id:
        value.fallback_provider_id ||
        uniqueProvider(options, value.fallback_model),
      temperature: value.temperature,
      max_tokens: value.max_tokens,
      thinking_budget: value.thinking_budget ?? 0,
    },
    knowledge_policy: {
      ...current.knowledge_policy,
      reranker_policy: {
        ...current.knowledge_policy.reranker_policy,
        enabled: value.reranker_enabled ?? true,
        provider_id:
          value.reranker_provider_id === undefined
            ? current.knowledge_policy.reranker_policy?.provider_id
            : value.reranker_provider_id || null,
        model_name:
          value.reranker_model === undefined
            ? current.knowledge_policy.reranker_policy?.model_name
            : value.reranker_model || null,
        top_k: value.reranker_top_k ?? 5,
        score_threshold: value.reranker_score_threshold ?? 0.4,
      },
    },
  };
}
