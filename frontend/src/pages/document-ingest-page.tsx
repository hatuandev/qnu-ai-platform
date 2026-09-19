import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  CircleAlert,
  FileCheck2,
  ShieldCheck,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  type FileRecommendation,
  cleanTitleFromFilename,
  detectDocumentTypeFromFilename,
  extractYearFromFilename,
  getPriorityForDocumentType,
  inspectFileAndRecommend,
} from "../lib/file-inspector";
import { type KnowledgeCollection, apiClient } from "../services/api-client";
import { listDocumentTypes } from "../services/document-types-api";

const OCR_ENGINE_PARAM: Record<string, string | undefined> = {
  auto: undefined,
  mistral: "mistral_ocr",
  docling: "docling",
  pymupdf: "pymupdf_ocr",
  easyocr: "easyocr",
};

export interface DocumentIngestPageProps {
  collection: KnowledgeCollection;
  onBack: () => void;
  onStartVerification: (documentId: string) => void;
}

export const DocumentIngestPage: React.FC<DocumentIngestPageProps> = ({
  collection,
  onBack,
  onStartVerification,
}) => {
  // Khởi tạo form rỗng động — tuyệt đối không gán cứng tên tài liệu mẫu
  const [docTitle, setDocTitle] = useState<string>("");
  const [docType, setDocType] = useState<string>("");
  const [year, setYear] = useState<string>("");
  const [ocrEngine, setOcrEngine] = useState<string>("auto");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [recommendation, setRecommendation] = useState<FileRecommendation | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const documentTypesQuery = useQuery({
    queryKey: ["document-types", "active"],
    queryFn: () => listDocumentTypes({ activeOnly: true }),
  });

  // Tự động khởi tạo Loại văn bản mặc định theo ngữ cảnh Kho tri thức nếu chưa có
  useEffect(() => {
    if (!docType) {
      const availableCodes = (documentTypesQuery.data || []).map((t) => t.code);
      const defaultDocType = detectDocumentTypeFromFilename("", availableCodes, collection);
      if (defaultDocType) {
        setDocType(defaultDocType);
      }
    }
  }, [collection, documentTypesQuery.data, docType]);

  const processFile = (f: File) => {
    setSelectedFile(f);
    setSubmitError(null);

    // 1. Tự động điền tiêu đề sạch từ tên tệp tin thực tế nếu ô tiêu đề đang rỗng
    if (!docTitle.trim()) {
      setDocTitle(cleanTitleFromFilename(f.name));
    }

    // 2. Chạy module phân tích tệp tin & đề xuất cấu hình bóc tách tối ưu
    const rec = inspectFileAndRecommend(f);
    setRecommendation(rec);

    // 3. Tự động chọn bộ máy OCR theo đề xuất
    if (rec.targetOcrKeyword === "docling") {
      setOcrEngine("docling");
    } else if (rec.targetOcrKeyword === "pymupdf") {
      setOcrEngine("pymupdf");
    } else {
      setOcrEngine("auto");
    }

    // 4. Tự động nhận diện Loại văn bản từ tên tệp tin đối chiếu với 37 loại trong Taxonomy & ngữ cảnh Kho
    const availableCodes = (documentTypesQuery.data || []).map((t) => t.code);
    const detectedType = detectDocumentTypeFromFilename(f.name, availableCodes, collection);
    if (detectedType) {
      setDocType(detectedType);
    }

    // 5. Tự động trích xuất Năm ban hành / hiệu lực từ tên tệp tin
    const detectedYear = extractYearFromFilename(f.name);
    if (detectedYear) {
      setYear(detectedYear);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      processFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile && !docTitle.trim()) {
      setSubmitError("Vui lòng chọn tệp tài liệu hoặc nhập tiêu đề trước khi bóc tách.");
      return;
    }
    setIsProcessing(true);
    setSubmitError(null);
    try {
      if (selectedFile) {
        // Tải lên tệp thực tế kèm bộ máy OCR đã chọn, nhận document ID động
        const uploaded = await apiClient.uploadDocument(
          collection.id,
          selectedFile,
          docTitle.trim() || undefined,
          OCR_ENGINE_PARAM[ocrEngine],
          docType
        );
        onStartVerification(uploaded.id);
      } else {
        // Tạo tài liệu văn bản mới từ tiêu đề đã nhập (upload thật qua API)
        const title = docTitle.trim();
        const textBlob = new File(
          [`# ${title}\n\n*Khởi tạo ngày ${new Date().toLocaleDateString("vi-VN")}*`],
          `${title}.txt`,
          { type: "text/plain;charset=utf-8" }
        );
        const created = await apiClient.uploadDocument(
          collection.id,
          textBlob,
          title,
          undefined,
          docType
        );
        onStartVerification(created.id);
      }
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Tải lên thất bại. Vui lòng thử lại.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      {/* Breadcrumb Navigation */}
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-1.5 hover:text-foreground transition-colors cursor-pointer"
        >
          <ArrowLeft className="size-3.5" />
          <span>Quay lại {collection.name}</span>
        </button>
        <span>&gt;</span>
        <span className="text-foreground font-medium">Nạp & Bóc tách Tài liệu Mới</span>
      </div>

      {/* Main Ingest Form Card */}
      <Card className="border-border shadow-md rounded-lg overflow-hidden bg-card">
        <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-6">
          {/* Header */}
          <div className="flex items-start gap-4 pb-4 border-b border-border/70">
            <div className="flex size-11 items-center justify-center rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 border border-emerald-200 dark:border-emerald-800/60 shrink-0">
              <UploadCloud className="size-6" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-foreground">
                Nạp & Bóc tách Tài liệu vào Kho Tri thức
              </h1>
              <p className="text-xs text-muted-foreground mt-1">
                Kho đích: <strong className="text-foreground">{collection.name}</strong> • Mô hình
                Vector:{" "}
                <span className="font-mono text-primary font-medium">
                  {collection.embedding_model || "BAAI/bge-m3 (1024-dim)"}
                </span>
              </p>
            </div>
          </div>

          {/* Field: Tiêu đề / Số hiệu Văn bản */}
          <div className="space-y-1.5">
            <label
              htmlFor="document-title-input"
              className="text-xs font-semibold text-foreground flex items-center gap-1"
            >
              <span>Tiêu đề / Số hiệu Văn bản</span>
              <span className="text-rose-500">*</span>
            </label>
            <Input
              id="document-title-input"
              value={docTitle}
              onChange={(e) => setDocTitle(e.target.value)}
              placeholder="VD: Quyết định 2705/QĐ-ĐHQN về Quy chế Đào tạo tín chỉ năm 2026"
              className="h-10 text-xs"
              required
            />
          </div>

          {/* Grid: Loại văn bản & Năm ban hành */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label
                  htmlFor="document-type-select"
                  className="text-xs font-semibold text-foreground"
                >
                  Loại văn bản
                </label>
                {docType && documentTypesQuery.data ? (
                  (() => {
                    const currentType = documentTypesQuery.data.find((t) => t.code === docType);
                    const prio = getPriorityForDocumentType(docType, currentType?.priority);
                    return (
                      <Badge
                        variant="outline"
                        className={`text-[10px] px-1.5 py-0 ${prio.badgeClass}`}
                      >
                        {prio.scoreText} • {prio.label}
                      </Badge>
                    );
                  })()
                ) : (
                  <span className="text-[10px] text-amber-500 font-medium">
                    Chưa xác định — Vui lòng chọn
                  </span>
                )}
              </div>
              <Select value={docType} onValueChange={setDocType}>
                <SelectTrigger id="document-type-select" className="w-full h-10 text-xs">
                  <SelectValue placeholder="Chọn loại văn bản" />
                </SelectTrigger>
                <SelectContent>
                  {(documentTypesQuery.data || []).map((type) => (
                    <SelectItem key={type.code} value={type.code}>
                      {type.name} ({type.category_name} — Ưu tiên {type.priority}/10)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {documentTypesQuery.error ? (
                <p className="text-[11px] text-destructive">
                  Không tải được taxonomy: {documentTypesQuery.error.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="effective-year-input"
                className="text-xs font-semibold text-foreground"
              >
                Năm ban hành / Hiệu lực
              </label>
              <Input
                id="effective-year-input"
                type="text"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                placeholder="2026"
                className="h-10 text-xs font-mono"
              />
            </div>
          </div>

          {/* Grid: OCR Engine & Mức độ ưu tiên pháp lý */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="ocr-engine-select" className="text-xs font-semibold text-foreground">
                Cấu hình Bộ máy OCR
              </label>
              <Select value={ocrEngine} onValueChange={setOcrEngine}>
                <SelectTrigger id="ocr-engine-select" className="w-full h-10 text-xs">
                  <SelectValue placeholder="Chọn bộ máy OCR" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">
                    ✨ Tự động nhận diện tối ưu theo tệp (Khuyên dùng...)
                  </SelectItem>
                  <SelectItem value="mistral">
                    Mistral OCR Cloud API (Chuyên văn bản scan tiếng Việt & con dấu, siêu tốc)
                  </SelectItem>
                  <SelectItem value="docling">
                    IBM Docling TableFormer (Bóc tách ma trận bảng biểu Word & Excel)
                  </SelectItem>
                  <SelectItem value="pymupdf">
                    PyMuPDF Fast (Bóc tách văn bản số nhanh & nguyên vẹn)
                  </SelectItem>
                  <SelectItem value="easyocr">
                    EasyOCR Local (Nhận diện tài liệu scan ảnh offline & con dấu)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-foreground block">
                Mức độ ưu tiên pháp lý tự động
              </span>
              <div className="h-10 px-3 rounded-md border border-border bg-muted/40 flex items-center justify-between text-xs">
                <span className="font-mono text-muted-foreground text-[11px]">
                  {getPriorityForDocumentType(docType).scoreText}
                </span>
                <Badge
                  variant="outline"
                  className={`${getPriorityForDocumentType(docType).badgeClass} text-[11px] gap-1 font-medium`}
                >
                  <ShieldCheck className="size-3" />
                  <span>{getPriorityForDocumentType(docType).label}</span>
                </Badge>
              </div>
            </div>
          </div>

          {/* Smart Recommendation Banner khi đã chọn tệp */}
          {selectedFile && recommendation && (
            <div className="p-4 rounded-lg bg-primary/5 border border-primary/25 text-xs space-y-3 transition-all animate-in fade-in duration-300">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className="size-8 rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0">
                    <Sparkles className="size-4" />
                  </div>
                  <div>
                    <h2 className="font-bold text-foreground text-xs flex items-center gap-2">
                      <span>{recommendation.title}</span>
                    </h2>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      {recommendation.reason}
                    </p>
                  </div>
                </div>
                <Badge
                  variant="outline"
                  className="bg-primary/15 text-primary border-primary/30 text-[11px] font-semibold shrink-0"
                >
                  {recommendation.badgeText}
                </Badge>
              </div>

              <div className="text-[11px] text-muted-foreground bg-background/70 p-3 rounded-md border border-border/60 space-y-1.5 leading-relaxed">
                <p className="font-semibold text-foreground">Cấu hình tự động tối ưu đã áp dụng:</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
                  <div>
                    <span className="text-foreground font-medium">• Bộ máy OCR:</span>{" "}
                    <span className="text-primary font-medium">
                      {ocrEngine === "docling"
                        ? "IBM Docling TableFormer (Bảo toàn 100% bảng)"
                        : ocrEngine === "pymupdf"
                          ? "PyMuPDF Fast (Bóc tách native siêu tốc)"
                          : "Tự động nhận diện tối ưu theo tệp"}
                    </span>
                  </div>
                  <div>
                    <span className="text-foreground font-medium">• Loại văn bản:</span>{" "}
                    <span className="text-foreground font-medium">
                      {documentTypesQuery.data?.find((t) => t.code === docType)?.name ||
                        (docType === "de_an"
                          ? "Đề án"
                          : docType === "quy_che"
                            ? "Quy chế"
                            : docType === "quyet_dinh"
                              ? "Quyết định"
                              : docType === "thong_bao"
                                ? "Thông báo"
                                : docType
                                  ? docType.replace(/_/g, " ")
                                  : "Tự động nhận diện")}
                    </span>
                  </div>
                  <div>
                    <span className="text-foreground font-medium">• Năm hiệu lực:</span>{" "}
                    <span className="font-mono text-foreground">{year || "Mặc định"}</span>
                  </div>
                  <div>
                    <span className="text-foreground font-medium">• Chiến lược phân đoạn:</span>{" "}
                    <span className="text-foreground font-medium">
                      {recommendation.recommendedChunking === "ClauseBasedChunker"
                        ? "Phân đoạn Điều / Khoản (ClauseBasedChunker)"
                        : "Phân đoạn Ngữ nghĩa (SemanticChunker)"}
                    </span>
                  </div>
                </div>
                <p className="text-[10px] text-muted-foreground/90 pt-1 border-t border-border/40 italic">
                  💡 {recommendation.technicalDetails} Bạn có thể tùy chỉnh lại bất kỳ thông số nào
                  bên dưới nếu muốn.
                </p>
              </div>
            </div>
          )}

          {/* Drag & Drop File Upload Area */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1">
              <span>Tệp tài liệu đính kèm (PDF, DOC, DOCX, XLSX, XLS, CSV, TXT, MD, PPTX)</span>
              <span className="text-rose-500">*</span>
            </span>
            <label
              htmlFor="file-upload-input"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                if (e.dataTransfer.files?.[0]) {
                  processFile(e.dataTransfer.files[0]);
                }
              }}
              className="border-2 border-dashed border-border hover:border-primary/60 transition-colors rounded-lg p-8 flex flex-col items-center justify-center text-center cursor-pointer bg-muted/10 hover:bg-muted/20"
            >
              <input
                id="file-upload-input"
                type="file"
                className="hidden"
                accept=".pdf,.doc,.docx,.xlsx,.xls,.csv,.txt,.md,.pptx"
                onChange={handleFileChange}
              />
              <div className="size-10 rounded-full bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 flex items-center justify-center mb-3">
                <UploadCloud className="size-5" />
              </div>
              <p className="text-xs font-medium text-foreground">
                {selectedFile ? (
                  <span className="text-primary font-bold">{selectedFile.name}</span>
                ) : (
                  <>
                    Kéo thả tệp vào đây, hoặc{" "}
                    <span className="text-primary underline font-semibold">Duyệt từ máy tính</span>
                  </>
                )}
              </p>
              <p className="text-[11px] text-muted-foreground mt-1">
                Hỗ trợ PDF, DOCX, XLSX, TXT, MD, PPTX (Tối đa 50MB)
              </p>
            </label>
          </div>

          {/* Standard Policy Alert Box */}
          <div className="p-4 rounded-lg bg-muted/40 border border-border text-xs space-y-1.5 leading-relaxed">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <FileCheck2 className="size-4 text-primary" />
                Chính sách Phân đoạn:{" "}
                {recommendation?.recommendedChunking === "ClauseBasedChunker"
                  ? "Phân đoạn Điều / Khoản (ClauseBasedChunker)"
                  : "Phân đoạn Tiêu chuẩn (Standard 512-Token)"}
              </span>
              <span className="font-mono text-[11px] text-primary">
                Vector: {collection.embedding_model || "BAAI/bge-m3 (1024-dim)"}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground">
              {recommendation
                ? recommendation.technicalDetails
                : "Hệ thống sẽ bóc tách văn bản qua [✨ Tự động nhận diện tối ưu theo tệp], giữ nguyên vẹn cấu trúc bảng biểu Markdown và mở Workspace Toàn màn hình để bạn kiểm tra đối chiếu trước khi tính vector."}
            </p>
          </div>

          {/* Submission Error Banner */}
          {submitError && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/30 text-xs text-destructive leading-relaxed">
              <CircleAlert className="size-4 shrink-0 mt-0.5" />
              <span>{submitError}</span>
            </div>
          )}

          {/* Form Actions Footer */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-border/70">
            <div className="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-start">
              <Button
                type="button"
                variant="outline"
                onClick={onBack}
                className="h-9 text-xs px-4 text-muted-foreground hover:text-foreground"
              >
                Hủy & Quay lại
              </Button>

              <Button
                type="button"
                variant="ghost"
                onClick={() => onStartVerification("doc_ts_2026")}
                className="h-9 text-xs px-3 text-muted-foreground hover:text-primary gap-1.5 border border-dashed border-border hover:border-primary/40"
                title="Mở tài liệu mẫu Đề án Tuyển sinh 2026 với 14 trang scan Docling thực tế"
              >
                <Sparkles className="size-3.5 text-amber-500" />
                <span>Xem tài liệu mẫu (Tuyển sinh 2026)</span>
              </Button>
            </div>

            <Button
              type="submit"
              disabled={isProcessing || (!selectedFile && !docTitle.trim())}
              className="h-9 text-xs px-5 gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium shadow-sm w-full sm:w-auto cursor-pointer disabled:opacity-50"
            >
              {isProcessing ? (
                <>
                  <div className="size-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Đang tải lên & bóc tách...</span>
                </>
              ) : (
                <>
                  <span>Bóc tách & Mở Studio Toàn màn hình</span>
                  <ArrowRight className="size-3.5" />
                </>
              )}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
};
