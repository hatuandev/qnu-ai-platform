import { Download, Loader2, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  type DiagnosticCheck,
  type DiscoveredModel,
  useDiagnostics,
  useRunDiagnostic,
} from "../diagnostic-queries";
import { CAPABILITY_LABELS, type Capability } from "../types";
import { useAddConnectionModel, useSyncConnectionCapacity } from "./api";

function describeMetadata(row?: DiscoveredModel) {
  const values = [
    row?.context_window_tokens
      ? `Context ${row.context_window_tokens.toLocaleString("vi-VN")}`
      : null,
    row?.max_output_tokens
      ? `Đầu ra ${row.max_output_tokens.toLocaleString("vi-VN")}`
      : null,
    row?.embedding_dimension ? `${row.embedding_dimension} chiều` : null,
  ].filter(Boolean);
  return values.length ? values.join(" · ") : "Server chưa công bố giới hạn";
}

export function ImportModelsDialog({
  open,
  onOpenChange,
  connectionId,
  connectionName,
  existingModels = [],
  onModelAdded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connectionId: string;
  connectionName: string;
  existingModels?: string[];
  onModelAdded?: () => void;
}) {
  const diagnostic = useDiagnostics(connectionId);
  const runDiagnostic = useRunDiagnostic(connectionId);
  const addModelMutation = useAddConnectionModel(connectionId);
  const syncMutation = useSyncConnectionCapacity(connectionId);
  const [loadedCheck, setCheck] = useState<DiagnosticCheck | null>();
  const [selected, setSelected] = useState<string[]>([]);
  const [capabilities, setCapabilities] = useState<Record<string, Capability>>(
    {},
  );
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const existingSet = new Set(existingModels);
  const latest = diagnostic.data?.checks.find(
    (item) => item.kind === "discovery",
  );
  const cachedCheck =
    latest?.outcome === "ok" && latest.configuration_status === "current"
      ? latest
      : null;
  const check = loadedCheck === undefined ? cachedCheck : loadedCheck;

  useEffect(() => {
    if (!open) {
      setCheck(undefined);
      setSelected([]);
      setError(null);
      return;
    }
  }, [open]);

  const handleDiscover = async () => {
    setError(null);
    setCheck(null);
    setSelected([]);
    try {
      const result = await runDiagnostic.mutateAsync("discovery");
      if (result.outcome !== "ok") {
        setError(result.detail);
        return;
      }
      setCheck(result);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Không lấy được danh sách model.",
      );
    }
  };

  const handleApply = async () => {
    if (!check) return;
    setIsSaving(true);
    setError(null);
    try {
      const registered = selected.filter((name) => existingSet.has(name));
      if (registered.length)
        await syncMutation.mutateAsync({
          check_id: check.id,
          model_names: registered,
        });
      for (const name of selected.filter((item) => !existingSet.has(item))) {
        await addModelMutation.mutateAsync({
          model_name: name,
          capabilities: [capabilities[name] ?? "chat"],
          ...(check.model_metadata?.some((row) => row.id === name)
            ? { discovery_check_id: check.id }
            : {}),
        });
        setSelected((current) => current.filter((item) => item !== name));
      }
      setSelected([]);
      toast.success("Đã áp dụng thông số model.");
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Không áp dụng được thông số model.",
      );
    } finally {
      setIsSaving(false);
      onModelAdded?.();
    }
  };

  return (
    <ResponsiveDialog
      open={open}
      onOpenChange={(value) => {
        if (!isSaving) onOpenChange(value);
      }}
    >
      <ResponsiveDialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] max-w-xl flex-col gap-0 overflow-hidden p-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 p-5">
          <ResponsiveDialogTitle className="flex items-center gap-2">
            <Download className="size-4" />
            Lấy model
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            Thông số do {connectionName} công bố; chưa phải kết quả kiểm định.
            Chọn model để thêm hoặc đồng bộ.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
          <Button
            size="sm"
            variant="outline"
            disabled={runDiagnostic.isPending || isSaving}
            onClick={handleDiscover}
          >
            {runDiagnostic.isPending ? (
              <Loader2 className="mr-2 size-3.5 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 size-3.5" />
            )}
            Lấy lại
          </Button>
          <p className="text-xs text-muted-foreground">
            Giới hạn input riêng và ngân sách ảnh OCR đã lưu được giữ lại. Chọn
            đúng chức năng khi thêm model mới.
          </p>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          {!check?.models.length && !runDiagnostic.isPending && (
            <p className="text-sm text-muted-foreground">
              Lấy danh sách để xem thông số hiện tại từ server.
            </p>
          )}
          <div className="divide-y">
            {check?.models.map((name) => {
              const metadata = check.model_metadata?.find(
                (row) => row.id === name,
              );
              const hasMetadata =
                metadata &&
                (metadata.context_window_tokens ||
                  metadata.max_output_tokens ||
                  metadata.embedding_dimension);
              return (
                <div key={name} className="flex items-start gap-3 py-3">
                  <Checkbox
                    id={`import-${name}`}
                    className="mt-1"
                    disabled={
                      isSaving || (existingSet.has(name) && !hasMetadata)
                    }
                    checked={selected.includes(name)}
                    onCheckedChange={(value) =>
                      setSelected((current) =>
                        value === true
                          ? [...current, name]
                          : current.filter((item) => item !== name),
                      )
                    }
                  />
                  <div className="min-w-0 flex-1 space-y-1">
                    <label
                      htmlFor={`import-${name}`}
                      className="break-all text-sm font-medium"
                    >
                      {name}
                    </label>
                    <p className="text-xs text-muted-foreground">
                      {describeMetadata(metadata)}
                    </p>
                    {existingSet.has(name) ? (
                      <p className="text-xs text-muted-foreground">
                        Đã thêm · đồng bộ thông số
                      </p>
                    ) : (
                      <Select
                        value={capabilities[name] ?? "chat"}
                        disabled={isSaving}
                        onValueChange={(value) =>
                          setCapabilities((current) => ({
                            ...current,
                            [name]: value as Capability,
                          }))
                        }
                      >
                        <SelectTrigger
                          aria-label={`Chức năng ${name}`}
                          className="w-40"
                        >
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(CAPABILITY_LABELS).map(
                            ([value, label]) => (
                              <SelectItem key={value} value={value}>
                                {label}
                              </SelectItem>
                            ),
                          )}
                        </SelectContent>
                      </Select>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        <ResponsiveDialogFooter className="border-t bg-card p-4">
          <Button
            variant="outline"
            size="sm"
            disabled={isSaving}
            onClick={() => onOpenChange(false)}
          >
            Đóng
          </Button>
          <Button
            size="sm"
            disabled={
              !check || !selected.length || isSaving || runDiagnostic.isPending
            }
            onClick={handleApply}
          >
            {isSaving && <Loader2 className="mr-2 size-3.5 animate-spin" />}Áp
            dụng
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
