import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  Download,
  Eye,
  FileText,
  Info,
  RefreshCw,
  Scan,
  Search,
  Trash2,
  Zap,
} from "lucide-react";
import { useState } from "react";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
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
  totalDocumentsCount: number;
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

export function CollectionDocumentsTab({
  documents,
  totalDocumentsCount,
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
  const [isGuideOpen, setIsGuideOpen] = useState<boolean>(false);
  const [isBatchActionRunning, setIsBatchActionRunning] =
    useState<boolean>(false);
  const [quickApprovingId, setQuickApprovingId] = useState<string | null>(null);

  const allVisibleIds = documents.map((d) => d.id);
  const isAllSelected =
    allVisibleIds.length > 0 &&
    allVisibleIds.every((id) => selectedDocIds.has(id));
  const isSomeSelected =
    allVisibleIds.some((id) => selectedDocIds.has(id)) && !isAllSelected;

  const handleToggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedDocIds(new Set());
    } else {
      setSelectedDocIds(new Set(allVisibleIds));
    }
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
      {/* Mini Stepper Guide (Collapsible) */}
      <div className="rounded-lg border border-border bg-card overflow-hidden transition-all shadow-xs">
        <button
          type="button"
          onClick={() => setIsGuideOpen(!isGuideOpen)}
          className="w-full flex items-center justify-between p-3 text-xs font-semibold text-foreground hover:bg-muted/40 transition-colors cursor-pointer text-left gap-2"
        >
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <div className="size-5 rounded bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <Info className="size-3.5" />
            </div>
            <span className="truncate">
              Quy trình 3 chặng vòng đời tài liệu trong Kho Tri Thức
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground text-[11px] font-normal shrink-0">
            <span className="hidden sm:inline">
              {isGuideOpen ? "Thu gọn" : "Xem chi tiết"}
            </span>
            {isGuideOpen ? (
              <ChevronUp className="size-3.5" />
            ) : (
              <ChevronDown className="size-3.5" />
            )}
          </div>
        </button>

        {isGuideOpen && (
          <div className="p-4 pt-1 border-t border-border/70 bg-muted/20 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded-md bg-card border border-border space-y-1">
              <div className="flex items-center gap-2 font-semibold text-foreground">
                <span className="size-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-mono">
                  1
                </span>
                <span>Chặng 1: Nạp & Bóc Tách</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                File được lưu trữ an toàn trên MinIO S3, PyMuPDF/OCR quét chữ và
                layout OpenCV nhận diện con dấu, bảng biểu số liệu.
              </p>
              <div className="flex items-center gap-1 pt-1">
                <Badge variant="outline" className="text-[10px]">
                  uploaded
                </Badge>
                <span className="text-muted-foreground text-[10px]">→</span>
                <Badge variant="outline" className="text-[10px]">
                  extracting
                </Badge>
              </div>
            </div>

            <div className="p-3 rounded-md bg-card border border-border space-y-1">
              <div className="flex items-center gap-2 font-semibold text-foreground">
                <span className="size-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-mono">
                  2
                </span>
                <span>Chặng 2: Thẩm Định & Duyệt</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Cán bộ đối soát mắt song song trên Scan Studio hoặc bấm nút{" "}
                <strong>Duyệt nhanh 1-Click</strong>. Data Quality Gate tự động
                chặn bảng vỡ.
              </p>
              <div className="flex items-center gap-1 pt-1">
                <Badge
                  variant="outline"
                  className="text-[10px] text-warning bg-warning/10 border-warning/30"
                >
                  pending
                </Badge>
                <span className="text-muted-foreground text-[10px]">→</span>
                <Badge
                  variant="outline"
                  className="text-[10px] text-success bg-success/10 border-success/30"
                >
                  approved
                </Badge>
              </div>
            </div>

            <div className="p-3 rounded-md bg-card border border-border space-y-1">
              <div className="flex items-center gap-2 font-semibold text-foreground">
                <span className="size-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-mono">
                  3
                </span>
                <span>Chặng 3: Sẵn Sàng AI</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Hệ thống nạp Vector BGE-M3 1024D vào Qdrant và cập nhật
                PostgreSQL FTS. Trợ lý AI chính thức được phép tra cứu RAG không
                bịa đặt.
              </p>
              <div className="flex items-center gap-1 pt-1">
                <Badge
                  variant="outline"
                  className="text-[10px] text-info bg-info/10 border-info/30"
                >
                  indexing
                </Badge>
                <span className="text-muted-foreground text-[10px]">→</span>
                <Badge
                  variant="outline"
                  className="text-[10px] text-success bg-success/15 border-success/30 font-semibold"
                >
                  ready / Hiệu lực
                </Badge>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Search and Filters Bar */}
      <div className="flex flex-col gap-2.5 bg-card p-3 rounded-lg border border-border shadow-2xs">
        {/* Row 1: Search Input & Summary Count */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div className="relative flex-1">
            <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Tìm tiêu đề, tên tệp..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="h-8 pl-8 text-xs w-full"
            />
          </div>
          <div className="text-xs text-muted-foreground text-right shrink-0">
            Hiển thị{" "}
            <strong className="text-foreground">{documents.length}</strong> /{" "}
            {totalDocumentsCount} tài liệu
          </div>
        </div>

        {/* Row 2: Select Filters: 2 cols on mobile, flex on tablet/desktop */}
        <div className="grid grid-cols-2 sm:flex sm:items-center gap-2 w-full lg:w-auto">
          <Select value={typeFilter} onValueChange={onTypeFilterChange}>
            <SelectTrigger sizeVariant="sm" className="w-full sm:w-[155px]">
              <SelectValue placeholder="Loại văn bản" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả loại văn bản</SelectItem>
              <SelectItem value="quy_che">Quy chế</SelectItem>
              <SelectItem value="thong_bao">Thông báo</SelectItem>
              <SelectItem value="de_an">Đề án</SelectItem>
              <SelectItem value="quyet_dinh">Quyết định</SelectItem>
              <SelectItem value="huong_dan">Hướng dẫn</SelectItem>
              <SelectItem value="nghi_dinh">Nghị định</SelectItem>
            </SelectContent>
          </Select>

          <Select value={statusFilter} onValueChange={onStatusFilterChange}>
            <SelectTrigger sizeVariant="sm" className="w-full sm:w-[155px]">
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
            <SelectTrigger
              sizeVariant="sm"
              className="col-span-2 sm:col-span-1 w-full sm:w-[155px]"
            >
              <SelectValue placeholder="Mức ưu tiên" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả mức ưu tiên</SelectItem>
              <SelectItem value="core">Ưu tiên Cốt lõi</SelectItem>
              <SelectItem value="high">Ưu tiên Bổ trợ</SelectItem>
              <SelectItem value="normal">Ưu tiên Tham khảo</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 1. Mobile Card-Based View (< 640px) */}
      <div className="sm:hidden space-y-2.5">
        {/* Mobile Batch Select-All Toolbar */}
        {documents.length > 0 && (
          <div className="flex items-center justify-between p-2.5 bg-muted/40 rounded-lg border border-border text-xs">
            <div className="flex items-center gap-2">
              <Checkbox
                checked={
                  isAllSelected
                    ? true
                    : isSomeSelected
                      ? "indeterminate"
                      : false
                }
                onCheckedChange={handleToggleSelectAll}
                aria-label="Chọn tất cả tài liệu"
              />
              <span className="font-medium text-foreground">
                Chọn tất cả ({documents.length})
              </span>
            </div>
            {selectedDocIds.size > 0 && (
              <span className="text-[11px] text-primary font-medium">
                Đã chọn {selectedDocIds.size}
              </span>
            )}
          </div>
        )}

        {documents.length === 0 ? (
          <div className="p-8 text-center bg-card rounded-lg border border-border text-xs text-muted-foreground">
            Không tìm thấy tài liệu phù hợp trong kho này.
          </div>
        ) : (
          documents.map((doc) => {
            const isSelected = selectedDocIds.has(doc.id);
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
                    <p className="text-[11px] text-muted-foreground font-mono truncate mt-0.5">
                      {doc.filename}
                    </p>
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
                  <span>•</span>
                  <span className="font-mono">
                    {formatFileSize(doc.file_size)}
                  </span>
                  <span>•</span>
                  <span className="font-mono">{doc.version || "v1.0"}</span>
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
                      variant="ghost"
                      size="icon"
                      onClick={() => onStartVerify(doc.id)}
                      className="size-7 text-muted-foreground hover:text-primary"
                      title="Mở Studio Bóc Tách"
                      aria-label="Mở Studio Bóc Tách"
                    >
                      <Scan className="size-3.5" />
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
                    isAllSelected
                      ? true
                      : isSomeSelected
                        ? "indeterminate"
                        : false
                  }
                  onCheckedChange={handleToggleSelectAll}
                  aria-label="Chọn tất cả tài liệu"
                />
              </TableHead>
              <TableHead>Tài liệu & Tên tệp gốc</TableHead>
              <TableHead>Loại văn bản</TableHead>
              <TableHead>Chunks Vector</TableHead>
              <TableHead>Trạng thái</TableHead>
              <TableHead className="text-right">Thao tác</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {documents.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="h-32 text-center text-xs text-muted-foreground"
                >
                  Không tìm thấy tài liệu phù hợp trong kho này.
                </TableCell>
              </TableRow>
            ) : (
              documents.map((doc) => {
                const isSelected = selectedDocIds.has(doc.id);
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
                        <div>
                          <button
                            type="button"
                            className="text-left font-semibold text-xs text-foreground hover:text-primary transition-colors cursor-pointer"
                            onClick={() => onPreviewDoc(doc)}
                          >
                            {doc.title}
                          </button>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono mt-0.5">
                            <span>{doc.filename}</span>
                            <span>•</span>
                            <span>{formatFileSize(doc.file_size)}</span>
                            <span>•</span>
                            <span className="text-primary font-medium">
                              {doc.version || "v1.0"}
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
                      <div className="flex items-center justify-end gap-1">
                        {/* 1-Click Quick Approve for Pending documents */}
                        {doc.status === "pending" && onQuickApprove && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleQuickApproveAction(doc.id)}
                            disabled={quickApprovingId === doc.id}
                            className="size-7 text-success hover:text-success hover:bg-success/10"
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
                              className="size-7 text-amber-500 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950/30"
                              title="Thử lại lập chỉ mục vector (Reindex)"
                              aria-label="Thử lại lập chỉ mục vector"
                            >
                              <Zap
                                className={`size-3.5 ${reindexingDocId === doc.id ? "animate-spin" : ""}`}
                              />
                            </Button>
                          )}
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => onStartVerify(doc.id)}
                          className="size-7 text-muted-foreground hover:text-primary"
                          title="Mở Studio Bóc Tách & Đối Soát (Split-Pane)"
                          aria-label="Mở Studio Bóc Tách & Đối Soát"
                        >
                          <Scan className="size-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => onPreviewDoc(doc)}
                          className="size-7 text-muted-foreground hover:text-foreground"
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
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

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
