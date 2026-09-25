import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  Check,
  Loader2,
  RefreshCw,
  Scan,
  ShieldCheck,
  Upload,
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  OcrCanvas,
  OcrInspector,
  type OcrRegionFilter,
  type OcrRightTab,
  OcrToolbar,
  type OcrViewLayoutMode,
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
import { knowledgeApi } from "@/services/knowledge-api";
import { ocrStudioApi } from "@/services/ocr-studio-api";

import type {
  DocumentVerificationData,
  KnowledgeCollection,
} from "@/types/knowledge";
import type {
  StudioOCRDocument,
  StudioOCRPage,
  StudioOCRRegion,
} from "@/types/studio-ocr";

export interface ScanStudioPageProps {
  documentId?: string;
  collectionId?: string;
  onNavigate?: (path: string) => void;
  onBack?: () => void;
  onApproveSuccess?: () => void;
}

function classifyStudioRegion(
  text: string,
  top: number,
  height: number,
  currentType?: string,
  prevHasBottomTable = false,
): { type: string; label: string } {
  const clean = text.trim();
  const existingType = currentType?.toLowerCase();

  // Giữ nguyên bảng và con dấu nếu backend đã định danh chuẩn
  if (existingType === "table") {
    return {
      type: "table",
      label:
        prevHasBottomTable && top <= 15
          ? "Bảng dữ liệu (tiếp nối)"
          : "Bảng dữ liệu",
    };
  }
  if (existingType === "stamp") {
    return { type: "stamp", label: "Con dấu" };
  }

  // 1. Header (chỉ ở đầu trang <= 16% và BẮT ĐẦU bằng từ khóa hành chính / số hiệu)
  if (top <= 16) {
    if (
      /^(?:bộ giáo dục|trường đại học|cộng hòa xã hội|độc lập\s*-\s*tự do|số\s*[:\/])/i.test(
        clean,
      )
    ) {
      return { type: "header", label: "Phần đầu văn bản" };
    }
  }

  // 2. Signature (chỉ ở cuối trang >= 65% và BẮT ĐẦU bằng chức danh người ký / nơi nhận)
  if (top + height >= 68 || top >= 65) {
    if (
      /^(?:hiệu trưởng|kt\.\s*hiệu trưởng|phó hiệu trưởng|trưởng phòng|giám đốc|chủ tịch|tl\.\s*hiệu trưởng|nơi nhận\s*[:\/])/i.test(
        clean,
      )
    ) {
      return { type: "signature", label: "Chữ ký / Nơi nhận" };
    }
  }

  // 3. Title
  if (/^(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\.\s+[A-ZÀ-Ỹ]/i.test(clean)) {
    return { type: "title", label: "Tiêu đề" };
  }
  if (/^(?:THÔNG BÁO|QUYẾT ĐỊNH|KẾ HOẠCH|QUY ĐỊNH|HƯỚNG DẪN)\b/i.test(clean)) {
    return { type: "title", label: "Tiêu đề" };
  }

  // 4. Bảng tiếp nối
  const isAdminParagraph =
    /^(?:[a-z]\.|\d+\.|\+|-\s|Trường hợp|Theo quy định|Căn cứ|Riêng đối với)/i.test(
      clean,
    );
  const hasTableSignals =
    /\b7\d{6}\b/.test(clean) ||
    /\b(?:A00|A01|A02|B00|B08|C00|C01|D01|D07|D08|D14|D15|H00|M00|M01|N00|T00|V00)\b/.test(
      clean,
    );
  if (
    !isAdminParagraph &&
    hasTableSignals &&
    ((prevHasBottomTable && top <= 30 && height <= 15) ||
      (top <= 25 && height <= 12))
  ) {
    return { type: "table", label: "Bảng dữ liệu (tiếp nối)" };
  }

  return { type: "text", label: "Khối văn bản" };
}

function cleanStudioRegions(regions: StudioOCRRegion[]): StudioOCRRegion[] {
  const tables = regions.filter((r) => r.type === "table");
  const nonTables = regions.filter((r) => r.type !== "table");

  const validTables = tables.filter((ti, i) => {
    const areaI = ti.width * ti.height;
    if (areaI <= 0) return false;
    for (let j = 0; j < tables.length; j++) {
      if (i === j) continue;
      const tj = tables[j];
      const areaJ = tj.width * tj.height;
      if (areaJ > areaI) {
        const ix0 = Math.max(ti.left, tj.left);
        const iy0 = Math.max(ti.top, tj.top);
        const ix1 = Math.min(ti.left + ti.width, tj.left + tj.width);
        const iy1 = Math.min(ti.top + ti.height, tj.top + tj.height);
        if (ix1 > ix0 && iy1 > iy0) {
          const interArea = (ix1 - ix0) * (iy1 - iy0);
          if (interArea / areaI >= 0.7) {
            return false;
          }
        }
      }
    }
    return true;
  });

  const validNonTables = nonTables.filter((r) => {
    if (r.type === "signature" || r.type === "header") return true;
    const areaR = r.width * r.height;
    if (areaR <= 0) return true;

    let totalInterArea = 0;
    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;

    for (const t of validTables) {
      if (
        cx >= t.left - 0.5 &&
        cx <= t.left + t.width + 0.5 &&
        cy >= t.top - 0.5 &&
        cy <= t.top + t.height + 0.5
      ) {
        return false;
      }

      const ix0 = Math.max(r.left, t.left);
      const iy0 = Math.max(r.top, t.top);
      const ix1 = Math.min(r.left + r.width, t.left + t.width);
      const iy1 = Math.min(r.top + r.height, t.top + t.height);
      if (ix1 > ix0 && iy1 > iy0) {
        totalInterArea += (ix1 - ix0) * (iy1 - iy0);
      }
    }

    return !(totalInterArea / areaR >= 0.4);
  });

  return [...validTables, ...validNonTables];
}

function mapVerificationDataToStudioDoc(
  data: DocumentVerificationData,
): StudioOCRDocument {
  return {
    filename: data.filename,
    totalPages: data.total_pages,
    size: `${data.file_size_mb} MB`,
    provider: "QNU Vision OCR",
    model: data.engine,
    latencyMs: 120,
    status: data.status,
    indexStatus: data.index_status,
    pdfUrl: `/platform/v1alpha1/knowledge/documents/${data.document_id}/preview-pdf`,
    pages: data.pages.map((p, pageIdx) => {
      const prevPage = pageIdx > 0 ? data.pages[pageIdx - 1] : null;
      let prevTableCoords: { left: number; width: number } | null = null;
      if (prevPage) {
        for (const b of prevPage.bounding_boxes || []) {
          const bType = b.type?.toLowerCase();
          const rawY = b.coordinates?.y ?? 0;
          const rawH = b.coordinates?.height ?? 0;
          const bottom =
            rawY > 100 ? ((rawY + rawH) / 1131) * 100 : rawY + rawH;
          if (bType === "table" && bottom >= 60) {
            const rawX = b.coordinates?.x ?? 0;
            const rawW = b.coordinates?.width ?? 0;
            const left = rawX > 100 ? (rawX / 800) * 100 : rawX;
            const width = rawW > 100 ? (rawW / 800) * 100 : rawW;
            prevTableCoords = { left, width };
          }
        }
      }
      const prevHasBottomTable = prevTableCoords !== null;
      const isLandscapePage = false;
      const pageBaseW = isLandscapePage ? 1131 : 800;
      const pageBaseH = isLandscapePage ? 800 : 1131;

      const hasBoundingBoxes =
        Array.isArray(p.bounding_boxes) && p.bounding_boxes.length > 0;
      const mappedRegions: StudioOCRRegion[] = hasBoundingBoxes
        ? p.bounding_boxes.map((b) => {
            const rawX = b.coordinates?.x ?? 10;
            const rawY = b.coordinates?.y ?? 10;
            const rawW = b.coordinates?.width ?? 80;
            const rawH = b.coordinates?.height ?? 8;

            const left = Math.max(
              0,
              Math.min(98, rawX > 100 ? (rawX / pageBaseW) * 100 : rawX),
            );
            const top = Math.max(
              0,
              Math.min(98, rawY > 100 ? (rawY / pageBaseH) * 100 : rawY),
            );
            const width = Math.max(
              2,
              Math.min(
                100 - left,
                rawW > 100 ? (rawW / pageBaseW) * 100 : rawW,
              ),
            );
            const height = Math.max(
              1.5,
              Math.min(
                100 - top,
                rawH > 100 ? (rawH / pageBaseH) * 100 : rawH,
              ),
            );

            const classified = classifyStudioRegion(
              b.content_snippet || b.label || "",
              top,
              height,
              b.type,
              prevHasBottomTable,
            );

            const isContinuation =
              classified.label.includes("tiếp nối") ||
              (classified.type === "table" && prevHasBottomTable && top <= 15);
            const finalLeft =
              isContinuation && prevTableCoords ? prevTableCoords.left : left;
            const finalWidth =
              isContinuation && prevTableCoords ? prevTableCoords.width : width;
            const isMissedTopRow =
              isContinuation && top > 6.5 && top <= 10.0 && height <= 3.5;
            const finalTop = isMissedTopRow
              ? Math.max(5.0, top - 2.1)
              : isContinuation
                ? Math.max(0, top - 0.4)
                : top;
            const finalHeight = isMissedTopRow
              ? height + (top - finalTop)
              : isContinuation
                ? height + 0.8
                : height;

            return {
              type: classified.type,
              label: b.label || classified.label,
              text: b.content_snippet || "",
              top: finalTop,
              left: finalLeft,
              width: finalWidth,
              height: finalHeight,
              confidence: b.confidence ?? 0.95,
            };
          })
        : (p.regions || []).map((r, idx) => {
            const top = Math.min(88, 8 + idx * 9);
            const left = 8;
            const width = 84;
            const height = 7;

            const classified = classifyStudioRegion(
              r.details || r.title || "",
              top,
              height,
              r.type,
              prevHasBottomTable,
            );

            return {
              type: classified.type,
              label: r.title || classified.label,
              text: r.details || "",
              top,
              left,
              width,
              height,
              confidence: r.confidence ?? 0.95,
            };
          });

      return {
        pageNumber: p.page_number,
        title: `Trang ${p.page_number}`,
        isSigned:
          (p.regions || []).some((r) => r.type === "signature") ||
          (p.bounding_boxes || []).some((b) => b.type === "signature"),
        hasTable:
          (p.regions || []).some((r) => r.type === "table") ||
          (p.bounding_boxes || []).some((b) => b.type === "table"),
        imageUrl:
          p.image_url ||
          `/platform/v1alpha1/knowledge/documents/${data.document_id}/pages/${p.page_number}/image`,
        markdown: p.markdown_content,
        rawText: p.raw_text,
        regions: cleanStudioRegions(mappedRegions),
        dimensions: {
          width: isLandscapePage ? 1131 : 800,
          height: isLandscapePage ? 800 : 1131,
        },
        wordCount: p.word_count,
        lineCount: p.line_count,
      };
    }),
  };
}

export const ScanStudioPage: React.FC<ScanStudioPageProps> = ({
  documentId: propDocumentId,
  collectionId: propCollectionId,
  onNavigate,
  onBack,
  onApproveSuccess,
}) => {
  const queryParams = useMemo(
    () => new URLSearchParams(window.location.search),
    [],
  );
  const effectiveDocId =
    propDocumentId ||
    queryParams.get("documentId") ||
    queryParams.get("docId") ||
    queryParams.get("document") ||
    "";
  const effectiveColId =
    propCollectionId ||
    queryParams.get("collectionId") ||
    queryParams.get("collection") ||
    "";

  const isDocumentVerificationMode = Boolean(effectiveDocId);

  // Document state
  const [doc, setDoc] = useState<StudioOCRDocument | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageInput, setPageInput] = useState<string>("1");
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [showBoxes, setShowBoxes] = useState<boolean>(true);
  const [regionFilter, setRegionFilter] = useState<OcrRegionFilter>("all");
  const [selectedRegion, setSelectedRegion] =
    useState<StudioOCRRegion | null>(null);
  const [rightTab, setRightTab] = useState<OcrRightTab>("markdown");
  const [markdownViewMode, setMarkdownViewMode] =
    useState<OcrViewMode>("rendered");

  // Editable markdown state per page
  const [editedPages, setEditedPages] = useState<Record<number, string>>({});

  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [selectedEngine, setSelectedEngine] = useState<string>("pymupdf_ocr");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCopied, setIsCopied] = useState<boolean>(false);

  // Dialog states for Standalone Lab mode
  const [saveModalOpen, setSaveModalOpen] = useState<boolean>(false);
  const [collections, setCollections] = useState<KnowledgeCollection[]>([]);
  const [targetCollectionId, setTargetCollectionId] =
    useState<string>(effectiveColId);
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
          const verificationData =
            await ocrStudioApi.getDocumentVerification(effectiveDocId);
          const studioDoc = mapVerificationDataToStudioDoc(verificationData);
          setDoc(studioDoc);
          setCurrentPage(1);
          const initialEdits: Record<number, string> = {};
          for (const p of studioDoc.pages) {
            initialEdits[p.pageNumber] = p.markdown;
          }
          setEditedPages(initialEdits);
        } else {
          // In standalone mode, load sample document for preview
          const sample = await ocrStudioApi.getStudioSampleDocument();
          setDoc(sample);
          setCurrentPage(1);
        }
      } catch (err: unknown) {
        const msg =
          err instanceof Error
            ? err.message
            : "Không thể tải tài liệu bóc tách.";
        setErrorMessage(msg);
      } finally {
        setIsProcessing(false);
      }
    }
    loadData();
  }, [effectiveDocId]);

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
        return (
          r.type === "text" ||
          r.type === "header" ||
          r.type === "title" ||
          r.type === "list"
        );
      return true;
    });
  }, [currentPageData, regionFilter]);

  const totalPages = doc?.totalPages || doc?.pages?.length || 1;

  const isAlreadyApproved = useMemo(() => {
    return doc?.status === "ready" || doc?.status === "approved";
  }, [doc?.status]);

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

  // Standalone mode: File upload
  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const parsed = await ocrStudioApi.parseStudioOcr(file, selectedEngine);
      setDoc(parsed);
      setCurrentPage(1);
      toast.success(`Đã bóc tách thành công tệp: ${file.name}`);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Đã xảy ra lỗi khi phân tích văn bản.";
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
          editedPages[p.pageNumber] !== undefined
            ? editedPages[p.pageNumber]
            : p.markdown,
      }));

      await ocrStudioApi.saveDocumentVerification(effectiveDocId, {
        pages: pagesPayload,
      });
      toast.success(
        isAlreadyApproved
          ? hasEdits
            ? "Cập nhật thành công! Đã làm mới chỉ mục Vector DB đồng bộ."
            : "Tái lập chỉ mục thành công! Dữ liệu Vector DB đồng bộ 100%."
          : "Đối soát thành công! Tài liệu đã được phê duyệt và lập chỉ mục Vector.",
      );

      if (onApproveSuccess) {
        onApproveSuccess();
      } else if (effectiveColId && onNavigate) {
        onNavigate(
          `/knowledge/${encodeURIComponent(effectiveColId)}`,
        );
      } else if (onNavigate) {
        onNavigate("/knowledge");
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Phê duyệt tài liệu thất bại.";
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
      const list = await knowledgeApi.getCollections();
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
      const fullMarkdown = doc.pages
        .map((p) => p.markdown)
        .join("\n\n---\n\n");
      const blob = new Blob([fullMarkdown], { type: "text/markdown" });
      const file = new File(
        [blob],
        `${doc.filename.replace(/\.[^/.]+$/, "")}.md`,
        {
          type: "text/markdown",
        },
      );
      await knowledgeApi.uploadDocument(targetCollectionId, file, doc.filename);
      setSaveSuccess(true);
      toast.success("Đã lưu tài liệu vào Kho tri thức!");
      setTimeout(() => {
        setSaveModalOpen(false);
        setSaveSuccess(false);
      }, 1200);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Lưu vào kho thất bại.";
      toast.error(msg);
    } finally {
      setIsSaving(false);
    }
  };

  const [layoutMode, setLayoutMode] =
    useState<OcrViewLayoutMode>("continuous");

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

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] bg-background">
      {/* 1. Header Toolbar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2 border-b border-border bg-card shrink-0 gap-2">
        {/* Left: Document Info & Back Button */}
        <div className="flex items-center gap-3 min-w-0">
          {isDocumentVerificationMode && (
            <Button
              variant="ghost"
              size="icon"
              className="size-8 text-muted-foreground hover:text-foreground shrink-0 rounded-md"
              onClick={() => {
                if (onBack) {
                  onBack();
                } else if (effectiveColId && onNavigate) {
                  onNavigate(
                    `/knowledge/${encodeURIComponent(effectiveColId)}`,
                  );
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

          <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary font-mono text-[11px] font-bold">
            <Scan className="size-4" />
          </div>

          <div className="min-w-0 flex items-center gap-2">
            <h1
              className="text-sm font-semibold text-foreground truncate max-w-[280px] sm:max-w-md"
              title={doc?.filename || "Tài liệu OCR"}
            >
              {doc?.filename || "Tài liệu bóc tách"}
            </h1>
            <Badge
              variant={isDocumentVerificationMode ? "outline" : "secondary"}
              className="text-[10px] font-medium shrink-0 bg-primary/10 text-primary border-primary/30"
            >
              {isDocumentVerificationMode ? "Đối soát Scan OCR" : "OCR Lab"}
            </Badge>
          </div>
        </div>

        {/* Right Actions: Download, Upload & Approve */}
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="icon"
            onClick={handleDownloadResults}
            disabled={!doc}
            className="size-8 text-muted-foreground hover:text-foreground"
            title="Tải xuống tệp Markdown bóc tách"
            aria-label="Tải xuống Markdown"
          >
            <Upload className="size-3.5 rotate-180" />
          </Button>

          {isDocumentVerificationMode ? (
            isAlreadyApproved && !hasEdits ? (
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled
                  className="h-8 text-xs gap-1.5 font-medium border-success/30 bg-success/10 text-success cursor-default opacity-95"
                  title="Tài liệu đã được đối soát, phê duyệt và lập chỉ mục Vector DB"
                >
                  <Check className="size-3.5 text-success" strokeWidth={2.5} />
                  <span>Đã duyệt & Lập chỉ mục</span>
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleApproveDocument}
                  disabled={isApproving || isProcessing}
                  className="h-8 text-xs gap-1.5 font-medium text-muted-foreground hover:text-foreground"
                  title="Tái lập chỉ mục sạch vào Vector DB"
                >
                  {isApproving ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="size-3.5" />
                  )}
                  <span>
                    {isApproving ? "Đang xử lý..." : "Tái lập chỉ mục"}
                  </span>
                </Button>
              </div>
            ) : hasEdits ? (
              <Button
                size="sm"
                onClick={handleApproveDocument}
                disabled={isApproving || isProcessing}
                className="h-8 text-xs gap-1.5 font-semibold bg-primary hover:bg-primary/90 text-primary-foreground shadow-xs"
                title="Lưu các nội dung đã hiệu đính và tái lập chỉ mục Vector DB"
              >
                {isApproving ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="size-3.5" />
                )}
                <span>
                  {isApproving
                    ? "Đang lưu & Tái lập..."
                    : "Cập nhật & Lập chỉ mục"}
                </span>
              </Button>
            ) : (
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
                <span>
                  {isApproving
                    ? "Đang phê duyệt..."
                    : "Xác nhận đối soát & Phê duyệt"}
                </span>
              </Button>
            )
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
                <span>Tải tệp thử nghiệm</span>
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
          <span>Đang bóc tách bố cục và nhận diện quang học OCR…</span>
        </div>
      )}

      {/* 2. Main Studio Split Grid: 7 cols Canvas / 5 cols Inspector */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 p-3 min-h-0 overflow-hidden">
        {/* Left Column: Canvas & Floating Pill Toolbar */}
        <div className="lg:col-span-7 flex flex-col bg-card border border-border rounded-lg overflow-hidden shadow-xs min-h-0 relative">
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
            layoutMode={layoutMode}
            onToggleLayoutMode={setLayoutMode}
            regionFilter={regionFilter}
            onRegionFilterChange={setRegionFilter}
            selectedEngine={selectedEngine}
            onSelectEngine={setSelectedEngine}
            disabled={isProcessing}
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

        {/* Right Column: Inspector Tabs */}
        <div className="lg:col-span-5 flex flex-col min-h-0 overflow-hidden">
          <OcrInspector
            pageData={currentPageData}
            allPages={doc?.pages || []}
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

      {/* 3. Modal: Save to Knowledge Base (Lab mode) */}
      <Dialog open={saveModalOpen} onOpenChange={setSaveModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BookOpen className="size-5 text-primary" />
              <span>Lưu Vào Kho Tri Thức</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Chọn Kho Tri Thức để nạp toàn bộ các trang và dữ liệu bảng biểu
              vào chỉ mục RAG.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2 text-xs">
            <div className="space-y-1.5">
              <label
                htmlFor="target-collection-select"
                className="font-semibold text-foreground"
              >
                Chọn Kho Tri Thức:
              </label>
              <Select
                value={targetCollectionId}
                onValueChange={setTargetCollectionId}
              >
                <SelectTrigger
                  id="target-collection-select"
                  className="w-full text-xs"
                >
                  <SelectValue placeholder="Chọn kho tri thức" />
                </SelectTrigger>
                <SelectContent>
                  {collections.map((c) => (
                    <SelectItem key={c.id} value={c.id} className="text-xs">
                      {c.name} ({c.document_count} văn bản)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="p-3 bg-muted/40 rounded-md border border-border space-y-1">
              <div className="font-semibold text-foreground">
                Tệp chuẩn bị nạp:
              </div>
              <div className="text-muted-foreground">{doc?.filename}</div>
              <div className="text-[11px] text-primary">
                Sẽ tự động phân tích cú pháp và nạp vào Qdrant + PostgreSQL Facts.
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
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSaveModalOpen(false)}
            >
              Hủy
            </Button>
            <Button
              size="sm"
              onClick={handleConfirmSave}
              disabled={isSaving || !targetCollectionId || saveSuccess}
            >
              {isSaving ? (
                <Loader2 className="size-3.5 animate-spin mr-1" />
              ) : null}
              <span>{isSaving ? "Đang lưu..." : "Xác nhận nạp"}</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
