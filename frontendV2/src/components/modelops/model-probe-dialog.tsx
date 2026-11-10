import {
  AlertCircle,
  CheckCircle2,
  Clock,
  FlaskConical,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useProbeModelMutation } from "@/api/modelops/queries";
import type {
  Capability,
  DiagnosticCheck,
  ModelProvider,
} from "@/api/modelops/types";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CAPABILITY_LABELS } from "./constants";

export function ModelProbeDialog({
  open,
  onOpenChange,
  model,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  model: ModelProvider;
}) {
  const probeMutation = useProbeModelMutation();

  const supportedCapabilities =
    model.capabilities.length > 0
      ? model.capabilities
      : (["chat"] as Capability[]);
  const firstCapability = supportedCapabilities[0];
  const [selectedCapability, setSelectedCapability] =
    useState<Capability>(firstCapability);
  const [probeResult, setProbeResult] = useState<DiagnosticCheck | null>(null);

  useEffect(() => {
    if (open && firstCapability) {
      setSelectedCapability(firstCapability);
      setProbeResult(null);
    }
  }, [open, firstCapability]);

  const handleRunProbe = async () => {
    try {
      const res = await probeMutation.mutateAsync({
        providerId: model.id,
        capability: selectedCapability,
      });
      setProbeResult(res);
      if (res.outcome === "ok") {
        toast.success(`Mô hình đáp ứng tốt! (${res.latency_ms ?? 0}ms)`);
      } else {
        toast.error(`Kiểm tra mô hình không thành công: ${res.detail}`);
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Thử nghiệm mô hình thất bại";
      toast.error(msg);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FlaskConical className="size-5 text-primary" />
            <span>Thử nghiệm khả năng suy luận của mô hình</span>
          </DialogTitle>
          <DialogDescription>
            Gửi yêu cầu thử nghiệm thực tế (active probe) tới mô hình{" "}
            <span className="font-semibold text-foreground font-mono">
              {model.model_name}
            </span>{" "}
            để xác minh tính sẵn sàng và đo độ trễ mạng.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-3">
          {/* Model info card */}
          <div className="rounded-lg border bg-muted/30 p-3 space-y-1.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Tên mô hình:</span>
              <span className="font-mono font-semibold text-foreground">
                {model.model_name}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Endpoint:</span>
              <span className="font-mono text-muted-foreground truncate max-w-[280px]">
                {model.base_url}
              </span>
            </div>
            {model.token_limits?.context_window_tokens && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Ngữ cảnh:</span>
                <span className="font-mono">
                  {model.token_limits.context_window_tokens.toLocaleString()}{" "}
                  tokens
                </span>
              </div>
            )}
          </div>

          <Field>
            <FieldLabel htmlFor="probe-cap">Năng lực cần kiểm tra *</FieldLabel>
            <Select
              value={selectedCapability}
              onValueChange={(val) => setSelectedCapability(val as Capability)}
            >
              <SelectTrigger id="probe-cap">
                <SelectValue placeholder="Chọn năng lực" />
              </SelectTrigger>
              <SelectContent>
                {supportedCapabilities.map((cap) => (
                  <SelectItem key={cap} value={cap}>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">
                        {CAPABILITY_LABELS[cap].label}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FieldDescription>
              Backend sẽ gửi một payload kiểm tra mẫu phù hợp với năng lực đã
              chọn và ghi nhận lịch sử chẩn đoán.
            </FieldDescription>
          </Field>

          {/* Trigger button */}
          <Button
            type="button"
            className="w-full gap-2"
            disabled={probeMutation.isPending}
            onClick={handleRunProbe}
          >
            {probeMutation.isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                <span>Đang gửi prompt thử nghiệm tới mô hình...</span>
              </>
            ) : (
              <>
                <Sparkles className="size-4" />
                <span>Bắt đầu thử nghiệm</span>
              </>
            )}
          </Button>

          {/* Probe result */}
          {probeResult && (
            <div className="pt-2">
              <Alert
                variant={
                  probeResult.outcome === "ok" ? "success" : "destructive"
                }
              >
                {probeResult.outcome === "ok" ? (
                  <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <AlertCircle className="size-4" />
                )}
                <AlertTitle className="flex items-center justify-between text-sm font-semibold">
                  <span>
                    {probeResult.outcome === "ok"
                      ? "Phản hồi hợp lệ (Sẵn sàng)"
                      : "Thử nghiệm thất bại"}
                  </span>
                  {probeResult.latency_ms !== null &&
                    probeResult.latency_ms !== undefined && (
                      <Badge
                        variant="outline"
                        className="text-[11px] gap-1 font-mono"
                      >
                        <Clock className="size-3" />
                        {probeResult.latency_ms} ms
                      </Badge>
                    )}
                </AlertTitle>
                <AlertDescription className="text-xs mt-1">
                  {probeResult.detail}
                </AlertDescription>
              </Alert>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Đóng
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
