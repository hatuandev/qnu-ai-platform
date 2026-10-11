import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { Button } from "@/components/ui/button";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";

export function DeleteSourceButton({
  sourceId,
  title,
  onDeleted,
}: {
  sourceId: string;
  title: string;
  onDeleted?: () => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const handled = useRef<string | null>(null);
  const client = useQueryClient();
  const job = useQuery({
    queryKey: ["knowledge-source-purge", sourceId, jobId],
    queryFn: () => {
      if (!jobId) throw new Error("Chưa có tác vụ xóa.");
      return knowledgeApi.getSourcePurgeJob(sourceId, jobId);
    },
    enabled: !!jobId,
    refetchInterval: (query) =>
      ["completed", "failed", "cancelled"].includes(
        query.state.data?.status || "",
      )
        ? false
        : 1000,
  });
  useEffect(() => {
    if (!job.data || handled.current === job.data.id) return;
    if (job.data.status === "completed") {
      handled.current = job.data.id;
      setIsOpen(false);
      void client.invalidateQueries({
        predicate: (q) =>
          String(q.queryKey[0]).includes("knowledge") ||
          q.queryKey[0] === "collection-summary-metrics",
      });
      toast.success("Đã xóa vĩnh viễn nguồn. Tệp ở Kho tài liệu vẫn được giữ.");
      onDeleted?.();
    } else if (job.data.status === "failed") {
      handled.current = job.data.id;
      toast.error(job.data.error || "Chưa xóa xong. Bạn có thể thử lại.");
    }
  }, [job.data, client, onDeleted]);
  const remove = useMutation({
    mutationFn: () => knowledgeApi.purgeSource(sourceId),
    onSuccess: (data) => {
      handled.current = null;
      client.setQueryData(["knowledge-source-purge", sourceId, data.id], data);
      setJobId(data.id);
    },
    onError: (err) =>
      toast.error(extractErrorMessage(err, "Không xóa được nguồn.")),
  });
  const isDeleting =
    remove.isPending ||
    (!!jobId && (!job.data || ["queued", "running"].includes(job.data.status)));
  return (
    <>
      <Button
        size="sm"
        variant="outline"
        className="text-destructive"
        onClick={() => setIsOpen(true)}
      >
        <Trash2 className="size-3.5" /> {isDeleting ? "Đang xóa" : "Xóa"}
      </Button>
      <ConfirmDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title="Xóa vĩnh viễn nguồn?"
        description={
          <>
            Xóa <strong>{title}</strong> cùng nội dung OCR, snapshot, chunks, dữ
            liệu số và vector thuộc nguồn trong Kho tri thức. Không thể hoàn
            tác. Tệp gốc trong Kho tài liệu và dữ liệu của nguồn khác được giữ
            nguyên.
            {isDeleting && (
              <p className="mt-2">
                Worker đang dọn dữ liệu. Bạn có thể đóng cửa sổ; tác vụ vẫn tiếp
                tục.
              </p>
            )}
            {job.data?.status === "failed" && (
              <p className="mt-2 text-destructive">
                {job.data.error || "Chưa xóa xong."} Bấm Xóa để thử lại.
              </p>
            )}
            {job.isError && (
              <p className="mt-2 text-destructive">
                Không đọc được tiến trình. Chưa xác nhận xóa xong; xem lại khi
                kết nối được phục hồi.
              </p>
            )}
          </>
        }
        confirmText="Xóa"
        isPending={isDeleting}
        onConfirm={() => remove.mutate()}
      />
    </>
  );
}
