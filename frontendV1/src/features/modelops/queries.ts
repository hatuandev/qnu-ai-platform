import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import {
  createAppApiKey,
  createProvider,
  createProviderKey,
  getCatalog,
  getDefaults,
  getIntegrationConfig,
  getProvider,
  listAppApiKeys,
  listAppClients,
  listAppRequestLogs,
  listKeyEvents,
  listModelOpsEvents,
  listProviderKeys,
  listProviders,
  listProvidersSummary,
  putDefaults,
  revokeAppApiKey,
  revokeProviderKey,
  rotateAppApiKey,
  rotateProviderKey,
  updateAppApiKeyStatus,
  updateProvider,
} from "@/features/modelops/requests";
import type {
  AppApiKeyCreateInput,
  AppApiKeyRevokeInput,
  AppApiKeyRotateInput,
  AppApiKeySecretResponse,
  AppApiKeyStatusUpdateInput,
  DefaultsUpdateInput,
  KeyCreateInput,
  KeyRevokeInput,
  KeyRotateInput,
  ProviderCreateInput,
  ProviderUpdateInput,
} from "@/features/modelops/types";

const ROOT = ["v1", "modelops"] as const;

export const modelopsKeys = {
  all: (sessionId?: number) =>
    sessionId !== undefined ? (["v1", sessionId, "modelops"] as const) : ROOT,
  providers: (sessionId?: number) =>
    sessionId !== undefined
      ? (["v1", sessionId, "modelops", "providers"] as const)
      : ([...ROOT, "providers"] as const),
  provider: (providerId: string, sessionId?: number) =>
    sessionId !== undefined
      ? (["v1", sessionId, "modelops", "providers", providerId] as const)
      : ([...ROOT, "providers", providerId] as const),
  keys: (providerId: string, sessionId?: number) =>
    sessionId !== undefined
      ? (["v1", sessionId, "modelops", "keys", providerId] as const)
      : ([...ROOT, "keys", providerId] as const),
  keyEvents: (providerId: string, sessionId?: number) =>
    sessionId !== undefined
      ? (["v1", sessionId, "modelops", "key-events", providerId] as const)
      : ([...ROOT, "key-events", providerId] as const),
  defaults: (sessionId?: number) =>
    sessionId !== undefined
      ? (["v1", sessionId, "modelops", "defaults"] as const)
      : ([...ROOT, "defaults"] as const),
  events: (sessionId?: number) =>
    sessionId !== undefined
      ? (["v1", sessionId, "modelops", "events"] as const)
      : ([...ROOT, "events"] as const),
  catalog: (workspaceId: string, sessionId?: number) =>
    sessionId !== undefined
      ? (["v1", sessionId, "modelops", "catalog", workspaceId] as const)
      : ([...ROOT, "catalog", workspaceId] as const),
  providersSummary: (sessionId?: number) =>
    sessionId !== undefined
      ? (["v1", sessionId, "modelops", "providers-summary"] as const)
      : ([...ROOT, "providers-summary"] as const),
  integrationConfig: (sessionId?: number) =>
    sessionId !== undefined
      ? (["v1", sessionId, "modelops", "integration", "config"] as const)
      : ([...ROOT, "integration", "config"] as const),
  integrationApps: (workspaceId: string, sessionId?: number) =>
    sessionId !== undefined
      ? ([
          "v1",
          sessionId,
          "modelops",
          "integration",
          "apps",
          workspaceId,
        ] as const)
      : ([...ROOT, "integration", "apps", workspaceId] as const),
  integrationKeys: (workspaceId: string, sessionId?: number) =>
    sessionId !== undefined
      ? ([
          "v1",
          sessionId,
          "modelops",
          "integration",
          "keys",
          workspaceId,
        ] as const)
      : ([...ROOT, "integration", "keys", workspaceId] as const),
  integrationLogs: (workspaceId: string, limit?: number, sessionId?: number) =>
    sessionId !== undefined
      ? ([
          "v1",
          sessionId,
          "modelops",
          "integration",
          "logs",
          workspaceId,
          limit,
        ] as const)
      : ([...ROOT, "integration", "logs", workspaceId, limit] as const),
};

export function useProvidersQuery(options?: { enabled?: boolean }) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: modelopsKeys.providers(sessionId),
    queryFn: ({ signal }) => listProviders(v1Client, { signal }),
    enabled: options?.enabled ?? true,
  });
}

export function useProviderQuery(providerId: string) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: modelopsKeys.provider(providerId, sessionId),
    queryFn: ({ signal }) => getProvider(v1Client, providerId, { signal }),
    enabled: Boolean(providerId),
  });
}

export function useCreateProvider() {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (input: ProviderCreateInput) => createProvider(v1Client, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.providersSummary(sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.providers(sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.events(sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.defaults(sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: ["v1", sessionId, "modelops", "catalog"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["v1", "modelops", "catalog"],
      });
    },
  });
}

export function useUpdateProvider(providerId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (patch: ProviderUpdateInput) =>
      updateProvider(v1Client, providerId, patch),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.providersSummary(sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.providers(sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.provider(providerId, sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.events(sessionId),
      });
      // A changed endpoint/model invalidates capacity, which defaults and catalog rely on.
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.defaults(sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: ["v1", sessionId, "modelops", "catalog"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["v1", "modelops", "catalog"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["v1", sessionId, "workspaces", "allowlist"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["v1", "workspaces", "allowlist"],
      });
    },
  });
}

export function useProviderKeysQuery(providerId: string) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: modelopsKeys.keys(providerId, sessionId),
    queryFn: ({ signal }) => listProviderKeys(v1Client, providerId, { signal }),
    enabled: Boolean(providerId),
  });
}

export function useKeyEventsQuery(providerId: string) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: modelopsKeys.keyEvents(providerId, sessionId),
    queryFn: ({ signal }) =>
      listKeyEvents(v1Client, providerId, 50, { signal }),
    enabled: Boolean(providerId),
  });
}

function invalidateKeys(
  queryClient: ReturnType<typeof useQueryClient>,
  providerId: string,
  sessionId?: number,
) {
  void queryClient.invalidateQueries({
    queryKey: modelopsKeys.providersSummary(sessionId),
  });
  void queryClient.invalidateQueries({
    queryKey: [...modelopsKeys.provider(providerId, sessionId), "diagnostics"],
  });
  void queryClient.invalidateQueries({
    queryKey: modelopsKeys.keys(providerId, sessionId),
  });
  void queryClient.invalidateQueries({
    queryKey: modelopsKeys.keyEvents(providerId, sessionId),
  });
  void queryClient.invalidateQueries({
    queryKey: modelopsKeys.events(sessionId),
  });
}

export function useCreateProviderKey(providerId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: async (input: KeyCreateInput) => {
      const secret = input.secret;
      // Strip immediately so mutation.state.variables never retains secret
      delete (input as Partial<KeyCreateInput>).secret;
      return createProviderKey(v1Client, providerId, {
        name: input.name,
        priority: input.priority,
        secret,
      });
    },
    onSuccess: () => invalidateKeys(queryClient, providerId, sessionId),
    onSettled: (_data, _error, variables) => {
      if (variables && typeof variables === "object" && "secret" in variables) {
        delete (variables as Record<string, unknown>).secret;
      }
    },
  });
}

export function useRotateProviderKey(providerId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: async (args: { keyId: string; input: KeyRotateInput }) => {
      const secret = args.input.secret;
      // Strip immediately so mutation.state.variables never retains secret
      delete (args.input as Partial<KeyRotateInput>).secret;
      return rotateProviderKey(v1Client, providerId, args.keyId, {
        name: args.input.name,
        priority: args.input.priority,
        reason: args.input.reason,
        secret,
      });
    },
    onSuccess: () => invalidateKeys(queryClient, providerId, sessionId),
    onSettled: (_data, _error, variables) => {
      if (
        variables?.input &&
        typeof variables.input === "object" &&
        "secret" in variables.input
      ) {
        delete (variables.input as Record<string, unknown>).secret;
      }
    },
  });
}

export function useRevokeProviderKey(providerId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (args: { keyId: string; input: KeyRevokeInput }) =>
      revokeProviderKey(v1Client, providerId, args.keyId, args.input),
    onSuccess: () => invalidateKeys(queryClient, providerId, sessionId),
  });
}

export function useDefaultsQuery(options?: { enabled?: boolean }) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: modelopsKeys.defaults(sessionId),
    queryFn: ({ signal }) => getDefaults(v1Client, { signal }),
    enabled: options?.enabled ?? true,
  });
}

export function usePutDefaults() {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (input: DefaultsUpdateInput) => putDefaults(v1Client, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.defaults(sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.events(sessionId),
      });
    },
  });
}

export function useModelOpsEventsQuery(options?: { enabled?: boolean }) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: modelopsKeys.events(sessionId),
    queryFn: ({ signal }) => listModelOpsEvents(v1Client, 50, { signal }),
    enabled: options?.enabled ?? true,
  });
}

export function useCatalogQuery(
  workspaceId: string,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: modelopsKeys.catalog(workspaceId, sessionId),
    queryFn: ({ signal }) => getCatalog(v1Client, workspaceId, { signal }),
    enabled: Boolean(workspaceId) && (options?.enabled ?? true),
  });
}

export function useProvidersSummaryQuery(options?: { enabled?: boolean }) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: modelopsKeys.providersSummary(sessionId),
    queryFn: ({ signal }) => listProvidersSummary(v1Client, { signal }),
    enabled: options?.enabled ?? true,
  });
}

export function useIntegrationConfigQuery(options?: { enabled?: boolean }) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: modelopsKeys.integrationConfig(sessionId),
    queryFn: ({ signal }) => getIntegrationConfig(v1Client, { signal }),
    enabled: options?.enabled ?? true,
  });
}

export function useIntegrationAppsQuery(
  workspaceId: string,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: modelopsKeys.integrationApps(workspaceId, sessionId),
    queryFn: ({ signal }) => listAppClients(v1Client, workspaceId, { signal }),
    enabled: Boolean(workspaceId) && (options?.enabled ?? true),
  });
}

export function useIntegrationKeysQuery(
  workspaceId: string,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: modelopsKeys.integrationKeys(workspaceId, sessionId),
    queryFn: ({ signal }) => listAppApiKeys(v1Client, workspaceId, { signal }),
    enabled: Boolean(workspaceId) && (options?.enabled ?? true),
  });
}

export function useCreateAppApiKeyMutation(
  workspaceId: string,
  onSecret: (data: AppApiKeySecretResponse) => void,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    gcTime: 0,
    mutationFn: async (input: AppApiKeyCreateInput) => {
      const response = await createAppApiKey(v1Client, workspaceId, input);
      onSecret(response); // Only the one-time modal owns plaintext; mutation result is void.
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.integrationKeys(workspaceId, sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.integrationApps(workspaceId, sessionId),
      });
    },
  });
}

export function useUpdateAppApiKeyStatusMutation(workspaceId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: ({
      keyId,
      input,
    }: {
      keyId: string;
      input: AppApiKeyStatusUpdateInput;
    }) => updateAppApiKeyStatus(v1Client, workspaceId, keyId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.integrationKeys(workspaceId, sessionId),
      });
    },
  });
}

export function useRotateAppApiKeyMutation(
  workspaceId: string,
  onSecret: (data: AppApiKeySecretResponse) => void,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    gcTime: 0,
    mutationFn: async ({
      keyId,
      input,
    }: {
      keyId: string;
      input: AppApiKeyRotateInput;
    }) => {
      const response = await rotateAppApiKey(
        v1Client,
        workspaceId,
        keyId,
        input,
      );
      onSecret(response);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.integrationKeys(workspaceId, sessionId),
      });
    },
  });
}

export function useRevokeAppApiKeyMutation(workspaceId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: ({
      keyId,
      input,
    }: {
      keyId: string;
      input: AppApiKeyRevokeInput;
    }) => revokeAppApiKey(v1Client, workspaceId, keyId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: modelopsKeys.integrationKeys(workspaceId, sessionId),
      });
    },
  });
}

export function useIntegrationLogsQuery(
  workspaceId: string,
  limit = 50,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: modelopsKeys.integrationLogs(workspaceId, limit, sessionId),
    queryFn: ({ signal }) =>
      listAppRequestLogs(v1Client, workspaceId, limit, { signal }),
    enabled: Boolean(workspaceId) && (options?.enabled ?? true),
  });
}
