import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Award,
  BookOpen,
  CheckCircle2,
  HelpCircle,
  Inbox,
  Play,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  XCircle,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import { EmptyState } from "../components/admin/empty-state";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "../components/ui/tabs";
import { type EvaluationRunItem, type GapInboxItem, apiClient } from "../services/api-client";

export const EvaluationPage: React.FC<{ onNavigateToKnowledge?: () => void }> = ({
  onNavigateToKnowledge,
}) => {
  const [activeTab, setActiveTab] = useState<string>("gauges");
  const [resolvedGaps, setResolvedGaps] = useState<string[]>([]);
  const [isRunningEval, setIsRunningEval] = useState(false);
  const queryClient = useQueryClient();

  const { data: metrics } = useQuery({
    queryKey: ["evaluation-metrics"],
    queryFn: () => apiClient.getEvaluationMetrics(),
  });

  const { data: runs = [], isLoading: isLoadingRuns } = useQuery({
    queryKey: ["evaluation-runs"],
    queryFn: () => apiClient.getEvaluationRuns(),
  });

  const { data: gapItems = [] } = useQuery({
    queryKey: ["gap-inbox"],
    queryFn: () => apiClient.getGapInbox(),
  });

  const handleRunEvaluation = async () => {
    try {
      setIsRunningEval(true);
      await apiClient.runEvaluation({
        assistant_code: "admissions",
        dataset_id: "qnu_admissions_benchmark",
        sample_size: 5,
      });
      await queryClient.invalidateQueries({ queryKey: ["evaluation-runs"] });
      await queryClient.invalidateQueries({ queryKey: ["evaluation-metrics"] });
      await queryClient.invalidateQueries({ queryKey: ["gap-inbox"] });
    } catch (err) {
      console.error("Lỗi khi chạy benchmark kiểm định:", err);
    } finally {
      setIsRunningEval(false);
    }
  };

  const handleResolve = (id: string) => {
    setResolvedGaps((prev) => [...prev, id]);
  };

  const totalEvals = metrics?.total_evaluations ?? 0;
  const hasRuns = totalEvals > 0;
  const faithfulnessPct = hasRuns ? ((metrics?.faithfulness ?? 0) * 100).toFixed(1) : "0.0";
  const relevancePct = hasRuns ? ((metrics?.answer_relevance ?? 0) * 100).toFixed(1) : "0.0";
  const precisionPct = hasRuns ? ((metrics?.context_precision ?? 0) * 100).toFixed(1) : "0.0";

  const isFaithful =
    hasRuns && (metrics?.faithfulness ?? 0) >= (metrics?.target_faithfulness ?? 0.9);
  const isRelevant =
    hasRuns && (metrics?.answer_relevance ?? 0) >= (metrics?.target_relevance ?? 0.85);
  const isPrecise =
    hasRuns && (metrics?.context_precision ?? 0) >= (metrics?.target_precision ?? 0.8);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            Kiểm Định Chất Lượng Ragas TM-08 & Gap Inbox
            <Badge variant="outline" className="font-mono text-xs text-primary border-primary/30">
              Tiêu Chuẩn TM-08
            </Badge>
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Đo lường định lượng 3 chỉ số Ragas tự động: Độ trung thực (Faithfulness), Độ liên quan
            (Relevance), Độ chính xác ngữ cảnh (Context Precision) và đối soát lỗ hổng tri thức.
          </p>
        </div>

        <Button
          size="sm"
          onClick={handleRunEvaluation}
          disabled={isRunningEval}
          className="h-9 gap-1.5 text-xs self-start sm:self-auto shrink-0"
        >
          {isRunningEval ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          <span>{isRunningEval ? "Đang Kiểm Định..." : "Chạy Benchmark TM-08"}</span>
        </Button>
      </div>

      {/* 3 Ragas TM-08 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Metric 1: Faithfulness */}
        <Card className="p-4 space-y-2 border-l-4 border-l-primary hover:border-primary/50 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <ShieldCheck className="h-4 w-4 text-primary" />
              Độ Trung Thực (Faithfulness)
            </span>
            <Badge variant={isFaithful ? "success" : "secondary"} className="text-[10px]">
              {isFaithful ? "Đạt Chuẩn" : hasRuns ? "Chưa Đạt" : "Chưa Đo"}
            </Badge>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-foreground font-mono">{faithfulnessPct}%</span>
            <span className="text-xs text-muted-foreground font-mono">/ Mục tiêu &ge; 90%</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(100, Math.max(0, Number.parseFloat(faithfulnessPct)))}%`,
              }}
            />
          </div>
          <p className="text-[11px] text-muted-foreground">
            Mức độ câu trả lời bám sát 100% tài liệu chính thức, không bịa đặt số liệu.
          </p>
        </Card>

        {/* Metric 2: Answer Relevance */}
        <Card className="p-4 space-y-2 border-l-4 border-l-info hover:border-info/50 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Award className="h-4 w-4 text-info" />
              Độ Liên Quan (Answer Relevance)
            </span>
            <Badge variant={isRelevant ? "success" : "secondary"} className="text-[10px]">
              {isRelevant ? "Đạt Chuẩn" : hasRuns ? "Chưa Đạt" : "Chưa Đo"}
            </Badge>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-foreground font-mono">{relevancePct}%</span>
            <span className="text-xs text-muted-foreground font-mono">/ Mục tiêu &ge; 85%</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-info rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, Number.parseFloat(relevancePct)))}%` }}
            />
          </div>
          <p className="text-[11px] text-muted-foreground">
            Câu trả lời giải quyết trực diện câu hỏi, không lan man thừa thông tin.
          </p>
        </Card>

        {/* Metric 3: Context Precision */}
        <Card className="p-4 space-y-2 border-l-4 border-l-emerald-500 hover:border-emerald-500/50 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-emerald-500" />
              Độ Chính Xác Ngữ Cảnh (Precision)
            </span>
            <Badge variant={isPrecise ? "success" : "secondary"} className="text-[10px]">
              {isPrecise ? "Đạt Chuẩn" : hasRuns ? "Chưa Đạt" : "Chưa Đo"}
            </Badge>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-foreground font-mono">{precisionPct}%</span>
            <span className="text-xs text-muted-foreground font-mono">/ Mục tiêu &ge; 80%</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-emerald-500 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, Number.parseFloat(precisionPct)))}%` }}
            />
          </div>
          <p className="text-[11px] text-muted-foreground">
            Các đoạn văn bản truy xuất bởi RRF và Reranker nằm ở top 3 vị trí đầu.
          </p>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-muted p-1 rounded-control">
          <TabsTrigger value="gauges" className="text-xs px-3 py-1.5">
            Lịch Sử Kiểm Định Ragas ({runs.length} runs)
          </TabsTrigger>
          <TabsTrigger value="gap-inbox" className="text-xs px-3 py-1.5 gap-1.5">
            <Inbox className="h-3.5 w-3.5" />
            <span>Hộp Thư Thiếu Tri Thức (Gap Inbox)</span>
            <Badge variant="warning" className="text-[10px] h-4 px-1 ml-1">
              {gapItems.filter((g) => !resolvedGaps.includes(g.id)).length}
            </Badge>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Test Runs Table */}
        {activeTab === "gauges" && (
          <div>
            {isLoadingRuns ? (
              <div className="p-8 text-center text-xs text-muted-foreground">
                <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2" />
                Đang tải dữ liệu kiểm định...
              </div>
            ) : runs.length === 0 ? (
              <EmptyState
                icon={ShieldCheck}
                title="Chưa có phiên kiểm định nào"
                description="Hệ thống chưa ghi nhận lần kiểm định tự động nào từ cơ sở dữ liệu. Hãy kích hoạt benchmark để đo lường 3 chỉ số Ragas TM-08."
                action={
                  <Button
                    size="sm"
                    onClick={handleRunEvaluation}
                    disabled={isRunningEval}
                    className="h-8 gap-1.5 text-xs"
                  >
                    {isRunningEval ? (
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Play className="h-3.5 w-3.5" />
                    )}
                    <span>Kích Hoạt Kiểm Định Ngay</span>
                  </Button>
                }
              />
            ) : (
              <div className="rounded-surface border border-border bg-card overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Tập Dữ Liệu Benchmark</TableHead>
                      <TableHead>Trợ Lý</TableHead>
                      <TableHead>Số Câu Test</TableHead>
                      <TableHead>Tỷ Lệ Đạt</TableHead>
                      <TableHead>Faithfulness</TableHead>
                      <TableHead>Relevance</TableHead>
                      <TableHead>Precision</TableHead>
                      <TableHead>Chuẩn TM-08</TableHead>
                      <TableHead>Thời Gian</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {runs.map((r: EvaluationRunItem) => (
                      <TableRow key={r.id}>
                        <TableCell className="font-medium text-xs font-mono">
                          {r.dataset_id}
                        </TableCell>
                        <TableCell className="text-xs">{r.assistant_code}</TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {r.passed_cases}/{r.total_cases} câu
                        </TableCell>
                        <TableCell className="font-mono text-xs font-semibold">
                          {(r.pass_rate * 100).toFixed(1)}%
                        </TableCell>
                        <TableCell className="font-mono text-xs font-bold text-primary">
                          {r.faithfulness_avg.toFixed(3)}
                        </TableCell>
                        <TableCell className="font-mono text-xs font-bold text-info">
                          {r.answer_relevance_avg.toFixed(3)}
                        </TableCell>
                        <TableCell className="font-mono text-xs font-bold text-emerald-500">
                          {r.context_precision_avg.toFixed(3)}
                        </TableCell>
                        <TableCell>
                          {r.meets_tm08_standard ? (
                            <Badge variant="success" className="text-[10px] gap-1">
                              <CheckCircle2 className="h-3 w-3" /> Đạt
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="text-[10px] gap-1">
                              <XCircle className="h-3 w-3" /> Chưa Đạt
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-[11px] text-muted-foreground font-mono">
                          {r.created_at ? new Date(r.created_at).toLocaleDateString("vi-VN") : ""}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Gap Inbox */}
        {activeTab === "gap-inbox" && (
          <div className="space-y-3">
            <div className="p-3.5 rounded-surface bg-muted/40 border border-border text-xs text-muted-foreground flex items-center justify-between">
              <span>
                Các câu hỏi dưới đây đã kích hoạt <strong>No-Answer Policy</strong> do tài liệu
                trong Kho tri thức chưa đề cập. Cán bộ phụ trách có thể bấm để nạp bổ sung văn bản
                quy phạm tương ứng.
              </span>
              {onNavigateToKnowledge && (
                <Button
                  size="sm"
                  onClick={onNavigateToKnowledge}
                  className="h-7 text-xs gap-1 shrink-0 ml-3"
                >
                  <Plus className="h-3 w-3" />
                  <span>Nạp Tri Thức Bổ Sung</span>
                </Button>
              )}
            </div>

            {gapItems.length === 0 ? (
              <EmptyState
                icon={Inbox}
                title="Hộp thư thiếu tri thức trống"
                description="Hiện tại chưa có câu hỏi nào kích hoạt No-Answer Policy. Tất cả câu hỏi đã được đối soát chính xác từ kho tài liệu chính thức."
              />
            ) : (
              <div className="grid grid-cols-1 gap-3">
                {gapItems.map((item: GapInboxItem) => {
                  const isResolved = resolvedGaps.includes(item.id);
                  return (
                    <Card
                      key={item.id}
                      className={`p-4 transition-all ${
                        isResolved ? "opacity-50 bg-muted/20" : "hover:border-primary/50"
                      }`}
                    >
                      <CardContent className="p-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                        <div className="space-y-1.5 flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <HelpCircle className="h-4 w-4 text-warning shrink-0" />
                            <h4 className="font-bold text-foreground truncate">
                              "{item.question}"
                            </h4>
                            <Badge variant="outline" className="text-[10px] font-mono shrink-0">
                              {item.assistant_name}
                            </Badge>
                            <Badge variant="secondary" className="text-[10px] shrink-0 font-mono">
                              Hỏi {item.frequency} lần
                            </Badge>
                          </div>
                          <p className="text-muted-foreground text-[11px] leading-relaxed pl-6">
                            Nguyên nhân thiếu: {item.reason}
                          </p>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {isResolved ? (
                            <span className="text-success font-medium text-xs flex items-center gap-1">
                              <CheckCircle2 className="h-3.5 w-3.5" /> Đã xử lý
                            </span>
                          ) : (
                            <>
                              {onNavigateToKnowledge && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={onNavigateToKnowledge}
                                  className="h-7 text-xs text-primary gap-1"
                                >
                                  <BookOpen className="h-3 w-3" />
                                  <span>Bổ sung vào RAG</span>
                                </Button>
                              )}
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleResolve(item.id)}
                                className="h-7 text-xs text-muted-foreground hover:text-foreground"
                              >
                                Bỏ qua
                              </Button>
                            </>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </Tabs>
    </div>
  );
};
