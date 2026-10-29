import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  Boxes,
  FolderOpen,
  RefreshCw,
  Settings2,
  UsersRound,
} from "lucide-react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { ErrorState } from "@/components/admin/error-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { canReadCompilation } from "@/features/knowledge/permissions";
import { useCollectionsQuery } from "@/features/knowledge/queries";
import { canReadOperations } from "@/features/lifecycle/permissions";
import { useFeatureScope } from "@/navigation/use-feature-scope";
import { DashboardOperations } from "./qnu-dashboard-operations";
import { useCallerWorkspaceRole, useWorkspaceQuery } from "./queries";
import { listWorkspaces } from "./requests";

type Props = {
  workspaceId?: string;
  page: number;
  onSearch: (patch: { workspaceId?: string; page?: number }) => void;
};
export function QnuDashboardPage(props: Props) {
  const { sessionId } = useV1Auth();
  return <DashboardSession key={sessionId} {...props} />;
}
function DashboardSession({ workspaceId, page }: Props) {
  const { sessionId } = useV1Auth();
  const scope = useFeatureScope();
  const query = useQuery({
    queryKey: ["v1", sessionId, "dashboard-workspaces", page],
    queryFn: ({ signal }) =>
      listWorkspaces(v1Client, { page, pageSize: 20 }, { signal }),
    retry: false,
  });
  const effectiveWorkspaceId =
    workspaceId || scope.workspaceId || query.data?.items?.[0]?.id;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="QNU AI"
        title="Tổng quan"
        description="Theo dõi kho tri thức, trợ lý và quá trình xử lý tài liệu của đơn vị đang chọn trên thanh đầu trang."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={query.isFetching}
              onClick={() => void query.refetch()}
            >
              <RefreshCw className="size-3.5" />
              Làm mới
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link to="/settings">
                <Settings2 className="size-3.5" />
                Cấu hình
              </Link>
            </Button>
          </div>
        }
      />
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : null}
      {effectiveWorkspaceId ? (
        <WorkspaceDashboard
          key={effectiveWorkspaceId}
          workspaceId={effectiveWorkspaceId}
        />
      ) : query.isPending ? (
        <Skeleton className="h-40 rounded-xl" />
      ) : (
        <Card className="rounded-xl shadow-2xs border-border/70">
          <CardContent className="flex items-center gap-3 p-6 text-sm text-muted-foreground">
            <Boxes className="size-5 shrink-0 text-primary" />
            <span>
              Chưa có đơn vị để hiển thị. Chọn đơn vị ở thanh đầu trang hoặc mở
              Cấu hình để khởi tạo đơn vị mới.
            </span>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
function WorkspaceDashboard({ workspaceId }: { workspaceId: string }) {
  const query = useWorkspaceQuery(workspaceId);
  if (query.isPending) return <Skeleton className="h-40" />;
  if (query.isError)
    return (
      <ErrorState error={query.error} onRetry={() => void query.refetch()} />
    );
  const workspace = query.data;
  return (
    <section aria-label="Tổng quan workspace" className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <h2 className="text-xl font-semibold break-words">
            {workspace.name}
          </h2>
          <p className="text-sm text-muted-foreground break-words">
            {workspace.description || "Chưa có mô tả."}
          </p>
        </div>
        <Badge variant={workspace.status === "active" ? "success" : "warning"}>
          {workspace.status === "active" ? "Đang hoạt động" : "Tạm dừng"}
        </Badge>
      </div>
      {workspace.status === "active" ? (
        <WorkspaceContents
          workspaceId={workspaceId}
          memberCount={workspace.member_count}
        />
      ) : (
        <p role="status" className="text-sm">
          Workspace tạm dừng. Mở quản lý workspace để kiểm tra trạng thái trước
          khi tiếp tục.
        </p>
      )}
    </section>
  );
}
function WorkspaceContents({
  workspaceId,
  memberCount,
}: {
  workspaceId: string;
  memberCount: number;
}) {
  const access = useCallerWorkspaceRole(workspaceId);
  if (access.isPending)
    return <p role="status">Đang kiểm tra quyền workspace…</p>;
  if (access.error) return <ErrorState error={access.error} />;
  if (!canReadCompilation(access.role))
    return <p role="alert">Chưa xác nhận được quyền đọc nội dung workspace.</p>;
  return (
    <>
      <DashboardCollections
        workspaceId={workspaceId}
        memberCount={memberCount}
      />
      {canReadOperations(access.role) ? (
        <DashboardOperations workspaceId={workspaceId} />
      ) : (
        <p className="text-sm text-muted-foreground">
          Số liệu tác vụ và usage dành cho quản trị, biên tập và rà soát.
        </p>
      )}
    </>
  );
}
function DashboardCollections({
  workspaceId,
  memberCount,
}: {
  workspaceId: string;
  memberCount: number;
}) {
  const query = useCollectionsQuery(workspaceId, { page: 1, pageSize: 6 });
  return (
    <Card className="rounded-xl shadow-2xs border-border/70">
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 pb-3">
        <CardTitle className="text-sm font-semibold">Kho tri thức</CardTitle>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 text-xs text-primary"
          asChild
        >
          <Link
            to="/workspaces/$workspaceId/collections"
            params={{ workspaceId }}
            search={{ page: 1, pageSize: 20 }}
          >
            Xem tất cả
          </Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {query.isPending ? (
          <Skeleton className="h-24" />
        ) : query.isError ? (
          <ErrorState
            error={query.error}
            onRetry={() => void query.refetch()}
          />
        ) : (
          <>
            <div className="grid grid-cols-2 divide-x rounded-xl border border-border/70 overflow-hidden">
              <KpiMetric
                label="Kho tài liệu"
                value={String(query.data.meta.total)}
                icon={FolderOpen}
              />
              <KpiMetric
                label="Thành viên"
                value={String(memberCount)}
                icon={UsersRound}
              />
            </div>
            {query.data.items.length ? (
              <ul className="grid gap-3 md:grid-cols-2">
                {query.data.items.map((item) => (
                  <li
                    key={item.id}
                    className="group min-w-0 rounded-xl border border-border/70 p-3.5 hover:border-primary/40 hover:bg-muted/20 transition-all flex items-center justify-between gap-3"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <FolderOpen className="size-4" />
                      </span>
                      <div className="min-w-0">
                        <Link
                          to="/workspaces/$workspaceId/collections/$collectionId"
                          params={{ workspaceId, collectionId: item.id }}
                          search={{ page: 1, pageSize: 20, tab: "sources" }}
                          className="font-semibold text-sm text-foreground group-hover:text-primary transition-colors truncate block"
                        >
                          {item.name}
                        </Link>
                        <p className="text-xs text-muted-foreground">
                          {item.source_count} nguồn tài liệu
                        </p>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">
                Chưa có kho tài liệu trong workspace này.
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
