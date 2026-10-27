import { useForm } from "@tanstack/react-form";
import { useRef, useState } from "react";
import { z } from "zod";
import { v1Client } from "@/app/api/v1";
import { Field, FieldLabel } from "@/components/admin/field";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { DocumentScopePicker } from "@/features/knowledge/document-scope-picker";
import type { IndexRun } from "@/features/knowledge/index-types";
import { useActionScope } from "@/features/lifecycle/action-scope";
import { useCatalogQuery } from "@/features/modelops/queries";
import { createIdempotencyKey } from "@/lib/idempotency-key";
import { EvaluationReport } from "./evaluation-report";
import { GoldPicker } from "./gold-picker";
import { runEvaluation } from "./requests";
import type {
  EvaluationQuestionDraft,
  EvaluationRequest,
  EvaluationResult,
  IndexManifest,
  LabelStatus,
} from "./types";

const newQuestion = (): EvaluationQuestionDraft => ({
  id: createIdempotencyKey(),
  query: "",
  group: "",
  gold: [],
  documents: [],
});
const settingsSchema = z
  .object({
    version: z.string().trim().min(1).max(100),
    author: z.string().trim().min(1).max(200),
    top: z.coerce.number().int().min(1).max(50),
    candidates: z.coerce.number().int().min(1).max(50),
  })
  .refine((v) => v.candidates >= v.top);
export function EvaluationForm({
  workspaceId,
  collectionId,
  run,
  manifest,
}: {
  workspaceId: string;
  collectionId: string;
  run: IndexRun;
  manifest: IndexManifest;
}) {
  const current = useActionScope();
  const catalog = useCatalogQuery(workspaceId);
  const [initialQuestions] = useState(() => [newQuestion()]);
  const [busy, setBusy] = useState(false);
  const active = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [report, setReport] = useState<{
    request: EvaluationRequest;
    result: EvaluationResult;
  } | null>(null);
  const form = useForm({
    defaultValues: {
      version: "",
      author: "",
      top: "5",
      candidates: "30",
      labelStatus: "draft_needs_human_check" as LabelStatus,
      rerank: false,
      provider: "default",
      queries: initialQuestions,
    },
    onSubmit: async ({ value }) => {
      if (active.current) return;
      const settings = settingsSchema.safeParse(value);
      if (
        !settings.success ||
        !value.queries.length ||
        value.queries.length > 20 ||
        value.queries.some(
          (q) =>
            !q.query.trim() ||
            q.query.trim().length > 8000 ||
            q.group.trim().length > 100 ||
            q.gold.length > 100 ||
            q.documents.length > 100,
        )
      ) {
        setError(
          "Nhập phiên bản nhãn, người gán nhãn, từ 1–20 câu hỏi và ngân sách 1–50 (ứng viên ≥ K).",
        );
        return;
      }
      if (value.labelStatus === "human_reviewed" && !reviewed) {
        setError(
          "Cần xác nhận đã rà soát nhãn trước khi đánh dấu nhãn đã kiểm tra.",
        );
        return;
      }
      const allowedDocuments = new Set(
        manifest.inputs.map((input) => input.document_id),
      );
      if (
        value.queries.some((q) =>
          q.documents.some((d) => !allowedDocuments.has(d.id)),
        )
      ) {
        setError("Tài liệu đã chọn không thuộc snapshot. Chọn lại phạm vi.");
        return;
      }
      const sealed = new Set(manifest.chunks.map((c) => c.id));
      if (
        !run.manifest_sha256 ||
        value.queries.some((q) => q.gold.some((h) => !sealed.has(h.chunk_id)))
      ) {
        setError("Đáp án chuẩn không thuộc snapshot hiện tại. Chọn lại nguồn.");
        return;
      }
      const body: EvaluationRequest = {
        index_run_id: run.id,
        manifest_sha256: run.manifest_sha256,
        label_version: settings.data.version,
        label_author: settings.data.author,
        label_status: value.labelStatus,
        top_k: settings.data.top,
        candidate_k: settings.data.candidates,
        include_rerank: value.rerank,
        rerank_provider_id:
          value.rerank && value.provider !== "default" ? value.provider : null,
        queries: value.queries.map((q) => ({
          id: q.id,
          query: q.query.trim(),
          group: q.group.trim() || "unspecified",
          gold_chunk_ids: q.gold.map((h) => h.chunk_id),
          document_ids: q.documents.length
            ? q.documents.map((d) => d.id)
            : null,
        })),
      };
      active.current = true;
      setBusy(true);
      setError(null);
      setReport(null);
      try {
        const result = await runEvaluation(
          v1Client,
          workspaceId,
          collectionId,
          body,
        );
        if (current()) setReport({ request: body, result });
      } catch (cause) {
        if (current())
          setError(
            cause instanceof Error
              ? cause.message
              : "Không chạy được đánh giá.",
          );
      } finally {
        active.current = false;
        if (current()) setBusy(false);
      }
    },
  });
  return (
    <div className="space-y-5">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void form.handleSubmit();
        }}
        className="space-y-5"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <form.Field name="version">
            {(field) => (
              <Field>
                <FieldLabel htmlFor="eval-version">
                  Phiên bản bộ nhãn
                </FieldLabel>
                <Input
                  id="eval-version"
                  value={field.state.value}
                  onChange={(e) => {
                    field.handleChange(e.target.value);
                    setReviewed(false);
                  }}
                  disabled={busy}
                  maxLength={100}
                />
              </Field>
            )}
          </form.Field>
          <form.Field name="author">
            {(field) => (
              <Field>
                <FieldLabel htmlFor="eval-author">Người gán nhãn</FieldLabel>
                <Input
                  id="eval-author"
                  value={field.state.value}
                  onChange={(e) => {
                    field.handleChange(e.target.value);
                    setReviewed(false);
                  }}
                  disabled={busy}
                  maxLength={200}
                />
              </Field>
            )}
          </form.Field>
          <form.Field name="top">
            {(field) => (
              <Field>
                <FieldLabel htmlFor="eval-top">Số đoạn lấy ra (K)</FieldLabel>
                <Input
                  id="eval-top"
                  type="number"
                  min={1}
                  max={50}
                  value={field.state.value}
                  onChange={(e) => {
                    field.handleChange(e.target.value);
                    setReviewed(false);
                  }}
                  disabled={busy}
                />
              </Field>
            )}
          </form.Field>
          <form.Field name="candidates">
            {(field) => (
              <Field>
                <FieldLabel htmlFor="eval-candidates">
                  Số đoạn ứng viên
                </FieldLabel>
                <Input
                  id="eval-candidates"
                  type="number"
                  min={1}
                  max={50}
                  value={field.state.value}
                  onChange={(e) => {
                    field.handleChange(e.target.value);
                    setReviewed(false);
                  }}
                  disabled={busy}
                />
              </Field>
            )}
          </form.Field>
          <form.Field name="labelStatus">
            {(field) => (
              <Field>
                <FieldLabel htmlFor="eval-label-status">
                  Trạng thái nhãn
                </FieldLabel>
                <Select
                  value={field.state.value}
                  onValueChange={(v) => {
                    field.handleChange(v as LabelStatus);
                    setReviewed(false);
                  }}
                  disabled={busy}
                >
                  <SelectTrigger id="eval-label-status">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="draft_needs_human_check">
                      Nháp — cần rà soát
                    </SelectItem>
                    <SelectItem value="human_reviewed">
                      Đã được người rà soát
                    </SelectItem>
                  </SelectContent>
                </Select>
              </Field>
            )}
          </form.Field>
          <div className="space-y-3">
            <form.Field name="rerank">
              {(field) => (
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="eval-rerank"
                    checked={field.state.value}
                    onCheckedChange={(v) => {
                      field.handleChange(v === true);
                      setReviewed(false);
                    }}
                    disabled={busy}
                  />
                  <Label htmlFor="eval-rerank">Đo thêm bước xếp hạng lại</Label>
                </div>
              )}
            </form.Field>
            <form.Subscribe selector={(state) => state.values.rerank}>
              {(enabled) =>
                enabled ? (
                  <form.Field name="provider">
                    {(field) => (
                      <Field>
                        <FieldLabel htmlFor="eval-provider">
                          Provider xếp hạng lại
                        </FieldLabel>
                        <Select
                          value={field.state.value}
                          onValueChange={(v) => {
                            field.handleChange(v);
                            setReviewed(false);
                          }}
                          disabled={busy}
                        >
                          <SelectTrigger id="eval-provider">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="default">
                              Theo cấu hình ModelOps
                            </SelectItem>
                            {(catalog.data ?? [])
                              .filter((p) => p.capabilities.includes("rerank"))
                              .map((p) => (
                                <SelectItem key={p.id} value={p.id}>
                                  {p.name} · {p.model_name}
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>
                        {catalog.isError ? (
                          <p role="alert" className="text-sm text-destructive">
                            Không đọc được danh sách provider. Server vẫn kiểm
                            tra quyền và cấu hình mặc định.
                          </p>
                        ) : null}
                      </Field>
                    )}
                  </form.Field>
                ) : null
              }
            </form.Subscribe>
          </div>
        </div>
        <form.Field name="queries" mode="array">
          {(field) => (
            <section className="space-y-4">
              <div className="flex flex-wrap justify-between gap-2">
                <h2 className="font-semibold text-sm">
                  Câu hỏi ({field.state.value.length}/20)
                </h2>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={busy || field.state.value.length >= 20}
                  onClick={() => {
                    field.pushValue(newQuestion());
                    setReviewed(false);
                  }}
                >
                  Thêm câu hỏi
                </Button>
              </div>
              {field.state.value.map((question, index) => (
                <div
                  key={question.id}
                  className="rounded-lg border p-4 space-y-3"
                >
                  <div className="flex justify-between items-center">
                    <h3 className="font-medium text-sm">Câu hỏi {index + 1}</h3>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={busy || field.state.value.length <= 1}
                      onClick={() => {
                        field.removeValue(index);
                        setReviewed(false);
                      }}
                    >
                      Bỏ câu hỏi
                    </Button>
                  </div>
                  <Field>
                    <FieldLabel htmlFor={`query-${question.id}`}>
                      Nội dung câu hỏi
                    </FieldLabel>
                    <Textarea
                      id={`query-${question.id}`}
                      value={question.query}
                      maxLength={8000}
                      disabled={busy}
                      onChange={(e) => {
                        field.replaceValue(index, {
                          ...question,
                          query: e.target.value,
                          gold: [],
                        });
                        setReviewed(false);
                      }}
                    />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor={`group-${question.id}`}>
                      Nhóm (tùy chọn)
                    </FieldLabel>
                    <Input
                      id={`group-${question.id}`}
                      value={question.group}
                      disabled={busy}
                      maxLength={100}
                      onChange={(e) => {
                        field.replaceValue(index, {
                          ...question,
                          group: e.target.value,
                        });
                        setReviewed(false);
                      }}
                    />
                  </Field>
                  <DocumentScopePicker
                    workspaceId={workspaceId}
                    collectionId={collectionId}
                    selected={question.documents}
                    allowedIds={manifest.inputs.map(
                      (input) => input.document_id,
                    )}
                    disabled={busy}
                    onChange={(documents) => {
                      field.replaceValue(index, {
                        ...question,
                        documents,
                        gold: [],
                      });
                      setReviewed(false);
                    }}
                  />
                  <GoldPicker
                    key={`${question.id}:${question.query}:${JSON.stringify(question.documents.map((d) => d.id))}`}
                    workspaceId={workspaceId}
                    collectionId={collectionId}
                    query={question.query}
                    documentIds={question.documents.map((d) => d.id)}
                    manifest={manifest}
                    manifestSha={run.manifest_sha256 ?? ""}
                    selected={question.gold}
                    disabled={busy}
                    onChange={(gold) => {
                      field.replaceValue(index, { ...question, gold });
                      setReviewed(false);
                    }}
                  />
                </div>
              ))}
            </section>
          )}
        </form.Field>
        <form.Subscribe selector={(state) => state.values.labelStatus}>
          {(status) =>
            status === "human_reviewed" ? (
              <div className="flex items-start gap-2">
                <Checkbox
                  id="eval-reviewed"
                  checked={reviewed}
                  onCheckedChange={(v) => setReviewed(v === true)}
                  disabled={busy}
                />
                <Label htmlFor="eval-reviewed" className="leading-relaxed">
                  Tôi đã đọc nguồn và kiểm tra độ đầy đủ của đáp án chuẩn cho
                  mọi câu hỏi.
                </Label>
              </div>
            ) : null
          }
        </form.Subscribe>
        {error ? (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
        <p className="text-xs text-muted-foreground">
          Chạy đánh giá sẽ gọi embedding và rerank (nếu chọn) qua ModelOps và có
          ghi nhận usage.
        </p>
        <Button type="submit" disabled={busy}>
          {busy ? "Đang đánh giá…" : "Chạy đánh giá truy xuất"}
        </Button>
      </form>
      {report ? (
        <EvaluationReport result={report.result} request={report.request} />
      ) : null}
    </div>
  );
}
