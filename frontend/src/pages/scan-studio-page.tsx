import {
  OcrCanvas,
  OcrInspector,
  type OcrRegionFilter,
  type OcrRightTab,
  OcrToolbar,
  type OcrViewMode,
} from "@/components/knowledge/ocr";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  type DocumentVerificationData,
  type KnowledgeCollection,
  type StudioOCRDocument,
  type StudioOCRPage,
  type StudioOCRRegion,
  apiClient,
  ocrStudioApi,
} from "@/services/api-client";
import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  Check,
  Code,
  Loader2,
  Scan,
  ShieldCheck,
  Upload,
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

export interface ScanStudioPageProps {
  documentId?: string;
  collectionId?: string;
  currentPath?: string;
  onNavigate?: (path: string) => void;
  onBack?: () => void;
  onApproveSuccess?: () => void;
}

function mapVerificationDataToStudioDoc(data: DocumentVerificationData): StudioOCRDocument {
  return {
    filename: data.filename,
    totalPages: data.total_pages,
    size: `${data.file_size_mb} MB`,
    provider: "QNU Vision OCR",
    model: data.engine,
    latencyMs: 120,
    pages: data.pages.map((p) => ({
      pageNumber: p.page_number,
      title: `Trang ${p.page_number}`,
      isSigned: p.regions.some((r) => r.type === "signature"),
      hasTable: p.regions.some((r) => r.type === "table"),
      imageUrl:
        p.image_url ||
        `/platform/v1alpha1/knowledge/documents/${data.document_id}/pages/${p.page_number}/image`,
      markdown: p.markdown_content,
      rawText: p.raw_text,
      regions: p.regions.map((r, idx) => ({
        type: r.type,
        label: r.title,
        text: r.details,
        top: 10 + ((idx * 60) % 600),
        left: 10,
        width: 780,
        height: 50,
        confidence: r.confidence,
      })),
      dimensions: { width: 800, height: 1131 },
      wordCount: p.word_count,
      lineCount: p.line_count,
    })),
  };
}

export const ScanStudioPage: React.FC<ScanStudioPageProps> = ({
  documentId: propDocumentId,
  collectionId: propCollectionId,
  onNavigate,
  onBack,
  onApproveSuccess,
}) => {
  // Query parameters resolution
  const queryParams = useMemo(() => new URLSearchParams(window.location.search), []);
  const effectiveDocId =
    propDocumentId || queryParams.get("documentId") || queryParams.get("document") || "";
  const effectiveColId =
    propCollectionId || queryParams.get("collectionId") || queryParams.get("collection") || "";

  const isDocumentVerificationMode = Boolean(effectiveDocId);

  // Document state
  const [doc, setDoc] = useState<StudioOCRDocument | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageInput, setPageInput] = useState<string>("1");
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [showBoxes, setShowBoxes] = useState<boolean>(true);
  const [regionFilter, setRegionFilter] = useState<OcrRegionFilter>("all");
  const [selectedRegion, setSelectedRegion] = useState<StudioOCRRegion | null>(null);
  const [rightTab, setRightTab] = useState<OcrRightTab>("markdown");
  const [markdownViewMode, setMarkdownViewMode] = useState<OcrViewMode>("rendered");

  // Editable markdown state per page
  const [editedPages, setEditedPages] = useState<Record<number, string>>({});

  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [selectedEngine, setSelectedEngine] = useState<string>("pymupdf_ocr");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCopied, setIsCopied] = useState<boolean>(false);

  // Dialog states for Standalone Lab mode
  const [codeModalOpen, setCodeModalOpen] = useState<boolean>(false);
  const [saveModalOpen, setSaveModalOpen] = useState<boolean>(false);
  const [collections, setCollections] = useState<KnowledgeCollection[]>([]);
  const [targetCollectionId, setTargetCollectionId] = useState<string>(effectiveColId);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load document on initial mount or when documentId changes
  useEffect(() => {
    async function loadData() {
      setIsProcessing(true);
      setErrorMessage(null);
      try {
        if (effectiveDocId) {
          const verificationData = await ocrStudioApi.getDocumentVerification(effectiveDocId);
          const studioDoc = mapVerificationDataToStudioDoc(verificationData);
          setDoc(studioDoc);
          setCurrentPage(1);
          // Initialize edited pages
          const initialEdits: Record<number, string> = {};
          for (const p of studioDoc.pages) {
            initialEdits[p.pageNumber] = p.markdown;
          }
          setEditedPages(initialEdits);
        } else {
          const sample = await apiClient.getStudioSampleDocument();
          setDoc(sample);
          setCurrentPage(1);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Không thể tải tài liệu bóc tách.";
        setErrorMessage(msg);
      } finally {
        setIsProcessing(false);
      }
    }
    loadData();
  }, [effectiveDocId]);

  // Sync page input on page change
  useEffect(() => {
    setPageInput(String(currentPage));
    setSelectedRegion(null);
  }, [currentPage]);

  const currentPageData: StudioOCRPage | null = useMemo(() => {
    if (!doc?.pages || doc.pages.length === 0) return null;
    const found = doc.pages.find((p) => p.pageNumber === currentPage);
    return found || doc.pages[0];
  }, [doc, currentPage]);

  const filteredRegions = useMemo(() => {
    if (!currentPageData?.regions) return [];
    if (regionFilter === "all") return currentPageData.regions;
    return currentPageData.regions.filter((r) => {
      if (regionFilter === "table") return r.type === "table";
      if (regionFilter === "signature") return r.type === "signature";
      if (regionFilter === "text")
        return r.type === "text" || r.type === "header" || r.type === "title" || r.type === "list";
      return true;
    });
  }, [currentPageData, regionFilter]);

  const totalPages = doc?.totalPages || doc?.pages?.length || 1;

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  const handleMarkdownChange = (text: string) => {
    setEditedPages((prev) => ({
      ...prev,
      [currentPage]: text,
    }));
  };

  const currentEditableMarkdown =
    editedPages[currentPage] !== undefined
      ? editedPages[currentPage]
      : currentPageData?.markdown || "";

  // Standalone mode: File upload
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const parsed = await apiClient.parseStudioOcr(file, selectedEngine);
      setDoc(parsed);
      setCurrentPage(1);
      toast.success(`Đã bóc tách thành công tệp: ${file.name}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Đã xảy ra lỗi khi phân tích văn bản.";
      setErrorMessage(msg);
      toast.error(msg);
    } finally {
      setIsProcessing(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  // Document verification mode: Approve document
  const handleApproveDocument = async () => {
    if (!effectiveDocId || !doc) return;
    setIsApproving(true);
    try {
      const pagesPayload = doc.pages.map((p) => ({
        page_number: p.pageNumber,
        markdown_content:
          editedPages[p.pageNumber] !== undefined ? editedPages[p.pageNumber] : p.markdown,
      }));

      await ocrStudioApi.saveDocumentVerification(effectiveDocId, { pages: pagesPayload });
      toast.success(
        "Đối soát thành công! Tài liệu đã được phê duyệt và chuyển sang chỉ mục Vector."
      );

      if (onApproveSuccess) {
        onApproveSuccess();
      } else if (effectiveColId && onNavigate) {
        onNavigate(`/knowledge/collections/${encodeURIComponent(effectiveColId)}`);
      } else if (onNavigate) {
        onNavigate("/knowledge");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Phê duyệt tài liệu thất bại.";
      toast.error(msg);
    } finally {
      setIsApproving(false);
    }
  };

  const handleCopyContent = (text: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setIsCopied(true);
    toast.success("Đã sao chép nội dung Markdown!");
    setTimeout(() => setIsCopied(false), 1500);
  };

  const handleOpenSaveModal = async () => {
    try {
      const list = await apiClient.getCollections();
      setCollections(list);
      if (list.length > 0 && !targetCollectionId) {
        setTargetCollectionId(list[0].id);
      }
      setSaveModalOpen(true);
    } catch {
      toast.error("Không tải được danh sách kho tri thức.");
    }
  };

  const handleConfirmSave = async () => {
    if (!targetCollectionId || !doc) return;
    setIsSaving(true);
    try {
      const fullMarkdown = doc.pages.map((p) => p.markdown).join("\n\n---\n\n");
      const blob = new Blob([fullMarkdown], { type: "text/markdown" });
      const file = new File([blob], `${doc.filename.replace(/\.[^/.]+$/, "")}.md`, {
        type: "text/markdown",
      });
      await apiClient.uploadDocument(targetCollectionId, file, doc.filename);
      setSaveSuccess(true);
      toast.success("Đã lưu tài liệu vào Bộ sưu tập tri thức!");
      setTimeout(() => {
        setSaveModalOpen(false);
        setSaveSuccess(false);
      }, 1200);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Lưu vào kho thất bại.";
      toast.error(msg);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] bg-background">
      {/* 1. Header Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-card shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          {isDocumentVerificationMode && (
            <Button
              variant="ghost"
              size="icon"
              className="size-8 text-muted-foreground hover:text-foreground shrink-0"
              onClick={() => {
                if (onBack) {
                  onBack();
                } else if (effectiveColId && onNavigate) {
                  onNavigate(`/knowledge/collections/${encodeURIComponent(effectiveColId)}`);
                } else if (onNavigate) {
                  onNavigate("/knowledge");
                }
              }}
              title="Quay lại Kho Tri Thức"
              aria-label="Quay lại Kho Tri Thức"
            >
              <ArrowLeft className="size-4" />
            </Button>
          )}

          <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Scan className="size-4" />
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-foreground truncate">
                {isDocumentVerificationMode
                  ? "Đối Soát & Hiệu Chỉnh OCR"
                  : "Phòng Thí Nghiệm OCR (Lab)"}
              </h1>
              <Badge
                variant={isDocumentVerificationMode ? "default" : "outline"}
                className="text-[10px] uppercase font-bold"
              >
                {isDocumentVerificationMode ? "Verification Mode" : "Lab Sandbox"}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground truncate">
              {doc?.filename
                ? `Tài liệu: ${doc.filename} (${doc.size || `${totalPages} trang`})`
                : "Phân tích cấu trúc phân cấp, nhận diện bảng biểu và bóc tách tài liệu scan."}
            </p>
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {isDocumentVerificationMode ? (
            <Button
              size="sm"
              onClick={handleApproveDocument}
              disabled={isApproving || isProcessing}
              className="h-8 text-xs gap-1.5 font-semibold bg-primary hover:bg-primary/90 text-primary-foreground shadow-xs"
            >
              {isApproving ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <ShieldCheck className="size-3.5" />
              )}
              <span>{isApproving ? "Đang phê duyệt..." : "Xác nhận đối soát & Phê duyệt"}</span>
            </Button>
          ) : (
            <>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp"
                className="hidden"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                disabled={isProcessing}
                className="h-8 text-xs gap-1.5"
              >
                <Upload className="size-3.5" />
                <span>Tải tệp lên</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={handleOpenSaveModal}
                disabled={isProcessing || !doc}
                className="h-8 text-xs gap-1.5"
              >
                <BookOpen className="size-3.5" />
                <span>Lưu vào Kho</span>
              </Button>

              <Button
                variant="ghost"
                size="icon"
                onClick={() => setCodeModalOpen(true)}
                className="size-8 text-muted-foreground hover:text-foreground"
                title="Mã API tích hợp"
                aria-label="Mã API tích hợp"
              >
                <Code className="size-4" />
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Error Alert Banner */}
      {errorMessage && (
        <div className="flex items-center gap-2 px-4 py-2 bg-destructive/10 border-b border-destructive/20 text-xs text-destructive shrink-0">
          <AlertCircle className="size-4 shrink-0" />
          <span className="flex-1">{errorMessage}</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setErrorMessage(null)}
            className="h-6 text-xs px-2"
          >
            Đóng
          </Button>
        </div>
      )}

      {/* Loading overlay */}
      {isProcessing && (
        <div className="flex items-center justify-center gap-2 py-2 bg-primary/10 border-b border-primary/20 text-xs text-primary shrink-0">
          <Loader2 className="size-4 animate-spin" />
          <span>Đang bóc tách bố cục và nhận diện chữ quang học OCR…</span>
        </div>
      )}

      {/* 2. Main Studio Split Grid */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 p-3 min-h-0 overflow-hidden">
        {/* Left Column: Canvas & Toolbar (7 cols) */}
        <div className="lg:col-span-7 flex flex-col bg-card border border-border rounded-lg overflow-hidden shadow-xs min-h-0">
          <OcrToolbar
            currentPage={currentPage}
            totalPages={totalPages}
            pageInput={pageInput}
            onPageInputChange={setPageInput}
            onPageChange={handlePageChange}
            zoomLevel={zoomLevel}
            onZoomIn={() => setZoomLevel((prev) => Math.min(200, prev + 15))}
            onZoomOut={() => setZoomLevel((prev) => Math.max(50, prev - 15))}
            onZoomReset={() => setZoomLevel(100)}
            showBoxes={showBoxes}
            onToggleBoxes={setShowBoxes}
            regionFilter={regionFilter}
            onRegionFilterChange={setRegionFilter}
            selectedEngine={selectedEngine}
            onSelectEngine={setSelectedEngine}
            disabled={isProcessing}
          />

          <OcrCanvas
            pageData={currentPageData}
            zoomLevel={zoomLevel}
            showBoxes={showBoxes}
            filteredRegions={filteredRegions}
            selectedRegion={selectedRegion}
            onSelectRegion={setSelectedRegion}
            documentTitle={doc?.filename}
          />
        </div>

        {/* Right Column: Inspector Tabs (5 cols) */}
        <div className="lg:col-span-5 flex flex-col min-h-0 overflow-hidden">
          <OcrInspector
            pageData={currentPageData}
            rightTab={rightTab}
            onTabChange={setRightTab}
            markdownViewMode={markdownViewMode}
            onMarkdownViewModeChange={setMarkdownViewMode}
            editableMarkdown={currentEditableMarkdown}
            onMarkdownChange={handleMarkdownChange}
            selectedRegion={selectedRegion}
            onSelectRegion={setSelectedRegion}
            onCopyContent={handleCopyContent}
            isCopied={isCopied}
            isEditable={isDocumentVerificationMode}
          />
        </div>
      </div>

      {/* 3. Modal: API Code Snippet */}
      <Dialog open={codeModalOpen} onOpenChange={setCodeModalOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Code className="size-5 text-primary" />
              <span>Tích Hợp API Studio OCR Cho Hệ Thống Khác</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Các phòng ban và ứng dụng con tại ĐH Quy Nhơn có thể gọi trực tiếp API này để bóc tách
              tài liệu scan.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2 text-xs">
            <p className="font-semibold text-foreground">Gọi bằng cURL (Terminal / Bash):</p>
            <pre className="p-3 bg-muted rounded-md border border-border font-mono text-xs overflow-x-auto whitespace-pre-wrap">
              {`curl -X POST "http://localhost:8001/api/v1/ocr/studio/parse" \\
  -F "file=@/duong/dan/tai_lieu_scan.pdf" \\
  -F "engine_id=docling"`}
            </pre>
            <p className="font-semibold text-foreground mt-3">
              Gọi bằng Python (httpx / requests):
            </p>
            <pre className="p-3 bg-muted rounded-md border border-border font-mono text-xs overflow-x-auto whitespace-pre-wrap">
              {`import httpx

url = "http://localhost:8001/api/v1/ocr/studio/parse"
with open("tai_lieu_scan.pdf", "rb") as f:
    files = {"file": ("tai_lieu_scan.pdf", f, "application/pdf")}
    data = {"engine_id": "docling"}
    resp = httpx.post(url, files=files, data=data, timeout=60.0)
    result = resp.json()
    print(f"Tổng số trang: {result['totalPages']}")`}
            </pre>
          </div>
          <DialogFooter>
            <Button size="sm" onClick={() => setCodeModalOpen(false)}>
              Đóng
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 4. Modal: Save to Knowledge Base (Lab mode) */}
      <Dialog open={saveModalOpen} onOpenChange={setSaveModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BookOpen className="size-5 text-primary" />
              <span>Lưu Vào Bộ Sưu Tập Tri Thức</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Chọn Kho Tri Thức để nạp toàn bộ các trang và dữ liệu bảng biểu vào chỉ mục RAG.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2 text-xs">
            <div className="space-y-1.5">
              <label htmlFor="target-collection-select" className="font-semibold text-foreground">
                Chọn Bộ Sưu Tập Mục Tiêu:
              </label>
              <Select value={targetCollectionId} onValueChange={setTargetCollectionId}>
                <SelectTrigger id="target-collection-select" className="w-full text-xs">
                  <SelectValue placeholder="Chọn bộ sưu tập" />
                </SelectTrigger>
                <SelectContent>
                  {collections.map((c) => (
                    <SelectItem key={c.id} value={c.id} className="text-xs">
                      {c.name} ({c.document_count} tài liệu)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="p-3 bg-muted/40 rounded-md border border-border space-y-1">
              <div className="font-semibold text-foreground">Tệp chuẩn bị nạp:</div>
              <div className="text-muted-foreground">{doc?.filename}</div>
              <div className="text-[11px] text-primary">
                Sẽ tự động chunking và nạp vào Qdrant + PostgreSQL Facts.
              </div>
            </div>
            {saveSuccess && (
              <div className="flex items-center gap-2 p-2 bg-emerald-500/10 text-emerald-600 rounded border border-emerald-500/20 font-medium">
                <Check className="size-4" />
                <span>Nạp tài liệu vào Kho Tri Thức thành công!</span>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setSaveModalOpen(false)}>
              Hủy
            </Button>
            <Button
              size="sm"
              onClick={handleConfirmSave}
              disabled={isSaving || !targetCollectionId || saveSuccess}
            >
              {isSaving ? <Loader2 className="size-3.5 animate-spin mr-1" /> : null}
              <span>{isSaving ? "Đang lưu..." : "Xác nhận nạp"}</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
