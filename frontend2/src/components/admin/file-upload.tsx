import { FileText, Image as ImageIcon, UploadCloud, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

type FileUploadProps = {
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
    return <img src={src} alt="" className="size-10 rounded-sm object-cover" />;
  }
  return file.type.startsWith("image/") ? (
    <ImageIcon className="size-5 text-muted-foreground" />
  ) : (
    <FileText className="size-5 text-muted-foreground" />
  );
}

function FileUpload({
  accept,
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
        setError(`Loại tệp của ${file.name} không được hỗ trợ.`);
        continue;
      }
      if (maxSize && file.size > maxSize) {
        setError(`Tệp vượt quá giới hạn ${formatLimit(maxSize)}.`);
        continue;
      }
      accepted.push(file);
    }

    const limit = maxFiles ?? (multiple ? Number.POSITIVE_INFINITY : 1);
    const nextFiles = [...files, ...accepted].slice(0, limit);
    if (accepted.length > nextFiles.length - files.length) {
      setError(`Chỉ được chọn tối đa ${limit} tệp.`);
    }
    updateFiles(multiple ? nextFiles : nextFiles.slice(-1));
  };

  const removeFile = (fileToRemove: File) => {
    updateFiles(files.filter((file) => file !== fileToRemove));
  };

  return (
    <div className={cn("space-y-3", className)}>
      <fieldset
        aria-label="Khu vực tải tệp lên"
        data-dragging={dragging}
        className={cn(
          "rounded-lg border border-dashed p-5 text-center transition-colors duration-[var(--motion-fast)]",
          dragging && "border-primary bg-primary/5",
          disabled && "pointer-events-none opacity-60",
        )}
        onDragEnter={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          if (event.currentTarget === event.target) setDragging(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          if (!disabled) addFiles(Array.from(event.dataTransfer.files));
        }}
      >
        <UploadCloud className="mx-auto size-8 text-muted-foreground" />
        <p className="mt-2 text-sm font-medium">Kéo và thả tệp vào đây</p>
        <p className="type-supporting mt-1 text-muted-foreground">hoặc</p>
        <input
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
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
        >
          Chọn tệp
        </Button>
        <p className="mt-3 text-xs text-muted-foreground">
          {accept ? accept.replaceAll(",", ", ") : "Tất cả định dạng"}
          {maxSize ? ` · tối đa ${formatLimit(maxSize)}` : ""}
        </p>
      </fieldset>
      {error ? (
        <p role="alert" className="type-supporting text-destructive">
          {error}
        </p>
      ) : null}
      {progress !== undefined ? (
        <div className="space-y-1.5">
          <div className="type-supporting flex justify-between">
            <span>{progressLabel}</span>
            <span>{progress}%</span>
          </div>
          <Progress
            value={progress}
            aria-label={`${progressLabel} ${progress}%`}
          />
        </div>
      ) : null}
      {files.length > 0 ? (
        <div className="divide-y rounded-lg border">
          {files.map((file) => (
            <div
              key={`${file.name}-${file.lastModified}`}
              className="flex min-w-0 items-center gap-3 p-3"
            >
              <FilePreview file={file} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {formatFileSize(file.size)}
                </p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label={`Xóa ${file.name}`}
                onClick={() => removeFile(file)}
              >
                <X />
              </Button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export { FileUpload };
