import { Link } from "@tanstack/react-router";
import { ArrowLeft, FolderOpen, Plus } from "lucide-react";
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
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow={destination.group}
        title={destination.title}
        description={
          choosingCollection
            ? "Chọn kho để mở chức năng. Lựa chọn này được dùng cho các mục tri thức trên sidebar."
            : "Chọn workspace để mở chức năng. Bạn có thể đổi lựa chọn trên sidebar."
        }
      />
      {choosingCollection && props.workspaceId ? (
        <CollectionChoices
          key={props.workspaceId}
          {...props}
          workspaceId={props.workspaceId}
        />
      ) : (
        <WorkspaceChoices {...props} />
      )}
    </div>
  );
}

function WorkspaceChoices({ feature, page, onPageChange }: Props) {
  const query = useWorkspacesQuery({ page, pageSize: 20 });
  const { actor } = useV1Auth();
  const canCreate = isPlatformWorkspaceAdmin(actor);
  const [creating, setCreating] = useState(false);
  const destination = workspaceFeatures[feature];
  if (query.isPending) return <Skeleton className="h-32 w-full" />;
  if (query.isError)
    return (
      <ErrorState error={query.error} onRetry={() => void query.refetch()} />
    );
  return (
    <>
      <div className="flex flex-wrap justify-end gap-2">
        <Button asChild variant="outline" size="sm">
          <Link to="/workspaces" search={{ page: 1, pageSize: 20 }}>
            Quản lý workspace
          </Link>
        </Button>
        {canCreate && (
          <Button size="sm" onClick={() => setCreating(true)}>
            <Plus className="size-4" />
            Tạo workspace
          </Button>
        )}
      </div>
      <Card>
        <CardContent className="p-4">
          {query.data.items.length === 0 ? (
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
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {query.data.items.map((workspace) => (
                <div
                  key={workspace.id}
                  className="rounded-lg border p-4 space-y-3"
                >
                  <div>
                    <h2 className="font-semibold break-words">
                      {workspace.name}
                    </h2>
                    <p className="text-xs text-muted-foreground">
                      {workspace.code}
                    </p>
                  </div>
                  {workspace.status === "suspended" ? (
                    <>
                      <Badge variant="warning">Tạm dừng</Badge>
                      <Button variant="outline" size="sm" asChild>
                        <Link
                          to="/workspaces/$workspaceId"
                          params={{ workspaceId: workspace.id }}
                        >
                          Quản lý trạng thái
                        </Link>
                      </Button>
                    </>
                  ) : (
                    <Button asChild size="sm" className="w-full">
                      {destination.kind === "collection" ? (
                        <Link
                          to="/workspaces/choose/$feature"
                          params={{ feature }}
                          search={{ workspaceId: workspace.id, page: 1 }}
                        >
                          Chọn {workspace.name}
                        </Link>
                      ) : (
                        <Link
                          {...featureTarget(feature, {
                            workspaceId: workspace.id,
                          })}
                        >
                          Mở {destination.title}
                        </Link>
                      )}
                    </Button>
                  )}
                </div>
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
              label="workspace"
            />
          )}
        </CardContent>
      </Card>
      {creating && <WorkspaceFormDialog open onOpenChange={setCreating} />}
    </>
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
  if (query.isPending || workspace.isPending)
    return <Skeleton className="h-32 w-full" />;
  if (query.isError || workspace.isError)
    return (
      <ErrorState
        error={query.error ?? workspace.error}
        onRetry={() => {
          void query.refetch();
          void workspace.refetch();
        }}
      />
    );
  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-medium">{workspace.data?.name}</p>
          <Link
            className="text-xs text-primary hover:underline"
            to="/workspaces/choose/$feature"
            params={{ feature }}
            search={{ page: 1 }}
          >
            <ArrowLeft className="mr-1 inline size-3" />
            Đổi workspace
          </Link>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link
              to="/workspaces/$workspaceId/collections"
              params={{ workspaceId }}
              search={{ page: 1, pageSize: 20 }}
            >
              Quản lý kho
            </Link>
          </Button>
          {canCreate && (
            <Button size="sm" onClick={() => setCreating(true)}>
              <Plus className="size-4" />
              Tạo kho
            </Button>
          )}
        </div>
      </div>
      <Card>
        <CardContent className="p-4">
          {query.data.items.length === 0 ? (
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
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {query.data.items.map((collection) => (
                <div
                  key={collection.id}
                  className="rounded-lg border p-4 space-y-3"
                >
                  <div>
                    <h2 className="font-semibold break-words">
                      {collection.name}
                    </h2>
                    <p className="text-xs text-muted-foreground">
                      {collection.source_count} nguồn tài liệu
                    </p>
                  </div>
                  <Button asChild size="sm" className="w-full">
                    <Link
                      {...featureTarget(feature, {
                        workspaceId,
                        collectionId: collection.id,
                      })}
                    >
                      Mở {collection.name}
                    </Link>
                  </Button>
                </div>
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
        </CardContent>
      </Card>
      {creating && (
        <CollectionFormDialog
          open
          onOpenChange={setCreating}
          workspaceId={workspaceId}
        />
      )}
    </>
  );
}
