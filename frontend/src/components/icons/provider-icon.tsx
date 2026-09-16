import { Cpu, FileText, Server } from "lucide-react";
import type React from "react";

interface ProviderIconProps {
  code: string;
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}

const LOBE_PROVIDER_ICONS: Record<string, string> = {
  cloudflare: "/icons/providers/cloudflare.svg",
  nvidia: "/icons/providers/nvidia.svg",
  openai: "/icons/providers/openai.svg",
  gemini: "/icons/providers/gemini.svg",
  google: "/icons/providers/gemini.svg",
  anthropic: "/icons/providers/anthropic.svg",
  claude: "/icons/providers/anthropic.svg",
  deepseek: "/icons/providers/deepseek.svg",
  groq: "/icons/providers/groq.svg",
  ollama: "/icons/providers/ollama.svg",
  vllm: "/icons/providers/vllm.svg",
  local_vllm: "/icons/providers/vllm.svg",
  qwen: "/icons/providers/qwen.svg",
  mistral: "/icons/providers/mistral.svg",
  openrouter: "/icons/providers/openrouter.svg",
};

export const ProviderIcon: React.FC<ProviderIconProps> = ({
  code,
  size = 24,
  className,
  style,
}) => {
  const normalized = (code || "").toLowerCase().trim();

  // Match known provider from official Lobe Icons
  const matchedKey = Object.keys(LOBE_PROVIDER_ICONS).find(
    (k) => normalized === k || normalized.includes(k)
  );

  if (matchedKey) {
    return (
      <img
        src={LOBE_PROVIDER_ICONS[matchedKey]}
        alt={code}
        width={size}
        height={size}
        className={className}
        style={{
          width: `${size}px`,
          height: `${size}px`,
          objectFit: "contain",
          display: "block",
          ...style,
        }}
      />
    );
  }

  if (normalized.includes("ocr") || normalized.includes("rapid")) {
    return <FileText size={size} style={{ color: "#d97706", ...style }} className={className} />;
  }

  if (normalized.includes("local") || normalized.includes("server") || normalized.includes("gpu")) {
    return (
      <Server size={size} className={className} style={{ color: "var(--primary)", ...style }} />
    );
  }

  return <Cpu size={size} className={className} style={{ color: "var(--primary)", ...style }} />;
};
