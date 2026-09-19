import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { KnowledgeReconciliationReport } from "@/services/api-client";
import { CheckCircle2, CircleAlert, RefreshCw, ShieldCheck, Zap } from "lucide-react";

interface CollectionReconcileDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  collectionCode: string;
  reconcileReport: KnowledgeReconciliationReport | null;
  isLoading: boolean;
  isFixing: boolean;
  onRefresh: () => void;
  onFix: () => void;
}

export function CollectionReconcileDialog({
  open,
  onOpenChange,
  collectionCode,
  reconcileReport,
  isLoading,
  isFixing,
  onRefresh,
  onFix,
}: CollectionReconcileDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base font-bold">
            <ShieldCheck className="size-5 text-primary" />
            <span>Đối Soát Kiểm Toán Dữ Liệu 4 Tầng (Reconciliation Audit)</span>
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="py-12 text-center space-y-3">
            <RefreshCw className="size-8 animate-spin mx-auto text-primary" />
            <p className="text-xs text-muted-foreground">
              Đang đối soát dữ liệu giữa PostgreSQL, Qdrant, MinIO và Redis...
            </p>
          </div>
        ) : reconcileReport ? (
          <div className="space-y-4 py-2 text-xs">
            <div className="flex items-center justify-between p-3 rounded-lg border bg-muted/30">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground">Trạng thái toàn vẹn:</span>
                {reconcileReport.is_consistent ? (
                  <Badge
                    variant="outline"
                    className="bg-emerald-500/10 text-emerald-600 border-emerald-500/30 gap-1"
                  >
                    <CheckCircle2 className="size-3" />
                    <span>Nhất quán 100% (Zero Ghost Vectors)</span>
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="bg-rose-500/10 text-rose-600 border-rose-500/30 gap-1"
                  >
                    <CircleAlert className="size-3" />
                    <span>Phát hiện sai lệch ({reconcileReport.discrepancies.length} vấn đề)</span>
                  </Badge>
                )}
              </div>
              <span className="font-mono text-muted-foreground">{collectionCode}</span>
            </div>

            {/* 4 Cards metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <div className="p-3 rounded-lg border bg-card text-center space-y-1">
                <p className="text-xs text-muted-foreground font-medium">Tài liệu DB</p>
                <p className="text-lg font-bold font-mono text-foreground">
                  {reconcileReport.db_documents_count}
                </p>
                <p className="text-xs text-emerald-600">
                  {reconcileReport.indexed_documents_count} đã index
                </p>
              </div>
              <div className="p-3 rounded-lg border bg-card text-center space-y-1">
                <p className="text-xs text-muted-foreground font-medium">Chunks DB</p>
                <p className="text-lg font-bold font-mono text-foreground">
                  {reconcileReport.db_chunks_count}
                </p>
                <p className="text-xs text-muted-foreground">Đoạn văn bản</p>
              </div>
              <div className="p-3 rounded-lg border bg-card text-center space-y-1">
                <p className="text-xs text-muted-foreground font-medium">Qdrant Points</p>
                <p className="text-lg font-bold font-mono text-primary">
                  {reconcileReport.qdrant_points_count}
                </p>
                <p className="text-xs text-muted-foreground">Vectors 1024-dim</p>
              </div>
              <div className="p-3 rounded-lg border bg-card text-center space-y-1">
                <p className="text-xs text-muted-foreground font-medium">Storage Files</p>
                <p className="text-lg font-bold font-mono text-foreground">
                  {reconcileReport.storage_files_count}
                </p>
                <p className="text-xs text-muted-foreground">Tệp vật lý S3/Local</p>
              </div>
            </div>

            {/* Discrepancies list */}
            {reconcileReport.discrepancies.length > 0 && (
              <div className="space-y-2">
                <p className="font-semibold text-foreground text-xs">
                  Chi tiết sai lệch phát hiện:
                </p>
                <div className="max-h-40 overflow-y-auto space-y-1.5 p-2.5 bg-rose-500/5 rounded-lg border border-rose-500/20">
                  {reconcileReport.discrepancies.map((d, idx) => (
                    <div
                      key={`${d.type}-${d.document_id || idx}`}
                      className="flex items-start gap-2 text-xs text-rose-600"
                    >
                      <CircleAlert className="size-3.5 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-mono font-medium">[{d.type}]</span>: {d.details}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : null}

        <div className="flex items-center justify-between pt-3 border-t border-border">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8 text-xs"
            onClick={() => onOpenChange(false)}
          >
            Đóng
          </Button>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 text-xs gap-1.5"
              disabled={isLoading || isFixing}
              onClick={onRefresh}
            >
              <RefreshCw className={`size-3.5 ${isLoading ? "animate-spin" : ""}`} />
              <span>Quét lại</span>
            </Button>
            {reconcileReport && !reconcileReport.is_consistent && (
              <Button
                type="button"
                size="sm"
                className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground"
                disabled={isFixing}
                onClick={onFix}
              >
                <Zap className={`size-3.5 ${isFixing ? "animate-spin" : ""}`} />
                <span>{isFixing ? "Đang đồng bộ..." : "Đồng bộ tất cả"}</span>
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
