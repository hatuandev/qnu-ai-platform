import { Link } from "@tanstack/react-router";
import { Copy, Pencil, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { getPermissionGroups } from "@/features/roles/permission-editor";
import type { RoleRecord } from "@/rbac/demo";
import { roleTypeLabel } from "@/rbac/policy";

export function RoleDetailsSheet({
  role,
  open,
  onOpenChange,
  canUpdate,
  canCreate,
  canDelete,
  onEdit,
  onDuplicate,
  onDelete,
}: {
  role: RoleRecord | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  canUpdate: boolean;
  canCreate: boolean;
  canDelete: boolean;
  onEdit: (role: RoleRecord) => void;
  onDuplicate: (role: RoleRecord) => void;
  onDelete: (role: RoleRecord) => void;
}) {
  if (!role) return null;
  const selected = new Set(role.permissions);
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex flex-col overflow-hidden sm:max-w-lg"
      >
        <SheetHeader className="border-b px-5 pb-4">
          <SheetTitle>{role.name}</SheetTitle>
          <SheetDescription>{role.description}</SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-5">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-xs text-muted-foreground">Role key</dt>
              <dd className="mt-1 font-mono text-xs">{role.key}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Loại</dt>
              <dd className="mt-1">
                <Badge variant={role.isSystem ? "secondary" : "outline"}>
                  {roleTypeLabel(role)}
                </Badge>
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Trạng thái</dt>
              <dd className="mt-1">
                <Badge
                  variant={role.status === "active" ? "success" : "secondary"}
                >
                  {role.status === "active"
                    ? "Đang hoạt động"
                    : "Không hoạt động"}
                </Badge>
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Người dùng</dt>
              <dd className="mt-1 font-medium">{role.userCount}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Quyền hạn</dt>
              <dd className="mt-1 font-medium">{role.permissions.length}</dd>
            </div>
          </dl>
          <div>
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold">Tóm tắt quyền hạn</h2>
              <Link
                to="/users"
                search={{
                  q: "",
                  create: false,
                  roles: role.name,
                  statuses: "",
                  page: 1,
                  pageSize: 10,
                  sort: "createdAt.desc",
                }}
                className="text-xs font-medium text-primary hover:underline"
              >
                Xem người dùng
              </Link>
            </div>
            <div className="space-y-4">
              {getPermissionGroups().map((group) => {
                const items = group.items.filter((permission) =>
                  selected.has(permission.key),
                );
                if (!items.length) return null;
                return (
                  <section key={group.resource}>
                    <h3 className="text-sm font-medium">{group.label}</h3>
                    <ul className="mt-1 space-y-1 text-sm text-muted-foreground">
                      {items.map((permission) => (
                        <li
                          key={permission.key}
                          className="flex items-center gap-2"
                        >
                          <span className="size-1.5 rounded-full bg-primary" />
                          {permission.label}
                        </li>
                      ))}
                    </ul>
                  </section>
                );
              })}
            </div>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2 border-t bg-background px-5 py-4">
          {canUpdate ? (
            <Button onClick={() => onEdit(role)}>
              <Pencil />
              Chỉnh sửa
            </Button>
          ) : null}
          {canCreate ? (
            <Button variant="outline" onClick={() => onDuplicate(role)}>
              <Copy />
              Nhân bản
            </Button>
          ) : null}
          {canDelete && !role.isSystem ? (
            <Button
              variant="outline"
              className="text-destructive"
              onClick={() => onDelete(role)}
            >
              <Trash2 />
              Xóa
            </Button>
          ) : null}
        </div>
      </SheetContent>
    </Sheet>
  );
}
