import { Bot, Check, Download, Loader2, Plus, Sparkles } from "lucide-react";
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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useDiagnostics, useRunDiagnostic } from "../diagnostic-queries";
import { useAddConnectionModel } from "./api";

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

  const [discoveredModels, setDiscoveredModels] = useState<string[]>([]);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [addingModel, setAddingModel] = useState<string | null>(null);

  const existingSet = new Set(existingModels);

  // Auto discover when opened
  useEffect(() => {
    if (open) {
      const latest = diagnostic.data?.checks.find((x) => x.kind === "discovery");
      if (latest?.outcome === "ok" && latest.models.length > 0) {
        setDiscoveredModels(latest.models);
      } else {
        handleDiscover();
      }
    }
  }, [open, diagnostic.data]);

  const handleDiscover = async () => {
    setIsDiscovering(true);
    try {
      const res = await runDiagnostic.mutateAsync("discovery");
      if (res.outcome === "ok" && res.models.length > 0) {
        setDiscoveredModels(res.models);
        toast.success(`Tìm thấy ${res.models.length} model từ /models`);
      } else {
        toast.error(res.detail || "Không tìm thấy model nào từ endpoint /models.");
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Không thể truy xuất danh sách model.");
    } finally {
      setIsDiscovering(false);
    }
  };

  const handleAddModel = async (modelName: string) => {
    setAddingModel(modelName);
    try {
      await addModelMutation.mutateAsync({
        model_name: modelName,
        capabilities: ["chat"],
      });
      toast.success(`Đã thêm model ${modelName}.`);
      onModelAdded?.();
    } catch {
      toast.error(`Không thể thêm model ${modelName}.`);
    } finally {
      setAddingModel(null);
    }
  };

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] max-w-lg flex-col gap-0 overflow-hidden p-0 text-xs">
        <ResponsiveDialogHeader className="border-b bg-muted/20 p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Download className="size-4" />
              </div>
              <div>
                <ResponsiveDialogTitle>Nhập mô hình từ /models</ResponsiveDialogTitle>
                <ResponsiveDialogDescription className="text-xs">
                  Truy vấn endpoint upstream của {connectionName} để lấy danh sách mô hình.
                </ResponsiveDialogDescription>
              </div>
            </div>

            <Button
              size="sm"
              variant="outline"
              className="h-8 gap-1.5 text-xs"
              disabled={isDiscovering}
              onClick={handleDiscover}
            >
              {isDiscovering ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Sparkles className="size-3.5" />
              )}
              <span>Quét lại</span>
            </Button>
          </div>
        </ResponsiveDialogHeader>

        <div className="min-h-0 flex-1 p-5 overflow-y-auto space-y-2">
          {isDiscovering ? (
            <div className="flex flex-col items-center justify-center p-8 space-y-2 text-muted-foreground">
              <Loader2 className="size-6 animate-spin text-primary" />
              <p>Đang kết nối tới endpoint /models...</p>
            </div>
          ) : discoveredModels.length === 0 ? (
            <div className="text-center p-8 space-y-2 text-muted-foreground">
              <Bot className="size-8 mx-auto text-muted-foreground/50" />
              <p>Chưa tìm thấy model nào từ nhà cung cấp.</p>
              <p className="text-[11px]">Đảm bảo bạn đã thêm API Key hợp lệ và địa chỉ Base URL chính xác.</p>
            </div>
          ) : (
            <div className="space-y-1.5">
              {discoveredModels.map((m) => {
                const isAdded = existingSet.has(m);
                const isCurrentAdding = addingModel === m;

                return (
                  <div
                    key={m}
                    className="flex items-center justify-between p-2.5 rounded-lg border border-border/80 bg-card hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <Bot className="size-4 text-primary shrink-0" />
                      <span className="font-mono text-xs font-medium truncate">
                        {m}
                      </span>
                    </div>

                    <div className="shrink-0 ml-2">
                      {isAdded ? (
                        <Badge variant="outline" className="text-[10px] gap-1 text-muted-foreground">
                          <Check className="size-3 text-success" />
                          Đã thêm
                        </Badge>
                      ) : (
                        <Button
                          size="sm"
                          variant="secondary"
                          className="h-7 text-xs gap-1"
                          disabled={isCurrentAdding}
                          onClick={() => handleAddModel(m)}
                        >
                          {isCurrentAdding ? (
                            <Loader2 className="size-3 animate-spin" />
                          ) : (
                            <Plus className="size-3" />
                          )}
                          <span>Thêm</span>
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <ResponsiveDialogFooter className="border-t bg-card p-4 flex justify-end">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Đóng
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

