import {
  Edit3,
  FileSpreadsheet,
  ImageIcon,
  Loader2,
  RotateCcw,
  ScanSearch,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AuthenticatedEmbeddedImage } from "@/features/knowledge/embedded-image";
import { OcrWordDiffView } from "@/features/knowledge/ocr-review-dialogs";
import {
  extractNormalizedBbox,
  formatUnitLocator,
} from "@/features/knowledge/ocr-schemas";
import type {
  PageStatusResponse,
  ReviewDocument,
  TextUnit,
} from "@/features/knowledge/ocr-types";
import { cn } from "@/lib/utils";

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

export interface DocumentSheetCanvasProps {
  sequentialBlocks: SequentialBlock[];
  activePageNumber?: number;
  isWordDocument?: boolean;
  activePageInfo?: PageStatusResponse | null;
  reviewDoc?: ReviewDocument | null;
  canManage: boolean;
  canCompareOcr: boolean;
  focusedEvidenceId?: string | null;
  selectedUnitIds?: ReadonlySet<string> | Set<string>;
  onToggleUnitSelection?: (evidenceId: string) => void;
  onFocusUnit?: (evidenceId: string | null) => void;
  onStartEdit: (unit: TextUnit, currentText: string) => void;
  onRevertUnitDraft?: (evidenceId: string) => void;
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  revisionId: string;
  runId?: string;
}

export function DocumentSheetCanvas({
  sequentialBlocks,
  activePageNumber = 1,
  activePageInfo,
  reviewDoc,
  canManage,
  canCompareOcr,
  focusedEvidenceId,
  selectedUnitIds,
  onToggleUnitSelection,
  onFocusUnit,
  onStartEdit,
  onRevertUnitDraft,
  workspaceId,
  collectionId,
  sourceId,
  revisionId,
  runId,
}: DocumentSheetCanvasProps) {
  if (sequentialBlocks.length === 0) {
    return (
      <div className="p-8 text-center text-xs text-muted-foreground space-y-1 bg-muted/15 rounded-xl border border-dashed">
        {activePageInfo?.status === "blank" ? (
          <p className="text-sm font-medium text-foreground">
            Trang {activePageNumber} không có chữ (Trang trắng).
          </p>
        ) : activePageInfo?.status === "in_flight" ||
          activePageInfo?.status === "pending" ? (
          <div className="flex flex-col items-center gap-2 py-4">
            <Loader2 className="size-5 animate-spin text-primary" />
            <p>Trang {activePageNumber} đang trong quá trình bóc tách…</p>
          </div>
        ) : (
          <p>Chưa có nội dung văn bản nào cho trang {activePageNumber}.</p>
        )}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-3 sm:px-6 py-5 bg-card border border-border/80 rounded-xl shadow-2xs space-y-3 font-sans">
      {sequentialBlocks.map((block) => {
        if (block.type === "prose") {
          const isFocused = focusedEvidenceId === block.unit.evidence_id;
          const isSelected = Boolean(
            selectedUnitIds?.has(block.unit.evidence_id),
          );
          const locator = formatUnitLocator(block.unit, reviewDoc?.units, {
            includePage: false,
          });
          const hasBbox = Boolean(extractNormalizedBbox(block.unit.bbox));

          return (
            <div
              key={block.unit.evidence_id}
              data-evidence-id={block.unit.evidence_id}
              className={cn(
                "group relative py-1.5 pl-7 pr-2.5 sm:pl-2.5 -mx-1.5 rounded-lg transition-all",
                isFocused
                  ? "ring-2 ring-primary bg-primary/5 border border-primary/30"
                  : block.hasUnsavedDraft
                    ? "bg-amber-500/10 border-l-2 border-l-amber-500 pl-3"
                    : block.wasSavedPreviously
                      ? "bg-muted/30 border-l-2 border-l-primary/50 pl-3"
                      : "hover:bg-muted/40",
              )}
            >
              {/* Keep actions visible and in flow for touch and keyboard access. */}
              <div className="flex flex-wrap items-center justify-end gap-1 mb-1">
                {/* Locator pill */}
                <button
                  type="button"
                  className="text-[10px] font-mono text-muted-foreground bg-background/90 backdrop-blur-xs px-1.5 py-0.5 rounded border border-border/60 hover:text-primary transition-colors flex items-center gap-1 cursor-pointer"
                  onClick={() =>
                    onFocusUnit?.(isFocused ? null : block.unit.evidence_id)
                  }
                  title={
                    canCompareOcr && hasBbox
                      ? "Nhấp để đánh dấu vị trí đoạn này trên ảnh gốc"
                      : "Chọn đoạn văn bản này"
                  }
                >
                  <span>{locator}</span>
                  {canCompareOcr && hasBbox ? (
                    <ScanSearch className="size-2.5 text-primary/70" />
                  ) : null}
                </button>

                {block.hasUnsavedDraft ? (
                  <Badge
                    variant="warning"
                    className="text-[10px] py-0 px-1.5 h-5"
                  >
                    Nháp
                  </Badge>
                ) : block.wasSavedPreviously ? (
                  <Badge
                    variant="secondary"
                    className="text-[10px] py-0 px-1.5 h-5 hidden sm:inline-flex"
                  >
                    Đã sửa
                  </Badge>
                ) : null}

                {canManage ? (
                  <div className="flex items-center gap-0.5 bg-background/90 backdrop-blur-xs rounded border border-border/60 p-0.5 shadow-2xs">
                    {block.hasUnsavedDraft && onRevertUnitDraft ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="h-5 px-1 text-[11px] text-muted-foreground hover:text-destructive"
                        onClick={() =>
                          onRevertUnitDraft(block.unit.evidence_id)
                        }
                        title="Khôi phục đoạn này về bản đã lưu"
                      >
                        <RotateCcw className="size-2.5 mr-0.5" />
                        <span>Hủy</span>
                      </Button>
                    ) : null}
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      className="h-5 px-1.5 text-[11px] text-primary hover:text-primary hover:bg-primary/10 gap-1 font-medium"
                      onClick={() => onStartEdit(block.unit, block.currentText)}
                      aria-label={`Sửa ${locator}`}
                    >
                      <Edit3 className="size-2.5" />
                      <span>Sửa</span>
                    </Button>
                  </div>
                ) : null}
              </div>

              {/* Keep the checkbox within the canvas gutter on narrow screens. */}
              {canManage &&
              onToggleUnitSelection &&
              block.currentText.trim().length > 0 ? (
                <div className="absolute left-1 sm:-left-4 top-2">
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() =>
                      onToggleUnitSelection(block.unit.evidence_id)
                    }
                    aria-label={`Chọn ${locator} để kiểm tra chính tả`}
                  />
                </div>
              ) : null}

              {/* Clean continuous typography */}
              {block.unit.kind === "heading" ? (
                <h3 className="text-sm sm:text-base font-bold text-foreground leading-snug whitespace-pre-wrap">
                  {block.currentText}
                </h3>
              ) : (
                <p className="text-sm text-foreground leading-relaxed font-sans whitespace-pre-wrap">
                  {block.currentText}
                </p>
              )}

              {/* Word diff comparison if draft exists */}
              {block.hasUnsavedDraft ? (
                <div className="mt-2 pt-1.5 border-t border-amber-500/30 space-y-1">
                  <span className="text-[10px] font-medium text-muted-foreground block">
                    Khác biệt so với bản đã lưu:
                  </span>
                  <OcrWordDiffView
                    before={block.unit.text}
                    after={block.currentText}
                    className="text-xs bg-background/80 rounded-md p-2 border border-border/50"
                  />
                </div>
              ) : null}
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
                  <span>Bảng dữ liệu ({block.rows.length} hàng)</span>
                </div>
                {canManage ? (
                  <span className="text-[11px] text-muted-foreground">
                    Nhấp vào ô để chỉnh sửa
                  </span>
                ) : null}
              </div>

              <div className="overflow-x-auto">
                <Table className="text-xs">
                  <TableHeader>
                    <TableRow>
                      {block.rows[0]?.cells.map(
                        ({ unit, currentText, hasUnsavedDraft }) => {
                          const isFocused =
                            focusedEvidenceId === unit.evidence_id;
                          return (
                            <TableHead
                              key={unit.evidence_id}
                              data-evidence-id={unit.evidence_id}
                              className={cn(
                                "font-semibold text-foreground text-xs bg-muted/20 py-2 px-3 transition-colors",
                                canManage && "cursor-pointer hover:bg-muted/40",
                                hasUnsavedDraft && "bg-amber-500/15",
                                isFocused &&
                                  "ring-2 ring-inset ring-primary bg-primary/10",
                              )}
                              onClick={() => {
                                onFocusUnit?.(unit.evidence_id);
                                if (canManage) {
                                  onStartEdit(unit, currentText);
                                }
                              }}
                              title={
                                canManage
                                  ? "Nhấp để đối chiếu và chỉnh sửa ô tiêu đề bảng"
                                  : "Nhấp để đối chiếu vị trí ô bảng"
                              }
                            >
                              {currentText || "—"}
                            </TableHead>
                          );
                        },
                      )}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {block.rows.slice(1).map((row) => (
                      <TableRow key={row.rowIdx}>
                        {row.cells.map(
                          ({
                            unit,
                            currentText,
                            hasUnsavedDraft,
                            wasSavedPreviously,
                          }) => {
                            const isFocused =
                              focusedEvidenceId === unit.evidence_id;
                            return (
                              <TableCell
                                key={unit.evidence_id}
                                data-evidence-id={unit.evidence_id}
                                className={cn(
                                  "text-xs py-2 px-3 leading-normal transition-colors",
                                  canManage &&
                                    "cursor-pointer hover:bg-muted/40",
                                  hasUnsavedDraft
                                    ? "bg-amber-500/15 font-medium"
                                    : wasSavedPreviously
                                      ? "bg-muted/30"
                                      : "",
                                  isFocused &&
                                    "ring-2 ring-inset ring-primary bg-primary/10",
                                )}
                                onClick={() => {
                                  onFocusUnit?.(unit.evidence_id);
                                  if (canManage) {
                                    onStartEdit(unit, currentText);
                                  }
                                }}
                                title={
                                  canManage
                                    ? `Hàng ${(unit.row ?? 0) + 1}, Cột ${(unit.column ?? 0) + 1} — Nhấp để chỉnh sửa`
                                    : `Hàng ${(unit.row ?? 0) + 1}, Cột ${(unit.column ?? 0) + 1}`
                                }
                              >
                                {currentText === "" ? (
                                  <span className="text-muted-foreground/60 italic">
                                    (trống)
                                  </span>
                                ) : (
                                  currentText
                                )}
                              </TableCell>
                            );
                          },
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
                  runId={runId ?? ""}
                  assetNo={block.assetNo}
                />
              </div>
            </div>
          );
        }

        return null;
      })}
    </div>
  );
}
