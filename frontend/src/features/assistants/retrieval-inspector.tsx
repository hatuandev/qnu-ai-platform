import { useForm } from "@tanstack/react-form";
import { useMutation } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { z } from "zod";
import { Field } from "@/components/admin/field";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { BASE_URL, getAuthHeaders } from "@/services/http-client";
import { extractErrorMessage } from "@/services/knowledge-api";

interface SearchResult {
  retrieval_diagnostics?: Record<string, unknown>;
  total_found: number;
  items: Array<{
    chunk_id: string;
    document_id: string;
    content: string;
    score: number;
  }>;
}

export function RetrievalDiagnostics({
  value,
}: {
  value?: Record<string, unknown>;
}) {
  if (!value)
    return (
      <p className="text-xs text-muted-foreground">
        Chưa có chẩn đoán cho lượt này.
      </p>
    );
  return (
    <details className="min-w-0 rounded-lg border border-border p-3">
      <summary className="cursor-pointer text-sm font-medium">
        Phân luồng và truy xuất
      </summary>
      <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-all text-xs text-muted-foreground">
        {JSON.stringify(value, null, 2)}
      </pre>
    </details>
  );
}

export function RetrievalInspector({
  assistantCode,
  collectionId,
}: {
  assistantCode: string;
  collectionId: string;
}) {
  const mutation = useMutation({
    mutationFn: async (query: string): Promise<SearchResult> => {
      const response = await fetch(`${BASE_URL}/rag/search`, {
        method: "POST",
        credentials: "include",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          query,
          assistant_code: assistantCode,
          collection_id: collectionId,
        }),
      });
      const data: unknown = await response.json();
      if (!response.ok)
        throw new Error(
          extractErrorMessage(
            data,
            `Tìm kiếm thất bại (HTTP ${response.status}).`,
          ),
        );
      return data as SearchResult;
    },
  });
  const form = useForm({
    defaultValues: { query: "" },
    onSubmit: async ({ value }) => {
      mutation.reset();
      await mutation.mutateAsync(value.query.trim()).catch(() => undefined);
    },
  });
  return (
    <details className="min-w-0 rounded-lg border border-border p-3">
      <summary className="cursor-pointer text-sm font-medium">
        Kiểm tra tìm kiếm
      </summary>
      <p className="my-2 text-xs text-muted-foreground">
        Chỉ tìm đoạn dữ liệu, không sinh câu trả lời. Dùng cấu hình đã lưu của
        trợ lý; chưa bao gồm các nhánh facts, liệt kê và kiểm chứng đầy đủ của
        chatbot.
      </p>
      <form
        className="space-y-2"
        onSubmit={(event) => {
          event.preventDefault();
          void form.handleSubmit();
        }}
      >
        <form.Field
          name="query"
          validators={{
            onChange: z.string().trim().min(1, "Nhập câu hỏi.").max(1000),
          }}
        >
          {(field) => (
            <Field label="Câu hỏi tìm kiếm" htmlFor="retrieval-probe-query">
              <Textarea
                id="retrieval-probe-query"
                value={field.state.value}
                onChange={(event) => field.handleChange(event.target.value)}
                rows={3}
                maxLength={1000}
              />
            </Field>
          )}
        </form.Field>
        <Button
          size="sm"
          type="submit"
          variant="outline"
          disabled={mutation.isPending}
        >
          <Search className="size-4" />
          {mutation.isPending ? "Đang tìm…" : "Tìm kiếm"}
        </Button>
      </form>
      {mutation.isError && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {mutation.error.message}
        </p>
      )}
      {mutation.data && (
        <div className="mt-3 space-y-2">
          <p className="text-sm">Tìm thấy {mutation.data.total_found} đoạn.</p>
          <RetrievalDiagnostics value={mutation.data.retrieval_diagnostics} />
          {mutation.data.items.map((item) => (
            <details
              key={item.chunk_id}
              className="rounded-md border border-border p-2"
            >
              <summary className="cursor-pointer break-all text-xs">
                {item.document_id} · RRF {item.score}
              </summary>
              <p className="mt-2 whitespace-pre-wrap text-sm">{item.content}</p>
            </details>
          ))}
        </div>
      )}
    </details>
  );
}
