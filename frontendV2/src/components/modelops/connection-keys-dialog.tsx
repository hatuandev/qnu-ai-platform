import { Key, Loader2, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import {
  useAddKeyMutation,
  useConnectionKeysQuery,
  useDeleteKeyMutation,
} from "@/api/modelops/queries";
import type { Connection, ProviderKey } from "@/api/modelops/types";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

export function ConnectionKeysDialog({
  open,
  onOpenChange,
  connection,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connection: Connection;
}) {
  const keysQuery = useConnectionKeysQuery(connection.id, open);
  const addKeyMutation = useAddKeyMutation(connection.id);
  const deleteKeyMutation = useDeleteKeyMutation(connection.id);

  const [name, setName] = useState("");
  const [secret, setSecret] = useState("");
  const [priority, setPriority] = useState(5);
  const [isAdding, setIsAdding] = useState(false);
  const [keyToDelete, setKeyToDelete] = useState<ProviderKey | null>(null);

  const keys = keysQuery.data ?? [];

  const handleAddKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Vui lòng nhập tên gợi nhớ cho khóa");
      return;
    }
    if (!secret.trim() || secret.trim().length < 8) {
      toast.error("Khóa API phải có độ dài tối thiểu 8 ký tự");
      return;
    }

    setIsAdding(true);
    try {
      await addKeyMutation.mutateAsync({
        name: name.trim(),
        secret: secret.trim(),
        priority,
      });
      toast.success(`Đã thêm khóa API "${name}" thành công`);
      setName("");
      setSecret("");
      setPriority(5);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Thêm khóa thất bại";
      toast.error(msg);
    } finally {
      setIsAdding(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!keyToDelete) return;
    try {
      await deleteKeyMutation.mutateAsync(keyToDelete.id);
      toast.success(`Đã xóa khóa "${keyToDelete.name}"`);
      setKeyToDelete(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Xóa khóa thất bại";
      toast.error(msg);
    }
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Key className="size-5 text-primary" />
              <span>Quản lý API Key · {connection.name}</span>
            </DialogTitle>
            <DialogDescription>
              Các khóa API được bảo vệ bằng mã hóa ở phía server. Khi gửi yêu
              cầu suy luận, hệ thống tự động chọn khóa hoạt động theo độ ưu
              tiên.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-5 py-3">
            {/* Existing Keys List */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-foreground">
                Danh sách khóa hiện có ({keys.length})
              </span>
              {keysQuery.isLoading ? (
                <div className="py-6 flex justify-center text-muted-foreground text-xs gap-2 items-center">
                  <Loader2 className="size-4 animate-spin" />
                  <span>Đang tải danh sách khóa...</span>
                </div>
              ) : keys.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border/80 p-5 text-center text-xs text-muted-foreground">
                  Chưa có khóa API nào được lưu cho nhà cung cấp này. Vui lòng
                  thêm khóa bên dưới để có thể gửi yêu cầu suy luận tới mô hình.
                </div>
              ) : (
                <div className="divide-y rounded-lg border bg-card">
                  {keys.map((k) => (
                    <div
                      key={k.id}
                      className="flex items-center justify-between p-3 text-xs gap-3"
                    >
                      <div className="min-w-0 space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-foreground">
                            {k.name}
                          </span>
                          <Badge
                            variant={
                              k.status === "active" ? "outline" : "secondary"
                            }
                            className={
                              k.status === "active"
                                ? "h-4 text-[10px] bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20"
                                : "h-4 text-[10px]"
                            }
                          >
                            {k.status === "active" ? "Hoạt động" : k.status}
                          </Badge>
                          <span className="text-[10px] text-muted-foreground font-mono">
                            Ưu tiên: {k.priority}
                          </span>
                        </div>
                        <div className="font-mono text-muted-foreground text-[11px]">
                          {k.masked_hint || "sk-••••••••"}
                        </div>
                      </div>

                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="size-7 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10 shrink-0"
                        title="Xóa khóa này"
                        onClick={() => setKeyToDelete(k)}
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Add Key Form */}
            <form
              onSubmit={handleAddKey}
              className="rounded-lg border bg-muted/20 p-4 space-y-3"
            >
              <div className="flex items-center gap-2 pb-1 border-b border-border/50 text-xs font-semibold">
                <ShieldCheck className="size-4 text-primary" />
                <span>Thêm khóa API mới</span>
              </div>

              <Field>
                <FieldLabel htmlFor="key-name">Tên gợi nhớ *</FieldLabel>
                <Input
                  id="key-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="VD: Production Main Key, Backup Free Tier..."
                  required
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="key-secret">
                  Mã khóa API bí mật (Secret) *
                </FieldLabel>
                <Input
                  id="key-secret"
                  type="password"
                  value={secret}
                  onChange={(e) => setSecret(e.target.value)}
                  placeholder="sk-... (tối thiểu 8 ký tự)"
                  autoComplete="off"
                  required
                />
                <FieldDescription>
                  Khóa được mã hóa trước khi lưu vào CSDL. Hệ thống chỉ hiển thị
                  dạng che (masked hint).
                </FieldDescription>
              </Field>

              <div className="flex items-center justify-between gap-4 pt-1">
                <div className="w-32">
                  <FieldLabel htmlFor="key-priority" className="text-xs">
                    Độ ưu tiên (1-10)
                  </FieldLabel>
                  <Input
                    id="key-priority"
                    type="number"
                    min={1}
                    max={10}
                    value={priority}
                    onChange={(e) => setPriority(Number(e.target.value) || 5)}
                    className="h-8 text-xs"
                  />
                </div>

                <Button
                  type="submit"
                  size="sm"
                  className="h-8 gap-1.5 self-end"
                  disabled={
                    isAdding || !name.trim() || secret.trim().length < 8
                  }
                >
                  {isAdding ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <Plus className="size-3.5" />
                  )}
                  <span>Lưu khóa</span>
                </Button>
              </div>
            </form>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Xong
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(keyToDelete)}
        onOpenChange={(open) => !open && setKeyToDelete(null)}
        title="Xóa khóa API"
        description={
          <>
            Bạn có chắc chắn muốn xóa khóa API{" "}
            <strong>{keyToDelete?.name}</strong> (
            <span className="font-mono">{keyToDelete?.masked_hint}</span>)? Nếu
            không còn khóa nào khác, nhà cung cấp sẽ không thể gửi yêu cầu suy
            luận.
          </>
        }
        confirmLabel="Xóa khóa"
        confirmVariant="destructive"
        isLoading={deleteKeyMutation.isPending}
        onConfirm={handleDeleteConfirm}
      />
    </>
  );
}
