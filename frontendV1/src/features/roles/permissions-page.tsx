import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { AccessDenied } from "@/components/admin/access-denied";
import { DataTableEmpty } from "@/components/admin/data-table/data-table-empty";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  getPermissionGroups,
  PermissionEditor,
} from "@/features/roles/permission-editor";
import { type PermissionKey, permissionCatalog } from "@/rbac/catalog";
import { useRbac } from "@/rbac/context";

function samePermissions(left: PermissionKey[], right: PermissionKey[]) {
  return (
    left.length === right.length &&
    left.every((permission) => right.includes(permission))
  );
}

export function PermissionsPage() {
  const { can, roles, updateRole } = useRbac();
  const [query, setQuery] = useState("");
  const [selectedRoleKey, setSelectedRoleKey] = useState(roles[0]?.key ?? "");
  const [draftPermissions, setDraftPermissions] = useState<PermissionKey[]>([]);
  const selectedRole =
    roles.find((role) => role.key === selectedRoleKey) ?? roles[0];
  const canEdit = can("roles.update");

  useEffect(() => {
    setSelectedRoleKey((current) =>
      roles.some((role) => role.key === current)
        ? current
        : (roles[0]?.key ?? ""),
    );
  }, [roles]);
  useEffect(() => {
    setDraftPermissions(selectedRole?.permissions ?? []);
  }, [selectedRole?.permissions]);

  const normalizedQuery = query.trim().toLowerCase();
  const visibleGroups = useMemo(
    () =>
      getPermissionGroups()
        .map((group) => ({
          ...group,
          items: group.items.filter((permission) =>
            [
              permission.label,
              permission.key,
              permission.description,
              permission.resource,
              permission.resourceLabel,
            ].some((part) => part.toLowerCase().includes(normalizedQuery)),
          ),
        }))
        .filter((group) => group.items.length),
    [normalizedQuery],
  );
  const isDirty = Boolean(
    selectedRole &&
      !samePermissions(draftPermissions, selectedRole.permissions),
  );

  if (!can("permissions.read")) return <AccessDenied />;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Quản trị / Quản lý"
        title="Quyền hạn"
        description="Xem danh mục quyền RBAC và điều chỉnh quyền hạn theo từng vai trò."
      />
      <section className="space-y-4 rounded-lg border bg-card p-4 sm:p-5">
        <div className="flex flex-col gap-1">
          <h2 className="text-base font-semibold">
            Trình chỉnh sửa quyền theo vai trò
          </h2>
          <p className="text-sm text-muted-foreground">
            Chọn một vai trò để xem hoặc cập nhật các quyền được gán.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:max-w-sm">
          <Label htmlFor="permission-role">Vai trò</Label>
          <Select
            value={selectedRole?.key ?? ""}
            onValueChange={setSelectedRoleKey}
          >
            <SelectTrigger id="permission-role" aria-label="Chọn vai trò">
              <SelectValue placeholder="Chọn vai trò" />
            </SelectTrigger>
            <SelectContent>
              {roles.map((role) => (
                <SelectItem key={role.id} value={role.key}>
                  {role.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {selectedRole ? (
          <>
            <PermissionEditor
              value={draftPermissions}
              onChange={setDraftPermissions}
              disabled={!canEdit}
            />
            <div className="flex flex-col-reverse gap-2 border-t pt-4 sm:flex-row sm:justify-end">
              <Button
                variant="outline"
                disabled={!isDirty}
                onClick={() => setDraftPermissions(selectedRole.permissions)}
              >
                Hủy thay đổi
              </Button>
              <Button
                disabled={!canEdit || !isDirty}
                onClick={() => {
                  updateRole(selectedRole.id, {
                    permissions: draftPermissions,
                  });
                  toast.success("Đã lưu quyền hạn cho vai trò");
                }}
              >
                Lưu thay đổi
              </Button>
            </div>
            {!canEdit ? (
              <p className="text-sm text-muted-foreground">
                Bạn chỉ có quyền xem. Cần quyền{" "}
                <span className="font-mono text-xs">roles.update</span> để chỉnh
                sửa.
              </p>
            ) : null}
          </>
        ) : (
          <DataTableEmpty
            title="Chưa có vai trò để chỉnh sửa"
            description="Hãy tạo vai trò trước khi gán quyền."
          />
        )}
      </section>
      <section className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-base font-semibold">Danh mục quyền</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Nguồn quyền duy nhất được định nghĩa trong RBAC catalog.
            </p>
          </div>
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tìm kiếm quyền hạn..."
            aria-label="Tìm kiếm danh mục quyền hạn"
            className="sm:max-w-sm"
          />
        </div>
        {visibleGroups.length ? (
          <div className="rounded-lg border bg-card">
            {visibleGroups.map((group, groupIndex) => (
              <section key={group.resource} className="px-4 py-4 sm:px-5">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold">{group.label}</h3>
                    <p className="text-xs text-muted-foreground">
                      {group.resource}
                    </p>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {group.items.length} quyền
                  </span>
                </div>
                <div className="divide-y rounded-md border">
                  {group.items.map((permission) => (
                    <div
                      key={permission.key}
                      className="grid gap-1 px-3 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] sm:gap-4"
                    >
                      <div>
                        <p className="text-sm font-semibold">
                          {permission.label}
                        </p>
                        <p className="type-metadata font-mono text-muted-foreground">
                          {permission.key}
                        </p>
                      </div>
                      <p className="type-supporting text-muted-foreground">
                        {permission.description}
                      </p>
                    </div>
                  ))}
                </div>
                {groupIndex < visibleGroups.length - 1 ? (
                  <Separator className="mt-4" />
                ) : null}
              </section>
            ))}
          </div>
        ) : (
          <DataTableEmpty
            title="Không tìm thấy quyền hạn phù hợp"
            description="Hãy thử từ khóa khác."
          />
        )}
      </section>
      <p className="text-xs text-muted-foreground">
        {permissionCatalog.length} quyền hạn trong catalog · Không thể tạo hoặc
        xóa permission từ giao diện.
      </p>
    </div>
  );
}
