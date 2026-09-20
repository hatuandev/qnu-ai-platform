import { STATUS_BADGE, formatFileSize } from "@/components/knowledge/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  Download,
  Eye,
  FileText,
  Info,
  Layers,
  RefreshCw,
  Scan,
  Search,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import { useState } from "react";

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
  const [isBatchActionRunning, setIsBatchActionRunning] = useState<boolean>(false);
  const [quickApprovingId, setQuickApprovingId] = useState<string | null>(null);

  const allVisibleIds = documents.map((d) => d.id);
  const isAllSelected =
    allVisibleIds.length > 0 && allVisibleIds.every((id) => selectedDocIds.has(id));
  const isSomeSelected = allVisibleIds.some((id) => selectedDocIds.has(id)) && !isAllSelected;

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
      ((d.status as string) === "pending" || (d.status as string) === "review_pending")
  ).length;

  return (
    <div className="space-y-4">
      {/* Mini Stepper Guide (Collapsible) */}
      <div className="rounded-lg border border-border bg-card overflow-hidden transition-all shadow-xs">
        <button
          type="button"
          onClick={() => setIsGuideOpen(!isGuideOpen)}
          className="w-full flex items-center justify-between p-3 text-xs font-semibold text-foreground hover:bg-muted/40 transition-colors cursor-pointer text-left"
        >
          <div className="flex items-center gap-2">
            <div className="size-5 rounded bg-primary/10 text-primary flex items-center justify-center">
              <Info className="size-3.5" />
            </div>
            <span>Hướng dẫn quy trình: 3 Chặng vòng đời tài liệu trong Kho Tri Thức</span>
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground text-[11px] font-normal">
            <span>{isGuideOpen ? "Thu gọn" : "Xem chi tiết"}</span>
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
                File được lưu trữ an toàn trên MinIO S3, PyMuPDF/OCR quét chữ và layout OpenCV nhận
                diện con dấu, bảng biểu số liệu.
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
                <strong>Duyệt nhanh 1-Click</strong>. Data Quality Gate tự động chặn bảng vỡ.
              </p>
              <div className="flex items-center gap-1 pt-1">
                <Badge variant="outline" className="text-[10px] text-amber-600 bg-amber-500/10">
                  pending
                </Badge>
                <span className="text-muted-foreground text-[10px]">→</span>
                <Badge variant="outline" className="text-[10px] text-emerald-600 bg-emerald-500/10">
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
                Hệ thống nạp Vector BGE-M3 1024D vào Qdrant và cập nhật PostgreSQL FTS. Trợ lý AI
                chính thức được phép tra cứu RAG không bịa đặt.
              </p>
              <div className="flex items-center gap-1 pt-1">
                <Badge variant="outline" className="text-[10px] text-blue-600 bg-blue-500/10">
                  indexing
                </Badge>
                <span className="text-muted-foreground text-[10px]">→</span>
                <Badge
                  variant="outline"
                  className="text-[10px] text-emerald-700 bg-emerald-500/15 font-semibold"
                >
                  ready / Hiệu lực
                </Badge>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bulk Action Floating Bar (when items selected) */}
      {selectedDocIds.size > 0 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 bg-primary/10 border border-primary/30 rounded-lg shadow-sm animate-in fade-in duration-200">
          <div className="flex items-center gap-2 text-xs font-semibold text-primary">
            <Layers className="size-4" />
            <span>Đã chọn {selectedDocIds.size} tài liệu</span>
            {pendingSelectedCount > 0 && (
              <span className="text-muted-foreground font-normal">
                ({pendingSelectedCount} tài liệu đang chờ duyệt)
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            {onBatchApprove && pendingSelectedCount > 0 && (
              <Button
                size="sm"
                onClick={handleBatchApproveAction}
                disabled={isBatchActionRunning}
                className="h-8 text-xs px-3 gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer"
              >
                {isBatchActionRunning ? (
                  <RefreshCw className="size-3 animate-spin" />
                ) : (
                  <Zap className="size-3" />
                )}
                <span>Phê duyệt {pendingSelectedCount} tài liệu</span>
              </Button>
            )}

            {onBatchDelete && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleBatchDeleteAction}
                disabled={isBatchActionRunning}
                className="h-8 text-xs px-3 gap-1.5 text-rose-600 border-rose-200 hover:bg-rose-50 dark:hover:bg-rose-950/30 cursor-pointer"
              >
                <Trash2 className="size-3" />
                <span>Xóa {selectedDocIds.size} tài liệu</span>
              </Button>
            )}

            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedDocIds(new Set())}
              className="h-8 text-xs px-2.5 text-muted-foreground hover:text-foreground cursor-pointer"
            >
              <X className="size-3.5" />
              <span>Bỏ chọn</span>
            </Button>
          </div>
        </div>
      )}

      {/* Search and Filters Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-card p-3 rounded-lg border border-border">
        <div className="flex items-center gap-2 w-full sm:w-80">
          <Search className="size-4 text-muted-foreground shrink-0" />
          <Input
            placeholder="Tìm tiêu đề, tên tệp..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="h-8 text-xs"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto flex-wrap justify-end">
          <Select value={typeFilter} onValueChange={onTypeFilterChange}>
            <SelectTrigger sizeVariant="sm" className="w-[160px]">
              <SelectValue placeholder="Tất cả loại văn bản" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả loại văn bản</SelectItem>
              <SelectItem value="Quy chế">Quy chế</SelectItem>
              <SelectItem value="Đề án">Đề án</SelectItem>
              <SelectItem value="Nghị định">Nghị định</SelectItem>
            </SelectContent>
          </Select>

          <Select value={statusFilter} onValueChange={onStatusFilterChange}>
            <SelectTrigger sizeVariant="sm" className="w-[165px]">
              <SelectValue placeholder="Tất cả trạng thái" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả trạng thái</SelectItem>
              <SelectItem value="pending">Chờ duyệt</SelectItem>
              <SelectItem value="approved">Đã duyệt (Hiệu lực)</SelectItem>
              <SelectItem value="completed">Hiệu lực</SelectItem>
              <SelectItem value="processing">Đang xử lý</SelectItem>
              <SelectItem value="archived">Lưu trữ</SelectItem>
              <SelectItem value="failed">Lỗi</SelectItem>
            </SelectContent>
          </Select>

          <Select value={priorityFilter} onValueChange={onPriorityFilterChange}>
            <SelectTrigger sizeVariant="sm" className="w-[170px]">
              <SelectValue placeholder="Tất cả mức ưu tiên" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả mức ưu tiên</SelectItem>
              <SelectItem value="core">Ưu tiên Cao (Cốt lõi)</SelectItem>
              <SelectItem value="high">Ưu tiên Trung bình</SelectItem>
            </SelectContent>
          </Select>

          <span className="text-xs text-muted-foreground ml-2">
            Hiển thị {documents.length} / {totalDocumentsCount} tài liệu
          </span>
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-card rounded-lg border border-border overflow-hidden shadow-xs">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40 hover:bg-muted/40 text-xs font-semibold text-muted-foreground uppercase">
              <TableHead className="w-10 text-center">
                <input
                  type="checkbox"
                  checked={isAllSelected}
                  ref={(input) => {
                    if (input) input.indeterminate = isSomeSelected;
                  }}
                  onChange={handleToggleSelectAll}
                  className="rounded border-border size-3.5 cursor-pointer accent-primary"
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
                <TableCell colSpan={6} className="h-32 text-center text-xs text-muted-foreground">
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
                      isSelected ? "bg-primary/5 hover:bg-primary/10" : "hover:bg-muted/30"
                    }`}
                  >
                    <TableCell className="text-center">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleToggleDoc(doc.id)}
                        className="rounded border-border size-3.5 cursor-pointer accent-primary"
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
                          {doc.document_type || "Quy chế"}
                        </span>
                        <Badge
                          variant="outline"
                          className="text-xs bg-primary/10 text-primary border-primary/30"
                        >
                          Ưu tiên Cao (Cốt lõi)
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
                            STATUS_BADGE[doc.status]?.className || STATUS_BADGE.pending.className
                          }`}
                        >
                          {STATUS_BADGE[doc.status]?.label || doc.status}
                        </Badge>
                        {doc.status === "approved" &&
                          (doc.index_status === "indexed" ? (
                            <Badge
                              variant="outline"
                              className="text-xs bg-emerald-500/10 text-emerald-600 border-emerald-500/30 gap-1 font-mono"
                            >
                              <CheckCircle2 className="size-2.5" />
                              <span>Đã index</span>
                            </Badge>
                          ) : doc.index_status === "indexing" ? (
                            <Badge
                              variant="outline"
                              className="text-xs bg-blue-500/10 text-blue-600 border-blue-500/30 gap-1 font-mono animate-pulse"
                            >
                              <RefreshCw className="size-2.5 animate-spin" />
                              <span>Đang index</span>
                            </Badge>
                          ) : doc.index_status === "index_failed" ? (
                            <Badge
                              variant="outline"
                              className="text-xs bg-rose-500/10 text-rose-600 border-rose-500/30 gap-1 font-mono"
                              title={doc.index_error || "Lỗi chỉ mục vector"}
                            >
                              <CircleAlert className="size-2.5" />
                              <span>Lỗi index</span>
                            </Badge>
                          ) : (
                            <Badge
                              variant="outline"
                              className="text-xs bg-amber-500/10 text-amber-600 border-amber-500/30 gap-1 font-mono"
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
                            className="size-7 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
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

                        {doc.status === "approved" && doc.index_status !== "indexed" && (
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
                          className="size-7 text-rose-500 hover:text-rose-600"
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
    </div>
  );
}
