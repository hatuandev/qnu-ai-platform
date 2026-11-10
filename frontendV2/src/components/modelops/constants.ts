import type { Capability, ConnectionFamily } from "@/api/modelops/types";

export type FamilyMeta = {
  id: ConnectionFamily;
  label: string;
  defaultUrl: string;
  prefix: string;
  description: string;
};

export const CONNECTION_FAMILIES: Record<ConnectionFamily, FamilyMeta> = {
  openai: {
    id: "openai",
    label: "OpenAI Compatible",
    defaultUrl: "https://api.openai.com/v1",
    prefix: "openai",
    description:
      "Tương thích chuẩn OpenAI v1 (OpenAI, DeepSeek, Groq, Together, vLLM, Ollama...)",
  },
  gemini: {
    id: "gemini",
    label: "Google Gemini",
    defaultUrl: "https://generativelanguage.googleapis.com/v1beta/openai",
    prefix: "google",
    description: "Google Gemini API qua cổng tương thích OpenAI hoặc Vertex",
  },
  anthropic: {
    id: "anthropic",
    label: "Anthropic Claude",
    defaultUrl: "https://api.anthropic.com/v1",
    prefix: "anthropic",
    description: "Giao thức Anthropic Messages API (Claude 3.5 Sonnet / Haiku)",
  },
  qnu: {
    id: "qnu",
    label: "Server AI QNU",
    defaultUrl: "http://100.105.13.53:8000/v1",
    prefix: "qnu",
    description: "Cụm máy chủ GPU nội bộ trường Đại học Quy Nhơn",
  },
  custom: {
    id: "custom",
    label: "Tùy biến (Custom)",
    defaultUrl: "",
    prefix: "custom",
    description: "Endpoint API máy chủ AI riêng hoặc dịch vụ proxy nội bộ",
  },
};

export const CAPABILITY_LABELS: Record<
  Capability,
  { label: string; description: string; badgeColor: string }
> = {
  chat: {
    label: "Hội thoại (Chat)",
    description: "Hỏi đáp, suy luận, trợ lý AI & sinh câu trả lời RAG",
    badgeColor:
      "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
  },
  embedding: {
    label: "Biểu diễn (Embedding)",
    description:
      "Tạo vector văn bản phục vụ tìm kiếm ngữ nghĩa trong kho tri thức",
    badgeColor:
      "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20",
  },
  rerank: {
    label: "Tái xếp hạng (Rerank)",
    description: "Đánh giá lại độ liên quan của các đoạn trích sau tìm kiếm",
    badgeColor:
      "bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20",
  },
  ocr: {
    label: "Bóc tách (OCR)",
    description: "Trích xuất văn bản và cấu trúc bảng từ hình ảnh / PDF scan",
    badgeColor:
      "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
  },
};
