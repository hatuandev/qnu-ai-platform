import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import type { Capability, Provider } from "../types";

export type ConnectionFamily = "openai" | "gemini" | "qnu" | "custom";
export type Connection = {
  id: string;
  name: string;
  family: ConnectionFamily;
  base_url: string;
  timeout_seconds: number;
  is_active: boolean;
  is_connection: true;
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
  is_active?: boolean;
};
export const FAMILIES: Record<ConnectionFamily, string> = {
  openai: "OpenAI / ChatGPT",
  gemini: "Google Gemini",
  qnu: "Server AI QNU",
  custom: "Nhà cung cấp khác",
};
export const PRESET_URLS: Record<ConnectionFamily, string> = {
  openai: "https://api.openai.com/v1",
  gemini: "https://generativelanguage.googleapis.com/v1beta/openai",
  qnu: "http://100.105.13.53:8000/v1",
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
export function useAddConnectionModel(id: string) {
  const cache = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (input: {
      model_name: string;
      capabilities: Capability[];
      embedding_dimension?: number;
    }) => v1Client.post<Provider>(`${path}/${id}/models`, input),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["v1", sessionId, "modelops"] });
    },
  });
}
