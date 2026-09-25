import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  AlertTriangle,
  GitFork,
  History,
  Lock,
  Network,
  Play,
  Plus,
  RefreshCw,
  Rocket,
  Save,
  Share2,
  ShieldCheck,
  Sliders,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "@/components/admin/empty-state";
import {
  InCanvasTestRunner,
  type NodeExecutionState,
} from "@/components/admin/in-canvas-test-runner";
import {
  NodeCatalogDrawer,
  type NodeCatalogItem,
} from "@/components/admin/node-catalog-drawer";
import { PropertyInspector } from "@/components/admin/property-inspector";
import { WorkflowVersionHistoryDialog } from "@/components/admin/workflow-version-history-dialog";
import { DAGCanvas, type WorkflowNodeData } from "@/components/ai/dag-canvas";
import {
  convertDagSpecToReactFlow,
  extractNodeId,
} from "@/components/ai/dag-layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  type WorkflowDagSpec,
  type WorkflowNodeSpec,
  type WorkflowValidationReport,
  workflowsApi,
} from "@/services/workflows-api";
import type { AssistantItem } from "@/types/assistants";

interface AssistantWorkflowTabProps {
  assistant: AssistantItem;
  onForkWorkflow: () => void;
  isForking: boolean;
}

export function AssistantWorkflowTab({
  assistant,
  onForkWorkflow,
  isForking,
}: AssistantWorkflowTabProps) {
  const queryClient = useQueryClient();
  const workflowId = assistant.workflow_id;

  // 1. Studio State
  const [workingDagSpec, setWorkingDagSpec] = useState<WorkflowDagSpec | null>(
    null,
  );
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [selectedNode, setSelectedNode] = useState<WorkflowNodeData | null>(
    null,
  );
  const [direction, setDirection] = useState<"TB" | "LR">("TB");
  const [validationReport, setValidationReport] =
    useState<WorkflowValidationReport | null>(null);
  const [executionStates, setExecutionStates] = useState<
    Record<string, NodeExecutionState>
  >({});

  // Modals & Panels
  const [isNodeCatalogOpen, setIsNodeCatalogOpen] = useState<boolean>(false);
  const [isTestRunnerOpen, setIsTestRunnerOpen] = useState<boolean>(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [showValidationSheet, setShowValidationSheet] =
    useState<boolean>(false);

  // 2. Fetch Workflow Draft
  const {
    data: draft,
    isLoading,
    isRefetching,
    error,
    refetch,
  } = useQuery({
    queryKey: ["workflow-draft", workflowId],
    queryFn: () => workflowsApi.getDraft(workflowId),
    enabled: Boolean(workflowId),
  });

  // 3. Sync draft spec into working copy
  const activeDagSpec = workingDagSpec || draft?.dag_spec || null;

  useEffect(() => {
    if (draft?.dag_spec && !isDirty) {
      setWorkingDagSpec(draft.dag_spec);
    }
  }, [draft, isDirty]);

  // 4. Convert DAG Spec to ReactFlow format
  const { nodes, edges } = useMemo(() => {
    if (!activeDagSpec) return { nodes: [], edges: [] };
    return convertDagSpecToReactFlow(
      activeDagSpec,
      executionStates,
      direction,
    );
  }, [activeDagSpec, executionStates, direction]);

  // 5. Save Draft Mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!workingDagSpec || !draft) {
        throw new Error("Không có đặc tả DAG để lưu.");
      }
      return workflowsApi.saveDraft(workflowId, {
        dag_spec: workingDagSpec,
        expected_revision: draft.revision,
        updated_by: "platform-admin",
      });
    },
    onSuccess: (updatedDraft) => {
      toast.success(
        `Đã lưu bản nháp DAG thành công! (Rev #${updatedDraft.revision})`,
      );
      setIsDirty(false);
      void queryClient.invalidateQueries({
        queryKey: ["workflow-draft", workflowId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["assistants", assistant.id],
      });
    },
    onError: (err: Error) => {
      toast.error(`Lưu bản nháp thất bại: ${err.message}`);
    },
  });

  // 6. Validate Draft Mutation
  const validateMutation = useMutation({
    mutationFn: async () => {
      return workflowsApi.validateDraft(workflowId);
    },
    onSuccess: (report) => {
      setValidationReport(report);
      if (report.is_valid) {
        toast.success(
          `Cấu trúc DAG hợp lệ! (${report.node_count} nodes, ${report.edge_count} cạnh kết nối)`,
        );
      } else {
        setShowValidationSheet(true);
        toast.warning(
          `Phát hiện ${report.issues.length} vấn đề cấu trúc cần xử lý trước khi xuất bản.`,
        );
      }
    },
    onError: (err: Error) => {
      toast.error(`Kiểm tra cấu trúc thất bại: ${err.message}`);
    },
  });

  // 7. Publish Draft Mutation
  const publishMutation = useMutation({
    mutationFn: async () => {
      if (!draft) throw new Error("Chưa tải được bản nháp.");
      return workflowsApi.publishDraft(workflowId, {
        expected_revision: draft.revision,
        published_by: "platform-admin",
      });
    },
    onSuccess: (publishedVersion) => {
      toast.success(
        `Xuất bản thành công phiên bản v${publishedVersion.version_number}!`,
      );
      setIsDirty(false);
      void queryClient.invalidateQueries({
        queryKey: ["workflow-draft", workflowId],
      });
    },
    onError: (err: Error) => {
      toast.error(`Xuất bản thất bại: ${err.message}`);
    },
  });

  // 8. Node Manipulation Handlers
  const handleUpdateNode = (
    nodeId: string,
    updatedData: Partial<WorkflowNodeData>,
  ) => {
    if (!workingDagSpec) return;

    const nextNodes: WorkflowNodeSpec[] = workingDagSpec.nodes.map((n) => {
      if (n.id !== nodeId) return n;

      const rawConfig =
        (updatedData.workflowConfig as Record<string, unknown> | undefined) ||
        (updatedData.config as Record<string, unknown> | undefined) ||
        n.config;

      const rawPolicy =
        (updatedData.workflowPolicy as Record<string, unknown> | undefined) ||
        (updatedData.policy as Record<string, unknown> | undefined) ||
        n.policy;

      return {
        ...n,
        display_name: updatedData.label ?? n.display_name,
        config: rawConfig,
        policy: {
          ...rawPolicy,
          description: updatedData.description ?? n.policy?.description,
          timeout_seconds:
            updatedData.timeoutSeconds ?? n.policy?.timeout_seconds ?? 30,
        },
      };
    });

    setWorkingDagSpec({
      ...workingDagSpec,
      nodes: nextNodes,
    });
    setIsDirty(true);
    toast.info(`Đã cập nhật cấu hình node "${updatedData.label || nodeId}"`);
  };

  const handleDeleteNode = (nodeId: string) => {
    if (!workingDagSpec) return;

    if (workingDagSpec.entry_node_id === nodeId) {
      toast.error("Không thể xóa entry node (điểm khởi đầu luồng công việc).");
      return;
    }

    const nextNodes = workingDagSpec.nodes.filter((n) => n.id !== nodeId);
    const nextEdges = workingDagSpec.edges.filter((e) => {
      const srcId = extractNodeId(e.source);
      const tgtId = extractNodeId(e.target);
      return srcId !== nodeId && tgtId !== nodeId;
    });

    setWorkingDagSpec({
      ...workingDagSpec,
      nodes: nextNodes,
      edges: nextEdges,
    });
    setSelectedNode(null);
    setIsDirty(true);
    toast.success(`Đã xóa node "${nodeId}" khỏi đồ thị.`);
  };

  const handleAddNodeFromCatalog = (item: NodeCatalogItem) => {
    if (!workingDagSpec) return;

    const cleanPrefix = item.type.replace(/[^a-zA-Z0-9]/g, "_");
    const uniqueId = `${cleanPrefix}_${Date.now().toString(36).slice(-4)}`;

    const newNodeSpec: WorkflowNodeSpec = {
      id: uniqueId,
      type: item.type,
      version: item.version || "1.0.0",
      display_name: item.label,
      config: item.defaultConfig || {},
      policy: {
        description: item.description,
        timeout_seconds: item.timeoutSeconds || 30,
      },
    };

    setWorkingDagSpec({
      ...workingDagSpec,
      nodes: [...workingDagSpec.nodes, newNodeSpec],
    });
    setIsDirty(true);
    setIsNodeCatalogOpen(false);
    toast.success(`Đã thêm node "${item.label}" vào sơ đồ DAG.`);
  };

  if (!workflowId) {
    return (
      <EmptyState
        icon={Network}
        title="Chưa Gán Workflow Cho Trợ Lý"
        description="Trợ lý này chưa được liên kết với quy trình DAG nào. Bạn có thể chọn quy trình trong phần Cài đặt tổng quan."
      />
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/40 bg-destructive/5">
        <CardContent className="flex flex-col sm:flex-row sm:items-center justify-between p-6 gap-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="size-5 text-destructive shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-foreground">
                Không thể tải sơ đồ DAG quy trình ({workflowId})
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {(error as Error)?.message ||
                  "Vui lòng kiểm tra lại dịch vụ Workflow Backend."}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs shrink-0"
            onClick={() => void refetch()}
          >
            Thử lại
          </Button>
        </CardContent>
      </Card>
    );
  }

  const isPrivate = assistant.workflow_ownership === "private";

  return (
    <Card className="border-border/80 shadow-xs flex flex-col overflow-hidden">
      {/* 1. Studio Header Toolbar */}
      <CardHeader className="p-3 sm:p-4 border-b border-border/70 bg-card/60 backdrop-blur-xs space-y-3">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          {/* Left: Info & Badges */}
          <div className="flex flex-wrap items-center gap-2 min-w-0">
            <div className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary shrink-0">
              <Network className="size-3.5" />
            </div>

            <CardTitle className="text-xs sm:text-sm font-bold text-foreground">
              Quy Trình DAG Trợ Lý
            </CardTitle>

            <span className="text-muted-foreground/60 hidden sm:inline">•</span>

            <code className="text-[11px] font-mono font-medium text-foreground bg-muted px-1.5 py-0.5 rounded">
              {workflowId}
            </code>

            <Badge
              variant="outline"
              className={
                isPrivate
                  ? "border-amber-500/30 text-amber-600 dark:text-amber-400 bg-amber-500/5 text-[10px] gap-1 px-1.5 py-0.5"
                  : "border-primary/30 text-primary bg-primary/5 text-[10px] gap-1 px-1.5 py-0.5"
              }
            >
              {isPrivate ? (
                <>
                  <Lock className="size-2.5" />
                  Riêng trợ lý
                </>
              ) : (
                <>
                  <Share2 className="size-2.5" />
                  Dùng chung
                </>
              )}
            </Badge>

            {draft && (
              <Badge
                variant="secondary"
                className="text-[10px] px-1 py-0 font-mono hidden sm:inline-flex"
              >
                Rev #{draft.revision}
              </Badge>
            )}

            {isDirty && (
              <span className="flex items-center gap-1 text-[11px] text-amber-500 font-medium">
                <span className="size-1.5 rounded-full bg-amber-500 animate-pulse" />
                <span>Chưa lưu</span>
              </span>
            )}
          </div>

          {/* Right: Studio Actions Toolbar */}
          <div className="flex flex-wrap items-center gap-1.5 shrink-0">
            {/* Fork Workflow (if shared) */}
            {!isPrivate && (
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs gap-1 border-amber-500/40 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10 font-medium"
                onClick={onForkWorkflow}
                disabled={isForking}
                title="Tách thành luồng riêng độc lập để tùy biến cho riêng trợ lý này"
              >
                <GitFork className="size-3" />
                <span className="hidden sm:inline">Tách riêng</span>
              </Button>
            )}

            {/* Layout Orientation Toggle */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 px-2.5 text-xs gap-1 font-mono"
                  onClick={() => setDirection(direction === "TB" ? "LR" : "TB")}
                  aria-label="Đổi hướng bố cục"
                >
                  <Sliders className="size-3 text-muted-foreground" />
                  <span className="hidden sm:inline">
                    {direction === "TB" ? "Dọc" : "Ngang"}
                  </span>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                Bố cục:{" "}
                {direction === "TB"
                  ? "Từ trên xuống (TB)"
                  : "Từ trái sang (LR)"}
              </TooltipContent>
            </Tooltip>

            {/* Add Node Button */}
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs gap-1 font-medium"
              onClick={() => setIsNodeCatalogOpen(true)}
            >
              <Plus className="size-3" />
              <span>Thêm node</span>
            </Button>

            {/* Validate Button */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 px-2 text-xs gap-1 font-medium"
                  onClick={() => validateMutation.mutate()}
                  disabled={validateMutation.isPending}
                >
                  <ShieldCheck
                    className={`size-3 ${validateMutation.isPending ? "animate-spin" : "text-primary"}`}
                  />
                  <span className="hidden sm:inline">Kiểm tra</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                Kiểm tra tính toàn vẹn cấu trúc DAG
              </TooltipContent>
            </Tooltip>

            {/* In-Canvas Test Runner Button */}
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs gap-1 text-primary border-primary/40 hover:bg-primary/5 font-medium"
              onClick={() => setIsTestRunnerOpen(true)}
            >
              <Play className="size-3 fill-primary text-primary" />
              <span>Chạy thử</span>
            </Button>

            {/* Version History Button */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="size-8 p-0 text-muted-foreground hover:text-foreground"
                  onClick={() => setIsHistoryOpen(true)}
                  aria-label="Lịch sử phiên bản"
                >
                  <History className="size-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                Xem lịch sử phiên bản & khôi phục
              </TooltipContent>
            </Tooltip>

            {/* Refresh Button */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="size-8 p-0 text-muted-foreground hover:text-foreground"
                  onClick={() => void refetch()}
                  disabled={isLoading || isRefetching}
                  aria-label="Làm mới"
                >
                  <RefreshCw
                    className={`size-3.5 ${
                      isLoading || isRefetching
                        ? "animate-spin text-primary"
                        : ""
                    }`}
                  />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                Tải lại bản nháp từ server
              </TooltipContent>
            </Tooltip>

            {/* Save Draft Button */}
            <Button
              variant={isDirty ? "default" : "outline"}
              size="sm"
              className="h-8 text-xs gap-1 font-medium"
              onClick={() => saveMutation.mutate()}
              disabled={!isDirty || saveMutation.isPending}
            >
              <Save
                className={`size-3 ${saveMutation.isPending ? "animate-spin" : ""}`}
              />
              <span>Lưu nháp</span>
            </Button>

            {/* Publish Button */}
            <Button
              size="sm"
              className="h-8 text-xs gap-1 bg-primary text-primary-foreground font-medium"
              onClick={() => publishMutation.mutate()}
              disabled={publishMutation.isPending}
            >
              <Rocket
                className={`size-3 ${publishMutation.isPending ? "animate-spin" : ""}`}
              />
              <span>Phát hành</span>
            </Button>
          </div>
        </div>
      </CardHeader>

      {/* 2. Interactive Studio Canvas Area */}
      <CardContent className="p-0 relative flex-1 min-h-[640px] h-[680px] w-full overflow-hidden bg-background">
        {isLoading || (!activeDagSpec && !draft) ? (
          <div className="flex flex-col items-center justify-center h-full w-full gap-3 text-muted-foreground min-h-[640px]">
            <RefreshCw className="size-6 animate-spin text-primary" />
            <p className="text-xs font-medium">
              Đang tải sơ đồ DAG quy trình...
            </p>
          </div>
        ) : (
          <DAGCanvas
            key={`${workflowId}-${direction}-${activeDagSpec?.nodes?.length || 0}`}
            initialNodes={nodes}
            initialEdges={edges}
            executionStates={executionStates}
            onNodeSelect={setSelectedNode}
            workflowName={`DAG — ${assistant.name}`}
            className="w-full h-full"
          />
        )}

        {/* Floating Validation Report (if issues exist) */}
        {validationReport &&
          validationReport.issues.length > 0 &&
          showValidationSheet && (
            <div className="absolute bottom-4 left-4 max-w-sm sm:max-w-md bg-card/95 backdrop-blur-md border border-border shadow-lg rounded-lg p-3 z-10 space-y-2 animate-in fade-in slide-in-from-bottom-2">
              <div className="flex items-center justify-between gap-2 border-b border-border/60 pb-2">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                  <AlertTriangle className="size-4 text-warning" />
                  Vấn Đề Kiểm Tra Cấu Trúc ({validationReport.issues.length})
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-6 text-muted-foreground hover:text-foreground"
                  onClick={() => setShowValidationSheet(false)}
                  aria-label="Đóng cảnh báo"
                >
                  <X className="size-3.5" />
                </Button>
              </div>

              <div className="max-h-40 overflow-y-auto space-y-1.5 pr-1">
                {validationReport.issues.map((issue) => (
                  <div
                    key={`${issue.code}-${issue.message}-${issue.node_id || ""}`}
                    className="flex items-start gap-2 p-1.5 rounded-sm bg-muted/40 text-[11px]"
                  >
                    <span
                      className={`size-1.5 rounded-full mt-1.5 shrink-0 ${
                        issue.severity === "error"
                          ? "bg-destructive"
                          : "bg-warning"
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-foreground font-medium">
                        {issue.message}
                      </p>
                      {issue.node_id && (
                        <p className="text-muted-foreground font-mono text-[10px]">
                          Node ID: {issue.node_id}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        {/* Selected Node Property Inspector */}
        {selectedNode && (
          <PropertyInspector
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
            onUpdateNode={handleUpdateNode}
            onDeleteNode={handleDeleteNode}
          />
        )}
      </CardContent>

      {/* 3. Modals & Drawers */}
      {/* Node Catalog Drawer */}
      <NodeCatalogDrawer
        isOpen={isNodeCatalogOpen}
        onClose={() => setIsNodeCatalogOpen(false)}
        onSelectNodeToAdd={handleAddNodeFromCatalog}
      />

      {/* In-Canvas Test Runner */}
      <InCanvasTestRunner
        workflowId={workflowId}
        workflowName={`DAG — ${assistant.name}`}
        isOpen={isTestRunnerOpen}
        onClose={() => setIsTestRunnerOpen(false)}
        onUpdateExecutionState={setExecutionStates}
        onResetCanvasStates={() => setExecutionStates({})}
      />

      {/* Version History Dialog */}
      <WorkflowVersionHistoryDialog
        workflowId={workflowId}
        workflowName={`DAG — ${assistant.name}`}
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onRollbackSuccess={() => {
          setIsDirty(false);
          void refetch();
          void queryClient.invalidateQueries({
            queryKey: ["workflow-draft", workflowId],
          });
        }}
      />
    </Card>
  );
}
