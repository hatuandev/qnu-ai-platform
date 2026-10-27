import { Ban, RotateCcw, UserPlus, Users } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { canManageMembers, useV1Auth } from "@/app/auth/v1";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
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
import { MemberFormDialog } from "@/features/workspaces/member-form-dialog";
import {
  useCallerWorkspaceRole,
  useMembersQuery,
  useRevokeMember,
  useUpdateMember,
} from "@/features/workspaces/queries";
import {
  MEMBER_STATUS_LABELS,
  WORKSPACE_ROLE_LABELS,
} from "@/features/workspaces/schemas";
import type {
  MemberStatus,
  WorkspaceMember,
  WorkspaceRole,
} from "@/features/workspaces/types";
import { formatDateTimeValue } from "@/lib/date-utils";

const ROLES: WorkspaceRole[] = ["admin", "editor", "reviewer", "member"];

function statusVariant(status: MemberStatus) {
  if (status === "active") return "success" as const;
  if (status === "pending") return "info" as const;
  return "secondary" as const;
}

export function MembersPanel({
  workspaceId,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
}: {
  workspaceId: string;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}) {
  const { actor } = useV1Auth();
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const query = useMembersQuery(workspaceId, { page, pageSize });
  const updateMutation = useUpdateMember(workspaceId);
  const revokeMutation = useRevokeMember(workspaceId);
  const [addOpen, setAddOpen] = useState(false);
  const [pendingRevoke, setPendingRevoke] = useState<WorkspaceMember | null>(
    null,
  );

  const canManage = canManageMembers(role);
  const total = query.data?.meta.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const items = query.data?.items ?? [];

  const changeRole = (member: WorkspaceMember, nextRole: WorkspaceRole) => {
    if (nextRole === member.role) return;
    void updateMutation
      .mutateAsync({ memberId: member.id, patch: { role: nextRole } })
      .then(() => toast.success("Đã đổi vai trò thành viên."))
      .catch((error: unknown) =>
        toast.error(
          error instanceof ApiProblemError
            ? error.message
            : "Không đổi được vai trò.",
        ),
      );
  };

  const restore = (member: WorkspaceMember) => {
    void updateMutation
      .mutateAsync({ memberId: member.id, patch: { status: "active" } })
      .then(() => toast.success("Đã khôi phục thành viên."))
      .catch((error: unknown) =>
        toast.error(
          error instanceof ApiProblemError
            ? error.message
            : "Không khôi phục được thành viên.",
        ),
      );
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold">Thành viên workspace</h2>
          <p className="text-xs text-muted-foreground">
            Vai trò lấy từ membership do máy chủ trả về và đối chiếu với
            <code className="mx-1 font-mono">actor_id</code>
            của bạn.
          </p>
        </div>
        <Button
          size="sm"
          className="gap-1.5 text-xs font-semibold"
          disabled={!canManage || rolePending}
          onClick={() => setAddOpen(true)}
          title={
            canManage
              ? undefined
              : "Cần vai trò admin của workspace này để thêm thành viên"
          }
        >
          <UserPlus className="size-3.5" />
          <span>Thêm thành viên</span>
        </Button>
      </div>

      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <Card className="overflow-hidden rounded-xl shadow-2xs">
          {query.isLoading ? (
            <div className="grid gap-2 p-4">
              {[0, 1, 2].map((row) => (
                <Skeleton key={row} className="h-11 w-full" />
              ))}
            </div>
          ) : items.length === 0 ? (
            <EmptyState
              icon={Users}
              title="Workspace chưa có thành viên"
              description="Thêm thành viên bằng actor_ref để cấp quyền truy cập workspace này."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>actor_ref</TableHead>
                  <TableHead className="hidden md:table-cell">
                    Tên hiển thị
                  </TableHead>
                  <TableHead className="w-[190px]">Vai trò</TableHead>
                  <TableHead className="w-[140px]">Trạng thái</TableHead>
                  <TableHead className="hidden w-[170px] lg:table-cell">
                    Cập nhật
                  </TableHead>
                  <TableHead className="w-[110px] text-right">
                    <span className="sr-only">Hành động</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((member) => {
                  const isSelf = member.actor_ref === actor?.actor_id;
                  const busy =
                    updateMutation.isPending || revokeMutation.isPending;
                  return (
                    <TableRow key={member.id}>
                      <TableCell className="font-mono text-xs">
                        <span className="flex items-center gap-1.5">
                          {member.actor_ref}
                          {isSelf ? (
                            <Badge variant="outline" className="text-[10px]">
                              bạn
                            </Badge>
                          ) : null}
                        </span>
                      </TableCell>
                      <TableCell className="hidden text-sm md:table-cell">
                        {member.display_name ?? (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {canManage && member.status !== "revoked" ? (
                          <Select
                            value={member.role}
                            onValueChange={(value) =>
                              changeRole(member, value as WorkspaceRole)
                            }
                            disabled={busy}
                          >
                            <SelectTrigger
                              className="h-8 text-xs"
                              aria-label={`Vai trò của ${member.actor_ref}`}
                            >
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {ROLES.map((roleOption) => (
                                <SelectItem
                                  key={roleOption}
                                  value={roleOption}
                                  className="text-xs"
                                >
                                  {WORKSPACE_ROLE_LABELS[roleOption]}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        ) : (
                          <span className="text-xs">
                            {WORKSPACE_ROLE_LABELS[member.role]}
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(member.status)}>
                          {MEMBER_STATUS_LABELS[member.status]}
                        </Badge>
                      </TableCell>
                      <TableCell className="hidden text-xs text-muted-foreground lg:table-cell">
                        {formatDateTimeValue(member.updated_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        {canManage ? (
                          member.status === "revoked" ? (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="gap-1 text-xs"
                              disabled={busy}
                              onClick={() => restore(member)}
                            >
                              <RotateCcw className="size-3.5" />
                              <span>Khôi phục</span>
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="gap-1 text-xs text-destructive"
                              disabled={busy}
                              onClick={() => setPendingRevoke(member)}
                            >
                              <Ban className="size-3.5" />
                              <span>Thu hồi</span>
                            </Button>
                          )
                        ) : null}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
          {items.length > 0 ? (
            <div className="border-t px-3">
              <DataTablePagination
                page={page}
                pageSize={pageSize}
                pageCount={pageCount}
                total={total}
                onPageChange={onPageChange}
                onPageSizeChange={onPageSizeChange}
              />
            </div>
          ) : null}
        </Card>
      )}

      <MemberFormDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        workspaceId={workspaceId}
      />

      <ConfirmDialog
        open={Boolean(pendingRevoke)}
        onOpenChange={(open) => {
          if (!open && !revokeMutation.isPending) setPendingRevoke(null);
        }}
        title="Thu hồi thành viên?"
        description={
          pendingRevoke
            ? `"${pendingRevoke.display_name ?? pendingRevoke.actor_ref}" sẽ mất quyền truy cập workspace. Bản ghi được giữ với trạng thái "Đã thu hồi" và có thể khôi phục sau. Backend từ chối nếu đây là admin cuối cùng.`
            : ""
        }
        confirmLabel="Thu hồi"
        isLoading={revokeMutation.isPending}
        onConfirm={() => {
          if (!pendingRevoke) return;
          void revokeMutation
            .mutateAsync(pendingRevoke.id)
            .then(() => {
              setPendingRevoke(null);
              toast.success("Đã thu hồi thành viên.");
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof ApiProblemError
                  ? error.message
                  : "Không thu hồi được thành viên.",
              ),
            );
        }}
      />
    </div>
  );
}
