import { Link } from "@tanstack/react-router";
import {
  ArrowUpRight,
  Download,
  FileCode,
  FileSpreadsheet,
  FileText,
  Folders,
  Hash,
  MoreHorizontal,
  Trash2,
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
      return <FileText className="size-4 text-destructive" />;
    case "xlsx":
    case "xls":
      return <FileSpreadsheet className="size-4 text-success" />;
    case "md":
    case "txt":
      return <FileCode className="size-4 text-info" />;
    default:
      return <FileText className="size-4 text-primary" />;
  }
}

export function DocumentsTable({
  documents,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
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
            <TableHead className="w-24 text-center">Định Dạng</TableHead>
            <TableHead className="w-28 text-right">Dung Lượng</TableHead>
            <TableHead className="w-44">Kho Lưu Trực Thuộc</TableHead>
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

                {/* Định dạng */}
                <TableCell className="text-center font-mono text-xs uppercase text-muted-foreground">
                  .{doc.file_type}
                </TableCell>

                {/* Dung lượng */}
                <TableCell className="text-right text-xs font-mono text-muted-foreground">
                  {formatFileSize(doc.file_size_bytes)}
                </TableCell>

                {/* Kho lưu trữ trực thuộc */}
                <TableCell>
                  {doc.groups && doc.groups.length > 0 ? (
                    <div className="flex flex-wrap items-center gap-1">
                      {doc.groups.map((g) => (
                        <Badge
                          key={g.id}
                          variant="outline"
                          className="text-[10px] py-0 h-4 px-1.5 text-muted-foreground bg-muted/30 border-border"
                        >
                          <Folders className="size-2.5 mr-1" />
                          {g.name}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground italic">
                      Chưa gán kho
                    </span>
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
                          Xem Chi Tiết
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
