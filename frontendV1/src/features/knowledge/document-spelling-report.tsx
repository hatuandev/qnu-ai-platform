import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { formatOcrError } from "./ocr-schemas";
import type { DocumentSpellingReport as Report } from "./ocr-spelling-batch";
import {
  type SpellingPanelProps,
  SpellingResultPanel,
} from "./spelling-result-panel";

export function DocumentSpellingProgress({
  report,
  stopping,
  onStop,
}: {
  report: Report;
  stopping: boolean;
  onStop: () => void;
}) {
  const finished = report.batches.filter(
    (b) =>
      b.status !== "pending" &&
      b.status !== "running" &&
      b.status !== "not_run",
  ).length;
  const active = report.batches.filter((b) => b.status === "running");
  const activePages = [...new Set(active.map((b) => b.page))];
  return (
    <div className="space-y-2 text-xs" role="status">
      <p>
        Đã xử lý {finished}/{report.batches.length} nhóm
        {active.length
          ? ` · Đang kiểm tra ${active.length} nhóm · Trang ${activePages.join(", ")}`
          : ""}
      </p>
      <Progress
        value={
          report.batches.length ? (finished / report.batches.length) * 100 : 0
        }
      />
      <p>
        Giữ trang này mở khi chạy. Tối đa 2 nhóm song song. Khi dừng, hệ thống
        chờ các nhóm đang xử lý và không gửi nhóm mới; hệ thống không tự gửi lại
        nhóm lỗi.
      </p>
      {!report.finished && (
        <Button
          size="sm"
          variant="outline"
          onClick={onStop}
          disabled={stopping}
        >
          {stopping
            ? "Đang chờ các nhóm hiện tại…"
            : "Dừng sau các nhóm hiện tại"}
        </Button>
      )}
    </div>
  );
}

export function DocumentSpellingReport({
  report,
  ...props
}: Omit<SpellingPanelProps, "checkId" | "localCheck"> & { report: Report }) {
  const completed = report.batches.filter((b) => b.status === "completed");
  const issues = report.batches.filter(
    (b) => b.status === "failed" || b.status === "uncertain",
  );
  const skipped = report.batches.filter((b) => b.status === "not_run");
  const suggestions = completed.reduce(
    (n, b) => n + (b.check?.suggestions.length ?? 0),
    0,
  );
  const withheld = completed.reduce(
    (n, b) => n + (b.check?.withheld_suggestions?.length ?? 0),
    0,
  );
  const download = () => {
    const blob = new Blob(
      [
        JSON.stringify(
          {
            version: report.version,
            sha256: report.sha256,
            finished: report.finished,
            batches: report.batches.map((b) => ({
              page: b.page,
              units: b.evidenceIds.length,
              status: b.status,
              check_id: b.check?.id,
              error_code: b.errorCode,
              suggestions: b.check?.suggestions.length ?? 0,
              withheld: b.check?.withheld_suggestions?.length ?? 0,
            })),
          },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "bao-cao-kiem-tra-chinh-ta.json";
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <section className="space-y-3" aria-label="Báo cáo kiểm tra chính tả">
      <div className="space-y-2 border-b pb-3 text-xs">
        <h3 className="font-semibold">
          {report.finished
            ? "Báo cáo kiểm tra chính tả"
            : "Đang kiểm tra chính tả"}
        </h3>
        <p>
          {completed.length}/{report.batches.length} nhóm hoàn tất ·{" "}
          {suggestions} gợi ý sửa · {withheld} mục cần đối chiếu ảnh.
        </p>
        {(issues.length > 0 || skipped.length > 0) && (
          <p className="text-warning">
            Chưa kiểm tra xong phạm vi đã chọn: {issues.length} nhóm lỗi/chưa
            xác định, {skipped.length} nhóm chưa chạy. Không tự gửi lại.
          </p>
        )}
        {report.finished && suggestions === 0 && (
          <p>Không có đề xuất sửa không đồng nghĩa toàn bộ OCR đã chính xác.</p>
        )}
        {issues.map((b, i) => (
          <p key={b.key} className="text-destructive">
            Trang {b.page} · {b.evidenceIds.length} đoạn:{" "}
            {b.errorCode === "model_not_configured"
              ? "Chưa đặt model Chat mặc định cho đơn vị."
              : formatOcrError(b.errorCode)}{" "}
            <span className="sr-only">Nhóm lỗi {i + 1}</span>
          </p>
        ))}
        {skipped.length > 0 && (
          <p>
            Các trang còn nhóm chưa chạy:{" "}
            {[...new Set(skipped.map((b) => b.page))].join(", ")}.
          </p>
        )}
        <Button variant="outline" size="sm" onClick={download}>
          Tải báo cáo JSON
        </Button>
      </div>
      {completed
        .filter(
          (b) =>
            b.check &&
            (b.check.suggestions.length ||
              b.check.withheld_suggestions?.length),
        )
        .map((b) => (
          <div key={b.key} className="space-y-2">
            <h4 className="text-xs font-medium">
              Trang {b.page} · {b.evidenceIds.length} đoạn đã kiểm tra
            </h4>
            <SpellingResultPanel {...props} localCheck={b.check ?? null} />
          </div>
        ))}
    </section>
  );
}
