import { ArrowRight, Check, Copy } from "lucide-react";
import type React from "react";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { getNodeCategoryLabel } from "@/services/node-catalog-api";
import type { NodeManifest } from "@/types/common";
import { NodeCategoryIcon } from "./node-icon";

interface NodeCatalogCardProps {
  node: NodeManifest;
  onSelect: (nodeType: string) => void;
}

function countSchemaProperties(
  schema: Record<string, unknown> | undefined,
): number {
  if (!schema || typeof schema !== "object") return 0;
  const props = schema.properties;
  if (!props || typeof props !== "object" || Array.isArray(props)) return 0;
  return Object.keys(props).length;
}

export function NodeCatalogCard({ node, onSelect }: NodeCatalogCardProps) {
  const [copied, setCopied] = useState(false);

  const inputCount = countSchemaProperties(node.input_schema);
  const outputCount = countSchemaProperties(node.output_schema);
  const configCount = countSchemaProperties(node.config_schema);

  const handleCopySpec = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(JSON.stringify(node, null, 2));
    setCopied(true);
    toast.success(`Đã sao chép manifest '${node.type}'`);
    setTimeout(() => setCopied(false), 1600);
  };

  return (
    <Card
      onClick={() => onSelect(node.type)}
      className="group flex flex-col h-full overflow-hidden transition-all duration-200 border-border/70 hover:border-primary/50 hover:shadow-xs cursor-pointer"
    >
      <CardHeader className="p-4 pb-2.5 space-y-3">
        {/* Top: Category Icon + Badges */}
        <div className="flex items-start justify-between gap-2.5">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary transition-transform group-hover:scale-105">
            <NodeCategoryIcon category={node.category} className="size-4.5" />
          </div>

          <div className="flex flex-wrap items-center justify-end gap-1.5">
            <Badge
              variant="outline"
              className="text-[10px] font-normal px-1.5 py-0.5"
            >
              {getNodeCategoryLabel(node.category)}
            </Badge>
            <Badge
              variant={node.status === "active" ? "default" : "secondary"}
              className="text-[10px] px-1.5 py-0.5 capitalize flex items-center gap-1"
            >
              <span
                className={`size-1.5 rounded-full ${
                  node.status === "active"
                    ? "bg-emerald-400"
                    : "bg-muted-foreground"
                }`}
              />
              {node.status}
            </Badge>
          </div>
        </div>

        {/* Title & Type identifier */}
        <div className="space-y-1">
          <h3 className="text-xs sm:text-sm font-semibold text-foreground line-clamp-1 group-hover:text-primary transition-colors">
            {node.display_name}
          </h3>
          <div className="flex items-center gap-1.5">
            <code className="text-[11px] font-mono text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded-xs truncate max-w-full">
              {node.type}@{node.version}
            </code>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col flex-1 p-4 pt-1 gap-3.5 justify-between">
        {/* Description */}
        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed min-h-8">
          {node.description}
        </p>

        {/* Telemetry I/O metrics strip */}
        <div className="grid grid-cols-3 gap-1 rounded-md bg-muted/40 p-2 text-center text-[11px] border border-border/40">
          <div>
            <div className="font-semibold text-foreground">{inputCount}</div>
            <div className="text-[10px] text-muted-foreground">Đầu vào</div>
          </div>
          <div className="border-x border-border/50">
            <div className="font-semibold text-foreground">{outputCount}</div>
            <div className="text-[10px] text-muted-foreground">Đầu ra</div>
          </div>
          <div>
            <div className="font-semibold text-foreground">{configCount}</div>
            <div className="text-[10px] text-muted-foreground">Cấu hình</div>
          </div>
        </div>

        {/* Actions footer */}
        <div className="flex items-center gap-2 pt-0.5">
          <Button
            size="sm"
            variant="outline"
            className="flex-1 h-8 text-xs font-medium justify-between group-hover:border-primary group-hover:bg-primary/5"
            onClick={(e) => {
              e.stopPropagation();
              onSelect(node.type);
            }}
          >
            <span>Chi tiết</span>
            <ArrowRight className="size-3.5 text-muted-foreground group-hover:text-primary transition-transform group-hover:translate-x-0.5" />
          </Button>

          <Button
            size="icon"
            variant="ghost"
            className="size-8 text-muted-foreground hover:text-foreground shrink-0"
            title="Sao chép JSON Manifest"
            onClick={handleCopySpec}
          >
            {copied ? (
              <Check className="size-3.5 text-emerald-500" />
            ) : (
              <Copy className="size-3.5" />
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
