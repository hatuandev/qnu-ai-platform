import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { apiClient } from "@/services/api-client";
import type { EvaluationResultItem } from "@/types/evaluation";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Award,
  CheckCircle2,
  Clock,
  Cpu,
  HelpCircle,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  XCircle,
  Zap,
} from "lucide-react";
import type React from "react";
import { useState } from "react";

interface EvaluationRunDetailSheetProps {
  runId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const EvaluationRunDetailSheet: React.FC<EvaluationRunDetailSheetProps> = ({
  runId,
  open,
  onOpenChange,
}) => {
  const [filterStatus, setFilterStatus] = useState<"all" | "passed" | "failed">("all");

  const { data: runDetail, isLoading } = useQuery({
    queryKey: ["evaluation-run-detail", runId],
    queryFn: () =>
      runId ? apiClient.getRunDetail(runId) : Promise.reject(new Error("runId is required")),
    enabled: !!runId && open,
  });

  const filteredItems = (runDetail?.items || []).filter((item: EvaluationResultItem) => {
    if (filterStatus === "passed") return item.passed_all_criteria;
    if (filterStatus === "failed") return !item.passed_all_criteria;
    return true;
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto p-6 space-y-5">
        <SheetHeader className="space-y-1.5 border-b border-border pb-4">
          <div className="flex flex-wrap items-center justify-between gap-2 pr-6">
            <SheetTitle className="text-base font-bold text-foreground flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-primary" />
              Chi Tiết Phiên Kiểm Định Ragas TM-08
            </SheetTitle>
            {runDetail?.meets_tm08_standard ? (
              <Badge variant="success" className="text-xs gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" /> Đạt Chuẩn TM-08
              </Badge>
            ) : (
              <Badge variant="secondary" className="text-xs gap-1">
                <XCircle className="h-3.5 w-3.5" /> Chưa Đạt Chuẩn
              </Badge>
            )}
          </div>
          <SheetDescription className="text-xs text-muted-foreground flex flex-wrap items-center gap-3">
            <span className="font-mono text-foreground font-semibold">{runDetail?.dataset_id}</span>
            <span>•</span>
            <span>
              Trợ lý: <strong className="text-foreground">{runDetail?.assistant_code}</strong>
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {runDetail?.created_at ? new Date(runDetail.created_at).toLocaleString("vi-VN") : ""}
            </span>
            <span>•</span>
            <Badge variant="outline" className="text-[10px] font-mono gap-1">
              {runDetail?.evaluation_method === "llm_judge" ? (
                <>
                  <Cpu className="h-2.5 w-2.5 text-primary" /> LLM-Judge
                </>
              ) : (
                <>
                  <Zap className="h-2.5 w-2.5 text-amber-500" /> Heuristic
                </>
              )}
            </Badge>
          </SheetDescription>
        </SheetHeader>

        {isLoading ? (
          <div className="py-12 text-center text-xs text-muted-foreground">
            <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-primary" />
            Đang tải dữ liệu chi tiết từng câu hỏi...
          </div>
        ) : !runDetail ? (
          <div className="py-8 text-center text-xs text-muted-foreground">
            Không tìm thấy thông tin chi tiết phiên kiểm định.
          </div>
        ) : (
          <div className="space-y-5">
            {/* 3 Metrics Summary Cards */}
            <div className="grid grid-cols-3 gap-2.5">
              <div className="p-3 rounded-lg border border-border bg-card space-y-1">
                <span className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                  <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                  Faithfulness
                </span>
                <div className="flex items-baseline gap-1">
                  <span className="text-lg font-bold font-mono text-primary">
                    {(runDetail.faithfulness_avg * 100).toFixed(1)}%
                  </span>
                  <span className="text-[10px] text-muted-foreground">&ge;90%</span>
                </div>
              </div>

              <div className="p-3 rounded-lg border border-border bg-card space-y-1">
                <span className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                  <Award className="h-3.5 w-3.5 text-info" />
                  Relevance
                </span>
                <div className="flex items-baseline gap-1">
                  <span className="text-lg font-bold font-mono text-info">
                    {(runDetail.answer_relevance_avg * 100).toFixed(1)}%
                  </span>
                  <span className="text-[10px] text-muted-foreground">&ge;85%</span>
                </div>
              </div>

              <div className="p-3 rounded-lg border border-border bg-card space-y-1">
                <span className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                  <Sparkles className="h-3.5 w-3.5 text-emerald-500" />
                  Precision
                </span>
                <div className="flex items-baseline gap-1">
                  <span className="text-lg font-bold font-mono text-emerald-500">
                    {(runDetail.context_precision_avg * 100).toFixed(1)}%
                  </span>
                  <span className="text-[10px] text-muted-foreground">&ge;80%</span>
                </div>
              </div>
            </div>

            {/* Filter Toolbar */}
            <div className="flex items-center justify-between text-xs pt-1">
              <span className="font-semibold text-foreground">
                Danh Sách Câu Hỏi Kiểm Định ({filteredItems.length} / {runDetail.total_cases} câu)
              </span>
              <div className="flex items-center gap-1 bg-muted p-0.5 rounded-md">
                {(["all", "passed", "failed"] as const).map((st) => (
                  <Button
                    key={st}
                    type="button"
                    variant={filterStatus === st ? "default" : "ghost"}
                    size="sm"
                    onClick={() => setFilterStatus(st)}
                    className="h-6 text-[11px] px-2"
                  >
                    {st === "all" ? "Tất cả" : st === "passed" ? "Đạt" : "Chưa đạt"}
                  </Button>
                ))}
              </div>
            </div>

            {/* Question Items List */}
            {filteredItems.length === 0 ? (
              <div className="p-6 text-center text-xs text-muted-foreground border border-dashed border-border rounded-lg">
                Không có câu hỏi nào thỏa mãn bộ lọc.
              </div>
            ) : (
              <div className="space-y-3">
                {filteredItems.map((item: EvaluationResultItem, idx: number) => (
                  <Card
                    key={item.id}
                    className={`border transition-all ${
                      item.passed_all_criteria
                        ? "border-border hover:border-primary/40 bg-card"
                        : "border-destructive/30 bg-destructive/5 hover:border-destructive/50"
                    }`}
                  >
                    <CardContent className="p-4 space-y-3 text-xs">
                      {/* Header of Item */}
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-mono font-bold text-muted-foreground text-[11px]">
                            #{idx + 1}
                          </span>
                          <span className="font-semibold text-foreground truncate max-w-sm">
                            {item.query}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <Badge
                            variant={item.passed_all_criteria ? "success" : "secondary"}
                            className="text-[10px] gap-1"
                          >
                            {item.passed_all_criteria ? (
                              <>
                                <CheckCircle2 className="h-3 w-3" /> Đạt
                              </>
                            ) : (
                              <>
                                <XCircle className="h-3 w-3" /> Chưa Đạt
                              </>
                            )}
                          </Badge>
                          {item.is_refusal && (
                            <Badge variant="warning" className="text-[10px] gap-0.5">
                              <AlertTriangle className="h-2.5 w-2.5" /> No-Answer
                            </Badge>
                          )}
                          {item.is_hallucinated && (
                            <Badge variant="destructive" className="text-[10px] gap-0.5">
                              <ShieldAlert className="h-2.5 w-2.5" /> Hallucination
                            </Badge>
                          )}
                        </div>
                      </div>

                      {/* Question Content */}
                      <div className="space-y-1 bg-muted/40 p-2.5 rounded-md text-[11px]">
                        <div className="flex items-start gap-1.5">
                          <HelpCircle className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" />
                          <span className="text-foreground font-medium">{item.query}</span>
                        </div>
                        {item.ground_truth && (
                          <div className="text-muted-foreground pl-5 text-[11px] leading-relaxed">
                            <strong>Kỳ vọng (Ground Truth):</strong> {item.ground_truth}
                          </div>
                        )}
                      </div>

                      {/* Generated Answer */}
                      <div className="space-y-1 pl-1">
                        <span className="text-[11px] font-semibold text-foreground flex items-center gap-1.5">
                          Phản hồi của Trợ lý:
                          <Badge
                            variant="outline"
                            className="text-[9px] font-mono h-3.5 px-1 text-muted-foreground"
                          >
                            {item.execution_path}
                          </Badge>
                        </span>
                        <p className="text-[11px] text-foreground/90 bg-card border border-border p-2.5 rounded-md whitespace-pre-wrap leading-relaxed">
                          {item.generated_answer || "(Không có phản hồi)"}
                        </p>
                      </div>

                      {/* Scores Strip */}
                      <div className="grid grid-cols-3 gap-2 pt-1 border-t border-border text-[11px]">
                        <div className="flex items-center justify-between bg-muted/30 px-2 py-1 rounded">
                          <span className="text-muted-foreground">Faithfulness:</span>
                          <strong className="font-mono text-primary">
                            {(item.faithfulness_score * 100).toFixed(0)}%
                          </strong>
                        </div>
                        <div className="flex items-center justify-between bg-muted/30 px-2 py-1 rounded">
                          <span className="text-muted-foreground">Relevance:</span>
                          <strong className="font-mono text-info">
                            {(item.answer_relevance_score * 100).toFixed(0)}%
                          </strong>
                        </div>
                        <div className="flex items-center justify-between bg-muted/30 px-2 py-1 rounded">
                          <span className="text-muted-foreground">Precision:</span>
                          <strong className="font-mono text-emerald-500">
                            {(item.context_precision_score * 100).toFixed(0)}%
                          </strong>
                        </div>
                      </div>

                      {/* Reasoning / Explanation */}
                      {item.reasoning && (
                        <div className="text-[11px] text-muted-foreground bg-muted/20 p-2 rounded border border-border/50">
                          <strong>Nhận xét:</strong> {item.reasoning}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
};
