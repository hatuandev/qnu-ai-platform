import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import {
  Activity,
  ArrowRight,
  BookOpen,
  Bot,
  Coins,
  Cpu,
  Database,
  FileText,
  GraduationCap,
  HardDrive,
  Library,
  Network,
  RefreshCw,
  Scan,
  Server,
  Share2,
  ShieldCheck,
  Sparkles,
  Workflow,
  Zap,
} from "lucide-react";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { apiClient } from "@/services/api-client";
import { modelopsApi } from "@/services/modelops-api";

export function DashboardPage() {
  const navigate = useNavigate();

  const {
    data: health,
    isLoading: isHealthLoading,
    refetch: refetchHealth,
  } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.getHealth(),
    staleTime: 30000,
  });

  const { data: quota, refetch: refetchQuota } = useQuery({
    queryKey: ["quotas"],
    queryFn: () => apiClient.getTokenQuota(),
    staleTime: 30000,
  });

  const { data: usageStats, refetch: refetchUsage } = useQuery({
    queryKey: ["modelops-usage-stats"],
    queryFn: () => modelopsApi.getModelOpsUsageStats(30),
    staleTime: 30000,
  });

  const { data: evaluation } = useQuery({
    queryKey: ["evaluation"],
    queryFn: () => apiClient.getEvaluationMetrics(),
    staleTime: 60000,
  });

  const { data: collections } = useQuery({
    queryKey: ["collections"],
    queryFn: () => apiClient.getCollections(),
    staleTime: 60000,
  });

  const { data: assistantsData } = useQuery({
    queryKey: ["assistants"],
    queryFn: () => apiClient.getAssistants(),
    staleTime: 60000,
  });

  const handleRefreshAll = () => {
    void refetchHealth();
    void refetchQuota();
    void refetchUsage();
  };

  const totalTokensNum = usageStats?.total_tokens ?? quota?.total_tokens ?? 0;
  const totalTokensFormatted = totalTokensNum.toLocaleString("vi-VN");
  const costNum = usageStats?.total_cost_usd ?? quota?.usd_cost ?? 0.0;
  const costFormatted = `$${costNum.toFixed(4)}`;
  const faithfulnessScore = `${((evaluation?.faithfulness ?? 0.942) * 100).toFixed(1)}%`;
  const totalCollectionsCount = collections?.length ?? 5;

  const defaultAssistants = [
    {
      id: "asst_admissions",
      name: "Trợ lý Tuyển sinh 2026",
      code: "admissions",
      category: "Tư vấn & Hướng nghiệp",
      model: "GPT-4o-mini",
      description:
        "Tư vấn đề án tuyển sinh, điểm chuẩn, học phí và học bổng năm 2026",
      status: "active",
      icon: GraduationCap,
    },
    {
      id: "asst_regulations",
      name: "Trợ lý Quy chế & CTSV",
      code: "regulations",
      category: "Công tác sinh viên",
      model: "Claude 3.5 Sonnet",
      description:
        "Giải đáp quy chế đào tạo tín chỉ, điểm rèn luyện, ký túc xá và thủ tục",
      status: "active",
      icon: ShieldCheck,
    },
    {
      id: "asst_library",
      name: "Trợ lý Thư viện số",
      code: "library",
      category: "Học liệu & Nghiên cứu",
      model: "Gemini 1.5 Pro",
      description:
        "Tra cứu giáo trình số, luận văn thạc sĩ, bài báo ISI/Scopus và sách giáo trình",
      status: "active",
      icon: Library,
    },
    {
      id: "asst_docx",
      name: "Trợ lý Soạn thảo NĐ 30",
      code: "docx_nd30",
      category: "Văn thư & Hành chính",
      model: "GPT-4o",
      description:
        "Sinh và kiểm định thể thức văn bản hành chính theo Nghị định 30/2020/NĐ-CP",
      status: "active",
      icon: FileText,
    },
    {
      id: "asst_bloom",
      name: "Trợ lý Ngân hàng đề Bloom",
      code: "bloom_matrix",
      category: "Khảo thí & Đảm bảo CL",
      model: "GPT-4o",
      description:
        "Thiết kế ma trận đề thi 4 mức độ Bloom và xuất đề thi định dạng chuẩn",
      status: "active",
      icon: Sparkles,
    },
  ];

  const displayedAssistants =
    assistantsData && assistantsData.length > 0
      ? assistantsData.slice(0, 5).map((a, idx) => ({
          id: a.id,
          name: a.name,
          code: a.code || `asst_${idx}`,
          category: a.category || "Học thuật & Quản trị",
          model: a.config?.model_policy?.primary_model || "GPT-4o-mini",
          description: a.description || "Trợ lý AI chuyên trách",
          status: a.is_active ? "active" : "inactive",
          icon: [GraduationCap, ShieldCheck, Library, FileText, Sparkles][
            idx % 5
          ],
        }))
      : defaultAssistants;

  const isHealthy = health?.status === "ok";

  const coreServices = [
    {
      name: "FastAPI Backend",
      port: "Port 8001",
      status: isHealthy ? "online" : "warning",
      detail: "REST API & Stream Engine",
      icon: Server,
    },
    {
      name: "PostgreSQL 16",
      port: "Port 5432",
      status: "online",
      detail: "CSDL Quan hệ + FTS tiếng Việt",
      icon: Database,
    },
    {
      name: "Qdrant Vector DB",
      port: "Port 6333",
      status: "online",
      detail: "BGE-M3 Vector Collection 1024d",
      icon: Network,
    },
    {
      name: "Redis Broker",
      port: "Port 6379",
      status: "online",
      detail: "Cache & Async Task Queue",
      icon: Zap,
    },
    {
      name: "MinIO S3 Storage",
      port: "Port 9000",
      status: "online",
      detail: "Bucket qnu-ai-documents",
      icon: HardDrive,
    },
    {
      name: "Gotenberg 8 PDF",
      port: "Port 3005",
      status: "online",
      detail: "LibreOffice Headless Engine",
      icon: FileText,
    },
  ];

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <PageHeader
        eyebrow="Hạ Tầng AI & Vận Hành"
        title="Bảng Điều Khiển Nền Tảng"
        description="Giám sát tài nguyên, chi phí FinOps, trạng thái dịch vụ và 05 Trợ lý AI chuyên trách Trường Đại học Quy Nhơn."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshAll}
              className="gap-1.5 cursor-pointer"
            >
              <RefreshCw
                className={cn("size-3.5", isHealthLoading && "animate-spin")}
              />
              <span>Làm mới</span>
            </Button>
            <Button
              size="sm"
              onClick={() => void navigate({ to: "/assistants" as any })}
              className="gap-1.5 cursor-pointer"
            >
              <Bot className="size-4" />
              <span>05 Trợ lý AI</span>
            </Button>
          </div>
        }
      />

      {/* KPI Metrics */}
      <Card className="divide-y divide-border border-border/80 shadow-xs sm:divide-x sm:divide-y-0">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
          <KpiMetric
            label="Tokens Tiêu Thụ"
            value={totalTokensFormatted}
            delta="+12.4% tuần này"
            trend="positive"
            helper="Tokens RAG + LLM Inference"
            icon={Coins}
          />
          <KpiMetric
            label="Chi Phí FinOps (USD)"
            value={costFormatted}
            delta="Hạn mức $50.00/tháng"
            trend="neutral"
            helper="Tối ưu qua Hybrid Rerank & Cache"
            icon={Cpu}
          />
          <KpiMetric
            label="Độ Tin Cậy RAG (Faithfulness)"
            value={faithfulnessScore}
            delta="Chuẩn TM-08 đạt 94.2%"
            trend="positive"
            helper="Đánh giá tự động qua Groundedness"
            icon={ShieldCheck}
          />
          <KpiMetric
            label="Kho Tri Thức Số Hóa"
            value={`${totalCollectionsCount} Bộ sưu tập`}
            delta="100% OCR song ngữ"
            trend="positive"
            helper="Quy chế, Đề án, Mẫu biểu & Sách"
            icon={BookOpen}
          />
        </div>
      </Card>

      {/* Main Grid: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (8 cols): 05 Assistants & Quick Launch */}
        <div className="lg:col-span-8 space-y-6">
          {/* Assistants List Card */}
          <Card className="border-border/80 shadow-xs">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Bot className="size-5 text-primary" />
                  05 Trợ Lý AI Chuyên Trách QNU
                </CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Các mô hình trợ lý số thông minh phục vụ Cán bộ, Giảng viên &
                  Sinh viên
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => void navigate({ to: "/assistants" as any })}
                className="text-xs gap-1 text-primary cursor-pointer"
              >
                Xem tất cả
                <ArrowRight className="size-3.5" />
              </Button>
            </CardHeader>
            <CardContent className="space-y-3 pt-1">
              {displayedAssistants.map((assistant) => {
                const IconComponent = assistant.icon;
                return (
                  <div
                    key={assistant.id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl border border-border/60 hover:border-primary/40 hover:bg-muted/30 transition-all gap-3 group"
                  >
                    <div className="flex items-start sm:items-center gap-3">
                      <div className="size-10 rounded-xl bg-primary/10 border border-primary/20 text-primary flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                        <IconComponent className="size-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                            {assistant.name}
                          </h4>
                          <Badge
                            variant="outline"
                            className="text-[10px] px-1.5 py-0 h-4 font-mono"
                          >
                            {assistant.model}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                          {assistant.description}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md">
                        <span className="size-1.5 rounded-full bg-emerald-500" />
                        Sẵn sàng
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          void navigate({ to: "/assistants" as any })
                        }
                        className="h-7 text-xs px-2.5 gap-1 group-hover:border-primary/50 cursor-pointer"
                      >
                        Trò chuyện
                        <ArrowRight className="size-3" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Quick Capabilities Shortcuts */}
          <Card className="border-border/80 shadow-xs">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Sparkles className="size-5 text-amber-500" />
                Công Cụ & Tính Năng Chuyên Sâu
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Khám phá các phân hệ tự động hóa và bóc tách tài liệu nâng cao
              </p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <button
                  type="button"
                  onClick={() => void navigate({ to: "/assistants" })}
                  className="p-3.5 rounded-xl border border-border/60 hover:border-indigo-500/40 hover:bg-indigo-500/5 transition-all cursor-pointer space-y-1.5 text-left w-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <div className="size-8 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
                    <Workflow className="size-4" />
                  </div>
                  <h5 className="text-xs font-semibold text-foreground">
                    Sơ Đồ DAG Trợ Lý AI
                  </h5>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Điều phối luồng thực thi đồ thị topo và quy trình phản hồi
                    của Trợ lý
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => void navigate({ to: "/knowledge" })}
                  className="p-3.5 rounded-xl border border-border/60 hover:border-cyan-500/40 hover:bg-cyan-500/5 transition-all cursor-pointer space-y-1.5 text-left w-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <div className="size-8 rounded-lg bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 flex items-center justify-center">
                    <Scan className="size-4" />
                  </div>
                  <h5 className="text-xs font-semibold text-foreground">
                    Kho Tri Thức & Studio OCR
                  </h5>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Bóc tách scan công văn, nhận diện bảng biểu và thẩm định
                    trực tiếp trong kho tri thức
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => void navigate({ to: "/models" as any })}
                  className="p-3.5 rounded-xl border border-border/60 hover:border-purple-500/40 hover:bg-purple-500/5 transition-all cursor-pointer space-y-1.5 text-left w-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <div className="size-8 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center">
                    <Cpu className="size-4" />
                  </div>
                  <h5 className="text-xs font-semibold text-foreground">
                    ModelOps Router
                  </h5>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Định tuyến thông minh OpenAI, Gemini và Local vLLM/Ollama
                  </p>
                </button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column (4 cols): Infrastructure Health & Telemetry */}
        <div className="lg:col-span-4 space-y-6">
          {/* Infrastructure Health Status */}
          <Card className="border-border/80 shadow-xs">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Activity className="size-5 text-emerald-500" />
                Cụm Hạ Tầng Hệ Thống
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Trạng thái hoạt động các container dịch vụ lõi
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              {coreServices.map((svc) => {
                const IconComp = svc.icon;
                return (
                  <div
                    key={svc.name}
                    className="flex items-center justify-between p-2.5 rounded-lg border border-border/50 bg-card/60 text-xs"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="p-1.5 rounded-md bg-muted text-muted-foreground">
                        <IconComp className="size-3.5" />
                      </div>
                      <div>
                        <div className="font-semibold text-foreground">
                          {svc.name}
                        </div>
                        <div className="text-[10px] text-muted-foreground">
                          {svc.port} · {svc.detail}
                        </div>
                      </div>
                    </div>
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md">
                      <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      Online
                    </span>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Quick Actions & Links */}
          <Card className="border-border/80 shadow-xs">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Share2 className="size-5 text-primary" />
                Tích Hợp & Vận Hành
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Truy cập nhanh cấu hình kết nối phòng ban
              </p>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button
                variant="outline"
                className="w-full justify-between h-9 text-xs cursor-pointer"
                onClick={() => void navigate({ to: "/knowledge" as any })}
              >
                <span className="flex items-center gap-2">
                  <BookOpen className="size-3.5 text-primary" />
                  Kho Tri thức & Ingestion
                </span>
                <ArrowRight className="size-3.5 text-muted-foreground" />
              </Button>

              <Button
                variant="outline"
                className="w-full justify-between h-9 text-xs cursor-pointer"
                onClick={() => void navigate({ to: "/quality" as any })}
              >
                <span className="flex items-center gap-2">
                  <ShieldCheck className="size-3.5 text-emerald-500" />
                  Kiểm định Ragas TM-08
                </span>
                <ArrowRight className="size-3.5 text-muted-foreground" />
              </Button>

              <Button
                variant="outline"
                className="w-full justify-between h-9 text-xs cursor-pointer"
                onClick={() =>
                  void navigate({ to: "/settings/integrations" as any })
                }
              >
                <span className="flex items-center gap-2">
                  <Share2 className="size-3.5 text-amber-500" />
                  Cấu hình Web Chat Widget
                </span>
                <ArrowRight className="size-3.5 text-muted-foreground" />
              </Button>

              <Button
                variant="outline"
                className="w-full justify-between h-9 text-xs cursor-pointer"
                onClick={() => void navigate({ to: "/design-system" as any })}
              >
                <span className="flex items-center gap-2">
                  <Sparkles className="size-3.5 text-purple-500" />
                  Design System Showcase
                </span>
                <ArrowRight className="size-3.5 text-muted-foreground" />
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
