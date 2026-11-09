import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle2,
  Circle,
  ClipboardList,
  Loader2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError, v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTimeValue } from "@/lib/date-utils";
import { compilationKeys } from "./compilation-queries";
import { getCompilationProgress } from "./compilation-requests";
import {
  useCancelPreparationIntentMutation,
  useCreatePreparationIntentMutation,
  usePreparationIntentQuery,
  usePreparationIntentsQuery,
} from "./preparation-queries";
import {
  formatElapsedDuration,
  formatPreparationError,
  isPreparationActive,
  preparationModeLabel,
  preparationPolicySummary,
  preparationStatusHint,
  preparationStatusLabel,
  preparationStatusVariant,
  shortHash,
} from "./preparation-schemas";
import type {
  PreparationIntent,
  PreparationRequestInput,
  PreparationStatus,
} from "./preparation-types";
import { generateIdempotencyKey } from "./schemas";

const PREPARATION_STEPS = [
  "Ghi nhận yêu cầu",
  "Đọc nội dung nguồn",
  "Tạo bản nháp có dẫn chứng",
] as const;

function activeStepIndex(status: PreparationStatus): number | null {
  switch (status) {
    case "queued":
      return 0;
    case "waiting_ocr":
      return 1;
    case "compiling":
      return 2;
    default:
      return null;
  }
}

function completedStepCount(
  status: PreparationStatus,
  hasCompilation: boolean,
): number {
  if (status === "ready") {
    return PREPARATION_STEPS.length;
  }
  const active = activeStepIndex(status);
  if (active !== null) {
    return active;
  }
  // A terminal intent without a compilation proves only that the request was
  // recorded; a compilation run proves the source was read.
  return hasCompilation ? 2 : 1;
}

export function PreparationDialog({
  workspaceId,
  collectionId,
  sourceId,
  sourceTitle,
  revisionId,
  revisionNo,
  revisionSha256,
  savedRunId,
  savedTextVersion,
  isOpen,
  onClose,
}: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  sourceTitle: string;
  revisionId: string;
  revisionNo: number;
  revisionSha256: string;
  savedRunId: string | null;
  savedTextVersion: number;
  isOpen: boolean;
  onClose: () => void;
}) {
  const [idempotencyKey, setIdempotencyKey] = useState(generateIdempotencyKey);
  const [createdIntentId, setCreatedIntentId] = useState<string | null>(null);
  const [isRestarting, setIsRestarting] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      setCreatedIntentId(null);
      setIsRestarting(false);
      return;
    }
    setIdempotencyKey(generateIdempotencyKey());
    setCreatedIntentId(null);
    setIsRestarting(false);
  }, [isOpen]);

  const intentsQuery = usePreparationIntentsQuery(
    workspaceId,
    collectionId,
    sourceId,
    20,
    { enabled: isOpen },
  );
  const activeIntent = useMemo(
    () => (intentsQuery.data ?? []).find(isPreparationActive) ?? null,
    [intentsQuery.data],
  );
  // Server state survives reload: reopen on the latest (or still running) intent.
  const knownIntent = activeIntent ?? intentsQuery.data?.[0] ?? null;
  const intentId =
    createdIntentId ?? (isRestarting ? null : (knownIntent?.id ?? null));
  const intentQuery = usePreparationIntentQuery(
    workspaceId,
    collectionId,
    intentId,
    { enabled: isOpen && Boolean(intentId) },
  );
  const intent = intentQuery.data ?? knownIntent;

  const createMutation = useCreatePreparationIntentMutation(
    workspaceId,
    collectionId,
    sourceId,
  );
  const cancelMutation = useCancelPreparationIntentMutation(
    workspaceId,
    collectionId,
    sourceId,
  );

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!revisionId) return;

    const input: PreparationRequestInput = {
      mode: "auto",
      revision_id: revisionId,
      ocr_run_id: savedRunId,
      text_version: savedRunId ? savedTextVersion : 0,
    };

    try {
      const outcome = await createMutation.mutateAsync({
        input,
        idempotencyKey,
      });
      setCreatedIntentId(outcome.intent.id);
      setIsRestarting(false);
      setIdempotencyKey(generateIdempotencyKey());
      toast.success(
        outcome.created
          ? "Đã ghi nhận. Hệ thống đang chuẩn bị ở nền."
          : "Đã mở lại yêu cầu chuẩn bị hiện có.",
      );
    } catch (error: unknown) {
      toast.error(
        error instanceof ApiProblemError
          ? formatPreparationError(error.code)
          : "Không thể gửi yêu cầu chuẩn bị nội dung.",
      );
    }
  };

  const handleCancel = async () => {
    if (!intentId || cancelMutation.isPending) return;
    try {
      const updated = await cancelMutation.mutateAsync(intentId);
      // Keep pointing at the intent the user acted on: if it finished first,
      // the server returns that terminal state instead of cancelling it.
      setCreatedIntentId(updated.id);
      setIsRestarting(false);
      setIdempotencyKey(generateIdempotencyKey());
      toast.info(
        updated.status === "cancelled"
          ? "Đã dừng yêu cầu. Hệ thống không chạy bước kế tiếp."
          : "Yêu cầu đã kết thúc trước khi dừng; trạng thái thật hiển thị bên dưới.",
      );
    } catch (error: unknown) {
      toast.error(
        error instanceof ApiProblemError
          ? formatPreparationError(error.code)
          : "Không thể dừng yêu cầu chuẩn bị.",
      );
    }
  };

  const handleNewRequest = () => {
    setCreatedIntentId(null);
    setIsRestarting(true);
    setIdempotencyKey(generateIdempotencyKey());
  };

  const isActive = isPreparationActive(intent);
  const isReady = intent?.status === "ready";
  const canRetry =
    intent?.status === "failed" ||
    intent?.status === "uncertain" ||
    intent?.status === "cancelled";
  const savedTextLabel =
    savedTextVersion > 0
      ? `Bản đã lưu v${savedTextVersion}`
      : savedRunId
        ? "Bản đọc gốc v0"
        : "Chưa đọc — hệ thống sẽ đọc trước";

  const statusView = intentId ? (
    intent ? (
      <PreparationStatusView
        intent={intent}
        workspaceId={workspaceId}
        collectionId={collectionId}
      />
    ) : intentQuery.isError ? (
      <Alert variant="destructive" className="py-2.5">
        <AlertCircle className="size-4" />
        <AlertTitle className="text-xs">
          Không đọc được trạng thái yêu cầu
        </AlertTitle>
        <AlertDescription className="text-xs">
          <p>
            Yêu cầu vẫn được lưu trên máy chủ. Hãy thử lại; nếu quyền truy cập
            vừa thay đổi, bạn cần liên hệ quản trị workspace.
          </p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="mt-2 h-7 text-xs"
            onClick={() => void intentQuery.refetch()}
          >
            Thử lại
          </Button>
        </AlertDescription>
      </Alert>
    ) : (
      <div className="space-y-2">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-16 w-full" />
      </div>
    )
  ) : null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg max-h-[min(760px,calc(100dvh-2rem))] flex flex-col p-0 gap-0">
        <DialogHeader className="p-4 sm:p-5 border-b bg-muted/20">
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <ClipboardList className="size-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-semibold">
                Chuẩn bị nội dung
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Từ bản đã lưu trên máy chủ, tạo bản nháp có dẫn chứng để bạn
                duyệt.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {intentId ? (
          <>
            <div className="flex-1 min-h-0 overflow-y-auto p-4 text-xs sm:p-5">
              {statusView}
            </div>
            <DialogFooter className="p-3 sm:p-4 border-t bg-card flex flex-wrap items-center justify-between gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 text-xs"
                onClick={onClose}
              >
                Đóng
              </Button>
              <div className="flex items-center gap-2">
                {isActive ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs"
                    disabled={cancelMutation.isPending}
                    onClick={() => void handleCancel()}
                  >
                    {cancelMutation.isPending ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : null}
                    Dừng
                  </Button>
                ) : null}
                {canRetry ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs"
                    onClick={handleNewRequest}
                  >
                    Chuẩn bị lại
                  </Button>
                ) : null}
                {isReady && intent?.compilation_run_id ? (
                  <Button asChild size="sm" className="h-8 text-xs gap-1.5">
                    <Link
                      to="/workspaces/$workspaceId/collections/$collectionId/compilations/$runId"
                      params={{
                        workspaceId,
                        collectionId,
                        runId: intent.compilation_run_id,
                      }}
                      onClick={onClose}
                    >
                      Mở bản nháp
                      <ArrowRight className="size-3.5" />
                    </Link>
                  </Button>
                ) : null}
              </div>
            </DialogFooter>
          </>
        ) : intentsQuery.isLoading ? (
          <>
            <div className="flex-1 min-h-0 space-y-2 p-4 sm:p-5">
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-24 w-full" />
            </div>
            <DialogFooter className="p-3 sm:p-4 border-t bg-card flex items-center justify-end">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 text-xs"
                onClick={onClose}
              >
                Đóng
              </Button>
            </DialogFooter>
          </>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="flex-1 flex flex-col min-h-0"
          >
            <div className="flex-1 space-y-4 overflow-y-auto p-4 text-xs sm:p-5">
              <div className="space-y-1.5">
                <p className="text-xs font-semibold">Nguồn sẽ dùng</p>
                <dl className="space-y-1 text-xs">
                  <div className="flex justify-between gap-3">
                    <dt className="text-muted-foreground">Tài liệu</dt>
                    <dd className="min-w-0 truncate font-medium text-foreground">
                      {sourceTitle}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-muted-foreground">Tệp</dt>
                    <dd className="font-mono text-[11px]">
                      v{revisionNo} · {shortHash(revisionSha256)}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-muted-foreground">Văn bản</dt>
                    <dd>{savedTextLabel}</dd>
                  </div>
                </dl>
              </div>

              <div className="space-y-1 pt-3 border-t">
                <p className="text-xs font-semibold">Cách chuẩn bị</p>
                <p className="text-xs text-muted-foreground">
                  Hệ thống tự chọn cách phù hợp, model và ngân sách theo chính
                  sách của đơn vị. Bản nguồn được giữ nguyên; AI chỉ bổ sung khi
                  cần và luôn kèm dẫn chứng.
                </p>
              </div>

              <div className="space-y-1 pt-3 border-t text-xs text-muted-foreground">
                <p className="font-semibold text-foreground">Khi xác nhận</p>
                <ul className="list-disc space-y-0.5 pl-4">
                  <li>
                    Hệ thống dùng đúng tệp v{revisionNo} và bản văn bản đã lưu.
                  </li>
                  <li>
                    Chỉ tạo bản nháp để bạn xem và sửa; không tự đăng ký, duyệt
                    hay xuất bản.
                  </li>
                  <li>
                    Có thể đóng hộp thoại; tác vụ chạy ở nền và trạng thái được
                    lấy lại từ máy chủ.
                  </li>
                </ul>
              </div>
            </div>

            <DialogFooter className="p-3 sm:p-4 border-t bg-card flex items-center justify-between gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 text-xs"
                onClick={onClose}
                disabled={createMutation.isPending}
              >
                Hủy
              </Button>
              <Button
                type="submit"
                size="sm"
                className="h-8 text-xs gap-1.5"
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" />
                    <span>Đang gửi...</span>
                  </>
                ) : (
                  <>
                    <ClipboardList className="size-3.5" />
                    <span>Chuẩn bị nội dung</span>
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

function PreparationStatusView({
  intent,
  workspaceId,
  collectionId,
}: {
  intent: PreparationIntent;
  workspaceId: string;
  collectionId: string;
}) {
  const isActive = isPreparationActive(intent);
  const isReady = intent.status === "ready";
  const isFailed = intent.status === "failed" || intent.status === "uncertain";
  const elapsed = formatElapsedDuration(
    intent.started_at ?? intent.created_at,
    intent.finished_at,
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Badge
          variant={preparationStatusVariant(intent.status)}
          className="gap-1.5"
        >
          {isActive ? <Loader2 className="size-3 animate-spin" /> : null}
          {preparationStatusLabel(intent.status)}
        </Badge>
        <span className="text-[11px] text-muted-foreground">
          Tệp v{intent.revision_no} · {shortHash(intent.revision_sha256)}
        </span>
      </div>

      <p className="text-xs text-muted-foreground">
        {preparationStatusHint(intent.status)}
      </p>

      <PreparationSteps
        status={intent.status}
        hasCompilation={Boolean(intent.compilation_run_id)}
      />

      <dl className="space-y-1 text-xs">
        <div className="flex justify-between gap-3">
          <dt className="text-muted-foreground">Cách chuẩn bị</dt>
          <dd>{preparationModeLabel(intent.mode)}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted-foreground">Chính sách</dt>
          <dd className="max-w-[70%] text-right text-muted-foreground">
            {preparationPolicySummary(intent.policy)}
          </dd>
        </div>
        {intent.reused ? (
          <div className="flex justify-between gap-3">
            <dt className="text-muted-foreground">Kết quả</dt>
            <dd className="text-right">
              Dùng lại bản nháp đã có cho đúng nguồn và chính sách
            </dd>
          </div>
        ) : null}
        <div className="flex justify-between gap-3">
          <dt className="text-muted-foreground">Văn bản</dt>
          <dd>
            {intent.text_version > 0
              ? `Bản đã lưu v${intent.text_version}`
              : "Bản đọc gốc v0"}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted-foreground">Gửi lúc</dt>
          <dd>{formatDateTimeValue(intent.created_at)}</dd>
        </div>
        {elapsed ? (
          <div className="flex justify-between gap-3">
            <dt className="text-muted-foreground">
              {intent.finished_at ? "Thời gian chạy" : "Đã chạy"}
            </dt>
            <dd>{elapsed}</dd>
          </div>
        ) : null}
      </dl>

      {intent.status === "compiling" && intent.compilation_run_id ? (
        <PreparationPartProgress
          workspaceId={workspaceId}
          collectionId={collectionId}
          runId={intent.compilation_run_id}
        />
      ) : null}

      {isReady ? (
        <Alert variant="success" className="py-2.5">
          <CheckCircle2 className="size-4" />
          <AlertTitle className="text-xs">Bản nháp đã sẵn sàng</AlertTitle>
          <AlertDescription className="text-xs">
            Mở bản nháp để xem nội dung, chỗ cần chú ý và gửi duyệt. Hệ thống
            không tự đăng ký hay xuất bản.
          </AlertDescription>
        </Alert>
      ) : null}

      {isFailed ? (
        <Alert variant="destructive" className="py-2.5">
          <AlertCircle className="size-4" />
          <AlertTitle className="text-xs">
            {preparationStatusLabel(intent.status)}
          </AlertTitle>
          <AlertDescription className="text-xs">
            <p>{formatPreparationError(intent.error_code)}</p>
            {intent.error_code ? (
              <details className="mt-1 text-[11px]">
                <summary className="cursor-pointer select-none">
                  Chi tiết kỹ thuật
                </summary>
                <span className="font-mono">{intent.error_code}</span>
              </details>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}

      {isActive ? (
        <p className="text-[11px] text-muted-foreground">
          Dừng chỉ ngăn bước kế tiếp; phần đã gửi tới nhà cung cấp có thể vẫn
          hoàn tất. Bạn có thể đóng hộp thoại, yêu cầu vẫn chạy ở nền.
        </p>
      ) : null}
    </div>
  );
}

function PreparationSteps({
  status,
  hasCompilation,
}: {
  status: PreparationStatus;
  hasCompilation: boolean;
}) {
  const completed = completedStepCount(status, hasCompilation);
  const isRunning = activeStepIndex(status) !== null;
  const isHalted = status === "failed" || status === "uncertain";
  return (
    <ol aria-label="Các bước chuẩn bị" className="space-y-1.5">
      {PREPARATION_STEPS.map((label, index) => {
        const isDone = index < completed;
        const isCurrent = isRunning && index === completed;
        const isFault = isHalted && index === completed;
        return (
          <li
            key={label}
            aria-current={isCurrent ? "step" : undefined}
            className="flex items-center gap-2"
          >
            {isDone ? (
              <Check className="size-3.5 text-success" aria-hidden />
            ) : isFault ? (
              <AlertCircle className="size-3.5 text-destructive" aria-hidden />
            ) : isCurrent ? (
              <Loader2
                className="size-3.5 animate-spin text-primary motion-reduce:animate-none"
                aria-hidden
              />
            ) : (
              <Circle className="size-3.5 text-muted-foreground" aria-hidden />
            )}
            <span
              className={
                isDone || isCurrent
                  ? "text-xs"
                  : "text-xs text-muted-foreground"
              }
            >
              {label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function PreparationPartProgress({
  workspaceId,
  collectionId,
  runId,
}: {
  workspaceId: string;
  collectionId: string;
  runId: string;
}) {
  const { sessionId } = useV1Auth();
  const query = useQuery({
    queryKey: [
      ...compilationKeys.run(workspaceId, collectionId, runId, sessionId),
      "progress",
    ],
    queryFn: ({ signal }) =>
      getCompilationProgress(v1Client, workspaceId, collectionId, runId, {
        signal,
      }),
    retry: false,
    refetchInterval: (query) =>
      query.state.data?.status === "queued" ||
      query.state.data?.status === "running"
        ? 3000
        : false,
  });
  const data = query.data;
  if (query.isError) {
    return (
      <p className="text-[11px] text-muted-foreground">
        Chưa đọc được tiến độ từng phần. Tác vụ chưa được xác nhận dừng.
      </p>
    );
  }
  if (!data || data.total <= 0) return null;
  const details = [
    `${data.completed}/${data.total} phần xong`,
    data.running > 0 ? `${data.running} đang chạy` : null,
    data.failed > 0 ? `${data.failed} lỗi` : null,
    data.uncertain > 0 ? `${data.uncertain} chưa xác định` : null,
  ].filter((item): item is string => item !== null);
  return (
    <div className="space-y-1 rounded-lg border bg-muted/30 px-3 py-2">
      <p role="status" className="text-xs">
        {details.join(" · ")}
      </p>
      {data.latest_output_partial ? (
        <p className="text-[11px] text-warning">
          Bản nháp hiện có còn phần chưa hoàn tất.
        </p>
      ) : null}
    </div>
  );
}
