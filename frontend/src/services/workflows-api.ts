/** Typed client for persisted workflow drafts, publications, execution, and approvals. */

const WORKFLOWS_API_BASE_URL = "/platform/v1alpha1/workflows";

export interface WorkflowNodeSpec {
  id: string;
  type: string;
  version: string;
  display_name?: string | null;
  config: Record<string, unknown>;
  policy: Record<string, unknown>;
}

export interface WorkflowEdgeSpec {
  source: string;
  target: string;
  source_port?: string | null;
  target_port?: string | null;
  condition?: string | null;
  label?: string | null;
}

export interface WorkflowDagSpec {
  execution_mode: string;
  entry_node_id: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  policies: Record<string, unknown>;
  nodes: WorkflowNodeSpec[];
  edges: WorkflowEdgeSpec[];
}

export interface WorkflowDefinition {
  id: string;
  name: string;
  display_name: string;
  description?: string | null;
  module_code: string;
  version: string;
  is_active: boolean;
  nodes_count: number;
  edges_count: number;
  published_version_id?: string | null;
}

export interface WorkflowDraft {
  workflow_id: string;
  dag_spec: WorkflowDagSpec;
  revision: number;
  updated_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowValidationIssue {
  code: string;
  message: string;
  severity: "error" | "warning";
  node_id?: string | null;
  edge_index?: number | null;
}

export interface WorkflowValidationReport {
  is_valid: boolean;
  issues: WorkflowValidationIssue[];
  node_count: number;
  edge_count: number;
}

export interface WorkflowVersion {
  id: string;
  workflow_id: string;
  version_number: number;
  content_hash: string;
  dag_spec: WorkflowDagSpec;
  validation_report: WorkflowValidationReport;
  published_by?: string | null;
  published_at: string;
}

export interface WorkflowExecutionRequest {
  workflow_id: string;
  inputs: Record<string, unknown>;
  tenant_id?: string;
  conversation_id?: string;
}

export interface WorkflowExecutionResponse {
  execution_id: string;
  workflow_id: string;
  status: "completed" | "failed" | "paused_for_approval";
  outputs: Record<string, unknown>;
  executed_nodes: string[];
  latency_ms: number;
  error_message?: string | null;
  paused_node_id?: string | null;
}

export interface WorkflowApproval {
  id: string;
  execution_id: string;
  checkpoint_id: string;
  node_id: string;
  description?: string | null;
  status: "pending" | "approved" | "rejected";
  decided_by?: string | null;
  decision_reason?: string | null;
  created_at: string;
  decided_at?: string | null;
}

interface ApiErrorPayload {
  detail?: string;
  title?: string;
}

async function readApiError(response: Response): Promise<string> {
  const fallbackMessage = `Yêu cầu workflow thất bại (HTTP ${response.status}).`;
  try {
    const payload = (await response.json()) as ApiErrorPayload;
    return payload.detail || payload.title || fallbackMessage;
  } catch {
    return fallbackMessage;
  }
}

async function requestWorkflow<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${WORKFLOWS_API_BASE_URL}${path}`, init);
  } catch {
    throw new Error("Không kết nối được Backend Workflow. Hãy kiểm tra dịch vụ đang chạy.");
  }
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as T;
}

function jsonRequest(method: "POST" | "PUT", body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export const workflowsApi = {
  listDefinitions(): Promise<WorkflowDefinition[]> {
    return requestWorkflow<WorkflowDefinition[]>("/definitions");
  },

  getDraft(workflowId: string): Promise<WorkflowDraft> {
    return requestWorkflow<WorkflowDraft>(`/definitions/${workflowId}/draft`);
  },

  saveDraft(
    workflowId: string,
    payload: {
      dag_spec: WorkflowDagSpec;
      expected_revision: number;
      updated_by: string;
    }
  ): Promise<WorkflowDraft> {
    return requestWorkflow<WorkflowDraft>(
      `/definitions/${workflowId}/draft`,
      jsonRequest("PUT", payload)
    );
  },

  validateDraft(workflowId: string): Promise<WorkflowValidationReport> {
    return requestWorkflow<WorkflowValidationReport>(
      `/definitions/${workflowId}/draft/validate`,
      jsonRequest("POST", {})
    );
  },

  publishDraft(
    workflowId: string,
    payload: { expected_revision: number; published_by: string }
  ): Promise<WorkflowVersion> {
    return requestWorkflow<WorkflowVersion>(
      `/definitions/${workflowId}/publish`,
      jsonRequest("POST", payload)
    );
  },

  listVersions(workflowId: string): Promise<WorkflowVersion[]> {
    return requestWorkflow<WorkflowVersion[]>(`/definitions/${workflowId}/versions`);
  },

  rollbackVersion(
    workflowId: string,
    versionId: string,
    payload: { published_by: string }
  ): Promise<WorkflowVersion> {
    return requestWorkflow<WorkflowVersion>(
      `/definitions/${workflowId}/versions/${versionId}/rollback`,
      jsonRequest("POST", payload)
    );
  },

  execute(payload: WorkflowExecutionRequest): Promise<WorkflowExecutionResponse> {
    return requestWorkflow<WorkflowExecutionResponse>("/execute", jsonRequest("POST", payload));
  },

  decideApproval(
    executionId: string,
    approvalId: string,
    payload: { approved: boolean; decided_by: string; decision_reason?: string }
  ): Promise<WorkflowExecutionResponse> {
    return requestWorkflow<WorkflowExecutionResponse>(
      `/executions/${executionId}/approvals/${approvalId}/decision`,
      jsonRequest("POST", payload)
    );
  },
};
