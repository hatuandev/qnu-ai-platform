import { Link } from "@tanstack/react-router";
import {
  Bot,
  Database,
  MessageSquare,
  MoreHorizontal,
  Pause,
  Pencil,
  Play,
  Trash2,
} from "lucide-react";
import {
  type AssistantResponse,
  useAssistantReadinessQuery,
} from "@/api/assistants";
import type { CatalogItem } from "@/api/modelops";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
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
import { READINESS_MAP, readinessDetail } from "./readiness";

const dateFormatter = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function modelLabel(
  model: CatalogItem | null | undefined,
  providerId: string | null,
): string {
  if (!providerId) return "Mô hình tự động theo hệ thống";
  return model?.model_name ?? "Mô hình không còn trong danh mục";
}

export function AssistantCard({
  workspaceId,
  assistant,
  collectionName,
  model,
  onEdit,
  onToggleActive,
  onDelete,
  isToggling,
}: {
  workspaceId: string;
  assistant: AssistantResponse;
  collectionName: string;
  model?: CatalogItem | null;
  onEdit: (assistant: AssistantResponse) => void;
  onToggleActive: (assistant: AssistantResponse) => void;
  onDelete: (assistant: AssistantResponse) => void;
  isToggling: boolean;
}) {
  const { data: readiness } = useAssistantReadinessQuery(
    workspaceId,
    assistant.id,
  );
  const readinessBadge = readiness ? READINESS_MAP[readiness.status] : null;

  return (
    <Card className="relative flex flex-col border-border/60 shadow-2xs transition-colors hover:border-primary/50">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Bot className="size-4" />
          </div>
          <div className="min-w-0">
            <CardTitle className="truncate text-sm font-semibold">
              <Link
                to="/assistants/$assistantId"
                params={{ assistantId: assistant.id }}
                search={{ tab: "overview" }}
                className="text-left hover:underline"
              >
                {assistant.name}
              </Link>
            </CardTitle>
            <p className="truncate text-[11px] text-muted-foreground">
              {modelLabel(model, assistant.chat_provider_id)}
            </p>
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="size-7 shrink-0 p-0"
              aria-label={`Thao tác cho ${assistant.name}`}
            >
              <MoreHorizontal className="size-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-44 text-xs">
            <DropdownMenuItem asChild>
              <Link
                to="/assistants/$assistantId"
                params={{ assistantId: assistant.id }}
                search={{ tab: "ask" }}
              >
                <MessageSquare className="size-3.5" />
                <span>Hỏi thử</span>
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onEdit(assistant)}>
              <Pencil className="size-3.5" />
              <span>Chỉnh sửa</span>
            </DropdownMenuItem>
            <DropdownMenuItem
              disabled={isToggling}
              onClick={() => onToggleActive(assistant)}
            >
              {assistant.is_active ? (
                <Pause className="size-3.5" />
              ) : (
                <Play className="size-3.5" />
              )}
              <span>
                {assistant.is_active ? "Tạm dừng" : "Tiếp tục phục vụ"}
              </span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => onDelete(assistant)}
            >
              <Trash2 className="size-3.5" />
              <span>Xóa vĩnh viễn</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>

      <CardContent className="flex-1 space-y-3 pb-3">
        <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
          {assistant.description || "Chưa có mô tả."}
        </p>
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge
            variant="secondary"
            className="h-4 gap-1 px-1.5 text-[10px] font-normal"
          >
            <Database className="size-3" />
            <span className="max-w-52 truncate">{collectionName}</span>
          </Badge>
          {!assistant.is_active && (
            <Badge
              variant="warning"
              className="h-4 px-1.5 text-[10px] font-normal"
            >
              Tạm dừng
            </Badge>
          )}
          {readinessBadge && (
            <Badge
              variant={readinessBadge.variant}
              className="h-4 px-1.5 text-[10px] font-normal"
            >
              {readinessBadge.label}
            </Badge>
          )}
        </div>
        {readiness && (
          <p className="text-[11px] text-muted-foreground">
            {readinessDetail(
              readiness.status,
              readiness.served_document_count,
              readiness.published_document_count,
            )}
          </p>
        )}
      </CardContent>

      <CardFooter className="flex items-center justify-between border-t border-border/40 pt-2 text-[11px] text-muted-foreground">
        <span>
          Cập nhật {dateFormatter.format(new Date(assistant.updated_at))}
        </span>
        <span>Phiên bản {assistant.revision}</span>
      </CardFooter>
    </Card>
  );
}
