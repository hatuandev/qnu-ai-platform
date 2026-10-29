import { Link } from "@tanstack/react-router";
import { ArrowLeft, Boxes, ChevronRight, FolderOpen, Plus } from "lucide-react";
import { useState } from "react";
import { isPlatformWorkspaceAdmin, useV1Auth } from "@/app/auth/v1";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CollectionFormDialog } from "@/features/knowledge/collection-form-dialog";
import { ListPagination } from "@/features/knowledge/list-pagination";
import { canManageKnowledge } from "@/features/knowledge/permissions";
import { useCollectionsQuery } from "@/features/knowledge/queries";
import {
  useCallerWorkspaceRole,
  useWorkspaceQuery,
  useWorkspacesQuery,
} from "@/features/workspaces/queries";
import {
  featureTarget,
  type WorkspaceFeature,
  workspaceFeatures,
} from "@/navigation/workspace-features";
import { WorkspaceFormDialog } from "./workspace-form-dialog";

type Props = {
  feature: WorkspaceFeature;
  workspaceId?: string;
  page: number;
  onPageChange: (page: number) => void;
};
export function FeatureEntryPage(props: Props) {
  const destination = workspaceFeatures[props.feature];
  const choosingCollection = Boolean(
    props.workspaceId && destination.kind === "collection",
  );
  return choosingCollection && props.workspaceId ? (
    <CollectionChoices
      key={props.workspaceId}
      {...props}
      workspaceId={props.workspaceId}
    />
  ) : (
    <WorkspaceChoices {...props} />
  );
}

function WorkspaceChoices({ feature, page, onPageChange }: Props) {
  const query = useWorkspacesQuery({ page, pageSize: 20 });
  const { actor } = useV1Auth();
  const canCreate = isPlatformWorkspaceAdmin(actor);
  const [creating, setCreating] = useState(false);
  const destination = workspaceFeatures[feature];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={destination.group}
        title={destination.title}
        description="Chọn đơn vị (workspace) để mở chức năng tương ứng."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button asChild variant="outline" size="sm" className="h-9 text-xs">
              <Link to="/workspaces" search={{ page: 1, pageSize: 20 }}>
                Quản lý workspace
              </Link>
            </Button>
            {canCreate && (
              <Button
                size="sm"
                className="h-9 text-xs gap-1.5"
                onClick={() => setCreating(true)}
              >
                <Plus className="size-3.5" />
                <span>Tạo workspace</span>
              </Button>
            )}
          </div>
        }
      />

      {query.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
        </div>
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : query.data.items.length === 0 ? (
        <Card className="rounded-xl border-border/70 shadow-2xs">
          <CardContent className="py-12">
            <EmptyState
              icon={FolderOpen}
              title="Chưa có workspace"
              description={
                canCreate
                  ? "Tạo workspace đầu tiên để bắt đầu."
                  : "Liên hệ quản trị viên để được cấp quyền workspace."
              }
              action={
                canCreate
                  ? { label: "Tạo workspace", onClick: () => setCreating(true) }
                  : undefined
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {query.data.items.map((workspace) => (
            <Card
              key={workspace.id}
              className="group rounded-xl border-border/70 p-4 flex flex-col justify-between gap-4 shadow-2xs hover:border-primary/40 transition-all"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Boxes className="size-4" />
                  </span>
                  <div className="min-w-0">
                    <h2 className="font-semibold text-sm text-foreground break-words">
                      {workspace.name}
                    </h2>
                    {workspace.code ? (
                      <p className="text-xs text-muted-foreground font-mono">
                        {workspace.code}
                      </p>
                    ) : null}
                  </div>
                </div>
                {workspace.status === "suspended" ? (
                  <Badge variant="warning" className="shrink-0">
                    Tạm dừng
                  </Badge>
                ) : null}
              </div>

              <div className="pt-3 border-t border-border/50 flex items-center justify-end">
                {workspace.status === "suspended" ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs w-full"
                    asChild
                  >
                    <Link
                      to="/workspaces/$workspaceId"
                      params={{ workspaceId: workspace.id }}
                    >
                      Quản lý trạng thái
                    </Link>
                  </Button>
                ) : (
                  <Button
                    asChild
                    size="sm"
                    variant="secondary"
                    className="h-8 text-xs w-full justify-between"
                  >
                    {destination.kind === "collection" ? (
                      <Link
                        to="/workspaces/choose/$feature"
                        params={{ feature }}
                        search={{ workspaceId: workspace.id, page: 1 }}
                      >
                        <span>Chọn {workspace.name}</span>
                        <ChevronRight className="size-3.5" />
                      </Link>
                    ) : (
                      <Link
                        {...featureTarget(feature, {
                          workspaceId: workspace.id,
                        })}
                      >
                        <span>Mở {destination.title}</span>
                        <ChevronRight className="size-3.5" />
                      </Link>
                    )}
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {query.data && query.data.meta.total > 20 && (
        <ListPagination
          page={page}
          pageSize={20}
          hasNext={page * 20 < query.data.meta.total}
          onPageChange={onPageChange}
          disabled={query.isFetching}
          label="workspace"
        />
      )}
      {creating && <WorkspaceFormDialog open onOpenChange={setCreating} />}
    </div>
  );
}

function CollectionChoices({
  feature,
  workspaceId,
  page,
  onPageChange,
}: Props & { workspaceId: string }) {
  const query = useCollectionsQuery(workspaceId, { page, pageSize: 20 });
  const workspace = useWorkspaceQuery(workspaceId);
  const access = useCallerWorkspaceRole(workspaceId);
  const canCreate = !access.isPending && canManageKnowledge(access.role);
  const [creating, setCreating] = useState(false);
  const destination = workspaceFeatures[feature];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={destination.group}
        title={destination.title}
        description="Chọn kho tri thức để mở chức năng tương ứng."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" className="h-9 text-xs" asChild>
              <Link
                to="/workspaces/$workspaceId/collections"
                params={{ workspaceId }}
                search={{ page: 1, pageSize: 20 }}
              >
                Quản lý kho
              </Link>
            </Button>
            {canCreate && (
              <Button
                size="sm"
                className="h-9 text-xs gap-1.5"
                onClick={() => setCreating(true)}
              >
                <Plus className="size-3.5" />
                <span>Tạo kho</span>
              </Button>
            )}
          </div>
        }
      />

      {query.isPending || workspace.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
        </div>
      ) : query.isError || workspace.isError ? (
        <ErrorState
          error={query.error ?? workspace.error}
          onRetry={() => {
            void query.refetch();
            void workspace.refetch();
          }}
        />
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-border/60 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Đơn vị đang chọn:</span>
              <span className="font-semibold text-foreground">
                {workspace.data?.name}
              </span>
            </div>
            <Link
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
              to="/workspaces/choose/$feature"
              params={{ feature }}
              search={{ page: 1 }}
            >
              <ArrowLeft className="size-3" />
              <span>Đổi workspace</span>
            </Link>
          </div>

          {query.data.items.length === 0 ? (
            <Card className="rounded-xl border-border/70 shadow-2xs">
              <CardContent className="py-12">
                <EmptyState
                  icon={FolderOpen}
                  title="Chưa có kho tri thức"
                  description={
                    canCreate
                      ? "Workspace này chưa có kho. Tạo kho, tải tài liệu lên rồi tiếp tục xử lý."
                      : "Liên hệ quản trị viên để thêm kho tri thức."
                  }
                  action={
                    canCreate
                      ? {
                          label: "Tạo kho đầu tiên",
                          onClick: () => setCreating(true),
                        }
                      : undefined
                  }
                />
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {query.data.items.map((collection) => (
                <Card
                  key={collection.id}
                  className="group rounded-xl border-border/70 p-4 flex flex-col justify-between gap-4 shadow-2xs hover:border-primary/40 transition-all"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <FolderOpen className="size-4" />
                    </span>
                    <div className="min-w-0">
                      <h2 className="font-semibold text-sm text-foreground break-words">
                        {collection.name}
                      </h2>
                      <p className="text-xs text-muted-foreground">
                        {collection.source_count} nguồn tài liệu
                      </p>
                    </div>
                  </div>
                  <div className="pt-3 border-t border-border/50">
                    <Button
                      asChild
                      size="sm"
                      variant="secondary"
                      className="h-8 text-xs w-full justify-between"
                    >
                      <Link
                        {...featureTarget(feature, {
                          workspaceId,
                          collectionId: collection.id,
                        })}
                      >
                        <span className="truncate">Mở {collection.name}</span>
                        <ChevronRight className="size-3.5 shrink-0" />
                      </Link>
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {query.data.meta.total > 20 && (
            <ListPagination
              page={page}
              pageSize={20}
              hasNext={page * 20 < query.data.meta.total}
              onPageChange={onPageChange}
              disabled={query.isFetching}
              label="kho tri thức"
            />
          )}
        </>
      )}

      {creating && (
        <CollectionFormDialog
          open
          onOpenChange={setCreating}
          workspaceId={workspaceId}
        />
      )}
    </div>
  );
}
