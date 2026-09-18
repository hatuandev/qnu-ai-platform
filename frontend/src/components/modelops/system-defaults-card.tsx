import { Cpu, RefreshCw, ShieldCheck, Sparkles, Zap } from "lucide-react";
import type React from "react";
import { Badge } from "../../components/ui/badge";
import { Card } from "../../components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import type { SystemModelDefaults } from "../../services/api-client";

export interface SystemDefaultsCardProps {
  systemDefaults?: SystemModelDefaults;
  availableEmbeddings: Array<{ provider_id: string; provider_name: string; model_name: string }>;
  availableRerankers: Array<{ provider_id: string; provider_name: string; model_name: string }>;
  availableOcrs: Array<{ provider_id: string; provider_name: string; model_name: string }>;
  isLoading?: boolean;
  onUpdateDefaults: (payload: Partial<SystemModelDefaults>) => void;
}

export const SystemDefaultsCard: React.FC<SystemDefaultsCardProps> = ({
  systemDefaults,
  availableEmbeddings,
  availableRerankers,
  availableOcrs,
  isLoading,
  onUpdateDefaults,
}) => {
  return (
    <Card className="p-4 border-primary/20 bg-gradient-to-r from-card via-card to-primary/5 space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/60 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-primary/10 text-primary">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-foreground">
                Mô Hình Mặc Định Hệ Thống (Active System Defaults)
              </h3>
              <Badge
                variant="outline"
                className="text-[10px] font-mono text-primary border-primary/30"
              >
                Kho Tri Thức & RAG
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Tự động áp dụng khi nạp tài liệu vào Kho Tri Thức (Embedding) và khi Trợ lý AI thực
              hiện truy xuất thông tin (Reranker).
            </p>
          </div>
        </div>
        {isLoading && <RefreshCw className="h-3.5 w-3.5 animate-spin text-primary shrink-0" />}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {/* 1. Default Embedding */}
        <div className="p-3 rounded-lg bg-background/60 border border-border/80 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Cpu className="h-3.5 w-3.5 text-primary" />
              Embedding (Kho Tri Thức)
            </span>
            <Badge variant="secondary" className="text-[10px] font-mono">
              1024-dim
            </Badge>
          </div>
          <Select
            value={`${systemDefaults?.default_embedding_provider_id}:::${systemDefaults?.default_embedding_model}`}
            onValueChange={(val) => {
              const [pId, mName] = val.split(":::");
              if (pId && mName) {
                onUpdateDefaults({
                  default_embedding_provider_id: pId,
                  default_embedding_model: mName,
                });
              }
            }}
          >
            <SelectTrigger className="w-full h-8 text-xs font-mono bg-card">
              <SelectValue placeholder="Chọn mô hình Embedding mặc định" />
            </SelectTrigger>
            <SelectContent>
              {availableEmbeddings.map((opt) => (
                <SelectItem
                  key={`${opt.provider_id}:::${opt.model_name}`}
                  value={`${opt.provider_id}:::${opt.model_name}`}
                >
                  <span className="font-semibold">{opt.model_name}</span>{" "}
                  <span className="text-muted-foreground text-[11px]">({opt.provider_name})</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-[10px] text-muted-foreground">
            {systemDefaults?.default_embedding_provider_id === "prov_cloudflare"
              ? "⚡ Đang dùng Cloudflare Edge GPU (~1.0s / 16 chunks)"
              : "💻 Đang dùng SentenceTransformers CPU Cục Bộ"}
          </p>
        </div>

        {/* 2. Default Reranker */}
        <div className="p-3 rounded-lg bg-background/60 border border-border/80 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Zap className="h-3.5 w-3.5 text-amber-500" />
              Reranker (Truy Xuất RAG)
            </span>
            <Badge variant="secondary" className="text-[10px] font-mono">
              Cross-Encoder
            </Badge>
          </div>
          <Select
            value={`${systemDefaults?.default_reranker_provider_id}:::${systemDefaults?.default_reranker_model}`}
            onValueChange={(val) => {
              const [pId, mName] = val.split(":::");
              if (pId && mName) {
                onUpdateDefaults({
                  default_reranker_provider_id: pId,
                  default_reranker_model: mName,
                });
              }
            }}
          >
            <SelectTrigger className="w-full h-8 text-xs font-mono bg-card">
              <SelectValue placeholder="Chọn mô hình Reranker mặc định" />
            </SelectTrigger>
            <SelectContent>
              {availableRerankers.map((opt) => (
                <SelectItem
                  key={`${opt.provider_id}:::${opt.model_name}`}
                  value={`${opt.provider_id}:::${opt.model_name}`}
                >
                  <span className="font-semibold">{opt.model_name}</span>{" "}
                  <span className="text-muted-foreground text-[11px]">({opt.provider_name})</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-[10px] text-muted-foreground">
            {systemDefaults?.default_reranker_provider_id === "prov_cloudflare"
              ? "⚡ Đang dùng Cloudflare BGE-Reranker-Base (~1.2s)"
              : "💻 Đang dùng thuật toán RRF Fused Scoring nội bộ"}
          </p>
        </div>

        {/* 3. Default OCR */}
        <div className="p-3 rounded-lg bg-background/60 border border-border/80 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-sky-500" />
              OCR (Bóc Tách Văn Bản)
            </span>
            <Badge variant="secondary" className="text-[10px] font-mono">
              Vision / OCR
            </Badge>
          </div>
          <Select
            value={`${systemDefaults?.default_ocr_provider_id}:::${systemDefaults?.default_ocr_model}`}
            onValueChange={(val) => {
              const [pId, mName] = val.split(":::");
              if (pId && mName) {
                onUpdateDefaults({
                  default_ocr_provider_id: pId,
                  default_ocr_model: mName,
                });
              }
            }}
          >
            <SelectTrigger className="w-full h-8 text-xs font-mono bg-card">
              <SelectValue placeholder="Chọn mô hình OCR mặc định" />
            </SelectTrigger>
            <SelectContent>
              {availableOcrs.map((opt) => (
                <SelectItem
                  key={`${opt.provider_id}:::${opt.model_name}`}
                  value={`${opt.provider_id}:::${opt.model_name}`}
                >
                  <span className="font-semibold">{opt.model_name}</span>{" "}
                  <span className="text-muted-foreground text-[11px]">({opt.provider_name})</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-[10px] text-muted-foreground">
            {systemDefaults?.default_ocr_provider_id === "prov_mistral"
              ? "🌐 Đang dùng Mistral OCR Cloud Vision"
              : "💻 Đang dùng Docling TableFormer Cục Bộ"}
          </p>
        </div>
      </div>
    </Card>
  );
};
