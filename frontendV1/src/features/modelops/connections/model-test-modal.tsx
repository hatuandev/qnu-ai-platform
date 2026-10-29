import { Bot, CheckCircle2, Clock, FlaskConical, Loader2, Sparkles, XCircle } from "lucide-react";
import { useState } from "react";
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
import { useRunDiagnostic } from "../diagnostic-queries";
import type { Capability, Provider } from "../types";

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
}) {
  const [result, setResult] = useState<{
    outcome: "ok" | "failed" | "unsupported" | null;
    latencyMs?: number | null;
    detail?: string;
    tokens?: number | null;
  }>({ outcome: null });

  const runDiagnostic = useRunDiagnostic(model?.id ?? "");

  const handleRunTest = async () => {
    if (!model) return;
    setResult({ outcome: null });
    try {
      const capability: Capability = model.capabilities.includes("chat")
        ? "chat"
        : ((model.capabilities[0] as Capability) ?? "chat");
      const check = await runDiagnostic.mutateAsync(capability);
      setResult({
        outcome: check.outcome,
        latencyMs: check.latency_ms,
        detail: check.detail || (check.outcome === "ok" ? "Phản hồi thành công từ mô hình LLM." : "Thất bại."),
        tokens: check.total_tokens,
      });
    } catch (err: unknown) {
      setResult({
        outcome: "failed",
        detail: err instanceof Error ? err.message : "Kiểm tra thất bại.",
      });
    }
  };

  if (!model) return null;

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] max-w-lg flex-col gap-0 overflow-hidden p-0 text-xs">
        <ResponsiveDialogHeader className="border-b bg-muted/20 p-5">
          <div className="flex items-center gap-2.5">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <FlaskConical className="size-4" />
            </div>
            <div>
              <ResponsiveDialogTitle>Kiểm thử Model LLM</ResponsiveDialogTitle>
              <ResponsiveDialogDescription className="text-xs">
                Chạy kiểm tra gọi thử nghiệm đến model {model.model_name} qua {connectionName}.
              </ResponsiveDialogDescription>
            </div>
          </div>
        </ResponsiveDialogHeader>

        <div className="p-5 space-y-4 overflow-y-auto">
          {/* Model Info Card */}
          <Card className="p-3.5 bg-muted/30 border-border/80 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bot className="size-4 text-primary" />
                <span className="font-semibold text-foreground text-sm font-mono">
                  {model.model_name}
                </span>
              </div>
              <Badge variant="outline" className="text-[10px]">
                {model.capabilities.join(", ")}
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground font-mono truncate">
              Endpoint: {model.base_url}
            </p>
          </Card>

          {/* Test Action */}
          <div className="flex items-center justify-between pt-1">
            <p className="text-muted-foreground text-xs">
              Gửi yêu cầu prompt suy luận mẫu để đo lường độ trễ và khả năng phản hồi.
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
                <div className="flex items-center gap-4 text-muted-foreground font-mono text-[11px] pt-1 border-t border-border/60">
                  {result.latencyMs != null && (
                    <span className="flex items-center gap-1">
                      <Clock className="size-3" />
                      Độ trễ: {result.latencyMs} ms
                    </span>
                  )}
                  {result.tokens != null && (
                    <span>Tokens: {result.tokens}</span>
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
        </div>

        <ResponsiveDialogFooter className="border-t bg-card p-4 flex justify-end">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Đóng
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

