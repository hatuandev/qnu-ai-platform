import {
  AlertCircle,
  File,
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  Plus,
  Trash2,
  Upload,
  UploadCloud,
  X,
} from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

export type FileUploadProps = {
  id?: string;
  accept?: string;
  acceptLabel?: string;
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
  if (size === 0) return "0 B";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function formatLimit(size?: number): string {
  if (!size) return "";
  return size >= 1024 * 1024
    ? `${Math.round(size / (1024 * 1024))} MB`
    : `${Math.round(size / 1024)} KB`;
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

function getFileInfo(file: File) {
  const name = file.name.toLowerCase();
  const ext = file.name.split(".").pop()?.toUpperCase() || "";

  if (name.endsWith(".pdf") || file.type === "application/pdf") {
    return {
      label: "PDF",
      badgeColor: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
      icon: FileText,
      iconColor: "text-rose-600 dark:text-rose-400",
    };
  }
  if (
    name.endsWith(".docx") ||
    name.endsWith(".doc") ||
    file.type.includes("word") ||
    file.type.includes("officedocument.wordprocessingml")
  ) {
    return {
      label: ext || "DOCX",
      badgeColor: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
      icon: FileText,
      iconColor: "text-blue-600 dark:text-blue-400",
    };
  }
  if (
    name.endsWith(".xlsx") ||
    name.endsWith(".xls") ||
    name.endsWith(".csv") ||
    file.type.includes("spreadsheet") ||
    file.type.includes("excel")
  ) {
    return {
      label: ext || "XLSX",
      badgeColor: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
      icon: FileSpreadsheet,
      iconColor: "text-emerald-600 dark:text-emerald-400",
    };
  }
  if (file.type.startsWith("image/")) {
    return {
      label: ext || "IMG",
      badgeColor: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
      icon: ImageIcon,
      iconColor: "text-amber-600 dark:text-amber-400",
    };
  }
  return {
    label: ext || "FILE",
    badgeColor: "bg-muted text-muted-foreground border-border",
    icon: File,
    iconColor: "text-muted-foreground",
  };
}

function FilePreview({ file }: { file: File }) {
  const [src, setSrc] = useState<string>();
  const info = getFileInfo(file);
  const IconComponent = info.icon;

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
        className="size-9 rounded-lg object-cover border border-border/60 shadow-2xs"
      />
    );
  }

  return (
    <div
      className={cn(
        "flex size-9 shrink-0 items-center justify-center rounded-lg border shadow-2xs transition-transform group-hover:scale-105",
        info.badgeColor,
      )}
    >
      <IconComponent className={cn("size-4", info.iconColor)} />
    </div>
  );
}

function FileUpload({
  id,
  accept,
  acceptLabel,
  multiple = false,
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

  const totalBytes = files.reduce((acc, f) => acc + f.size, 0);

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
        setError(`Tệp "${file.name}" vượt quá giới hạn ${formatLimit(maxSize)}.`);
        continue;
      }
      // Tránh thêm file trùng lặp hoàn toàn trong cùng đợt chọn
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

    if (accepted.length === 0 && incoming.length > 0) {
      return;
    }

    const limit = maxFiles ?? (multiple ? Number.POSITIVE_INFINITY : 1);
    const nextFiles = multiple
      ? [...files, ...accepted].slice(0, limit)
      : accepted.slice(0, 1);

    if (multiple && maxFiles && files.length + accepted.length > limit) {
      setError(`Chỉ được chọn tối đa ${limit} tệp.`);
    }

    updateFiles(nextFiles);
  };

  const removeFile = (fileToRemove: File) => {
    updateFiles(files.filter((file) => file !== fileToRemove));
  };

  // Trích xuất danh sách nhãn định dạng hiển thị đẹp mắt
  const formatBadges = acceptLabel
    ? acceptLabel.split(",").map((s) => s.trim().toUpperCase())
    : accept
      ? accept
          .split(",")
          .map((s) => s.trim().replace(/^\./, "").toUpperCase())
          .filter((s) => s.length <= 6 && !s.includes("/"))
      : [];

  return (
    <div className={cn("space-y-3", className)}>
      {/* Ẩn input file gốc, kích hoạt thông qua Label hoặc Ref */}
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

      {/* Trường hợp 1: Chưa chọn tệp nào -> Dropzone to rõ, trực quan */}
      {files.length === 0 ? (
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
            "group relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-border/80 bg-muted/20 text-center transition-all duration-200 select-none",
            disabled
              ? "pointer-events-none opacity-50 cursor-not-allowed"
              : "cursor-pointer hover:border-primary/60 hover:bg-muted/35",
            "p-6 sm:p-7",
            dragging && "border-primary bg-primary/10 ring-2 ring-primary/20 scale-[0.99]",
          )}
        >
          <div
            className={cn(
              "flex size-13 items-center justify-center rounded-2xl bg-primary/10 text-primary border border-primary/20 shadow-xs transition-transform duration-200 group-hover:scale-105",
              dragging && "scale-110 bg-primary/20 animate-pulse",
            )}
          >
            <UploadCloud className="size-6 text-primary" />
          </div>

          <div className="mt-3 space-y-1">
            <p className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
              {dragging
                ? "Thả các tệp vào đây ngay..."
                : "Kéo và thả tệp vào đây, hoặc nhấn để chọn"}
            </p>
            <p className="text-xs text-muted-foreground">
              {multiple
                ? "Hỗ trợ chọn hoặc thả nhiều tệp cùng lúc"
                : "Hỗ trợ tải lên 1 tệp tài liệu"}
            </p>
          </div>

          {/* Huy hiệu định dạng & dung lượng tối đa */}
          <div className="mt-3 flex flex-wrap items-center justify-center gap-1.5">
            {formatBadges.length > 0 ? (
              formatBadges.map((badge) => (
                <Badge
                  key={badge}
                  variant="secondary"
                  className="px-2 py-0 text-[10px] font-mono font-semibold bg-background/80 text-foreground border border-border/70 shadow-2xs"
                >
                  .{badge}
                </Badge>
              ))
            ) : (
              <span className="text-xs text-muted-foreground">
                {accept ? accept.replaceAll(",", " · ") : "Tất cả định dạng"}
              </span>
            )}
            {maxSize ? (
              <span className="text-xs text-muted-foreground">
                · Tối đa {formatLimit(maxSize)}/tệp
              </span>
            ) : null}
          </div>

          <div className="mt-3.5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={disabled}
              className="h-8 pointer-events-none border-primary/30 text-primary shadow-2xs group-hover:bg-primary group-hover:text-primary-foreground transition-colors gap-1.5 text-xs font-medium"
              tabIndex={-1}
            >
              <Upload className="size-3.5" />
              <span>Duyệt tệp từ thiết bị</span>
            </Button>
          </div>
        </label>
      ) : (
        /* Trường hợp 2: Đã có tệp được chọn -> Thanh công cụ + Danh sách tệp + Dải thả thêm */
        <div className="space-y-2.5">
          {/* Thanh tổng quan & Thao tác nhanh */}
          <div className="flex items-center justify-between px-1 text-xs">
            <div className="flex items-center gap-1.5 font-medium text-foreground">
              <span>
                Đã chọn <strong className="text-primary font-semibold">{files.length}</strong> tệp
              </span>
              <span className="text-muted-foreground">({formatFileSize(totalBytes)})</span>
            </div>
            <div className="flex items-center gap-1.5">
              {multiple && (!maxFiles || files.length < maxFiles) ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={disabled}
                  onClick={() => inputRef.current?.click()}
                  className="h-7 px-2 text-xs text-primary gap-1 hover:bg-primary/10"
                >
                  <Plus className="size-3.5" />
                  <span>Thêm tệp</span>
                </Button>
              ) : null}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={disabled}
                onClick={() => updateFiles([])}
                className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/10 gap-1"
              >
                <Trash2 className="size-3.5" />
                <span>Xóa hết</span>
              </Button>
            </div>
          </div>

          {/* Dải thả tệp bổ sung (nếu cho phép multiple và chưa vượt giới hạn) */}
          {multiple && (!maxFiles || files.length < maxFiles) ? (
            <label
              htmlFor={disabled ? undefined : inputId}
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
                "flex items-center justify-center gap-2 rounded-lg border border-dashed py-2.5 px-3 text-xs text-muted-foreground transition-all duration-150 select-none",
                disabled
                  ? "pointer-events-none opacity-50"
                  : "cursor-pointer hover:border-primary/50 hover:bg-muted/30 hover:text-foreground",
                dragging
                  ? "border-primary bg-primary/10 text-primary font-medium"
                  : "border-border/80 bg-muted/20",
              )}
            >
              <UploadCloud className="size-3.5 text-primary shrink-0" />
              <span>
                {dragging
                  ? "Thả tệp vào đây để thêm..."
                  : "Kéo thả thêm tệp vào đây hoặc nhấn để chọn thêm"}
              </span>
            </label>
          ) : null}

          {/* Danh sách thẻ tệp đã chọn */}
          <div className="max-h-48 overflow-y-auto space-y-2 pr-0.5">
            {files.map((file) => {
              const info = getFileInfo(file);
              return (
                <div
                  key={`${file.name}-${file.size}-${file.lastModified}`}
                  className="group flex items-center justify-between gap-3 rounded-lg border border-border/70 bg-card p-2.5 shadow-2xs transition-all hover:border-primary/30 hover:shadow-xs"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <FilePreview file={file} />
                    <div className="min-w-0">
                      <p
                        className="truncate text-xs font-semibold text-foreground max-w-[260px] sm:max-w-[320px]"
                        title={file.name}
                      >
                        {file.name}
                      </p>
                      <p className="text-[11px] text-muted-foreground flex items-center gap-1.5 mt-0.5">
                        <span>{formatFileSize(file.size)}</span>
                        <span>·</span>
                        <span className="uppercase text-[10px] font-mono tracking-wider font-semibold text-muted-foreground">
                          {info.label}
                        </span>
                      </p>
                    </div>
                  </div>

                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    disabled={disabled}
                    aria-label={`Xóa ${file.name}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(file);
                    }}
                    className="size-7 rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors shrink-0"
                  >
                    <X className="size-3.5" />
                  </Button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Thông báo lỗi chọn tệp */}
      {error ? (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-2.5 text-xs text-destructive"
        >
          <AlertCircle className="size-4 shrink-0 mt-0.5" />
          <span className="font-medium">{error}</span>
        </div>
      ) : null}

      {/* Thanh tiến trình khi đang upload */}
      {progress !== undefined ? (
        <div className="space-y-1.5 rounded-xl border border-primary/20 bg-primary/5 p-3">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-primary flex items-center gap-2 truncate pr-2">
              <span className="relative flex size-2 shrink-0">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                <span className="relative inline-flex size-2 rounded-full bg-primary" />
              </span>
              <span className="truncate">{progressLabel}</span>
            </span>
            <span className="font-mono font-bold text-primary shrink-0">{progress}%</span>
          </div>
          <Progress value={progress} className="h-1.5" />
        </div>
      ) : null}
    </div>
  );
}

export { FileUpload };
