import { ChevronDown, Quote, TriangleAlert } from "lucide-react";
import type { AnswerResult, AnswerSource } from "@/api/answer-reviews";
import { CitationBadge } from "@/components/knowledge/citation-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

const REASON_TEXT: Record<string, string> = {
  no_eligible_content:
    "Kho tri thức chưa có nội dung phù hợp để trả lời câu hỏi này.",
  no_match: "Không tìm thấy đoạn tài liệu liên quan trong kho.",
  model_abstained: "Mô hình từ chối trả lời vì bằng chứng chưa đủ.",
  answer_not_supported:
    "Câu trả lời không được chứng minh bởi nguồn trích dẫn nên đã bị loại.",
  answer_verification_uncertain:
    "Bước kiểm chứng câu trả lời chưa đủ chắc chắn để công bố.",
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function sourceLocation(source: AnswerSource): string | undefined {
  const structure = asRecord(source.structure);
  const context = structure ? asRecord(structure.context) : null;
  const heading =
    context && typeof context.heading === "string" ? context.heading : null;
  const title =
    context && typeof context.title === "string" ? context.title : null;
  const citation =
    structure && typeof structure.source_table_citation === "string"
      ? structure.source_table_citation
      : null;
  const location = heading ?? title ?? citation;
  return location ? location.slice(0, 120) : undefined;
}

function sourceExcerpt(source: AnswerSource): string {
  const passage = source.source_passages[0]?.text;
  const text = passage ?? source.text;
  return text.length > 320 ? `${text.slice(0, 320)}…` : text;
}

function sourceKindLabel(kind: string): string {
  if (kind === "table") return "Bảng";
  if (kind === "text") return "Đoạn văn";
  return kind;
}

function StatementList({
  statements,
  sources,
}: {
  statements: { text: string; evidence_ids: string[] }[];
  sources: AnswerSource[];
}) {
  const indexByEvidence = new Map(
    sources.map((source, index) => [source.evidence_id, index + 1]),
  );
  const sourceByEvidence = new Map(
    sources.map((source) => [source.evidence_id, source]),
  );

  return (
    <div className="space-y-2">
      {statements.map((statement) => (
        <p
          key={`${statement.text.slice(0, 32)}-${statement.evidence_ids.join("|")}`}
          className="whitespace-pre-wrap text-sm leading-relaxed text-foreground"
        >
          {statement.text}
          {statement.evidence_ids.map((evidenceId) => {
            const index = indexByEvidence.get(evidenceId);
            if (!index) return null;
            const source = sourceByEvidence.get(evidenceId);
            return (
              <CitationBadge
                key={evidenceId}
                index={index}
                rawKey={evidenceId}
                location={source ? sourceLocation(source) : undefined}
                excerpt={source ? sourceExcerpt(source) : undefined}
              />
            );
          })}
        </p>
      ))}
    </div>
  );
}

function SourceList({ sources }: { sources: AnswerSource[] }) {
  return (
    <ul className="space-y-2">
      {sources.map((source) => (
        <li
          key={source.evidence_id}
          className="rounded-md border border-border/50 bg-muted/30 p-2 text-[11px]"
        >
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge
              variant="outline"
              className="h-4 px-1.5 text-[10px] font-medium"
            >
              {sourceKindLabel(source.kind)}
            </Badge>
            {sourceLocation(source) ? (
              <span className="truncate text-muted-foreground">
                {sourceLocation(source)}
              </span>
            ) : null}
          </div>
          <p className="mt-1 line-clamp-4 whitespace-pre-wrap text-foreground/80">
            {sourceExcerpt(source)}
          </p>
        </li>
      ))}
    </ul>
  );
}

export function AnswerBody({ result }: { result: AnswerResult }) {
  const reason =
    result.reason && !result.message ? REASON_TEXT[result.reason] : null;

  return (
    <div className="space-y-3">
      {reason ? (
        <p className="flex items-start gap-2 text-xs text-muted-foreground">
          <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
          <span>{reason}</span>
        </p>
      ) : null}
      {result.statements.length > 0 ? (
        <StatementList
          statements={result.statements}
          sources={result.sources}
        />
      ) : result.message ? (
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
          {result.message}
        </p>
      ) : result.answer ? (
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
          {result.answer}
        </p>
      ) : null}
      {result.sources.length > 0 ? (
        <Collapsible>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1.5 px-2 text-[11px] text-muted-foreground"
            >
              <Quote className="size-3.5" />
              <span>{result.sources.length} nguồn trích dẫn</span>
              <ChevronDown className="size-3.5 transition-transform data-[state=open]:rotate-180" />
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-2">
            <SourceList sources={result.sources} />
          </CollapsibleContent>
        </Collapsible>
      ) : null}
    </div>
  );
}
