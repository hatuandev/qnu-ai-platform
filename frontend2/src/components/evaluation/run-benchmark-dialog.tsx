import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cpu, Play, RefreshCw, Sparkles, Zap } from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { apiClient } from "@/services/api-client";
import type { AssistantItem } from "@/types/assistants";
import type { EvaluationRunRequest } from "@/types/evaluation";

interface RunBenchmarkDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export const RunBenchmarkDialog: React.FC<RunBenchmarkDialogProps> = ({
  open,
  onOpenChange,
  onSuccess,
}) => {
  const queryClient = useQueryClient();
  const [selectedAssistant, setSelectedAssistant] =
    useState<string>("admissions");
  const [selectedDataset, setSelectedDataset] = useState<string>(
    "qnu_admissions_benchmark",
  );
  const [sampleSize, setSampleSize] = useState<number | undefined>(5);
  const [evalMethod, setEvalMethod] = useState<"heuristic" | "llm_judge">(
    "heuristic",
  );

  const { data: assistants = [] } = useQuery({
    queryKey: ["assistants-for-eval"],
    queryFn: () => apiClient.getAssistants({ includeInactive: false }),
    enabled: open,
  });

  const { data: datasets = [] } = useQuery({
    queryKey: ["datasets-for-eval"],
    queryFn: () => apiClient.getDatasets(),
    enabled: open,
  });

  // Automatically match dataset when assistant changes
  useEffect(() => {
    if (selectedAssistant) {
      const matched = datasets.find(
        (d) =>
          d.assistant_code === selectedAssistant ||
          d.id.includes(selectedAssistant),
      );
      if (matched) {
        setSelectedDataset(matched.id);
      }
    }
  }, [selectedAssistant, datasets]);

  const runMutation = useMutation({
    mutationFn: (req: EvaluationRunRequest) => apiClient.runEvaluation(req),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["evaluation-runs"] });
      queryClient.invalidateQueries({ queryKey: ["evaluation-metrics"] });
      queryClient.invalidateQueries({ queryKey: ["gap-inbox"] });
      toast.success(
        `Phiên kiểm định hoàn tất! Tỷ lệ đạt: ${(data.pass_rate * 100).toFixed(1)}% (${data.passed_cases}/${data.total_cases} câu).`,
      );
      onOpenChange(false);
      onSuccess?.();
    },
    onError: (err: Error) => {
      toast.error(`Kiểm định thất bại: ${err.message}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runMutation.mutate({
      assistant_code: selectedAssistant,
      dataset_id: selectedDataset,
      sample_size: sampleSize,
      evaluation_method: evalMethod,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base font-bold text-foreground">
            <Sparkles className="h-4 w-4 text-primary" />
            Cấu Hình Kiểm Định Chất Lượng Ragas TM-08
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Thiết lập Trợ lý AI, bộ dữ liệu benchmark chính thức và phương pháp
            chấm điểm để đo lường 3 chỉ số chuẩn Ragas TM-08.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2 text-xs">
          {/* Chọn Trợ lý AI */}
          <div className="space-y-1.5">
            <label
              htmlFor="eval-assistant-select"
              className="font-semibold text-foreground"
            >
              1. Chọn Trợ Lý AI Cần Kiểm Định
            </label>
            <select
              id="eval-assistant-select"
              value={selectedAssistant}
              onChange={(e) => setSelectedAssistant(e.target.value)}
              className="w-full h-9 px-3 rounded-md border border-border bg-background text-foreground text-xs focus:outline-hidden focus:ring-1 focus:ring-primary"
            >
              {assistants.length === 0 ? (
                <>
                  <option value="admissions">
                    Trợ lý Tuyển sinh (admissions)
                  </option>
                  <option value="regulations">
                    Trợ lý Quy chế học vụ (regulations)
                  </option>
                  <option value="library">Trợ lý Thư viện (library)</option>
                  <option value="drafting">
                    Trợ lý Soạn thảo văn bản (drafting)
                  </option>
                  <option value="exam_matrix">
                    Trợ lý Đề thi & Ma trận Bloom (exam_matrix)
                  </option>
                </>
              ) : (
                assistants.map((ast: AssistantItem) => (
                  <option key={ast.id} value={ast.code}>
                    {ast.name} ({ast.code})
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Chọn Tập Dữ Liệu Benchmark */}
          <div className="space-y-1.5">
            <label
              htmlFor="eval-dataset-select"
              className="font-semibold text-foreground"
            >
              2. Bộ Dữ Liệu Benchmark Đối Soát
            </label>
            <select
              id="eval-dataset-select"
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value)}
              className="w-full h-9 px-3 rounded-md border border-border bg-background text-foreground text-xs font-mono focus:outline-hidden focus:ring-1 focus:ring-primary"
            >
              {datasets.length === 0 ? (
                <>
                  <option value="qnu_admissions_benchmark">
                    qnu_admissions_benchmark (20 câu hỏi Tuyển sinh 2024)
                  </option>
                  <option value="qnu_regulations_benchmark">
                    qnu_regulations_benchmark (50 câu hỏi Quy chế tín chỉ QNU)
                  </option>
                  <option value="qnu_library_benchmark">
                    qnu_library_benchmark (20 câu hỏi Thư viện & Luận văn)
                  </option>
                  <option value="qnu_drafting_benchmark">
                    qnu_drafting_benchmark (20 câu hỏi Nghị định 30)
                  </option>
                  <option value="qnu_exam_benchmark">
                    qnu_exam_benchmark (20 câu hỏi Ma trận đề thi Bloom)
                  </option>
                </>
              ) : (
                datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.total_test_cases} câu hỏi)
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Chọn Số Lượng Câu Mẫu */}
          <div className="space-y-1.5">
            <span className="font-semibold text-foreground block">
              3. Số Lượng Câu Hỏi Kiểm Tra
            </span>
            <div className="flex flex-wrap gap-2">
              {[
                { label: "5 câu mẫu (Nhanh)", value: 5 },
                { label: "10 câu", value: 10 },
                { label: "20 câu", value: 20 },
                { label: "Toàn bộ", value: undefined },
              ].map((opt) => (
                <Button
                  key={opt.label}
                  type="button"
                  variant={sampleSize === opt.value ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSampleSize(opt.value)}
                  className="h-7 text-xs px-2.5 rounded-md"
                >
                  {opt.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Chọn Phương Pháp Đánh Giá */}
          <div className="space-y-1.5">
            <span className="font-semibold text-foreground block">
              4. Phương Pháp Thẩm Định TM-08
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setEvalMethod("heuristic")}
                className={`p-2.5 rounded-lg border text-left transition-all ${
                  evalMethod === "heuristic"
                    ? "border-primary bg-primary/5 ring-1 ring-primary"
                    : "border-border bg-card hover:border-border/80"
                }`}
              >
                <div className="flex items-center gap-1.5 font-semibold text-foreground">
                  <Zap className="h-3.5 w-3.5 text-amber-500" />
                  <span>Heuristic Nhanh</span>
                  <Badge
                    variant="outline"
                    className="text-[9px] h-4 px-1 ml-auto"
                  >
                    Khuyến nghị
                  </Badge>
                </div>
                <p className="text-[11px] text-muted-foreground mt-1 leading-snug">
                  Đo lường n-gram & từ khóa tức thì (~1-2s). 0 tốn token LLM,
                  phù hợp CI/CD và kiểm tra thường xuyên.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setEvalMethod("llm_judge")}
                className={`p-2.5 rounded-lg border text-left transition-all ${
                  evalMethod === "llm_judge"
                    ? "border-primary bg-primary/5 ring-1 ring-primary"
                    : "border-border bg-card hover:border-border/80"
                }`}
              >
                <div className="flex items-center gap-1.5 font-semibold text-foreground">
                  <Cpu className="h-3.5 w-3.5 text-primary" />
                  <span>LLM-as-a-Judge</span>
                </div>
                <p className="text-[11px] text-muted-foreground mt-1 leading-snug">
                  Mô hình LLM thẩm định ngữ nghĩa sâu sắc theo rubric TM-08 ĐH
                  Quy Nhơn và giải thích lý do chấm điểm.
                </p>
              </button>
            </div>
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              className="h-8 text-xs"
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={runMutation.isPending}
              className="h-8 gap-1.5 text-xs"
            >
              {runMutation.isPending ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Play className="h-3.5 w-3.5" />
              )}
              <span>
                {runMutation.isPending
                  ? "Đang Chạy Kiểm Định..."
                  : "Bắt Đầu Kiểm Định"}
              </span>
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
