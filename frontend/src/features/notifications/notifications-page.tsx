import { useForm } from "@tanstack/react-form";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowRight,
  Banknote,
  Bell,
  Check,
  CheckCheck,
  DoorOpen,
  Eye,
  FileCheck2,
  Inbox,
  LoaderCircle,
  MoreHorizontal,
  RefreshCw,
  RotateCcw,
  Search,
  Send,
  Users,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { ApiError } from "@/app/api/client";
import { AccessDenied } from "@/components/admin/access-denied";
import { Combobox } from "@/components/admin/combobox";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { EmptyState } from "@/components/admin/empty-state";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/admin/field";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  useCreateNotification,
  useMarkNotificationAsRead,
  useMyNotificationsQuery,
  useNotificationsQuery,
} from "@/features/notifications/api";
import {
  type NotificationType,
  notificationTypeLabels as typeLabels,
} from "@/features/notifications/types";
import { useStudentsQuery } from "@/features/students/api";
import { formatDateTime } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

export const notificationTypes = [
  "application_result",
  "check_in",
  "fee_due",
  "room_selection",
  "general",
] as const;

export type NotificationsSearch = {
  q: string | number;
  type?: NotificationType;
  page: number;
  pageSize: number;
};

function formatNotificationDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : formatDateTime(date);
}

function firstError(errors: unknown[]) {
  const error = errors[0];
  return error ? String(error) : undefined;
}

const typeDotColors: Record<NotificationType, string> = {
  application_result: "bg-emerald-500",
  room_selection: "bg-blue-500",
  fee_due: "bg-amber-500",
  check_in: "bg-purple-500",
  general: "bg-muted-foreground/60",
};

const typeBadgeVariants: Record<
  NotificationType,
  "success" | "info" | "warning" | "secondary"
> = {
  application_result: "success",
  room_selection: "info",
  fee_due: "warning",
  check_in: "secondary",
  general: "secondary",
};

export function NotificationsPage({
  search,
  onSearchChange,
}: {
  search: NotificationsSearch;
  onSearchChange: (changes: Partial<NotificationsSearch>) => void;
}) {
  const navigate = useNavigate();
  const { can } = useRbac();
  const canViewPersonal = can("ktx.notifications.view");
  const canManageNotifications = can("ktx.notifications.create");
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());

  const query = useNotificationsQuery(
    {
      search: String(search.q).trim() || undefined,
      type: search.type,
      page: search.page,
      pageSize: search.pageSize,
    },
    { enabled: canManageNotifications },
  );

  const items = query.data?.items ?? [];

  const typeOptions = useMemo(
    () => [
      { value: "all", label: "Tất cả loại thông báo" },
      ...notificationTypes.map((t) => ({ value: t, label: typeLabels[t] })),
    ],
    [],
  );

  const hasFilters = Boolean(String(search.q).trim() || search.type);

  const resetFilters = () => {
    onSearchChange({
      q: "",
      type: undefined,
      page: 1,
    });
  };

  const allSelected =
    items.length > 0 && items.every((item) => selectedIds.has(item.id));
  const someSelected =
    items.some((item) => selectedIds.has(item.id)) && !allSelected;

  const toggleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(items.map((item) => item.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const toggleSelect = (id: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  if (!canViewPersonal) return <AccessDenied />;
  if (!canManageNotifications) return <MyNotificationsPage />;

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        eyebrow="TRAO ĐỔI / QUẢN TRỊ"
        title="Thông báo"
        description="Gửi thông tin quan trọng và theo dõi phạm vi người nhận trong hệ thống."
        actions={
          can("ktx.notifications.create") ? (
            <Button
              size="sm"
              className="gap-1.5 text-xs font-semibold"
              onClick={() => setCreateOpen(true)}
            >
              <Send className="size-3.5" />
              <span>Tạo thông báo</span>
            </Button>
          ) : undefined
        }
      />

      {/* 2. KPI Metrics Summary Cards */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={Bell}
            label="Tổng thông báo"
            value={(query.data?.total ?? items.length).toLocaleString("vi-VN")}
            helper="Tổng số thông báo đã phát hành trong hệ thống"
          />
          <KpiMetric
            icon={Users}
            label="Lượt người nhận"
            value={items
              .reduce((sum, item) => sum + item.recipientCount, 0)
              .toLocaleString("vi-VN")}
            helper="Tổng lượt sinh viên đã tiếp nhận thông báo"
          />
        </CardContent>
      </Card>

      {/* 3. Filter & Search Toolbar */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="relative w-full lg:w-80">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9 text-xs"
            value={String(search.q)}
            placeholder="Tìm theo tiêu đề thông báo..."
            aria-label="Tìm thông báo"
            onChange={(event) =>
              onSearchChange({ q: event.target.value, page: 1 })
            }
          />
        </div>

        <div className="grid grid-cols-2 gap-2 w-full sm:flex sm:flex-wrap sm:items-center lg:w-auto">
          {/* Loại thông báo */}
          <Combobox
            className="w-full col-span-2 sm:col-span-1 sm:w-56 text-xs"
            options={typeOptions}
            value={search.type ?? "all"}
            searchPlaceholder="Tìm loại thông báo..."
            onValueChange={(value) =>
              onSearchChange({
                type: value === "all" ? undefined : (value as NotificationType),
                page: 1,
              })
            }
          />

          {hasFilters && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground col-span-2 sm:col-span-1"
              onClick={resetFilters}
            >
              <RotateCcw className="size-3.5 mr-1" />
              <span>Đặt lại</span>
            </Button>
          )}
        </div>
      </div>

      {/* 4. Data Table */}
      <div className="overflow-x-auto rounded-xl border bg-card shadow-xs">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40 hover:bg-muted/40">
              <TableHead className="w-10 pl-3">
                <div className="flex items-center pl-1">
                  <Checkbox
                    aria-label="Chọn tất cả thông báo"
                    checked={
                      allSelected
                        ? true
                        : someSelected
                          ? "indeterminate"
                          : false
                    }
                    onCheckedChange={(val) => toggleSelectAll(Boolean(val))}
                  />
                </div>
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[280px]">
                Tiêu đề
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[170px]">
                Loại thông báo
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[140px] text-center">
                Người nhận
              </TableHead>
              <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[160px]">
                Ngày tạo
              </TableHead>
              <TableHead className="w-12" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {query.isLoading ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="py-12 text-center text-xs text-muted-foreground"
                >
                  <div className="flex items-center justify-center gap-2">
                    <LoaderCircle className="size-4 animate-spin" />
                    <span>Đang tải danh sách thông báo...</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : query.isError ? (
              <TableRow>
                <TableCell colSpan={6} className="p-8">
                  <EmptyState
                    icon={Bell}
                    title="Không thể tải thông báo"
                    description="Kiểm tra kết nối mạng hoặc thử tải lại sau ít phút."
                    action={{
                      label: "Thử lại",
                      onClick: () => void query.refetch(),
                    }}
                  />
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="p-8">
                  <EmptyState
                    icon={Bell}
                    title={
                      hasFilters
                        ? "Không có thông báo phù hợp"
                        : "Chưa có thông báo nào"
                    }
                    description={
                      hasFilters
                        ? "Không tìm thấy thông báo nào phù hợp với bộ lọc hiện tại."
                        : "Các thông báo được gửi đến sinh viên trong ký túc xá sẽ xuất hiện tại đây."
                    }
                    action={
                      hasFilters
                        ? { label: "Xóa bộ lọc", onClick: resetFilters }
                        : can("ktx.notifications.create")
                          ? {
                              label: "Tạo thông báo đầu tiên",
                              onClick: () => setCreateOpen(true),
                            }
                          : undefined
                    }
                  />
                </TableCell>
              </TableRow>
            ) : (
              items.map((notification) => (
                <TableRow
                  key={notification.id}
                  className="cursor-pointer transition-colors hover:bg-muted/50 whitespace-nowrap"
                  onClick={() =>
                    void navigate({
                      to: "/notifications/$notificationId",
                      params: { notificationId: notification.id },
                    })
                  }
                >
                  <TableCell
                    className="pl-3"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <div className="flex items-center pl-1">
                      <Checkbox
                        aria-label={`Chọn thông báo ${notification.title}`}
                        checked={selectedIds.has(notification.id)}
                        onCheckedChange={(val) =>
                          toggleSelect(notification.id, Boolean(val))
                        }
                      />
                    </div>
                  </TableCell>

                  <TableCell>
                    <span className="font-semibold text-foreground text-sm max-w-md truncate block">
                      {notification.title}
                    </span>
                  </TableCell>

                  <TableCell>
                    <Badge
                      variant={typeBadgeVariants[notification.type]}
                      className="gap-1.5 font-medium px-2.5 py-0.5 text-xs"
                    >
                      <span
                        className={cn(
                          "size-1.5 rounded-full",
                          typeDotColors[notification.type],
                        )}
                      />
                      {typeLabels[notification.type]}
                    </Badge>
                  </TableCell>

                  <TableCell className="text-center">
                    <span className="font-mono font-semibold tabular-nums text-foreground text-sm">
                      {notification.recipientCount}
                    </span>
                    <span className="text-xs text-muted-foreground ml-1">
                      người
                    </span>
                  </TableCell>

                  <TableCell>
                    <span className="text-xs text-muted-foreground font-mono">
                      {formatNotificationDate(notification.createdAt)}
                    </span>
                  </TableCell>

                  <TableCell onClick={(event) => event.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          className="size-8 text-muted-foreground hover:text-foreground"
                          aria-label={`Thao tác với thông báo ${notification.title}`}
                          onClick={(event) => event.stopPropagation()}
                        >
                          <MoreHorizontal className="size-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-48">
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            void navigate({
                              to: "/notifications/$notificationId",
                              params: { notificationId: notification.id },
                            });
                          }}
                        >
                          <Eye className="size-4 mr-2 text-muted-foreground" />
                          Xem chi tiết
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 5. Pagination */}
      {query.data ? (
        <DataTablePagination
          page={query.data.page}
          pageSize={query.data.pageSize}
          pageCount={Math.max(query.data.totalPages, 1)}
          total={query.data.total}
          onPageChange={(page) => onSearchChange({ page })}
          onPageSizeChange={(pageSize) => onSearchChange({ pageSize, page: 1 })}
        />
      ) : null}

      {/* 6. Bulk Actions Floating Bar */}
      <DataTableBulkActions
        selectedCount={selectedIds.size}
        selectedLabel="thông báo"
        onClear={() => setSelectedIds(new Set())}
      />

      {/* 7. Create Dialog */}
      <CreateNotificationDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
      />
    </div>
  );
}

function getNotificationConfig(type: NotificationType) {
  switch (type) {
    case "application_result":
      return {
        icon: FileCheck2,
        bg: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
        badgeVariant: "success" as const,
      };
    case "room_selection":
      return {
        icon: DoorOpen,
        bg: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
        badgeVariant: "info" as const,
      };
    case "fee_due":
      return {
        icon: Banknote,
        bg: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
        badgeVariant: "warning" as const,
      };
    case "check_in":
      return {
        icon: DoorOpen,
        bg: "bg-purple-500/10 text-purple-600 dark:text-purple-400",
        badgeVariant: "secondary" as const,
      };
    default:
      return {
        icon: Bell,
        bg: "bg-primary/10 text-primary",
        badgeVariant: "secondary" as const,
      };
  }
}

function NotificationAction({ type }: { type: NotificationType }) {
  if (type === "application_result") {
    return (
      <Button
        asChild
        variant="outline"
        size="sm"
        className="h-7 text-xs gap-1 shadow-xs"
      >
        <Link to="/student/registration-history">
          Xem lịch sử hồ sơ <ArrowRight className="size-3" />
        </Link>
      </Button>
    );
  }
  if (type === "room_selection") {
    return (
      <Button asChild size="sm" className="h-7 text-xs gap-1 shadow-xs">
        <Link to="/student/room-selection">
          Chọn phòng ngay <ArrowRight className="size-3" />
        </Link>
      </Button>
    );
  }
  if (type === "fee_due") {
    return (
      <Button asChild size="sm" className="h-7 text-xs gap-1 shadow-xs">
        <Link to="/student/payments">
          Thanh toán KTX <ArrowRight className="size-3" />
        </Link>
      </Button>
    );
  }
  return null;
}

function MyNotificationsPage() {
  const query = useMyNotificationsQuery(false);
  const markAsRead = useMarkNotificationAsRead();
  const [filterTab, setFilterTab] = useState<"all" | "unread" | "read">("all");

  const items = query.data ?? [];
  const unreadItems = useMemo(
    () => items.filter((item) => !item.readAt),
    [items],
  );
  const readItems = useMemo(
    () => items.filter((item) => Boolean(item.readAt)),
    [items],
  );

  const filteredItems = useMemo(() => {
    if (filterTab === "unread") return unreadItems;
    if (filterTab === "read") return readItems;
    return items;
  }, [filterTab, items, readItems, unreadItems]);

  async function handleMarkAllAsRead() {
    if (!unreadItems.length) return;
    try {
      await Promise.all(
        unreadItems.map((item) => markAsRead.mutateAsync(item.id)),
      );
      toast.success("Đã đánh dấu tất cả thông báo là đã đọc.");
    } catch {
      toast.error("Không thể đánh dấu tất cả đã đọc.");
    }
  }

  if (query.isLoading) {
    return <MyNotificationsSkeleton />;
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5 px-3.5 pb-16 sm:space-y-6 sm:px-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="inline-flex items-center gap-1.5 rounded-md bg-primary/10 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider text-primary">
            <Bell className="size-3.5" /> Hộp thư thông báo
          </div>
          <h1 className="mt-1.5 text-xl font-bold tracking-tight sm:text-2xl md:text-3xl">
            Thông báo của bạn
          </h1>
          <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
            Theo dõi các tin tức, cập nhật kết quả hồ sơ, thời gian chọn phòng
            và nhắc nhở thanh toán.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {unreadItems.length > 0 ? (
            <Button
              variant="outline"
              size="sm"
              onClick={handleMarkAllAsRead}
              disabled={markAsRead.isPending}
              className="text-xs gap-1.5"
            >
              <CheckCheck className="size-4 text-primary" />
              Đánh dấu tất cả đã đọc
            </Button>
          ) : null}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void query.refetch()}
            disabled={query.isFetching}
            className="text-xs gap-1.5"
          >
            <RefreshCw
              className={cn("size-3.5", query.isFetching && "animate-spin")}
            />
            Làm mới
          </Button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-1.5 border-b pb-2 text-xs sm:text-sm">
        <button
          type="button"
          onClick={() => setFilterTab("all")}
          className={cn(
            "flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-all",
            filterTab === "all"
              ? "bg-primary text-primary-foreground font-semibold shadow-xs"
              : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
          )}
        >
          <span>Tất cả</span>
          <Badge
            variant={filterTab === "all" ? "secondary" : "outline"}
            className="h-5 px-1.5 text-[11px]"
          >
            {items.length}
          </Badge>
        </button>

        <button
          type="button"
          onClick={() => setFilterTab("unread")}
          className={cn(
            "flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-all",
            filterTab === "unread"
              ? "bg-primary text-primary-foreground font-semibold shadow-xs"
              : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
          )}
        >
          <span>Chưa đọc</span>
          {unreadItems.length > 0 ? (
            <Badge
              variant={filterTab === "unread" ? "secondary" : "default"}
              className="h-5 px-1.5 text-[11px]"
            >
              {unreadItems.length}
            </Badge>
          ) : (
            <Badge variant="outline" className="h-5 px-1.5 text-[11px]">
              0
            </Badge>
          )}
        </button>

        <button
          type="button"
          onClick={() => setFilterTab("read")}
          className={cn(
            "flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-all",
            filterTab === "read"
              ? "bg-primary text-primary-foreground font-semibold shadow-xs"
              : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
          )}
        >
          <span>Đã đọc</span>
          <Badge
            variant={filterTab === "read" ? "secondary" : "outline"}
            className="h-5 px-1.5 text-[11px]"
          >
            {readItems.length}
          </Badge>
        </button>
      </div>

      {/* Notifications List */}
      {query.isError ? (
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <div>
            <AlertTitle>Không thể tải danh sách thông báo</AlertTitle>
            <AlertDescription>
              Vui lòng thử bấm Làm mới hoặc kiểm tra lại kết nối mạng.
            </AlertDescription>
          </div>
        </Alert>
      ) : filteredItems.length > 0 ? (
        <div className="space-y-3">
          {filteredItems.map((item) => {
            const config = getNotificationConfig(item.type);
            const IconComponent = config.icon;
            const isUnread = !item.readAt;

            return (
              <Card
                key={item.id}
                className={cn(
                  "overflow-hidden transition-all text-left shadow-xs hover:shadow-sm",
                  isUnread
                    ? "border-primary/40 bg-primary/[0.02] ring-1 ring-primary/20"
                    : "border-border/70 bg-card",
                )}
              >
                <CardContent className="p-4 sm:p-5">
                  <div className="flex items-start gap-3 sm:gap-4">
                    {/* Semantic Icon */}
                    <div
                      className={cn(
                        "flex size-9 sm:size-10 shrink-0 items-center justify-center rounded-lg",
                        config.bg,
                      )}
                    >
                      <IconComponent className="size-4.5 sm:size-5" />
                    </div>

                    {/* Content */}
                    <div className="min-w-0 flex-1 space-y-1.5">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <h2
                            className={cn(
                              "text-sm sm:text-base font-bold",
                              isUnread
                                ? "text-foreground"
                                : "text-foreground/85",
                            )}
                          >
                            {item.title}
                          </h2>
                          <Badge
                            variant={config.badgeVariant}
                            className="text-[11px] h-5"
                          >
                            {typeLabels[item.type]}
                          </Badge>
                          {isUnread && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary">
                              <span className="size-1.5 rounded-full bg-primary animate-pulse" />
                              Mới
                            </span>
                          )}
                        </div>

                        <span className="text-[11px] sm:text-xs text-muted-foreground whitespace-nowrap">
                          {formatNotificationDate(item.createdAt)}
                        </span>
                      </div>

                      <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                        {item.content}
                      </p>

                      {/* Footer Actions */}
                      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border/40">
                        <NotificationAction type={item.type} />

                        {isUnread && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => void markAsRead.mutateAsync(item.id)}
                            className="h-7 text-xs text-muted-foreground hover:text-foreground ml-auto"
                          >
                            <Check className="size-3.5" /> Đánh dấu đã đọc
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card className="border-dashed shadow-xs">
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <div className="flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
              <Inbox className="size-6" />
            </div>
            <div className="space-y-1">
              <p className="text-base font-semibold sm:text-lg">
                {filterTab === "unread"
                  ? "Bạn đã đọc hết tất cả thông báo"
                  : "Chưa có thông báo nào"}
              </p>
              <p className="max-w-md text-xs text-muted-foreground sm:text-sm">
                {filterTab === "unread"
                  ? "Tuyệt vời! Không còn thông báo mới nào chưa xử lý."
                  : "Các thông tin về kết quả hồ sơ, thời hạn chọn phòng và đóng học phí sẽ xuất hiện tại đây."}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function MyNotificationsSkeleton() {
  return (
    <div className="mx-auto max-w-4xl space-y-5 px-3.5 pb-16 sm:space-y-6 sm:px-6">
      <div className="flex justify-between items-center">
        <div className="space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-8 w-60" />
          <Skeleton className="h-4 w-80" />
        </div>
        <Skeleton className="h-9 w-28" />
      </div>

      <div className="flex gap-2 border-b pb-2">
        <Skeleton className="h-8 w-20 rounded-md" />
        <Skeleton className="h-8 w-24 rounded-md" />
        <Skeleton className="h-8 w-20 rounded-md" />
      </div>

      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: skeleton items
          <Card key={i}>
            <CardContent className="p-4 sm:p-5">
              <div className="flex gap-4">
                <Skeleton className="size-10 rounded-lg shrink-0" />
                <div className="space-y-2.5 w-full">
                  <div className="flex justify-between">
                    <Skeleton className="h-5 w-48" />
                    <Skeleton className="h-4 w-24" />
                  </div>
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

type NotificationFormValues = {
  title: string;
  content: string;
  type: NotificationType;
  recipientMode: "all" | "student";
  studentId: string;
};

const notificationFormSchema = z
  .object({
    title: z
      .string()
      .trim()
      .min(1, "Tiêu đề là bắt buộc.")
      .max(255, "Tiêu đề tối đa 255 ký tự."),
    content: z
      .string()
      .trim()
      .min(1, "Nội dung là bắt buộc.")
      .max(4000, "Nội dung tối đa 4.000 ký tự."),
    type: z.enum(notificationTypes),
    recipientMode: z.enum(["all", "student"]),
    studentId: z.string(),
  })
  .superRefine((value, context) => {
    if (value.recipientMode === "student" && !value.studentId) {
      context.addIssue({
        code: "custom",
        path: ["studentId"],
        message: "Hãy chọn sinh viên nhận thông báo.",
      });
    }
  });

function CreateNotificationDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const create = useCreateNotification();
  const [studentSearch, setStudentSearch] = useState("");
  const students = useStudentsQuery(
    { search: studentSearch.trim() || undefined, page: 1, pageSize: 20 },
    { enabled: open },
  );
  const form = useForm({
    defaultValues: {
      title: "",
      content: "",
      type: "general" as NotificationType,
      recipientMode: "all" as NotificationFormValues["recipientMode"],
      studentId: "",
    } satisfies NotificationFormValues,
    validators: { onSubmit: notificationFormSchema },
    onSubmit: async ({ value }) => {
      try {
        await create.mutateAsync({
          title: value.title.trim(),
          content: value.content.trim(),
          type: value.type,
          sendToAllStudents: value.recipientMode === "all",
          studentRecipientIds:
            value.recipientMode === "student" ? [value.studentId] : [],
          userRecipientIds: [],
        });
        form.reset();
        setStudentSearch("");
        onOpenChange(false);
        toast.success("Đã gửi thông báo.");
      } catch (error) {
        toast.error(
          error instanceof ApiError
            ? error.message
            : "Không thể gửi thông báo.",
        );
      }
    },
  });

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(760px,calc(100dvh-1rem))] w-full max-w-2xl flex-col overflow-hidden">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>Tạo thông báo</ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            Chọn phạm vi người nhận rõ ràng. Khi gửi toàn bộ, danh sách sinh
            viên được lấy tại thời điểm gửi.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <form
          className="min-h-0 flex-1 overflow-y-auto"
          onSubmit={(event) => {
            event.preventDefault();
            event.stopPropagation();
            void form.handleSubmit();
          }}
        >
          <div className="grid gap-5 px-1 py-4 sm:px-2">
            <Alert>
              <Send />
              <AlertTitle>Thông báo trong hệ thống</AlertTitle>
              <AlertDescription>
                Người nhận sẽ thấy thông báo ngay trong QNU KTX. Email hoặc kênh
                ngoài chỉ được bổ sung khi hệ thống đã cấu hình.
              </AlertDescription>
            </Alert>
            <form.Field name="title">
              {(field) => {
                const error = firstError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="notification-title">
                      Tiêu đề
                    </FieldLabel>
                    <Input
                      id="notification-title"
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      aria-invalid={Boolean(error)}
                      placeholder="Ví dụ: Kết quả xét duyệt hồ sơ KTX"
                    />
                    {error ? <FieldError>{error}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>
            <div className="grid gap-5 sm:grid-cols-2">
              <form.Field name="type">
                {(field) => (
                  <Field>
                    <FieldLabel>Loại thông báo</FieldLabel>
                    <Select
                      value={field.state.value}
                      onValueChange={(value) =>
                        field.handleChange(value as NotificationType)
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {notificationTypes.map((type) => (
                          <SelectItem key={type} value={type}>
                            {typeLabels[type]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </Field>
                )}
              </form.Field>
              <form.Field name="recipientMode">
                {(field) => (
                  <Field>
                    <FieldLabel>Phạm vi người nhận</FieldLabel>
                    <Select
                      value={field.state.value}
                      onValueChange={(value) => {
                        field.handleChange(
                          value as NotificationFormValues["recipientMode"],
                        );
                        if (value === "all")
                          form.setFieldValue("studentId", "");
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Tất cả sinh viên</SelectItem>
                        <SelectItem value="student">Một sinh viên</SelectItem>
                      </SelectContent>
                    </Select>
                  </Field>
                )}
              </form.Field>
            </div>
            <form.Subscribe selector={(state) => state.values.recipientMode}>
              {(recipientMode) =>
                recipientMode === "student" ? (
                  <form.Field name="studentId">
                    {(field) => {
                      const error = firstError(field.state.meta.errors);
                      return (
                        <Field>
                          <FieldLabel htmlFor="notification-student-search">
                            Sinh viên nhận thông báo
                          </FieldLabel>
                          <Input
                            id="notification-student-search"
                            value={studentSearch}
                            onChange={(event) =>
                              setStudentSearch(event.target.value)
                            }
                            placeholder="Tìm theo mã hoặc tên sinh viên..."
                          />
                          <FieldDescription>
                            Chọn một kết quả bên dưới để tránh nhập nhầm ID nội
                            bộ.
                          </FieldDescription>
                          <div className="max-h-44 overflow-y-auto rounded-md border">
                            {students.isLoading ? (
                              <div className="p-3 text-sm text-muted-foreground">
                                Đang tìm sinh viên...
                              </div>
                            ) : students.data?.items.length ? (
                              students.data.items.map((student) => (
                                <button
                                  type="button"
                                  key={student.id}
                                  className={`flex w-full items-center justify-between gap-3 border-b px-3 py-2 text-left text-sm last:border-0 hover:bg-muted/40 ${field.state.value === student.id ? "bg-primary/[0.06]" : ""}`}
                                  onClick={() => field.handleChange(student.id)}
                                >
                                  <span className="min-w-0">
                                    <span className="block truncate font-medium">
                                      {student.fullName}
                                    </span>
                                    <span className="block text-xs text-muted-foreground">
                                      {student.studentCode}
                                    </span>
                                  </span>
                                  {field.state.value === student.id ? (
                                    <Check className="size-4 shrink-0 text-primary" />
                                  ) : null}
                                </button>
                              ))
                            ) : (
                              <div className="p-3 text-sm text-muted-foreground">
                                Không tìm thấy sinh viên phù hợp.
                              </div>
                            )}
                          </div>
                          {error ? <FieldError>{error}</FieldError> : null}
                        </Field>
                      );
                    }}
                  </form.Field>
                ) : (
                  <div className="rounded-md border border-primary/20 bg-primary/[0.04] px-3 py-2 text-sm text-muted-foreground">
                    Hệ thống sẽ tạo người nhận từ toàn bộ sinh viên hiện có tại
                    thời điểm gửi.
                  </div>
                )
              }
            </form.Subscribe>
            <form.Field name="content">
              {(field) => {
                const error = firstError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="notification-content">
                      Nội dung
                    </FieldLabel>
                    <Textarea
                      id="notification-content"
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      aria-invalid={Boolean(error)}
                      placeholder="Nhập nội dung cần thông báo..."
                      className="min-h-32"
                      maxLength={4000}
                    />
                    <FieldDescription>Tối đa 4.000 ký tự.</FieldDescription>
                    {error ? <FieldError>{error}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>
          </div>
          <ResponsiveDialogFooter className="border-t px-1 pt-4 sm:px-2">
            <Button
              type="button"
              variant="outline"
              disabled={create.isPending}
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <form.Subscribe
              selector={(state) => [state.canSubmit, state.isSubmitting]}
            >
              {([canSubmit, formSubmitting]) => (
                <Button
                  type="submit"
                  disabled={!canSubmit || formSubmitting || create.isPending}
                >
                  <Send />
                  {create.isPending ? "Đang gửi..." : "Gửi thông báo"}
                </Button>
              )}
            </form.Subscribe>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
