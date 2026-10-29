import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { modelopsPaths } from "@/app/api/v1/endpoints";
import { isModelAdmin, useV1Auth } from "@/app/auth/v1";
import { modelopsKeys } from "./queries";
import type { Capability } from "./types";

export type DiagnosticCheck = {
  id: string;
  key_id?: string | null;
  kind: "discovery" | Capability;
  outcome: "ok" | "failed" | "unsupported";
  configuration_status: "current" | "stale";
  tested_at: string;
  latency_ms: number | null;
  code: string;
  detail: string;
  http_status: number | null;
  retry_after: string | null;
  requested_model: string;
  observed_model: string | null;
  observed_dimension: number | null;
  total_tokens: number | null;
  models: string[];
};
export type ProviderDiagnostics = {
  provider_id: string;
  configured_active: boolean;
  checks: DiagnosticCheck[];
};

export const diagnosticsKey = (providerId: string, sessionId: number) =>
  [...modelopsKeys.provider(providerId, sessionId), "diagnostics"] as const;

export function useDiagnostics(providerId: string) {
  const { sessionId, isAuthenticated, actor } = useV1Auth();
  return useQuery({
    queryKey: diagnosticsKey(providerId, sessionId),
    enabled: Boolean(providerId) && isAuthenticated && isModelAdmin(actor),
    queryFn: ({ signal }) =>
      v1Client.get<ProviderDiagnostics>(modelopsPaths.diagnostics(providerId), {
        signal,
      }),
  });
}

export function useRunDiagnostic(providerId: string) {
  const { sessionId } = useV1Auth();
  const queryClient = useQueryClient();
  return useMutation({
    retry: false,
    mutationFn: (kind: "discovery" | Capability) =>
      v1Client.post<DiagnosticCheck>(
        kind === "discovery"
          ? modelopsPaths.discover(providerId)
          : modelopsPaths.probe(providerId),
        kind === "discovery" ? {} : { capability: kind },
        { timeoutMs: 70_000 },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["v1", sessionId, "modelops", "connections"],
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.providersSummary(sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: diagnosticsKey(providerId, sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.events(sessionId),
      });
    },
  });
}
