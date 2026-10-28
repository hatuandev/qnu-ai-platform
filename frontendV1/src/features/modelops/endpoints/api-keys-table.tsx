import {
  Key,
  MoreVertical,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useRotateAppApiKeyMutation,
  useUpdateAppApiKeyStatusMutation,
} from "@/features/modelops/queries";
import type {
  AppApiKey,
  AppApiKeySecretResponse,
} from "@/features/modelops/types";
import { formatDateTimeValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

interface ApiKeysTableProps {
  keys: AppApiKey[];
  workspaceId: string;
  onOpenCreate: () => void;
  onOpenRevoke: (keyItem: AppApiKey) => void;
  onRotateSuccess: (data: AppApiKeySecretResponse) => void;
}

export function ApiKeysTable({
  keys,
  workspaceId,
  onOpenCreate,
  onOpenRevoke,
  onRotateSuccess,
}: ApiKeysTableProps) {
  const updateStatusMutation = useUpdateAppApiKeyStatusMutation(workspaceId);
  const rotateMutation = useRotateAppApiKeyMutation(
    workspaceId,
    onRotateSuccess,
  );

  const handleToggleStatus = async (keyItem: AppApiKey) => {
    const nextStatus = keyItem.status === "active" ? "suspended" : "active";
    try {
      await updateStatusMutation.mutateAsync({
        keyId: keyItem.id,
        input: {
          status: nextStatus,
          reason:
            nextStatus === "suspended"
              ? "Tạm ngưng bởi quản trị viên"
              : "Kích hoạt lại",
        },
      });
      toast.success(
        nextStatus === "suspended"
          ? `Đã tạm ngưng khóa "${keyItem.name}".`
          : `Đã kích hoạt lại khóa "${keyItem.name}".`,
      );
    } catch (err: unknown) {
      toast.error(
        (err as Error)?.message || "Không thể cập nhật trạng thái khóa.",
      );
    }
  };

  const handleRotate = async (keyItem: AppApiKey) => {
    try {
      await rotateMutation.mutateAsync({
        keyId: keyItem.id,
        input: { expires_in_days: 60, idempotency_key: crypto.randomUUID() },
      });
      toast.success(`Đã xoay khóa "${keyItem.name}" thành công!`);
    } catch (err: unknown) {
      toast.error((err as Error)?.message || "Không thể xoay khóa.");
    }
  };

  if (keys.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
        <div className="rounded-full bg-muted/60 p-3 mb-3">
          <Key className="size-6 text-muted-foreground" />
        </div>
        <h3 className="text-sm font-semibold text-foreground">
          Chưa có khóa API ứng dụng nào
        </h3>
        <p className="text-xs text-muted-foreground mt-1 max-w-sm">
          Tạo khóa API đầu tiên để cấp quyền cho website trường, ứng dụng di
          động hoặc đối tác bên ngoài kết nối với trợ lý QNU.
        </p>
        <Button
          size="sm"
          className="mt-4 gap-1.5 text-xs font-semibold"
          onClick={onOpenCreate}
        >
          <Plus className="size-3.5" />
          <span>Tạo khóa mới</span>
        </Button>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent text-[11px]">
            <TableHead className="w-[200px]">Tên khóa & Ứng dụng</TableHead>
            <TableHead className="w-[140px]">Tiền tố (Prefix)</TableHead>
            <TableHead className="w-[100px]">Trạng thái</TableHead>
            <TableHead className="w-[120px]">Hạn mức</TableHead>
            <TableHead className="w-[180px]">Phạm vi trợ lý</TableHead>
            <TableHead className="w-[140px]">Hạn sử dụng</TableHead>
            <TableHead className="w-[130px]">Lần dùng cuối</TableHead>
            <TableHead className="w-[70px] text-right">Thao tác</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody className="text-xs">
          {keys.map((k) => {
            const isRevoked = k.status === "revoked";
            const isSuspended = k.status === "suspended";
            const isActive = k.status === "active";

            return (
              <TableRow
                key={k.id}
                className={cn(
                  "group transition-colors",
                  isRevoked && "opacity-60 bg-muted/20",
                )}
              >
                {/* Name & App */}
                <TableCell className="font-medium">
                  <div className="flex flex-col">
                    <span className="font-semibold text-foreground group-hover:text-primary transition-colors">
                      {k.name}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      App: {k.app_name}
                    </span>
                  </div>
                </TableCell>

                {/* Key Prefix */}
                <TableCell>
                  <code className="rounded bg-muted/60 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-foreground">
                    {k.key_prefix}...
                  </code>
                </TableCell>

                {/* Status Badge */}
                <TableCell>
                  {isActive && (
                    <Badge
                      variant="success"
                      className="text-[10px] py-0 px-1.5"
                    >
                      Đang bật
                    </Badge>
                  )}
                  {isSuspended && (
                    <Badge
                      variant="outline"
                      className="text-[10px] py-0 px-1.5 text-warning border-warning/40 bg-warning/5"
                    >
                      Tạm ngưng
                    </Badge>
                  )}
                  {isRevoked && (
                    <Badge
                      variant="destructive"
                      className="text-[10px] py-0 px-1.5"
                    >
                      Đã thu hồi
                    </Badge>
                  )}
                </TableCell>

                {/* Rate Limits */}
                <TableCell>
                  <div className="flex flex-col text-[11px] font-mono text-muted-foreground">
                    <span>{k.rate_limit_rpm} RPM</span>
                    <span>{k.rate_limit_rpd.toLocaleString()} RPD</span>
                  </div>
                </TableCell>

                {/* Assistant Scope */}
                <TableCell>
                  {k.allowed_assistant_ids &&
                  k.allowed_assistant_ids.length > 0 ? (
                    <Badge variant="outline" className="text-[10px] py-0">
                      {k.allowed_assistant_ids.length} trợ lý được cấp
                    </Badge>
                  ) : (
                    <span className="text-[11px] text-muted-foreground">
                      Tất cả trong đơn vị
                    </span>
                  )}
                </TableCell>

                {/* Expiry */}
                <TableCell className="text-[11px] text-muted-foreground">
                  {k.expires_at
                    ? formatDateTimeValue(k.expires_at)
                    : "Vô thời hạn"}
                </TableCell>

                {/* Last Used */}
                <TableCell className="text-[11px] text-muted-foreground">
                  {k.last_used_at
                    ? formatDateTimeValue(k.last_used_at)
                    : "Chưa gọi"}
                </TableCell>

                {/* Actions */}
                <TableCell className="text-right">
                  {!isRevoked ? (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                        >
                          <MoreVertical className="size-3.5" />
                          <span className="sr-only">Tùy chọn</span>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-40 text-xs">
                        <DropdownMenuItem
                          onClick={() => handleToggleStatus(k)}
                          disabled={updateStatusMutation.isPending}
                          className="gap-2"
                        >
                          {isActive ? (
                            <>
                              <Pause className="size-3.5 text-warning" />
                              <span>Tạm ngưng khóa</span>
                            </>
                          ) : (
                            <>
                              <Play className="size-3.5 text-primary" />
                              <span>Kích hoạt lại</span>
                            </>
                          )}
                        </DropdownMenuItem>

                        <DropdownMenuItem
                          onClick={() => handleRotate(k)}
                          disabled={rotateMutation.isPending}
                          className="gap-2"
                        >
                          <RefreshCw className="size-3.5 text-primary" />
                          <span>Xoay khóa (Rotate)</span>
                        </DropdownMenuItem>

                        <DropdownMenuSeparator />

                        <DropdownMenuItem
                          onClick={() => onOpenRevoke(k)}
                          className="gap-2 text-destructive focus:text-destructive"
                        >
                          <Trash2 className="size-3.5" />
                          <span>Thu hồi vĩnh viễn</span>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  ) : (
                    <span className="text-[10px] text-muted-foreground italic">
                      {k.revoked_reason || "Đã hủy"}
                    </span>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
