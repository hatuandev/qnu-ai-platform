import { useQuery } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { AccessDenied } from "@/components/admin/access-denied";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import type { DataTableFacetOption } from "@/components/admin/data-table/data-table-faceted-filter";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import { loadUsers } from "@/features/users/data";
import { updateUsersStatus } from "@/features/users/operations";
import type { User, UserSort, UserStatus } from "@/features/users/types";
import { UserDetailsDialog } from "@/features/users/user-details-dialog";
import {
  UserFormSheet,
  type UserFormValues,
} from "@/features/users/user-form-sheet";
import { UsersTable } from "@/features/users/users-table";
import { useRbac } from "@/rbac/context";

const statusValues: UserStatus[] = [
  "active",
  "inactive",
  "pending",
  "suspended",
];

export type UsersSearch = {
  q: string;
  create: boolean;
  roles: string;
  statuses: string;
  page: number;
  pageSize: number;
  sort: UserSort;
};

type FormState = { mode: "create" | "edit"; user: User | null } | null;

function compareUsers(a: User, b: User, sort: UserSort) {
  const [field, direction] = sort.split(".") as [
    "name" | "role" | "status" | "createdAt",
    "asc" | "desc",
  ];
  const left =
    field === "createdAt"
      ? new Date(a.createdAt).getTime()
      : a[field].toLowerCase();
  const right =
    field === "createdAt"
      ? new Date(b.createdAt).getTime()
      : b[field].toLowerCase();
  const result = left < right ? -1 : left > right ? 1 : 0;
  return direction === "asc" ? result : -result;
}

function splitFacetParam(value: string) {
  return value ? value.split(",") : [];
}

const statusLabels: Record<UserStatus, string> = {
  active: "Đang hoạt động",
  inactive: "Không hoạt động",
  pending: "Đang chờ",
  suspended: "Tạm khóa",
};

export function UsersPage({
  search,
  onSearchChange,
}: {
  search: UsersSearch;
  onSearchChange: (changes: Partial<UsersSearch>) => void;
}) {
  const { can, roles } = useRbac();
  const query = useQuery({ queryKey: ["users"], queryFn: loadUsers });
  const [localUsers, setLocalUsers] = useState<User[] | null>(null);
  const [formState, setFormState] = useState<FormState>(null);
  const [viewUser, setViewUser] = useState<User | null>(null);
  const [deleteUsers, setDeleteUsers] = useState<User[]>([]);
  const allUsers = localUsers ?? query.data ?? [];
  const roleNames = useMemo(
    () => new Set(roles.map((role) => role.name)),
    [roles],
  );
  const selectedRoles = splitFacetParam(search.roles).filter((role) =>
    roleNames.has(role),
  );
  const selectedStatuses = splitFacetParam(search.statuses);
  const hasActiveFilters = Boolean(
    search.q || selectedRoles.length || selectedStatuses.length,
  );

  const filteredUsers = useMemo(() => {
    const queryText = search.q.trim().toLowerCase();
    return allUsers.filter(
      (user) =>
        (!queryText ||
          user.name.toLowerCase().includes(queryText) ||
          user.email.toLowerCase().includes(queryText)) &&
        (!selectedRoles.length || selectedRoles.includes(user.role)) &&
        (!selectedStatuses.length || selectedStatuses.includes(user.status)),
    );
  }, [allUsers, search.q, selectedRoles, selectedStatuses]);
  const sortedUsers = useMemo(
    () => [...filteredUsers].sort((a, b) => compareUsers(a, b, search.sort)),
    [filteredUsers, search.sort],
  );
  const pageCount = Math.max(
    1,
    Math.ceil(sortedUsers.length / search.pageSize),
  );
  const activePage = Math.min(search.page, pageCount);
  const pageUsers = sortedUsers.slice(
    (activePage - 1) * search.pageSize,
    activePage * search.pageSize,
  );

  const roleFacetBase = allUsers.filter(
    (user) =>
      !selectedStatuses.length || selectedStatuses.includes(user.status),
  );
  const statusFacetBase = allUsers.filter(
    (user) => !selectedRoles.length || selectedRoles.includes(user.role),
  );
  const queryText = search.q.trim().toLowerCase();
  const roleOptions = useMemo<DataTableFacetOption[]>(
    () =>
      roles.map((role) => ({
        value: role.name,
        label: role.name,
        count: roleFacetBase.filter(
          (user) =>
            (!queryText ||
              user.name.toLowerCase().includes(queryText) ||
              user.email.toLowerCase().includes(queryText)) &&
            user.role === role.name,
        ).length,
      })),
    [queryText, roleFacetBase, roles],
  );
  const statusOptions = useMemo<DataTableFacetOption[]>(
    () =>
      statusValues.map((status) => ({
        value: status,
        label: statusLabels[status],
        count: statusFacetBase.filter(
          (user) =>
            (!queryText ||
              user.name.toLowerCase().includes(queryText) ||
              user.email.toLowerCase().includes(queryText)) &&
            user.status === status,
        ).length,
      })),
    [queryText, statusFacetBase],
  );

  const updateSearch = useCallback(
    (changes: Partial<UsersSearch>) => onSearchChange(changes),
    [onSearchChange],
  );
  useEffect(() => {
    if (search.create && can("users.create") && !formState) {
      setFormState({ mode: "create", user: null });
      updateSearch({ create: false });
    }
  }, [can, formState, search.create, updateSearch]);

  if (!can("users.read")) return <AccessDenied />;

  const updateUsers = (updater: (current: User[]) => User[]) =>
    setLocalUsers(updater(localUsers ?? query.data ?? []));
  const createUser = async (values: UserFormValues) => {
    const newUser: User = {
      ...values,
      id:
        typeof crypto.randomUUID === "function"
          ? crypto.randomUUID()
          : `user-${Date.now()}`,
      createdAt: new Date().toISOString(),
    };
    updateUsers((current) => [newUser, ...current]);
    toast.success("Đã tạo lời mời");
    updateSearch({ page: 1 });
  };
  const editUser = async (values: UserFormValues) => {
    if (!formState?.user) return;
    updateUsers((current) =>
      current.map((item) =>
        item.id === formState.user?.id ? { ...item, ...values } : item,
      ),
    );
    toast.success("Đã cập nhật người dùng");
  };
  const confirmDelete = () => {
    const ids = new Set(deleteUsers.map((user) => user.id));
    updateUsers((current) => current.filter((user) => !ids.has(user.id)));
    setDeleteUsers([]);
    toast.success(`Đã xóa ${ids.size} người dùng`);
    updateSearch({ page: 1 });
  };
  const updateUserStatus = (users: User[], status: UserStatus) => {
    updateUsers((current) => updateUsersStatus(current, users, status));
    toast.success(
      `${users.length} người dùng đã chuyển sang trạng thái ${statusLabels[status]}`,
    );
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Quản trị / Quản lý"
        title="Người dùng"
        description="Quản lý quyền truy cập không gian làm việc với danh sách người dùng có tìm kiếm, sắp xếp và phân quyền."
        actions={
          can("users.create") ? (
            <Button
              onClick={() => setFormState({ mode: "create", user: null })}
            >
              <UserPlus />
              Mời người dùng
            </Button>
          ) : null
        }
      />
      <UsersTable
        data={pageUsers}
        totalCount={sortedUsers.length}
        page={activePage}
        pageSize={search.pageSize}
        sort={search.sort}
        isLoading={query.isLoading}
        isError={query.isError}
        errorMessage={
          query.error instanceof Error ? query.error.message : undefined
        }
        hasUsers={allUsers.length > 0}
        hasActiveFilters={hasActiveFilters}
        query={search.q}
        roleOptions={roleOptions}
        statusOptions={statusOptions}
        selectedRoles={selectedRoles}
        selectedStatuses={selectedStatuses}
        canUpdate={can("users.update")}
        canDelete={can("users.delete")}
        onRetry={() => void query.refetch()}
        onQueryChange={(q) => updateSearch({ q, page: 1 })}
        onRolesChange={(roles) =>
          updateSearch({ roles: roles.join(","), page: 1 })
        }
        onStatusesChange={(statuses) =>
          updateSearch({ statuses: statuses.join(","), page: 1 })
        }
        onResetFilters={() =>
          updateSearch({ q: "", roles: "", statuses: "", page: 1 })
        }
        onPageChange={(page) => updateSearch({ page })}
        onPageSizeChange={(pageSize) => updateSearch({ pageSize, page: 1 })}
        onSortChange={(sort) => updateSearch({ sort, page: 1 })}
        onView={setViewUser}
        onEdit={(user) => setFormState({ mode: "edit", user })}
        onDelete={(user) => setDeleteUsers([user])}
        onStatusChange={(user, status) => updateUserStatus([user], status)}
        onBulkUpdate={updateUserStatus}
        onBulkDelete={setDeleteUsers}
      />
      <UserFormSheet
        key={`${formState?.mode ?? "closed"}-${formState?.user?.id ?? "new"}`}
        open={Boolean(formState)}
        onOpenChange={(open) => {
          if (!open) setFormState(null);
        }}
        mode={formState?.mode ?? "create"}
        user={formState?.user}
        onSubmit={formState?.mode === "edit" ? editUser : createUser}
      />
      <UserDetailsDialog
        user={viewUser}
        open={Boolean(viewUser)}
        onOpenChange={(open) => {
          if (!open) setViewUser(null);
        }}
        canUpdate={can("users.update")}
        onEdit={(user) => {
          setViewUser(null);
          setFormState({ mode: "edit", user });
        }}
      />
      <ConfirmDialog
        open={deleteUsers.length > 0}
        onOpenChange={(open) => {
          if (!open) setDeleteUsers([]);
        }}
        title={`Xóa ${deleteUsers.length === 1 ? "người dùng" : `${deleteUsers.length} người dùng`}?`}
        description="Hành động này sẽ xóa người dùng khỏi không gian làm việc demo và không thể hoàn tác."
        confirmLabel="Xóa"
        onConfirm={confirmDelete}
      />
    </div>
  );
}
