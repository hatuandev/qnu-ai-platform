import { Clock, History, Loader2, RotateCcw } from "lucide-react";
import * as React from "react";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
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
import type { AssistantVersionItem } from "@/types/assistants";

interface AssistantVersionHistoryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assistantName: string;
  versions?: AssistantVersionItem[];
  isLoading: boolean;
  onRollback: (versionId: string) => void;
  isRollbacking: boolean;
}

export function AssistantVersionHistoryDialog({
  open,
  onOpenChange,
  assistantName,
  versions = [],
  isLoading,
  onRollback,
  isRollbacking,
}: AssistantVersionHistoryDialogProps) {
  const [rollbackTarget, setRollbackTarget] =
    React.useState<AssistantVersionItem | null>(null);

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base font-bold">
              <History className="size-4 text-primary" />
              Lịch Sử Phiên Bản & Khôi Phục (Rollback)
            </DialogTitle>
            <DialogDescription className="text-xs">
              Xem lại các mốc cấu hình đã lưu của Trợ lý{" "}
              <strong className="text-foreground">{assistantName}</strong>. Mỗi
              lần lưu hoặc xuất bản đều tự động tạo một snapshot bất biến.
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto pr-1 space-y-3 py-2 text-xs">
            {isLoading ? (
              <div className="flex items-center justify-center py-12 text-muted-foreground gap-2">
                <Loader2 className="size-4 animate-spin text-primary" />
                <span>Đang tải lịch sử phiên bản...</span>
              </div>
            ) : versions.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground border border-dashed rounded-lg">
                <History className="size-8 mx-auto mb-2 opacity-30" />
                <p className="font-medium text-foreground">
                  Chưa có bản ghi phiên bản nào
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Khi bạn lưu thay đổi hoặc xuất bản, hệ thống sẽ tự động tạo
                  mốc phiên bản tại đây.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {versions.map((ver, idx) => (
                  <div
                    key={ver.id}
                    className="p-3.5 rounded-lg border border-border bg-card/60 hover:bg-card transition-colors flex items-start justify-between gap-4"
                  >
                    <div className="space-y-1.5 flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge
                          variant="outline"
                          className="font-mono text-primary bg-primary/10 border-primary/30"
                        >
                          v{ver.version_number}
                        </Badge>
                        {idx === 0 && (
                          <Badge
                            variant="default"
                            className="text-xs bg-primary text-primary-foreground"
                          >
                            Hiện tại
                          </Badge>
                        )}
                        <span className="text-muted-foreground text-xs flex items-center gap-1">
                          <Clock className="size-3" />
                          {ver.created_at
                            ? new Date(ver.created_at).toLocaleString("vi-VN")
                            : "Gần đây"}
                        </span>
                        <span className="text-muted-foreground text-xs">
                          • bởi{" "}
                          <strong className="text-foreground">
                            {ver.created_by}
                          </strong>
                        </span>
                      </div>
                      <p className="text-foreground font-medium text-xs">
                        {ver.change_summary}
                      </p>
                      {ver.snapshot_data && (
                        <div className="text-xs text-muted-foreground flex items-center gap-3">
                          <span>
                            Workflow:{" "}
                            <code className="text-primary font-mono">
                              {String(ver.snapshot_data.workflow_id || "N/A")}
                            </code>
                          </span>
                          <span>
                            Kho:{" "}
                            <code className="text-primary font-mono">
                              {String(ver.snapshot_data.collection_id || "N/A")}
                            </code>
                          </span>
                        </div>
                      )}
                    </div>

                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 text-xs gap-1.5 shrink-0 hover:border-primary hover:text-primary"
                      disabled={isRollbacking || idx === 0}
                      onClick={() => setRollbackTarget(ver)}
                    >
                      <RotateCcw className="size-3.5" />
                      {idx === 0 ? "Bản hiện hành" : "Khôi phục"}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => onOpenChange(false)}
            >
              Đóng
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirm Rollback Dialog */}
      <ConfirmDialog
        open={Boolean(rollbackTarget)}
        title={`Khôi phục về phiên bản v${rollbackTarget?.version_number}?`}
        description={`Toàn bộ 7 lớp cấu hình hiện tại (Persona, ModelOps, Guardrails, Workflow, Kho tri thức) sẽ được khôi phục về trạng thái của mốc "${rollbackTarget?.change_summary}". Bạn có chắc chắn muốn thực hiện?`}
        confirmText="Xác nhận khôi phục"
        variant="default"
        isPending={isRollbacking}
        onConfirm={() => {
          if (rollbackTarget) {
            onRollback(rollbackTarget.id);
            setRollbackTarget(null);
          }
        }}
        onOpenChange={(isOpen) => {
          if (!isOpen) setRollbackTarget(null);
        }}
      />
    </>
  );
}
