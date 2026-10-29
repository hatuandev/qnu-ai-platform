import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import type { Capability, Provider, ProviderKey } from "../types";

export type ConnectionFamily =
  | "openai"
  | "gemini"
  | "qnu"
  | "custom"
  | "anthropic";

export type Connection = {
  id: string;
  name: string;
  family: ConnectionFamily;
  base_url: string;
  timeout_seconds: number;
  is_active: boolean;
  is_connection: true;
  prefix?: string | null;
  api_type?: string | null;
  model_count: number;
  active_model_count: number;
  active_keys_count: number;
  total_keys_count: number;
  last_probe_status:
    | "success"
    | "failed"
    | "unsupported"
    | "untested"
    | "stale";
  last_probe_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ConnectionInput = {
  name: string;
  family: ConnectionFamily;
  base_url: string;
  timeout_seconds: number;
  prefix?: string | null;
  api_type?: string | null;
  is_active?: boolean;
};

export type ConnectionTestResult = {
  ok: boolean;
  key_id?: string | null;
  check_id?: string | null;
  code?: string;
  http_status?: number | null;
  tested_at?: string | null;
  latency_ms?: number | null;
  detail: string;
  models?: string[];
};

export const FAMILIES: Record<ConnectionFamily, string> = {
  openai: "OpenAI Compatible",
  anthropic: "Anthropic Compatible",
  gemini: "Google Gemini",
  qnu: "Server AI QNU",
  custom: "Custom / Khác",
};

export const PRESET_URLS: Record<ConnectionFamily, string> = {
  openai: "https://api.openai.com/v1",
  anthropic: "https://api.anthropic.com/v1",
  gemini: "https://generativelanguage.googleapis.com/v1beta/openai",
  qnu: "http://100.105.13.53:8000/v1",
  custom: "",
};

export const PRESET_PREFIXES: Record<ConnectionFamily, string> = {
  openai: "openai",
  anthropic: "anthropic",
  gemini: "google",
  qnu: "qnu",
  custom: "",
};

const path = "/modelops/connections";

export function useConnections() {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: ["v1", sessionId, "modelops", "connections", "list"],
    queryFn: ({ signal }) => v1Client.get<Connection[]>(path, { signal }),
  });
}

export function useConnection(id: string) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: ["v1", sessionId, "modelops", "connections", id],
    queryFn: ({ signal }) =>
      v1Client.get<Connection>(`${path}/${id}`, { signal }),
    enabled: Boolean(id),
  });
}

export function useConnectionModels(id: string) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: ["v1", sessionId, "modelops", "connections", id, "models"],
    queryFn: ({ signal }) =>
      v1Client.get<Provider[]>(`${path}/${id}/models`, { signal }),
    enabled: Boolean(id),
  });
}

export function useConnectionKeys(connectionId: string) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: [
      "v1",
      sessionId,
      "modelops",
      "connections",
      connectionId,
      "keys",
    ],
    queryFn: ({ signal }) =>
      v1Client.get<ProviderKey[]>(`/modelops/providers/${connectionId}/keys`, {
        signal,
      }),
    enabled: Boolean(connectionId),
  });
}

export function useSaveConnection(id?: string) {
  const cache = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (input: ConnectionInput) =>
      id
        ? v1Client.patch<Connection>(`${path}/${id}`, input)
        : v1Client.post<Connection>(path, input),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["v1", sessionId, "modelops"] });
    },
  });
}

export function useDeleteConnection() {
  const cache = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (connectionId: string) =>
      v1Client.delete(`${path}/${connectionId}`),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["v1", sessionId, "modelops"] });
    },
  });
}

export function useAddConnectionModel(connectionId: string) {
  const cache = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (input: {
      model_name: string;
      capabilities: Capability[];
      embedding_dimension?: number;
    }) => v1Client.post<Provider>(`${path}/${connectionId}/models`, input),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["v1", sessionId, "modelops"] });
    },
  });
}

export function useDeleteConnectionModel(connectionId: string) {
  const cache = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (modelId: string) =>
      v1Client.delete(`${path}/${connectionId}/models/${modelId}`),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["v1", sessionId, "modelops"] });
    },
  });
}

export function useAddConnectionKey(connectionId: string) {
  const cache = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (input: {
      name: string;
      secret: string;
      priority: number;
    }) =>
      v1Client.post<ProviderKey>(
        `/modelops/providers/${connectionId}/keys`,
        {
          name: input.name,
          secret: input.secret,
          priority: input.priority,
        },
      ),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["v1", sessionId, "modelops"] });
    },
  });
}

export function useDeleteConnectionKey(connectionId: string) {
  const cache = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (keyId: string) =>
      v1Client.delete(`${path}/${connectionId}/keys/${keyId}`),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["v1", sessionId, "modelops"] });
    },
  });
}

export function useTestConnection(connectionId: string) {
  const cache = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    retry: false,
    mutationFn: (input: {
      key_id?: string;
      api_key?: string;
      model_name?: string;
    }) =>
      v1Client.post<ConnectionTestResult>(
        `${path}/${connectionId}/test`,
        input,
        { timeoutMs: 310_000 },
      ),
    onSettled: (_result, _error, input) => {
      if (!input.api_key)
        void cache.invalidateQueries({
          queryKey: ["v1", sessionId, "modelops"],
        });
    },
  });
}
