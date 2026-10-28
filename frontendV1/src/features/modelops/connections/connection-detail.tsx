import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  Bot,
  Copy,
  Cpu,
  Download,
  FlaskConical,
  Key,
  Loader2,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useState } from "react";
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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import type { Provider, ProviderKey } from "../types";
import {
  FAMILIES,
  useAddConnectionModel,
  useConnection,
  useConnectionKeys,
  useConnectionModels,
  useDeleteConnection,
  useDeleteConnectionKey,
  useDeleteConnectionModel,
  useTestConnection,
} from "./api";
import { ConnectionForm } from "./connection-form";
import { ConnectionKeyModal } from "./connection-key-modal";
import { ImportModelsDialog } from "./import-models-dialog";
import { ModelTestModal } from "./model-test-modal";

export function ConnectionDetail({ connectionId }: { connectionId: string }) {
  const navigate = useNavigate();
  const query = useConnection(connectionId);
  const modelsQuery = useConnectionModels(connectionId);
  const keysQuery = useConnectionKeys(connectionId);

  const deleteConnectionMutation = useDeleteConnection();
  const addModelMutation = useAddConnectionModel(connectionId);
  const deleteModelMutation = useDeleteConnectionModel(connectionId);
  const deleteKeyMutation = useDeleteConnectionKey(connectionId);
  const testMutation = useTestConnection(connectionId);

  // Dialog states
  const [editOpen, setEditOpen] = useState(false);
  const [addKeyOpen, setAddKeyOpen] = useState(false);
  const [importModelsOpen, setImportModelsOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [modelToTest, setModelToTest] = useState<Provider | null>(null);

  // New model input
  const [newModelId, setNewModelId] = useState("");
  const [roundRobin, setRoundRobin] = useState(false);
  const [testingAll, setTestingAll] = useState(false);
  const [testingKeyId, setTestingKeyId] = useState<string | null>(null);

  const connection =
    query.data && !Array.isArray(query.data) ? query.data : undefined;
  const models = modelsQuery.data ?? [];
  const keys = keysQuery.data ?? [];

  if (query.isLoading) return <Skeleton className="h-64 w-full rounded-xl" />;
  if (query.isError || !connection) {
    return (
      <div className="space-y-4">
        <Button asChild size="sm" variant="ghost">
          <Link to="/providers">
            <ArrowLeft className="size-4 mr-1" />
            Về danh sách nhà cung cấp
          </Link>
        </Button>
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      </div>
    );
  }

  const handleDeleteConnection = async () => {
    try {
      await deleteConnectionMutation.mutateAsync(connectionId);
      toast.success(`Đã xóa nhà cung cấp ${connection.name}.`);
      void navigate({ to: "/providers" });
    } catch {
      toast.error("Không thể xóa nhà cung cấp. Vui lòng thử lại.");
    }
  };

  const handleAddModel = async () => {
    if (!newModelId.trim()) return;
    try {
      await addModelMutation.mutateAsync({
        model_name: newModelId.trim(),
        capabilities: ["chat"],
      });
      toast.success(`Đã thêm model ${newModelId.trim()}.`);
      setNewModelId("");
    } catch {
      toast.error("Không thể thêm model. Vui lòng kiểm tra lại API Key dùng chung.");
    }
  };

  const handleDeleteModel = async (model: Provider) => {
    if (!confirm(`Bạn có chắc muốn xóa model ${model.model_name}?`)) return;
    try {
      await deleteModelMutation.mutateAsync(model.id);
      toast.success(`Đã xóa model ${model.model_name}.`);
    } catch {
      toast.error("Không thể xóa model.");
    }
  };

  const handleDeleteKey = async (key: ProviderKey) => {
    if (!confirm(`Bạn có chắc muốn xóa API Key '${key.name}'?`)) return;
    try {
      await deleteKeyMutation.mutateAsync(key.id);
      toast.success(`Đã xóa API Key ${key.name}.`);
    } catch {
      toast.error("Không thể xóa API Key.");
    }
  };

  const handleTestAllConnections = async () => {
    setTestingAll(true);
    try {
      const res = await testMutation.mutateAsync({});
      if (res.ok) {
        toast.success(res.detail || "Kết nối thành công tới nhà cung cấp!");
      } else {
        toast.error(res.detail || "Kiểm tra kết nối thất bại.");
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Kiểm tra kết nối thất bại.");
    } finally {
      setTestingAll(false);
    }
  };

  const handleTestSingleKey = async (key: ProviderKey) => {
    setTestingKeyId(key.id);
    try {
      const res = await testMutation.mutateAsync({});
      if (res.ok) {
        toast.success(`Khóa '${key.name}': ${res.detail}`);
      } else {
        toast.error(`Khóa '${key.name}': ${res.detail}`);
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Kiểm tra kết nối thất bại.");
    } finally {
      setTestingKeyId(null);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    void navigator.clipboard.writeText(text);
    toast.success(`Đã sao chép ${label}.`);
  };

  const fullPrefix = connection.prefix ? `${connection.prefix}/` : "";

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Button asChild size="sm" variant="ghost" className="text-xs gap-1.5 -ml-2 text-muted-foreground hover:text-foreground">
        <Link to="/providers">
          <ArrowLeft className="size-3.5" />
          <span>Quay lại danh sách</span>
        </Link>
      </Button>

      {/* Header with Provider Logo and Title */}
      <div className="flex items-center gap-3">
        <div className="flex size-12 items-center justify-center rounded-2xl bg-muted/60 border border-border/80 text-primary shadow-xs">
          {connection.family === "anthropic" ? (
            <Sparkles className="size-6 text-amber-600 dark:text-amber-400" />
          ) : connection.family === "qnu" ? (
            <Cpu className="size-6 text-teal-600 dark:text-teal-400" />
          ) : (
            <Bot className="size-6 text-primary" />
          )}
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            {connection.name}
          </h1>
          <p className="text-xs text-muted-foreground">
            {keys.length} kết nối · {FAMILIES[connection.family] ?? "OpenAI Compatible"}
          </p>
        </div>
      </div>

      {/* CARD 1: Provider Details */}
      <Card className="rounded-xl shadow-2xs border-border/80">
        <CardContent className="p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-sm font-semibold text-foreground">
              Chi tiết kết nối
            </h2>
            <p className="text-xs text-muted-foreground font-mono break-all">
              Hoàn thành trò chuyện (Chat) · {connection.base_url}/chat/completions
            </p>
            {connection.prefix && (
              <p className="text-[11px] text-muted-foreground font-mono">
                Tiền tố model: <span className="font-semibold text-foreground">{connection.prefix}/</span>
              </p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {/* Primary Action: Thêm API Key */}
            <Button
              size="sm"
              className="h-8 gap-1.5 text-xs font-semibold shadow-xs"
              onClick={() => setAddKeyOpen(true)}
            >
              <Plus className="size-3.5" />
              <span>Thêm API Key</span>
            </Button>

            {/* Edit */}
            <Button
              size="sm"
              variant="outline"
              className="h-8 gap-1.5 text-xs"
              onClick={() => setEditOpen(true)}
            >
              <Pencil className="size-3.5" />
              <span>Chỉnh sửa</span>
            </Button>

            {/* Delete */}
            <Button
              size="sm"
              variant="outline"
              className="h-8 gap-1.5 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={() => setDeleteConfirmOpen(true)}
            >
              <Trash2 className="size-3.5" />
              <span>Xóa</span>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* CARD 2: Connections (API Keys) */}
      <Card className="rounded-xl shadow-2xs border-border/80">
        <CardHeader className="p-5 pb-3 border-b flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <CardTitle className="text-sm font-semibold">Danh sách API Key</CardTitle>

          <div className="flex items-center gap-3 shrink-0">
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs gap-1.5"
              disabled={testingAll || keys.length === 0}
              onClick={handleTestAllConnections}
            >
              {testingAll ? (
                <Loader2 className="size-3 animate-spin" />
              ) : (
                <RefreshCw className="size-3 text-muted-foreground" />
              )}
              <span>Kiểm tra kết nối lần lượt</span>
            </Button>

            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span>Xoay vòng khóa (Round Robin)</span>
              <Switch
                checked={roundRobin}
                onCheckedChange={setRoundRobin}
                className="scale-75"
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-5 space-y-3">
          {keysQuery.isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : keys.length === 0 ? (
            <div className="text-center p-6 space-y-2 text-muted-foreground">
              <Key className="size-6 mx-auto text-muted-foreground/40" />
              <p className="text-xs">Chưa có API Key nào được thiết lập cho nhà cung cấp này.</p>
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs gap-1.5 mt-1"
                onClick={() => setAddKeyOpen(true)}
              >
                <Plus className="size-3" />
                <span>Thêm API Key đầu tiên</span>
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {keys.map((key, index) => {
                const isTestingThis = testingKeyId === key.id;

                return (
                  <div
                    key={key.id}
                    className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-3 rounded-lg border border-border/80 bg-muted/10 hover:bg-muted/20 transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <Key className="size-4 text-muted-foreground shrink-0" />
                      <div className="min-w-0 space-y-0.5">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-xs text-foreground">
                            {key.name}
                          </span>
                          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                            <span className="size-1.5 rounded-full bg-emerald-500" />
                            Đang hoạt động
                          </span>
                          <Badge variant="secondary" className="text-[10px] py-0 px-1 font-normal">
                            Khóa API
                          </Badge>
                          <span className="font-mono text-[11px] text-muted-foreground">
                            #{index + 1} · {key.masked_hint}
                          </span>
                          <Badge variant="outline" className="text-[10px] py-0 px-1 font-mono">
                            Ưu tiên: {key.priority}
                          </Badge>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-auto">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-xs gap-1 text-primary hover:text-primary"
                        disabled={isTestingThis}
                        onClick={() => handleTestSingleKey(key)}
                        title="Kiểm tra kết nối khóa này"
                      >
                        {isTestingThis ? (
                          <Loader2 className="size-3 animate-spin" />
                        ) : (
                          <Play className="size-3" />
                        )}
                        <span>Kiểm tra</span>
                      </Button>

                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={() => handleDeleteKey(key)}
                        title="Xóa API Key"
                      >
                        <Trash2 className="size-3.5" />
                        <span className="sr-only">Xóa</span>
                      </Button>

                      <Switch
                        checked={key.status === "active"}
                        className="scale-75"
                        disabled
                        title="Trạng thái kích hoạt"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* CARD 3: Available Models */}
      <Card className="rounded-xl shadow-2xs border-border/80">
        <CardHeader className="p-5 pb-3 border-b space-y-1">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold">Mô hình sẵn có (LLM Models)</CardTitle>
          </div>
          <p className="text-xs text-muted-foreground">
            Thêm mô hình tương thích OpenAI bằng tay hoặc nhập tự động từ endpoint /models.
          </p>
        </CardHeader>

        <CardContent className="p-5 space-y-4">
          {/* Model ID Input Bar (as shown in screenshot) */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <div className="relative flex-1">
              <Input
                value={newModelId}
                onChange={(e) => setNewModelId(e.target.value)}
                placeholder="Mã mô hình (Model ID, ví dụ: gpt-4o, qwen3.8-27b-q4...)"
                className="font-mono text-xs h-9"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    void handleAddModel();
                  }
                }}
              />
            </div>

            <Button
              size="sm"
              className="h-9 gap-1.5 text-xs shrink-0"
              disabled={!newModelId.trim() || addModelMutation.isPending}
              onClick={handleAddModel}
            >
              {addModelMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Plus className="size-3.5" />
              )}
              <span>Thêm model</span>
            </Button>

            <Button
              size="sm"
              variant="outline"
              className="h-9 gap-1.5 text-xs shrink-0 text-foreground"
              onClick={() => setImportModelsOpen(true)}
            >
              <Download className="size-3.5" />
              <span>Nhập từ /models</span>
            </Button>
          </div>

          {/* Model List Items (as shown in screenshot) */}
          {modelsQuery.isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : models.length === 0 ? (
            <div className="text-center p-6 space-y-1 text-muted-foreground border rounded-lg bg-muted/10">
              <Bot className="size-6 mx-auto text-muted-foreground/40" />
              <p className="text-xs">Chưa có model nào được thêm.</p>
              <p className="text-[11px]">Nhập Mã mô hình ở trên rồi bấm 'Thêm model' hoặc bấm 'Nhập từ /models'.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {models.map((m) => {
                const fullModelPath = `${fullPrefix}${m.model_name}`;

                return (
                  <div
                    key={m.id}
                    className="flex items-center justify-between p-3 rounded-lg border border-border/80 bg-muted/10 hover:bg-muted/20 transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="flex size-7 shrink-0 items-center justify-center rounded bg-primary/10 text-primary">
                        <Bot className="size-4" />
                      </div>
                      <div className="min-w-0 space-y-0.5">
                        <p className="font-mono text-xs font-semibold text-foreground truncate">
                          {m.model_name}
                        </p>
                        <p className="font-mono text-[11px] text-muted-foreground truncate">
                          {fullModelPath}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0 ml-2">
                      {/* Copy Model ID */}
                      <Button
                        size="sm"
                        variant="ghost"
                        className="size-7 p-0 text-muted-foreground hover:text-foreground"
                        onClick={() => copyToClipboard(fullModelPath, "tên model")}
                        title="Sao chép tên model"
                      >
                        <Copy className="size-3.5" />
                      </Button>

                      {/* Test Model Flask Icon */}
                      <Button
                        size="sm"
                        variant="ghost"
                        className="size-7 p-0 text-primary hover:text-primary hover:bg-primary/10"
                        onClick={() => setModelToTest(m)}
                        title="Chạy thử nghiệm / test model này"
                      >
                        <FlaskConical className="size-3.5" />
                      </Button>

                      {/* Delete Model */}
                      <Button
                        size="sm"
                        variant="ghost"
                        className="size-7 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={() => handleDeleteModel(m)}
                        title="Xóa model khỏi nhà cung cấp"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* MODAL 1: Edit Connection Form */}
      <ConnectionForm
        open={editOpen}
        onOpenChange={setEditOpen}
        connection={connection}
        onCreated={() => void query.refetch()}
      />

      {/* MODAL 2: Add API Key Modal */}
      <ConnectionKeyModal
        open={addKeyOpen}
        onOpenChange={setAddKeyOpen}
        connectionId={connectionId}
        connectionName={connection.name}
        availableModels={models.map((m) => m.model_name)}
        onKeyAdded={() => {
          void keysQuery.refetch();
          void query.refetch();
        }}
      />

      {/* MODAL 3: Import Models from /models */}
      <ImportModelsDialog
        open={importModelsOpen}
        onOpenChange={setImportModelsOpen}
        connectionId={connectionId}
        connectionName={connection.name}
        existingModels={models.map((m) => m.model_name)}
        onModelAdded={() => {
          void modelsQuery.refetch();
          void query.refetch();
        }}
      />

      {/* MODAL 4: Model Test Modal */}
      <ModelTestModal
        open={Boolean(modelToTest)}
        onOpenChange={(open) => {
          if (!open) setModelToTest(null);
        }}
        model={modelToTest}
        connectionName={connection.name}
      />

      {/* Delete Connection Confirmation Dialog */}
      <ResponsiveDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <ResponsiveDialogContent className="max-w-md p-5 text-xs space-y-4">
          <ResponsiveDialogHeader>
            <ResponsiveDialogTitle>Xóa nhà cung cấp AI</ResponsiveDialogTitle>
            <ResponsiveDialogDescription className="text-xs">
              Bạn có chắc chắn muốn xóa nhà cung cấp <strong>{connection.name}</strong>? Thao tác này sẽ xóa toàn bộ các API Key và model thuộc nhà cung cấp này.
            </ResponsiveDialogDescription>
          </ResponsiveDialogHeader>
          <ResponsiveDialogFooter className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setDeleteConfirmOpen(false)}>
              Hủy
            </Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={deleteConnectionMutation.isPending}
              onClick={handleDeleteConnection}
            >
              {deleteConnectionMutation.isPending ? "Đang xóa..." : "Xác nhận xóa"}
            </Button>
          </ResponsiveDialogFooter>
        </ResponsiveDialogContent>
      </ResponsiveDialog>
    </div>
  );
}
