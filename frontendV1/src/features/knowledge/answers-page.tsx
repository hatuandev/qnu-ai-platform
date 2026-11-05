import { useForm } from "@tanstack/react-form";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { ArrowLeft, Loader2, SendHorizontal } from "lucide-react";
import { useRef, useState } from "react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Field, FieldLabel } from "@/components/admin/field";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { AnswerResponse } from "@/features/conversations/types";
import { useActionScope } from "@/features/lifecycle/action-scope";
import { useCatalogQuery } from "@/features/modelops/queries";
import {
  EMPTY_METADATA_FILTER_DRAFT,
  MetadataFilterFields,
} from "@/features/rag/metadata-filter-fields";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import {
  type AnswerRequest,
  buildAnswerRequest,
  DEFAULT_ANSWER_SETTINGS,
  requestAnswer,
} from "./answer-request";
import { AnswerResult } from "./answer-result";
import { AnswerSettings } from "./answer-settings";
import {
  DocumentScopePicker,
  type DocumentSelection,
} from "./document-scope-picker";
import { canReadCompilation } from "./permissions";
import { useCollectionQuery } from "./queries";

type Props = { workspaceId: string; collectionId: string };
export function AnswersPage(props: Props) {
  const { sessionId } = useV1Auth();
  return (
    <AnswerPageSession
      key={`${sessionId}:${props.workspaceId}:${props.collectionId}`}
      {...props}
    />
  );
}
function AnswerPageSession({ workspaceId, collectionId }: Props) {
  const access = useCallerWorkspaceRole(workspaceId);
  const collection = useCollectionQuery(workspaceId, collectionId);
  return (
    <div className="space-y-5">
      <Button variant="ghost" size="sm" asChild>
        <Link
          to="/workspaces/$workspaceId/collections/$collectionId"
          params={{ workspaceId, collectionId }}
          search={{ page: 1, pageSize: 20, tab: "index" }}
        >
          <ArrowLeft className="size-3.5" />
          Về kho
        </Link>
      </Button>
      <PageHeader
        eyebrow="Kho tri thức"
        title="Hỏi đáp thử"
        description={
          collection.data
            ? `Đặt câu hỏi trực tiếp với kho ${collection.data.name}, đọc câu trả lời và đối chiếu dẫn nguồn.`
            : "Đặt câu hỏi và đối chiếu dẫn nguồn trong kho tài liệu."
        }
      />
      {collection.isPending || access.isPending ? (
        <p role="status">Đang đọc kho và quyền truy cập…</p>
      ) : collection.isError ? (
        <ErrorState
          error={collection.error}
          onRetry={() => void collection.refetch()}
        />
      ) : access.error ? (
        <ErrorState error={access.error} />
      ) : !canReadCompilation(access.role) ? (
        <p role="alert">Chưa xác nhận được quyền hỏi đáp trong workspace.</p>
      ) : (
        <AnswerForm workspaceId={workspaceId} collectionId={collectionId} />
      )}
    </div>
  );
}
export function AnswerForm({ workspaceId, collectionId }: Props) {
  const { sessionId } = useV1Auth();
  const client = useQueryClient();
  const catalog = useCatalogQuery(workspaceId);
  const current = useActionScope();
  const active = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<{
    request: AnswerRequest;
    response: AnswerResponse;
  } | null>(null);
  const form = useForm({
    defaultValues: {
      question: "",
      settings: { ...DEFAULT_ANSWER_SETTINGS },
      documents: [] as DocumentSelection[],
      metadata: { ...EMPTY_METADATA_FILTER_DRAFT },
    },
    onSubmit: async ({ value }) => {
      if (active.current || !catalog.isSuccess) return;
      let request: AnswerRequest;
      try {
        request = buildAnswerRequest(
          value.question,
          value.settings,
          value.documents.map((d) => d.id),
          value.metadata,
        );
      } catch (cause) {
        setError(cause);
        return;
      }
      active.current = true;
      setBusy(true);
      setError(null);
      setResult(null);
      try {
        const response = await requestAnswer(
          v1Client,
          workspaceId,
          collectionId,
          request,
        );
        if (current()) setResult({ request, response });
      } catch (cause) {
        if (current()) setError(cause);
      } finally {
        active.current = false;
        if (current()) {
          setBusy(false);
          void client.invalidateQueries({
            queryKey: ["v1", sessionId, "operations-summary", workspaceId],
          });
          void client.invalidateQueries({
            queryKey: ["v1", sessionId, "workspaces", "quota", workspaceId],
          });
          void client.invalidateQueries({
            queryKey: ["v1", sessionId, "workspaces", "usage", workspaceId],
          });
        }
      }
    },
  });
  return (
    <div className="space-y-5">
      <p className="text-sm text-muted-foreground">
        Mỗi lần gửi là một câu hỏi độc lập, không dùng lịch sử trước đó và có
        thể phát sinh token. Muốn hội thoại nhiều lượt, hãy dùng trợ lý.
      </p>
      {catalog.isError ? (
        <ErrorState
          error={catalog.error}
          onRetry={() => void catalog.refetch()}
        />
      ) : null}
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void form.handleSubmit();
        }}
      >
        <form.Field name="question">
          {(field) => (
            <Field>
              <FieldLabel htmlFor="answer-question">Câu hỏi</FieldLabel>
              <Textarea
                id="answer-question"
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                maxLength={8000}
                rows={4}
                disabled={busy}
                placeholder="Nhập câu hỏi…"
              />
            </Field>
          )}
        </form.Field>
        <form.Subscribe selector={(s) => s.values.settings}>
          {(settings) => (
            <AnswerSettings
              value={settings}
              catalog={catalog.data ?? []}
              disabled={busy || !catalog.isSuccess}
              onChange={(v) => form.setFieldValue("settings", v)}
            />
          )}
        </form.Subscribe>
        <form.Subscribe selector={(s) => s.values.documents}>
          {(documents) => (
            <DocumentScopePicker
              workspaceId={workspaceId}
              collectionId={collectionId}
              selected={documents}
              disabled={busy}
              onChange={(v) => form.setFieldValue("documents", v)}
            />
          )}
        </form.Subscribe>
        <details className="rounded-lg border p-3">
          <summary className="cursor-pointer text-sm font-medium">
            Phạm vi năm, ngành và hiệu lực
          </summary>
          <div className="pt-4">
            <form.Subscribe selector={(s) => s.values.metadata}>
              {(metadata) => (
                <MetadataFilterFields
                  workspaceId={workspaceId}
                  collectionId={collectionId}
                  value={metadata}
                  disabled={busy}
                  onChange={(v) => form.setFieldValue("metadata", v)}
                />
              )}
            </form.Subscribe>
          </div>
        </details>
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={busy || !catalog.isSuccess}>
            {busy ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <SendHorizontal className="size-4" />
            )}
            Gửi câu hỏi
          </Button>
          {busy ? (
            <p role="status" className="text-sm text-muted-foreground">
              Đang truy xuất và tạo câu trả lời. Rời trang không hủy xử lý trên
              server.
            </p>
          ) : null}
        </div>
      </form>
      {error ? (
        <div className="space-y-2">
          <ErrorState error={error} />
          <p className="text-xs text-muted-foreground">
            Không tự gửi lại yêu cầu. Nếu bị mất kết nối, lần xử lý trước có thể
            vẫn đang chạy trên server.
          </p>
        </div>
      ) : null}
      {result ? (
        <AnswerResult
          key={result.response.id}
          workspaceId={workspaceId}
          collectionId={collectionId}
          result={result.response}
          request={result.request}
        />
      ) : null}
    </div>
  );
}
