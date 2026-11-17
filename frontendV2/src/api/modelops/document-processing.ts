import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { v1Client } from "../v1-client";
import { modelopsKeys } from "./queries";

export type DocumentMode = "priority" | "parallel";

export type DocumentThinkingLevel = "server" | "low" | "off";

export type DocumentThinking = {
  configured: DocumentThinkingLevel;
  effective: DocumentThinkingLevel;
  verified: boolean;
  status: string;
  reason?: string | null;
};

export type DocumentModelEntry = {
  provider_id: string;
  name: string;
  model_name: string;
  concurrency: number;
  effective_concurrency: number;
  available: boolean;
  thinking: DocumentThinking;
};

export type DocumentProcessingSettings = {
  mode: DocumentMode;
  models: DocumentModelEntry[];
  max_concurrency: number;
  shared_concurrency: number;
  provider_id: string | null;
  concurrency: Record<string, number>;
};

export type DocumentModelInput = {
  provider_id: string;
  concurrency: number;
};

export type DocumentProcessingUpdate = {
  mode?: DocumentMode;
  models?: DocumentModelInput[];
};

const path = "/modelops/document-processing";
const key = modelopsKeys.documentProcessing();

export function useDocumentProcessing() {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: key,
    queryFn: ({ signal }) =>
      v1Client.get<DocumentProcessingSettings>(path, { signal }),
  });
  const update = useMutation({
    mutationFn: (settings: DocumentProcessingUpdate) =>
      v1Client.patch<DocumentProcessingSettings>(path, settings),
    onSuccess: (settings) => client.setQueryData(key, settings),
  });
  return { query, update };
}

export const THINKING_LEVEL_LABEL: Record<DocumentThinkingLevel, string> = {
  server: "Theo máy chủ",
  low: "Thấp",
  off: "Tắt",
};
