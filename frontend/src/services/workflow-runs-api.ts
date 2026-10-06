import type {
  WorkflowApproval,
  WorkflowExecuteRequest,
  WorkflowExecuteResponse,
  WorkflowRun,
} from "@/types/workflows";
import { BASE_URL, isJsonObject } from "./http-client";

export const workflowRunsApi = {
  async getWorkflowRuns(): Promise<WorkflowRun[]> {
    const res = await fetch(`${BASE_URL}/workflows/executions`);
    if (!res.ok) {
      throw new Error(`Không tải được lịch sử workflow (HTTP ${res.status}).`);
    }
    const data: unknown = await res.json();
    if (!Array.isArray(data)) {
      throw new Error("Backend trả về lịch sử workflow không đúng định dạng.");
    }
    return data.map((item, index) => {
      if (!isJsonObject(item)) {
        throw new Error(
          `Bản ghi workflow thứ ${index + 1} không đúng định dạng.`,
        );
      }
      const status = item.status;
      if (
        status !== "completed" &&
        status !== "running" &&
        status !== "failed" &&
        status !== "paused_for_approval"
      ) {
        throw new Error(
          `Bản ghi workflow thứ ${index + 1} có trạng thái không hợp lệ.`,
        );
      }
      const requiredStringFields = [
        "id",
        "workflow_id",
        "workflow_name",
        "started_at",
      ];
      if (
        !requiredStringFields.every((field) => typeof item[field] === "string")
      ) {
        throw new Error(
          `Bản ghi workflow thứ ${index + 1} thiếu trường bắt buộc.`,
        );
      }
      const numericFields = ["duration_ms", "steps_completed", "total_steps"];
      if (!numericFields.every((field) => typeof item[field] === "number")) {
        throw new Error(
          `Bản ghi workflow thứ ${index + 1} thiếu số liệu thực thi.`,
        );
      }
      return {
        id: item.id as string,
        workflow_id: item.workflow_id as string,
        workflow_name: item.workflow_name as string,
        status,
        duration_ms: item.duration_ms as number,
        steps_completed: item.steps_completed as number,
        total_steps: item.total_steps as number,
        started_at: item.started_at as string,
        executed_nodes: Array.isArray(item.executed_nodes)
          ? item.executed_nodes.filter(
              (nodeId): nodeId is string => typeof nodeId === "string",
            )
          : [],
      };
    });
  },

  async executeWorkflow(
    payload: WorkflowExecuteRequest,
  ): Promise<WorkflowExecuteResponse> {
    const res = await fetch(`${BASE_URL}/workflows/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workflow_id: payload.workflow_id,
        inputs: payload.inputs,
        tenant_id: payload.tenant_id || "tenant_qnu",
        conversation_id: payload.conversation_id,
      }),
    });
    if (!res.ok) {
      throw new Error(`Thực thi workflow thất bại (HTTP ${res.status}).`);
    }
    return (await res.json()) as WorkflowExecuteResponse;
  },

  async getPendingApprovals(): Promise<WorkflowApproval[]> {
    const res = await fetch(`${BASE_URL}/workflows/approvals`);
    if (!res.ok) {
      throw new Error(
        `Không tải được danh sách phê duyệt (HTTP ${res.status}).`,
      );
    }
    return (await res.json()) as WorkflowApproval[];
  },

  async decideApproval(
    executionId: string,
    approvalId: string,
    payload: {
      approved: boolean;
      decided_by: string;
      decision_reason?: string;
    },
  ): Promise<WorkflowExecuteResponse> {
    const res = await fetch(
      `${BASE_URL}/workflows/executions/${executionId}/approvals/${approvalId}/decision`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) {
      throw new Error(`Xử lý phê duyệt thất bại (HTTP ${res.status}).`);
    }
    return (await res.json()) as WorkflowExecuteResponse;
  },
};
