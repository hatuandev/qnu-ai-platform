import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  Check,
  Copy,
  Cpu,
  Eye,
  GitBranch,
  Layers,
  Network,
  RefreshCw,
  Search,
  X,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "@/components/admin/empty-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { NodeCatalogCard } from "@/components/capabilities/nodes/node-catalog-card";
import { NodeCategoryIcon } from "@/components/capabilities/nodes/node-icon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ViewModeToggle } from "@/components/ui/view-mode-toggle";
import {
  getNodeCategoryLabel,
  NODE_CATEGORIES,
  nodeCatalogApi,
} from "@/services/node-catalog-api";
import type { NodeManifest } from "@/types/common";

function countSchemaProps(schema: Record<string, unknown> | undefined): number {
  if (!schema || typeof schema !== "object") return 0;
  const props = schema.properties;
  if (!props || typeof props !== "object" || Array.isArray(props)) return 0;
  return Object.keys(props).length;
}

export function NodeCatalogPage() {
  const navigate = useNavigate();

  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  const [copiedType, setCopiedType] = useState<string | null>(null);

  // 1. Fetch Node Manifests
  const {
    data: nodes = [],
    isLoading,
    isRefetching,
    error,
    refetch,
  } = useQuery({
    queryKey: ["node-catalog"],
    queryFn: () => nodeCatalogApi.listNodes(),
  });

  // 2. Filter nodes
  const filteredNodes = useMemo(() => {
    const q = search.trim().toLowerCase();
    return nodes.filter((node) => {
      if (category !== "all" && node.category !== category) {
        return false;
      }
      if (statusFilter !== "all" && node.status !== statusFilter) {
        return false;
      }
      if (!q) return true;
      return (
        node.display_name.toLowerCase().includes(q) ||
        node.type.toLowerCase().includes(q) ||
        node.description.toLowerCase().includes(q) ||
        node.category.toLowerCase().includes(q)
      );
    });
  }, [nodes, search, category, statusFilter]);

  // 3. Telemetry KPIs
  const activeCount = useMemo(
    () => nodes.filter((n) => n.status === "active").length,
    [nodes],
  );

  const totalCategories = useMemo(
    () => new Set(nodes.map((n) => n.category)).size,
    [nodes],
  );

  const totalPorts = useMemo(() => {
    return nodes.reduce((acc, curr) => {
      return (
        acc +
        countSchemaProps(curr.input_schema) +
        countSchemaProps(curr.output_schema)
      );
    }, 0);
  }, [nodes]);

  const handleCopySpec = (e: React.MouseEvent, node: NodeManifest) => {
    e.stopPropagation();
    navigator.clipboard.writeText(JSON.stringify(node, null, 2));
    setCopiedType(node.type);
    toast.success(`Đã sao chép manifest '${node.type}'`);
    setTimeout(() => setCopiedType(null), 1600);
  };

  const handleSelectNode = (nodeType: string) => {
    void navigate({
      to: "/capabilities/nodes/$nodeType",
      params: { nodeType },
    });
  };

  return (
    <div className="space-y-5">
      {/* 1. Header Hero & Actions */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Network className="size-5" />
            </div>
            <h1 className="text-lg sm:text-xl font-bold tracking-tight text-foreground">
              Thư Viện Nodes
            </h1>
            {!isLoading && nodes.length > 0 && (
              <Badge variant="outline" className="font-mono text-xs">
                {nodes.length} Nodes
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            Danh mục các khối xử lý hạt nhân chuẩn QNU AI Core, tích hợp trực
            tiếp vào DAG Workflow Studio.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2 w-full sm:flex sm:w-auto">
          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 text-xs"
            onClick={() => void refetch()}
            disabled={isLoading || isRefetching}
          >
            <RefreshCw
              className={`size-3.5 ${
                isLoading || isRefetching ? "animate-spin text-primary" : ""
              }`}
            />
            <span>Làm mới</span>
          </Button>

          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs"
            onClick={() => void navigate({ to: "/assistants" as never })}
          >
            <Bot className="size-3.5" />
            <span>Trợ lý AI</span>
          </Button>
        </div>
      </div>

      {/* 2. KPI Telemetry Strip (Symmetrical 2x2 Matrix on Mobile, 4 Cols on Desktop) */}
      <Card className="overflow-hidden border-border/70 bg-card/80 backdrop-blur-xs">
        <div className="grid grid-cols-2 lg:grid-cols-4">
          <KpiMetric
            label="Tổng Node Hạt Nhân"
            value={`${nodes.length}`}
            icon={Cpu}
            className="border-r border-b lg:border-b-0 border-border/60"
          />
          <KpiMetric
            label="Nhóm Phân Loại"
            value={`${totalCategories || 8}`}
            icon={Layers}
            className="border-b lg:border-b-0 lg:border-r border-border/60"
          />
          <KpiMetric
            label="Sẵn Sàng Runtime"
            value={`${activeCount} Active`}
            delta={`${nodes.length - activeCount} Thử nghiệm`}
            trend="positive"
            icon={GitBranch}
            className="border-r border-border/60"
          />
          <KpiMetric
            label="Tổng Cổng I/O"
            value={`${totalPorts}`}
            icon={Network}
          />
        </div>
      </Card>

      {/* 3. Error Banner */}
      {error && (
        <Card className="border-destructive/40 bg-destructive/5">
          <CardContent className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 gap-3">
            <div className="flex items-start gap-3">
              <AlertTriangle className="size-4 shrink-0 text-destructive mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-foreground">
                  Không thể tải danh mục Node từ Platform Core
                </p>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  {(error as Error)?.message ||
                    "Vui lòng kiểm tra lại dịch vụ Backend."}
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => void refetch()}
            >
              Thử lại
            </Button>
          </CardContent>
        </Card>
      )}

      {/* 4. Seamless & Borderless Filter Bar */}
      <div className="space-y-2.5">
        {/* Hàng 1: Tìm kiếm bên trái - Bộ lọc bên phải */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
          {/* Bên trái: Ô tìm kiếm gọn gàng */}
          <div className="relative w-full sm:w-72 lg:w-80 shrink-0">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground pointer-events-none" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm kiếm node..."
              className="h-8.5 sm:h-8 pl-8 pr-8 text-xs bg-background w-full"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer"
                aria-label="Xóa tìm kiếm"
              >
                <X className="size-3.5" />
              </button>
            )}
          </div>

          {/* Bên phải: Cụm bộ lọc (Nhóm + Trạng thái + Nút đặt lại) */}
          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <div className="grid grid-cols-2 gap-2 w-full sm:flex sm:w-auto">
              {/* Lọc theo Nhóm */}
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="h-8.5 sm:h-8 text-xs w-full sm:w-[160px] bg-background [&>span]:truncate">
                  <SelectValue placeholder="Nhóm phân loại" />
                </SelectTrigger>
                <SelectContent>
                  {NODE_CATEGORIES.map((cat) => (
                    <SelectItem
                      key={cat.key}
                      value={cat.key}
                      className="text-xs"
                    >
                      {cat.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Lọc theo Trạng thái */}
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="h-8.5 sm:h-8 text-xs w-full sm:w-[145px] bg-background [&>span]:truncate">
                  <SelectValue placeholder="Trạng thái" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all" className="text-xs">
                    Tất cả trạng thái
                  </SelectItem>
                  <SelectItem value="active" className="text-xs">
                    Chính thức (Active)
                  </SelectItem>
                  <SelectItem value="experimental" className="text-xs">
                    Thử nghiệm (Beta)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Nút đặt lại bộ lọc khi đang có điều kiện lọc */}
            {(search || category !== "all" || statusFilter !== "all") && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8.5 sm:h-8 px-2 text-xs text-muted-foreground hover:text-foreground gap-1 shrink-0"
                onClick={() => {
                  setSearch("");
                  setCategory("all");
                  setStatusFilter("all");
                }}
                title="Đặt lại bộ lọc"
              >
                <X className="size-3.5" />
                <span className="hidden sm:inline">Đặt lại</span>
              </Button>
            )}
          </div>
        </div>

        {/* Hàng 2: Chip lọc nhanh nhóm bên trái & Chuyển đổi Grid/Table bên phải trên cùng 1 dòng */}
        <div className="flex items-center justify-between gap-2 w-full">
          <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 scrollbar-none no-scrollbar text-xs flex-1 min-w-0">
            {NODE_CATEGORIES.slice(0, 7).map((cat) => (
              <Button
                key={cat.key}
                variant={category === cat.key ? "default" : "outline"}
                size="sm"
                className="h-6.5 px-2.5 text-[11px] rounded-full shrink-0"
                onClick={() => setCategory(cat.key)}
              >
                {cat.shortLabel || cat.label}
              </Button>
            ))}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[11px] text-muted-foreground hidden md:inline">
              <strong>{filteredNodes.length}</strong> / {nodes.length} nodes
            </span>

            {/* Chuyển Grid/Table */}
            <ViewModeToggle value={viewMode} onChange={setViewMode} />
          </div>
        </div>
      </div>

      {/* 5. Main Content Area */}
      {isLoading ? (
        <Card className="border-border/60">
          <CardContent className="flex flex-col items-center justify-center p-12 space-y-3">
            <RefreshCw className="size-6 text-primary animate-spin" />
            <p className="text-xs text-muted-foreground">
              Đang tải danh mục Node từ QNU AI Core...
            </p>
          </CardContent>
        </Card>
      ) : filteredNodes.length === 0 ? (
        <EmptyState
          icon={Search}
          title="Không tìm thấy Node xử lý nào"
          description={
            search || category !== "all" || statusFilter !== "all"
              ? "Không có Node nào khớp với điều kiện tìm kiếm. Hãy thử xóa bớt bộ lọc."
              : "Hệ thống chưa tìm thấy NodeManifest nào. Vui lòng kiểm tra lại thư mục configs/nodes."
          }
          action={{
            label: "Đặt lại bộ lọc",
            onClick: () => {
              setSearch("");
              setCategory("all");
              setStatusFilter("all");
            },
          }}
        />
      ) : viewMode === "grid" ? (
        /* Grid 4-2-1 Cards */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {filteredNodes.map((node) => (
            <NodeCatalogCard
              key={`${node.type}@${node.version}`}
              node={node}
              onSelect={handleSelectNode}
            />
          ))}
        </div>
      ) : (
        /* Adaptive List View */
        <div className="space-y-2.5">
          {/* Mobile Compact List View (Dành riêng cho màn hình di động <sm chống vỡ cột) */}
          <div className="space-y-2 sm:hidden">
            {filteredNodes.map((node) => {
              const inputCount = countSchemaProps(node.input_schema);
              const outputCount = countSchemaProps(node.output_schema);
              const configCount = countSchemaProps(node.config_schema);
              const isCopied = copiedType === node.type;

              return (
                <div
                  key={`${node.type}@${node.version}`}
                  className="p-3 rounded-lg border border-border/70 bg-card hover:border-primary/50 transition-colors space-y-2 shadow-2xs"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="flex size-8 items-center justify-center rounded-md bg-primary/10 text-primary shrink-0">
                        <NodeCategoryIcon
                          category={node.category}
                          className="size-4"
                        />
                      </div>
                      <div className="min-w-0">
                        <div className="font-semibold text-xs text-foreground truncate">
                          {node.display_name}
                        </div>
                        <div className="font-mono text-[10px] text-muted-foreground truncate">
                          {node.type}@{node.version}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <Badge
                        variant="outline"
                        className="text-[10px] px-1.5 py-0"
                      >
                        {getNodeCategoryLabel(node.category, true)}
                      </Badge>
                      <Badge
                        variant={
                          node.status === "active" ? "default" : "secondary"
                        }
                        className="text-[10px] px-1.5 py-0 capitalize"
                      >
                        {node.status}
                      </Badge>
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-2 pt-1 border-t border-border/40 text-[11px]">
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <span className="font-mono bg-muted/60 px-1.5 py-0.5 rounded-xs text-[10px]">
                        Vào: {inputCount}
                      </span>
                      <span className="font-mono bg-muted/60 px-1.5 py-0.5 rounded-xs text-[10px]">
                        Ra: {outputCount}
                      </span>
                      <span className="font-mono bg-muted/60 px-1.5 py-0.5 rounded-xs text-[10px]">
                        Cfg: {configCount}
                      </span>
                    </div>

                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-7"
                        title="Sao chép JSON"
                        onClick={(e) => handleCopySpec(e, node)}
                      >
                        {isCopied ? (
                          <Check className="size-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="size-3.5 text-muted-foreground" />
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 px-2 text-[11px] gap-1 font-medium"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectNode(node.type);
                        }}
                      >
                        <span>Chi tiết</span>
                        <ArrowRight className="size-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Desktop/Tablet Data Table View (Hiển thị đầy đủ 7 cột có cuộn ngang an toàn trên màn hình >= sm) */}
          <div className="hidden sm:block rounded-lg border border-border/70 overflow-hidden bg-card">
            <div className="w-full overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/40 hover:bg-muted/40 text-xs">
                    <TableHead className="w-[280px] font-semibold text-foreground whitespace-nowrap">
                      Node / Mã Type
                    </TableHead>
                    <TableHead className="w-[160px] font-semibold text-foreground whitespace-nowrap">
                      Nhóm phân loại
                    </TableHead>
                    <TableHead className="w-[90px] font-semibold text-foreground text-center whitespace-nowrap">
                      Đầu vào
                    </TableHead>
                    <TableHead className="w-[90px] font-semibold text-foreground text-center whitespace-nowrap">
                      Đầu ra
                    </TableHead>
                    <TableHead className="w-[90px] font-semibold text-foreground text-center whitespace-nowrap">
                      Cấu hình
                    </TableHead>
                    <TableHead className="w-[110px] font-semibold text-foreground text-center whitespace-nowrap">
                      Trạng thái
                    </TableHead>
                    <TableHead className="w-[130px] font-semibold text-foreground text-right whitespace-nowrap">
                      Thao tác
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredNodes.map((node) => {
                    const inputCount = countSchemaProps(node.input_schema);
                    const outputCount = countSchemaProps(node.output_schema);
                    const configCount = countSchemaProps(node.config_schema);
                    const isCopied = copiedType === node.type;

                    return (
                      <TableRow
                        key={`${node.type}@${node.version}`}
                        className="text-xs hover:bg-muted/30 cursor-pointer"
                        onClick={() => handleSelectNode(node.type)}
                      >
                        <TableCell className="py-2.5">
                          <div className="flex items-center gap-2.5">
                            <div className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary shrink-0">
                              <NodeCategoryIcon
                                category={node.category}
                                className="size-3.5"
                              />
                            </div>
                            <div className="min-w-0">
                              <div className="font-semibold text-foreground truncate">
                                {node.display_name}
                              </div>
                              <div className="font-mono text-[10px] text-muted-foreground truncate">
                                {node.type}@{node.version}
                              </div>
                            </div>
                          </div>
                        </TableCell>

                        <TableCell className="py-2.5 whitespace-nowrap">
                          <Badge
                            variant="outline"
                            className="text-[10px] px-1.5 py-0"
                          >
                            {getNodeCategoryLabel(node.category)}
                          </Badge>
                        </TableCell>

                        <TableCell className="text-center py-2.5 font-medium">
                          {inputCount}
                        </TableCell>

                        <TableCell className="text-center py-2.5 font-medium">
                          {outputCount}
                        </TableCell>

                        <TableCell className="text-center py-2.5 font-medium">
                          {configCount}
                        </TableCell>

                        <TableCell className="text-center py-2.5">
                          <Badge
                            variant={
                              node.status === "active" ? "default" : "secondary"
                            }
                            className="text-[10px] px-1.5 py-0 capitalize"
                          >
                            {node.status}
                          </Badge>
                        </TableCell>

                        <TableCell className="text-right py-2.5">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 px-2 text-[11px] gap-1"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelectNode(node.type);
                              }}
                            >
                              <Eye className="size-3" />
                              <span>Chi tiết</span>
                            </Button>

                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-7"
                              title="Sao chép JSON"
                              onClick={(e) => handleCopySpec(e, node)}
                            >
                              {isCopied ? (
                                <Check className="size-3.5 text-emerald-500" />
                              ) : (
                                <Copy className="size-3.5 text-muted-foreground" />
                              )}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
