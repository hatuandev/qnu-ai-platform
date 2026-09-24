import {
  CheckCircle2,
  CircleAlert,
  RefreshCw,
  RotateCcw,
  Search,
  Terminal,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { TASK_STATUS_BADGE } from "@/components/knowledge/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { IngestionTask } from "@/types";

interface CollectionTasksTabProps {
  tasks: IngestionTask[];
  totalTasksCount: number;
  searchQuery: string;
  onSearchChange: (val: string) => void;
  statusFilter: string;
  onStatusFilterChange: (val: string) => void;
  taskActionId: string | null;
  isCleaningTasks: boolean;
  canCleanup: boolean;
  taskSuccessMessage: string | null;
  onRefresh: () => void;
  onOpenConfirmCleanup: () => void;
  onViewLog: (task: IngestionTask) => void;
  onTaskAction: (taskId: string, action: "retry" | "cancel") => void;
  onDeleteTask: (task: IngestionTask) => void;
}

export function CollectionTasksTab({
  tasks,
  totalTasksCount,
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  taskActionId,
  isCleaningTasks,
  canCleanup,
  taskSuccessMessage,
  onRefresh,
  onOpenConfirmCleanup,
  onViewLog,
  onTaskAction,
  onDeleteTask,
}: CollectionTasksTabProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card p-3.5 sm:p-4 rounded-lg border border-border">
        <div>
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            Hàng Đợi & Lịch Sử Tác Vụ Ngầm ({totalTasksCount})
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
            Giám sát thời gian thực quá trình Bóc tách (Ingestion), OCR tài liệu
            và Tái lập chỉ mục (Reindex) của kho này.
          </p>
        </div>
        <div className="grid grid-cols-2 sm:flex sm:items-center gap-2 w-full sm:w-auto shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenConfirmCleanup}
            disabled={isCleaningTasks || !canCleanup}
            className="h-8 text-xs text-muted-foreground hover:text-foreground gap-1.5"
            title="Dọn dẹp các tác vụ đã hoàn tất, thất bại hoặc đã hủy"
          >
            <Trash2 className="size-3.5" />
            <span>{isCleaningTasks ? "Đang dọn..." : "Dọn tác vụ cũ"}</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            className="h-8 text-xs gap-1.5"
          >
            <RefreshCw className="size-3.5" />
            <span>Làm mới</span>
          </Button>
        </div>
      </div>

      {taskSuccessMessage && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-success/10 border border-success/30 text-xs text-success">
          <CheckCircle2 className="size-4 shrink-0" />
          <span>{taskSuccessMessage}</span>
        </div>
      )}

      {/* Filter Bar for Tasks */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-2.5 bg-card p-3 rounded-lg border border-border shadow-2xs">
        <div className="flex items-center gap-2 w-full sm:w-80">
          <Search className="size-4 text-muted-foreground shrink-0" />
          <Input
            placeholder="Tìm tác vụ, tệp, worker..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="h-8 text-xs w-full"
          />
        </div>

        <div className="flex items-center justify-between sm:justify-end gap-2 w-full sm:w-auto">
          <Select value={statusFilter} onValueChange={onStatusFilterChange}>
            <SelectTrigger sizeVariant="sm" className="w-full sm:w-[165px]">
              <SelectValue placeholder="Tất cả trạng thái" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả trạng thái</SelectItem>
              <SelectItem value="completed">Hoàn tất</SelectItem>
              <SelectItem value="processing">Đang xử lý</SelectItem>
              <SelectItem value="cancelled">Đã hủy</SelectItem>
              <SelectItem value="failed">Thất bại</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-xs text-muted-foreground whitespace-nowrap ml-2">
            Hiển thị <strong className="text-foreground">{tasks.length}</strong>{" "}
            / {totalTasksCount}
          </span>
        </div>
      </div>

      {/* 1. Mobile Tasks Card View (< 640px) */}
      <div className="sm:hidden space-y-2.5">
        {tasks.length === 0 ? (
          <div className="p-8 text-center bg-card rounded-lg border border-border text-xs text-muted-foreground">
            Không có tác vụ nền nào đang chờ hoặc đã xử lý.
          </div>
        ) : (
          tasks.map((t) => (
            <div
              key={t.id}
              className="p-3.5 rounded-lg border border-border bg-card space-y-2.5 shadow-2xs"
            >
              {/* Top row: Title + Status */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2.5 min-w-0">
                  <div className="flex size-7 items-center justify-center rounded bg-primary/10 text-primary shrink-0 mt-0.5">
                    <Upload className="size-3.5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-xs text-foreground truncate">
                      {t.task_name}
                    </p>
                    <p className="text-[11px] text-muted-foreground font-mono truncate mt-0.5">
                      {t.source_file}
                    </p>
                  </div>
                </div>

                <Badge
                  variant="outline"
                  className={`text-[10px] px-1.5 py-0 shrink-0 gap-1 ${
                    TASK_STATUS_BADGE[t.status]?.className ||
                    TASK_STATUS_BADGE.processing.className
                  }`}
                >
                  {t.status === "completed" ? (
                    <CheckCircle2 className="size-2.5" />
                  ) : t.status === "processing" ? (
                    <RefreshCw className="size-2.5 animate-spin" />
                  ) : t.status === "cancelled" ? (
                    <X className="size-2.5" />
                  ) : (
                    <CircleAlert className="size-2.5" />
                  )}
                  <span>{TASK_STATUS_BADGE[t.status]?.label || t.status}</span>
                </Badge>
              </div>

              {/* Progress Bar */}
              <div className="space-y-1 pt-1 border-t border-border/50">
                <div className="flex justify-between text-[11px] font-mono">
                  <span className="text-muted-foreground">Tiến độ</span>
                  <span className="text-primary font-bold">
                    {t.progress_percent}%
                  </span>
                </div>
                <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all"
                    style={{ width: `${t.progress_percent}%` }}
                  />
                </div>
              </div>

              {/* Metadata & Actions */}
              <div className="flex items-center justify-between pt-1 border-t border-border/50 text-[11px] text-muted-foreground">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                    {t.category === "ingestion"
                      ? "Nạp tài liệu"
                      : t.category === "ocr"
                        ? "OCR & Bóc tách"
                        : "Tái lập chỉ mục"}
                  </Badge>
                  <span>•</span>
                  <span>{t.duration_seconds}s</span>
                </div>

                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onViewLog(t)}
                    className="size-7 text-muted-foreground hover:text-foreground"
                    title="Xem nhật ký Terminal"
                  >
                    <Terminal className="size-3.5" />
                  </Button>
                  {(t.status === "failed" || t.status === "cancelled") && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onTaskAction(t.id, "retry")}
                      disabled={taskActionId === t.id}
                      className="size-7 text-primary hover:text-primary/80"
                      title="Chạy lại job"
                    >
                      <RotateCcw className="size-3.5" />
                    </Button>
                  )}
                  {t.status === "processing" && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onTaskAction(t.id, "cancel")}
                      disabled={taskActionId === t.id}
                      className="size-7 text-warning hover:text-warning/80"
                      title="Hủy job"
                    >
                      <X className="size-3.5" />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onDeleteTask(t)}
                    disabled={taskActionId === t.id}
                    className="size-7 text-destructive hover:text-destructive/80"
                    title="Xóa tác vụ"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* 2. Desktop & Tablet Tasks Table (>= 640px) */}
      <div className="hidden sm:block bg-card rounded-lg border border-border overflow-hidden shadow-xs">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40 hover:bg-muted/40 text-xs font-semibold text-muted-foreground uppercase">
              <TableHead>Tác vụ & Tài nguyên mục tiêu</TableHead>
              <TableHead>Phân loại</TableHead>
              <TableHead>Tiến độ</TableHead>
              <TableHead>Trạng thái</TableHead>
              <TableHead>Thời điểm</TableHead>
              <TableHead className="text-right">Thao tác</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="h-32 text-center text-xs text-muted-foreground"
                >
                  Không có tác vụ nền nào đang chờ hoặc đã xử lý.
                </TableCell>
              </TableRow>
            ) : (
              tasks.map((t) => (
                <TableRow
                  key={t.id}
                  className="hover:bg-muted/30 transition-colors"
                >
                  <TableCell>
                    <div className="flex items-start gap-3">
                      <div className="flex size-8 items-center justify-center rounded bg-primary/10 text-primary shrink-0 mt-0.5">
                        <Upload className="size-4" />
                      </div>
                      <div>
                        <p className="font-semibold text-xs text-foreground">
                          {t.task_name}
                        </p>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono mt-0.5">
                          <span>{t.source_file}</span>
                          <span>•</span>
                          <span>Worker: {t.worker_name}</span>
                          <span>•</span>
                          <span>{t.duration_seconds}s</span>
                        </div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-xs font-medium text-foreground">
                      {t.category === "ingestion"
                        ? "Nạp tài liệu"
                        : t.category === "ocr"
                          ? "OCR & Bóc tách"
                          : "Tái lập chỉ mục"}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="w-28 space-y-1">
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-primary font-bold">
                          {t.progress_percent}%
                        </span>
                        <span className="text-muted-foreground">Xong</span>
                      </div>
                      <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${t.progress_percent}%` }}
                        />
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={`text-xs gap-1 ${
                        TASK_STATUS_BADGE[t.status]?.className ||
                        TASK_STATUS_BADGE.processing.className
                      }`}
                    >
                      {t.status === "completed" ? (
                        <CheckCircle2 className="size-3" />
                      ) : t.status === "processing" ? (
                        <RefreshCw className="size-3 animate-spin" />
                      ) : t.status === "cancelled" ? (
                        <X className="size-3" />
                      ) : (
                        <CircleAlert className="size-3" />
                      )}
                      <span>
                        {TASK_STATUS_BADGE[t.status]?.label || t.status}
                      </span>
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="text-xs text-muted-foreground font-mono">
                      {t.created_at}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onViewLog(t)}
                        className="size-7 font-mono text-xs text-muted-foreground hover:text-foreground"
                        title="Xem nhật ký Terminal"
                        aria-label="Xem nhật ký Terminal"
                      >
                        <Terminal className="size-3.5" />
                      </Button>
                      {(t.status === "failed" || t.status === "cancelled") && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => onTaskAction(t.id, "retry")}
                          disabled={taskActionId === t.id}
                          className="size-7 text-primary hover:text-primary/80"
                          title="Chạy lại job"
                          aria-label="Chạy lại job"
                        >
                          <RotateCcw className="size-3.5" />
                        </Button>
                      )}
                      {t.status === "processing" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => onTaskAction(t.id, "cancel")}
                          disabled={taskActionId === t.id}
                          className="size-7 text-warning hover:text-warning/80"
                          title="Hủy job"
                          aria-label="Hủy job"
                        >
                          <X className="size-3.5" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onDeleteTask(t)}
                        disabled={taskActionId === t.id}
                        className="size-7 text-destructive hover:text-destructive/80"
                        title="Xóa tác vụ khỏi danh sách"
                        aria-label="Xóa tác vụ"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
