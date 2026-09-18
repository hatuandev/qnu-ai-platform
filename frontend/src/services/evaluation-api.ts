import type {
  EvaluationMetrics,
  EvaluationRunItem,
  EvaluationRunRequest,
  GapInboxItem,
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

  async getGapInbox(): Promise<GapInboxItem[]> {
    const res = await fetch(`${BASE_URL}/evaluation/gap-inbox`);
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
        reason: (d.reason as string) || "Chưa có tài liệu tương ứng trong Kho tri thức.",
        frequency: typeof d.frequency === "number" ? d.frequency : 1,
        timestamp: (d.timestamp as string) || new Date().toISOString(),
        status: ((d.status as string) || "pending") as "pending" | "resolved",
      };
    });
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
