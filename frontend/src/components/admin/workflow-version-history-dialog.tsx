import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock, History, Loader2, RotateCcw, ShieldCheck } from "lucide-react";
import type React from "react";
import { useState } from "react";
import { toast } from "sonner";
import { type WorkflowVersion, workflowsApi } from "../../services/workflows-api";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../ui/dialog";
import { ConfirmDialog } from "./confirm-dialog";

export interface WorkflowVersionHistoryDialogProps {
  workflowId: string;
  workflowName: string;
  isOpen: boolean;
  onClose: () => void;
  onRollbackSuccess?: () => void;
}

export const WorkflowVersionHistoryDialog: React.FC<WorkflowVersionHistoryDialogProps> = ({
  workflowId,
  workflowName,
  isOpen,
  onClose,
  onRollbackSuccess,
}) => {
  const queryClient = useQueryClient();
  const [selectedRollbackVersion, setSelectedRollbackVersion] = useState<WorkflowVersion | null>(
    null
  );

  const versionsQuery = useQuery({
    queryKey: ["workflow-versions", workflowId],
    queryFn: () => workflowsApi.listVersions(workflowId),
    enabled: isOpen && Boolean(workflowId),
  });

  const rollbackMutation = useMutation({
    mutationFn: (versionId: string) =>
      workflowsApi.rollbackVersion(workflowId, versionId, {
        published_by: "platform-admin",
      }),
    onSuccess: (newVersion: WorkflowVersion) => {
      toast.success(
        `Đã khôi phục thành công! Phiên bản mới v${newVersion.version_number} đã được kích hoạt.`
      );
      setSelectedRollbackVersion(null);
      void queryClient.invalidateQueries({ queryKey: ["workflow-versions", workflowId] });
      void queryClient.invalidateQueries({ queryKey: ["workflow-draft", workflowId] });
      void queryClient.invalidateQueries({ queryKey: ["workflow-definitions"] });
      onRollbackSuccess?.();
      onClose();
    },
    onError: (error: Error) => {
      toast.error(`Khôi phục phiên bản thất bại: ${error.message}`);
    },
  });

  const versions: WorkflowVersion[] = versionsQuery.data ?? [];
  const latestVersionNumber =
    versions.length > 0 ? Math.max(...versions.map((v: WorkflowVersion) => v.version_number)) : 0;

  return (
    <>
      <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col p-6">
          <DialogHeader className="pb-3 border-b border-border">
            <div className="flex items-center gap-2.5">
              <div className="flex size-8 items-center justify-center rounded-control bg-primary/10 text-primary">
                <History className="size-4" />
              </div>
              <div>
                <DialogTitle className="text-base font-bold text-foreground">
                  Lịch Sử Xuất Bản Phiên Bản
                </DialogTitle>
                <DialogDescription className="text-xs text-muted-foreground">
                  Đặc tả DAG bất biến của{" "}
                  <span className="font-semibold text-primary">{workflowName}</span> ({workflowId})
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto py-2 space-y-3">
            {versionsQuery.isLoading ? (
              <div className="flex flex-col items-center justify-center py-12 gap-2 text-muted-foreground">
                <Loader2 className="size-6 animate-spin text-primary" />
                <span className="text-xs">Đang tải lịch sử phiên bản...</span>
              </div>
            ) : versions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
                <History className="size-8 opacity-40 mb-2" />
                <p className="text-xs font-medium">Chưa có phiên bản xuất bản nào</p>
                <p className="text-[11px] opacity-75">
                  Hãy nhấn nút "Xuất bản" trên thanh công cụ Canvas để lưu phiên bản bất biến đầu
                  tiên.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-border border border-border rounded-surface overflow-hidden bg-card">
                {versions
                  .slice()
                  .sort(
                    (a: WorkflowVersion, b: WorkflowVersion) => b.version_number - a.version_number
                  )
                  .map((ver: WorkflowVersion) => {
                    const isLatest = ver.version_number === latestVersionNumber;
                    return (
                      <div
                        key={ver.id}
                        className={`p-3.5 flex items-center justify-between gap-4 transition-colors ${
                          isLatest ? "bg-primary/5" : "hover:bg-muted/30"
                        }`}
                      >
                        <div className="min-w-0 space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-foreground font-mono">
                              Phiên bản v{ver.version_number}
                            </span>
                            {isLatest && (
                              <Badge className="h-4 px-1.5 text-[9px] bg-primary/20 text-primary border-primary/30">
                                Hiện tại
                              </Badge>
                            )}
                            <Badge
                              variant="outline"
                              className="h-4 px-1.5 text-[9px] font-mono text-muted-foreground gap-1"
                            >
                              <ShieldCheck className="size-2.5 text-success" />
                              {ver.content_hash.slice(0, 8)}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Clock className="size-3" />
                              {new Date(ver.published_at).toLocaleString("vi-VN")}
                            </span>
                            <span>•</span>
                            <span>Bởi: {ver.published_by || "Quản trị viên"}</span>
                            <span>•</span>
                            <span>{ver.dag_spec.nodes?.length ?? 0} nodes</span>
                          </div>
                        </div>

                        <div>
                          {isLatest ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-primary">
                              <CheckCircle2 className="size-3.5" />
                              Đang phục vụ
                            </span>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs gap-1 hover:bg-warning/10 hover:text-warning hover:border-warning/30"
                              onClick={() => setSelectedRollbackVersion(ver)}
                            >
                              <RotateCcw className="size-3" />
                              Khôi phục
                            </Button>
                          )}
                        </div>
                      </div>
                    );
                  })}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Confirmation Dialog for Rollback */}
      <ConfirmDialog
        open={Boolean(selectedRollbackVersion)}
        onOpenChange={(open) => !open && setSelectedRollbackVersion(null)}
        title={`Khôi phục về phiên bản v${selectedRollbackVersion?.version_number}?`}
        description={`Hệ thống sẽ tạo một phiên bản xuất bản mới sao chép toàn bộ cấu trúc DAG của phiên bản v${selectedRollbackVersion?.version_number}. Bản nháp và luồng phục vụ hiện tại sẽ lập tức được cập nhật.`}
        confirmText="Xác nhận khôi phục"
        cancelText="Hủy bỏ"
        variant="default"
        isPending={rollbackMutation.isPending}
        onConfirm={() => {
          if (selectedRollbackVersion) {
            rollbackMutation.mutate(selectedRollbackVersion.id);
          }
        }}
      />
    </>
  );
};
