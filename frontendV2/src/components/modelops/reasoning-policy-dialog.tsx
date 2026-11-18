import { Brain } from "lucide-react";
import { useId, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/api/client";
import {
  useProviderReasoningQuery,
  useSetProviderReasoningMutation,
} from "@/api/modelops/queries";
import type {
  ModelProvider,
  ProviderReasoning,
  ReasoningLevel,
  ReasoningPolicy,
  ReasoningStatus,
  ReasoningTrace,
} from "@/api/modelops/types";
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
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";

const LEVEL_LABEL: Record<ReasoningLevel, string> = {
  off: "Tắt",
  low: "Thấp",
};

const STATUS_LABEL: Record<ReasoningStatus, string> = {
  not_configured: "Chưa khai báo",
  server_default: "Theo máy chủ",
  unverified: "Chưa xác minh",
  active: "Đang áp dụng",
};

const REASON_LABEL: Record<string, string> = {
  provider_keeps_server_default: "giữ mặc định máy chủ",
  capability_not_verified: "tham số chưa được xác minh",
  level_not_set: "chưa chọn mức",
};

function declaredLevels(policy: ReasoningPolicy | null): ReasoningLevel[] {
  if (!policy) return [];
  return [
    ...(policy.off_value !== null ? (["off"] as const) : []),
    ...(policy.low_value !== null ? (["low"] as const) : []),
  ];
}

function effectiveLabel(trace: ReasoningTrace): string {
  if (trace.applied && trace.level) return LEVEL_LABEL[trace.level];
  const reason = trace.reason
    ? (REASON_LABEL[trace.reason] ?? trace.reason)
    : null;
  return reason ? `Theo máy chủ (${reason})` : "Theo máy chủ";
}

export function ReasoningPolicyDialog({
  open,
  onOpenChange,
  connectionId,
  model,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connectionId: string;
  model: ModelProvider | null;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[95vw] max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Brain className="size-5 text-primary" />
            Mức suy nghĩ
          </DialogTitle>
          <DialogDescription>
            {model
              ? `${model.model_name} · áp dụng cho mọi tác vụ dùng model này.`
              : ""}
          </DialogDescription>
        </DialogHeader>
        {model && (
          <ReasoningPolicyForm
            key={model.id}
            connectionId={connectionId}
            model={model}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function ReasoningPolicyForm({
  connectionId,
  model,
}: {
  connectionId: string;
  model: ModelProvider;
}) {
  const fieldId = useId();
  const query = useProviderReasoningQuery(model.id);
  const update = useSetProviderReasoningMutation(model.id, connectionId);
  const [draft, setDraft] = useState<{
    base: ProviderReasoning;
    level: ReasoningLevel;
  } | null>(null);

  if (query.isPending) return <Skeleton className="h-48 w-full" />;
  if (query.isError || !query.data) {
    return (
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <p role="alert">Không tải được mức suy nghĩ của model.</p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void query.refetch()}
        >
          Thử lại
        </Button>
      </div>
    );
  }

  const data = query.data;
  const policy = data.policy;
  const hasContract =
    policy !== null &&
    policy.mode !== "server_default" &&
    policy.parameter !== null;
  const canTune = hasContract && policy?.verified === true;
  const levels = declaredLevels(policy);
  const canTurnOn = levels.includes("low");
  const storedLevel = policy?.level ?? "off";
  const level = draft?.base === data ? draft.level : storedLevel;
  const isDirty = level !== storedLevel;
  const switchId = `${fieldId}-thinking`;

  return (
    <>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <Badge variant={data.status === "active" ? "success" : "secondary"}>
            {STATUS_LABEL[data.status]}
          </Badge>
          {hasContract && policy && (
            <span className="font-mono text-muted-foreground">
              {policy.parameter}
            </span>
          )}
          <span className="text-muted-foreground">
            {policy?.verified
              ? "Tham số đã được xác minh với endpoint này."
              : "Chưa xác minh tham số với endpoint này."}
          </span>
        </div>

        {!hasContract && (
          <Alert>
            <AlertTitle>Chưa có hợp đồng tham số</AlertTitle>
            <AlertDescription>
              Endpoint này chưa khai báo tham số suy nghĩ đã xác minh. Hệ thống
              giữ mặc định của máy chủ và không tự đoán tên tham số.
            </AlertDescription>
          </Alert>
        )}

        <div className="space-y-3 border-t border-border pt-3">
          <div className="flex items-center justify-between gap-3">
            <div className="space-y-0.5">
              <Label htmlFor={switchId}>Suy nghĩ</Label>
              <p className="text-xs text-muted-foreground">
                Bật để gửi tham số suy nghĩ, tắt để gửi giá trị tắt.
              </p>
            </div>
            <Switch
              id={switchId}
              checked={level === "low"}
              disabled={!canTune || update.isPending || !canTurnOn}
              onCheckedChange={(checked) =>
                setDraft({ base: data, level: checked ? "low" : "off" })
              }
            />
          </div>

          <p className="text-xs text-muted-foreground">
            Hiệu lực hiện tại:{" "}
            <span className="text-foreground">
              {effectiveLabel(data.effective)}
            </span>
          </p>
          {canTune && !canTurnOn && (
            <p className="text-xs text-muted-foreground">
              Endpoint chỉ khai báo giá trị tắt cho tham số này.
            </p>
          )}
          {!canTune && hasContract && (
            <p className="text-xs text-muted-foreground">
              Chỉ chỉnh được sau khi tham số đã được xác minh với endpoint này.
            </p>
          )}
        </div>
      </div>
      <DialogFooter>
        <Button
          type="button"
          variant="outline"
          disabled={update.isPending}
          onClick={() => setDraft(null)}
        >
          Hoàn tác
        </Button>
        <Button
          type="button"
          disabled={!canTune || !isDirty || update.isPending}
          onClick={() => {
            if (policy === null) return;
            update.mutate(
              { ...policy, level },
              {
                onSuccess: () => {
                  setDraft(null);
                  toast.success("Đã lưu mức suy nghĩ cho model.");
                },
                onError: (error) =>
                  toast.error(
                    error instanceof ApiProblemError
                      ? error.message
                      : "Chưa lưu được mức suy nghĩ.",
                  ),
              },
            );
          }}
        >
          {update.isPending ? "Đang lưu…" : "Lưu thay đổi"}
        </Button>
      </DialogFooter>
    </>
  );
}
