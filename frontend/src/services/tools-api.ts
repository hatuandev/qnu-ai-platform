import { ADMINISTRATIVE_TEMPLATES } from "@/constants/administrative-templates";
import { UIS_MAJORS_DATABASE } from "@/constants/uis-majors";
import type { AdministrativeTemplate, UisMajorInfo } from "@/types/domain-templates";
import type { ToolExecuteRequest, ToolExecuteResponse, ToolItem } from "@/types/tools";
import { BASE_URL } from "./http-client";

export const toolsApi = {
  async getTools(): Promise<ToolItem[]> {
    const res = await fetch(`${BASE_URL}/tools`);
    if (!res.ok) {
      throw new Error(`Không tải được danh sách công cụ (HTTP ${res.status}).`);
    }
    const data = await res.json();
    if (!Array.isArray(data)) {
      return [];
    }
    return data.map((item, idx) => {
      const d = item as Record<string, unknown>;
      const rawName = (d.display_name as string) || (d.name as string) || "Tool";
      const code = (d.code as string) || (d.name as string) || `tool_${idx}`;
      let normalizedCode = code;
      if (code.includes("admission") || code.includes("score")) {
        normalizedCode = "uis_admissions_query";
      } else if (code.includes("document") || code.includes("nd30")) {
        normalizedCode = "docx_nd30_exporter";
      } else if (code.includes("exam") || code.includes("matrix") || code.includes("bloom")) {
        normalizedCode = "xlsx_bloom_matrix";
      }

      return {
        id: (d.id as string) || `tool_${idx + 1}`,
        code: normalizedCode,
        name: rawName,
        description: (d.description as string) || "",
        category: (d.category as string) || "general",
        requires_approval: typeof d.requires_approval === "boolean" ? d.requires_approval : false,
        status: ((d.status as string) || (d.is_active ? "ready" : "maintenance")) as
          | "ready"
          | "maintenance",
        usage_count: typeof d.usage_count === "number" ? d.usage_count : 0,
        endpoint: (d.endpoint as string) || `/platform/v1alpha1/tools/${code}`,
      };
    });
  },

  /**
   * Lấy danh sách phôi mẫu văn bản hành chính chuẩn QNU.
   */
  async getAdministrativeTemplates(): Promise<AdministrativeTemplate[]> {
    return Promise.resolve(ADMINISTRATIVE_TEMPLATES);
  },

  /**
   * Lấy danh sách thông tin tuyển sinh & điểm chuẩn các ngành từ Cổng UIS.
   */
  async getUisMajors(): Promise<UisMajorInfo[]> {
    return Promise.resolve(UIS_MAJORS_DATABASE);
  },

  /**
   * Thực thi công cụ ngoại vi (Function Calling Execution) trung thực qua Tool Gateway.
   */
  async executeTool(payload: ToolExecuteRequest): Promise<ToolExecuteResponse> {
    const startTs = Date.now();
    try {
      const res = await fetch("/platform/v1alpha1/tools/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        return await res.json();
      }
      const errData = await res.json().catch(() => ({}));
      const errorMsg =
        errData.detail ||
        errData.message ||
        `Lỗi thực thi công cụ ngoại vi '${payload.tool_name}' (HTTP ${res.status}).`;
      return {
        tool_name: payload.tool_name,
        status: "failed",
        error_message: errorMsg,
        result: { error: errorMsg },
        latency_ms: Date.now() - startTs,
      };
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Mất kết nối tới dịch vụ Tool Gateway máy chủ.";
      return {
        tool_name: payload.tool_name,
        status: "failed",
        error_message: errorMsg,
        result: { error: errorMsg },
        latency_ms: Date.now() - startTs,
      };
    }
  },
};
