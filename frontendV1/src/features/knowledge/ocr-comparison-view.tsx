import {
  AlertCircle,
  Code,
  FileSpreadsheet,
  FileText,
  ImageIcon,
  Info,
  Loader2,
  Maximize2,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
}) {
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [rawDialogOpen, setRawDialogOpen] = useState<boolean>(false);
  const [activeTabMobile, setActiveTabMobile] = useState<string>("content");

  // Load page image blob
  const {
    blobUrl: imageBlobUrl,
    isLoading: imageLoading,
    error: imageError,
  } = usePageImageBlobUrl(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    run.id,
    activePageNumber,
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

  // Group table cells if any
  const { tableUnits, proseUnits } = useMemo(() => {
    const table: TextUnit[] = [];
    const prose: TextUnit[] = [];
    for (const u of pageUnits) {
      if (u.kind === "table_cell" || u.row !== null || u.column !== null) {
        table.push(u);
      } else {
        prose.push(u);
      }
    }
    return { tableUnits: table, proseUnits: prose };
  }, [pageUnits]);

  // Construct structured table rows if table units exist
  const tableRows = useMemo(() => {
    if (tableUnits.length === 0) return [];
    const rowsMap = new Map<number, TextUnit[]>();
    for (const u of tableUnits) {
      const rowIdx = u.row ?? 0;
      const list = rowsMap.get(rowIdx) ?? [];
      list.push(u);
      rowsMap.set(rowIdx, list);
    }
    const sortedRowIndices = Array.from(rowsMap.keys()).sort((a, b) => a - b);
    return sortedRowIndices.map((rowIdx) => {
      const cells = rowsMap.get(rowIdx) ?? [];
      return cells.sort((a, b) => (a.column ?? 0) - (b.column ?? 0));
    });
  }, [tableUnits]);

  const activePageInfo = pages.find((p) => p.page_number === activePageNumber);
  const totalPages = run.pages_total ?? pages.length;

  return (
    <div className="space-y-4">
      {/* Page Header & Navigation Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg border bg-card text-xs">
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
              className="text-[10px] py-0"
            >
              {activePageInfo.status === "blank"
                ? "Trang trắng"
                : activePageInfo.status === "completed"
                  ? "Đã OCR"
                  : activePageInfo.status}
            </Badge>
          ) : null}
          {activePageInfo?.has_tables ? (
            <Badge variant="outline" className="text-[10px] py-0 gap-1">
              <FileSpreadsheet className="size-3 text-primary" />
              <span>Có bảng</span>
            </Badge>
          ) : null}
        </div>

        {/* Page selector buttons */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs"
            disabled={activePageNumber <= 1}
            onClick={() => onPageChange(activePageNumber - 1)}
          >
            Trang trước
          </Button>

          <div className="flex items-center gap-1 max-w-[200px] overflow-x-auto py-1">
            {pages.map((p) => {
              const isActive = p.page_number === activePageNumber;
              return (
                <Button
                  key={p.page_number}
                  size="sm"
                  variant={isActive ? "default" : "ghost"}
                  className="h-7 w-7 p-0 text-xs font-mono shrink-0"
                  onClick={() => onPageChange(p.page_number)}
                  title={`Trang ${p.page_number} (${p.status})`}
                >
                  {p.page_number}
                </Button>
              );
            })}
          </div>

          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs"
            disabled={totalPages > 0 && activePageNumber >= totalPages}
            onClick={() => onPageChange(activePageNumber + 1)}
          >
            Trang sau
          </Button>

          {/* Raw Response trigger */}
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs gap-1 ml-2 text-muted-foreground hover:text-foreground"
            onClick={() => setRawDialogOpen(true)}
            title="Xem raw response nguyên bản của trang này"
          >
            <Code className="size-3.5" />
            <span className="hidden sm:inline">Raw JSON</span>
          </Button>
        </div>
      </div>

      {/* Side-by-side comparison (Desktop) / Tabs (Mobile) */}
      <div className="hidden lg:grid lg:grid-cols-2 gap-4 items-start">
        {/* Left Column: Page Image */}
        <Card className="rounded-xl shadow-2xs overflow-hidden flex flex-col h-[750px]">
          <div className="p-2.5 border-b bg-muted/20 flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5 font-medium text-foreground">
              <ImageIcon className="size-3.5 text-primary" />
              <span>Ảnh render của lượt OCR (Trang {activePageNumber})</span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="size-6 p-0"
                onClick={() => setZoomLevel((z) => Math.max(0.6, z - 0.2))}
                title="Thu nhỏ"
              >
                <ZoomOut className="size-3.5" />
              </Button>
              <span className="text-[10px] font-mono w-8 text-center">
                {Math.round(zoomLevel * 100)}%
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="size-6 p-0"
                onClick={() => setZoomLevel((z) => Math.min(2.5, z + 0.2))}
                title="Phóng to"
              >
                <ZoomIn className="size-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="size-6 p-0"
                onClick={() => setZoomLevel(1)}
                title="Vừa vặn (100%)"
              >
                <Maximize2 className="size-3.5" />
              </Button>
            </div>
          </div>

          <div className="flex-1 overflow-auto p-4 bg-muted/10 flex items-center justify-center relative">
            {imageLoading ? (
              <div className="flex flex-col items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="size-6 animate-spin text-primary" />
                <span>Đang tải ảnh trang...</span>
              </div>
            ) : imageError ? (
              <Alert variant="destructive" className="max-w-md">
                <AlertCircle className="size-4" />
                <AlertTitle>Không tải được ảnh</AlertTitle>
                <AlertDescription className="text-xs mt-1">
                  {imageError}
                </AlertDescription>
              </Alert>
            ) : imageBlobUrl ? (
              <img
                src={imageBlobUrl}
                alt={`Trang ${activePageNumber} lượt OCR`}
                className="max-w-none transition-transform duration-100 shadow-md rounded border bg-white"
                style={{
                  transform: `scale(${zoomLevel})`,
                  transformOrigin: "center center",
                }}
              />
            ) : null}
          </div>

          {isDocx ? (
            <div className="p-2 border-t bg-muted/20 text-[11px] text-muted-foreground flex items-center gap-1.5">
              <Info className="size-3.5 text-info shrink-0" />
              <span>
                Ảnh render fixed-layout (docx-story) đã dùng để OCR. Có thể có
                chênh lệch nhỏ so với Word gốc.
              </span>
            </div>
          ) : null}
        </Card>

        {/* Right Column: Extracted Content (Text & Tables) */}
        <Card className="rounded-xl shadow-2xs overflow-hidden flex flex-col h-[750px]">
          <div className="p-2.5 border-b bg-muted/20 flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5 font-medium text-foreground">
              <FileText className="size-3.5 text-primary" />
              <span>
                Văn bản & Bảng đã trích xuất ({pageUnits.length} khối)
              </span>
            </div>
            <span className="text-[11px] text-muted-foreground font-mono">
              Bản dẫn xuất hiện hành
            </span>
          </div>

          <div className="flex-1 overflow-auto p-4 space-y-4">
            {pageUnits.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted-foreground">
                {activePageInfo?.status === "blank" ? (
                  <p>Trang này được xác định là trang trắng (không có mực).</p>
                ) : (
                  <p>
                    Chưa có nội dung văn bản nào được trích xuất cho trang này.
                  </p>
                )}
              </div>
            ) : (
              <>
                {/* Prose Paragraphs */}
                {proseUnits.length > 0 ? (
                  <div className="space-y-2.5">
                    {proseUnits.map((u) => {
                      const isEdited = u.text !== u.original_text;
                      return (
                        <div
                          key={u.evidence_id}
                          className="p-3 rounded-lg border bg-card text-xs space-y-1.5 hover:border-primary/40 transition-colors"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <Badge
                              variant="outline"
                              className="font-mono text-[10px] py-0 text-muted-foreground"
                            >
                              {u.kind} · {u.evidence_id.slice(0, 16)}...
                            </Badge>
                            {isEdited ? (
                              <Badge
                                variant="warning"
                                className="text-[9px] py-0"
                              >
                                Đã sửa
                              </Badge>
                            ) : null}
                          </div>
                          <p className="text-foreground leading-relaxed whitespace-pre-wrap font-sans">
                            {u.text}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                ) : null}

                {/* Structured Tables */}
                {tableRows.length > 0 ? (
                  <div className="space-y-2 pt-2 border-t">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                      <FileSpreadsheet className="size-3.5 text-primary" />
                      <span>Bảng dữ liệu trên trang</span>
                    </div>

                    <div className="rounded-lg border overflow-x-auto">
                      <Table className="text-xs">
                        <TableHeader>
                          <TableRow>
                            {tableRows[0]?.map((cell) => (
                              <TableHead
                                key={cell.evidence_id}
                                className="font-semibold text-foreground text-xs"
                              >
                                {cell.text || "—"}
                              </TableHead>
                            ))}
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {tableRows.slice(1).map((row, rIdx) => (
                            <TableRow
                              key={row[0]?.evidence_id ?? `row_${rIdx}`}
                            >
                              {row.map((cell) => (
                                <TableCell
                                  key={cell.evidence_id}
                                  className="text-xs py-2 leading-normal"
                                >
                                  {cell.text === "" ? (
                                    <span className="text-muted-foreground italic">
                                      (trống)
                                    </span>
                                  ) : (
                                    cell.text
                                  )}
                                </TableCell>
                              ))}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                ) : null}
              </>
            )}
          </div>
        </Card>
      </div>

      {/* Mobile Accordion / Tabs */}
      <div className="lg:hidden">
        <Tabs
          value={activeTabMobile}
          onValueChange={setActiveTabMobile}
          className="w-full"
        >
          <TabsList className="grid grid-cols-2 w-full h-9">
            <TabsTrigger value="content" className="text-xs">
              Văn bản ({pageUnits.length})
            </TabsTrigger>
            <TabsTrigger value="image" className="text-xs">
              Ảnh đối chiếu
            </TabsTrigger>
          </TabsList>

          <TabsContent value="content" className="mt-3">
            <Card className="p-4 space-y-3">
              {pageUnits.map((u) => (
                <div
                  key={u.evidence_id}
                  className="p-3 rounded-lg border text-xs space-y-1"
                >
                  <span className="font-mono text-[10px] text-muted-foreground block">
                    {u.kind} · {u.evidence_id.slice(0, 16)}...
                  </span>
                  <p className="whitespace-pre-wrap">{u.text}</p>
                </div>
              ))}
            </Card>
          </TabsContent>

          <TabsContent value="image" className="mt-3">
            <Card className="p-3 overflow-auto max-h-[500px] flex items-center justify-center">
              {imageLoading ? (
                <Loader2 className="size-6 animate-spin text-primary" />
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

      {/* Raw Response Modal */}
      <Dialog open={rawDialogOpen} onOpenChange={setRawDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold flex items-center gap-2">
              <Code className="size-4 text-primary" />
              Raw OCR Response (Trang {activePageNumber})
            </DialogTitle>
            <DialogDescription className="text-xs">
              Dữ liệu JSON nguyên bản do mô hình OCR trả về cho trang này.
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
              <p className="text-muted-foreground">Không có dữ liệu.</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
