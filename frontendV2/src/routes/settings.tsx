import { createFileRoute, useBlocker } from "@tanstack/react-router";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Cpu,
  FileText,
  Loader2,
  Moon,
  Palette,
  RotateCcw,
  RotateCw,
  Save,
  ShieldAlert,
  SpellCheck,
  Sun,
  User,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { useMeQuery } from "@/api/auth/queries";
import { ApiProblemError } from "@/api/client";
import {
  useConnectionsQuery,
  useModelDefaultsQuery,
  useProvidersQuery,
  useUpdateModelDefaultsMutation,
} from "@/api/modelops/queries";
import type {
  Capability,
  DefaultsUpdateRequest,
  ModelProvider,
} from "@/api/modelops/types";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { SystemResetPanel } from "@/components/admin/system-reset-panel";
import { SpellingDefaultsPanel } from "@/components/knowledge/spelling-defaults-panel";
import { DocumentProcessingPanel } from "@/components/modelops/document-processing-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  buildSystemDefaultsPayload,
  CAPABILITIES_LIST,
  formatModelLabel,
  NONE_VALUE,
} from "@/lib/default-models";
import { isModelAdmin } from "@/lib/permissions";
import { useUiStore } from "@/lib/ui-store";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/settings")({
  component: SettingsPage,
});

type SettingsTab =
  | "appearance"
  | "models"
  | "documents"
  | "spelling"
  | "system"
  | "account";

const NAV_ITEMS: {
  id: SettingsTab;
  title: string;
  icon: typeof Palette;
}[] = [
  {
    id: "appearance",
    title: "Giao diện",
    icon: Palette,
  },
  {
    id: "models",
    title: "Mô hình mặc định",
    icon: Cpu,
  },
  {
    id: "documents",
    title: "Xử lý văn bản",
    icon: FileText,
  },
  {
    id: "spelling",
    title: "Soát chính tả",
    icon: SpellCheck,
  },
  {
    id: "system",
    title: "Đặt lại hệ thống",
    icon: RotateCcw,
  },
  {
    id: "account",
    title: "Tài khoản",
    icon: User,
  },
];

function SettingsPage() {
  const { theme, setTheme } = useUiStore();

  // Tab state inside this single page
  const [activeTab, setActiveTab] = useState<SettingsTab>(() => {
    if (typeof window !== "undefined" && window.location.search) {
      if (window.location.search.includes("models")) return "models";
      if (window.location.search.includes("documents")) return "documents";
      if (window.location.search.includes("spelling")) return "spelling";
      if (window.location.search.includes("system")) return "system";
      if (window.location.search.includes("account")) return "account";
    }
    return "appearance";
  });

  const authQuery = useMeQuery();
  const authData = authQuery.data;
  const actor = authData?.actor;
  const isSignedIn = !authQuery.isError && actor?.authenticated === true;
  const canManageSystem = isSignedIn && isModelAdmin(actor);
  const shouldLoadModels =
    (activeTab === "models" || activeTab === "documents") && canManageSystem;
  const accountError =
    authQuery.error instanceof ApiProblemError && authQuery.error.isUnauthorized
      ? "Bạn chưa đăng nhập."
      : "Không thể tải thông tin tài khoản.";

  const {
    data: defaults,
    isLoading: loadingDefaults,
    isError: errorDefaults,
    refetch: refetchDefaults,
    isFetching: fetchingDefaults,
  } = useModelDefaultsQuery(activeTab === "models" && canManageSystem);

  const {
    data: providers = [],
    isLoading: loadingProviders,
    isError: errorProviders,
    refetch: refetchProviders,
    isFetching: fetchingProviders,
  } = useProvidersQuery(shouldLoadModels);

  const {
    data: connections = [],
    isLoading: loadingConnections,
    isError: errorConnections,
    refetch: refetchConnections,
    isFetching: fetchingConnections,
  } = useConnectionsQuery(shouldLoadModels);
  const hasModelLoadError = errorDefaults || errorProviders || errorConnections;

  const updateMutation = useUpdateModelDefaultsMutation();

  // Track user edits: capability -> providerId or null (null means clear to None)
  const [userEdits, setUserEdits] = useState<
    Partial<Record<Capability, string | null>>
  >({});

  // Map of connection status
  const connectionActiveMap = useMemo(() => {
    const map = new Map<string, boolean>();
    for (const conn of connections) {
      map.set(conn.id, Boolean(conn.is_active));
    }
    return map;
  }, [connections]);

  // Providers map by ID for lookup
  const providersMap = useMemo(() => {
    const map = new Map<string, ModelProvider>();
    for (const p of providers) {
      map.set(p.id, p);
    }
    return map;
  }, [providers]);

  // Filter selectable models per capability
  const availableModelsForCapability = useMemo(() => {
    const map = new Map<Capability, ModelProvider[]>();
    for (const item of CAPABILITIES_LIST) {
      const cap = item.key;
      const list = providers.filter((p) => {
        if (p.is_connection) return false;
        if (!p.is_active) return false;
        if (p.parent_id && !connectionActiveMap.get(p.parent_id)) return false;
        const caps = (p.capabilities as string[]) || [];
        return caps.includes(cap);
      });
      map.set(cap, list);
    }
    return map;
  }, [providers, connectionActiveMap]);

  // Server configured baseline values
  const serverValues: Record<Capability, string | null> = useMemo(() => {
    return {
      chat: defaults?.chat_provider_id ?? null,
      embedding: defaults?.embedding_provider_id ?? null,
      rerank: defaults?.rerank_provider_id ?? null,
      ocr: defaults?.ocr_provider_id ?? null,
    };
  }, [defaults]);

  // Effective values = server values overlaid with user edits
  const effectiveValues: Record<Capability, string | null> = useMemo(() => {
    const result: Record<Capability, string | null> = { ...serverValues };
    for (const cap of CAPABILITIES_LIST.map((c) => c.key)) {
      if (cap in userEdits) {
        result[cap] = userEdits[cap] ?? null;
      }
    }
    return result;
  }, [serverValues, userEdits]);

  // Has unsaved edits
  const isDirty = useMemo(() => {
    for (const cap of CAPABILITIES_LIST.map((c) => c.key)) {
      if (cap in userEdits) {
        const edited = userEdits[cap];
        const server = serverValues[cap];
        if (edited !== server) return true;
      }
    }
    return false;
  }, [userEdits, serverValues]);

  // Warn on navigation if dirty
  const blocker = useBlocker({
    shouldBlockFn: () => isDirty,
    enableBeforeUnload: () => isDirty,
    withResolver: true,
  });
  const isBlocked = blocker.status === "blocked";

  const handleModelChange = (capability: Capability, value: string) => {
    const resolvedValue = value === NONE_VALUE ? null : value;
    setUserEdits((prev) => {
      if (resolvedValue === serverValues[capability]) {
        const next = { ...prev };
        delete next[capability];
        return next;
      }
      return {
        ...prev,
        [capability]: resolvedValue,
      };
    });
  };

  const handleRefresh = async () => {
    const results = await Promise.all([
      refetchDefaults(),
      refetchProviders(),
      refetchConnections(),
    ]);
    if (results.every((result) => result.isSuccess)) {
      toast.success("Đã làm mới dữ liệu từ máy chủ.");
    }
  };

  const handleSave = async () => {
    if (!isDirty || !canManageSystem || hasModelLoadError) return;

    const payload = buildSystemDefaultsPayload(
      userEdits,
      serverValues,
    ) as DefaultsUpdateRequest;

    try {
      await updateMutation.mutateAsync(payload);
      setUserEdits({});
      toast.success("Đã lưu mô hình mặc định hệ thống thành công!");
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Có lỗi xảy ra khi lưu cấu hình mặc định";
      toast.error(msg);
    }
  };

  const isLoading =
    loadingDefaults ||
    (canManageSystem && (loadingProviders || loadingConnections));
  const isRefreshing =
    fetchingDefaults || fetchingProviders || fetchingConnections;

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="space-y-0.5">
        <h2 className="text-xl font-bold tracking-tight text-foreground">
          Cài đặt
        </h2>
        <p className="text-xs text-muted-foreground">
          Quản lý giao diện hiển thị, cấu hình mô hình AI mặc định và thông tin
          tài khoản.
        </p>
      </div>

      <Separator />

      {/* Main 2-column layout */}
      <div className="flex flex-col space-y-6 md:flex-row md:space-x-8 md:space-y-0">
        {/* Left Sub-nav */}
        <aside className="md:w-48 lg:w-56 shrink-0">
          <nav className="flex flex-wrap gap-1 md:flex-col">
            {NAV_ITEMS.filter(
              (item) =>
                (item.id !== "spelling" &&
                  item.id !== "documents" &&
                  item.id !== "system") ||
                canManageSystem,
            ).map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveTab(item.id)}
                  className={cn(
                    "flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors md:w-full text-left",
                    isActive
                      ? "bg-muted font-semibold text-foreground shadow-2xs"
                      : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
                  )}
                >
                  <Icon className="size-4 shrink-0 text-muted-foreground" />
                  <span>{item.title}</span>
                </button>
              );
            })}
          </nav>
        </aside>

        {/* Right Content Panel */}
        <div className="flex-1 min-w-0 max-w-3xl">
          {/* TAB 1: GIAO DIỆN (APPEARANCE) */}
          {activeTab === "appearance" && (
            <div className="space-y-6">
              <div className="space-y-0.5">
                <h3 className="text-base font-semibold text-foreground">
                  Giao diện
                </h3>
                <p className="text-xs text-muted-foreground">
                  Tùy chỉnh chủ đề sáng hoặc tối cho giao diện người dùng.
                </p>
              </div>

              <Separator />

              <div className="space-y-4">
                <div>
                  <span className="text-xs font-semibold text-foreground block mb-2.5">
                    Chủ đề hiển thị
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-md">
                    {/* Light Mode Card */}
                    <button
                      type="button"
                      onClick={() => setTheme("light")}
                      className={cn(
                        "group cursor-pointer rounded-xl border-2 p-1.5 transition-all text-left outline-none focus-visible:ring-2 focus-visible:ring-primary/40 select-none w-full",
                        theme === "light"
                          ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                          : "border-border/70 hover:border-primary/50 bg-card",
                      )}
                    >
                      <div className="space-y-2 rounded-lg bg-[#f4f5f7] p-2.5 border border-border/40">
                        <div className="space-y-1.5 rounded-md bg-white p-2 shadow-2xs border border-border/30">
                          <div className="h-2 w-16 rounded bg-[#e2e4e8]" />
                          <div className="h-2 w-24 rounded bg-[#e2e4e8]" />
                        </div>
                        <div className="flex items-center gap-2 rounded-md bg-white p-2 shadow-2xs border border-border/30">
                          <div className="size-3.5 rounded-full bg-primary/20" />
                          <div className="h-2 w-20 rounded bg-[#e2e4e8]" />
                        </div>
                      </div>
                      <div className="pt-2 pb-1 px-1 flex items-center justify-between text-xs font-medium text-foreground">
                        <span className="flex items-center gap-1.5">
                          <Sun className="size-3.5 text-amber-500" />
                          <span>Chế độ Sáng</span>
                        </span>
                        {theme === "light" && (
                          <Check className="size-3.5 text-primary" />
                        )}
                      </div>
                    </button>

                    {/* Dark Mode Card */}
                    <button
                      type="button"
                      onClick={() => setTheme("dark")}
                      className={cn(
                        "group cursor-pointer rounded-xl border-2 p-1.5 transition-all text-left outline-none focus-visible:ring-2 focus-visible:ring-primary/40 select-none w-full",
                        theme === "dark"
                          ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                          : "border-border/70 hover:border-primary/50 bg-card",
                      )}
                    >
                      <div className="space-y-2 rounded-lg bg-zinc-950 p-2.5 border border-zinc-800">
                        <div className="space-y-1.5 rounded-md bg-zinc-900 p-2 shadow-2xs border border-zinc-800">
                          <div className="h-2 w-16 rounded bg-zinc-700" />
                          <div className="h-2 w-24 rounded bg-zinc-700" />
                        </div>
                        <div className="flex items-center gap-2 rounded-md bg-zinc-900 p-2 shadow-2xs border border-zinc-800">
                          <div className="size-3.5 rounded-full bg-primary/40" />
                          <div className="h-2 w-20 rounded bg-zinc-700" />
                        </div>
                      </div>
                      <div className="pt-2 pb-1 px-1 flex items-center justify-between text-xs font-medium text-foreground">
                        <span className="flex items-center gap-1.5">
                          <Moon className="size-3.5 text-blue-400" />
                          <span>Chế độ Tối</span>
                        </span>
                        {theme === "dark" && (
                          <Check className="size-3.5 text-primary" />
                        )}
                      </div>
                    </button>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-2.5">
                    Chọn chủ đề hiển thị phù hợp với điều kiện làm việc của bạn.
                    Cài đặt được lưu tự động trên trình duyệt.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: MÔ HÌNH MẶC ĐỊNH (MODELS) */}
          {activeTab === "models" && (
            <div className="space-y-6">
              <div className="space-y-0.5">
                <h3 className="text-base font-semibold text-foreground">
                  Mô hình mặc định
                </h3>
                <p className="text-xs text-muted-foreground">
                  Thiết lập mô hình mặc định cho bốn chức năng cốt lõi. Cấu hình
                  này áp dụng cho tất cả đơn vị.
                </p>
              </div>

              <Separator />

              {authQuery.isPending ? (
                <Skeleton className="h-12 w-full" />
              ) : !canManageSystem ? (
                <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center gap-3 text-xs text-foreground">
                  <ShieldAlert className="size-4 text-amber-600 shrink-0" />
                  <span>
                    {authQuery.isError
                      ? accountError
                      : isSignedIn
                        ? "Bạn không có quyền xem cấu hình mô hình hệ thống."
                        : "Bạn cần đăng nhập để xem cấu hình mô hình."}
                  </span>
                </div>
              ) : (
                <>
                  <Card className="shadow-2xs">
                    <CardHeader className="pb-4 border-b border-border/60">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <Cpu className="size-4 text-primary" />
                          <CardTitle className="text-sm font-semibold">
                            Mô hình mặc định toàn hệ thống
                          </CardTitle>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleRefresh}
                          disabled={
                            isLoading ||
                            isRefreshing ||
                            updateMutation.isPending
                          }
                          className="h-8 text-xs gap-1.5"
                        >
                          <RotateCw
                            className={cn(
                              "size-3.5",
                              isRefreshing && "animate-spin",
                            )}
                          />
                          <span>
                            {hasModelLoadError ? "Thử lại" : "Làm mới"}
                          </span>
                        </Button>
                      </div>
                      <CardDescription className="text-xs mt-1">
                        Áp dụng cho tác vụ mới sử dụng mô hình mặc định.
                      </CardDescription>
                    </CardHeader>

                    <CardContent className="p-0 divide-y divide-border/60">
                      {hasModelLoadError ? (
                        <p
                          role="alert"
                          className="p-5 flex items-center gap-2 text-xs text-destructive"
                        >
                          <AlertTriangle className="size-4 shrink-0" />
                          Không thể tải cấu hình hoặc danh sách mô hình từ máy
                          chủ.
                        </p>
                      ) : isLoading ? (
                        <div className="p-6 space-y-4">
                          <Skeleton className="h-14 w-full" />
                          <Skeleton className="h-14 w-full" />
                          <Skeleton className="h-14 w-full" />
                          <Skeleton className="h-14 w-full" />
                        </div>
                      ) : (
                        CAPABILITIES_LIST.map((item) => {
                          const cap = item.key;
                          const currentValue = effectiveValues[cap];
                          const availableModels =
                            availableModelsForCapability.get(cap) || [];
                          const selectedProvider = currentValue
                            ? providersMap.get(currentValue)
                            : null;

                          const isAssignedUnavailable =
                            currentValue &&
                            !availableModels.some(
                              (model) => model.id === currentValue,
                            );

                          const isChanged =
                            cap in userEdits &&
                            userEdits[cap] !== serverValues[cap];

                          return (
                            <div
                              key={cap}
                              className={cn(
                                "p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-6 transition-colors",
                                isChanged && "bg-primary/5",
                              )}
                            >
                              <div className="space-y-1 min-w-0 flex-1">
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-semibold text-foreground">
                                    {item.name}
                                  </span>
                                  {currentValue ? (
                                    <Badge
                                      variant="secondary"
                                      className="text-[10px] h-4.5 px-1.5 font-normal bg-primary/10 text-primary border-primary/20"
                                    >
                                      Đã đặt
                                    </Badge>
                                  ) : (
                                    <Badge
                                      variant="outline"
                                      className="text-[10px] h-4.5 px-1.5 font-normal text-muted-foreground"
                                    >
                                      Chưa cấu hình
                                    </Badge>
                                  )}
                                  {isChanged && (
                                    <Badge
                                      variant="outline"
                                      className="text-[10px] h-4.5 px-1.5 font-normal text-amber-600 border-amber-300 bg-amber-50 dark:bg-amber-950/40"
                                    >
                                      Chưa lưu
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-[11px] text-muted-foreground leading-relaxed">
                                  {item.description}
                                </p>
                                {isAssignedUnavailable && (
                                  <div className="flex items-center gap-1.5 text-[11px] text-amber-600 mt-1">
                                    <AlertTriangle className="size-3.5 shrink-0" />
                                    <span>
                                      Mô hình đã gán trước đây hiện không khả
                                      dụng hoặc bị ngắt kết nối.
                                    </span>
                                  </div>
                                )}
                              </div>

                              <div className="w-full sm:w-80 shrink-0">
                                <Select
                                  value={currentValue ?? NONE_VALUE}
                                  onValueChange={(val) =>
                                    handleModelChange(cap, val)
                                  }
                                  disabled={
                                    !canManageSystem || updateMutation.isPending
                                  }
                                >
                                  <SelectTrigger className="h-9 text-xs w-full bg-background">
                                    <SelectValue placeholder="Chọn mô hình mặc định..." />
                                  </SelectTrigger>
                                  <SelectContent className="text-xs max-h-72">
                                    <SelectItem
                                      value={NONE_VALUE}
                                      className="text-muted-foreground italic"
                                    >
                                      Chưa đặt mặc định hệ thống
                                    </SelectItem>
                                    {isAssignedUnavailable && (
                                      <SelectItem
                                        value={currentValue}
                                        disabled
                                        className="text-destructive font-mono text-xs"
                                      >
                                        {selectedProvider
                                          ? `${formatModelLabel(selectedProvider)} (Không khả dụng)`
                                          : "Mô hình không khả dụng"}
                                      </SelectItem>
                                    )}
                                    {availableModels.map((m) => (
                                      <SelectItem key={m.id} value={m.id}>
                                        {formatModelLabel(m)}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </CardContent>
                  </Card>

                  {!isLoading && !hasModelLoadError && defaults && (
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-2">
                      <div className="flex items-center gap-2 text-xs">
                        {isDirty ? (
                          <span className="text-amber-600 font-medium flex items-center gap-1.5">
                            <AlertTriangle className="size-3.5" />
                            Có thay đổi chưa lưu
                          </span>
                        ) : (
                          <span className="text-muted-foreground flex items-center gap-1.5">
                            <CheckCircle2 className="size-3.5 text-primary" />
                            Đã đồng bộ với cấu hình hệ thống
                          </span>
                        )}
                      </div>

                      {canManageSystem && (
                        <Button
                          type="button"
                          size="sm"
                          onClick={handleSave}
                          disabled={
                            !isDirty || updateMutation.isPending || isLoading
                          }
                          className="h-8 text-xs gap-1.5"
                        >
                          {updateMutation.isPending ? (
                            <Loader2 className="size-3.5 animate-spin" />
                          ) : (
                            <Save className="size-3.5" />
                          )}
                          <span>
                            {updateMutation.isPending
                              ? "Đang lưu..."
                              : "Lưu thay đổi"}
                          </span>
                        </Button>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {activeTab === "documents" &&
            canManageSystem &&
            (errorProviders || errorConnections ? (
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <p role="alert">Không tải được danh sách mô hình.</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    void refetchProviders();
                    void refetchConnections();
                  }}
                >
                  Thử lại
                </Button>
              </div>
            ) : loadingProviders || loadingConnections ? (
              <Skeleton className="h-48 w-full" />
            ) : (
              <DocumentProcessingPanel
                models={availableModelsForCapability.get("chat") ?? []}
                connections={connections}
              />
            ))}
          {activeTab === "spelling" && canManageSystem && (
            <SpellingDefaultsPanel />
          )}
          {/* TÀI KHOẢN */}
          {activeTab === "account" && (
            <div className="space-y-6">
              <div className="space-y-0.5">
                <h3 className="text-base font-semibold text-foreground">
                  Tài khoản
                </h3>
                <p className="text-xs text-muted-foreground">
                  Thông tin phiên làm việc và quyền hạn tài khoản hiện tại.
                </p>
              </div>

              <Separator />

              {authQuery.isPending ? (
                <Skeleton className="h-32 w-full" />
              ) : authQuery.isError ? (
                <div
                  role="alert"
                  className="flex items-center justify-between gap-3 text-sm text-destructive"
                >
                  <span>{accountError}</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void authQuery.refetch()}
                    disabled={authQuery.isFetching}
                  >
                    Thử lại
                  </Button>
                </div>
              ) : !actor?.authenticated ? (
                <p className="text-sm text-muted-foreground">
                  Bạn chưa đăng nhập.
                </p>
              ) : (
                <div className="space-y-4">
                  <div className="p-5 rounded-xl border border-border/70 bg-card space-y-4 shadow-2xs">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                      <div>
                        <span className="text-muted-foreground block text-[11px] mb-1">
                          Tên hiển thị
                        </span>
                        <span className="font-semibold text-foreground text-sm">
                          {actor.display_name ||
                            actor.username ||
                            "Chưa có tên hiển thị"}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px] mb-1">
                          Tên đăng nhập
                        </span>
                        <span className="font-mono text-foreground">
                          {actor.username || "Chưa có thông tin"}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px] mb-1">
                          Loại người dùng
                        </span>
                        <span className="font-medium text-foreground capitalize">
                          {actor.user_type || "Chưa có thông tin"}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px] mb-1">
                          Trạng thái phiên
                        </span>
                        <Badge
                          variant="secondary"
                          className="bg-primary/10 text-primary border-primary/20 text-[10px] h-5 px-1.5"
                        >
                          Đã đăng nhập
                        </Badge>
                      </div>
                    </div>

                    <Separator />

                    <div>
                      <span className="text-muted-foreground block text-[11px] mb-2 font-medium">
                        Quyền hạn hệ thống
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {actor.permissions.length > 0 ? (
                          actor.permissions.map((perm) => (
                            <Badge
                              key={perm}
                              variant="outline"
                              className="font-mono text-[10px] h-5 px-1.5 bg-muted/40 text-foreground"
                            >
                              {perm}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-muted-foreground text-xs italic">
                            Quyền tài khoản cơ bản
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 6: ĐẶT LẠI HỆ THỐNG (SYSTEM RESET & SEED) */}
          {activeTab === "system" && canManageSystem && <SystemResetPanel />}
        </div>
      </div>

      {/* Confirm Discard Modal */}
      <ConfirmDialog
        open={isBlocked}
        onOpenChange={(open) => {
          if (!open && blocker.status === "blocked") {
            blocker.reset();
          }
        }}
        title="Bỏ các thay đổi chưa lưu?"
        description="Bạn đã chỉnh sửa mô hình mặc định nhưng chưa nhấn Lưu thay đổi. Nếu rời khỏi trang, các lựa chọn này sẽ bị mất."
        confirmLabel="Rời đi"
        confirmVariant="destructive"
        onConfirm={() => {
          setUserEdits({});
          if (blocker.status === "blocked") {
            blocker.proceed();
          }
        }}
      />
    </div>
  );
}
