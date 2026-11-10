import { useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileText,
  Loader2,
  StopCircle,
  X,
} from "lucide-react";
import { useEffect, useMemo } from "react";
import { toast } from "sonner";
import { knowledgeKeys } from "@/api/knowledge/queries";
import {
  useCancelPreparationIntentMutation,
  usePreparationIntentQuery,
} from "@/api/preparation";
import { usePreparationProgressQuery } from "@/api/preparation/progress";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  type BackgroundTask,
  useBackgroundTasksStore,
} from "@/lib/background-tasks-store";
import { resolveDocumentTaskProgress } from "@/lib/document-task-progress";
import { useUiStore } from "@/lib/ui-store";
import { cn } from "@/lib/utils";

const activeStatuses = new Set(["queued", "waiting_ocr", "compiling"]);

function TaskItemRow({ task }: { task: BackgroundTask }) {
  const queryClient = useQueryClient();
  const updateTaskStatus = useBackgroundTasksStore((s) => s.updateTaskStatus);
  const dismissTask = useBackgroundTasksStore((s) => s.dismissTask);
  const isRunning = activeStatuses.has(task.status);

  const { data: intentData, isError } = usePreparationIntentQuery(
    task.workspaceId,
    task.collectionId,
    task.id,
    { enabled: isRunning },
  );

  const progressQuery = usePreparationProgressQuery(intentData);
  const disconnected = isError || (isRunning && progressQuery.isError);

  const cancelMutation = useCancelPreparationIntentMutation(
    task.workspaceId,
    task.collectionId,
  );

  // Synchronize server state with store and trigger once-only completion toast
  useEffect(() => {
    if (!intentData) return;

    updateTaskStatus(task.id, {
      status: intentData.status,
      step: intentData.step || undefined,
      errorCode: intentData.error_code,
    });

    if (intentData.status === "ready" && task.status !== "ready") {
      toast.success(`Tài liệu "${task.sourceTitle}" đã chuẩn bị xong.`, {
        id: `preparation-ready:${task.workspaceId}:${task.id}`,
        description: "Mở bản nháp để kiểm tra và duyệt.",
      });

      void queryClient.invalidateQueries({
        queryKey: [
          ...knowledgeKeys.all,
          "sources",
          task.workspaceId,
          task.collectionId,
        ],
      });
      void queryClient.invalidateQueries({
        queryKey: knowledgeKeys.sourceSummary(
          task.workspaceId,
          task.collectionId,
          task.sourceId,
        ),
      });
    }
  }, [
    intentData,
    task.id,
    task.sourceTitle,
    task.status,
    task.workspaceId,
    task.collectionId,
    task.sourceId,
    updateTaskStatus,
    queryClient,
  ]);

  const handleCancel = async () => {
    try {
      await cancelMutation.mutateAsync(task.id);
      toast.info(`Đã gửi yêu cầu dừng "${task.sourceTitle}".`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Không thể dừng tác vụ");
    }
  };

  const presentation = useMemo(() => {
    return resolveDocumentTaskProgress({
      status: intentData?.status || task.status,
      step: intentData?.step || task.step,
      errorCode: intentData?.error_code || task.errorCode,
      ocrProgress: progressQuery.data?.ocrProgress,
      compilationProgress: progressQuery.data?.compilationProgress,
    });
  }, [intentData, task.status, task.step, task.errorCode, progressQuery.data]);

  return (
    <div
      hidden={task.isDismissed}
      className="py-2.5 px-3.5 hover:bg-muted/20 transition-colors text-xs space-y-1.5"
    >
      {/* Row 1: Left (Icon + Title) & Right (Status/%/CTA + Close) */}
      <div className="flex items-center justify-between gap-2 min-h-6">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* Status Icon */}
          <div className="shrink-0 flex items-center justify-center">
            {isRunning ? (
              <Loader2 className="size-3.5 animate-spin text-primary" />
            ) : presentation.isOverallComplete ? (
              <CheckCircle2 className="size-3.5 text-emerald-600 dark:text-emerald-400" />
            ) : presentation.isFailed ? (
              <AlertCircle className="size-3.5 text-destructive" />
            ) : presentation.isUncertain ? (
              <AlertCircle className="size-3.5 text-amber-500" />
            ) : presentation.isCancelled ? (
              <StopCircle className="size-3.5 text-muted-foreground" />
            ) : (
              <FileText className="size-3.5 text-muted-foreground" />
            )}
          </div>

          {/* Document Title */}
          <p
            className="font-medium text-foreground truncate max-w-[175px] sm:max-w-[200px] leading-tight"
            title={task.sourceTitle || task.fileName}
          >
            {task.sourceTitle || task.fileName}
          </p>
        </div>

        {/* Action Controls & Percentage */}
        <div className="flex items-center gap-1.5 shrink-0">
          {/* When running: % and Stop button */}
          {isRunning && (
            <>
              {presentation.unifiedPercent !== null && (
                <span className="tabular-nums text-xs font-semibold text-primary">
                  {presentation.unifiedPercent}%
                </span>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCancel}
                disabled={cancelMutation.isPending}
                className="h-5 px-1.5 text-[11px] text-muted-foreground hover:text-destructive gap-1"
                aria-label={`Dừng xử lý ${task.sourceTitle}`}
              >
                <StopCircle className="size-3" />
                <span>Dừng</span>
              </Button>
            </>
          )}

          {/* When Complete: Open Draft Link */}
          {presentation.isOverallComplete && (
            <Link
              className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:underline inline-flex items-center gap-1"
              to="/knowledge/$sourceId"
              params={{ sourceId: task.sourceId }}
              search={{ collectionId: task.collectionId }}
            >
              <span>Mở bản nháp</span>
              <ArrowRight className="size-3" />
            </Link>
          )}

          {/* When Terminal Error/Cancelled/Uncertain: Short Badge */}
          {!isRunning && !presentation.isOverallComplete && (
            <span
              className={cn(
                "text-[10px] font-medium px-1.5 py-0.5 rounded",
                presentation.isFailed && "bg-destructive/10 text-destructive",
                presentation.isCancelled && "bg-muted text-muted-foreground",
                presentation.isUncertain &&
                  "bg-amber-500/10 text-amber-600 dark:text-amber-400",
              )}
            >
              {presentation.statusLabel}
            </span>
          )}

          {/* Dismiss button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => dismissTask(task.id)}
            className="size-5 p-0 text-muted-foreground hover:text-foreground rounded-full"
            aria-label={`Ẩn tác vụ ${task.sourceTitle}`}
          >
            <X className="size-3" />
          </Button>
        </div>
      </div>

      {/* Row 2: Progress track & subtitle */}
      <div className="space-y-1">
        <Progress
          value={
            presentation.isOverallComplete
              ? 100
              : presentation.isIndeterminate
                ? undefined
                : (presentation.unifiedPercent ?? 0)
          }
          aria-label="Tiến độ xử lý tài liệu"
          className={cn(
            "h-1 w-full",
            presentation.isOverallComplete &&
              "[&>div]:bg-emerald-600 dark:[&>div]:bg-emerald-500",
            presentation.isIndeterminate && "animate-pulse",
          )}
        />

        <div className="flex items-center justify-between text-[11px] text-muted-foreground leading-tight">
          <span className="truncate">
            {disconnected
              ? "Mất kết nối theo dõi. Đang kết nối lại…"
              : isRunning
                ? presentation.stepLabel
                : presentation.isOverallComplete
                  ? "Đã sẵn sàng duyệt và hỏi đáp"
                  : presentation.detail}
          </span>
        </div>
      </div>
    </div>
  );
}

export function BackgroundTasksBar() {
  const tasks = useBackgroundTasksStore((s) => s.tasks);
  const isExpanded = useBackgroundTasksStore((s) => s.isExpanded);
  const toggleExpanded = useBackgroundTasksStore((s) => s.toggleExpanded);
  const clearCompleted = useBackgroundTasksStore((s) => s.clearCompleted);
  const workspaceId = useUiStore((s) => s.activeWorkspaceId);

  const scopedTasks = tasks.filter(
    (t) => t.workspaceId === workspaceId && t.kind === "preparation",
  );
  const visibleTasks = scopedTasks.filter((t) => !t.isDismissed);
  const activeCount = visibleTasks.filter((t) =>
    activeStatuses.has(t.status),
  ).length;
  const completedCount = visibleTasks.filter(
    (t) => t.status === "ready",
  ).length;

  // Keep monitors mounted while collapsed/hidden: hiding the panel never stops a job.
  return (
    <section
      hidden={visibleTasks.length === 0}
      aria-label="Tác vụ xử lý tài liệu"
      className="fixed bottom-4 right-4 z-40 w-96 max-w-[calc(100vw-2rem)] rounded-xl border border-border bg-card text-foreground shadow-xl overflow-hidden transition-all duration-200"
    >
      <div className="flex items-center justify-between px-3.5 py-2 border-b border-border/70 bg-card select-none">
        <button
          type="button"
          onClick={toggleExpanded}
          aria-expanded={isExpanded}
          aria-label={
            isExpanded ? "Thu gọn bảng tác vụ" : "Mở rộng bảng tác vụ"
          }
          className="flex items-center gap-2 text-xs font-semibold text-foreground hover:opacity-80 transition-opacity"
        >
          <span>Tác vụ nền ({visibleTasks.length})</span>
          {activeCount > 0 ? (
            <span className="inline-flex items-center gap-1 text-[10px] font-medium text-primary bg-primary/10 px-1.5 py-0.5 rounded-full">
              <span className="size-1.5 rounded-full bg-primary animate-pulse" />
              {activeCount} đang chạy
            </span>
          ) : completedCount > 0 ? (
            <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded-full">
              {completedCount} đã xong
            </span>
          ) : null}
        </button>

        <div className="flex items-center gap-1">
          {completedCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearCompleted}
              className="h-6 px-1.5 text-[11px] text-muted-foreground hover:text-foreground"
            >
              Dọn xong
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleExpanded}
            className="size-6 p-0 text-muted-foreground hover:text-foreground"
            aria-label={isExpanded ? "Thu gọn" : "Mở rộng"}
          >
            {isExpanded ? (
              <ChevronDown className="size-3.5" />
            ) : (
              <ChevronUp className="size-3.5" />
            )}
          </Button>
        </div>
      </div>

      <div
        hidden={!isExpanded}
        className="divide-y divide-border/60 max-h-[min(18rem,40dvh)] overflow-y-auto"
      >
        {scopedTasks.map((task) => (
          <TaskItemRow key={task.id} task={task} />
        ))}
      </div>
    </section>
  );
}
