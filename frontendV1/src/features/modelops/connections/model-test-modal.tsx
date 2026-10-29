import {
  ArrowUpDown,
  Bot,
  CheckCircle2,
  Clock,
  FileText,
  FlaskConical,
  Layers,
  Loader2,
  Sparkles,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useRunDiagnostic } from "../diagnostic-queries";
import type { Capability, Provider } from "../types";

const CAPABILITY_CONFIG: Record<
  Capability,
  {
    name: string;
    title: string;
    description: string;
    icon: typeof Bot;
    color: string;
    testDesc: string;
  }
> = {
  chat: {
    name: "Trò chuyện (Chat)",
    title: "Kiểm thử Mô hình Chat (LLM)",
    description:
      "Gửi prompt suy luận mẫu để đo lường độ trễ và khả năng phản hồi hội thoại.",
    icon: Bot,
    color: "text-blue-500",
    testDesc:
      "Gửi yêu cầu prompt suy luận mẫu để đo lường độ trễ và khả năng phản hồi.",
  },
  embedding: {
    name: "Nhúng ngữ nghĩa (Embedding)",
    title: "Kiểm thử Mô hình Nhúng (Embedding)",
    description:
      "Gửi đoạn văn bản mẫu để tạo vector nhúng và kiểm tra chiều vector (dimension).",
    icon: Layers,
    color: "text-amber-500",
    testDesc:
      "Gửi văn bản mẫu qua /v1/embeddings để kiểm tra vector nhúng và đo kích thước chiều không gian.",
  },
  rerank: {
    name: "Xếp hạng lại (Reranking)",
    title: "Kiểm thử Mô hình Xếp hạng lại (Reranking)",
    description:
      "Gửi câu truy vấn và danh sách tài liệu mẫu để kiểm tra tính điểm liên quan (relevance score).",
    icon: ArrowUpDown,
    color: "text-emerald-500",
    testDesc:
      "Gửi câu truy vấn và tài liệu mẫu qua /v1/rerank để kiểm tra thuật toán chấm điểm độ liên quan.",
  },
  ocr: {
    name: "Nhận dạng văn bản (OCR)",
    title: "Kiểm thử Mô hình Nhận dạng Văn bản (OCR)",
    description:
      "Gửi ảnh tài liệu mẫu để kiểm tra bóc tách văn bản quang học và xác thực tọa độ bounding boxes.",
    icon: FileText,
    color: "text-rose-500",
    testDesc:
      "Gửi trang tài liệu mẫu để bóc tách văn bản và kiểm tra định vị tọa độ khối văn bản.",
  },
};

export function ModelTestModal({
  open,
  onOpenChange,
  model,
  connectionName,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  model: Provider | null;
  connectionName: string;
  onUpdated?: () => void;
}) {
  const [selectedCapability, setSelectedCapability] = useState<Capability>("chat");

  const [result, setResult] = useState<{
    outcome: "ok" | "failed" | "unsupported" | null;
    latencyMs?: number | null;
    detail?: string;
    tokens?: number | null;
    dimension?: number | null;
    observedModel?: string | null;
  }>({ outcome: null });

  const runDiagnostic = useRunDiagnostic(model?.id ?? "");

  // Sync initial capability from model
  useEffect(() => {
    if (model) {
      setResult({ outcome: null });
      if (model.capabilities && model.capabilities.length > 0) {
        setSelectedCapability(model.capabilities[0] as Capability);
      } else {
        setSelectedCapability("chat");
      }
    }
  }, [model]);

  if (!model) return null;

  const currentCapConfig =
    CAPABILITY_CONFIG[selectedCapability] ?? CAPABILITY_CONFIG.chat;
  const CapIcon = currentCapConfig.icon;

  const handleRunTest = async () => {
    if (!model) return;
    setResult({ outcome: null });
    try {
      const check = await runDiagnostic.mutateAsync(selectedCapability);
      setResult({
        outcome: check.outcome,
        latencyMs: check.latency_ms,
        detail:
          check.detail ||
          (check.outcome === "ok"
            ? "Kiểm thử thành công hợp đồng của chức năng."
            : "Thất bại."),
        tokens: check.total_tokens,
        dimension: check.observed_dimension,
        observedModel: check.observed_model,
      });
    } catch (err: unknown) {
      setResult({
        outcome: "failed",
        detail: err instanceof Error ? err.message : "Kiểm tra thất bại.",
      });
    }
  };

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] max-w-lg flex-col gap-0 overflow-hidden p-0 text-xs">
        <ResponsiveDialogHeader className="border-b bg-muted/20 p-5">
          <div className="flex items-center gap-2.5">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <FlaskConical className="size-4" />
            </div>
            <div>
              <ResponsiveDialogTitle>
                {currentCapConfig.title}
              </ResponsiveDialogTitle>
              <ResponsiveDialogDescription className="text-xs">
                Chạy kiểm tra gọi thử nghiệm đến model {model.model_name} qua{" "}
                {connectionName}.
              </ResponsiveDialogDescription>
            </div>
          </div>
        </ResponsiveDialogHeader>

        <div className="p-5 space-y-4 overflow-y-auto">
          {/* Model Info Card */}
          <Card className="p-3.5 bg-muted/30 border-border/80 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CapIcon className={`size-4 ${currentCapConfig.color}`} />
                <span className="font-semibold text-foreground text-sm font-mono">
                  {model.model_name}
                </span>
              </div>
              <Badge variant="outline" className="text-[10px]">
                {model.capabilities.map((c) => CAPABILITY_CONFIG[c as Capability]?.name ?? c).join(", ")}
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground font-mono truncate">
              Endpoint: {model.base_url}
            </p>
          </Card>

          {/* Capability Selector if model has multiple or user wants to switch */}
          {model.capabilities.length > 1 && (
            <div className="space-y-1.5">
              <label className="text-[11px] font-medium text-muted-foreground">
                Chức năng kiểm thử
              </label>
              <Select
                value={selectedCapability}
                onValueChange={(val) => {
                  setSelectedCapability(val as Capability);
                  setResult({ outcome: null });
                }}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="Chọn chức năng..." />
                </SelectTrigger>
                <SelectContent>
                  {model.capabilities.map((cap) => (
                    <SelectItem key={cap} value={cap}>
                      {CAPABILITY_CONFIG[cap as Capability]?.name ?? cap}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Test Action */}
          <div className="flex items-center justify-between pt-1 gap-3">
            <p className="text-muted-foreground text-xs leading-relaxed">
              {currentCapConfig.testDesc}
            </p>
            <Button
              size="sm"
              className="gap-1.5 shrink-0"
              disabled={runDiagnostic.isPending}
              onClick={handleRunTest}
            >
              {runDiagnostic.isPending ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang test...</span>
                </>
              ) : (
                <>
                  <Sparkles className="size-3.5" />
                  <span>Chạy kiểm thử</span>
                </>
              )}
            </Button>
          </div>

          {/* Result Display */}
          {result.outcome === "ok" && (
            <Alert className="border-success/40 bg-success/10 p-3.5 space-y-1">
              <div className="flex items-center gap-2 text-success font-semibold">
                <CheckCircle2 className="size-4" />
                <span>Kiểm thử thành công!</span>
              </div>
              <AlertDescription className="text-foreground text-xs space-y-2 mt-1">
                <p>{result.detail}</p>
                <div className="flex flex-wrap items-center gap-4 text-muted-foreground font-mono text-[11px] pt-1 border-t border-border/60">
                  {result.latencyMs != null && (
                    <span className="flex items-center gap-1">
                      <Clock className="size-3" />
                      Độ trễ: {result.latencyMs} ms
                    </span>
                  )}
                  {result.dimension != null && (
                    <span className="font-semibold text-primary">
                      Chiều vector (Dimension): {result.dimension}
                    </span>
                  )}
                  {result.tokens != null && (
                    <span>Tokens: {result.tokens}</span>
                  )}
                  {result.observedModel && (
                    <span>Model: {result.observedModel}</span>
                  )}
                </div>
              </AlertDescription>
            </Alert>
          )}

          {result.outcome === "failed" && (
            <Alert variant="destructive" className="p-3.5 space-y-1">
              <div className="flex items-center gap-2 font-semibold">
                <XCircle className="size-4" />
                <span>Kiểm thử thất bại</span>
              </div>
              <AlertDescription className="text-xs mt-1">
                {result.detail}
              </AlertDescription>
            </Alert>
          )}

          {result.outcome === "unsupported" && (
            <Alert variant="warning" className="p-3.5 space-y-1 border-amber-500/50 bg-amber-500/10">
              <div className="flex items-center gap-2 font-semibold text-amber-600">
                <XCircle className="size-4" />
                <span>Chưa hỗ trợ kiểm thử</span>
              </div>
              <AlertDescription className="text-xs mt-1 text-muted-foreground">
                {result.detail}
              </AlertDescription>
            </Alert>
          )}
        </div>

        <ResponsiveDialogFooter className="border-t bg-card p-4 flex justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
          >
            Đóng
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
