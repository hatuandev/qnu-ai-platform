import { Check, Eye, EyeOff, Key, Loader2, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
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
import { useAddConnectionKey, useTestConnection } from "./api";

export function ConnectionKeyModal({
  open,
  onOpenChange,
  connectionId,
  connectionName,
  availableModels = [],
  onKeyAdded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connectionId: string;
  connectionName: string;
  availableModels?: string[];
  onKeyAdded?: () => void;
}) {
  const [name, setName] = useState("");
  const [secret, setSecret] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [defaultModel, setDefaultModel] = useState("");
  const [priority, setPriority] = useState(5);

  const [testResult, setTestResult] = useState<{
    status: "idle" | "testing" | "success" | "error";
    message: string;
    latencyMs?: number | null;
  }>({ status: "idle", message: "" });

  const addKeyMutation = useAddConnectionKey(connectionId);
  const testMutation = useTestConnection(connectionId);

  const handleTestConnection = async () => {
    if (!secret.trim()) {
      setTestResult({
        status: "error",
        message: "Vui lòng nhập API Key trước khi kiểm tra kết nối.",
      });
      return;
    }

    setTestResult({ status: "testing", message: "Đang kiểm tra kết nối tới nhà cung cấp..." });
    try {
      const res = await testMutation.mutateAsync({
        api_key: secret.trim(),
        model_name: defaultModel.trim() || undefined,
      });

      if (res.ok) {
        setTestResult({
          status: "success",
          message: res.detail,
          latencyMs: res.latency_ms,
        });
      } else {
        setTestResult({
          status: "error",
          message: res.detail,
        });
      }
    } catch (err: unknown) {
      setTestResult({
        status: "error",
        message: err instanceof Error ? err.message : "Không thể kết nối đến nhà cung cấp.",
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !secret.trim()) {
      toast.error("Vui lòng điền đầy đủ Tên và API Key.");
      return;
    }

    try {
      await addKeyMutation.mutateAsync({
        name: name.trim(),
        secret: secret.trim(),
        priority,
        default_model: defaultModel.trim() || undefined,
      });

      toast.success("Đã thêm API Key thành công.");
      setName("");
      setSecret("");
      setDefaultModel("");
      setPriority(5);
      setTestResult({ status: "idle", message: "" });
      onOpenChange(false);
      onKeyAdded?.();
    } catch {
      toast.error("Không thể lưu API Key. Vui lòng thử lại.");
    }
  };

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] max-w-lg flex-col gap-0 overflow-hidden p-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 p-5">
          <div className="flex items-center gap-2">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Key className="size-4" />
            </div>
            <div>
              <ResponsiveDialogTitle>Thêm API Key / Kết nối</ResponsiveDialogTitle>
              <ResponsiveDialogDescription className="text-xs">
                Cấu hình API Key cho {connectionName}. Khóa được lưu trữ mã hóa an toàn.
              </ResponsiveDialogDescription>
            </div>
          </div>
        </ResponsiveDialogHeader>

        <form onSubmit={handleSubmit} className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5 text-xs">
          {/* Tên kết nối / Key Name */}
          <div className="space-y-1.5">
            <Label htmlFor="key-name">Tên kết nối / Gợi nhớ *</Label>
            <Input
              id="key-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              minLength={2}
              maxLength={120}
              placeholder="Ví dụ: Primary Key, Key #1, Account Production..."
            />
          </div>

          {/* API KEY */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="key-secret">API Key *</Label>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-6 px-1.5 text-[11px] text-muted-foreground"
                onClick={() => setShowSecret(!showSecret)}
              >
                {showSecret ? (
                  <>
                    <EyeOff className="size-3 mr-1" />
                    Ẩn
                  </>
                ) : (
                  <>
                    <Eye className="size-3 mr-1" />
                    Hiện
                  </>
                )}
              </Button>
            </div>
            <div className="relative">
              <Input
                id="key-secret"
                type={showSecret ? "text" : "password"}
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
                required
                minLength={8}
                placeholder="sk-..."
                className="font-mono text-xs pr-10"
              />
            </div>
            <p className="text-[11px] text-muted-foreground">
              Khóa API bí mật của nhà cung cấp để gửi kèm trong header yêu cầu.
            </p>
          </div>

          {/* Default Model & Priority */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="key-default-model">Mô hình mặc định (Default Model)</Label>
              {availableModels.length > 0 ? (
                <div className="space-y-1">
                  <Select value={defaultModel} onValueChange={setDefaultModel}>
                    <SelectTrigger id="key-default-model">
                      <SelectValue placeholder="Chọn hoặc nhập model..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__all__">Tất cả mô hình</SelectItem>
                      {availableModels.map((m) => (
                        <SelectItem key={m} value={m}>
                          {m}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ) : (
                <Input
                  id="key-default-model"
                  value={defaultModel}
                  onChange={(e) => setDefaultModel(e.target.value)}
                  placeholder="Ví dụ: gpt-4o, qwen3.8-27b..."
                />
              )}
              <p className="text-[11px] text-muted-foreground">
                Model ưu tiên sử dụng với khóa này (tùy chọn)
              </p>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="key-priority">Độ ưu tiên (Priority)</Label>
                <Badge variant="outline" className="font-mono text-[10px]">
                  {priority}
                </Badge>
              </div>
              <Input
                id="key-priority"
                type="number"
                min={1}
                max={10}
                value={priority}
                onChange={(e) => setPriority(Number(e.target.value))}
              />
              <p className="text-[11px] text-muted-foreground">
                Thang điểm từ 1 (cao nhất) đến 10 (thấp nhất)
              </p>
            </div>
          </div>

          {/* Test Connection Button & Result */}
          <div className="rounded-lg border border-border/80 bg-muted/20 p-3.5 space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 font-medium text-foreground">
                <Sparkles className="size-3.5 text-primary" />
                <span>Kiểm tra kết nối</span>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 text-xs gap-1.5"
                disabled={testResult.status === "testing" || !secret.trim()}
                onClick={handleTestConnection}
              >
                {testResult.status === "testing" ? (
                  <>
                    <Loader2 className="size-3 animate-spin" />
                    <span>Đang kiểm tra...</span>
                  </>
                ) : (
                  <>
                    <Check className="size-3 text-primary" />
                    <span>Kiểm tra kết nối</span>
                  </>
                )}
              </Button>
            </div>

            {testResult.status === "success" && (
              <Alert className="border-success/40 bg-success/10 py-2 text-xs">
                <Check className="size-3.5 text-success mr-2" />
                <AlertDescription className="text-foreground">
                  {testResult.message}
                </AlertDescription>
              </Alert>
            )}

            {testResult.status === "error" && (
              <Alert variant="destructive" className="py-2 text-xs">
                <X className="size-3.5 mr-2" />
                <AlertDescription>{testResult.message}</AlertDescription>
              </Alert>
            )}
          </div>

          <ResponsiveDialogFooter className="grid grid-cols-2 gap-2 border-t bg-card pt-4 sm:flex sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <Button type="submit" disabled={addKeyMutation.isPending}>
              {addKeyMutation.isPending ? "Đang lưu…" : "Lưu API Key"}
            </Button>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

