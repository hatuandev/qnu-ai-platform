import { ArrowRight, Cpu, Layers } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { getNodeCategoryLabel } from "@/services/node-catalog-api";
import type { NodeManifest } from "@/types/common";
import { NodeCategoryIcon } from "./node-icon";

interface NodePinoutDiagramProps {
  node: NodeManifest;
}

export function NodePinoutDiagram({ node }: NodePinoutDiagramProps) {
  const inputProps = Object.keys(
    (node.input_schema?.properties as Record<string, unknown>) || {},
  );
  const outputProps = Object.keys(
    (node.output_schema?.properties as Record<string, unknown>) || {},
  );
  const configProps = Object.keys(
    (node.config_schema?.properties as Record<string, unknown>) || {},
  );

  return (
    <Card className="border-border/70 overflow-hidden bg-card/60 backdrop-blur-xs">
      <CardContent className="p-4 sm:p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-border/50 pb-3">
          <div className="flex items-center gap-2">
            <Layers className="size-4 text-primary" />
            <h4 className="text-xs font-semibold text-foreground">
              Sơ Đồ Ghép Nối Chân Cắm (Pinout DAG)
            </h4>
          </div>
          <Badge variant="outline" className="text-[10px] font-mono">
            {node.api_version}
          </Badge>
        </div>

        {/* Pinout Visual Canvas */}
        <div className="relative rounded-lg border border-border/60 bg-muted/20 p-4 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-7 gap-3 items-center">
            {/* Input Pins (Left 2 cols on md) */}
            <div className="md:col-span-2 space-y-1.5 order-1 md:order-1">
              <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center justify-between">
                <span>Cổng Đầu Vào</span>
                <span className="text-[10px] font-mono">
                  ({inputProps.length})
                </span>
              </div>
              {inputProps.length === 0 ? (
                <div className="text-[11px] italic text-muted-foreground bg-muted/40 p-2 rounded-sm text-center">
                  Không yêu cầu input
                </div>
              ) : (
                inputProps.map((port) => (
                  <div
                    key={port}
                    className="flex items-center justify-between gap-1.5 p-1.5 rounded-sm bg-background border border-border/70 text-xs shadow-2xs group hover:border-primary/50 transition-colors"
                  >
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="size-2 rounded-full bg-cyan-500 shrink-0" />
                      <span className="font-mono text-[11px] text-foreground truncate">
                        {port}
                      </span>
                    </div>
                    <ArrowRight className="size-3 text-muted-foreground shrink-0 group-hover:text-primary transition-colors" />
                  </div>
                ))
              )}
            </div>

            {/* Processor Core (Center 3 cols on md) */}
            <div className="md:col-span-3 flex flex-col items-center justify-center p-4 rounded-xl bg-card border-2 border-primary/30 shadow-xs space-y-2 order-2 md:order-2">
              <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <NodeCategoryIcon category={node.category} className="size-5" />
              </div>
              <div className="text-center space-y-0.5">
                <div className="text-xs font-bold text-foreground">
                  {node.display_name}
                </div>
                <code className="text-[10px] font-mono text-muted-foreground block">
                  {node.type}
                </code>
              </div>
              <div className="flex items-center gap-1 pt-1">
                <Badge variant="outline" className="text-[9px] px-1 py-0">
                  {getNodeCategoryLabel(node.category)}
                </Badge>
                <Badge variant="default" className="text-[9px] px-1 py-0">
                  v{node.version}
                </Badge>
              </div>
            </div>

            {/* Output Pins (Right 2 cols on md) */}
            <div className="md:col-span-2 space-y-1.5 order-3 md:order-3">
              <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center justify-between">
                <span>Cổng Đầu Ra</span>
                <span className="text-[10px] font-mono">
                  ({outputProps.length})
                </span>
              </div>
              {outputProps.length === 0 ? (
                <div className="text-[11px] italic text-muted-foreground bg-muted/40 p-2 rounded-sm text-center">
                  Không sinh output
                </div>
              ) : (
                outputProps.map((port) => (
                  <div
                    key={port}
                    className="flex items-center justify-between gap-1.5 p-1.5 rounded-sm bg-background border border-border/70 text-xs shadow-2xs group hover:border-primary/50 transition-colors"
                  >
                    <ArrowRight className="size-3 text-muted-foreground shrink-0 group-hover:text-primary transition-colors" />
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="font-mono text-[11px] text-foreground truncate">
                        {port}
                      </span>
                      <span className="size-2 rounded-full bg-emerald-500 shrink-0" />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Configuration summary bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-md bg-muted/40 border border-border/50 text-xs">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Cpu className="size-3.5 text-primary" />
            <span>Tham số cấu hình DAG:</span>
            <strong className="text-foreground">
              {configProps.length} thuộc tính
            </strong>
          </div>
          <div className="flex flex-wrap gap-1">
            {configProps.slice(0, 3).map((prop) => (
              <code
                key={prop}
                className="text-[10px] font-mono bg-background px-1.5 py-0.5 rounded-xs border border-border/60"
              >
                {prop}
              </code>
            ))}
            {configProps.length > 3 && (
              <span className="text-[10px] text-muted-foreground">
                +{configProps.length - 3} nữa
              </span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
