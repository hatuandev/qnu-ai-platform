import { Bell } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { MyNotification } from "@/features/student/types";
import { formatDateValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

export function NotificationsCard({
  notifications,
  onMarkRead,
}: {
  notifications: MyNotification[];
  onMarkRead: (id: string) => void;
}) {
  const unreadCount = notifications.filter((item) => !item.readAt).length;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">Thông báo</CardTitle>
          {unreadCount > 0 ? (
            <Badge variant="secondary">{unreadCount} chưa đọc</Badge>
          ) : null}
        </div>
        <CardDescription>Những thông tin mới nhất từ ký túc xá</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {notifications.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Chưa có thông báo nào.
          </p>
        ) : (
          notifications.slice(0, 4).map((notification) => (
            <button
              key={notification.id}
              type="button"
              className={cn(
                "flex w-full items-start gap-3 rounded-lg border bg-card p-3 text-left transition-colors hover:bg-muted/50",
                !notification.readAt && "border-primary/40 bg-primary/5",
              )}
              onClick={() => {
                if (!notification.readAt) onMarkRead(notification.id);
              }}
            >
              <Bell className="mt-0.5 size-4 shrink-0 text-primary" />
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2">
                  <span className="text-sm font-semibold">
                    {notification.title}
                  </span>
                  {!notification.readAt ? (
                    <span className="size-1.5 shrink-0 rounded-full bg-primary" />
                  ) : null}
                </span>
                <span className="mt-0.5 block text-sm text-muted-foreground line-clamp-2">
                  {notification.content}
                </span>
                <span className="mt-1 block text-xs text-muted-foreground">
                  {formatDateValue(notification.createdAt)}
                </span>
              </span>
            </button>
          ))
        )}
      </CardContent>
    </Card>
  );
}
