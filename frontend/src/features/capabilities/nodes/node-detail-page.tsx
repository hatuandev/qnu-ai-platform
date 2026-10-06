import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  Bot,
  Check,
  CheckCircle2,
  Code2,
  Copy,
  GitBranch,
  Network,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "@/components/admin/empty-state";
import { NodeCategoryIcon } from "@/components/capabilities/nodes/node-icon";
import { NodePinoutDiagram } from "@/components/capabilities/nodes/node-pinout-diagram";
import { NodeSchemaTable } from "@/components/capabilities/nodes/node-schema-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  getNodeCategoryLabel,
  nodeCatalogApi,
} from "@/services/node-catalog-api";
import type { NodeManifest } from "@/types/common";

interface NodeDetailPageProps {
  nodeType: string;
}

export function NodeDetailPage({ nodeType }: NodeDetailPageProps) {
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("input");

  // Fetch all nodes and select matching nodeType
  const { data: nodes = [], isLoading } = useQuery({
    queryKey: ["node-catalog"],
    queryFn: () => nodeCatalogApi.listNodes(),
  });

  const node: NodeManifest | undefined = nodes.find(
    (n) => n.type === nodeType || `${n.type}@${n.version}` === nodeType,
  );

  const handleCopySpec = () => {
    if (!node) return;
    navigator.clipboard.writeText(JSON.stringify(node, null, 2));
    setCopied(true);
    toast.success("Đã sao chép toàn bộ Manifest JSON");
    setTimeout(() => setCopied(false), 1600);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-3">
        <RefreshCw className="size-7 text-primary animate-spin" />
        <p className="text-xs text-muted-foreground">
          Đang nạp đặc tả Node từ Platform Engine...
        </p>
      </div>
    );
  }

  if (!node) {
    return (
      <div className="space-y-4">
        <Button
          variant="ghost"
          size="sm"
          className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          onClick={() => void navigate({ to: "/capabilities/nodes" })}
        >
          <ArrowLeft className="size-3.5" />
          <span>Quay lại Thư viện Nodes</span>
        </Button>

        <EmptyState
          icon={Network}
          title="Không tìm thấy Node xử lý"
          description={`Mã định danh node '${nodeType}' không tồn tại trong danh mục đã chứng nhận.`}
          action={{
            label: "Về danh sách Nodes",
            onClick: () => {
              void navigate({ to: "/capabilities/nodes" });
            },
          }}
        />
      </div>
    );
  }

  const inputCount = Object.keys(
    (node.input_schema?.properties as Record<string, unknown>) || {},
  ).length;
  const outputCount = Object.keys(
    (node.output_schema?.properties as Record<string, unknown>) || {},
  ).length;
  const configCount = Object.keys(
    (node.config_schema?.properties as Record<string, unknown>) || {},
  ).length;

  return (
    <div className="space-y-5">
      {/* 1. Header Navigation & Breadcrumb */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground gap-1"
            onClick={() => void navigate({ to: "/capabilities/nodes" })}
          >
            <ArrowLeft className="size-3.5" />
            <span className="hidden xs:inline">Thư viện Nodes</span>
            <span className="xs:hidden">Quay lại</span>
          </Button>
          <span>/</span>
          <span className="font-mono text-[11px] truncate max-w-[200px] sm:max-w-none">
            {node.type}
          </span>
        </div>

        {/* Hero Card */}
        <Card className="border-border/70 overflow-hidden bg-card/70 backdrop-blur-xs">
          <CardContent className="p-4 sm:p-5">
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
              <div className="flex items-start gap-3.5 min-w-0">
                <div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary shrink-0 shadow-2xs">
                  <NodeCategoryIcon
                    category={node.category}
                    className="size-5.5"
                  />
                </div>

                <div className="space-y-1.5 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h1 className="text-base sm:text-lg font-bold text-foreground">
                      {node.display_name}
                    </h1>
                    <Badge variant="outline" className="text-[11px]">
                      {getNodeCategoryLabel(node.category)}
                    </Badge>
                    <Badge
                      variant={
                        node.status === "active" ? "default" : "secondary"
                      }
                      className="text-[11px] capitalize"
                    >
                      {node.status}
                    </Badge>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground font-mono">
                    <span className="bg-muted px-2 py-0.5 rounded-xs text-foreground">
                      {node.type}@{node.version}
                    </span>
                    <span>·</span>
                    <span>API {node.api_version}</span>
                  </div>

                  <p className="text-xs text-muted-foreground leading-relaxed pt-1">
                    {node.description}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-2 w-full sm:flex sm:w-auto shrink-0 self-stretch sm:self-start">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 gap-1.5 text-xs w-full sm:w-auto"
                  onClick={handleCopySpec}
                >
                  {copied ? (
                    <Check className="size-3.5 text-emerald-500" />
                  ) : (
                    <Copy className="size-3.5" />
                  )}
                  <span>{copied ? "Đã sao chép" : "Sao chép JSON"}</span>
                </Button>

                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 gap-1.5 text-xs w-full sm:w-auto"
                  onClick={() => void navigate({ to: "/assistants" as never })}
                >
                  <Bot className="size-3.5" />
                  <span>Xem Trợ lý AI</span>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 2. Main 2-Column Deep Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Schema Inspector (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          <Card className="border-border/70 overflow-hidden">
            <CardHeader className="p-4 pb-2 border-b border-border/50">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs sm:text-sm font-semibold flex items-center gap-2">
                  <Code2 className="size-4 text-primary" />
                  <span>Đặc Tả Cổng Giao Tiếp (Schema Specifications)</span>
                </CardTitle>

                <Badge variant="outline" className="text-[10px] font-mono">
                  OpenAPI / JSON Schema
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="p-4 sm:p-5">
              <Tabs
                value={activeTab}
                onValueChange={setActiveTab}
                className="w-full space-y-4"
              >
                <TabsList className="grid grid-cols-4 w-full h-8 p-0.5 bg-muted/60">
                  <TabsTrigger
                    value="input"
                    className="text-xs h-7 px-1 data-[state=active]:bg-background"
                  >
                    <span>Đầu vào</span>
                    <span className="ml-0.5 text-[10px] opacity-75">
                      ({inputCount})
                    </span>
                  </TabsTrigger>
                  <TabsTrigger
                    value="output"
                    className="text-xs h-7 px-1 data-[state=active]:bg-background"
                  >
                    <span>Đầu ra</span>
                    <span className="ml-0.5 text-[10px] opacity-75">
                      ({outputCount})
                    </span>
                  </TabsTrigger>
                  <TabsTrigger
                    value="config"
                    className="text-xs h-7 px-1 data-[state=active]:bg-background"
                  >
                    <span>Cấu hình</span>
                    <span className="ml-0.5 text-[10px] opacity-75">
                      ({configCount})
                    </span>
                  </TabsTrigger>
                  <TabsTrigger
                    value="raw"
                    className="text-xs h-7 px-1 data-[state=active]:bg-background"
                  >
                    <span>Mã JSON</span>
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="input" className="mt-0 space-y-3">
                  <div className="text-xs text-muted-foreground flex items-center justify-between">
                    <span>
                      Các cổng dữ liệu tiếp nhận từ các node phía trước trong đồ
                      thị:
                    </span>
                    <span className="font-semibold text-foreground">
                      {inputCount} cổng
                    </span>
                  </div>
                  <NodeSchemaTable
                    schema={node.input_schema}
                    emptyMessage="Node này không yêu cầu tham số đầu vào (Input)."
                  />
                </TabsContent>

                <TabsContent value="output" className="mt-0 space-y-3">
                  <div className="text-xs text-muted-foreground flex items-center justify-between">
                    <span>
                      Các trường dữ liệu phát sinh để truyền sang các node kế
                      tiếp:
                    </span>
                    <span className="font-semibold text-foreground">
                      {outputCount} cổng
                    </span>
                  </div>
                  <NodeSchemaTable
                    schema={node.output_schema}
                    emptyMessage="Node này không sinh cổng dữ liệu đầu ra."
                  />
                </TabsContent>

                <TabsContent value="config" className="mt-0 space-y-3">
                  <div className="text-xs text-muted-foreground flex items-center justify-between">
                    <span>
                      Thuộc tính tĩnh có thể tùy biến khi cấu hình node trên DAG
                      Canvas:
                    </span>
                    <span className="font-semibold text-foreground">
                      {configCount} thuộc tính
                    </span>
                  </div>
                  <NodeSchemaTable
                    schema={node.config_schema}
                    emptyMessage="Node này không yêu cầu cấu hình tĩnh."
                  />
                </TabsContent>

                <TabsContent value="raw" className="mt-0 space-y-2">
                  <div className="flex items-center justify-between pb-1">
                    <span className="text-xs text-muted-foreground">
                      Bản khai manifest gốc (JSON Schema chuẩn):
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs gap-1"
                      onClick={handleCopySpec}
                    >
                      {copied ? (
                        <Check className="size-3 text-emerald-500" />
                      ) : (
                        <Copy className="size-3" />
                      )}
                      <span>Sao chép</span>
                    </Button>
                  </div>
                  <pre className="max-h-[500px] overflow-auto rounded-lg border border-border/70 bg-muted/40 p-4 font-mono text-[11px] leading-relaxed text-foreground">
                    {JSON.stringify(node, null, 2)}
                  </pre>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Pinout Diagram & Metadata (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          {/* Visual Pinout */}
          <NodePinoutDiagram node={node} />

          {/* Compatibility & Core Standards */}
          <Card className="border-border/70">
            <CardHeader className="p-4 pb-2">
              <CardTitle className="text-xs font-semibold flex items-center gap-2">
                <ShieldCheck className="size-4 text-primary" />
                <span>Tiêu Chuẩn QNU AI Core</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-1 space-y-2.5 text-xs">
              <div className="flex items-center justify-between py-1 border-b border-border/40">
                <span className="text-muted-foreground">Chuẩn Đăng Kiểm</span>
                <span className="font-medium text-foreground flex items-center gap-1">
                  <CheckCircle2 className="size-3 text-emerald-500" />
                  TM-08 Verified
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-border/40">
                <span className="text-muted-foreground">
                  Kiến Trúc Thực Thi
                </span>
                <span className="font-mono text-[11px] text-foreground">
                  Python Async / DAG
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-border/40">
                <span className="text-muted-foreground">Cơ Chế Phục Hồi</span>
                <span className="font-medium text-foreground">
                  Circuit Breaker & Fallback
                </span>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-muted-foreground">Streaming SSE</span>
                <span className="font-medium text-foreground">
                  {node.category === "ai" || node.category === "output"
                    ? "Có hỗ trợ"
                    : "Đồng bộ (Atomic)"}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Recommended Topology */}
          <Card className="border-border/70 bg-muted/20">
            <CardHeader className="p-4 pb-2">
              <CardTitle className="text-xs font-semibold flex items-center gap-2">
                <GitBranch className="size-4 text-primary" />
                <span>Khuyến Nghị Ghép Nối Luồng</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-1 space-y-2 text-xs text-muted-foreground leading-relaxed">
              <p>
                Khối{" "}
                <strong className="text-foreground">{node.display_name}</strong>{" "}
                được thiết kế để hoạt động tốt nhất trong các pipeline đa tầng
                của Nhà trường.
              </p>
              <div className="p-2.5 rounded-md bg-background border border-border/60 text-[11px] font-mono space-y-1">
                <div className="text-muted-foreground">Gợi ý chuỗi xử lý:</div>
                <div className="text-primary truncate">
                  input.chat → {node.type} → output.chat
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
