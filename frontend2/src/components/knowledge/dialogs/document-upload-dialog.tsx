import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Upload, Zap } from "lucide-react";
import type React from "react";
import { useState } from "react";
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
}

const OCR_ENGINES = [
  { value: "auto", label: "Tự động phát hiện (Auto)" },
  { value: "pymupdf_ocr", label: "PyMuPDF (Nhanh, văn bản số)" },
  { value: "docling", label: "Docling (Bóc tách bảng phức tạp)" },
  { value: "gemini_vision", label: "Google Gemini Vision (Scan, OCR)" },
  { value: "mistral_ocr", label: "Mistral OCR (Bố cục, bảng đa trang)" },
];

export function DocumentUploadDialog({
  open,
  onOpenChange,
  collectionId,
  collectionName,
  onSuccess,
}: DocumentUploadDialogProps) {
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [documentTypeCode, setDocumentTypeCode] = useState("all");
  const [ocrEngine, setOcrEngine] = useState("auto");
  const [autoApprove, setAutoApprove] = useState(true);

  // Fetch document types taxonomy
  const { data: documentTypes = [] } = useQuery({
    queryKey: ["document-types"],
    queryFn: () => documentTypesApi.getDocumentTypes(),
    staleTime: 60000,
  });

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
      toast.success(`Đã nạp thành công tài liệu: ${newDoc.title}`);
      queryClient.invalidateQueries({ queryKey: ["documents", collectionId] });
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      queryClient.invalidateQueries({ queryKey: ["ingestion-tasks"] });
      resetForm();
      onOpenChange(false);
      onSuccess?.();
    },
    onError: (err: Error) => {
      toast.error(`Nạp tài liệu thất bại: ${err.message}`);
    },
  });

  const resetForm = () => {
    setSelectedFile(null);
    setTitle("");
    setDocumentTypeCode("all");
    setOcrEngine("auto");
    setAutoApprove(true);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      if (!title) {
        // Set default title from filename without extension
        const baseName = file.name.replace(/\.[^/.]+$/, "");
        setTitle(baseName);
      }
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!uploadMutation.isPending) {
          if (!v) resetForm();
          onOpenChange(v);
        }
      }}
    >
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base font-bold">
            <Upload className="size-4 text-primary" />
            <span>Nạp tài liệu vào kho</span>
          </DialogTitle>
          {collectionName && (
            <p className="text-xs text-muted-foreground mt-0.5">
              Kho tri thức:{" "}
              <strong className="text-foreground">{collectionName}</strong>
            </p>
          )}
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* File Picker Zone */}
          <div className="space-y-1.5">
            <label
              htmlFor="upload-file-input"
              className="text-xs font-semibold text-foreground block"
            >
              Tệp tài liệu (PDF, Word, Excel, TXT, MD)
            </label>
            <div className="border-2 border-dashed border-border rounded-lg p-5 text-center hover:border-primary/50 transition-colors bg-muted/20">
              <input
                id="upload-file-input"
                type="file"
                accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md"
                className="hidden"
                disabled={uploadMutation.isPending}
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
                      Hỗ trợ tối đa 50MB (PDF, DOCX, XLSX, TXT)
                    </p>
                  </div>
                )}
              </label>
            </div>
          </div>

          {/* Title Input */}
          <div className="space-y-1.5">
            <label
              htmlFor="document-title"
              className="text-xs font-semibold text-foreground block"
            >
              Tiêu đề văn bản
            </label>
            <Input
              id="document-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="VD: Đề án tuyển sinh Đại học Quy Nhơn năm 2026..."
              disabled={uploadMutation.isPending}
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
              disabled={uploadMutation.isPending}
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
            <Select
              value={ocrEngine}
              onValueChange={setOcrEngine}
              disabled={uploadMutation.isPending}
            >
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

          {/* Fast-Track Auto Approve Switch */}
          <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-muted/20">
            <div className="space-y-0.5">
              <label
                htmlFor="auto-approve-switch"
                className="text-xs font-semibold text-foreground flex items-center gap-1.5 cursor-pointer"
              >
                <Zap className="size-3.5 text-primary" />
                <span>Nạp vector tức thì (Fast-Track)</span>
              </label>
              <p className="text-[11px] text-muted-foreground leading-normal">
                Tự động phê duyệt và vector hóa vào Qdrant ngay sau khi bóc tách
                hoàn tất.
              </p>
            </div>
            <Switch
              id="auto-approve-switch"
              checked={autoApprove}
              onCheckedChange={setAutoApprove}
              disabled={uploadMutation.isPending}
            />
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={uploadMutation.isPending}
            className="h-8 text-xs"
          >
            Hủy
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={() => uploadMutation.mutate()}
            disabled={!selectedFile || uploadMutation.isPending}
            className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <Upload className="size-3.5" />
            <span>
              {uploadMutation.isPending ? "Đang nạp..." : "Tải lên & Bóc tách"}
            </span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
