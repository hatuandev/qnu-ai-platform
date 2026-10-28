import { Link, Outlet } from "@tanstack/react-router";
import {
  ArrowLeft,
  Gauge,
  PauseCircle,
  Pencil,
  PlayCircle,
  Users,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import {
  canManageMembers,
  isPlatformWorkspaceAdmin,
  useV1Auth,
} from "@/app/auth/v1";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { canReadOperations } from "@/features/lifecycle/permissions";
import {
  useCallerWorkspaceRole,
  useUpdateWorkspace,
  useWorkspaceQuery,
} from "@/features/workspaces/queries";
import { DEFAULT_PAGE_SEARCH } from "@/features/workspaces/search";
import { WorkspaceFormDialog } from "@/features/workspaces/workspace-form-dialog";
import { WorkspaceStatusHint } from "@/features/workspaces/workspaces-table";
import { cn } from "@/lib/utils";
import { workspaceFeatures } from "@/navigation/config";

const TABS = [
  {
    id: "overview",
    label: "Tổng quan",
    to: "/workspaces/$workspaceId",
    exact: true,
  },
  {
    id: "collections",
    label: workspaceFeatures.collections.title,
    to: workspaceFeatures.collections.to,
    exact: false,
  },
  {
    id: "assistants",
    label: workspaceFeatures.assistants.title,
    to: workspaceFeatures.assistants.to,
    exact: false,
  },
  {
    id: "conversations",
    label: workspaceFeatures.conversations.title,
    to: workspaceFeatures.conversations.to,
    exact: false,
  },
  {
    id: "members",
    label: workspaceFeatures.members.title,
    to: workspaceFeatures.members.to,
    exact: false,
  },
  {
    id: "models",
    label: workspaceFeatures.models.title,
    to: workspaceFeatures.models.to,
    exact: false,
  },
  {
    id: "quota",
    label: workspaceFeatures.quota.title,
    to: workspaceFeatures.quota.to,
    exact: false,
  },
  {
    id: "operations",
    label: "Vận hành",
    to: workspaceFeatures.jobs.to,
    exact: false,
  },
  {
    id: "resources",
    label: workspaceFeatures.resources.title,
    to: workspaceFeatures.resources.to,
    exact: false,
  },
  {
    id: "audit",
    label: workspaceFeatures.audit.title,
    to: workspaceFeatures.audit.to,
    exact: false,
  },
] as const;

export function WorkspaceDetailLayout({
  workspaceId,
}: {
  workspaceId: string;
}) {
  const { actor } = useV1Auth();
  const workspaceQuery = useWorkspaceQuery(workspaceId);
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const updateMutation = useUpdateWorkspace(workspaceId);
  const [editOpen, setEditOpen] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);

  const workspace = workspaceQuery.data;
  const platformAdmin = isPlatformWorkspaceAdmin(actor);

  if (workspaceQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (workspaceQuery.isError || !workspace) {
    return (
      <div className="space-y-4">
        <Button asChild variant="ghost" size="sm" className="gap-1.5 text-xs">
          <Link to="/workspaces" search={DEFAULT_PAGE_SEARCH}>
            <ArrowLeft className="size-3.5" />
            Danh sách workspace
          </Link>
        </Button>
        <ErrorState
          error={workspaceQuery.error}
          onRetry={() => void workspaceQuery.refetch()}
        />
      </div>
    );
  }

  const nextStatus = workspace.status === "active" ? "suspended" : "active";

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Button asChild variant="ghost" size="sm" className="gap-1.5 text-xs">
          <Link to="/workspaces" search={DEFAULT_PAGE_SEARCH}>
            <ArrowLeft className="size-3.5" />
            Danh sách workspace
          </Link>
        </Button>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="min-w-0">
            <p className="type-metadata mb-2 font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              QNU AI · Workspace
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="type-page-title m-0 truncate">{workspace.name}</h1>
              {workspace.status === "active" ? (
                <Badge variant="success">Đang hoạt động</Badge>
              ) : (
                <Badge variant="destructive">Tạm dừng</Badge>
              )}
            </div>
            <p className="mt-1.5 font-mono text-xs text-muted-foreground">
              {workspace.code} · {workspace.id}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
              disabled={!platformAdmin || updateMutation.isPending}
              onClick={() => setEditOpen(true)}
              title={
                platformAdmin
                  ? undefined
                  : "Cần quyền ai.workspaces.manage để sửa workspace"
              }
            >
              <Pencil className="size-3.5" />
              <span>Sửa</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
              disabled={!platformAdmin || updateMutation.isPending}
              onClick={() => setStatusOpen(true)}
              title={
                platformAdmin
                  ? undefined
                  : "Cần quyền ai.workspaces.manage để tạm dừng workspace"
              }
            >
              {nextStatus === "suspended" ? (
                <PauseCircle className="size-3.5" />
              ) : (
                <PlayCircle className="size-3.5" />
              )}
              <span>
                {nextStatus === "suspended" ? "Tạm dừng" : "Kích hoạt"}
              </span>
            </Button>
          </div>
        </div>

        <Card className="rounded-xl shadow-2xs">
          <CardContent className="grid gap-3 py-4 sm:grid-cols-3">
            <div className="flex items-center gap-2 text-sm">
              <Users className="size-4 text-muted-foreground" />
              <span className="text-muted-foreground">Thành viên:</span>
              <span className="font-semibold">{workspace.member_count}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Gauge className="size-4 text-muted-foreground" />
              <span className="text-muted-foreground">Vai trò của bạn:</span>
              <span className="font-medium">
                {rolePending
                  ? "Đang xác định..."
                  : role.kind === "platform-admin"
                    ? "Quản trị nền tảng"
                    : role.kind === "member"
                      ? role.role
                      : role.kind === "unknown"
                        ? "Chưa xác định"
                        : "Không phải thành viên"}
              </span>
            </div>
            <WorkspaceStatusHint status={workspace.status} />
          </CardContent>
        </Card>

        {!rolePending && role.kind === "unknown" ? (
          <p className="text-xs text-muted-foreground">
            Danh sách thành viên chưa tải hết nên chưa xác định được vai trò của
            bạn. Các thao tác quản trị tạm đóng cho tới khi xác định xong.
          </p>
        ) : null}
      </div>

      <nav
        aria-label="Mục workspace"
        className="flex gap-1 overflow-x-auto border-b"
      >
        {TABS.filter(
          (tab) => tab.id !== "operations" || canReadOperations(role),
        ).map((tab) => (
          <Link
            key={tab.id}
            to={tab.to}
            params={{ workspaceId }}
            activeOptions={{ exact: tab.exact }}
            className={cn(
              "type-control inline-flex min-h-10 shrink-0 items-center border-b-2 border-transparent px-3 text-muted-foreground transition-colors hover:text-foreground",
            )}
            activeProps={{
              className:
                "border-primary font-semibold text-foreground hover:text-foreground",
            }}
          >
            {tab.label}
          </Link>
        ))}
      </nav>

      <Outlet />

      <WorkspaceFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        workspace={workspace}
      />

      <ConfirmDialog
        open={statusOpen}
        onOpenChange={(open) => {
          if (!updateMutation.isPending) setStatusOpen(open);
        }}
        title={
          nextStatus === "suspended"
            ? "Tạm dừng workspace?"
            : "Kích hoạt lại workspace?"
        }
        description={
          nextStatus === "suspended"
            ? "Thành viên sẽ nhận 403 workspace_suspended khi truy cập nội dung. Dữ liệu và cấu hình được giữ nguyên."
            : "Workspace trở lại trạng thái hoạt động và thành viên truy cập nội dung được bình thường."
        }
        confirmLabel={nextStatus === "suspended" ? "Tạm dừng" : "Kích hoạt"}
        confirmVariant={nextStatus === "suspended" ? "destructive" : "default"}
        isLoading={updateMutation.isPending}
        onConfirm={() => {
          void updateMutation
            .mutateAsync({ status: nextStatus })
            .then(() => {
              setStatusOpen(false);
              toast.success(
                nextStatus === "suspended"
                  ? "Đã tạm dừng workspace."
                  : "Đã kích hoạt lại workspace.",
              );
            })
            .catch((error: unknown) => {
              toast.error(
                error instanceof ApiProblemError
                  ? error.message
                  : "Không đổi được trạng thái workspace.",
              );
            });
        }}
      />

      {canManageMembers(role) ? null : (
        <p className="text-[11px] text-muted-foreground">
          Thao tác quản trị thành viên cần vai trò admin của workspace này;
          quyền toàn hệ thống không được suy ra từ vai trò workspace.
        </p>
      )}
    </div>
  );
}
