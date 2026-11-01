import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  ArrowUpDown,
  Bot,
  Copy,
  Cpu,
  Download,
  FileText,
  FlaskConical,
  Gauge,
  Key,
  Layers,
  Loader2,
  MoreHorizontal,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { v1Client } from "@/app/api/v1";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { updateProvider } from "@/features/modelops/requests";
import {
  CapacityBadge,
  ProviderOperationalBudgetsSummary,
} from "../capacity-badge";
import { useDiagnostics } from "../diagnostic-queries";
import { CapacityPanel } from "../provider-detail";
import { ProviderFormDialog } from "../provider-form-dialog";
import type { Capability, Provider, ProviderKey } from "../types";
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
  return (
    <ConnectionDetailContent key={connectionId} connectionId={connectionId} />
  );
}

function ConnectionDetailContent({ connectionId }: { connectionId: string }) {
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
  const [modelToInspect, setModelToInspect] = useState<Provider | null>(null);
  const [modelToDelete, setModelToDelete] = useState<Provider | null>(null);
  const [keyToDelete, setKeyToDelete] = useState<ProviderKey | null>(null);

  // New model input & capability
  const [newModelId, setNewModelId] = useState("");
  const [newModelCapability, setNewModelCapability] =
    useState<Capability>("chat");

  // Edit model modal state
  const [modelToEdit, setModelToEdit] = useState<Provider | null>(null);

  const handleModelNameChange = (val: string) => {
    setNewModelId(val);
    const lower = val.toLowerCase();
    if (lower.includes("embed") || lower.includes("bge-m3")) {
      setNewModelCapability("embedding");
    } else if (lower.includes("rerank")) {
      setNewModelCapability("rerank");
    } else if (
      lower.includes("ocr") ||
      lower.includes("parse") ||
      lower.includes("nemotron")
    ) {
      setNewModelCapability("ocr");
    } else {
      setNewModelCapability("chat");
    }
  };

  const diagnostics = useDiagnostics(connectionId);
  const [keyResults, setKeyResults] = useState<Record<string, string>>({});
  const operation = useRef(0);
  useEffect(() => {
    operation.current += 1;
    setKeyResults({});
    return () => {
      operation.current += 1;
    };
  }, []);
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
    const trimmed = newModelId.trim();
    try {
      const created = await addModelMutation.mutateAsync({
        model_name: trimmed,
        capabilities: [newModelCapability],
      });

      // Nếu là connection QNU AI trên máy 100.105.13.53: tự động gán port tương ứng cho embedding/ocr
      if (connection.base_url.includes("100.105.13.53") && created?.id) {
        let targetPort = "8000";
        if (newModelCapability === "embedding" || trimmed.includes("bge-m3")) {
          targetPort = "8001";
        } else if (
          newModelCapability === "ocr" ||
          trimmed.includes("nemotron")
        ) {
          targetPort = "8081";
        }
        if (targetPort !== "8000") {
          try {
            await updateProvider(v1Client, created.id, {
              base_url: `http://100.105.13.53:${targetPort}/v1`,
            });
          } catch {
            // Port mapping update optional
          }
        }
      }

      toast.success(`Đã thêm model ${trimmed}.`);
      setNewModelId("");
      void modelsQuery.refetch();
    } catch (err: unknown) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Không thể thêm model. Vui lòng kiểm tra lại API Key dùng chung.",
      );
    }
  };

  const handleConfirmDeleteModel = async () => {
    if (!modelToDelete) return;
    try {
      await deleteModelMutation.mutateAsync(modelToDelete.id);
      toast.success(`Đã xóa model ${modelToDelete.model_name}.`);
      setModelToDelete(null);
    } catch {
      toast.error("Không thể xóa model.");
    }
  };

  const handleConfirmDeleteKey = async () => {
    if (!keyToDelete) return;
    try {
      await deleteKeyMutation.mutateAsync(keyToDelete.id);
      toast.success(`Đã xóa API Key ${keyToDelete.name}.`);
      setKeyToDelete(null);
    } catch {
      toast.error("Không thể xóa API Key.");
    }
  };

  const runKeyTest = async (key: ProviderKey, ticket: number) => {
    try {
      const res = await testMutation.mutateAsync({ key_id: key.id });
      if (ticket !== operation.current) return false;
      setKeyResults((previous) => ({
        ...previous,
        [key.id]: `${res.ok ? "Đạt" : "Lỗi"}: ${res.detail}${res.latency_ms != null ? ` (${res.latency_ms} ms)` : ""}`,
      }));
      return res.ok;
    } catch (error) {
      if (ticket === operation.current)
        setKeyResults((previous) => ({
          ...previous,
          [key.id]: `Lỗi: ${error instanceof Error ? error.message : "Không kiểm tra được kết nối."}`,
        }));
      return false;
    }
  };
  const handleTestAllConnections = async () => {
    const ticket = operation.current;
    setTestingAll(true);
    let passed = 0;
    const active = keys.filter((key) => key.status === "active");
    try {
      for (const key of active) {
        if (ticket !== operation.current) return;
        setTestingKeyId(key.id);
        if (await runKeyTest(key, ticket)) passed += 1;
      }
      if (ticket === operation.current) {
        const detail = `Đã kiểm tra ${active.length} khóa: ${passed} đạt, ${active.length - passed} lỗi; ${keys.length - active.length} khóa không hoạt động được bỏ qua.`;
        if (passed === active.length) toast.success(detail);
        else toast.error(detail);
      }
    } finally {
      if (ticket === operation.current) {
        setTestingAll(false);
        setTestingKeyId(null);
      }
    }
  };
  const handleTestSingleKey = async (key: ProviderKey) => {
    const ticket = operation.current;
    setTestingKeyId(key.id);
    try {
      await runKeyTest(key, ticket);
    } finally {
      if (ticket === operation.current) setTestingKeyId(null);
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
      <Button
        asChild
        size="sm"
        variant="ghost"
        className="text-xs gap-1.5 -ml-2 text-muted-foreground hover:text-foreground"
      >
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
            {keys.length} kết nối ·{" "}
            {FAMILIES[connection.family] ?? "OpenAI Compatible"}
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
              Hoàn thành trò chuyện (Chat) · {connection.base_url}
              /chat/completions
            </p>
            {connection.prefix && (
              <p className="text-[11px] text-muted-foreground font-mono">
                Tiền tố model:{" "}
                <span className="font-semibold text-foreground">
                  {connection.prefix}/
                </span>
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
          <CardTitle className="text-sm font-semibold">
            Danh sách API Key
          </CardTitle>

          <div className="flex items-center gap-3 shrink-0">
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs gap-1.5"
              disabled={
                testingAll ||
                testingKeyId !== null ||
                !connection.is_active ||
                !keys.some((key) => key.status === "active")
              }
              onClick={handleTestAllConnections}
            >
              {testingAll ? (
                <Loader2 className="size-3 animate-spin" />
              ) : (
                <RefreshCw className="size-3 text-muted-foreground" />
              )}
              <span>Kiểm tra kết nối lần lượt</span>
            </Button>

            <p className="text-xs text-muted-foreground">
              Xoay khóa theo chính sách ModelOps của từng model.
            </p>
          </div>
        </CardHeader>

        <CardContent className="p-5 space-y-3">
          {keysQuery.isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : keys.length === 0 ? (
            <div className="text-center p-6 space-y-2 text-muted-foreground">
              <Key className="size-6 mx-auto text-muted-foreground/40" />
              <p className="text-xs">
                Chưa có API Key nào được thiết lập cho nhà cung cấp này.
              </p>
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
                    className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-3 rounded-lg bg-muted/20 hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <Key className="size-4 text-muted-foreground shrink-0" />
                      <div className="min-w-0 space-y-0.5">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-xs text-foreground">
                            {key.name}
                          </span>
                          <span
                            className={`inline-flex items-center gap-1 text-[10px] font-medium ${key.status === "active" ? "text-success" : "text-muted-foreground"}`}
                          >
                            <span
                              className={`size-1.5 rounded-full ${key.status === "active" ? "bg-success" : "bg-muted-foreground"}`}
                            />
                            {key.status === "active"
                              ? "Đang hoạt động"
                              : key.status === "revoked"
                                ? "Đã thu hồi"
                                : "Đã tạm dừng"}
                          </span>
                          <Badge
                            variant="secondary"
                            className="text-[10px] py-0 px-1 font-normal"
                          >
                            Khóa API
                          </Badge>
                          <span className="font-mono text-[11px] text-muted-foreground">
                            #{index + 1} · {key.masked_hint}
                          </span>
                          <Badge
                            variant="outline"
                            className="text-[10px] py-0 px-1 font-mono"
                          >
                            Ưu tiên: {key.priority}
                          </Badge>
                        </div>
                      </div>
                    </div>

                    <p
                      className="text-xs text-muted-foreground break-words"
                      role="status"
                    >
                      {keyResults[key.id] ??
                        (() => {
                          const check = diagnostics.data?.checks.find(
                            (item) => item.key_id === key.id,
                          );
                          if (!check)
                            return "Chưa có kết quả kiểm tra khóa này.";
                          return `${check.configuration_status === "stale" ? "Cần kiểm tra lại" : check.outcome === "ok" ? "Đạt" : "Lỗi"}: ${check.detail} · ${new Date(check.tested_at).toLocaleString("vi-VN")}`;
                        })()}
                    </p>
                    <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-auto">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-xs gap-1 text-primary hover:text-primary"
                        disabled={
                          testingAll ||
                          testingKeyId !== null ||
                          !connection.is_active ||
                          key.status !== "active"
                        }
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
                        onClick={() => setKeyToDelete(key)}
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
            <CardTitle className="text-sm font-semibold">
              Mô hình sẵn có (LLM Models)
            </CardTitle>
          </div>
          <p className="text-xs text-muted-foreground">
            Thêm mô hình tương thích OpenAI bằng tay hoặc nhập tự động từ
            endpoint /models.
          </p>
        </CardHeader>

        <CardContent className="p-5 space-y-4">
          {/* Model ID Input Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <div className="relative flex-1">
              <Input
                value={newModelId}
                onChange={(e) => handleModelNameChange(e.target.value)}
                placeholder="Mã mô hình (Model ID, ví dụ: gpt-4o, bge-m3, nemotron-parse...)"
                className="font-mono text-xs h-9"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    void handleAddModel();
                  }
                }}
              />
            </div>

            <div className="w-full sm:w-48 shrink-0">
              <Select
                value={newModelCapability}
                onValueChange={(v) => setNewModelCapability(v as Capability)}
              >
                <SelectTrigger className="h-9 text-xs">
                  <SelectValue placeholder="Chức năng..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="chat">Trò chuyện (Chat)</SelectItem>
                  <SelectItem value="embedding">
                    Nhúng vector (Embedding)
                  </SelectItem>
                  <SelectItem value="rerank">
                    Xếp hạng lại (Reranker)
                  </SelectItem>
                  <SelectItem value="ocr">Bóc tách văn bản (OCR)</SelectItem>
                </SelectContent>
              </Select>
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

          {/* Model List Items */}
          {modelsQuery.isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : models.length === 0 ? (
            <div className="text-center p-6 space-y-1 text-muted-foreground border rounded-lg bg-muted/10">
              <Bot className="size-6 mx-auto text-muted-foreground/40" />
              <p className="text-xs">Chưa có model nào được thêm.</p>
              <p className="text-[11px]">
                Nhập Mã mô hình ở trên rồi bấm 'Thêm model' hoặc bấm 'Nhập từ
                /models'.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {models.map((m) => {
                const fullModelPath = `${fullPrefix}${m.model_name}`;
                const visual = (() => {
                  const cap = (m.capabilities?.[0] as Capability) || "chat";
                  switch (cap) {
                    case "embedding":
                      return {
                        icon: <Layers className="size-4 text-amber-500" />,
                        badge: (
                          <Badge
                            variant="outline"
                            className="text-[10px] py-0 px-1.5 border-amber-500/40 text-amber-600 bg-amber-500/10 font-normal"
                          >
                            Nhúng vector (Embedding)
                          </Badge>
                        ),
                      };
                    case "rerank":
                      return {
                        icon: (
                          <ArrowUpDown className="size-4 text-emerald-500" />
                        ),
                        badge: (
                          <Badge
                            variant="outline"
                            className="text-[10px] py-0 px-1.5 border-emerald-500/40 text-emerald-600 bg-emerald-500/10 font-normal"
                          >
                            Xếp hạng lại (Reranker)
                          </Badge>
                        ),
                      };
                    case "ocr":
                      return {
                        icon: <FileText className="size-4 text-rose-500" />,
                        badge: (
                          <Badge
                            variant="outline"
                            className="text-[10px] py-0 px-1.5 border-rose-500/40 text-rose-600 bg-rose-500/10 font-normal"
                          >
                            Bóc tách văn bản (OCR)
                          </Badge>
                        ),
                      };
                    default:
                      return {
                        icon: <Bot className="size-4 text-blue-500" />,
                        badge: (
                          <Badge
                            variant="secondary"
                            className="text-[10px] py-0 px-1.5 text-blue-600 bg-blue-500/10 font-normal"
                          >
                            Trò chuyện (Chat)
                          </Badge>
                        ),
                      };
                  }
                })();

                return (
                  <div
                    key={m.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/20 hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="flex size-7 shrink-0 items-center justify-center rounded bg-muted/60">
                        {visual.icon}
                      </div>
                      <div className="min-w-0 space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="font-mono text-xs font-semibold text-foreground truncate">
                            {m.model_name}
                          </p>
                          {visual.badge}
                          <CapacityBadge status={m.capacity_status} />
                        </div>
                        <ProviderOperationalBudgetsSummary
                          provider={m}
                          compact
                        />
                        <p className="font-mono text-[11px] text-muted-foreground truncate">
                          Endpoint: {m.base_url}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0 ml-2">
                      {/* Edit Model (kept directly accessible for quick edit & test compatibility) */}
                      <Button
                        size="sm"
                        variant="ghost"
                        className="size-7 p-0 text-muted-foreground hover:text-foreground"
                        onClick={() => setModelToEdit(m)}
                        title="Cấu hình model và giới hạn xử lý"
                      >
                        <Pencil className="size-3.5" />
                      </Button>

                      {/* Grouped secondary actions in 1 DropdownMenu per ui-standards.md */}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="size-7 p-0 text-muted-foreground hover:text-foreground"
                            aria-label={`Tác vụ khác cho model ${m.model_name}`}
                          >
                            <MoreHorizontal className="size-3.5" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="text-xs">
                          <DropdownMenuItem
                            onClick={() => setModelToInspect(m)}
                          >
                            <Gauge className="size-3.5 mr-2" />
                            <span>Giới hạn &amp; Ngân sách đang áp dụng</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setModelToTest(m)}>
                            <FlaskConical className="size-3.5 mr-2" />
                            <span>Chạy thử nghiệm model</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() =>
                              copyToClipboard(fullModelPath, "tên model")
                            }
                          >
                            <Copy className="size-3.5 mr-2" />
                            <span>Sao chép tên model</span>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => setModelToDelete(m)}
                          >
                            <Trash2 className="size-3.5 mr-2" />
                            <span>Xóa model</span>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
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

      {/* MODAL 5: Edit Model Dialog */}
      {modelToEdit ? (
        <ProviderFormDialog
          open={Boolean(modelToEdit)}
          provider={modelToEdit}
          onOpenChange={(open) => {
            if (!open) setModelToEdit(null);
          }}
        />
      ) : null}

      {/* MODAL 6: Inspect Model Capacity & Operational Budgets */}
      <ResponsiveDialog
        open={Boolean(modelToInspect)}
        onOpenChange={(open) => {
          if (!open) setModelToInspect(null);
        }}
      >
        <ResponsiveDialogContent className="max-w-2xl p-5 space-y-4">
          <ResponsiveDialogHeader>
            <ResponsiveDialogTitle>
              Giới hạn &amp; Ngân sách xử lý:{" "}
              <span className="font-mono">{modelToInspect?.model_name}</span>
            </ResponsiveDialogTitle>
            <ResponsiveDialogDescription className="text-xs">
              Phân biệt thông số giới hạn đã biết của model với ngân sách vận
              hành mà ứng dụng đang áp dụng.
            </ResponsiveDialogDescription>
          </ResponsiveDialogHeader>
          {modelToInspect ? (
            <CapacityPanel
              provider={
                models.find((item) => item.id === modelToInspect.id) ??
                modelToInspect
              }
              canManage={true}
              onEdit={() => {
                const target =
                  models.find((item) => item.id === modelToInspect.id) ??
                  modelToInspect;
                setModelToInspect(null);
                setModelToEdit(target);
              }}
            />
          ) : null}
          <ResponsiveDialogFooter className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setModelToInspect(null)}
            >
              Đóng
            </Button>
          </ResponsiveDialogFooter>
        </ResponsiveDialogContent>
      </ResponsiveDialog>

      {/* Delete Model Confirmation Dialog */}
      <ConfirmDialog
        open={Boolean(modelToDelete)}
        onOpenChange={(open) => {
          if (!open) setModelToDelete(null);
        }}
        title="Xóa model khỏi nhà cung cấp"
        description={
          <>
            Bạn có chắc chắn muốn xóa model{" "}
            <strong className="font-mono">{modelToDelete?.model_name}</strong>{" "}
            khỏi nhà cung cấp <strong>{connection.name}</strong>?
          </>
        }
        confirmLabel="Xóa model"
        confirmVariant="destructive"
        isLoading={deleteModelMutation.isPending}
        onConfirm={() => void handleConfirmDeleteModel()}
      />

      {/* Delete API Key Confirmation Dialog */}
      <ConfirmDialog
        open={Boolean(keyToDelete)}
        onOpenChange={(open) => {
          if (!open) setKeyToDelete(null);
        }}
        title="Xóa API Key"
        description={
          <>
            Bạn có chắc chắn muốn xóa API Key{" "}
            <strong>{keyToDelete?.name}</strong>?
          </>
        }
        confirmLabel="Xóa khóa"
        confirmVariant="destructive"
        isLoading={deleteKeyMutation.isPending}
        onConfirm={() => void handleConfirmDeleteKey()}
      />

      {/* Delete Connection Confirmation Dialog */}
      <ResponsiveDialog
        open={deleteConfirmOpen}
        onOpenChange={setDeleteConfirmOpen}
      >
        <ResponsiveDialogContent className="max-w-md p-5 text-xs space-y-4">
          <ResponsiveDialogHeader>
            <ResponsiveDialogTitle>Xóa nhà cung cấp AI</ResponsiveDialogTitle>
            <ResponsiveDialogDescription className="text-xs">
              Bạn có chắc chắn muốn xóa nhà cung cấp{" "}
              <strong>{connection.name}</strong>? Thao tác này sẽ xóa toàn bộ
              các API Key và model thuộc nhà cung cấp này.
            </ResponsiveDialogDescription>
          </ResponsiveDialogHeader>
          <ResponsiveDialogFooter className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDeleteConfirmOpen(false)}
            >
              Hủy
            </Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={deleteConnectionMutation.isPending}
              onClick={handleDeleteConnection}
            >
              {deleteConnectionMutation.isPending
                ? "Đang xóa..."
                : "Xác nhận xóa"}
            </Button>
          </ResponsiveDialogFooter>
        </ResponsiveDialogContent>
      </ResponsiveDialog>
    </div>
  );
}
