import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  BookOpen,
  ExternalLink,
  GitBranch,
  Loader2,
  Plus,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDateTimeValue } from "@/lib/date-utils";
import { useCompilationRunsQuery } from "./compilation-queries";
import {
  formatCompilationOrigin,
  formatCompilationStatus,
} from "./compilation-schemas";
import { ListPagination, type ListPagingProps } from "./list-pagination";

export function CompilationRunsList({
  workspaceId,
  collectionId,
  canManage,
  onOpenCreateDialog,
  page = 1,
  pageSize = 20,
  onPageChange,
  onPageSizeChange,
}: ListPagingProps & {
  workspaceId: string;
  collectionId: string;
  canManage: boolean;
  onOpenCreateDialog: () => void;
}) {
  const runsQuery = useCompilationRunsQuery(
    workspaceId,
    collectionId,
    pageSize,
    { offset: (page - 1) * pageSize, lookahead: true },
  );
  const runs = (runsQuery.data ?? []).slice(0, pageSize);

  if (runsQuery.isLoading) {
    return (
      <Card className="rounded-xl shadow-2xs p-4 space-y-3">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </Card>
    );
  }

  if (runsQuery.isError) {
    return (
      <Card className="rounded-xl border-destructive/20 bg-destructive/5 p-4 text-xs">
        <div className="flex items-center gap-2 text-destructive font-semibold">
          <AlertCircle className="size-4 shrink-0" />
          <span>Không thể tải các lần chuẩn bị nội dung</span>
        </div>
        <p className="text-muted-foreground mt-1">
          {runsQuery.error instanceof Error
            ? runsQuery.error.message
            : "Lỗi kết nối máy chủ."}
        </p>
        <Button
          size="sm"
          variant="outline"
          className="mt-3 h-7 text-xs gap-1.5"
          onClick={() => void runsQuery.refetch()}
        >
          <RefreshCw className="size-3" />
          <span>Tải lại</span>
        </Button>
        <ListPagination
          page={page}
          pageSize={pageSize}
          onPageChange={onPageChange}
          onPageSizeChange={onPageSizeChange}
          hasNext={false}
          label="lần chuẩn bị"
        />
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {/* Top toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5">
        <div>
          <h2 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
            <BookOpen className="size-4 text-primary" />
            <span>Các lần chuẩn bị nội dung</span>
          </h2>
          <p className="text-xs text-muted-foreground">
            Trang {page} · tối đa {pageSize} lần chuẩn bị nội dung (mới nhất
            trước).
          </p>
        </div>

        <div className="flex items-center gap-2">
          {canManage && (
            <Button
              size="sm"
              className="h-8 text-xs gap-1.5"
              onClick={onOpenCreateDialog}
            >
              <Plus className="size-3.5" />
              <span>Chuẩn bị nội dung</span>
            </Button>
          )}
        </div>
      </div>

      {runs.length === 0 ? (
        <Card className="rounded-xl shadow-2xs">
          <CardContent className="py-12 text-center space-y-3">
            <div className="size-10 rounded-full bg-primary/10 flex items-center justify-center mx-auto text-primary">
              <BookOpen className="size-5" />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-foreground">
                Chưa có lần chuẩn bị nội dung nào
              </h3>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Bắt đầu lần chuẩn bị đầu tiên để tổng hợp nội dung đã đọc thành
                bản nháp có cấu trúc kèm dẫn chứng.
              </p>
            </div>
            {canManage && (
              <Button
                size="sm"
                className="h-8 text-xs gap-1.5 mt-2"
                onClick={onOpenCreateDialog}
              >
                <Plus className="size-3.5" />
                <span>Bắt đầu chuẩn bị</span>
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card className="rounded-xl shadow-2xs overflow-hidden">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-muted/30">
                <TableRow>
                  <TableHead className="text-xs min-w-[200px]">
                    Chủ đề
                  </TableHead>
                  <TableHead className="w-28 text-xs">Cách tạo</TableHead>
                  <TableHead className="w-32 text-xs">Trạng thái</TableHead>
                  <TableHead className="w-36 text-xs">Thời điểm</TableHead>
                  <TableHead className="w-24 text-right text-xs">
                    Thao tác
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => {
                  const statusInfo = formatCompilationStatus(run.status);
                  const originInfo = formatCompilationOrigin(run.origin);

                  return (
                    <TableRow key={run.id} className="hover:bg-muted/10">
                      <TableCell className="text-xs">
                        <Link
                          to="/workspaces/$workspaceId/collections/$collectionId/compilations/$runId"
                          params={{
                            workspaceId,
                            collectionId,
                            runId: run.id,
                          }}
                          className="font-medium text-foreground hover:text-primary transition-colors line-clamp-1 block"
                        >
                          {run.topic}
                        </Link>
                      </TableCell>

                      <TableCell className="text-xs">
                        {originInfo.isEdit ? (
                          <div className="space-y-0.5">
                            <Badge
                              variant="secondary"
                              className="text-[10px] py-0 gap-1 bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20"
                            >
                              <GitBranch className="size-2.5" />
                              <span>Bản sửa</span>
                            </Badge>
                            {run.parent_run_id && (
                              <div className="text-[10px] text-muted-foreground">
                                từ lần trước
                              </div>
                            )}
                          </div>
                        ) : (
                          <Badge
                            variant="outline"
                            className="text-[10px] py-0 gap-1"
                          >
                            <Sparkles className="size-2.5 text-primary" />
                            <span>Tự động</span>
                          </Badge>
                        )}
                      </TableCell>

                      <TableCell className="text-xs">
                        <div className="flex items-center gap-1.5">
                          <Badge
                            variant={statusInfo.variant}
                            className="text-[11px] py-0 font-normal"
                            title={run.error_code ?? undefined}
                          >
                            {statusInfo.label}
                          </Badge>
                          {run.status === "running" && (
                            <Loader2 className="size-3 animate-spin text-primary" />
                          )}
                        </div>
                      </TableCell>

                      <TableCell className="text-xs text-muted-foreground">
                        <div>{formatDateTimeValue(run.requested_at)}</div>
                        {run.finished_at && (
                          <div className="text-[10px] text-muted-foreground/70">
                            Xong: {formatDateTimeValue(run.finished_at)}
                          </div>
                        )}
                      </TableCell>

                      <TableCell className="text-right">
                        <Button
                          asChild
                          size="sm"
                          variant="ghost"
                          className="h-7 px-2 text-xs gap-1"
                        >
                          <Link
                            to="/workspaces/$workspaceId/collections/$collectionId/compilations/$runId"
                            params={{
                              workspaceId,
                              collectionId,
                              runId: run.id,
                            }}
                          >
                            <ExternalLink className="size-3 text-muted-foreground" />
                            <span>Xem</span>
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </Card>
      )}
      <ListPagination
        page={page}
        pageSize={pageSize}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
        hasNext={(runsQuery.data?.length ?? 0) > pageSize}
        disabled={runsQuery.isFetching}
        label="lần chuẩn bị"
      />
    </div>
  );
}
