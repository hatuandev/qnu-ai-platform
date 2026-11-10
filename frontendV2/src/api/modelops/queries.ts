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
  getConnection,
  listConnectionKeys,
  listConnectionModels,
  listConnections,
  probeModel,
  testConnection,
  updateConnection,
} from "./requests";
import type {
  Capability,
  ConnectionInput,
  ConnectionModelCreateInput,
  ConnectionTestRequest,
  ConnectionUpdateInput,
  KeyCreateRequest,
} from "./types";

export const modelopsKeys = {
  all: ["v1", "modelops"] as const,
  connections: () => [...modelopsKeys.all, "connections"] as const,
  connection: (id: string) => [...modelopsKeys.connections(), id] as const,
  connectionModels: (id: string) =>
    [...modelopsKeys.connection(id), "models"] as const,
  connectionKeys: (id: string) =>
    [...modelopsKeys.connection(id), "keys"] as const,
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
