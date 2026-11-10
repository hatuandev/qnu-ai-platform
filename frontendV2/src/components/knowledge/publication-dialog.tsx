import { AlertCircle, CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import { useRef, useState } from "react";
import {
  useCommitDecisionMutation,
  useCompiledVersionQuery,
  useCreateCompiledDocumentMutation,
  useDecisionPreviewMutation,
  useDocumentSummaryQuery,
  useRegisterCompiledDocumentVersionMutation,
  useReviewGateQuery,
} from "@/api/documents/queries";
import type {
  DecisionFindingResolution,
  DecisionPreviewResponse,
  DocumentSummaryResponse,
  ReviewAck,
  VersionResponse,
} from "@/api/documents/types";
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
    lock.current = true;
    setBusy(true);
    setError(null);
    try {
      const result = documentId
        ? await registerVersion.mutateAsync({
            documentId,
            data: { compilation_run_id: compilationRunId },
            idempotencyKey: `reg_version_${documentId}_${compilationRunId}`,
          })
        : await create.mutateAsync({
            data: registration.current,
            idempotencyKey: `reg_${compilationRunId}`,
          });
      setDocumentId(result.document.id);
      setVersionId(result.version.id);
      setRegisteredVersion(result.version);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Không thể đăng ký tài liệu.",
      );
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
          <p className="text-sm text-muted-foreground">
            Lưu bản đang xem thành{" "}
            {documentId ? "phiên bản mới của tài liệu" : "tài liệu"} trước khi
            duyệt.
          </p>
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
