import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import type { AssistantItem } from "@/services/api-client";
import type { AssistantReadinessResponse } from "@/types/assistants";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Code,
  Copy,
  Download,
  History,
  Loader2,
  MessageSquare,
  MoreHorizontal,
  Network,
  RefreshCw,
  Rocket,
  Save,
  XCircle,
} from "lucide-react";
import { useState } from "react";

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
  workflowId?: string;
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
  workflowId,
}: AssistantHeaderProps) {
  const [isReadinessExpanded, setIsReadinessExpanded] = useState(false);
  const assistantCode = assistant.code || assistant.id;
  const targetWorkflowId = workflowId || assistant.workflow_id;

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
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Action 1: Direct Full-Screen DAG Studio Link */}
          {targetWorkflowId && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-9 text-xs gap-1.5 border-primary/30 text-primary hover:bg-primary/10"
              onClick={() =>
                onNavigate(`/assistants/${encodeURIComponent(assistantCode)}/workflow`)
              }
              title="Mở đồ thị điều phối DAG trong màn hình Studio riêng biệt"
            >
              <Network className="size-3.5" />
              <span>Sơ đồ DAG Studio</span>
            </Button>
          )}

          {/* Action 2: Primary Chat Test */}
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
            <span>Thử chat</span>
          </Button>

          {/* Action 3: Save Changes (Shown on all config tabs) */}
          {["overview", "models", "tools"].includes(subView) && onSave && (
            <Button
              disabled={isSaving}
              type="button"
              size="sm"
              className="h-9 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={onSave}
            >
              <Save className="size-3.5" />
              {isSaving ? "Đang lưu..." : "Lưu thay đổi"}
            </Button>
          )}

          {/* Action 4: More Actions Dropdown Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button type="button" variant="outline" size="sm" className="h-9 text-xs gap-1.5">
                <MoreHorizontal className="size-3.5" />
                <span>Thao tác khác</span>
                <ChevronDown className="size-3 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              {targetWorkflowId && (
                <DropdownMenuItem
                  onClick={() =>
                    onNavigate(`/assistants/${encodeURIComponent(assistantCode)}/workflow`)
                  }
                >
                  <Network className="size-3.5 mr-2 text-primary" />
                  <span>Mở đồ thị DAG Studio</span>
                </DropdownMenuItem>
              )}
              <DropdownMenuItem onClick={onOpenClone}>
                <Copy className="size-3.5 mr-2 text-primary" />
                <span>Nhân bản Trợ lý</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onOpenHistory}>
                <History className="size-3.5 mr-2 text-primary" />
                <span>Lịch sử phiên bản</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onOpenEmbed}>
                <Code className="size-3.5 mr-2 text-primary" />
                <span>Lấy mã nhúng Web</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem disabled={isExporting} onClick={onExport}>
                <Download className="size-3.5 mr-2" />
                <span>Xuất bundle JSON</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* 5-Layer Publish Gate Readiness Banner (Collapsible Compact Alert) */}
      {isReadinessLoading ? (
        <div className="flex h-12 items-center justify-center text-xs text-muted-foreground gap-2 rounded-lg border border-dashed px-4">
          <Loader2 className="size-3.5 animate-spin text-primary" />
          Đang thẩm định 5 tiêu chí sẵn sàng xuất bản...
        </div>
      ) : readiness ? (
        <div
          className={cn(
            "rounded-lg border bg-card transition-colors",
            readiness.is_ready_for_publish
              ? "border-emerald-500/40 shadow-xs"
              : readiness.blockers.length > 0
                ? "border-border"
                : "border-amber-500/30"
          )}
        >
          {/* 1-Row Summary Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-3 sm:px-4">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="shrink-0">
                {readiness.is_ready_for_publish ? (
                  <CheckCircle2 className="size-4.5 text-emerald-600 dark:text-emerald-400" />
                ) : readiness.blockers.length > 0 ? (
                  <XCircle className="size-4.5 text-destructive" />
                ) : (
                  <AlertTriangle className="size-4.5 text-amber-600 dark:text-amber-400" />
                )}
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="font-semibold text-sm text-foreground">
                  {readiness.is_ready_for_publish
                    ? "Trợ lý AI Đã Sẵn Sàng Xuất Bản"
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
                  className="text-xs px-2 py-0.5"
                >
                  {passedChecksCount}/{totalChecksCount} Tiêu chí (
                  {readiness.overall_readiness_score}%)
                </Badge>
                {readiness.blockers.length > 0 && !isReadinessExpanded && (
                  <span className="hidden md:inline text-xs text-muted-foreground truncate max-w-md">
                    • {readiness.blockers[0]}
                    {readiness.blockers.length > 1 &&
                      ` (+${readiness.blockers.length - 1} lỗi khác)`}
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-center">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 px-2.5 text-xs gap-1 text-muted-foreground hover:text-foreground"
                onClick={() => setIsReadinessExpanded((prev) => !prev)}
              >
                <span>
                  {isReadinessExpanded
                    ? "Thu gọn"
                    : `Chi tiết (${readiness.blockers.length > 0 ? `${readiness.blockers.length} lỗi` : "tiêu chí"})`}
                </span>
                {isReadinessExpanded ? (
                  <ChevronUp className="size-3.5" />
                ) : (
                  <ChevronDown className="size-3.5" />
                )}
              </Button>

              {onRefetchReadiness && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground gap-1"
                  disabled={isReadinessFetching}
                  onClick={onRefetchReadiness}
                >
                  <RefreshCw className={cn("size-3.5", isReadinessFetching && "animate-spin")} />
                  Kiểm tra
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
                  className="h-8 gap-1.5 text-xs"
                  variant={assistant.is_active ? "outline" : "default"}
                >
                  <Rocket className="size-3.5" />
                  {isPublishing
                    ? "Đang xuất bản..."
                    : assistant.is_active
                      ? "Tái xuất bản"
                      : "Xuất Bản Trợ Lý"}
                </Button>
              )}
            </div>
          </div>

          {/* Collapsible Expanded Details */}
          {isReadinessExpanded && (
            <div className="border-t border-border/50 px-4 py-3 bg-muted/20 space-y-3 text-xs">
              {readiness.checks && readiness.checks.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {readiness.checks.map((c) => (
                    <span
                      key={c.name}
                      className={cn(
                        "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium border",
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
                      <span>{c.name}:</span>
                      <span className="font-semibold">{c.score}/100</span>
                    </span>
                  ))}
                </div>
              )}

              {readiness.blockers.length > 0 && (
                <div className="rounded-md bg-destructive/10 p-2.5 border border-destructive/20">
                  <p className="font-semibold text-destructive mb-1 flex items-center gap-1.5">
                    <AlertCircle className="size-3.5 shrink-0" />
                    Danh sách các tiêu chí chặn xuất bản cần khắc phục:
                  </p>
                  <ul className="space-y-1 pl-5 list-disc text-destructive">
                    {readiness.blockers.map((b) => (
                      <li key={b}>{b}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
