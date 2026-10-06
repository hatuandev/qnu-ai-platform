import { useNavigate } from "@tanstack/react-router";
import { ArrowRight, BookOpen, Clock, Settings2, X } from "lucide-react";
import type { WorkflowNodeData } from "@/components/ai/dag-canvas";
import { NodeCategoryIcon } from "@/components/capabilities/nodes/node-icon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getNodeCategoryLabel } from "@/services/node-catalog-api";

interface AssistantWorkflowNodeInspectorProps {
  node: WorkflowNodeData | null;
  onClose: () => void;
}

export function AssistantWorkflowNodeInspector({
  node,
  onClose,
}: AssistantWorkflowNodeInspectorProps) {
  const navigate = useNavigate();

  if (!node) return null;

  const nodeType = (node.nodeType as string) || node.id;
  const config = (node.config as Record<string, unknown>) || {};
  const configEntries = Object.entries(config);

  const handleOpenCatalog = () => {
    void navigate({
      to: "/capabilities/nodes/$nodeType",
      params: { nodeType },
    });
  };

  return (
    <Card className="absolute top-3 right-3 bottom-3 w-80 sm:w-96 z-10 flex flex-col border-border/80 bg-card/95 backdrop-blur-md shadow-lg overflow-hidden animate-in fade-in slide-in-from-right-4 duration-200">
      {/* Header */}
      <CardHeader className="p-3.5 border-b border-border/60 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
              <NodeCategoryIcon category={node.category} className="size-4" />
            </div>
            <div className="min-w-0">
              <CardTitle className="text-xs sm:text-sm font-semibold text-foreground truncate">
                {node.label}
              </CardTitle>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="font-mono text-[10px] text-muted-foreground truncate">
                  {nodeType}
                </span>
                {Boolean(node.version) && (
                  <Badge variant="outline" className="text-[9px] px-1 py-0">
                    v{String(node.version)}
                  </Badge>
                )}
              </div>
            </div>
          </div>

          <Button
            variant="ghost"
            size="icon"
            className="size-7 rounded-sm text-muted-foreground hover:text-foreground shrink-0"
            onClick={onClose}
            aria-label="Đóng bảng chi tiết"
          >
            <X className="size-3.5" />
          </Button>
        </div>

        <div className="flex items-center gap-1.5">
          <Badge variant="outline" className="text-[10px]">
            {getNodeCategoryLabel(node.category)}
          </Badge>
          {node.status && (
            <Badge
              variant={node.status === "completed" ? "default" : "secondary"}
              className="text-[10px] capitalize"
            >
              {node.status}
            </Badge>
          )}
        </div>
      </CardHeader>

      {/* Body Content */}
      <CardContent className="flex-1 overflow-y-auto p-3.5 space-y-4 text-xs">
        {/* Description */}
        {node.description && (
          <div className="space-y-1">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
              Mô tả nhiệm vụ
            </span>
            <p className="text-foreground leading-relaxed text-xs bg-muted/30 p-2.5 rounded-md border border-border/40">
              {node.description}
            </p>
          </div>
        )}

        {/* Configuration summary */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <Settings2 className="size-3 text-primary" />
              <span>Cấu hình tĩnh (Config)</span>
            </span>
            <span className="font-mono text-[10px]">
              ({configEntries.length})
            </span>
          </div>

          {configEntries.length === 0 ? (
            <p className="text-[11px] italic text-muted-foreground bg-muted/20 p-2 rounded-sm text-center">
              Node không yêu cầu cấu hình riêng.
            </p>
          ) : (
            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
              {configEntries.map(([key, val]) => (
                <div
                  key={key}
                  className="p-2 rounded-md bg-muted/40 border border-border/50 text-[11px] space-y-0.5"
                >
                  <span className="font-mono font-medium text-foreground block">
                    {key}:
                  </span>
                  <div className="font-mono text-muted-foreground text-[10px] break-all max-h-24 overflow-y-auto">
                    {typeof val === "object"
                      ? JSON.stringify(val, null, 2)
                      : String(val)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Execution policy */}
        {Boolean(node.policy) && (
          <div className="space-y-1.5 pt-1 border-t border-border/40">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="size-3 text-primary" />
              <span>Chính sách thực thi</span>
            </span>
            <div className="grid grid-cols-2 gap-1.5 text-[11px]">
              <div className="p-2 rounded-md bg-muted/30 border border-border/40">
                <span className="text-muted-foreground block text-[10px]">
                  Timeout:
                </span>
                <span className="font-mono font-semibold text-foreground">
                  {String(
                    (node.policy as Record<string, unknown>).timeout_seconds ??
                      "Mặc định",
                  )}
                  s
                </span>
              </div>
              <div className="p-2 rounded-md bg-muted/30 border border-border/40">
                <span className="text-muted-foreground block text-[10px]">
                  Số lần thử:
                </span>
                <span className="font-mono font-semibold text-foreground">
                  {String(
                    (node.policy as Record<string, unknown>).max_attempts ?? 1,
                  )}
                </span>
              </div>
            </div>
          </div>
        )}
      </CardContent>

      {/* Footer Actions */}
      <div className="p-3 border-t border-border/60 bg-muted/20 flex items-center justify-between gap-2">
        <Button
          variant="outline"
          size="sm"
          className="w-full h-8 text-xs gap-1.5 font-medium"
          onClick={handleOpenCatalog}
        >
          <BookOpen className="size-3.5 text-primary" />
          <span>Xem đặc tả Node Core</span>
          <ArrowRight className="size-3 ml-auto text-muted-foreground" />
        </Button>
      </div>
    </Card>
  );
}
