import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import {
  BookOpen,
  Bot,
  CheckCircle2,
  Code,
  Copy,
  Download,
  FileUp,
  History,
  LayoutGrid,
  List,
  Loader2,
  MessageSquare,
  MoreHorizontal,
  Network,
  Plus,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "@/components/admin/empty-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { AssistantCard } from "@/components/assistants/assistant-card";
import { AssistantCloneDialog } from "@/components/assistants/dialogs/assistant-clone-dialog";
import { AssistantEmbedDialog } from "@/components/assistants/dialogs/assistant-embed-dialog";
import { AssistantVersionHistoryDialog } from "@/components/assistants/dialogs/assistant-version-history-dialog";
import { CreateAssistantDialog } from "@/components/assistants/dialogs/create-assistant-dialog";
import { CATEGORY_OPTIONS } from "@/components/assistants/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  type AssistantBundle,
  activateAssistant,
  cloneAssistant,
  deactivateAssistant,
  exportAssistantBundle,
  getAssistantVersions,
  importAssistantBundle,
  listAssistants,
  rollbackAssistantVersion,
  seedDefaultAssistants,
} from "@/services/assistants-api";
import { knowledgeApi } from "@/services/knowledge-api";
import { workflowsApi } from "@/services/workflows-api";
import type { AssistantItem } from "@/types/assistants";

function isAssistantBundle(value: unknown): value is AssistantBundle {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return (
    record.format_version === "qnu.assistant.bundle/v1" && "assistant" in record
  );
}

function downloadBundle(filename: string, bundle: object) {
  const content = JSON.stringify(bundle, null, 2);
  const blob = new Blob([content], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function AssistantsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Search & Filter State
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");

  // Dialog States
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [cloneTarget, setCloneTarget] = useState<AssistantItem | null>(null);
  const [embedTarget, setEmbedTarget] = useState<AssistantItem | null>(null);
  const [historyTarget, setHistoryTarget] = useState<AssistantItem | null>(
    null,
  );

  // 1. Fetch Assistants
  const assistantsQuery = useQuery({
    queryKey: ["assistants", search, category],
    queryFn: () => listAssistants({ search, category, includeInactive: true }),
  });

  // 2. Fetch Supporting Collections & Workflows
  const collectionsQuery = useQuery({
    queryKey: ["knowledge-collections"],
    queryFn: () => knowledgeApi.getCollections(),
  });

  const workflowsQuery = useQuery({
    queryKey: ["workflow-definitions"],
    queryFn: () => workflowsApi.listDefinitions(),
  });

  // 3. Fetch Versions for History Dialog
  const versionsQuery = useQuery({
    queryKey: ["assistant-versions", historyTarget?.code || historyTarget?.id],
    queryFn: () =>
      historyTarget
        ? getAssistantVersions(historyTarget.code || historyTarget.id)
        : Promise.resolve([]),
    enabled: Boolean(historyTarget),
  });

  // Mutations
  const seedMutation = useMutation({
    mutationFn: seedDefaultAssistants,
    onSuccess: (result) => {
      toast.success(
        `Đã đồng bộ ${result.assistants_added} trợ lý và ${result.workflows_added} workflow (Tổng cộng: ${result.total_assistants} trợ lý).`,
      );
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const importMutation = useMutation({
    mutationFn: importAssistantBundle,
    onSuccess: (assistant) => {
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      toast.success(`Đã nhập thành công bundle trợ lý “${assistant.name}”!`);
      navigate({
        to: "/assistants/$assistantId",
        params: { assistantId: assistant.code || assistant.id },
      });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const cloneMutation = useMutation({
    mutationFn: (data: {
      targetId: string;
      req: {
        new_code: string;
        new_name: string;
        new_description?: string;
        target_collection_id?: string;
        fork_workflow?: boolean;
      };
    }) => cloneAssistant(data.targetId, data.req),
    onSuccess: (newAssistant) => {
      toast.success(`Đã nhân bản thành công Trợ lý “${newAssistant.name}”!`);
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      setCloneTarget(null);
      navigate({
        to: "/assistants/$assistantId",
        params: { assistantId: newAssistant.code || newAssistant.id },
      });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const rollbackMutation = useMutation({
    mutationFn: (data: { assistantId: string; versionId: string }) =>
      rollbackAssistantVersion(data.assistantId, data.versionId),
    onSuccess: (res) => {
      toast.success(
        res.message || `Đã khôi phục về phiên bản ${res.restored_version}!`,
      );
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
      if (historyTarget) {
        queryClient.invalidateQueries({
          queryKey: [
            "assistant-versions",
            historyTarget.code || historyTarget.id,
          ],
        });
      }
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: async ({
      assistant,
      active,
    }: {
      assistant: AssistantItem;
      active: boolean;
    }) => {
      const ref = assistant.code || assistant.id;
      return active ? activateAssistant(ref) : deactivateAssistant(ref);
    },
    onSuccess: (updated) => {
      toast.success(
        updated.is_active
          ? `Đã kích hoạt Trợ lý “${updated.name}”.`
          : `Đã tạm dừng Trợ lý “${updated.name}”.`,
      );
      queryClient.invalidateQueries({ queryKey: ["assistants"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const exportMutation = useMutation({
    mutationFn: (ref: string) => exportAssistantBundle(ref),
    onSuccess: (bundle) => {
      downloadBundle(`${bundle.assistant.code}.qnu.bundle.json`, bundle);
      toast.success("Đã xuất gói cấu hình bundle JSON thành công.");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  // Calculate items and metrics
  const rawItems = assistantsQuery.data ?? [];
  const items = useMemo(() => {
    return rawItems.filter((item) => {
      if (statusFilter === "active") return item.is_active;
      if (statusFilter === "inactive") return !item.is_active;
      return true;
    });
  }, [rawItems, statusFilter]);

  const activeCount = rawItems.filter((item) => item.is_active).length;
  const guardedCount = rawItems.filter(
    (item) => item.config?.guardrails?.require_grounded_answer,
  ).length;

  const uniqueCollectionsCount = useMemo(() => {
    const set = new Set(rawItems.map((i) => i.collection_id).filter(Boolean));
    return set.size;
  }, [rawItems]);

  const uniqueWorkflowsCount = useMemo(() => {
    const set = new Set(rawItems.map((i) => i.workflow_id).filter(Boolean));
    return set.size;
  }, [rawItems]);

  const handleImportFile = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      const parsed: unknown = JSON.parse(await file.text());
      if (!isAssistantBundle(parsed)) {
        throw new Error("Tệp không phải bundle trợ lý QNU hợp lệ.");
      }
      importMutation.mutate(parsed);
    } catch (importError) {
      toast.error(
        importError instanceof Error
          ? importError.message
          : "Nhập bundle trợ lý thất bại.",
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Header & Actions */}
      <PageHeader
        title="Trợ Lý AI"
        description="Quản trị các Trợ lý AI chuyên trách theo vòng đời 7 lớp, kết nối Kho tri thức chính thức và quy trình điều phối DAG."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={fileInputRef}
              accept="application/json,.bundle"
              className="hidden"
              type="file"
              onChange={handleImportFile}
            />
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs gap-1.5"
              onClick={() => seedMutation.mutate()}
              disabled={seedMutation.isPending}
              title="Khôi phục các trợ lý hạt nhân chuẩn của ĐH Quy Nhơn"
            >
              <RefreshCw
                className={`size-3.5 ${seedMutation.isPending ? "animate-spin text-primary" : ""}`}
              />
              <span>Đồng bộ mẫu</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs gap-1.5"
              onClick={() => fileInputRef.current?.click()}
              disabled={importMutation.isPending}
              title="Nhập gói trợ lý (.json)"
            >
              <FileUp className="size-3.5" />
              <span>Nhập bundle</span>
            </Button>
            <Button
              size="sm"
              onClick={() => setIsCreateOpen(true)}
              className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 shadow-xs"
            >
              <Plus className="size-3.5" />
              <span>Thêm trợ lý</span>
            </Button>
          </div>
        }
      />

      {/* 2. KPI Metrics Strip */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={Bot}
            label="Trợ lý AI"
            value={rawItems.length.toLocaleString("vi-VN")}
            helper={`${activeCount} đang hoạt động`}
          />
          <KpiMetric
            icon={ShieldCheck}
            label="Đạt chuẩn TM-08"
            value={guardedCount.toLocaleString("vi-VN")}
            helper="Groundedness ≥ 0.90"
          />
          <KpiMetric
            icon={BookOpen}
            label="Kho tri thức"
            value={`${uniqueCollectionsCount} kho`}
            helper="Tri thức liên kết chính thức"
          />
          <KpiMetric
            icon={Network}
            label="Quy trình DAG"
            value={`${uniqueWorkflowsCount} luồng`}
            helper="Workflow điều phối thông minh"
          />
        </CardContent>
      </Card>

      {/* 3. Filter Bar & View Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm theo tên hoặc mã trợ lý..."
              className="h-8 pl-8 text-xs"
            />
          </div>

          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger className="h-8 w-[165px] text-xs">
              <SelectValue placeholder="Lĩnh vực" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả lĩnh vực</SelectItem>
              {CATEGORY_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="h-8 w-[140px] text-xs">
              <SelectValue placeholder="Trạng thái" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tất cả trạng thái</SelectItem>
              <SelectItem value="active">Đang hoạt động</SelectItem>
              <SelectItem value="inactive">Đã tạm dừng</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-1 border rounded-md p-0.5 bg-muted/30 shrink-0 self-end sm:self-auto">
          <Button
            variant={viewMode === "grid" ? "secondary" : "ghost"}
            size="sm"
            className="h-7 w-7 p-0"
            onClick={() => setViewMode("grid")}
            title="Xem dạng thẻ lưới"
          >
            <LayoutGrid className="size-3.5" />
          </Button>
          <Button
            variant={viewMode === "table" ? "secondary" : "ghost"}
            size="sm"
            className="h-7 w-7 p-0"
            onClick={() => setViewMode("table")}
            title="Xem dạng danh sách bảng"
          >
            <List className="size-3.5" />
          </Button>
        </div>
      </div>

      {/* 4. Assistants Main Content */}
      {assistantsQuery.isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
          <Loader2 className="size-6 animate-spin text-primary" />
          <span className="text-xs">
            Đang tải danh sách Trợ lý AI từ CSDL...
          </span>
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={Bot}
          title={
            search || category !== "all" || statusFilter !== "all"
              ? "Không tìm thấy Trợ lý AI phù hợp"
              : "Chưa có Trợ lý AI nào trong hệ thống"
          }
          description={
            search || category !== "all" || statusFilter !== "all"
              ? "Thử thay đổi từ khóa tìm kiếm hoặc đặt lại các bộ lọc lĩnh vực / trạng thái."
              : "Khởi tạo trợ lý mới hoặc đồng bộ các mẫu trợ lý chuẩn của ĐH Quy Nhơn."
          }
          action={{
            label: "Thêm trợ lý",
            onClick: () => setIsCreateOpen(true),
          }}
          secondaryAction={{
            label: "Đồng bộ mẫu",
            onClick: () => seedMutation.mutate(),
          }}
        />
      ) : viewMode === "grid" ? (
        /* Cards Grid View: 1 col on mobile, 2 on tablet, 4 on desktop */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {items.map((ast) => (
            <AssistantCard
              key={ast.id || ast.code}
              assistant={ast}
              onOpen={() =>
                navigate({
                  to: "/assistants/$assistantId",
                  params: { assistantId: ast.code || ast.id },
                  search: { tab: "overview" },
                })
              }
              onChat={() =>
                navigate({
                  to: "/assistants/$assistantId",
                  params: { assistantId: ast.code || ast.id },
                  search: { tab: "playground" },
                })
              }
              onOpenWorkflow={() =>
                navigate({
                  to: "/assistants/$assistantId",
                  params: { assistantId: ast.code || ast.id },
                  search: { tab: "workflow" },
                })
              }
              onClone={() => setCloneTarget(ast)}
              onExport={() => exportMutation.mutate(ast.code || ast.id)}
              onHistory={() => setHistoryTarget(ast)}
              onEmbed={() => setEmbedTarget(ast)}
              onToggleActive={(active) =>
                toggleActiveMutation.mutate({ assistant: ast, active })
              }
              isToggling={toggleActiveMutation.isPending}
            />
          ))}
        </div>
      ) : (
        /* Table View */
        <Card className="overflow-hidden border border-border/80">
          <div className="w-full overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="h-10 hover:bg-transparent">
                  <TableHead className="w-[280px] text-xs">Trợ lý AI</TableHead>
                  <TableHead className="text-xs">Lĩnh vực</TableHead>
                  <TableHead className="text-xs">Mô hình AI</TableHead>
                  <TableHead className="text-xs">Kho Tri Thức</TableHead>
                  <TableHead className="text-xs">Chuẩn TM-08</TableHead>
                  <TableHead className="text-xs text-center w-[100px]">
                    Hoạt động
                  </TableHead>
                  <TableHead className="text-xs text-right w-[140px]">
                    Thao tác
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((ast) => (
                  <TableRow
                    key={ast.id || ast.code}
                    className="h-12 hover:bg-muted/40 transition-colors"
                  >
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2.5">
                        <div className="size-8 rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0 font-bold text-xs">
                          <Bot className="size-4" />
                        </div>
                        <div className="min-w-0">
                          <button
                            type="button"
                            onClick={() =>
                              navigate({
                                to: "/assistants/$assistantId",
                                params: { assistantId: ast.code || ast.id },
                                search: { tab: "overview" },
                              })
                            }
                            className="font-semibold text-foreground hover:text-primary transition-colors text-xs text-left truncate block max-w-[220px]"
                          >
                            {ast.name}
                          </button>
                          <span className="font-mono text-[10px] text-muted-foreground block truncate">
                            {ast.code}
                          </span>
                        </div>
                      </div>
                    </TableCell>

                    <TableCell>
                      <Badge
                        variant="outline"
                        className="text-[10px] capitalize"
                      >
                        {ast.category}
                      </Badge>
                    </TableCell>

                    <TableCell className="font-mono text-xs text-foreground">
                      {ast.config?.model_policy?.primary_model || "Mặc định"}
                    </TableCell>

                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {ast.collection_id || "—"}
                    </TableCell>

                    <TableCell>
                      {ast.config?.guardrails?.require_grounded_answer ? (
                        <span className="inline-flex items-center gap-1 text-[11px] text-success font-medium">
                          <CheckCircle2 className="size-3" />
                          Grounded
                        </span>
                      ) : (
                        <span className="text-[11px] text-muted-foreground">
                          Cơ bản
                        </span>
                      )}
                    </TableCell>

                    <TableCell className="text-center">
                      <Switch
                        checked={ast.is_active}
                        disabled={toggleActiveMutation.isPending}
                        onCheckedChange={(checked) =>
                          toggleActiveMutation.mutate({
                            assistant: ast,
                            active: checked,
                          })
                        }
                      />
                    </TableCell>

                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 px-2 text-xs"
                          onClick={() =>
                            navigate({
                              to: "/assistants/$assistantId",
                              params: { assistantId: ast.code || ast.id },
                              search: { tab: "overview" },
                            })
                          }
                          title="Quản trị"
                        >
                          <Settings className="size-3.5 text-primary" />
                          <span className="sr-only">Quản trị</span>
                        </Button>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0"
                            >
                              <MoreHorizontal className="size-3.5" />
                              <span className="sr-only">Thao tác</span>
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-44">
                            <DropdownMenuItem
                              onClick={() =>
                                navigate({
                                  to: "/assistants/$assistantId",
                                  params: { assistantId: ast.code || ast.id },
                                  search: { tab: "playground" },
                                })
                              }
                            >
                              <MessageSquare className="size-3.5 mr-2 text-primary" />
                              <span>Thử nghiệm</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => setCloneTarget(ast)}
                            >
                              <Copy className="size-3.5 mr-2 text-primary" />
                              <span>Nhân bản</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => setHistoryTarget(ast)}
                            >
                              <History className="size-3.5 mr-2 text-primary" />
                              <span>Lịch sử</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => setEmbedTarget(ast)}
                            >
                              <Code className="size-3.5 mr-2 text-primary" />
                              <span>Mã nhúng</span>
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() =>
                                exportMutation.mutate(ast.code || ast.id)
                              }
                            >
                              <Download className="size-3.5 mr-2" />
                              <span>Xuất bundle</span>
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      )}

      {/* 5. Modals & Dialogs */}
      <CreateAssistantDialog
        open={isCreateOpen}
        onOpenChange={setIsCreateOpen}
        onSuccess={(newAst) => {
          queryClient.invalidateQueries({ queryKey: ["assistants"] });
          navigate({
            to: "/assistants/$assistantId",
            params: { assistantId: newAst.code || newAst.id },
          });
        }}
        collections={collectionsQuery.data || []}
        workflows={workflowsQuery.data || []}
      />

      {cloneTarget && (
        <AssistantCloneDialog
          open={Boolean(cloneTarget)}
          onOpenChange={(open) => !open && setCloneTarget(null)}
          originalName={cloneTarget.name}
          initialCode={`${cloneTarget.code}_copy`}
          initialName={`${cloneTarget.name} (Bản sao)`}
          initialDescription={cloneTarget.description}
          initialCollectionId={cloneTarget.collection_id}
          onConfirm={(data) => {
            cloneMutation.mutate({
              targetId: cloneTarget.code || cloneTarget.id,
              req: {
                new_code: data.code,
                new_name: data.name,
                new_description: data.description,
                target_collection_id: data.collectionId,
                fork_workflow: data.forkWorkflow,
              },
            });
          }}
          isPending={cloneMutation.isPending}
        />
      )}

      {historyTarget && (
        <AssistantVersionHistoryDialog
          open={Boolean(historyTarget)}
          onOpenChange={(open) => !open && setHistoryTarget(null)}
          assistantName={historyTarget.name}
          versions={versionsQuery.data || []}
          isLoading={versionsQuery.isLoading}
          onRollback={(versionId) =>
            rollbackMutation.mutate({
              assistantId: historyTarget.code || historyTarget.id,
              versionId,
            })
          }
          isRollbacking={rollbackMutation.isPending}
        />
      )}

      {embedTarget && (
        <AssistantEmbedDialog
          open={Boolean(embedTarget)}
          onOpenChange={(open) => !open && setEmbedTarget(null)}
          assistantCode={embedTarget.code}
          assistantName={embedTarget.name}
        />
      )}
    </div>
  );
}
