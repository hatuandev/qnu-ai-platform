/** Types for Platform Tools & Function Calling */

export interface ToolItem {
  id: string;
  code: string;
  name: string;
  description: string;
  category: string;
  requires_approval: boolean;
  status: "ready" | "maintenance";
  usage_count: number;
  endpoint: string;
}

export interface ToolExecuteRequest {
  tool_name: string;
  parameters: Record<string, unknown>;
  tenant_id?: string;
  assistant_code?: string;
  conversation_id?: string;
}

export interface ToolExecuteResponse {
  tool_name: string;
  status: "success" | "failed" | "requires_approval";
  result: Record<string, unknown>;
  latency_ms: number;
  error_message?: string | null;
}
