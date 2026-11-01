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
  type Connection,
  type ConnectionFamily,
  type ConnectionInput,
  PRESET_PREFIXES,
  PRESET_URLS,
  useSaveConnection,
} from "./api";

export function ConnectionForm({
  open,
  onOpenChange,
  connection,
  initialFamily = "custom",
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connection?: Connection;
  initialFamily?: ConnectionFamily;
  onCreated?: (connection: Connection) => void;
}) {
  const form = useForm({
    defaultValues: {
      family: connection?.family ?? initialFamily,
      name: connection?.name ?? "",
      prefix:
        connection?.prefix ??
        (connection ? "" : PRESET_PREFIXES[initialFamily]),
      apiType: connection?.api_type ?? "",
      url:
        connection?.base_url ?? (connection ? "" : PRESET_URLS[initialFamily]),
    },
  });

  const family = useStore(form.store, (state) => state.values.family);
  const name = useStore(form.store, (state) => state.values.name);
  const prefix = useStore(form.store, (state) => state.values.prefix);
  const apiType = useStore(form.store, (state) => state.values.apiType);
  const url = useStore(form.store, (state) => state.values.url);

  const setName = (value: string) => form.setFieldValue("name", value);
  const setPrefix = (value: string) => form.setFieldValue("prefix", value);
  const setUrl = (value: string) => form.setFieldValue("url", value);

  const mutation = useSaveConnection(connection?.id);

  useEffect(() => {
    if (open) {
      const activeFamily = connection?.family ?? initialFamily;
      form.reset({
        family: activeFamily,
        name:
          connection?.name ??
          (connection
            ? ""
            : activeFamily === "custom"
              ? ""
              : activeFamily === "qnu"
                ? "QNU Server"
                : "OpenAI Compatible"),
        prefix:
          connection?.prefix ??
          (connection ? "" : PRESET_PREFIXES[activeFamily]),
        apiType: connection?.api_type ?? "",
        url:
          connection?.base_url ?? (connection ? "" : PRESET_URLS[activeFamily]),
      });
      mutation.reset();
    }
  }, [open, connection, initialFamily, mutation.reset, form]);

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] max-w-lg flex-col gap-0 overflow-hidden p-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 p-5">
          <ResponsiveDialogTitle>
            {connection ? "Chỉnh sửa nhà cung cấp" : "Thêm nhà cung cấp mới"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            Thiết lập kết nối với nhà cung cấp mô hình AI (OpenAI Compatible).
            Sau khi lưu, bạn có thể thêm API Key và cấu hình Model LLM trong
            trang chi tiết.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <form
          className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5 text-xs"
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              const payload: ConnectionInput = {
                name: name.trim(),
                family,
                base_url: url.trim(),
                timeout_seconds: connection?.timeout_seconds ?? 30,
                ...(prefix.trim() ? { prefix: prefix.trim() } : {}),
                ...(apiType.trim() ? { api_type: apiType.trim() } : {}),
              };

              const saved = await mutation.mutateAsync(payload);
              onOpenChange(false);
              onCreated?.(saved);
              toast.success(`Đã lưu nhà cung cấp ${saved.name}.`);
            } catch {
              /* ErrorState shows server error */
            }
          }}
        >
          {/* Tên hiển thị */}
          <div className="space-y-1.5">
            <Label htmlFor="connection-name">Tên hiển thị</Label>
            <Input
              id="connection-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              minLength={2}
              maxLength={120}
              required
              placeholder="Ví dụ: QNU Server, OpenAI, NaraRouter..."
            />
          </div>

          {/* Tiền tố (Prefix) */}
          <div className="space-y-1.5">
            <Label htmlFor="connection-prefix">Tiền tố (Prefix)</Label>
            <Input
              id="connection-prefix"
              value={prefix}
              onChange={(e) => setPrefix(e.target.value)}
              maxLength={32}
              placeholder="Ví dụ: qnu, openai"
            />
            <p className="text-[11px] text-muted-foreground">
              Định danh tiền tố trước model (ví dụ: qnu/qwen...)
            </p>
          </div>

          {/* Base URL */}
          <div className="space-y-1.5">
            <Label htmlFor="connection-url">Địa chỉ API</Label>
            <Input
              id="connection-url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              type="url"
              placeholder="http://100.105.13.53:8000/v1 hoặc https://api.openai.com/v1"
            />
            <p className="text-[11px] text-muted-foreground">
              Địa chỉ Base URL endpoint /chat/completions hoặc /models
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
