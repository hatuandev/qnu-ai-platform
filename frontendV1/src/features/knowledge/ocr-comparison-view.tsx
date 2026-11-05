import {
  AlertCircle,
  Check,
  ChevronLeft,
  ChevronRight,
  Code,
  Copy,
  Edit3,
  Eye,
  FileSpreadsheet,
  FileText,
  ImageIcon,
  Info,
  Loader2,
  Maximize2,
  RotateCcw,
  ScanSearch,
  Sparkles,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { Group, Panel, Separator, useGroupRef } from "react-resizable-panels";
import {
  type ReactZoomPanPinchContentRef,
  TransformComponent,
  TransformWrapper,
} from "react-zoom-pan-pinch";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { DocumentSheetCanvas } from "@/features/knowledge/document-sheet-canvas";
import {
  usePageImageBlobUrl,
  usePageRawText,
  useRevisionContentBlob,
} from "@/features/knowledge/ocr-queries";
import { OcrWordDiffView } from "@/features/knowledge/ocr-review-dialogs";
import {
  extractNormalizedBbox,
  formatUnitLocator,
} from "@/features/knowledge/ocr-schemas";
import type {
  PageStatusResponse,
  ProcessingRunResponse,
  ReviewDocument,
  TextUnit,
} from "@/features/knowledge/ocr-types";
import {
  DocxOriginalViewer,
  type OriginalPreviewZoomMode,
  PdfOriginalViewer,
} from "@/features/knowledge/original-file-preview";
import { cn } from "@/lib/utils";

// Sequential block types to preserve exact source order
export type SequentialBlock =
  | {
      type: "prose";
      unit: TextUnit;
      blockId: string;
      hasUnsavedDraft: boolean;
      wasSavedPreviously: boolean;
      currentText: string;
    }
  | {
      type: "table";
      blockId: string;
      rows: Array<{
        rowIdx: number;
        cells: Array<{
          unit: TextUnit;
          hasUnsavedDraft: boolean;
          wasSavedPreviously: boolean;
          currentText: string;
        }>;
      }>;
    }
  | {
      type: "image";
      blockId: string;
      assetNo: number;
      unit?: TextUnit;
    };

export type MobileReviewPane = "image" | "content" | "spelling";
export type LeftPaneViewerMode = "ocr" | "original";

export function OcrComparisonView({
  workspaceId,
  collectionId,
  sourceId,
  revisionId,
  run,
  pages,
  activePageNumber,
  onPageChange,
  reviewDoc,
  isDocx,
  canManage = true,
  draftChanges,
  onSaveDraftChange,
  onRevertUnitDraft,
  onStartSpellCheck,
  selectedUnitIds,
  onToggleUnitSelection,
  onSelectPageUnits,
  focusedEvidenceId,
  onFocusUnit,
  locateRequestNonce = 0,
  externalEditUnitId,
  onClearExternalEditUnit,
  spellingPanel,
  documentReviewOpen = false,
  spellingSuggestionsCount = 0,
  mobilePane: controlledMobilePane,
  onMobilePaneChange,
  unprocessedRightPanel,
}: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  revisionId: string;
  run: ProcessingRunResponse | null;
  pages: PageStatusResponse[];
  activePageNumber: number;
  onPageChange: (newPage: number) => void;
  reviewDoc: ReviewDocument | undefined;
  isDocx: boolean;
  canManage?: boolean;
  draftChanges?: ReadonlyMap<string, string>;
  onSaveDraftChange?: (
    evidenceId: string,
    before: string,
    after: string,
  ) => void;
  onRevertUnitDraft?: (evidenceId: string) => void;
  onStartSpellCheck?: (evidenceIds: string[]) => void;
  selectedUnitIds?: ReadonlySet<string>;
  onToggleUnitSelection?: (evidenceId: string) => void;
  onSelectPageUnits?: (evidenceIds: string[], selected: boolean) => void;
  focusedEvidenceId?: string | null;
  onFocusUnit?: (evidenceId: string | null) => void;
  locateRequestNonce?: number;
  externalEditUnitId?: string | null;
  onClearExternalEditUnit?: () => void;
  spellingPanel?: ReactNode;
  documentReviewOpen?: boolean;
  spellingSuggestionsCount?: number;
  mobilePane?: MobileReviewPane;
  onMobilePaneChange?: (pane: MobileReviewPane) => void;
  unprocessedRightPanel?: ReactNode;
}) {
  const isWordDocument = run?.pagination === "document";
  const canCompareOcr =
    !isWordDocument &&
    pages.some(
      (page) => page.page_number === activePageNumber && page.used_ocr === true,
    );
  const viewerKey = `${sourceId}:${revisionId}:${run?.id ?? ""}`;
  const [chosenMode, setChosenMode] = useState<{
    key: string;
    mode: LeftPaneViewerMode;
  }>();
  const leftPaneMode = canCompareOcr
    ? chosenMode?.key === viewerKey
      ? chosenMode.mode
      : "ocr"
    : "original";
  const [pdfPageCount, setPdfPageCount] = useState<{
    revisionId: string;
    count: number;
  }>();
  const detectedPdfPages =
    pdfPageCount?.revisionId === revisionId ? pdfPageCount.count : null;

  const handleSelectLeftPaneMode = (mode: LeftPaneViewerMode) => {
    setChosenMode({ key: viewerKey, mode });
  };

  // Zoom mode: "fit-width" (default 100% width), "fit-page" (trọn trang), "custom"
  const [zoomMode, setZoomMode] =
    useState<OriginalPreviewZoomMode>("fit-width");
  const [customZoom, setCustomZoom] = useState<number>(100);
  const [leftPanePct, setLeftPanePct] = useState<number>(50);
  const [inputPage, setInputPage] = useState<string>(String(activePageNumber));
  const [internalMobilePane, setInternalMobilePane] =
    useState<MobileReviewPane>("image");

  const activeMobilePane = controlledMobilePane ?? internalMobilePane;
  const setMobilePane = (pane: MobileReviewPane) => {
    setInternalMobilePane(pane);
    onMobilePaneChange?.(pane);
  };

  const containerRef = useRef<HTMLDivElement | null>(null);
  const splitGroupRef = useGroupRef();
  const transformRef = useRef<ReactZoomPanPinchContentRef | null>(null);
  const bboxHighlightRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setInputPage(String(activePageNumber));
  }, [activePageNumber]);

  const handleZoomIn = () => {
    if (leftPaneMode === "original") {
      setZoomMode("custom");
      setCustomZoom((prev) => Math.min(250, prev + 25));
      return;
    }
    transformRef.current?.zoomIn(0.25, 180);
  };

  const handleZoomOut = () => {
    if (leftPaneMode === "original") {
      setZoomMode("custom");
      setCustomZoom((prev) => Math.max(50, prev - 25));
      return;
    }
    transformRef.current?.zoomOut(0.25, 180);
  };

  const handleResetZoom = () => {
    setZoomMode("fit-width");
    setCustomZoom(100);
    transformRef.current?.resetTransform(180);
  };

  const handleZoomToBbox = () => {
    const el = bboxHighlightRef.current;
    if (el && el.offsetWidth > 0 && transformRef.current) {
      transformRef.current.zoomToElement(el, 2.2, 220);
    }
  };

  const handleSetSplitRatio = (leftPct: number) => {
    const clamped = Math.max(28, Math.min(72, Math.round(leftPct)));
    setLeftPanePct(clamped);
    try {
      splitGroupRef.current?.setLayout({
        "ocr-image-panel": clamped,
        "ocr-content-panel": 100 - clamped,
      });
    } catch {
      // Bỏ qua trong môi trường chưa đo kích thước DOM thực (như jsdom)
    }
  };

  const [rawDialogOpen, setRawDialogOpen] = useState<boolean>(false);
  const [fullscreenImageOpen, setFullscreenImageOpen] =
    useState<boolean>(false);
  const [activeTabRight, setActiveTabRight] = useState<string>("content");
  useEffect(() => {
    if (documentReviewOpen) setActiveTabRight("document-spelling");
  }, [documentReviewOpen]);
  const rightTab =
    activeTabRight === "document-spelling" && !documentReviewOpen
      ? "content"
      : activeTabRight;
  const [copiedType, setCopiedType] = useState<"md" | "json" | null>(null);

  // Inline edit state
  const [editingUnit, setEditingUnit] = useState<TextUnit | null>(null);
  const [editingText, setEditingText] = useState<string>("");

  // Load page image blob for OCR comparison mode
  const {
    blobUrl: imageBlobUrl,
    isLoading: imageLoading,
    error: imageError,
    refetch: refetchImage,
  } = usePageImageBlobUrl(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    run?.id,
    leftPaneMode === "ocr" ? activePageNumber : null,
    run?.status,
  );

  // Load original source revision file only when "Xem tệp gốc" is opened
  const originalRevision = useRevisionContentBlob(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    leftPaneMode === "original",
  );

  // Load raw response when dialog opens
  const {
    rawText,
    isLoading: rawLoading,
    error: rawError,
  } = usePageRawText(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    run?.id,
    activePageNumber,
    rawDialogOpen,
  );

  // Filter units for the active page
  const pageUnits = useMemo(() => {
    return (reviewDoc?.units ?? []).filter((u) => u.page === activePageNumber);
  }, [reviewDoc, activePageNumber]);

  // Selectable non-empty text units on the current page
  const selectablePageUnits = useMemo(() => {
    return pageUnits.filter(
      (u) =>
        u.kind !== "image" &&
        u.kind !== "figure" &&
        (draftChanges?.get(u.evidence_id) ?? u.text).trim().length > 0,
    );
  }, [pageUnits, draftChanges]);

  const selectedOnPageCount = useMemo(() => {
    if (!selectedUnitIds) return 0;
    return selectablePageUnits.filter((u) => selectedUnitIds.has(u.evidence_id))
      .length;
  }, [selectablePageUnits, selectedUnitIds]);

  const allPageUnitsSelected =
    selectablePageUnits.length > 0 &&
    selectedOnPageCount === selectablePageUnits.length;

  // Focused unit on the active page (for bbox highlighting and scroll)
  const focusedUnitOnPage = useMemo(() => {
    if (!focusedEvidenceId) return null;
    return pageUnits.find((u) => u.evidence_id === focusedEvidenceId) ?? null;
  }, [pageUnits, focusedEvidenceId]);

  const focusedBbox = useMemo(() => {
    if (!focusedUnitOnPage) return null;
    return extractNormalizedBbox(focusedUnitOnPage.bbox);
  }, [focusedUnitOnPage]);

  // When user clicks "Đối chiếu trên trang" / "Định vị trên trang" or focuses a unit,
  // automatically switch the left pane back to "Đối chiếu OCR" mode and scroll bbox into view.
  const prevFocusedRef = useRef<string | null | undefined>(focusedEvidenceId);
  const prevLocateNonceRef = useRef<number>(locateRequestNonce);

  useEffect(() => {
    const focusChangedToUnit =
      Boolean(focusedEvidenceId) &&
      focusedEvidenceId !== prevFocusedRef.current;
    const locateTriggered =
      locateRequestNonce > 0 &&
      locateRequestNonce !== prevLocateNonceRef.current;

    prevFocusedRef.current = focusedEvidenceId;
    prevLocateNonceRef.current = locateRequestNonce;

    if ((focusChangedToUnit || locateTriggered) && canCompareOcr) {
      setChosenMode({ key: viewerKey, mode: "ocr" });
    }
  }, [focusedEvidenceId, locateRequestNonce, canCompareOcr, viewerKey]);

  // Scroll focused unit in right pane into view when focusedEvidenceId changes
  useEffect(() => {
    if (!focusedEvidenceId || !containerRef.current) return;
    const escaped =
      typeof CSS !== "undefined" && typeof CSS.escape === "function"
        ? CSS.escape(focusedEvidenceId)
        : focusedEvidenceId.replace(/"/g, '\\"');
    const el = containerRef.current.querySelector<HTMLElement>(
      `[data-evidence-id="${escaped}"]`,
    );
    if (el && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [focusedEvidenceId]);

  // Scroll bbox highlight in left pane into view when focusedBbox is active in OCR mode
  useEffect(() => {
    void locateRequestNonce;
    if (leftPaneMode !== "ocr" || !focusedBbox) return;
    const el = bboxHighlightRef.current;
    if (el && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({
        behavior: "smooth",
        block: "center",
        inline: "center",
      });
    }
  }, [focusedBbox, leftPaneMode, locateRequestNonce]);

  const handleFocusUnitFromRightPane = (evidenceId: string | null) => {
    if (evidenceId && canCompareOcr) {
      handleSelectLeftPaneMode("ocr");
    }
    onFocusUnit?.(evidenceId);
  };

  // Handle external edit trigger (e.g. "Sửa tay" clicked from SpellingResultPanel)
  useEffect(() => {
    if (!externalEditUnitId || !canManage) return;
    const unit = (reviewDoc?.units ?? []).find(
      (u) => u.evidence_id === externalEditUnitId,
    );
    if (unit) {
      const current = draftChanges?.get(unit.evidence_id) ?? unit.text;
      setEditingUnit(unit);
      setEditingText(current);
      onClearExternalEditUnit?.();
    }
  }, [
    externalEditUnitId,
    canManage,
    reviewDoc,
    draftChanges,
    onClearExternalEditUnit,
  ]);

  // Construct sequential blocks preserving exact source order
  const sequentialBlocks = useMemo<SequentialBlock[]>(() => {
    if (pageUnits.length === 0) return [];

    const blocks: SequentialBlock[] = [];
    let currentTableBlockId: string | null = null;
    let currentTableRowsMap = new Map<
      number,
      Array<{
        unit: TextUnit;
        hasUnsavedDraft: boolean;
        wasSavedPreviously: boolean;
        currentText: string;
      }>
    >();

    const flushTable = () => {
      if (currentTableBlockId && currentTableRowsMap.size > 0) {
        const sortedRowKeys = Array.from(currentTableRowsMap.keys()).sort(
          (a, b) => a - b,
        );
        const rows = sortedRowKeys.map((rowIdx) => ({
          rowIdx,
          cells: (currentTableRowsMap.get(rowIdx) ?? []).sort(
            (a, b) => (a.unit.column ?? 0) - (b.unit.column ?? 0),
          ),
        }));
        blocks.push({
          type: "table",
          blockId: currentTableBlockId,
          rows,
        });
        currentTableRowsMap = new Map();
        currentTableBlockId = null;
      }
    };

    for (const u of pageUnits) {
      const baseBlockId = u.evidence_id.includes("_c")
        ? u.evidence_id.slice(0, u.evidence_id.indexOf("_c"))
        : u.evidence_id;

      const draftText = draftChanges?.get(u.evidence_id);
      const currentText = draftText !== undefined ? draftText : u.text;
      const hasUnsavedDraft = draftText !== undefined && draftText !== u.text;
      const wasSavedPreviously = !hasUnsavedDraft && u.text !== u.original_text;

      const isTableCell =
        u.kind === "table_cell" || u.row !== null || u.column !== null;
      const isImage = u.kind === "image" || u.kind === "figure";

      if (isTableCell) {
        if (currentTableBlockId && currentTableBlockId !== baseBlockId) {
          flushTable();
        }
        currentTableBlockId = baseBlockId;
        const rowIdx = u.row ?? 0;
        const existingRow = currentTableRowsMap.get(rowIdx) ?? [];
        existingRow.push({
          unit: u,
          hasUnsavedDraft,
          wasSavedPreviously,
          currentText,
        });
        currentTableRowsMap.set(rowIdx, existingRow);
      } else {
        flushTable();
        if (isImage) {
          const assetNo =
            ((u.bbox as Record<string, unknown>)?.asset_no as number) ?? 1;
          blocks.push({
            type: "image",
            blockId: baseBlockId,
            assetNo,
            unit: u,
          });
        } else {
          blocks.push({
            type: "prose",
            unit: u,
            blockId: baseBlockId,
            hasUnsavedDraft,
            wasSavedPreviously,
            currentText,
          });
        }
      }
    }

    flushTable();
    return blocks;
  }, [pageUnits, draftChanges]);

  // Derived Markdown for this page
  const pageMarkdown = useMemo(() => {
    const lines: string[] = [];
    const position = isWordDocument
      ? "Tài liệu Word"
      : `Trang ${activePageNumber}`;
    lines.push(`<!-- ${position} -->\n`);

    for (const block of sequentialBlocks) {
      if (block.type === "prose") {
        if (block.unit.kind === "heading") {
          lines.push(`### ${block.currentText}\n`);
        } else {
          lines.push(`${block.currentText}\n`);
        }
      } else if (block.type === "table") {
        if (block.rows.length > 0) {
          const headerRow = block.rows[0];
          const headers = headerRow.cells.map((c) => c.currentText || "—");
          lines.push(`| ${headers.join(" | ")} |`);
          lines.push(`| ${headers.map(() => "---").join(" | ")} |`);

          for (let i = 1; i < block.rows.length; i++) {
            const row = block.rows[i];
            const cells = row.cells.map((c) => c.currentText || "");
            lines.push(`| ${cells.join(" | ")} |`);
          }
          lines.push("");
        }
      } else if (block.type === "image") {
        lines.push(
          `![Ảnh đính kèm #${block.assetNo}](images/asset_${block.assetNo}.png)\n`,
        );
      }
    }

    return lines.join("\n");
  }, [sequentialBlocks, activePageNumber, isWordDocument]);

  // Derived JSON for this page (for diagnostic view)
  const pageJson = useMemo(() => {
    return JSON.stringify(
      {
        page_number: activePageNumber,
        status:
          pages.find((p) => p.page_number === activePageNumber)?.status ??
          "completed",
        units: pageUnits.map((u) => {
          const draftText = draftChanges?.get(u.evidence_id);
          return {
            evidence_id: u.evidence_id,
            kind: u.kind,
            text: draftText !== undefined ? draftText : u.text,
            original_text: u.original_text,
            row: u.row,
            column: u.column,
            bbox: u.bbox,
            is_edited: Boolean(
              draftText !== undefined || u.text !== u.original_text,
            ),
          };
        }),
      },
      null,
      2,
    );
  }, [pageUnits, activePageNumber, pages, draftChanges]);

  const handleCopy = (text: string, type: "md" | "json") => {
    void navigator.clipboard.writeText(text);
    setCopiedType(type);
    toast.success(
      type === "md"
        ? "Đã sao chép Markdown của trang này."
        : "Đã sao chép JSON của trang này.",
    );
    setTimeout(() => setCopiedType(null), 2000);
  };

  const handleStartEdit = (unit: TextUnit, currentText: string) => {
    if (!canManage) return;
    setEditingUnit(unit);
    setEditingText(currentText);
  };

  const handleSaveEdit = () => {
    if (!canManage || !editingUnit) return;
    if (editingText.trim().length === 0) {
      toast.error(
        "Không được xóa trắng hoàn toàn nội dung của đoạn/ô văn bản.",
      );
      return;
    }
    onSaveDraftChange?.(editingUnit.evidence_id, editingUnit.text, editingText);
    setEditingUnit(null);
    toast.success("Đã ghi thay đổi vào bản nháp (chưa lưu lên máy chủ).");
  };

  const activePageInfo = pages.find((p) => p.page_number === activePageNumber);
  const ocrTotalPages = (run?.pages_total ?? pages.length) || 0;
  const totalPages =
    leftPaneMode === "original" && !isDocx && detectedPdfPages
      ? detectedPdfPages
      : ocrTotalPages;

  // Phím tắt [ và ] để chuyển nhanh Trang trước / Trang sau khi rà soát
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        event.defaultPrevented ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey
      ) {
        return;
      }
      if (editingUnit || fullscreenImageOpen || rawDialogOpen) return;
      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT" ||
          target.isContentEditable)
      ) {
        return;
      }
      if (event.key === "[" && activePageNumber > 1) {
        event.preventDefault();
        onPageChange(activePageNumber - 1);
      } else if (
        event.key === "]" &&
        totalPages > 0 &&
        activePageNumber < totalPages
      ) {
        event.preventDefault();
        onPageChange(activePageNumber + 1);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    activePageNumber,
    totalPages,
    editingUnit,
    fullscreenImageOpen,
    rawDialogOpen,
    onPageChange,
  ]);

  return (
    <div ref={containerRef} className="space-y-3">
      {/* Thanh điều hướng trang tinh gọn khi là tài liệu PDF nhiều trang */}
      {!isWordDocument && totalPages > 1 ? (
        <div className="flex flex-wrap items-center justify-between gap-3 py-1 text-xs">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-foreground text-xs sm:text-sm">
              Trang {activePageNumber} / {totalPages > 0 ? totalPages : "?"}
            </span>
            {activePageInfo ? (
              <Badge
                variant={
                  activePageInfo.status === "completed"
                    ? "success"
                    : activePageInfo.status === "blank"
                      ? "secondary"
                      : activePageInfo.status === "failed"
                        ? "destructive"
                        : "outline"
                }
                className="text-[11px] py-0 font-normal"
              >
                {activePageInfo.status === "blank"
                  ? "Trang trắng (không có chữ)"
                  : activePageInfo.status === "completed"
                    ? "Đã bóc tách"
                    : activePageInfo.status === "in_flight" ||
                        activePageInfo.status === "pending"
                      ? "Đang xử lý…"
                      : activePageInfo.status}
              </Badge>
            ) : null}

            {activePageInfo?.has_tables ? (
              <Badge
                variant="outline"
                className="text-[11px] py-0 gap-1 font-normal"
              >
                <FileSpreadsheet className="size-3 text-primary" />
                <span>Có bảng biểu</span>
              </Badge>
            ) : null}

            {focusedUnitOnPage ? (
              <Badge
                variant="outline"
                className="text-[11px] py-0 gap-1 border-primary/40 bg-primary/5 text-primary"
              >
                <ScanSearch className="size-3" />
                <span>
                  Đang đối chiếu:{" "}
                  {formatUnitLocator(focusedUnitOnPage, reviewDoc?.units, {
                    includePage: false,
                  })}
                </span>
                {!focusedBbox ? (
                  <span className="text-muted-foreground">
                    (không có tọa độ vùng ảnh)
                  </span>
                ) : null}
              </Badge>
            ) : null}
          </div>

          {/* Nút chuyển trang tinh gọn cho PDF */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-8 px-2.5 text-xs gap-1"
              disabled={activePageNumber <= 1}
              onClick={() => onPageChange(activePageNumber - 1)}
              title="Trang trước (Phím tắt: [)"
            >
              <ChevronLeft className="size-3.5" />
              <span className="hidden sm:inline">Trang trước</span>
            </Button>

            <div className="flex items-center gap-1.5 font-mono text-xs px-1">
              <label
                htmlFor="ocr-page-number-input"
                className="text-muted-foreground font-sans"
              >
                Trang
              </label>
              <Input
                id="ocr-page-number-input"
                type="number"
                min={1}
                max={totalPages || 1}
                value={inputPage}
                onChange={(e) => setInputPage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    const p = parseInt(inputPage, 10);
                    if (!Number.isNaN(p) && p >= 1 && p <= totalPages) {
                      onPageChange(p);
                    }
                  }
                }}
                onBlur={() => {
                  const p = parseInt(inputPage, 10);
                  if (!Number.isNaN(p) && p >= 1 && p <= totalPages) {
                    onPageChange(p);
                  } else {
                    setInputPage(String(activePageNumber));
                  }
                }}
                className="w-14 h-8 px-1.5 text-center font-mono text-xs"
                aria-label="Số trang hiện tại"
              />
              <span className="text-muted-foreground font-sans">
                / {totalPages > 0 ? totalPages : 1}
              </span>
            </div>

            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-8 px-2.5 text-xs gap-1"
              disabled={totalPages > 0 && activePageNumber >= totalPages}
              onClick={() => onPageChange(activePageNumber + 1)}
              title="Trang sau (Phím tắt: ])"
            >
              <span className="hidden sm:inline">Trang sau</span>
              <ChevronRight className="size-3.5" />
            </Button>
          </div>
        </div>
      ) : null}

      {/* Thanh chuyển vùng rõ ràng cho Mobile / Tablet (< lg) — Giữ nguyên trang, nháp và gợi ý */}
      <div
        role="tablist"
        aria-label="Chuyển vùng hiển thị trên màn hình nhỏ"
        className="grid lg:hidden grid-cols-3 gap-1 rounded-xl border bg-muted/30 p-1"
      >
        <Button
          type="button"
          role="tab"
          aria-selected={activeMobilePane === "image"}
          variant={activeMobilePane === "image" ? "default" : "ghost"}
          size="sm"
          className="h-8 text-xs gap-1.5"
          onClick={() => setMobilePane("image")}
        >
          <ImageIcon className="size-3.5 shrink-0" />
          <span className="truncate">Ảnh trang {activePageNumber}</span>
        </Button>
        <Button
          type="button"
          role="tab"
          aria-selected={activeMobilePane === "content"}
          variant={activeMobilePane === "content" ? "default" : "ghost"}
          size="sm"
          className="h-8 text-xs gap-1.5"
          onClick={() => setMobilePane("content")}
        >
          <FileText className="size-3.5 shrink-0" />
          <span className="truncate">Văn bản ({pageUnits.length})</span>
        </Button>
        <Button
          type="button"
          role="tab"
          aria-selected={activeMobilePane === "spelling"}
          variant={activeMobilePane === "spelling" ? "default" : "ghost"}
          size="sm"
          className="h-8 text-xs gap-1.5"
          onClick={() => setMobilePane("spelling")}
        >
          <Sparkles className="size-3.5 shrink-0" />
          <span className="truncate">
            Gợi ý
            {spellingSuggestionsCount > 0
              ? ` (${spellingSuggestionsCount})`
              : ""}
          </span>
        </Button>
      </div>

      {/* Bố cục Hai Cột Đối Chiếu có thanh kéo điều chỉnh độ rộng (Desktop: Resizable Split | Mobile: Chuyển vùng 1 DOM) */}
      <Group
        id="ocr-split-group"
        groupRef={splitGroupRef}
        orientation="horizontal"
        onLayoutChanged={(layout) => {
          const left = layout["ocr-image-panel"];
          if (typeof left === "number" && !Number.isNaN(left)) {
            setLeftPanePct(Math.round(left));
          }
        }}
        className={cn(
          "w-full items-stretch",
          activeMobilePane === "image"
            ? "max-lg:[&>#ocr-content-panel]:hidden max-lg:[&>#ocr-panel-separator]:hidden max-lg:[&>#ocr-image-panel]:!basis-full"
            : "max-lg:[&>#ocr-image-panel]:hidden max-lg:[&>#ocr-panel-separator]:hidden max-lg:[&>#ocr-content-panel]:!basis-full",
        )}
      >
        {/* CỘT TRÁI: Đối chiếu OCR hoặc Xem tệp gốc (.docx / .pdf) */}
        <Panel
          id="ocr-image-panel"
          defaultSize="50%"
          minSize="28%"
          maxSize="72%"
          className="flex flex-col"
        >
          <Card
            className={cn(
              "rounded-xl shadow-2xs overflow-hidden flex-col lg:h-[calc(100vh-9rem)] min-h-[520px] lg:min-h-[640px] border-border/80 w-full",
              activeMobilePane === "image" ? "flex" : "hidden lg:flex",
            )}
          >
            {/* Thanh công cụ cố định phía trên tài liệu */}
            <div className="p-2 border-b bg-muted/20 flex items-center justify-between gap-2 text-xs min-h-[41px]">
              {/* Cột trái: Bộ chuyển chế độ Đối chiếu OCR vs Xem tệp gốc nếu tài liệu hỗ trợ */}
              <div className="flex items-center gap-2 flex-1 justify-start min-w-0">
                {canCompareOcr ? (
                  <>
                    <fieldset
                      className="inline-flex items-center rounded-lg border bg-background p-0.5"
                      aria-label="Chế độ xem tài liệu khung trái"
                    >
                      <Button
                        type="button"
                        size="sm"
                        variant={leftPaneMode === "ocr" ? "secondary" : "ghost"}
                        aria-pressed={leftPaneMode === "ocr"}
                        data-testid="left-pane-mode-ocr"
                        className="h-6 px-2.5 text-xs font-medium gap-1.5"
                        onClick={() => handleSelectLeftPaneMode("ocr")}
                      >
                        <ScanSearch className="size-3.5 text-primary" />
                        <span>Đối chiếu OCR</span>
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant={
                          leftPaneMode === "original" ? "secondary" : "ghost"
                        }
                        aria-pressed={leftPaneMode === "original"}
                        data-testid="left-pane-mode-original"
                        className="h-6 px-2.5 text-xs font-medium gap-1.5"
                        onClick={() => handleSelectLeftPaneMode("original")}
                      >
                        <Eye className="size-3.5 text-primary" />
                        <span>Xem tệp gốc</span>
                      </Button>
                    </fieldset>

                    {leftPaneMode === "ocr" ? (
                      <>
                        <span className="text-muted-foreground hidden sm:inline">
                          Trang {activePageNumber}
                        </span>
                        {isDocx ? (
                          <Badge
                            variant="outline"
                            className="text-[10px] py-0 px-1.5 border-border bg-muted/40 text-muted-foreground font-normal"
                          >
                            Bản dàn trang từ DOCX
                          </Badge>
                        ) : null}
                        {focusedBbox ? (
                          <>
                            <Badge
                              variant="outline"
                              className="text-[10px] py-0 px-1.5 border-primary/40 text-primary"
                            >
                              Đang đánh dấu vùng văn bản
                            </Badge>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="h-6 px-1.5 text-[11px] gap-1 text-primary hover:bg-primary/10"
                              onClick={handleZoomToBbox}
                              title="Phóng to trực tiếp vào vùng văn bản đang đối chiếu trên ảnh"
                            >
                              <ScanSearch className="size-3" />
                              <span>Phóng vào vùng này</span>
                            </Button>
                          </>
                        ) : null}
                      </>
                    ) : (
                      <Badge
                        variant="outline"
                        className="text-[10px] py-0 px-1.5 border-primary/30 bg-primary/5 text-primary font-normal"
                      >
                        {isDocx
                          ? "Word (.docx)"
                          : `PDF gốc · Trang ${activePageNumber}${
                              totalPages > 0 ? ` / ${totalPages}` : ""
                            }`}
                      </Badge>
                    )}
                  </>
                ) : null}
              </div>

              {/* Điều khiển Phóng to / Thu nhỏ CANH GIỮA (mặc định vừa chiều ngang) */}
              <div className="flex items-center justify-center gap-1 shrink-0">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="size-7 p-0 text-muted-foreground hover:text-foreground"
                  onClick={handleZoomOut}
                  aria-label="Thu nhỏ"
                  title="Thu nhỏ"
                >
                  <ZoomOut className="size-3.5" />
                </Button>
                <span className="text-[11px] font-mono min-w-9 text-center text-muted-foreground select-none">
                  {customZoom}%
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="size-7 p-0 text-muted-foreground hover:text-foreground"
                  onClick={handleZoomIn}
                  aria-label="Phóng to"
                  title="Phóng to"
                >
                  <ZoomIn className="size-3.5" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="size-7 p-0 text-muted-foreground hover:text-foreground"
                  onClick={handleResetZoom}
                  aria-label="Đặt lại vừa chiều ngang"
                  title="Đặt lại vừa chiều ngang"
                >
                  <RotateCcw className="size-3" />
                </Button>
                {leftPaneMode === "ocr" && imageBlobUrl ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="size-7 p-0 text-muted-foreground hover:text-foreground ml-0.5"
                    onClick={() => setFullscreenImageOpen(true)}
                    aria-label="Mở rộng ảnh toàn màn hình"
                    title="Mở rộng toàn màn hình"
                  >
                    <Maximize2 className="size-3.5" />
                  </Button>
                ) : null}
              </div>

              {/* Cột phải cân bằng khoảng trống */}
              <div className="flex items-center justify-end flex-1 min-w-0" />
            </div>

            {leftPaneMode === "original" ? (
              <div className="flex-1 overflow-hidden flex flex-col bg-muted/30 relative">
                {originalRevision.isLoading ? (
                  <div className="flex-1 flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground py-12">
                    <Loader2 className="size-6 animate-spin text-primary" />
                    <span>Đang tải tệp gốc từ kho lưu trữ...</span>
                  </div>
                ) : originalRevision.error ? (
                  <div className="flex-1 flex items-center justify-center p-4">
                    <Alert
                      variant="destructive"
                      role="alert"
                      className="max-w-md bg-background"
                    >
                      <AlertCircle className="size-4" />
                      <AlertTitle>Không tải được tệp gốc</AlertTitle>
                      <AlertDescription className="text-xs mt-1 space-y-2">
                        <p>{originalRevision.error}</p>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="h-7 text-xs bg-card"
                          onClick={() => void originalRevision.refetch()}
                        >
                          <RotateCcw className="size-3 mr-1" />
                          <span>Thử tải lại</span>
                        </Button>
                      </AlertDescription>
                    </Alert>
                  </div>
                ) : isDocx && originalRevision.blob ? (
                  <DocxOriginalViewer
                    blob={originalRevision.blob}
                    revisionKey={`${sourceId}:${revisionId}`}
                    zoomPercent={customZoom}
                    zoomMode={zoomMode}
                  />
                ) : !isDocx &&
                  (originalRevision.blob || originalRevision.blobUrl) ? (
                  <PdfOriginalViewer
                    blob={originalRevision.blob}
                    blobUrl={originalRevision.blobUrl}
                    revisionKey={`${sourceId}:${revisionId}`}
                    pageNumber={activePageNumber}
                    onPageChange={onPageChange}
                    onTotalPagesDetected={(count) =>
                      setPdfPageCount({ revisionId, count })
                    }
                    zoomPercent={customZoom}
                    zoomMode={zoomMode}
                  />
                ) : (
                  <div className="flex-1 flex items-center justify-center p-6 text-xs text-muted-foreground">
                    Chưa có dữ liệu tệp gốc cho phiên bản này.
                  </div>
                )}
              </div>
            ) : (
              <div className="flex-1 overflow-auto p-3 bg-muted/30 flex items-center justify-center relative">
                {!run ? (
                  <div className="flex flex-col items-center gap-2.5 text-xs text-muted-foreground py-12 text-center max-w-xs">
                    <ScanSearch className="size-7 text-muted-foreground/60" />
                    <span className="font-medium text-foreground">
                      Chưa có lượt bóc tách OCR
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      Tài liệu chưa được bóc tách. Bạn có thể đọc nội dung ở tab{" "}
                      <strong className="text-foreground">Xem tệp gốc</strong>{" "}
                      hoặc bấm bắt đầu bóc tách.
                    </span>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="h-7 text-xs mt-1 gap-1.5"
                      onClick={() => handleSelectLeftPaneMode("original")}
                    >
                      <Eye className="size-3.5 text-primary" />
                      <span>Mở Xem tệp gốc</span>
                    </Button>
                  </div>
                ) : imageLoading ? (
                  <div className="flex flex-col items-center gap-2 text-xs text-muted-foreground py-12">
                    <Loader2 className="size-6 animate-spin text-primary" />
                    <span>Đang tải ảnh trang {activePageNumber}...</span>
                  </div>
                ) : run.status === "running" || run.status === "queued" ? (
                  <div className="flex flex-col items-center gap-2 text-xs text-muted-foreground py-12 text-center max-w-xs">
                    <Loader2 className="size-6 animate-spin text-primary" />
                    <span className="font-medium text-foreground">
                      Đang bóc tách và tạo bản xem trước...
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      Hệ thống đang chuyển đổi tài liệu và kết xuất các trang.
                      Ảnh sẽ tự động hiển thị khi hoàn tất.
                    </span>
                  </div>
                ) : imageError ? (
                  <Alert variant="destructive" className="max-w-md">
                    <AlertCircle className="size-4" />
                    <AlertTitle>
                      Không tải được ảnh trang {activePageNumber}
                    </AlertTitle>
                    <AlertDescription className="text-xs mt-1 space-y-2">
                      <p>{imageError}</p>
                      <div className="flex items-center gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="h-7 text-xs bg-card"
                          onClick={() => void refetchImage()}
                        >
                          <RotateCcw className="size-3 mr-1" />
                          <span>Thử tải lại</span>
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          className="h-7 text-xs gap-1"
                          onClick={() => handleSelectLeftPaneMode("original")}
                        >
                          <Eye className="size-3" />
                          <span>Xem tệp gốc</span>
                        </Button>
                      </div>
                    </AlertDescription>
                  </Alert>
                ) : imageBlobUrl ? (
                  <TransformWrapper
                    ref={transformRef}
                    initialScale={1}
                    minScale={0.5}
                    maxScale={4}
                    onTransform={(_ref, state) =>
                      setCustomZoom(Math.round(state.scale * 100))
                    }
                    wheel={{ step: 0.15 }}
                    doubleClick={{ mode: "reset" }}
                    panning={{ velocityDisabled: true }}
                  >
                    <TransformComponent
                      wrapperClass="!w-full !h-full"
                      contentClass={cn(
                        "!w-full flex transition-all duration-150",
                        zoomMode === "fit-page"
                          ? "items-center justify-center !h-full"
                          : "items-start justify-center",
                      )}
                    >
                      <div
                        className={cn(
                          "relative inline-block",
                          zoomMode === "fit-width" && "w-full max-w-full",
                          zoomMode === "fit-page" && "max-w-full max-h-full",
                        )}
                      >
                        <img
                          src={imageBlobUrl}
                          alt={`Bản gốc trang ${activePageNumber}`}
                          className={cn(
                            "shadow-sm rounded border bg-white select-none block",
                            zoomMode === "fit-width" && "w-full h-auto",
                            zoomMode === "fit-page" &&
                              "max-w-full max-h-full w-auto h-auto object-contain",
                          )}
                        />
                        {/* Chỉ đánh dấu vùng ảnh khi có bbox thật, không tạo vị trí ước đoán */}
                        {focusedBbox ? (
                          <div
                            ref={bboxHighlightRef}
                            data-testid="ocr-bbox-highlight"
                            role="img"
                            aria-label="Vùng văn bản đang đối chiếu trên ảnh gốc"
                            className="absolute border-2 border-primary bg-primary/15 rounded-xs pointer-events-none transition-all duration-200"
                            style={{
                              left: `${focusedBbox.x0 * 100}%`,
                              top: `${focusedBbox.y0 * 100}%`,
                              width: `${(focusedBbox.x1 - focusedBbox.x0) * 100}%`,
                              height: `${(focusedBbox.y1 - focusedBbox.y0) * 100}%`,
                            }}
                          />
                        ) : null}
                      </div>
                    </TransformComponent>
                  </TransformWrapper>
                ) : (
                  <div className="flex flex-col items-center gap-2 text-xs text-muted-foreground text-center">
                    <span>
                      {activePageInfo?.status === "in_flight" ||
                      activePageInfo?.status === "pending"
                        ? "Trang đang chờ kết xuất..."
                        : run.status === "failed" || run.status === "uncertain"
                          ? "Lượt bóc tách chưa thành công nên chưa có ảnh đối chiếu OCR."
                          : "Chưa có ảnh cho trang này."}
                    </span>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="h-7 text-xs gap-1.5 mt-1"
                      onClick={() => handleSelectLeftPaneMode("original")}
                    >
                      <Eye className="size-3.5 text-primary" />
                      <span>Mở Xem tệp gốc</span>
                    </Button>
                  </div>
                )}
              </div>
            )}

            {isDocx && leftPaneMode === "ocr" ? (
              <div className="p-2 border-t bg-muted/20 text-[11px] text-muted-foreground flex items-center gap-1.5">
                <Info className="size-3.5 text-info shrink-0" />
                <span>
                  Ảnh trang là bản dàn trang từ DOCX sang PDF để đối chiếu trực
                  quan theo tọa độ OCR.
                </span>
              </div>
            ) : null}
          </Card>
        </Panel>

        {/* Thanh kéo chia cột trên Desktop (hỗ trợ bàn phím ArrowLeft / ArrowRight / Home / End / Enter) */}
        <Separator
          id="ocr-panel-separator"
          aria-label="Kéo để thay đổi độ rộng cột ảnh và cột văn bản"
          onKeyDownCapture={(e) => {
            if (e.key === "ArrowLeft") {
              e.preventDefault();
              e.stopPropagation();
              e.nativeEvent.stopImmediatePropagation();
              handleSetSplitRatio(leftPanePct - 4);
            } else if (e.key === "ArrowRight") {
              e.preventDefault();
              e.stopPropagation();
              e.nativeEvent.stopImmediatePropagation();
              handleSetSplitRatio(leftPanePct + 4);
            } else if (e.key === "Home") {
              e.preventDefault();
              e.stopPropagation();
              e.nativeEvent.stopImmediatePropagation();
              handleSetSplitRatio(38);
            } else if (e.key === "End") {
              e.preventDefault();
              e.stopPropagation();
              e.nativeEvent.stopImmediatePropagation();
              handleSetSplitRatio(62);
            } else if (e.key === "Enter") {
              e.preventDefault();
              e.stopPropagation();
              e.nativeEvent.stopImmediatePropagation();
              handleSetSplitRatio(50);
            }
          }}
          className="hidden lg:flex w-3 items-center justify-center group cursor-col-resize focus-visible:outline-none"
        >
          <div className="h-12 w-1 rounded-full bg-border group-hover:bg-primary/60 group-focus-visible:bg-primary transition-colors" />
        </Separator>

        {/* CỘT PHẢI: Văn bản bóc tách & Gợi ý chính tả */}
        <Panel
          id="ocr-content-panel"
          defaultSize="50%"
          minSize="28%"
          maxSize="72%"
          className="flex flex-col"
        >
          <Card
            className={cn(
              "rounded-xl shadow-2xs overflow-hidden flex-col lg:h-[calc(100vh-9rem)] min-h-[520px] lg:min-h-[640px] border-border/80 w-full",
              activeMobilePane !== "image" ? "flex" : "hidden lg:flex",
            )}
          >
            {!run && unprocessedRightPanel ? (
              <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-muted/10">
                {unprocessedRightPanel}
              </div>
            ) : (
              <Tabs
                value={rightTab}
                onValueChange={setActiveTabRight}
                className="flex-1 flex flex-col h-full min-h-0"
              >
                {/* Header Tabs: Văn bản trang | Markdown | Chi tiết kỹ thuật */}
                <div className="p-2 border-b bg-muted/20 flex items-center justify-between gap-2 flex-wrap">
                  <TabsList className="h-8">
                    {documentReviewOpen && (
                      <TabsTrigger
                        value="document-spelling"
                        className="h-7 text-xs"
                      >
                        Rà soát chính tả
                      </TabsTrigger>
                    )}
                    <TabsTrigger
                      value="content"
                      className="text-xs gap-1.5 h-7"
                    >
                      <FileText className="size-3 text-primary" />
                      <span>
                        {isWordDocument
                          ? "Văn bản"
                          : `Văn bản trang ${activePageNumber}`}
                      </span>
                    </TabsTrigger>
                    <TabsTrigger
                      value="markdown"
                      className="text-xs gap-1.5 h-7"
                    >
                      <FileText className="size-3 text-primary" />
                      <span>Markdown</span>
                    </TabsTrigger>
                    <TabsTrigger value="json" className="text-xs gap-1.5 h-7">
                      <Code className="size-3 text-primary" />
                      <span>Dữ liệu kỹ thuật</span>
                    </TabsTrigger>
                  </TabsList>

                  <div className="flex items-center gap-1.5 text-xs">
                    {activeTabRight === "markdown" ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="h-7 text-xs gap-1"
                        onClick={() => handleCopy(pageMarkdown, "md")}
                      >
                        {copiedType === "md" ? (
                          <Check className="size-3 text-success" />
                        ) : (
                          <Copy className="size-3" />
                        )}
                        <span>
                          {copiedType === "md" ? "Đã chép" : "Sao chép MD"}
                        </span>
                      </Button>
                    ) : null}

                    {activeTabRight === "json" ? (
                      <>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          className="h-7 text-xs gap-1"
                          onClick={() => handleCopy(pageJson, "json")}
                        >
                          {copiedType === "json" ? (
                            <Check className="size-3 text-success" />
                          ) : (
                            <Copy className="size-3" />
                          )}
                          <span>
                            {copiedType === "json"
                              ? "Đã chép"
                              : "Sao chép JSON"}
                          </span>
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="h-7 text-xs gap-1"
                          onClick={() => setRawDialogOpen(true)}
                        >
                          <Code className="size-3" />
                          <span>Phản hồi OCR gốc</span>
                        </Button>
                      </>
                    ) : null}
                  </div>
                </div>

                {documentReviewOpen && (
                  <TabsContent
                    forceMount
                    value="document-spelling"
                    className="m-0 flex-1 overflow-auto p-3 data-[state=inactive]:hidden"
                  >
                    {spellingPanel}
                  </TabsContent>
                )}
                {/* TAB 1: NỘI DUNG TUẦN TỰ & GỢI Ý CHÍNH TẢ */}
                <TabsContent
                  value="content"
                  className="flex-1 overflow-auto p-3 sm:p-4 m-0 bg-background space-y-2.5"
                >
                  {/* Khu vực Gợi ý chính tả: Hiển thị ngay bên cạnh ảnh trên Desktop, hoặc khi mở tab Gợi ý trên Mobile */}
                  {spellingPanel && !documentReviewOpen ? (
                    <div
                      className={cn(
                        activeMobilePane === "spelling"
                          ? "block"
                          : "hidden lg:block",
                      )}
                    >
                      {spellingPanel}
                    </div>
                  ) : activeMobilePane === "spelling" && !documentReviewOpen ? (
                    <div className="rounded-xl border border-dashed bg-card p-6 text-center space-y-2 text-xs text-muted-foreground lg:hidden">
                      <Sparkles className="size-5 text-primary mx-auto" />
                      <p className="font-medium text-foreground text-sm">
                        Chưa có lượt kiểm tra chính tả nào đang mở
                      </p>
                      <p>
                        Hãy chọn các đoạn văn trên trang rồi bấm nút{" "}
                        <strong className="text-foreground">
                          Kiểm tra chính tả
                        </strong>{" "}
                        ở thanh điều khiển phía trên để AI phân tích và đề xuất
                        sửa lỗi.
                      </p>
                      {canManage &&
                      onStartSpellCheck &&
                      selectablePageUnits.length > 0 ? (
                        <Button
                          type="button"
                          size="sm"
                          className="h-8 text-xs gap-1.5 mt-2"
                          onClick={() =>
                            onStartSpellCheck(
                              selectablePageUnits.map((u) => u.evidence_id),
                            )
                          }
                        >
                          <Sparkles className="size-3.5" />
                          <span>
                            Kiểm tra trang này ({selectablePageUnits.length}{" "}
                            đoạn)
                          </span>
                        </Button>
                      ) : null}
                    </div>
                  ) : null}

                  {/* Mặt giấy văn bản của trang (bỏ viền lồng nhau, giảm khoảng trắng giữa các đoạn) */}
                  <div
                    className={cn(
                      "space-y-2",
                      activeMobilePane === "spelling"
                        ? "hidden lg:block"
                        : "block",
                    )}
                  >
                    {/* Thanh chọn phạm vi đoạn văn trên trang để gửi AI kiểm tra chính tả */}
                    {canManage &&
                    selectablePageUnits.length > 0 &&
                    (onToggleUnitSelection || onStartSpellCheck) ? (
                      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-muted/30 px-3 py-1.5 text-xs">
                        <div className="flex items-center gap-2 flex-wrap">
                          {onSelectPageUnits ? (
                            <div className="flex items-center gap-2">
                              <Checkbox
                                id={`select-all-page-${activePageNumber}`}
                                checked={allPageUnitsSelected}
                                onCheckedChange={(checked) =>
                                  onSelectPageUnits(
                                    selectablePageUnits.map(
                                      (u) => u.evidence_id,
                                    ),
                                    Boolean(checked),
                                  )
                                }
                                aria-label={`Chọn tất cả đoạn trên trang ${activePageNumber}`}
                              />
                              <label
                                htmlFor={`select-all-page-${activePageNumber}`}
                                className="font-medium text-foreground cursor-pointer select-none"
                              >
                                Chọn đoạn trên trang {activePageNumber}
                              </label>
                            </div>
                          ) : (
                            <span className="font-medium text-foreground">
                              Trang {activePageNumber}:{" "}
                              {selectablePageUnits.length} đoạn/ô có chữ
                            </span>
                          )}

                          {selectedUnitIds ? (
                            <Badge
                              variant="secondary"
                              className="text-[11px] py-0"
                            >
                              Đã chọn {selectedOnPageCount} /{" "}
                              {selectablePageUnits.length} đoạn trên trang
                            </Badge>
                          ) : null}
                        </div>

                        {onStartSpellCheck ? (
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="h-7 px-2.5 text-xs gap-1.5 text-primary border-primary/30 hover:bg-primary/5"
                            onClick={() =>
                              onStartSpellCheck(
                                selectedOnPageCount > 0 && selectedUnitIds
                                  ? selectablePageUnits
                                      .filter((u) =>
                                        selectedUnitIds.has(u.evidence_id),
                                      )
                                      .map((u) => u.evidence_id)
                                  : selectablePageUnits.map(
                                      (u) => u.evidence_id,
                                    ),
                              )
                            }
                          >
                            <Sparkles className="size-3.5" />
                            <span>
                              {selectedOnPageCount > 0
                                ? `Kiểm tra ${selectedOnPageCount} đoạn đã chọn`
                                : `Kiểm tra trang ${activePageNumber} (${selectablePageUnits.length} đoạn)`}
                            </span>
                          </Button>
                        ) : null}
                      </div>
                    ) : null}

                    <DocumentSheetCanvas
                      sequentialBlocks={sequentialBlocks}
                      activePageNumber={activePageNumber}
                      isWordDocument={isWordDocument}
                      activePageInfo={activePageInfo}
                      reviewDoc={reviewDoc}
                      canManage={canManage}
                      canCompareOcr={canCompareOcr}
                      focusedEvidenceId={focusedEvidenceId}
                      selectedUnitIds={selectedUnitIds}
                      onToggleUnitSelection={onToggleUnitSelection}
                      onFocusUnit={handleFocusUnitFromRightPane}
                      onStartEdit={handleStartEdit}
                      onRevertUnitDraft={onRevertUnitDraft}
                      workspaceId={workspaceId}
                      collectionId={collectionId}
                      sourceId={sourceId}
                      revisionId={revisionId}
                      runId={run?.id}
                    />
                  </div>
                </TabsContent>

                {/* TAB 2: MARKDOWN DẪN XUẤT */}
                <TabsContent
                  value="markdown"
                  className="flex-1 overflow-auto p-4 m-0 font-mono text-xs whitespace-pre-wrap bg-muted/10 text-foreground leading-relaxed"
                >
                  {pageMarkdown || "Chưa có nội dung Markdown cho trang này."}
                </TabsContent>

                {/* TAB 3: DỮ LIỆU KỸ THUẬT */}
                <TabsContent
                  value="json"
                  className="flex-1 overflow-auto p-4 m-0 font-mono text-[11px] whitespace-pre-wrap bg-muted/10 text-foreground"
                >
                  {pageJson}
                </TabsContent>
              </Tabs>
            )}
          </Card>
        </Panel>
      </Group>

      {/* Modal Chỉnh sửa một khối văn bản / ô bảng */}
      <Dialog
        open={Boolean(editingUnit)}
        onOpenChange={(open) => {
          if (!open) setEditingUnit(null);
        }}
      >
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold flex items-center gap-2">
              <Edit3 className="size-4 text-primary" />
              <span>
                Chỉnh sửa{" "}
                {editingUnit
                  ? formatUnitLocator(editingUnit, reviewDoc?.units)
                  : "khối văn bản"}
              </span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Thay đổi sẽ được ghi vào bản nháp của bạn. Bấm &ldquo;Lưu phiên
              bản&rdquo; ở thanh công cụ chính để tạo phiên bản hiệu đính mới
              trên máy chủ.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <div className="space-y-1.5">
              <label
                htmlFor="edit-text-input"
                className="text-xs font-medium text-foreground"
              >
                Nội dung hiệu đính:
              </label>
              <Textarea
                id="edit-text-input"
                rows={5}
                value={editingText}
                onChange={(e) => setEditingText(e.target.value)}
                className="text-sm font-sans leading-relaxed"
              />
            </div>

            {editingUnit && editingText !== editingUnit.text ? (
              <div className="p-2.5 rounded-lg bg-muted/30 border text-xs space-y-1">
                <span className="font-semibold text-foreground block">
                  Xem trước các từ thay đổi so với bản đã lưu:
                </span>
                <OcrWordDiffView
                  before={editingUnit.text}
                  after={editingText}
                />
              </div>
            ) : null}

            {editingUnit && editingUnit.text !== editingUnit.original_text ? (
              <div className="p-2.5 rounded-lg bg-muted/40 border text-xs text-muted-foreground space-y-1">
                <span className="font-semibold text-foreground block">
                  Nội dung ở phiên bản đã lưu (v{reviewDoc?.version ?? 0}):
                </span>
                <p className="whitespace-pre-wrap">{editingUnit.text}</p>
              </div>
            ) : null}

            {editingUnit?.original_text ? (
              <div className="p-2.5 rounded-lg bg-muted/20 border text-xs text-muted-foreground space-y-1">
                <span className="font-semibold block">
                  Văn bản OCR gốc ban đầu (v0):
                </span>
                <p className="whitespace-pre-wrap">
                  {editingUnit.original_text}
                </p>
              </div>
            ) : null}
          </div>

          <DialogFooter className="flex flex-wrap items-center justify-between gap-2">
            <div>
              {editingUnit &&
              draftChanges?.has(editingUnit.evidence_id) &&
              onRevertUnitDraft ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="text-xs text-destructive hover:text-destructive gap-1"
                  onClick={() => {
                    onRevertUnitDraft(editingUnit.evidence_id);
                    setEditingUnit(null);
                  }}
                >
                  <RotateCcw className="size-3.5" />
                  <span>Hoàn tác nháp đoạn này</span>
                </Button>
              ) : null}
            </div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setEditingUnit(null)}
              >
                Hủy
              </Button>
              <Button type="button" size="sm" onClick={handleSaveEdit}>
                Áp dụng vào nháp
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Mở rộng Toàn màn hình ảnh Bản gốc */}
      <Dialog open={fullscreenImageOpen} onOpenChange={setFullscreenImageOpen}>
        <DialogContent className="max-w-5xl max-h-[92vh] flex flex-col p-2">
          <DialogHeader className="p-2 pb-0">
            <DialogTitle className="text-sm font-semibold flex items-center gap-2">
              <ImageIcon className="size-4 text-primary" />
              <span>Ảnh gốc trang {activePageNumber} (Phóng to)</span>
            </DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-auto p-2 flex items-center justify-center">
            {imageBlobUrl ? (
              <div className="relative inline-block">
                <img
                  src={imageBlobUrl}
                  alt={`Trang ${activePageNumber} phóng to`}
                  className="max-w-full h-auto rounded border shadow-lg"
                />
                {focusedBbox ? (
                  <div
                    className="absolute border-2 border-primary bg-primary/15 rounded-xs pointer-events-none"
                    style={{
                      left: `${focusedBbox.x0 * 100}%`,
                      top: `${focusedBbox.y0 * 100}%`,
                      width: `${(focusedBbox.x1 - focusedBbox.x0) * 100}%`,
                      height: `${(focusedBbox.y1 - focusedBbox.y0) * 100}%`,
                    }}
                  />
                ) : null}
              </div>
            ) : null}
          </div>
        </DialogContent>
      </Dialog>

      {/* Modal Raw OCR Response */}
      <Dialog open={rawDialogOpen} onOpenChange={setRawDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold flex items-center gap-2">
              <Code className="size-4 text-primary" />
              <span>Phản hồi OCR gốc (Trang {activePageNumber})</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Dữ liệu nguyên bản do mô hình OCR trả về cho trang này (dành cho
              kiểm tra kỹ thuật).
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-auto p-3 bg-muted/20 rounded-lg border font-mono text-[11px] whitespace-pre-wrap break-all">
            {rawLoading ? (
              <div className="p-8 flex items-center justify-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="size-4 animate-spin text-primary" />
                <span>Đang tải dữ liệu...</span>
              </div>
            ) : rawError ? (
              <p className="text-destructive">{rawError}</p>
            ) : rawText ? (
              rawText
            ) : (
              <p className="text-muted-foreground">
                Không có dữ liệu phản hồi gốc.
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
