import { FileText, Loader2, Upload, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { useUploadSourceMutation } from "@/api/knowledge/queries";
import type { FolderResponse, SourceResponse } from "@/api/knowledge/types";
import { useCreatePreparationIntentMutation } from "@/api/preparation/queries";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useBackgroundTasksStore } from "@/lib/background-tasks-store";

const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".xlsx"];
const MAX_FILE_SIZE = 60 * 1024 * 1024; // 60 MB

export function SourceUploadDialog({
  open,
  onOpenChange,
  workspaceId,
  collectionId,
  folders = [],
  defaultFolderId,
  initialFile,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collectionId: string;
  folders?: FolderResponse[];
  defaultFolderId?: string | null;
  initialFile?: File | null;
  onSuccess?: (source: SourceResponse) => void;
}) {
  const uploadMutation = useUploadSourceMutation(workspaceId, collectionId);
  const prepareMutation = useCreatePreparationIntentMutation(
    workspaceId,
    collectionId,
  );
  const registerPreparationTask = useBackgroundTasksStore(
    (s) => s.registerPreparationTask,
  );

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [folderId, setFolderId] = useState<string>("root");
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState<string>("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setSelectedFile(initialFile ?? null);
      setTitle(
        initialFile?.name.replace(/\.[^/.]+$/, "").replace(/_/g, " ") ?? "",
      );
      setFolderId(defaultFolderId || "root");
      setError(null);
      setIsUploading(false);
      setUploadStep("");
    }
  }, [open, initialFile, defaultFolderId]);

  const handleFileChange = (file: File | null) => {
    if (!file) {
      setSelectedFile(null);
      return;
    }

    const ext = `.${file.name.split(".").pop()?.toLowerCase()}`;
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError("Chỉ hỗ trợ tệp định dạng .docx, .pdf hoặc .xlsx");
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setError("Dung lượng tệp vượt quá giới hạn 60 MB");
      return;
    }

    setError(null);
    setSelectedFile(file);
    if (!title) {
      setTitle(file.name.replace(/\.[^/.]+$/, "").replace(/_/g, " "));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Vui lòng chọn tệp văn bản");
      return;
    }

    setError(null);
    setIsUploading(true);
    setUploadStep("Đang tải tệp lên máy chủ...");

    try {
      // 1. Pack FormData
      const formData = new FormData();
      formData.append("file", selectedFile);
      if (title.trim()) {
        formData.append("title", title.trim());
      }
      if (folderId !== "root") {
        formData.append("folder_id", folderId);
      }
      formData.append("auto_extract", "true");

      const uploadIdempotencyKey = `up_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

      // 2. Upload source
      const res = await uploadMutation.mutateAsync({
        formData,
        idempotencyKey: uploadIdempotencyKey,
      });

      setUploadStep("Khởi chạy tiến trình chuẩn bị nội dung AI...");

      // 3. Immediately queue preparation intent in background
      const prepIdempotencyKey = `prep_${res.source.id}_${res.revision.id}`;
      try {
        const prepRes = await prepareMutation.mutateAsync({
          sourceId: res.source.id,
          input: {
            mode: "auto",
            revision_id: res.revision.id,
          },
          idempotencyKey: prepIdempotencyKey,
        });

        // 4. Register to background tasks bar
        registerPreparationTask({
          id: prepRes.intent.id,
          workspaceId,
          collectionId,
          sourceId: res.source.id,
          sourceTitle: res.source.title,
          fileName: res.source.file_name,
        });
      } catch (prepErr) {
        // If preparation trigger fails, the upload itself was still successful!
        console.warn("Preparation trigger warning:", prepErr);
      }

      toast.success(`Đã tải lên "${res.source.title}"!`, {
        description: "Hệ thống đang chuẩn bị nội dung và bóc tách ngầm.",
      });

      onOpenChange(false);
      onSuccess?.(res.source);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Có lỗi xảy ra khi tải lên";
      setError(msg);
      toast.error(msg);
    } finally {
      setIsUploading(false);
      setUploadStep("");
    }
  };

  return (
    <Dialog open={open} onOpenChange={isUploading ? undefined : onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <Upload className="size-4 text-primary" />
              <span>Tải tài liệu vào kho</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Hỗ trợ văn bản Word (.docx), PDF (.pdf) hoặc bảng tính (.xlsx).
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="p-2.5 rounded-md bg-destructive/10 border border-destructive/20 text-xs text-destructive">
              {error}
            </div>
          )}

          {isUploading && uploadStep && (
            <div className="p-3 rounded-lg bg-primary/10 border border-primary/20 flex items-center gap-2.5 text-xs text-primary font-medium">
              <Loader2 className="size-4 animate-spin shrink-0" />
              <span>{uploadStep}</span>
            </div>
          )}

          <div className="space-y-3">
            {/* File selector zone */}
            {!selectedFile ? (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full border-2 border-dashed border-border/80 hover:border-primary/60 rounded-xl p-6 text-center cursor-pointer transition-colors bg-muted/20 hover:bg-muted/40 block"
              >
                <div className="size-10 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto mb-2">
                  <Upload className="size-5" />
                </div>
                <div className="text-xs font-semibold text-foreground">
                  Nhấp để chọn tệp từ máy tính
                </div>
                <div className="text-[11px] text-muted-foreground mt-1">
                  .DOCX, .PDF, .XLSX (Tối đa 60 MB)
                </div>
              </button>
            ) : (
              <div className="flex items-center justify-between p-2.5 rounded-lg border border-border/70 bg-card">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="size-8 rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0">
                    <FileText className="size-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium text-foreground truncate">
                      {selectedFile.name}
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </div>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedFile(null)}
                  disabled={isUploading}
                  className="size-7 p-0 text-muted-foreground hover:text-foreground"
                >
                  <X className="size-3.5" />
                </Button>
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.xlsx"
              className="hidden"
              onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
            />

            <Field>
              <FieldLabel>Tiêu đề tài liệu</FieldLabel>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Tên hiển thị nhận diện tài liệu..."
                className="h-8 text-xs"
                disabled={isUploading}
              />
              <FieldDescription>
                Nếu để trống sẽ sử dụng tên tệp gốc.
              </FieldDescription>
            </Field>

            <Field>
              <FieldLabel>Thư mục lưu trữ</FieldLabel>
              <Select
                value={folderId}
                onValueChange={setFolderId}
                disabled={isUploading}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="Chọn thư mục..." />
                </SelectTrigger>
                <SelectContent className="text-xs">
                  <SelectItem value="root">📁 Gốc kho tri thức</SelectItem>
                  {folders.map((f) => (
                    <SelectItem key={f.id} value={f.id}>
                      📁 {f.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={isUploading}
              className="h-8 text-xs"
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={!selectedFile || isUploading}
              className="h-8 text-xs gap-1.5"
            >
              {isUploading ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Upload className="size-3.5" />
              )}
              <span>Tải lên</span>
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
