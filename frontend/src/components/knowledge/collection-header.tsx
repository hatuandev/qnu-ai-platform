import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { KnowledgeCollection } from "@/types";
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
    collection.embedding_model || systemDefaultEmbeddingModel || "BAAI/bge-m3 (1024-dim)";

  const isCloudflareModel = embeddingModelDisplay.includes("@cf/");

  return (
    <div className="bg-card border border-border rounded-lg p-5 sm:p-6 shadow-xs space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="icon"
            onClick={onBack}
            className="size-9 rounded-md shrink-0 text-muted-foreground hover:text-foreground"
            title="Quay lại danh sách kho"
            aria-label="Quay lại danh sách kho"
          >
            <ArrowLeft className="size-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-lg sm:text-xl font-bold text-foreground">{collection.name}</h1>
              <Badge
                variant="outline"
                className="bg-emerald-500/10 text-emerald-600 border-emerald-500/30 font-medium text-xs"
              >
                Sẵn sàng
              </Badge>
              <span className="font-mono text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                {collection.code}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
              {collection.description}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenReconcile}
            className="h-8 text-xs gap-1.5"
          >
            <ShieldCheck className="size-3.5 text-primary" />
            <span>Đối soát Kho</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={onReindex}
            disabled={isReindexing}
            className="h-8 text-xs gap-1.5"
          >
            <RefreshCw className={`size-3.5 ${isReindexing ? "animate-spin text-primary" : ""}`} />
            <span>{isReindexing ? "Đang Reindex..." : "Reindex Kho"}</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs gap-1.5"
            onClick={onOpenConfig}
          >
            <Settings className="size-3.5" />
            <span>Cấu hình</span>
          </Button>

          <Button
            size="sm"
            onClick={onStartIngest}
            className="h-8 text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium shadow-sm"
          >
            <Upload className="size-3.5" />
            <span>+ Nạp tài liệu</span>
          </Button>
        </div>
      </div>

      {/* Sub Meta Info Line */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border/60 flex-wrap">
        <span className="flex items-center gap-1.5 font-mono text-xs text-primary">
          {isCloudflareModel ? (
            <Zap className="size-3.5 text-amber-500 shrink-0" />
          ) : (
            <Cpu className="size-3.5 shrink-0" />
          )}
          <span>{embeddingModelDisplay}</span>
          {!collection.embedding_model && systemDefaultEmbeddingModel && (
            <Badge
              variant="outline"
              className="text-xs px-1.5 py-0 border-primary/30 text-primary bg-primary/5 font-sans font-normal"
            >
              Mặc định hệ thống
            </Badge>
          )}
        </span>
        <span>•</span>
        <span className="text-xs">Cập nhật: {collection.updated_at}</span>
        <span>•</span>
        <span className="text-xs font-medium text-foreground">
          {documentCount} văn bản ({collection.chunk_count} chunks)
        </span>
        {reindexJobId && (
          <span className="text-xs text-emerald-600 font-semibold ml-auto flex items-center gap-1">
            <CheckCircle2 className="size-3.5" /> Đã tạo job reindex ({reindexJobId}) — theo dõi ở
            tab Tác vụ!
          </span>
        )}
      </div>

      {actionError && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/30 text-xs text-destructive leading-relaxed">
          <CircleAlert className="size-4 shrink-0 mt-0.5" />
          <span>{actionError}</span>
        </div>
      )}
    </div>
  );
}
