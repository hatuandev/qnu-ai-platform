import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  CheckCircle2,
  CircleAlert,
  Download,
  Eye,
  FileText,
  RefreshCw,
  RotateCcw,
  Scan,
  Search,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import { useMemo, useState } from "react";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { formatFileSize, STATUS_BADGE } from "@/components/knowledge/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { KnowledgeDocument } from "@/types";

interface CollectionDocumentsTabProps {
  documents: KnowledgeDocument[];
  totalDocumentsCount?: number;
  searchQuery: string;
  onSearchChange: (val: string) => void;
  typeFilter: string;
  onTypeFilterChange: (val: string) => void;
  statusFilter: string;
  onStatusFilterChange: (val: string) => void;
  priorityFilter: string;
  onPriorityFilterChange: (val: string) => void;
  reindexingDocId: string | null;
  downloadingId: string | null;
  onReindexDoc: (docId: string) => void;
  onStartVerify: (docId: string) => void;
  onPreviewDoc: (doc: KnowledgeDocument) => void;
  onDownloadDoc: (doc: KnowledgeDocument) => void;
  onDeleteDoc: (doc: KnowledgeDocument) => void;
  onQuickApprove?: (docId: string) => Promise<void> | void;
  onBatchApprove?: (docIds: string[]) => Promise<void> | void;
  onBatchDelete?: (docIds: string[]) => Promise<void> | void;
}

function formatDocumentType(typeOrCode?: string): string {
  if (!typeOrCode) return "Văn bản";
  const map: Record<string, string> = {
    thong_bao: "Thông báo",
    quy_che: "Quy chế",
    de_an: "Đề án",
    de_an_tuyen_sinh: "Đề án tuyển sinh",
    quyet_dinh: "Quyết định",
    ke_hoach: "Kế hoạch",
    cong_van: "Công văn",
    hop_dong: "Hợp đồng",
    to_trinh: "Tờ trình",
    bien_ban: "Biên bản",
    huong_dan: "Hướng dẫn",
    thong_tu: "Thông tư",
    nghi_dinh: "Nghị định",
    nghi_quyet: "Nghị quyết",
    luat: "Luật",
    giao_trinh: "Giáo trình",
    tai_lieu: "Tài liệu",
    quy_dinh: "Quy định",
    chuong_trinh: "Chương trình",
  };
  return (
    map[typeOrCode.toLowerCase()] ||
    typeOrCode.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

const PRIORITY_LABELS: Record<string, string> = {
  core: "Cốt lõi",
  high: "Bổ trợ",
  normal: "Tham khảo",
};

function getCleanMetadata(doc: {
  title?: string;
  filename?: string;
  file_size?: number;
  version?: string;
}) {
  const titleNorm = (doc.title || "").trim().toLowerCase();
  const rawFilename = (doc.filename || "").trim();
  const filenameWithoutExt = rawFilename
    .replace(/\.[^/.]+$/, "")
    .trim()
    .toLowerCase();
  const ext = rawFilename.includes(".")
    ? rawFilename.split(".").pop()?.toUpperCase()
    : null;
  const isRedundant = Boolean(
    titleNorm &&
      (titleNorm === filenameWithoutExt ||
        titleNorm === rawFilename.toLowerCase()),
  );

  return {
    showFilename: !isRedundant && Boolean(rawFilename),
    filename: rawFilename,
    ext,
    fileSize: formatFileSize(doc.file_size || 0),
    version: doc.version || "v1.0",
  };
}

export type SortField =
  | "title"
  | "document_type"
  | "chunk_count"
  | "status"
  | "file_size"
  | "created_at";

export type SortOrder = "asc" | "desc";

export function CollectionDocumentsTab({
  documents,
  totalDocumentsCount: _totalDocumentsCount,
  searchQuery,
  onSearchChange,
  typeFilter,
  onTypeFilterChange,
  statusFilter,
  onStatusFilterChange,
  priorityFilter,
  onPriorityFilterChange,
  reindexingDocId,
  downloadingId,
  onReindexDoc,
  onStartVerify,
  onPreviewDoc,
  onDownloadDoc,
  onDeleteDoc,
  onQuickApprove,
  onBatchApprove,
  onBatchDelete,
}: CollectionDocumentsTabProps) {
  const [selectedDocIds, setSelectedDocIds] = useState<Set<string>>(new Set());
  const [isBatchActionRunning, setIsBatchActionRunning] =
    useState<boolean>(false);
  const [quickApprovingId, setQuickApprovingId] = useState<string | null>(null);

  const hasActiveFilters = Boolean(
    searchQuery ||
      typeFilter !== "all" ||
      statusFilter !== "all" ||
      priorityFilter !== "all",
  );

  const handleResetFilters = () => {
    onSearchChange("");
    onTypeFilterChange("all");
    onStatusFilterChange("all");
    onPriorityFilterChange("all");
  };

  // Sorting state
  const [sortField, setSortField] = useState<SortField>("created_at");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // Pagination state
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Reset to page 1 when search, filters, or sorting change
  const filterKey = `${searchQuery}_${typeFilter}_${statusFilter}_${priorityFilter}_${sortField}_${sortOrder}`;
  const [prevFilterKey, setPrevFilterKey] = useState(filterKey);
  if (filterKey !== prevFilterKey) {
    setPrevFilterKey(filterKey);
    setPage(1);
  }

  const handleToggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder(
        field === "chunk_count" || field === "file_size" ? "desc" : "asc",
      );
    }
  };

  // Sort documents client-side
  const sortedDocuments = useMemo(() => {
    return [...documents].sort((a, b) => {
      let diff = 0;
      switch (sortField) {
        case "title": {
          const titleA = (a.title || a.filename || "").trim();
          const titleB = (b.title || b.filename || "").trim();
          diff = titleA.localeCompare(titleB, "vi", { sensitivity: "base" });
          break;
        }
        case "document_type": {
          const typeA = a.document_type || a.document_type_code || "";
          const typeB = b.document_type || b.document_type_code || "";
          diff = typeA.localeCompare(typeB, "vi");
          break;
        }
        case "chunk_count":
          diff = (a.chunk_count || 0) - (b.chunk_count || 0);
          break;
        case "status": {
          const statusA = a.status || "";
          const statusB = b.status || "";
          diff = statusA.localeCompare(statusB);
          break;
        }
        case "file_size":
          diff = (a.file_size || 0) - (b.file_size || 0);
          break;
        case "created_at": {
          const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
          const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
          diff = timeA - timeB;
          break;
        }
        default:
          diff = 0;
          break;
      }
      return sortOrder === "asc" ? diff : -diff;
    });
  }, [documents, sortField, sortOrder]);

  const totalDocs = sortedDocuments.length;
  const pageCount = Math.max(1, Math.ceil(totalDocs / pageSize));
  const validPage = Math.min(page, pageCount);

  // Paginated slice
  const paginatedDocuments = useMemo(() => {
    const start = (validPage - 1) * pageSize;
    return sortedDocuments.slice(start, start + pageSize);
  }, [sortedDocuments, validPage, pageSize]);

  // Selection operates on currently visible page
  const currentPageIds = useMemo(
    () => paginatedDocuments.map((d) => d.id),
    [paginatedDocuments],
  );

  const isAllCurrentSelected =
    currentPageIds.length > 0 &&
    currentPageIds.every((id) => selectedDocIds.has(id));
  const isSomeCurrentSelected =
    currentPageIds.some((id) => selectedDocIds.has(id)) &&
    !isAllCurrentSelected;

  const handleToggleSelectAll = () => {
    const next = new Set(selectedDocIds);
    if (isAllCurrentSelected) {
      for (const id of currentPageIds) {
        next.delete(id);
      }
    } else {
      for (const id of currentPageIds) {
        next.add(id);
      }
    }
    setSelectedDocIds(next);
  };

  const handleToggleDoc = (docId: string) => {
    const next = new Set(selectedDocIds);
    if (next.has(docId)) {
      next.delete(docId);
    } else {
      next.add(docId);
    }
    setSelectedDocIds(next);
  };

  const handleQuickApproveAction = async (docId: string) => {
    if (!onQuickApprove) return;
    setQuickApprovingId(docId);
    try {
      await onQuickApprove(docId);
    } finally {
      setQuickApprovingId(null);
    }
  };

  const handleBatchApproveAction = async () => {
    if (!onBatchApprove || selectedDocIds.size === 0) return;
    setIsBatchActionRunning(true);
    try {
      await onBatchApprove(Array.from(selectedDocIds));
      setSelectedDocIds(new Set());
    } finally {
      setIsBatchActionRunning(false);
    }
  };

  const handleBatchDeleteAction = async () => {
    if (!onBatchDelete || selectedDocIds.size === 0) return;
    setIsBatchActionRunning(true);
    try {
      await onBatchDelete(Array.from(selectedDocIds));
      setSelectedDocIds(new Set());
    } finally {
      setIsBatchActionRunning(false);
    }
  };

  const pendingSelectedCount = documents.filter(
    (d) =>
      selectedDocIds.has(d.id) &&
      ((d.status as string) === "pending" ||
        (d.status as string) === "review_pending"),
  ).length;

  return (
    <div className="space-y-4">
      {/* Unified Search and Filters Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2.5">
        {/* Search Input */}
        <div className="relative w-full lg:w-72 xl:w-80 shrink-0">
          <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Tìm tiêu đề, tên tệp..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="h-8 pl-8 pr-8 text-xs w-full"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => onSearchChange("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground text-xs"
              title="Xóa từ khóa tìm kiếm"
            >
              <X className="size-3" />
            </button>
          )}
        </div>

        {/* Filters & Reset */}
        <div className="flex flex-wrap sm:flex-nowrap items-center gap-2 w-full lg:w-auto justify-start sm:justify-end">
          <Select value={typeFilter} onValueChange={onTypeFilterChange}>
            <SelectTrigger
              sizeVariant="sm"
              className="w-[calc(50%-4px)] sm:w-[135px]"
            >
              <SelectValue placeholder="Loại" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả loại</SelectItem>
              <SelectItem value="quy_che">Quy chế</SelectItem>
              <SelectItem value="thong_bao">Thông báo</SelectItem>
              <SelectItem value="de_an">Đề án</SelectItem>
              <SelectItem value="quyet_dinh">Quyết định</SelectItem>
              <SelectItem value="huong_dan">Hướng dẫn</SelectItem>
              <SelectItem value="nghi_dinh">Nghị định</SelectItem>
            </SelectContent>
          </Select>

          <Select value={statusFilter} onValueChange={onStatusFilterChange}>
            <SelectTrigger
              sizeVariant="sm"
              className="w-[calc(50%-4px)] sm:w-[140px]"
            >
              <SelectValue placeholder="Trạng thái" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả trạng thái</SelectItem>
              <SelectItem value="pending">Chờ duyệt</SelectItem>
              <SelectItem value="approved">Hiệu lực</SelectItem>
              <SelectItem value="processing">Đang xử lý</SelectItem>
              <SelectItem value="archived">Lưu trữ</SelectItem>
              <SelectItem value="failed">Lỗi</SelectItem>
            </SelectContent>
          </Select>

          <Select value={priorityFilter} onValueChange={onPriorityFilterChange}>
            <SelectTrigger sizeVariant="sm" className="w-full sm:w-[130px]">
              <SelectValue placeholder="Mức ưu tiên" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả ưu tiên</SelectItem>
              <SelectItem value="core">Ưu tiên Cốt lõi</SelectItem>
              <SelectItem value="high">Ưu tiên Bổ trợ</SelectItem>
              <SelectItem value="normal">Ưu tiên Tham khảo</SelectItem>
            </SelectContent>
          </Select>

          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleResetFilters}
              className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground shrink-0 gap-1"
              title="Đặt lại toàn bộ bộ lọc"
            >
              <RotateCcw className="size-3" />
              <span className="hidden sm:inline">Đặt lại</span>
            </Button>
          )}
        </div>
      </div>

      {/* 1. Mobile Card-Based View (< 640px) */}
      <div className="sm:hidden space-y-2.5">
        {/* Mobile Batch Select-All & Quick Sort Toolbar */}
        {totalDocs > 0 && (
          <div className="flex items-center justify-between p-2.5 bg-muted/40 rounded-lg border border-border text-xs">
            <div className="flex items-center gap-2">
              <Checkbox
                checked={
                  isAllCurrentSelected
                    ? true
                    : isSomeCurrentSelected
                      ? "indeterminate"
                      : false
                }
                onCheckedChange={handleToggleSelectAll}
                aria-label="Chọn tất cả tài liệu trang này"
              />
              <span className="font-medium text-foreground">
                Chọn trang ({paginatedDocuments.length})
              </span>
            </div>
            <div className="flex items-center gap-2">
              {selectedDocIds.size > 0 && (
                <span className="text-[11px] text-primary font-medium">
                  ({selectedDocIds.size})
                </span>
              )}
              <Select
                value={`${sortField}-${sortOrder}`}
                onValueChange={(val) => {
                  const [f, o] = val.split("-") as [SortField, SortOrder];
                  setSortField(f);
                  setSortOrder(o);
                }}
              >
                <SelectTrigger className="h-7 text-[11px] w-[115px] border-border/60 bg-background">
                  <ArrowUpDown className="size-3 mr-1 text-muted-foreground" />
                  <SelectValue placeholder="Sắp xếp" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="created_at-desc">Mới nhất</SelectItem>
                  <SelectItem value="title-asc">Tên A → Z</SelectItem>
                  <SelectItem value="title-desc">Tên Z → A</SelectItem>
                  <SelectItem value="chunk_count-desc">Nhiều chunks</SelectItem>
                  <SelectItem value="file_size-desc">Dung lượng</SelectItem>
                  <SelectItem value="status-asc">Trạng thái</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        {paginatedDocuments.length === 0 ? (
          <div className="p-8 text-center bg-card rounded-lg border border-border text-xs text-muted-foreground">
            Không tìm thấy tài liệu phù hợp trong kho này.
          </div>
        ) : (
          paginatedDocuments.map((doc) => {
            const isSelected = selectedDocIds.has(doc.id);
            const meta = getCleanMetadata(doc);
            return (
              <div
                key={doc.id}
                className={`p-3.5 rounded-lg border bg-card transition-all space-y-2.5 shadow-2xs ${
                  isSelected ? "border-primary bg-primary/5" : "border-border"
                }`}
              >
                {/* Header: Checkbox + Title + Status Badges */}
                <div className="flex items-start gap-2.5">
                  <div className="pt-0.5">
                    <Checkbox
                      checked={isSelected}
                      onCheckedChange={() => handleToggleDoc(doc.id)}
                      aria-label={`Chọn tài liệu ${doc.title}`}
                    />
                  </div>
                  <div className="flex size-7 items-center justify-center rounded bg-primary/10 text-primary shrink-0 mt-0.5">
                    <FileText className="size-3.5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <button
                      type="button"
                      className="text-left font-semibold text-xs text-foreground hover:text-primary transition-colors cursor-pointer line-clamp-2 leading-tight"
                      onClick={() => onPreviewDoc(doc)}
                    >
                      {doc.title}
                    </button>
                    {meta.showFilename ? (
                      <p
                        className="text-[11px] text-muted-foreground font-mono truncate mt-0.5"
                        title={meta.filename}
                      >
                        {meta.filename}
                      </p>
                    ) : (
                      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mt-0.5">
                        {meta.ext && (
                          <Badge
                            variant="outline"
                            className="text-[9px] px-1 py-0 font-mono font-semibold uppercase bg-muted/60 text-muted-foreground border-border"
                          >
                            {meta.ext}
                          </Badge>
                        )}
                        <span>•</span>
                        <span className="font-mono">{meta.fileSize}</span>
                        <span>•</span>
                        <span className="text-primary font-medium font-mono">
                          {meta.version}
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="shrink-0 flex flex-col items-end gap-1">
                    <Badge
                      variant="outline"
                      className={`text-[10px] px-1.5 py-0 ${
                        STATUS_BADGE[doc.status]?.className ||
                        STATUS_BADGE.pending.className
                      }`}
                    >
                      {STATUS_BADGE[doc.status]?.label || doc.status}
                    </Badge>
                    {(doc.status === "approved" ||
                      doc.status === "ready" ||
                      doc.status === "completed") &&
                      (doc.index_status === "indexed" ? (
                        <Badge
                          variant="outline"
                          className="text-[10px] px-1.5 py-0 bg-success/10 text-success border-success/30 font-mono"
                        >
                          Đã index
                        </Badge>
                      ) : doc.index_status === "indexing" ? (
                        <Badge
                          variant="outline"
                          className="text-[10px] px-1.5 py-0 bg-info/10 text-info border-info/30 font-mono animate-pulse"
                        >
                          Đang index
                        </Badge>
                      ) : doc.index_status === "index_failed" ? (
                        <Badge
                          variant="outline"
                          className="text-[10px] px-1.5 py-0 bg-destructive/10 text-destructive border-destructive/30 font-mono"
                        >
                          Lỗi index
                        </Badge>
                      ) : null)}
                  </div>
                </div>

                {/* Metadata row: Types, Chunks, Size, Version */}
                <div className="flex items-center gap-1.5 text-[11px] flex-wrap text-muted-foreground pt-1.5 border-t border-border/50">
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                    {formatDocumentType(
                      doc.document_type || doc.document_type_code,
                    )}
                  </Badge>
                  <Badge
                    variant="outline"
                    className="text-[10px] px-1.5 py-0 bg-primary/10 text-primary border-primary/30"
                  >
                    {PRIORITY_LABELS[doc.priority_level || "core"] || "Cốt lõi"}
                  </Badge>
                  <span className="font-mono text-primary font-medium">
                    {doc.chunk_count} chunks
                  </span>
                  {meta.showFilename && (
                    <>
                      <span>•</span>
                      <span className="font-mono">{meta.fileSize}</span>
                      <span>•</span>
                      <span className="font-mono text-primary">
                        {meta.version}
                      </span>
                    </>
                  )}
                </div>

                {/* Actions row */}
                <div className="flex items-center justify-between pt-1.5 border-t border-border/50">
                  {doc.status === "pending" && onQuickApprove ? (
                    <Button
                      size="sm"
                      onClick={() => handleQuickApproveAction(doc.id)}
                      disabled={quickApprovingId === doc.id}
                      className="h-7 text-xs px-2.5 gap-1.5 bg-success text-success-foreground hover:bg-success/90"
                    >
                      {quickApprovingId === doc.id ? (
                        <RefreshCw className="size-3 animate-spin" />
                      ) : (
                        <CheckCircle2 className="size-3" />
                      )}
                      <span>Duyệt nhanh</span>
                    </Button>
                  ) : (
                    <div />
                  )}

                  <div className="flex items-center gap-1">
                    {doc.status === "approved" &&
                      doc.index_status !== "indexed" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => onReindexDoc(doc.id)}
                          disabled={reindexingDocId === doc.id}
                          className="size-7 text-amber-500 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950/30"
                          title="Reindex vector"
                        >
                          <Zap
                            className={`size-3.5 ${reindexingDocId === doc.id ? "animate-spin" : ""}`}
                          />
                        </Button>
                      )}
                    <Button
                      size="sm"
                      onClick={() => onStartVerify(doc.id)}
                      className="h-7 text-xs px-2 gap-1 border border-primary/25 bg-primary/10 text-primary hover:bg-primary hover:text-primary-foreground font-medium transition-colors shrink-0"
                      title="Mở Studio Bóc Tách & Đối Soát"
                      aria-label="Mở Studio Bóc Tách"
                    >
                      <Scan className="size-3" />
                      <span>Studio</span>
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onPreviewDoc(doc)}
                      className="size-7 text-muted-foreground hover:text-foreground"
                      title="Xem trước Chunks"
                      aria-label="Xem trước Chunks"
                    >
                      <Eye className="size-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onDownloadDoc(doc)}
                      disabled={downloadingId === doc.id}
                      className="size-7 text-muted-foreground hover:text-foreground"
                      title="Tải tệp gốc"
                      aria-label="Tải tệp gốc"
                    >
                      <Download className="size-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onDeleteDoc(doc)}
                      className="size-7 text-destructive hover:text-destructive"
                      title="Xóa tài liệu"
                      aria-label="Xóa tài liệu"
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* 2. Desktop & Tablet Table View (>= 640px) */}
      <div className="hidden sm:block bg-card rounded-lg border border-border overflow-hidden shadow-xs">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40 hover:bg-muted/40 text-xs font-semibold text-muted-foreground uppercase">
              <TableHead className="w-10 text-center">
                <Checkbox
                  checked={
                    isAllCurrentSelected
                      ? true
                      : isSomeCurrentSelected
                        ? "indeterminate"
                        : false
                  }
                  onCheckedChange={handleToggleSelectAll}
                  aria-label="Chọn tất cả tài liệu trang này"
                />
              </TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleToggleSort("title")}
                  className="-ml-2 h-8 px-2 font-semibold text-muted-foreground hover:text-foreground text-xs gap-1.5"
                  title="Sắp xếp theo tên tài liệu"
                >
                  <span>Tài liệu & Tên tệp gốc</span>
                  {sortField === "title" ? (
                    sortOrder === "asc" ? (
                      <ArrowUp className="size-3 text-primary" />
                    ) : (
                      <ArrowDown className="size-3 text-primary" />
                    )
                  ) : (
                    <ArrowUpDown className="size-3 opacity-40 hover:opacity-100" />
                  )}
                </Button>
              </TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleToggleSort("document_type")}
                  className="-ml-2 h-8 px-2 font-semibold text-muted-foreground hover:text-foreground text-xs gap-1.5"
                  title="Sắp xếp theo loại văn bản"
                >
                  <span>Loại văn bản</span>
                  {sortField === "document_type" ? (
                    sortOrder === "asc" ? (
                      <ArrowUp className="size-3 text-primary" />
                    ) : (
                      <ArrowDown className="size-3 text-primary" />
                    )
                  ) : (
                    <ArrowUpDown className="size-3 opacity-40 hover:opacity-100" />
                  )}
                </Button>
              </TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleToggleSort("chunk_count")}
                  className="-ml-2 h-8 px-2 font-semibold text-muted-foreground hover:text-foreground text-xs gap-1.5"
                  title="Sắp xếp theo số lượng chunks"
                >
                  <span>Chunks Vector</span>
                  {sortField === "chunk_count" ? (
                    sortOrder === "asc" ? (
                      <ArrowUp className="size-3 text-primary" />
                    ) : (
                      <ArrowDown className="size-3 text-primary" />
                    )
                  ) : (
                    <ArrowUpDown className="size-3 opacity-40 hover:opacity-100" />
                  )}
                </Button>
              </TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleToggleSort("status")}
                  className="-ml-2 h-8 px-2 font-semibold text-muted-foreground hover:text-foreground text-xs gap-1.5"
                  title="Sắp xếp theo trạng thái"
                >
                  <span>Trạng thái</span>
                  {sortField === "status" ? (
                    sortOrder === "asc" ? (
                      <ArrowUp className="size-3 text-primary" />
                    ) : (
                      <ArrowDown className="size-3 text-primary" />
                    )
                  ) : (
                    <ArrowUpDown className="size-3 opacity-40 hover:opacity-100" />
                  )}
                </Button>
              </TableHead>
              <TableHead className="text-right w-56">Thao tác</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedDocuments.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="h-32 text-center text-xs text-muted-foreground"
                >
                  Không tìm thấy tài liệu phù hợp trong kho này.
                </TableCell>
              </TableRow>
            ) : (
              paginatedDocuments.map((doc) => {
                const isSelected = selectedDocIds.has(doc.id);
                const meta = getCleanMetadata(doc);
                return (
                  <TableRow
                    key={doc.id}
                    className={`transition-colors ${
                      isSelected
                        ? "bg-primary/5 hover:bg-primary/10"
                        : "hover:bg-muted/30"
                    }`}
                  >
                    <TableCell className="text-center">
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={() => handleToggleDoc(doc.id)}
                        aria-label={`Chọn tài liệu ${doc.title}`}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex items-start gap-3">
                        <div className="flex size-8 items-center justify-center rounded bg-primary/10 text-primary shrink-0 mt-0.5">
                          <FileText className="size-4" />
                        </div>
                        <div className="min-w-0">
                          <button
                            type="button"
                            className="text-left font-semibold text-xs text-foreground hover:text-primary transition-colors cursor-pointer line-clamp-1 block"
                            onClick={() => onPreviewDoc(doc)}
                            title={doc.title}
                          >
                            {doc.title}
                          </button>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                            {meta.showFilename ? (
                              <span
                                className="font-mono truncate max-w-[220px]"
                                title={meta.filename}
                              >
                                {meta.filename}
                              </span>
                            ) : (
                              meta.ext && (
                                <Badge
                                  variant="outline"
                                  className="text-[10px] px-1.5 py-0 font-mono font-semibold uppercase bg-muted/60 text-muted-foreground border-border"
                                >
                                  {meta.ext}
                                </Badge>
                              )
                            )}
                            <span>•</span>
                            <span className="font-mono text-[11px]">
                              {meta.fileSize}
                            </span>
                            <span>•</span>
                            <span className="text-primary font-medium font-mono text-[11px]">
                              {meta.version}
                            </span>
                          </div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <span className="text-xs text-foreground font-medium block">
                          {formatDocumentType(
                            doc.document_type || doc.document_type_code,
                          )}
                        </span>
                        <Badge
                          variant="outline"
                          className="text-[11px] bg-primary/10 text-primary border-primary/30"
                        >
                          {PRIORITY_LABELS[doc.priority_level || "core"] ||
                            "Cốt lõi"}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="font-semibold text-xs text-primary font-mono">
                        {doc.chunk_count} chunks
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1 items-start">
                        <Badge
                          variant="outline"
                          className={`text-xs ${
                            STATUS_BADGE[doc.status]?.className ||
                            STATUS_BADGE.pending.className
                          }`}
                        >
                          {STATUS_BADGE[doc.status]?.label || doc.status}
                        </Badge>
                        {(doc.status === "approved" ||
                          doc.status === "ready" ||
                          doc.status === "completed") &&
                          (doc.index_status === "indexed" ? (
                            <Badge
                              variant="outline"
                              className="text-xs bg-success/10 text-success border-success/30 gap-1 font-mono"
                            >
                              <CheckCircle2 className="size-2.5" />
                              <span>Đã index</span>
                            </Badge>
                          ) : doc.index_status === "indexing" ? (
                            <Badge
                              variant="outline"
                              className="text-xs bg-info/10 text-info border-info/30 gap-1 font-mono animate-pulse"
                            >
                              <RefreshCw className="size-2.5 animate-spin" />
                              <span>Đang index</span>
                            </Badge>
                          ) : doc.index_status === "index_failed" ? (
                            <Badge
                              variant="outline"
                              className="text-xs bg-destructive/10 text-destructive border-destructive/30 gap-1 font-mono"
                              title={doc.index_error || "Lỗi chỉ mục vector"}
                            >
                              <CircleAlert className="size-2.5" />
                              <span>Lỗi index</span>
                            </Badge>
                          ) : (
                            <Badge
                              variant="outline"
                              className="text-xs bg-warning/10 text-warning border-warning/30 gap-1 font-mono"
                            >
                              <span>Chờ index</span>
                            </Badge>
                          ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {/* 1-Click Quick Approve for Pending documents */}
                        {doc.status === "pending" && onQuickApprove && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleQuickApproveAction(doc.id)}
                            disabled={quickApprovingId === doc.id}
                            className="size-7 text-success hover:text-success hover:bg-success/10 shrink-0"
                            title="Duyệt nhanh tài liệu & nạp vào Vector DB ngay lập tức"
                            aria-label="Duyệt nhanh tài liệu"
                          >
                            {quickApprovingId === doc.id ? (
                              <RefreshCw className="size-3.5 animate-spin" />
                            ) : (
                              <CheckCircle2 className="size-3.5" />
                            )}
                          </Button>
                        )}

                        {doc.status === "approved" &&
                          doc.index_status !== "indexed" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => onReindexDoc(doc.id)}
                              disabled={reindexingDocId === doc.id}
                              className="size-7 text-amber-500 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950/30 shrink-0"
                              title="Thử lại lập chỉ mục vector (Reindex)"
                              aria-label="Thử lại lập chỉ mục vector"
                            >
                              <Zap
                                className={`size-3.5 ${reindexingDocId === doc.id ? "animate-spin" : ""}`}
                              />
                            </Button>
                          )}

                        {/* Primary CTA: Studio OCR & Verify */}
                        <Button
                          size="sm"
                          onClick={() => onStartVerify(doc.id)}
                          className="h-7 text-xs px-2.5 gap-1.5 border border-primary/25 bg-primary/10 text-primary hover:bg-primary hover:text-primary-foreground font-medium transition-colors shrink-0 shadow-2xs"
                          title="Mở Studio Bóc Tách & Đối Soát (Split-Pane)"
                          aria-label="Mở Studio Bóc Tách & Đối Soát"
                        >
                          <Scan className="size-3" />
                          <span>Studio OCR</span>
                        </Button>

                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => onPreviewDoc(doc)}
                          className="size-7 text-muted-foreground hover:text-foreground shrink-0"
                          title="Xem trước Chunks Inspector"
                          aria-label="Xem trước Chunks"
                        >
                          <Eye className="size-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => onDownloadDoc(doc)}
                          disabled={downloadingId === doc.id}
                          className="size-7 text-muted-foreground hover:text-foreground shrink-0"
                          title="Tải tệp gốc"
                          aria-label="Tải tệp gốc"
                        >
                          <Download className="size-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => onDeleteDoc(doc)}
                          className="size-7 text-destructive hover:text-destructive shrink-0"
                          title="Xóa tài liệu"
                          aria-label="Xóa tài liệu"
                        >
                          <Trash2 className="size-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* 3. Pagination Controls (Shared for both Desktop Table & Mobile Cards) */}
      {totalDocs > 0 && (
        <DataTablePagination
          page={validPage}
          pageSize={pageSize}
          pageCount={pageCount}
          total={totalDocs}
          onPageChange={setPage}
          onPageSizeChange={(newSize) => {
            setPageSize(newSize);
            setPage(1);
          }}
          className="pt-1 px-0.5"
        />
      )}

      {/* Floating Bottom-Center Bulk Actions Bar */}
      <DataTableBulkActions
        selectedCount={selectedDocIds.size}
        selectedLabel="tài liệu"
        onClear={() => setSelectedDocIds(new Set())}
      >
        {onBatchApprove && pendingSelectedCount > 0 ? (
          <Button
            size="sm"
            onClick={handleBatchApproveAction}
            disabled={isBatchActionRunning}
            className="h-7 text-xs px-2.5 gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 rounded-xl cursor-pointer shadow-2xs"
            title={`Phê duyệt ${pendingSelectedCount} tài liệu đang chờ`}
          >
            {isBatchActionRunning ? (
              <RefreshCw className="size-3 animate-spin" />
            ) : (
              <Zap className="size-3" />
            )}
            <span>Duyệt ({pendingSelectedCount})</span>
          </Button>
        ) : null}

        {onBatchDelete ? (
          <Button
            variant="destructive"
            size="sm"
            onClick={handleBatchDeleteAction}
            disabled={isBatchActionRunning}
            className="h-7 text-xs px-2.5 gap-1.5 rounded-xl cursor-pointer shadow-2xs"
            title={`Xóa ${selectedDocIds.size} tài liệu đã chọn`}
          >
            <Trash2 className="size-3" />
            <span>Xóa ({selectedDocIds.size})</span>
          </Button>
        ) : null}
      </DataTableBulkActions>
    </div>
  );
}
