import { Link } from "@tanstack/react-router";
import { ArrowRight, CalendarClock, Fingerprint, Info } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaceQuery } from "@/features/workspaces/queries";
import { DEFAULT_PAGE_SEARCH } from "@/features/workspaces/search";
import { formatDateTimeValue } from "@/lib/date-utils";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid gap-1 border-b py-2.5 last:border-0 sm:grid-cols-[180px_1fr] sm:items-baseline">
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-sm break-words">{value}</dd>
    </div>
  );
}

export function WorkspaceOverview({ workspaceId }: { workspaceId: string }) {
  const query = useWorkspaceQuery(workspaceId);
  const workspace = query.data;

  if (query.isLoading) return <Skeleton className="h-64 w-full" />;
  if (!workspace) return null;

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="rounded-xl shadow-2xs lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-sm">Thông tin workspace</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="m-0">
            <Row
              label="Mô tả"
              value={
                workspace.description ? (
                  workspace.description
                ) : (
                  <span className="text-muted-foreground">Chưa có mô tả</span>
                )
              }
            />
            <Row
              label="Mã"
              value={
                <code className="font-mono text-xs">{workspace.code}</code>
              }
            />
            <Row
              label="Định danh"
              value={
                <span className="flex items-center gap-1.5">
                  <Fingerprint className="size-3.5 text-muted-foreground" />
                  <code className="font-mono text-xs">{workspace.id}</code>
                </span>
              }
            />
            <Row
              label="Trạng thái"
              value={
                workspace.status === "active"
                  ? "Đang hoạt động"
                  : "Tạm dừng (thành viên bị chặn nội dung)"
              }
            />
            <Row label="Số thành viên" value={workspace.member_count} />
          </dl>
        </CardContent>
      </Card>

      <div className="grid content-start gap-4">
        <Card className="rounded-xl shadow-2xs">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <CalendarClock className="size-4 text-muted-foreground" />
              Mốc thời gian
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm">
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs text-muted-foreground">Tạo lúc</span>
              <span>{formatDateTimeValue(workspace.created_at)}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs text-muted-foreground">Cập nhật</span>
              <span>{formatDateTimeValue(workspace.updated_at)}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-xl shadow-2xs">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Info className="size-4 text-muted-foreground" />
              Tiếp theo
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-1 text-sm">
            <Link
              to="/workspaces/$workspaceId/members"
              search={DEFAULT_PAGE_SEARCH}
              params={{ workspaceId }}
              className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-muted"
            >
              <span>Quản lý thành viên và vai trò</span>
              <ArrowRight className="size-3.5" />
            </Link>
            <Link
              to="/workspaces/$workspaceId/models"
              params={{ workspaceId }}
              className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-muted"
            >
              <span>Model được cấp và model mặc định</span>
              <ArrowRight className="size-3.5" />
            </Link>
            <Link
              to="/workspaces/$workspaceId/quota"
              search={DEFAULT_PAGE_SEARCH}
              params={{ workspaceId }}
              className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-muted"
            >
              <span>Quota tháng và usage đã quan sát</span>
              <ArrowRight className="size-3.5" />
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
