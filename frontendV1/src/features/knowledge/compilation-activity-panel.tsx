import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  BookOpen,
  CheckCircle2,
  ChevronDown,
  Ellipsis,
  Loader2,
  TriangleAlert,
  X,
} from "lucide-react";
import { useEffect } from "react";
import { ApiProblemError, v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Progress } from "@/components/ui/progress";
import { useCompilationActivity } from "./compilation-activity";
import { compilationKeys } from "./compilation-queries";
import { getCompilationProgress } from "./compilation-requests";
import type {
  CompilationRunResponse,
  CompilationStatus,
} from "./compilation-types";

function isActive(status: CompilationStatus) {
  return status === "queued" || status === "running";
}

function isUnavailable(error: Error | null) {
  return (
    error instanceof ApiProblemError && [401, 403, 404].includes(error.status)
  );
}

const statusLabels: Record<CompilationStatus, string> = {
  queued: "Đang chờ",
  running: "Đang biên soạn",
  completed: "Đã biên soạn · Mở để xem và duyệt",
  failed: "Biên soạn thất bại · Mở để xem lỗi",
  uncertain: "Chưa xác định kết quả · Mở để kiểm tra",
  cancelled: "Đã dừng",
};

export function CompilationActivityPanel() {
  const activity = useCompilationActivity();
  const { isAuthenticated } = useV1Auth();
  if (!isAuthenticated || !activity?.runs.length) return null;
  return (
    <Collapsible
      open={activity.isExpanded}
      onOpenChange={activity.setExpanded}
      aria-label="Tiến độ biên soạn"
      className="fixed right-3 bottom-3 z-40 w-[calc(100%-1.5rem)] max-w-sm rounded-xl border bg-card text-card-foreground shadow-lg sm:right-6 sm:bottom-6"
    >
      <div className="flex items-center gap-1 pr-2">
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="h-12 min-w-0 flex-1 justify-between px-4"
            aria-label={
              activity.isExpanded
                ? "Thu gọn tiến độ biên soạn"
                : "Mở tiến độ biên soạn"
            }
          >
            <span className="flex items-center gap-2">
              <BookOpen className="size-4" />
              Biên soạn ({activity.runs.length})
            </span>
            <ChevronDown
              className={`size-4 ${activity.isExpanded ? "" : "rotate-180"}`}
            />
          </Button>
        </CollapsibleTrigger>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Đóng bảng tiến độ biên soạn"
          title="Đóng bảng · Tác vụ vẫn chạy nền"
          onClick={activity.dismissAll}
        >
          <X className="size-4" />
        </Button>
      </div>
      {/* Keep observers mounted when collapsed; hiding the panel never stops a job. */}
      <CollapsibleContent forceMount hidden={!activity.isExpanded}>
        <ul className="max-h-[min(45vh,360px)] divide-y overflow-y-auto border-t">
          {activity.runs.map((run) => (
            <ActivityRow key={run.id} run={run} />
          ))}
        </ul>
        <p className="border-t px-4 py-2 text-xs text-muted-foreground">
          Bạn có thể chuyển trang. Tác vụ vẫn chạy nền.
        </p>
      </CollapsibleContent>
    </Collapsible>
  );
}

function ActivityRow({ run }: { run: CompilationRunResponse }) {
  const activity = useCompilationActivity();
  const { sessionId } = useV1Auth();
  const progress = useQuery({
    queryKey: [
      ...compilationKeys.run(
        run.workspace_id,
        run.collection_id,
        run.id,
        sessionId,
      ),
      "progress",
    ],
    queryFn: ({ signal }) =>
      getCompilationProgress(
        v1Client,
        run.workspace_id,
        run.collection_id,
        run.id,
        { signal },
      ),
    retry: false,
    refetchInterval: (query) =>
      isUnavailable(query.state.error)
        ? false
        : isActive(query.state.data?.status ?? run.status)
          ? 3000
          : false,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: false,
  });
  const unavailable = isUnavailable(progress.error);
  useEffect(() => {
    if (unavailable) activity?.dismiss(run.id);
  }, [unavailable, activity?.dismiss, run.id]);
  if (unavailable) return null;
  const data = progress.data;
  const status = data?.status ?? run.status;
  const active = isActive(status);
  // Only server-observed completed groups, never a time-based estimate.
  const percent =
    data && data.total > 0
      ? Math.min(100, Math.floor((data.completed / data.total) * 100))
      : null;
  const Icon = active
    ? Loader2
    : status === "completed"
      ? CheckCircle2
      : TriangleAlert;
  return (
    <li className="flex gap-3 px-4 py-3">
      <Icon
        aria-hidden
        className={`mt-1 size-4 shrink-0 ${active ? "animate-spin motion-reduce:animate-none text-primary" : status === "completed" ? "text-success" : "text-warning"}`}
      />
      <div className="min-w-0 flex-1">
        <Link
          to="/workspaces/$workspaceId/collections/$collectionId/compilations/$runId"
          params={{
            workspaceId: run.workspace_id,
            collectionId: run.collection_id,
            runId: run.id,
          }}
          className="block truncate text-sm font-medium hover:underline"
          title={run.topic}
        >
          {run.topic}
        </Link>
        <p
          role="status"
          className={`mt-1 text-xs ${progress.isError ? "text-warning" : "text-muted-foreground"}`}
        >
          {progress.isError
            ? "Mất kết nối cập nhật. Tác vụ chưa được xác nhận dừng."
            : statusLabels[status]}
        </p>
        {active && !progress.isError && data && percent !== null && (
          <div className="mt-2 space-y-1">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>
                {data.completed}/{data.total} nhóm hoàn tất
              </span>
              <span>{percent}%</span>
            </div>
            <Progress value={percent} aria-label={`Tiến độ ${run.topic}`} />
          </div>
        )}
        {!active && data?.latest_output_partial && (
          <p className="mt-1 text-xs text-warning">
            Bản nháp còn phần chưa hoàn tất.
          </p>
        )}
      </div>
      {!active && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={`Thao tác ${run.topic}`}
            >
              <Ellipsis className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={() => activity?.dismiss(run.id)}>
              Ẩn khỏi danh sách
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </li>
  );
}
