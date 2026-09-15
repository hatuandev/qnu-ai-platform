import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { File, FileSpreadsheet, FileText, UploadCloud, X } from "lucide-react";
import * as React from "react";

export interface FileUploadProps {
  onFileSelect: (file: File | null) => void;
  selectedFile?: File | null;
  accept?: string;
  maxSizeBytes?: number;
  className?: string;
  disabled?: boolean;
}

export function FileUpload({
  onFileSelect,
  selectedFile,
  accept = ".pdf,.docx,.xlsx,.txt",
  maxSizeBytes = 25 * 1024 * 1024, // 25 MB
  className,
  disabled = false,
}: FileUploadProps) {
  const [isDragOver, setIsDragOver] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.size <= maxSizeBytes) {
        onFileSelect(file);
      }
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (file.size <= maxSizeBytes) {
        onFileSelect(file);
      }
    }
  };

  const getFileIcon = (fileName: string) => {
    if (fileName.endsWith(".pdf")) return <FileText className="size-6 text-destructive" />;
    if (fileName.endsWith(".docx") || fileName.endsWith(".doc"))
      return <FileText className="size-6 text-primary" />;
    if (fileName.endsWith(".xlsx") || fileName.endsWith(".xls"))
      return <FileSpreadsheet className="size-6 text-success" />;
    return <File className="size-6 text-muted-foreground" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className={cn("w-full", className)}>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileInputChange}
        disabled={disabled}
        className="hidden"
      />

      {!selectedFile ? (
        <button
          type="button"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !disabled && fileInputRef.current?.click()}
          disabled={disabled}
          aria-label="Tải lên tệp tài liệu"
          className={cn(
            "flex w-full flex-col items-center justify-center rounded-lg border-2 border-dashed border-border p-6 text-center cursor-pointer transition-colors hover:border-primary/50 hover:bg-muted/20 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1",
            isDragOver && "border-primary bg-primary/5",
            disabled && "cursor-not-allowed opacity-50"
          )}
        >
          <div className="flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary mb-3">
            <UploadCloud className="size-5" />
          </div>
          <p className="text-xs font-medium text-foreground">
            Kéo thả tệp tài liệu vào đây hoặc{" "}
            <span className="text-primary font-semibold">chọn từ máy tính</span>
          </p>
          <p className="mt-1 text-[11px] text-muted-foreground">
            Hỗ trợ PDF, DOCX, XLSX, TXT (Dung lượng tối đa{" "}
            {(maxSizeBytes / (1024 * 1024)).toFixed(0)}MB)
          </p>
        </button>
      ) : (
        <div className="flex items-center justify-between rounded-lg border border-border bg-card p-3 shadow-2xs">
          <div className="flex items-center gap-3 min-w-0">
            {getFileIcon(selectedFile.name)}
            <div className="min-w-0">
              <p className="text-xs font-medium text-foreground truncate max-w-[280px]">
                {selectedFile.name}
              </p>
              <p className="text-[11px] text-muted-foreground font-mono">
                {formatFileSize(selectedFile.size)}
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={(e) => {
              e.stopPropagation();
              onFileSelect(null);
              if (fileInputRef.current) fileInputRef.current.value = "";
            }}
            aria-label="Xóa tệp đã chọn"
          >
            <X className="size-4 text-muted-foreground hover:text-destructive" />
          </Button>
        </div>
      )}
    </div>
  );
}
