import { Link } from "@tanstack/react-router";
import {
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  Clock,
  Download,
  FileCode,
  FileSpreadsheet,
  FileText,
  Hash,
  MoreHorizontal,
  RefreshCw,
  Trash2,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { documentsApi } from "@/services/documents-api";
import type { RepositoryDocumentListItem } from "@/types/documents";

interface DocumentsTableProps {
  documents: RepositoryDocumentListItem[];
  selectedIds: string[];
  onToggleSelect: (id: string) => void;
  onToggleSelectAll: () => void;
  onReparse: (doc: RepositoryDocumentListItem) => void;
  onDelete: (doc: RepositoryDocumentListItem) => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(fileType: string) {
  switch (fileType.toLowerCase()) {
    case "pdf":
      return <FileText className="size-4 text-red-500" />;
    case "xlsx":
    case "xls":
      return <FileSpreadsheet className="size-4 text-emerald-600" />;
    case "md":
    case "txt":
      return <FileCode className="size-4 text-sky-500" />;
    default:
      return <FileText className="size-4 text-primary" />;
  }
}

export function DocumentsTable({
  documents,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onReparse,
  onDelete,
}: DocumentsTableProps) {
  const allSelected =
    documents.length > 0 && selectedIds.length === documents.length;
  const someSelected =
    selectedIds.length > 0 && selectedIds.length < documents.length;

  return (
    <div className="rounded-lg border border-border/70 bg-card overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-10">
              <Checkbox
                checked={
                  allSelected ? true : someSelected ? "indeterminate" : false
                }
                onCheckedChange={onToggleSelectAll}
                aria-label="Chọn tất cả"
              />
            </TableHead>
            <TableHead>Tài Liệu & Tệp Gốc</TableHead>
            <TableHead className="w-44">Số Hiệu & Phân Loại</TableHead>
            <TableHead className="w-36">Trạng Thái MD</TableHead>
            <TableHead className="w-28 text-right">Dung Lượng</TableHead>
            <TableHead className="w-36 text-center">Kho Tri Thức</TableHead>
            <TableHead className="w-32">Ngày Tải</TableHead>
            <TableHead className="w-16 text-right">Thao Tác</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => {
            const isSelected = selectedIds.includes(doc.id);
            const downloadUrl = documentsApi.getDownloadUrl(doc.id);

            return (
              <TableRow
                key={doc.id}
                data-state={isSelected ? "selected" : undefined}
                className="h-11 hover:bg-muted/40 transition-colors"
              >
                {/* Checkbox */}
                <TableCell>
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() => onToggleSelect(doc.id)}
                    aria-label={`Chọn ${doc.title || doc.file_name}`}
                  />
                </TableCell>

                {/* Tên tài liệu & Tệp */}
                <TableCell>
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-muted/60">
                      {getFileIcon(doc.file_type)}
                    </div>
                    <div className="min-w-0">
                      <Link
                        to="/documents/$documentId"
                        params={{ documentId: doc.id }}
                        className="font-medium text-xs sm:text-sm text-foreground hover:text-primary transition-colors truncate block"
                        title={doc.title || doc.file_name}
                      >
                        {doc.title || doc.file_name}
                      </Link>
                      <span className="text-[11px] text-muted-foreground truncate block">
                        {doc.file_name}
                      </span>
                    </div>
                  </div>
                </TableCell>

                {/* Số hiệu & Loại VB */}
                <TableCell>
                  <div className="space-y-0.5">
                    {doc.document_number ? (
                      <div className="flex items-center gap-1 font-mono text-xs text-foreground">
                        <Hash className="size-3 text-muted-foreground" />
                        <span>{doc.document_number}</span>
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground italic">
                        Chưa có số
                      </span>
                    )}
                    {doc.document_type_name && (
                      <span className="text-[11px] text-primary block truncate font-medium">
                        {doc.document_type_name}
                      </span>
                    )}
                  </div>
                </TableCell>

                {/* Trạng thái bóc tách Markdown */}
                <TableCell>
                  {doc.parse_status === "parsed" && (
                    <Badge
                      variant="outline"
                      className="gap-1 text-[11px] py-0 h-5 border-emerald-600/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10"
                    >
                      <CheckCircle2 className="size-3" />
                      Markdown Sạch
                    </Badge>
                  )}
                  {doc.parse_status === "parsing" && (
                    <Badge
                      variant="outline"
                      className="gap-1 text-[11px] py-0 h-5 border-amber-500/30 text-amber-600 dark:text-amber-400 bg-amber-500/10"
                    >
                      <Clock className="size-3 animate-spin" />
                      Đang Xử Lý
                    </Badge>
                  )}
                  {doc.parse_status === "failed" && (
                    <Badge
                      variant="outline"
                      className="gap-1 text-[11px] py-0 h-5 border-destructive/30 text-destructive bg-destructive/10"
                    >
                      <XCircle className="size-3" />
                      Thất Bại
                    </Badge>
                  )}
                  {doc.parse_status === "pending" && (
                    <Badge variant="outline" className="text-[11px] py-0 h-5">
                      Chờ Xử Lý
                    </Badge>
                  )}
                </TableCell>

                {/* Dung lượng */}
                <TableCell className="text-right text-xs font-mono text-muted-foreground">
                  {formatFileSize(doc.file_size_bytes)}
                </TableCell>

                {/* Số Kho Tri Thức */}
                <TableCell className="text-center">
                  {doc.attached_collections_count > 0 ? (
                    <Badge
                      variant="secondary"
                      className="gap-1 text-[11px] py-0 h-5 bg-primary/10 text-primary border-primary/20"
                    >
                      <BookOpen className="size-3" />
                      {doc.attached_collections_count} Kho
                    </Badge>
                  ) : (
                    <span className="text-xs text-muted-foreground">0</span>
                  )}
                </TableCell>

                {/* Ngày tải */}
                <TableCell className="text-xs text-muted-foreground">
                  {new Date(doc.created_at).toLocaleDateString("vi-VN")}
                </TableCell>

                {/* Thao tác */}
                <TableCell className="text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 text-muted-foreground hover:text-foreground"
                      >
                        <MoreHorizontal className="size-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-44">
                      <DropdownMenuItem asChild>
                        <Link
                          to="/documents/$documentId"
                          params={{ documentId: doc.id }}
                          className="gap-2 cursor-pointer"
                        >
                          <ArrowUpRight className="size-4 text-muted-foreground" />
                          Xem Chi Tiết & MD
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <a
                          href={downloadUrl}
                          download={doc.file_name}
                          className="gap-2 cursor-pointer"
                        >
                          <Download className="size-4 text-muted-foreground" />
                          Tải Về Tệp Gốc
                        </a>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => onReparse(doc)}
                        className="gap-2 cursor-pointer"
                      >
                        <RefreshCw className="size-4 text-muted-foreground" />
                        Bóc Tách Lại MD
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={() => onDelete(doc)}
                        className="gap-2 text-destructive focus:text-destructive cursor-pointer"
                      >
                        <Trash2 className="size-4" />
                        Xóa Khỏi Kho
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
