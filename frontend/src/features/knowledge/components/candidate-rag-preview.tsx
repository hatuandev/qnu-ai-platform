import { useMutation } from "@tanstack/react-query";
import { FlaskConical } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { knowledgeApi } from "@/services/knowledge-api";

export function CandidateRagPreview({
  collectionId,
  generationId,
}: {
  collectionId: string;
  generationId: string;
}) {
  const [question, setQuestion] = useState("");
  const preview = useMutation({
    mutationFn: () =>
      knowledgeApi.previewVectorGeneration(
        collectionId,
        generationId,
        question,
      ),
  });
  return (
    <section className="space-y-2 border-t border-border pt-3">
      <p className="text-xs text-muted-foreground">
        Thử RAG trên bản dự thảo qua ModelOps mặc định, không thay chỉ mục đang
        dùng. Đây không phải bài test DAG của trợ lý.
      </p>
      <div className="flex gap-2">
        <Input
          aria-label="Câu hỏi thử RAG"
          placeholder="Câu hỏi đối chiếu..."
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <Button
          variant="outline"
          disabled={!generationId || !question.trim() || preview.isPending}
          onClick={() => preview.mutate()}
        >
          <FlaskConical className="size-3.5" />
          {preview.isPending ? "Đang thử" : "Thử RAG"}
        </Button>
      </div>
      {preview.error && (
        <p role="alert" className="text-xs text-destructive">
          {preview.error.message}
        </p>
      )}
      {preview.data && (
        <div className="max-h-72 overflow-auto space-y-2 text-xs">
          <p className="text-muted-foreground">
            {preview.data.status === "answered"
              ? "Có câu trả lời"
              : "Thiếu căn cứ"}
          </p>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {preview.data.answer}
          </ReactMarkdown>
          {preview.data.citations.map((citation) => (
            <p
              key={`${citation.title}-${citation.page_number}-${citation.quote}`}
              className="text-muted-foreground"
            >
              {citation.title} · Trang {citation.page_number ?? "?"}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}
