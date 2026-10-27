import { AlertCircle, Cpu, Loader2, Play } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useRequestProcessingRunMutation } from "@/features/knowledge/ocr-queries";
import { formatOcrError } from "@/features/knowledge/ocr-schemas";
import { useCatalogQuery } from "@/features/modelops/queries";

export function OcrRequestDialog({
  workspaceId,
  collectionId,
  sourceId,
  revisionId,
  revisionNo,
  fileName,
  isOpen,
  onClose,
  onSuccess,
}: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  revisionId: string;
  revisionNo: number;
  fileName: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (runId: string) => void;
}) {
  const [providerId, setProviderId] = useState<string>("default");
  const [force, setForce] = useState(false);

  const catalogQuery = useCatalogQuery(workspaceId, { enabled: isOpen });
  const requestMutation = useRequestProcessingRunMutation(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
  );

  const ocrProviders = (catalogQuery.data ?? []).filter((p) =>
    p.capabilities.includes("ocr"),
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const outcome = await requestMutation.mutateAsync({
        provider_id: providerId === "default" ? null : providerId,
        force,
      });

      if (outcome.created) {
        toast.success(
          `Đã tạo lượt xử lý OCR mới: Thế hệ #${outcome.run.generation}.`,
        );
      } else {
        toast.info(
          `Đã tái sử dụng lượt xử lý tương thích: Thế hệ #${outcome.run.generation}.`,
        );
      }

      onSuccess?.(outcome.run.id);
      onClose();
    } catch (error: unknown) {
      if (error instanceof ApiProblemError) {
        toast.error(formatOcrError(error.code, error.message));
      } else {
        toast.error("Không thể yêu cầu xử lý OCR.");
      }
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[480px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base font-semibold">
              <Cpu className="size-4 text-primary" />
              Yêu cầu xử lý OCR
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Phiên bản v{revisionNo} ({fileName})
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4 text-sm">
            {/* Provider selection */}
            <div className="space-y-1.5">
              <Label htmlFor="ocr-provider" className="text-xs font-medium">
                Mô hình OCR (ModelOps)
              </Label>
              <Select
                value={providerId}
                onValueChange={(val) => setProviderId(val)}
                disabled={requestMutation.isPending}
              >
                <SelectTrigger id="ocr-provider" className="h-9 text-xs">
                  <SelectValue placeholder="Chọn provider OCR" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="default" className="text-xs">
                    Theo mặc định workspace
                  </SelectItem>
                  {ocrProviders.map((p) => (
                    <SelectItem key={p.id} value={p.id} className="text-xs">
                      {p.name} ({p.id})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-[11px] text-muted-foreground">
                Chỉ hiển thị các nhà cung cấp đang hoạt động và có năng lực OCR
                trong ModelOps.
              </p>
            </div>

            {/* Force checkbox with warning */}
            <div className="rounded-lg border p-3 space-y-2 bg-muted/20">
              <div className="flex items-start gap-2.5">
                <Checkbox
                  id="force-reprocess"
                  checked={force}
                  onCheckedChange={(checked) => setForce(Boolean(checked))}
                  disabled={requestMutation.isPending}
                  className="mt-0.5"
                />
                <div className="space-y-0.5">
                  <Label
                    htmlFor="force-reprocess"
                    className="text-xs font-semibold cursor-pointer"
                  >
                    Xử lý lại thành lượt mới (force = true)
                  </Label>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Mặc định hệ thống sẽ tự động tái sử dụng kết quả hoàn tất
                    nếu cùng cấu hình để tiết kiệm quota. Bật tùy chọn này để
                    bắt buộc sinh thế hệ OCR mới.
                  </p>
                </div>
              </div>

              {force ? (
                <Alert
                  variant="warning"
                  className="text-xs py-2 px-3 border-warning/40 bg-warning/10"
                >
                  <AlertCircle className="size-3.5 text-warning" />
                  <AlertTitle className="text-xs font-semibold text-warning">
                    Lưu ý về tài nguyên
                  </AlertTitle>
                  <AlertDescription className="text-[11px] text-warning/90 mt-0.5">
                    Hành động này sẽ gửi lại tài liệu đến mô hình OCR và phát
                    sinh mức tiêu thụ token/quota mới.
                  </AlertDescription>
                </Alert>
              ) : null}
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={requestMutation.isPending}
              className="text-xs"
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={requestMutation.isPending}
              className="text-xs gap-1.5"
            >
              {requestMutation.isPending ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang gửi...</span>
                </>
              ) : (
                <>
                  <Play className="size-3.5" />
                  <span>Bắt đầu xử lý</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
