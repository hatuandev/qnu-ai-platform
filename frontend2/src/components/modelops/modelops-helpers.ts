import type { ModelProvider } from "../../services/api-client";

export type ProviderCategory = "all" | "cloud" | "local" | "custom";

export const getProviderCategory = (
  prov: ModelProvider,
): "cloud" | "local" | "custom" => {
  const t = (prov.type || prov.code || "").toLowerCase();
  if (t === "custom") return "custom";
  if (
    t === "sentence_transformers" ||
    t === "docling" ||
    t === "ollama" ||
    t === "local_vllm" ||
    t === "local" ||
    prov.id.includes("local") ||
    prov.id.includes("sentence_transformers") ||
    prov.id.includes("docling") ||
    prov.name.toLowerCase().includes("local") ||
    prov.name.toLowerCase().includes("cục bộ")
  ) {
    return "local";
  }
  return "cloud";
};

export interface ModelCapabilityInfo {
  hasVision: boolean;
  hasReasoning: boolean;
  isOcr: boolean;
  isEmbedding: boolean;
  isReranker: boolean;
  isChat: boolean;
  capabilityLabel: string;
}

export const getModelCapabilities = (
  modelName: string,
): ModelCapabilityInfo => {
  const mLower = modelName.toLowerCase();
  const isGemma = mLower.startsWith("gemma");

  const isEmbedding =
    mLower.includes("embed") ||
    mLower.includes("bge-m3") ||
    mLower.includes("bge-base") ||
    mLower.includes("bge-small") ||
    mLower.includes("bge-large") ||
    mLower.includes("sentence-transformers") ||
    mLower.includes("text-embedding");

  const isReranker =
    mLower.includes("rerank") ||
    mLower.includes("cross-encoder") ||
    mLower.includes("rrf") ||
    mLower.includes("bge-reranker");

  const isOcr =
    !isGemma &&
    !isEmbedding &&
    !isReranker &&
    (mLower.includes("ocr") ||
      mLower.includes("docling") ||
      mLower.includes("easyocr") ||
      mLower.includes("flash-image") ||
      mLower.startsWith("gemini") ||
      mLower.includes("gemini") ||
      mLower.includes("4o") ||
      mLower.includes("sonnet") ||
      mLower.includes("vision"));

  const hasVision =
    !isGemma &&
    !isEmbedding &&
    !isReranker &&
    (isOcr ||
      mLower.includes("vision") ||
      mLower.includes("flash") ||
      mLower.includes("4o") ||
      mLower.includes("sonnet") ||
      mLower.includes("opus"));

  const hasReasoning =
    !isEmbedding &&
    !isReranker &&
    (mLower.includes("reason") ||
      mLower.includes("o1") ||
      mLower.includes("o3") ||
      mLower.includes("r1") ||
      mLower.includes("thinking") ||
      (mLower.includes("pro") && !isEmbedding) ||
      mLower.includes("high"));

  const isChat = !isEmbedding && !isReranker;

  let capabilityLabel = "Thuần Văn Bản (Text-Only)";
  if (isEmbedding) {
    capabilityLabel = "Nhúng Vector Ngữ Nghĩa (Vector Embedding)";
  } else if (isReranker) {
    capabilityLabel = "Tái Xếp Hạng Ngữ Nghĩa (Cross-Encoder Reranker)";
  } else if (isOcr) {
    capabilityLabel = "Bóc Tách Văn Bản & Bảng Biểu (Vision OCR)";
  } else if (hasVision) {
    capabilityLabel = "Thị Giác Máy Tính (Vision)";
  } else if (hasReasoning) {
    capabilityLabel = "Suy Luận Phức Tạp (Reasoning)";
  }

  return {
    hasVision,
    hasReasoning,
    isOcr,
    isEmbedding,
    isReranker,
    isChat,
    capabilityLabel,
  };
};

export const TASK_TYPE_META: Record<
  string,
  {
    label: string;
    shortLabel: string;
    badgeClass: string;
    icon: string;
  }
> = {
  ocr: {
    label: "Bóc Tách & OCR Thị Giác",
    shortLabel: "Vision OCR",
    badgeClass: "bg-primary/10 text-primary border-primary/30",
    icon: "Eye",
  },
  embedding: {
    label: "Nhúng Vector (Kho Tri Thức)",
    shortLabel: "Vector Embedding",
    badgeClass: "bg-primary/10 text-primary border-primary/30",
    icon: "Cpu",
  },
  reranker: {
    label: "Tái Xếp Hạng RAG (Cross-Encoder)",
    shortLabel: "RAG Reranker",
    badgeClass: "bg-primary/10 text-primary border-primary/30",
    icon: "Zap",
  },
  chat: {
    label: "Hội Thoại & Lý Luận (LLM)",
    shortLabel: "LLM Chat",
    badgeClass: "bg-primary/10 text-primary border-primary/30",
    icon: "Brain",
  },
};

export const STRATEGY_META: Record<
  string,
  { label: string; description: string; badgeClass: string }
> = {
  fallback: {
    label: "Fallback (Dự Phòng Lỗi)",
    description:
      "Tự động chuyển tiếp sang mô hình tiếp theo khi gặp Rate Limit 429 hoặc Timeout",
    badgeClass: "bg-muted text-foreground border-border/80 font-mono",
  },
  round_robin: {
    label: "Round Robin (Cân Bằng Tải)",
    description:
      "Chia đều lượt gọi API luân phiên qua các mô hình trong danh sách để dàn trải chi phí",
    badgeClass: "bg-muted text-foreground border-border/80 font-mono",
  },
  fusion: {
    label: "Fusion (Đồng Thời / Ghép Điểm)",
    description:
      "Chạy đồng thời nhiều mô hình và tổng hợp kết quả (hợp nhất điểm số / phiếu bầu)",
    badgeClass: "bg-muted text-foreground border-border/80 font-mono",
  },
};

export const getModelDisplayName = (modelName: string): string => {
  if (modelName.startsWith("@cf/")) {
    return modelName.replace("@cf/", "").toUpperCase();
  }
  const clean = modelName.replace(/^ag\//, "").replace(/-\d{8}$/, "");
  return clean
    .split(/[-_]/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
};

export const PRESET_SUGGESTED_MODELS: Record<string, string[]> = {
  openai: ["gpt-4o", "gpt-4o-mini", "o1-mini"],
  gemini: [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-image",
    "gemini-3.1-pro-preview",
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
  ],
  claude: ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
  deepseek: ["deepseek-chat", "deepseek-reasoner"],
  groq: [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
  ],
  mistral: ["mistral-ocr-latest"],
  cloudflare: [
    "@cf/baai/bge-m3",
    "@cf/baai/bge-reranker-base",
    "@cf/meta/llama-3.1-8b-instruct",
  ],
  nvidia: ["meta/llama-3.3-70b-instruct", "deepseek-ai/deepseek-r1"],
  ollama: ["qwen2.5:7b", "llama3.1:8b", "bge-m3:latest"],
  local_vllm: ["qwen2.5-7b-instruct"],
  openrouter: [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct",
  ],
  sentence_transformers: ["BAAI/bge-m3"],
  docling: ["docling-tableformer-local"],
};
