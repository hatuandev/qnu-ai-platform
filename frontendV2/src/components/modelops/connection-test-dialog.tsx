import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Cpu,
  Loader2,
  Plus,
  Sparkles,
  Terminal,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import {
  useConnectionKeysQuery,
  useTestConnectionMutation,
} from "@/api/modelops/queries";
import type { Connection, ConnectionTestResult } from "@/api/modelops/types";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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

export function ConnectionTestDialog({
  open,
  onOpenChange,
  connection,
  onAddDiscoveredModel,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connection: Connection;
  onAddDiscoveredModel?: (modelName: string) => void;
}) {
  const keysQuery = useConnectionKeysQuery(connection.id, open);
  const testMutation = useTestConnectionMutation(connection.id);

  const [useCustomKey, setUseCustomKey] = useState(false);
  const [customApiKey, setCustomApiKey] = useState("");
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(
    null,
  );

  const activeKeys = keysQuery.data?.filter((k) => k.status === "active") ?? [];
  const hasActiveKey = activeKeys.length > 0;

  const handleRunTest = async () => {
    try {
      const payload: { api_key?: string } = {};
      if (useCustomKey && customApiKey.trim()) {
        payload.api_key = customApiKey.trim();
      } else if (!hasActiveKey && customApiKey.trim()) {
        payload.api_key = customApiKey.trim();
      }

      const res = await testMutation.mutateAsync(payload);
      setTestResult(res);
      if (res.ok) {
        toast.success(
          `Kiểm tra kết nối thành công! (${res.latency_ms ?? 0}ms)`,
        );
      } else {
        toast.error(`Kiểm tra kết nối thất bại: ${res.detail}`);
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Kiểm tra kết nối thất bại";
      toast.error(msg);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Terminal className="size-5 text-primary" />
            <span>Kiểm tra kết nối & Phát hiện mô hình</span>
          </DialogTitle>
          <DialogDescription>
            Kiểm tra khả năng giao tiếp tới nhà cung cấp{" "}
            <span className="font-semibold text-foreground">
              {connection.name}
            </span>{" "}
            ({connection.base_url}).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-3">
          {/* Endpoint Information */}
          <div className="rounded-lg border bg-muted/30 p-3 space-y-1.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Endpoint:</span>
              <span className="font-mono font-medium">
                {connection.base_url}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Khóa API đã lưu:</span>
              <span>
                {hasActiveKey ? (
                  <Badge
                    variant="outline"
                    className="h-4 text-[10px] bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20"
                  >
                    {activeKeys.length} khóa hoạt động (
                    {activeKeys[0].masked_hint})
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="h-4 text-[10px] text-amber-600 border-amber-500/20 bg-amber-500/10"
                  >
                    Chưa có khóa lưu
                  </Badge>
                )}
              </span>
            </div>
          </div>

          {/* Key Selection */}
          {!hasActiveKey || useCustomKey ? (
            <Field>
              <FieldLabel htmlFor="test-custom-key">
                Nhập khóa API để thử nghiệm *
              </FieldLabel>
              <Input
                id="test-custom-key"
                type="password"
                value={customApiKey}
                onChange={(e) => setCustomApiKey(e.target.value)}
                placeholder="sk-..."
                autoComplete="off"
              />
              <FieldDescription>
                Khóa này chỉ dùng thử nghiệm kết nối trong phiên này, không tự
                động lưu vào cơ sở dữ liệu.
              </FieldDescription>
              {hasActiveKey && (
                <Button
                  type="button"
                  variant="link"
                  size="sm"
                  className="p-0 h-auto text-xs text-primary justify-start"
                  onClick={() => setUseCustomKey(false)}
                >
                  ← Dùng khóa đã lưu của nhà cung cấp
                </Button>
              )}
            </Field>
          ) : (
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">
                Đang dùng khóa API mặc định ({activeKeys[0]?.masked_hint})
              </span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-7 text-xs text-muted-foreground hover:text-foreground"
                onClick={() => setUseCustomKey(true)}
              >
                Nhập khóa khác để thử
              </Button>
            </div>
          )}

          {/* Test Trigger Button */}
          <div className="pt-1">
            <Button
              type="button"
              className="w-full gap-2"
              disabled={
                testMutation.isPending ||
                (!hasActiveKey && !customApiKey.trim())
              }
              onClick={handleRunTest}
            >
              {testMutation.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  <span>
                    Đang kết nối tới máy chủ ({connection.base_url})...
                  </span>
                </>
              ) : (
                <>
                  <Sparkles className="size-4" />
                  <span>Bắt đầu kiểm tra kết nối</span>
                </>
              )}
            </Button>
          </div>

          {/* Test Results Display */}
          {testResult && (
            <div className="space-y-3 pt-2">
              <Alert variant={testResult.ok ? "success" : "destructive"}>
                {testResult.ok ? (
                  <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <AlertCircle className="size-4" />
                )}
                <AlertTitle className="flex items-center justify-between text-sm font-semibold">
                  <span>
                    {testResult.ok ? "Kết nối thành công" : "Kết nối thất bại"}
                  </span>
                  {testResult.latency_ms !== null &&
                    testResult.latency_ms !== undefined && (
                      <Badge
                        variant="outline"
                        className="text-[11px] gap-1 font-mono"
                      >
                        <Clock className="size-3" />
                        {testResult.latency_ms} ms
                      </Badge>
                    )}
                </AlertTitle>
                <AlertDescription className="text-xs mt-1">
                  {testResult.detail}
                </AlertDescription>
              </Alert>

              {/* Discovered Models */}
              {testResult.models && testResult.models.length > 0 && (
                <div className="rounded-lg border bg-card p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold flex items-center gap-1.5">
                      <Cpu className="size-3.5 text-primary" />
                      Mô hình máy chủ công bố ({testResult.models.length})
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      Nhấp để đăng ký nhanh vào hệ thống
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto pr-1">
                    {testResult.models.map((modelName) => (
                      <button
                        key={modelName}
                        type="button"
                        onClick={() => {
                          if (onAddDiscoveredModel) {
                            onAddDiscoveredModel(modelName);
                            onOpenChange(false);
                          }
                        }}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono bg-muted/60 hover:bg-primary/10 hover:text-primary hover:border-primary/40 border border-border/60 transition-colors text-left"
                        title="Bấm để đăng ký mô hình này"
                      >
                        <span>{modelName}</span>
                        <Plus className="size-3 opacity-60" />
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Đóng
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
