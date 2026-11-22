import {
  AlertTriangle,
  Check,
  Code2,
  Copy,
  KeyRound,
  Loader2,
  MoreHorizontal,
  Plus,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  Terminal,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import type { AssistantResponse } from "@/api/assistants";
import {
  type AppApiKey,
  useApiKeysQuery,
  useAppClientsQuery,
  useCreateApiKeyMutation,
  useIntegrationConfigQuery,
  useRevokeApiKeyMutation,
  useRotateApiKeyMutation,
  useUpdateApiKeyStatusMutation,
} from "@/api/integrations";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
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

const dateFormatter = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

interface AssistantIntegrationsTabProps {
  workspaceId: string;
  assistant: AssistantResponse;
}

export function AssistantIntegrationsTab({
  workspaceId,
  assistant,
}: AssistantIntegrationsTabProps) {
  const { data: config } = useIntegrationConfigQuery();
  const {
    data: keys,
    isLoading: isKeysLoading,
    refetch: refetchKeys,
  } = useApiKeysQuery(workspaceId);
  const { data: apps } = useAppClientsQuery(workspaceId);

  const createKeyMutation = useCreateApiKeyMutation(workspaceId);
  const updateStatusMutation = useUpdateApiKeyStatusMutation(workspaceId);
  const rotateKeyMutation = useRotateApiKeyMutation(workspaceId);
  const revokeKeyMutation = useRevokeApiKeyMutation(workspaceId);

  // Filter keys for this assistant or all
  const [filterThisAssistantOnly, setFilterThisAssistantOnly] = useState(true);

  // Dialog States
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [selectedAppId, setSelectedAppId] = useState("");
  const [newAppName, setNewAppName] = useState("");
  const [scopeThisAssistantOnly, setScopeThisAssistantOnly] = useState(true);
  const [rateLimitRpm, setRateLimitRpm] = useState("60");
  const [rateLimitRpd, setRateLimitRpd] = useState("10000");
  const [expiresInDays, setExpiresInDays] = useState<string>("none");

  // Secret Key Revealed Modal
  const [revealedSecret, setRevealedSecret] = useState<string | null>(null);
  const [revealedKeyName, setRevealedKeyName] = useState<string>("");
  const [copiedSecret, setCopiedSecret] = useState(false);

  // Key Action Confirm Dialogs
  const [keyToRotate, setKeyToRotate] = useState<AppApiKey | null>(null);
  const [keyToRevoke, setKeyToRevoke] = useState<AppApiKey | null>(null);
  const [revokeReason, setRevokeReason] = useState("Thu hồi bởi quản trị viên");

  // Snippet Copy State
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);

  const openaiEndpoint = useMemo(() => {
    if (config?.openai_endpoint) return config.openai_endpoint;
    if (typeof window !== "undefined") {
      return `${window.location.origin}/api/v1/integrations/openai/v1`;
    }
    return "/api/v1/integrations/openai/v1";
  }, [config?.openai_endpoint]);

  const displayedKeys = useMemo(() => {
    if (!keys) return [];
    if (!filterThisAssistantOnly) return keys;
    return keys.filter(
      (k) =>
        k.allowed_assistant_ids.length === 0 ||
        k.allowed_assistant_ids.includes(assistant.id),
    );
  }, [keys, filterThisAssistantOnly, assistant.id]);

  const handleCopyText = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(`Đã sao chép ${label}`);
    } catch {
      toast.error("Trình duyệt không cho phép sao chép tự động");
    }
  };

  const handleOpenCreateDialog = () => {
    setNewKeyName(`Key ${assistant.name}`);
    setSelectedAppId(apps && apps.length > 0 ? apps[0].id : "");
    setNewAppName(`App ${assistant.name}`);
    setScopeThisAssistantOnly(true);
    setRateLimitRpm("60");
    setRateLimitRpd("10000");
    setExpiresInDays("none");
    setCreateDialogOpen(true);
  };

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) {
      toast.error("Vui lòng nhập tên khóa API");
      return;
    }

    try {
      const payload = {
        name: newKeyName.trim(),
        app_id: selectedAppId || undefined,
        app_name: selectedAppId ? undefined : newAppName.trim() || undefined,
        allowed_assistant_ids: scopeThisAssistantOnly ? [assistant.id] : [],
        allow_all_assistants: !scopeThisAssistantOnly,
        rate_limit_rpm: rateLimitRpm ? Number(rateLimitRpm) : undefined,
        rate_limit_rpd: rateLimitRpd ? Number(rateLimitRpd) : undefined,
        expires_in_days:
          expiresInDays !== "none" ? Number(expiresInDays) : undefined,
      };

      const result = await createKeyMutation.mutateAsync(payload);
      setCreateDialogOpen(false);
      setRevealedSecret(result.secret_key);
      setRevealedKeyName(result.name);
      toast.success("Đã tạo API key thành công");
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Không tạo được API key",
      );
    }
  };

  const handleToggleKeyStatus = async (key: AppApiKey) => {
    const nextStatus = key.status === "active" ? "suspended" : "active";
    try {
      await updateStatusMutation.mutateAsync({
        keyId: key.id,
        data: {
          status: nextStatus,
          reason:
            nextStatus === "suspended"
              ? "Tạm dừng qua giao diện"
              : "Kích hoạt lại qua giao diện",
        },
      });
      toast.success(
        nextStatus === "active"
          ? `Đã kích hoạt khóa "${key.name}"`
          : `Đã tạm dừng khóa "${key.name}"`,
      );
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Không cập nhật được trạng thái",
      );
    }
  };

  const handleConfirmRotate = async () => {
    if (!keyToRotate) return;
    try {
      const result = await rotateKeyMutation.mutateAsync({
        keyId: keyToRotate.id,
        data: {},
      });
      setKeyToRotate(null);
      setRevealedSecret(result.secret_key);
      setRevealedKeyName(result.name);
      toast.success(`Đã xoay vòng khóa "${keyToRotate.name}" thành công`);
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Không xoay được API key",
      );
    }
  };

  const handleConfirmRevoke = async () => {
    if (!keyToRevoke) return;
    try {
      await revokeKeyMutation.mutateAsync({
        keyId: keyToRevoke.id,
        data: { reason: revokeReason.trim() || "Thu hồi bởi quản trị viên" },
      });
      setKeyToRevoke(null);
      toast.success(`Đã thu hồi khóa "${keyToRevoke.name}"`);
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Không thu hồi được API key",
      );
    }
  };

  const curlSnippet = `curl -X POST "${openaiEndpoint}/chat/completions" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "${assistant.id}",
    "messages": [
      {"role": "user", "content": "Học phí và hồ sơ xét tuyển năm 2026?"}
    ]
  }'`;

  const pythonSnippet = `from openai import OpenAI

# Khởi tạo client kết nối tới Gateway QNU AI Platform
client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="${openaiEndpoint}",
)

response = client.chat.completions.create(
    model="${assistant.id}",
    messages=[
        {"role": "user", "content": "Học phí và hồ sơ xét tuyển năm 2026?"}
    ],
)

print(response.choices[0].message.content)`;

  const nodeSnippet = `import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "YOUR_API_KEY",
  baseURL: "${openaiEndpoint}",
});

const response = await client.chat.completions.create({
  model: "${assistant.id}",
  messages: [
    { role: "user", content: "Học phí và hồ sơ xét tuyển năm 2026?" },
  ],
});

console.log(response.choices[0].message.content);`;

  return (
    <div className="space-y-6">
      {/* Overview & Gateway Endpoint Card */}
      <Card className="border-border/60 shadow-2xs">
        <CardHeader className="border-b border-border/50 pb-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Code2 className="size-4" />
              </div>
              <div>
                <CardTitle className="text-sm font-semibold">
                  Tích hợp OpenAI & API Gateway
                </CardTitle>
                <CardDescription>
                  Nhúng trợ lý "{assistant.name}" vào hệ thống ngoài qua chuẩn
                  OpenAI Chat Completions.
                </CardDescription>
              </div>
            </div>
            <Button
              size="sm"
              className="h-8 gap-1.5 text-xs font-medium"
              onClick={handleOpenCreateDialog}
            >
              <Plus className="size-3.5" />
              <span>Tạo API Key mới</span>
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5 rounded-lg border border-border/50 bg-muted/20 p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-foreground">
                  Base URL (OpenAI Compatible)
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-1.5 text-[11px] gap-1 cursor-pointer"
                  onClick={() =>
                    void handleCopyText(openaiEndpoint, "OpenAI Endpoint")
                  }
                >
                  <Copy className="size-3" />
                  <span>Sao chép</span>
                </Button>
              </div>
              <p className="font-mono text-xs text-muted-foreground break-all select-all">
                {openaiEndpoint}
              </p>
            </div>

            <div className="space-y-1.5 rounded-lg border border-border/50 bg-muted/20 p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-foreground">
                  Định danh Model (Trợ lý này)
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-1.5 text-[11px] gap-1 cursor-pointer"
                  onClick={() =>
                    void handleCopyText(assistant.id, "Model ID trợ lý")
                  }
                >
                  <Copy className="size-3" />
                  <span>Sao chép</span>
                </Button>
              </div>
              <p className="font-mono text-xs text-primary font-medium break-all select-all">
                {assistant.id}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Keys Table Card */}
      <Card className="border-border/60 shadow-2xs">
        <CardHeader className="border-b border-border/50 pb-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <KeyRound className="size-4 text-primary" />
              <CardTitle className="text-sm font-semibold">
                Danh sách khóa API
              </CardTitle>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Switch
                  id="filter-this-assistant"
                  checked={filterThisAssistantOnly}
                  onCheckedChange={setFilterThisAssistantOnly}
                />
                <label
                  htmlFor="filter-this-assistant"
                  className="cursor-pointer text-xs text-muted-foreground select-none"
                >
                  Chỉ khóa áp dụng cho trợ lý này
                </label>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 size-7 p-0"
                onClick={() => void refetchKeys()}
                title="Tải lại danh sách khóa"
              >
                <RefreshCw className="size-3.5" />
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {isKeysLoading ? (
            <div className="space-y-2 p-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : displayedKeys.length === 0 ? (
            <div className="p-6">
              <EmptyState
                icon={KeyRound}
                title="Chưa có khóa API nào"
                description={
                  filterThisAssistantOnly
                    ? "Chưa có API key nào được cấp quyền cho trợ lý này. Bạn có thể tạo khóa mới để cấp quyền truy cập."
                    : "Chưa có API key nào trong đơn vị."
                }
                action={{
                  label: "Tạo API Key đầu tiên",
                  onClick: handleOpenCreateDialog,
                }}
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="text-xs">Tên khóa</TableHead>
                    <TableHead className="text-xs">Tiền tố bí mật</TableHead>
                    <TableHead className="text-xs">Ứng dụng</TableHead>
                    <TableHead className="text-xs">Phạm vi</TableHead>
                    <TableHead className="text-xs">Trạng thái</TableHead>
                    <TableHead className="text-xs">Hạn mức</TableHead>
                    <TableHead className="text-xs">Lần dùng cuối</TableHead>
                    <TableHead className="w-10 text-right text-xs" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {displayedKeys.map((key) => {
                    const isTargetAssistantOnly =
                      key.allowed_assistant_ids.length > 0;
                    return (
                      <TableRow key={key.id} className="text-xs">
                        <TableCell className="font-medium">
                          {key.name}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {key.key_prefix}...
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {key.app_name || "—"}
                        </TableCell>
                        <TableCell>
                          {isTargetAssistantOnly ? (
                            <Badge
                              variant="outline"
                              className="text-[10px] font-normal"
                            >
                              Chỉ định cụ thể
                            </Badge>
                          ) : (
                            <Badge
                              variant="secondary"
                              className="text-[10px] font-normal"
                            >
                              Tất cả trợ lý
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {key.status === "active" ? (
                            <Badge
                              variant="default"
                              className="bg-emerald-600/15 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400 border-transparent text-[10px]"
                            >
                              Hoạt động
                            </Badge>
                          ) : key.status === "suspended" ? (
                            <Badge variant="warning" className="text-[10px]">
                              Tạm dừng
                            </Badge>
                          ) : (
                            <Badge
                              variant="outline"
                              className="border-destructive/30 bg-destructive/10 text-destructive text-[10px]"
                            >
                              Đã thu hồi
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {key.rate_limit_rpm
                            ? `${key.rate_limit_rpm} RPM`
                            : "KGH"}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-[11px]">
                          {key.last_used_at
                            ? dateFormatter.format(new Date(key.last_used_at))
                            : "Chưa dùng"}
                        </TableCell>
                        <TableCell className="text-right">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="size-7 p-0"
                                aria-label="Thao tác cho API key"
                              >
                                <MoreHorizontal className="size-3.5" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent
                              align="end"
                              className="w-44 text-xs"
                            >
                              {key.status !== "revoked" ? (
                                <>
                                  <DropdownMenuItem
                                    onClick={() =>
                                      void handleToggleKeyStatus(key)
                                    }
                                  >
                                    <RotateCcw className="size-3.5" />
                                    <span>
                                      {key.status === "active"
                                        ? "Tạm dừng khóa"
                                        : "Kích hoạt khóa"}
                                    </span>
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    onClick={() => setKeyToRotate(key)}
                                  >
                                    <RefreshCw className="size-3.5" />
                                    <span>Xoay vòng khóa (Rotate)</span>
                                  </DropdownMenuItem>
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem
                                    className="text-destructive"
                                    onClick={() => {
                                      setRevokeReason(
                                        "Thu hồi bởi quản trị viên",
                                      );
                                      setKeyToRevoke(key);
                                    }}
                                  >
                                    <Trash2 className="size-3.5" />
                                    <span>Thu hồi khóa</span>
                                  </DropdownMenuItem>
                                </>
                              ) : (
                                <DropdownMenuItem disabled>
                                  <span>Khóa đã bị thu hồi</span>
                                </DropdownMenuItem>
                              )}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Integration Snippets */}
      <Card className="border-border/60 shadow-2xs">
        <CardHeader className="border-b border-border/50 pb-3">
          <div className="flex items-center gap-2">
            <Terminal className="size-4 text-primary" />
            <CardTitle className="text-sm font-semibold">
              Mẫu tích hợp nhanh
            </CardTitle>
          </div>
          <CardDescription>
            Tương thích trực tiếp với thư viện OpenAI SDK trên mọi ngôn ngữ lập
            trình.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4">
          <Tabs defaultValue="curl" className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <TabsList className="h-8">
                <TabsTrigger value="curl" className="text-xs">
                  cURL
                </TabsTrigger>
                <TabsTrigger value="python" className="text-xs">
                  Python (OpenAI)
                </TabsTrigger>
                <TabsTrigger value="node" className="text-xs">
                  Node.js (OpenAI)
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="curl" className="space-y-2">
              <div className="relative rounded-lg border border-border/50 bg-muted/40 p-3 font-mono text-xs">
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-2 h-7 px-2 text-[11px] gap-1 cursor-pointer"
                  onClick={() => {
                    void handleCopyText(curlSnippet, "lệnh cURL");
                    setCopiedSnippet("curl");
                    setTimeout(() => setCopiedSnippet(null), 2000);
                  }}
                >
                  {copiedSnippet === "curl" ? (
                    <Check className="size-3 text-emerald-600" />
                  ) : (
                    <Copy className="size-3" />
                  )}
                  <span>Sao chép</span>
                </Button>
                <pre className="overflow-x-auto whitespace-pre-wrap leading-relaxed pr-16 text-[11px]">
                  {curlSnippet}
                </pre>
              </div>
            </TabsContent>

            <TabsContent value="python" className="space-y-2">
              <div className="relative rounded-lg border border-border/50 bg-muted/40 p-3 font-mono text-xs">
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-2 h-7 px-2 text-[11px] gap-1 cursor-pointer"
                  onClick={() => {
                    void handleCopyText(pythonSnippet, "mã nguồn Python");
                    setCopiedSnippet("python");
                    setTimeout(() => setCopiedSnippet(null), 2000);
                  }}
                >
                  {copiedSnippet === "python" ? (
                    <Check className="size-3 text-emerald-600" />
                  ) : (
                    <Copy className="size-3" />
                  )}
                  <span>Sao chép</span>
                </Button>
                <pre className="overflow-x-auto whitespace-pre-wrap leading-relaxed pr-16 text-[11px]">
                  {pythonSnippet}
                </pre>
              </div>
            </TabsContent>

            <TabsContent value="node" className="space-y-2">
              <div className="relative rounded-lg border border-border/50 bg-muted/40 p-3 font-mono text-xs">
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-2 h-7 px-2 text-[11px] gap-1 cursor-pointer"
                  onClick={() => {
                    void handleCopyText(nodeSnippet, "mã nguồn Node.js");
                    setCopiedSnippet("node");
                    setTimeout(() => setCopiedSnippet(null), 2000);
                  }}
                >
                  {copiedSnippet === "node" ? (
                    <Check className="size-3 text-emerald-600" />
                  ) : (
                    <Copy className="size-3" />
                  )}
                  <span>Sao chép</span>
                </Button>
                <pre className="overflow-x-auto whitespace-pre-wrap leading-relaxed pr-16 text-[11px]">
                  {nodeSnippet}
                </pre>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Dialog: Create Key */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Tạo API Key mới</DialogTitle>
            <DialogDescription>
              Cấp khóa truy cập API cho ứng dụng ngoài tương tác với trợ lý.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <Field>
              <FieldLabel required className="text-xs font-medium">
                Tên khóa API
              </FieldLabel>
              <Input
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="VD: Khóa Cổng thông tin Tuyển sinh"
                className="h-9 text-xs"
              />
              <FieldDescription>
                Tên gợi nhớ để phân biệt mục đích sử dụng.
              </FieldDescription>
            </Field>

            <Field>
              <FieldLabel className="text-xs font-medium">
                Ứng dụng liên kết
              </FieldLabel>
              {apps && apps.length > 0 ? (
                <div className="space-y-2">
                  <select
                    value={selectedAppId}
                    onChange={(e) => setSelectedAppId(e.target.value)}
                    className="h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    <option value="">-- Tạo ứng dụng mới --</option>
                    {apps.map((app) => (
                      <option key={app.id} value={app.id}>
                        {app.name} ({app.id.slice(0, 8)})
                      </option>
                    ))}
                  </select>
                  {!selectedAppId ? (
                    <Input
                      value={newAppName}
                      onChange={(e) => setNewAppName(e.target.value)}
                      placeholder="Tên ứng dụng mới"
                      className="h-9 text-xs"
                    />
                  ) : null}
                </div>
              ) : (
                <Input
                  value={newAppName}
                  onChange={(e) => setNewAppName(e.target.value)}
                  placeholder="Tên ứng dụng tích hợp"
                  className="h-9 text-xs"
                />
              )}
              <FieldDescription>
                Tập hợp các khóa thuộc cùng một ứng dụng client.
              </FieldDescription>
            </Field>

            <div className="space-y-2 rounded-lg border border-border/50 bg-muted/20 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="space-y-0.5">
                  <span className="text-xs font-medium text-foreground">
                    Chỉ cho phép trợ lý này
                  </span>
                  <p className="text-[11px] text-muted-foreground">
                    Giới hạn khóa chỉ được hỏi trợ lý "{assistant.name}".
                  </p>
                </div>
                <Switch
                  checked={scopeThisAssistantOnly}
                  onCheckedChange={setScopeThisAssistantOnly}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel className="text-xs font-medium">
                  Giới hạn RPM (phút)
                </FieldLabel>
                <Input
                  type="number"
                  min={1}
                  max={10000}
                  value={rateLimitRpm}
                  onChange={(e) => setRateLimitRpm(e.target.value)}
                  className="h-9 text-xs"
                />
              </Field>

              <Field>
                <FieldLabel className="text-xs font-medium">
                  Hạn sử dụng
                </FieldLabel>
                <select
                  value={expiresInDays}
                  onChange={(e) => setExpiresInDays(e.target.value)}
                  className="h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  <option value="none">Không thời hạn</option>
                  <option value="30">30 ngày</option>
                  <option value="90">90 ngày</option>
                  <option value="180">180 ngày</option>
                  <option value="365">1 năm</option>
                </select>
              </Field>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              disabled={createKeyMutation.isPending}
              onClick={() => setCreateDialogOpen(false)}
            >
              Hủy
            </Button>
            <Button
              disabled={createKeyMutation.isPending || !newKeyName.trim()}
              onClick={() => void handleCreateKey()}
            >
              {createKeyMutation.isPending ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang tạo...</span>
                </>
              ) : (
                "Tạo khóa"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Secret Key Revealed (Shown only once) */}
      <Dialog
        open={Boolean(revealedSecret)}
        onOpenChange={(open) => {
          if (!open) {
            setRevealedSecret(null);
            setCopiedSecret(false);
          }
        }}
      >
        <DialogContent className="max-w-lg" role="alertdialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-primary">
              <KeyRound className="size-5" />
              <span>Khóa bí mật API mới</span>
            </DialogTitle>
            <DialogDescription>
              Khóa API "{revealedKeyName}" đã được tạo thành công.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <Alert variant="destructive">
              <ShieldAlert className="size-4" />
              <AlertTitle>Chỉ hiển thị một lần duy nhất!</AlertTitle>
              <AlertDescription>
                Vì lý do an toàn bảo mật, hệ thống không lưu secret key dưới
                dạng văn bản. Hãy sao chép và lưu trữ ở nơi an toàn ngay bây
                giờ.
              </AlertDescription>
            </Alert>

            <div className="relative rounded-lg border border-border bg-muted/40 p-3 font-mono text-xs">
              <p className="break-all select-all font-medium text-foreground pr-10">
                {revealedSecret}
              </p>
              <Button
                size="sm"
                variant="outline"
                className="absolute right-2 top-2 h-7 px-2 text-[11px] gap-1 cursor-pointer"
                onClick={() => {
                  if (revealedSecret) {
                    void handleCopyText(revealedSecret, "Secret Key");
                    setCopiedSecret(true);
                  }
                }}
              >
                {copiedSecret ? (
                  <Check className="size-3 text-emerald-600" />
                ) : (
                  <Copy className="size-3" />
                )}
                <span>{copiedSecret ? "Đã chép" : "Sao chép"}</span>
              </Button>
            </div>
          </div>

          <DialogFooter>
            <Button
              className="w-full sm:w-auto"
              onClick={() => {
                setRevealedSecret(null);
                setCopiedSecret(false);
              }}
            >
              Tôi đã lưu secret key
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Confirm Rotate */}
      <ConfirmDialog
        open={Boolean(keyToRotate)}
        onOpenChange={(open) => !open && setKeyToRotate(null)}
        title={`Xoay vòng khóa "${keyToRotate?.name}"?`}
        description={
          <div className="space-y-2">
            <p>
              Khi xoay vòng, khóa cũ sẽ bị vô hiệu hóa ngay lập tức và một
              secret key mới sẽ được cấp.
            </p>
            <p className="font-semibold text-warning">
              Các hệ thống đang dùng khóa cũ sẽ bị từ chối kết nối cho đến khi
              được cập nhật khóa mới.
            </p>
          </div>
        }
        confirmLabel="Xoay vòng và cấp khóa mới"
        confirmVariant="default"
        isLoading={rotateKeyMutation.isPending}
        onConfirm={() => void handleConfirmRotate()}
      />

      {/* Dialog: Confirm Revoke */}
      <Dialog
        open={Boolean(keyToRevoke)}
        onOpenChange={(open) => !open && setKeyToRevoke(null)}
      >
        <DialogContent className="max-w-md" role="alertdialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="size-4" />
              <span>Thu hồi API key "{keyToRevoke?.name}"?</span>
            </DialogTitle>
            <DialogDescription>
              Khóa sẽ bị vô hiệu hóa vĩnh viễn và không thể kích hoạt lại. Mọi
              yêu cầu sử dụng khóa này sẽ bị từ chối ngay lập tức.
            </DialogDescription>
          </DialogHeader>

          <div className="py-2">
            <Field>
              <FieldLabel className="text-xs font-medium">
                Lý do thu hồi
              </FieldLabel>
              <Input
                value={revokeReason}
                onChange={(e) => setRevokeReason(e.target.value)}
                placeholder="VD: Khóa bị lộ, thay thế ứng dụng..."
                className="h-9 text-xs"
              />
            </Field>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              disabled={revokeKeyMutation.isPending}
              onClick={() => setKeyToRevoke(null)}
            >
              Hủy
            </Button>
            <Button
              variant="destructive"
              disabled={revokeKeyMutation.isPending}
              onClick={() => void handleConfirmRevoke()}
            >
              {revokeKeyMutation.isPending ? "Đang xử lý..." : "Thu hồi khóa"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
