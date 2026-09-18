import type {
  AssistantCloneRequest,
  AssistantItem,
  AssistantLifecycleConfig,
  AssistantPublishResponse,
  AssistantReadinessResponse,
  AssistantRollbackResponse,
  AssistantVersionItem,
} from "@/types/assistants";

const ASSISTANTS_URL = "/platform/v1alpha1/assistants";

export interface AssistantInput {
  code: string;
  name: string;
  description: string;
  avatar_url?: string | null;
  category: string;
  system_prompt: string;
  workflow_id: string;
  collection_id: string;
  is_active: boolean;
  tenant_id: string;
  config: AssistantLifecycleConfig;
}

export type AssistantUpdateInput = Partial<Omit<AssistantInput, "code" | "tenant_id">>;

export interface AssistantTemplate {
  code: string;
  name: string;
  description: string;
  category: string;
  system_prompt: string;
  workflow_id: string;
  collection_id: string;
  config: AssistantLifecycleConfig;
}

export interface AssistantSeedResult {
  assistants_added: number;
  assistants_skipped: number;
  workflows_added: number;
  workflows_skipped: number;
  total_assistants: number;
}

export interface AssistantBundleWorkflow {
  id: string;
  name: string;
  display_name: string;
  description?: string | null;
  module_code: string;
  version: string;
  dag_spec: Record<string, unknown>;
}

export interface AssistantBundle {
  format_version: "qnu.assistant.bundle/v1";
  exported_at: string;
  assistant: AssistantInput;
  workflow?: AssistantBundleWorkflow | null;
}

function getErrorMessage(payload: unknown, status: number): string {
  if (typeof payload === "object" && payload !== null) {
    const record = payload as Record<string, unknown>;
    if (typeof record.detail === "string") return record.detail;
    if (typeof record.title === "string") return record.title;
  }
  return `Yêu cầu quản trị trợ lý thất bại (HTTP ${status}).`;
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    throw new Error(getErrorMessage(payload, response.status));
  }
  return (await response.json()) as T;
}

export function listAssistants(options?: {
  search?: string;
  category?: string;
  includeInactive?: boolean;
}): Promise<AssistantItem[]> {
  const params = new URLSearchParams();
  if (options?.search) params.set("search", options.search);
  if (options?.category && options.category !== "all") {
    params.set("category", options.category);
  }
  if (options?.includeInactive) params.set("include_inactive", "true");
  const query = params.toString();
  return requestJson<AssistantItem[]>(`${ASSISTANTS_URL}${query ? `?${query}` : ""}`);
}

export function getAssistant(reference: string): Promise<AssistantItem> {
  return requestJson<AssistantItem>(`${ASSISTANTS_URL}/${encodeURIComponent(reference)}`);
}

export function listAssistantTemplates(): Promise<AssistantTemplate[]> {
  return requestJson<AssistantTemplate[]>(`${ASSISTANTS_URL}/templates`);
}

export function createAssistant(input: AssistantInput): Promise<AssistantItem> {
  return requestJson<AssistantItem>(ASSISTANTS_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function updateAssistant(
  reference: string,
  input: AssistantUpdateInput
): Promise<AssistantItem> {
  return requestJson<AssistantItem>(`${ASSISTANTS_URL}/${encodeURIComponent(reference)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function deactivateAssistant(reference: string): Promise<AssistantItem> {
  return requestJson<AssistantItem>(`${ASSISTANTS_URL}/${encodeURIComponent(reference)}`, {
    method: "DELETE",
  });
}

export function activateAssistant(reference: string): Promise<AssistantItem> {
  return updateAssistant(reference, { is_active: true });
}

export function seedDefaultAssistants(): Promise<AssistantSeedResult> {
  return requestJson<AssistantSeedResult>(`${ASSISTANTS_URL}/seed-defaults`, { method: "POST" });
}

export function exportAssistantBundle(reference: string): Promise<AssistantBundle> {
  return requestJson<AssistantBundle>(`${ASSISTANTS_URL}/${encodeURIComponent(reference)}/export`);
}

export function importAssistantBundle(bundle: AssistantBundle): Promise<AssistantItem> {
  return requestJson<AssistantItem>(`${ASSISTANTS_URL}/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(bundle),
  });
}

export interface AssistantGeneratedSpec {
  name: string;
  description: string;
  category: string;
  system_prompt: string;
  sample_questions: string[];
  temperature: number;
  no_answer_message: string;
  suggested_workflow_id?: string | null;
}

export function generateAssistantSpec(
  idea: string,
  categoryHint?: string
): Promise<AssistantGeneratedSpec> {
  return requestJson<AssistantGeneratedSpec>(`${ASSISTANTS_URL}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      idea,
      category_hint: categoryHint && categoryHint !== "all" ? categoryHint : undefined,
    }),
  });
}

export function getAssistantReadiness(reference: string): Promise<AssistantReadinessResponse> {
  return requestJson<AssistantReadinessResponse>(
    `${ASSISTANTS_URL}/${encodeURIComponent(reference)}/readiness`
  );
}

export function publishAssistant(reference: string): Promise<AssistantPublishResponse> {
  return requestJson<AssistantPublishResponse>(
    `${ASSISTANTS_URL}/${encodeURIComponent(reference)}/publish`,
    {
      method: "POST",
    }
  );
}

export function cloneAssistant(
  reference: string,
  request: AssistantCloneRequest
): Promise<AssistantItem> {
  return requestJson<AssistantItem>(`${ASSISTANTS_URL}/${encodeURIComponent(reference)}/clone`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function getAssistantVersions(reference: string): Promise<AssistantVersionItem[]> {
  return requestJson<AssistantVersionItem[]>(
    `${ASSISTANTS_URL}/${encodeURIComponent(reference)}/versions`
  );
}

export function rollbackAssistantVersion(
  reference: string,
  versionId: string
): Promise<AssistantRollbackResponse> {
  return requestJson<AssistantRollbackResponse>(
    `${ASSISTANTS_URL}/${encodeURIComponent(reference)}/rollback/${encodeURIComponent(versionId)}`,
    {
      method: "POST",
    }
  );
}

export const assistantsApi = {
  getAssistants: listAssistants,
  getAssistant,
  createAssistant,
  updateAssistant,
  deleteAssistant: deactivateAssistant,
  toggleAssistant: (reference: string, isActive: boolean) =>
    updateAssistant(reference, { is_active: isActive }),
  generateAssistantSpec,
  listAssistantTemplates,
  seedDefaultAssistants,
  exportAssistantBundle,
  importAssistantBundle,
  getAssistantReadiness,
  publishAssistant,
  cloneAssistant,
  getAssistantVersions,
  rollbackAssistantVersion,
};
