import {
  AlertCircle,
  ArrowLeft,
  Download,
  Loader2,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { VectorLoadControls } from "@/features/knowledge/components/vector-load-controls";
import { saveStudioRevision } from "@/features/knowledge/utils/studio-actions";
import { mapVerificationDataToStudioDoc } from "@/features/knowledge/utils/studio-mapper";
import {
  type DocumentVerificationData,
  type KnowledgeCollection,
  ocrStudioApi,
  type StudioOCRDocument,
  type StudioOCRPage,
  type StudioOCRRegion,
} from "@/services/api-client";
import { knowledgeApi } from "@/services/knowledge-api";
import { OcrCanvas } from "./ocr-canvas";
import { OcrInspector } from "./ocr-inspector";
import { OcrToolbar } from "./ocr-toolbar";
import type { OcrRightTab, OcrViewLayoutMode, OcrViewMode } from "./types";

export interface DocumentStudioWorkspaceProps {
  collection: KnowledgeCollection;
  documentId: string;
  revisionId?: string;
  onBack: () => void;
  onApproveSuccess?: (revisionId?: string) => void;
}

export const DocumentStudioWorkspace: React.FC<
  DocumentStudioWorkspaceProps
> = ({ collection, documentId, revisionId, onBack, onApproveSuccess }) => {
  // Document state
  const [doc, setDoc] = useState<StudioOCRDocument | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageInput, setPageInput] = useState<string>("1");
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [showBoxes, setShowBoxes] = useState<boolean>(true);
  const [selectedRegion, setSelectedRegion] = useState<StudioOCRRegion | null>(
    null,
  );
  const [rightTab, setRightTab] = useState<OcrRightTab>("markdown");
  const [markdownViewMode, setMarkdownViewMode] =
    useState<OcrViewMode>("rendered");

  // Editable markdown state per page
  const [editedPages, setEditedPages] = useState<Record<number, string>>({});

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRescanning, setIsRescanning] = useState<boolean>(false);
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [indexingStage, setIndexingStage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCopied, setIsCopied] = useState<boolean>(false);

  // Ergonomic Layout States
  const layoutMode: OcrViewLayoutMode = "continuous";

  // Compute document-wide structural statistics
  const totalStats = useMemo(() => {
    if (!doc?.pages) return { tables: 0, regions: 0, words: 0 };
    let tables = 0;
    let regions = 0;
    let words = 0;
    for (const p of doc.pages) {
      regions += p.regions?.length || 0;
      tables += p.regions?.filter((r) => r.type === "table").length || 0;
      words += p.wordCount || 0;
    }
    return { tables, regions, words };
  }, [doc]);

  // Keyboard navigation shortcuts (J/K or Left/Right for pages, B for bounding boxes)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }

      if (e.key === "ArrowLeft" || e.key === "j" || e.key === "J") {
        if (currentPage > 1) {
          setCurrentPage((prev) => prev - 1);
        }
      } else if (e.key === "ArrowRight" || e.key === "k" || e.key === "K") {
        if (doc?.pages && currentPage < doc.pages.length) {
          setCurrentPage((prev) => prev + 1);
        }
      } else if (e.key === "b" || e.key === "B") {
        setShowBoxes((prev) => !prev);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentPage, doc?.pages]);

  // Load document verification data
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      let verificationData: DocumentVerificationData;
      if (documentId.startsWith("bnd_") || documentId.startsWith("src_")) {
        verificationData = await knowledgeApi.getSourceStudioView(
          collection.id,
          documentId,
          revisionId,
        );
      } else {
        try {
          verificationData = await knowledgeApi.getSourceStudioView(
            collection.id,
            documentId,
            revisionId,
          );
        } catch {
          verificationData =
            await ocrStudioApi.getDocumentVerification(documentId);
        }
      }
      const studioDoc = mapVerificationDataToStudioDoc(verificationData);
      setDoc(studioDoc);
      setCurrentPage(1);

      const initialEdits: Record<number, string> = {};
      for (const p of studioDoc.pages) {
        initialEdits[p.pageNumber] = p.markdown;
      }
      setEditedPages(initialEdits);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Không thể tải dữ liệu bóc tách của tài liệu.";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }, [collection.id, documentId, revisionId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

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
    return currentPageData?.regions || [];
  }, [currentPageData]);

  const totalPages = doc?.totalPages || doc?.pages?.length || 1;

  const hasEdits = useMemo(() => {
    if (!doc?.pages) return false;
    return doc.pages.some((p) => {
      const edited = editedPages[p.pageNumber];
      return edited !== undefined && edited !== p.markdown;
    });
  }, [doc?.pages, editedPages]);

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

  // Rescan layout handler
  const handleRescanLayout = async () => {
    setIsRescanning(true);
    try {
      let verificationData: DocumentVerificationData;
      if (documentId.startsWith("bnd_") || documentId.startsWith("src_")) {
        verificationData = await knowledgeApi.getSourceStudioView(
          collection.id,
          documentId,
          doc?.revisionId || revisionId,
        );
      } else {
        verificationData = await ocrStudioApi.getDocumentVerification(
          documentId,
          true,
        );
      }
      const studioDoc = mapVerificationDataToStudioDoc(verificationData);
      setDoc(studioDoc);
      toast.success("Đã tải lại dữ liệu bố cục đã lưu; không chạy OCR lại.");
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Làm mới bố cục thất bại.";
      toast.error(msg);
    } finally {
      setIsRescanning(false);
    }
  };

  const handleSaveRevision = async (approve = false) => {
    if (!doc) return;
    setIsApproving(true);
    setIndexingStage(approve ? "Đang duyệt..." : "Đang lưu...");
    try {
      let savedRevisionId = doc.revisionId;
      if (documentId.startsWith("bnd_") || documentId.startsWith("src_")) {
        if (!doc.revisionId)
          throw new Error("Không xác định được bản đang hiển thị.");
        const markdown = hasEdits
          ? doc.pages
              .map(
                (p) =>
                  `<!-- Trang ${p.pageNumber} -->\n\n${editedPages[p.pageNumber] ?? p.markdown}`,
              )
              .join("\n\n")
          : undefined;
        const targetId = await saveStudioRevision(
          knowledgeApi,
          collection.id,
          documentId,
          { id: doc.revisionId, status: doc.status },
          markdown,
          approve,
        );
        const verified = await knowledgeApi.getSourceStudioView(
          collection.id,
          documentId,
          targetId,
        );
        const refreshed = mapVerificationDataToStudioDoc(verified);
        savedRevisionId = refreshed.revisionId;
        setDoc(refreshed);
        setEditedPages(
          Object.fromEntries(
            refreshed.pages.map((p) => [p.pageNumber, p.markdown]),
          ),
        );
      } else {
        await ocrStudioApi.saveDocumentVerification(documentId, {
          pages: doc.pages.map((p) => ({
            page_number: p.pageNumber,
            markdown_content: editedPages[p.pageNumber] ?? p.markdown,
          })),
        });
        await loadData();
      }
      toast.success(
        approve
          ? "Đã duyệt bản bóc tách."
          : "Đã lưu bản hiệu đính; chỉ mục vector chưa thay đổi.",
      );
      onApproveSuccess?.(savedRevisionId);
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Không lưu được bản bóc tách.",
      );
    } finally {
      setIsApproving(false);
      setIndexingStage("");
    }
  };

  const handleCopyContent = (text: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setIsCopied(true);
    toast.success("Đã sao chép nội dung Markdown!");
    setTimeout(() => setIsCopied(false), 1500);
  };

  const handleDownloadResults = () => {
    if (!doc) return;
    const fullMarkdown = doc.pages
      .map((p) =>
        editedPages[p.pageNumber] !== undefined
          ? editedPages[p.pageNumber]
          : p.markdown,
      )
      .join("\n\n---\n\n");
    const blob = new Blob([fullMarkdown], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(doc.filename || "ocr_export").replace(/\.[^/.]+$/, "")}_boc_tach.md`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Đã tải xuống tệp Markdown bóc tách!");
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] p-8 space-y-4 bg-card rounded-lg border border-border">
        <div className="relative flex items-center justify-center size-14 rounded-full bg-primary/10 text-primary">
          <Loader2 className="size-7 animate-spin" />
        </div>
        <div className="text-center space-y-1">
          <h3 className="text-sm font-semibold text-foreground">
            Đang nạp không gian làm việc Studio bóc tách...
          </h3>
          <p className="text-xs text-muted-foreground">
            Tải cấu trúc trang, tọa độ bounding boxes và nội dung Markdown
          </p>
        </div>
      </div>
    );
  }

  if (errorMessage || !doc) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] p-8 space-y-4 bg-card rounded-lg border border-border">
        <div className="relative flex items-center justify-center size-14 rounded-full bg-destructive/10 text-destructive">
          <AlertCircle className="size-7" />
        </div>
        <div className="text-center space-y-1 max-w-md">
          <h3 className="text-sm font-semibold text-foreground">
            Không thể nạp dữ liệu bóc tách của tài liệu
          </h3>
          <p className="text-xs text-muted-foreground">
            {errorMessage ||
              "Tài liệu chưa có dữ liệu bố cục hoặc đang trong tiến trình xử lý."}
          </p>
        </div>
        <div className="flex items-center gap-2 pt-2">
          <Button variant="outline" size="sm" onClick={onBack}>
            Quay lại kho
          </Button>
          <Button size="sm" onClick={() => loadData()}>
            Thử lại
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8.5rem)] min-h-[640px] bg-background border border-border rounded-lg overflow-hidden shadow-xs">
      {/* 1. Integrated Modern Header Toolbar */}
      <div className="flex flex-wrap items-center justify-between px-3 py-2 border-b border-border bg-card shrink-0 gap-2">
        {/* Left: Back & Document Metadata */}
        <div className="flex items-center gap-2 min-w-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground gap-1.5 rounded-md shrink-0 whitespace-nowrap"
            title={`Quay lại: ${collection.name}`}
          >
            <ArrowLeft className="size-3.5" />
            <span className="font-medium">Quay lại</span>
          </Button>

          <div className="h-4 w-px bg-border/80 hidden sm:block" />

          {/* Document Format & Title */}
          <div className="min-w-0 flex items-center gap-2">
            <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary font-mono text-[10px] font-bold">
              PDF
            </div>
            <h2
              className="text-xs sm:text-sm font-semibold text-foreground truncate max-w-[180px] sm:max-w-xs md:max-w-sm"
              title={doc?.filename || "Tài liệu bóc tách"}
            >
              {doc?.filename || "Tài liệu bóc tách"}
            </h2>
          </div>

          {/* Document Structural Stats Badges */}
          <div className="hidden xl:flex items-center gap-1.5 pl-1">
            <Badge
              variant="outline"
              className="text-[10px] font-mono bg-muted/40 text-muted-foreground border-border/80"
            >
              {totalPages} trang
            </Badge>
            {totalStats.tables > 0 && (
              <Badge
                variant="outline"
                className="text-[10px] font-mono bg-primary/5 text-primary border-primary/20"
              >
                {totalStats.tables} bảng biểu
              </Badge>
            )}
            <Badge
              variant="outline"
              className="text-[10px] font-mono bg-muted/40 text-muted-foreground border-border/80"
            >
              {totalStats.regions} khối
            </Badge>
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex flex-wrap items-center gap-1.5 min-w-0">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRescanLayout}
            disabled={isRescanning || isApproving}
            className="h-8 text-xs px-2.5 gap-1.5 text-muted-foreground hover:text-foreground"
            title="Tải lại dữ liệu bố cục đã lưu"
          >
            {isRescanning ? (
              <Loader2 className="size-3 animate-spin" />
            ) : (
              <RefreshCw className="size-3" />
            )}
            <span className="hidden md:inline">Làm mới</span>
          </Button>

          <Button
            variant="outline"
            size="icon"
            onClick={handleDownloadResults}
            disabled={!doc || isApproving}
            className="size-8 text-muted-foreground hover:text-foreground"
            title="Tải xuống tài liệu Markdown"
            aria-label="Tải xuống Markdown"
          >
            <Download className="size-3.5" />
          </Button>

          <Button
            size="sm"
            onClick={() => handleSaveRevision()}
            variant="outline"
            disabled={isApproving || !hasEdits}
          >
            Lưu Markdown
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleSaveRevision(true)}
            disabled={
              isApproving || hasEdits || doc?.status !== "review_required"
            }
          >
            <ShieldCheck className="size-3.5" /> Duyệt
          </Button>
          <VectorLoadControls
            collectionId={collection.id}
            targets={
              doc.revisionId
                ? [
                    {
                      binding_id: documentId,
                      source_revision_id: doc.revisionId,
                    },
                  ]
                : []
            }
            disabledReason={
              doc.indexStatus === "paused"
                ? "Nguồn đã ngừng dùng."
                : isApproving
                  ? "Đang lưu Markdown."
                  : hasEdits
                    ? "Hãy lưu Markdown trước khi nạp vector."
                    : doc.status !== "ready"
                      ? "Hãy duyệt Markdown trước khi nạp vector."
                      : undefined
            }
          />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-border bg-muted/30 px-4 py-2 text-xs text-muted-foreground">
        <Badge variant="outline">
          {hasEdits
            ? "Markdown chưa lưu"
            : doc.status === "ready"
              ? "MD sẵn sàng"
              : "Chờ duyệt / xử lý"}
        </Badge>
        <span>Lưu Markdown → Duyệt nếu cần → Nạp vector → Xuất bản</span>
      </div>

      {/* Indexing Progress Banner */}
      {isApproving && (
        <div className="px-4 py-2 bg-primary/10 border-b border-primary/20 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-primary flex items-center gap-1.5">
              <Loader2 className="size-3.5 animate-spin" />
              <span>{indexingStage}</span>
            </span>
          </div>
        </div>
      )}

      {/* Error Banner */}
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

      {/* 2. Main Studio Body with Balanced 50:50 Split Grid */}
      <div className="flex-1 flex min-h-0 overflow-hidden p-2 gap-2">
        {/* Balanced 50:50 Split Grid (Canvas & Inspector) */}
        <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-2 gap-2 overflow-hidden">
          {/* Left: Canvas & Toolbar */}
          <div className="flex flex-col bg-card border border-border rounded-lg overflow-hidden shadow-xs min-h-0 relative">
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
              onFitWidth={() => setZoomLevel(90)}
              showBoxes={showBoxes}
              onToggleBoxes={setShowBoxes}
              selectedEngine={doc?.model || "pymupdf_ocr"}
              onSelectEngine={() => {}}
              disabled={isLoading || isRescanning}
            />

            <OcrCanvas
              pageData={currentPageData}
              allPages={doc?.pages || []}
              layoutMode={layoutMode}
              zoomLevel={zoomLevel}
              showBoxes={showBoxes}
              filteredRegions={filteredRegions}
              selectedRegion={selectedRegion}
              onSelectRegion={setSelectedRegion}
              documentTitle={doc?.filename}
              pdfUrl={doc?.pdfUrl}
              onPageChange={handlePageChange}
            />
          </div>

          {/* Right: Inspector Tabs */}
          <div className="flex flex-col min-h-0 overflow-hidden">
            <OcrInspector
              citationMetadata={doc?.citationMetadata}
              structuredArtifact={doc?.structuredArtifact}
              layoutTextAlignment={doc?.layoutTextAlignment}
              pageData={currentPageData}
              allPages={doc?.pages || []}
              documentTitle={doc?.filename}
              documentFilename={doc?.filename}
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
              isEditable={true}
              onJumpToPage={handlePageChange}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
