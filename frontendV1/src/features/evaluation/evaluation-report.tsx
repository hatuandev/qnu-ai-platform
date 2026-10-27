import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EvidenceFields } from "@/features/knowledge/evidence-fields";
import { downloadBlob } from "@/lib/download-blob";
import { evaluationCsv } from "./report-export";
import type { EvaluationRequest, EvaluationResult } from "./types";

function metric(value: number | null | undefined) {
  return value === null || value === undefined ? "Chưa đo" : value.toFixed(3);
}
const labels: Record<string, string> = {
  dense: "Vector",
  hybrid: "Kết hợp",
  hybrid_rerank: "Kết hợp + xếp hạng lại",
};
export function EvaluationReport({
  result,
  request,
}: {
  result: EvaluationResult;
  request: EvaluationRequest;
}) {
  return (
    <section aria-label="Báo cáo đánh giá" className="space-y-4 border-t pt-4">
      <div className="flex flex-wrap justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold">
            Kết quả đánh giá truy xuất
          </h2>
          <p className="text-sm text-muted-foreground">
            {result.label_status === "human_reviewed"
              ? "Nhãn do người dùng xác nhận đã rà soát"
              : "Nhãn nháp — cần người rà soát"}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              downloadBlob(
                new Blob([JSON.stringify({ request, result }, null, 2)], {
                  type: "application/json;charset=utf-8",
                }),
                `${result.id}.json`,
              )
            }
          >
            Xuất JSON
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              downloadBlob(
                new Blob([evaluationCsv(result, request)], {
                  type: "text/csv;charset=utf-8",
                }),
                `${result.id}.csv`,
              )
            }
          >
            Xuất CSV
          </Button>
        </div>
      </div>
      <p className="text-sm text-warning">
        Chưa đánh giá độ đúng và mức bám nguồn của câu trả lời. Báo cáo không tự
        phê duyệt xuất bản. Kết quả chỉ có trong phiên này; hãy xuất tệp trước
        khi rời trang.
      </p>
      <div className="text-xs text-muted-foreground break-all space-y-1">
        <p>Chỉ mục: {result.index_run_id}</p>
        <p>Hash: {result.manifest_sha256}</p>
        <p>
          Nhãn: {result.label_version} · {result.label_author}
        </p>
      </div>
      <p className="text-xs text-muted-foreground">
        Mỗi câu hỏi dùng chung bước embedding, tìm vector, từ khóa và hợp nhất.
        Rerank đo phần bổ sung; không có phép đo độ trễ vector độc lập. Điểm
        trung bình chỉ tính lượt hoàn tất có nhãn.
      </p>
      <div className="overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Chiến lược</TableHead>
              <TableHead>Hoàn tất / Dự kiến</TableHead>
              <TableHead>Lỗi</TableHead>
              <TableHead>Hit@K</TableHead>
              <TableHead>Recall@K</TableHead>
              <TableHead>MRR@K</TableHead>
              <TableHead>Precision@K</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Object.entries(result.summary).map(([strategy, summary]) => (
              <TableRow key={strategy}>
                <TableCell>{labels[strategy] ?? strategy}</TableCell>
                <TableCell>
                  {summary.completed}/{summary.expected}
                </TableCell>
                <TableCell>{summary.errors}</TableCell>
                <TableCell>
                  {metric(summary.completed_only_metrics.hit_at_k)}
                </TableCell>
                <TableCell>
                  {metric(summary.completed_only_metrics.annotated_recall_at_k)}
                </TableCell>
                <TableCell>
                  {metric(summary.completed_only_metrics.mrr_at_k)}
                </TableCell>
                <TableCell>
                  {metric(
                    summary.completed_only_metrics.annotated_precision_at_k,
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="space-y-3">
        {request.queries.map((query) => (
          <details key={query.id} className="rounded-lg border p-3">
            <summary className="cursor-pointer text-sm font-medium break-words">
              {query.query}
            </summary>
            <p className="mt-2 text-xs text-muted-foreground">
              Nhóm: {query.group || "Chưa phân nhóm"} ·{" "}
              {query.gold_chunk_ids.length} đoạn chuẩn · Toàn bộ tài liệu đủ
              điều kiện trong snapshot
            </p>
            <div className="space-y-3 pt-3">
              {result.records
                .filter((r) => r.query_id === query.id)
                .map((record) => (
                  <div
                    key={record.strategy}
                    className="border-t pt-3 space-y-1 text-sm"
                  >
                    <h3 className="font-medium">
                      {labels[record.strategy] ?? record.strategy} ·{" "}
                      {record.status === "completed" ? "Hoàn tất" : "Lỗi"}
                    </h3>
                    {record.error_code ? (
                      <p role="alert" className="text-destructive">
                        {record.error_code}
                      </p>
                    ) : null}
                    {record.metrics?.empty_gold ? (
                      <p>Nhãn rỗng — không tính điểm chất lượng.</p>
                    ) : null}
                    <p>
                      Recall: {metric(record.metrics?.annotated_recall_at_k)} ·
                      MRR: {metric(record.metrics?.mrr_at_k)}
                    </p>
                    <details>
                      <summary className="cursor-pointer text-xs">
                        Thứ tự đoạn và dấu vết ứng viên
                      </summary>
                      <EvidenceFields
                        value={{
                          ranked_ids: record.ranked_ids,
                          ...record.candidate_trace,
                        }}
                      />
                    </details>
                  </div>
                ))}
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}
