/**
 * TanStack Query hooks for the Integrations domain.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createApiKey,
  createAppClient,
  getIntegrationConfig,
  listApiKeys,
  listAppClients,
  listIntegrationLogs,
  revokeApiKey,
  rotateApiKey,
  updateApiKeyStatus,
} from "./requests";
import type {
  AppApiKeyCreate,
  AppApiKeyRevokeRequest,
  AppApiKeyRotateRequest,
  AppApiKeyStatusUpdate,
  AppClientCreate,
} from "./types";

export const integrationKeys = {
  all: ["v1", "integrations"] as const,
  config: () => [...integrationKeys.all, "config"] as const,
  apps: (workspaceId: string) =>
    [...integrationKeys.all, "apps", workspaceId] as const,
  keys: (workspaceId: string) =>
    [...integrationKeys.all, "keys", workspaceId] as const,
  logs: (workspaceId: string, limit = 50) =>
    [...integrationKeys.all, "logs", workspaceId, limit] as const,
};

export function useIntegrationConfigQuery() {
  return useQuery({
    queryKey: integrationKeys.config(),
    queryFn: ({ signal }) => getIntegrationConfig({ signal }),
    staleTime: 5 * 60 * 1000,
  });
}

export function useAppClientsQuery(workspaceId?: string | null) {
  return useQuery({
    queryKey: workspaceId
      ? integrationKeys.apps(workspaceId)
      : [...integrationKeys.all, "apps", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return listAppClients(workspaceId, { signal });
    },
    enabled: Boolean(workspaceId),
    staleTime: 30 * 1000,
  });
}

export function useCreateAppClientMutation(workspaceId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AppClientCreate) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return createAppClient(workspaceId, data);
    },
    onSuccess: () => {
      if (workspaceId) {
        void queryClient.invalidateQueries({
          queryKey: integrationKeys.apps(workspaceId),
        });
      }
    },
  });
}

export function useApiKeysQuery(workspaceId?: string | null) {
  return useQuery({
    queryKey: workspaceId
      ? integrationKeys.keys(workspaceId)
      : [...integrationKeys.all, "keys", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return listApiKeys(workspaceId, { signal });
    },
    enabled: Boolean(workspaceId),
    staleTime: 30 * 1000,
  });
}

export function useCreateApiKeyMutation(workspaceId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AppApiKeyCreate) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return createApiKey(workspaceId, data);
    },
    onSuccess: () => {
      if (workspaceId) {
        void queryClient.invalidateQueries({
          queryKey: integrationKeys.keys(workspaceId),
        });
        void queryClient.invalidateQueries({
          queryKey: integrationKeys.apps(workspaceId),
        });
      }
    },
  });
}

export function useUpdateApiKeyStatusMutation(workspaceId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      keyId,
      data,
    }: {
      keyId: string;
      data: AppApiKeyStatusUpdate;
    }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return updateApiKeyStatus(workspaceId, keyId, data);
    },
    onSuccess: () => {
      if (workspaceId) {
        void queryClient.invalidateQueries({
          queryKey: integrationKeys.keys(workspaceId),
        });
      }
    },
  });
}

export function useRotateApiKeyMutation(workspaceId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      keyId,
      data,
    }: {
      keyId: string;
      data: AppApiKeyRotateRequest;
    }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return rotateApiKey(workspaceId, keyId, data);
    },
    onSuccess: () => {
      if (workspaceId) {
        void queryClient.invalidateQueries({
          queryKey: integrationKeys.keys(workspaceId),
        });
      }
    },
  });
}

export function useRevokeApiKeyMutation(workspaceId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      keyId,
      data,
    }: {
      keyId: string;
      data?: AppApiKeyRevokeRequest;
    }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return revokeApiKey(workspaceId, keyId, data);
    },
    onSuccess: () => {
      if (workspaceId) {
        void queryClient.invalidateQueries({
          queryKey: integrationKeys.keys(workspaceId),
        });
      }
    },
  });
}

export function useIntegrationLogsQuery(
  workspaceId?: string | null,
  limit = 50,
) {
  return useQuery({
    queryKey: workspaceId
      ? integrationKeys.logs(workspaceId, limit)
      : [...integrationKeys.all, "logs", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return listIntegrationLogs(workspaceId, limit, { signal });
    },
    enabled: Boolean(workspaceId),
    staleTime: 30 * 1000,
  });
}
