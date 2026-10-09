import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronUp,
  FileStack,
  Loader2,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  Upload,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { FileUpload } from "@/components/admin/file-upload";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  type DocumentTypeItem,
  documentTypesApi,
} from "@/services/document-types-api";
import { documentsApi } from "@/services/documents-api";

interface DocumentUploadModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

interface UploadProgressState {
  current: number;
  total: number;
  currentFileName: string;
  percent: number;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentUploadModal({
  open,
  onOpenChange,
  onSuccess,
}: DocumentUploadModalProps) {
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<File[]>([]);
  const [issuingAuthority, setIssuingAuthority] = useState(
    "Trường Đại học Quy Nhơn",
  );
  const [documentTypeCode, setDocumentTypeCode] = useState("");
  const [autoParse, setAutoParse] = useState(true);
  const [showBatchOptions, setShowBatchOptions] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progressState, setProgressState] =
    useState<UploadProgressState | null>(null);

  // Lấy danh mục loại văn bản
  const { data: documentTypes = [] } = useQuery({
    queryKey: ["document-types"],
    queryFn: () => documentTypesApi.listDocumentTypes(),
  });

  // Tính tổng dung lượng các tệp đã chọn
  const totalSizeBytes = useMemo(
    () => files.reduce((acc, f) => acc + f.size, 0),
    [files],
  );

  const resetForm = () => {
    setFiles([]);
    setDocumentTypeCode("");
    setIssuingAuthority("Trường Đại học Quy Nhơn");
    setShowBatchOptions(false);
    setProgressState(null);
    setIsUploading(false);
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (isUploading) return; // Ngăn đóng modal khi đang tải lên
    if (!nextOpen) {
      resetForm();
    }
    onOpenChange(nextOpen);
  };

  const handleBatchUpload = async () => {
    if (files.length === 0) {
      toast.error("Vui lòng chọn hoặc kéo thả ít nhất 1 tệp văn bản.");
      return;
    }

    setIsUploading(true);
    let successCount = 0;
    const errors: string[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const percent = Math.round(((i + 1) / files.length) * 100);
      setProgressState({
        current: i + 1,
        total: files.length,
        currentFileName: file.name,
        percent,
      });

      try {
        await documentsApi.uploadDocument(file, {
          issuing_authority: issuingAuthority.trim() || undefined,
          document_type_code: documentTypeCode || undefined,
          auto_parse: autoParse,
        });
        successCount++;
      } catch (err: unknown) {
        const errorMsg =
          err instanceof Error ? err.message : "Tải lên thất bại";
        errors.push(`${file.name}: ${errorMsg}`);
      }
    }

    setIsUploading(false);
    setProgressState(null);

    // Đồng bộ lại dữ liệu
    queryClient.invalidateQueries({ queryKey: ["repository-documents"] });
    queryClient.invalidateQueries({ queryKey: ["repository-stats"] });

    if (errors.length === 0) {
      toast.success(
        `Đã nạp thành công toàn bộ ${successCount} tệp vào Kho Tài Liệu! Tất cả đang được tự động bóc tách.`,
      );
      resetForm();
      onOpenChange(false);
      onSuccess?.();
    } else if (successCount > 0) {
      toast.warning(
        `Đã nạp thành công ${successCount}/${files.length} tệp. ${errors.length} tệp gặp sự cố.`,
      );
      resetForm();
      onOpenChange(false);
      onSuccess?.();
    } else {
      toast.error(`Không thể nạp tệp nào: ${errors[0]}`);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <FileStack className="size-5" />
            </div>
            <div>
              <DialogTitle>Tải Tài Liệu Vào Kho Tập Trung</DialogTitle>
              <DialogDescription>
                Hỗ trợ kéo thả nhiều tệp, lưu trữ MinIO S3 chống trùng lặp và tự
                động nhận diện bóc tách.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* File Drag & Drop (Nhiều tệp) */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-foreground">
                Tệp tài liệu văn bản <span className="text-destructive">*</span>
              </span>
              {files.length > 0 && !isUploading && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">
                    Đã chọn {files.length} tệp ({formatBytes(totalSizeBytes)})
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setFiles([])}
                    className="h-6 gap-1 px-1.5 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive"
                  >
                    <Trash2 className="size-3" />
                    Xóa tất cả
                  </Button>
                </div>
              )}
            </div>

            <FileUpload
              accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md"
              multiple={true}
              maxFiles={50}
              maxSize={50 * 1024 * 1024}
              value={files}
              onFilesChange={setFiles}
              disabled={isUploading}
            />
          </div>

          {/* Banner Nhận diện thông minh (AI & NĐ 30 Engine) */}
          <div className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs leading-relaxed">
            <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/15 text-primary">
              <Sparkles className="size-3.5" />
            </div>
            <div className="space-y-0.5">
              <p className="font-semibold text-foreground">
                Tự động nhận diện thể thức văn bản (Nghị định 30/2020/NĐ-CP)
              </p>
              <p className="text-muted-foreground">
                Hệ thống tự động phân tích và trích xuất{" "}
                <span className="font-medium text-foreground">
                  Số hiệu, Ngày ban hành, Tiêu đề trích yếu và Người ký
                </span>{" "}
                từ nội dung từng văn bản sau khi tải lên. Bạn không cần phải
                nhập thủ công.
              </p>
            </div>
          </div>

          {/* Cấu hình chung cho lô tải lên (Collapsible tùy chọn) */}
          <Collapsible
            open={showBatchOptions}
            onOpenChange={setShowBatchOptions}
            className="rounded-lg border border-border/70 bg-card/60 p-2.5 transition-colors"
          >
            <CollapsibleTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="w-full justify-between h-8 px-2 text-xs font-medium text-muted-foreground hover:text-foreground"
                disabled={isUploading}
              >
                <div className="flex items-center gap-1.5">
                  <SlidersHorizontal className="size-3.5 text-primary" />
                  <span>Cấu hình chung cho lô tệp (Tùy chọn)</span>
                </div>
                {showBatchOptions ? (
                  <ChevronUp className="size-3.5" />
                ) : (
                  <ChevronDown className="size-3.5" />
                )}
              </Button>
            </CollapsibleTrigger>

            <CollapsibleContent className="space-y-3 pt-3">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <span className="text-xs font-medium text-foreground">
                    Loại văn bản chung
                  </span>
                  <Select
                    value={documentTypeCode}
                    onValueChange={setDocumentTypeCode}
                    disabled={isUploading}
                  >
                    <SelectTrigger className="h-9">
                      <SelectValue placeholder="Tự động nhận diện..." />
                    </SelectTrigger>
                    <SelectContent className="max-h-56">
                      <SelectItem value="">
                        Tự động nhận diện theo tệp
                      </SelectItem>
                      {documentTypes.map((dt: DocumentTypeItem) => (
                        <SelectItem key={dt.code} value={dt.code}>
                          {dt.name} ({dt.code})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <span className="text-xs font-medium text-foreground">
                    Cơ quan / Đơn vị ban hành
                  </span>
                  <Input
                    className="h-9 text-xs"
                    placeholder="Trường Đại học Quy Nhơn"
                    value={issuingAuthority}
                    onChange={(e) => setIssuingAuthority(e.target.value)}
                    disabled={isUploading}
                  />
                </div>
              </div>
            </CollapsibleContent>
          </Collapsible>

          {/* Checkbox Auto Parse */}
          <div className="flex items-start space-x-2.5 rounded-lg border border-border/60 bg-muted/20 p-3">
            <Checkbox
              id="auto-parse-checkbox"
              checked={autoParse}
              onCheckedChange={(checked) => setAutoParse(Boolean(checked))}
              disabled={isUploading}
              className="mt-0.5"
            />
            <label
              htmlFor="auto-parse-checkbox"
              className="text-xs text-foreground cursor-pointer select-none leading-relaxed"
            >
              <span className="font-semibold text-primary">
                Tự động bóc tách sang Markdown sạch ngay lập tức
              </span>
              <br />
              <span className="text-muted-foreground">
                Trích xuất tiêu đề, bảng biểu, cấu trúc văn bản và chuẩn hóa NFC
                Tiếng Việt sẵn sàng nạp vào mọi Kho Tri Thức.
              </span>
            </label>
          </div>

          {/* Progress bar khi đang tải lên nhiều tệp */}
          {progressState && (
            <div className="space-y-1.5 rounded-lg border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-foreground">
                  Đang tải lên tệp {progressState.current}/{progressState.total}
                </span>
                <span className="font-semibold text-primary">
                  {progressState.percent}%
                </span>
              </div>
              <Progress
                value={progressState.percent}
                className="h-2"
                aria-label={`Tiến độ tải lên ${progressState.percent}%`}
              />
              <p className="truncate text-xs text-muted-foreground">
                Tệp hiện tại:{" "}
                <span className="font-medium text-foreground">
                  {progressState.currentFileName}
                </span>
              </p>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isUploading}
          >
            Hủy Bỏ
          </Button>
          <Button
            onClick={handleBatchUpload}
            disabled={isUploading || files.length === 0}
            className="gap-1.5"
          >
            {isUploading ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Đang Tải Lên (
                {progressState
                  ? `${progressState.current}/${progressState.total}`
                  : "..."}
                )...
              </>
            ) : (
              <>
                <Upload className="size-4" />
                {files.length > 1
                  ? `Lưu ${files.length} Tệp Vào Kho`
                  : "Lưu Vào Kho Tài Liệu"}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
