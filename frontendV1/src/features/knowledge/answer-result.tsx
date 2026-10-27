import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type {
  AnswerResponse,
  EvidenceSource,
} from "@/features/conversations/types";
import {
  describeAnswerReason,
  describeMetadataFilter,
} from "@/features/rag/types";
import {
  formatUsage,
  VerificationPanel,
} from "@/features/rag/verification-panel";
import type { AnswerRequest } from "./answer-request";
import { EvidenceFields } from "./evidence-fields";
import { SearchEvidenceSheet } from "./search-evidence";

export function AnswerResult({
  workspaceId,
  collectionId,
  result,
  request,
}: {
  workspaceId: string;
  collectionId: string;
  result: AnswerResponse;
  request: AnswerRequest;
}) {
  const [source, setSource] = useState<EvidenceSource | null>(null);
  const open = (id: string) => {
    const found = result.sources.find((s) => s.evidence_id === id);
    if (found) setSource(found);
  };
  const coherent =
    result.status !== "answered" ||
    (result.statements.length > 0 &&
      result.statements.every(
        (s) =>
          s.evidence_ids.length > 0 &&
          s.evidence_ids.every((id) =>
            result.sources.some((e) => e.evidence_id === id),
          ),
      ));
  return (
    <section
      aria-label="Kết quả hỏi đáp thử"
      className="rounded-xl border bg-card p-4 sm:p-5 space-y-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">Kết quả hỏi đáp</h2>
        <Badge variant="outline">Generation {result.generation}</Badge>
      </div>
      <p className="whitespace-pre-wrap break-words text-sm">
        <strong>Câu hỏi đã gửi: </strong>
        {request.question}
      </p>
      <p className="text-xs text-muted-foreground">
        {request.document_ids
          ? `Phạm vi: ${request.document_ids.length} tài liệu đã chọn`
          : "Phạm vi: toàn bộ tài liệu đủ điều kiện"}{" "}
        · {describeMetadataFilter(request.metadata_filter)}
      </p>
      {!coherent ? (
        <p role="alert" className="text-sm text-destructive">
          Phản hồi không có dẫn nguồn nhất quán. Chưa hiển thị nội dung trả lời.
        </p>
      ) : result.status === "insufficient_evidence" ? (
        <p role="status" className="text-sm text-warning">
          {describeAnswerReason(result.reason)}
        </p>
      ) : (
        <ul className="space-y-4">
          {result.statements.map((s) => (
            <li
              key={`${result.id}:${s.text}:${s.evidence_ids.join(",")}`}
              className="space-y-2"
            >
              <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                {s.text}
              </p>
              <div className="flex flex-wrap gap-2">
                {s.evidence_ids.map((id) => (
                  <Button
                    key={id}
                    variant="outline"
                    size="sm"
                    onClick={() => open(id)}
                  >
                    Nguồn {id}
                  </Button>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
      <VerificationPanel
        trace={result.trace.verification}
        onOpenEvidence={open}
      />
      <div className="text-xs text-muted-foreground space-y-1">
        <p>
          Model trả lời: {result.trace.model_name ?? "Chưa gọi model trả lời"}
        </p>
        <p>Token sinh câu trả lời: {formatUsage(result.trace.total_tokens)}</p>
        <p>Lịch sử của màn hỏi thử chỉ có trong lần mở trang này.</p>
      </div>
      <details>
        <summary className="cursor-pointer text-xs text-muted-foreground">
          Chi tiết xử lý
        </summary>
        <div className="pt-3">
          <EvidenceFields
            value={{
              index_run_id: result.index_run_id,
              retrieval: result.trace.retrieval,
              context: result.trace.context,
              evidence_sha256: result.trace.evidence_sha256,
              stage_ms: result.trace.stage_ms,
            }}
          />
        </div>
      </details>
      {source ? (
        <SearchEvidenceSheet
          workspaceId={workspaceId}
          collectionId={collectionId}
          hit={source}
          onClose={() => setSource(null)}
        />
      ) : null}
    </section>
  );
}
