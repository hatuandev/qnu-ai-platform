import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useRbac } from "@/rbac/context";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";
import type { KnowledgeSourceRevisionResponse } from "@/types/knowledge";
import { refreshSourceQueries } from "../utils/source-query-cache";
import { QnuDocumentReader } from "./qnu-document-reader";

function QnuStandardSourceEditor({
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
  const rbac = useRbac();
  const canEdit =
    rbac.isAccessVerified &&
    !rbac.isDemoMode &&
    rbac.can("ai.knowledge.update");
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
          ? "Gói chuẩn dùng để đối chiếu; RAG sử dụng bản chiếu đã lược metadata."
          : "Đang phục vụ định dạng cũ. Lưu và duyệt bản chuẩn để chuẩn bị chỉ mục mới."}{" "}
        Lưu file không tự xuất bản.
      </p>
      {draft === null ? (
        <>
          <Button
            variant="outline"
            size="sm"
            disabled={!canEdit}
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

type EditorProps = Parameters<typeof QnuStandardSourceEditor>[0];

function ReaderPreview({ collectionId, sourceId, revision }: EditorProps) {
  const content = useQuery({
    queryKey: [
      "qnu-reader",
      collectionId,
      sourceId,
      revision.id,
      revision.canonical_hash,
    ],
    queryFn: () =>
      knowledgeApi.getSourceReader(collectionId, sourceId, revision.id),
  });
  if (content.isPending)
    return (
      <p role="status" className="text-sm text-muted-foreground">
        Đang chuẩn bị bản đọc…
      </p>
    );
  if (content.isError)
    return (
      <div className="space-y-2">
        <p role="alert" className="text-sm text-destructive">
          {extractErrorMessage(content.error, "Không đọc được tài liệu.")}
        </p>
        <Button variant="outline" size="sm" onClick={() => content.refetch()}>
          Thử lại
        </Button>
      </div>
    );
  return <QnuDocumentReader document={content.data} />;
}

export function QnuStandardEditor(props: EditorProps) {
  const download = useMutation({
    mutationFn: (format: "reader" | "md" | "json") =>
      knowledgeApi.downloadSourceQnuMarkdown(
        props.collectionId,
        props.sourceId,
        props.revision.id,
        format,
      ),
    onSuccess: () => toast.success("Đã tải tài liệu."),
    onError: (error) =>
      toast.error(extractErrorMessage(error, "Không tải được tài liệu.")),
  });
  return (
    <Tabs defaultValue="reader" className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <TabsList
          aria-label="Dạng nội dung tài liệu"
          className="grid h-auto w-full grid-cols-3 sm:w-auto"
        >
          <TabsTrigger
            value="reader"
            className="min-w-0 whitespace-normal px-2 py-2 text-center leading-snug"
          >
            Bản dễ đọc
          </TabsTrigger>
          <TabsTrigger
            value="standard"
            className="min-w-0 whitespace-normal px-2 py-2 text-center leading-snug"
          >
            Gói chuẩn
          </TabsTrigger>
          <TabsTrigger
            value="rag"
            className="min-w-0 whitespace-normal px-2 py-2 text-center leading-snug"
          >
            Bản phục vụ RAG
          </TabsTrigger>
        </TabsList>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={download.isPending}
            onClick={() => download.mutate("reader")}
          >
            Tải bản dễ đọc .md
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={download.isPending}
            onClick={() => download.mutate("md")}
          >
            Tải chuẩn .md
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={download.isPending}
            onClick={() => download.mutate("json")}
          >
            Tải JSON
          </Button>
        </div>
      </div>
      <TabsContent
        value="reader"
        className="rounded-lg border border-border bg-card p-4"
      >
        <ReaderPreview {...props} />
      </TabsContent>
      <TabsContent value="standard">
        <QnuStandardSourceEditor {...props} />
      </TabsContent>
      <TabsContent value="rag">
        <p className="text-sm text-muted-foreground mb-3">
          Nội dung đã lược metadata để xử lý RAG. Đây là bản chiếu của cùng
          revision, không phải nguồn mới và không chứng minh đã xuất bản.
        </p>
        <pre className="max-h-[600px] overflow-auto whitespace-pre-wrap font-mono text-xs">
          {props.revision.canonical_markdown || "Chưa có bản phục vụ RAG."}
        </pre>
      </TabsContent>
    </Tabs>
  );
}
