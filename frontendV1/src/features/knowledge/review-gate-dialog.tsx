import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  FileCheck2,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useState } from "react";
import { ApiProblemError } from "@/app/api/v1";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { RetrievalAnnotation } from "@/features/rag/types";
import { FindingCard } from "./compilation-review-tab";
import { formatReviewVerdict } from "./compilation-schemas";
import {
  useCompiledVersionReviewGateQuery,
  useDecisionPreviewMutation,
} from "./publication-queries";
import { formatPublicationError } from "./publication-schemas";
import type {
  DecisionPreviewResponse,
  FindingResolutionInput,
} from "./publication-types";
import { RetrievalMetadataView } from "./retrieval-metadata-view";

export function ReviewGateDialog({
  workspaceId,
  collectionId,
  documentId,
  versionId,
  versionNo,
  retrievalMetadata,
  retrievalMetadataSha256,
  isOpen,
  onClose,
  onPreviewSuccess,
}: {
  workspaceId: string;
  collectionId: string;
  documentId: string;
  versionId: string;
  versionNo: number;
  /** Declared metadata of this exact version, as returned by the backend. */
  retrievalMetadata: RetrievalAnnotation[];
  /** Backend-computed digest; sent back verbatim, never typed by the reviewer. */
  retrievalMetadataSha256: string;
  isOpen: boolean;
  onClose: () => void;
  onPreviewSuccess: (preview: DecisionPreviewResponse) => void;
}) {
  const [confirmedReviewed, setConfirmedReviewed] = useState(false);
  const [confirmedMetadata, setConfirmedMetadata] = useState(false);
  const [overallReason, setOverallReason] = useState("");
  const [resolutions, setResolutions] = useState<
    Record<
      string,
      { decision: "accepted_risk" | "not_an_issue" | ""; reason: string }
    >
  >({});
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const reviewGateQuery = useCompiledVersionReviewGateQuery(
    workspaceId,
    collectionId,
    documentId,
    versionId,
    { enabled: isOpen },
  );

  const previewMutation = useDecisionPreviewMutation(
    workspaceId,
    collectionId,
    documentId,
    versionId,
  );

  const data = reviewGateQuery.data;

  // Initialize resolution state when review gate data loads
  useEffect(() => {
    if (data?.findings) {
      const initialResolutions: Record<
        string,
        { decision: "accepted_risk" | "not_an_issue" | ""; reason: string }
      > = {};
      for (const item of data.findings) {
        initialResolutions[item.finding_id] = {
          decision: "",
          reason: "",
        };
      }
      setResolutions(initialResolutions);
      setConfirmedReviewed(false);
      setConfirmedMetadata(false);
      setOverallReason("");
      setErrorBanner(null);
    }
  }, [data]);

  const handleResolutionDecisionChange = (
    findingId: string,
    decision: "accepted_risk" | "not_an_issue",
  ) => {
    setResolutions((prev) => ({
      ...prev,
      [findingId]: {
        ...prev[findingId],
        decision,
      },
    }));
  };

  const handleResolutionReasonChange = (findingId: string, reason: string) => {
    setResolutions((prev) => ({
      ...prev,
      [findingId]: {
        ...prev[findingId],
        reason,
      },
    }));
  };

  const findingsList = data?.findings ?? [];

  // A version that declares metadata needs its own explicit acknowledgement: the
  // backend compares the digest the reviewer confirmed against the stored one.
  const hasMetadata = retrievalMetadata.length > 0;
  const metadataAcknowledged = !hasMetadata || confirmedMetadata;

  // Validation
  const allFindingsResolved = findingsList.every((item) => {
    const res = resolutions[item.finding_id];
    return (
      res &&
      (res.decision === "accepted_risk" || res.decision === "not_an_issue") &&
      res.reason.trim().length >= 10 &&
      res.reason.trim().length <= 2000
    );
  });

  const canSubmit =
    confirmedReviewed &&
    metadataAcknowledged &&
    overallReason.trim().length >= 1 &&
    overallReason.trim().length <= 1000 &&
    allFindingsResolved &&
    !previewMutation.isPending;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorBanner(null);

    if (!data) return;

    if (!confirmedReviewed) {
      setErrorBanner("Bạn phải xác nhận đã xem và kiểm tra báo cáo rà soát.");
      return;
    }

    if (!metadataAcknowledged) {
      setErrorBanner(
        "Bạn phải xác nhận đã xem metadata truy xuất của phiên bản trước khi duyệt.",
      );
      return;
    }

    if (!overallReason.trim()) {
      setErrorBanner("Vui lòng nhập lý do quyết định duyệt.");
      return;
    }

    if (!allFindingsResolved) {
      setErrorBanner(
        "Cần giải trình đầy đủ tất cả các vấn đề (chọn quyết định và nhập lý do tối thiểu 10 ký tự cho từng mục).",
      );
      return;
    }

    const payloadResolutions: FindingResolutionInput[] = findingsList.map(
      (item) => {
        const res = resolutions[item.finding_id];
        return {
          finding_id: item.finding_id,
          decision: res.decision as "accepted_risk" | "not_an_issue",
          reason: res.reason.trim(),
        };
      },
    );

    try {
      const preview = await previewMutation.mutateAsync({
        input: {
          action: "approve",
          reason: overallReason.trim(),
          review_ack: {
            review_id: data.review_id,
            report_sha256: data.report_sha256,
            confirmed_reviewed: true,
            resolutions: payloadResolutions,
            // Exact digest from the version response. The reviewer never types it.
            ...(hasMetadata
              ? { retrieval_metadata_sha256: retrievalMetadataSha256 }
              : {}),
          },
        },
      });

      onClose();
      onPreviewSuccess(preview);
    } catch (err: unknown) {
      if (err instanceof ApiProblemError) {
        setErrorBanner(formatPublicationError(err.code, err.message));
        if (err.code === "publication_metadata_review_required") {
          // The version's metadata changed under us; force a fresh look.
          setConfirmedMetadata(false);
          void reviewGateQuery.refetch();
        }
      } else {
        setErrorBanner("Không thể tạo bản xem trước duyệt. Vui lòng thử lại.");
      }
    }
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => !previewMutation.isPending && !open && onClose()}
    >
      <DialogContent className="sm:max-w-2xl max-h-[min(840px,calc(100vh-2rem))] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="size-8 rounded-lg bg-info/10 text-info flex items-center justify-center shrink-0">
              <ShieldCheck className="size-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-semibold">
                Cổng rà soát duyệt phiên bản v{versionNo}
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Kiểm tra báo cáo rà soát độc lập và giải trình các vấn đề trước
                khi chuyển trạng thái sang đã duyệt.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {reviewGateQuery.isLoading ? (
          <div className="space-y-3 py-6">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : reviewGateQuery.isError ? (
          <div className="space-y-4 py-4">
            <Alert variant="destructive">
              <AlertCircle className="size-4" />
              <AlertDescription className="text-xs">
                {reviewGateQuery.error instanceof ApiProblemError
                  ? formatPublicationError(
                      reviewGateQuery.error.code,
                      reviewGateQuery.error.message,
                    )
                  : "Không thể tải báo cáo rà soát cho phiên bản này."}
              </AlertDescription>
            </Alert>
            <div className="flex justify-end gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={onClose}
                className="text-xs"
              >
                Đóng
              </Button>
              <Button
                size="sm"
                variant="default"
                onClick={() => void reviewGateQuery.refetch()}
                className="text-xs"
              >
                Thử lại
              </Button>
            </div>
          </div>
        ) : !data ? null : (
          <form onSubmit={handleSubmit} className="space-y-4 pt-2">
            {errorBanner && (
              <Alert variant="destructive" className="py-2.5">
                <AlertCircle className="size-4" />
                <AlertDescription className="text-xs">
                  {errorBanner}
                </AlertDescription>
              </Alert>
            )}

            {/* Verdict and Review Summary */}
            <div className="rounded-lg border bg-card p-3.5 space-y-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-muted-foreground">
                    Kết luận mô hình:
                  </span>
                  <Badge
                    variant={
                      data.verdict === "no_issues_detected"
                        ? "default"
                        : data.verdict === "needs_attention"
                          ? "destructive"
                          : "secondary"
                    }
                    className="text-xs font-semibold capitalize"
                  >
                    {formatReviewVerdict(data.verdict).label}
                  </Badge>
                </div>
                <div className="text-[11px] font-mono text-muted-foreground">
                  Review ID: {data.review_id}
                </div>
              </div>

              <p className="text-[11px] text-muted-foreground bg-muted/30 p-2 rounded">
                Kết luận của mô hình mang tính chất tham khảo kỹ thuật. Người
                duyệt có trách nhiệm xem xét, giải trình từng phát hiện và đưa
                ra quyết định hành chính cuối cùng.
              </p>

              <div className="text-[11px] font-mono text-muted-foreground truncate">
                Report SHA-256: {data.report_sha256}
              </div>
            </div>

            {/*
              Metadata review comes before the report acknowledgement because the
              backend rejects the ack when the digest was not explicitly confirmed.
            */}
            {hasMetadata ? (
              <div className="space-y-2">
                <RetrievalMetadataView
                  annotations={retrievalMetadata}
                  sha256={retrievalMetadataSha256}
                />
                <div className="flex items-start space-x-2.5 rounded-lg border border-warning/30 bg-warning/5 p-3">
                  <Checkbox
                    id="confirm-metadata"
                    checked={confirmedMetadata}
                    onCheckedChange={(checked) =>
                      setConfirmedMetadata(Boolean(checked))
                    }
                    className="mt-0.5"
                  />
                  <div className="space-y-1 leading-none">
                    <label
                      htmlFor="confirm-metadata"
                      className="text-xs font-medium text-foreground cursor-pointer select-none"
                    >
                      Tôi xác nhận đã đọc và đối chiếu metadata truy xuất cùng
                      căn cứ trích dẫn của phiên bản này{" "}
                      <span className="text-destructive">*</span>
                    </label>
                    <p className="text-[11px] text-muted-foreground">
                      Hệ thống gửi kèm mã băm metadata của phiên bản khi bạn xác
                      nhận. Nếu metadata thay đổi, bước duyệt sẽ bị từ chối và
                      bạn phải xem lại.
                    </p>
                  </div>
                </div>
              </div>
            ) : null}

            {/* Mandatory Checkbox */}
            <div className="flex items-start space-x-2.5 rounded-lg border border-primary/20 bg-primary/5 p-3">
              <Checkbox
                id="confirm-review"
                checked={confirmedReviewed}
                onCheckedChange={(checked) =>
                  setConfirmedReviewed(Boolean(checked))
                }
                className="mt-0.5"
              />
              <div className="space-y-1 leading-none">
                <label
                  htmlFor="confirm-review"
                  className="text-xs font-medium text-foreground cursor-pointer select-none"
                >
                  Tôi xác nhận đã đọc và xem xét đầy đủ nội dung báo cáo rà soát
                  của phiên bản này <span className="text-destructive">*</span>
                </label>
                <p className="text-[11px] text-muted-foreground">
                  Bắt buộc xác nhận để kích hoạt bước giải trình và xem trước
                  quyết định duyệt.
                </p>
              </div>
            </div>

            {/* Findings Resolution List */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <FileCheck2 className="size-3.5 text-primary" />
                  Giải trình các vấn đề phát hiện ({findingsList.length})
                </Label>
                {findingsList.length > 0 && (
                  <span className="text-[11px] text-muted-foreground">
                    Tất cả các mục đều bắt buộc giải trình
                  </span>
                )}
              </div>

              {findingsList.length === 0 ? (
                <div className="p-4 rounded-lg border bg-muted/20 text-center space-y-1">
                  <CheckCircle2 className="size-5 text-success mx-auto" />
                  <p className="text-xs font-medium text-foreground">
                    Không có vấn đề nào được ghi nhận
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    Báo cáo rà soát không phát hiện lỗi sai lệch hay xung đột dữ
                    kiện.
                  </p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[340px] overflow-y-auto pr-1">
                  {findingsList.map((item, index) => {
                    const res = resolutions[item.finding_id] ?? {
                      decision: "",
                      reason: "",
                    };
                    const finding = item.finding;
                    const isResolved =
                      Boolean(res.decision) && res.reason.trim().length >= 10;

                    return (
                      <Card
                        key={item.finding_id}
                        className={`p-3.5 space-y-3 text-xs border transition-colors ${
                          isResolved
                            ? "border-border bg-card"
                            : "border-warning/40 bg-warning/5"
                        }`}
                      >
                        {/* Finding header */}
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="font-semibold text-xs text-foreground">
                              #{index + 1}. Vấn đề
                            </span>
                          </div>
                          <span className="font-mono text-[10px] text-muted-foreground shrink-0">
                            ID: {item.finding_id.slice(0, 12)}...
                          </span>
                        </div>

                        <FindingCard finding={finding} index={index + 1} />

                        {/* Resolution Decision */}
                        <div className="space-y-1.5 pt-2 border-t">
                          <Label className="text-[11px] font-medium text-foreground">
                            Quyết định xử lý{" "}
                            <span className="text-destructive">*</span>
                          </Label>
                          <RadioGroup
                            value={res.decision}
                            onValueChange={(val) =>
                              handleResolutionDecisionChange(
                                item.finding_id,
                                val as "accepted_risk" | "not_an_issue",
                              )
                            }
                            className="flex flex-col sm:flex-row gap-2"
                          >
                            <label
                              htmlFor={`dec-risk-${item.finding_id}`}
                              className={`flex items-center gap-2 p-2 rounded-md border text-xs cursor-pointer flex-1 ${
                                res.decision === "accepted_risk"
                                  ? "border-primary bg-primary/5 font-medium"
                                  : "border-border hover:bg-muted/30"
                              }`}
                            >
                              <RadioGroupItem
                                value="accepted_risk"
                                id={`dec-risk-${item.finding_id}`}
                              />
                              <span>Chấp nhận rủi ro</span>
                            </label>

                            <label
                              htmlFor={`dec-noissue-${item.finding_id}`}
                              className={`flex items-center gap-2 p-2 rounded-md border text-xs cursor-pointer flex-1 ${
                                res.decision === "not_an_issue"
                                  ? "border-primary bg-primary/5 font-medium"
                                  : "border-border hover:bg-muted/30"
                              }`}
                            >
                              <RadioGroupItem
                                value="not_an_issue"
                                id={`dec-noissue-${item.finding_id}`}
                              />
                              <span>Không phải vấn đề</span>
                            </label>
                          </RadioGroup>
                        </div>

                        {/* Resolution Reason */}
                        <div className="space-y-1">
                          <div className="flex items-center justify-between text-[11px]">
                            <Label
                              htmlFor={`reason-${item.finding_id}`}
                              className="font-medium"
                            >
                              Lý do giải trình (10 - 2000 ký tự){" "}
                              <span className="text-destructive">*</span>
                            </Label>
                            <span
                              className={`${
                                res.reason.trim().length >= 10
                                  ? "text-muted-foreground"
                                  : "text-destructive font-medium"
                              }`}
                            >
                              {res.reason.trim().length}/2000
                            </span>
                          </div>
                          <Textarea
                            id={`reason-${item.finding_id}`}
                            value={res.reason}
                            onChange={(e) =>
                              handleResolutionReasonChange(
                                item.finding_id,
                                e.target.value,
                              )
                            }
                            placeholder="Nêu rõ căn cứ tại sao chấp nhận hoặc tại sao đây không phải vấn đề..."
                            rows={2}
                            maxLength={2000}
                            className="text-xs resize-none"
                          />
                        </div>
                      </Card>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Overall Decision Reason */}
            <div className="space-y-1.5 pt-2 border-t">
              <div className="flex items-center justify-between text-xs">
                <Label
                  htmlFor="overall-reason"
                  className="font-semibold text-foreground"
                >
                  Lý do quyết định duyệt{" "}
                  <span className="text-destructive">*</span>
                </Label>
                <span className="text-[11px] text-muted-foreground">
                  {overallReason.trim().length}/1000
                </span>
              </div>
              <Textarea
                id="overall-reason"
                value={overallReason}
                onChange={(e) => setOverallReason(e.target.value)}
                placeholder="Nhập nhận định chung và căn cứ phê duyệt phiên bản này..."
                rows={2}
                maxLength={1000}
                className="text-xs resize-none"
              />
            </div>

            <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onClose}
                disabled={previewMutation.isPending}
                className="text-xs"
              >
                Hủy
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={!canSubmit}
                className="text-xs gap-1.5"
              >
                {previewMutation.isPending ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" />
                    <span>Đang tạo bản xem trước...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="size-3.5" />
                    <span>Xem trước duyệt</span>
                    <ArrowRight className="size-3.5" />
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
