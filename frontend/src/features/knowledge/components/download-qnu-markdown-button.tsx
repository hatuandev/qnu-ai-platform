import { useMutation } from "@tanstack/react-query";
import { FileDown } from "lucide-react";
import { toast } from "sonner";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";

export function DownloadQnuMarkdownButton({
  collectionId,
  sourceId,
  revisionId,
  disabled,
  format = "md",
}: {
  collectionId: string;
  sourceId: string;
  revisionId: string | null;
  disabled?: boolean;
  format?: "md" | "reader";
}) {
  const download = useMutation({
    mutationFn: () =>
      knowledgeApi.downloadSourceQnuMarkdown(
        collectionId,
        sourceId,
        revisionId ?? "",
        format,
      ),
    onSuccess: () =>
      toast.success(
        format === "reader"
          ? "Đã tải Markdown dành cho người đọc."
          : "Đã tải tệp QNU RAG Markdown v1.0.",
      ),
    onError: (error) =>
      toast.error(
        extractErrorMessage(error, "Không tải được tệp QNU RAG Markdown."),
      ),
  });
  return (
    <DropdownMenuItem
      disabled={!revisionId || disabled || download.isPending}
      onSelect={(event) => {
        event.preventDefault();
        download.mutate();
      }}
    >
      <FileDown />
      {download.isPending
        ? "Đang tải…"
        : format === "reader"
          ? "Tải Markdown dễ đọc"
          : "Tải gói Markdown chuẩn"}
    </DropdownMenuItem>
  );
}
