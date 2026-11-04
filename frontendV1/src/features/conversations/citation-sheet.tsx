import { Link } from "@tanstack/react-router";
import {
  BookOpen,
  CheckCircle2,
  ExternalLink,
  FileText,
  Hash,
  Layers,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import type { EvidenceSource, Statement } from "./types";

export function CitationSheet({
  open,
  onOpenChange,
  statement,
  sources,
  turnNo,
  workspaceId,
  collectionId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  statement?: Statement | null;
  sources: EvidenceSource[];
  turnNo?: number;
  workspaceId?: string;
  collectionId?: string;
}) {
  // Map evidence sources specifically bound to this statement
  const relevantSources = statement
    ? sources.filter((s) => statement.evidence_ids.includes(s.evidence_id))
    : sources;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-xl md:max-w-2xl p-0 flex flex-col h-full bg-background border-l"
      >
        <SheetHeader className="border-b bg-muted/20 px-6 py-4 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <BookOpen className="size-4" />
            </div>
            <div>
              <SheetTitle className="text-base font-semibold">
                Dẫn nguồn bằng chứng {turnNo ? `(Lượt #${turnNo})` : ""}
              </SheetTitle>
              <SheetDescription className="text-xs text-muted-foreground mt-0.5">
                Các trích đoạn từ tài liệu dùng để đối chiếu nội dung và phần
                còn cần làm rõ.
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto min-h-0 p-6 space-y-6">
          {/* Statement text quote */}
          {statement && (
            <div className="rounded-lg border bg-muted/30 p-4 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-primary">
                <Sparkles className="size-3.5" />
                <span>Nội dung đang đối chiếu</span>
              </div>
              <p className="text-sm font-medium text-foreground leading-relaxed">
                "{statement.text}"
              </p>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {statement.evidence_ids.map((id) => (
                  <Badge
                    key={id}
                    variant="secondary"
                    className="font-mono text-[10px]"
                  >
                    {id}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Sources list */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Tài liệu dẫn nguồn ({relevantSources.length})
              </h3>
            </div>

            {relevantSources.length === 0 ? (
              <div className="rounded-lg border border-dashed p-6 text-center text-xs text-muted-foreground">
                Không tìm thấy bằng chứng liên quan cho mệnh đề này.
              </div>
            ) : (
              relevantSources.map((source) => {
                const citations = source.citations || {};
                const pageNum = citations.page ?? citations.page_number;
                const tableNum = citations.table ?? citations.table_index;
                const section = citations.section ?? citations.heading;
                const rawSourceId =
                  typeof citations.source_id === "string"
                    ? citations.source_id
                    : undefined;
                const rawRevisionId =
                  typeof citations.revision_id === "string"
                    ? citations.revision_id
                    : undefined;
                const rawRunId =
                  typeof citations.run_id === "string"
                    ? citations.run_id
                    : undefined;
                const parsedPage =
                  typeof pageNum === "number"
                    ? pageNum
                    : typeof pageNum === "string" && /^\d+$/.test(pageNum)
                      ? Number(pageNum)
                      : undefined;

                return (
                  <div
                    key={`${source.evidence_id}_${source.chunk_id}`}
                    className="rounded-lg border bg-card p-4 space-y-3.5 shadow-2xs"
                  >
                    {/* Header info */}
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-2.5">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className="font-mono text-xs font-semibold bg-muted/40"
                        >
                          {source.evidence_id}
                        </Badge>
                        <Badge
                          variant="secondary"
                          className="text-[11px] capitalize"
                        >
                          {source.kind || "Văn bản"}
                        </Badge>
                      </div>

                      {typeof source.score === "number" && (
                        <div className="text-[11px] font-mono text-muted-foreground flex items-center gap-1">
                          <span>Độ khớp:</span>
                          <span className="font-semibold text-foreground">
                            {(source.score * 100).toFixed(1)}%
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Metadata Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-[11px]">
                      <div className="space-y-0.5">
                        <span className="text-muted-foreground flex items-center gap-1">
                          <FileText className="size-3" /> Mã tài liệu:
                        </span>
                        <p
                          className="font-mono font-medium text-foreground truncate"
                          title={source.document_id}
                        >
                          {source.document_id || "Không có thông tin"}
                        </p>
                      </div>

                      <div className="space-y-0.5">
                        <span className="text-muted-foreground flex items-center gap-1">
                          <Layers className="size-3" /> Phiên bản:
                        </span>
                        <p
                          className="font-mono font-medium text-foreground truncate"
                          title={source.version_id}
                        >
                          {source.version_id || "Không có thông tin"}
                        </p>
                      </div>

                      <div className="space-y-0.5">
                        <span className="text-muted-foreground flex items-center gap-1">
                          <Hash className="size-3" /> Vị trí trang:
                        </span>
                        <p className="font-medium text-foreground">
                          {pageNum !== undefined && pageNum !== null
                            ? `Trang ${String(pageNum)}`
                            : "Không có thông tin"}
                        </p>
                      </div>

                      {tableNum !== undefined && tableNum !== null && (
                        <div className="space-y-0.5">
                          <span className="text-muted-foreground">
                            Bảng biểu:
                          </span>
                          <p className="font-medium text-foreground">
                            Bảng #{String(tableNum)}
                          </p>
                        </div>
                      )}

                      {Boolean(section) && (
                        <div className="space-y-0.5 col-span-2">
                          <span className="text-muted-foreground">
                            Mục/Tiêu đề:
                          </span>
                          <p className="font-medium text-foreground line-clamp-1">
                            {String(section)}
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Content text */}
                    <div className="space-y-1.5 pt-1">
                      <span className="text-xs font-medium text-muted-foreground">
                        Nội dung trích đoạn:
                      </span>
                      <div className="rounded-md bg-muted/40 p-3 text-xs font-mono leading-relaxed text-foreground whitespace-pre-wrap max-h-60 overflow-y-auto border">
                        {source.text || "(Trích đoạn trống)"}
                      </div>
                    </div>

                    {/* Liên kết mở về đúng tài liệu/phiên bản/trang */}
                    {workspaceId &&
                    collectionId &&
                    (rawSourceId || source.document_id) ? (
                      <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border/60">
                        {rawSourceId ? (
                          <Button
                            asChild
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs gap-1.5"
                            onClick={() => onOpenChange(false)}
                          >
                            <Link
                              to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
                              params={{
                                workspaceId,
                                collectionId,
                                sourceId: rawSourceId,
                              }}
                              search={{
                                revisionId: rawRevisionId,
                                runId: rawRunId,
                                page: parsedPage ?? 1,
                              }}
                            >
                              <FileText className="size-3 text-primary" />
                              <span>
                                Mở tài liệu nguồn
                                {parsedPage ? ` (Trang ${parsedPage})` : ""}
                              </span>
                              <ExternalLink className="size-3" />
                            </Link>
                          </Button>
                        ) : null}
                        {source.document_id && source.version_id ? (
                          <Button
                            asChild
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs gap-1.5"
                            onClick={() => onOpenChange(false)}
                          >
                            <Link
                              to="/workspaces/$workspaceId/collections/$collectionId/documents/$documentId/versions/$versionId"
                              params={{
                                workspaceId,
                                collectionId,
                                documentId: source.document_id,
                                versionId: source.version_id,
                              }}
                            >
                              <Layers className="size-3 text-primary" />
                              <span>Mở bản phát hành đã trích dẫn</span>
                              <ExternalLink className="size-3" />
                            </Link>
                          </Button>
                        ) : source.document_id ? (
                          <Button
                            asChild
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs gap-1.5"
                            onClick={() => onOpenChange(false)}
                          >
                            <Link
                              to="/workspaces/$workspaceId/collections/$collectionId/documents/$documentId"
                              params={{
                                workspaceId,
                                collectionId,
                                documentId: source.document_id,
                              }}
                            >
                              <Layers className="size-3 text-primary" />
                              <span>Mở tài liệu phát hành</span>
                              <ExternalLink className="size-3" />
                            </Link>
                          </Button>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="border-t bg-muted/10 px-6 py-3 shrink-0 flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5 text-success">
            <CheckCircle2 className="size-3.5" />
            <span className="text-[11px]">
              Bằng chứng đã qua kiểm tra xuất bản
            </span>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
