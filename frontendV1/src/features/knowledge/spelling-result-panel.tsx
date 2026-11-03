import {
  AlertTriangle,
  ArrowRight,
  Check,
  Clock,
  Edit3,
  Eye,
  EyeOff,
  RotateCcw,
  ScanSearch,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useDetectCheckQuery } from "./ocr-queries";
import {
  extractNormalizedBbox,
  formatOcrError,
  formatUnitLocator,
  replaceSpanByCodePoints,
  validateSuggestionSpan,
} from "./ocr-schemas";
import type {
  DetectionResponse,
  ReviewDocument,
  Suggestion,
} from "./ocr-types";

export type SpellingPanelProps = {
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
  onLocateUnit?: (target: { evidenceId: string; page?: number }) => void;
  onManualEditUnit?: (evidenceId: string, page?: number) => void;
  onRevertUnitDraft?: (evidenceId: string) => void;
  focusedEvidenceId?: string | null;
};
type Props = SpellingPanelProps;

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
      onLocateUnit={props.onLocateUnit}
      onManualEditUnit={props.onManualEditUnit}
      onRevertUnitDraft={props.onRevertUnitDraft}
      focusedEvidenceId={props.focusedEvidenceId}
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
  onLocateUnit,
  onManualEditUnit,
  onRevertUnitDraft,
  focusedEvidenceId,
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
      <p role="status" className="text-sm text-muted-foreground p-3">
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
      onLocateUnit={onLocateUnit}
      onManualEditUnit={onManualEditUnit}
      onRevertUnitDraft={onRevertUnitDraft}
      focusedEvidenceId={focusedEvidenceId}
    />
  );
}

export function SpellingResultView({
  check,
  doc,
  draftChanges,
  canManage,
  onApply,
  onLocateUnit,
  onManualEditUnit,
  onRevertUnitDraft,
  focusedEvidenceId,
}: Pick<
  Props,
  | "doc"
  | "draftChanges"
  | "canManage"
  | "onApply"
  | "onLocateUnit"
  | "onManualEditUnit"
  | "onRevertUnitDraft"
  | "focusedEvidenceId"
> & {
  check: DetectionResponse;
}) {
  const [applied, setApplied] = useState<Set<number>>(() => new Set());
  const [dismissed, setDismissed] = useState<Set<number>>(() => new Set());
  const [showResolved, setShowResolved] = useState(false);

  const matches =
    check.version === doc.version &&
    check.canonical_sha256 === doc.canonical_sha256;
  const completed = check.status === "completed";

  // Classify each suggestion's status accurately
  const classifiedSuggestions = check.suggestions.map((suggestion, index) => {
    const unit = doc.units.find(
      (item) => item.evidence_id === suggestion.evidence_id,
    );
    const currentText = unit
      ? (draftChanges.get(unit.evidence_id) ?? unit.text)
      : null;
    const expectedDraftAfter =
      unit && validateSuggestionSpan(unit.text, suggestion)
        ? replaceSpanByCodePoints(
            unit.text,
            suggestion.start,
            suggestion.end,
            suggestion.replacement,
          )
        : null;
    const isAppliedInDraft =
      applied.has(index) ||
      Boolean(
        unit &&
          draftChanges.has(unit.evidence_id) &&
          expectedDraftAfter !== null &&
          draftChanges.get(unit.evidence_id) === expectedDraftAfter,
      );
    const isDismissed = !isAppliedInDraft && dismissed.has(index);
    const isSpanValid =
      !isAppliedInDraft &&
      currentText !== null &&
      validateSuggestionSpan(currentText, suggestion);

    const status: "pending" | "applied" | "dismissed" | "mismatch" =
      isAppliedInDraft
        ? "applied"
        : isDismissed
          ? "dismissed"
          : isSpanValid
            ? "pending"
            : "mismatch";

    return {
      suggestion,
      index,
      unit,
      currentText,
      isSpanValid,
      status,
    };
  });

  const pendingOrMismatchItems = classifiedSuggestions.filter(
    (item) => item.status === "pending" || item.status === "mismatch",
  );
  const resolvedItems = classifiedSuggestions.filter(
    (item) => item.status === "applied" || item.status === "dismissed",
  );
  const appliedCount = classifiedSuggestions.filter(
    (item) => item.status === "applied",
  ).length;
  const dismissedCount = classifiedSuggestions.filter(
    (item) => item.status === "dismissed",
  ).length;
  const mismatchCount = classifiedSuggestions.filter(
    (item) => item.status === "mismatch",
  ).length;

  const visibleItems = showResolved
    ? classifiedSuggestions
    : pendingOrMismatchItems;

  return (
    <section
      aria-label="Kết quả kiểm tra chính tả"
      className="rounded-xl border bg-card p-4 space-y-3 text-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-primary shrink-0" />
          <h3 className="font-semibold text-foreground">
            Kết quả kiểm tra chính tả
          </h3>
          <Badge variant="secondary" className="text-xs">
            Phiên bản v{check.version}
          </Badge>
        </div>
        <Badge
          variant={
            check.status === "completed"
              ? "success"
              : check.status === "failed"
                ? "destructive"
                : check.status === "uncertain"
                  ? "warning"
                  : "outline"
          }
        >
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

      {check.error_code ? (
        <div
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive space-y-1"
        >
          <p className="font-medium">{formatOcrError(check.error_code)}</p>
          <details className="text-muted-foreground">
            <summary className="cursor-pointer select-none">
              Chi tiết kỹ thuật
            </summary>
            <p className="font-mono mt-1 break-all">{check.error_code}</p>
          </details>
        </div>
      ) : null}

      {!completed ? (
        <p role="status" className="text-xs text-muted-foreground">
          Lần kiểm tra chưa hoàn tất thành công. Giao diện chỉ đọc trạng thái,
          không tự gọi model lại.
        </p>
      ) : !matches ? (
        <div
          role="alert"
          className="rounded-lg border border-warning/40 bg-warning/10 p-3 text-xs text-foreground space-y-1"
        >
          <p className="font-medium text-warning">
            Kết quả thuộc phiên bản hoặc hash khác với văn bản đang mở. Chọn
            phiên bản v{check.version} trong bộ chọn văn bản để đối chiếu; chưa
            cho áp dụng gợi ý.
          </p>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-muted/40 px-3 py-2 text-xs">
            <div className="flex flex-wrap items-center gap-2 text-muted-foreground">
              <span>
                Phạm vi đã kiểm tra:{" "}
                <strong className="text-foreground">
                  {check.checked_evidence_ids.length}
                </strong>{" "}
                đoạn
              </span>
              <span>·</span>
              <span>
                Còn{" "}
                <strong className="text-foreground">
                  {pendingOrMismatchItems.length}
                </strong>{" "}
                đề xuất cần xem
              </span>
              {appliedCount > 0 ? (
                <Badge variant="success" className="text-[11px] py-0 px-1.5">
                  Đã áp dụng vào nháp: {appliedCount}
                </Badge>
              ) : null}
              {dismissedCount > 0 ? (
                <Badge variant="secondary" className="text-[11px] py-0 px-1.5">
                  Đã bỏ qua: {dismissedCount}
                </Badge>
              ) : null}
              {mismatchCount > 0 ? (
                <Badge variant="warning" className="text-[11px] py-0 px-1.5">
                  Không còn khớp: {mismatchCount}
                </Badge>
              ) : null}
            </div>

            {resolvedItems.length > 0 ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-xs gap-1"
                onClick={() => setShowResolved((prev) => !prev)}
              >
                {showResolved ? (
                  <>
                    <EyeOff className="size-3.5" />
                    <span>Ẩn mục đã xử lý ({resolvedItems.length})</span>
                  </>
                ) : (
                  <>
                    <Eye className="size-3.5" />
                    <span>Xem mục đã xử lý ({resolvedItems.length})</span>
                  </>
                )}
              </Button>
            ) : null}
          </div>

          {check.suggestions.length === 0 ? (
            <div className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground space-y-1">
              <p className="text-foreground font-medium">
                {check.withheld_suggestions?.length
                  ? "Không có gợi ý tự động; có các mục bên dưới cần đối chiếu ảnh gốc trước khi sửa."
                  : "Không có đề xuất trong lần kiểm tra này. Điều này không xác nhận OCR đã chính xác."}
              </p>
              <p>
                Kết quả rỗng chỉ có nghĩa mô hình không phát hiện lỗi chính tả
                rõ ràng trong phạm vi {check.checked_evidence_ids.length} đoạn
                đã gửi; vui lòng vẫn đối chiếu ảnh gốc với các số liệu hoặc tên
                riêng quan trọng.
              </p>
            </div>
          ) : visibleItems.length === 0 ? (
            <div className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground flex flex-wrap items-center justify-between gap-2">
              <span>
                Bạn đã xem xét hết {check.suggestions.length} đề xuất trong lượt
                kiểm tra này ({appliedCount} đã áp dụng vào nháp,{" "}
                {dismissedCount} đã bỏ qua).
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 text-xs"
                onClick={() => setShowResolved(true)}
              >
                Xem lại các mục đã xử lý
              </Button>
            </div>
          ) : (
            <ul
              aria-label="Danh sách gợi ý sửa chính tả"
              className="max-h-96 overflow-y-auto space-y-3 pr-1"
            >
              {visibleItems.map(
                ({
                  suggestion,
                  index,
                  unit,
                  currentText,
                  isSpanValid,
                  status,
                }) => {
                  const locator = unit
                    ? formatUnitLocator(unit, doc.units)
                    : "Trang chưa xác định";
                  const hasBbox = Boolean(
                    unit && extractNormalizedBbox(unit.bbox),
                  );
                  const isFocused =
                    Boolean(focusedEvidenceId) &&
                    focusedEvidenceId === suggestion.evidence_id;

                  return (
                    <li
                      key={`${suggestion.evidence_id}:${suggestion.start}:${suggestion.end}`}
                      className={`rounded-lg border p-3 space-y-2.5 transition-colors ${
                        isFocused
                          ? "border-primary bg-primary/5"
                          : status === "applied"
                            ? "border-success/40 bg-success/5"
                            : status === "dismissed"
                              ? "opacity-75 bg-muted/20"
                              : ""
                      }`}
                    >
                      {/* Header: Page/Unit location + Status Badge */}
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-1.5 text-xs">
                          <span className="font-semibold text-foreground">
                            {locator}
                          </span>
                          {hasBbox ? (
                            <Badge
                              variant="outline"
                              className="text-[10px] py-0 px-1.5 text-muted-foreground"
                            >
                              Có vùng ảnh đối chiếu
                            </Badge>
                          ) : null}
                        </div>

                        {status === "pending" ? (
                          <Badge
                            variant="outline"
                            className="text-[11px] gap-1 py-0"
                          >
                            <Clock className="size-3" />
                            <span>Chờ xem xét</span>
                          </Badge>
                        ) : status === "applied" ? (
                          <Badge
                            variant="success"
                            className="text-[11px] gap-1 py-0"
                          >
                            <Check className="size-3" />
                            <span>Đã áp dụng vào nháp</span>
                          </Badge>
                        ) : status === "dismissed" ? (
                          <Badge
                            variant="secondary"
                            className="text-[11px] gap-1 py-0"
                          >
                            <EyeOff className="size-3" />
                            <span>Đã bỏ qua</span>
                          </Badge>
                        ) : (
                          <Badge
                            variant="warning"
                            className="text-[11px] gap-1 py-0"
                          >
                            <AlertTriangle className="size-3" />
                            <span>Không còn khớp</span>
                          </Badge>
                        )}
                      </div>

                      {/* Word Change: original -> replacement */}
                      <div className="flex flex-wrap items-center gap-1.5 text-xs">
                        <span className="text-muted-foreground">Thay chữ:</span>
                        <span className="line-through bg-destructive/10 text-destructive px-1.5 py-0.5 rounded font-medium">
                          {suggestion.original}
                        </span>
                        <ArrowRight
                          className="size-3.5 text-muted-foreground shrink-0"
                          aria-hidden="true"
                        />
                        <span className="bg-success/15 text-success px-1.5 py-0.5 rounded font-semibold">
                          {suggestion.replacement}
                        </span>
                      </div>

                      {/* Reason */}
                      <p className="text-xs text-muted-foreground">
                        <span className="font-medium text-foreground/80">
                          Lý do:{" "}
                        </span>
                        {suggestion.reason}
                      </p>

                      {/* Context Phrases Before / After */}
                      <div className="rounded-md bg-muted/30 p-2.5 space-y-1.5 text-xs border border-border/50">
                        <p className="whitespace-pre-wrap break-words text-foreground">
                          {currentText ?? suggestion.original}
                        </p>
                        {suggestion.context_before &&
                        suggestion.context_before !==
                          (currentText ?? suggestion.original) ? (
                          <p className="whitespace-pre-wrap break-words">
                            <span className="text-muted-foreground font-medium">
                              Cụm trước sửa:{" "}
                            </span>
                            {suggestion.context_before}
                          </p>
                        ) : null}
                        {suggestion.context_after ? (
                          <p className="whitespace-pre-wrap break-words">
                            <span className="text-muted-foreground font-medium">
                              Cụm sau sửa:{" "}
                            </span>
                            {suggestion.context_after}
                          </p>
                        ) : null}
                      </div>

                      {status === "mismatch" ? (
                        <p className="text-xs text-warning flex items-center gap-1.5">
                          <AlertTriangle className="size-3.5 shrink-0" />
                          <span>
                            Văn bản đã thay đổi, gợi ý không còn khớp vị trí.
                            Vui lòng đối chiếu ảnh và sửa tay nếu cần.
                          </span>
                        </p>
                      ) : null}

                      {/* Actions */}
                      <div className="flex flex-wrap items-center gap-2 pt-0.5">
                        {status === "pending" || status === "mismatch" ? (
                          <>
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs gap-1"
                              disabled={!isSpanValid || !canManage}
                              onClick={() => {
                                if (
                                  isSpanValid &&
                                  canManage &&
                                  onApply(suggestion)
                                ) {
                                  setApplied((before) =>
                                    new Set(before).add(index),
                                  );
                                }
                              }}
                            >
                              <Check className="size-3.5" />
                              <span>Áp dụng vào nháp</span>
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="h-7 text-xs"
                              onClick={() =>
                                setDismissed((before) =>
                                  new Set(before).add(index),
                                )
                              }
                            >
                              Bỏ qua
                            </Button>
                          </>
                        ) : status === "dismissed" ? (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs gap-1"
                            onClick={() =>
                              setDismissed((before) => {
                                const next = new Set(before);
                                next.delete(index);
                                return next;
                              })
                            }
                          >
                            <RotateCcw className="size-3" />
                            <span>Đưa lại vào danh sách chờ</span>
                          </Button>
                        ) : status === "applied" &&
                          canManage &&
                          onRevertUnitDraft &&
                          unit &&
                          draftChanges.has(unit.evidence_id) ? (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs gap-1"
                            onClick={() => {
                              onRevertUnitDraft(unit.evidence_id);
                              setApplied((before) => {
                                const next = new Set(before);
                                next.delete(index);
                                return next;
                              });
                            }}
                          >
                            <RotateCcw className="size-3" />
                            <span>Hoàn tác nháp đoạn này</span>
                          </Button>
                        ) : null}

                        {onLocateUnit && unit ? (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-7 text-xs gap-1 text-primary"
                            onClick={() =>
                              onLocateUnit({
                                evidenceId: unit.evidence_id,
                                page: unit.page,
                              })
                            }
                          >
                            <ScanSearch className="size-3.5" />
                            <span>Đối chiếu trên trang</span>
                          </Button>
                        ) : null}

                        {onManualEditUnit && unit && canManage ? (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-7 text-xs gap-1"
                            onClick={() =>
                              onManualEditUnit(unit.evidence_id, unit.page)
                            }
                          >
                            <Edit3 className="size-3.5" />
                            <span>Sửa tay</span>
                          </Button>
                        ) : null}
                      </div>
                    </li>
                  );
                },
              )}
            </ul>
          )}

          {check.withheld_suggestions?.length ? (
            <div
              className="rounded-lg border border-warning/40 bg-warning/5 p-3 space-y-2.5"
              role="note"
              aria-label="Cần đối chiếu ảnh gốc"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h4 className="font-semibold text-warning flex items-center gap-1.5 text-xs sm:text-sm">
                  <AlertTriangle className="size-4 shrink-0" />
                  <span>
                    Cần đối chiếu ảnh gốc ({check.withheld_suggestions.length})
                  </span>
                </h4>
                <Badge variant="warning" className="text-[10px] py-0">
                  Chỉ sửa tay sau khi xem ảnh
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Những đề xuất này thay đổi chữ hoặc cấu trúc từ có thể làm đổi
                nghĩa câu, nên hệ thống không cho áp dụng trực tiếp. Vui lòng
                đối chiếu ảnh nguồn và tự chỉnh sửa tay trong ô văn bản nếu
                trang gốc thực sự viết như vậy.
              </p>
              <ul className="divide-y divide-border/60">
                {check.withheld_suggestions.map((item) => {
                  const unit = doc.units.find(
                    (u) => u.evidence_id === item.evidence_id,
                  );
                  const locator = unit
                    ? formatUnitLocator(unit, doc.units)
                    : "Trang chưa xác định";
                  return (
                    <li
                      key={`${item.evidence_id}:${item.start}:${item.end}`}
                      className="py-2.5 space-y-1.5 text-xs"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-semibold text-foreground">
                          {locator}
                        </span>
                        <span className="text-muted-foreground">
                          Chưa được xác minh từ ảnh nguồn
                        </span>
                      </div>
                      <p className="whitespace-pre-wrap break-words rounded bg-background/80 p-2 border border-border/50 text-foreground">
                        {item.context_before ?? unit?.text}
                      </p>
                      <p className="flex flex-wrap items-center gap-1.5">
                        <span className="text-muted-foreground">
                          Từ nghi ngờ cần đối chiếu:
                        </span>
                        <span className="font-medium text-foreground">
                          {item.original}
                        </span>
                        <ArrowRight
                          className="size-3 text-muted-foreground"
                          aria-hidden="true"
                        />
                        <span className="font-medium text-warning">
                          {item.replacement}
                        </span>
                      </p>
                      {item.reason ? (
                        <p className="text-muted-foreground">
                          Lý do nghi ngờ: {item.reason}
                        </p>
                      ) : null}
                      {unit &&
                      (onLocateUnit || (onManualEditUnit && canManage)) ? (
                        <div className="flex flex-wrap items-center gap-2 pt-1">
                          {onLocateUnit ? (
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs gap-1"
                              onClick={() =>
                                onLocateUnit({
                                  evidenceId: unit.evidence_id,
                                  page: unit.page,
                                })
                              }
                            >
                              <ScanSearch className="size-3.5" />
                              <span>Đối chiếu trên trang ảnh</span>
                            </Button>
                          ) : null}
                          {onManualEditUnit && canManage ? (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="h-7 text-xs gap-1"
                              onClick={() =>
                                onManualEditUnit(unit.evidence_id, unit.page)
                              }
                            >
                              <Edit3 className="size-3.5" />
                              <span>Sửa tay sau khi đối chiếu</span>
                            </Button>
                          ) : null}
                        </div>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}

          <p className="text-xs text-muted-foreground">
            Kiểm tra này dựa trên văn bản, chưa đối chiếu ảnh gốc. Gợi ý được áp
            dụng vào bản nháp. Cần chọn Lưu thay đổi để tạo bản dẫn xuất mới;
            tệp OCR gốc được giữ lại.
          </p>
        </>
      )}

      <details className="text-[11px] text-muted-foreground pt-1 border-t border-border/40">
        <summary className="cursor-pointer select-none">
          Thông tin phiên kiểm tra (dành cho hỗ trợ kỹ thuật)
        </summary>
        <p className="font-mono mt-1 break-all">
          Mã lần kiểm tra: {check.id} · Phiên bản văn bản v{check.version}
        </p>
      </details>
    </section>
  );
}
