import type { Capability } from "@/api/modelops/types";

export const NONE_VALUE = "__none__";

export const CAPABILITIES_LIST: {
  key: Capability;
  name: string;
  description: string;
}[] = [
  {
    key: "chat",
    name: "Trò chuyện",
    description: "Dùng cho hội thoại và tác vụ văn bản theo cấu hình mặc định",
  },
  {
    key: "embedding",
    name: "Lập chỉ mục",
    description: "Tạo vector để tìm nội dung tài liệu",
  },
  {
    key: "rerank",
    name: "Xếp hạng kết quả",
    description: "Sắp xếp lại các đoạn tìm được",
  },
  {
    key: "ocr",
    name: "Đọc tài liệu ảnh",
    description: "Bóc tách chữ từ ảnh và PDF scan",
  },
];

export function formatProviderLabel(item: {
  model_name: string;
  name: string;
}): string {
  const parts = item.name.split("·").map((s) => s.trim());
  if (
    parts.length > 1 &&
    parts[parts.length - 1].toLowerCase() === item.model_name.toLowerCase()
  ) {
    return parts.slice(0, -1).join(" · ").trim();
  }
  return parts[0] || item.name;
}

export function formatModelLabel(item: {
  model_name: string;
  name: string;
}): string {
  return `${item.model_name} · ${formatProviderLabel(item)}`;
}

export function buildSystemDefaultsPayload(
  userEdits: Partial<Record<Capability, string | null>>,
  serverValues: Record<Capability, string | null>,
): Record<string, string | null> {
  const payload: Record<string, string | null> = {};
  for (const cap of CAPABILITIES_LIST.map((c) => c.key)) {
    if (cap in userEdits) {
      const edited = userEdits[cap];
      const server = serverValues[cap];
      if (edited !== undefined && edited !== server) {
        payload[`${cap}_provider_id`] = edited;
      }
    }
  }
  return payload;
}
