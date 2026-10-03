import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Cpu,
  FileText,
  Files,
  Loader2,
  Plus,
  Scan,
  Sparkles,
  Trash2,
  Upload,
  X,
  Zap,
} from "lucide-react";
import type React from "react";
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
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
import { Switch } from "@/components/ui/switch";
import { documentTypesApi } from "@/services/document-types-api";
import { knowledgeApi } from "@/services/knowledge-api";

interface DocumentUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  collectionId: string;
  collectionName?: string;
  onSuccess?: () => void;
  onOpenStudio?: (documentId: string) => void;
}

interface BatchItem {
  id: string;
  file: File;
  title: string;
  status: "waiting" | "processing" | "success" | "duplicate" | "error";
  docId?: string;
  errorMsg?: string;
}

const OCR_ENGINES = [
  { value: "auto", label: "Tự động phát hiện (Auto Pipeline)" },
  { value: "pymupdf_ocr", label: "PyMuPDF (Nhanh, văn bản số & hành chính)" },
  {
    value: "gemini_vision",
    label: "Google Gemini Vision (Ảnh scan mờ, bản chụp)",
  },
  { value: "mistral_ocr", label: "Mistral OCR (Bố cục phức tạp & đa trang)" },
];

const PROCESSING_STAGES = [
  {
    percent: 20,
    title: "Tải lên & Lưu trữ an toàn",
    detail: "Mã hóa tệp tin & lưu trữ bảo mật trên MinIO S3",
    icon: Upload,
  },
  {
    percent: 50,
    title: "Bóc tách quang học OCR",
    detail: "Trích xuất văn bản đa tầng qua mô hình thị giác máy tính",
    icon: Cpu,
  },
  {
    percent: 80,
    title: "Nhận diện Khung scan & Bảng biểu",
    detail: "Định vị Bounding Boxes, tách bảng điểm, con dấu, chữ ký",
    icon: Scan,
  },
  {
    percent: 95,
    title: "Tái dựng Markdown & Bảng tính",
    detail: "Chuẩn hóa cấu trúc văn bản và đồng bộ Studio",
    icon: Sparkles,
  },
];

const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${Number.parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function DocumentUploadDialog({
  open,
  onOpenChange,
  collectionId,
  collectionName,
  onSuccess,
  onOpenStudio,
}: DocumentUploadDialogProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // File selection state
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [title, setTitle] = useState("");
  const [documentTypeCode, setDocumentTypeCode] = useState("all");
  const [ocrEngine, setOcrEngine] = useState("auto");
  const [autoApprove, setAutoApprove] = useState(false);
  const [openStudioAfterUpload, setOpenStudioAfterUpload] = useState(true);

  // Single-file processing state
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [currentStageText, setCurrentStageText] = useState("");
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [processingError, setProcessingError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Batch-file processing state
  const [isBatchMode, setIsBatchMode] = useState(false);
  const [batchItems, setBatchItems] = useState<BatchItem[]>([]);
  const [batchCurrentIdx, setBatchCurrentIdx] = useState(0);
  const [isBatchComplete, setIsBatchComplete] = useState(false);

  // Fetch document types taxonomy
  const { data: documentTypes = [] } = useQuery({
    queryKey: ["document-types"],
    queryFn: () => documentTypesApi.getDocumentTypes(),
    staleTime: 60000,
  });

  // Fetch existing documents in this collection to detect duplicate file names early
  const { data: existingDocuments = [] } = useQuery({
    queryKey: ["documents", collectionId],
    queryFn: () => knowledgeApi.getDocuments(collectionId),
    enabled: !!collectionId && open,
  });

  // Duplicate files warning in currently selected list
  const duplicateFiles = useMemo(() => {
    if (selectedFiles.length === 0) return [];
    return selectedFiles.filter((file) =>
      existingDocuments.some(
        (d) =>
          d.filename.trim().toLowerCase() === file.name.trim().toLowerCase() ||
          d.title.trim().toLowerCase() === file.name.trim().toLowerCase(),
      ),
    );
  }, [selectedFiles, existingDocuments]);

  const totalSelectedSizeBytes = useMemo(() => {
    return selectedFiles.reduce((acc, f) => acc + f.size, 0);
  }, [selectedFiles]);

  const resetForm = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setSelectedFiles([]);
    setIsDragging(false);
    setTitle("");
    setDocumentTypeCode("all");
    setOcrEngine("auto");
    setAutoApprove(false);
    setOpenStudioAfterUpload(true);
    setIsProcessing(false);
    setProgressPercent(0);
    setCurrentStageText("");
    setCurrentStageIdx(0);
    setProcessingError(null);
    setIsBatchMode(false);
    setBatchItems([]);
    setBatchCurrentIdx(0);
    setIsBatchComplete(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleAddFiles = (newFiles: File[]) => {
    const validFiles: File[] = [];
    const oversizedFiles: string[] = [];

    newFiles.forEach((file) => {
      if (file.size > MAX_FILE_SIZE_BYTES) {
        oversizedFiles.push(file.name);
      } else {
        // Prevent adding exact duplicate in selection
        const alreadyInList = selectedFiles.some(
          (f) => f.name === file.name && f.size === file.size,
        );
        if (!alreadyInList) {
          validFiles.push(file);
        }
      }
    });

    if (oversizedFiles.length > 0) {
      toast.warning(
        `Đã bỏ qua ${oversizedFiles.length} tệp vượt quá giới hạn 50MB: ${oversizedFiles.join(", ")}`,
      );
    }

    if (validFiles.length > 0) {
      const updated = [...selectedFiles, ...validFiles];
      setSelectedFiles(updated);

      // If exactly 1 file in total, prefill title
      if (updated.length === 1 && !title) {
        const baseName = updated[0].name.replace(/\.[^/.]+$/, "");
        setTitle(baseName);
      }
    }
  };

  const handleRemoveFile = (index: number) => {
    const updated = selectedFiles.filter((_, idx) => idx !== index);
    setSelectedFiles(updated);
    if (updated.length === 1) {
      const baseName = updated[0].name.replace(/\.[^/.]+$/, "");
      setTitle(baseName);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleClearAll = () => {
    setSelectedFiles([]);
    setTitle("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleAddFiles(Array.from(e.target.files));
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) setIsDragging(true);
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleAddFiles(Array.from(e.dataTransfer.files));
    }
  };

  // Single-file Upload Mutation
  const singleUploadMutation = useMutation({
    mutationFn: async () => {
      const singleFile = selectedFiles[0];
      if (!singleFile) throw new Error("Vui lòng chọn tệp tài liệu.");
      return await knowledgeApi.uploadDocument(
        collectionId,
        singleFile,
        title.trim() || undefined,
        ocrEngine === "auto" ? undefined : ocrEngine,
        documentTypeCode === "all" ? undefined : documentTypeCode,
        autoApprove,
      );
    },
    onSuccess: (newDoc) => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setProgressPercent(100);
      setCurrentStageIdx(3);
      setCurrentStageText("Bóc tách thành công! Đang chuyển vào Studio...");

      queryClient.invalidateQueries({ queryKey: ["documents", collectionId] });
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      queryClient.invalidateQueries({ queryKey: ["ingestion-tasks"] });

      toast.success(`Đã bóc tách thành công tài liệu: ${newDoc.title}`);

      setTimeout(() => {
        const docId = newDoc.id;
        resetForm();
        onOpenChange(false);
        onSuccess?.();

        if (openStudioAfterUpload && docId && onOpenStudio) {
          onOpenStudio(docId);
        }
      }, 700);
    },
    onError: (err: Error) => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      const rawMsg = err.message || "";
      const isDuplicate =
        rawMsg.includes("đã tồn tại") ||
        rawMsg.includes("trùng") ||
        rawMsg.includes("Trùng") ||
        rawMsg.includes("409") ||
        rawMsg.includes("already exists");
      const displayMsg = isDuplicate
        ? rawMsg.includes("đã tồn tại") || rawMsg.includes("trùng")
          ? rawMsg
          : `Tệp '${selectedFiles[0]?.name || "này"}' đã tồn tại trong kho tri thức này (Trùng lặp tệp). Vui lòng chọn tệp khác.`
        : rawMsg || "Bóc tách tài liệu thất bại.";

      setProcessingError(displayMsg);
      setIsProcessing(false);
      toast.error(displayMsg, { duration: 6000 });
    },
  });

  // Batch Processing Execution
  const executeBatchUpload = async () => {
    setIsProcessing(true);
    setIsBatchMode(true);
    setIsBatchComplete(false);
    setProcessingError(null);

    const initialItems: BatchItem[] = selectedFiles.map((file, idx) => ({
      id: `${file.name}-${file.size}-${idx}`,
      file,
      title: file.name.replace(/\.[^/.]+$/, ""),
      status: "waiting",
    }));

    setBatchItems(initialItems);
    setProgressPercent(0);

    const total = initialItems.length;
    let successCount = 0;
    let duplicateCount = 0;
    let errorCount = 0;

    for (let i = 0; i < total; i++) {
      const current = initialItems[i];
      setBatchCurrentIdx(i);

      // Update current item to processing
      setBatchItems((prev) =>
        prev.map((item, idx) =>
          idx === i ? { ...item, status: "processing" } : item,
        ),
      );

      setCurrentStageText(
        `Đang tải lên & bóc tách tệp ${i + 1}/${total}: ${current.file.name}...`,
      );

      try {
        const doc = await knowledgeApi.uploadDocument(
          collectionId,
          current.file,
          current.title,
          ocrEngine === "auto" ? undefined : ocrEngine,
          documentTypeCode === "all" ? undefined : documentTypeCode,
          autoApprove,
        );

        successCount++;
        setBatchItems((prev) =>
          prev.map((item, idx) =>
            idx === i ? { ...item, status: "success", docId: doc.id } : item,
          ),
        );
      } catch (err: unknown) {
        const rawMsg = err instanceof Error ? err.message : String(err || "");
        const isDuplicate =
          rawMsg.includes("đã tồn tại") ||
          rawMsg.includes("trùng") ||
          rawMsg.includes("Trùng") ||
          rawMsg.includes("409") ||
          rawMsg.includes("already exists");

        if (isDuplicate) {
          duplicateCount++;
          setBatchItems((prev) =>
            prev.map((item, idx) =>
              idx === i
                ? {
                    ...item,
                    status: "duplicate",
                    errorMsg: "Tệp đã tồn tại trong kho",
                  }
                : item,
            ),
          );
        } else {
          errorCount++;
          setBatchItems((prev) =>
            prev.map((item, idx) =>
              idx === i
                ? {
                    ...item,
                    status: "error",
                    errorMsg: rawMsg || "Bóc tách thất bại",
                  }
                : item,
            ),
          );
        }
      }

      setProgressPercent(Math.round(((i + 1) / total) * 100));
    }

    // Finished entire batch
    setIsBatchComplete(true);
    setIsProcessing(false);
    setCurrentStageText(
      `Hoàn tất bóc tách: ${successCount} thành công, ${duplicateCount} trùng lặp, ${errorCount} lỗi.`,
    );

    queryClient.invalidateQueries({ queryKey: ["documents", collectionId] });
    queryClient.invalidateQueries({ queryKey: ["collections"] });
    queryClient.invalidateQueries({ queryKey: ["ingestion-tasks"] });

    if (errorCount === 0 && duplicateCount === 0) {
      toast.success(`Đã bóc tách thành công toàn bộ ${total} tài liệu vào kho.`);
    } else {
      toast.info(
        `Bóc tách hoàn tất: ${successCount} thành công, ${duplicateCount} trùng lặp, ${errorCount} lỗi.`,
      );
    }
  };

  const handleStartUpload = () => {
    if (selectedFiles.length === 0) return;

    if (selectedFiles.length === 1) {
      // Single-file flow with multi-stage progress
      setIsBatchMode(false);
      setIsProcessing(true);
      setProcessingError(null);
      setProgressPercent(15);
      setCurrentStageIdx(0);
      setCurrentStageText("Đang tải tệp lên máy chủ & lưu trữ an toàn...");

      let stage = 0;
      timerRef.current = setInterval(() => {
        if (stage < PROCESSING_STAGES.length - 1) {
          stage++;
          setCurrentStageIdx(stage);
          setProgressPercent(PROCESSING_STAGES[stage].percent);
          setCurrentStageText(PROCESSING_STAGES[stage].detail);
        }
      }, 1100);

      singleUploadMutation.mutate();
    } else {
      // Multi-file batch flow
      executeBatchUpload();
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!isProcessing) {
          if (!v) resetForm();
          onOpenChange(v);
        }
      }}
    >
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base font-bold">
            <Upload className="size-4 text-primary" />
            <span>Nạp & Bóc Tách Tài Liệu Vào Kho</span>
          </DialogTitle>
          {collectionName && (
            <p className="text-xs text-muted-foreground mt-0.5">
              Kho tri thức:{" "}
              <strong className="text-foreground">{collectionName}</strong>
            </p>
          )}
        </DialogHeader>

        {/* 1. VIEW BATCH HOÀN TẤT (SUMMARY REPORT) */}
        {isBatchComplete ? (
          <div className="space-y-4 py-3">
            <div className="p-4 rounded-lg border border-primary/20 bg-primary/5 space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <CheckCircle2 className="size-4 text-primary" />
                  <span>Tổng kết bóc tách hàng loạt</span>
                </p>
                <Badge variant="default" className="text-xs font-mono font-bold">
                  {batchItems.filter((i) => i.status === "success").length} /{" "}
                  {batchItems.length} thành công
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Tất cả các tài liệu hợp lệ đã được bóc tách, chia đoạn và số hóa
                vào kho tri thức.
              </p>
            </div>

            {/* List of items processed */}
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {batchItems.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-border bg-card text-xs gap-2"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    {item.status === "success" && (
                      <CheckCircle2 className="size-4 text-success shrink-0" />
                    )}
                    {item.status === "duplicate" && (
                      <AlertCircle className="size-4 text-warning shrink-0" />
                    )}
                    {item.status === "error" && (
                      <AlertCircle className="size-4 text-destructive shrink-0" />
                    )}
                    <div className="min-w-0">
                      <p className="font-medium text-foreground truncate max-w-[260px]">
                        {item.file.name}
                      </p>
                      <p className="text-[11px] text-muted-foreground">
                        {item.status === "success" && (
                          <span className="text-success font-medium">
                            Bóc tách thành công
                          </span>
                        )}
                        {item.status === "duplicate" && (
                          <span className="text-warning font-medium">
                            Đã tồn tại trong kho (Trùng lặp)
                          </span>
                        )}
                        {item.status === "error" && (
                          <span className="text-destructive font-medium">
                            {item.errorMsg || "Lỗi bóc tách"}
                          </span>
                        )}
                        {" • "}
                        {formatBytes(item.file.size)}
                      </p>
                    </div>
                  </div>

                  {item.status === "success" && item.docId && onOpenStudio && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        const targetDocId = item.docId;
                        if (targetDocId) {
                          resetForm();
                          onOpenChange(false);
                          onSuccess?.();
                          onOpenStudio(targetDocId);
                        }
                      }}
                      className="h-7 px-2 text-[11px] gap-1 text-primary hover:text-primary hover:bg-primary/10 shrink-0"
                    >
                      <Scan className="size-3" />
                      <span>Studio</span>
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : isProcessing ? (
          /* 2. VIEW TIẾN TRÌNH XỬ LÝ (SINGLE HOẶC BATCH) */
          <div className="space-y-5 py-4">
            {isBatchMode ? (
              /* Batch Progress Mode */
              <div className="space-y-4">
                <div className="p-3.5 rounded-lg border border-primary/20 bg-primary/5 flex items-center justify-between">
                  <div className="min-w-0 space-y-0.5">
                    <p className="text-xs font-semibold text-foreground truncate max-w-[260px]">
                      Đang xử lý tệp {batchCurrentIdx + 1} / {batchItems.length}
                    </p>
                    <p className="text-[11px] text-muted-foreground truncate max-w-[260px]">
                      {batchItems[batchCurrentIdx]?.file.name}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="font-mono text-xl font-bold text-primary">
                      {progressPercent}%
                    </span>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Progress value={progressPercent} className="h-2" />
                  <p className="text-[11px] text-muted-foreground text-center flex items-center justify-center gap-1.5">
                    <Loader2 className="size-3 animate-spin text-primary" />
                    <span>{currentStageText}</span>
                  </p>
                </div>

                {/* Realtime Batch Status Checklist */}
                <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                  {batchItems.map((item, idx) => (
                    <div
                      key={item.id}
                      className={`flex items-center justify-between p-2 rounded-md text-xs transition-colors ${
                        item.status === "processing"
                          ? "bg-primary/10 border border-primary/20 text-primary"
                          : item.status === "success"
                            ? "bg-muted/40 text-foreground"
                            : item.status === "duplicate"
                              ? "bg-amber-500/10 text-amber-800 dark:text-amber-300"
                              : item.status === "error"
                                ? "bg-destructive/10 text-destructive"
                                : "text-muted-foreground opacity-60"
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate min-w-0">
                        <span className="font-mono text-[10px] w-4 text-center shrink-0">
                          {idx + 1}
                        </span>
                        <p className="truncate font-medium">{item.file.name}</p>
                      </div>
                      <div className="shrink-0 flex items-center gap-1.5 ml-2">
                        {item.status === "waiting" && (
                          <span className="text-[10px] text-muted-foreground">
                            Chờ xử lý
                          </span>
                        )}
                        {item.status === "processing" && (
                          <span className="text-[10px] text-primary flex items-center gap-1">
                            <Loader2 className="size-3 animate-spin" />
                            Đang bóc tách
                          </span>
                        )}
                        {item.status === "success" && (
                          <CheckCircle2 className="size-3.5 text-success" />
                        )}
                        {item.status === "duplicate" && (
                          <span className="text-[10px] font-medium text-amber-600 dark:text-amber-400">
                            Trùng lặp
                          </span>
                        )}
                        {item.status === "error" && (
                          <span className="text-[10px] font-medium text-destructive">
                            Lỗi
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              /* Single-file 4-stage Progress Mode */
              <div className="space-y-4">
                <div className="p-3.5 rounded-lg border border-primary/20 bg-primary/5 flex items-center justify-between">
                  <div className="min-w-0 space-y-0.5">
                    <p className="text-xs font-semibold text-foreground truncate max-w-[260px]">
                      {selectedFiles[0]?.name}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      Động cơ:{" "}
                      <strong className="text-primary font-medium">
                        {OCR_ENGINES.find((e) => e.value === ocrEngine)?.label}
                      </strong>
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="font-mono text-xl font-bold text-primary">
                      {progressPercent}%
                    </span>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Progress value={progressPercent} className="h-2" />
                  <p className="text-[11px] text-muted-foreground text-center flex items-center justify-center gap-1.5">
                    <Loader2 className="size-3 animate-spin text-primary" />
                    <span>{currentStageText}</span>
                  </p>
                </div>

                <div className="space-y-2 pt-2 border-t border-border/60">
                  {PROCESSING_STAGES.map((stg, idx) => {
                    const IconComp = stg.icon;
                    const isDone =
                      currentStageIdx > idx || progressPercent === 100;
                    const isCurrent =
                      currentStageIdx === idx && progressPercent < 100;

                    return (
                      <div
                        key={stg.title}
                        className={`flex items-center gap-3 p-2 rounded-md transition-colors text-xs ${
                          isDone
                            ? "bg-muted/40 text-foreground"
                            : isCurrent
                              ? "bg-primary/10 text-primary border border-primary/20"
                              : "text-muted-foreground opacity-60"
                        }`}
                      >
                        <div
                          className={`flex size-6 shrink-0 items-center justify-center rounded-full text-xs ${
                            isDone
                              ? "bg-primary text-primary-foreground"
                              : isCurrent
                                ? "bg-primary/20 text-primary"
                                : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {isDone ? (
                            <CheckCircle2 className="size-3.5" />
                          ) : isCurrent ? (
                            <Loader2 className="size-3.5 animate-spin" />
                          ) : (
                            <IconComp className="size-3.5" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{stg.title}</p>
                          <p className="text-[10px] text-muted-foreground truncate">
                            {stg.detail}
                          </p>
                        </div>
                        <span className="text-[10px] font-mono shrink-0">
                          {stg.percent}%
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* 3. VIEW THIẾT LẬP NẠP FILE & KÉO THẢ */
          <div className="space-y-4 py-2">
            {processingError && (
              <div
                className={`flex items-start gap-2.5 p-3 rounded-lg border text-xs leading-relaxed ${
                  processingError.includes("đã tồn tại") ||
                  processingError.includes("trùng") ||
                  processingError.includes("Trùng")
                    ? "bg-amber-500/10 border-amber-500/30 text-amber-900 dark:text-amber-200"
                    : "bg-destructive/10 border-destructive/20 text-destructive"
                }`}
              >
                <AlertCircle
                  className={`size-4 shrink-0 mt-0.5 ${
                    processingError.includes("đã tồn tại") ||
                    processingError.includes("trùng") ||
                    processingError.includes("Trùng")
                      ? "text-amber-600 dark:text-amber-400"
                      : "text-destructive"
                  }`}
                />
                <div className="space-y-0.5">
                  <p className="font-semibold">
                    {processingError.includes("đã tồn tại") ||
                    processingError.includes("trùng") ||
                    processingError.includes("Trùng")
                      ? "Thông báo trùng tệp tài liệu"
                      : "Tải lên tài liệu thất bại"}
                  </p>
                  <p className="opacity-90">{processingError}</p>
                </div>
              </div>
            )}

            {/* Hidden Input for File Selection */}
            <input
              ref={fileInputRef}
              id="upload-file-input"
              type="file"
              multiple
              accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md,.png,.jpg,.jpeg"
              className="hidden"
              onChange={handleFileInputChange}
            />

            {/* File Drag & Drop Zone */}
            <div className="space-y-1.5">
              <label
                htmlFor="upload-file-input"
                className="text-xs font-semibold text-foreground flex items-center justify-between"
              >
                <span>
                  Tệp tài liệu scan hoặc số hóa (PDF, DOCX, XLSX, TXT, Ảnh)
                </span>
                {selectedFiles.length > 0 && (
                  <span className="text-[11px] font-normal text-muted-foreground">
                    {selectedFiles.length} tệp • {formatBytes(totalSelectedSizeBytes)}
                  </span>
                )}
              </label>

              {selectedFiles.length === 0 ? (
                /* Empty Drop Zone */
                <div
                  onDragOver={handleDragOver}
                  onDragEnter={handleDragEnter}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all duration-200 ${
                    isDragging
                      ? "border-primary bg-primary/10 ring-2 ring-primary/20 scale-[0.99]"
                      : "border-border hover:border-primary/50 bg-muted/20 hover:bg-muted/30"
                  }`}
                >
                  <div className="space-y-2 pointer-events-none">
                    <div className="size-10 rounded-full bg-primary/10 text-primary mx-auto flex items-center justify-center">
                      <Upload className="size-5" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-foreground">
                        {isDragging
                          ? "Thả các tệp vào đây ngay..."
                          : "Nhấn để chọn tệp hoặc kéo thả nhiều tệp vào đây"}
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        Hỗ trợ PDF scan, Word, Bảng tính, Ảnh (Tối đa 50MB/tệp)
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                /* Selected Files Container */
                <div className="space-y-2">
                  {/* Drop zone strip for adding more */}
                  <div
                    onDragOver={handleDragOver}
                    onDragEnter={handleDragEnter}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className={`border-2 border-dashed rounded-lg p-2.5 transition-all duration-200 ${
                      isDragging
                        ? "border-primary bg-primary/10 ring-2 ring-primary/20"
                        : "border-border/70 bg-muted/20"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 px-1">
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Files className="size-3.5 text-primary" />
                        <span>Kéo thả thêm tệp vào đây hoặc</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => fileInputRef.current?.click()}
                          className="h-7 px-2 text-[11px] gap-1"
                        >
                          <Plus className="size-3" />
                          <span>Thêm tệp</span>
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={handleClearAll}
                          className="h-7 px-2 text-[11px] gap-1 text-destructive hover:text-destructive hover:bg-destructive/10"
                        >
                          <Trash2 className="size-3" />
                          <span>Xóa hết</span>
                        </Button>
                      </div>
                    </div>
                  </div>

                  {/* Scrollable File List */}
                  <div className="max-h-40 overflow-y-auto space-y-1.5 pr-1 rounded-md border border-border/60 p-1.5 bg-background">
                    {selectedFiles.map((file, idx) => {
                      const isDup = existingDocuments.some(
                        (d) =>
                          d.filename.trim().toLowerCase() ===
                            file.name.trim().toLowerCase() ||
                          d.title.trim().toLowerCase() ===
                            file.name.trim().toLowerCase(),
                      );

                      return (
                        <div
                          key={`${file.name}-${file.size}-${idx}`}
                          className={`flex items-center justify-between p-2 rounded-md border text-xs gap-2 transition-colors ${
                            isDup
                              ? "bg-amber-500/10 border-amber-500/30 text-amber-900 dark:text-amber-200"
                              : "bg-muted/30 border-border/60 text-foreground"
                          }`}
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <FileText
                              className={`size-4 shrink-0 ${
                                isDup ? "text-amber-600 dark:text-amber-400" : "text-primary/70"
                              }`}
                            />
                            <div className="min-w-0">
                              <p className="font-medium truncate max-w-[260px]">
                                {file.name}
                              </p>
                              <p className="text-[10px] text-muted-foreground">
                                {formatBytes(file.size)}
                                {isDup && (
                                  <span className="text-amber-600 dark:text-amber-400 font-semibold ml-1.5">
                                    (Tệp đã có trong kho)
                                  </span>
                                )}
                              </p>
                            </div>
                          </div>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemoveFile(idx)}
                            className="size-6 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10 shrink-0 rounded-full"
                          >
                            <X className="size-3.5" />
                          </Button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {duplicateFiles.length > 0 && !processingError && (
                <div className="flex items-start gap-2 p-2 rounded-md bg-amber-500/10 border border-amber-500/30 text-[11px] text-amber-800 dark:text-amber-300">
                  <AlertCircle className="size-3.5 shrink-0 text-amber-600 mt-0.5" />
                  <span>
                    Lưu ý: Có <strong>{duplicateFiles.length} tệp</strong> đã có
                    tên trong kho này. Nếu nội dung trùng lặp hoàn toàn, hệ thống
                    sẽ tự động phát hiện và bỏ qua để tránh trùng dữ liệu.
                  </span>
                </div>
              )}
            </div>

            {/* Title Input (Chỉ hiển thị khi nạp 1 tệp) */}
            {selectedFiles.length <= 1 ? (
              <div className="space-y-1.5">
                <label
                  htmlFor="document-title"
                  className="text-xs font-semibold text-foreground block"
                >
                  Tiêu đề tài liệu
                </label>
                <Input
                  id="document-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="VD: Đề án tuyển sinh Đại học Quy Nhơn năm 2026..."
                  className="h-9 text-xs"
                />
              </div>
            ) : (
              <div className="p-2.5 rounded-lg border border-border/60 bg-muted/20 text-xs text-muted-foreground space-y-0.5">
                <p className="font-semibold text-foreground">
                  Tiêu đề tự động theo tên từng tệp
                </p>
                <p className="text-[11px]">
                  Hệ thống sẽ tự động gán tiêu đề chuẩn theo tên của từng tệp tin
                  trong danh sách (đã loại bỏ phần đuôi mở rộng).
                </p>
              </div>
            )}

            {/* Document Type Selector */}
            <div className="space-y-1.5">
              <label
                htmlFor="document-type-select"
                className="text-xs font-semibold text-foreground block"
              >
                Loại văn bản chuẩn hóa
              </label>
              <Select
                value={documentTypeCode}
                onValueChange={setDocumentTypeCode}
              >
                <SelectTrigger id="document-type-select" className="h-9 text-xs">
                  <SelectValue placeholder="Chọn loại văn bản" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tự động phân loại</SelectItem>
                  {documentTypes.map((t) => (
                    <SelectItem key={t.code} value={t.code}>
                      {t.name} ({t.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* OCR Engine Selector */}
            <div className="space-y-1.5">
              <label
                htmlFor="ocr-engine-select"
                className="text-xs font-semibold text-foreground block"
              >
                Bộ máy bóc tách & OCR
              </label>
              <Select value={ocrEngine} onValueChange={setOcrEngine}>
                <SelectTrigger id="ocr-engine-select" className="h-9 text-xs">
                  <SelectValue placeholder="Chọn bộ máy OCR" />
                </SelectTrigger>
                <SelectContent>
                  {OCR_ENGINES.map((eng) => (
                    <SelectItem key={eng.value} value={eng.value}>
                      {eng.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Ingestion & Studio Workflow Options */}
            <div className="space-y-2 pt-1">
              {/* Option 1: Open Studio Workspace */}
              <div
                className={`flex items-center justify-between p-3 rounded-lg border transition-opacity ${
                  selectedFiles.length > 1
                    ? "opacity-60 bg-muted/30 border-border"
                    : "border-primary/20 bg-primary/5"
                }`}
              >
                <div className="space-y-0.5">
                  <label
                    htmlFor="open-studio-switch"
                    className={`text-xs font-semibold flex items-center gap-1.5 ${
                      selectedFiles.length > 1
                        ? "text-muted-foreground cursor-not-allowed"
                        : "text-foreground cursor-pointer"
                    }`}
                  >
                    <Scan className="size-3.5 text-primary" />
                    <span>Mở Studio Thẩm định ngay sau khi bóc tách</span>
                  </label>
                  <p className="text-[11px] text-muted-foreground leading-normal">
                    {selectedFiles.length > 1
                      ? "Chế độ nạp nhiều tệp: Bạn có thể chọn mở Studio cho từng tệp sau khi bóc tách xong."
                      : "Kiểm tra trực quan bounding boxes nhận diện khung văn bản, bảng biểu và đối soát."}
                  </p>
                </div>
                <Switch
                  id="open-studio-switch"
                  checked={selectedFiles.length <= 1 && openStudioAfterUpload}
                  disabled={selectedFiles.length > 1}
                  onCheckedChange={setOpenStudioAfterUpload}
                />
              </div>

              {/* Option 2: Fast-Track Auto Approve */}
              <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-muted/20">
                <div className="space-y-0.5">
                  <label
                    htmlFor="auto-approve-switch"
                    className="text-xs font-semibold text-foreground flex items-center gap-1.5 cursor-pointer"
                  >
                    <Zap className="size-3.5 text-muted-foreground" />
                    <span>Nạp Vector tức thì (Bỏ qua đối soát)</span>
                  </label>
                  <p className="text-[11px] text-muted-foreground leading-normal">
                    Tự động phê duyệt và vector hóa vào Qdrant ngay sau khi bóc
                    tách xong.
                  </p>
                </div>
                <Switch
                  id="auto-approve-switch"
                  checked={autoApprove}
                  onCheckedChange={setAutoApprove}
                />
              </div>
            </div>
          </div>
        )}

        {/* Modal Action Bar */}
        <DialogFooter className="gap-3 sm:gap-3 pt-2">
          {isBatchComplete ? (
            <Button
              type="button"
              size="sm"
              onClick={() => {
                resetForm();
                onOpenChange(false);
                onSuccess?.();
              }}
              className="h-9 px-4 text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
            >
              Hoàn tất & Đóng
            </Button>
          ) : (
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  resetForm();
                  onOpenChange(false);
                }}
                disabled={isProcessing}
                className="h-9 px-4 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
              >
                Hủy bỏ
              </Button>
              {!isProcessing && (
                <Button
                  type="button"
                  size="sm"
                  onClick={handleStartUpload}
                  disabled={selectedFiles.length === 0}
                  className="h-9 px-4 text-xs font-semibold gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm active:scale-[0.98] transition-all"
                >
                  <Upload className="size-3.5" />
                  <span>
                    {selectedFiles.length > 1
                      ? `Bắt đầu bóc tách (${selectedFiles.length} tệp)`
                      : openStudioAfterUpload
                        ? "Bắt đầu bóc tách & Mở Studio"
                        : "Bắt đầu tải lên & Bóc tách"}
                  </span>
                </Button>
              )}
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
