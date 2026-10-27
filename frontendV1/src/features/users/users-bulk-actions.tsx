import { CheckCircle2, CircleOff, PauseCircle, Trash2 } from "lucide-react";
import type { ReactNode } from "react";
import { DataTableBulkActions } from "@/components/admin/data-table/data-table-bulk-actions";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { User, UserStatus } from "@/features/users/types";

function BulkActionButton({
  label,
  children,
  onClick,
  variant = "outline",
}: {
  label: string;
  children: ReactNode;
  onClick: () => void;
  variant?: "outline" | "destructive";
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant={variant}
          size="icon"
          className="size-8 rounded-xl border-border/80 shadow-2xs hover:bg-muted"
          aria-label={label}
          onClick={onClick}
        >
          {children}
        </Button>
      </TooltipTrigger>
      <TooltipContent side="top">{label}</TooltipContent>
    </Tooltip>
  );
}

export function UsersBulkActions({
  users,
  canUpdate,
  canDelete,
  onClear,
  onStatusChange,
  onDelete,
}: {
  users: User[];
  canUpdate: boolean;
  canDelete: boolean;
  onClear: () => void;
  onStatusChange: (users: User[], status: UserStatus) => void;
  onDelete: (users: User[]) => void;
}) {
  if (!users.length) return null;
  return (
    <TooltipProvider>
      <DataTableBulkActions
        selectedCount={users.length}
        selectedLabel="người dùng"
        onClear={onClear}
      >
        {canUpdate ? (
          <>
            <BulkActionButton
              label="Kích hoạt các mục đã chọn"
              onClick={() => onStatusChange(users, "active")}
            >
              <CheckCircle2 />
            </BulkActionButton>
            <BulkActionButton
              label="Tạm khóa các mục đã chọn"
              onClick={() => onStatusChange(users, "suspended")}
            >
              <PauseCircle />
            </BulkActionButton>
            <BulkActionButton
              label="Vô hiệu hóa các mục đã chọn"
              onClick={() => onStatusChange(users, "inactive")}
            >
              <CircleOff />
            </BulkActionButton>
          </>
        ) : null}
        {canUpdate && canDelete ? (
          <Separator orientation="vertical" className="mx-1 h-6" />
        ) : null}
        {canDelete ? (
          <BulkActionButton
            label="Xóa các mục đã chọn"
            variant="destructive"
            onClick={() => onDelete(users)}
          >
            <Trash2 />
          </BulkActionButton>
        ) : null}
      </DataTableBulkActions>
    </TooltipProvider>
  );
}
