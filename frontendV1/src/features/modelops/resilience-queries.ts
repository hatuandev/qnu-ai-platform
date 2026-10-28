import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { modelopsPaths } from "@/app/api/v1/endpoints";
import { isModelAdmin, useV1Auth } from "@/app/auth/v1";
import { modelopsKeys } from "./queries";
import type { Capability, ProviderType } from "./types";

export type Transport = {
  provider_type: ProviderType;
  label: string;
  protocols: Partial<Record<Capability, string>>;
  discovery: boolean;
  structured_output: string;
  streaming: boolean;
  responses_api: boolean;
  tools: boolean;
  image_input: string[];
  multi_item_input: string[];
  metadata_basis: string;
};
export const TASKS = {
  chat: "Chat chung",
  answer: "Hỏi đáp",
  followup: "Câu hỏi nối tiếp",
  compiler: "Compiler",
  compiler_review: "Review Compiler",
  ocr_review: "Sửa chính tả",
  ocr: "OCR",
  rerank: "Rerank",
} as const;
export type Task = keyof typeof TASKS;
export const taskCapability = (task: Task): Capability =>
  task === "ocr" || task === "rerank" ? task : "chat";
export type ResiliencePolicy = {
  key_pool_enabled: boolean;
  retry_owner: "qnu" | "gateway";
  max_key_attempts: number;
  auth_cooldown_seconds: number;
  rate_cooldown_seconds: number;
  fallbacks: Partial<Record<Task, string[]>>;
};
export type PolicyResponse = {
  provider_id: string;
  status: "default" | "configured" | "stale";
  policy: ResiliencePolicy;
  routing_phase: "before_dispatch";
  explicit_provider_is_pinned: boolean;
  embedding_model_fallback: boolean;
};
export type ExecutionObservation = {
  id: string;
  created_at: string;
  call_id: string;
  usage_id: string | null;
  capability: string;
  model_name: string;
  key_id: string | null;
  code: string;
  upstream_status: number | null;
  attempt: number;
  latency_ms: number | null;
  total_tokens: number | null;
};

export function useExecutions(providerId: string) {
  const { sessionId, isAuthenticated, actor } = useV1Auth();
  return useQuery({
    queryKey: [...modelopsKeys.provider(providerId, sessionId), "executions"],
    enabled: Boolean(providerId) && isAuthenticated && isModelAdmin(actor),
    queryFn: ({ signal }) =>
      v1Client.get<ExecutionObservation[]>(
        modelopsPaths.executions(providerId),
        { signal },
      ),
  });
}
const policyPath = modelopsPaths.resilience;

export function useTransportRegistry() {
  const { sessionId, isAuthenticated, actor } = useV1Auth();
  return useQuery({
    queryKey: [...modelopsKeys.all(sessionId), "registry"],
    enabled: isAuthenticated && isModelAdmin(actor),
    queryFn: ({ signal }) =>
      v1Client.get<Transport[]>(modelopsPaths.registry, { signal }),
  });
}

export function useResilience(providerId: string) {
  const { sessionId, isAuthenticated, actor } = useV1Auth();
  return useQuery({
    queryKey: [...modelopsKeys.provider(providerId, sessionId), "resilience"],
    enabled: Boolean(providerId) && isAuthenticated && isModelAdmin(actor),
    queryFn: ({ signal }) =>
      v1Client.get<PolicyResponse>(policyPath(providerId), { signal }),
  });
}

export function useSaveResilience(providerId: string) {
  const { sessionId } = useV1Auth();
  const client = useQueryClient();
  return useMutation({
    retry: false,
    mutationFn: (policy: ResiliencePolicy) =>
      v1Client.put<PolicyResponse>(policyPath(providerId), policy),
    onSuccess: () => {
      void client.invalidateQueries({
        queryKey: modelopsKeys.provider(providerId, sessionId),
      });
      void client.invalidateQueries({
        queryKey: modelopsKeys.events(sessionId),
      });
    },
  });
}
