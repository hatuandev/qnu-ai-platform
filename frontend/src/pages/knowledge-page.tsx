import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Cpu,
  FileText,
  Plus,
  RefreshCw,
  Settings,
  Terminal,
  Trash2,
  Upload,
  Zap,
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useState } from "react";
import { DebouncedSearchInput } from "../components/admin/debounced-search-input";
import { KpiMetric } from "../components/admin/kpi-metric";
import { PageHeader } from "../components/admin/page-header";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { cn } from "../lib/utils";
import { type IngestionTask, apiClient } from "../services/api-client";
import { CollectionDetailPage } from "./collection-detail-page";

export interface KnowledgePageProps {
  currentPath?: string;
  onNavigate?: (path: string) => void;
}

export const KnowledgePage: React.FC<KnowledgePageProps> = ({ currentPath, onNavigate }) => {
  const queryClient = useQueryClient();

  // Parse path for Deep Linking
  // Examples:
  // /knowledge/collections/col_admissions/ingest
  // /knowledge/collections/col_admissions/verify/doc_ts_2026
  // /knowledge/collections/col_admissions
  const pathInfo = useMemo(() => {
    if (!currentPath || currentPath === "/knowledge" || currentPath === "/document-types") {
      return { collectionId: null, subView: "list" as const, docId: undefined };
    }

    if (currentPath.includes("/collections/")) {
      const parts = currentPath.split("/collections/")[1].split("/");
      const colId = parts[0] || null;
      if (parts[1] === "ingest") {
        return { collectionId: colId, subView: "ingest" as const, docId: undefined };
      }
      if (parts[1] === "verify") {
        return {
          collectionId: colId,
          subView: "verify" as const,
          docId: parts[2] || undefined,
        };
      }
      return { collectionId: colId, subView: "list" as const, docId: undefined };
    }

    // fallback for /knowledge/:id
    if (currentPath.startsWith("/knowledge/")) {
      const id = currentPath.replace("/knowledge/", "").trim();
      return { collectionId: id || null, subView: "list" as const, docId: undefined };
    }

    return { collectionId: null, subView: "list" as const, docId: undefined };
  }, [currentPath]);

  const [selectedCollectionId, setSelectedCollectionId] = useState<string | null>(
    pathInfo.collectionId
  );
  const [activeTab, setActiveTab] = useState<"collections" | "tasks">("collections");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedTaskLog, setSelectedTaskLog] = useState<IngestionTask | null>(null);

  // Keep state in sync with URL
  useEffect(() => {
    setSelectedCollectionId(pathInfo.collectionId);
  }, [pathInfo.collectionId]);

  // Fetch collections
  const { data: collections = [] } = useQuery({
    queryKey: ["collections"],
    queryFn: () => apiClient.getCollections(),
  });

  // Fetch tasks
  const { data: allTasks = [] } = useQuery({
    queryKey: ["ingestion-tasks"],
    queryFn: () => apiClient.getIngestionTasks(),
  });

  // Fetch system-wide model defaults (Embedding, Reranker, OCR)
  const { data: systemDefaultsResponse } = useQuery({
    queryKey: ["system-model-defaults"],
    queryFn: () => apiClient.getSystemModelDefaults(),
    staleTime: 30000,
  });
  const systemDefaults = systemDefaultsResponse?.defaults;

  // Total summary metrics
  const totalDocs = useMemo(() => {
    return collections.reduce((acc, c) => acc + (c.document_count || 0), 0);
  }, [collections]);

  const totalChunks = useMemo(() => {
    return collections.reduce((acc, c) => acc + (c.chunk_count || 0), 0);
  }, [collections]);

  // Filtered collections
  const filteredCollections = useMemo(() => {
    if (!searchQuery.trim()) return collections;
    const q = searchQuery.toLowerCase();
    return collections.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.code.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q)
    );
  }, [collections, searchQuery]);

  const handleSelectCollection = (colId: string) => {
    setSelectedCollectionId(colId);
    const targetUrl = `/knowledge/collections/${colId}`;
    if (onNavigate) {
      onNavigate(targetUrl);
    } else {
      window.history.pushState({}, "", targetUrl);
    }
  };

  const handleBackToList = () => {
    setSelectedCollectionId(null);
    const targetUrl = "/knowledge";
    if (onNavigate) {
      onNavigate(targetUrl);
    } else {
      window.history.pushState({}, "", targetUrl);
    }
  };

  // IF A COLLECTION IS SELECTED: Render Dedicated Detail Page
  if (selectedCollectionId) {
    return (
      <CollectionDetailPage
        collectionId={selectedCollectionId}
        onBack={handleBackToList}
        onNavigate={onNavigate}
        initialSubView={pathInfo.subView}
        initialVerifyDocId={pathInfo.docId}
      />
    );
  }

  // MASTER VIEW: Kho Tri Thức & Vector Collections Overview
  return (
    <div className="space-y-6 pb-10">
      {/* 1. Page Header Chuẩn QLKTX */}
      <PageHeader
        eyebrow="Kho Tri Thức / RAG Corpus"
        title="Kho Tri Thức & Vector Collections"
        description="Quản trị kho vector Qdrant, giám sát tác vụ bóc tách tài liệu và cấu hình Embedding ModelOps phục vụ Trợ lý AI RAG."
        actions={
          <Button
            size="sm"
            className="gap-1.5"
            onClick={() => {
              // Dialog mở tạo kho mới nếu có
            }}
          >
            <Plus className="size-4" />
            Khởi tạo Kho Mới
          </Button>
        }
      />

      {/* 2. Dải Thống kê Kho Tri thức (Summary Strip) Chuẩn QLKTX */}
      <Card>
        <CardContent className="grid p-0 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            label="Tổng Bộ Sưu Tập"
            value={collections.length}
            delta="Kho"
            helper="Cơ sở tri thức số hóa"
            icon={BookOpen}
          />
          <KpiMetric
            label="Tổng Văn Bản"
            value={totalDocs}
            delta="Tài liệu"
            helper="PDF, DOCX, Quyết định"
            icon={FileText}
          />
          <KpiMetric
            label="Tổng Vector Chunks"
            value={totalChunks}
            delta="Đoạn vector"
            helper="Qdrant dense vector 1024d"
            icon={Cpu}
          />
          <KpiMetric
            label="Tác Vụ Hoạt Động"
            value={allTasks.length}
            delta="Tác vụ"
            helper="Ingestion & OCR pipeline"
            icon={Activity}
          />
        </CardContent>
      </Card>

      {/* Model mặc định hệ thống */}
      {systemDefaults && (
        <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-lg border border-border/70 bg-card text-xs text-muted-foreground flex-wrap shadow-2xs">
          <span className="font-medium text-foreground">Model mặc định hệ thống:</span>
          <span className="inline-flex items-center gap-1 font-mono text-[11px] text-foreground bg-muted px-2 py-0.5 rounded border border-border/50">
            {systemDefaults.default_embedding_model.includes("@cf/") ? (
              <Zap className="size-3 text-warning" />
            ) : (
              <Cpu className="size-3 text-primary" />
            )}
            {systemDefaults.default_embedding_model}
          </span>
          <span className="text-muted-foreground">•</span>
          <span className="inline-flex items-center gap-1 font-mono text-[11px] text-muted-foreground">
            Reranker: {systemDefaults.default_reranker_model}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onNavigate?.("/models")}
            className="h-6 px-2 text-xs text-primary hover:text-primary/80 gap-1 ml-auto"
          >
            <Settings className="size-3" />
            <span>Quản lý ModelOps</span>
          </Button>
        </div>
      )}

      {/* 2. Sub-Navigation Tabs Chuẩn QLKTX */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-1 p-1 rounded-lg bg-muted/60 border border-border/60">
          <button
            type="button"
            onClick={() => setActiveTab("collections")}
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer",
              activeTab === "collections"
                ? "bg-background text-foreground shadow-2xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <BookOpen className="size-3.5 text-primary" />
            <span>Kho Tri thức ({collections.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("tasks")}
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer",
              activeTab === "tasks"
                ? "bg-background text-foreground shadow-2xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Activity className="size-3.5 text-primary" />
            <span>Tác vụ Nền & Bóc tách ({allTasks.length})</span>
          </button>
        </div>
      </div>

      {/* 3. TAB 1: KHO TRI THỨC GRID */}
      {activeTab === "collections" && (
        <div className="space-y-4">
          {/* Search Filter Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="w-full sm:w-96">
              <DebouncedSearchInput
                placeholder="Tìm theo tên kho, mã Qdrant collection..."
                value={searchQuery}
                onChange={(val) => setSearchQuery(val)}
              />
            </div>
            <span className="type-caption text-muted-foreground">
              Hiển thị {filteredCollections.length} / {collections.length} Kho Tri thức
            </span>
          </div>

          {/* Card Grid 3 Cột */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredCollections.map((col) => (
              <Card
                key={col.id}
                className="flex flex-col justify-between border-border hover:border-primary/50 transition-all rounded-lg bg-card shadow-2xs"
              >
                <div className="p-5 space-y-3">
                  {/* Card Header: Icon + Title + Status Badge */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <div className="flex size-8 items-center justify-center rounded-md bg-primary/10 text-primary shrink-0">
                        <BookOpen className="size-4" />
                      </div>
                      <div>
                        <h2 className="text-sm font-semibold text-foreground leading-snug">
                          {col.name}
                        </h2>
                        <span className="font-mono text-[11px] text-muted-foreground block mt-0.5">
                          {col.code}
                        </span>
                      </div>
                    </div>
                    <Badge
                      variant="outline"
                      className="bg-success/10 text-success border-success/30 text-[10px] font-medium shrink-0"
                    >
                      Sẵn sàng
                    </Badge>
                  </div>

                  {/* Description (2 lines clamp) */}
                  <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed min-h-[36px]">
                    {col.description}
                  </p>

                  {/* Model Embedding Chip */}
                  <div className="pt-1 flex items-center gap-1.5 flex-wrap">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-muted/60 text-muted-foreground text-[11px] font-mono border border-border/50">
                      {(
                        col.embedding_model ||
                        systemDefaults?.default_embedding_model ||
                        ""
                      ).includes("@cf/") ? (
                        <Zap className="size-3 text-warning shrink-0" />
                      ) : (
                        <Cpu className="size-3 text-primary shrink-0" />
                      )}
                      <span>
                        {col.embedding_model ||
                          systemDefaults?.default_embedding_model ||
                          "BAAI/bge-m3 (1024-dim)"}
                      </span>
                    </span>
                    {!col.embedding_model && systemDefaults?.default_embedding_model && (
                      <Badge
                        variant="outline"
                        className="text-[10px] px-1.5 py-0 border-primary/30 text-primary bg-primary/5"
                      >
                        Mặc định
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Card Footer: Metrics & Action Buttons */}
                <div className="flex items-center justify-between px-5 py-3 border-t border-border/60 bg-muted/10 text-xs">
                  <span className="font-medium text-foreground text-[11px]">
                    {col.document_count} văn bản • {col.chunk_count} chunks
                  </span>

                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-[11px] text-muted-foreground hover:text-foreground gap-1"
                    >
                      <RefreshCw className="size-3" />
                      <span>Reindex</span>
                    </Button>

                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7 text-destructive hover:text-destructive/80"
                    >
                      <Trash2 className="size-3" />
                    </Button>

                    <Button
                      size="sm"
                      onClick={() => handleSelectCollection(col.id)}
                      className="h-7 px-3 text-[11px] gap-1"
                    >
                      <span>Xem tài liệu</span>
                      <ArrowRight className="size-3" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}

            {/* Dashed Placeholder Card: Khởi tạo Kho Mới */}
            <div className="border-2 border-dashed border-border/80 hover:border-primary/60 transition-colors rounded-lg p-6 flex flex-col items-center justify-center text-center cursor-pointer bg-card/40 hover:bg-primary/5 min-h-[220px]">
              <div className="flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary mb-3">
                <Plus className="size-5" />
              </div>
              <h3 className="text-sm font-bold text-foreground">+ Khởi tạo Kho Tri thức Mới</h3>
              <p className="text-xs text-muted-foreground mt-1 max-w-xs">
                Tạo Qdrant Collection & cấu hình Embedding ModelOps
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 4. TAB 2: TÁC VỤ NỀN & BÓC TÁCH (All System Tasks) */}
      {activeTab === "tasks" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card p-4 rounded-lg border border-border">
            <div>
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                Hàng Đợi & Lịch Sử Tác Vụ Toàn Hệ Thống ({allTasks.length})
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Giám sát thời gian thực quá trình Bóc tách (Ingestion), OCR tài liệu và Tái lập chỉ
                mục (Reindex).
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => queryClient.invalidateQueries({ queryKey: ["ingestion-tasks"] })}
              className="h-8 text-xs gap-1.5"
            >
              <RefreshCw className="size-3.5" />
              <span>Làm mới</span>
            </Button>
          </div>

          <div className="bg-card rounded-lg border border-border overflow-hidden shadow-xs">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase">
                  <TableHead>Tác vụ & Tài nguyên mục tiêu</TableHead>
                  <TableHead>Kho tri thức</TableHead>
                  <TableHead>Phân loại</TableHead>
                  <TableHead>Tiến độ</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead>Thời điểm</TableHead>
                  <TableHead className="text-right">Thao tác</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {allTasks.map((t) => (
                  <TableRow key={t.id} className="hover:bg-muted/30 transition-colors">
                    <TableCell>
                      <div className="flex items-start gap-3">
                        <div className="flex size-8 items-center justify-center rounded bg-primary/10 text-primary shrink-0 mt-0.5">
                          <Upload className="size-4" />
                        </div>
                        <div>
                          <p className="font-semibold text-xs text-foreground">{t.task_name}</p>
                          <div className="flex items-center gap-2 text-[11px] text-muted-foreground font-mono mt-0.5">
                            <span>{t.source_file}</span>
                            <span>•</span>
                            <span>Worker: {t.worker_name}</span>
                            <span>•</span>
                            <span>{t.duration_seconds}s</span>
                          </div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-[10px]">
                        {t.collection_code}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs font-medium text-foreground">
                        {t.category === "ingestion"
                          ? "Nạp tài liệu"
                          : t.category === "ocr"
                            ? "OCR & Bóc tách"
                            : "Tái lập chỉ mục"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="w-24 space-y-1">
                        <div className="flex justify-between text-[11px] font-mono">
                          <span className="text-primary font-bold">{t.progress_percent}%</span>
                          <span className="text-muted-foreground">Xong</span>
                        </div>
                        <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary rounded-full"
                            style={{ width: `${t.progress_percent}%` }}
                          />
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className="bg-success/10 text-success border-success/30 text-[11px] gap-1"
                      >
                        <CheckCircle2 className="size-3" />
                        <span>Hoàn tất</span>
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-muted-foreground font-mono">
                        {t.created_at}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setSelectedTaskLog(t)}
                        className="size-7 font-mono text-xs text-muted-foreground hover:text-foreground"
                        title="Xem nhật ký Terminal"
                      >
                        <Terminal className="size-3.5" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {/* Terminal Log Modal */}
      <Dialog open={!!selectedTaskLog} onOpenChange={() => setSelectedTaskLog(null)}>
        <DialogContent className="max-w-2xl bg-slate-950 text-slate-100 font-mono text-xs">
          <DialogHeader>
            <DialogTitle className="text-sm font-mono text-primary flex items-center gap-2">
              <Terminal className="size-4" />
              <span>Worker Log: {selectedTaskLog?.worker_name}</span>
            </DialogTitle>
          </DialogHeader>
          <pre className="p-4 bg-slate-900 rounded border border-slate-800 text-[11px] leading-relaxed overflow-x-auto whitespace-pre-wrap">
            {selectedTaskLog?.log_output ||
              "[INFO] Tác vụ đã thực thi thành công không có cảnh báo."}
          </pre>
        </DialogContent>
      </Dialog>
    </div>
  );
};
