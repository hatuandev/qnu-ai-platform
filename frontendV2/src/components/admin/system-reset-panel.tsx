import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  RotateCcw,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { systemResetAndSeed } from "@/api/operations/requests";
import type { SystemResetResponse } from "@/api/operations/types";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

const REQUIRED_CONFIRM_PHRASE = "RESET_AND_SEED";

export function SystemResetPanel() {
  const [seedWorkspace, setSeedWorkspace] = useState(true);
  const [seedModelops, setSeedModelops] = useState(true);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [confirmPhrase, setConfirmPhrase] = useState("");
  const [isPending, setIsPending] = useState(false);
  const [lastResult, setLastResult] = useState<SystemResetResponse | null>(
    null,
  );

  const handleOpenDialog = () => {
    setConfirmPhrase("");
    setDialogOpen(true);
  };

  const handleExecuteReset = async () => {
    if (confirmPhrase.trim() !== REQUIRED_CONFIRM_PHRASE) {
      toast.error(
        `Vui lòng nhập chính xác cụm từ xác nhận "${REQUIRED_CONFIRM_PHRASE}".`,
      );
      return;
    }

    setIsPending(true);
    try {
      const res = await systemResetAndSeed({
        confirm_phrase: REQUIRED_CONFIRM_PHRASE,
        seed_workspace: seedWorkspace,
        seed_modelops: seedModelops,
        seed_assistant: false,
      });

      setLastResult(res);
      setDialogOpen(false);
      setConfirmPhrase("");
      toast.success(
        "Đã đặt lại toàn bộ hệ thống và nạp dữ liệu hạt giống thành công!",
      );
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Có lỗi xảy ra khi thực hiện đặt lại hệ thống.";
      toast.error(msg);
    } finally {
      setIsPending(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Tiêu đề mục */}
      <div className="space-y-0.5">
        <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
          <RotateCcw className="size-4 text-primary shrink-0" />
          <span>Đặt lại hệ thống & Dữ liệu hạt giống</span>
        </h3>
        <p className="text-xs text-muted-foreground">
          Dọn sạch toàn bộ cơ sở dữ liệu runtime, vector Qdrant, MinIO blob
          storage, Redis cache và tùy chọn nạp lại dữ liệu mẫu ban đầu.
        </p>
      </div>

      <Separator />

      {/* Tùy chọn nạp dữ liệu hạt giống (Seed Options) */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-primary shrink-0" />
          <h4 className="text-xs font-semibold text-foreground">
            Tùy chọn nạp dữ liệu hạt giống (Seed Data)
          </h4>
        </div>
        <p className="text-xs text-muted-foreground">
          Sau khi dọn sạch cơ sở dữ liệu, hệ thống sẽ tự động cấu hình lại các
          thành phần được chọn bên dưới:
        </p>

        <div className="grid gap-3 pt-1">
          {/* Checkbox 1: Workspace */}
          <label
            htmlFor="seed-workspace-checkbox"
            className="flex items-start gap-3 p-3 rounded-lg border border-border/70 bg-card hover:bg-muted/40 cursor-pointer transition-colors"
          >
            <Checkbox
              id="seed-workspace-checkbox"
              checked={seedWorkspace}
              onCheckedChange={(checked) => setSeedWorkspace(Boolean(checked))}
              className="mt-0.5"
            />
            <div className="space-y-0.5 min-w-0">
              <span className="text-xs font-medium text-foreground block">
                Tự động tạo Workspace SHL mặc định
              </span>
              <span className="text-[11px] text-muted-foreground block leading-relaxed">
                Tạo lại không gian làm việc{" "}
                <code className="font-mono text-primary">shl</code> (Trung tâm
                Số & Học liệu), gán quyền Quản trị viên cho tài khoản hiện tại
                cùng các thành viên thử nghiệm chuẩn.
              </span>
            </div>
          </label>

          {/* Checkbox 2: ModelOps */}
          <label
            htmlFor="seed-modelops-checkbox"
            className="flex items-start gap-3 p-3 rounded-lg border border-border/70 bg-card hover:bg-muted/40 cursor-pointer transition-colors"
          >
            <Checkbox
              id="seed-modelops-checkbox"
              checked={seedModelops}
              onCheckedChange={(checked) => setSeedModelops(Boolean(checked))}
              className="mt-0.5"
            />
            <div className="space-y-0.5 min-w-0">
              <span className="text-xs font-medium text-foreground block">
                Tự động cấu hình ModelOps kết nối QNU AI Server
              </span>
              <span className="text-[11px] text-muted-foreground block leading-relaxed">
                Thiết lập kết nối với mô hình Chat (
                <code className="font-mono">qwen3.8-27b-q4</code> kèm thinking
                policy), Embedding (<code className="font-mono">bge-m3</code>),
                Reranker (<code className="font-mono">bge-reranker-v2-m3</code>)
                và OCR (<code className="font-mono">mineru</code>), đồng thời
                gán mặc định cho hệ thống.
              </span>
            </div>
          </label>
        </div>
      </div>

      {/* Thẻ Cảnh báo Nguy hiểm (Danger Zone) */}
      <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 sm:p-5 space-y-4">
        <div className="flex items-start gap-3">
          <div className="size-8 rounded-lg bg-destructive/10 flex items-center justify-center shrink-0 mt-0.5 text-destructive">
            <ShieldAlert className="size-5" />
          </div>
          <div className="space-y-1 min-w-0">
            <h4 className="text-xs font-semibold text-destructive">
              Khu vực nguy hiểm (Danger Zone)
            </h4>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Thao tác này sẽ thực hiện lệnh{" "}
              <code className="font-mono text-destructive">
                TRUNCATE TABLE ... RESTART IDENTITY CASCADE
              </code>{" "}
              trên hơn 50 bảng nghiệp vụ runtime, xóa vĩnh viễn toàn bộ lịch sử
              hội thoại, kho tri thức, tệp upload gốc, vector Qdrant và Redis
              cache.
            </p>
            <p className="text-[11px] text-muted-foreground leading-relaxed font-medium">
              Bảng di trú hệ thống (
              <code className="font-mono">alembic_version_backendv1</code>) và
              bảng từ điển chính tả (
              <code className="font-mono">ocr_spelling_defaults</code>) luôn
              được bảo toàn an toàn tuyệt đối.
            </p>
          </div>
        </div>

        <div className="pt-1 flex items-center justify-between gap-3 border-t border-destructive/20">
          <span className="text-[11px] text-muted-foreground">
            Yêu cầu xác nhận trước khi thực thi
          </span>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleOpenDialog}
            className="shrink-0"
          >
            <RotateCcw className="size-3.5 mr-1.5" />
            <span>Đặt lại toàn bộ hệ thống...</span>
          </Button>
        </div>
      </div>

      {/* Bảng kết quả sau khi reset (nếu vừa chạy) */}
      {lastResult && (
        <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-3">
          <div className="flex items-center gap-2 text-primary font-semibold text-xs">
            <CheckCircle2 className="size-4 shrink-0" />
            <span>Kết quả đặt lại và nạp dữ liệu gần nhất</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1 text-xs">
            <div className="p-2.5 rounded-lg bg-card border border-border/60">
              <span className="text-[10px] text-muted-foreground block">
                Bảng đã dọn
              </span>
              <span className="text-sm font-semibold font-mono text-foreground">
                {String(lastResult.stats.tables_truncated ?? 0)}
              </span>
            </div>
            <div className="p-2.5 rounded-lg bg-card border border-border/60">
              <span className="text-[10px] text-muted-foreground block">
                Vector Qdrant xóa
              </span>
              <span className="text-sm font-semibold font-mono text-foreground">
                {String(lastResult.stats.qdrant_collections_deleted ?? 0)}
              </span>
            </div>
            <div className="p-2.5 rounded-lg bg-card border border-border/60">
              <span className="text-[10px] text-muted-foreground block">
                File MinIO xóa
              </span>
              <span className="text-sm font-semibold font-mono text-foreground">
                {String(lastResult.stats.blob_objects_purged ?? 0)}
              </span>
            </div>
            <div className="p-2.5 rounded-lg bg-card border border-border/60">
              <span className="text-[10px] text-muted-foreground block">
                Redis Key dọn
              </span>
              <span className="text-sm font-semibold font-mono text-foreground">
                {String(lastResult.stats.redis_keys_cleared ?? 0)}
              </span>
            </div>
          </div>

          <div className="pt-2 flex flex-wrap items-center justify-between gap-2 border-t border-primary/10">
            <div className="text-[11px] text-muted-foreground">
              {lastResult.stats.workspace_code && (
                <span>
                  Workspace mới:{" "}
                  <code className="font-mono text-foreground font-semibold">
                    {String(lastResult.stats.workspace_code)}
                  </code>{" "}
                  ({String(lastResult.stats.workspace_name)})
                </span>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                window.location.href = "/";
              }}
              className="text-xs"
            >
              <span>Về màn hình Tổng quan</span>
            </Button>
          </div>
        </div>
      )}

      {/* Dialog Xác nhận Bảo vệ An toàn */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md" role="alertdialog">
          <DialogHeader>
            <div className="size-10 rounded-full bg-destructive/10 text-destructive flex items-center justify-center mb-2 mx-auto sm:mx-0">
              <AlertTriangle className="size-5" />
            </div>
            <DialogTitle className="text-base text-foreground">
              Xác nhận đặt lại toàn bộ hệ thống
            </DialogTitle>
            <DialogDescription asChild>
              <div className="space-y-3 pt-1 text-xs text-muted-foreground leading-relaxed">
                <p>
                  Thao tác này sẽ{" "}
                  <strong className="text-destructive font-semibold">
                    XÓA TOÀN BỘ DỮ LIỆU CŨ
                  </strong>{" "}
                  trên PostgreSQL, Qdrant, MinIO và Redis. Hệ thống sau đó sẽ
                  nạp lại cấu hình hạt giống theo các tùy chọn bạn đã chọn.
                </p>
                <p>
                  Để xác nhận, vui lòng nhập chính xác từ khóa{" "}
                  <code className="font-mono font-bold text-destructive px-1.5 py-0.5 rounded bg-destructive/10">
                    {REQUIRED_CONFIRM_PHRASE}
                  </code>{" "}
                  vào ô dưới đây:
                </p>
              </div>
            </DialogDescription>
          </DialogHeader>

          <div className="py-2">
            <Input
              value={confirmPhrase}
              onChange={(e) => setConfirmPhrase(e.target.value)}
              placeholder="Nhập RESET_AND_SEED"
              autoFocus
              className="font-mono text-xs text-center"
              disabled={isPending}
            />
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDialogOpen(false)}
              disabled={isPending}
            >
              Hủy
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleExecuteReset}
              disabled={
                confirmPhrase.trim() !== REQUIRED_CONFIRM_PHRASE || isPending
              }
            >
              {isPending ? (
                <>
                  <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                  <span>Đang dọn sạch & Seed...</span>
                </>
              ) : (
                <>
                  <RotateCcw className="size-3.5 mr-1.5" />
                  <span>Xác nhận Đặt lại</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
