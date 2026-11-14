import { createFileRoute } from "@tanstack/react-router";
import { Bot, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import {
  type AssistantResponse,
  useAssistantsQuery,
  useDeleteAssistantMutation,
  useUpdateAssistantMutation,
} from "@/api/assistants";
import { ApiProblemError } from "@/api/client";
import { useCollectionsQuery } from "@/api/knowledge";
import { useCatalogQuery } from "@/api/modelops";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { PageHeader } from "@/components/admin/page-header";
import { AssistantCard } from "@/components/assistants/assistant-card";
import { AssistantFormDialog } from "@/components/assistants/assistant-form-dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useUiStore } from "@/lib/ui-store";

export const Route = createFileRoute("/assistants/")({
  component: AssistantsPage,
});

function updatePayload(
  assistant: AssistantResponse,
  overrides?: { is_active?: boolean },
) {
  return {
    name: assistant.name,
    description: assistant.description,
    persona: assistant.persona,
    collection_id: assistant.collection_id,
    chat_provider_id: assistant.chat_provider_id,
    top_k: assistant.top_k,
    history_turns: assistant.history_turns,
    max_output_tokens: assistant.max_output_tokens,
    is_active: overrides?.is_active ?? assistant.is_active,
    rag_policy: assistant.rag_policy,
    expected_revision: assistant.revision,
  };
}

function AssistantsPage() {
  const workspaceId = useUiStore((state) => state.activeWorkspaceId);
  const {
    data: assistants = [],
    isLoading,
    isError,
    refetch,
  } = useAssistantsQuery(workspaceId);
  const { data: collectionsPage } = useCollectionsQuery(workspaceId, {
    page: 1,
    pageSize: 100,
  });
  const { data: catalog = [] } = useCatalogQuery(workspaceId);
  const updateMutation = useUpdateAssistantMutation(workspaceId);
  const deleteMutation = useDeleteAssistantMutation(workspaceId);

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<AssistantResponse | null>(null);
  const [deleting, setDeleting] = useState<AssistantResponse | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const collectionNames = useMemo(
    () =>
      new Map(
        (collectionsPage?.items ?? []).map((item) => [item.id, item.name]),
      ),
    [collectionsPage],
  );
  const models = useMemo(
    () => new Map(catalog.map((item) => [item.id, item])),
    [catalog],
  );

  const openCreate = () => {
    setEditing(null);
    setFormOpen(true);
  };

  const openEdit = (assistant: AssistantResponse) => {
    setEditing(assistant);
    setFormOpen(true);
  };

  const handleToggleActive = async (assistant: AssistantResponse) => {
    setTogglingId(assistant.id);
    try {
      await updateMutation.mutateAsync({
        assistantId: assistant.id,
        data: updatePayload(assistant, { is_active: !assistant.is_active }),
      });
      toast.success(
        assistant.is_active
          ? `Đã tạm dừng "${assistant.name}"`
          : `Đã bật lại "${assistant.name}"`,
      );
    } catch (err: unknown) {
      if (
        err instanceof ApiProblemError &&
        err.code === "assistant_revision_conflict"
      ) {
        toast.error(
          "Cấu hình trợ lý vừa thay đổi. Danh sách đã được tải lại, vui lòng thử lại.",
        );
        void refetch();
      } else if (err instanceof ApiProblemError && err.kind === "forbidden") {
        toast.error("Chỉ quản trị viên của đơn vị mới có thể đổi trạng thái.");
      } else {
        toast.error(
          err instanceof Error
            ? err.message
            : "Không thể đổi trạng thái trợ lý.",
        );
      }
    } finally {
      setTogglingId(null);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleting) return;
    try {
      await deleteMutation.mutateAsync(deleting.id);
      toast.success(`Đã xóa vĩnh viễn "${deleting.name}"`);
      setDeleting(null);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Không thể xóa trợ lý.");
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <PageHeader
        eyebrow="Tương tác & Triển khai"
        title="Trợ lý AI"
        description="Cấu hình trợ lý theo kho tri thức, mô hình và chỉ dẫn trả lời."
        actions={
          <Button
            size="sm"
            className="h-8 gap-1.5 text-xs"
            onClick={openCreate}
            disabled={!workspaceId}
          >
            <Plus className="size-3.5" />
            <span>Tạo trợ lý</span>
          </Button>
        }
      />

      {!workspaceId ? (
        <EmptyState
          icon={Bot}
          title="Chưa chọn đơn vị"
          description="Chọn một đơn vị ở thanh bên để quản lý trợ lý AI."
        />
      ) : isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {["first", "second", "third"].map((slot) => (
            <Skeleton
              key={`assistant-skeleton-${slot}`}
              className="h-48 rounded-lg"
            />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={Bot}
          title="Không tải được danh sách trợ lý"
          description="Kết nối tới máy chủ không thành công hoặc phiên đăng nhập đã hết hạn."
          action={{ label: "Tải lại", onClick: () => void refetch() }}
        />
      ) : assistants.length === 0 ? (
        <EmptyState
          icon={Bot}
          title="Chưa có trợ lý nào"
          description="Tạo trợ lý đầu tiên, gắn với một kho tri thức đã xuất bản nội dung."
          action={{ label: "Tạo trợ lý", onClick: openCreate }}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {assistants.map((assistant) => (
            <AssistantCard
              key={assistant.id}
              workspaceId={workspaceId}
              assistant={assistant}
              collectionName={
                collectionNames.get(assistant.collection_id) ??
                "Kho tri thức không khả dụng"
              }
              model={
                assistant.chat_provider_id
                  ? models.get(assistant.chat_provider_id)
                  : null
              }
              onEdit={openEdit}
              onToggleActive={(item) => void handleToggleActive(item)}
              onDelete={setDeleting}
              isToggling={togglingId === assistant.id}
            />
          ))}
        </div>
      )}

      {workspaceId && (
        <AssistantFormDialog
          open={formOpen}
          onOpenChange={setFormOpen}
          workspaceId={workspaceId}
          assistant={editing}
        />
      )}

      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
        title="Xóa vĩnh viễn trợ lý?"
        confirmLabel="Xóa vĩnh viễn"
        isLoading={deleteMutation.isPending}
        onConfirm={() => void handleConfirmDelete()}
        description={
          <span>
            Trợ lý <strong>{deleting?.name}</strong> cùng toàn bộ hội thoại và
            kết quả kiểm thử câu trả lời sẽ bị xóa vĩnh viễn, không thể hoàn
            tác. Kho tri thức và tài liệu nguồn không bị ảnh hưởng.
          </span>
        }
      />
    </div>
  );
}
