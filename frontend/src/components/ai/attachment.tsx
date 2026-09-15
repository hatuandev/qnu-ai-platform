import {
  AlertCircle,
  CheckCircle2,
  File,
  FileCode,
  FileImage,
  FileSpreadsheet,
  FileText,
  Loader2,
  X,
} from "lucide-react";
import type React from "react";
import type { ChatAttachment } from "../../hooks/use-rag-stream";
import { cn } from "../../lib/utils";

export interface AttachmentProps {
  attachment: ChatAttachment;
  onRemove?: (id: string) => void;
  className?: string;
}

function getFileIcon(type: string, name: string) {
  const ext = name.split(".").pop()?.toLowerCase() || "";
  if (type.includes("pdf") || ext === "pdf") {
    return <FileText className="h-4 w-4 text-red-500 shrink-0" />;
  }
  if (
    type.includes("sheet") ||
    type.includes("excel") ||
    ext === "xlsx" ||
    ext === "xls" ||
    ext === "csv"
  ) {
    return <FileSpreadsheet className="h-4 w-4 text-emerald-600 shrink-0" />;
  }
  if (type.includes("word") || ext === "docx" || ext === "doc") {
    return <FileText className="h-4 w-4 text-blue-600 shrink-0" />;
  }
  if (type.includes("image") || ["png", "jpg", "jpeg", "webp"].includes(ext)) {
    return <FileImage className="h-4 w-4 text-purple-600 shrink-0" />;
  }
  if (["json", "py", "ts", "js", "html", "css"].includes(ext)) {
    return <FileCode className="h-4 w-4 text-amber-600 shrink-0" />;
  }
  return <File className="h-4 w-4 text-muted-foreground shrink-0" />;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / k ** i).toFixed(1)} ${sizes[i]}`;
}

export const Attachment: React.FC<AttachmentProps> = ({ attachment, onRemove, className }) => {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-2.5 px-3 py-1.5 rounded-control bg-muted/60 hover:bg-muted text-xs border border-border transition-colors group",
        className
      )}
    >
      {getFileIcon(attachment.type, attachment.name)}

      <div className="flex flex-col min-w-0 pr-1">
        <span
          className="font-medium text-foreground truncate max-w-[140px] sm:max-w-[200px]"
          title={attachment.name}
        >
          {attachment.name}
        </span>
        <span className="text-[11px] text-muted-foreground">{formatBytes(attachment.size)}</span>
      </div>

      {attachment.ocrStatus && attachment.ocrStatus !== "idle" && (
        <span className="shrink-0">
          {attachment.ocrStatus === "processing" && (
            <span
              className="inline-flex items-center gap-1 text-[10px] text-info bg-info/10 px-1.5 py-0.5 rounded-micro"
              title="Đang bóc tách OCR đa tầng"
            >
              <Loader2 className="h-3 w-3 animate-spin" />
              OCR
            </span>
          )}
          {attachment.ocrStatus === "completed" && (
            <span
              className="inline-flex items-center gap-1 text-[10px] text-success bg-success/10 px-1.5 py-0.5 rounded-micro"
              title="Bóc tách OCR thành công"
            >
              <CheckCircle2 className="h-3 w-3" />
              Sẵn sàng
            </span>
          )}
          {attachment.ocrStatus === "failed" && (
            <span
              className="inline-flex items-center gap-1 text-[10px] text-destructive bg-destructive/10 px-1.5 py-0.5 rounded-micro"
              title="Lỗi bóc tách OCR"
            >
              <AlertCircle className="h-3 w-3" />
              Lỗi
            </span>
          )}
        </span>
      )}

      {onRemove && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove(attachment.id);
          }}
          className="text-muted-foreground hover:text-destructive p-0.5 rounded-micro transition-colors shrink-0"
          title="Xóa tệp đính kèm"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
};
