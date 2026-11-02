import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Cpu,
  Globe,
  Key,
  XCircle,
} from "lucide-react";
import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  CapacityBadge,
  ProviderOperationalBudgetsSummary,
} from "@/features/modelops/capacity-badge";
import {
  CAPABILITY_LABELS,
  type Capability,
  PROVIDER_TYPE_LABELS,
  type Provider,
  type ProviderSummaryItem,
  type ProviderType,
} from "@/features/modelops/types";
import { formatDateTimeValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

interface ProviderCardGridProps {
  providers: ProviderSummaryItem[];
  onOpen: (provider: Provider) => void;
}

const PROVIDER_FAMILY_ORDER: ProviderType[] = [
  "openai_compatible",
  "local",
  "nemotron",
  "mineru",
  "paddleocr",
  "gemini",
];

const FAMILY_HEADERS: Record<ProviderType, { title: string; desc: string }> = {
  openai_compatible: {
    title: "OpenAI Compatible",
    desc: "Cổng giao tiếp chuẩn HTTP OpenAI (vLLM, Ollama, API Gateway, Cloud Endpoints)",
  },
  local: {
    title: "Local Models",
    desc: "Mô hình triển khai nội bộ trường hoặc máy chủ on-premise",
  },
  nemotron: {
    title: "NVIDIA Nemotron OCR",
    desc: "Công cụ trích xuất tài liệu và nhận dạng cấu trúc bảng",
  },
  mineru: {
    title: "MinerU PDF OCR",
    desc: "Nhận dạng cả PDF theo tác vụ, giữ trang, bảng và bằng chứng gốc",
  },
  paddleocr: {
    title: "PaddleOCR Engine",
    desc: "Trích xuất văn bản nhanh đa ngôn ngữ",
  },
  gemini: {
    title: "Gemini",
    desc: "Google Gemini Cloud Provider",
  },
};

export const ProviderCardGrid: React.FC<ProviderCardGridProps> = ({
  providers,
  onOpen,
}) => {
  // Group providers by provider_type
  const grouped = React.useMemo(() => {
    const map = new Map<ProviderType, ProviderSummaryItem[]>();
    for (const p of providers) {
      const list = map.get(p.provider_type) ?? [];
      list.push(p);
      map.set(p.provider_type, list);
    }
    return map;
  }, [providers]);

  // Sort groups by defined order, then any leftovers
  const orderedTypes = React.useMemo(() => {
    const presentTypes = Array.from(grouped.keys());
    const sorted: ProviderType[] = [];
    for (const t of PROVIDER_FAMILY_ORDER) {
      if (grouped.has(t)) sorted.push(t);
    }
    for (const t of presentTypes) {
      if (!sorted.includes(t)) sorted.push(t);
    }
    return sorted;
  }, [grouped]);

  return (
    <div className="space-y-8 p-4 sm:p-6">
      {orderedTypes.map((type) => {
        const items = grouped.get(type) ?? [];
        const familyMeta = FAMILY_HEADERS[type] ?? {
          title: PROVIDER_TYPE_LABELS[type] ?? type,
          desc: "Nhóm nhà cung cấp mô hình",
        };

        return (
          <div key={type} className="space-y-3">
            <div className="flex items-baseline justify-between border-b pb-2">
              <div>
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <span>{familyMeta.title}</span>
                  <Badge
                    variant="outline"
                    className="text-[11px] font-mono px-1.5 py-0"
                  >
                    {items.length}
                  </Badge>
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {familyMeta.desc}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {items.map((provider) => (
                <ProviderCard
                  key={provider.id}
                  provider={provider}
                  onClick={() => onOpen(provider)}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

interface ProviderCardProps {
  provider: ProviderSummaryItem;
  onClick: () => void;
}

function ProviderCard({ provider, onClick }: ProviderCardProps) {
  const probeStatus = provider.last_probe_status;
  const isHealthy = probeStatus === "success";
  const isFailed = probeStatus === "failed";
  const isUntested = probeStatus === "untested" || !probeStatus;

  return (
    <Card
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      className={cn(
        "group relative flex flex-col justify-between overflow-hidden rounded-xl border border-border bg-card p-4 transition-all duration-200",
        "hover:border-primary/40 hover:shadow-md cursor-pointer text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        !provider.is_active && "opacity-75 bg-muted/20 border-dashed",
      )}
    >
      <div className="space-y-3">
        {/* Top Header: Name, Type Badge & Active Status */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <h4 className="truncate text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                {provider.name}
              </h4>
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5 truncate">
              {PROVIDER_TYPE_LABELS[provider.provider_type] ??
                provider.provider_type}
            </p>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {provider.is_active ? (
              <Badge variant="success" className="text-[10px] py-0 px-1.5">
                Đang bật
              </Badge>
            ) : (
              <Badge variant="secondary" className="text-[10px] py-0 px-1.5">
                Đang tắt
              </Badge>
            )}
          </div>
        </div>

        {/* Model & Base URL */}
        <div className="rounded-lg bg-muted/40 p-2.5 space-y-1.5 text-xs">
          <div className="flex items-center gap-2">
            <Cpu className="size-3.5 text-primary shrink-0" />
            <span
              className="font-mono font-medium truncate text-foreground"
              title={provider.model_name}
            >
              {provider.model_name}
            </span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Globe className="size-3.5 shrink-0" />
            <span
              className="font-mono text-[11px] truncate"
              title={provider.base_url}
            >
              {provider.base_url}
            </span>
          </div>
        </div>

        {/* Capabilities & Capacity / Operational Budget Badges */}
        <div className="space-y-1.5">
          <div className="flex flex-wrap gap-1">
            {provider.capabilities.length > 0 ? (
              provider.capabilities.map((cap) => (
                <Badge
                  key={cap}
                  variant="outline"
                  className="text-[10px] px-1.5 py-0 font-normal bg-background/50 border-border"
                >
                  {CAPABILITY_LABELS[cap as Capability] ?? cap}
                </Badge>
              ))
            ) : (
              <span className="text-[11px] text-muted-foreground">
                Chưa có chức năng
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <CapacityBadge status={provider.capacity_status} />
            <ProviderOperationalBudgetsSummary provider={provider} compact />
          </div>
        </div>
      </div>

      {/* Bottom Metadata & Diagnostics Summary */}
      <div className="mt-4 pt-3 border-t border-border/60 flex flex-col gap-2 text-[11px]">
        {/* Keys & Diagnostics Status */}
        <div className="flex items-center justify-between gap-2">
          {/* AI Server Keys count */}
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Key className="size-3 text-muted-foreground" />
            {provider.total_keys_count > 0 ? (
              <span>
                <strong className="text-foreground font-semibold">
                  {provider.active_keys_count}
                </strong>
                /{provider.total_keys_count} khóa
              </span>
            ) : (
              <span className="text-warning flex items-center gap-1">
                <AlertCircle className="size-3" />
                Chưa có khóa
              </span>
            )}
          </div>

          {/* Connection Test Status */}
          <div className="flex items-center gap-1">
            {isHealthy && (
              <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                <CheckCircle2 className="size-3" />
                Đã kiểm tra
              </span>
            )}
            {isFailed && (
              <span
                className="flex items-center gap-1 text-destructive font-medium"
                title={provider.last_probe_error ?? "Kiểm tra thất bại"}
              >
                <XCircle className="size-3" />
                Lỗi kết nối
              </span>
            )}
            {isUntested && (
              <span className="flex items-center gap-1 text-muted-foreground">
                <Clock className="size-3" />
                Chưa kiểm tra
              </span>
            )}
            {probeStatus === "stale" && (
              <span className="text-warning">Cần kiểm tra lại</span>
            )}
            {probeStatus === "unsupported" && (
              <span className="text-muted-foreground">
                Chưa hỗ trợ kiểm tra
              </span>
            )}
          </div>
        </div>

        {/* Hover Action bar */}
        <div className="flex items-center justify-between text-muted-foreground/80 pt-1 group-hover:text-primary transition-colors">
          <span className="text-[10px]">
            {provider.last_probe_at ? (
              <span>Đo: {formatDateTimeValue(provider.last_probe_at)}</span>
            ) : (
              <span>Cập nhật: {formatDateTimeValue(provider.updated_at)}</span>
            )}
          </span>
          <span className="flex items-center gap-0.5 text-[11px] font-medium">
            <span>Chi tiết</span>
            <ArrowRight className="size-3 group-hover:translate-x-0.5 transition-transform" />
          </span>
        </div>
      </div>
    </Card>
  );
}
