import { type Edge, MarkerType, type Node } from "@xyflow/react";
import type { WorkflowDagSpec } from "@/services/workflows-api";
import type { WorkflowNodeData } from "./dag-canvas";

export type CanvasNodeKind =
  | "chatInput"
  | "conditionRoute"
  | "ragKnowledge"
  | "llmGenerate"
  | "toolCall"
  | "guardrail"
  | "humanApproval"
  | "chatOutput";

/**
 * Maps a QNU Core node type string (e.g. "input.chat", "query.rewrite", "guard.citation")
 * to the corresponding custom ReactFlow component node kind.
 */
export function toCanvasNodeKind(nodeType: string): CanvasNodeKind {
  const t = nodeType.toLowerCase();
  if (t.startsWith("input.") || t.includes("chat_input")) return "chatInput";
  if (
    t.startsWith("condition.") ||
    t.startsWith("routing.") ||
    t.includes("route") ||
    t.includes("router")
  ) {
    return "conditionRoute";
  }
  if (
    t.startsWith("rag.") ||
    t.includes("retrieval") ||
    t.includes("fusion") ||
    t.includes("knowledge")
  ) {
    return "ragKnowledge";
  }
  if (
    t.startsWith("guard.") ||
    t.includes("citation") ||
    t.includes("mask") ||
    t.includes("injection")
  ) {
    return "guardrail";
  }
  if (
    t.startsWith("tool.") ||
    t.includes("api_caller") ||
    t.includes("tool_call")
  ) {
    return "toolCall";
  }
  if (
    t.startsWith("control.") ||
    t.includes("human_approval") ||
    t.includes("checkpoint")
  ) {
    return "humanApproval";
  }
  if (
    t.startsWith("output.") ||
    t.includes("chat_output") ||
    t.includes("no_answer")
  ) {
    return "chatOutput";
  }
  return "llmGenerate";
}

/**
 * Maps a canvas node kind to a category key for theming and metrics.
 */
export function toNodeCategory(
  nodeKind: CanvasNodeKind,
): WorkflowNodeData["category"] {
  const mapping: Record<CanvasNodeKind, WorkflowNodeData["category"]> = {
    chatInput: "input",
    conditionRoute: "route",
    ragKnowledge: "rag",
    llmGenerate: "llm",
    toolCall: "tool",
    guardrail: "guard",
    humanApproval: "human",
    chatOutput: "output",
  };
  return mapping[nodeKind] ?? "llm";
}

/**
 * Safely extracts the string node_id from an endpoint (which can be a string or { node_id, port }).
 */
export function extractNodeId(endpoint: unknown): string {
  if (!endpoint) return "";
  if (typeof endpoint === "string") return endpoint;
  if (typeof endpoint === "object" && endpoint !== null) {
    if (
      "node_id" in endpoint &&
      typeof (endpoint as { node_id?: unknown }).node_id === "string"
    ) {
      return (endpoint as { node_id: string }).node_id;
    }
    if (
      "id" in endpoint &&
      typeof (endpoint as { id?: unknown }).id === "string"
    ) {
      return (endpoint as { id: string }).id;
    }
  }
  return String(endpoint);
}

/**
 * Safely extracts the port name from an endpoint or edge fallback.
 */
export function extractPort(
  endpoint: unknown,
  fallbackPort?: string | null,
): string | undefined {
  if (
    typeof endpoint === "object" &&
    endpoint !== null &&
    "port" in endpoint &&
    typeof (endpoint as { port?: unknown }).port === "string"
  ) {
    return (endpoint as { port: string }).port;
  }
  return fallbackPort || undefined;
}

/**
 * Computes deterministic (x, y) coordinates for all nodes in a DAG without overlap.
 * Uses topological ranking / longest-path leveling to arrange nodes in clean tiers.
 */
export function computeDagLayout(
  dagSpec: WorkflowDagSpec,
  direction: "TB" | "LR" = "TB",
): Map<string, { x: number; y: number }> {
  const nodeIds = new Set(dagSpec.nodes.map((n) => n.id));
  const inDegree = new Map<string, number>();
  const adjacency = new Map<string, string[]>();

  for (const n of dagSpec.nodes) {
    inDegree.set(n.id, 0);
    adjacency.set(n.id, []);
  }

  for (const edge of dagSpec.edges) {
    const srcId = extractNodeId(edge.source);
    const tgtId = extractNodeId(edge.target);
    if (nodeIds.has(srcId) && nodeIds.has(tgtId)) {
      inDegree.set(tgtId, (inDegree.get(tgtId) || 0) + 1);
      adjacency.get(srcId)?.push(tgtId);
    }
  }

  // 1. Assign ranks (depth tiers)
  const ranks = new Map<string, number>();

  // Start with entry node or all nodes with inDegree === 0
  const roots: string[] = [];
  if (dagSpec.entry_node_id && nodeIds.has(dagSpec.entry_node_id)) {
    roots.push(dagSpec.entry_node_id);
  }
  for (const [id, deg] of inDegree) {
    if (deg === 0 && !roots.includes(id)) {
      roots.push(id);
    }
  }

  // Topological BFS queue
  const queue: { id: string; rank: number }[] = roots.map((id) => ({
    id,
    rank: 0,
  }));
  for (const root of roots) {
    ranks.set(root, 0);
  }

  while (queue.length > 0) {
    const curr = queue.shift();
    if (!curr) break;
    const children = adjacency.get(curr.id) || [];
    for (const childId of children) {
      const nextRank = curr.rank + 1;
      const existingRank = ranks.get(childId) ?? -1;
      if (nextRank > existingRank) {
        ranks.set(childId, nextRank);
        queue.push({ id: childId, rank: nextRank });
      }
    }
  }

  // Fallback for any unvisited nodes
  for (const n of dagSpec.nodes) {
    if (!ranks.has(n.id)) {
      ranks.set(n.id, 0);
    }
  }

  // 2. Group nodes by rank level
  const rankGroups = new Map<number, string[]>();
  for (const [id, rank] of ranks) {
    const list = rankGroups.get(rank) || [];
    list.push(id);
    rankGroups.set(rank, list);
  }

  // Find max columns to center all rows
  let maxColCount = 1;
  for (const list of rankGroups.values()) {
    if (list.length > maxColCount) {
      maxColCount = list.length;
    }
  }

  const positions = new Map<string, { x: number; y: number }>();
  const nodeSpacingX = 270;
  const nodeSpacingY = 155;
  const startX = 60;
  const startY = 40;

  // 3. Calculate balanced coordinates
  if (direction === "TB") {
    for (const [rank, nodeIdsInRank] of rankGroups) {
      const count = nodeIdsInRank.length;
      const rowWidth = (count - 1) * nodeSpacingX;
      const maxWidth = (maxColCount - 1) * nodeSpacingX;
      const offsetLeft = Math.max(0, (maxWidth - rowWidth) / 2);

      nodeIdsInRank.forEach((nodeId, index) => {
        positions.set(nodeId, {
          x: startX + offsetLeft + index * nodeSpacingX,
          y: startY + rank * nodeSpacingY,
        });
      });
    }
  } else {
    // Left-to-Right layout
    for (const [rank, nodeIdsInRank] of rankGroups) {
      const count = nodeIdsInRank.length;
      const colHeight = (count - 1) * nodeSpacingY;
      const maxHeight = (maxColCount - 1) * nodeSpacingY;
      const offsetTop = Math.max(0, (maxHeight - colHeight) / 2);

      nodeIdsInRank.forEach((nodeId, index) => {
        positions.set(nodeId, {
          x: startX + rank * 320,
          y: startY + offsetTop + index * nodeSpacingY,
        });
      });
    }
  }

  return positions;
}

/**
 * Converts a raw backend WorkflowDagSpec into ReactFlow nodes and edges.
 */
export function convertDagSpecToReactFlow(
  dagSpec: WorkflowDagSpec,
  executionStates?: Record<
    string,
    {
      status: "idle" | "running" | "completed" | "waiting" | "failed";
      durationMs?: number;
      error?: string;
    }
  >,
  direction: "TB" | "LR" = "TB",
): { nodes: Node<WorkflowNodeData>[]; edges: Edge[] } {
  const positions = computeDagLayout(dagSpec, direction);

  const nodes: Node<WorkflowNodeData>[] = dagSpec.nodes.map((node) => {
    const nodeKind = toCanvasNodeKind(node.type);
    const category = toNodeCategory(nodeKind);
    const exec = executionStates?.[node.id];

    return {
      id: node.id,
      type: nodeKind,
      position: positions.get(node.id) ?? { x: 80, y: 40 },
      data: {
        id: node.id,
        label: node.display_name || node.id,
        category,
        nodeType: node.type,
        version: node.version,
        config: node.config,
        policy: node.policy,
        description:
          typeof node.policy.description === "string"
            ? node.policy.description
            : undefined,
        status: exec?.status || "idle",
        durationMs: exec?.durationMs,
        error: exec?.error,
      },
    };
  });

  const edges: Edge[] = dagSpec.edges.map((edge, index) => {
    const srcId = extractNodeId(edge.source);
    const tgtId = extractNodeId(edge.target);
    const srcPort = extractPort(edge.source, edge.source_port);

    const hasLabel = Boolean(
      edge.label ||
        (srcPort &&
          srcPort !== "message" &&
          srcPort !== "output" &&
          srcPort !== "response"),
    );
    const labelText = edge.label || (hasLabel ? srcPort : undefined);

    return {
      id: edge.id || `edge-${srcId}-${tgtId}-${index}`,
      source: srcId,
      target: tgtId,
      animated: true,
      label: labelText,
      labelStyle: {
        fontSize: 10,
        fontFamily: "monospace",
        fill: "var(--foreground)",
      },
      labelBgStyle: {
        fill: "var(--card)",
        stroke: "var(--border)",
        strokeWidth: 1,
        rx: 4,
        ry: 4,
      },
      labelBgPadding: [6, 3],
      style: {
        strokeWidth: 1.75,
        stroke: "var(--primary)",
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 14,
        height: 14,
        color: "var(--primary)",
      },
    };
  });

  return { nodes, edges };
}
