import {
  Award,
  BookOpen,
  Bot,
  CheckCircle2,
  Code,
  Copy,
  Download,
  GraduationCap,
  History,
  Library,
  MessageSquare,
  MoreHorizontal,
  Network,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Switch } from "@/components/ui/switch";
import type { AssistantItem } from "@/types/assistants";

interface AssistantCardProps {
  assistant: AssistantItem;
  onOpen: () => void;
  onChat: () => void;
  onOpenWorkflow: () => void;
  onClone?: () => void;
  onExport?: () => void;
  onHistory?: () => void;
  onEmbed?: () => void;
  onToggleActive?: (active: boolean) => void;
  isToggling?: boolean;
}

function getCategoryIcon(category: string) {
  switch (category) {
    case "admissions":
      return GraduationCap;
    case "academic":
      return ShieldCheck;
    case "resources":
      return Library;
    case "administration":
      return BookOpen;
    case "examination":
      return Award;
    default:
      return Bot;
  }
}

function formatCategoryLabel(category: string): string {
  switch (category) {
    case "admissions":
      return "Tuyển sinh";
    case "academic":
      return "Học vụ";
    case "resources":
      return "Thư viện";
    case "administration":
      return "Hành chính";
    case "examination":
      return "Khảo thí";
    default:
      return "Tổng hợp";
  }
}

export function AssistantCard({
  assistant,
  onOpen,
  onChat,
  onOpenWorkflow,
  onClone,
  onExport,
  onHistory,
  onEmbed,
  onToggleActive,
  isToggling,
}: AssistantCardProps) {
  const Icon = getCategoryIcon(assistant.category);
  const modelPolicy = assistant.config?.model_policy;
  const guardrails = assistant.config?.guardrails;

  return (
    <Card className="group flex h-full flex-col border-border/80 transition-all hover:border-primary/50 hover:shadow-xs">
      <CardHeader className="space-y-2.5 p-4 pb-2">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary transition-transform group-hover:scale-105">
              <Icon className="size-5" />
            </div>
            <div className="min-w-0">
              <CardTitle
                className="text-sm font-bold text-foreground line-clamp-1 group-hover:text-primary transition-colors cursor-pointer"
                onClick={onOpen}
              >
                {assistant.name}
              </CardTitle>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="font-mono text-[10px] text-muted-foreground truncate">
                  {assistant.code}
                </span>
                <Badge variant="outline" className="text-[9px] px-1 py-0 h-4">
                  {formatCategoryLabel(assistant.category)}
                </Badge>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <Switch
              checked={assistant.is_active}
              disabled={isToggling}
              onCheckedChange={(checked) => onToggleActive?.(checked)}
              aria-label={`Trạng thái hoạt động ${assistant.name}`}
            />
          </div>
        </div>

        <CardDescription className="line-clamp-2 text-xs leading-relaxed text-muted-foreground min-h-8">
          {assistant.description ||
            "Chưa có phần giới thiệu chi tiết cho trợ lý này."}
        </CardDescription>
      </CardHeader>

      <CardContent className="mt-auto space-y-2.5 p-4 pt-0">
        <div className="grid gap-1.5 border-t border-border/70 pt-2 text-xs">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground">
              Mô hình AI:
            </span>
            <span className="truncate font-mono text-[11px] font-medium text-foreground">
              {modelPolicy?.primary_model || "Mặc định"}
            </span>
          </div>

          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground">
              Kho Tri Thức:
            </span>
            <span className="truncate font-mono text-[11px] text-muted-foreground">
              {assistant.collection_id || "Chưa gán"}
            </span>
          </div>

          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground">
              Tiêu chuẩn:
            </span>
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-success">
              <CheckCircle2 className="size-3" />
              {guardrails?.require_grounded_answer
                ? "TM-08 Grounded"
                : "Cơ bản"}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 pt-1">
          <Button
            variant="outline"
            size="sm"
            className="h-8 flex-1 text-xs gap-1 px-2"
            onClick={onChat}
            title="Thử trò chuyện trực tiếp"
          >
            <MessageSquare className="size-3 text-primary shrink-0" />
            <span className="truncate">Thử nghiệm</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="h-8 flex-1 text-xs gap-1 px-2 border-primary/20 text-primary hover:bg-primary/10"
            onClick={onOpen}
            title="Mở trung tâm quản trị trợ lý"
          >
            <Settings className="size-3 shrink-0" />
            <span className="truncate">Quản trị</span>
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-muted-foreground shrink-0"
                title="Thao tác khác"
              >
                <MoreHorizontal className="size-3.5" />
                <span className="sr-only">Thao tác</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44 text-xs">
              {onOpenWorkflow && (
                <DropdownMenuItem onClick={onOpenWorkflow}>
                  <Network className="size-3.5 mr-2 text-primary" />
                  <span>Sơ đồ DAG</span>
                </DropdownMenuItem>
              )}
              {onClone && (
                <DropdownMenuItem onClick={onClone}>
                  <Copy className="size-3.5 mr-2 text-primary" />
                  <span>Nhân bản</span>
                </DropdownMenuItem>
              )}
              {onHistory && (
                <DropdownMenuItem onClick={onHistory}>
                  <History className="size-3.5 mr-2 text-primary" />
                  <span>Lịch sử</span>
                </DropdownMenuItem>
              )}
              {onEmbed && (
                <DropdownMenuItem onClick={onEmbed}>
                  <Code className="size-3.5 mr-2 text-primary" />
                  <span>Mã nhúng</span>
                </DropdownMenuItem>
              )}
              {onExport && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={onExport}>
                    <Download className="size-3.5 mr-2 text-primary" />
                    <span>Xuất bundle</span>
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardContent>
    </Card>
  );
}
