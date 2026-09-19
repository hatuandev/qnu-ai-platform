import {
  Bot,
  Check,
  Code,
  Copy,
  ExternalLink,
  MessageSquare,
  Share2,
  Sparkles,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";

export const ChannelsPage: React.FC = () => {
  const [selectedAssistant, setSelectedAssistant] = useState("ast_admissions");
  const [widgetTitle, setWidgetTitle] = useState("Trợ lý Tuyển sinh QNU");
  const [position, setPosition] = useState<"bottom-right" | "bottom-left">("bottom-right");
  const [welcomeMessage, setWelcomeMessage] = useState(
    "Xin chào! Mình có thể giúp gì cho bạn về thông tin tuyển sinh QNU?"
  );
  const [copied, setCopied] = useState(false);

  const originUrl =
    typeof window !== "undefined" ? window.location.origin : "https://ai.qnu.edu.vn";
  const embedScript = `<!-- QNU AI Platform — Standalone Web Chat Widget ĐH Quy Nhơn -->
<script
  src="${originUrl}/embed/qnu-chat-widget.js"
  data-assistant="${selectedAssistant}"
  data-title="${widgetTitle}"
  data-position="${position}"
  data-welcome="${welcomeMessage}"
  data-api-base="${originUrl}"
  defer>
</script>`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(embedScript);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
          Kênh Phân Phối & Mã Nhúng Web Chat Widget
          <Badge variant="outline" className="font-mono text-xs">
            CDN Embed
          </Badge>
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          Nhúng Trợ lý AI trực tiếp vào Cổng thông tin trường (`qnu.edu.vn`, `tuyensinh.qnu.edu.vn`,
          `daotao.qnu.edu.vn`) qua 1 dòng mã script.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Configuration Form */}
        <Card className="p-5 space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-border">
            <Share2 className="h-4 w-4 text-primary" />
            <h2 className="text-xs font-bold text-foreground uppercase tracking-wider">
              Tùy Biến Cấu Hình Widget
            </h2>
          </div>

          <div className="space-y-3 text-xs">
            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">Trợ lý AI mặc định</span>
              <Select
                value={selectedAssistant}
                onValueChange={(val) => {
                  setSelectedAssistant(val);
                  if (val === "ast_admissions") setWidgetTitle("Trợ lý Tuyển sinh QNU");
                  else if (val === "ast_regulations") setWidgetTitle("Trợ lý Quy chế Học vụ");
                  else if (val === "ast_library") setWidgetTitle("Trợ lý Thư viện Số");
                  else if (val === "ast_drafting") setWidgetTitle("Trợ lý Soạn thảo NĐ 30");
                  else setWidgetTitle("Trợ lý Ngân hàng Đề thi");
                }}
              >
                <SelectTrigger className="w-full h-9 text-xs">
                  <SelectValue placeholder="Chọn Trợ lý AI" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ast_admissions">
                    Trợ lý Tuyển sinh (tuyensinh.qnu.edu.vn)
                  </SelectItem>
                  <SelectItem value="ast_regulations">
                    Trợ lý Quy chế Học vụ (daotao.qnu.edu.vn)
                  </SelectItem>
                  <SelectItem value="ast_library">Trợ lý Thư viện Số (lib.qnu.edu.vn)</SelectItem>
                  <SelectItem value="ast_drafting">
                    Trợ lý Soạn thảo NĐ 30 (hanhchinh.qnu.edu.vn)
                  </SelectItem>
                  <SelectItem value="ast_question_bank">
                    Trợ lý Ngân hàng Đề thi (khaothi.qnu.edu.vn)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">
                Tiêu đề hiển thị trên header widget
              </span>
              <Input
                value={widgetTitle}
                onChange={(e) => setWidgetTitle(e.target.value)}
                className="text-xs h-9"
              />
            </div>

            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">
                Lời chào mở đầu (Welcome Greeting)
              </span>
              <Input
                value={welcomeMessage}
                onChange={(e) => setWelcomeMessage(e.target.value)}
                className="text-xs h-9"
              />
            </div>

            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">
                Vị trí nút nổi trên màn hình
              </span>
              <div className="grid grid-cols-2 gap-3 pt-0.5">
                <label
                  className={`flex items-center gap-2 p-2.5 rounded-control border cursor-pointer text-xs ${
                    position === "bottom-right"
                      ? "border-primary bg-primary/5 font-semibold text-foreground"
                      : "border-border text-muted-foreground"
                  }`}
                >
                  <input
                    type="radio"
                    name="pos"
                    checked={position === "bottom-right"}
                    onChange={() => setPosition("bottom-right")}
                  />
                  <span>Góc dưới phải (Mặc định)</span>
                </label>
                <label
                  className={`flex items-center gap-2 p-2.5 rounded-control border cursor-pointer text-xs ${
                    position === "bottom-left"
                      ? "border-primary bg-primary/5 font-semibold text-foreground"
                      : "border-border text-muted-foreground"
                  }`}
                >
                  <input
                    type="radio"
                    name="pos"
                    checked={position === "bottom-left"}
                    onChange={() => setPosition("bottom-left")}
                  />
                  <span>Góc dưới trái</span>
                </label>
              </div>
            </div>
          </div>

          {/* Embed Code Snippet */}
          <div className="space-y-2 pt-2 border-t border-border">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-foreground flex items-center gap-1.5 text-xs">
                <Code className="h-3.5 w-3.5 text-primary" />
                Mã HTML Nhúng Trực Tiếp
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                className="h-7 px-2.5 text-xs text-primary gap-1"
              >
                {copied ? (
                  <Check className="h-3.5 w-3.5 text-success" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
                <span>{copied ? "Đã sao chép!" : "Sao chép mã"}</span>
              </Button>
            </div>

            <pre className="p-3 rounded-control bg-muted/90 font-mono text-[11px] text-foreground overflow-x-auto border border-border leading-relaxed select-text">
              {embedScript}
            </pre>
          </div>
        </Card>

        {/* Right: Live Preview */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="font-bold text-xs uppercase tracking-wider text-foreground flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-primary" />
              Xem Trước Giao Diện Thực Tế (Live Preview)
            </span>
            <Badge variant="outline" className="text-[10px]">
              Tỉ lệ 1:1
            </Badge>
          </div>

          {/* Simulated Web Page Frame */}
          <div className="rounded-surface border border-border bg-card shadow-md overflow-hidden relative h-[420px] flex flex-col justify-between">
            {/* Fake browser bar */}
            <div className="p-2.5 border-b border-border bg-muted/40 flex items-center gap-2 text-[11px] text-muted-foreground">
              <span className="h-2.5 w-2.5 rounded-full bg-destructive/60" />
              <span className="h-2.5 w-2.5 rounded-full bg-warning/60" />
              <span className="h-2.5 w-2.5 rounded-full bg-success/60" />
              <span className="ml-2 font-mono bg-background px-3 py-0.5 rounded-micro border border-border text-[10px] truncate max-w-xs flex items-center gap-1">
                https://tuyensinh.qnu.edu.vn
                <ExternalLink className="h-2.5 w-2.5" />
              </span>
            </div>

            {/* Fake page body */}
            <div className="p-6 text-muted-foreground/60 text-xs space-y-2">
              <div className="h-4 w-48 bg-muted rounded-micro" />
              <div className="h-3 w-full bg-muted/50 rounded-micro" />
              <div className="h-3 w-3/4 bg-muted/50 rounded-micro" />
            </div>

            {/* Floating Chat Widget Mockup */}
            <div
              className={`absolute bottom-4 ${
                position === "bottom-right" ? "right-4" : "left-4"
              } flex flex-col items-end gap-2`}
            >
              {/* Widget Window */}
              <div className="w-72 rounded-surface bg-card border border-border shadow-xl overflow-hidden flex flex-col text-xs animate-in slide-in-from-bottom-3 duration-200">
                <div className="p-3 bg-primary text-primary-foreground flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Bot className="h-4 w-4" />
                    <span className="font-bold text-xs">{widgetTitle}</span>
                  </div>
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                </div>

                <div className="p-3 space-y-2 bg-muted/20 min-h-[120px]">
                  <div className="p-2.5 rounded-surface rounded-tl-micro bg-card border border-border text-foreground leading-relaxed shadow-2xs">
                    {welcomeMessage}
                  </div>
                </div>

                <div className="p-2 border-t border-border bg-card flex items-center gap-1.5 text-muted-foreground">
                  <span className="text-[10px] pl-1">Nhập tin nhắn...</span>
                </div>
              </div>

              {/* Floating trigger button */}
              <div className="h-11 w-11 rounded-full bg-primary text-primary-foreground shadow-lg flex items-center justify-center cursor-pointer hover:scale-105 transition-transform">
                <MessageSquare className="h-5 w-5" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
