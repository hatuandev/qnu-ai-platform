import { KeyRound, Plus, RefreshCw, ShieldOff } from "lucide-react";
import { useState } from "react";
import { isModelAdmin, useV1Auth } from "@/app/auth/v1";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  KeyCreateDialog,
  KeyRevokeDialog,
  KeyRotateDialog,
} from "@/features/modelops/key-dialogs";
import { useProviderKeysQuery } from "@/features/modelops/queries";
import type { ProviderKey } from "@/features/modelops/types";
import { formatDateTimeValue } from "@/lib/date-utils";

type DialogState =
  | { kind: "create" }
  | { kind: "rotate"; key: ProviderKey }
  | { kind: "revoke"; key: ProviderKey }
  | null;

export function KeysPanel({ providerId }: { providerId: string }) {
  const { actor } = useV1Auth();
  const query = useProviderKeysQuery(providerId);
  const [dialog, setDialog] = useState<DialogState>(null);
  const canManage = isModelAdmin(actor);

  const keys = query.data ?? [];
  const activeCount = keys.filter((key) => key.status === "active").length;

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold">API keys</h2>
          <p className="text-xs text-muted-foreground">
            Chỉ hiển thị <code className="font-mono">masked_hint</code> do máy
            chủ trả về. Secret không đọc lại được sau khi tạo hoặc xoay.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs"
            onClick={() => void query.refetch()}
            disabled={query.isFetching}
          >
            <RefreshCw
              className={
                query.isFetching ? "size-3.5 animate-spin" : "size-3.5"
              }
            />
            <span>Làm mới</span>
          </Button>
          <Button
            size="sm"
            className="gap-1.5 text-xs font-semibold"
            disabled={!canManage}
            title={
              canManage ? undefined : "Cần quyền ai.models.manage để thêm key"
            }
            onClick={() => setDialog({ kind: "create" })}
          >
            <Plus className="size-3.5" />
            <span>Thêm key</span>
          </Button>
        </div>
      </div>

      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <Card className="overflow-hidden rounded-xl shadow-2xs">
          {query.isLoading ? (
            <div className="grid gap-2 p-4">
              {[0, 1].map((row) => (
                <Skeleton key={row} className="h-11 w-full" />
              ))}
            </div>
          ) : keys.length === 0 ? (
            <EmptyState
              icon={KeyRound}
              title="Provider chưa có key"
              description={
                canManage
                  ? "Thêm key để backendV1 gọi được endpoint này."
                  : "Cần quyền ai.models.manage để thêm key."
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tên</TableHead>
                  <TableHead>Masked hint</TableHead>
                  <TableHead className="w-[120px]">Trạng thái</TableHead>
                  <TableHead className="hidden w-[100px] md:table-cell">
                    Ưu tiên
                  </TableHead>
                  <TableHead className="hidden w-[170px] lg:table-cell">
                    Tạo lúc
                  </TableHead>
                  <TableHead className="w-[210px] text-right">
                    <span className="sr-only">Hành động</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {keys.map((key) => (
                  <TableRow key={key.id}>
                    <TableCell className="text-sm">{key.name}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {key.masked_hint}
                    </TableCell>
                    <TableCell>
                      {key.status === "revoked" ? (
                        <Badge variant="secondary">Đã thu hồi</Badge>
                      ) : key.cooldown_until &&
                        new Date(key.cooldown_until).getTime() > Date.now() ? (
                        <div className="space-y-1">
                          <Badge variant="warning">Tạm nghỉ</Badge>
                          <p className="text-xs text-muted-foreground">
                            Đến {formatDateTimeValue(key.cooldown_until)}
                          </p>
                        </div>
                      ) : key.lease_until &&
                        new Date(key.lease_until).getTime() > Date.now() ? (
                        <Badge variant="outline">Đang gọi</Badge>
                      ) : (
                        <Badge variant="success">Sẵn sàng</Badge>
                      )}
                      {Boolean(key.consecutive_failures) && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          {key.consecutive_failures} lỗi khóa liên tiếp
                        </p>
                      )}
                    </TableCell>
                    <TableCell className="hidden text-xs md:table-cell">
                      {key.priority}
                    </TableCell>
                    <TableCell className="hidden text-xs text-muted-foreground lg:table-cell">
                      {formatDateTimeValue(key.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      {canManage && key.status === "active" ? (
                        <div className="flex justify-end gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="gap-1 text-xs"
                            onClick={() => setDialog({ kind: "rotate", key })}
                          >
                            <RefreshCw className="size-3.5" />
                            <span>Xoay</span>
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="gap-1 text-xs text-destructive"
                            onClick={() => setDialog({ kind: "revoke", key })}
                          >
                            <ShieldOff className="size-3.5" />
                            <span>Thu hồi</span>
                          </Button>
                        </div>
                      ) : (
                        <span className="text-[11px] text-muted-foreground">
                          {key.status === "active" ? "—" : "Không dùng được"}
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Card>
      )}

      <p className="text-[11px] text-muted-foreground">
        {activeCount} key đang hoạt động trên {keys.length} bản ghi. Secret chỉ
        tồn tại trong form lúc tạo hoặc xoay, không lưu ở trình duyệt.
      </p>

      {dialog?.kind === "create" ? (
        <KeyCreateDialog
          providerId={providerId}
          onClose={() => setDialog(null)}
        />
      ) : null}
      {dialog?.kind === "rotate" ? (
        <KeyRotateDialog
          providerId={providerId}
          providerKey={dialog.key}
          onClose={() => setDialog(null)}
        />
      ) : null}
      {dialog?.kind === "revoke" ? (
        <KeyRevokeDialog
          providerId={providerId}
          providerKey={dialog.key}
          onClose={() => setDialog(null)}
        />
      ) : null}
    </div>
  );
}
