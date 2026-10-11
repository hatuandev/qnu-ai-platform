import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  Cpu,
  FileCheck2,
  FolderGit2,
  FolderPlus,
  Layers,
  MoreHorizontal,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import type React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useVectorWorkflow } from "@/features/knowledge/components/use-vector-workflow";
import type {
  CollectionSummaryMetrics,
  KnowledgeCollection,
} from "@/types/knowledge";

interface CollectionHeaderProps {
  collection: KnowledgeCollection;
  metrics?: CollectionSummaryMetrics | null;
  onBack: () => void;
  onAddSource: () => void;
  onOpenConfig?: () => void;
  onOpenExcelImport?: () => void;
}

export const CollectionHeader: React.FC<CollectionHeaderProps> = ({
  collection,
  onBack,
  onAddSource,
  onOpenConfig,
  onOpenExcelImport,
}) => {
  const { sources, generations, state } = useVectorWorkflow(collection.id);
  const activeGeneration = generations.data?.find(
    (generation) => generation.status === "active",
  );
  const published = (sources.data || []).filter((source) =>
    state.data?.indexes.some(
      (index) =>
        index.id === source.active_index_revision_id &&
        index.vector_generation_id === activeGeneration?.id,
    ),
  );
  const activeChunks = published.reduce(
    (total, source) =>
      total +
      (state.data?.indexes.find(
        (index) => index.id === source.active_index_revision_id,
      )?.chunk_count || 0),
    0,
  );
  const needsIndex = (sources.data || []).filter(
    (source) =>
      !state.data?.indexes.some(
        (index) =>
          index.id === source.active_index_revision_id &&
          index.source_revision_v2_id === source.active_source_revision_id &&
          index.vector_generation_id === activeGeneration?.id,
      ),
  ).length;
  const isKnown =
    !!sources.data &&
    !!state.data &&
    !!generations.data &&
    !sources.isError &&
    !state.isError &&
    !generations.isError;
  // Model embedding name without fake hardcoding
  const configuredModel = activeGeneration?.embedding_model;
  const embeddingModelDisplay = configuredModel || "Chưa xuất bản chỉ mục";

  // Business Status badge based on real metrics
  const status: CollectionSummaryMetrics["collection_status"] = !isKnown
    ? "pending"
    : !sources.data?.length
      ? "empty"
      : state.data?.jobs.some((job) =>
            ["queued", "running"].includes(job.status),
          )
        ? "syncing"
        : published.length
          ? needsIndex
            ? "updates_available"
            : "ready"
          : "pending";

  const renderStatusBadge = () => {
    switch (status) {
      case "ready":
        return (
          <Badge
            variant="outline"
            className="bg-success/10 text-success border-success/30 font-medium text-xs py-0 gap-1"
          >
            <CheckCircle2 className="size-3" />
            Sẵn sàng
          </Badge>
        );
      case "updates_available":
        return (
          <Badge
            variant="outline"
            className="bg-warning/10 text-warning border-warning/30 font-medium text-xs py-0 gap-1"
          >
            <Sparkles className="size-3" />
            Có cập nhật
          </Badge>
        );
      case "syncing":
        return (
          <Badge
            variant="outline"
            className="bg-primary/10 text-primary border-primary/30 font-medium text-xs py-0 gap-1"
          >
            <RefreshCw className="size-3 animate-spin" />
            Đang đồng bộ
          </Badge>
        );
      case "pending":
        return (
          <Badge
            variant="outline"
            className="bg-muted text-muted-foreground border-border font-medium text-xs py-0 gap-1"
          >
            <Clock className="size-3" />
            {isKnown ? "Chờ nạp / xuất bản" : "Đang tải"}
          </Badge>
        );
      default:
        return (
          <Badge
            variant="outline"
            className="bg-muted text-muted-foreground border-border font-medium text-xs py-0"
          >
            Trống
          </Badge>
        );
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-3 sm:p-5 shadow-2xs space-y-3">
      {/* Top Header Section */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="flex flex-col sm:flex-row sm:items-center gap-2.5 min-w-0">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onBack}
              className="h-8 px-2.5 rounded-md shrink-0 text-muted-foreground hover:text-foreground text-xs gap-1.5"
              title="Quay lại danh sách kho tri thức"
              aria-label="Quay lại danh sách kho tri thức"
            >
              <ArrowLeft className="size-3.5" />
              <span>Kho</span>
            </Button>

            <div className="flex items-center gap-1.5 sm:hidden">
              {renderStatusBadge()}
              <span className="font-mono text-[11px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                {collection.code}
              </span>
            </div>
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-sm sm:text-base md:text-lg font-bold text-foreground break-words leading-tight">
                {collection.name}
              </h1>
              <div className="hidden sm:flex items-center gap-1.5">
                {renderStatusBadge()}
                <span className="font-mono text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                  {collection.code}
                </span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
              {collection.description ||
                "Kho tri thức phục vụ tra cứu thông tin và phản hồi RAG của Trợ lý AI."}
            </p>
          </div>
        </div>

        {/* Action Button: ONLY ONE Primary CTA + Dropdown Menu */}
        <div className="flex items-center gap-2 w-full lg:w-auto shrink-0 justify-end">
          <Button
            size="sm"
            onClick={onAddSource}
            className="flex-1 sm:flex-initial h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 font-medium shadow-xs"
            title="Thêm nguồn từ Kho tài liệu"
          >
            <FolderPlus className="size-3.5" />
            <span>Thêm nguồn</span>
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                title="Tác vụ khác"
              >
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="text-xs">
              {onOpenExcelImport && (
                <DropdownMenuItem onClick={onOpenExcelImport}>
                  Nhập số liệu Excel
                </DropdownMenuItem>
              )}
              {onOpenConfig && (
                <DropdownMenuItem onClick={onOpenConfig}>
                  Cấu hình Kho tri thức
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* KPI Metrics Chips bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 border-t border-border/50 text-xs">
        <div className="flex items-center gap-2 p-2 rounded-md bg-muted/30">
          <FolderGit2 className="size-4 text-primary shrink-0" />
          <div className="min-w-0">
            <div className="text-[11px] text-muted-foreground truncate">
              Nguồn tài liệu
            </div>
            <div className="font-semibold text-foreground">
              {isKnown ? sources.data?.length : "—"}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 p-2 rounded-md bg-muted/30">
          <FileCheck2 className="size-4 text-success shrink-0" />
          <div className="min-w-0">
            <div className="text-[11px] text-muted-foreground truncate">
              Đã xuất bản
            </div>
            <div className="font-semibold text-foreground">
              {isKnown ? published.length : "—"}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 p-2 rounded-md bg-muted/30">
          <RefreshCw
            className={`size-4 shrink-0 ${needsIndex > 0 ? "text-warning" : "text-muted-foreground"}`}
          />
          <div className="min-w-0">
            <div className="text-[11px] text-muted-foreground truncate">
              Chưa xuất bản bản mới
            </div>
            <div
              className={`font-semibold ${needsIndex > 0 ? "text-warning font-bold" : "text-foreground"}`}
            >
              {isKnown ? needsIndex : "—"}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 p-2 rounded-md bg-muted/30">
          <Layers className="size-4 text-primary shrink-0" />
          <div className="min-w-0">
            <div className="text-[11px] text-muted-foreground truncate">
              Chunks hoạt động
            </div>
            <div className="font-semibold text-foreground">
              {isKnown ? activeChunks : "—"}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Embedding Model Info Chip */}
      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground pt-0.5">
        <Cpu className="size-3 text-muted-foreground" />
        <span>Mô hình Vector:</span>
        <span className="font-medium text-foreground">
          {embeddingModelDisplay}
        </span>
      </div>
    </div>
  );
};
