import {
  FileCode,
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  UploadCloud,
  X,
} from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

type FileUploadProps = {
  id?: string;
  accept?: string;
  multiple?: boolean;
  maxFiles?: number;
  maxSize?: number;
  disabled?: boolean;
  value?: File[];
  onFilesChange?: (files: File[]) => void;
  progress?: number;
  progressLabel?: string;
  className?: string;
};

function formatFileSize(size: number): string {
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function formatLimit(size?: number): string {
  if (!size) return "";
  return size >= 1024 * 1024
    ? `${size / (1024 * 1024)} MB`
    : `${size / 1024} KB`;
}

function fileMatchesAccept(file: File, accept?: string): boolean {
  if (!accept) return true;
  return accept.split(",").some((rule) => {
    const normalized = rule.trim().toLowerCase();
    if (!normalized) return false;
    if (normalized.startsWith("."))
      return file.name.toLowerCase().endsWith(normalized);
    if (normalized.endsWith("/*"))
      return file.type.startsWith(normalized.slice(0, -1));
    return file.type.toLowerCase() === normalized;
  });
}

function FilePreview({ file }: { file: File }) {
  const [src, setSrc] = useState<string>();

  useEffect(() => {
    if (!file.type.startsWith("image/")) return;
    const objectUrl = URL.createObjectURL(file);
    setSrc(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  if (src) {
    return (
      <img
        src={src}
        alt=""
        className="size-9 rounded-md object-cover border border-border/60"
      />
    );
  }

  const nameLower = file.name.toLowerCase();
  let IconComponent = FileText;
  if (nameLower.endsWith(".xlsx") || nameLower.endsWith(".xls")) {
    IconComponent = FileSpreadsheet;
  } else if (nameLower.endsWith(".txt") || nameLower.endsWith(".md")) {
    IconComponent = FileCode;
  } else if (file.type.startsWith("image/")) {
    IconComponent = ImageIcon;
  }

  return (
    <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary border border-primary/20">
      <IconComponent className="size-4" />
    </div>
  );
}

function getFileExtension(filename: string): string {
  const parts = filename.split(".");
  return parts.length > 1 ? (parts.pop()?.toUpperCase() ?? "") : "";
}

function FileUpload({
  id,
  accept,
  multiple = true,
  maxFiles,
  maxSize,
  disabled,
  value,
  onFilesChange,
  progress,
  progressLabel = "Đang tải",
  className,
}: FileUploadProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const inputRef = useRef<HTMLInputElement>(null);
  const [internalFiles, setInternalFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string>();
  const files = value ?? internalFiles;

  const updateFiles = (nextFiles: File[]) => {
    if (value === undefined) setInternalFiles(nextFiles);
    onFilesChange?.(nextFiles);
  };

  const addFiles = (incoming: File[]) => {
    setError(undefined);
    const accepted: File[] = [];
    for (const file of incoming) {
      if (!fileMatchesAccept(file, accept)) {
        setError(`Loại tệp "${file.name}" không được hỗ trợ.`);
        continue;
      }
      if (maxSize && file.size > maxSize) {
        setError(
          `Tệp "${file.name}" vượt quá giới hạn ${formatLimit(maxSize)}.`,
        );
        continue;
      }
      // Tránh thêm file trùng lặp hoàn toàn
      const isDuplicate = files.some(
        (f) =>
          f.name === file.name &&
          f.size === file.size &&
          f.lastModified === file.lastModified,
      );
      if (!isDuplicate) {
        accepted.push(file);
      }
    }

    if (accepted.length === 0 && incoming.length > 0 && !error) {
      return;
    }

    const limit = maxFiles ?? (multiple ? Number.POSITIVE_INFINITY : 1);
    const nextFiles = multiple
      ? [...files, ...accepted].slice(0, limit)
      : accepted.slice(0, 1);

    if (files.length + accepted.length > limit) {
      setError(`Chỉ được chọn tối đa ${limit} tệp.`);
    }
    updateFiles(nextFiles);
  };

  const removeFile = (fileToRemove: File) => {
    updateFiles(files.filter((file) => file !== fileToRemove));
  };

  return (
    <div className={cn("space-y-3", className)}>
      {/* Vùng Dropzone bấm được toàn diện thông qua Semantic Label */}
      <label
        htmlFor={disabled ? undefined : inputId}
        data-dragging={dragging}
        onDragEnter={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={(event) => {
          if (event.currentTarget === event.target) setDragging(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          if (!disabled) addFiles(Array.from(event.dataTransfer.files));
        }}
        className={cn(
          "group relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border/80 bg-muted/10 text-center transition-all duration-200 select-none",
          disabled
            ? "pointer-events-none opacity-60 cursor-not-allowed"
            : "cursor-pointer hover:border-primary/60 hover:bg-primary/5",
          files.length > 0 ? "p-4 sm:p-5" : "p-6 sm:p-7",
          dragging && "border-primary bg-primary/10 scale-[1.01] shadow-inner",
        )}
      >
        <input
          id={inputId}
          ref={inputRef}
          type="file"
          className="sr-only"
          accept={accept}
          multiple={multiple}
          disabled={disabled}
          onChange={(event) => {
            if (event.target.files) addFiles(Array.from(event.target.files));
            event.target.value = "";
          }}
        />

        <div
          className={cn(
            "flex size-11 items-center justify-center rounded-full bg-primary/10 text-primary border border-primary/20 transition-transform duration-200 group-hover:scale-110",
            dragging && "scale-110 bg-primary/20 animate-pulse",
          )}
        >
          <UploadCloud className="size-5" />
        </div>

        <div className="mt-2.5 space-y-0.5">
          <p className="text-xs sm:text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
            {dragging
              ? "Thả các tệp vào đây ngay..."
              : files.length > 0
                ? multiple
                  ? "Kéo thả thêm tệp vào đây, hoặc nhấn để chọn thêm"
                  : "Kéo thả tệp mới vào đây để thay thế"
                : multiple
                  ? "Kéo và thả tệp vào đây, hoặc nhấn để chọn"
                  : "Kéo và thả tệp vào đây, hoặc nhấn để chọn"}
          </p>
          <p className="text-[11px] sm:text-xs text-muted-foreground">
            {multiple
              ? "Hỗ trợ chọn nhiều tài liệu cùng lúc (Ctrl / Shift + Click)"
              : "Hỗ trợ tải lên 1 tài liệu"}
          </p>
        </div>

        <p className="mt-2 text-[11px] text-muted-foreground/80">
          {accept ? accept.replaceAll(",", " · ") : "Tất cả định dạng"}
          {maxSize ? ` · Tối đa ${formatLimit(maxSize)}` : ""}
        </p>
      </label>

      {error ? (
        <p role="alert" className="text-xs text-destructive">
          {error}
        </p>
      ) : null}

      {progress !== undefined ? (
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span>{progressLabel}</span>
            <span className="font-medium">{progress}%</span>
          </div>
          <Progress
            value={progress}
            aria-label={`${progressLabel} ${progress}%`}
          />
        </div>
      ) : null}

      {/* Danh sách tệp đã chọn */}
      {files.length > 0 ? (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground px-0.5">
            <span>Danh sách tệp chuẩn bị tải lên ({files.length}):</span>
          </div>
          <div className="max-h-48 overflow-y-auto divide-y divide-border/60 rounded-lg border border-border/70 bg-card/60">
            {files.map((file) => {
              const ext = getFileExtension(file.name);
              return (
                <div
                  key={`${file.name}-${file.size}-${file.lastModified}`}
                  className="flex min-w-0 items-center gap-3 p-2.5 hover:bg-muted/30 transition-colors"
                >
                  <FilePreview file={file} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <p className="truncate text-xs font-medium text-foreground">
                        {file.name}
                      </p>
                      {ext && (
                        <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[9px] font-semibold text-muted-foreground">
                          {ext}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={`Xóa ${file.name}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(file);
                    }}
                    disabled={disabled}
                    className="size-7 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                  >
                    <X className="size-3.5" />
                  </Button>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export { FileUpload };
