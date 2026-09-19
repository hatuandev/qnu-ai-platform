/** Types for Workflow DAG Executions & Runs */

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  workflow_name: string;
  status: "completed" | "running" | "failed" | "paused_for_approval";
  duration_ms: number;
  steps_completed: number;
  total_steps: number;
  started_at: string;
  executed_nodes: string[];
}

export interface WorkflowExecuteRequest {
  workflow_id: string;
  inputs: Record<string, unknown>;
  tenant_id?: string;
  conversation_id?: string;
}

export interface WorkflowExecuteResponse {
  execution_id: string;
  workflow_id: string;
  status: "completed" | "failed" | "paused_for_approval";
  outputs: Record<string, unknown>;
  executed_nodes: string[];
  latency_ms: number;
  error_message?: string | null;
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

export interface WorkflowAssistantsUsageItem {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
  published_workflow_version_id?: string | null;
}

export interface WorkflowAssistantsUsageResponse {
  workflow_id: string;
  count: number;
  assistants: WorkflowAssistantsUsageItem[];
}
