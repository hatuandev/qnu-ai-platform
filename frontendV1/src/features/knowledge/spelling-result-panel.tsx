import { useState } from "react";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useDetectCheckQuery } from "./ocr-queries";
import { validateSuggestionSpan } from "./ocr-schemas";
import type {
  DetectionResponse,
  ReviewDocument,
  Suggestion,
} from "./ocr-types";

type Props = {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  revisionId: string;
  runId: string;
  checkId?: string;
  localCheck: DetectionResponse | null;
  doc: ReviewDocument;
  draftChanges: ReadonlyMap<string, string>;
  canManage: boolean;
  onApply: (suggestion: Suggestion) => boolean;
};
export function SpellingResultPanel(props: Props) {
  if (props.checkId)
    return (
      <StoredCheck key={props.checkId} {...props} checkId={props.checkId} />
    );
  return props.localCheck ? (
    <SpellingResultView
      key={props.localCheck.id}
      check={props.localCheck}
      doc={props.doc}
      draftChanges={props.draftChanges}
      canManage={props.canManage}
      onApply={props.onApply}
    />
  ) : null;
}
function StoredCheck({
  workspaceId,
  collectionId,
  sourceId,
  revisionId,
  runId,
  checkId,
  doc,
  draftChanges,
  canManage,
  onApply,
}: Props & { checkId: string }) {
  const query = useDetectCheckQuery(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    runId,
    checkId,
  );
  if (query.isPending)
    return (
      <p role="status" className="text-sm">
        Đang mở lại lần kiểm tra chính tả…
      </p>
    );
  if (query.isError)
    return (
      <ErrorState error={query.error} onRetry={() => void query.refetch()} />
    );
  return (
    <SpellingResultView
      key={query.data.id}
      check={query.data}
      doc={doc}
      draftChanges={draftChanges}
      canManage={canManage}
      onApply={onApply}
    />
  );
}
export function SpellingResultView({
  check,
  doc,
  draftChanges,
  canManage,
  onApply,
}: Pick<Props, "doc" | "draftChanges" | "canManage" | "onApply"> & {
  check: DetectionResponse;
}) {
  const [dismissed, setDismissed] = useState<Set<number>>(() => new Set());
  const matches =
    check.version === doc.version &&
    check.canonical_sha256 === doc.canonical_sha256;
  const completed = check.status === "completed";
  return (
    <section
      aria-label="Kết quả kiểm tra chính tả"
      className="rounded-xl border p-4 space-y-3 text-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">Kết quả kiểm tra chính tả</h3>
        <Badge variant="outline">
          {check.status === "completed"
            ? "Hoàn tất"
            : check.status === "running"
              ? "Đang xử lý"
              : check.status === "uncertain"
                ? "Chưa rõ kết quả"
                : check.status === "failed"
                  ? "Thất bại"
                  : check.status}
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground break-all">
        Mã lần kiểm tra: {check.id} · Phiên bản văn bản v{check.version}
      </p>
      {check.error_code ? (
        <p role="alert" className="text-destructive">
          {check.error_code}
        </p>
      ) : null}
      {!completed ? (
        <p role="status">
          Lần kiểm tra chưa hoàn tất thành công. Giao diện chỉ đọc trạng thái,
          không tự gọi model lại.
        </p>
      ) : !matches ? (
        <p role="alert" className="text-warning">
          Kết quả thuộc phiên bản hoặc hash khác với văn bản đang mở. Chọn phiên
          bản v{check.version} trong bộ chọn văn bản để đối chiếu; chưa cho áp
          dụng gợi ý.
        </p>
      ) : (
        <>
          <p className="text-xs text-muted-foreground">
            Phạm vi đã kiểm tra: {check.checked_evidence_ids.length} đoạn · Còn{" "}
            {check.suggestions.length - dismissed.size} đề xuất
          </p>
          {check.suggestions.length === 0 ? (
            <p>
              Không có đề xuất trong lần kiểm tra này. Điều này không xác nhận
              OCR đã chính xác.
            </p>
          ) : (
            <ul className="max-h-80 overflow-y-auto space-y-3">
              {check.suggestions.map((suggestion, index) => {
                if (dismissed.has(index)) return null;
                const unit = doc.units.find(
                  (item) => item.evidence_id === suggestion.evidence_id,
                );
                const text = unit
                  ? (draftChanges.get(unit.evidence_id) ?? unit.text)
                  : null;
                const valid =
                  text !== null && validateSuggestionSpan(text, suggestion);
                return (
                  <li
                    key={`${suggestion.evidence_id}:${suggestion.start}:${suggestion.end}`}
                    className="rounded-lg border p-3 space-y-2"
                  >
                    <p className="text-xs text-muted-foreground">
                      Trang {unit?.page ?? "chưa xác định"}
                    </p>
                    <p className="whitespace-pre-wrap break-words">
                      {text ?? suggestion.original}
                    </p>
                    <p>
                      <span className="line-through text-destructive">
                        {suggestion.original}
                      </span>{" "}
                      →{" "}
                      <span className="text-success font-medium">
                        {suggestion.replacement}
                      </span>
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {suggestion.reason}
                    </p>
                    {!valid ? (
                      <p className="text-xs text-warning">
                        Văn bản đã thay đổi, gợi ý không còn khớp vị trí.
                      </p>
                    ) : null}
                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={!valid || !canManage}
                        onClick={() => {
                          if (valid && canManage && onApply(suggestion))
                            setDismissed((before) =>
                              new Set(before).add(index),
                            );
                        }}
                      >
                        Áp dụng vào nháp
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setDismissed((before) => new Set(before).add(index))
                        }
                      >
                        Bỏ qua
                      </Button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
          <p className="text-xs text-muted-foreground">
            Kiểm tra này dựa trên văn bản, chưa đối chiếu ảnh gốc. Gợi ý được áp
            dụng vào bản nháp. Cần chọn Lưu thay đổi để tạo bản dẫn xuất mới;
            tệp OCR gốc được giữ lại.
          </p>
        </>
      )}
    </section>
  );
}
