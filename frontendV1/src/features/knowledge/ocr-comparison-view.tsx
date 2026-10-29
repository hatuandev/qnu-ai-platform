import {
  AlertCircle,
  Check,
  ChevronLeft,
  ChevronRight,
  Code,
  Copy,
  Edit3,
  FileSpreadsheet,
  FileText,
  ImageIcon,
  Info,
  Loader2,
  Maximize2,
  RotateCcw,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { AuthenticatedEmbeddedImage } from "@/features/knowledge/embedded-image";
import {
  usePageImageBlobUrl,
  usePageRawText,
} from "@/features/knowledge/ocr-queries";
import type {
  PageStatusResponse,
  ProcessingRunResponse,
  ReviewDocument,
  TextUnit,
} from "@/features/knowledge/ocr-types";
import { cn } from "@/lib/utils";

// Sequential block types to preserve exact source order
export type SequentialBlock =
  | {
      type: "prose";
      unit: TextUnit;
      blockId: string;
      isEdited: boolean;
      currentText: string;
    }
  | {
      type: "table";
      blockId: string;
      rows: Array<{
        rowIdx: number;
        cells: Array<{
          unit: TextUnit;
          isEdited: boolean;
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
  draftChanges,
  onSaveDraftChange,
  onStartSpellCheck: _onStartSpellCheck,
}: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  revisionId: string;
  run: ProcessingRunResponse;
  pages: PageStatusResponse[];
  activePageNumber: number;
  onPageChange: (newPage: number) => void;
  reviewDoc: ReviewDocument | undefined;
  isDocx: boolean;
  draftChanges?: ReadonlyMap<string, string>;
  onSaveDraftChange?: (
    evidenceId: string,
    before: string,
    after: string,
  ) => void;
  onStartSpellCheck?: (evidenceIds: string[]) => void;
}) {
  // Zoom mode: "fit-width" (default 100% width), "fit-page" (trọn trang), "custom"
  const [zoomMode, setZoomMode] = useState<"fit-width" | "fit-page" | "custom">(
    "fit-width",
  );
  const [customZoom, setCustomZoom] = useState<number>(100);
  const [inputPage, setInputPage] = useState<string>(String(activePageNumber));

  useEffect(() => {
    setInputPage(String(activePageNumber));
  }, [activePageNumber]);

  const handleZoomIn = () => {
    setZoomMode("custom");
    setCustomZoom((prev) => Math.min(250, prev + 20));
  };

  const handleZoomOut = () => {
    setZoomMode("custom");
    setCustomZoom((prev) => Math.max(50, prev - 20));
  };

  const handleResetZoom = () => {
    setZoomMode("fit-width");
    setCustomZoom(100);
  };

  const handleToggleFit = () => {
    setZoomMode((prev) => (prev === "fit-width" ? "fit-page" : "fit-width"));
  };

  const [rawDialogOpen, setRawDialogOpen] = useState<boolean>(false);
  const [fullscreenImageOpen, setFullscreenImageOpen] =
    useState<boolean>(false);
  const [activeTabDesktop, setActiveTabDesktop] = useState<string>("content");
  const [activeTabMobile, setActiveTabMobile] = useState<string>("content");
  const [copiedType, setCopiedType] = useState<"md" | "json" | null>(null);

  // Inline edit state
  const [editingUnit, setEditingUnit] = useState<TextUnit | null>(null);
  const [editingText, setEditingText] = useState<string>("");

  // Load page image blob
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
    run.id,
    activePageNumber,
    run.status,
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
    run.id,
    activePageNumber,
    rawDialogOpen,
  );

  // Filter units for the active page
  const pageUnits = useMemo(() => {
    return (reviewDoc?.units ?? []).filter((u) => u.page === activePageNumber);
  }, [reviewDoc, activePageNumber]);

  // Construct sequential blocks preserving exact source order
  const sequentialBlocks = useMemo<SequentialBlock[]>(() => {
    if (pageUnits.length === 0) return [];

    const blocks: SequentialBlock[] = [];
    let currentTableBlockId: string | null = null;
    let currentTableRowsMap = new Map<
      number,
      Array<{ unit: TextUnit; isEdited: boolean; currentText: string }>
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
      // Get base block ID
      const baseBlockId = u.evidence_id.includes("_c")
        ? u.evidence_id.slice(0, u.evidence_id.indexOf("_c"))
        : u.evidence_id;

      // Determine text with draft if available
      const draftText = draftChanges?.get(u.evidence_id);
      const currentText = draftText !== undefined ? draftText : u.text;
      const isEdited = Boolean(
        draftText !== undefined || u.text !== u.original_text,
      );

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
        existingRow.push({ unit: u, isEdited, currentText });
        currentTableRowsMap.set(rowIdx, existingRow);
      } else {
        flushTable();
        if (isImage) {
          // Extract asset number from block or fallback to 1
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
            isEdited,
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
    lines.push(`<!-- Trang ${activePageNumber} -->\n`);

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
  }, [sequentialBlocks, activePageNumber]);

  // Derived JSON for this page
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
    setEditingUnit(unit);
    setEditingText(currentText);
  };

  const handleSaveEdit = () => {
    if (!editingUnit) return;
    onSaveDraftChange?.(editingUnit.evidence_id, editingUnit.text, editingText);
    setEditingUnit(null);
    toast.success("Đã ghi thay đổi vào bản nháp.");
  };

  const activePageInfo = pages.find((p) => p.page_number === activePageNumber);
  const totalPages = run.pages_total ?? pages.length;

  return (
    <div className="space-y-3">
      {/* Thanh điều hướng trang phẳng dùng chung cho cả 2 cột (Không đóng hộp chồng hộp) */}
      <div className="flex flex-wrap items-center justify-between gap-3 py-1 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-foreground">
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
              className="text-[10px] py-0 font-normal"
            >
              {activePageInfo.status === "blank"
                ? "Trang trắng"
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
              className="text-[10px] py-0 gap-1 font-normal"
            >
              <FileSpreadsheet className="size-3 text-primary" />
              <span>Có bảng</span>
            </Badge>
          ) : null}
        </div>

        {/* Nút chuyển trang tinh gọn */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <Button
            size="sm"
            variant="outline"
            className="h-8 px-2.5 text-xs gap-1"
            disabled={activePageNumber <= 1}
            onClick={() => onPageChange(activePageNumber - 1)}
          >
            <ChevronLeft className="size-3.5" />
            <span className="hidden sm:inline">Trang trước</span>
          </Button>

          <div className="flex items-center gap-1.5 font-mono text-xs px-1">
            <span className="text-muted-foreground font-sans">Trang</span>
            <input
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
              className="w-12 h-8 text-center rounded-md border border-input bg-background font-mono text-xs focus:ring-1 focus:ring-primary focus:outline-hidden"
              title="Nhập số trang và nhấn Enter"
            />
            <span className="text-muted-foreground font-sans">
              / {totalPages > 0 ? totalPages : 1}
            </span>
          </div>

          <Button
            size="sm"
            variant="outline"
            className="h-8 px-2.5 text-xs gap-1"
            disabled={totalPages > 0 && activePageNumber >= totalPages}
            onClick={() => onPageChange(activePageNumber + 1)}
          >
            <span className="hidden sm:inline">Trang sau</span>
            <ChevronRight className="size-3.5" />
          </Button>

          {/* Raw Response trigger */}
          <Button
            size="sm"
            variant="ghost"
            className="h-8 px-2 text-xs gap-1 ml-1 text-muted-foreground hover:text-foreground"
            onClick={() => setRawDialogOpen(true)}
            title="Xem raw response nguyên bản của trang"
          >
            <Code className="size-3.5" />
            <span className="hidden sm:inline">Raw JSON</span>
          </Button>
        </div>
      </div>

      {/* Bố cục Hai Cột Đối Chiếu (Desktop: lg:grid-cols-2 | Mobile: Tabs Bản gốc / Kết quả) */}
      <div className="hidden lg:grid lg:grid-cols-2 gap-4 items-start">
        {/* CỘT TRÁI: Bản gốc của trang đang chọn */}
        <Card className="rounded-xl shadow-2xs overflow-hidden flex flex-col h-[calc(100vh-14rem)] min-h-[580px] border-border/80">
          <div className="p-2.5 border-b bg-muted/20 flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5 font-medium text-foreground">
              <ImageIcon className="size-3.5 text-primary" />
              <span>Bản gốc trang {activePageNumber}</span>
            </div>

            {/* Điều khiển Phóng to / Thu nhỏ / Vừa chiều ngang / Mở rộng */}
            <div className="flex items-center gap-1">
              <Button
                variant={zoomMode === "fit-width" ? "secondary" : "ghost"}
                size="sm"
                className="h-6 px-2 text-[11px] font-medium"
                onClick={handleToggleFit}
                title={
                  zoomMode === "fit-width"
                    ? "Đang vừa bề ngang (nhấp để chuyển sang vừa trọn trang)"
                    : "Đang vừa trọn trang (nhấp để chuyển sang vừa bề ngang)"
                }
              >
                <span>
                  {zoomMode === "fit-width" ? "Vừa ngang" : "Trọn trang"}
                </span>
              </Button>

              <div className="h-3.5 w-px bg-border/60 mx-0.5" />

              <Button
                variant="ghost"
                size="sm"
                className="size-6 p-0 text-muted-foreground hover:text-foreground"
                onClick={handleZoomOut}
                title="Thu nhỏ"
              >
                <ZoomOut className="size-3.5" />
              </Button>
              <span className="text-[10px] font-mono min-w-8 text-center text-muted-foreground">
                {zoomMode === "custom"
                  ? `${customZoom}%`
                  : zoomMode === "fit-width"
                    ? "Ngang"
                    : "Trọn"}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="size-6 p-0 text-muted-foreground hover:text-foreground"
                onClick={handleZoomIn}
                title="Phóng to"
              >
                <ZoomIn className="size-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="size-6 p-0 text-muted-foreground hover:text-foreground"
                onClick={handleResetZoom}
                title="Đặt lại vừa chiều ngang"
              >
                <RotateCcw className="size-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="size-6 p-0 text-muted-foreground hover:text-foreground ml-1"
                onClick={() => setFullscreenImageOpen(true)}
                title="Mở rộng toàn màn hình"
              >
                <Maximize2 className="size-3.5" />
              </Button>
            </div>
          </div>

          <div className="flex-1 overflow-auto p-4 bg-muted/10 flex items-center justify-center relative">
            {imageLoading ? (
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
                  Hệ thống đang chuyển đổi tài liệu và kết xuất các trang. Ảnh
                  sẽ tự động hiển thị khi hoàn tất.
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
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs bg-card"
                    onClick={() => void refetchImage()}
                  >
                    <RotateCcw className="size-3 mr-1" />
                    <span>Thử tải lại</span>
                  </Button>
                </AlertDescription>
              </Alert>
            ) : imageBlobUrl ? (
              <div
                className={cn(
                  "w-full h-full flex transition-all duration-150",
                  zoomMode === "fit-page"
                    ? "items-center justify-center"
                    : "items-start justify-center",
                )}
              >
                <img
                  src={imageBlobUrl}
                  alt={`Bản gốc trang ${activePageNumber}`}
                  className={cn(
                    "shadow-sm rounded border bg-white select-none transition-all duration-150",
                    zoomMode === "fit-width" && "w-full max-w-full h-auto",
                    zoomMode === "fit-page" &&
                      "max-w-full max-h-full w-auto h-auto object-contain",
                    zoomMode === "custom" && "max-w-none h-auto",
                  )}
                  style={
                    zoomMode === "custom"
                      ? { width: `${customZoom}%` }
                      : undefined
                  }
                />
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">
                {activePageInfo?.status === "in_flight" ||
                activePageInfo?.status === "pending"
                  ? "Trang đang chờ kết xuất..."
                  : "Chưa có ảnh cho trang này."}
              </div>
            )}
          </div>

          {/* DOCX Note */}
          {isDocx ? (
            <div className="p-2 border-t bg-muted/20 text-[11px] text-muted-foreground flex items-center gap-1.5">
              <Info className="size-3.5 text-info shrink-0" />
              <span>
                Ảnh trang là bản hiển thị được chuyển đổi từ Word (.docx) qua
                Gotenberg (LibreOffice) sang PDF chuẩn xác.
              </span>
            </div>
          ) : null}
        </Card>

        {/* CỘT PHẢI: Kết quả bóc tách đúng trang (Nội dung / Markdown / JSON) */}
        <Card className="rounded-xl shadow-2xs overflow-hidden flex flex-col h-[calc(100vh-14rem)] min-h-[580px] border-border/80">
          <Tabs
            value={activeTabDesktop}
            onValueChange={setActiveTabDesktop}
            className="flex-1 flex flex-col h-full"
          >
            {/* Header Tabs: Nội dung | Markdown | JSON */}
            <div className="p-2 border-b bg-muted/20 flex items-center justify-between">
              <TabsList className="h-8">
                <TabsTrigger value="content" className="text-xs gap-1.5 h-7">
                  <FileText className="size-3 text-primary" />
                  <span>Nội dung</span>
                </TabsTrigger>
                <TabsTrigger value="markdown" className="text-xs gap-1.5 h-7">
                  <FileText className="size-3 text-primary" />
                  <span>Markdown</span>
                </TabsTrigger>
                <TabsTrigger value="json" className="text-xs gap-1.5 h-7">
                  <Code className="size-3 text-primary" />
                  <span>JSON</span>
                </TabsTrigger>
              </TabsList>

              {/* Actions on active view */}
              <div className="flex items-center gap-1.5 text-xs">
                {activeTabDesktop === "markdown" ? (
                  <Button
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

                {activeTabDesktop === "json" ? (
                  <Button
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
                      {copiedType === "json" ? "Đã chép" : "Sao chép JSON"}
                    </span>
                  </Button>
                ) : null}
              </div>
            </div>

            {/* TAB 1: NỘI DUNG TUẦN TỰ (Mặt giấy văn bản liền mạch) */}
            <TabsContent
              value="content"
              className="flex-1 overflow-auto p-4 sm:p-5 m-0 bg-muted/15"
            >
              {sequentialBlocks.length === 0 ? (
                <div className="p-8 text-center text-xs text-muted-foreground space-y-1">
                  {activePageInfo?.status === "blank" ? (
                    <p>
                      Trang này được xác định là trang trắng (không chứa mực
                      in).
                    </p>
                  ) : activePageInfo?.status === "in_flight" ||
                    activePageInfo?.status === "pending" ? (
                    <div className="flex flex-col items-center gap-2 py-4">
                      <Loader2 className="size-5 animate-spin text-primary" />
                      <p>Trang đang trong quá trình bóc tách…</p>
                    </div>
                  ) : (
                    <p>Chưa có nội dung nào được trích xuất cho trang này.</p>
                  )}
                </div>
              ) : (
                <div className="mx-auto max-w-2xl bg-card border border-border/60 rounded-xl p-5 sm:p-7 shadow-2xs space-y-2.5 font-sans min-h-full">
                  {sequentialBlocks.map((block) => {
                    if (block.type === "prose") {
                      return (
                        <div
                          key={block.unit.evidence_id}
                          className={cn(
                            "group relative py-1 px-2.5 -mx-2.5 rounded-md transition-colors",
                            block.isEdited
                              ? "bg-amber-500/10 border-l-2 border-amber-500 pl-3"
                              : "hover:bg-muted/50",
                          )}
                        >
                          {/* Nút Sửa nổi nhẹ nhàng khi di chuột qua đoạn */}
                          <div className="absolute right-2 top-1 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1.5 bg-background/95 backdrop-blur-xs px-1.5 py-0.5 rounded-md border border-border/80 shadow-2xs z-10">
                            {block.isEdited ? (
                              <span className="text-[9px] text-amber-600 dark:text-amber-400 font-medium pl-1">
                                Đã sửa
                              </span>
                            ) : null}
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-5 px-1.5 text-[11px] gap-1 text-primary hover:text-primary hover:bg-primary/10"
                              onClick={() =>
                                handleStartEdit(block.unit, block.currentText)
                              }
                              title="Chỉnh sửa đoạn này"
                            >
                              <Edit3 className="size-3" />
                              <span>Sửa</span>
                            </Button>
                          </div>

                          {/* Hiển thị phân cấp theo loại đoạn văn */}
                          {block.unit.kind === "heading" ? (
                            <h3 className="text-sm sm:text-base font-bold text-foreground leading-snug">
                              {block.currentText}
                            </h3>
                          ) : (
                            <p className="text-xs sm:text-sm text-foreground/90 leading-relaxed font-sans whitespace-pre-wrap">
                              {block.currentText}
                            </p>
                          )}
                        </div>
                      );
                    }

                    if (block.type === "table") {
                      return (
                        <div
                          key={block.blockId}
                          className="my-3 rounded-lg border border-border/70 bg-card overflow-hidden shadow-2xs"
                        >
                          <div className="px-3 py-1.5 bg-muted/30 border-b border-border/60 flex items-center justify-between text-xs">
                            <div className="flex items-center gap-1.5 font-medium text-foreground">
                              <FileSpreadsheet className="size-3.5 text-primary" />
                              <span>
                                Bảng số liệu ({block.rows.length} hàng)
                              </span>
                            </div>
                          </div>

                          <div className="overflow-x-auto">
                            <Table className="text-xs">
                              <TableHeader>
                                <TableRow>
                                  {block.rows[0]?.cells.map(
                                    ({ unit, currentText }) => (
                                      <TableHead
                                        key={unit.evidence_id}
                                        className="font-semibold text-foreground text-xs whitespace-nowrap bg-muted/20 py-2 px-3"
                                      >
                                        {currentText || "—"}
                                      </TableHead>
                                    ),
                                  )}
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {block.rows.slice(1).map((row) => (
                                  <TableRow key={row.rowIdx}>
                                    {row.cells.map(
                                      ({ unit, currentText, isEdited }) => (
                                        <TableCell
                                          key={unit.evidence_id}
                                          className={cn(
                                            "text-xs py-2 px-3 leading-normal cursor-pointer hover:bg-muted/40 transition-colors",
                                            isEdited
                                              ? "bg-amber-500/10 font-medium"
                                              : "",
                                          )}
                                          onClick={() =>
                                            handleStartEdit(unit, currentText)
                                          }
                                          title="Nhấp để sửa ô này"
                                        >
                                          {currentText === "" ? (
                                            <span className="text-muted-foreground/60 italic">
                                              (trống)
                                            </span>
                                          ) : (
                                            currentText
                                          )}
                                        </TableCell>
                                      ),
                                    )}
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </div>
                        </div>
                      );
                    }

                    if (block.type === "image") {
                      return (
                        <div
                          key={block.blockId}
                          className="my-3 p-3 rounded-lg border border-border/70 bg-muted/10 flex flex-col items-center gap-2"
                        >
                          <div className="flex items-center gap-1.5 text-xs text-muted-foreground self-start">
                            <ImageIcon className="size-3.5 text-primary" />
                            <span>Ảnh trích xuất #{block.assetNo}</span>
                          </div>

                          <div className="flex justify-center p-2 bg-background rounded border">
                            <AuthenticatedEmbeddedImage
                              workspaceId={workspaceId}
                              collectionId={collectionId}
                              sourceId={sourceId}
                              revisionId={revisionId}
                              runId={run.id}
                              assetNo={block.assetNo}
                            />
                          </div>
                        </div>
                      );
                    }

                    return null;
                  })}
                </div>
              )}
            </TabsContent>

            {/* TAB 2: MARKDOWN DẪN XUẤT */}
            <TabsContent
              value="markdown"
              className="flex-1 overflow-auto p-4 m-0 font-mono text-xs whitespace-pre-wrap bg-muted/10 text-foreground leading-relaxed"
            >
              {pageMarkdown || "Chưa có nội dung Markdown cho trang này."}
            </TabsContent>

            {/* TAB 3: JSON CẤU TRÚC */}
            <TabsContent
              value="json"
              className="flex-1 overflow-auto p-4 m-0 font-mono text-[11px] whitespace-pre-wrap bg-muted/10 text-foreground"
            >
              {pageJson}
            </TabsContent>
          </Tabs>
        </Card>
      </div>

      {/* Mobile view: Chuyển đổi linh hoạt giữa Bản gốc / Kết quả thay vì ép 2 cột */}
      <div className="lg:hidden">
        <Tabs
          value={activeTabMobile}
          onValueChange={setActiveTabMobile}
          className="w-full space-y-3"
        >
          <TabsList className="grid grid-cols-2 w-full h-9">
            <TabsTrigger value="content" className="text-xs">
              Nội dung
            </TabsTrigger>
            <TabsTrigger value="image" className="text-xs">
              Bản gốc trang {activePageNumber}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="content" className="mt-0">
            <div className="bg-card border border-border/60 rounded-xl p-4 shadow-2xs space-y-2 font-sans">
              {sequentialBlocks.map((block) => {
                if (block.type === "prose") {
                  return (
                    <div
                      key={block.unit.evidence_id}
                      className={cn(
                        "relative py-1 px-2 rounded-md",
                        block.isEdited
                          ? "bg-amber-500/10 border-l-2 border-amber-500 pl-2.5"
                          : "",
                      )}
                    >
                      <div className="flex items-center justify-end text-[10px] text-muted-foreground mb-0.5">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-5 px-1.5 text-[11px] text-primary"
                          onClick={() =>
                            handleStartEdit(block.unit, block.currentText)
                          }
                        >
                          <Edit3 className="size-3 mr-1" />
                          <span>Sửa</span>
                        </Button>
                      </div>
                      <p className="text-xs text-foreground/90 leading-relaxed whitespace-pre-wrap">
                        {block.currentText}
                      </p>
                    </div>
                  );
                }
                return null;
              })}
            </div>
          </TabsContent>

          <TabsContent value="image" className="mt-0">
            <Card className="p-2 overflow-auto flex items-center justify-center">
              {imageLoading ? (
                <Loader2 className="size-6 animate-spin text-primary py-8" />
              ) : imageBlobUrl ? (
                <img
                  src={imageBlobUrl}
                  alt={`Trang ${activePageNumber}`}
                  className="max-w-full h-auto rounded border"
                />
              ) : null}
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Modal Chỉnh sửa một khối văn bản */}
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
              <span>Chỉnh sửa khối văn bản</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Thay đổi sẽ được lưu vào bản nháp. Bấm &ldquo;Lưu thay đổi&rdquo;
              ở thanh công cụ chính để xác nhận ghi bản hiệu đính mới.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <div className="space-y-1">
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
                className="text-xs font-sans leading-relaxed"
              />
            </div>

            {editingUnit?.original_text && (
              <div className="p-2 rounded bg-muted/30 border text-[11px] text-muted-foreground space-y-1">
                <span className="font-semibold block">
                  Văn bản OCR ban đầu:
                </span>
                <p className="font-mono text-muted-foreground/80">
                  {editingUnit.original_text}
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setEditingUnit(null)}
            >
              Hủy
            </Button>
            <Button type="button" size="sm" onClick={handleSaveEdit}>
              Lưu vào nháp
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Mở rộng Toàn màn hình ảnh Bản gốc */}
      <Dialog open={fullscreenImageOpen} onOpenChange={setFullscreenImageOpen}>
        <DialogContent className="max-w-5xl max-h-[92vh] flex flex-col p-2">
          <DialogHeader className="p-2 pb-0">
            <DialogTitle className="text-sm font-semibold flex items-center gap-2">
              <ImageIcon className="size-4 text-primary" />
              <span>Bản gốc trang {activePageNumber} (Phóng to)</span>
            </DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-auto p-2 flex items-center justify-center">
            {imageBlobUrl ? (
              <img
                src={imageBlobUrl}
                alt={`Trang ${activePageNumber} phóng to`}
                className="max-w-full h-auto rounded border shadow-lg"
              />
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
              <span>Raw OCR Response (Trang {activePageNumber})</span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Dữ liệu JSON nguyên bản do provider trả về cho trang này.
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-auto p-3 bg-muted/20 rounded-lg border font-mono text-[11px] whitespace-pre-wrap break-all">
            {rawLoading ? (
              <div className="p-8 flex items-center justify-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="size-4 animate-spin text-primary" />
                <span>Đang tải raw response...</span>
              </div>
            ) : rawError ? (
              <p className="text-destructive">{rawError}</p>
            ) : rawText ? (
              rawText
            ) : (
              <p className="text-muted-foreground">
                Không có dữ liệu raw response.
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
