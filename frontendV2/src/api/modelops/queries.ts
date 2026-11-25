/**
 * TanStack Query hooks for ModelOps & AI Provider domain.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createConnection,
  createConnectionKey,
  createConnectionModel,
  deleteConnection,
  deleteConnectionKey,
  deleteConnectionModel,
  discoverProvider,
  getCatalog,
  getConnection,
  getModelDefaults,
  getProviderReasoning,
  listConnectionKeys,
  listConnectionModels,
  listConnections,
  listProviders,
  probeModel,
  syncConnectionCapacity,
  testConnection,
  updateConnection,
  updateModelDefaults,
  updateProviderCapacity,
  updateProviderReasoning,
} from "./requests";
import type {
  Capability,
  ConnectionInput,
  ConnectionModelCreateInput,
  ConnectionTestRequest,
  ConnectionUpdateInput,
  DefaultsUpdateRequest,
  KeyCreateRequest,
  ReasoningPolicy,
  TokenLimits,
} from "./types";

export const modelopsKeys = {
  all: ["v1", "modelops"] as const,
  connections: () => [...modelopsKeys.all, "connections"] as const,
  connection: (id: string) => [...modelopsKeys.connections(), id] as const,
  connectionModels: (id: string) =>
    [...modelopsKeys.connection(id), "models"] as const,
  connectionKeys: (id: string) =>
    [...modelopsKeys.connection(id), "keys"] as const,
  defaults: () => [...modelopsKeys.all, "defaults"] as const,
  providers: () => [...modelopsKeys.all, "providers"] as const,
  reasoning: (providerId: string) =>
    [...modelopsKeys.all, "reasoning", providerId] as const,
  documentProcessing: () =>
    [...modelopsKeys.all, "document-processing"] as const,
  catalog: (workspaceId?: string | null) =>
    [...modelopsKeys.all, "catalog", workspaceId ?? "global"] as const,
};

export function useConnectionsQuery(enabled = true) {
  return useQuery({
    queryKey: modelopsKeys.connections(),
    queryFn: ({ signal }) => listConnections({ signal }),
    enabled,
    staleTime: 30 * 1000,
  });
}

export function useConnectionQuery(connectionId: string, enabled = true) {
  return useQuery({
    queryKey: modelopsKeys.connection(connectionId),
    queryFn: ({ signal }) => getConnection(connectionId, { signal }),
    enabled: Boolean(connectionId) && enabled,
  });
}

export function useConnectionModelsQuery(connectionId: string, enabled = true) {
  return useQuery({
    queryKey: modelopsKeys.connectionModels(connectionId),
    queryFn: ({ signal }) => listConnectionModels(connectionId, { signal }),
    enabled: Boolean(connectionId) && enabled,
    staleTime: 30 * 1000,
  });
}

export function useConnectionKeysQuery(connectionId: string, enabled = true) {
  return useQuery({
    queryKey: modelopsKeys.connectionKeys(connectionId),
    queryFn: ({ signal }) => listConnectionKeys(connectionId, { signal }),
    enabled: Boolean(connectionId) && enabled,
    staleTime: 30 * 1000,
  });
}

export function useCreateConnectionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ConnectionInput) => createConnection(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connections(),
      });
      void queryClient.invalidateQueries({
        queryKey: [...modelopsKeys.all, "catalog"],
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.providers(),
      });
    },
  });
}

export function useUpdateConnectionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      connectionId,
      input,
    }: {
      connectionId: string;
      input: ConnectionUpdateInput;
    }) => updateConnection(connectionId, input),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connection(variables.connectionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connections(),
      });
      void queryClient.invalidateQueries({
        queryKey: [...modelopsKeys.all, "catalog"],
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.providers(),
      });
    },
  });
}

export function useDeleteConnectionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (connectionId: string) => deleteConnection(connectionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connections(),
      });
      void queryClient.invalidateQueries({
        queryKey: [...modelopsKeys.all, "catalog"],
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.providers(),
      });
    },
  });
}

export function useTestConnectionMutation(connectionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    retry: false,
    mutationFn: (req: ConnectionTestRequest) =>
      testConnection(connectionId, req),
    onSettled: (_data, _error, variables) => {
      // Invalidate if testing with saved key to refresh connection's last_probe_status
      if (!variables.api_key) {
        void queryClient.invalidateQueries({
          queryKey: modelopsKeys.connections(),
        });
        void queryClient.invalidateQueries({
          queryKey: modelopsKeys.connection(connectionId),
        });
      }
    },
  });
}

export function useAddModelMutation(connectionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ConnectionModelCreateInput) =>
      createConnectionModel(connectionId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connectionModels(connectionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connections(),
      });
      void queryClient.invalidateQueries({
        queryKey: [...modelopsKeys.all, "catalog"],
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.providers(),
      });
    },
  });
}

export function useDeleteModelMutation(connectionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (modelId: string) =>
      deleteConnectionModel(connectionId, modelId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connectionModels(connectionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connections(),
      });
      void queryClient.invalidateQueries({
        queryKey: [...modelopsKeys.all, "catalog"],
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.providers(),
      });
    },
  });
}

export function useSyncModelCapacityMutation(connectionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (modelName: string) => {
      const check = await discoverProvider(connectionId);
      if (check.outcome !== "ok") {
        throw new Error(check.detail || "Không đọc được metadata máy chủ.");
      }
      const rows = await syncConnectionCapacity(connectionId, {
        check_id: check.id,
        model_names: [modelName],
      });
      return rows[0];
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connectionModels(connectionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connections(),
      });
    },
  });
}

export function useUpdateModelCapacityMutation(connectionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      providerId,
      tokenLimits,
    }: {
      providerId: string;
      tokenLimits: TokenLimits;
    }) => updateProviderCapacity(providerId, tokenLimits),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connectionModels(connectionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.defaults(),
      });
    },
  });
}

export function useAddKeyMutation(connectionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: KeyCreateRequest) =>
      createConnectionKey(connectionId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connectionKeys(connectionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connections(),
      });
    },
  });
}

export function useDeleteKeyMutation(connectionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) => deleteConnectionKey(connectionId, keyId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connectionKeys(connectionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connections(),
      });
    },
  });
}

export function useProbeModelMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    retry: false,
    mutationFn: ({
      providerId,
      capability,
    }: {
      providerId: string;
      capability: Capability;
    }) => probeModel(providerId, capability),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.connections(),
      });
    },
  });
}

export function useProvidersQuery(enabled = true) {
  return useQuery({
    queryKey: modelopsKeys.providers(),
    queryFn: ({ signal }) => listProviders({ signal }),
    enabled,
    staleTime: 30 * 1000,
  });
}

export function useModelDefaultsQuery(enabled = true) {
  return useQuery({
    queryKey: modelopsKeys.defaults(),
    queryFn: ({ signal }) => getModelDefaults({ signal }),
    enabled,
    staleTime: 30 * 1000,
  });
}

export function useUpdateModelDefaultsMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: DefaultsUpdateRequest) => updateModelDefaults(body),
    onSuccess: (defaults) => {
      queryClient.setQueryData(modelopsKeys.defaults(), defaults);
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.defaults(),
      });
      void queryClient.invalidateQueries({
        queryKey: [...modelopsKeys.all, "catalog"],
      });
    },
  });
}

export function useCatalogQuery(workspaceId?: string | null, enabled = true) {
  return useQuery({
    queryKey: modelopsKeys.catalog(workspaceId),
    queryFn: ({ signal }) => getCatalog({ workspaceId }, { signal }),
    enabled,
    staleTime: 30 * 1000,
  });
}

export function useProviderReasoningQuery(providerId: string) {
  return useQuery({
    queryKey: modelopsKeys.reasoning(providerId),
    queryFn: ({ signal }) => getProviderReasoning(providerId, { signal }),
    staleTime: 30 * 1000,
  });
}

export function useSetProviderReasoningMutation(
  providerId: string,
  connectionId?: string,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (policy: ReasoningPolicy) =>
      updateProviderReasoning(providerId, policy),
    onSuccess: (reasoning) => {
      queryClient.setQueryData(modelopsKeys.reasoning(providerId), reasoning);
      if (connectionId) {
        void queryClient.invalidateQueries({
          queryKey: modelopsKeys.connectionModels(connectionId),
        });
      }
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.providers(),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.documentProcessing(),
      });
    },
  });
}
