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
