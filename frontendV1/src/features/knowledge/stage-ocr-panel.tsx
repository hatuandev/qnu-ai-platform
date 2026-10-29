import {
  ArrowLeft,
  ArrowRight,
  FileEdit,
  FileSpreadsheet,
  FileText,
  Play,
  ScanLine,
} from "lucide-react";
import { useMemo, useState } from "react";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { ErrorState } from "@/components/admin/error-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { OcrRequestDialog } from "@/features/knowledge/ocr-request-dialog";
import {
  type OcrSubTab,
  OcrTabContainer,
} from "@/features/knowledge/ocr-tab-container";
import {
  useRevisionsQuery,
  useSourceQuery,
  useSourcesQuery,
} from "@/features/knowledge/queries";
import { formatBytes, isDocx, isPdf } from "@/features/knowledge/schemas";
import type { KBRevision, KBSource } from "@/features/knowledge/types";
import { formatDateTimeValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

interface StageOcrPanelProps {
  workspaceId: string;
  collectionId: string;
  canManage: boolean;
  selectedSourceId?: string | null;
  onSelectSourceId?: (sourceId: string | null) => void;
  onProceedToCompiler?: () => void;
}

export function StageOcrPanel({
  workspaceId,
  collectionId,
  canManage,
  selectedSourceId: initialSelectedSourceId,
  onSelectSourceId,
  onProceedToCompiler,
}: StageOcrPanelProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  // Sources in the collection
  const sourcesQuery = useSourcesQuery(workspaceId, collectionId, {
    page,
    pageSize,
    allFolders: true,
  });

  const sources = sourcesQuery.data?.items ?? [];

  // Local selection state
  const [internalSelectedId, setInternalSelectedId] = useState<string | null>(
    initialSelectedSourceId ?? null,
  );
  const activeSourceId = onSelectSourceId
    ? initialSelectedSourceId
    : internalSelectedId;
  const sourceQuery = useSourceQuery(
    workspaceId,
    collectionId,
    activeSourceId ?? "",
  );

  const handleSelectSource = (id: string | null) => {
    setInternalSelectedId(id);
    onSelectSourceId?.(id);
  };

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | "pdf" | "docx">("all");

  // Selected source object
  const activeSource =
    sourceQuery.data ??
    sources.find((source) => source.id === activeSourceId) ??
    null;

  // Request OCR Dialog state for a specific source
  const [ocrDialogOpen, setOcrDialogOpen] = useState(false);
  const [sourceForOcr, setSourceForOcr] = useState<KBSource | null>(null);

  // Filtered sources
  const filteredSources = useMemo(() => {
    return sources.filter((s) => {
      const matchesSearch =
        !searchQuery.trim() ||
        s.title.toLowerCase().includes(searchQuery.toLowerCase().trim()) ||
        s.file_name.toLowerCase().includes(searchQuery.toLowerCase().trim());

      const pdf = isPdf(s.content_type, s.file_name);
      const docx = isDocx(s.content_type, s.file_name);

      const matchesType =
        typeFilter === "all" ||
        (typeFilter === "pdf" && pdf) ||
        (typeFilter === "docx" && docx);

      return matchesSearch && matchesType;
    });
  }, [sources, searchQuery, typeFilter]);

  // Total stats
  const pdfCount = useMemo(
    () => sources.filter((s) => isPdf(s.content_type, s.file_name)).length,
    [sources],
  );
  const docxCount = useMemo(
    () => sources.filter((s) => isDocx(s.content_type, s.file_name)).length,
    [sources],
  );

  // If a source is selected, render the full Studio Workspace
  if (sourcesQuery.isError || (activeSourceId && sourceQuery.isError)) {
    const failed =
      activeSourceId && sourceQuery.isError ? sourceQuery : sourcesQuery;
    return (
      <ErrorState error={failed.error} onRetry={() => void failed.refetch()} />
    );
  }
  if (activeSourceId && sourceQuery.isLoading)
    return <Skeleton className="h-64 w-full" />;
  if (activeSourceId && !activeSource)
    return (
      <div className="space-y-3">
        <p>Không tìm thấy tài liệu đã chọn.</p>
        <Button onClick={() => handleSelectSource(null)}>Về danh sách</Button>
      </div>
    );
  if (activeSource) {
    return (
      <OcrStudioWorkspace
        key={activeSource.id}
        workspaceId={workspaceId}
        collectionId={collectionId}
        source={activeSource}
        canManage={canManage}
        onBack={() => handleSelectSource(null)}
        onProceedToCompiler={onProceedToCompiler}
      />
    );
  }

  // Otherwise, render the Master OCR Queue & Document Table
  return (
    <div className="space-y-5">
      {/* 1. Header & Summary Cards (Chuẩn KpiMetric) */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={ScanLine}
            label="Tổng tài liệu bóc tách"
            value={(sourcesQuery.data?.meta.total ?? 0).toLocaleString("vi-VN")}
          />
          <KpiMetric
            icon={FileText}
            label="PDF trên trang"
            value={pdfCount.toLocaleString("vi-VN")}
            trend="positive"
          />
          <KpiMetric
            icon={FileSpreadsheet}
            label="DOCX trên trang"
            value={docxCount.toLocaleString("vi-VN")}
          />
        </CardContent>
      </Card>

      {/* 2. Search & Filter Bar */}
      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between rounded-xl border bg-card p-3 shadow-2xs">
        <div className="w-full sm:w-72">
          <DebouncedSearchInput
            value={searchQuery}
            onChange={setSearchQuery}
            placeholder="Tìm trong trang này..."
            className="text-xs h-8"
          />
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <Button
            size="sm"
            variant={typeFilter === "all" ? "default" : "outline"}
            className="h-8 text-xs px-2.5"
            onClick={() => setTypeFilter("all")}
          >
            Tất cả ({sources.length})
          </Button>
          <Button
            size="sm"
            variant={typeFilter === "pdf" ? "default" : "outline"}
            className="h-8 text-xs px-2.5 gap-1"
            onClick={() => setTypeFilter("pdf")}
          >
            <span className="size-1.5 rounded-full bg-rose-500" />
            <span>PDF ({pdfCount})</span>
          </Button>
          <Button
            size="sm"
            variant={typeFilter === "docx" ? "default" : "outline"}
            className="h-8 text-xs px-2.5 gap-1"
            onClick={() => setTypeFilter("docx")}
          >
            <span className="size-1.5 rounded-full bg-blue-500" />
            <span>DOCX ({docxCount})</span>
          </Button>
        </div>
      </div>

      {/* 3. Document Table */}
      {sourcesQuery.isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full rounded-xl" />
          <Skeleton className="h-12 w-full rounded-xl" />
          <Skeleton className="h-12 w-full rounded-xl" />
        </div>
      ) : filteredSources.length === 0 ? (
        <Card className="rounded-xl border border-dashed p-10 text-center space-y-3">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-muted mx-auto text-muted-foreground">
            <ScanLine className="size-6" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-foreground">
              {searchQuery
                ? "Không tìm thấy tài liệu phù hợp"
                : "Chưa có tài liệu nào trong kho"}
            </p>
            <p className="text-xs text-muted-foreground max-w-sm mx-auto">
              {searchQuery
                ? "Vui lòng kiểm tra lại từ khóa tìm kiếm hoặc bộ lọc định dạng."
                : "Hãy quay lại Chặng 1 để tải tài liệu lên trước khi thực hiện OCR và hiệu đính."}
            </p>
          </div>
        </Card>
      ) : (
        <Card className="rounded-xl shadow-2xs overflow-hidden border-border/80">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40">
                <TableHead className="w-[40%]">
                  Tên tài liệu & Định dạng
                </TableHead>
                <TableHead className="w-[12%] text-center">Phiên bản</TableHead>
                <TableHead className="w-[15%]">Kích thước</TableHead>
                <TableHead className="w-[15%]">Cập nhật</TableHead>
                <TableHead className="w-[18%] text-right">Thao tác</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredSources.map((s) => {
                const pdf = isPdf(s.content_type, s.file_name);
                const docx = isDocx(s.content_type, s.file_name);

                return (
                  <TableRow key={s.id} className="group hover:bg-muted/30">
                    <TableCell>
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div
                          className={cn(
                            "flex size-8 shrink-0 items-center justify-center rounded-lg border",
                            pdf
                              ? "bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-950/40 dark:border-rose-800"
                              : docx
                                ? "bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-950/40 dark:border-blue-800"
                                : "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-800",
                          )}
                        >
                          {pdf ? (
                            <FileText className="size-4" />
                          ) : docx ? (
                            <FileSpreadsheet className="size-4" />
                          ) : (
                            <FileText className="size-4" />
                          )}
                        </div>
                        <div className="min-w-0 flex-1">
                          <button
                            type="button"
                            onClick={() => handleSelectSource(s.id)}
                            className="text-xs font-semibold text-foreground hover:text-primary transition-colors truncate block text-left w-full cursor-pointer"
                          >
                            {s.title}
                          </button>
                          <p className="text-[11px] text-muted-foreground truncate">
                            {s.file_name}
                          </p>
                        </div>
                      </div>
                    </TableCell>

                    <TableCell className="text-center">
                      <Badge
                        variant="outline"
                        className="text-[10px] font-mono px-1.5 py-0"
                      >
                        v{s.current_revision_no}
                      </Badge>
                    </TableCell>

                    <TableCell className="text-xs text-muted-foreground">
                      {formatBytes(s.size_bytes)}
                    </TableCell>

                    <TableCell className="text-xs text-muted-foreground">
                      {formatDateTimeValue(s.updated_at)}
                    </TableCell>

                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {/* Nút chính: Mở Studio Hiệu đính */}
                        <Button
                          size="sm"
                          className="h-7 px-2.5 text-xs gap-1 shadow-xs"
                          onClick={() => handleSelectSource(s.id)}
                        >
                          <FileEdit className="size-3.5" />
                          <span>Hiệu đính</span>
                        </Button>

                        {/* Nút kích hoạt lượt OCR */}
                        {canManage && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 px-2 text-xs gap-1 text-muted-foreground hover:text-foreground"
                            title="Yêu cầu bóc tách OCR"
                            onClick={() => {
                              setSourceForOcr(s);
                              setOcrDialogOpen(true);
                            }}
                          >
                            <Play className="size-3" />
                            <span className="hidden sm:inline">Chạy OCR</span>
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Card>
      )}

      <DataTablePagination
        page={page}
        pageSize={pageSize}
        pageCount={Math.max(
          1,
          Math.ceil((sourcesQuery.data?.meta.total ?? 0) / pageSize),
        )}
        total={sourcesQuery.data?.meta.total ?? 0}
        onPageChange={setPage}
        onPageSizeChange={(size) => {
          setPageSize(size);
          setPage(1);
        }}
      />
      {/* Dialog kích hoạt bóc tách OCR */}
      {sourceForOcr && (
        <OcrSourceTriggerDialog
          workspaceId={workspaceId}
          collectionId={collectionId}
          source={sourceForOcr}
          isOpen={ocrDialogOpen}
          onClose={() => {
            setOcrDialogOpen(false);
            setSourceForOcr(null);
          }}
          onSuccess={() => {
            // Khi trigger xong, tự động mở thẳng Studio hiệu đính cho source đó
            handleSelectSource(sourceForOcr.id);
          }}
        />
      )}
    </div>
  );
}

/**
 * Bàn làm việc Hiệu đính Studio toàn diện cho 1 tài liệu
 */
function OcrStudioWorkspace({
  workspaceId,
  collectionId,
  source,
  canManage,
  onBack,
  onProceedToCompiler,
}: {
  workspaceId: string;
  collectionId: string;
  source: KBSource;
  canManage: boolean;
  onBack: () => void;
  onProceedToCompiler?: () => void;
}) {
  const revisionsQuery = useRevisionsQuery(
    workspaceId,
    collectionId,
    source.id,
  );
  const revisions = revisionsQuery.data ?? [];

  const [selectedRevisionId, setSelectedRevisionId] = useState<string | null>(
    null,
  );
  const [subTab, setSubTab] = useState<OcrSubTab>("review");

  const activeRevision = useMemo<KBRevision | undefined>(() => {
    if (selectedRevisionId) {
      return revisions.find((r) => r.id === selectedRevisionId) ?? revisions[0];
    }
    return revisions[0];
  }, [revisions, selectedRevisionId]);

  if (revisionsQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96 w-full rounded-xl" />
      </div>
    );
  }

  if (revisionsQuery.isError)
    return (
      <ErrorState
        error={revisionsQuery.error}
        onRetry={() => void revisionsQuery.refetch()}
      />
    );

  if (!activeRevision) {
    return (
      <Card className="p-8 text-center space-y-3 rounded-xl border-dashed">
        <p className="text-sm font-medium text-foreground">
          Không tìm thấy phiên bản tệp để hiệu đính.
        </p>
        <Button size="sm" variant="outline" onClick={onBack}>
          <ArrowLeft className="size-4 mr-1" />
          Quay lại danh sách tài liệu
        </Button>
      </Card>
    );
  }

  const pdf = isPdf(source.content_type, source.file_name);
  const docx = isDocx(source.content_type, source.file_name);

  return (
    <div className="space-y-4">
      {/* Thanh điều hướng quay lại & Tiêu đề Studio */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-xl border bg-card p-3.5 shadow-2xs">
        <div className="flex items-center gap-3 min-w-0">
          <Button
            size="sm"
            variant="outline"
            className="h-8 px-2.5 text-xs gap-1.5 shrink-0"
            onClick={onBack}
          >
            <ArrowLeft className="size-3.5" />
            <span>Danh sách OCR</span>
          </Button>

          <div className="h-5 w-px bg-border/70 shrink-0" />

          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-sm sm:text-base font-bold text-foreground truncate max-w-md">
                {source.title}
              </h2>
              {revisions.length > 1 ? (
                <select
                  value={activeRevision.id}
                  onChange={(e) => setSelectedRevisionId(e.target.value)}
                  className="text-[10px] font-mono h-5 rounded border border-input bg-background px-1"
                >
                  {revisions.map((r) => (
                    <option key={r.id} value={r.id}>
                      v{r.revision_no}
                    </option>
                  ))}
                </select>
              ) : (
                <Badge
                  variant="outline"
                  className="text-[10px] font-mono h-4.5"
                >
                  v{activeRevision.revision_no}
                </Badge>
              )}
              <Badge
                variant="secondary"
                className={cn(
                  "text-[10px] h-4.5",
                  pdf
                    ? "text-rose-600"
                    : docx
                      ? "text-blue-600"
                      : "text-emerald-600",
                )}
              >
                {pdf ? "PDF" : docx ? "DOCX" : "Khác"}
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground truncate">
              {source.file_name}
            </p>
          </div>
        </div>

        {/* Chuyển sang Chặng 3: Biên soạn */}
        {onProceedToCompiler && (
          <Button
            size="sm"
            className="h-8 px-3 text-xs gap-1.5 shadow-xs shrink-0 bg-primary"
            onClick={onProceedToCompiler}
          >
            <span>Tiến tới Chặng 3: Biên soạn</span>
            <ArrowRight className="size-3.5" />
          </Button>
        )}
      </div>

      {/* Khung làm việc đầy đủ 4 tab: Review văn bản, Đối soát scan, Bảng biểu, Lịch sử run */}
      <OcrTabContainer
        workspaceId={workspaceId}
        collectionId={collectionId}
        sourceId={source.id}
        revisionId={activeRevision.id}
        revisionNo={activeRevision.revision_no}
        fileName={source.file_name}
        contentType={source.content_type}
        canManage={canManage}
        initialSubTab={subTab}
        onDeepLinkChange={(params) => {
          if (params.subTab) setSubTab(params.subTab);
        }}
      />
    </div>
  );
}

/**
 * Trợ thủ kích hoạt OCR nhanh khi người dùng click "Chạy OCR" trên danh sách
 */
function OcrSourceTriggerDialog({
  workspaceId,
  collectionId,
  source,
  isOpen,
  onClose,
  onSuccess,
}: {
  workspaceId: string;
  collectionId: string;
  source: KBSource;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (runId: string) => void;
}) {
  const revisionsQuery = useRevisionsQuery(
    workspaceId,
    collectionId,
    source.id,
  );
  const revisions = revisionsQuery.data ?? [];
  const activeRevision = revisions.find(
    (revision) => revision.revision_no === source.current_revision_no,
  );

  if (!isOpen) return null;
  if (!activeRevision || revisionsQuery.isError)
    return (
      <ResponsiveDialog
        open
        onOpenChange={(open) => {
          if (!open) onClose();
        }}
      >
        <ResponsiveDialogContent>
          <ResponsiveDialogTitle>Yêu cầu OCR</ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            {source.title}
          </ResponsiveDialogDescription>
          {revisionsQuery.isError ? (
            <ErrorState
              error={revisionsQuery.error}
              onRetry={() => void revisionsQuery.refetch()}
            />
          ) : (
            <p>
              {revisionsQuery.isLoading
                ? "Đang tải phiên bản tệp…"
                : "Không tìm thấy phiên bản tệp hiện tại. Hãy tải lại danh sách."}
            </p>
          )}
          <Button variant="outline" onClick={onClose}>
            Đóng
          </Button>
        </ResponsiveDialogContent>
      </ResponsiveDialog>
    );

  return (
    <OcrRequestDialog
      workspaceId={workspaceId}
      collectionId={collectionId}
      sourceId={source.id}
      revisionId={activeRevision.id}
      revisionNo={activeRevision.revision_no}
      fileName={source.file_name}
      isOpen={isOpen}
      onClose={onClose}
      onSuccess={onSuccess}
    />
  );
}
