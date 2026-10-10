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
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { FileUpload } from "@/components/admin/file-upload";
import { Button } from "@/components/ui/button";
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
  groupId?: string;
  groupName?: string;
}

interface UploadProgressState {
  current: number;
  total: number;
  currentFileName: string;
  percent: number;
}

export interface UploadFileResult {
  fileName: string;
  status:
    | "queued"
    | "processing"
    | "validating"
    | "review_required"
    | "ready"
    | "failed"
    | "cancelled";
  statusLabel: string;
  documentId?: string;
  jobId?: string | null;
  error?: string;
}

function getRevisionStatusLabel(status: string): string {
  switch (status) {
    case "queued":
      return "Chờ xử lý";
    case "processing":
      return "Đang xử lý";
    case "validating":
      return "Đang kiểm tra";
    case "review_required":
      return "Cần duyệt";
    case "ready":
      return "Sẵn sàng";
    case "failed":
      return "Lỗi";
    case "cancelled":
      return "Đã hủy";
    default:
      return "Chờ xử lý";
  }
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
  groupId,
  groupName,
}: DocumentUploadModalProps) {
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<File[]>([]);
  const [issuingAuthority, setIssuingAuthority] = useState(
    "Trường Đại học Quy Nhơn",
  );
  const [documentTypeCode, setDocumentTypeCode] = useState("");
  const [showBatchOptions, setShowBatchOptions] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progressState, setProgressState] =
    useState<UploadProgressState | null>(null);
  const [uploadResults, setUploadResults] = useState<UploadFileResult[]>([]);

  const idempotencyKeysRef = useRef<WeakMap<File, string>>(new WeakMap());

  function getOrCreateIdempotencyKey(file: File): string {
    let key = idempotencyKeysRef.current.get(file);
    if (!key) {
      key = crypto.randomUUID();
      idempotencyKeysRef.current.set(file, key);
    }
    return key;
  }

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
    setUploadResults([]);
    setIsUploading(false);
    idempotencyKeysRef.current = new WeakMap();
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
    setUploadResults([]);
    let successCount = 0;
    const errors: string[] = [];
    const results: UploadFileResult[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const idempotencyKey = getOrCreateIdempotencyKey(file);
      const percent = Math.round(((i + 1) / files.length) * 100);
      setProgressState({
        current: i + 1,
        total: files.length,
        currentFileName: file.name,
        percent,
      });

      try {
        const intakeRes = await documentsApi.intakeDocument(file, {
          issuing_authority: issuingAuthority.trim() || undefined,
          document_type_code: documentTypeCode || undefined,
          group_id: groupId,
          idempotency_key: idempotencyKey,
        });

        const rawStatus = (intakeRes.status ||
          "queued") as UploadFileResult["status"];
        results.push({
          fileName: file.name,
          status: rawStatus,
          statusLabel: getRevisionStatusLabel(rawStatus),
          documentId: intakeRes.document_id,
          jobId: intakeRes.job_id,
        });
        successCount++;
      } catch (err: unknown) {
        const errorMsg =
          err instanceof Error ? err.message : "Tiếp nhận tệp thất bại";
        errors.push(`${file.name}: ${errorMsg}`);
        results.push({
          fileName: file.name,
          status: "failed",
          statusLabel: "Lỗi",
          error: errorMsg,
        });
      }
    }

    setUploadResults(results);
    setIsUploading(false);
    setProgressState(null);

    // Đồng bộ lại dữ liệu
    queryClient.invalidateQueries({ queryKey: ["repository-documents"] });
    queryClient.invalidateQueries({ queryKey: ["repository-stats"] });
    if (groupId) {
      queryClient.invalidateQueries({ queryKey: ["group-documents", groupId] });
      queryClient.invalidateQueries({ queryKey: ["document-group", groupId] });
      queryClient.invalidateQueries({ queryKey: ["document-groups"] });
    }

    if (errors.length === 0) {
      toast.success(
        groupName
          ? `Đã tiếp nhận ${successCount} tệp vào hàng đợi xử lý của kho "${groupName}".`
          : `Đã tiếp nhận ${successCount} tệp vào hàng đợi xử lý của Kho Tài Liệu.`,
      );
      resetForm();
      onOpenChange(false);
      onSuccess?.();
    } else if (successCount > 0) {
      toast.warning(
        `Đã tiếp nhận ${successCount}/${files.length} tệp. ${errors.length} tệp gặp sự cố.`,
      );
    } else {
      toast.error(`Không thể tiếp nhận tệp nào: ${errors[0]}`);
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
              <DialogTitle>
                {groupName
                  ? `Tải lên tài liệu vào kho: ${groupName}`
                  : "Tải tài liệu vào Kho Tài Liệu"}
              </DialogTitle>
              <DialogDescription>
                {groupName
                  ? `Tài liệu sau khi tải lên sẽ lưu trữ trên MinIO S3, đưa vào hàng đợi bóc tách V2 và trực thuộc kho "${groupName}".`
                  : "Hỗ trợ kéo thả nhiều tệp, lưu trữ MinIO S3 chống trùng lặp và tự động nhận diện bóc tách bất đồng bộ."}
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

          {/* Thông tin tự động bóc tách V2 */}
          <div className="flex items-center gap-2.5 rounded-lg border border-border/60 bg-muted/20 px-3 py-2.5 text-xs text-muted-foreground">
            <Sparkles className="size-4 shrink-0 text-primary" />
            <span className="leading-relaxed">
              Tài liệu sẽ được tự động bóc tách sau khi tiếp nhận.
            </span>
          </div>

          {/* Progress bar khi đang tải lên nhiều tệp */}
          {progressState && (
            <div className="space-y-1.5 rounded-lg border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-foreground">
                  Đang tiếp nhận tệp {progressState.current}/
                  {progressState.total}
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

          {/* Danh sách kết quả từng file nếu có lỗi một phần */}
          {uploadResults.length > 0 && !isUploading && (
            <div className="space-y-2 rounded-lg border border-border/80 bg-muted/15 p-3">
              <div className="flex items-center justify-between text-xs font-semibold text-foreground">
                <span>Kết quả tiếp nhận từng tệp</span>
                <span className="text-muted-foreground font-normal">
                  {uploadResults.filter((r) => r.status !== "failed").length}/
                  {uploadResults.length} thành công
                </span>
              </div>
              <div className="max-h-40 space-y-1.5 overflow-y-auto pr-1">
                {uploadResults.map((r) => (
                  <div
                    key={`${r.fileName}-${r.documentId || r.status}`}
                    className="flex items-center justify-between gap-2 rounded border border-border/50 bg-background/80 px-2.5 py-1.5 text-xs"
                  >
                    <span
                      className="truncate font-medium text-foreground"
                      title={r.fileName}
                    >
                      {r.fileName}
                    </span>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <span
                        className={
                          r.status === "failed"
                            ? "font-medium text-destructive"
                            : r.status === "ready"
                              ? "font-medium text-primary"
                              : "font-medium text-warning"
                        }
                      >
                        {r.statusLabel}
                      </span>
                      {r.error && (
                        <span
                          className="text-[11px] text-destructive truncate max-w-44"
                          title={r.error}
                        >
                          ({r.error})
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isUploading}
          >
            {uploadResults.length > 0 && !isUploading ? "Đóng" : "Hủy Bỏ"}
          </Button>
          <Button
            onClick={handleBatchUpload}
            disabled={isUploading || files.length === 0}
            className="gap-1.5"
          >
            {isUploading ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Đang Tiếp Nhận (
                {progressState
                  ? `${progressState.current}/${progressState.total}`
                  : "..."}
                )...
              </>
            ) : (
              <>
                <Upload className="size-4" />
                {files.length > 1
                  ? groupName
                    ? `Lưu ${files.length} Tệp Vào Kho`
                    : `Lưu ${files.length} Tệp Vào Kho`
                  : groupName
                    ? `Lưu Vào Kho "${groupName}"`
                    : "Lưu Vào Kho Tài Liệu"}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
