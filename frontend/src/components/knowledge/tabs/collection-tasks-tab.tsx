import {
  CheckCircle2,
  CircleAlert,
  RefreshCw,
  RotateCcw,
  Scan,
  Search,
  Terminal,
  Trash2,
  Upload,
  X,
  Zap,
} from "lucide-react";
import { useMemo, useState } from "react";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
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

function formatTaskTime(dateStr?: string): { formatted: string; full: string } {
  if (!dateStr) return { formatted: "—", full: "—" };
  try {
    const d = new Date(dateStr);
    if (Number.isNaN(d.getTime())) return { formatted: dateStr, full: dateStr };
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, "0");
    const minutes = String(d.getMinutes()).padStart(2, "0");
    const seconds = String(d.getSeconds()).padStart(2, "0");
    return {
      formatted: `${hours}:${minutes}:${seconds} • ${day}/${month}/${year}`,
      full: d.toLocaleString("vi-VN"),
    };
  } catch {
    return { formatted: dateStr, full: dateStr };
  }
}

function formatDuration(seconds?: number): string {
  if (seconds === undefined || seconds === null) return "—";
  if (seconds <= 0) return "< 1s";
  if (seconds < 1) return `${seconds.toFixed(1)}s`;
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

function getCategoryInfo(category?: string) {
  switch (category) {
    case "ocr":
      return {
        label: "Bóc tách OCR",
        icon: Scan,
        badgeClass:
          "bg-purple-500/10 text-purple-600 border-purple-500/30 dark:text-purple-400",
        iconClass: "bg-purple-500/10 text-purple-600 dark:text-purple-400",
      };
    case "reindex":
      return {
        label: "Tái lập chỉ mục",
        icon: Zap,
        badgeClass:
          "bg-amber-500/10 text-amber-600 border-amber-500/30 dark:text-amber-400",
        iconClass: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
      };
    default:
      return {
        label: "Nạp tài liệu",
        icon: Upload,
        badgeClass: "bg-primary/10 text-primary border-primary/30",
        iconClass: "bg-primary/10 text-primary",
      };
  }
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
  // Pagination state
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Reset to page 1 on filter or search change
  const filterKey = `${searchQuery}_${statusFilter}`;
  const [prevFilterKey, setPrevFilterKey] = useState(filterKey);
  if (filterKey !== prevFilterKey) {
    setPrevFilterKey(filterKey);
    setPage(1);
  }

  const totalTasks = tasks.length;
  const pageCount = Math.max(1, Math.ceil(totalTasks / pageSize));
  const validPage = Math.min(page, pageCount);

  const paginatedTasks = useMemo(() => {
    const start = (validPage - 1) * pageSize;
    return tasks.slice(start, start + pageSize);
  }, [tasks, validPage, pageSize]);

  return (
    <div className="space-y-4">
      {/* Header Banner */}
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
      <div className="flex flex-col sm:flex-row items-center justify-between gap-2.5">
        <div className="relative w-full sm:w-80 shrink-0">
          <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Tìm tác vụ, tệp, worker..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="h-8 pl-8 pr-8 text-xs w-full"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => onSearchChange("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground text-xs"
              title="Xóa từ khóa tìm kiếm"
            >
              <X className="size-3" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto justify-start sm:justify-end">
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

          {(searchQuery || statusFilter !== "all") && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                onSearchChange("");
                onStatusFilterChange("all");
              }}
              className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground shrink-0 gap-1"
              title="Đặt lại bộ lọc"
            >
              <RotateCcw className="size-3" />
              <span className="hidden sm:inline">Đặt lại</span>
            </Button>
          )}
        </div>
      </div>

      {/* 1. Mobile Tasks Card View (< 640px) */}
      <div className="sm:hidden space-y-2.5">
        {paginatedTasks.length === 0 ? (
          <div className="p-8 text-center bg-card rounded-lg border border-border text-xs text-muted-foreground">
            Không có tác vụ nền nào đang chờ hoặc đã xử lý.
          </div>
        ) : (
          paginatedTasks.map((t) => {
            const cat = getCategoryInfo(t.category);
            const CatIcon = cat.icon;
            const time = formatTaskTime(t.created_at);
            const duration = formatDuration(t.duration_seconds);

            return (
              <div
                key={t.id}
                className="p-3.5 rounded-lg border border-border bg-card space-y-2.5 shadow-2xs"
              >
                {/* Top row: Title + Status */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2.5 min-w-0">
                    <div
                      className={`flex size-7 items-center justify-center rounded shrink-0 mt-0.5 ${cat.iconClass}`}
                    >
                      <CatIcon className="size-3.5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-xs text-foreground truncate">
                        {t.task_name}
                      </p>
                      <p
                        className="text-[11px] text-muted-foreground font-mono truncate mt-0.5"
                        title={t.source_file}
                      >
                        {t.source_file || "Hệ thống"}
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
                    <span>
                      {TASK_STATUS_BADGE[t.status]?.label || t.status}
                    </span>
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
                    <Badge
                      variant="outline"
                      className={`text-[10px] px-1.5 py-0 ${cat.badgeClass}`}
                    >
                      {cat.label}
                    </Badge>
                    <span>•</span>
                    <span className="font-mono">{duration}</span>
                    <span>•</span>
                    <span className="font-mono text-[10px]" title={time.full}>
                      {time.formatted}
                    </span>
                  </div>

                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onViewLog(t)}
                      className="size-7 text-muted-foreground hover:text-foreground"
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
                      title="Xóa tác vụ"
                      aria-label="Xóa tác vụ"
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </div>
              </div>
            );
          })
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
            {paginatedTasks.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="h-32 text-center text-xs text-muted-foreground"
                >
                  Không có tác vụ nền nào đang chờ hoặc đã xử lý.
                </TableCell>
              </TableRow>
            ) : (
              paginatedTasks.map((t) => {
                const cat = getCategoryInfo(t.category);
                const CatIcon = cat.icon;
                const time = formatTaskTime(t.created_at);
                const duration = formatDuration(t.duration_seconds);

                return (
                  <TableRow
                    key={t.id}
                    className="hover:bg-muted/30 transition-colors"
                  >
                    <TableCell>
                      <div className="flex items-start gap-3">
                        <div
                          className={`flex size-8 items-center justify-center rounded shrink-0 mt-0.5 ${cat.iconClass}`}
                        >
                          <CatIcon className="size-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="font-semibold text-xs text-foreground truncate">
                            {t.task_name}
                          </p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono mt-0.5">
                            <span
                              className="truncate max-w-[260px]"
                              title={t.source_file}
                            >
                              {t.source_file || "Hệ thống"}
                            </span>
                            <span>•</span>
                            <span>Worker: {t.worker_name || "arq"}</span>
                            <span>•</span>
                            <span>{duration}</span>
                          </div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={`text-xs ${cat.badgeClass}`}
                      >
                        {cat.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="w-28 space-y-1">
                        <div className="flex justify-between text-xs font-mono">
                          <span className="text-primary font-bold">
                            {t.progress_percent}%
                          </span>
                          <span className="text-muted-foreground text-[11px]">
                            {t.progress_percent === 100 ? "Xong" : "Đang chạy"}
                          </span>
                        </div>
                        <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary rounded-full transition-all"
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
                      <span
                        className="text-xs text-muted-foreground font-mono whitespace-nowrap"
                        title={time.full}
                      >
                        {time.formatted}
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
                        {(t.status === "failed" ||
                          t.status === "cancelled") && (
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
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* 3. Pagination Controls */}
      {totalTasks > 0 && (
        <DataTablePagination
          page={validPage}
          pageSize={pageSize}
          pageCount={pageCount}
          total={totalTasks}
          onPageChange={setPage}
          onPageSizeChange={(newSize) => {
            setPageSize(newSize);
            setPage(1);
          }}
          className="pt-1 px-0.5"
        />
      )}
    </div>
  );
}
