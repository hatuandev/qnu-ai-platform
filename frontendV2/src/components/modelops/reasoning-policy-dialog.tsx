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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

const TASKS = [
  {
    key: "compiler",
    label: "Biên soạn",
    hint: "Áp dụng khi biên dịch văn bản.",
  },
  {
    key: "compiler_review",
    label: "Rà soát",
    hint: "Áp dụng khi rà soát bản biên soạn.",
  },
] as const;

type TaskKey = (typeof TASKS)[number]["key"];
type TaskLevel = ReasoningLevel | "server";
type Levels = Record<TaskKey, TaskLevel>;

const LEVEL_LABEL: Record<TaskLevel, string> = {
  server: "Theo máy chủ",
  low: "Thấp",
  off: "Tắt",
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
  task_not_configured: "tác vụ chưa khai báo mức",
};

function declaredLevels(policy: ReasoningPolicy | null): Levels {
  const tasks = policy?.tasks ?? {};
  const find = (task: TaskKey): TaskLevel => {
    if (tasks.off?.includes(task)) return "off";
    if (tasks.low?.includes(task)) return "low";
    return "server";
  };
  return {
    compiler: find("compiler"),
    compiler_review: find("compiler_review"),
  };
}

function withTaskLevels(
  policy: ReasoningPolicy,
  levels: Levels,
): ReasoningPolicy {
  const tasks: Partial<Record<ReasoningLevel, string[]>> = {};
  for (const level of ["off", "low"] as const) {
    const kept = (policy.tasks?.[level] ?? []).filter(
      (task) => !TASKS.some((item) => item.key === task),
    );
    if (kept.length > 0) tasks[level] = kept;
  }
  for (const task of TASKS) {
    const level = levels[task.key];
    if (level === "server") continue;
    tasks[level] = [...(tasks[level] ?? []), task.key];
  }
  return { ...policy, tasks };
}

function effectiveLabel(trace: ReasoningTrace | undefined): string {
  if (!trace) return "Chưa có";
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
              ? `${model.model_name} · chỉ áp dụng cho biên soạn và rà soát của đúng endpoint này.`
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
    levels: Levels;
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
  const serverLevels = declaredLevels(policy);
  const levels = draft?.base === data ? draft.levels : serverLevels;
  const isDirty = TASKS.some(
    (task) => levels[task.key] !== serverLevels[task.key],
  );

  const setLevel = (task: TaskKey, level: TaskLevel) => {
    setDraft({ base: data, levels: { ...levels, [task]: level } });
  };

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

        {TASKS.map((task) => {
          const htmlId = `${fieldId}-${task.key}`;
          return (
            <div
              key={task.key}
              className="space-y-2 border-t border-border pt-3"
            >
              <div className="flex flex-wrap items-end justify-between gap-2">
                <div className="space-y-0.5">
                  <Label htmlFor={htmlId}>{task.label}</Label>
                  <p className="text-xs text-muted-foreground">{task.hint}</p>
                </div>
                <Select
                  value={levels[task.key]}
                  disabled={update.isPending}
                  onValueChange={(value) =>
                    setLevel(task.key, value as TaskLevel)
                  }
                >
                  <SelectTrigger id={htmlId} className="w-40 shrink-0">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="server">Theo máy chủ</SelectItem>
                    <SelectItem value="low" disabled={!canTune}>
                      Thấp
                    </SelectItem>
                    <SelectItem value="off" disabled={!canTune}>
                      Tắt
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <p className="text-xs text-muted-foreground">
                Đã khai báo:{" "}
                <span className="text-foreground">
                  {LEVEL_LABEL[levels[task.key]]}
                </span>
                {" · "}Hiệu lực:{" "}
                <span className="text-foreground">
                  {effectiveLabel(data.effective[task.key])}
                </span>
              </p>
            </div>
          );
        })}

        {!canTune && hasContract && (
          <p className="text-xs text-muted-foreground">
            Chỉ chọn được Thấp hoặc Tắt sau khi tham số đã được xác minh với
            endpoint này.
          </p>
        )}
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
          disabled={!isDirty || update.isPending || policy === null}
          onClick={() => {
            if (policy === null) return;
            update.mutate(withTaskLevels(policy, levels), {
              onSuccess: () => {
                setDraft(null);
                toast.success("Đã lưu mức suy nghĩ cho biên soạn và rà soát.");
              },
              onError: (error) =>
                toast.error(
                  error instanceof ApiProblemError
                    ? error.message
                    : "Chưa lưu được mức suy nghĩ.",
                ),
            });
          }}
        >
          {update.isPending ? "Đang lưu…" : "Lưu thay đổi"}
        </Button>
      </DialogFooter>
    </>
  );
}
