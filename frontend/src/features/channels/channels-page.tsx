import { useQuery } from "@tanstack/react-query";
import {
  Bot,
  Check,
  Code2,
  Copy,
  ExternalLink,
  Globe,
  Layers,
  MessageSquare,
  Send,
  Share2,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useRAGStream } from "@/hooks/use-rag-stream";
import { listAssistants } from "@/services/assistants-api";

export function ChannelsPage() {
  const [copied, setCopied] = React.useState(false);
  const [selectedAssistantCode, setSelectedAssistantCode] =
    React.useState("admissions");
  const [widgetTitle, setWidgetTitle] = React.useState("Trợ lý Tuyển sinh QNU");
  const [welcomeMessage, setWelcomeMessage] = React.useState(
    "Xin chào! Mình là Trợ lý ảo Trường Đại học Quy Nhơn. Mình có thể giúp gì cho bạn hôm nay?",
  );
  const [position, setPosition] = React.useState<
    "bottom-right" | "bottom-left"
  >("bottom-right");

  // Preview interactive state
  const [previewOpen, setPreviewOpen] = React.useState(true);
  const [previewInput, setPreviewInput] = React.useState("");

  const { data: assistants = [] } = useQuery({
    queryKey: ["assistants-channels"],
    queryFn: () => listAssistants(),
  });

  // Keep assistant name in sync with selected assistant
  const currentAssistant = React.useMemo(() => {
    return (
      assistants.find(
        (a) =>
          a.code === selectedAssistantCode || a.id === selectedAssistantCode,
      ) || null
    );
  }, [assistants, selectedAssistantCode]);

  React.useEffect(() => {
    if (currentAssistant) {
      setWidgetTitle(currentAssistant.name);
    }
  }, [currentAssistant]);

  const originUrl =
    typeof window !== "undefined"
      ? window.location.origin
      : "https://ai.qnu.edu.vn";

  const embedScript = React.useMemo(() => {
    return `<!-- QNU AI Platform — Standalone Web Chat Widget ĐH Quy Nhơn -->
<script
  src="${originUrl}/embed/qnu-chat-widget.js"
  data-assistant="${selectedAssistantCode}"
  data-title="${widgetTitle}"
  data-position="${position}"
  data-welcome="${welcomeMessage}"
  data-api-base="${originUrl}"
  defer>
</script>`;
  }, [originUrl, selectedAssistantCode, widgetTitle, position, welcomeMessage]);

  const handleCopyScript = async () => {
    try {
      await navigator.clipboard.writeText(embedScript);
      setCopied(true);
      toast.success("Đã sao chép mã nhúng Widget vào clipboard!");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error(
        "Không thể sao chép tự động. Vui lòng chọn và sao chép thủ công.",
      );
    }
  };

  // Preview chat streaming hook
  const {
    messages: previewMessages,
    sendMessage: sendPreviewMessage,
    isStreaming: isPreviewStreaming,
    clearMessages: clearPreviewMessages,
  } = useRAGStream({
    assistantCode: selectedAssistantCode,
    tenantId: "tenant_qnu",
  });

  const handleSendPreview = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!previewInput.trim() || isPreviewStreaming) return;
    sendPreviewMessage(previewInput.trim());
    setPreviewInput("");
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
              Kênh Phân Phối & Web Chat Widget
            </h1>
            <Badge
              variant="outline"
              className="font-mono text-[11px] uppercase tracking-wider text-primary border-primary/30"
            >
              CDN Embed
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Cấu hình tùy biến và nhúng Trợ lý AI trực tiếp vào Cổng thông tin
            trường (`qnu.edu.vn`, `tuyensinh.qnu.edu.vn`) qua 1 dòng script.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="text-xs h-9 rounded-md gap-1.5 self-start sm:self-auto"
          onClick={() => window.open("/chat", "_blank")}
        >
          <ExternalLink className="size-3.5" />
          <span>Mở Cổng Chat Công Khai</span>
        </Button>
      </div>

      {/* Main Grid: Configurator vs Live Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Configurator & Embed Code (7 cols) */}
        <div className="lg:col-span-6 space-y-6">
          {/* Card 1: Customizer */}
          <Card className="bg-card">
            <CardHeader className="p-5 pb-3 border-b border-border/60">
              <div className="flex items-center gap-2">
                <div className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <Share2 className="size-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-bold text-foreground">
                    Tùy Biến Cấu Hình Widget
                  </CardTitle>
                  <CardDescription className="text-xs text-muted-foreground">
                    Điều chỉnh giao diện và hành vi bong bóng chat trên trang
                    web đích.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>

            <CardContent className="p-5 space-y-4 text-xs">
              {/* Select Assistant */}
              <div className="space-y-1.5">
                <Label
                  htmlFor="assistant-select"
                  className="text-xs font-semibold text-foreground"
                >
                  Trợ lý AI mặc định
                </Label>
                <Select
                  value={selectedAssistantCode}
                  onValueChange={(val) => {
                    setSelectedAssistantCode(val);
                    clearPreviewMessages();
                  }}
                >
                  <SelectTrigger id="assistant-select" className="h-9 text-xs">
                    <SelectValue placeholder="Chọn Trợ lý AI" />
                  </SelectTrigger>
                  <SelectContent>
                    {assistants.map((ast) => (
                      <SelectItem key={ast.id} value={ast.code || ast.id}>
                        {ast.name} ({ast.category || "AI"})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Title Input */}
              <div className="space-y-1.5">
                <Label
                  htmlFor="widget-title"
                  className="text-xs font-semibold text-foreground"
                >
                  Tiêu đề thanh tiêu đề Widget
                </Label>
                <Input
                  id="widget-title"
                  value={widgetTitle}
                  onChange={(e) => setWidgetTitle(e.target.value)}
                  placeholder="Ví dụ: Trợ lý Tuyển sinh QNU"
                  className="h-9 text-xs"
                />
              </div>

              {/* Welcome Message */}
              <div className="space-y-1.5">
                <Label
                  htmlFor="welcome-msg"
                  className="text-xs font-semibold text-foreground"
                >
                  Lời chào ban đầu (Welcome Message)
                </Label>
                <Textarea
                  id="welcome-msg"
                  value={welcomeMessage}
                  onChange={(e) => setWelcomeMessage(e.target.value)}
                  rows={2}
                  className="text-xs resize-none"
                  placeholder="Nhập câu chào khi người dùng bấm mở widget..."
                />
              </div>

              {/* Position */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold text-foreground">
                  Vị trí xuất hiện trên màn hình
                </Label>
                <div className="grid grid-cols-2 gap-3 pt-1">
                  <button
                    type="button"
                    onClick={() => setPosition("bottom-right")}
                    className={`p-3 rounded-lg border text-left text-xs transition-all flex items-center justify-between ${
                      position === "bottom-right"
                        ? "border-primary bg-primary/10 text-primary font-semibold"
                        : "border-border bg-card text-muted-foreground hover:border-border/80"
                    }`}
                  >
                    <span>Góc Dưới Phải (Khuyến nghị)</span>
                    {position === "bottom-right" && (
                      <Check className="size-4" />
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => setPosition("bottom-left")}
                    className={`p-3 rounded-lg border text-left text-xs transition-all flex items-center justify-between ${
                      position === "bottom-left"
                        ? "border-primary bg-primary/10 text-primary font-semibold"
                        : "border-border bg-card text-muted-foreground hover:border-border/80"
                    }`}
                  >
                    <span>Góc Dưới Trái</span>
                    {position === "bottom-left" && <Check className="size-4" />}
                  </button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card 2: Generated Embed Snippet */}
          <Card className="bg-card">
            <CardHeader className="p-5 pb-3 border-b border-border/60">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary">
                    <Code2 className="size-4" />
                  </div>
                  <div>
                    <CardTitle className="text-sm font-bold text-foreground">
                      Mã Nhúng HTML Script
                    </CardTitle>
                    <CardDescription className="text-xs text-muted-foreground">
                      Dán đoạn mã này trước thẻ &lt;/body&gt; trên trang web của
                      trường.
                    </CardDescription>
                  </div>
                </div>

                <Button
                  size="sm"
                  className="h-8 text-xs gap-1.5 font-medium"
                  onClick={handleCopyScript}
                >
                  {copied ? (
                    <Check className="size-3.5" />
                  ) : (
                    <Copy className="size-3.5" />
                  )}
                  <span>{copied ? "Đã sao chép" : "Sao chép mã"}</span>
                </Button>
              </div>
            </CardHeader>

            <CardContent className="p-5 space-y-3">
              <div className="relative rounded-lg border border-border bg-muted/50 p-3 font-mono text-[11px] text-foreground overflow-x-auto">
                <pre className="whitespace-pre-wrap">{embedScript}</pre>
              </div>

              <div className="p-3 rounded-lg bg-primary/5 border border-primary/20 space-y-1.5 text-xs">
                <div className="flex items-center gap-1.5 font-semibold text-primary">
                  <Sparkles className="size-3.5" />
                  <span>Ưu điểm của Web Chat Widget QNU:</span>
                </div>
                <ul className="list-disc list-inside space-y-0.5 text-muted-foreground text-[11px]">
                  <li>
                    Dung lượng siêu nhẹ (&lt; 15KB), không tải thêm thư viện
                    cồng kềnh.
                  </li>
                  <li>
                    Hỗ trợ phản hồi Streaming thời gian thực (SSE) mượt mà từng
                    từ.
                  </li>
                  <li>
                    Giao diện tự động tối ưu hiển thị dạng ngăn kéo (Drawer)
                    trên điện thoại.
                  </li>
                </ul>
              </div>
            </CardContent>
          </Card>

          {/* Card 3: Domain Whitelist Security */}
          <Card className="bg-card">
            <CardHeader className="p-5 pb-3 border-b border-border/60">
              <div className="flex items-center gap-2">
                <div className="flex size-7 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                  <ShieldCheck className="size-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-bold text-foreground">
                    Bảo Vệ Tên Miền (Domain Whitelist CORS)
                  </CardTitle>
                  <CardDescription className="text-xs text-muted-foreground">
                    Ngăn chặn website lạ bên ngoài tự ý lấy mã nhúng gây tiêu
                    hao ngân sách Token.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>

            <CardContent className="p-5 space-y-3 text-xs">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge
                  variant="outline"
                  className="font-mono text-[11px] gap-1"
                >
                  <Globe className="size-3 text-emerald-500" />
                  <span>*.qnu.edu.vn</span>
                </Badge>
                <Badge variant="outline" className="font-mono text-[11px]">
                  tuyensinh.qnu.edu.vn
                </Badge>
                <Badge variant="outline" className="font-mono text-[11px]">
                  daotao.qnu.edu.vn
                </Badge>
                <Badge
                  variant="secondary"
                  className="font-mono text-[11px] text-muted-foreground"
                >
                  localhost:* (Dev)
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Tất cả request gọi API chat từ widget đều được kiểm tra header
                Origin/Referer. Các request không khớp danh sách Whitelist sẽ bị
                chặn với mã HTTP 403 Forbidden.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Live Mockup Interactive Preview (6 cols) */}
        <div className="lg:col-span-6 space-y-3 sticky top-20">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Layers className="size-3.5 text-primary" />
              Mô Phỏng Trực Tiếp Trên Website Trường
            </span>
            <Badge variant="outline" className="text-[10px]">
              Live Preview 1:1
            </Badge>
          </div>

          {/* Browser Window Frame */}
          <div className="rounded-xl border border-border/80 bg-card overflow-hidden shadow-lg flex flex-col h-[620px] relative">
            {/* Browser Top Bar */}
            <div className="h-9 bg-muted/60 border-b border-border/80 px-3 flex items-center gap-2 shrink-0">
              <div className="flex items-center gap-1.5">
                <div className="size-2.5 rounded-full bg-red-400" />
                <div className="size-2.5 rounded-full bg-amber-400" />
                <div className="size-2.5 rounded-full bg-emerald-400" />
              </div>
              <div className="flex-1 mx-2 bg-background/80 rounded-md px-2.5 py-1 text-[10px] font-mono text-muted-foreground border border-border/60 truncate">
                https://tuyensinh.qnu.edu.vn
              </div>
            </div>

            {/* Mock Website Content */}
            <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-slate-50 dark:bg-slate-950/40 select-none">
              {/* Mock School Header */}
              <div className="flex items-center justify-between pb-4 border-b border-border/40">
                <div className="flex items-center gap-2.5">
                  <div className="size-9 rounded-lg bg-primary/20 text-primary font-bold flex items-center justify-center text-xs">
                    QNU
                  </div>
                  <div>
                    <div className="font-bold text-xs text-foreground">
                      TRƯỜNG ĐẠI HỌC QUY NHƠN
                    </div>
                    <div className="text-[10px] text-muted-foreground">
                      Cổng Thông Tin Tuyển Sinh & Đào Tạo
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-[11px] text-muted-foreground font-medium">
                  <span>Giới thiệu</span>
                  <span>Đề án</span>
                  <span>Điểm chuẩn</span>
                </div>
              </div>

              {/* Mock Hero Banner */}
              <div className="rounded-lg bg-gradient-to-r from-teal-900 to-teal-700 text-white p-5 space-y-2">
                <Badge className="bg-white/20 text-white hover:bg-white/30 text-[10px] border-none">
                  Tuyển sinh Đại học Chính quy 2026
                </Badge>
                <h3 className="text-base font-bold">
                  Khởi Đầu Tương Lai Tại Đại Học Quy Nhơn
                </h3>
                <p className="text-xs text-teal-100/90 leading-relaxed">
                  50+ ngành đào tạo đạt chuẩn kiểm định chất lượng giáo dục quốc
                  gia và quốc tế.
                </p>
              </div>

              {/* Mock Articles */}
              <div className="space-y-3">
                <div className="h-4 w-32 bg-muted/60 rounded" />
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg border border-border/60 bg-background space-y-1.5">
                    <div className="h-3 w-3/4 bg-muted/80 rounded" />
                    <div className="h-2 w-full bg-muted/50 rounded" />
                  </div>
                  <div className="p-3 rounded-lg border border-border/60 bg-background space-y-1.5">
                    <div className="h-3 w-2/3 bg-muted/80 rounded" />
                    <div className="h-2 w-full bg-muted/50 rounded" />
                  </div>
                </div>
              </div>
            </div>

            {/* Widget Interactive Overlay (Simulated) */}
            <div
              className={`absolute bottom-4 ${
                position === "bottom-left" ? "left-4" : "right-4"
              } z-30 flex flex-col items-end`}
            >
              {/* Expanded Chat Box */}
              {previewOpen && (
                <div className="w-[320px] sm:w-[350px] h-[440px] rounded-xl border border-border/90 bg-card shadow-2xl flex flex-col overflow-hidden mb-3 animate-in fade-in zoom-in-95 duration-200">
                  {/* Widget Header */}
                  <div className="h-12 bg-primary text-primary-foreground px-4 flex items-center justify-between shrink-0">
                    <div className="flex items-center gap-2">
                      <div className="size-7 rounded-full bg-white/20 flex items-center justify-center">
                        <Bot className="size-4" />
                      </div>
                      <div>
                        <div className="font-bold text-xs leading-none">
                          {widgetTitle}
                        </div>
                        <div className="text-[10px] opacity-80 mt-0.5">
                          ĐH Quy Nhơn (Trực tuyến)
                        </div>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setPreviewOpen(false)}
                      className="size-6 rounded-md hover:bg-white/20 flex items-center justify-center transition-colors"
                      title="Thu nhỏ"
                    >
                      <X className="size-3.5" />
                    </button>
                  </div>

                  {/* Messages Box */}
                  <div className="flex-1 p-3.5 space-y-3 overflow-y-auto text-xs bg-slate-50/50 dark:bg-card">
                    {/* Welcome Bubble */}
                    <div className="flex gap-2">
                      <div className="size-6 rounded-full bg-primary/20 text-primary flex items-center justify-center shrink-0 mt-0.5">
                        <Bot className="size-3.5" />
                      </div>
                      <div className="p-2.5 rounded-lg rounded-tl-none bg-muted/60 text-foreground border border-border/40 text-[11px] leading-relaxed max-w-[85%]">
                        {welcomeMessage}
                      </div>
                    </div>

                    {/* Preview conversation */}
                    {previewMessages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex gap-2 ${
                          msg.role === "user" ? "justify-end" : "justify-start"
                        }`}
                      >
                        {msg.role === "assistant" && (
                          <div className="size-6 rounded-full bg-primary/20 text-primary flex items-center justify-center shrink-0 mt-0.5">
                            <Bot className="size-3.5" />
                          </div>
                        )}
                        <div
                          className={`p-2.5 rounded-lg text-[11px] leading-relaxed max-w-[85%] ${
                            msg.role === "user"
                              ? "bg-primary text-primary-foreground rounded-tr-none"
                              : "bg-muted/60 text-foreground border border-border/40 rounded-tl-none"
                          }`}
                        >
                          {msg.content}
                        </div>
                      </div>
                    ))}
                    {isPreviewStreaming && (
                      <div className="text-[10px] text-muted-foreground italic animate-pulse">
                        Trợ lý đang suy nghĩ và gõ phản hồi...
                      </div>
                    )}
                  </div>

                  {/* Input Box */}
                  <form
                    onSubmit={handleSendPreview}
                    className="p-2 border-t border-border/70 bg-card flex items-center gap-1.5"
                  >
                    <Input
                      value={previewInput}
                      onChange={(e) => setPreviewInput(e.target.value)}
                      placeholder="Gõ thử câu hỏi tại đây..."
                      className="h-8 text-[11px] bg-background border-border/80"
                    />
                    <Button
                      type="submit"
                      size="icon"
                      className="size-8 shrink-0 rounded-md"
                      disabled={!previewInput.trim() || isPreviewStreaming}
                    >
                      <Send className="size-3.5" />
                    </Button>
                  </form>
                </div>
              )}

              {/* Launcher Floating Button */}
              <button
                type="button"
                onClick={() => setPreviewOpen(!previewOpen)}
                className="size-13 rounded-full bg-primary text-primary-foreground shadow-xl flex items-center justify-center hover:scale-105 transition-all border-2 border-white/20"
                title="Bấm để mở / đóng Widget"
              >
                {previewOpen ? (
                  <X className="size-5" />
                ) : (
                  <MessageSquare className="size-5" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
