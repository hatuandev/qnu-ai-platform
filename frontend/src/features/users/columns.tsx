import type { ColumnDef } from "@tanstack/react-table";
import {
  CheckCircle2,
  CircleOff,
  MoreHorizontal,
  PauseCircle,
  Trash2,
} from "lucide-react";
import { DataTableColumnHeader } from "@/components/admin/data-table-column-header";
import { StatusBadge } from "@/components/admin/status-badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { User, UserStatus } from "@/features/users/types";
import { formatDateValue } from "@/lib/date-utils";

function initials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function statusAction(user: User, status: UserStatus) {
  if (user.status === status) return null;
  const actions: Record<
    UserStatus,
    { label: string; icon: typeof CheckCircle2 }
  > = {
    active: { label: "Kích hoạt người dùng", icon: CheckCircle2 },
    inactive: { label: "Vô hiệu hóa người dùng", icon: CircleOff },
    pending: { label: "Giữ trạng thái chờ", icon: PauseCircle },
    suspended: { label: "Tạm khóa người dùng", icon: PauseCircle },
  };
  const action = actions[status];
  if (status === "pending") return null;
  return action;
}

export function createUserColumns({
  canUpdate,
  canDelete,
  onView,
  onEdit,
  onDelete,
  onStatusChange,
}: {
  canUpdate: boolean;
  canDelete: boolean;
  onView: (user: User) => void;
  onEdit: (user: User) => void;
  onDelete: (user: User) => void;
  onStatusChange: (user: User, status: UserStatus) => void;
}): ColumnDef<User>[] {
  return [
    {
      id: "select",
      header: ({ table }) => (
        <Checkbox
          aria-label="Chọn tất cả dòng"
          checked={
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() && "indeterminate")
          }
          onCheckedChange={(value) =>
            table.toggleAllPageRowsSelected(Boolean(value))
          }
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          aria-label={`Chọn ${row.original.name}`}
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(Boolean(value))}
        />
      ),
      enableSorting: false,
      enableHiding: false,
      size: 36,
    },
    {
      accessorKey: "name",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Người dùng" />
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-2.5">
          <Avatar>
            <AvatarFallback>{initials(row.original.name)}</AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-foreground">
              {row.original.name}
            </div>
            <div className="truncate text-xs text-muted-foreground">
              {row.original.email}
            </div>
          </div>
        </div>
      ),
    },
    {
      accessorKey: "role",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Vai trò" />
      ),
    },
    {
      accessorKey: "status",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Trạng thái" />
      ),
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: "createdAt",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Ngày tạo" />
      ),
      cell: ({ row }) => formatDateValue(row.original.createdAt),
    },
    {
      id: "actions",
      enableHiding: false,
      enableSorting: false,
      cell: ({ row }) => {
        const user = row.original;
        const statusItems = canUpdate
          ? (["active", "inactive", "suspended"] as UserStatus[])
              .map((status) => ({ status, action: statusAction(user, status) }))
              .filter(
                (
                  item,
                ): item is {
                  status: UserStatus;
                  action: NonNullable<ReturnType<typeof statusAction>>;
                } => item.action !== null,
              )
          : [];

        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={`Thao tác với ${user.name}`}
              >
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Thao tác</DropdownMenuLabel>
              <DropdownMenuItem onSelect={() => onView(user)}>
                Xem chi tiết
              </DropdownMenuItem>
              {canUpdate ? (
                <DropdownMenuItem onSelect={() => onEdit(user)}>
                  Chỉnh sửa người dùng
                </DropdownMenuItem>
              ) : null}
              {statusItems.length ? (
                <>
                  <DropdownMenuSeparator />
                  {statusItems.map(({ status, action }) => {
                    const Icon = action.icon;
                    return (
                      <DropdownMenuItem
                        key={status}
                        onSelect={() => onStatusChange(user, status)}
                      >
                        <Icon />
                        {action.label}
                      </DropdownMenuItem>
                    );
                  })}
                </>
              ) : null}
              {canDelete ? (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    variant="destructive"
                    onSelect={() => onDelete(user)}
                  >
                    <Trash2 />
                    Xóa người dùng
                  </DropdownMenuItem>
                </>
              ) : null}
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ];
}
