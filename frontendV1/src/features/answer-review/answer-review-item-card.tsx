import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  HelpCircle,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ANSWER_REVIEW_ITEM_STATUS_META,
  ANSWER_REVIEW_LABEL_META,
  formatAnswerReviewError,
} from "@/features/answer-review/format";
import type {
  AnswerReviewItem,
  AnswerReviewLabel,
} from "@/features/answer-review/types";
import type {
  AnswerResponse,
  EvidenceSource,
  Statement,
} from "@/features/conversations/types";
import { AnswerCoverageNotice } from "@/features/rag/answer-coverage";
import { describeAnswerReason } from "@/features/rag/types";
import { formatUsage } from "@/features/rag/verification-panel";
import { formatDateTimeValue } from "@/lib/date-utils";

export type OpenCitationHandler = (
  statement: Statement | null,
  sources: EvidenceSource[],
) => void;

type LabelChoice = "none" | AnswerReviewLabel;

const LABEL_CHOICES: { value: LabelChoice; label: string }[] = [
  { value: "none", label: "Chưa gắn nhãn" },
  { value: "correct", label: "Đúng" },
  { value: "missing", label: "Thiếu nguồn" },
  { value: "wrong_source", label: "Sai nguồn" },
  { value: "wrong_year", label: "Sai năm" },
];

export function AnswerReviewItemCard({
  item,
  assistantRevision,
  canLabel,
  isSavingLabel,
  onSaveLabel,
  onOpenCitation,
}: {
  item: AnswerReviewItem;
  assistantRevision: number;
  canLabel: boolean;
  isSavingLabel: boolean;
  onSaveLabel: (
    item: AnswerReviewItem,
    label: AnswerReviewLabel | null,
    note: string,
  ) => void;
  onOpenCitation: OpenCitationHandler;
}) {
  const statusMeta = ANSWER_REVIEW_ITEM_STATUS_META[item.status];

  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-1 min-w-0">
          <span className="text-[10px] font-mono text-muted-foreground">
            Câu hỏi #{item.ordinal + 1}
          </span>
          <p className="text-sm font-medium text-foreground break-words">
            {item.question}
          </p>
        </div>
        <Badge variant={statusMeta.variant} className="text-[10px] shrink-0">
          {statusMeta.label}
        </Badge>
      </div>

      {item.status === "answered" && item.result ? (
        <AnsweredBody result={item.result} onOpenCitation={onOpenCitation} />
      ) : null}

      {item.status === "insufficient_evidence" && item.result ? (
        <InsufficientBody
          result={item.result}
          onOpenCitation={onOpenCitation}
        />
      ) : null}

      {item.status === "failed" || item.status === "uncertain" ? (
        <FailureBody item={item} />
      ) : null}

      <TechnicalFooter item={item} assistantRevision={assistantRevision} />

      <LabelSection
        item={item}
        canLabel={canLabel}
        isSavingLabel={isSavingLabel}
        onSaveLabel={onSaveLabel}
      />
    </div>
  );
}

function AnsweredBody({
  result,
  onOpenCitation,
}: {
  result: AnswerResponse;
  onOpenCitation: OpenCitationHandler;
}) {
  const statements = result.statements;
  const firstSource = result.sources[0];
  const openAllSources = () =>
    onOpenCitation(
      statements[0] ?? {
        text: "",
        evidence_ids: firstSource ? [firstSource.evidence_id] : [],
      },
      result.sources,
    );

  return (
    <div className="space-y-2.5">
      {statements.length > 0 ? (
        <div className="space-y-2 text-sm leading-relaxed text-foreground">
          {statements.map((statement) => (
            <div
              key={`${result.id}_stmt_${statement.evidence_ids.join("-")}_${statement.text.length}`}
              className="flex flex-wrap items-baseline gap-1.5"
            >
              <span className="break-words">{statement.text}</span>
              <span className="inline-flex flex-wrap gap-1">
                {statement.evidence_ids.map((evidenceId) => (
                  <Button
                    key={evidenceId}
                    variant="secondary"
                    size="sm"
                    className="h-5 px-1.5 font-mono text-[10px]"
                    onClick={() => onOpenCitation(statement, result.sources)}
                  >
                    {evidenceId}
                  </Button>
                ))}
              </span>
            </div>
          ))}
        </div>
      ) : result.answer ? (
        <p className="text-sm leading-relaxed text-foreground">
          {result.answer}
        </p>
      ) : null}

      <AnswerCoverageNotice
        coverage={result.coverage}
        onOpenSources={(ids) =>
          onOpenCitation(
            { text: "Phần nguồn cần đối chiếu", evidence_ids: ids },
            result.sources,
          )
        }
      />

      {result.sources.length > 0 ? (
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs gap-1.5"
          onClick={openAllSources}
        >
          <ExternalLink className="size-3" />
          Xem nguồn ({result.sources.length})
        </Button>
      ) : null}
    </div>
  );
}

function InsufficientBody({
  result,
  onOpenCitation,
}: {
  result: AnswerResponse;
  onOpenCitation: OpenCitationHandler;
}) {
  return (
    <div className="rounded-md border border-warning/40 bg-warning/5 p-3 space-y-2">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-warning">
        <AlertTriangle className="size-3.5 shrink-0" />
        Không đủ bằng chứng để trả lời
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">
        {describeAnswerReason(result.reason)}
      </p>
      <AnswerCoverageNotice
        coverage={result.coverage}
        onOpenSources={(ids) =>
          onOpenCitation(
            { text: "Phần nguồn cần đối chiếu", evidence_ids: ids },
            result.sources,
          )
        }
      />
      {result.sources.length > 0 ? (
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs gap-1.5"
          onClick={() =>
            onOpenCitation(
              result.statements[0] ?? {
                text: "",
                evidence_ids: [result.sources[0].evidence_id],
              },
              result.sources,
            )
          }
        >
          <ExternalLink className="size-3" />
          Đối chiếu nguồn ({result.sources.length})
        </Button>
      ) : null}
    </div>
  );
}

function FailureBody({ item }: { item: AnswerReviewItem }) {
  const isUncertain = item.status === "uncertain";
  return (
    <Alert variant={isUncertain ? "warning" : "destructive"}>
      {isUncertain ? (
        <HelpCircle className="size-4 text-warning" />
      ) : (
        <XCircle className="size-4" />
      )}
      <AlertDescription className="text-xs leading-relaxed">
        {formatAnswerReviewError(
          item.error_code,
          isUncertain
            ? "Chưa xác định được kết quả của câu hỏi này. Không có câu trả lời nào được ghi nhận."
            : "Không thể tạo câu trả lời cho câu hỏi này.",
        )}
      </AlertDescription>
    </Alert>
  );
}

function TechnicalFooter({
  item,
  assistantRevision,
}: {
  item: AnswerReviewItem;
  assistantRevision: number;
}) {
  const trace = item.result?.trace;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t pt-2 text-[10px] font-mono text-muted-foreground">
      <span>Cấu hình trợ lý v{assistantRevision}</span>
      {item.generation !== null ? (
        <span>Chỉ mục thế hệ {item.generation}</span>
      ) : null}
      {trace?.model_name ? <span>{trace.model_name}</span> : null}
      {typeof trace?.total_tokens === "number" ? (
        <span title="Token của bước sinh câu trả lời, không phải tổng toàn pipeline">
          Token sinh: {formatUsage(trace.total_tokens)}
        </span>
      ) : null}
      {item.index_run_id ? (
        <span title={item.index_run_id} className="truncate max-w-48">
          Mã chỉ mục: {shortenId(item.index_run_id)}
        </span>
      ) : null}
    </div>
  );
}

function LabelSection({
  item,
  canLabel,
  isSavingLabel,
  onSaveLabel,
}: {
  item: AnswerReviewItem;
  canLabel: boolean;
  isSavingLabel: boolean;
  onSaveLabel: (
    item: AnswerReviewItem,
    label: AnswerReviewLabel | null,
    note: string,
  ) => void;
}) {
  const [choice, setChoice] = useState<LabelChoice>(item.label ?? "none");
  const [note, setNote] = useState(item.label_note ?? "");
  const isLabelable =
    item.status === "answered" || item.status === "insufficient_evidence";

  if (canLabel && isLabelable) {
    const isDirty =
      choice !== (item.label ?? "none") ||
      note.trim() !== (item.label_note ?? "");
    return (
      <div className="border-t pt-3 space-y-2">
        <div className="flex flex-col gap-2 sm:flex-row">
          <Select
            value={choice}
            onValueChange={(value) => setChoice(value as LabelChoice)}
          >
            <SelectTrigger className="h-8 w-full text-xs sm:w-44">
              <SelectValue placeholder="Gắn nhãn đánh giá" />
            </SelectTrigger>
            <SelectContent>
              {LABEL_CHOICES.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Ghi chú đánh giá (tuỳ chọn)"
            className="h-8 text-xs"
            maxLength={2000}
          />
          <Button
            size="sm"
            className="h-8 shrink-0"
            disabled={!isDirty || isSavingLabel}
            onClick={() =>
              onSaveLabel(item, choice === "none" ? null : choice, note)
            }
          >
            {isSavingLabel ? "Đang lưu..." : "Lưu nhãn"}
          </Button>
        </div>
        <p className="text-[11px] text-muted-foreground">
          Nhãn do người kiểm thử gắn để đánh giá câu trả lời; không phải nhãn
          vàng retrieval và không tự động dùng cho benchmark.
        </p>
      </div>
    );
  }

  if (!item.label) return null;

  const labelMeta = ANSWER_REVIEW_LABEL_META[item.label];
  return (
    <div className="border-t pt-2 flex flex-wrap items-center gap-2 text-[11px]">
      <CheckCircle2 className="size-3.5 text-muted-foreground" />
      <span className="text-muted-foreground">Nhãn người kiểm thử:</span>
      <Badge variant={labelMeta.variant} className="text-[10px]">
        {labelMeta.label}
      </Badge>
      {item.label_note ? (
        <span className="text-muted-foreground break-words">
          “{item.label_note}”
        </span>
      ) : null}
      {item.labelled_at ? (
        <span className="text-muted-foreground">
          lúc {formatDateTimeValue(item.labelled_at)}
        </span>
      ) : null}
    </div>
  );
}

function shortenId(value: string): string {
  if (value.length <= 18) return value;
  return `${value.slice(0, 10)}…${value.slice(-4)}`;
}
