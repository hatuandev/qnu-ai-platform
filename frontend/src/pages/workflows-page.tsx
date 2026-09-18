import { WorkflowVersionHistoryDialog } from "@/components/admin/workflow-version-history-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/services/api-client";
import { listAssistants } from "@/services/assistants-api";
import { type WorkflowDefinition, workflowsApi } from "@/services/workflows-api";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  BookOpen,
  Bot,
  CheckCircle2,
  FileCode,
  FileText,
  GraduationCap,
  History,
  Layers,
  Library,
  Network,
  Play,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

interface WorkflowsPageProps {
  onNavigate: (path: string) => void;
}

const MODULE_CATEGORIES = [
  { value: "all", label: "Tất cả lĩnh vực" },
  { value: "admission", label: "Tuyển sinh & Hướng nghiệp" },
  { value: "regulation", label: "Quy chế & Học vụ" },
  { value: "library", label: "Thư viện & Học liệu Số" },
  { value: "drafting", label: "Soạn thảo Văn bản NĐ 30" },
  { value: "question_bank", label: "Khảo thí & Đề thi Bloom" },
];

function getModuleIcon(moduleCode: string): ReactNode {
  if (moduleCode.includes("admission")) {
    return <GraduationCap className="size-5 text-emerald-600 dark:text-emerald-400" />;
  }
  if (moduleCode.includes("regulation")) {
    return <BookOpen className="size-5 text-blue-600 dark:text-blue-400" />;
  }
  if (moduleCode.includes("library")) {
    return <Library className="size-5 text-amber-600 dark:text-amber-400" />;
  }
  if (moduleCode.includes("drafting")) {
    return <FileText className="size-5 text-purple-600 dark:text-purple-400" />;
  }
  return <FileCode className="size-5 text-teal-600 dark:text-teal-400" />;
}

function getModuleCategory(moduleCode: string): string {
  if (moduleCode.includes("admission")) return "admission";
  if (moduleCode.includes("regulation")) return "regulation";
  if (moduleCode.includes("library")) return "library";
  if (moduleCode.includes("drafting")) return "drafting";
  if (moduleCode.includes("question_bank")) return "question_bank";
  return "general";
}

export function WorkflowsPage({ onNavigate }: WorkflowsPageProps) {
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [historyWorkflow, setHistoryWorkflow] = useState<WorkflowDefinition | null>(null);

  const definitionsQuery = useQuery({
    queryKey: ["workflows", "definitions"],
    queryFn: () => workflowsApi.listDefinitions(),
  });

  const runsQuery = useQuery({
    queryKey: ["workflow-runs"],
    queryFn: () => apiClient.getWorkflowRuns(),
  });

  const assistantsQuery = useQuery({
    queryKey: ["assistants"],
    queryFn: () => listAssistants({ includeInactive: true }),
  });

  const definitions = definitionsQuery.data || [];
  const runs = runsQuery.data || [];
  const assistants = assistantsQuery.data || [];

  // Thống kê KPI
  const kpiMetrics = useMemo(() => {
    const totalWorkflows = definitions.length;
    const activeWorkflows = definitions.filter((d) => d.is_active).length;
    const totalNodes = definitions.reduce((sum, d) => sum + (d.nodes_count || 0), 0);
    const avgNodes = totalWorkflows > 0 ? (totalNodes / totalWorkflows).toFixed(1) : "0";
    const totalRuns = runs.length;

    return {
      totalWorkflows,
      activeWorkflows,
      avgNodes,
      totalRuns,
    };
  }, [definitions, runs]);

  // Lọc danh sách workflows
  const filteredDefinitions = useMemo(() => {
    return definitions.filter((item) => {
      const matchCategory =
        selectedCategory === "all" || getModuleCategory(item.module_code) === selectedCategory;
      const term = search.trim().toLowerCase();
      const matchSearch =
        !term ||
        item.name.toLowerCase().includes(term) ||
        item.display_name.toLowerCase().includes(term) ||
        (item.description?.toLowerCase().includes(term) ?? false) ||
        item.module_code.toLowerCase().includes(term);
      return matchCategory && matchSearch;
    });
  }, [definitions, selectedCategory, search]);

  const handleRefresh = () => {
    definitionsQuery.refetch();
    runsQuery.refetch();
    toast.success("Đã làm mới danh mục Quy trình Workflow DAG.");
  };

  return (
    <div className="space-y-6">
      {/* 1. Header & Navigation Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Network className="size-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
                Quy Trình & Workflow DAG
              </h1>
              <p className="text-xs text-muted-foreground mt-0.5">
                Điều phối động cơ thực thi có hướng (DAG Runtime Engine) và Workflow Control Plane
                cho 05 Trợ lý AI QNU.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-9 text-xs gap-1.5"
            onClick={handleRefresh}
            disabled={definitionsQuery.isFetching}
          >
            <RefreshCw
              className={`size-3.5 text-muted-foreground ${definitionsQuery.isFetching ? "animate-spin" : ""}`}
            />
            Làm mới
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-9 text-xs gap-1.5"
            onClick={() => onNavigate("/nodes")}
          >
            <Layers className="size-3.5 text-primary" />
            Thư viện DAG Nodes
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-9 text-xs gap-1.5"
            onClick={() => onNavigate("/runs")}
          >
            <History className="size-3.5 text-muted-foreground" />
            Lịch sử Runs
          </Button>
        </div>
      </div>

      {/* 2. KPI Metrics Strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card className="border-border bg-card/60 shadow-2xs">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">Tổng Quy Trình</span>
              <Network className="size-4 text-primary" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-foreground">
                {kpiMetrics.totalWorkflows}
              </span>
              <span className="text-[11px] text-muted-foreground">chuẩn QNU</span>
            </div>
            <p className="mt-1 text-[11px] text-muted-foreground">Phủ 5 chuyên môn học thuật</p>
          </CardContent>
        </Card>

        <Card className="border-border bg-card/60 shadow-2xs">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">Đang Phục Vụ</span>
              <CheckCircle2 className="size-4 text-emerald-500" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                {kpiMetrics.activeWorkflows}
              </span>
              <span className="text-[11px] text-muted-foreground">
                / {kpiMetrics.totalWorkflows} active
              </span>
            </div>
            <p className="mt-1 text-[11px] text-muted-foreground">Phiên bản v1.0.0 đã xuất bản</p>
          </CardContent>
        </Card>

        <Card className="border-border bg-card/60 shadow-2xs">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">Độ Phức Tạp DAG</span>
              <Layers className="size-4 text-primary" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-foreground">{kpiMetrics.avgNodes}</span>
              <span className="text-[11px] text-muted-foreground">nodes / workflow</span>
            </div>
            <p className="mt-1 text-[11px] text-muted-foreground">Topo Ready-Set Scheduler</p>
          </CardContent>
        </Card>

        <Card className="border-border bg-card/60 shadow-2xs">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">Chuẩn Kiểm Định</span>
              <ShieldCheck className="size-4 text-amber-500" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-amber-600 dark:text-amber-400">TM-08</span>
              <span className="text-[11px] text-muted-foreground">Anti-Hallucination</span>
            </div>
            <p className="mt-1 text-[11px] text-muted-foreground">Bắt buộc trích dẫn văn bản</p>
          </CardContent>
        </Card>
      </div>

      {/* 3. Search & Category Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm theo tên quy trình, mã module, mô tả…"
            className="h-9 pl-9 text-xs"
          />
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {MODULE_CATEGORIES.map((cat) => (
            <Button
              type="button"
              key={cat.value}
              variant={selectedCategory === cat.value ? "default" : "outline"}
              size="sm"
              className="h-8 text-xs font-medium"
              onClick={() => setSelectedCategory(cat.value)}
            >
              {cat.label}
            </Button>
          ))}
        </div>
      </div>

      {/* 4. Grid of Workflow Cards */}
      {definitionsQuery.isLoading ? (
        <div className="flex h-64 items-center justify-center text-xs text-muted-foreground">
          <RefreshCw className="mr-2 size-4 animate-spin text-primary" />
          Đang nạp danh mục Workflow DAG từ CSDL…
        </div>
      ) : filteredDefinitions.length === 0 ? (
        <Card className="p-12 text-center">
          <Network className="mx-auto size-8 text-muted-foreground/50" />
          <h3 className="mt-3 text-sm font-semibold text-foreground">
            Không tìm thấy quy trình phù hợp
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Thử thay đổi từ khóa tìm kiếm hoặc chọn lại danh mục lĩnh vực.
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-4 h-8 text-xs"
            onClick={() => {
              setSearch("");
              setSelectedCategory("all");
            }}
          >
            Đặt lại bộ lọc
          </Button>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredDefinitions.map((workflow) => {
            const assistant = assistants.find((a) => a.workflow_id === workflow.id);

            return (
              <Card
                key={workflow.id}
                className="group relative flex flex-col justify-between overflow-hidden border-border bg-card/80 transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
              >
                <div>
                  <CardHeader className="p-5 pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20">
                        {getModuleIcon(workflow.module_code)}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Badge variant="outline" className="text-[10px] font-mono">
                          {workflow.version || "v1.0.0"}
                        </Badge>
                        <Badge
                          variant={workflow.is_active ? "success" : "secondary"}
                          className="text-[10px]"
                        >
                          {workflow.is_active ? "Đã xuất bản" : "Bản nháp"}
                        </Badge>
                      </div>
                    </div>

                    <CardTitle className="mt-3 text-base font-bold text-foreground group-hover:text-primary transition-colors">
                      {workflow.display_name}
                    </CardTitle>
                    <CardDescription className="line-clamp-2 text-xs text-muted-foreground mt-1 min-h-8">
                      {workflow.description ||
                        "Quy trình xử lý tuần tự có hướng chuẩn ĐH Quy Nhơn."}
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="px-5 py-2 space-y-3">
                    {/* DAG Spec Summary */}
                    <div className="flex items-center gap-2 rounded-md bg-muted/50 p-2.5 text-xs text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Layers className="size-3.5 text-primary" />
                        <span className="font-semibold text-foreground">
                          {workflow.nodes_count || 5}
                        </span>
                        <span>nodes</span>
                      </div>
                      <span className="text-muted-foreground/40">•</span>
                      <div className="flex items-center gap-1">
                        <Activity className="size-3.5 text-primary" />
                        <span className="font-semibold text-foreground">
                          {workflow.edges_count || 4}
                        </span>
                        <span>connections</span>
                      </div>
                      <span className="text-muted-foreground/40">•</span>
                      <span className="truncate text-[11px] font-mono text-muted-foreground">
                        {workflow.module_code}
                      </span>
                    </div>

                    {/* Linked Assistant Banner */}
                    <div className="flex items-center justify-between rounded-md border border-border/80 bg-card p-2 text-xs">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <Bot className="size-3.5 text-primary shrink-0" />
                        <span className="text-muted-foreground text-[11px] shrink-0">
                          Trợ lý số:
                        </span>
                        <span className="font-medium text-foreground truncate text-[11px]">
                          {assistant?.name || workflow.display_name.replace("Quy trình ", "")}
                        </span>
                      </div>
                      {assistant && (
                        <button
                          type="button"
                          onClick={() => onNavigate(`/assistants/${assistant.code}`)}
                          className="shrink-0 text-[11px] text-primary hover:underline"
                        >
                          Cấu hình
                        </button>
                      )}
                    </div>
                  </CardContent>
                </div>

                {/* Footer Quick Action Toolbar */}
                <div className="border-t border-border/80 bg-muted/20 px-5 py-3 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
                      onClick={() => setHistoryWorkflow(workflow)}
                      title="Xem lịch sử các phiên bản xuất bản"
                    >
                      <History className="size-3.5 mr-1" />
                      Lịch sử
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
                      onClick={() =>
                        onNavigate(
                          `/chat?assistant=${encodeURIComponent(assistant?.code || workflow.id)}`
                        )
                      }
                      title="Mở Chat Studio chạy thử trực tiếp"
                    >
                      <Play className="size-3.5 mr-1 fill-muted-foreground" />
                      Thử nghiệm
                    </Button>
                  </div>

                  <Button
                    size="sm"
                    className="h-8 text-xs font-semibold gap-1"
                    onClick={() => onNavigate(`/workflows/${workflow.id}`)}
                  >
                    <span>Mở DAG Studio</span>
                    <ArrowRight className="size-3.5" />
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* 5. Version History & Rollback Modal */}
      {historyWorkflow && (
        <WorkflowVersionHistoryDialog
          workflowId={historyWorkflow.id}
          workflowName={historyWorkflow.display_name}
          isOpen={Boolean(historyWorkflow)}
          onClose={() => setHistoryWorkflow(null)}
          onRollbackSuccess={() => {
            definitionsQuery.refetch();
            setHistoryWorkflow(null);
          }}
        />
      )}
    </div>
  );
}
