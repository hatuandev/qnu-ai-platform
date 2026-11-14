import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Bot,
  Database,
  LayoutDashboard,
  ListChecks,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Play,
  RefreshCw,
  ScrollText,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import {
  useAssistantQuery,
  useAssistantReadinessQuery,
  useDeleteAssistantMutation,
} from "@/api/assistants";
import { ApiProblemError } from "@/api/client";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { PageBreadcrumbs } from "@/components/admin/page-breadcrumbs";
import { PageHeader } from "@/components/admin/page-header";
import { AnswerReviewHistory } from "@/components/assistants/answer-review-history";
import { AskTestPanel } from "@/components/assistants/ask-test-panel";
import { AssistantConfigForm } from "@/components/assistants/assistant-config-form";
import { AssistantLogs } from "@/components/assistants/assistant-logs";
import { AssistantOverview } from "@/components/assistants/assistant-overview";
import {
  READINESS_MAP,
  readinessHeroLabel,
} from "@/components/assistants/readiness";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useUiStore } from "@/lib/ui-store";

const assistantDetailSearchSchema = z.object({
  tab: z
    .enum(["overview", "config", "ask", "reviews", "logs"])
    .catch("overview"),
});

type AssistantTab = z.infer<typeof assistantDetailSearchSchema>["tab"];

const updatedAtFormatter = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export const Route = createFileRoute("/assistants/$assistantId")({
  validateSearch: (search) => assistantDetailSearchSchema.parse(search),
  component: AssistantDetailPage,
});

function AssistantDetailPage() {
  const { assistantId } = Route.useParams();
  const { tab } = Route.useSearch();
  const navigate = Route.useNavigate();
  const workspaceId = useUiStore((state) => state.activeWorkspaceId);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const deleteMutation = useDeleteAssistantMutation(workspaceId);

  const {
    data: assistant,
    isError,
    error,
    refetch,
  } = useAssistantQuery(workspaceId, assistantId);
  const {
    data: readiness,
    refetch: refetchReadiness,
    isRefetching: isRefreshingReadiness,
  } = useAssistantReadinessQuery(workspaceId, assistant?.id);

  const goToTab = (next: AssistantTab) => {
    void navigate({ search: { tab: next }, replace: true });
  };

  if (!workspaceId) {
    return (
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <EmptyState
          icon={Bot}
          title="Chưa chọn đơn vị"
          description="Chọn một đơn vị ở thanh bên để mở trợ lý AI."
        />
      </div>
    );
  }

  if (isError) {
    const isNotFound =
      error instanceof ApiProblemError && error.kind === "not_found";
    return (
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <EmptyState
          icon={Bot}
          title={
            isNotFound
              ? "Không tìm thấy trợ lý"
              : "Không tải được cấu hình trợ lý"
          }
          description={
            isNotFound
              ? "Trợ lý có thể đã bị xóa hoặc không thuộc đơn vị đang chọn."
              : "Kết nối tới máy chủ không thành công hoặc phiên đăng nhập đã hết hạn."
          }
          action={
            isNotFound
              ? {
                  label: "Về danh sách trợ lý",
                  onClick: () => void navigate({ to: "/assistants" }),
                }
              : { label: "Tải lại", onClick: () => void refetch() }
          }
        />
      </div>
    );
  }

  if (!assistant) {
    return (
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <Skeleton className="h-4 w-56" />
        <Skeleton className="h-16 w-full rounded-lg" />
        <Skeleton className="h-40 w-full rounded-lg" />
      </div>
    );
  }

  const readinessBadge = readiness
    ? READINESS_MAP[readiness.status]
    : undefined;
  const collectionName =
    readiness?.collection_name ?? "Kho tri thức đang liên kết";

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(assistant.id);
      toast.success(`Đã xóa trợ lý "${assistant.name}"`);
      setDeleteOpen(false);
      void navigate({ to: "/assistants" });
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Không xóa được trợ lý.",
      );
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <PageBreadcrumbs
        items={[
          { label: "Trợ lý AI", to: "/assistants", icon: Bot },
          { label: assistant.name },
        ]}
      />

      <PageHeader
        eyebrow="Trợ lý AI"
        title={
          <div className="flex flex-wrap items-center gap-2">
            <span>{assistant.name}</span>
            {readinessBadge ? (
              <Badge
                variant={readinessBadge.variant}
                className="h-5 px-1.5 text-[11px] font-normal"
              >
                {readinessHeroLabel(readiness?.status ?? "uncertain")}
              </Badge>
            ) : null}
            {!assistant.is_active ? (
              <Badge
                variant="warning"
                className="h-5 px-1.5 text-[11px] font-normal"
              >
                Tạm dừng
              </Badge>
            ) : null}
          </div>
        }
        description={
          <span className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
            {assistant.description ? (
              <span>{assistant.description}</span>
            ) : (
              <span>Chưa có mô tả.</span>
            )}
            <span>·</span>
            <span>{collectionName}</span>
            <span>·</span>
            <span>
              Cập nhật{" "}
              {updatedAtFormatter.format(new Date(assistant.updated_at))}
            </span>
            <span>·</span>
            <span>Phiên bản {assistant.revision}</span>
          </span>
        }
        actions={
          <div className="flex shrink-0 items-center gap-2">
            {tab !== "ask" ? (
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-1.5 text-xs font-medium"
                onClick={() => goToTab("ask")}
              >
                <Play className="size-3.5 text-primary" />
                <span>Hỏi thử</span>
              </Button>
            ) : null}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="size-8 p-0"
                  aria-label="Thao tác khác cho trợ lý"
                >
                  <MoreHorizontal className="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48 text-xs">
                <DropdownMenuItem
                  disabled={isRefreshingReadiness}
                  onClick={() => void refetchReadiness()}
                >
                  <RefreshCw className="size-3.5" />
                  <span>Tải lại trạng thái</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => goToTab("config")}>
                  <Pencil className="size-3.5" />
                  <span>Chỉnh cấu hình</span>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link
                    to="/knowledge"
                    search={{ collectionId: assistant.collection_id }}
                  >
                    <Database className="size-3.5" />
                    <span>Mở kho tri thức</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive"
                  onClick={() => setDeleteOpen(true)}
                >
                  <Trash2 className="size-3.5" />
                  <span>Xóa trợ lý</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        }
      />

      <Tabs
        value={tab}
        onValueChange={(value) => goToTab(value as AssistantTab)}
        className="space-y-4"
      >
        <TabsList className="w-full justify-start overflow-x-auto sm:w-auto">
          <TabsTrigger value="overview" className="gap-1.5 text-xs">
            <LayoutDashboard className="size-3.5" />
            <span>Tổng quan</span>
          </TabsTrigger>
          <TabsTrigger value="config" className="gap-1.5 text-xs">
            <SlidersHorizontal className="size-3.5" />
            <span>Cấu hình</span>
          </TabsTrigger>
          <TabsTrigger value="ask" className="gap-1.5 text-xs">
            <MessageSquare className="size-3.5" />
            <span>Hỏi thử</span>
          </TabsTrigger>
          <TabsTrigger value="reviews" className="gap-1.5 text-xs">
            <ListChecks className="size-3.5" />
            <span>Kiểm thử</span>
          </TabsTrigger>
          <TabsTrigger value="logs" className="gap-1.5 text-xs">
            <ScrollText className="size-3.5" />
            <span>Nhật ký</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <AssistantOverview
            workspaceId={workspaceId}
            assistant={assistant}
            readiness={readiness}
            isRefreshingReadiness={isRefreshingReadiness}
            onRefreshReadiness={() => void refetchReadiness()}
          />
        </TabsContent>

        <TabsContent
          value="config"
          forceMount
          className="data-[state=inactive]:hidden"
        >
          <AssistantConfigForm
            workspaceId={workspaceId}
            assistant={assistant}
          />
        </TabsContent>

        <TabsContent value="ask">
          <AskTestPanel workspaceId={workspaceId} assistant={assistant} />
        </TabsContent>

        <TabsContent value="reviews">
          <AnswerReviewHistory
            workspaceId={workspaceId}
            assistantId={assistant.id}
            onGoToAsk={() => goToTab("ask")}
          />
        </TabsContent>

        <TabsContent value="logs">
          <AssistantLogs workspaceId={workspaceId} assistantId={assistant.id} />
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title={`Xóa trợ lý "${assistant.name}"?`}
        description={
          <span>
            Trợ lý sẽ bị xóa vĩnh viễn và không thể khôi phục. Các lượt hỏi đang
            chạy sẽ bị hủy; lịch sử hội thoại và kiểm thử đã ghi nhận được giữ
            lại để tra cứu.
          </span>
        }
        confirmLabel="Xóa trợ lý"
        isLoading={deleteMutation.isPending}
        onConfirm={() => void handleDelete()}
      />
    </div>
  );
}
