import {
  AlertCircle,
  CheckCircle2,
  Cpu,
  FlaskConical,
  Key,
  Loader2,
  MoreHorizontal,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  useAddKeyMutation,
  useConnectionKeysQuery,
  useConnectionModelsQuery,
  useDeleteKeyMutation,
  useDeleteModelMutation,
  useSyncModelCapacityMutation,
  useTestConnectionMutation,
  useUpdateConnectionMutation,
} from "@/api/modelops/queries";
import type {
  CapacitySource,
  Connection,
  ConnectionFamily,
  ConnectionTestResult,
  ModelProvider,
  ProviderKey,
} from "@/api/modelops/types";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { CopyButton } from "@/components/admin/copy-button";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CAPABILITY_LABELS, CONNECTION_FAMILIES } from "./constants";
import { ModelCapacityDialog } from "./model-capacity-dialog";

const SOURCE_LABELS: Record<CapacitySource, string> = {
  server_reported: "Nhà cung cấp công bố",
  operator_configured: "Quản trị viên khai báo",
  application_default: "QNU tạm tính",
};

const SOURCE_BADGES: Record<CapacitySource, string> = {
  server_reported:
    "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
  operator_configured: "bg-primary/10 text-primary border-primary/20",
  application_default:
    "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
};

function capacitySource(model: ModelProvider): CapacitySource {
  if (model.capacity_status === "configured" && model.token_limits) {
    const sources = Object.values(model.field_sources ?? {});
    if (sources.length > 0 && sources.every((s) => s === "server_reported")) {
      return "server_reported";
    }
    if (sources.some((s) => s === "operator_configured")) {
      return "operator_configured";
    }
    return model.capacity_basis ?? "operator_configured";
  }
  return "application_default";
}

function formatLimit(value?: number | null): string {
  if (!value) return "—";
  return value >= 1000 ? `${Math.round(value / 1000)}k` : String(value);
}

function CapacitySummary({ model }: { model: ModelProvider }) {
  if (model.capacity_status === "stale") {
    return (
      <div className="space-y-0.5">
        <span className="text-[11px] text-muted-foreground">
          Endpoint hoặc model đã đổi
        </span>
        <Badge
          variant="outline"
          className="h-3.5 px-1 text-[9px] font-normal bg-destructive/10 text-destructive border-destructive/20"
        >
          Cần đồng bộ lại
        </Badge>
      </div>
    );
  }
  const source = capacitySource(model);
  const limits = model.token_limits;
  const parts: string[] = [];
  if (limits?.context_window_tokens) {
    parts.push(`Ngữ cảnh ${formatLimit(limits.context_window_tokens)}`);
  }
  if (limits?.max_input_tokens) {
    parts.push(`Đầu vào ${formatLimit(limits.max_input_tokens)}`);
  }
  if (limits?.max_output_tokens) {
    parts.push(`Đầu ra ${formatLimit(limits.max_output_tokens)}`);
  }
  if (parts.length === 0) {
    if (!model.capabilities.includes("chat")) {
      return <span className="text-[11px] text-muted-foreground">—</span>;
    }
    parts.push("Ngữ cảnh 32k · Đầu ra 4k");
  }
  return (
    <div className="space-y-0.5">
      <span className="font-mono text-[11px] text-muted-foreground">
        {parts.join(" · ")}
      </span>
      <Badge
        variant="outline"
        className={`h-3.5 px-1 text-[9px] font-normal ${SOURCE_BADGES[source]}`}
      >
        {SOURCE_LABELS[source]}
      </Badge>
    </div>
  );
}

export function ProviderDetailSheet({
  connection,
  open,
  onOpenChange,
  onOpenAddModel,
  onOpenProbeModel,
  onRequestDeleteConnection,
}: {
  connection: Connection | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenAddModel: (conn: Connection, prefillName?: string) => void;
  onOpenProbeModel: (model: ModelProvider) => void;
  onRequestDeleteConnection: (conn: Connection) => void;
}) {
  if (!connection) return null;

  return (
    <ProviderDetailSheetContent
      key={connection.id}
      connection={connection}
      open={open}
      onOpenChange={onOpenChange}
      onOpenAddModel={onOpenAddModel}
      onOpenProbeModel={onOpenProbeModel}
      onRequestDeleteConnection={onRequestDeleteConnection}
    />
  );
}

function ProviderDetailSheetContent({
  connection,
  open,
  onOpenChange,
  onOpenAddModel,
  onOpenProbeModel,
  onRequestDeleteConnection,
}: {
  connection: Connection;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenAddModel: (conn: Connection, prefillName?: string) => void;
  onOpenProbeModel: (model: ModelProvider) => void;
  onRequestDeleteConnection: (conn: Connection) => void;
}) {
  const modelsQuery = useConnectionModelsQuery(connection.id, open);
  const keysQuery = useConnectionKeysQuery(connection.id, open);

  const updateMutation = useUpdateConnectionMutation();
  const testMutation = useTestConnectionMutation(connection.id);
  const deleteModelMutation = useDeleteModelMutation(connection.id);
  const syncCapacityMutation = useSyncModelCapacityMutation(connection.id);
  const addKeyMutation = useAddKeyMutation(connection.id);
  const deleteKeyMutation = useDeleteKeyMutation(connection.id);

  const models = modelsQuery.data ?? [];
  const keys = keysQuery.data ?? [];
  const activeKey = keys.find((k) => k.status === "active") ?? keys[0];
  const familyMeta =
    CONNECTION_FAMILIES[connection.family] ?? CONNECTION_FAMILIES.custom;

  // Active tab state
  const [activeTab, setActiveTab] = useState<"models" | "keys" | "settings">(
    "models",
  );

  // Settings form states
  const [name, setName] = useState(connection.name);
  const [family, setFamily] = useState<ConnectionFamily>(connection.family);
  const [baseUrl, setBaseUrl] = useState(connection.base_url);
  const [timeoutSeconds, setTimeoutSeconds] = useState(
    connection.timeout_seconds || 30,
  );
  const [isActive, setIsActive] = useState(connection.is_active);
  const [isSavingSettings, setIsSavingSettings] = useState(false);

  // Add Key inline states
  const [showAddKeyForm, setShowAddKeyForm] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeySecret, setNewKeySecret] = useState("");
  const [newKeyPriority, setNewKeyPriority] = useState(5);
  const [isAddingKey, setIsAddingKey] = useState(false);

  // Test connection state
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(
    null,
  );

  // Delete confirmations
  const [modelToDelete, setModelToDelete] = useState<ModelProvider | null>(
    null,
  );
  const [capacityModel, setCapacityModel] = useState<ModelProvider | null>(
    null,
  );
  const [keyToDelete, setKeyToDelete] = useState<ProviderKey | null>(null);

  useEffect(() => {
    setName(connection.name);
    setFamily(connection.family);
    setBaseUrl(connection.base_url);
    setTimeoutSeconds(connection.timeout_seconds || 30);
    setIsActive(connection.is_active);
    setTestResult(null);
  }, [connection]);

  // Quick toggle active state
  const handleToggleActive = async (checked: boolean) => {
    setIsActive(checked);
    try {
      await updateMutation.mutateAsync({
        connectionId: connection.id,
        input: { is_active: checked },
      });
      toast.success(
        checked
          ? `Đã kích hoạt "${connection.name}"`
          : `Đã tắt "${connection.name}"`,
      );
    } catch (err: unknown) {
      setIsActive(!checked);
      const msg = err instanceof Error ? err.message : "Cập nhật thất bại";
      toast.error(msg);
    }
  };

  // Run test connection
  const handleRunTest = async () => {
    if (!activeKey) {
      toast.warning(
        "Nhà cung cấp chưa có khóa API hoạt động để gửi yêu cầu. Vui lòng thêm khóa trong tab 'Khóa API'!",
      );
    }
    try {
      const res = await testMutation.mutateAsync({});
      setTestResult(res);
      if (res.ok) {
        const keyHint = activeKey
          ? ` qua khóa "${activeKey.name}" (${activeKey.masked_hint})`
          : "";
        toast.success(
          `Kết nối thành công${keyHint}! Độ trễ phản hồi: ${res.latency_ms ?? 0}ms`,
        );
      } else {
        toast.error(`Kết nối thất bại: ${res.detail}`);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Kiểm tra thất bại";
      toast.error(msg);
    }
  };

  // Save settings
  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !baseUrl.trim()) {
      toast.error("Vui lòng điền đầy đủ tên và URL");
      return;
    }
    setIsSavingSettings(true);
    try {
      await updateMutation.mutateAsync({
        connectionId: connection.id,
        input: {
          name: name.trim(),
          family,
          base_url: baseUrl.trim(),
          timeout_seconds: timeoutSeconds,
          is_active: isActive,
        },
      });
      toast.success("Đã cập nhật cấu hình nhà cung cấp thành công!");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Cập nhật thất bại";
      toast.error(msg);
    } finally {
      setIsSavingSettings(false);
    }
  };

  // Add Key
  const handleAddKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim() || newKeySecret.trim().length < 8) {
      toast.error("Khóa API phải tối thiểu 8 ký tự và có tên gợi nhớ");
      return;
    }
    setIsAddingKey(true);
    try {
      await addKeyMutation.mutateAsync({
        name: newKeyName.trim(),
        secret: newKeySecret.trim(),
        priority: newKeyPriority,
      });
      toast.success(`Đã thêm khóa "${newKeyName}" thành công`);
      setNewKeyName("");
      setNewKeySecret("");
      setNewKeyPriority(5);
      setShowAddKeyForm(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Thêm khóa thất bại";
      toast.error(msg);
    } finally {
      setIsAddingKey(false);
    }
  };

  // Confirm delete model
  const handleConfirmDeleteModel = async () => {
    if (!modelToDelete) return;
    try {
      await deleteModelMutation.mutateAsync(modelToDelete.id);
      toast.success(`Đã xóa mô hình "${modelToDelete.model_name}"`);
      setModelToDelete(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Xóa mô hình thất bại";
      toast.error(msg);
    }
  };

  // Confirm delete key
  const handleConfirmDeleteKey = async () => {
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

  // Đồng bộ giới hạn token do endpoint công bố cho một model
  const handleSyncCapacity = async (model: ModelProvider) => {
    try {
      const row = await syncCapacityMutation.mutateAsync(model.model_name);
      if (!row?.token_limits) {
        toast.warning(
          `Nhà cung cấp không công bố giới hạn token cho "${model.model_name}".`,
        );
        return;
      }
      toast.success(`Đã đồng bộ giới hạn token cho "${model.model_name}"`);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Đồng bộ giới hạn thất bại";
      toast.error(msg);
    }
  };

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent
          side="right"
          className="!max-w-2xl sm:!max-w-2xl w-full p-0 flex flex-col bg-background"
        >
          {/* 1. Drawer Header */}
          <SheetHeader className="p-5 pb-4 border-b border-border/60 bg-muted/15 space-y-2">
            <div className="flex items-center justify-between pr-8">
              <div className="flex items-center gap-2 flex-wrap">
                <SheetTitle className="text-base font-bold text-foreground">
                  {connection.name}
                </SheetTitle>
                <Badge
                  variant="outline"
                  className="text-[10px] h-4.5 px-1.5 font-normal"
                >
                  {familyMeta.label}
                </Badge>
              </div>

              {/* Active Toggle Switch */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">
                  {isActive ? "Đang bật" : "Đang tắt"}
                </span>
                <Switch
                  checked={isActive}
                  onCheckedChange={handleToggleActive}
                  aria-label="Kích hoạt nhà cung cấp"
                />
              </div>
            </div>

            <SheetDescription asChild>
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-mono">
                <span
                  className="truncate max-w-[380px]"
                  title={connection.base_url}
                >
                  {connection.base_url}
                </span>
                <CopyButton
                  value={connection.base_url}
                  className="size-5 p-0"
                  tooltip="Sao chép Endpoint"
                />
              </div>
            </SheetDescription>

            {/* Quick Test Bar with Active Key Display */}
            <div className="rounded-lg border bg-muted/30 p-2.5 space-y-2 text-xs">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-muted-foreground">
                    Khóa gửi request:
                  </span>
                  {activeKey ? (
                    <span className="inline-flex items-center gap-1.5 font-medium text-foreground bg-background px-2 py-0.5 rounded border border-border/70 text-xs">
                      <Key className="size-3 text-emerald-600 dark:text-emerald-400 shrink-0" />
                      <span>{activeKey.name}</span>
                      <span className="font-mono text-[11px] text-muted-foreground">
                        ({activeKey.masked_hint})
                      </span>
                    </span>
                  ) : (
                    <Badge
                      variant="outline"
                      className="text-[10px] h-4.5 text-amber-600 border-amber-500/30 bg-amber-500/10 font-normal"
                    >
                      Chưa có khóa API
                    </Badge>
                  )}
                </div>

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs gap-1.5 shadow-2xs font-medium"
                  onClick={handleRunTest}
                  disabled={testMutation.isPending || !activeKey}
                >
                  {testMutation.isPending ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="size-3.5 text-primary" />
                  )}
                  <span>Kiểm tra kết nối</span>
                </Button>
              </div>

              {/* Status and Latency Bar */}
              <div className="flex items-center justify-between text-xs pt-1 border-t border-border/50">
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground">Trạng thái:</span>
                  {connection.last_probe_status === "success" ? (
                    <span className="inline-flex items-center gap-1 font-medium text-emerald-600 dark:text-emerald-400 text-[11px]">
                      <CheckCircle2 className="size-3.5" />
                      <span>Sẵn sàng phục vụ</span>
                    </span>
                  ) : connection.last_probe_status === "failed" ? (
                    <span className="inline-flex items-center gap-1 font-medium text-destructive text-[11px]">
                      <AlertCircle className="size-3.5" />
                      <span>Lỗi kết nối</span>
                    </span>
                  ) : (
                    <span className="text-muted-foreground text-[11px]">
                      Chưa kiểm tra độ trễ
                    </span>
                  )}
                </div>

                {testResult?.latency_ms !== null &&
                  testResult?.latency_ms !== undefined && (
                    <Badge
                      variant="outline"
                      className="text-[10px] h-4 font-mono font-normal"
                    >
                      Độ trễ: {testResult.latency_ms} ms
                    </Badge>
                  )}
              </div>

              {/* Test result alert if test just executed */}
              {testResult && (
                <Alert
                  variant={testResult.ok ? "success" : "destructive"}
                  className="text-xs py-2 mt-1"
                >
                  <AlertTitle className="text-xs font-semibold flex items-center justify-between">
                    <span>
                      {testResult.ok
                        ? "Kết nối đạt chuẩn (HTTP 200)"
                        : "Lỗi kết nối"}
                    </span>
                    {testResult.latency_ms && (
                      <span className="font-mono text-[11px]">
                        {testResult.latency_ms}ms
                      </span>
                    )}
                  </AlertTitle>
                  <AlertDescription className="text-[11px] mt-1 space-y-1">
                    <p>{testResult.detail}</p>
                    {activeKey && (
                      <p className="text-muted-foreground flex items-center gap-1 pt-0.5">
                        <span>Đã xác thực thành công qua khóa:</span>
                        <strong className="text-foreground">
                          {activeKey.name}
                        </strong>
                        <span className="font-mono text-foreground">
                          ({activeKey.masked_hint})
                        </span>
                      </p>
                    )}
                  </AlertDescription>
                </Alert>
              )}
            </div>

            {/* Discovered models banner if detected */}
            {testResult?.models && testResult.models.length > 0 && (
              <div className="rounded-md border border-primary/20 bg-primary/5 p-2.5 space-y-1.5 mt-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-primary flex items-center gap-1">
                    <Sparkles className="size-3" />
                    Máy chủ công bố {testResult.models.length} model
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    Bấm để đăng ký nhanh
                  </span>
                </div>
                <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                  {testResult.models.map((mName) => (
                    <button
                      key={mName}
                      type="button"
                      onClick={() => onOpenAddModel(connection, mName)}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-background border hover:border-primary hover:text-primary transition-colors"
                      title="Đăng ký model này"
                    >
                      <span>{mName}</span>
                      <Plus className="size-2.5 opacity-60" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </SheetHeader>

          {/* 2. Drawer Tabs Body */}
          <div className="flex-1 overflow-y-auto">
            <Tabs
              value={activeTab}
              onValueChange={(v) => setActiveTab(v as typeof activeTab)}
              className="w-full flex flex-col h-full"
            >
              <div className="px-5 border-b border-border/60 bg-card sticky top-0 z-10">
                <TabsList className="h-10 bg-transparent p-0 gap-4">
                  <TabsTrigger
                    value="models"
                    className="h-10 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none text-xs font-semibold gap-1.5 px-1"
                  >
                    <Cpu className="size-3.5" />
                    <span>Mô hình AI</span>
                    <Badge
                      variant="secondary"
                      className="h-4 px-1 text-[10px] ml-1"
                    >
                      {models.length}
                    </Badge>
                  </TabsTrigger>

                  <TabsTrigger
                    value="keys"
                    className="h-10 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none text-xs font-semibold gap-1.5 px-1"
                  >
                    <Key className="size-3.5" />
                    <span>Khóa API</span>
                    <Badge
                      variant="secondary"
                      className="h-4 px-1 text-[10px] ml-1"
                    >
                      {keys.length}
                    </Badge>
                  </TabsTrigger>

                  <TabsTrigger
                    value="settings"
                    className="h-10 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none text-xs font-semibold gap-1.5 px-1"
                  >
                    <span>Cấu hình kết nối</span>
                  </TabsTrigger>
                </TabsList>
              </div>

              {/* TAB 1: MODELS */}
              <TabsContent value="models" className="p-5 space-y-4 m-0 flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-foreground">
                    Danh mục mô hình đã đăng ký ({models.length})
                  </span>
                  <Button
                    type="button"
                    size="sm"
                    className="h-7 text-xs gap-1 shadow-2xs"
                    onClick={() => onOpenAddModel(connection)}
                  >
                    <Plus className="size-3.5" />
                    <span>Thêm mô hình</span>
                  </Button>
                </div>

                {modelsQuery.isLoading ? (
                  <div className="py-12 flex justify-center text-xs text-muted-foreground gap-2 items-center">
                    <Loader2 className="size-4 animate-spin" />
                    <span>Đang tải danh sách mô hình...</span>
                  </div>
                ) : models.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border/70 p-8 text-center text-xs text-muted-foreground space-y-3">
                    <Cpu className="size-8 mx-auto text-muted-foreground/50" />
                    <p>Chưa có mô hình nào được gán cho nhà cung cấp này.</p>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => onOpenAddModel(connection)}
                    >
                      Đăng ký mô hình đầu tiên
                    </Button>
                  </div>
                ) : (
                  <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="h-9 text-[11px] bg-muted/20">
                          <TableHead className="w-[170px]">
                            Tên mô hình
                          </TableHead>
                          <TableHead>Năng lực</TableHead>
                          <TableHead className="w-[210px]">Giới hạn</TableHead>
                          <TableHead className="w-[44px] text-right">
                            <span className="sr-only">Thao tác</span>
                          </TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {models.map((model) => (
                          <TableRow key={model.id} className="h-11 text-xs">
                            <TableCell className="font-mono font-medium text-foreground">
                              {model.model_name}
                            </TableCell>

                            <TableCell>
                              <div className="flex flex-wrap gap-1">
                                {model.capabilities.map((cap) => {
                                  const meta = CAPABILITY_LABELS[cap];
                                  return (
                                    <Badge
                                      key={cap}
                                      variant="outline"
                                      className={`text-[9px] h-3.5 px-1 font-normal ${meta?.badgeColor ?? ""}`}
                                    >
                                      {cap.toUpperCase()}
                                    </Badge>
                                  );
                                })}
                              </div>
                            </TableCell>

                            <TableCell>
                              <CapacitySummary model={model} />
                            </TableCell>

                            <TableCell className="text-right">
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    className="size-7 p-0 text-muted-foreground data-[state=open]:bg-accent"
                                    title="Thao tác"
                                  >
                                    {syncCapacityMutation.isPending &&
                                    syncCapacityMutation.variables ===
                                      model.model_name ? (
                                      <Loader2 className="size-3.5 animate-spin" />
                                    ) : (
                                      <MoreHorizontal className="size-3.5" />
                                    )}
                                    <span className="sr-only">Thao tác</span>
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent
                                  align="end"
                                  className="text-xs"
                                >
                                  <DropdownMenuItem
                                    onSelect={() => onOpenProbeModel(model)}
                                  >
                                    <FlaskConical className="size-3.5" />
                                    Kiểm tra suy luận
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    onSelect={() => setCapacityModel(model)}
                                  >
                                    <Pencil className="size-3.5" />
                                    Sửa giới hạn
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    onSelect={() => {
                                      void handleSyncCapacity(model);
                                    }}
                                    disabled={syncCapacityMutation.isPending}
                                  >
                                    <RefreshCw className="size-3.5" />
                                    Đồng bộ từ nhà cung cấp
                                  </DropdownMenuItem>
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem
                                    onSelect={() => setModelToDelete(model)}
                                    className="text-destructive focus:text-destructive"
                                  >
                                    <Trash2 className="size-3.5" />
                                    Xóa model
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </TabsContent>

              {/* TAB 2: API KEYS */}
              <TabsContent value="keys" className="p-5 space-y-5 m-0 flex-1">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-semibold text-foreground block">
                        Khóa API đã lưu trên máy chủ ({keys.length})
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        Hệ thống tự động dùng khóa đang hoạt động có mức ưu tiên
                        cao nhất.
                      </span>
                    </div>

                    {!showAddKeyForm && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs gap-1 shadow-2xs"
                        onClick={() => setShowAddKeyForm(true)}
                      >
                        <Plus className="size-3.5" />
                        <span>Thêm khóa mới</span>
                      </Button>
                    )}
                  </div>

                  {keysQuery.isLoading ? (
                    <div className="py-6 flex justify-center text-xs text-muted-foreground gap-2 items-center">
                      <Loader2 className="size-4 animate-spin" />
                      <span>Đang tải khóa...</span>
                    </div>
                  ) : keys.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-border/70 p-4 text-center text-xs text-muted-foreground">
                      Chưa có khóa API nào. Vui lòng thêm khóa bên dưới để gửi
                      yêu cầu suy luận.
                    </div>
                  ) : (
                    <div className="divide-y rounded-lg border bg-card overflow-hidden">
                      {keys.map((k) => (
                        <div
                          key={k.id}
                          className={`flex items-center justify-between p-3 text-xs gap-3 ${
                            k.status === "active" ? "bg-emerald-500/5" : ""
                          }`}
                        >
                          <div className="min-w-0 space-y-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-semibold text-foreground">
                                {k.name}
                              </span>
                              {k.status === "active" ? (
                                <Badge
                                  variant="outline"
                                  className="h-4.5 text-[10px] bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20 font-medium"
                                >
                                  Khóa chính (Đang dùng gửi request)
                                </Badge>
                              ) : (
                                <Badge
                                  variant="secondary"
                                  className="h-4 text-[10px]"
                                >
                                  {k.status}
                                </Badge>
                              )}
                              <span className="text-[10px] text-muted-foreground font-mono">
                                Ưu tiên: {k.priority}
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground">
                              <span>Mã che đã lưu:</span>
                              <span className="font-semibold text-foreground bg-muted/60 px-1.5 py-0.5 rounded border border-border/50">
                                {k.masked_hint || "sk-••••••••"}
                              </span>
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

                {/* Inline Add Key Form (Collapsible) */}
                {(showAddKeyForm || keys.length === 0) && (
                  <form
                    onSubmit={handleAddKey}
                    className="rounded-lg border bg-muted/20 p-4 space-y-3"
                  >
                    <div className="flex items-center justify-between pb-1 border-b border-border/50">
                      <div className="flex items-center gap-2 text-xs font-semibold">
                        <ShieldCheck className="size-4 text-primary" />
                        <span>Thêm khóa API mới</span>
                      </div>
                      {keys.length > 0 && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-[11px]"
                          onClick={() => setShowAddKeyForm(false)}
                        >
                          Hủy
                        </Button>
                      )}
                    </div>

                    <Field>
                      <FieldLabel htmlFor="sheet-key-name">
                        Tên gợi nhớ *
                      </FieldLabel>
                      <Input
                        id="sheet-key-name"
                        value={newKeyName}
                        onChange={(e) => setNewKeyName(e.target.value)}
                        placeholder="VD: Backup API Key, Personal Token..."
                        required
                        className="h-8 text-xs"
                      />
                    </Field>

                    <Field>
                      <FieldLabel htmlFor="sheet-key-secret">
                        Khóa bí mật (Secret) *
                      </FieldLabel>
                      <Input
                        id="sheet-key-secret"
                        type="password"
                        value={newKeySecret}
                        onChange={(e) => setNewKeySecret(e.target.value)}
                        placeholder="sk-... (tối thiểu 8 ký tự)"
                        autoComplete="off"
                        required
                        className="h-8 text-xs font-mono"
                      />
                      <FieldDescription>
                        Được mã hóa an toàn trên máy chủ; giao diện chỉ hiển thị
                        phần che.
                      </FieldDescription>
                    </Field>

                    <div className="flex items-center justify-between gap-4 pt-1">
                      <div className="w-32">
                        <FieldLabel
                          htmlFor="sheet-key-priority"
                          className="text-xs"
                        >
                          Độ ưu tiên (1-10)
                        </FieldLabel>
                        <Input
                          id="sheet-key-priority"
                          type="number"
                          min={1}
                          max={10}
                          value={newKeyPriority}
                          onChange={(e) =>
                            setNewKeyPriority(Number(e.target.value) || 5)
                          }
                          className="h-8 text-xs"
                        />
                      </div>

                      <Button
                        type="submit"
                        size="sm"
                        className="h-8 gap-1.5 self-end text-xs shadow-2xs"
                        disabled={
                          isAddingKey ||
                          !newKeyName.trim() ||
                          newKeySecret.trim().length < 8
                        }
                      >
                        {isAddingKey ? (
                          <Loader2 className="size-3.5 animate-spin" />
                        ) : (
                          <Plus className="size-3.5" />
                        )}
                        <span>Lưu khóa</span>
                      </Button>
                    </div>
                  </form>
                )}
              </TabsContent>

              {/* TAB 3: SETTINGS */}
              <TabsContent
                value="settings"
                className="p-5 space-y-5 m-0 flex-1"
              >
                <form onSubmit={handleSaveSettings} className="space-y-4">
                  <Field>
                    <FieldLabel htmlFor="sheet-name">Tên hiển thị *</FieldLabel>
                    <Input
                      id="sheet-name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      className="h-8 text-xs"
                    />
                  </Field>

                  <Field>
                    <FieldLabel htmlFor="sheet-family">
                      Chuẩn giao thức *
                    </FieldLabel>
                    <Select
                      value={family}
                      onValueChange={(val) =>
                        setFamily(val as ConnectionFamily)
                      }
                    >
                      <SelectTrigger id="sheet-family" className="h-8 text-xs">
                        <SelectValue placeholder="Chọn chuẩn giao thức" />
                      </SelectTrigger>
                      <SelectContent className="text-xs">
                        {Object.values(CONNECTION_FAMILIES).map((fam) => (
                          <SelectItem key={fam.id} value={fam.id}>
                            {fam.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </Field>

                  <Field>
                    <FieldLabel htmlFor="sheet-url">
                      Endpoint URL (Base URL) *
                    </FieldLabel>
                    <Input
                      id="sheet-url"
                      value={baseUrl}
                      onChange={(e) => setBaseUrl(e.target.value)}
                      required
                      className="h-8 text-xs font-mono"
                    />
                  </Field>

                  <Field>
                    <FieldLabel htmlFor="sheet-timeout">
                      Thời gian chờ tối đa (Timeout giây)
                    </FieldLabel>
                    <Input
                      id="sheet-timeout"
                      type="number"
                      min={5}
                      max={300}
                      value={timeoutSeconds}
                      onChange={(e) =>
                        setTimeoutSeconds(Number(e.target.value) || 30)
                      }
                      className="h-8 text-xs"
                    />
                  </Field>

                  <Button
                    type="submit"
                    size="sm"
                    className="h-8 gap-1.5 text-xs shadow-2xs"
                    disabled={isSavingSettings}
                  >
                    {isSavingSettings ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <Save className="size-3.5" />
                    )}
                    <span>Lưu thay đổi</span>
                  </Button>
                </form>

                {/* Danger Zone */}
                <div className="pt-6 border-t border-destructive/20 space-y-3">
                  <h4 className="text-xs font-semibold text-destructive">
                    Vùng nguy hiểm
                  </h4>
                  <div className="flex items-center justify-between p-3 rounded-lg border border-destructive/30 bg-destructive/5 text-xs">
                    <div>
                      <p className="font-medium text-foreground">
                        Xóa nhà cung cấp AI này
                      </p>
                      <p className="text-muted-foreground text-[11px]">
                        Hành động này sẽ xóa toàn bộ model và khóa API liên kết.
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="destructive"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => {
                        onOpenChange(false);
                        onRequestDeleteConnection(connection);
                      }}
                    >
                      Xóa kết nối
                    </Button>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </SheetContent>
      </Sheet>

      {/* Confirm Delete Model */}
      <ConfirmDialog
        open={Boolean(modelToDelete)}
        onOpenChange={(open) => !open && setModelToDelete(null)}
        title="Xóa mô hình AI"
        description={
          <>
            Bạn có chắc chắn muốn xóa mô hình{" "}
            <strong className="font-mono">{modelToDelete?.model_name}</strong>{" "}
            khỏi nhà cung cấp này?
          </>
        }
        confirmLabel="Xác nhận xóa"
        confirmVariant="destructive"
        isLoading={deleteModelMutation.isPending}
        onConfirm={handleConfirmDeleteModel}
      />

      {/* Confirm Delete Key */}
      <ConfirmDialog
        open={Boolean(keyToDelete)}
        onOpenChange={(open) => !open && setKeyToDelete(null)}
        title="Xóa khóa API"
        description={
          <>
            Bạn có chắc chắn muốn xóa khóa API{" "}
            <strong>{keyToDelete?.name}</strong> (
            <span className="font-mono">{keyToDelete?.masked_hint}</span>)?
          </>
        }
        confirmLabel="Xác nhận xóa"
        confirmVariant="destructive"
        isLoading={deleteKeyMutation.isPending}
        onConfirm={handleConfirmDeleteKey}
      />

      {/* Thông số ngữ cảnh/đầu ra của model */}
      <ModelCapacityDialog
        connectionId={connection.id}
        model={capacityModel}
        open={Boolean(capacityModel)}
        onOpenChange={(next) => {
          if (!next) setCapacityModel(null);
        }}
      />
    </>
  );
}
