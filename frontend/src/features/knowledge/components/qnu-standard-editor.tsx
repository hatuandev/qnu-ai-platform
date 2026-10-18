import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";
import type { KnowledgeSourceRevisionResponse } from "@/types/knowledge";
import { refreshSourceQueries } from "../utils/source-query-cache";

export function QnuStandardEditor({
  collectionId,
  sourceId,
  revision,
  onSaved,
}: {
  collectionId: string;
  sourceId: string;
  revision: KnowledgeSourceRevisionResponse;
  onSaved: (revisionId: string) => void;
}) {
  const client = useQueryClient();
  const [draft, setDraft] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const content = useQuery({
    queryKey: ["qnu-standard", collectionId, sourceId, revision.id],
    queryFn: () =>
      knowledgeApi.getSourceQnuMarkdown(collectionId, sourceId, revision.id),
  });
  const save = useMutation({
    mutationFn: () =>
      knowledgeApi.updateSourceRevisionContent(
        collectionId,
        sourceId,
        revision.id,
        draft ?? "",
        {
          change_reason: reason.trim(),
          expected_canonical_hash: revision.canonical_hash ?? undefined,
          content_format: "qnu-rag-markdown/1.0",
        },
      ),
    onSuccess: async (saved) => {
      await refreshSourceQueries(client, collectionId, sourceId);
      setDraft(null);
      setReason("");
      onSaved(saved.id);
      toast.success("Đã tạo bản chuẩn chờ duyệt; chưa thay nguồn xuất bản.");
    },
    onError: (error) =>
      toast.error(extractErrorMessage(error, "Không lưu được bản chuẩn.")),
  });
  if (content.isPending)
    return (
      <p className="text-sm text-muted-foreground">
        Đang đọc bản QNU Markdown…
      </p>
    );
  if (content.isError)
    return (
      <div className="space-y-2">
        <p role="alert" className="text-sm text-destructive">
          {extractErrorMessage(content.error, "Không đọc được bản chuẩn.")}
        </p>
        <Button variant="outline" size="sm" onClick={() => content.refetch()}>
          Thử lại
        </Button>
      </div>
    );
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        QNU RAG Markdown v1.0.{" "}
        {revision.canonical_format === "qnu-rag-projection/v1"
          ? "Đây là bản đầu vào của RAG cho revision này."
          : "Đang phục vụ định dạng cũ. Lưu và duyệt bản chuẩn để chuẩn bị chỉ mục mới."}{" "}
        Lưu file không tự xuất bản.
      </p>
      {draft === null ? (
        <>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDraft(content.data ?? "")}
          >
            Hiệu đính bản chuẩn
          </Button>
          <pre className="max-h-[600px] overflow-auto whitespace-pre-wrap font-mono text-xs leading-relaxed">
            {content.data}
          </pre>
        </>
      ) : (
        <>
          <Textarea
            aria-label="QNU Markdown chuẩn"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            rows={24}
            className="font-mono text-sm"
            disabled={save.isPending}
          />
          <p className="text-xs text-muted-foreground">
            Giữ ID và vị trí nguồn. Với dòng bảng dạng records, sửa giá trị
            trong attributes.fields; không chỉ sửa phần chữ hiển thị. Metadata
            trong file không thay thế quyết định duyệt.
          </p>
          <Textarea
            aria-label="Lý do hiệu đính bản chuẩn"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            rows={2}
            maxLength={2000}
            placeholder="Lý do sau khi đối chiếu tài liệu gốc…"
            disabled={save.isPending}
          />
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              disabled={
                save.isPending ||
                !reason.trim() ||
                !draft.trim() ||
                draft === content.data
              }
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Đang lưu…" : "Lưu chờ duyệt"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={save.isPending}
              onClick={() => {
                setDraft(null);
                setReason("");
              }}
            >
              Hủy
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
