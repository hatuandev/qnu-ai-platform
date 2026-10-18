import { useForm } from "@tanstack/react-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { ArrowLeft, Calculator } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Combobox } from "@/components/admin/combobox";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { Field } from "@/components/admin/field";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { formatDateTimeValue } from "@/lib/date-utils";
import { useRbac } from "@/rbac/context";
import { scoreRulesApi } from "@/services/score-rules-api";
import type { ScoreRuleAction, ScoreRuleRecord } from "@/types/score-rules";
import { SCORE_RULE_STATUS } from "./score-rule-list";

const ACTION_LABELS: Record<ScoreRuleAction, string> = {
  approve: "Duyệt",
  activate: "Kích hoạt",
  deactivate: "Ngừng dùng",
  revoke: "Thu hồi",
};

function RuleActions({
  collectionId,
  item,
  version,
}: {
  collectionId: string;
  item: ScoreRuleRecord;
  version: number;
}) {
  const { can } = useRbac();
  const client = useQueryClient();
  const [action, setAction] = useState<ScoreRuleAction | null>(null);
  const mutation = useMutation({
    mutationFn: ({ kind, reason }: { kind: ScoreRuleAction; reason: string }) =>
      scoreRulesApi.act(
        collectionId,
        item.definition.id,
        kind,
        reason,
        version,
        crypto.randomUUID(),
      ),
    onSuccess: () => {
      toast.success("Đã cập nhật trạng thái quy tắc.");
      setAction(null);
    },
    onError: (error: Error) => toast.error(error.message),
    onSettled: () =>
      client.invalidateQueries({ queryKey: ["score-rules", collectionId] }),
  });
  const form = useForm({ defaultValues: { reason: "" } });
  if (!can("ai.knowledge.review")) return null;
  const actions: ScoreRuleAction[] =
    item.status === "draft"
      ? ["approve", "revoke"]
      : item.status === "approved"
        ? ["activate", "revoke"]
        : item.status === "active"
          ? ["deactivate", "revoke"]
          : [];
  return (
    <>
      <div className="flex flex-wrap gap-2">
        {actions.map((kind) => (
          <Button
            key={kind}
            size="sm"
            variant={kind === "revoke" ? "destructive" : "outline"}
            onClick={() => {
              form.reset();
              setAction(kind);
            }}
          >
            {ACTION_LABELS[kind]}
          </Button>
        ))}
      </div>
      <form.Subscribe selector={(state) => state.values.reason}>
        {(reason) => (
          <ConfirmDialog
            open={action !== null}
            onOpenChange={(open) => {
              if (!open && !mutation.isPending) setAction(null);
            }}
            title={`${action ? ACTION_LABELS[action] : "Xác nhận"} quy tắc`}
            description={
              <div className="space-y-3">
                <p>
                  {action === "activate"
                    ? "Chatbot sẽ được phép dùng quy tắc này. Máy chủ sẽ đối chiếu lại nguồn trước khi kích hoạt."
                    : action === "revoke"
                      ? "Chatbot sẽ ngừng dùng quy tắc; lịch sử và tài liệu nguồn vẫn được giữ."
                      : "Xác nhận đã kiểm tra bảng điểm, ánh xạ tổ hợp, phạm vi năm và chính sách làm tròn."}
                </p>
                <form.Field name="reason">
                  {(field) => (
                    <Field label="Lý do / ghi chú đối chiếu" required>
                      {(props) => (
                        <Textarea
                          {...props}
                          maxLength={500}
                          value={field.state.value}
                          onChange={(event) =>
                            field.handleChange(event.target.value)
                          }
                        />
                      )}
                    </Field>
                  )}
                </form.Field>
              </div>
            }
            confirmLabel={action ? ACTION_LABELS[action] : "Xác nhận"}
            variant={action === "revoke" ? "destructive" : "default"}
            isPending={mutation.isPending}
            onConfirm={
              action && reason.trim().length >= 3
                ? () => mutation.mutate({ kind: action, reason: reason.trim() })
                : null
            }
          />
        )}
      </form.Subscribe>
    </>
  );
}

function RulePreview({
  collectionId,
  item,
  version,
}: {
  collectionId: string;
  item: ScoreRuleRecord;
  version: number;
}) {
  const rule = item.definition;
  const mutation = useMutation({
    mutationFn: (values: { combination: string; score: string }) =>
      scoreRulesApi.preview(
        collectionId,
        rule.id,
        values.combination,
        values.score,
        version,
      ),
  });
  const form = useForm({
    defaultValues: {
      combination: rule.mappings[0]?.combination ?? "",
      score: "",
    },
    onSubmit: async ({ value }) => {
      await mutation.mutateAsync(value).catch(() => undefined);
    },
  });
  return (
    <section className="space-y-3 rounded-lg border border-border p-4">
      <h2 className="flex items-center gap-2 font-semibold">
        <Calculator className="size-4" />
        Tính thử · không kích hoạt
      </h2>
      <form
        className="grid gap-3 sm:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault();
          void form.handleSubmit();
        }}
      >
        <form.Field name="combination">
          {(field) => (
            <Field label="Tổ hợp">
              {(props) => (
                <Combobox
                  id={props.id}
                  value={field.state.value}
                  onValueChange={(value) => {
                    field.handleChange(value ?? "");
                    mutation.reset();
                  }}
                  options={rule.mappings.map((mapping) => ({
                    value: mapping.combination,
                    label: `${mapping.combination} → ${mapping.base_combination}`,
                  }))}
                  searchPlaceholder="Tìm tổ hợp..."
                />
              )}
            </Field>
          )}
        </form.Field>
        <form.Field name="score">
          {(field) => (
            <Field label={`Điểm ${rule.source_method}`} required>
              {(props) => (
                <Input
                  {...props}
                  inputMode="decimal"
                  value={field.state.value}
                  onChange={(event) => {
                    field.handleChange(event.target.value);
                    mutation.reset();
                  }}
                  placeholder="Nhập điểm cần quy đổi"
                />
              )}
            </Field>
          )}
        </form.Field>
        <Button
          type="submit"
          className="sm:col-span-2"
          disabled={mutation.isPending || item.status === "revoked"}
        >
          {mutation.isPending
            ? "Đang tính..."
            : "Tính thử bằng nguồn đã xuất bản"}
        </Button>
      </form>
      {mutation.isError && (
        <Alert variant="destructive">
          <AlertDescription>{mutation.error.message}</AlertDescription>
        </Alert>
      )}
      {mutation.data && (
        <div className="space-y-2" aria-live="polite">
          <p className="text-sm text-muted-foreground">
            {mutation.data.message}
          </p>
          {mutation.data.status === "calculated" && (
            <>
              <p className="text-xl font-semibold text-primary">
                {mutation.data.result} điểm {rule.target_method}
              </p>
              <p className="break-words font-mono text-xs">
                {mutation.data.formula}
              </p>
              <p className="text-sm">
                Hai mốc: {mutation.data.x1} → {mutation.data.y1};{" "}
                {mutation.data.x2} → {mutation.data.y2}. Làm tròn:{" "}
                {mutation.data.rounding}.
              </p>
            </>
          )}
          <p className="text-xs text-muted-foreground">
            {mutation.data.citations.length} đoạn trích kiểm chứng. Xem bằng
            chứng gốc bên dưới.
          </p>
        </div>
      )}
    </section>
  );
}

export function ScoreRuleDetail({
  collectionId,
  ruleId,
}: {
  collectionId: string;
  ruleId: string;
}) {
  const query = useQuery({
    queryKey: ["score-rules", collectionId],
    queryFn: () => scoreRulesApi.list(collectionId),
  });
  if (query.isPending) return <Skeleton className="h-60" />;
  if (query.isError)
    return (
      <Alert variant="destructive">
        <AlertDescription>
          {query.error.message}
          <Button variant="outline" onClick={() => query.refetch()}>
            Thử lại
          </Button>
        </AlertDescription>
      </Alert>
    );
  const item = query.data.items.find(
    (candidate) => candidate.definition.id === ruleId,
  );
  if (!item)
    return (
      <EmptyState
        title="Không tìm thấy quy tắc"
        description="Quy tắc không tồn tại trong kho tri thức này."
      />
    );
  const rule = item.definition;
  return (
    <div className="space-y-5">
      <Button asChild variant="ghost" size="sm">
        <Link
          to="/knowledge/$collectionId"
          params={{ collectionId }}
          search={{ tab: "scores" }}
        >
          <ArrowLeft className="size-4" />
          Kho tri thức / Quy đổi điểm
        </Link>
      </Button>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="break-all text-xl font-semibold">{rule.id}</h1>
          <p className="text-sm text-muted-foreground">
            {rule.year} · {rule.source_method} → {rule.target_method} · tổ hợp
            gốc {rule.base_combination}
          </p>
          <Badge
            className="mt-2"
            variant={item.status === "active" ? "success" : "secondary"}
          >
            {SCORE_RULE_STATUS[item.status]}
          </Badge>
        </div>
        <RuleActions
          collectionId={collectionId}
          item={item}
          version={query.data.version}
        />
      </header>
      <div className="grid min-w-0 gap-5 lg:grid-cols-3">
        <section className="min-w-0 space-y-4 lg:col-span-2">
          <div className="space-y-2">
            <h2 className="font-semibold">Bảng mốc và chính sách</h2>
            <p className="text-sm">
              Nội suy tuyến tính theo từng khoảng; làm tròn một lần ở cuối đến{" "}
              {rule.decimal_places} chữ số ({rule.rounding}). Đây là chính sách
              phải được người duyệt đối chiếu, không phải model tự quyết định.
            </p>
            <p className="text-xs text-muted-foreground">
              Người duyệt: {item.reviewed_by ?? "Chưa duyệt"}
              {item.reviewed_at
                ? ` · ${formatDateTimeValue(item.reviewed_at)}`
                : ""}
            </p>
          </div>
          <div className="w-full overflow-x-auto rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{rule.source_attribute}</TableHead>
                  <TableHead>{rule.target_attribute}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rule.points.map((point) => (
                  <TableRow
                    key={`${point.source.block_id}:${point.source.fact_id}`}
                  >
                    <TableCell>{point.source.value}</TableCell>
                    <TableCell>{point.target.value}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <section className="space-y-2">
            <h2 className="font-semibold">Bằng chứng và phiên bản nguồn</h2>
            <Link
              className="text-sm text-primary hover:underline"
              to="/knowledge/$collectionId/sources/$sourceId"
              params={{ collectionId, sourceId: rule.binding_id }}
              search={{ revision: rule.source_revision_id }}
            >
              Mở nguồn để đối chiếu
            </Link>
            <p className="break-all font-mono text-xs text-muted-foreground">
              Source: {rule.source_revision_id}
              <br />
              Index: {rule.index_revision_id}
              <br />
              SHA-256: {rule.canonical_hash}
            </p>
            {rule.rule_proofs.map((proof) => (
              <blockquote
                key={`${proof.block_id}:${proof.quote}`}
                className="border-l-2 border-primary/30 pl-3 text-sm"
              >
                {proof.quote}
              </blockquote>
            ))}
          </section>
        </section>
        <RulePreview
          key={`${ruleId}:${query.data.version}`}
          collectionId={collectionId}
          item={item}
          version={query.data.version}
        />
      </div>
      <section className="space-y-2">
        <h2 className="font-semibold">Lịch sử thao tác</h2>
        <div className="w-full overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Thời gian</TableHead>
                <TableHead>Thao tác</TableHead>
                <TableHead>Người thực hiện</TableHead>
                <TableHead>Ghi chú</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.data.audit
                .filter((entry) => entry.rule_id === ruleId)
                .reverse()
                .map((entry) => (
                  <TableRow key={entry.request_id}>
                    <TableCell className="whitespace-nowrap">
                      {formatDateTimeValue(entry.at)}
                    </TableCell>
                    <TableCell>
                      {entry.action === "create"
                        ? "Tạo bản nháp"
                        : (ACTION_LABELS[entry.action as ScoreRuleAction] ??
                          entry.action)}
                    </TableCell>
                    <TableCell>{entry.actor_id}</TableCell>
                    <TableCell>{entry.reason}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </div>
      </section>
    </div>
  );
}
