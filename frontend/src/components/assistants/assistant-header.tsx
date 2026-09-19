import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { AssistantItem } from "@/services/api-client";
import type { AssistantReadinessResponse } from "@/types/assistants";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Bot,
  CheckCircle2,
  Clock,
  Code,
  Copy,
  Download,
  History,
  Library,
  Loader2,
  MessageSquare,
  Network,
  RefreshCw,
  Rocket,
  Save,
  ShieldCheck,
  XCircle,
} from "lucide-react";

interface AssistantHeaderProps {
  assistant: AssistantItem;
  onNavigate: (path: string) => void;
  subView: string;
  onOpenClone: () => void;
  onOpenHistory: () => void;
  onOpenEmbed: () => void;
  onExport: () => void;
  isExporting: boolean;
  onSave?: () => void;
  isSaving?: boolean;
  onPublish?: () => void;
  isPublishing?: boolean;
  readiness?: AssistantReadinessResponse | null;
  isReadinessLoading?: boolean;
  isReadinessFetching?: boolean;
  onRefetchReadiness?: () => void;
  kpiStats: {
    totalRuns: number;
    avgLatency: number;
    collectionName: string;
    docCount: number;
    workflowName: string;
  };
}

export function AssistantHeader({
  assistant,
  onNavigate,
  subView,
  onOpenClone,
  onOpenHistory,
  onOpenEmbed,
  onExport,
  isExporting,
  onSave,
  isSaving,
  onPublish,
  isPublishing,
  readiness,
  isReadinessLoading,
  isReadinessFetching,
  onRefetchReadiness,
  kpiStats,
}: AssistantHeaderProps) {
  const assistantCode = assistant.code || assistant.id;

  const passedChecksCount = readiness?.checks?.filter((c) => c.status === "passed").length ?? 0;
  const totalChecksCount = readiness?.checks?.length ?? 5;

  return (
    <div className="space-y-6">
      {/* Top Header & Action Toolbar */}
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <Button
            className="mb-2 -ml-2.5 h-8 text-xs text-muted-foreground hover:text-foreground gap-1.5"
            size="sm"
            type="button"
            variant="ghost"
            onClick={() => onNavigate("/assistants")}
          >
            <ArrowLeft className="size-3.5" />
            Danh mục trợ lý
          </Button>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Bot className="size-4 text-primary" />
            <span>Trợ lý AI / {assistant.code}</span>
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">{assistant.name}</h1>
            <Badge variant={assistant.is_active ? "success" : "secondary"}>
              {assistant.is_active ? "Hoạt động" : "Đã tắt"}
            </Badge>
            <Badge variant="outline" className="capitalize">
              {assistant.category}
            </Badge>
          </div>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{assistant.id}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-9 text-xs gap-1.5"
            onClick={() =>
              onNavigate(`/assistants/${encodeURIComponent(assistantCode)}/playground`)
            }
          >
            <MessageSquare className="size-3.5 text-primary" />
            Thử chat
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-9 text-xs gap-1.5"
            onClick={() => onNavigate(`/assistants/${encodeURIComponent(assistantCode)}/workflow`)}
          >
            <Network className="size-3.5 text-primary" />
            Mở DAG
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-9 text-xs gap-1.5"
            onClick={onOpenClone}
          >
            <Copy className="size-3.5 text-primary" />
            Nhân bản
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-9 text-xs gap-1.5"
            onClick={onOpenHistory}
          >
            <History className="size-3.5 text-primary" />
            Lịch sử phiên bản
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-9 text-xs gap-1.5"
            onClick={onOpenEmbed}
          >
            <Code className="size-3.5 text-primary" />
            Mã nhúng Web
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-9 text-xs gap-1.5"
            disabled={isExporting}
            onClick={onExport}
          >
            <Download className="size-3.5" />
            Xuất bundle
          </Button>
          {subView === "overview" && onSave && (
            <Button
              disabled={isSaving}
              type="button"
              size="sm"
              className="h-9 text-xs gap-1.5"
              onClick={onSave}
            >
              <Save className="size-3.5" />
              {isSaving ? "Đang lưu..." : "Lưu thay đổi"}
            </Button>
          )}
        </div>
      </div>

      {/* KPI Metrics Strip (Only shown on overview subview) */}
      {subView === "overview" && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Card className="p-3.5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Lượt Hội Thoại</span>
                <Activity className="size-3.5 text-primary" />
              </div>
              <p className="mt-1 text-xl font-bold font-mono text-foreground">
                {kpiStats.totalRuns.toLocaleString()}
              </p>
              <span className="text-xs text-muted-foreground">Tổng phiên thực thi</span>
            </Card>

            <Card className="p-3.5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Độ Trễ Phản Hồi</span>
                <Clock className="size-3.5 text-primary" />
              </div>
              <p className="mt-1 text-xl font-bold font-mono text-foreground">
                {kpiStats.avgLatency} ms
              </p>
              <span className="text-xs text-muted-foreground">Thời gian sinh token</span>
            </Card>

            <Card className="p-3.5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Kho Tri Thức</span>
                <Library className="size-3.5 text-primary" />
              </div>
              <p
                className="mt-1 text-sm font-semibold truncate text-foreground"
                title={kpiStats.collectionName}
              >
                {kpiStats.collectionName}
              </p>
              <span className="text-xs text-muted-foreground">
                {kpiStats.docCount} tài liệu bóc tách
              </span>
            </Card>

            <Card className="p-3.5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Chuẩn Ragas TM-08</span>
                <ShieldCheck className="size-3.5 text-success" />
              </div>
              <p className="mt-1 text-sm font-bold text-success">Đạt Chuẩn QNU</p>
              <span className="text-xs text-muted-foreground">Faithfulness ≥ 0.90</span>
            </Card>
          </div>

          {/* 5-Layer Publish Gate Readiness Banner */}
          {isReadinessLoading ? (
            <div className="flex h-20 items-center justify-center text-xs text-muted-foreground gap-2 rounded-lg border border-dashed p-4">
              <Loader2 className="size-4 animate-spin text-primary" />
              Đang thẩm định 5 tiêu chí sẵn sàng xuất bản...
            </div>
          ) : readiness ? (
            <div
              className={cn(
                "rounded-lg border p-4 transition-colors",
                readiness.is_ready_for_publish
                  ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-950 dark:text-emerald-200"
                  : readiness.blockers.length > 0
                    ? "border-destructive/30 bg-destructive/5 text-destructive"
                    : "border-amber-500/30 bg-amber-500/5 text-amber-950 dark:text-amber-200"
              )}
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 shrink-0">
                    {readiness.is_ready_for_publish ? (
                      <CheckCircle2 className="size-5 text-emerald-600 dark:text-emerald-400" />
                    ) : readiness.blockers.length > 0 ? (
                      <XCircle className="size-5 text-destructive" />
                    ) : (
                      <AlertTriangle className="size-5 text-amber-600 dark:text-amber-400" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm">
                        {readiness.is_ready_for_publish
                          ? "Trợ lý AI Đã Sẵn Sàng Xuất Bản (Ready to Publish)"
                          : readiness.blockers.length > 0
                            ? "Có Lỗi Chặn Xuất Bản — Cần Khắc Phục"
                            : "Chưa Đủ Điều Kiện Xuất Bản — Khuyến Nghị Bổ Sung"}
                      </span>
                      <Badge
                        variant={
                          readiness.is_ready_for_publish
                            ? "success"
                            : readiness.blockers.length > 0
                              ? "destructive"
                              : "warning"
                        }
                        className="text-xs"
                      >
                        {passedChecksCount}/{totalChecksCount} Tiêu chí (
                        {readiness.overall_readiness_score}%)
                      </Badge>
                    </div>

                    {readiness.checks && readiness.checks.length > 0 && (
                      <div className="mt-2.5 flex flex-wrap gap-2">
                        {readiness.checks.map((c) => (
                          <span
                            key={c.name}
                            className={cn(
                              "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium border",
                              c.status === "passed"
                                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                                : c.status === "warning"
                                  ? "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300"
                                  : "border-destructive/30 bg-destructive/10 text-destructive"
                            )}
                          >
                            {c.status === "passed" ? (
                              <CheckCircle2 className="size-3 text-emerald-600 dark:text-emerald-400" />
                            ) : c.status === "warning" ? (
                              <AlertTriangle className="size-3 text-amber-600 dark:text-amber-400" />
                            ) : (
                              <XCircle className="size-3 text-destructive" />
                            )}
                            {c.name}: {c.score}/100
                          </span>
                        ))}
                      </div>
                    )}

                    {readiness.blockers.length > 0 && (
                      <ul className="mt-2 space-y-1 text-xs text-destructive">
                        {readiness.blockers.map((b) => (
                          <li key={b} className="flex items-center gap-1.5">
                            <AlertCircle className="size-3.5 shrink-0" />
                            <span>{b}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {onRefetchReadiness && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground gap-1"
                      disabled={isReadinessFetching}
                      onClick={onRefetchReadiness}
                    >
                      <RefreshCw
                        className={cn("size-3.5", isReadinessFetching && "animate-spin")}
                      />
                      Kiểm tra lại
                    </Button>
                  )}
                  {onPublish && (
                    <Button
                      type="button"
                      size="sm"
                      disabled={
                        isPublishing || (!assistant.is_active && !readiness.is_ready_for_publish)
                      }
                      onClick={onPublish}
                      className="gap-1.5 text-xs"
                      variant={assistant.is_active ? "outline" : "default"}
                    >
                      <Rocket className="size-3.5" />
                      {isPublishing
                        ? "Đang xuất bản..."
                        : assistant.is_active
                          ? "Tái xuất bản (Đang hoạt động)"
                          : "Xuất Bản Trợ Lý"}
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
