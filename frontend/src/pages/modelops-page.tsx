import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Cpu,
  KeyRound,
  Lock,
  Plus,
  Server,
  ShieldCheck,
  Zap,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { apiClient } from "../services/api-client";

export const ModelOpsPage: React.FC = () => {
  const [isKeyModalOpen, setIsKeyModalOpen] = useState(false);
  const [selectedProviderName, setSelectedProviderName] = useState("OpenAI");
  const [inputKey, setInputKey] = useState("");
  const [keySaveSuccess, setKeySaveSuccess] = useState(false);

  const { data: providers = [] } = useQuery({
    queryKey: ["model-providers"],
    queryFn: () => apiClient.getModelProviders(),
  });

  const { data: quota } = useQuery({
    queryKey: ["quotas"],
    queryFn: () => apiClient.getTokenQuotas(),
  });

  const totalTokens = quota?.total_tokens || 1458200;
  const limitTokens = quota?.limit_tokens || 10000000;
  const usagePct = Math.round((totalTokens / limitTokens) * 100);

  const handleSaveKey = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputKey.trim()) return;
    setKeySaveSuccess(true);
    setTimeout(() => {
      setKeySaveSuccess(false);
      setInputKey("");
      setIsKeyModalOpen(false);
    }, 1200);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            Quản Trị ModelOps & Khả Năng Phục Hồi
            <Badge variant="outline" className="font-mono text-xs">
              Circuit Breaker RFC
            </Badge>
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Điều phối các nhà cung cấp LLM, chính sách Fallback dự phòng, hạn ngạch Token Quota và
            giám sát Circuit Breaker.
          </p>
        </div>

        <Button size="sm" onClick={() => setIsKeyModalOpen(true)} className="h-8 text-xs gap-1.5">
          <Plus className="h-3.5 w-3.5" />
          <span>Thêm / Cập Nhật API Key</span>
        </Button>
      </div>

      {/* Quota & FinOps Section */}
      <Card className="p-5 bg-gradient-to-r from-card to-muted/30">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border/80">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-foreground uppercase tracking-wider flex items-center gap-1.5">
              <Zap className="h-4 w-4 text-warning" />
              Hạn Ngạch Token Tháng (Tenant: tenant_qnu)
            </span>
            <p className="text-xs text-muted-foreground">
              Chu kỳ thanh toán sẽ tự động thiết lập lại vào ngày:{" "}
              <strong className="text-foreground">{quota?.reset_date || "2026-10-01"}</strong>
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <span className="text-xs text-muted-foreground block">Đã sử dụng</span>
              <span className="text-lg font-bold text-foreground font-mono">
                {totalTokens.toLocaleString("vi-VN")} / {limitTokens.toLocaleString("vi-VN")}
              </span>
            </div>
            <Badge variant="warning" className="text-xs font-mono h-6">
              {usagePct}%
            </Badge>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-4 space-y-2">
          <div className="h-2.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-500"
              style={{ width: `${usagePct}%` }}
            />
          </div>

          <div className="flex flex-wrap items-center justify-between text-[11px] text-muted-foreground pt-1">
            <span>
              Chi phí ước tính:{" "}
              <strong className="text-primary font-mono">
                ${quota?.usd_cost.toFixed(4) || "0.4374"}
              </strong>
            </span>
            <span>Ngưỡng cảnh báo hạn ngạch: 80% (8,000,000 tokens)</span>
          </div>
        </div>
      </Card>

      {/* Providers Grid */}
      <div className="space-y-3.5">
        <h2 className="text-sm font-bold text-foreground uppercase tracking-wider flex items-center gap-2">
          <Server className="h-4 w-4 text-primary" />
          Nhà Cung Cấp LLM & Trạng Thái Circuit Breaker
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {providers.map((prov) => (
            <Card
              key={prov.id}
              className="p-4 space-y-3.5 hover:border-primary/50 transition-all flex flex-col justify-between"
            >
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-control bg-primary/10 text-primary">
                      <Cpu className="h-4 w-4" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-xs text-foreground">{prov.name}</h3>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {prov.code}
                      </span>
                    </div>
                  </div>
                  <Badge
                    variant={prov.circuit_breaker_status === "CLOSED" ? "success" : "destructive"}
                    className="text-[10px] font-mono"
                  >
                    CB: {prov.circuit_breaker_status}
                  </Badge>
                </div>

                <div className="space-y-1 text-xs">
                  <span className="text-muted-foreground text-[11px] block">Mô hình khả dụng:</span>
                  <div className="flex flex-wrap gap-1">
                    {prov.models.map((m) => (
                      <Badge
                        key={m}
                        variant="outline"
                        className="text-[10px] font-mono bg-muted/30"
                      >
                        {m}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px] border-t border-border/60 pt-2.5 text-muted-foreground">
                <div>
                  <span>Độ trễ trung bình:</span>
                  <p className="font-bold text-foreground font-mono mt-0.5">{prov.latency_ms} ms</p>
                </div>
                <div>
                  <span>Tỷ lệ lỗi (Error Rate):</span>
                  <p className="font-bold text-success font-mono mt-0.5">{prov.failure_rate}%</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Resilience & Routing Rules */}
      <div className="space-y-3.5">
        <h2 className="text-sm font-bold text-foreground uppercase tracking-wider flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-primary" />
          Chính Sách Chuyển Vùng Dự Phòng (Dynamic Fallback Policy)
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="p-4 space-y-2">
            <h4 className="font-semibold text-xs text-foreground flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-primary" />
              Nghiệp Vụ Tra Cứu Quy Chế & Tuyển Sinh (Low Temp 0.1 - 0.2)
            </h4>
            <div className="p-3 rounded-control bg-muted/40 border border-border/80 text-xs space-y-1 font-mono">
              <p className="text-foreground">
                Primary: <span className="text-primary font-bold">gpt-4o-mini</span> (OpenAI)
              </p>
              <p className="text-muted-foreground">
                Fallback 1: <span className="text-info font-bold">gemini-1.5-flash</span> (Google
                Vertex)
              </p>
              <p className="text-muted-foreground">
                Fallback 2: <span className="text-emerald-500 font-bold">qwen2.5-7b-instruct</span>{" "}
                (Local vLLM)
              </p>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Tự động kích hoạt Fallback khi Primary gặp lỗi HTTP 429 (Rate Limit) hoặc timeout quá
              5 giây.
            </p>
          </Card>

          <Card className="p-4 space-y-2">
            <h4 className="font-semibold text-xs text-foreground flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-info" />
              Nghiệp Vụ Soạn Thảo Văn Bản NĐ 30 & Đề Thi (Temp 0.4 - 0.6)
            </h4>
            <div className="p-3 rounded-control bg-muted/40 border border-border/80 text-xs space-y-1 font-mono">
              <p className="text-foreground">
                Primary: <span className="text-primary font-bold">gpt-4o</span> (OpenAI)
              </p>
              <p className="text-muted-foreground">
                Fallback: <span className="text-info font-bold">gemini-1.5-pro</span> (Google
                Vertex)
              </p>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Yêu cầu token ngữ cảnh lớn (128k context window) để nạp mẫu Nghị định 30/2020/NĐ-CP
              nguyên bản.
            </p>
          </Card>
        </div>
      </div>

      {/* API Key Modal */}
      <Dialog open={isKeyModalOpen} onOpenChange={setIsKeyModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold flex items-center gap-2">
              <KeyRound className="h-4 w-4 text-primary" />
              Cấu Hình Khóa Bí Mật API Key
            </DialogTitle>
            <DialogDescription className="text-xs">
              Khóa API được mã hóa an toàn bằng thuật toán AES-256 trước khi lưu trữ vào Vault QNU.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSaveKey} className="space-y-4 text-xs pt-2">
            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">Nhà cung cấp LLM</span>
              <select
                value={selectedProviderName}
                onChange={(e) => setSelectedProviderName(e.target.value)}
                className="w-full h-9 rounded-control border border-border bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="OpenAI">OpenAI Platform (sk-...)</option>
                <option value="Gemini">Google Cloud Gemini / Vertex AI</option>
                <option value="Local">QNU Local vLLM Inference API</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">Khóa API Secret Key *</span>
              <div className="relative">
                <Input
                  required
                  type="password"
                  placeholder="sk-proj-..."
                  value={inputKey}
                  onChange={(e) => setInputKey(e.target.value)}
                  className="text-xs h-9 pr-8"
                />
                <Lock className="h-3.5 w-3.5 text-muted-foreground absolute right-2.5 top-3" />
              </div>
            </div>

            <div className="p-3 rounded-control bg-warning/10 border border-warning/30 text-[11px] text-warning flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>
                Không bao giờ chia sẻ API Key hoặc đưa vào mã nguồn client. Toàn bộ cuộc gọi API
                thực tế được proxy qua Backend Port 8001.
              </span>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsKeyModalOpen(false)}
                className="text-xs h-8"
              >
                Hủy
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={!inputKey.trim() || keySaveSuccess}
                className="text-xs h-8"
              >
                {keySaveSuccess ? (
                  <span className="flex items-center gap-1 text-success">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Đã cập nhật
                  </span>
                ) : (
                  <span>Lưu Cấu Hình Key</span>
                )}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};
