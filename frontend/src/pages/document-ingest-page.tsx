import { ArrowLeft, ArrowRight, FileCheck2, ShieldCheck, UploadCloud } from "lucide-react";
import type React from "react";
import { useState } from "react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import type { KnowledgeCollection } from "../services/api-client";

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
  const [docTitle, setDocTitle] = useState<string>("Thong tin tuyen sinh dai hoc 2026 Lan2 1 (1)");
  const [docType, setDocType] = useState<string>("quy_che");
  const [year, setYear] = useState<string>("2026");
  const [ocrEngine, setOcrEngine] = useState<string>("auto");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      const f = e.target.files[0];
      setSelectedFile(f);
      if (!docTitle.trim() || docTitle === "Thong tin tuyen sinh dai hoc 2026 Lan2 1 (1)") {
        setDocTitle(f.name.replace(/\.[^/.]+$/, ""));
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);
    setTimeout(() => {
      setIsProcessing(false);
      onStartVerification("doc_ts_2026");
    }, 600);
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
              <label
                htmlFor="document-type-select"
                className="text-xs font-semibold text-foreground"
              >
                Loại văn bản
              </label>
              <select
                id="document-type-select"
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="w-full h-10 rounded-md border border-border bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="quy_che">Quy chế (Văn bản Quy phạm & Nội bộ)</option>
                <option value="de_an">Đề án & Kế hoạch Tuyển sinh</option>
                <option value="quyet_dinh">Quyết định Ban hành</option>
                <option value="thong_bao">Thông báo Hướng dẫn</option>
                <option value="giao_trinh">Giáo trình & Học liệu số</option>
              </select>
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
              <select
                id="ocr-engine-select"
                value={ocrEngine}
                onChange={(e) => setOcrEngine(e.target.value)}
                className="w-full h-10 rounded-md border border-border bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="auto">✨ Tự động nhận diện tối ưu theo tệp (Khuyên dùng...)</option>
                <option value="docling">
                  IBM Docling TableFormer (Bóc tách ma trận bảng biểu tuyển sinh)
                </option>
                <option value="pymupdf">
                  PyMuPDF Fast (Bóc tách văn bản số nhanh & nguyên vẹn)
                </option>
                <option value="easyocr">
                  EasyOCR Local (Nhận diện tài liệu scan ảnh & dấu mộc đỏ)
                </option>
              </select>
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-foreground block">
                Mức độ ưu tiên pháp lý tự động
              </span>
              <div className="h-10 px-3 rounded-md border border-border bg-muted/40 flex items-center justify-between text-xs">
                <span className="font-mono text-muted-foreground text-[11px]">Điểm: 10/10</span>
                <Badge
                  variant="outline"
                  className="bg-emerald-500/10 text-emerald-600 border-emerald-500/30 text-[11px] gap-1 font-medium"
                >
                  <ShieldCheck className="size-3" />
                  <span>Ưu tiên Cao (Cốt lõi) (x100)</span>
                </Badge>
              </div>
            </div>
          </div>

          {/* Drag & Drop File Upload Area */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1">
              <span>Tệp tài liệu đính kèm (PDF, DOC, DOCX, XLSX, XLS, CSV, TXT, MD, PPTX)</span>
              <span className="text-rose-500">*</span>
            </span>
            <label
              htmlFor="file-upload-input"
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
                Chính sách Phân đoạn: Phân đoạn Tiêu chuẩn (Standard 512-Token)
              </span>
              <span className="font-mono text-[11px] text-primary">
                Vector: {collection.embedding_model || "BAAI/bge-m3 (1024-dim)"}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Hệ thống sẽ bóc tách văn bản qua [✨ Tự động nhận diện tối ưu theo tệp], giữ nguyên
              vẹn cấu trúc bảng biểu Markdown và mở Workspace Toàn màn hình để bạn kiểm tra đối
              chiếu trước khi tính vector.
            </p>
          </div>

          {/* Form Actions Footer */}
          <div className="flex items-center justify-between pt-4 border-t border-border/70">
            <Button
              type="button"
              variant="outline"
              onClick={onBack}
              className="h-9 text-xs px-4 text-muted-foreground hover:text-foreground"
            >
              Hủy & Quay lại
            </Button>

            <Button
              type="submit"
              disabled={isProcessing}
              className="h-9 text-xs px-5 gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium shadow-sm"
            >
              {isProcessing ? (
                <>
                  <div className="size-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Đang bóc tách...</span>
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
