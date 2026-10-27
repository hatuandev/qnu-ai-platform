import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, Bell, LoaderCircle } from "lucide-react";
import { AccessDenied } from "@/components/admin/access-denied";
import { EmptyState } from "@/components/admin/empty-state";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useNotificationQuery } from "@/features/notifications/api";
import type { NotificationType } from "@/features/notifications/types";
import { formatDateTime } from "@/lib/date-utils";
import { useRbac } from "@/rbac/context";

const typeLabels: Record<NotificationType, string> = {
  application_result: "Kết quả hồ sơ",
  check_in: "Nhận phòng",
  fee_due: "Thanh toán",
  room_selection: "Chọn phòng",
  general: "Thông báo chung",
};

export const Route = createFileRoute("/notifications/$notificationId")({
  component: () => (
    <NotificationDetail notificationId={Route.useParams().notificationId} />
  ),
});

function NotificationDetail({ notificationId }: { notificationId: string }) {
  const navigate = useNavigate({ from: "/notifications/$notificationId" });
  const { can } = useRbac();
  const canView = can("ktx.notifications.create");
  const query = useNotificationQuery(notificationId, { enabled: canView });

  if (!canView) return <AccessDenied />;
  if (query.isLoading) {
    return (
      <div className="flex min-h-64 items-center justify-center gap-2 rounded-lg border text-sm text-muted-foreground">
        <LoaderCircle className="size-4 animate-spin" />
        Đang tải thông báo...
      </div>
    );
  }
  if (query.isError || !query.data) {
    return (
      <EmptyState
        icon={Bell}
        title="Không thể tải thông báo"
        description="Thông báo có thể không tồn tại hoặc bạn không có quyền xem."
        action={{
          label: "Quay lại danh sách",
          onClick: () =>
            void navigate({
              to: "/notifications",
              search: { q: "", page: 1, pageSize: 10 },
            }),
        }}
      />
    );
  }

  const item = query.data;
  const readCount = item.recipients.filter(
    (recipient) => recipient.readAt,
  ).length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Trao đổi / Thông báo"
        title={item.title}
        description={`${typeLabels[item.type]} · ${formatDateTime(new Date(item.createdAt))}`}
        actions={
          <Button
            variant="outline"
            onClick={() =>
              void navigate({
                to: "/notifications",
                search: { q: "", page: 1, pageSize: 10 },
              })
            }
          >
            <ArrowLeft />
            Quay lại
          </Button>
        }
      />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
        <article className="rounded-lg border bg-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-4">
            <Badge variant="secondary">{typeLabels[item.type]}</Badge>
            <span className="text-sm text-muted-foreground">
              Tạo bởi {item.createdBy || "Hệ thống"}
            </span>
          </div>
          <p className="whitespace-pre-wrap pt-5 text-sm leading-7">
            {item.content}
          </p>
        </article>
        <aside className="rounded-lg border bg-card p-5">
          <h2 className="font-semibold">Phạm vi gửi</h2>
          <dl className="mt-4 space-y-4 text-sm">
            <Info label="Tổng người nhận" value={String(item.recipientCount)} />
            <Info label="Đã đọc" value={String(readCount)} />
            <Info
              label="Chưa đọc"
              value={String(Math.max(item.recipientCount - readCount, 0))}
            />
            <Info
              label="Ngày tạo"
              value={formatDateTime(new Date(item.createdAt))}
            />
          </dl>
        </aside>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 font-medium tabular-nums">{value}</dd>
    </div>
  );
}
