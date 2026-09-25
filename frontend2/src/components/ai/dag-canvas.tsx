import {
  Background,
  BackgroundVariant,
  Controls,
  type Edge,
  Handle,
  MiniMap,
  type Node,
  type NodeProps,
  Panel,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Clock,
  GitBranch,
  Layers,
  Loader2,
  MessageSquare,
  Search,
  Send,
  ShieldCheck,
  UserCheck,
  Wrench,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect } from "react";
import { Badge } from "../ui/badge";

export interface WorkflowNodeData {
  id: string;
  label: string;
  category:
    | "input"
    | "route"
    | "rag"
    | "llm"
    | "tool"
    | "guard"
    | "human"
    | "output";
  description?: string;
  configSummary?: string;
  timeoutSeconds?: number;
  status?: "idle" | "running" | "completed" | "waiting" | "failed";
  durationMs?: number;
  error?: string;
  [key: string]: unknown;
}

// Helper to render node execution status badge
const NodeStatusIndicator: React.FC<{
  status?: "idle" | "running" | "completed" | "waiting" | "failed";
  durationMs?: number;
}> = ({ status = "idle", durationMs }) => {
  if (status === "running") {
    return (
      <span className="flex items-center gap-1 text-[10px] font-mono text-primary font-semibold animate-pulse">
        <Loader2 className="size-3 animate-spin" />
        <span>Đang chạy...</span>
      </span>
    );
  }
  if (status === "completed") {
    return (
      <span className="flex items-center gap-1 text-[10px] font-mono text-success font-semibold">
        <CheckCircle2 className="size-3" />
        <span>{durationMs ? `${durationMs}ms` : "Xong"}</span>
      </span>
    );
  }
  if (status === "waiting") {
    return (
      <span className="flex items-center gap-1 text-[10px] font-mono text-warning font-semibold animate-bounce">
        <Clock className="size-3" />
        <span>Chờ duyệt</span>
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="flex items-center gap-1 text-[10px] font-mono text-destructive font-semibold">
        <AlertCircle className="size-3" />
        <span>Lỗi</span>
      </span>
    );
  }
  return null;
};

// 1. Custom Node: Input
const ChatInputNode = ({
  data,
  selected,
}: NodeProps<Node<WorkflowNodeData>>) => {
  const isRunning = data.status === "running";
  return (
    <div
      className={`min-w-[220px] rounded-surface bg-card border-2 p-3 shadow-xs transition-all ${
        isRunning
          ? "border-teal-500 ring-2 ring-teal-500/40 shadow-teal-500/10"
          : selected
            ? "border-primary ring-2 ring-primary/20"
            : "border-teal-500/40 hover:border-teal-500/70"
      }`}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="p-1 rounded-micro bg-teal-500/10 text-teal-600 dark:text-teal-400">
          <MessageSquare className="size-3.5" />
        </span>
        <span className="text-xs font-bold text-foreground">Chat Input</span>
        <div className="ml-auto flex items-center gap-1">
          <NodeStatusIndicator
            status={data.status}
            durationMs={data.durationMs}
          />
          <Badge variant="outline" className="text-[10px] font-mono">
            input.chat
          </Badge>
        </div>
      </div>
      <p className="text-xs font-semibold text-foreground">{data.label}</p>
      {data.description && (
        <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2">
          {data.description}
        </p>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        className="size-2.5 bg-teal-500 border-2 border-background"
      />
    </div>
  );
};

// 2. Custom Node: Route
const ConditionRouteNode = ({
  data,
  selected,
}: NodeProps<Node<WorkflowNodeData>>) => {
  const isRunning = data.status === "running";
  return (
    <div
      className={`min-w-[220px] rounded-surface bg-card border-2 p-3 shadow-xs transition-all ${
        isRunning
          ? "border-amber-500 ring-2 ring-amber-500/40 shadow-amber-500/10"
          : selected
            ? "border-primary ring-2 ring-primary/20"
            : "border-amber-500/40 hover:border-amber-500/70"
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="size-2.5 bg-amber-500 border-2 border-background"
      />
      <div className="flex items-center gap-2 mb-1.5">
        <span className="p-1 rounded-micro bg-amber-500/10 text-amber-600 dark:text-amber-400">
          <GitBranch className="size-3.5" />
        </span>
        <span className="text-xs font-bold text-foreground">Intent Route</span>
        <div className="ml-auto flex items-center gap-1">
          <NodeStatusIndicator
            status={data.status}
            durationMs={data.durationMs}
          />
          <Badge variant="outline" className="text-[10px] font-mono">
            condition.route
          </Badge>
        </div>
      </div>
      <p className="text-xs font-semibold text-foreground">{data.label}</p>
      {data.configSummary && (
        <p className="text-[10px] font-mono text-muted-foreground mt-1 bg-muted/60 p-1 rounded-micro line-clamp-1">
          {data.configSummary}
        </p>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        className="size-2.5 bg-amber-500 border-2 border-background"
      />
    </div>
  );
};

// 3. Custom Node: RAG Knowledge Answer
const RAGKnowledgeNode = ({
  data,
  selected,
}: NodeProps<Node<WorkflowNodeData>>) => {
  const isRunning = data.status === "running";
  return (
    <div
      className={`min-w-[240px] rounded-surface bg-card border-2 p-3 shadow-xs transition-all ${
        isRunning
          ? "border-blue-500 ring-2 ring-blue-500/40 shadow-blue-500/10"
          : selected
            ? "border-primary ring-2 ring-primary/20"
            : "border-blue-500/40 hover:border-blue-500/70"
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="size-2.5 bg-blue-500 border-2 border-background"
      />
      <div className="flex items-center gap-2 mb-1.5">
        <span className="p-1 rounded-micro bg-blue-500/10 text-blue-600 dark:text-blue-400">
          <Search className="size-3.5" />
        </span>
        <span className="text-xs font-bold text-foreground">Hybrid RAG</span>
        <div className="ml-auto flex items-center gap-1">
          <NodeStatusIndicator
            status={data.status}
            durationMs={data.durationMs}
          />
          <Badge variant="outline" className="text-[10px] font-mono">
            qdrant+fts
          </Badge>
        </div>
      </div>
      <p className="text-xs font-semibold text-foreground">{data.label}</p>
      <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground border-t border-border/50 pt-1.5 font-mono">
        <span>Dense 1024D</span>
        <span className="text-primary font-semibold">RRF k=60</span>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="size-2.5 bg-blue-500 border-2 border-background"
      />
    </div>
  );
};

// 4. Custom Node: LLM Core Generate
const LLMGenerateNode = ({
  data,
  selected,
}: NodeProps<Node<WorkflowNodeData>>) => {
  const isRunning = data.status === "running";
  return (
    <div
      className={`min-w-[220px] rounded-surface bg-card border-2 p-3 shadow-xs transition-all ${
        isRunning
          ? "border-purple-500 ring-2 ring-purple-500/40 shadow-purple-500/10"
          : selected
            ? "border-primary ring-2 ring-primary/20"
            : "border-purple-500/40 hover:border-purple-500/70"
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="size-2.5 bg-purple-500 border-2 border-background"
      />
      <div className="flex items-center gap-2 mb-1.5">
        <span className="p-1 rounded-micro bg-purple-500/10 text-purple-600 dark:text-purple-400">
          <Bot className="size-3.5" />
        </span>
        <span className="text-xs font-bold text-foreground">LLM Generate</span>
        <div className="ml-auto flex items-center gap-1">
          <NodeStatusIndicator
            status={data.status}
            durationMs={data.durationMs}
          />
          <Badge variant="outline" className="text-[10px] font-mono">
            core.llm
          </Badge>
        </div>
      </div>
      <p className="text-xs font-semibold text-foreground">{data.label}</p>
      {data.description && (
        <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2">
          {data.description}
        </p>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        className="size-2.5 bg-purple-500 border-2 border-background"
      />
    </div>
  );
};

// 5. Custom Node: Tool API Caller
const ToolNode = ({ data, selected }: NodeProps<Node<WorkflowNodeData>>) => {
  const isRunning = data.status === "running";
  return (
    <div
      className={`min-w-[220px] rounded-surface bg-card border-2 p-3 shadow-xs transition-all ${
        isRunning
          ? "border-cyan-500 ring-2 ring-cyan-500/40 shadow-cyan-500/10"
          : selected
            ? "border-primary ring-2 ring-primary/20"
            : "border-cyan-500/40 hover:border-cyan-500/70"
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="size-2.5 bg-cyan-500 border-2 border-background"
      />
      <div className="flex items-center gap-2 mb-1.5">
        <span className="p-1 rounded-micro bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
          <Wrench className="size-3.5" />
        </span>
        <span className="text-xs font-bold text-foreground">Tool Gateway</span>
        <div className="ml-auto flex items-center gap-1">
          <NodeStatusIndicator
            status={data.status}
            durationMs={data.durationMs}
          />
          <Badge variant="outline" className="text-[10px] font-mono">
            tool.api
          </Badge>
        </div>
      </div>
      <p className="text-xs font-semibold text-foreground">{data.label}</p>
      <Handle
        type="source"
        position={Position.Bottom}
        className="size-2.5 bg-cyan-500 border-2 border-background"
      />
    </div>
  );
};

// 6. Custom Node: Guardrail & Groundedness
const GuardrailNode = ({
  data,
  selected,
}: NodeProps<Node<WorkflowNodeData>>) => {
  const isRunning = data.status === "running";
  return (
    <div
      className={`min-w-[220px] rounded-surface bg-card border-2 p-3 shadow-xs transition-all ${
        isRunning
          ? "border-indigo-500 ring-2 ring-indigo-500/40 shadow-indigo-500/10"
          : selected
            ? "border-primary ring-2 ring-primary/20"
            : "border-indigo-500/40 hover:border-indigo-500/70"
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="size-2.5 bg-indigo-500 border-2 border-background"
      />
      <div className="flex items-center gap-2 mb-1.5">
        <span className="p-1 rounded-micro bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
          <ShieldCheck className="size-3.5" />
        </span>
        <span className="text-xs font-bold text-foreground">
          Citation Guard
        </span>
        <div className="ml-auto flex items-center gap-1">
          <NodeStatusIndicator
            status={data.status}
            durationMs={data.durationMs}
          />
          <Badge variant="outline" className="text-[10px] font-mono">
            guard.citation
          </Badge>
        </div>
      </div>
      <p className="text-xs font-semibold text-foreground">{data.label}</p>
      {data.description && (
        <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2">
          {data.description}
        </p>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        className="size-2.5 bg-indigo-500 border-2 border-background"
      />
    </div>
  );
};

// 7. Custom Node: Human Approval Checkpoint
const HumanApprovalNode = ({
  data,
  selected,
}: NodeProps<Node<WorkflowNodeData>>) => {
  const isWaiting = data.status === "waiting";
  return (
    <div
      className={`min-w-[220px] rounded-surface bg-card border-2 p-3 shadow-xs transition-all ${
        isWaiting
          ? "border-orange-500 ring-2 ring-orange-500/40 shadow-orange-500/10 animate-pulse"
          : selected
            ? "border-primary ring-2 ring-primary/20"
            : "border-orange-500/40 hover:border-orange-500/70"
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="size-2.5 bg-orange-500 border-2 border-background"
      />
      <div className="flex items-center gap-2 mb-1.5">
        <span className="p-1 rounded-micro bg-orange-500/10 text-orange-600 dark:text-orange-400">
          <UserCheck className="size-3.5" />
        </span>
        <span className="text-xs font-bold text-foreground">
          Human Approval
        </span>
        <div className="ml-auto flex items-center gap-1">
          <NodeStatusIndicator
            status={data.status}
            durationMs={data.durationMs}
          />
          <Badge
            variant="outline"
            className="text-[10px] font-mono text-orange-600"
          >
            checkpoint
          </Badge>
        </div>
      </div>
      <p className="text-xs font-semibold text-foreground">{data.label}</p>
      <Handle
        type="source"
        position={Position.Bottom}
        className="size-2.5 bg-orange-500 border-2 border-background"
      />
    </div>
  );
};

// 8. Custom Node: Output
const ChatOutputNode = ({
  data,
  selected,
}: NodeProps<Node<WorkflowNodeData>>) => {
  const isRunning = data.status === "running";
  return (
    <div
      className={`min-w-[220px] rounded-surface bg-card border-2 p-3 shadow-xs transition-all ${
        isRunning
          ? "border-emerald-500 ring-2 ring-emerald-500/40 shadow-emerald-500/10"
          : selected
            ? "border-primary ring-2 ring-primary/20"
            : "border-emerald-500/40 hover:border-emerald-500/70"
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="size-2.5 bg-emerald-500 border-2 border-background"
      />
      <div className="flex items-center gap-2 mb-1.5">
        <span className="p-1 rounded-micro bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
          <Send className="size-3.5" />
        </span>
        <span className="text-xs font-bold text-foreground">Chat Output</span>
        <div className="ml-auto flex items-center gap-1">
          <NodeStatusIndicator
            status={data.status}
            durationMs={data.durationMs}
          />
          <Badge variant="outline" className="text-[10px] font-mono">
            markdown
          </Badge>
        </div>
      </div>
      <p className="text-xs font-semibold text-foreground">{data.label}</p>
      {data.description && (
        <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2">
          {data.description}
        </p>
      )}
    </div>
  );
};

export interface DAGCanvasProps {
  initialNodes: Node<WorkflowNodeData>[];
  initialEdges: Edge[];
  executionStates?: Record<
    string,
    {
      status: "idle" | "running" | "completed" | "waiting" | "failed";
      durationMs?: number;
      error?: string;
    }
  >;
  onNodeSelect?: (node: WorkflowNodeData | null) => void;
  workflowName?: string;
  className?: string;
}

const DEFAULT_EXECUTION_STATES: Record<
  string,
  {
    status: "idle" | "running" | "completed" | "waiting" | "failed";
    durationMs?: number;
    error?: string;
  }
> = {};

const NODE_TYPES = {
  chatInput: ChatInputNode,
  conditionRoute: ConditionRouteNode,
  ragKnowledge: RAGKnowledgeNode,
  llmGenerate: LLMGenerateNode,
  toolCall: ToolNode,
  guardrail: GuardrailNode,
  humanApproval: HumanApprovalNode,
  chatOutput: ChatOutputNode,
};

export const DAGCanvas: React.FC<DAGCanvasProps> = ({
  initialNodes = [],
  initialEdges = [],
  executionStates = DEFAULT_EXECUTION_STATES,
  onNodeSelect,
  workflowName = "QNU Assistant Workflow",
  className,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync initial nodes when workflow changes
  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  // Sync initial edges when workflow changes
  useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  // Merge dynamic executionStates into node data safely
  useEffect(() => {
    if (!executionStates || Object.keys(executionStates).length === 0) {
      return;
    }

    setNodes((prevNodes) =>
      prevNodes.map((node) => {
        const exec = executionStates[node.id];
        if (!exec) return node;
        if (
          node.data.status === exec.status &&
          node.data.durationMs === exec.durationMs &&
          node.data.error === exec.error
        ) {
          return node;
        }
        return {
          ...node,
          data: {
            ...node.data,
            status: exec.status,
            durationMs: exec.durationMs,
            error: exec.error,
          },
        };
      }),
    );
  }, [executionStates, setNodes]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (onNodeSelect) {
        onNodeSelect(node.data as WorkflowNodeData);
      }
    },
    [onNodeSelect],
  );

  const handlePaneClick = useCallback(() => {
    if (onNodeSelect) {
      onNodeSelect(null);
    }
  }, [onNodeSelect]);

  return (
    <div className={`w-full h-full relative min-h-[500px] ${className || ""}`}>
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          onPaneClick={handlePaneClick}
          nodeTypes={NODE_TYPES}
          fitView
          fitViewOptions={{ padding: 0.25 }}
          minZoom={0.3}
          maxZoom={1.8}
          defaultEdgeOptions={{
            animated: true,
            style: { strokeWidth: 2, stroke: "var(--primary)" },
          }}
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
          <Controls
            showInteractive={false}
            className="bg-card border border-border shadow-xs"
          />
          <MiniMap
            zoomable
            pannable
            className="bg-card border border-border rounded-surface shadow-xs"
            nodeColor={(node) => {
              switch (node.type) {
                case "chatInput":
                  return "#14b8a6";
                case "conditionRoute":
                  return "#f59e0b";
                case "ragKnowledge":
                  return "#3b82f6";
                case "llmGenerate":
                  return "#a855f7";
                case "toolCall":
                  return "#06b6d4";
                case "guardrail":
                  return "#6366f1";
                case "humanApproval":
                  return "#f97316";
                case "chatOutput":
                  return "#10b981";
                default:
                  return "#64748b";
              }
            }}
          />

          <Panel position="top-left" className="m-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-control bg-card/90 backdrop-blur-xs border border-border shadow-xs text-xs">
              <Layers className="size-3.5 text-primary" />
              <span className="font-semibold text-foreground">
                {workflowName}
              </span>
              <span className="text-muted-foreground">•</span>
              <span className="text-muted-foreground font-mono">
                {nodes.length} nodes, {edges.length} edges
              </span>
            </div>
          </Panel>

          <Panel position="bottom-left" className="m-3">
            <div className="flex flex-wrap items-center gap-3 px-3 py-1.5 rounded-control bg-card/90 backdrop-blur-xs border border-border shadow-xs text-[11px] text-muted-foreground">
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-teal-500" /> Input
              </span>
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-amber-500" /> Route
              </span>
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-blue-500" /> RAG
              </span>
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-purple-500" /> LLM
              </span>
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-cyan-500" /> Tool
              </span>
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-indigo-500" /> Guard
              </span>
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-orange-500" /> Approval
              </span>
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-emerald-500" /> Output
              </span>
            </div>
          </Panel>
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
};
