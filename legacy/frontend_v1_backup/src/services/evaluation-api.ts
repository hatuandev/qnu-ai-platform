import type {
  EvaluationMetrics,
  EvaluationRunItem,
  EvaluationRunRequest,
  GapInboxItem,
  KnowledgeGapResolveRequest,
} from "@/types/evaluation";
import { BASE_URL } from "./http-client";

export const evaluationApi = {
  async getEvaluationMetrics(): Promise<EvaluationMetrics> {
    const res = await fetch(`${BASE_URL}/evaluation/metrics`);
    if (!res.ok) {
      throw new Error(`Không tải được chỉ số kiểm định TM-08 (HTTP ${res.status}).`);
    }
    return await res.json();
  },

  async getGapInbox(options?: {
    assistantCode?: string;
    status?: string;
  }): Promise<GapInboxItem[]> {
    const params = new URLSearchParams();
    if (options?.assistantCode && options.assistantCode !== "all") {
      params.set("assistant_code", options.assistantCode);
    }
    if (options?.status) {
      params.set("status", options.status);
    }
    const query = params.toString();
    const res = await fetch(`${BASE_URL}/evaluation/gap-inbox${query ? `?${query}` : ""}`);
    if (!res.ok) {
      throw new Error(`Không tải được danh sách gap inbox (HTTP ${res.status}).`);
    }
    const data = await res.json();
    if (!Array.isArray(data)) {
      return [];
    }
    return data.map((item, idx) => {
      const d = item as Record<string, unknown>;
      return {
        id: (d.id as string) || `gap_${idx + 1}`,
        question: (d.question as string) || "Câu hỏi cần bổ sung tri thức",
        assistant_code: (d.assistant_code as string) || "admissions",
        assistant_name: (d.assistant_name as string) || "Trợ lý QNU",
        collection_id: (d.collection_id as string) || undefined,
        reason: (d.reason as string) || "Chưa có tài liệu tương ứng trong Kho tri thức.",
        frequency: typeof d.frequency === "number" ? d.frequency : 1,
        timestamp: (d.timestamp as string) || new Date().toISOString(),
        status: ((d.status as string) || "pending") as "pending" | "resolved" | "dismissed",
        resolution_notes: (d.resolution_notes as string) || null,
        resolved_by: (d.resolved_by as string) || null,
      };
    });
  },

  async resolveGap(gapId: string, req: KnowledgeGapResolveRequest): Promise<GapInboxItem> {
    const res = await fetch(`${BASE_URL}/evaluation/gap-inbox/${encodeURIComponent(gapId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      throw new Error(`Không thể đánh dấu xử lý lỗ hổng tri thức (HTTP ${res.status}).`);
    }
    return await res.json();
  },

  async getDatasets(): Promise<
    Array<{
      id: string;
      name: string;
      description: string;
      assistant_code: string;
      total_test_cases: number;
    }>
  > {
    const res = await fetch(`${BASE_URL}/evaluation/datasets`);
    if (!res.ok) {
      throw new Error(`Không tải được danh sách tập dữ liệu kiểm định (HTTP ${res.status}).`);
    }
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  },

  async getEvaluationRuns(assistantCode?: string): Promise<EvaluationRunItem[]> {
    const url = assistantCode
      ? `${BASE_URL}/evaluation/runs?assistant_code=${encodeURIComponent(assistantCode)}`
      : `${BASE_URL}/evaluation/runs`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`Không tải được lịch sử kiểm định (HTTP ${res.status}).`);
    }
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  },

  async getRunDetail(runId: string): Promise<import("@/types/evaluation").EvaluationRunDetail> {
    const res = await fetch(`${BASE_URL}/evaluation/runs/${encodeURIComponent(runId)}`);
    if (!res.ok) {
      throw new Error(`Không tải được chi tiết phiên kiểm định (HTTP ${res.status}).`);
    }
    return await res.json();
  },

  async getRunItems(runId: string): Promise<import("@/types/evaluation").EvaluationResultItem[]> {
    const res = await fetch(`${BASE_URL}/evaluation/runs/${encodeURIComponent(runId)}/items`);
    if (!res.ok) {
      throw new Error(`Không tải được danh sách câu hỏi kiểm định (HTTP ${res.status}).`);
    }
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  },

  async runEvaluation(request: EvaluationRunRequest): Promise<EvaluationRunItem> {
    const res = await fetch(`${BASE_URL}/evaluation/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) {
      throw new Error(`Không thể chạy phiên kiểm định TM-08 (HTTP ${res.status}).`);
    }
    return await res.json();
  },
};
