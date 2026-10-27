import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  ExternalLink,
  Loader2,
  Send,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useDispatchProcessingRunMutation,
  useProcessingRunsQuery,
} from "@/features/knowledge/ocr-queries";
import {
  formatOcrError,
  formatRunStatus,
} from "@/features/knowledge/ocr-schemas";
import type { ProcessingRunResponse } from "@/features/knowledge/ocr-types";
import { formatDateTimeValue } from "@/lib/date-utils";

export function OcrRunsList({
  workspaceId,
  collectionId,
  sourceId,
  revisionId,
  selectedRunId,
  onSelectRun,
  canManage,
  page,
  onPageChange,
}: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  revisionId: string;
  selectedRunId: string | null;
  onSelectRun: (run: ProcessingRunResponse) => void;
  canManage: boolean;
  page: number;
  onPageChange: (newPage: number) => void;
}) {
  const pageSize = 10;
  const runsQuery = useProcessingRunsQuery(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    page,
    pageSize,
  );

  const dispatchMutation = useDispatchProcessingRunMutation(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
  );

  const handleDispatch = async (e: React.MouseEvent, runId: string) => {
    e.stopPropagation();
    try {
      await dispatchMutation.mutateAsync(runId);
      toast.success("Đã gửi lượt xử lý vào hàng đợi xử lý.");
    } catch (error: unknown) {
      if (error instanceof ApiProblemError) {
        toast.error(formatOcrError(error.code, error.message));
      } else {
        toast.error("Không thể dispatch lượt xử lý.");
      }
    }
  };

  if (runsQuery.isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (runsQuery.isError) {
    return (
      <Card className="rounded-xl border-destructive/20 bg-destructive/5 p-4 text-xs">
        <div className="flex items-center gap-2 text-destructive font-medium">
          <AlertCircle className="size-4" />
          <span>Không tải được danh sách lượt xử lý OCR.</span>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="mt-2 text-xs"
          onClick={() => void runsQuery.refetch()}
        >
          Thử lại
        </Button>
      </Card>
    );
  }

  const items = runsQuery.data?.items ?? [];
  const meta = runsQuery.data?.meta ?? {
    page: 1,
    page_size: pageSize,
    total: 0,
  };
  const totalPages = Math.max(1, Math.ceil(meta.total / meta.page_size));

  if (items.length === 0) {
    return (
      <Card className="rounded-xl border-dashed p-6 text-center text-xs text-muted-foreground">
        <Clock className="size-8 mx-auto mb-2 text-muted-foreground/50" />
        <p className="font-medium text-foreground">
          Chưa có lượt xử lý OCR nào cho phiên bản này.
        </p>
        <p className="mt-1">
          Nhấn nút &ldquo;Yêu cầu OCR&rdquo; ở trên để bắt đầu trích xuất nội
          dung văn bản và bảng từ tệp tài liệu.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <Card className="rounded-xl shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[12%]">Thế hệ</TableHead>
                <TableHead className="w-[16%]">Trạng thái</TableHead>
                <TableHead className="w-[18%]">Tiến độ trang</TableHead>
                <TableHead className="w-[14%]">Model / Provider</TableHead>
                <TableHead className="w-[12%]">Token</TableHead>
                <TableHead className="w-[16%]">Thời gian</TableHead>
                <TableHead className="w-[12%] text-right">Thao tác</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((run) => {
                const isSelected = selectedRunId === run.id;
                const statusInfo = formatRunStatus(run.status);
                const hasFailedPages = run.pages_failed > 0;

                return (
                  <TableRow
                    key={run.id}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? "bg-primary/5 font-medium border-l-2 border-l-primary"
                        : "hover:bg-muted/40"
                    }`}
                    onClick={() => onSelectRun(run)}
                  >
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        <Badge
                          variant={isSelected ? "default" : "outline"}
                          className="font-mono text-xs"
                        >
                          Gen #{run.generation}
                        </Badge>
                      </div>
                    </TableCell>

                    <TableCell>
                      <div className="flex flex-col gap-1 items-start">
                        <Badge
                          variant={statusInfo.variant}
                          className="text-[11px] py-0"
                        >
                          {statusInfo.label}
                        </Badge>
                        {run.dispatch_pending ? (
                          <span className="text-[10px] text-warning font-medium">
                            Chờ dispatch
                          </span>
                        ) : null}
                      </div>
                    </TableCell>

                    <TableCell>
                      <div className="text-xs space-y-0.5 font-mono">
                        <div>
                          {run.pages_total !== null ? (
                            <span>
                              {run.pages_done} / {run.pages_total} trang
                            </span>
                          ) : (
                            <span className="text-muted-foreground italic">
                              Chờ xác định tổng trang...
                            </span>
                          )}
                        </div>
                        {hasFailedPages ? (
                          <span className="text-[10px] text-destructive font-medium block">
                            {run.pages_failed} trang lỗi
                          </span>
                        ) : null}
                        {run.attempt_count > 1 ? (
                          <span className="text-[10px] text-muted-foreground block">
                            Lần thử: {run.attempt_count}/{run.max_attempts}
                          </span>
                        ) : null}
                      </div>
                    </TableCell>

                    <TableCell className="text-xs font-mono text-muted-foreground truncate max-w-[140px]">
                      {run.provider_id || "Mặc định"}
                    </TableCell>

                    <TableCell className="text-xs font-mono text-muted-foreground">
                      {run.usage_tokens !== null ? (
                        <div className="flex items-center gap-1">
                          <Zap className="size-3 text-warning shrink-0" />
                          <span>{run.usage_tokens.toLocaleString()}</span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground/60 italic text-[11px]">
                          Chưa ghi nhận
                        </span>
                      )}
                    </TableCell>

                    <TableCell className="text-xs text-muted-foreground">
                      <div>{formatDateTimeValue(run.requested_at)}</div>
                      {run.finished_at ? (
                        <div className="text-[10px] text-muted-foreground/70">
                          Xong: {formatDateTimeValue(run.finished_at)}
                        </div>
                      ) : null}
                    </TableCell>

                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {run.dispatch_pending && canManage ? (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 px-2 text-xs gap-1 border-warning/40 text-warning hover:bg-warning/10"
                            disabled={dispatchMutation.isPending}
                            onClick={(e) => handleDispatch(e, run.id)}
                            title="Gửi lượt này vào hàng đợi xử lý"
                          >
                            {dispatchMutation.isPending ? (
                              <Loader2 className="size-3 animate-spin" />
                            ) : (
                              <Send className="size-3" />
                            )}
                            <span className="hidden sm:inline">Dispatch</span>
                          </Button>
                        ) : null}

                        {run.status === "completed" && canManage && (
                          <Button
                            asChild
                            size="sm"
                            variant="outline"
                            className="h-7 px-2 text-xs gap-1 border-primary/30 text-primary hover:bg-primary/5"
                            title="Sử dụng lượt OCR này để tạo bản biên soạn"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Link
                              to="/workspaces/$workspaceId/collections/$collectionId/compilations"
                              params={{ workspaceId, collectionId }}
                              search={{
                                create: true,
                                ocrRunId: run.id,
                                sourceId,
                                revisionId,
                                revisionNo: run.revision_no,
                                generation: run.generation,
                                version: 0,
                              }}
                            >
                              <BookOpen className="size-3" />
                              <span className="hidden sm:inline">
                                Biên soạn
                              </span>
                            </Link>
                          </Button>
                        )}

                        <Button
                          size="sm"
                          variant={isSelected ? "secondary" : "ghost"}
                          className="h-7 px-2 text-xs gap-1"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectRun(run);
                          }}
                        >
                          {isSelected ? (
                            <CheckCircle2 className="size-3 text-primary" />
                          ) : (
                            <ExternalLink className="size-3 text-muted-foreground" />
                          )}
                          <span className="hidden sm:inline">
                            {isSelected ? "Đang chọn" : "Chi tiết"}
                          </span>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>

        {/* Pagination Bar */}
        {totalPages > 1 ? (
          <div className="flex items-center justify-between p-3 border-t text-xs text-muted-foreground bg-muted/10">
            <span>
              Tổng số {meta.total} lượt xử lý (Trang {meta.page}/{totalPages})
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                className="h-7 w-7 p-0"
                disabled={page <= 1}
                onClick={() => onPageChange(page - 1)}
              >
                <ChevronLeft className="size-3.5" />
                <span className="sr-only">Trang trước</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-7 w-7 p-0"
                disabled={page >= totalPages}
                onClick={() => onPageChange(page + 1)}
              >
                <ChevronRight className="size-3.5" />
                <span className="sr-only">Trang sau</span>
              </Button>
            </div>
          </div>
        ) : null}
      </Card>
    </div>
  );
}
