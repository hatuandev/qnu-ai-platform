export type PreparationMode = "source" | "ai";

export type PreparationStatus =
  | "queued"
  | "waiting_ocr"
  | "compiling"
  | "ready"
  | "failed"
  | "uncertain"
  | "cancelled";

export interface PreparationIntent {
  id: string;
  workspace_id: string;
  collection_id: string;
  source_id: string;
  revision_id: string;
  revision_no: number;
  revision_sha256: string;
  mode: PreparationMode;
  status: PreparationStatus;
  topic: string;
  text_version: number;
  text_version_id: string | null;
  text_canonical_sha256: string | null;
  provider_id: string | null;
  max_output_tokens: number | null;
  ocr_run_id: string | null;
  compilation_run_id: string | null;
  error_code: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface PreparationRequestInput {
  mode: PreparationMode;
  revision_id: string;
  ocr_run_id?: string | null;
  text_version?: number;
  topic?: string | null;
  provider_id?: string | null;
  max_output_tokens?: number | null;
}

export interface PreparationCreatedResponse {
  intent: PreparationIntent;
  created: boolean;
  dispatched: boolean;
}
