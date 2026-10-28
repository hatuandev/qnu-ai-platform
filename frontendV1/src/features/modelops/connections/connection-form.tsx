import { useForm, useStore } from "@tanstack/react-form";
import { useEffect } from "react";
import { toast } from "sonner";
import { ErrorState } from "@/components/admin/error-state";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
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
import {
  type Connection,
  type ConnectionFamily,
  FAMILIES,
  PRESET_URLS,
  useSaveConnection,
} from "./api";

export function ConnectionForm({
  open,
  onOpenChange,
  connection,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connection?: Connection;
  onCreated?: (connection: Connection) => void;
}) {
  const form = useForm({
    defaultValues: {
      family: connection?.family ?? ("custom" as ConnectionFamily),
      name: connection?.name ?? "",
      url: connection?.base_url ?? "",
    },
  });
  const family = useStore(form.store, (state) => state.values.family);
  const name = useStore(form.store, (state) => state.values.name);
  const url = useStore(form.store, (state) => state.values.url);
  const setFamily = (value: ConnectionFamily) =>
    form.setFieldValue("family", value);
  const setName = (value: string) => form.setFieldValue("name", value);
  const setUrl = (value: string) => form.setFieldValue("url", value);
  const mutation = useSaveConnection(connection?.id);
  useEffect(() => {
    if (open) {
      form.reset({
        family: connection?.family ?? "custom",
        name: connection?.name ?? "",
        url: connection?.base_url ?? "",
      });
      mutation.reset();
    }
  }, [open, connection, mutation.reset, form]);
  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] max-w-lg flex-col gap-0 overflow-hidden p-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 p-5">
          <ResponsiveDialogTitle>
            {connection ? "Sửa nhà cung cấp" : "Thêm nhà cung cấp"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            Tạo kết nối trước. API key và các model sẽ được thêm trong trang chi
            tiết.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <form
          className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5"
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              const saved = await mutation.mutateAsync({
                name: name.trim(),
                family,
                base_url: url.trim(),
                timeout_seconds: connection?.timeout_seconds ?? 30,
              });
              onOpenChange(false);
              onCreated?.(saved);
              toast.success("Đã lưu nhà cung cấp.");
            } catch {
              /* ErrorState shows the server response. */
            }
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="connection-family">Nhà cung cấp</Label>
            <Select
              value={family}
              onValueChange={(value) => {
                const next = value as ConnectionFamily;
                setFamily(next);
                if (!connection) {
                  setUrl(PRESET_URLS[next]);
                  setName(FAMILIES[next]);
                }
              }}
            >
              <SelectTrigger id="connection-family">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(FAMILIES).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="connection-name">Tên hiển thị</Label>
            <Input
              id="connection-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              minLength={2}
              maxLength={120}
              required
              placeholder="Ví dụ: Server AI QNU"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="connection-url">Địa chỉ API</Label>
            <Input
              id="connection-url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              type="url"
              placeholder="https://server/v1"
            />
            <p className="text-xs text-muted-foreground">
              Địa chỉ API tương thích OpenAI. Với Gemini, dùng endpoint OpenAI
              compatibility.
            </p>
          </div>
          {mutation.isError && <ErrorState error={mutation.error} />}
          <ResponsiveDialogFooter className="grid grid-cols-2 gap-2 border-t bg-card p-4 sm:flex sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Đang lưu…" : "Lưu nhà cung cấp"}
            </Button>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
