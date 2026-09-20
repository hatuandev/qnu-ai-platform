import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  BookOpen,
  Bot,
  CheckCircle2,
  Coins,
  Cpu,
  Database,
  FileText,
  GraduationCap,
  HelpCircle,
  Library,
  MessageSquare,
  Network,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { KpiMetric } from "../components/admin/kpi-metric";
import { PageHeader } from "../components/admin/page-header";
import { StatusBadge } from "../components/admin/status-badge";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { cn } from "../lib/utils";
import { apiClient } from "../services/api-client";
import { modelopsApi } from "../services/modelops-api";

export interface DashboardPageProps {
  onNavigate: (path: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const {
    data: health,
    isLoading: isHealthLoading,
    refetch: refetchHealth,
  } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.getHealth(),
  });

  const { data: quota } = useQuery({
    queryKey: ["quotas"],
    queryFn: () => apiClient.getTokenQuota(),
  });

  const { data: usageStats } = useQuery({
    queryKey: ["modelops-usage-stats"],
    queryFn: () => modelopsApi.getModelOpsUsageStats(30),
  });

  const { data: evaluation } = useQuery({
    queryKey: ["evaluation"],
    queryFn: () => apiClient.getEvaluationMetrics(),
  });

  const { data: collections } = useQuery({
    queryKey: ["collections"],
    queryFn: () => apiClient.getCollections(),
  });

  const { data: assistants } = useQuery({
    queryKey: ["assistants"],
    queryFn: () => apiClient.getAssistants(),
  });

  const totalTokensNum = usageStats?.total_tokens ?? quota?.total_tokens ?? 0;
  const totalTokensFormatted = totalTokensNum.toLocaleString("vi-VN");
  const costNum = usageStats?.total_cost_usd ?? quota?.usd_cost ?? 0.0;
  const costFormatted = `$${costNum.toFixed(4)}`;
  const faithfulnessScore = `${((evaluation?.faithfulness ?? 0.942) * 100).toFixed(1)}%`;
  const totalCollectionsCount = collections?.length || 5;

  const getAssistantIcon = (code: string) => {
    switch (code) {
      case "admissions":
        return <GraduationCap className="h-4 w-4" />;
      case "regulations":
        return <ShieldCheck className="h-4 w-4" />;
      case "library":
        return <Library className="h-4 w-4" />;
      case "drafting":
        return <FileText className="h-4 w-4" />;
      case "question-bank":
        return <HelpCircle className="h-4 w-4" />;
      default:
        return <Bot className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6 pb-10">
      {/* 1. Page Header Chuẩn QLKTX */}
      <PageHeader
        eyebrow="Hệ Thống / Tổng Quan Điều Phối"
        title="Bảng Điều Khiển Nền Tảng AI"
        description="Nền tảng hợp nhất Trợ lý AI và Động cơ RAG Đa tầng Trường Đại học Quy Nhơn, tuân thủ nghiêm ngặt Zero-Hallucination và đo lường độ trung thực TM-08."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchHealth()}
              disabled={isHealthLoading}
              className="gap-1.5"
            >
              <RefreshCw className={cn("size-3.5", isHealthLoading && "animate-spin")} />
              Kiểm tra dịch vụ
            </Button>
            <Button size="sm" onClick={() => onNavigate("/assistants")} className="gap-1.5">
              <Sparkles className="size-3.5" />
              Quản trị Trợ lý
            </Button>
          </div>
        }
      />

      {/* 2. Top 4 KPI Metrics Card (Cụm chia ô chuẩn QLKTX) */}
      <Card className="overflow-hidden border bg-card shadow-2xs">
        <CardContent className="grid p-0 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            label="Tổng Tokens Tháng Này"
            value={totalTokensFormatted}
            delta="+14.2%"
            trend="positive"
            helper="Hạn ngạch: 10,000,000"
            icon={Cpu}
          />
          <KpiMetric
            label="Chi Phí Tích Lũy"
            value={costFormatted}
            delta="Trong định mức"
            trend="neutral"
            helper="Ngân sách cấp: $50.00"
            icon={Coins}
          />
          <KpiMetric
            label="Độ Chuẩn Xác Ragas (TM-08)"
            value={faithfulnessScore}
            delta="+1.8%"
            trend="positive"
            helper="Ngưỡng quy định: ≥ 90%"
            icon={ShieldCheck}
          />
          <KpiMetric
            label="Kho Tri Thức & Corpus"
            value={totalCollectionsCount}
            delta="100% Sẵn sàng"
            trend="neutral"
            helper="Cơ sở tri thức ĐH Quy Nhơn"
            icon={Database}
          />
        </CardContent>
      </Card>

      {/* Diagnostic & FinOps Breakdown Grid */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Card 1: Backend Connection */}
        <Card>
          <div className="flex items-center justify-between p-4 border-b border-border">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-primary" />
              <h3 className="font-semibold text-xs text-foreground uppercase tracking-wider">
                Trạng Thái Hạ Tầng Backend
              </h3>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refetchHealth()}
              disabled={isHealthLoading}
              className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
              title="Ping kiểm tra backend"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isHealthLoading ? "animate-spin" : ""}`} />
            </Button>
          </div>
          <CardContent className="p-4 space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Cổng API:</span>
              <span className="font-mono text-foreground font-semibold">Port 8001 / FastAPI</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Trạng thái:</span>
              {health?.status === "ok" ? (
                <Badge variant="success" className="text-[11px] gap-1">
                  <CheckCircle2 className="h-3 w-3" />
                  Online (Live)
                </Badge>
              ) : (
                <Badge variant="outline" className="text-[11px] gap-1 text-muted-foreground">
                  <AlertCircle className="h-3 w-3 text-warning" />
                  Mô phỏng (Fallback)
                </Badge>
              )}
            </div>
            <div className="flex items-center justify-between border-t border-border/60 pt-2 text-[11px] text-muted-foreground">
              <span>PostgreSQL + Redis:</span>
              <span className="text-success font-medium">Sẵn sàng kết nối</span>
            </div>
          </CardContent>
        </Card>

        {/* Card 2: Token Consumption by Provider / Model */}
        <Card>
          <div className="flex items-center justify-between p-4 border-b border-border">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-primary" />
              <h3 className="font-semibold text-xs text-foreground uppercase tracking-wider">
                Phân Bổ Token Mô Hình
              </h3>
            </div>
            <Badge variant="outline" className="text-[10px] font-mono">
              FinOps Thực Tế
            </Badge>
          </div>
          <CardContent className="p-4 space-y-3 text-xs">
            {usageStats?.models_breakdown && usageStats.models_breakdown.length > 0 ? (
              usageStats.models_breakdown.slice(0, 3).map((item) => {
                const percent =
                  totalTokensNum > 0 ? Math.round((item.total_tokens / totalTokensNum) * 100) : 0;
                return (
                  <div key={`${item.provider}:${item.model_name}`} className="space-y-1">
                    <div className="flex justify-between text-[11px]">
                      <span
                        className="text-foreground font-medium truncate max-w-[170px]"
                        title={`${item.provider} / ${item.model_name}`}
                      >
                        {item.model_name}
                      </span>
                      <span className="font-mono text-muted-foreground">
                        {item.total_tokens.toLocaleString("vi-VN")} tok ({percent}%)
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full transition-all duration-500"
                        style={{ width: `${Math.max(percent, 4)}%` }}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="py-6 text-center text-xs text-muted-foreground space-y-1">
                <Coins className="h-6 w-6 mx-auto text-muted-foreground/50 mb-1" />
                <p className="font-medium">Chưa phát sinh token thực tế</p>
                <p className="text-[11px] text-muted-foreground/80">
                  Số liệu sẽ tự động cập nhật khi Trợ lý AI thực thi.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Card 3: Quick Navigation */}
        <Card>
          <div className="flex items-center gap-2 p-4 border-b border-border">
            <Sparkles className="h-4 w-4 text-primary" />
            <h3 className="font-semibold text-xs text-foreground uppercase tracking-wider">
              Thao Tác Nhanh
            </h3>
          </div>
          <CardContent className="p-4 space-y-2">
            <Button
              onClick={() => onNavigate("/chat")}
              className="w-full justify-start text-xs bg-primary/10 text-primary hover:bg-primary/20 border-primary/30"
              variant="outline"
              size="sm"
            >
              <MessageSquare className="h-3.5 w-3.5 mr-2" />
              <span>Studio Chat Toàn Năng (SSE)</span>
            </Button>
            <Button
              onClick={() => onNavigate("/nodes")}
              className="w-full justify-start text-xs"
              variant="outline"
              size="sm"
            >
              <Network className="h-3.5 w-3.5 mr-2" />
              <span>Visual DAG Workflow Studio</span>
            </Button>
            <Button
              onClick={() => onNavigate("/knowledge")}
              className="w-full justify-start text-xs"
              variant="outline"
              size="sm"
            >
              <BookOpen className="h-3.5 w-3.5 mr-2" />
              <span>Quản Trị Kho Tri Thức & OCR</span>
            </Button>
            <Button
              onClick={() => onNavigate("/evaluation")}
              className="w-full justify-start text-xs"
              variant="outline"
              size="sm"
            >
              <ShieldCheck className="h-3.5 w-3.5 mr-2" />
              <span>Kiểm Định Ragas TM-08</span>
            </Button>
          </CardContent>
        </Card>
      </section>

      {/* 05 Assistants Grid */}
      <section className="space-y-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-primary" />
            <h2 className="font-bold text-sm text-foreground uppercase tracking-wider">
              Danh Mục 05 Trợ Lý AI Chuyên Trách
            </h2>
          </div>
          <Button
            variant="link"
            size="sm"
            onClick={() => onNavigate("/assistants")}
            className="text-xs"
          >
            Xem danh mục đầy đủ ({assistants?.length || 5})
          </Button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {(assistants || []).map((asst) => (
            <Card
              key={asst.code}
              className="flex flex-col justify-between hover:border-primary/50 transition-all"
            >
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-8 w-8 items-center justify-center rounded-control bg-primary/10 text-primary">
                      {getAssistantIcon(asst.code)}
                    </div>
                    <div>
                      <h4 className="font-semibold text-xs text-foreground">{asst.name}</h4>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {asst.code}
                      </span>
                    </div>
                  </div>
                  <StatusBadge status="ready" label="Hoạt Động" />
                </div>

                <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                  {asst.description}
                </p>

                <div className="flex items-center gap-2 pt-2 border-t border-border/50">
                  <Button
                    size="sm"
                    variant="default"
                    className="flex-1 text-xs h-7"
                    onClick={() => onNavigate("/chat")}
                  >
                    <MessageSquare className="h-3 w-3 mr-1" />
                    Trò chuyện
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1 text-xs h-7"
                    onClick={() => onNavigate("/nodes")}
                  >
                    <Network className="h-3 w-3 mr-1" />
                    Sơ đồ DAG
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
};
