import {
  Check,
  Copy,
  Globe,
  Layers,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { IntegrationConfig } from "@/features/modelops/types";

interface EndpointCardProps {
  config?: IntegrationConfig;
}

export function EndpointCard({ config }: EndpointCardProps) {
  const [copiedOpenAI, setCopiedOpenAI] = React.useState(false);

  if (!config) {
    return (
      <p className="text-sm text-muted-foreground">
        Chưa có cấu hình endpoint từ server.
      </p>
    );
  }
  const openAiBaseUrl = config.openai_endpoint;

  const copyToClipboard = async (
    text: string,
    setCopiedState: (v: boolean) => void,
  ) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedState(true);
      toast.success("Đã sao chép vào clipboard!");
      setTimeout(() => setCopiedState(false), 2000);
    } catch {
      toast.error("Không thể tự động sao chép.");
    }
  };

  return (
    <Card className="rounded-xl border border-border bg-card shadow-2xs overflow-hidden">
      <CardHeader className="border-b bg-muted/20 pb-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div className="flex items-center gap-2">
            <Globe className="size-4 text-primary" />
            <CardTitle className="text-sm font-semibold">
              Điểm Cuối API Tích Hợp (Endpoints)
            </CardTitle>
          </div>
          <div className="flex items-center gap-1.5">
            <Badge
              variant="outline"
              className="text-[10px] font-mono border-primary/30 text-primary"
            >
              OpenAI v1 Compatible
            </Badge>
            <Badge variant="secondary" className="text-[10px]">
              OpenAI Errors
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-4 sm:p-5 space-y-4 text-xs">
        {/* OpenAI Compatible Base URL */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <span>OpenAI Base URL</span>
              <span className="text-[11px] font-normal text-muted-foreground">
                (Dùng cho OpenAI SDK, LangChain, cURL)
              </span>
            </span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-6 gap-1 px-2 text-[11px] text-muted-foreground hover:text-foreground"
              onClick={() => copyToClipboard(openAiBaseUrl, setCopiedOpenAI)}
            >
              {copiedOpenAI ? (
                <Check className="size-3 text-emerald-500" />
              ) : (
                <Copy className="size-3" />
              )}
              <span>{copiedOpenAI ? "Đã chép" : "Sao chép"}</span>
            </Button>
          </div>

          <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 font-mono text-xs">
            <span className="flex-1 break-all select-all font-medium text-foreground">
              {openAiBaseUrl}
            </span>
          </div>
        </div>

        {/* Feature & Contract Highlights */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <div className="rounded-lg border border-border/60 bg-muted/20 p-2.5 space-y-1">
            <div className="flex items-center gap-1.5 font-medium text-foreground">
              <Sparkles className="size-3.5 text-primary" />
              <span>POST /chat/completions</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Một câu hỏi mỗi yêu cầu; dùng cấu hình trợ lý và trả lời kèm trích
              dẫn dẫn chứng.
            </p>
          </div>

          <div className="rounded-lg border border-border/60 bg-muted/20 p-2.5 space-y-1">
            <div className="flex items-center gap-1.5 font-medium text-foreground">
              <Layers className="size-3.5 text-primary" />
              <span>GET /models</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Danh sách các trợ lý AI được cấp phép trong workspace tương ứng
              với khóa API.
            </p>
          </div>

          <div className="rounded-lg border border-border/60 bg-muted/20 p-2.5 space-y-1">
            <div className="flex items-center gap-1.5 font-medium text-foreground">
              <ShieldCheck className="size-3.5 text-emerald-500" />
              <span>Bảo vệ quyền & Quota</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Định danh máy (machine actor), kiểm tra trạng thái tức thời và
              kiểm soát RPM/RPD qua Redis.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
