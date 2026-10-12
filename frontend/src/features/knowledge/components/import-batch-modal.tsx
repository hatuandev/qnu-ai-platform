import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Layers,
  RefreshCw,
  XCircle,
} from "lucide-react";
import type React from "react";
import { toast } from "sonner";
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
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";
import type { KnowledgeImportBatchResponse } from "@/types/knowledge";

interface ImportBatchModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  collectionId: string;
  batchId: string | null;
  onComplete?: () => void;
}

import { getBatchProgress, getItemProgress } from "../utils/import-progress";

export const ImportBatchModal: React.FC<ImportBatchModalProps> = ({
  open,
  onOpenChange,
  collectionId,
  batchId,
  onComplete,
}) => {
  const queryClient = useQueryClient();

  // 1. Fetch Batch Status with smart polling
  const {
    data: batch,
    isLoading,
    refetch,
  } = useQuery<KnowledgeImportBatchResponse>({
    queryKey: ["knowledge-import-batch", collectionId, batchId],
    queryFn: () =>
      batchId
        ? knowledgeApi.getImportBatch(collectionId, batchId)
        : Promise.reject(new Error("No batchId")),
    enabled: !!batchId && open,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      if (data.status === "queued" || data.status === "processing") {
        return 2000;
      }
      return false;
    },
  });

  // 2. Retry mutation
  const retryMutation = useMutation({
    mutationFn: () => {
      if (!batchId) throw new Error("Chưa có mã đợt nạp.");
      return knowledgeApi.retryFailedImportItems(collectionId, batchId);
    },
    onSuccess: () => {
      toast.success("Đang thử lại các tài liệu gặp lỗi...");
      refetch();
      queryClient.invalidateQueries({
        queryKey: ["knowledge-import-batch", collectionId, batchId],
      });
    },
    onError: (err: unknown) => {
      toast.error(extractErrorMessage(err, "Thử lại đợt nạp thất bại."));
    },
  });

  // 3. Cancel mutation
  const cancelMutation = useMutation({
    mutationFn: () => {
      if (!batchId) throw new Error("Chưa có mã đợt nạp.");
      return knowledgeApi.cancelImportBatch(collectionId, batchId);
    },
    onSuccess: () => {
      toast.success("Đã gửi yêu cầu hủy đợt nạp tài liệu.");
      refetch();
    },
    onError: (err: unknown) => {
      toast.error(extractErrorMessage(err, "Hủy đợt nạp thất bại."));
    },
  });

  if (!batchId) return null;

  const percent = getBatchProgress(batch?.items || []);
  const isFinished =
    batch?.status === "completed" ||
    batch?.status === "partial_failed" ||
    batch?.status === "failed" ||
    batch?.status === "cancelled";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] flex flex-col p-0 overflow-hidden">
        <DialogHeader className="p-5 pb-3 border-b border-border">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Layers className="size-5" />
              </div>
              <div>
                <DialogTitle className="text-base font-bold text-foreground flex items-center gap-2">
                  <span>Tiến Trình Đợt Nạp Tài Liệu</span>
                  {batch && (
                    <Badge
                      variant="outline"
                      className={`text-[11px] ${
                        batch.status === "completed"
                          ? "bg-success/10 text-success border-success/30"
                          : batch.status === "partial_failed" ||
                              batch.status === "failed"
                            ? "bg-destructive/10 text-destructive border-destructive/30"
                            : "bg-primary/10 text-primary border-primary/30"
                      }`}
                    >
                      {batch.status === "completed"
                        ? "Hoàn tất"
                        : batch.status === "partial_failed"
                          ? "Lỗi một phần"
                          : batch.status === "failed"
                            ? "Thất bại"
                            : batch.status === "cancelled"
                              ? "Đã hủy"
                              : "Đang xử lý"}
                    </Badge>
                  )}
                </DialogTitle>
                <DialogDescription className="text-xs text-muted-foreground">
                  Mã đợt:{" "}
                  <span className="font-mono text-foreground">{batchId}</span>
                </DialogDescription>
              </div>
            </div>

            <Button
              variant="ghost"
              size="icon"
              className="size-8"
              onClick={() => refetch()}
              title="Làm mới"
            >
              <RefreshCw className="size-3.5" />
            </Button>
          </div>
        </DialogHeader>

        <div className="p-5 space-y-4 flex-1 overflow-y-auto">
          {isLoading && !batch ? (
            <div className="py-12 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
              <RefreshCw className="size-4 animate-spin" />
              <span>Đang tải thông tin đợt nạp...</span>
            </div>
          ) : batch ? (
            <>
              {/* Progress Bar & Percent */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-foreground">
                    Tiến độ hoàn thành
                  </span>
                  <span className="font-semibold text-primary">{percent}%</span>
                </div>
                <Progress value={percent} className="h-2" />
              </div>

              {/* KPI Counters Ribbon */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center">
                <div className="p-2.5 rounded-lg border border-border bg-muted/30">
                  <span className="text-[11px] text-muted-foreground block">
                    Tổng số
                  </span>
                  <span className="text-base font-bold text-foreground">
                    {batch.total_count}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg border border-primary/20 bg-primary/5 text-primary">
                  <span className="text-[11px] block">Đang xử lý</span>
                  <span className="text-base font-bold">
                    {batch.processing_count + batch.queued_count}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg border border-success/20 bg-success/5 text-success">
                  <span className="text-[11px] block">Thành công</span>
                  <span className="text-base font-bold">
                    {batch.succeeded_count}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg border border-destructive/20 bg-destructive/5 text-destructive">
                  <span className="text-[11px] block">Thất bại</span>
                  <span className="text-base font-bold">
                    {batch.failed_count}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg border border-warning/20 bg-warning/5 text-warning">
                  <span className="text-[11px] block">Cần duyệt</span>
                  <span className="text-base font-bold">
                    {batch.review_required_count}
                  </span>
                </div>
              </div>

              {/* Error message if any */}
              {batch.error_message && (
                <div className="p-3 rounded-lg border border-destructive/30 bg-destructive/10 text-destructive text-xs flex items-start gap-2">
                  <AlertCircle className="size-4 shrink-0 mt-0.5" />
                  <span>{batch.error_message}</span>
                </div>
              )}

              {/* Items Table */}
              <div className="rounded-lg border border-border overflow-hidden">
                <div className="p-3 bg-muted/40 border-b border-border text-xs font-semibold text-foreground">
                  Danh sách tài liệu trong đợt nạp ({batch.items.length})
                </div>
                <div className="max-h-60 w-full overflow-auto">
                  <Table>
                    <TableHeader className="bg-muted/20 sticky top-0">
                      <TableRow className="text-xs h-8">
                        <TableHead>Tên tài liệu</TableHead>
                        <TableHead className="w-24 text-center">
                          Giai đoạn
                        </TableHead>
                        <TableHead className="text-center">
                          Tiến độ
                          <span className="block text-[11px] font-normal text-muted-foreground">
                            Theo giai đoạn
                          </span>
                        </TableHead>
                        <TableHead className="w-28 text-center">
                          Trạng thái
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {batch.items.map((item) => (
                        <TableRow key={item.id} className="text-xs h-10">
                          <TableCell>
                            <span className="font-medium text-foreground block truncate">
                              {item.origin_title || item.origin_file_name}
                            </span>
                            <span className="text-[11px] text-muted-foreground block truncate">
                              {item.origin_file_name}
                            </span>
                            {item.failure_detail && (
                              <span className="text-[10px] text-destructive block mt-0.5">
                                {item.failure_code}: {item.failure_detail}
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="text-center font-mono text-[11px]">
                            {item.progress_phase || item.phase}
                          </TableCell>
                          <TableCell>
                            <div
                              className="space-y-1 min-w-24"
                              title="Tiến độ theo các bước đã hoàn thành, không phải phần trăm trang OCR"
                            >
                              <span className="block text-center tabular-nums">
                                {Math.round(getItemProgress(item))}%
                              </span>
                              <Progress
                                value={getItemProgress(item)}
                                aria-label={`Tiến độ ${item.origin_title || item.origin_file_name}`}
                              />
                            </div>
                          </TableCell>
                          <TableCell className="text-center">
                            {item.status === "succeeded" ? (
                              <Badge
                                variant="outline"
                                className="bg-success/10 text-success border-success/30 text-[10px] gap-1"
                              >
                                <CheckCircle2 className="size-2.5" />
                                Thành công
                              </Badge>
                            ) : item.status === "failed" ? (
                              <Badge
                                variant="destructive"
                                className="text-[10px] gap-1"
                              >
                                <XCircle className="size-2.5" />
                                Thất bại
                              </Badge>
                            ) : item.status === "review_required" ? (
                              <Badge
                                variant="outline"
                                className="border-warning/30 bg-warning/10 text-warning"
                              >
                                Cần duyệt
                              </Badge>
                            ) : item.status === "processing" ? (
                              <Badge
                                variant="outline"
                                className="bg-primary/10 text-primary border-primary/30 text-[10px] gap-1"
                              >
                                <RefreshCw className="size-2.5 animate-spin" />
                                Đang xử lý
                              </Badge>
                            ) : (
                              <Badge
                                variant="outline"
                                className="bg-muted text-muted-foreground text-[10px] gap-1"
                              >
                                <Clock className="size-2.5" />
                                Chờ
                              </Badge>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </>
          ) : null}
        </div>

        <DialogFooter className="p-4 border-t border-border flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {!isFinished && (
              <Button
                variant="ghost"
                size="sm"
                className="text-xs text-destructive hover:bg-destructive/10"
                disabled={cancelMutation.isPending}
                onClick={() => cancelMutation.mutate()}
              >
                Hủy đợt nạp
              </Button>
            )}
            {batch && batch.failed_count > 0 && (
              <Button
                variant="outline"
                size="sm"
                className="text-xs gap-1.5"
                disabled={retryMutation.isPending}
                onClick={() => retryMutation.mutate()}
              >
                <RefreshCw
                  className={`size-3.5 ${retryMutation.isPending ? "animate-spin" : ""}`}
                />
                Thử lại {batch.failed_count} mục lỗi
              </Button>
            )}
          </div>

          <Button
            size="sm"
            className="text-xs"
            onClick={() => {
              onOpenChange(false);
              onComplete?.();
            }}
          >
            {isFinished ? "Hoàn tất & Đóng" : "Đóng cửa sổ"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
