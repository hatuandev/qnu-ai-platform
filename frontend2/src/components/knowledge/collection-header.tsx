import {
  ArrowLeft,
  CheckCircle2,
  CircleAlert,
  Cpu,
  RefreshCw,
  Settings,
  ShieldCheck,
  Upload,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { KnowledgeCollection } from "@/types";

interface CollectionHeaderProps {
  collection: KnowledgeCollection;
  documentCount: number;
  systemDefaultEmbeddingModel?: string;
  onBack: () => void;
  onOpenReconcile: () => void;
  onReindex: () => void;
  isReindexing: boolean;
  onOpenConfig: () => void;
  onStartIngest: () => void;
  actionError: string | null;
  reindexJobId: string | null;
}

export function CollectionHeader({
  collection,
  documentCount,
  systemDefaultEmbeddingModel,
  onBack,
  onOpenReconcile,
  onReindex,
  isReindexing,
  onOpenConfig,
  onStartIngest,
  actionError,
  reindexJobId,
}: CollectionHeaderProps) {
  const embeddingModelDisplay =
    collection.embedding_model ||
    systemDefaultEmbeddingModel ||
    "BAAI/bge-m3 (1024-dim)";

  const isCloudflareModel = embeddingModelDisplay.includes("@cf/");

  return (
    <div className="bg-card border border-border rounded-lg p-3.5 sm:p-5 shadow-xs space-y-3">
      {/* Top Header Section */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3.5">
        <div className="flex flex-col sm:flex-row sm:items-center gap-2.5 min-w-0">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onBack}
              className="h-8 px-2.5 rounded-md shrink-0 text-muted-foreground hover:text-foreground text-xs gap-1.5"
              title="Quay lại danh sách kho"
              aria-label="Quay lại danh sách kho"
            >
              <ArrowLeft className="size-3.5" />
              <span>Kho</span>
            </Button>

            <div className="flex items-center gap-1.5 sm:hidden">
              <Badge
                variant="outline"
                className="bg-success/10 text-success border-success/30 font-medium text-[11px] py-0"
              >
                Sẵn sàng
              </Badge>
              <span className="font-mono text-[11px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                {collection.code}
              </span>
            </div>
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-base sm:text-lg font-bold text-foreground break-words">
                {collection.name}
              </h1>
              <div className="hidden sm:flex items-center gap-1.5">
                <Badge
                  variant="outline"
                  className="bg-success/10 text-success border-success/30 font-medium text-xs py-0"
                >
                  Sẵn sàng
                </Badge>
                <span className="font-mono text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                  {collection.code}
                </span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2 sm:line-clamp-1">
              {collection.description ||
                "Chưa có mô tả chi tiết cho kho tri thức này."}
            </p>
          </div>
        </div>

        {/* Action Buttons: 3 cols grid + full width primary CTA on mobile, inline flex on desktop */}
        <div className="grid grid-cols-3 sm:flex sm:items-center gap-2 w-full lg:w-auto shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenReconcile}
            className="h-8 text-xs gap-1 sm:gap-1.5 px-2"
            title="Đối soát dữ liệu giữa PostgreSQL, Qdrant và MinIO"
          >
            <ShieldCheck className="size-3.5 text-primary" />
            <span>Đối soát</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={onReindex}
            disabled={isReindexing}
            className="h-8 text-xs gap-1 sm:gap-1.5 px-2"
            title="Tính toán lại toàn bộ vector embeddings trong kho"
          >
            <RefreshCw
              className={`size-3.5 ${isReindexing ? "animate-spin text-primary" : ""}`}
            />
            <span>{isReindexing ? "Đang reindex..." : "Reindex"}</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs gap-1 sm:gap-1.5 px-2"
            onClick={onOpenConfig}
            title="Chỉnh sửa tên và mô tả kho"
          >
            <Settings className="size-3.5" />
            <span>Sửa</span>
          </Button>

          <Button
            size="sm"
            onClick={onStartIngest}
            className="col-span-3 sm:col-span-1 h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 font-medium shadow-xs"
          >
            <Upload className="size-3.5" />
            <span>Nạp tài liệu</span>
          </Button>
        </div>
      </div>

      {/* Sub Meta Info Line */}
      <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs text-muted-foreground pt-2.5 border-t border-border/60">
        <span className="inline-flex items-center gap-1.5 font-mono text-xs text-primary bg-primary/5 px-2 py-0.5 rounded border border-primary/20">
          {isCloudflareModel ? (
            <Zap className="size-3.5 text-amber-500 shrink-0" />
          ) : (
            <Cpu className="size-3.5 shrink-0" />
          )}
          <span>{embeddingModelDisplay}</span>
          {!collection.embedding_model && systemDefaultEmbeddingModel && (
            <Badge
              variant="outline"
              className="text-[10px] px-1 py-0 border-primary/30 text-primary bg-primary/10 font-sans font-normal"
            >
              Mặc định
            </Badge>
          )}
        </span>

        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-muted/50 rounded">
          <span className="text-muted-foreground">Chiến lược:</span>
          <strong className="text-foreground font-medium">
            {collection.chunking_strategy}
          </strong>
        </span>

        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-muted/50 rounded font-medium text-foreground">
          <span>{documentCount} văn bản</span>
          <span className="text-muted-foreground font-mono font-normal">
            ({collection.chunk_count} chunks)
          </span>
        </span>

        {reindexJobId && (
          <span className="text-xs text-success font-medium ml-auto flex items-center gap-1">
            <CheckCircle2 className="size-3.5" /> Job {reindexJobId}
          </span>
        )}
      </div>

      {actionError && (
        <div className="flex items-start gap-2 p-2.5 rounded-lg bg-destructive/10 border border-destructive/30 text-xs text-destructive leading-relaxed">
          <CircleAlert className="size-4 shrink-0 mt-0.5" />
          <span>{actionError}</span>
        </div>
      )}
    </div>
  );
}
