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
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import { GitBranch, Layers, MessageSquare, Search, Send, ShieldCheck } from "lucide-react";
import type React from "react";
import { useCallback, useMemo } from "react";
import { Badge } from "../ui/badge";

export interface WorkflowNodeData {
  id: string;
  label: string;
  category: "input" | "route" | "rag" | "guard" | "output";
  description?: string;
  configSummary?: string;
  timeoutSeconds?: number;
  [key: string]: unknown;
}

// 1. Custom Node: Input
const ChatInputNode = ({ data, selected }: NodeProps<Node<WorkflowNodeData>>) => {
  return (
    <div
      className={`min-w-[220px] rounded-surface bg-card border-2 p-3 shadow-sm transition-all ${
        selected ? "border-primary ring-2 ring-primary/20" : "border-teal-500/40"
      }`}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="p-1 rounded-micro bg-teal-500/10 text-teal-600 dark:text-teal-400">
          <MessageSquare className="h-3.5 w-3.5" />
        </span>
        <span className="text-xs font-bold text-foreground">Chat Input</span>
        <Badge variant="outline" className="text-[10px] ml-auto font-mono">
          input.chat
        </Badge>
      </div>
      <p className="text-xs font-semibold text-foreground">{data.label}</p>
      {data.description && (
        <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2">{data.description}</p>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2.5 h-2.5 bg-teal-500 border-2 border-background"
      />
    </div>
  );
};

// 2. Custom Node: Route
const ConditionRouteNode = ({ data, selected }: NodeProps<Node<WorkflowNodeData>>) => {
  return (
    <div
      className={`min-w-[220px] rounded-surface bg-card border-2 p-3 shadow-sm transition-all ${
        selected ? "border-primary ring-2 ring-primary/20" : "border-amber-500/40"
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="w-2.5 h-2.5 bg-amber-500 border-2 border-background"
      />
      <div className="flex items-center gap-2 mb-1.5">
        <span className="p-1 rounded-micro bg-amber-500/10 text-amber-600 dark:text-amber-400">
          <GitBranch className="h-3.5 w-3.5" />
        </span>
        <span className="text-xs font-bold text-foreground">Intent Route</span>
        <Badge variant="outline" className="text-[10px] ml-auto font-mono">
          condition.route
        </Badge>
      </div>
      <p className="text-xs font-semibold text-foreground">{data.label}</p>
      {data.configSummary && (
        <p className="text-[10px] font-mono text-muted-foreground mt-1 bg-muted/60 p-1 rounded-micro">
          {data.configSummary}
        </p>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2.5 h-2.5 bg-amber-500 border-2 border-background"
      />
    </div>
  );
};

// 3. Custom Node: RAG Knowledge Answer
const RAGKnowledgeNode = ({ data, selected }: NodeProps<Node<WorkflowNodeData>>) => {
  return (
    <div
      className={`min-w-[240px] rounded-surface bg-card border-2 p-3 shadow-sm transition-all ${
        selected ? "border-primary ring-2 ring-primary/20" : "border-blue-500/50"
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="w-2.5 h-2.5 bg-blue-500 border-2 border-background"
      />
      <div className="flex items-center gap-2 mb-1.5">
        <span className="p-1 rounded-micro bg-blue-500/10 text-blue-600 dark:text-blue-400">
          <Search className="h-3.5 w-3.5" />
        </span>
        <span className="text-xs font-bold text-foreground">Hybrid RAG</span>
        <Badge variant="outline" className="text-[10px] ml-auto font-mono">
          rag_fast
        </Badge>
      </div>
      <p className="text-xs font-semibold text-foreground">{data.label}</p>
      <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground border-t border-border/50 pt-1.5">
        <span>Qdrant + FTS</span>
        <span className="font-mono text-primary">RRF k=60</span>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2.5 h-2.5 bg-blue-500 border-2 border-background"
      />
    </div>
  );
};

// 4. Custom Node: Guardrail & Human Approval
const GuardrailNode = ({ data, selected }: NodeProps<Node<WorkflowNodeData>>) => {
  return (
    <div
      className={`min-w-[220px] rounded-surface bg-card border-2 p-3 shadow-sm transition-all ${
        selected ? "border-primary ring-2 ring-primary/20" : "border-purple-500/50"
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="w-2.5 h-2.5 bg-purple-500 border-2 border-background"
      />
      <div className="flex items-center gap-2 mb-1.5">
        <span className="p-1 rounded-micro bg-purple-500/10 text-purple-600 dark:text-purple-400">
          <ShieldCheck className="h-3.5 w-3.5" />
        </span>
        <span className="text-xs font-bold text-foreground">Citation Guard</span>
        <Badge variant="outline" className="text-[10px] ml-auto font-mono">
          groundedness
        </Badge>
      </div>
      <p className="text-xs font-semibold text-foreground">{data.label}</p>
      {data.description && (
        <p className="text-[11px] text-muted-foreground mt-1">{data.description}</p>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2.5 h-2.5 bg-purple-500 border-2 border-background"
      />
    </div>
  );
};

// 5. Custom Node: Output
const ChatOutputNode = ({ data, selected }: NodeProps<Node<WorkflowNodeData>>) => {
  return (
    <div
      className={`min-w-[220px] rounded-surface bg-card border-2 p-3 shadow-sm transition-all ${
        selected ? "border-primary ring-2 ring-primary/20" : "border-emerald-500/50"
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="w-2.5 h-2.5 bg-emerald-500 border-2 border-background"
      />
      <div className="flex items-center gap-2 mb-1.5">
        <span className="p-1 rounded-micro bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
          <Send className="h-3.5 w-3.5" />
        </span>
        <span className="text-xs font-bold text-foreground">Chat Output</span>
        <Badge variant="outline" className="text-[10px] ml-auto font-mono">
          markdown
        </Badge>
      </div>
      <p className="text-xs font-semibold text-foreground">{data.label}</p>
      {data.description && (
        <p className="text-[11px] text-muted-foreground mt-1">{data.description}</p>
      )}
    </div>
  );
};

export interface DAGCanvasProps {
  initialNodes: Node<WorkflowNodeData>[];
  initialEdges: Edge[];
  onNodeSelect?: (node: WorkflowNodeData | null) => void;
  workflowName?: string;
  className?: string;
}

export const DAGCanvas: React.FC<DAGCanvasProps> = ({
  initialNodes,
  initialEdges,
  onNodeSelect,
  workflowName = "QNU Assistant Workflow",
  className,
}) => {
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const nodeTypes = useMemo(
    () => ({
      chatInput: ChatInputNode,
      conditionRoute: ConditionRouteNode,
      ragKnowledge: RAGKnowledgeNode,
      guardrail: GuardrailNode,
      chatOutput: ChatOutputNode,
    }),
    []
  );

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (onNodeSelect) {
        onNodeSelect(node.data as WorkflowNodeData);
      }
    },
    [onNodeSelect]
  );

  const handlePaneClick = useCallback(() => {
    if (onNodeSelect) {
      onNodeSelect(null);
    }
  }, [onNodeSelect]);

  return (
    <div className={`w-full h-full relative ${className || ""}`}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        nodeTypes={nodeTypes}
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
        <Controls showInteractive={false} className="bg-card border border-border shadow-xs" />
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
              case "guardrail":
                return "#a855f7";
              case "chatOutput":
                return "#10b981";
              default:
                return "#64748b";
            }
          }}
        />

        <Panel position="top-left" className="m-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-control bg-card/90 backdrop-blur-xs border border-border shadow-xs text-xs">
            <Layers className="h-3.5 w-3.5 text-primary" />
            <span className="font-semibold text-foreground">{workflowName}</span>
            <span className="text-muted-foreground">•</span>
            <span className="text-muted-foreground font-mono">
              {nodes.length} nodes, {edges.length} edges
            </span>
          </div>
        </Panel>

        <Panel position="bottom-left" className="m-3">
          <div className="flex items-center gap-3 px-3 py-1.5 rounded-control bg-card/90 backdrop-blur-xs border border-border shadow-xs text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-teal-500" /> Input
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-amber-500" /> Route
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-blue-500" /> RAG
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-purple-500" /> Guard
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-emerald-500" /> Output
            </span>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};
