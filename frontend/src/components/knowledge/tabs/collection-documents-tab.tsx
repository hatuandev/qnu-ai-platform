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
  CircleAlert,
  Download,
  Eye,
  FileText,
  RefreshCw,
  Scan,
  Search,
  Trash2,
  Zap,
} from "lucide-react";

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
}: CollectionDocumentsTabProps) {
  return (
    <div className="space-y-4">
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
                  className="rounded border-border size-3.5"
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
              documents.map((doc) => (
                <TableRow key={doc.id} className="hover:bg-muted/30 transition-colors">
                  <TableCell className="text-center">
                    <input
                      type="checkbox"
                      className="rounded border-border size-3.5"
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
                          <span className="text-primary font-medium">{doc.version || "v1.0"}</span>
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
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
