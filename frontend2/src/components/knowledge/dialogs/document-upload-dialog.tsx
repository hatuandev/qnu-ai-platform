import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Cpu,
  FileText,
  Loader2,
  Scan,
  Sparkles,
  Upload,
  Zap,
} from "lucide-react";
import type React from "react";
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
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

const OCR_ENGINES = [
  { value: "auto", label: "Tự động phát hiện (Auto Pipeline)" },
  { value: "pymupdf_ocr", label: "PyMuPDF (Nhanh, văn bản số & hành chính)" },
  {
    value: "docling",
    label: "Docling (Bóc tách bảng biểu & tài liệu học thuật)",
  },
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

export function DocumentUploadDialog({
  open,
  onOpenChange,
  collectionId,
  collectionName,
  onSuccess,
  onOpenStudio,
}: DocumentUploadDialogProps) {
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [documentTypeCode, setDocumentTypeCode] = useState("all");
  const [ocrEngine, setOcrEngine] = useState("auto");
  const [autoApprove, setAutoApprove] = useState(false);
  const [openStudioAfterUpload, setOpenStudioAfterUpload] = useState(true);

  // Multi-stage progress state
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [currentStageText, setCurrentStageText] = useState("");
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [processingError, setProcessingError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  const duplicateDoc = useMemo(() => {
    if (!selectedFile) return null;
    return (
      existingDocuments.find(
        (d) =>
          d.filename.trim().toLowerCase() ===
            selectedFile.name.trim().toLowerCase() ||
          d.title.trim().toLowerCase() ===
            selectedFile.name.trim().toLowerCase(),
      ) || null
    );
  }, [selectedFile, existingDocuments]);

  const resetForm = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setSelectedFile(null);
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
  };

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile) throw new Error("Vui lòng chọn tệp tài liệu.");
      return await knowledgeApi.uploadDocument(
        collectionId,
        selectedFile,
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
          : `Tệp '${selectedFile?.name || "này"}' đã tồn tại trong kho tri thức này (Trùng lặp tệp). Vui lòng chọn tệp khác.`
        : rawMsg || "Bóc tách tài liệu thất bại.";

      setProcessingError(displayMsg);
      setIsProcessing(false);
      toast.error(displayMsg, { duration: 6000 });
    },
  });

  const handleStartUpload = () => {
    if (!selectedFile) return;
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

    uploadMutation.mutate();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      if (!title) {
        const baseName = file.name.replace(/\.[^/.]+$/, "");
        setTitle(baseName);
      }
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
      <DialogContent className="sm:max-w-lg">
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

        {/* 1. VIEW GIAI ĐOẠN ĐANG XỬ LÝ (MULTI-STAGE PROGRESS WITH %) */}
        {isProcessing ? (
          <div className="space-y-5 py-4">
            {/* Top Percentage & File Banner */}
            <div className="p-3.5 rounded-lg border border-primary/20 bg-primary/5 flex items-center justify-between">
              <div className="min-w-0 space-y-0.5">
                <p className="text-xs font-semibold text-foreground truncate max-w-[260px]">
                  {selectedFile?.name}
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

            {/* Dynamic Progress Bar */}
            <div className="space-y-1.5">
              <Progress value={progressPercent} className="h-2" />
              <p className="text-[11px] text-muted-foreground text-center flex items-center justify-center gap-1.5">
                <Loader2 className="size-3 animate-spin text-primary" />
                <span>{currentStageText}</span>
              </p>
            </div>

            {/* 4 Pipeline Stages Checklist */}
            <div className="space-y-2 pt-2 border-t border-border/60">
              {PROCESSING_STAGES.map((stg, idx) => {
                const IconComp = stg.icon;
                const isDone = currentStageIdx > idx || progressPercent === 100;
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
        ) : (
          /* 2. VIEW THIẾT LẬP NẠP FILE */
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

            {/* File Picker Zone */}
            <div className="space-y-1.5">
              <label
                htmlFor="upload-file-input"
                className="text-xs font-semibold text-foreground block"
              >
                Tệp tài liệu scan hoặc số hóa (PDF, DOCX, XLSX, TXT, Ảnh)
              </label>
              <div className="border-2 border-dashed border-border rounded-lg p-5 text-center hover:border-primary/50 transition-colors bg-muted/20">
                <input
                  id="upload-file-input"
                  type="file"
                  accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md,.png,.jpg,.jpeg"
                  className="hidden"
                  onChange={handleFileChange}
                />
                <label
                  htmlFor="upload-file-input"
                  className="cursor-pointer block space-y-2"
                >
                  <FileText className="size-8 mx-auto text-primary/70" />
                  {selectedFile ? (
                    <div>
                      <p className="text-xs font-semibold text-foreground">
                        {selectedFile.name}
                      </p>
                      <p className="text-[11px] text-muted-foreground">
                        {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs font-medium text-foreground">
                        Nhấn để chọn tệp hoặc kéo thả vào đây
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        Hỗ trợ PDF scan, Word, Bảng tính (Tối đa 50MB)
                      </p>
                    </div>
                  )}
                </label>
              </div>

              {duplicateDoc && !processingError && (
                <div className="flex items-start gap-2 p-2 rounded-md bg-amber-500/10 border border-amber-500/30 text-[11px] text-amber-800 dark:text-amber-300">
                  <AlertCircle className="size-3.5 shrink-0 text-amber-600 mt-0.5" />
                  <span>
                    Lưu ý: Tệp <strong>"{duplicateDoc.filename}"</strong> đã có
                    trong kho này. Nếu tệp có cùng nội dung, hệ thống sẽ báo
                    trùng.
                  </span>
                </div>
              )}
            </div>

            {/* Title Input */}
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
                <SelectTrigger
                  id="document-type-select"
                  className="h-9 text-xs"
                >
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
              <div className="flex items-center justify-between p-3 rounded-lg border border-primary/20 bg-primary/5">
                <div className="space-y-0.5">
                  <label
                    htmlFor="open-studio-switch"
                    className="text-xs font-semibold text-foreground flex items-center gap-1.5 cursor-pointer"
                  >
                    <Scan className="size-3.5 text-primary" />
                    <span>Mở Studio Thẩm định ngay sau khi bóc tách</span>
                  </label>
                  <p className="text-[11px] text-muted-foreground leading-normal">
                    Kiểm tra trực quan bounding boxes nhận diện khung văn bản,
                    bảng biểu và đối soát nội dung.
                  </p>
                </div>
                <Switch
                  id="open-studio-switch"
                  checked={openStudioAfterUpload}
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

        {/* Modal Action Bar with generous gap and proper button labels */}
        <DialogFooter className="gap-3 sm:gap-3 pt-2">
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
              disabled={!selectedFile}
              className="h-9 px-4 text-xs font-semibold gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm active:scale-[0.98] transition-all"
            >
              <Upload className="size-3.5" />
              <span>
                {openStudioAfterUpload
                  ? "Bắt đầu bóc tách & Mở Studio"
                  : "Bắt đầu tải lên & Bóc tách"}
              </span>
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
