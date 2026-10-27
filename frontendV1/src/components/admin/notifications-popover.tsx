import { useRouter } from "@tanstack/react-router";
import { Bell, Check, LoaderCircle } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  useMarkNotificationAsRead,
  useMyNotificationsQuery,
  useMyNotificationUnreadCountQuery,
} from "@/features/notifications/api";
import type {
  MyNotification,
  NotificationType,
} from "@/features/notifications/types";

const typeLabels: Record<NotificationType, string> = {
  application_result: "Kết quả hồ sơ",
  check_in: "Nhận phòng",
  fee_due: "Thanh toán",
  room_selection: "Chọn phòng",
  general: "Thông báo chung",
};

export function NotificationsPopover() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const notifications = useMyNotificationsQuery(false);
  const unreadCount = useMyNotificationUnreadCountQuery();
  const markAsRead = useMarkNotificationAsRead();
  const items = notifications.data?.slice(0, 5) ?? [];

  const openAdminNotifications = () => {
    setOpen(false);
    void router.navigate({
      to: "/notifications",
      search: { q: "", type: undefined, page: 1, pageSize: 10 },
    });
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <Tooltip>
        <TooltipTrigger asChild>
          <PopoverTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Thông báo">
              <span className="relative">
                <Bell />
                {(unreadCount.data ?? 0) > 0 ? (
                  <span className="absolute -right-2 -top-2 min-w-4 rounded-full bg-destructive px-1 text-center text-[10px] font-semibold leading-4 text-destructive-foreground">
                    {(unreadCount.data ?? 0) > 99 ? "99+" : unreadCount.data}
                  </span>
                ) : null}
              </span>
              <span className="sr-only">Thông báo mới</span>
            </Button>
          </PopoverTrigger>
        </TooltipTrigger>
        <TooltipContent>Thông báo</TooltipContent>
      </Tooltip>
      <PopoverContent
        align="end"
        className="w-[min(390px,calc(100vw-1rem))] overflow-hidden p-0"
      >
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold">Thông báo</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Cập nhật mới nhất dành cho bạn
            </p>
          </div>
          {(unreadCount.data ?? 0) > 0 ? (
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
              {unreadCount.data} chưa đọc
            </span>
          ) : null}
        </div>
        <div className="max-h-[min(420px,60vh)] overflow-y-auto">
          {notifications.isLoading ? (
            <div className="flex items-center gap-2 px-4 py-8 text-sm text-muted-foreground">
              <LoaderCircle className="size-4 animate-spin" />
              Đang tải thông báo...
            </div>
          ) : notifications.isError ? (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
              Chưa thể tải thông báo lúc này.
            </div>
          ) : items.length === 0 ? (
            <div className="px-4 py-10 text-center text-sm text-muted-foreground">
              Bạn chưa có thông báo nào.
            </div>
          ) : (
            items.map((item) => (
              <NotificationItem
                key={`${item.id}-${item.readAt ?? "unread"}`}
                item={item}
                onRead={() => {
                  if (!item.readAt) void markAsRead.mutateAsync(item.id);
                }}
              />
            ))
          )}
        </div>
        <div className="flex items-center justify-between gap-3 border-t px-4 py-3 text-sm">
          <button
            type="button"
            className="font-medium text-primary hover:underline"
            onClick={openAdminNotifications}
          >
            Xem danh sách
          </button>
          <span className="text-xs text-muted-foreground">
            Tự động cập nhật
          </span>
        </div>
      </PopoverContent>
    </Popover>
  );
}

function NotificationItem({
  item,
  onRead,
}: {
  item: MyNotification;
  onRead: () => void;
}) {
  return (
    <button
      type="button"
      className={`flex w-full items-start gap-3 border-b px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-muted/40 ${item.readAt ? "" : "bg-primary/[0.04]"}`}
      onClick={onRead}
    >
      <span className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
        {item.readAt ? (
          <Check className="size-3.5" />
        ) : (
          <Bell className="size-3.5" />
        )}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-start justify-between gap-2">
          <span className="line-clamp-2 text-sm font-medium">{item.title}</span>
          {!item.readAt ? (
            <span className="mt-1 size-2 shrink-0 rounded-full bg-primary" />
          ) : null}
        </span>
        <span className="mt-1 block line-clamp-2 text-xs text-muted-foreground">
          {item.content}
        </span>
        <span className="mt-1 block text-[11px] text-muted-foreground">
          {typeLabels[item.type]} · {formatDate(item.createdAt)}
        </span>
      </span>
    </button>
  );
}

function formatDate(value: string) {
  return new Date(value).toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
