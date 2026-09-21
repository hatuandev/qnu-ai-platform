import type { ModelProvider } from "../../services/api-client";

export type ProviderCategory = "all" | "cloud" | "local" | "custom";

export const getProviderCategory = (prov: ModelProvider): "cloud" | "local" | "custom" => {
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

export const getModelCapabilities = (
  modelName: string
): { hasVision: boolean; hasReasoning: boolean } => {
  const mLower = modelName.toLowerCase();
  const hasVision =
    mLower.includes("vision") ||
    mLower.includes("flash") ||
    mLower.includes("4o") ||
    mLower.includes("sonnet") ||
    mLower.includes("opus") ||
    mLower.includes("ocr") ||
    mLower.includes("docling");
  const hasReasoning =
    mLower.includes("reason") ||
    mLower.includes("o1") ||
    mLower.includes("o3") ||
    mLower.includes("r1") ||
    mLower.includes("thinking") ||
    mLower.includes("pro") ||
    mLower.includes("high");
  return { hasVision, hasReasoning };
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
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
  ],
  claude: ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
  deepseek: ["deepseek-chat", "deepseek-reasoner"],
  groq: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
  mistral: ["mistral-ocr-latest"],
  cloudflare: ["@cf/baai/bge-m3", "@cf/baai/bge-reranker-base", "@cf/meta/llama-3.1-8b-instruct"],
  nvidia: ["meta/llama-3.3-70b-instruct", "deepseek-ai/deepseek-r1"],
  ollama: ["qwen2.5:7b", "llama3.1:8b", "bge-m3:latest"],
  local_vllm: ["qwen2.5-7b-instruct"],
  openrouter: ["google/gemini-2.0-flash-exp:free", "meta-llama/llama-3.3-70b-instruct"],
  sentence_transformers: ["BAAI/bge-m3"],
  docling: ["docling-tableformer-local"],
};
