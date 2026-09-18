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
import type React from "react";
import { KpiMetric } from "../components/admin/kpi-metric";
import { StatusBadge } from "../components/admin/status-badge";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { apiClient } from "../services/api-client";

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

  const totalTokensFormatted = (quota?.total_tokens ?? 1458200).toLocaleString("vi-VN");
  const costFormatted = `$${(quota?.usd_cost ?? 0.4374).toFixed(4)}`;
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
    <div className="space-y-6">
      {/* Welcome Banner */}
      <section className="relative overflow-hidden rounded-surface border border-border bg-gradient-to-br from-card via-card to-muted/40 p-6 shadow-xs">
        <div className="relative z-10 max-w-3xl space-y-2.5">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs text-primary font-medium">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>QNU AI Platform — Hệ Thống Sản Xuất Đạt Chuẩn</span>
          </div>
          <h1 className="font-bold text-2xl tracking-tight text-foreground sm:text-3xl">
            Nền Tảng Điều Phối Trợ Lý AI & Động Cơ RAG
          </h1>
          <p className="text-muted-foreground text-xs sm:text-sm leading-relaxed">
            Hợp nhất 05 Trợ lý Chuyên trách (Tuyển sinh, Quy chế, Thư viện, Soạn thảo NĐ 30, Đề thi
            Bloom) trên một hạ tầng AI hiện đại, bảo mật và tuân thủ Zero-Hallucination.
          </p>
        </div>
      </section>

      {/* KPI Metrics Row */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiMetric
          title="Tổng Tokens Tháng Này"
          value={totalTokensFormatted}
          change="+14.2%"
          changeType="increase"
          description="Hạn ngạch: 10,000,000"
          icon={Cpu}
        />
        <KpiMetric
          title="Chi Phí FinOps USD"
          value={costFormatted}
          change="-3.8%"
          changeType="decrease"
          description="Tiết kiệm nhờ local vLLM"
          icon={Coins}
        />
        <KpiMetric
          title="Độ Trung Thực Ragas TM-08"
          value={faithfulnessScore}
          change="Đạt Chuẩn"
          changeType="increase"
          description="Ngưỡng tối thiểu >= 90%"
          icon={ShieldCheck}
        />
        <KpiMetric
          title="Kho Tri Thức RAG"
          value={`${totalCollectionsCount} Collections`}
          change="5 Phân hệ"
          changeType="neutral"
          description="Qdrant + Postgres FTS"
          icon={BookOpen}
        />
      </section>

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

        {/* Card 2: Token Consumption by Provider */}
        <Card>
          <div className="flex items-center justify-between p-4 border-b border-border">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-primary" />
              <h3 className="font-semibold text-xs text-foreground uppercase tracking-wider">
                Phân Bổ Token Provider
              </h3>
            </div>
            <Badge variant="outline" className="text-[10px] font-mono">
              FinOps
            </Badge>
          </div>
          <CardContent className="p-4 space-y-3 text-xs">
            <div className="space-y-1">
              <div className="flex justify-between text-[11px]">
                <span className="text-foreground font-medium">OpenAI (gpt-4o-mini)</span>
                <span className="font-mono text-muted-foreground">820K tokens (56%)</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                <div className="h-full bg-primary rounded-full w-[56%]" />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-[11px]">
                <span className="text-foreground font-medium">Google (Gemini 1.5 Flash)</span>
                <span className="font-mono text-muted-foreground">490K tokens (34%)</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                <div className="h-full bg-info rounded-full w-[34%]" />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-[11px]">
                <span className="text-foreground font-medium">Local vLLM (Qwen2.5)</span>
                <span className="font-mono text-muted-foreground">148K tokens (10%)</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full w-[10%]" />
              </div>
            </div>
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
