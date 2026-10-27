import { Mail, Pencil, UserRound } from "lucide-react";
import { StatusBadge } from "@/components/admin/status-badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { User } from "@/features/users/types";
import { formatDateValue } from "@/lib/date-utils";

function initials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function UserDetailsDialog({
  user,
  open,
  onOpenChange,
  canUpdate,
  onEdit,
}: {
  user: User | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  canUpdate: boolean;
  onEdit: (user: User) => void;
}) {
  if (!user) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Chi tiết người dùng</DialogTitle>
          <DialogDescription>
            Xem hồ sơ, vai trò và trạng thái tài khoản của người dùng này.
          </DialogDescription>
        </DialogHeader>
        <div className="flex items-center gap-3 border-b pb-4">
          <Avatar className="size-11">
            <AvatarFallback>{initials(user.name)}</AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <div className="text-sm font-semibold">{user.name}</div>
            <div className="type-supporting flex items-center gap-1.5 text-muted-foreground">
              <Mail className="size-3.5" />
              {user.email}
            </div>
          </div>
        </div>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-muted-foreground">Vai trò</dt>
            <dd className="mt-1 flex items-center gap-1.5 font-medium">
              <UserRound className="size-3.5 text-muted-foreground" />
              {user.role}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Trạng thái</dt>
            <dd className="mt-1">
              <StatusBadge status={user.status} />
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Ngày tạo</dt>
            <dd className="mt-1 font-medium">
              {formatDateValue(user.createdAt)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">
              Hoạt động gần nhất
            </dt>
            <dd className="mt-1 font-medium">
              {formatDateValue(user.lastActive) || "Chưa có dữ liệu"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Mã người dùng</dt>
            <dd className="mt-1 font-mono text-xs">{user.id}</dd>
          </div>
        </dl>
        <DialogFooter>
          {canUpdate ? (
            <Button variant="outline" onClick={() => onEdit(user)}>
              <Pencil />
              Chỉnh sửa người dùng
            </Button>
          ) : null}
          <Button onClick={() => onOpenChange(false)}>Xong</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
