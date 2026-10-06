import type { NodeManifest } from "@/types/common";
import { BASE_URL, isJsonObject } from "./http-client";

export type NodeCategoryKey =
  | "all"
  | "input"
  | "ai"
  | "knowledge"
  | "routing"
  | "control"
  | "interaction"
  | "tool"
  | "output";

export interface NodeCategoryMeta {
  key: NodeCategoryKey;
  label: string;
  shortLabel: string;
  description: string;
}

export const NODE_CATEGORIES: NodeCategoryMeta[] = [
  {
    key: "all",
    label: "Tất cả nhóm",
    shortLabel: "Tất cả",
    description: "Toàn bộ danh mục Node",
  },
  {
    key: "input",
    label: "Đầu vào & Tiếp nhận",
    shortLabel: "Đầu vào",
    description: "Tiếp nhận câu hỏi, hội thoại người dùng",
  },
  {
    key: "ai",
    label: "Trí tuệ Nhân tạo (LLM)",
    shortLabel: "AI Core",
    description: "Sinh văn bản, viết lại truy vấn, trích xuất thực thể",
  },
  {
    key: "knowledge",
    label: "Tri thức & RAG",
    shortLabel: "RAG Tri thức",
    description: "Truy hồi vector Qdrant, kết hợp ngữ nghĩa và bảng sự thực",
  },
  {
    key: "routing",
    label: "Điều hướng & Rẽ nhánh",
    shortLabel: "Điều hướng",
    description: "Định tuyến điều kiện, phân luồng nghiệp vụ",
  },
  {
    key: "control",
    label: "Kiểm soát & Giám sát (HITL)",
    shortLabel: "Kiểm soát",
    description: "Phê duyệt cán bộ, guardrail trích dẫn an toàn",
  },
  {
    key: "interaction",
    label: "Tương tác & Làm rõ",
    shortLabel: "Tương tác",
    description: "Hỏi thêm thông tin, làm rõ ngữ cảnh câu hỏi",
  },
  {
    key: "tool",
    label: "Công cụ & Xuất bản",
    shortLabel: "Công cụ",
    description: "Gọi API bên thứ ba, xuất tệp tin văn bản",
  },
  {
    key: "output",
    label: "Đầu ra & Phản hồi",
    shortLabel: "Đầu ra",
    description: "Phát luồng SSE, xuất bản ghi, từ chối an toàn",
  },
];

export function getNodeCategoryLabel(
  categoryKey: string,
  short = false,
): string {
  const found = NODE_CATEGORIES.find((c) => c.key === categoryKey);
  if (!found) return categoryKey;
  return short ? found.shortLabel : found.label;
}

export function isNodeManifest(value: unknown): value is NodeManifest {
  if (!isJsonObject(value)) {
    return false;
  }
  const stringFields = [
    "api_version",
    "type",
    "version",
    "display_name",
    "description",
    "category",
    "status",
  ];
  return (
    stringFields.every((field) => typeof value[field] === "string") &&
    isJsonObject(value.input_schema) &&
    isJsonObject(value.output_schema) &&
    isJsonObject(value.config_schema)
  );
}

export interface ListNodesParams {
  search?: string;
  category?: string;
  status?: string;
}

export const nodeCatalogApi = {
  async listNodes(params?: ListNodesParams): Promise<NodeManifest[]> {
    const url = new URL(`${BASE_URL}/nodes`, window.location.origin);
    if (params?.search?.trim()) {
      url.searchParams.set("search", params.search.trim());
    }
    if (params?.category && params.category !== "all") {
      url.searchParams.set("category", params.category);
    }
    if (params?.status && params.status !== "all") {
      url.searchParams.set("status", params.status);
    }

    const res = await fetch(url.toString(), {
      headers: {
        Accept: "application/json",
      },
    });

    if (!res.ok) {
      throw new Error(
        `Không thể tải danh mục Node (Mã phản hồi HTTP ${res.status}).`,
      );
    }

    const data: unknown = await res.json();
    if (!isJsonObject(data) || !Array.isArray(data.items)) {
      throw new Error("Phản hồi danh mục Node không đúng định dạng dữ liệu.");
    }

    return data.items.filter(isNodeManifest);
  },

  async getNodeByType(type: string): Promise<NodeManifest | null> {
    const all = await this.listNodes();
    return all.find((n) => n.type === type) || null;
  },
};
