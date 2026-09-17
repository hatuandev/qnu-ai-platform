import { useMutation, useQuery } from "@tanstack/react-query";
import type { Edge, Node } from "@xyflow/react";
import {
  AlertCircle,
  BookOpen,
  Check,
  Copy,
  FileText,
  GraduationCap,
  Library,
  MessageSquare,
  Network,
  Play,
  Plus,
  RefreshCw,
  Save,
  Send,
  ShieldCheck,
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  InCanvasTestRunner,
  type NodeExecutionState,
} from "../components/admin/in-canvas-test-runner";
import { NodeCatalogDrawer, type NodeCatalogItem } from "../components/admin/node-catalog-drawer";
import { PropertyInspector } from "../components/admin/property-inspector";
import { DAGCanvas, type WorkflowNodeData } from "../components/ai/dag-canvas";
import { Button } from "../components/ui/button";
import {
  type WorkflowDagSpec,
  type WorkflowDefinition,
  type WorkflowDraft,
  type WorkflowNodeSpec,
  workflowsApi,
} from "../services/workflows-api";

type CanvasNodeKind =
  | "chatInput"
  | "conditionRoute"
  | "ragKnowledge"
  | "llmGenerate"
  | "toolCall"
  | "guardrail"
  | "humanApproval"
  | "chatOutput";

interface WorkflowCanvasState {
  definition: WorkflowDefinition;
  dagSpec: WorkflowDagSpec;
  draftRevision: number;
  nodes: Node<WorkflowNodeData>[];
  edges: Edge[];
}

export interface DAGCanvasPageProps {
  onNavigateToChat?: (assistantCode: string) => void;
}

function toCanvasNodeKind(nodeType: string): CanvasNodeKind {
  if (nodeType === "input.chat" || nodeType === "chat_input") return "chatInput";
  if (nodeType === "condition.route" || nodeType === "router") return "conditionRoute";
  if (nodeType.startsWith("rag.") || nodeType.includes("knowledge.answer")) return "ragKnowledge";
  if (nodeType.includes("human_approval") || nodeType === "human.approval") return "humanApproval";
  if (nodeType.startsWith("guard.") || nodeType.includes("citation")) return "guardrail";
  if (nodeType.startsWith("output.") || nodeType.includes("_output")) return "chatOutput";
  if (nodeType.startsWith("tool.")) return "toolCall";
  return "llmGenerate";
}

function toNodeCategory(nodeKind: CanvasNodeKind): WorkflowNodeData["category"] {
  const categories: Record<CanvasNodeKind, WorkflowNodeData["category"]> = {
    chatInput: "input",
    conditionRoute: "route",
    ragKnowledge: "rag",
    llmGenerate: "llm",
    toolCall: "tool",
    guardrail: "guard",
    humanApproval: "human",
    chatOutput: "output",
  };
  return categories[nodeKind];
}

function summarizeConfig(config: Record<string, unknown>): string {
  const entries = Object.entries(config).slice(0, 3);
  if (entries.length === 0) return "Chưa có cấu hình riêng";
  return entries
    .map(([key, value]) => `${key}: ${typeof value === "string" ? value : JSON.stringify(value)}`)
    .join(", ");
}

function calculatePositions(dagSpec: WorkflowDagSpec): Map<string, { x: number; y: number }> {
  const levels = new Map<string, number>([[dagSpec.entry_node_id, 0]]);
  for (let pass = 0; pass < dagSpec.nodes.length; pass += 1) {
    let changed = false;
    for (const edge of dagSpec.edges) {
      const sourceLevel = levels.get(edge.source);
      if (sourceLevel === undefined) continue;
      const targetLevel = sourceLevel + 1;
      if ((levels.get(edge.target) ?? -1) < targetLevel) {
        levels.set(edge.target, targetLevel);
        changed = true;
      }
    }
    if (!changed) break;
  }

  const lanes = new Map<number, string[]>();
  for (const node of dagSpec.nodes) {
    const level = levels.get(node.id) ?? 0;
    lanes.set(level, [...(lanes.get(level) ?? []), node.id]);
  }

  const positions = new Map<string, { x: number; y: number }>();
  for (const [level, nodeIds] of lanes) {
    nodeIds.forEach((nodeId, index) => {
      positions.set(nodeId, { x: 80 + index * 300, y: 36 + level * 155 });
    });
  }
  return positions;
}

function toCanvasState(definition: WorkflowDefinition, draft: WorkflowDraft): WorkflowCanvasState {
  const positions = calculatePositions(draft.dag_spec);
  return {
    definition,
    dagSpec: draft.dag_spec,
    draftRevision: draft.revision,
    nodes: draft.dag_spec.nodes.map((node) => {
      const nodeKind = toCanvasNodeKind(node.type);
      return {
        id: node.id,
        type: nodeKind,
        position: positions.get(node.id) ?? { x: 80, y: 36 },
        data: {
          id: node.id,
          label: node.display_name || node.id,
          category: toNodeCategory(nodeKind),
          description:
            typeof node.policy.description === "string" ? node.policy.description : undefined,
          configSummary: summarizeConfig(node.config),
          timeoutSeconds:
            typeof node.policy.timeout_seconds === "number"
              ? node.policy.timeout_seconds
              : undefined,
          workflowNodeType: node.type,
          workflowNodeVersion: node.version,
          workflowConfig: node.config,
          workflowPolicy: node.policy,
        },
      };
    }),
    edges: draft.dag_spec.edges.map((edge, index) => ({
      id: `${edge.source}-${edge.target}-${index}`,
      source: edge.source,
      target: edge.target,
      label: edge.label || edge.source_port || undefined,
      animated: true,
    })),
  };
}

function readNodeRecord(nodeData: WorkflowNodeData, key: string): Record<string, unknown> {
  const value = nodeData[key];
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function readNodeString(nodeData: WorkflowNodeData, key: string, fallback: string): string {
  const value = nodeData[key];
  return typeof value === "string" && value.trim() ? value : fallback;
}

function toPersistedDagSpec(workflow: WorkflowCanvasState): WorkflowDagSpec {
  const nodeById = new Map(workflow.nodes.map((node) => [node.id, node]));
  const persistedNodes: WorkflowNodeSpec[] = workflow.nodes.map((node) => {
    const originalNode = workflow.dagSpec.nodes.find((item) => item.id === node.id);
    return {
      id: node.id,
      type: readNodeString(node.data, "workflowNodeType", originalNode?.type || "llm.generate"),
      version: readNodeString(node.data, "workflowNodeVersion", originalNode?.version || "1.0.0"),
      display_name: node.data.label,
      config: readNodeRecord(node.data, "workflowConfig"),
      policy: readNodeRecord(node.data, "workflowPolicy"),
    };
  });
  const persistedEdges = workflow.edges.map((edge) => {
    const originalEdge = workflow.dagSpec.edges.find(
      (item) => item.source === edge.source && item.target === edge.target
    );
    return {
      source: edge.source,
      target: edge.target,
      source_port: originalEdge?.source_port,
      target_port: originalEdge?.target_port,
      condition: originalEdge?.condition,
      label: typeof edge.label === "string" ? edge.label : originalEdge?.label,
    };
  });
  const entryNodeId = nodeById.has(workflow.dagSpec.entry_node_id)
    ? workflow.dagSpec.entry_node_id
    : persistedNodes[0]?.id || "";
  return {
    ...workflow.dagSpec,
    entry_node_id: entryNodeId,
    nodes: persistedNodes,
    edges: persistedEdges,
  };
}

function workflowIcon(moduleCode: string): React.ReactNode {
  if (moduleCode.includes("admission")) return <GraduationCap className="size-4" />;
  if (moduleCode.includes("regulation")) return <BookOpen className="size-4" />;
  if (moduleCode.includes("library")) return <Library className="size-4" />;
  return <FileText className="size-4" />;
}

function nodeTypeForCatalogItem(item: NodeCatalogItem): {
  kind: CanvasNodeKind;
  workflowNodeType: string;
} {
  const mappings: Record<string, { kind: CanvasNodeKind; workflowNodeType: string }> = {
    input: { kind: "chatInput", workflowNodeType: "input.chat" },
    route: { kind: "conditionRoute", workflowNodeType: "condition.route" },
    rag: { kind: "ragKnowledge", workflowNodeType: "core.knowledge.answer" },
    llm: { kind: "llmGenerate", workflowNodeType: "llm.generate" },
    tool: { kind: "toolCall", workflowNodeType: "tool.human_approval" },
    guard: { kind: "guardrail", workflowNodeType: "guard.citation_policy" },
    human: { kind: "humanApproval", workflowNodeType: "tool.human_approval" },
    output: { kind: "chatOutput", workflowNodeType: "output.chat" },
  };
  return mappings[item.category] || mappings.llm;
}

export const DAGCanvasPage: React.FC<DAGCanvasPageProps> = ({ onNavigateToChat }) => {
  const requestedAssistant = new URLSearchParams(window.location.search).get("assistant");
  const [selectedWorkflowId, setSelectedWorkflowId] = useState(
    requestedAssistant ? `${requestedAssistant}-assistant` : ""
  );
  const [workflow, setWorkflow] = useState<WorkflowCanvasState | null>(null);
  const [executionStates, setExecutionStates] = useState<Record<string, NodeExecutionState>>({});
  const [selectedNodeData, setSelectedNodeData] = useState<WorkflowNodeData | null>(null);
  const [isCatalogOpen, setIsCatalogOpen] = useState(false);
  const [isTestRunnerOpen, setIsTestRunnerOpen] = useState(false);
  const [isJsonCopied, setIsJsonCopied] = useState(false);
  const [validationSummary, setValidationSummary] = useState<string | null>(null);

  const definitionsQuery = useQuery({
    queryKey: ["workflow-definitions"],
    queryFn: workflowsApi.listDefinitions,
  });
  const definitions = definitionsQuery.data ?? [];

  useEffect(() => {
    if (definitions.length === 0) return;
    if (definitions.some((definition) => definition.id === selectedWorkflowId)) return;
    setSelectedWorkflowId(definitions[0].id);
  }, [definitions, selectedWorkflowId]);

  const selectedDefinition = useMemo(
    () => definitions.find((definition) => definition.id === selectedWorkflowId) ?? null,
    [definitions, selectedWorkflowId]
  );
  const draftQuery = useQuery({
    queryKey: ["workflow-draft", selectedWorkflowId],
    queryFn: () => workflowsApi.getDraft(selectedWorkflowId),
    enabled: Boolean(selectedWorkflowId),
  });

  useEffect(() => {
    if (!selectedDefinition || !draftQuery.data) return;
    setWorkflow(toCanvasState(selectedDefinition, draftQuery.data));
    setSelectedNodeData(null);
    setExecutionStates({});
    setValidationSummary(null);
  }, [draftQuery.data, selectedDefinition]);

  const saveMutation = useMutation({
    mutationFn: (currentWorkflow: WorkflowCanvasState) =>
      workflowsApi.saveDraft(currentWorkflow.definition.id, {
        dag_spec: toPersistedDagSpec(currentWorkflow),
        expected_revision: currentWorkflow.draftRevision,
        updated_by: "platform-admin",
      }),
    onSuccess: (draft) => {
      if (!selectedDefinition) return;
      setWorkflow(toCanvasState(selectedDefinition, draft));
      toast.success("Đã lưu bản nháp DAG.");
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const validateMutation = useMutation({
    mutationFn: workflowsApi.validateDraft,
    onSuccess: (report) => {
      const errorCount = report.issues.filter((issue) => issue.severity === "error").length;
      setValidationSummary(
        report.is_valid
          ? `DAG hợp lệ: ${report.node_count} node, ${report.edge_count} cạnh.`
          : `DAG có ${errorCount} lỗi cần xử lý trước khi xuất bản.`
      );
      if (report.is_valid) toast.success("DAG đạt điều kiện xuất bản.");
      else toast.error("DAG chưa đạt điều kiện xuất bản.");
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const publishMutation = useMutation({
    mutationFn: ({ workflowId, revision }: { workflowId: string; revision: number }) =>
      workflowsApi.publishDraft(workflowId, {
        expected_revision: revision,
        published_by: "platform-admin",
      }),
    onSuccess: (version) =>
      toast.success(`Đã xuất bản workflow phiên bản ${version.version_number}.`),
    onError: (error: Error) => toast.error(error.message),
  });

  const updateWorkflow = (
    updater: (currentWorkflow: WorkflowCanvasState) => WorkflowCanvasState
  ) => {
    setWorkflow((currentWorkflow) =>
      currentWorkflow ? updater(currentWorkflow) : currentWorkflow
    );
  };

  const handleValidateDraft = async () => {
    if (!workflow) return;
    try {
      const savedDraft = await saveMutation.mutateAsync(workflow);
      await validateMutation.mutateAsync(savedDraft.workflow_id);
    } catch {
      // Each mutation already surfaces a user-facing error toast.
    }
  };

  const handlePublishDraft = async () => {
    if (!workflow) return;
    try {
      const savedDraft = await saveMutation.mutateAsync(workflow);
      const report = await validateMutation.mutateAsync(savedDraft.workflow_id);
      if (!report.is_valid) return;
      await publishMutation.mutateAsync({
        workflowId: savedDraft.workflow_id,
        revision: savedDraft.revision,
      });
    } catch {
      // Each mutation already surfaces a user-facing error toast.
    }
  };

  const handleAddNodeFromCatalog = (catalogItem: NodeCatalogItem) => {
    if (!workflow) return;
    const mapping = nodeTypeForCatalogItem(catalogItem);
    const nodeId = `${catalogItem.category}_${crypto.randomUUID().slice(0, 8)}`;
    const newNode: Node<WorkflowNodeData> = {
      id: nodeId,
      type: mapping.kind,
      position: { x: 100, y: 80 + workflow.nodes.length * 90 },
      data: {
        id: nodeId,
        label: catalogItem.label,
        category: toNodeCategory(mapping.kind),
        description: catalogItem.description,
        configSummary: catalogItem.defaultConfigSummary,
        timeoutSeconds: catalogItem.timeoutSeconds,
        workflowNodeType: mapping.workflowNodeType,
        workflowNodeVersion: "1.0.0",
        workflowConfig: {},
        workflowPolicy: { timeout_seconds: catalogItem.timeoutSeconds },
      },
    };
    updateWorkflow((currentWorkflow) => ({
      ...currentWorkflow,
      nodes: [...currentWorkflow.nodes, newNode],
    }));
    setSelectedNodeData(newNode.data);
    setIsCatalogOpen(false);
  };

  const handleUpdateNode = (nodeId: string, updatedData: Partial<WorkflowNodeData>) => {
    updateWorkflow((currentWorkflow) => ({
      ...currentWorkflow,
      nodes: currentWorkflow.nodes.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, ...updatedData } } : node
      ),
    }));
    setSelectedNodeData((currentNode) =>
      currentNode?.id === nodeId ? { ...currentNode, ...updatedData } : currentNode
    );
  };

  const handleDeleteNode = (nodeId: string) => {
    updateWorkflow((currentWorkflow) => ({
      ...currentWorkflow,
      nodes: currentWorkflow.nodes.filter((node) => node.id !== nodeId),
      edges: currentWorkflow.edges.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId
      ),
    }));
    setSelectedNodeData(null);
  };

  const handleCopyDag = () => {
    if (!workflow || !navigator.clipboard) return;
    navigator.clipboard.writeText(JSON.stringify(toPersistedDagSpec(workflow), null, 2));
    setIsJsonCopied(true);
    window.setTimeout(() => setIsJsonCopied(false), 2000);
  };

  const loadError = definitionsQuery.error || draftQuery.error;
  if (loadError) {
    return (
      <div className="-m-6 grid h-[calc(100vh-4rem)] place-items-center bg-background p-6">
        <div className="max-w-md rounded-surface border border-destructive/30 bg-destructive/10 p-5 text-center">
          <AlertCircle className="mx-auto size-6 text-destructive" />
          <h1 className="mt-3 text-sm font-bold text-foreground">Không tải được Workflow DAG</h1>
          <p className="mt-1 text-xs text-muted-foreground">{loadError.message}</p>
          <Button className="mt-4 h-8 text-xs" onClick={() => void definitionsQuery.refetch()}>
            <RefreshCw className="mr-1 size-3" />
            Tải lại
          </Button>
        </div>
      </div>
    );
  }

  if (definitionsQuery.isPending || draftQuery.isPending || !workflow) {
    return (
      <div className="-m-6 grid h-[calc(100vh-4rem)] place-items-center bg-background">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <RefreshCw className="size-4 animate-spin text-primary" />
          <span>Đang tải bản nháp DAG từ Platform…</span>
        </div>
      </div>
    );
  }

  const assistantCode = workflow.definition.id.replace(/-assistant$/, "");
  const isMutating =
    saveMutation.isPending || validateMutation.isPending || publishMutation.isPending;

  return (
    <div className="-m-6 flex h-[calc(100vh-4rem)] flex-col overflow-hidden bg-background">
      <div className="z-10 flex h-14 shrink-0 items-center justify-between border-b border-border bg-card/90 px-5 backdrop-blur-md">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-control bg-primary/10 text-primary">
            <Network className="size-4" />
          </div>
          <div className="min-w-0">
            <h1 className="flex items-center gap-2 truncate text-sm font-bold text-foreground">
              <span>DAG Studio</span>
              <span className="font-normal text-muted-foreground">•</span>
              <span className="truncate text-xs font-medium text-primary">
                {workflow.definition.display_name}
              </span>
            </h1>
            <p className="truncate text-[10px] text-muted-foreground">
              Bản nháp r{workflow.draftRevision} — {workflow.nodes.length} nodes,{" "}
              {workflow.edges.length} connections
            </p>
          </div>
          <div className="ml-3 hidden items-center gap-1 border-l border-border pl-3 lg:flex">
            {definitions.map((definition) => (
              <button
                type="button"
                key={definition.id}
                onClick={() => setSelectedWorkflowId(definition.id)}
                className={`flex cursor-pointer items-center gap-1.5 rounded-control px-2.5 py-1 text-xs font-medium transition-all ${
                  selectedWorkflowId === definition.id
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                {workflowIcon(definition.module_code)}
                <span>{definition.display_name}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs"
            onClick={() => setIsCatalogOpen(true)}
          >
            <Plus className="mr-1 size-3.5 text-primary" />
            Thêm node
          </Button>
          <Button size="sm" className="h-8 text-xs" onClick={() => setIsTestRunnerOpen(true)}>
            <Play className="mr-1 size-3.5 fill-primary-foreground" />
            Chạy thử
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs"
            disabled={isMutating}
            onClick={() => saveMutation.mutate(workflow)}
          >
            <Save className="mr-1 size-3.5" />
            Lưu nháp
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs"
            disabled={isMutating}
            onClick={() => void handleValidateDraft()}
          >
            <ShieldCheck className="mr-1 size-3.5" />
            Kiểm tra
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs"
            disabled={isMutating}
            onClick={() => void handlePublishDraft()}
          >
            <Send className="mr-1 size-3.5" />
            Xuất bản
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-8"
            onClick={handleCopyDag}
            title="Sao chép JSON"
          >
            {isJsonCopied ? (
              <Check className="size-3.5 text-success" />
            ) : (
              <Copy className="size-3.5" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-8"
            onClick={() => void draftQuery.refetch()}
            title="Tải lại bản nháp đã lưu"
          >
            <RefreshCw className="size-3.5" />
          </Button>
          {onNavigateToChat && (
            <Button
              variant="outline"
              size="sm"
              className="ml-1 hidden h-8 text-xs sm:flex"
              onClick={() => onNavigateToChat(assistantCode)}
            >
              <MessageSquare className="mr-1 size-3.5 text-primary" />
              Studio Chat
            </Button>
          )}
        </div>
      </div>

      {validationSummary && (
        <div className="flex shrink-0 items-center gap-2 border-b border-border bg-muted/40 px-5 py-1.5 text-xs text-muted-foreground">
          <ShieldCheck className="size-3.5 text-primary" />
          <span>{validationSummary}</span>
        </div>
      )}

      <div className="relative flex-1 overflow-hidden">
        <DAGCanvas
          initialNodes={workflow.nodes}
          initialEdges={workflow.edges}
          executionStates={executionStates}
          onNodeSelect={setSelectedNodeData}
          workflowName={workflow.definition.display_name}
          className="h-full w-full"
        />
        <NodeCatalogDrawer
          isOpen={isCatalogOpen}
          onClose={() => setIsCatalogOpen(false)}
          onSelectNodeToAdd={handleAddNodeFromCatalog}
        />
        <PropertyInspector
          node={selectedNodeData}
          onClose={() => setSelectedNodeData(null)}
          onUpdateNode={handleUpdateNode}
          onDeleteNode={handleDeleteNode}
        />
        <InCanvasTestRunner
          workflowId={workflow.definition.id}
          workflowName={workflow.definition.display_name}
          isOpen={isTestRunnerOpen}
          onClose={() => setIsTestRunnerOpen(false)}
          onUpdateExecutionState={(states) =>
            setExecutionStates((previous) => ({ ...previous, ...states }))
          }
          onResetCanvasStates={() => setExecutionStates({})}
        />
      </div>
    </div>
  );
};
