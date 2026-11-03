import { Link, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  Bot,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Clock,
  Cpu,
  Database,
  ExternalLink,
  HelpCircle,
  Layers,
  MessageSquare,
  Pencil,
  Sliders,
  Sparkles,
  User,
} from "lucide-react";
import { useState } from "react";
import { CopyButton } from "@/components/admin/copy-button";
import { ErrorState } from "@/components/admin/error-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { AssistantFormDialog } from "@/features/assistants/assistant-form-dialog";
import { canManageAssistants } from "@/features/assistants/permissions";
import { useAssistantQuery } from "@/features/assistants/queries";
import { DEFAULT_ASSISTANT_SEARCH } from "@/features/assistants/schemas";
import { ConversationCreateDialog } from "@/features/conversations/conversation-create-dialog";
import { useCollectionQuery } from "@/features/knowledge/queries";
import { LifecycleActions } from "@/features/lifecycle/lifecycle-actions";
import { useCatalogQuery } from "@/features/modelops/queries";
import { RagPolicySummary } from "@/features/rag/rag-policy-summary";
import {
  useCallerWorkspaceRole,
  useWorkspaceQuery,
} from "@/features/workspaces/queries";
import { DEFAULT_PAGE_SEARCH } from "@/features/workspaces/search";
import { formatDateTimeValue } from "@/lib/date-utils";

export function AssistantDetailPage({
  workspaceId,
  assistantId,
}: {
  workspaceId: string;
  assistantId: string;
}) {
  const navigate = useNavigate();
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const workspaceQuery = useWorkspaceQuery(workspaceId);
  const assistantQuery = useAssistantQuery(workspaceId, assistantId);

  const assistant = assistantQuery.data;
  const collectionId = assistant?.collection_id ?? "";

  // Related collection query
  const collectionQuery = useCollectionQuery(workspaceId, collectionId);
  // Catalog query to resolve model information
  const catalogQuery = useCatalogQuery(workspaceId);

  const [editOpen, setEditOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  const canManage = !rolePending && canManageAssistants(role);

  // Model details from catalog
  const catalogItem = assistant?.chat_provider_id
    ? (catalogQuery.data ?? []).find(
        (item) => item.id === assistant.chat_provider_id,
      )
    : null;

  const isModelMissing =
    Boolean(assistant?.chat_provider_id) &&
    !catalogQuery.isPending &&
    !catalogItem;

  if (assistantQuery.isPending) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <Skeleton className="h-8 w-24" />
          <Skeleton className="h-8 w-48" />
        </div>
        <Card>
          <CardContent className="p-6 space-y-4">
            <Skeleton className="h-8 w-1/3" />
            <Skeleton className="h-20 w-full" />
            <div className="grid grid-cols-2 gap-4">
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (assistantQuery.isError || !assistant) {
    return (
      <div className="space-y-6">
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={() =>
            void navigate({
              to: "/workspaces/$workspaceId/assistants",
              params: { workspaceId },
              search: DEFAULT_ASSISTANT_SEARCH,
            })
          }
        >
          <ArrowLeft className="size-4" />
          Quay lại danh sách trợ lý
        </Button>
        <ErrorState
          error={assistantQuery.error}
          onRetry={() => void assistantQuery.refetch()}
          title="Không tìm thấy trợ lý AI"
          description="Trợ lý có thể đã bị xóa hoặc bạn không có quyền xem trong workspace này."
        />
      </div>
    );
  }

  const workspaceName = workspaceQuery.data?.name ?? workspaceId;

  return (
    <div className="space-y-6">
      {/* Breadcrumbs & Navigation */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
          <Link
            to="/workspaces/$workspaceId"
            params={{ workspaceId }}
            className="hover:text-foreground transition-colors"
          >
            {workspaceName}
          </Link>
          <ChevronRight className="size-3.5" />
          <Link
            to="/workspaces/$workspaceId/assistants"
            params={{ workspaceId }}
            search={DEFAULT_ASSISTANT_SEARCH}
            className="hover:text-foreground transition-colors"
          >
            Trợ lý AI
          </Link>
          <ChevronRight className="size-3.5" />
          <span className="font-medium text-foreground line-clamp-1">
            {assistant.name}
          </span>
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 text-xs self-start sm:self-auto"
          onClick={() =>
            void navigate({
              to: "/workspaces/$workspaceId/assistants",
              params: { workspaceId },
              search: DEFAULT_ASSISTANT_SEARCH,
            })
          }
        >
          <ArrowLeft className="size-3.5" />
          Danh sách trợ lý
        </Button>
      </div>

      {/* Main Header Card */}
      <Card className="overflow-hidden">
        <div className="border-b bg-muted/20 p-5 sm:p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
                  <Bot className="size-6 text-primary" />
                  {assistant.name}
                </h1>
                <Badge variant="outline" className="font-mono text-xs">
                  v{assistant.revision}
                </Badge>
                <Badge
                  variant={assistant.is_active ? "default" : "secondary"}
                  className="text-xs"
                >
                  {assistant.is_active ? "Đang bật" : "Đã tắt"}
                </Badge>
              </div>
              <p className="type-supporting text-muted-foreground max-w-2xl">
                {assistant.description || (
                  <span className="italic">Chưa có mô tả cho trợ lý này.</span>
                )}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              <Button
                size="sm"
                variant={assistant.is_active ? "default" : "secondary"}
                className="gap-2"
                disabled={!assistant.is_active}
                onClick={() => setChatOpen(true)}
              >
                <MessageSquare className="size-3.5" />
                Trò chuyện
              </Button>

              {canManage && (
                <>
                  <LifecycleActions
                    workspaceId={workspaceId}
                    kind="assistant"
                    resourceId={assistantId}
                    label={assistant.name}
                    role={role}
                    isActive={assistant.is_active}
                  />

                  <Button
                    size="sm"
                    className="gap-2"
                    onClick={() => setEditOpen(true)}
                  >
                    <Pencil className="size-3.5" />
                    Sửa cấu hình
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Metadata summary bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 text-xs bg-muted/5 border-t">
          <div className="space-y-0.5">
            <span className="text-muted-foreground flex items-center gap-1">
              <User className="size-3" /> Người tạo
            </span>
            <div className="font-mono font-medium truncate">
              {assistant.created_by || "Hệ thống"}
            </div>
          </div>

          <div className="space-y-0.5">
            <span className="text-muted-foreground flex items-center gap-1">
              <Calendar className="size-3" /> Thời gian tạo
            </span>
            <div className="font-medium">
              {formatDateTimeValue(assistant.created_at)}
            </div>
          </div>

          <div className="space-y-0.5">
            <span className="text-muted-foreground flex items-center gap-1">
              <Clock className="size-3" /> Cập nhật lần cuối
            </span>
            <div className="font-medium">
              {formatDateTimeValue(assistant.updated_at)}
            </div>
          </div>

          <div className="space-y-0.5">
            <span className="text-muted-foreground flex items-center gap-1">
              ID Trợ lý
            </span>
            <div className="flex items-center gap-1">
              <span className="font-mono text-[11px] truncate">
                {assistant.id}
              </span>
              <CopyButton
                value={assistant.id}
                tooltip="Sao chép ID trợ lý"
                showToast
                className="size-5"
              />
            </div>
          </div>
        </div>
      </Card>

      {/* Main Sections Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left & Middle columns: Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Section: Kho tri thức gắn kết */}
          <Card>
            <CardHeader className="pb-3 border-b">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Database className="size-4 text-primary" />
                  Kho tri thức gắn kết
                </CardTitle>
                <Badge variant="outline" className="text-[10px] uppercase">
                  Bất biến
                </Badge>
              </div>
              <CardDescription className="text-xs">
                Mỗi trợ lý AI được gắn cố định với một bộ sưu tập kho tri thức
                duy nhất trong workspace.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4 space-y-3">
              {collectionQuery.isPending ? (
                <div className="space-y-2">
                  <Skeleton className="h-5 w-40" />
                  <Skeleton className="h-4 w-60" />
                </div>
              ) : collectionQuery.isError ? (
                <Alert variant="destructive">
                  <AlertCircle className="size-4" />
                  <AlertTitle className="text-xs font-semibold">
                    Không thể tải thông tin bộ sưu tập
                  </AlertTitle>
                  <AlertDescription className="text-xs">
                    Mã bộ sưu tập:{" "}
                    <code className="font-mono">{assistant.collection_id}</code>
                    . Có thể bộ sưu tập đã bị thay đổi hoặc người dùng không có
                    quyền truy cập.
                  </AlertDescription>
                </Alert>
              ) : (
                <div className="rounded-lg border p-4 bg-muted/10 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground text-sm">
                      {collectionQuery.data.name}
                    </span>
                    <Link
                      to="/workspaces/$workspaceId/collections/$collectionId"
                      params={{
                        workspaceId,
                        collectionId: assistant.collection_id,
                      }}
                      search={DEFAULT_PAGE_SEARCH}
                      className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                    >
                      Xem tài liệu kho tri thức
                      <ExternalLink className="size-3" />
                    </Link>
                  </div>
                  {collectionQuery.data.description && (
                    <p className="text-xs text-muted-foreground">
                      {collectionQuery.data.description}
                    </p>
                  )}
                  <div className="pt-2 border-t text-[11px] text-muted-foreground flex items-center justify-between">
                    <span>
                      Mã bộ sưu tập:{" "}
                      <code className="font-mono">
                        {assistant.collection_id}
                      </code>
                    </span>
                    <span>
                      Cập nhật:{" "}
                      {formatDateTimeValue(collectionQuery.data.updated_at)}
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Section: Model Chat */}
          <Card>
            <CardHeader className="pb-3 border-b">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Cpu className="size-4 text-primary" />
                  Cấu hình Model Chat
                </CardTitle>
                <Link
                  to="/workspaces/$workspaceId/models"
                  params={{ workspaceId }}
                  className="text-xs text-muted-foreground hover:text-primary transition-colors flex items-center gap-1"
                >
                  Xem Model workspace
                  <ExternalLink className="size-3" />
                </Link>
              </div>
              <CardDescription className="text-xs">
                Model LLM thực hiện nhiệm vụ đọc ngữ cảnh tài liệu và sinh câu
                trả lời cho người dùng.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4 space-y-3">
              {assistant.chat_provider_id === null ? (
                <div className="rounded-lg border p-4 bg-muted/10 space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className="bg-primary/10 text-primary border-primary/20 text-xs font-medium"
                    >
                      Theo mặc định workspace
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Trợ lý này đang sử dụng model chat mặc định được gán cho
                    workspace qua hệ thống ModelOps. Khi workspace thay đổi
                    model chat mặc định, trợ lý sẽ tự động áp dụng cấu hình mới
                    mà không cần sửa cấu hình trợ lý.
                  </p>
                </div>
              ) : isModelMissing ? (
                <Alert className="border-amber-500/40 bg-amber-500/5 text-amber-900 dark:text-amber-200">
                  <AlertCircle className="size-4 text-amber-600 dark:text-amber-400" />
                  <AlertTitle className="text-xs font-semibold">
                    Provider không còn trong Catalog
                  </AlertTitle>
                  <AlertDescription className="text-xs space-y-1">
                    <p>
                      Mã provider đang lưu:{" "}
                      <code className="font-mono">
                        {assistant.chat_provider_id}
                      </code>{" "}
                      hiện không còn trong danh mục chat được cấp phép cho
                      workspace này.
                    </p>
                    <p className="text-muted-foreground">
                      Bạn nên sửa cấu hình để chuyển sang model chat khác hoặc
                      chuyển về &ldquo;Theo mặc định workspace&rdquo;.
                    </p>
                  </AlertDescription>
                </Alert>
              ) : catalogItem ? (
                <div className="rounded-lg border p-4 bg-muted/10 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground text-sm">
                      {catalogItem.name}
                    </span>
                    <Badge variant="outline" className="font-mono text-xs">
                      {catalogItem.model_name}
                    </Badge>
                  </div>
                  <div className="text-[11px] text-muted-foreground flex items-center gap-2">
                    <span>
                      Provider ID:{" "}
                      <code className="font-mono">{catalogItem.id}</code>
                    </span>
                    <span>•</span>
                    <span>
                      Capabilities: {catalogItem.capabilities.join(", ")}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="space-y-1">
                  <Skeleton className="h-5 w-40" />
                  <Skeleton className="h-4 w-60" />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Section: Persona & System Instructions */}
          <Card>
            <CardHeader className="pb-3 border-b">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Layers className="size-4 text-primary" />
                  Chỉ dẫn hệ thống (Persona)
                </CardTitle>
                {assistant.persona && (
                  <CopyButton
                    value={assistant.persona}
                    tooltip="Sao chép persona"
                    showToast
                    className="size-7"
                  />
                )}
              </div>
              <CardDescription className="text-xs">
                Lời nhắc định hình phong cách, giới hạn nghiệp vụ và căn cứ trả
                lời của trợ lý.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4">
              {assistant.persona ? (
                <div className="rounded-lg border bg-muted/20 p-4 font-mono text-xs leading-relaxed text-foreground whitespace-pre-wrap max-h-80 overflow-y-auto">
                  {assistant.persona}
                </div>
              ) : (
                <div className="rounded-lg border border-dashed p-6 text-center text-xs text-muted-foreground">
                  Chưa có chỉ dẫn persona riêng. Trợ lý sẽ hoạt động theo prompt
                  mặc định của hệ thống.
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right column: Parameters & Checklist */}
        <div className="space-y-6">
          {/* Section: Retrieval & Generation Parameters */}
          <Card>
            <CardHeader className="pb-3 border-b">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Sliders className="size-4 text-primary" />
                Tham số phản hồi & RAG
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4 text-xs">
              <div className="flex items-center justify-between pb-3 border-b">
                <div>
                  <div className="font-medium text-foreground">
                    Top K Chunks
                  </div>
                  <div className="text-muted-foreground text-[11px]">
                    Số đoạn tài liệu truy xuất vào ngữ cảnh
                  </div>
                </div>
                <Badge variant="secondary" className="font-mono text-xs">
                  {assistant.top_k}
                </Badge>
              </div>

              <div className="flex items-center justify-between pb-3 border-b">
                <div>
                  <div className="font-medium text-foreground">
                    Lượt hội thoại
                  </div>
                  <div className="text-muted-foreground text-[11px]">
                    Lịch sử hội thoại giữ trong ngữ cảnh
                  </div>
                </div>
                <Badge variant="secondary" className="font-mono text-xs">
                  {assistant.history_turns}
                </Badge>
              </div>

              <div className="flex items-center justify-between pb-3 border-b">
                <div>
                  <div className="font-medium text-foreground">
                    Max Output Tokens
                  </div>
                  <div className="text-muted-foreground text-[11px]">
                    Trần token tạo ra cho mỗi câu trả lời
                  </div>
                </div>
                <Badge variant="secondary" className="font-mono text-xs">
                  {assistant.max_output_tokens ?? "Tự động"}
                </Badge>
              </div>

              <RagPolicySummary policy={assistant.rag_policy} />
            </CardContent>
          </Card>

          {/* Section: Honest Condition Checklist */}
          <Card>
            <CardHeader className="pb-3 border-b">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <CheckCircle2 className="size-4 text-primary" />
                Điều kiện cấu hình
              </CardTitle>
              <CardDescription className="text-xs">
                Tình trạng khai báo tham số và các lưu ý trước khi triển khai
                hội thoại.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4 space-y-3.5 text-xs">
              {/* Check 1: Kho tri thức */}
              <div className="flex items-start gap-2.5">
                <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-medium text-foreground">
                    Bộ sưu tập kho tri thức
                  </div>
                  <div className="text-muted-foreground text-[11px]">
                    Đã liên kết với bộ sưu tập &ldquo;
                    {collectionQuery.data?.name ?? assistant.collection_id}
                    &rdquo;.
                  </div>
                </div>
              </div>

              {/* Check 2: Model Chat */}
              <div className="flex items-start gap-2.5">
                {isModelMissing ? (
                  <AlertCircle className="size-4 text-amber-500 shrink-0 mt-0.5" />
                ) : (
                  <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                )}
                <div>
                  <div className="font-medium text-foreground">
                    Model hội thoại
                  </div>
                  <div className="text-muted-foreground text-[11px]">
                    {assistant.chat_provider_id === null
                      ? "Đang dùng model chat mặc định của workspace."
                      : catalogItem
                        ? `Đã cấu hình provider ${catalogItem.name}.`
                        : "Cần chọn lại model chat hợp lệ."}
                  </div>
                </div>
              </div>

              {/* Check 3: Runtime vector indexing (Honest indicator) */}
              <div className="flex items-start gap-2.5 opacity-80">
                <HelpCircle className="size-4 text-muted-foreground shrink-0 mt-0.5" />
                <div>
                  <div className="font-medium text-foreground flex items-center gap-1">
                    Index & Xuất bản tri thức
                    <Badge variant="outline" className="text-[10px] py-0">
                      Chưa kiểm tra runtime
                    </Badge>
                  </div>
                  <div className="text-muted-foreground text-[11px]">
                    Trạng thái sẵn sàng của tài liệu trong kho tri thức cần được
                    nghiệm thu tại bước truy xuất thực tế.
                  </div>
                </div>
              </div>

              {/* Check 4: Inference test (Honest indicator) */}
              <div className="flex items-start gap-2.5">
                <Sparkles className="size-4 text-primary shrink-0 mt-0.5" />
                <div>
                  <div className="font-medium text-foreground flex items-center gap-1">
                    Chức năng Hội thoại (Chat)
                    <Badge variant="info" className="text-[10px] py-0">
                      Sẵn sàng
                    </Badge>
                  </div>
                  <div className="text-muted-foreground text-[11px]">
                    Bấm &ldquo;Chat thử&rdquo; trên thanh đầu trang để mở phiên
                    hội thoại và kiểm tra câu trả lời có dẫn nguồn bằng chứng.
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Edit Form Dialog */}
      <AssistantFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        workspaceId={workspaceId}
        assistant={assistant}
        onSuccess={() => setEditOpen(false)}
      />

      {/* Create Conversation Dialog */}
      <ConversationCreateDialog
        workspaceId={workspaceId}
        open={chatOpen}
        onOpenChange={setChatOpen}
        preselectedAssistant={assistant}
      />
    </div>
  );
}
