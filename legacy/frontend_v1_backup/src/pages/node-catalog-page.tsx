import { EmptyState } from "@/components/admin/empty-state";
import { NodeCatalogCard } from "@/components/admin/node-catalog-card";
import { NodeManifestDialog } from "@/components/admin/node-manifest-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { type NodeManifest, apiClient } from "@/services/api-client";
import { AlertTriangle, Cpu, RefreshCw, Search, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

const CATEGORY_LABELS: Record<string, string> = {
  ai: "Mô hình & Trí tuệ AI",
  control: "Kiểm soát & Con người",
  input: "Đầu vào Dữ liệu",
  interaction: "Tương tác & Làm rõ",
  knowledge: "Tri thức & RAG",
  output: "Đầu ra Phản hồi",
  routing: "Điều hướng & Rẽ nhánh",
  tool: "Công cụ & Xuất bản",
};

function getCategoryLabel(category: string): string {
  return CATEGORY_LABELS[category] || category;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Đã xảy ra lỗi không xác định khi tải catalog.";
}

export function NodeCatalogPage() {
  const [nodes, setNodes] = useState<NodeManifest[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNode, setSelectedNode] = useState<NodeManifest | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadNodes = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      setNodes(await apiClient.getNodeCatalog());
    } catch (error) {
      setNodes([]);
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadNodes();
  }, [loadNodes]);

  const categories = useMemo(
    () => ["all", ...Array.from(new Set(nodes.map((node) => node.category))).sort()],
    [nodes]
  );

  const filteredNodes = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLocaleLowerCase();
    return nodes.filter((node) => {
      if (selectedCategory !== "all" && node.category !== selectedCategory) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      return [node.display_name, node.type, node.description, node.category].some((value) =>
        value.toLocaleLowerCase().includes(normalizedQuery)
      );
    });
  }, [nodes, searchQuery, selectedCategory]);

  const activeCount = nodes.filter((node) => node.status === "active").length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
              <Cpu className="size-6 text-primary" />
              Danh mục Node Xử lý
            </h1>
            {!isLoading && !errorMessage && (
              <Badge variant="default">{nodes.length} NodeManifest</Badge>
            )}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Catalog manifest chuẩn QNU AI Core, dùng chung cho Runtime Engine và Visual DAG Canvas.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void loadNodes()} disabled={isLoading}>
          <RefreshCw className={isLoading ? "mr-1.5 size-3.5 animate-spin" : "mr-1.5 size-3.5"} />
          Làm mới
        </Button>
      </div>

      {errorMessage && (
        <Card className="border-destructive/40 bg-destructive/5">
          <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
              <div>
                <p className="text-sm font-semibold text-foreground">Không tải được Node Catalog</p>
                <p className="mt-1 text-xs text-muted-foreground">{errorMessage}</p>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={() => void loadNodes()}>
              Thử lại
            </Button>
          </CardContent>
        </Card>
      )}

      {!errorMessage && !isLoading && nodes.length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <CatalogMetric label="Node đã nạp" value={nodes.length} />
          <CatalogMetric label="Phân loại" value={categories.length - 1} />
          <CatalogMetric label="Đang hoạt động" value={activeCount} />
        </div>
      )}

      {!isLoading && nodes.length > 0 && (
        <div className="space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="relative w-full lg:max-w-md">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Tìm theo tên, type hoặc chức năng..."
                className="pl-9 pr-9"
              />
              {searchQuery && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-1 top-1/2 size-7 -translate-y-1/2"
                  onClick={() => setSearchQuery("")}
                  aria-label="Xóa tìm kiếm"
                >
                  <X className="size-3.5" />
                </Button>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              Hiển thị <span className="font-semibold text-foreground">{filteredNodes.length}</span>{" "}
              / {nodes.length} node
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {categories.map((category) => (
              <Button
                key={category}
                variant={selectedCategory === category ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedCategory(category)}
              >
                {category === "all" ? "Tất cả Node" : getCategoryLabel(category)}
                <span className="ml-1.5 text-[10px] opacity-75">
                  {category === "all"
                    ? nodes.length
                    : nodes.filter((node) => node.category === category).length}
                </span>
              </Button>
            ))}
          </div>
        </div>
      )}

      {isLoading ? (
        <Card>
          <CardContent className="flex min-h-56 flex-col items-center justify-center gap-3 p-8 text-center">
            <RefreshCw className="size-7 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Đang tải manifest từ Platform Engine...</p>
          </CardContent>
        </Card>
      ) : errorMessage ? null : nodes.length === 0 ? (
        <EmptyState
          icon={Cpu}
          title="Chưa có NodeManifest"
          description="Platform chưa tìm thấy manifest Node nào trong catalog. Hãy kiểm tra bộ seed configs/nodes hoặc khởi động lại backend."
          action={
            <Button variant="outline" size="sm" onClick={() => void loadNodes()}>
              <RefreshCw className="mr-1.5 size-3.5" />
              Tải lại catalog
            </Button>
          }
        />
      ) : filteredNodes.length === 0 ? (
        <EmptyState
          icon={Search}
          title="Không tìm thấy Node phù hợp"
          description="Thử xóa bộ lọc hoặc tìm bằng mã type khác."
          action={
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchQuery("");
                setSelectedCategory("all");
              }}
            >
              Đặt lại bộ lọc
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filteredNodes.map((node) => (
            <NodeCatalogCard
              key={`${node.type}@${node.version}`}
              node={node}
              categoryLabel={getCategoryLabel(node.category)}
              onInspect={setSelectedNode}
            />
          ))}
        </div>
      )}

      <NodeManifestDialog node={selectedNode} onClose={() => setSelectedNode(null)} />
    </div>
  );
}

interface CatalogMetricProps {
  label: string;
  value: number;
}

function CatalogMetric({ label, value }: CatalogMetricProps) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
        <p className="mt-1 text-xl font-bold text-foreground">{value}</p>
      </CardContent>
    </Card>
  );
}
