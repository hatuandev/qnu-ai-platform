import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import {
  useCommitDecisionMutation,
  useCompiledVersionQuery,
  useCreateCompiledDocumentMutation,
  useDecisionPreviewMutation,
  useDocumentSummaryQuery,
  useRegisterCompiledDocumentVersionMutation,
  useRegistrationMetadataQuery,
  useReviewGateQuery,
} from "@/api/documents/queries";
import type {
  AutomaticMetadataPreview,
  DecisionFindingResolution,
  DecisionPreviewResponse,
  DocumentSummaryResponse,
  EventMoment,
  MetadataEvent,
  RetrievalAnnotation,
  ReviewAck,
  ReviewFinding,
  VersionResponse,
} from "@/api/documents/types";
import { getRevisionContentBlob } from "@/api/knowledge/requests";
import type { SourceVersionRef } from "@/api/knowledge/types";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

type PendingDecision = {
  action: "approve" | "publish";
  preview: DecisionPreviewResponse;
  key: string;
};

type SourceLocation = NonNullable<
  ReviewFinding["finding"]["source_locations"]
>[number];

function ReviewSource({
  workspaceId,
  collectionId,
  location,
}: {
  workspaceId: string;
  collectionId: string;
  location: SourceLocation;
}) {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState<{
    url: string;
    pdf: boolean;
    fileName?: string;
  } | null>(null);
  const [error, setError] = useState(false);
  const {
    source_id: sourceId,
    revision_id: revisionId,
    page,
    file_name: fileName,
  } = location;
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    let url: string | undefined;
    void getRevisionContentBlob(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      {
        signal: controller.signal,
      },
    ).then(
      ({ blob, contentType, fileName: revisionFileName }) => {
        if (controller.signal.aborted) return;
        url = URL.createObjectURL(blob);
        setSource({
          url,
          pdf: contentType.split(";")[0] === "application/pdf",
          fileName: revisionFileName,
        });
      },
      () => {
        if (!controller.signal.aborted) setError(true);
      },
    );
    return () => {
      controller.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [workspaceId, collectionId, sourceId, revisionId, open]);

  return (
    <details
      onToggle={(event) => {
        const expanded = event.currentTarget.open;
        setOpen(expanded);
        if (!expanded) {
          setSource(null);
          setError(false);
        }
      }}
    >
      <summary className="cursor-pointer font-medium text-primary">
        {fileName || "Tệp gốc"} · Bảng {location.table_number} · Trang {page}
      </summary>
      {open && (
        <div className="mt-2 space-y-2">
          {error ? (
            <p role="alert">Không thể mở tệp gốc. Hãy đóng và mở lại để thử.</p>
          ) : source ? (
            <>
              {source.pdf && (
                <iframe
                  className="h-96 w-full"
                  title={`Tệp gốc, trang ${page}`}
                  src={`${source.url}#page=${page}`}
                />
              )}
              <a
                className="text-primary underline"
                href={source.url}
                download={source.fileName || fileName || "tep-goc"}
              >
                Tải tệp gốc
              </a>
            </>
          ) : (
            <p role="status">Đang mở tệp gốc…</p>
          )}
        </div>
      )}
    </details>
  );
}

const EVENT_UNITS: Record<string, string> = {
  day: "ngày",
  working_day: "ngày làm việc",
  week: "tuần",
  month: "tháng",
};

function formatIsoDate(value: string): string {
  const [year, month, day] = value.split("-");
  return day && month && year ? `${day}/${month}/${year}` : value;
}

function formatMoment(moment: EventMoment | null | undefined): string {
  if (!moment) return "";
  const parts: string[] = [];
  if (moment.date) parts.push(formatIsoDate(moment.date));
  else if (moment.year && moment.month)
    parts.push(`tháng ${moment.month}/${moment.year}`);
  else if (moment.month && moment.day)
    parts.push(`ngày ${moment.day}/${moment.month}`);
  else if (moment.month) parts.push(`tháng ${moment.month}`);
  if (moment.time) parts.push(moment.time);
  return parts.join(" ");
}

function formatSchedule(event: MetadataEvent): string {
  if (event.relative) {
    const unit = EVENT_UNITS[event.relative.unit] ?? event.relative.unit;
    return `trong ${event.relative.value} ${unit} kể từ ${event.relative.from_event}`;
  }
  if (event.dates?.length) return event.dates.map(formatIsoDate).join(", ");
  const start = formatMoment(event.window_start);
  const moment = formatMoment(event.moment);
  const end = event.end_exclusive && moment ? `trước ${moment}` : moment;
  if (start && end) return `từ ${start} đến ${end}`;
  return end || start || "chưa rõ thời điểm";
}

function formatScalar(value: string | number | boolean): string {
  if (typeof value === "boolean") return value ? "Có" : "Không";
  return String(value);
}

function annotationContext(target: string): string | null {
  if (target === "document") return null;
  if (target.startsWith("section:")) return "Trong một mục";
  if (target.startsWith("paragraph:")) return "Trong một đoạn";
  if (/^table:.+:row:/.test(target)) return "Trong một hàng của bảng";
  if (target.startsWith("table:")) return "Trong một cột của bảng";
  return "Trong một phần của tài liệu";
}

function annotationLines(values: RetrievalAnnotation["values"]): string[] {
  const lines: string[] = [];
  if (values.data_year) lines.push(`Năm dữ liệu: ${values.data_year}`);
  if (values.issued_year) lines.push(`Năm ban hành: ${values.issued_year}`);
  if (values.effective_from)
    lines.push(`Hiệu lực từ: ${formatIsoDate(values.effective_from)}`);
  if (values.effective_until)
    lines.push(`Hiệu lực đến: ${formatIsoDate(values.effective_until)}`);
  if (values.program) lines.push(`Ngành: ${values.program}`);
  if (values.intake) lines.push(`Đợt: ${values.intake}`);
  for (const [key, value] of Object.entries(values.attributes ?? {})) {
    lines.push(`${key}: ${formatScalar(value)}`);
  }
  for (const event of values.events ?? []) {
    lines.push(`${event.label}: ${formatSchedule(event)}`);
  }
  return [...new Set(lines)];
}

function RegistrationMetadataPanel({
  preview,
  isPending,
  error,
  onRetry,
}: {
  preview?: AutomaticMetadataPreview;
  isPending: boolean;
  error: Error | null;
  onRetry: () => void;
}) {
  return (
    <div className="space-y-2 rounded-md bg-muted/40 p-3">
      <p className="font-medium">Thông tin tự nhận diện từ nguồn</p>
      {isPending ? (
        <p role="status">Đang nhận diện năm, ngành, đợt và lịch…</p>
      ) : error ? (
        <div role="alert" className="space-y-2 text-destructive">
          <p>Không tải được thông tin đăng ký: {error.message}</p>
          <Button variant="outline" size="sm" onClick={onRetry}>
            <RefreshCw className="size-3.5" />
            Thử lại
          </Button>
        </div>
      ) : preview?.annotations.length ? (
        <ul className="space-y-2">
          {preview.annotations.map((annotation) => {
            const context = annotationContext(annotation.target);
            return (
              <li key={annotation.target} className="space-y-1">
                {context && (
                  <p className="text-xs text-muted-foreground">{context}</p>
                )}
                <ul className="list-disc pl-4">
                  {annotationLines(annotation.values).map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </li>
            );
          })}
        </ul>
      ) : (
        <p>
          Chưa nhận diện được năm, ngành, đợt hoặc lịch có căn cứ trong nguồn
          này.
        </p>
      )}
      <p className="text-xs text-muted-foreground">
        Thông tin này được lưu cùng phiên bản và chỉ dùng làm phạm vi tra cứu;
        hãy đối chiếu nhanh trước khi đăng ký.
      </p>
    </div>
  );
}

/** The dialog is keyed by compilation run. Closing it never resets a committed step. */
export function PublicationDialog({
  open,
  onOpenChange,
  workspaceId,
  collectionId,
  sourceTitle,
  compilationRunId,
  existingDocumentId,
  existingVersion,
  canRegister,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collectionId: string;
  sourceTitle: string;
  compilationRunId: string;
  existingDocumentId?: string | null;
  existingVersion?: SourceVersionRef | null;
  canRegister?: boolean;
  onSuccess?: (summary: DocumentSummaryResponse) => void;
}) {
  const [documentId, setDocumentId] = useState(
    existingVersion?.document_id ?? existingDocumentId ?? null,
  );
  const [versionId, setVersionId] = useState(
    existingVersion?.version_id ?? null,
  );
  const [registeredVersion, setRegisteredVersion] =
    useState<VersionResponse | null>(null);
  const [committedStatus, setCommittedStatus] = useState<{
    status: "approved" | "published";
    at: number;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [skipReview, setSkipReview] = useState(false);
  const [reason, setReason] = useState("");
  const [resolutions, setResolutions] = useState<
    Record<
      string,
      Omit<DecisionFindingResolution, "decision"> & {
        decision?: DecisionFindingResolution["decision"];
      }
    >
  >({});
  const pending = useRef<PendingDecision | null>(null);
  const registration = useRef({
    document_key: `doc_${compilationRunId}`,
    title: sourceTitle,
    compilation_run_id: compilationRunId,
  });
  const create = useCreateCompiledDocumentMutation(workspaceId, collectionId);
  const registerVersion = useRegisterCompiledDocumentVersionMutation(
    workspaceId,
    collectionId,
  );
  const preview = useDecisionPreviewMutation(workspaceId, collectionId);
  const commit = useCommitDecisionMutation(workspaceId, collectionId);
  const versionQuery = useCompiledVersionQuery(
    workspaceId,
    collectionId,
    open ? documentId : null,
    open ? versionId : null,
  );
  const summaryQuery = useDocumentSummaryQuery(
    workspaceId,
    collectionId,
    open ? documentId : null,
  );
  const gateQuery = useReviewGateQuery(
    workspaceId,
    collectionId,
    open ? documentId : null,
    open ? versionId : null,
  );
  const metadataQuery = useRegistrationMetadataQuery(
    workspaceId,
    collectionId,
    open ? compilationRunId : null,
    open && !versionId,
  );
  const version = versionQuery.data ?? registeredVersion;
  const summary = summaryQuery.data;
  const exact =
    version?.compilation_run_id === compilationRunId &&
    version.id === versionId;
  const status =
    committedStatus && versionQuery.dataUpdatedAt <= committedStatus.at
      ? committedStatus.status
      : exact
        ? version.status
        : null;
  const served =
    status === "published" &&
    summary?.served_version?.id === versionId &&
    summary.serving_matches_published &&
    summary.readiness.status === "ready";
  const capabilities = summary?.capabilities;
  const gate = gateQuery.data;
  const noReview =
    (gateQuery.error as { code?: string } | null)?.code ===
    "publication_review_required";
  const findingCount = gate?.findings.length ?? 0;
  const resolved =
    gate?.findings.every(
      (item) =>
        Boolean(resolutions[item.finding_id]?.decision) &&
        resolutions[item.finding_id]?.reason.trim().length >= 10,
    ) ?? false;
  const canApprove =
    exact &&
    status === "draft" &&
    capabilities?.can_approve === true &&
    confirmed &&
    (skipReview
      ? reason.trim().length >= 10
      : Boolean(
          gate && gate.bundle_sha256 === version?.bundle_sha256 && resolved,
        ));
  const canPublish =
    exact && status === "approved" && capabilities?.can_publish === true;

  async function register() {
    if (
      lock.current ||
      !(canRegister === true || capabilities?.can_register === true)
    )
      return;
    const metadataSha = metadataQuery.data?.sha256;
    if (!metadataSha) {
      setError(
        "Chưa tải được thông tin tự nhận diện của nguồn. Hãy thử tải lại trước khi đăng ký.",
      );
      return;
    }
    lock.current = true;
    setBusy(true);
    setError(null);
    try {
      const result = documentId
        ? await registerVersion.mutateAsync({
            documentId,
            data: {
              compilation_run_id: compilationRunId,
              automatic_metadata_sha256: metadataSha,
            },
            idempotencyKey: `reg_version_${documentId}_${compilationRunId}`,
          })
        : await create.mutateAsync({
            data: {
              ...registration.current,
              automatic_metadata_sha256: metadataSha,
            },
            idempotencyKey: `reg_${compilationRunId}`,
          });
      setDocumentId(result.document.id);
      setVersionId(result.version.id);
      setRegisteredVersion(result.version);
    } catch (err) {
      if (
        (err as { code?: string } | null)?.code ===
        "registration_metadata_changed"
      ) {
        void metadataQuery.refetch();
        setError(
          "Thông tin tự nhận diện vừa thay đổi. Bản xem trước đã được tải lại; hãy đối chiếu rồi bấm Tiếp tục.",
        );
      } else {
        setError(
          err instanceof Error ? err.message : "Không thể đăng ký tài liệu.",
        );
      }
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  async function decide(action: "approve" | "publish") {
    if (!documentId || !versionId || !version || lock.current) return;
    if (!pending.current && !(action === "approve" ? canApprove : canPublish))
      return;
    lock.current = true;
    setBusy(true);
    setError(null);
    try {
      // After a lost commit response, a user retry replays exactly the same receipt.
      // Never generate a different preview under the old idempotency key.
      if (!pending.current) {
        let reviewAck: ReviewAck | undefined;
        if (action === "approve" && !skipReview) {
          if (!gate) throw new Error("Chưa tải được báo cáo rà soát.");
          reviewAck = {
            review_id: gate.review_id,
            report_sha256: gate.report_sha256,
            confirmed_reviewed: true,
            retrieval_metadata_sha256: version.retrieval_metadata_sha256,
            resolutions: gate.findings.map((item) => {
              const resolution = resolutions[item.finding_id];
              if (!resolution?.decision || resolution.reason.trim().length < 10)
                throw new Error(
                  "Cần giải trình từng nhận xét trước khi duyệt.",
                );
              return { ...resolution, decision: resolution.decision };
            }),
          };
        }
        const result = await preview.mutateAsync({
          documentId,
          versionId,
          data: {
            action,
            reason:
              action === "publish"
                ? "Phát hành bản đã duyệt để phục vụ tra cứu."
                : skipReview
                  ? reason.trim()
                  : "Đã đối chiếu nội dung và báo cáo rà soát của phiên bản này.",
            ...(action === "approve"
              ? skipReview
                ? {
                    review_skip: {
                      confirmed_skip: true,
                      version_id: versionId,
                      bundle_sha256: version.bundle_sha256,
                      retrieval_metadata_sha256:
                        version.retrieval_metadata_sha256,
                    },
                  }
                : {
                    review_ack: reviewAck,
                  }
              : {}),
          },
        });
        pending.current = {
          action,
          preview: result,
          key: `decision_${result.id}`,
        };
      }
      const receipt = pending.current;
      await commit.mutateAsync({
        documentId,
        versionId,
        data: {
          preview_id: receipt.preview.id,
          preview_sha256: receipt.preview.preview_sha256,
        },
        idempotencyKey: receipt.key,
      });
      setCommittedStatus({
        status: receipt.action === "approve" ? "approved" : "published",
        at: Date.now(),
      });
      pending.current = null;
      setConfirmed(false);
      void versionQuery.refetch();
      void summaryQuery.refetch();
    } catch (err) {
      const code = (err as { code?: string } | null)?.code;
      if (
        code === "publication_preview_expired" ||
        code === "publication_preview_stale"
      ) {
        pending.current = null;
        setConfirmed(false);
        void versionQuery.refetch();
        void summaryQuery.refetch();
      }
      setError(
        err instanceof Error
          ? err.message
          : "Chưa xác định được kết quả. Hãy kiểm tra lại cùng thao tác.",
      );
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  const frozen = busy || Boolean(pending.current);
  return (
    <Dialog open={open} onOpenChange={busy ? undefined : onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[85dvh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-primary" />
            Duyệt & Phát hành
          </DialogTitle>
          <DialogDescription>
            {sourceTitle.replace(/_/g, " ")}
          </DialogDescription>
        </DialogHeader>
        {error && (
          <div role="alert" className="flex gap-2 text-sm text-destructive">
            <AlertCircle className="size-4 shrink-0" />
            {error}
          </div>
        )}
        {!versionId ? (
          <div className="space-y-3 text-sm">
            <p className="text-muted-foreground">
              Lưu bản đang xem thành{" "}
              {documentId ? "phiên bản mới của tài liệu" : "tài liệu"} trước khi
              duyệt.
            </p>
            <RegistrationMetadataPanel
              preview={metadataQuery.data}
              isPending={metadataQuery.isPending}
              error={metadataQuery.error}
              onRetry={() => void metadataQuery.refetch()}
            />
          </div>
        ) : versionQuery.isPending && !registeredVersion ? (
          <p role="status" className="text-sm">
            Đang kiểm tra phiên bản…
          </p>
        ) : !exact ? (
          <p role="alert" className="text-sm text-destructive">
            {versionQuery.error?.message ??
              "Chưa xác nhận được phiên bản khớp bản đang xem."}
          </p>
        ) : status === "draft" ? (
          <div className="space-y-4 text-sm">
            {gateQuery.isPending && (
              <p role="status">Đang tải báo cáo rà soát…</p>
            )}
            {gate && (
              <>
                <p>
                  {findingCount
                    ? `${findingCount} nhận xét cần đối chiếu trước khi duyệt.`
                    : "Báo cáo rà soát không ghi nhận vấn đề. Bạn vẫn cần kiểm tra nội dung."}
                </p>
                {!skipReview &&
                  gate.findings.map((item, index) => (
                    <div
                      key={item.finding_id}
                      className="space-y-2 border-b pb-3"
                    >
                      <p>
                        {index + 1}.{" "}
                        {item.finding.explanation ??
                          "Nhận xét cần đối chiếu với bản gốc."}
                      </p>
                      {item.finding.source_locations?.map((location) => (
                        <ReviewSource
                          key={`${location.revision_id}:${location.table_number}`}
                          workspaceId={workspaceId}
                          collectionId={collectionId}
                          location={location}
                        />
                      ))}
                      {Boolean(item.finding.source_locations?.length) && (
                        <details>
                          <summary className="cursor-pointer font-medium text-primary">
                            Xem đoạn cần đối chiếu
                          </summary>
                          {item.finding.draft_excerpts?.map((draft) => (
                            <div
                              className="mt-2 whitespace-pre-wrap"
                              key={draft.text}
                            >
                              {draft.heading && (
                                <p className="font-medium">{draft.heading}</p>
                              )}
                              <p>{draft.text}</p>
                            </div>
                          ))}
                        </details>
                      )}
                      <select
                        aria-label={`Xử lý nhận xét ${index + 1}`}
                        disabled={frozen}
                        className="w-full rounded-md border p-2 bg-background"
                        value={resolutions[item.finding_id]?.decision ?? ""}
                        onChange={(event) =>
                          setResolutions((old) => ({
                            ...old,
                            [item.finding_id]: {
                              finding_id: item.finding_id,
                              reason: old[item.finding_id]?.reason ?? "",
                              decision: event.target
                                .value as DecisionFindingResolution["decision"],
                            },
                          }))
                        }
                      >
                        <option value="" disabled>
                          Chọn cách xử lý
                        </option>
                        <option value="accepted_risk">
                          Chấp nhận sau khi đối chiếu
                        </option>
                        <option value="not_an_issue">Không phải lỗi</option>
                      </select>
                      <Textarea
                        aria-label={`Giải trình nhận xét ${index + 1}`}
                        placeholder="Giải trình (ít nhất 10 ký tự)"
                        maxLength={2000}
                        disabled={frozen}
                        value={resolutions[item.finding_id]?.reason ?? ""}
                        onChange={(event) =>
                          setResolutions((old) => ({
                            ...old,
                            [item.finding_id]: {
                              finding_id: item.finding_id,
                              decision: old[item.finding_id]?.decision,
                              reason: event.target.value,
                            },
                          }))
                        }
                      />
                    </div>
                  ))}
              </>
            )}
            {noReview && (
              <p>Chưa có báo cáo rà soát hoàn tất cho phiên bản này.</p>
            )}
            {gateQuery.error && !noReview && (
              <p role="alert" className="text-destructive">
                {gateQuery.error.message}
              </p>
            )}
            {(gate || noReview) && (
              <>
                <label className="flex items-start gap-2">
                  <input
                    type="checkbox"
                    checked={skipReview}
                    disabled={frozen}
                    onChange={(event) => {
                      setSkipReview(event.target.checked);
                      setConfirmed(false);
                    }}
                  />
                  Duyệt không dùng báo cáo AI
                </label>
                {skipReview && (
                  <Textarea
                    aria-label="Lý do duyệt không dùng báo cáo AI"
                    placeholder="Lý do (ít nhất 10 ký tự)"
                    maxLength={1000}
                    value={reason}
                    disabled={frozen}
                    onChange={(event) => setReason(event.target.value)}
                  />
                )}
                <label className="flex items-start gap-2">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    disabled={frozen}
                    onChange={(event) => setConfirmed(event.target.checked)}
                  />
                  Tôi đã đối chiếu và xác nhận nội dung của phiên bản này.
                </label>
              </>
            )}
            {capabilities?.can_approve === false && (
              <p className="text-muted-foreground">
                Cần người có quyền duyệt xác nhận phiên bản này.
              </p>
            )}
          </div>
        ) : status === "approved" ? (
          <p className="text-sm">
            Đã duyệt. Phát hành để hệ thống tự đưa bản này vào tra cứu.
          </p>
        ) : status === "published" ? (
          <p role="status" className="flex gap-2 text-sm">
            {served ? (
              <CheckCircle2 className="size-4 text-primary" />
            ) : (
              <Loader2 className="size-4 animate-spin" />
            )}
            {served
              ? "Sẵn sàng phục vụ hỏi đáp."
              : "Đã phát hành. Hệ thống đang đồng bộ; bạn có thể đóng cửa sổ này."}
          </p>
        ) : (
          <p className="text-sm">
            Phiên bản này không còn ở bước duyệt hoặc phát hành.
          </p>
        )}
        {summaryQuery.error && (
          <p role="alert" className="text-sm text-destructive">
            Không tải được trạng thái phục vụ: {summaryQuery.error.message}
          </p>
        )}
        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            disabled={busy}
            onClick={() => {
              if (summary) onSuccess?.(summary);
              onOpenChange(false);
            }}
          >
            Đóng
          </Button>
          {!versionId && (
            <Button
              disabled={
                busy ||
                !metadataQuery.data ||
                !(canRegister === true || capabilities?.can_register === true)
              }
              onClick={register}
            >
              {busy ? "Đang lưu…" : "Tiếp tục"}
            </Button>
          )}
          {versionId && status === "draft" && (
            <Button
              disabled={busy || (!pending.current && !canApprove)}
              onClick={() => decide("approve")}
            >
              {busy
                ? "Đang duyệt…"
                : pending.current
                  ? "Thử lại cùng thao tác"
                  : "Xác nhận duyệt"}
            </Button>
          )}
          {status === "approved" && (
            <Button
              disabled={busy || (!pending.current && !canPublish)}
              onClick={() => decide("publish")}
            >
              {busy
                ? "Đang phát hành…"
                : pending.current
                  ? "Thử lại cùng thao tác"
                  : "Phát hành"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
