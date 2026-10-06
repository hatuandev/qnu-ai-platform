import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { AccessDenied } from "@/components/admin/access-denied";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import { RoleDetailsSheet } from "@/features/roles/role-details-sheet";
import {
  type RoleFormMode,
  RoleFormSheet,
  type RoleFormValues,
} from "@/features/roles/role-form-sheet";
import { RolesTable } from "@/features/roles/roles-table";
import type { PermissionKey } from "@/rbac/catalog";
import type { RoleInput } from "@/rbac/context";
import { useRbac } from "@/rbac/context";
import type { RoleRecord } from "@/rbac/demo";

export type RolesSearch = {
  q: string;
  create: boolean;
  type: "" | "system" | "custom";
  status: "" | "active" | "inactive";
  page: number;
  pageSize: number;
  sort:
    | "name.asc"
    | "name.desc"
    | "userCount.asc"
    | "userCount.desc"
    | "permissions.asc"
    | "permissions.desc"
    | "status.asc"
    | "status.desc";
};

type FormState = {
  mode: RoleFormMode;
  role: RoleRecord | null;
} | null;

function compareRoles(a: RoleRecord, b: RoleRecord, sort: string) {
  const [field, direction] = sort.split(".") as [
    "name" | "userCount" | "permissions" | "status",
    "asc" | "desc",
  ];
  const left =
    field === "name" || field === "status"
      ? (field === "status" ? a.status : a.name).toLowerCase()
      : field === "permissions"
        ? a.permissions.length
        : a.userCount;
  const right =
    field === "name" || field === "status"
      ? (field === "status" ? b.status : b.name).toLowerCase()
      : field === "permissions"
        ? b.permissions.length
        : b.userCount;
  const result = left < right ? -1 : left > right ? 1 : 0;
  return direction === "asc" ? result : -result;
}

function makeUniqueKey(roles: RoleRecord[], base: string) {
  const keys = new Set(roles.map((role) => role.key));
  if (!keys.has(base)) return base;
  let index = 2;
  while (keys.has(`${base}_${index}`)) index += 1;
  return `${base}_${index}`;
}

export function RolesPage({
  search,
  onSearchChange,
}: {
  search: RolesSearch;
  onSearchChange: (changes: Partial<RolesSearch>) => void;
}) {
  const { can, roles, createRole, updateRole, deleteRole } = useRbac();
  const [formState, setFormState] = useState<FormState>(null);
  const [viewRole, setViewRole] = useState<RoleRecord | null>(null);
  const [pendingDelete, setPendingDelete] = useState<RoleRecord | null>(null);

  const queryText = search.q.trim().toLowerCase();
  const filteredRoles = useMemo(
    () =>
      roles.filter((role) => {
        const matchesQuery = [role.name, role.key, role.description]
          .join(" ")
          .toLowerCase()
          .includes(queryText);
        const matchesType =
          !search.type ||
          (search.type === "system" ? role.isSystem : !role.isSystem);
        const matchesStatus = !search.status || role.status === search.status;
        return matchesQuery && matchesType && matchesStatus;
      }),
    [queryText, roles, search.status, search.type],
  );
  const sortedRoles = useMemo(
    () => [...filteredRoles].sort((a, b) => compareRoles(a, b, search.sort)),
    [filteredRoles, search.sort],
  );
  const pageCount = Math.max(
    1,
    Math.ceil(sortedRoles.length / search.pageSize),
  );
  const activePage = Math.min(search.page, pageCount);
  const pageRoles = sortedRoles.slice(
    (activePage - 1) * search.pageSize,
    activePage * search.pageSize,
  );
  const hasActiveFilters = Boolean(search.q || search.type || search.status);
  const updateSearch = useCallback(
    (changes: Partial<RolesSearch>) => onSearchChange(changes),
    [onSearchChange],
  );

  useEffect(() => {
    if (search.create && can("roles.create") && !formState) {
      setFormState({ mode: "create", role: null });
      updateSearch({ create: false });
    }
  }, [can, formState, search.create, updateSearch]);
  const typeOptions = useMemo(
    () => [
      {
        value: "system",
        label: "Hệ thống",
        count: roles.filter((role) => role.isSystem).length,
      },
      {
        value: "custom",
        label: "Tùy chỉnh",
        count: roles.filter((role) => !role.isSystem).length,
      },
    ],
    [roles],
  );
  const statusOptions = useMemo(
    () => [
      {
        value: "active",
        label: "Đang hoạt động",
        count: roles.filter((role) => role.status === "active").length,
      },
      {
        value: "inactive",
        label: "Không hoạt động",
        count: roles.filter((role) => role.status === "inactive").length,
      },
    ],
    [roles],
  );

  if (!can("roles.read")) return <AccessDenied />;

  const saveRole = async (
    values: RoleFormValues,
    permissions: PermissionKey[],
  ) => {
    const current = formState?.role;
    const duplicate = roles.some(
      (role) => role.key === values.key && role.id !== current?.id,
    );
    if (duplicate) {
      toast.error("Role key đã tồn tại. Hãy chọn một key khác.");
      throw new Error("Role key đã tồn tại");
    }
    const input: RoleInput = { ...values, permissions };
    if (formState?.mode === "edit" && current) {
      updateRole(current.id, input);
      toast.success("Đã cập nhật vai trò");
    } else {
      createRole({ ...input, key: makeUniqueKey(roles, input.key) });
      toast.success(
        formState?.mode === "duplicate"
          ? "Đã nhân bản vai trò"
          : "Đã tạo vai trò",
      );
    }
  };
  const confirmDelete = () => {
    if (!pendingDelete) return;
    if (pendingDelete.userCount > 0) {
      toast.error("Không thể xóa vai trò đang được gán cho người dùng.");
      setPendingDelete(null);
      return;
    }
    if (deleteRole(pendingDelete.id)) toast.success("Đã xóa vai trò");
    else toast.error("Vai trò hệ thống không thể bị xóa.");
    setPendingDelete(null);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Quản trị / Quản lý"
        title="Vai trò"
        description="Quản lý các cấp độ truy cập và quyền hạn được gán cho từng vai trò."
        actions={
          can("roles.create") ? (
            <Button
              onClick={() => setFormState({ mode: "create", role: null })}
            >
              Tạo vai trò
            </Button>
          ) : null
        }
      />
      <RolesTable
        data={pageRoles}
        totalCount={sortedRoles.length}
        page={activePage}
        pageSize={search.pageSize}
        sort={search.sort}
        query={search.q}
        type={search.type}
        status={search.status}
        typeOptions={typeOptions}
        statusOptions={statusOptions}
        isLoading={false}
        isError={false}
        hasRoles={roles.length > 0}
        hasActiveFilters={hasActiveFilters}
        onQueryChange={(q) => updateSearch({ q, page: 1 })}
        onTypeChange={(values) =>
          updateSearch({
            type: (values[0] ?? "") as RolesSearch["type"],
            page: 1,
          })
        }
        onStatusChange={(values) =>
          updateSearch({
            status: (values[0] ?? "") as RolesSearch["status"],
            page: 1,
          })
        }
        onResetFilters={() =>
          updateSearch({ q: "", type: "", status: "", page: 1 })
        }
        onPageChange={(page) => updateSearch({ page })}
        onPageSizeChange={(pageSize) => updateSearch({ pageSize, page: 1 })}
        onSortChange={(sort) =>
          updateSearch({ sort: sort as RolesSearch["sort"], page: 1 })
        }
        canUpdate={can("roles.update")}
        canCreate={can("roles.create")}
        canDelete={can("roles.delete")}
        onView={setViewRole}
        onEdit={(role) => setFormState({ mode: "edit", role })}
        onDuplicate={(role) => setFormState({ mode: "duplicate", role })}
        onDelete={setPendingDelete}
      />
      <RoleDetailsSheet
        role={viewRole}
        open={Boolean(viewRole)}
        onOpenChange={(open) => {
          if (!open) setViewRole(null);
        }}
        canUpdate={can("roles.update")}
        canCreate={can("roles.create")}
        canDelete={can("roles.delete")}
        onEdit={(role) => {
          setViewRole(null);
          setFormState({ mode: "edit", role });
        }}
        onDuplicate={(role) => {
          setViewRole(null);
          setFormState({ mode: "duplicate", role });
        }}
        onDelete={(role) => {
          setViewRole(null);
          setPendingDelete(role);
        }}
      />
      <RoleFormSheet
        key={`${formState?.mode ?? "closed"}-${formState?.role?.id ?? "new"}`}
        open={Boolean(formState)}
        onOpenChange={(open) => {
          if (!open) setFormState(null);
        }}
        mode={formState?.mode ?? "create"}
        role={formState?.role}
        onSubmit={saveRole}
      />
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null);
        }}
        title="Xóa vai trò?"
        description={
          pendingDelete?.userCount
            ? `Vai trò này đang được gán cho ${pendingDelete.userCount} người dùng và không thể xóa.`
            : `Vai trò ${pendingDelete?.name ?? "này"} sẽ bị xóa khỏi dữ liệu demo và không thể hoàn tác.`
        }
        confirmLabel="Xóa vai trò"
        onConfirm={confirmDelete}
      />
    </div>
  );
}
