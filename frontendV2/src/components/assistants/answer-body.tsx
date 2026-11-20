import { ChevronDown, HelpCircle, Quote, TriangleAlert } from "lucide-react";
import { useState } from "react";
import type { AnswerResult, AnswerSource } from "@/api/answer-reviews";
import { CitationBadge } from "@/components/knowledge/citation-badge";
import { MarkdownContent } from "@/components/knowledge/markdown-content";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

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
  return location ? location.slice(0, 140) : undefined;
}

function sourceFullText(source: AnswerSource): string {
  const passage = source.source_passages[0]?.text;
  return (passage ?? source.text ?? "").trim();
}

function sourceKindLabel(kind: string): string {
  if (kind === "table") return "Bảng dữ liệu";
  if (kind === "row_card") return "Thẻ dòng dữ liệu";
  if (kind === "text") return "Đoạn văn";
  return kind;
}

function StatementList({
  statements,
  sources,
  onSelectEvidence,
}: {
  statements: { text: string; evidence_ids: string[] }[];
  sources: AnswerSource[];
  onSelectEvidence?: (evidenceId: string, index: number) => void;
}) {
  const indexByEvidence = new Map(
    sources.map((source, index) => [source.evidence_id, index + 1]),
  );
  const sourceByEvidence = new Map(
    sources.map((source) => [source.evidence_id, source]),
  );

  return (
    <div className="space-y-3">
      {statements.map((statement) => {
        const badges = statement.evidence_ids.map((evidenceId) => {
          const index = indexByEvidence.get(evidenceId);
          if (!index) return null;
          const source = sourceByEvidence.get(evidenceId);
          const fullText = source ? sourceFullText(source) : undefined;
          return (
            <CitationBadge
              key={evidenceId}
              index={index}
              rawKey={evidenceId}
              location={source ? sourceLocation(source) : undefined}
              excerpt={fullText}
              fullText={fullText}
              onSelect={(idx, key) => onSelectEvidence?.(key, idx)}
            />
          );
        });

        return (
          <MarkdownContent
            key={`${statement.text.slice(0, 32)}-${statement.evidence_ids.join("|")}`}
            content={statement.text}
            compact
            suffix={
              badges.length > 0 ? (
                <span className="inline-flex items-center align-baseline">
                  {badges}
                </span>
              ) : undefined
            }
          />
        );
      })}
    </div>
  );
}

function SourceItem({
  source,
  index,
}: {
  source: AnswerSource;
  index: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const text = sourceFullText(source);
  const isLong = text.length > 240;
  const isTableOrCard = source.kind === "table" || source.kind === "row_card";

  return (
    <li
      key={source.evidence_id}
      className="rounded-md border border-border/60 bg-muted/25 p-2.5 text-[11px] space-y-1.5 transition-colors hover:bg-muted/40"
    >
      <div className="flex flex-wrap items-center justify-between gap-1.5">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="font-semibold text-primary">[{index}]</span>
          <Badge
            variant="outline"
            className={cn(
              "h-4 px-1.5 text-[10px] font-medium",
              isTableOrCard && "border-primary/40 bg-primary/10 text-primary",
            )}
          >
            {sourceKindLabel(source.kind)}
          </Badge>
          {sourceLocation(source) ? (
            <span
              className="max-w-[280px] truncate text-muted-foreground font-medium"
              title={sourceLocation(source)}
            >
              {sourceLocation(source)}
            </span>
          ) : null}
        </div>

        {isLong && (
          <button
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            className="text-[10px] text-primary hover:underline font-medium cursor-pointer"
          >
            {expanded ? "Thu gọn" : `Xem trọn vẹn (${text.length} ký tự)`}
          </button>
        )}
      </div>

      <div
        className={cn(
          "whitespace-pre-wrap text-foreground/85 leading-relaxed select-text",
          !expanded && "line-clamp-3",
          expanded &&
            "font-mono text-[10.5px] max-h-72 overflow-y-auto bg-card/70 p-2 rounded border border-border/40",
        )}
      >
        {text}
      </div>
    </li>
  );
}

function SourceList({ sources }: { sources: AnswerSource[] }) {
  return (
    <ul className="space-y-2">
      {sources.map((source, index) => (
        <SourceItem
          key={source.evidence_id}
          source={source}
          index={index + 1}
        />
      ))}
    </ul>
  );
}

function InsufficientEvidenceCallout({ result }: { result: AnswerResult }) {
  const messageText =
    result.message ||
    result.answer ||
    (result.reason ? REASON_TEXT[result.reason] : null) ||
    "Hệ thống chưa tìm thấy đủ dữ kiện trong các tài liệu đã xuất bản để trả lời chắc chắn câu hỏi này.";

  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3.5 space-y-2.5 dark:border-amber-400/20 dark:bg-amber-950/20">
        <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
          <HelpCircle className="size-4 shrink-0" />
          <span className="text-xs font-semibold">
            Chưa đủ căn cứ trong tài liệu đã xuất bản
          </span>
        </div>

        <div className="text-xs text-foreground/90 leading-relaxed">
          <MarkdownContent content={messageText} compact />
        </div>

        <div className="border-t border-amber-500/20 pt-2 text-[11px] text-muted-foreground space-y-1">
          <p className="font-medium text-foreground/80">
            Gợi ý để có câu trả lời chính xác:
          </p>
          <ul className="list-disc pl-4 space-y-0.5 text-[11px]">
            <li>
              Cung cấp tên hoặc số hiệu văn bản cụ thể (ví dụ:{" "}
              <span className="font-mono text-primary font-medium">
                QĐ 4740/QĐ-BGDĐT
              </span>
              ,{" "}
              <span className="font-mono text-primary font-medium">
                KH 130/KH-ĐHQN
              </span>
              ).
            </li>
            <li>
              Nêu rõ số điều, phụ lục, bảng biểu hoặc mã tiêu chí (ví dụ:{" "}
              <span className="font-mono text-primary font-medium">
                Tiêu chí 2.4
              </span>
              ,{" "}
              <span className="font-mono text-primary font-medium">Bảng 2</span>
              ,{" "}
              <span className="font-mono text-primary font-medium">
                Mục II.3
              </span>
              ).
            </li>
            <li>
              Chỉ định rõ năm áp dụng hoặc mốc thời gian nếu tài liệu có nhiều
              chu kỳ đánh giá hoặc kế hoạch theo từng năm.
            </li>
            <li>
              Kiểm tra tài liệu đã được tải lên và phê duyệt xuất bản trong kho
              tri thức của trợ lý chưa.
            </li>
          </ul>
        </div>
      </div>

      {result.sources.length > 0 ? (
        <Collapsible>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1.5 px-2 text-[11px] text-muted-foreground cursor-pointer hover:text-foreground"
            >
              <Quote className="size-3.5" />
              <span>
                {result.sources.length} đoạn trích tham khảo đã tra cứu
              </span>
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

export function AnswerBody({
  result,
  onSelectEvidence,
}: {
  result: AnswerResult;
  onSelectEvidence?: (evidenceId: string, index: number) => void;
}) {
  if (result.status === "insufficient_evidence") {
    return <InsufficientEvidenceCallout result={result} />;
  }

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
          onSelectEvidence={onSelectEvidence}
        />
      ) : result.message ? (
        <MarkdownContent content={result.message} compact />
      ) : result.answer ? (
        <MarkdownContent content={result.answer} compact />
      ) : null}
      {result.sources.length > 0 ? (
        <div className="flex items-center gap-2 pt-1 flex-wrap">
          {onSelectEvidence && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7 gap-1.5 px-2.5 text-[11px] font-medium text-primary border-primary/30 hover:bg-primary/10 cursor-pointer shadow-2xs"
              onClick={() => onSelectEvidence(result.sources[0]?.evidence_id, 1)}
            >
              <Quote className="size-3" />
              <span>Xem {result.sources.length} nguồn dẫn chứng đối soát</span>
            </Button>
          )}
          <Collapsible className={onSelectEvidence ? "inline-block" : "w-full"}>
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1 px-2 text-[11px] text-muted-foreground cursor-pointer hover:text-foreground"
              >
                <span>{onSelectEvidence ? "Xem nhanh tại chỗ" : `${result.sources.length} nguồn trích dẫn`}</span>
                <ChevronDown className="size-3 transition-transform data-[state=open]:rotate-180" />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="pt-2">
              <SourceList sources={result.sources} />
            </CollapsibleContent>
          </Collapsible>
        </div>
      ) : null}
    </div>
  );
}
