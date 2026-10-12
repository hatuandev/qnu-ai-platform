import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Pause } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { Button } from "@/components/ui/button";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";

export function PauseSourceButton({
  sourceId,
  title,
  status,
}: {
  sourceId: string;
  title: string;
  status: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const client = useQueryClient();
  const pause = useMutation({
    mutationFn: () => knowledgeApi.pauseSource(sourceId),
    onSuccess: () => {
      setIsOpen(false);
      void client.invalidateQueries({
        predicate: (query) =>
          String(query.queryKey[0]).includes("knowledge") ||
          query.queryKey[0] === "collection-summary-metrics",
      });
      toast.success(
        "Đã ngừng dùng nguồn cho lượt tra cứu mới. Dữ liệu được giữ nguyên.",
      );
    },
    onError: (error) =>
      toast.error(extractErrorMessage(error, "Không ngừng dùng được nguồn.")),
  });
  return (
    <>
      <Button
        size="sm"
        variant="outline"
        disabled={!["active", "pending"].includes(status) || pause.isPending}
        onClick={() => setIsOpen(true)}
      >
        <Pause className="size-3.5" />
        {status === "paused"
          ? "Đã ngừng"
          : pause.isPending
            ? "Đang ngừng"
            : "Ngừng dùng"}
      </Button>
      <ConfirmDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title="Ngừng dùng nguồn?"
        description={
          <>
            Chatbot sẽ không dùng <strong>{title}</strong> trong lượt tra cứu
            mới. Tệp gốc, Markdown và vector vẫn được giữ. Câu trả lời đang xử
            lý có thể hoàn tất bằng bản cũ. Bạn có thể xóa nguồn sau khi ngừng.
          </>
        }
        confirmText="Ngừng dùng"
        variant="default"
        isPending={pause.isPending}
        onConfirm={() => pause.mutate()}
      />
    </>
  );
}
