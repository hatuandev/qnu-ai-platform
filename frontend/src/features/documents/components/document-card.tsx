import { Link } from "@tanstack/react-router";
import {
  ArrowUpRight,
  BookOpen,
  Calendar,
  CheckCircle2,
  Clock,
  Download,
  FileCode,
  FileSpreadsheet,
  FileText,
  Hash,
  MoreVertical,
  RefreshCw,
  Trash2,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { documentsApi } from "@/services/documents-api";
import type { RepositoryDocumentListItem } from "@/types/documents";

interface DocumentCardProps {
  document: RepositoryDocumentListItem;
  selected?: boolean;
  onToggleSelect?: (id: string) => void;
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
      return <FileText className="size-5 text-destructive" />;
    case "xlsx":
    case "xls":
      return <FileSpreadsheet className="size-5 text-success" />;
    case "md":
    case "txt":
      return <FileCode className="size-5 text-info" />;
    default:
      return <FileText className="size-5 text-primary" />;
  }
}

export function DocumentCard({
  document,
  selected = false,
  onToggleSelect,
  onReparse,
  onDelete,
}: DocumentCardProps) {
  const downloadUrl = documentsApi.getDownloadUrl(document.id);

  return (
    <Card
      className={`group relative flex flex-col transition-all duration-200 hover:border-primary/40 hover:shadow-md ${selected ? "border-primary bg-primary/5" : ""}`}
    >
      <CardContent className="flex flex-1 flex-col p-4">
        {/* Header: Checkbox + File icon + Title + Menu */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-2.5 min-w-0">
            {onToggleSelect && (
              <div className="pt-1">
                <Checkbox
                  checked={selected}
                  onCheckedChange={() => onToggleSelect(document.id)}
                  aria-label={`Chọn ${document.title || document.file_name}`}
                />
              </div>
            )}
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted/70 group-hover:bg-primary/10 transition-colors">
              {getFileIcon(document.file_type)}
            </div>
            <div className="min-w-0">
              <Link
                to="/documents/$documentId"
                params={{ documentId: document.id }}
                className="font-medium text-sm text-foreground hover:text-primary transition-colors line-clamp-1"
                title={document.title || document.file_name}
              >
                {document.title || document.file_name}
              </Link>
              <div className="flex items-center gap-2 mt-0.5 text-xs text-muted-foreground truncate">
                <span>{document.file_name}</span>
                <span>•</span>
                <span>{formatFileSize(document.file_size_bytes)}</span>
              </div>
            </div>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="size-7 shrink-0 text-muted-foreground hover:text-foreground"
              >
                <MoreVertical className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem asChild>
                <Link
                  to="/documents/$documentId"
                  params={{ documentId: document.id }}
                  className="gap-2 cursor-pointer"
                >
                  <ArrowUpRight className="size-4 text-muted-foreground" />
                  Xem Chi Tiết & MD
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <a
                  href={downloadUrl}
                  download={document.file_name}
                  className="gap-2 cursor-pointer"
                >
                  <Download className="size-4 text-muted-foreground" />
                  Tải Về Tệp Gốc
                </a>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => onReparse(document)}
                className="gap-2 cursor-pointer"
              >
                <RefreshCw className="size-4 text-muted-foreground" />
                Bóc Tách Lại MD
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => onDelete(document)}
                className="gap-2 text-destructive focus:text-destructive cursor-pointer"
              >
                <Trash2 className="size-4" />
                Xóa Khỏi Kho
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Metadata Badges: Số hiệu & Loại VB */}
        <div className="flex flex-wrap items-center gap-1.5 mt-3.5">
          {document.document_number && (
            <Badge
              variant="outline"
              className="gap-1 font-mono text-[11px] py-0 h-5"
            >
              <Hash className="size-3 text-muted-foreground" />
              {document.document_number}
            </Badge>
          )}

          {document.document_type_name && (
            <Badge
              variant="secondary"
              className="text-[11px] py-0 h-5 bg-primary/10 text-primary border-primary/20"
            >
              {document.document_type_name}
            </Badge>
          )}

          {/* Parse status */}
          {document.parse_status === "parsed" && (
            <Badge
              variant="outline"
              className="gap-1 text-[11px] py-0 h-5 border-success/30 text-success bg-success/10"
            >
              <CheckCircle2 className="size-3" />
              Markdown Sạch
            </Badge>
          )}
          {document.parse_status === "parsing" && (
            <Badge
              variant="outline"
              className="gap-1 text-[11px] py-0 h-5 border-warning/30 text-warning bg-warning/10"
            >
              <Clock className="size-3 animate-spin" />
              Đang Bóc Tách
            </Badge>
          )}
          {document.parse_status === "failed" && (
            <Badge
              variant="outline"
              className="gap-1 text-[11px] py-0 h-5 border-destructive/30 text-destructive bg-destructive/10"
            >
              <XCircle className="size-3" />
              Lỗi Bóc Tách
            </Badge>
          )}

          {document.groups && document.groups.length > 0 && (
            <div className="flex flex-wrap items-center gap-1 w-full pt-1">
              {document.groups.map((g) => (
                <Badge
                  key={g.id}
                  variant="outline"
                  className="text-[10px] py-0 h-4.5 bg-muted/40 text-muted-foreground border-border"
                >
                  {g.name}
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Footer info: Kho tri thức gắn & Ngày tạo */}
        <div className="mt-auto pt-4 border-t border-border/50 flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <BookOpen className="size-3.5 text-primary" />
            <span>
              {document.attached_collections_count > 0 ? (
                <span className="font-medium text-foreground">
                  Gắn trong {document.attached_collections_count} Kho
                </span>
              ) : (
                <span className="text-muted-foreground">Chưa gắn kho nào</span>
              )}
            </span>
          </div>

          <div className="flex items-center gap-1">
            <Calendar className="size-3" />
            <span>
              {new Date(document.created_at).toLocaleDateString("vi-VN")}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
