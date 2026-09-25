import {
  AlertCircle,
  ArrowLeft,
  Check,
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
import { Progress } from "@/components/ui/progress";
import {
  type DocumentVerificationData,
  type KnowledgeCollection,
  ocrStudioApi,
  type StudioOCRDocument,
  type StudioOCRPage,
  type StudioOCRRegion,
} from "@/services/api-client";
import { OcrCanvas } from "./ocr-canvas";
import { OcrInspector } from "./ocr-inspector";
import { OcrToolbar } from "./ocr-toolbar";
import type { OcrRightTab, OcrViewLayoutMode, OcrViewMode } from "./types";

export interface DocumentStudioWorkspaceProps {
  collection: KnowledgeCollection;
  documentId: string;
  onBack: () => void;
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

  // 1. Giữ nguyên bảng và con dấu nếu backend đã định danh chuẩn
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

  // 2. Main Document Title (Ưu tiên cao nhất cho tên loại văn bản như KẾ HOẠCH, QUYẾT ĐỊNH...)
  if (
    /^(?:THÔNG BÁO|QUYẾT ĐỊNH|KẾ HOẠCH|QUY ĐỊNH|HƯỚNG DẪN|TỜ TRÌNH|BÁO CÁO|ĐỀ ÁN|PHƯƠNG ÁN|QUY CHẾ)\b/i.test(
      clean,
    )
  ) {
    return { type: "title", label: "Tiêu đề" };
  }

  // 3. Header hành chính (Quốc hiệu, Tiêu ngữ, Tên cơ quan, số hiệu)
  if (
    existingType === "header" ||
    (top <= 18 &&
      (/^(?:bộ\s+|sở\s+|trường\s+|viện\s+|đại học|cộng h[oò][aà]\s+xã hội|độc lập\s*-\s*tự do|số\s*[:/])/i.test(
        clean,
      ) ||
        /cộng h[oò][aà]\s+xã hội\s+chủ nghĩa\s+việt nam/i.test(clean) ||
        /độc lập\s*-\s*tự do\s*-\s*hạnh phúc/i.test(clean)))
  ) {
    return { type: "header", label: "Phần đầu văn bản" };
  }

  // 4. Signature & Nơi nhận
  if (existingType === "signature") {
    return { type: "signature", label: "Chữ ký / Nơi nhận" };
  }
  if (top + height >= 65 || top >= 60) {
    if (
      /^(?:hiệu trưởng|kt\.\s*hiệu trưởng|phó hiệu trưởng|trưởng phòng|giám đốc|chủ tịch|tl\.\s*hiệu trưởng|nơi nhận\s*[:/])/i.test(
        clean,
      )
    ) {
      return { type: "signature", label: "Chữ ký / Nơi nhận" };
    }
  }

  // 5. Danh sách (list)
  if (existingType === "list") {
    return { type: "list", label: "Danh sách" };
  }

  // 6. Title (tiêu đề số La Mã lớn, in hoa)
  if (/^(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\.\s+[A-ZÀ-Ỹ]/i.test(clean)) {
    return { type: "title", label: "Tiêu đề" };
  }
  const firstLine = clean.split("\n")[0].trim();
  const letters = firstLine.replace(/[^a-zA-ZÀ-ỹ]/g, "");
  if (
    top > 12 &&
    letters.length >= 8 &&
    letters.length <= 100 &&
    firstLine.length <= 120
  ) {
    const upperCount = (letters.match(/[A-ZÀ-Ỹ]/g) || []).length;
    if (upperCount / letters.length >= 0.8) {
      return { type: "title", label: "Tiêu đề" };
    }
  }

  // 7. Table continuation rescue
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

  // 8. Mặc định là Text
  return { type: "text", label: "Khối văn bản" };
}

function cleanStudioRegions(regions: StudioOCRRegion[]): StudioOCRRegion[] {
  const tables = regions.filter((r) => r.type === "table");
  const nonTables = regions.filter((r) => r.type !== "table");

  // Khử nested sub-tables: nếu bảng con A nằm lọt >= 70% trong bảng cha B, loại bỏ A
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

  // Khử text blocks rơi vào bên trong tables
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

    if (totalInterArea / areaR >= 0.4) {
      return false;
    }

    return true;
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
    pdfUrl:
      data.pdf_url ||
      `/platform/v1alpha1/knowledge/documents/${data.document_id}/preview-pdf`,
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

      const isLandscapePage = p.dimensions
        ? p.dimensions.width > p.dimensions.height
        : false;
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
              Math.min(100 - top, rawH > 100 ? (rawH / pageBaseH) * 100 : rawH),
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
              label: r.title || classified.label,
              text: r.details || "",
              top: finalTop,
              left: finalLeft,
              width: finalWidth,
              height: finalHeight,
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
        dimensions: p.dimensions || {
          width: isLandscapePage ? 1131 : 800,
          height: isLandscapePage ? 800 : 1131,
        },
        wordCount: p.word_count,
        lineCount: p.line_count,
      };
    }),
  };
}

export const DocumentStudioWorkspace: React.FC<
  DocumentStudioWorkspaceProps
> = ({ collection, documentId, onBack, onApproveSuccess }) => {
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
  const [indexingProgress, setIndexingProgress] = useState<number>(0);
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
      const verificationData =
        await ocrStudioApi.getDocumentVerification(documentId);
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
  }, [documentId]);

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

  // Rescan layout handler
  const handleRescanLayout = async () => {
    setIsRescanning(true);
    try {
      const verificationData = await ocrStudioApi.getDocumentVerification(
        documentId,
        true,
      );
      const studioDoc = mapVerificationDataToStudioDoc(verificationData);
      setDoc(studioDoc);
      toast.success("Đã làm mới bố cục và tính toán lại các khung nhận diện!");
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Làm mới bố cục thất bại.";
      toast.error(msg);
    } finally {
      setIsRescanning(false);
    }
  };

  // Approve & Vectorize handler with multi-stage progress
  const handleApproveAndIndex = async () => {
    if (!doc) return;
    setIsApproving(true);
    setIndexingProgress(15);
    setIndexingStage("Đang lưu nội dung hiệu đính...");

    const stages = [
      { p: 40, msg: "Phân mảnh ngữ nghĩa (Semantic Chunking)..." },
      { p: 70, msg: "Tạo vector embeddings đa chiều..." },
      { p: 90, msg: "Lập chỉ mục Qdrant Vector DB & Fact Layer..." },
    ];
    let stageIdx = 0;
    const progressTimer = setInterval(() => {
      if (stageIdx < stages.length) {
        setIndexingProgress(stages[stageIdx].p);
        setIndexingStage(stages[stageIdx].msg);
        stageIdx++;
      }
    }, 600);

    try {
      const pagesPayload = doc.pages.map((p) => ({
        page_number: p.pageNumber,
        markdown_content:
          editedPages[p.pageNumber] !== undefined
            ? editedPages[p.pageNumber]
            : p.markdown,
      }));

      await ocrStudioApi.saveDocumentVerification(documentId, {
        pages: pagesPayload,
      });

      clearInterval(progressTimer);
      setIndexingProgress(100);
      setIndexingStage("Lập chỉ mục Vector DB hoàn tất thành công!");

      toast.success(
        isAlreadyApproved
          ? "Đã cập nhật và tái lập chỉ mục Vector DB đồng bộ!"
          : "Phê duyệt thành công! Tài liệu đã được đưa vào Kho Tri Thức.",
      );

      setTimeout(() => {
        setIsApproving(false);
        setIndexingProgress(0);
        setIndexingStage("");
        setDoc((prev) =>
          prev ? { ...prev, status: "approved", indexStatus: "indexed" } : null,
        );
        onApproveSuccess?.();
      }, 700);
    } catch (err: unknown) {
      clearInterval(progressTimer);
      setIsApproving(false);
      setIndexingProgress(0);
      setIndexingStage("");
      const msg =
        err instanceof Error ? err.message : "Phê duyệt tài liệu thất bại.";
      toast.error(msg);
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
        <div className="flex items-center gap-1.5 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRescanLayout}
            disabled={isRescanning || isApproving}
            className="h-8 text-xs px-2.5 gap-1.5 text-muted-foreground hover:text-foreground"
            title="Phân tích lại bố cục và khung nhận diện scan"
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

          {/* Primary CTA: Phê duyệt & Lập chỉ mục Vector */}
          {isAlreadyApproved && !hasEdits ? (
            <div className="flex items-center gap-1.5">
              <Button
                size="sm"
                variant="outline"
                disabled
                className="h-8 text-xs px-3 gap-1.5 font-medium border-primary/30 bg-primary/10 text-primary cursor-default opacity-95"
              >
                <Check className="size-3 text-primary" strokeWidth={2.5} />
                <span>Đã nạp Vector</span>
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleApproveAndIndex}
                disabled={isApproving}
                className="h-8 text-xs px-2.5 gap-1.5 font-medium text-muted-foreground hover:text-foreground"
                title="Tái lập chỉ mục sạch vào Qdrant Vector DB"
              >
                <RefreshCw className="size-3" />
                <span className="hidden sm:inline">Tái index</span>
              </Button>
            </div>
          ) : hasEdits ? (
            <Button
              size="sm"
              onClick={handleApproveAndIndex}
              disabled={isApproving}
              className="h-8 text-xs px-3.5 gap-1.5 font-semibold bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm active:scale-[0.98] transition-all shrink-0 whitespace-nowrap"
              title="Lưu các nội dung đã hiệu đính và nạp vào Qdrant Vector DB"
            >
              {isApproving ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <RefreshCw className="size-3.5" />
              )}
              <span>Cập nhật</span>
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={handleApproveAndIndex}
              disabled={isApproving}
              className="h-8 text-xs px-3.5 gap-1.5 font-semibold bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm active:scale-[0.98] transition-all shrink-0 whitespace-nowrap"
              title="Xác nhận & Nạp Vector vào kho tri thức"
            >
              {isApproving ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <ShieldCheck className="size-3.5" />
              )}
              <span>Nạp Vector</span>
            </Button>
          )}
        </div>
      </div>

      {/* Indexing Progress Banner */}
      {isApproving && (
        <div className="px-4 py-2 bg-primary/10 border-b border-primary/20 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-primary flex items-center gap-1.5">
              <Loader2 className="size-3.5 animate-spin" />
              <span>{indexingStage}</span>
            </span>
            <span className="font-mono text-xs font-bold text-primary">
              {indexingProgress}%
            </span>
          </div>
          <Progress value={indexingProgress} className="h-1.5" />
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
