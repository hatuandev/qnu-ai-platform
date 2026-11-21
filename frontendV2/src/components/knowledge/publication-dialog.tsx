import {
  AlertCircle,
  CheckCircle2,
  Info,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
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
import { getReviewGate } from "@/api/documents/requests";
import type {
  DecisionPreviewRequest,
  DocumentSummaryResponse,
  ReviewGateResponse,
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

/**
 * Modal duy nhất duyệt và phát hành tài liệu:
 * Gộp toàn bộ luồng lưu phiên bản -> duyệt (approve) -> phát hành (publish) -> kích hoạt index.
 * Không yêu cầu nhập lý do bắt buộc, thông tin rà soát AI chỉ mang tính chất tham khảo.
 */
export function PublicationDialog({
  open,
  onOpenChange,
  workspaceId,
  collectionId,
  sourceTitle,
  compilationRunId,
  existingDocumentId,
  existingVersion,
  canRegister: _canRegister,
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
  const [documentId, setDocumentId] = useState<string | null>(
    existingVersion?.document_id ?? existingDocumentId ?? null,
  );
  const [versionId, setVersionId] = useState<string | null>(
    existingVersion?.version_id ?? null,
  );
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // API mutations
  const createDoc = useCreateCompiledDocumentMutation(
    workspaceId,
    collectionId,
  );
  const registerVersion = useRegisterCompiledDocumentVersionMutation(
    workspaceId,
    collectionId,
  );
  const previewDecision = useDecisionPreviewMutation(workspaceId, collectionId);
  const commitDecision = useCommitDecisionMutation(workspaceId, collectionId);

  // Queries
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

  const version = versionQuery.data;
  const gate = gateQuery.data;
  const isNoAiReview =
    (gateQuery.error as { code?: string } | null)?.code ===
    "publication_review_required";

  const handleApproveAndPublish = async () => {
    if (isProcessing) return;
    setIsProcessing(true);
    setError(null);

    try {
      // BƯỚC 1: Đảm bảo tài liệu & phiên bản đã được đăng ký
      let currentDocId = documentId;
      let currentVerId = versionId;
      let currentVersion: VersionResponse | undefined = version;

      if (!currentDocId || !currentVerId || !currentVersion) {
        const metadataSha = metadataQuery.data?.sha256;
        if (!metadataSha) {
          throw new Error(
            "Chưa nạp được thông tin tự nhận diện của nguồn. Vui lòng thử lại sau giây lát.",
          );
        }

        if (currentDocId) {
          const regRes = await registerVersion.mutateAsync({
            documentId: currentDocId,
            data: {
              compilation_run_id: compilationRunId,
              automatic_metadata_sha256: metadataSha,
            },
            idempotencyKey: `reg_ver_${currentDocId}_${compilationRunId}`,
          });
          currentVerId = regRes.version.id;
          currentVersion = regRes.version;
          setVersionId(currentVerId);
        } else {
          const createRes = await createDoc.mutateAsync({
            data: {
              document_key: `doc_${compilationRunId}`,
              title: sourceTitle,
              compilation_run_id: compilationRunId,
              automatic_metadata_sha256: metadataSha,
            },
            idempotencyKey: `reg_doc_${compilationRunId}`,
          });
          currentDocId = createRes.document.id;
          currentVerId = createRes.version.id;
          currentVersion = createRes.version;
          setDocumentId(currentDocId);
          setVersionId(currentVerId);
        }
      }

      // Nếu đã phát hành rồi, đóng modal
      if (currentVersion?.status === "published") {
        toast.info("Tài liệu đã ở trạng thái đã phát hành.");
        onOpenChange(false);
        return;
      }

      // BƯỚC 2: Duyệt (Approve) nếu phiên bản đang ở dạng draft
      if (!currentVersion || currentVersion.status === "draft") {
        let freshGate: ReviewGateResponse | null = null;
        try {
          freshGate = await getReviewGate(
            workspaceId,
            collectionId,
            currentDocId,
            currentVerId,
          );
        } catch (err: unknown) {
          const code = (err as { code?: string } | null)?.code;
          if (code !== "publication_review_required") {
            // Không chặn tiến trình
          }
        }

        const standardReason = "Duyệt và phát hành trực tiếp bởi người dùng.";
        let approvalPayload: DecisionPreviewRequest;

        if (freshGate?.findings && freshGate.findings.length > 0) {
          approvalPayload = {
            action: "approve",
            reason: standardReason,
            confirm_spelling_in_progress: true,
            review_ack: {
              review_id: freshGate.review_id,
              report_sha256: freshGate.report_sha256,
              confirmed_reviewed: true,
              retrieval_metadata_sha256:
                currentVersion?.retrieval_metadata_sha256,
              resolutions: freshGate.findings.map((item) => ({
                finding_id: item.finding_id,
                reason: "Đã đối chiếu và chấp nhận phát hành.",
                decision: "accepted_risk",
              })),
            },
          };
        } else if (freshGate) {
          approvalPayload = {
            action: "approve",
            reason: standardReason,
            confirm_spelling_in_progress: true,
            review_ack: {
              review_id: freshGate.review_id,
              report_sha256: freshGate.report_sha256,
              confirmed_reviewed: true,
              retrieval_metadata_sha256:
                currentVersion?.retrieval_metadata_sha256,
              resolutions: [],
            },
          };
        } else {
          // Chưa có báo cáo rà soát AI -> Bỏ qua review và duyệt trực tiếp
          approvalPayload = {
            action: "approve",
            reason: standardReason,
            confirm_spelling_in_progress: true,
            review_skip: {
              confirmed_skip: true,
              version_id: currentVerId,
              bundle_sha256: currentVersion?.bundle_sha256 || "",
              retrieval_metadata_sha256:
                currentVersion?.retrieval_metadata_sha256,
            },
          };
        }

        const approvePreviewRes = await previewDecision.mutateAsync({
          documentId: currentDocId,
          versionId: currentVerId,
          data: approvalPayload,
        });

        await commitDecision.mutateAsync({
          documentId: currentDocId,
          versionId: currentVerId,
          data: {
            preview_id: approvePreviewRes.id,
            preview_sha256: approvePreviewRes.preview_sha256,
          },
          idempotencyKey: `dec_appr_${approvePreviewRes.id}`,
        });
      }

      // BƯỚC 3: Phát hành (Publish)
      const publishPreviewRes = await previewDecision.mutateAsync({
        documentId: currentDocId,
        versionId: currentVerId,
        data: {
          action: "publish",
          reason: "Phát hành bản đã duyệt để phục vụ tra cứu.",
        },
      });

      await commitDecision.mutateAsync({
        documentId: currentDocId,
        versionId: currentVerId,
        data: {
          preview_id: publishPreviewRes.id,
          preview_sha256: publishPreviewRes.preview_sha256,
        },
        idempotencyKey: `dec_pub_${publishPreviewRes.id}`,
      });

      // BƯỚC 4: Thông báo thành công & đóng modal gọn gàng
      toast.success(
        "Đã duyệt và phát hành tài liệu thành công. Hệ thống đang tiến hành lập chỉ mục.",
      );

      const refetchedSummary = await summaryQuery.refetch();
      if (refetchedSummary.data) {
        onSuccess?.(refetchedSummary.data);
      }

      onOpenChange(false);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Có lỗi xảy ra khi duyệt và phát hành tài liệu.";
      setError(msg);
      toast.error(msg);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={isProcessing ? undefined : onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base text-foreground">
            <ShieldCheck className="size-5 text-primary shrink-0" />
            <span>Xác nhận duyệt & phát hành tài liệu</span>
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground pt-1">
            Xác nhận nội dung và đưa tài liệu vào kho tri thức để sẵn sàng phục
            vụ tra cứu và hội thoại.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2 text-xs">
          {/* Thông tin tên tài liệu */}
          <div className="rounded-lg border border-border/70 bg-card p-3 space-y-1">
            <span className="text-[11px] text-muted-foreground block font-medium">
              Tên tài liệu
            </span>
            <span className="text-xs font-semibold text-foreground block truncate">
              {sourceTitle.replace(/_/g, " ")}
            </span>
          </div>

          {/* Ghi chú thông tin rà soát AI & tiến trình ngầm (chỉ để tham khảo) */}
          <div className="rounded-lg border border-border/60 bg-muted/30 p-3 space-y-2">
            {gateQuery.isPending ? (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="size-3.5 animate-spin shrink-0" />
                <span>Đang kiểm tra trạng thái rà soát AI...</span>
              </div>
            ) : gate?.findings && gate.findings.length > 0 ? (
              <div className="flex items-start gap-2 text-primary">
                <CheckCircle2 className="size-4 shrink-0 mt-0.5" />
                <span>
                  Báo cáo rà soát AI ghi nhận {gate.findings.length} lưu ý đối
                  chiếu. Hệ thống sẽ tự động chấp nhận để hoàn tất phát hành.
                </span>
              </div>
            ) : gate ? (
              <div className="flex items-center gap-2 text-primary">
                <CheckCircle2 className="size-4 shrink-0" />
                <span>Báo cáo rà soát AI không ghi nhận bất thường.</span>
              </div>
            ) : isNoAiReview || gateQuery.error ? (
              <div className="flex items-start gap-2 text-muted-foreground">
                <Info className="size-4 shrink-0 mt-0.5 text-muted-foreground/80" />
                <span>
                  Tài liệu chưa qua rà soát AI tự động. Hệ thống sẽ ghi nhận
                  duyệt và phát hành trực tiếp.
                </span>
              </div>
            ) : null}

            {gate?.spelling_in_progress && (
              <div className="flex items-start gap-2 text-amber-700 dark:text-amber-400 pt-1 border-t border-border/40">
                <AlertCircle className="size-4 shrink-0 mt-0.5" />
                <span>
                  Đang chạy soát chính tả đa lượt ngầm (Lượt{" "}
                  {gate.spelling_details?.pass_number ?? 1}/
                  {gate.spelling_details?.total_passes ?? 2}). Việc duyệt sẽ
                  phát hành ngay bản nội dung hiện tại.
                </span>
              </div>
            )}
          </div>

          <p className="text-[11px] text-muted-foreground leading-relaxed">
            Sau khi bấm <strong>Đồng ý</strong>, hệ thống sẽ thực hiện toàn bộ
            các bước duyệt, phát hành và tự động đẩy vào hàng đợi lập chỉ mục
            vector.
          </p>

          {/* Thông báo lỗi nếu có */}
          {error && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-2.5 text-xs text-destructive"
            >
              <AlertCircle className="size-4 shrink-0 mt-0.5" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            size="sm"
            disabled={isProcessing}
            onClick={() => onOpenChange(false)}
          >
            Hủy
          </Button>
          <Button
            size="sm"
            disabled={isProcessing || (!versionId && metadataQuery.isPending)}
            onClick={handleApproveAndPublish}
          >
            {isProcessing ? (
              <>
                <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                <span>Đang duyệt & phát hành...</span>
              </>
            ) : (
              <>
                <ShieldCheck className="size-3.5 mr-1.5" />
                <span>Đồng ý duyệt & phát hành</span>
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
