import type { AssistantEditForm } from "@/components/assistants/types";

const MODEL_POLICY_FIELDS = [
  "primary_model",
  "preferred_provider_id",
  "fallback_model",
  "fallback_provider_id",
  "temperature",
  "max_tokens",
  "thinking_budget",
] as const;

type ModelPolicyForm = Pick<
  AssistantEditForm,
  (typeof MODEL_POLICY_FIELDS)[number]
>;

export function hasPendingModelPolicy(
  draft: ModelPolicyForm,
  saved: ModelPolicyForm,
): boolean {
  return MODEL_POLICY_FIELDS.some((key) => draft[key] !== saved[key]);
}
