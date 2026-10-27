import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { Boxes, FolderOpen, RefreshCw, UsersRound } from "lucide-react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { Combobox } from "@/components/admin/combobox";
import { ErrorState } from "@/components/admin/error-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ListPagination } from "@/features/knowledge/list-pagination";
import { canReadCompilation } from "@/features/knowledge/permissions";
import { useCollectionsQuery } from "@/features/knowledge/queries";
import {
  canReadOperations,
  isLifecycleAdmin,
} from "@/features/lifecycle/permissions";
import { ReadinessPanel } from "@/features/operations/readiness-panel";
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
function DashboardSession({ workspaceId, page, onSearch }: Props) {
  const { sessionId } = useV1Auth();
  const query = useQuery({
    queryKey: ["v1", sessionId, "dashboard-workspaces", page],
    queryFn: ({ signal }) =>
      listWorkspaces(v1Client, { page, pageSize: 20 }, { signal }),
    retry: false,
  });
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="QNU AI"
        title="Tổng quan"
        description="Theo dõi kho tri thức và quá trình xử lý trong workspace bạn có quyền truy cập."
        actions={
          <Button variant="outline" size="sm" asChild>
            <Link to="/workspaces" search={{ page: 1, pageSize: 20 }}>
              Workspaces
            </Link>
          </Button>
        }
      />
      <section aria-label="Chọn workspace tổng quan" className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="w-full sm:w-96">
            <Combobox
              options={(query.data?.items ?? []).map((item) => ({
                value: item.id,
                label: `${item.name} · ${item.code}`,
              }))}
              value={workspaceId}
              placeholder="Chọn workspace…"
              searchPlaceholder="Lọc trong trang…"
              loading={query.isPending}
              disabled={query.isFetching || query.isError}
              onValueChange={(id) => onSearch({ workspaceId: id })}
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            disabled={query.isFetching}
            onClick={() => void query.refetch()}
          >
            <RefreshCw className="size-3.5" />
            Làm mới
          </Button>
          {query.isSuccess ? (
            <span className="text-xs text-muted-foreground">
              {query.data.meta.total} workspace có quyền truy cập
            </span>
          ) : null}
        </div>
        {query.isError ? (
          <ErrorState
            error={query.error}
            onRetry={() => void query.refetch()}
          />
        ) : null}
        {query.isSuccess && query.data.meta.total === 0 ? (
          <p className="text-sm text-muted-foreground">
            Chưa có workspace để hiển thị. Quản trị viên có thể tạo hoặc cấp
            quyền ở Workspaces.
          </p>
        ) : null}
        <ListPagination
          page={page}
          pageSize={20}
          onPageChange={(p) => onSearch({ page: p })}
          hasNext={
            !query.isError &&
            Boolean(query.data && page * 20 < query.data.meta.total)
          }
          disabled={query.isFetching}
          label="workspace tổng quan"
        />
      </section>
      {workspaceId ? (
        <WorkspaceDashboard key={workspaceId} workspaceId={workspaceId} />
      ) : (
        <Card className="rounded-xl shadow-2xs">
          <CardContent className="flex gap-3 p-6 text-sm">
            <Boxes className="size-5 shrink-0 text-primary" />
            Chọn một workspace để xem dữ liệu. Đường dẫn sẽ giữ lựa chọn khi tải
            lại trang.
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
      <nav aria-label="Truy cập nhanh QNU" className="flex flex-wrap gap-2">
        <Button size="sm" variant="outline" asChild>
          <Link
            to="/workspaces/$workspaceId/assistants"
            params={{ workspaceId }}
            search={{ limit: 20, offset: 0 }}
          >
            Trợ lý
          </Link>
        </Button>
        <Button size="sm" variant="outline" asChild>
          <Link
            to="/workspaces/$workspaceId/conversations"
            params={{ workspaceId }}
          >
            Hội thoại
          </Link>
        </Button>
        {canReadOperations(access.role) ? (
          <Button size="sm" variant="outline" asChild>
            <Link
              to="/workspaces/$workspaceId/operations"
              params={{ workspaceId }}
              search={{ page: 1, pageSize: 20 }}
            >
              Vận hành
            </Link>
          </Button>
        ) : null}
      </nav>
      {canReadOperations(access.role) ? (
        <DashboardOperations workspaceId={workspaceId} />
      ) : (
        <p className="text-sm text-muted-foreground">
          Số liệu tác vụ và usage dành cho quản trị, biên tập và rà soát.
        </p>
      )}
      {isLifecycleAdmin(access.role) ? (
        <ReadinessPanel workspaceId={workspaceId} />
      ) : null}
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
    <Card className="rounded-xl shadow-2xs">
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
        <CardTitle className="text-sm">Kho tri thức</CardTitle>
        <Button variant="outline" size="sm" asChild>
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
            <div className="grid grid-cols-2 divide-x rounded-lg border">
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
                  <li key={item.id} className="min-w-0 rounded-lg border p-3">
                    <Link
                      to="/workspaces/$workspaceId/collections/$collectionId"
                      params={{ workspaceId, collectionId: item.id }}
                      search={{ page: 1, pageSize: 20, tab: "sources" }}
                      className="font-medium text-primary break-words hover:underline"
                    >
                      {item.name}
                    </Link>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {item.source_count} nguồn tài liệu
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">
                Chưa có kho tài liệu trong workspace này.
              </p>
            )}
            {query.data.meta.total > query.data.items.length ? (
              <p className="text-xs text-muted-foreground">
                Đang hiển thị {query.data.items.length} kho đầu tiên. Chọn Xem
                tất cả để xem danh sách đầy đủ.
              </p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
