const DOCUMENT_TYPES_BASE_URL = "/platform/v1alpha1/document-types";

export type DocumentTypeCategory = "legal_internal" | "administrative" | "academic" | "forms";

export interface DocumentTypeItem {
  id: string;
  code: string;
  name: string;
  category: DocumentTypeCategory;
  category_name: string;
  description: string | null;
  priority: number;
  retention_period: string | null;
  nd30: boolean;
  is_active: boolean;
  is_system_default: boolean;
  is_custom: boolean;
  doc_count: number;
  source_system: string;
  source_version: string | null;
  source_hash: string | null;
  synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentTypeInput {
  code: string;
  name: string;
  category: DocumentTypeCategory;
  description: string;
  priority: number;
  retention_period: string;
}

export type DocumentTypeUpdateInput = Omit<DocumentTypeInput, "code"> & {
  is_active?: boolean;
};

export interface DocumentTypeSyncResult {
  taxonomy_version: string;
  source_system: string;
  source_hash: string;
  added: number;
  updated: number;
  deactivated: number;
  skipped: number;
  total: number;
  synced_at: string;
}

interface ApiProblem {
  detail?: string;
  title?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${DOCUMENT_TYPES_BASE_URL}${path}`, init);
  } catch {
    throw new Error("Không kết nối được Backend để tải taxonomy loại văn bản.");
  }

  if (!response.ok) {
    const problem = (await response.json().catch(() => null)) as ApiProblem | null;
    throw new Error(
      problem?.detail || problem?.title || `API loại văn bản lỗi HTTP ${response.status}.`
    );
  }

  return (await response.json()) as T;
}

export async function listDocumentTypes(
  params: {
    search?: string;
    category?: DocumentTypeCategory | "all";
    activeOnly?: boolean;
  } = {}
): Promise<DocumentTypeItem[]> {
  const query = new URLSearchParams();
  if (params.search?.trim()) {
    query.set("search", params.search.trim());
  }
  if (params.category && params.category !== "all") {
    query.set("category", params.category);
  }
  if (params.activeOnly) {
    query.set("active_only", "true");
  }
  const queryString = query.toString();
  return request<DocumentTypeItem[]>(queryString ? `?${queryString}` : "");
}

export function getDocumentType(code: string): Promise<DocumentTypeItem> {
  return request<DocumentTypeItem>(`/${encodeURIComponent(code)}`);
}

export function createDocumentType(input: DocumentTypeInput): Promise<DocumentTypeItem> {
  return request<DocumentTypeItem>("", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function updateDocumentType(
  code: string,
  input: DocumentTypeUpdateInput
): Promise<DocumentTypeItem> {
  return request<DocumentTypeItem>(`/${encodeURIComponent(code)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function deactivateDocumentType(code: string): Promise<DocumentTypeItem> {
  return request<DocumentTypeItem>(`/${encodeURIComponent(code)}/deactivate`, { method: "POST" });
}

export function activateDocumentType(code: string): Promise<DocumentTypeItem> {
  return request<DocumentTypeItem>(`/${encodeURIComponent(code)}/activate`, { method: "POST" });
}

export function syncDocumentTypes(): Promise<DocumentTypeSyncResult> {
  return request<DocumentTypeSyncResult>("/sync", { method: "POST" });
}
