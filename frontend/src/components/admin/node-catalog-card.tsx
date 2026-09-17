import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { NodeManifest } from "@/services/api-client";
import { CheckCircle2, Eye, Network } from "lucide-react";

interface NodeCatalogCardProps {
  node: NodeManifest;
  categoryLabel: string;
  onInspect: (node: NodeManifest) => void;
}

function countSchemaProperties(schema: Record<string, unknown>): number {
  const properties = schema.properties;
  if (!properties || typeof properties !== "object" || Array.isArray(properties)) {
    return 0;
  }
  return Object.keys(properties).length;
}

export function NodeCatalogCard({ node, categoryLabel, onInspect }: NodeCatalogCardProps) {
  const inputCount = countSchemaProperties(node.input_schema);
  const outputCount = countSchemaProperties(node.output_schema);
  const configCount = countSchemaProperties(node.config_schema);

  return (
    <Card className="group flex h-full flex-col overflow-hidden transition-colors hover:border-primary/50">
      <CardHeader className="space-y-3 p-5 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Network className="size-5" />
          </div>
          <div className="flex flex-wrap justify-end gap-1.5">
            <Badge variant="outline">{categoryLabel}</Badge>
            <Badge variant={node.status === "active" ? "success" : "warning"}>
              <CheckCircle2 className="mr-1 size-3" />
              {node.status}
            </Badge>
          </div>
        </div>
        <div className="space-y-1">
          <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-foreground">
            {node.display_name}
          </h3>
          <code className="block truncate rounded-md bg-muted px-2 py-1 font-mono text-[11px] text-muted-foreground">
            {node.type}@{node.version}
          </code>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-4 p-5 pt-0">
        <p className="line-clamp-3 min-h-14 text-xs leading-relaxed text-muted-foreground">
          {node.description}
        </p>
        <div className="mt-auto grid grid-cols-3 gap-2 border-y border-border/60 py-3 text-center text-[11px]">
          <div>
            <div className="font-semibold text-foreground">{inputCount}</div>
            <div className="text-muted-foreground">Input</div>
          </div>
          <div>
            <div className="font-semibold text-foreground">{outputCount}</div>
            <div className="text-muted-foreground">Output</div>
          </div>
          <div>
            <div className="font-semibold text-foreground">{configCount}</div>
            <div className="text-muted-foreground">Config</div>
          </div>
        </div>
        <Button variant="outline" size="sm" className="w-full" onClick={() => onInspect(node)}>
          <Eye className="mr-1.5 size-3.5" />
          Xem Manifest & Schema
        </Button>
      </CardContent>
    </Card>
  );
}
