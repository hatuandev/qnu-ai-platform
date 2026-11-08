import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  Loader2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ConsumerModelBudgetNotice } from "@/features/modelops/capacity-badge";
import { useCatalogQuery } from "@/features/modelops/queries";
import { formatDateTimeValue } from "@/lib/date-utils";
import {
  useCancelPreparationIntentMutation,
  useCreatePreparationIntentMutation,
  usePreparationIntentQuery,
  usePreparationIntentsQuery,
} from "./preparation-queries";
import {
  formatPreparationError,
  isPreparationActive,
  preparationStatusHint,
  preparationStatusLabel,
  preparationStatusVariant,
  shortHash,
} from "./preparation-schemas";
import type {
  PreparationIntent,
  PreparationMode,
  PreparationRequestInput,
} from "./preparation-types";
import { generateIdempotencyKey } from "./schemas";

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
  const [mode, setMode] = useState<PreparationMode>("source");
  const [providerId, setProviderId] = useState("default");
  const [maxOutputTokens, setMaxOutputTokens] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState(generateIdempotencyKey);
  const [createdIntentId, setCreatedIntentId] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setCreatedIntentId(null);
      return;
    }
    setMode("source");
    setProviderId("default");
    setMaxOutputTokens("");
    setIdempotencyKey(generateIdempotencyKey());
    setCreatedIntentId(null);
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
  const intentId = createdIntentId ?? activeIntent?.id ?? null;
  const intentQuery = usePreparationIntentQuery(
    workspaceId,
    collectionId,
    intentId,
    { enabled: isOpen && Boolean(intentId) },
  );
  const intent = intentQuery.data ?? activeIntent;

  const catalogQuery = useCatalogQuery(workspaceId, {
    enabled: isOpen && mode === "ai" && !intentId,
  });
  const chatProviders = useMemo(
    () =>
      (catalogQuery.data ?? []).filter((p) => p.capabilities.includes("chat")),
    [catalogQuery.data],
  );
  const defaultChatProvider = chatProviders.find((p) =>
    p.default_capabilities?.includes("chat"),
  );

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
      mode,
      revision_id: revisionId,
      ocr_run_id: savedRunId,
      text_version: savedRunId ? savedTextVersion : 0,
      ...(mode === "ai"
        ? {
            provider_id: providerId === "default" ? null : providerId,
            max_output_tokens: maxOutputTokens ? Number(maxOutputTokens) : null,
          }
        : {}),
    };

    try {
      const outcome = await createMutation.mutateAsync({
        input,
        idempotencyKey,
      });
      setCreatedIntentId(outcome.intent.id);
      setIdempotencyKey(generateIdempotencyKey());
      toast.success(
        outcome.created
          ? "Đã ghi nhận yêu cầu chuẩn bị nội dung."
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
      await cancelMutation.mutateAsync(intentId);
      setCreatedIntentId(null);
      setIdempotencyKey(generateIdempotencyKey());
      toast.info("Đã hủy yêu cầu. Hệ thống không chạy bước kế tiếp.");
    } catch (error: unknown) {
      toast.error(
        error instanceof ApiProblemError
          ? formatPreparationError(error.code)
          : "Không thể hủy yêu cầu chuẩn bị.",
      );
    }
  };

  const handleNewRequest = () => {
    setCreatedIntentId(null);
    setIdempotencyKey(generateIdempotencyKey());
  };

  const isActive = isPreparationActive(intent);
  const isReady = intent?.status === "ready";
  const canRetry =
    intent?.status === "failed" ||
    intent?.status === "uncertain" ||
    intent?.status === "cancelled";
  const aiUnavailable =
    mode === "ai" && catalogQuery.isSuccess && chatProviders.length === 0;
  const savedTextLabel =
    savedTextVersion > 0
      ? `Bản đã lưu v${savedTextVersion}`
      : savedRunId
        ? "Bản đọc gốc v0"
        : "Chưa đọc — hệ thống sẽ đọc trước";

  const statusView = intentId ? (
    intent ? (
      <PreparationStatusView intent={intent} />
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
                    Hủy yêu cầu
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

              <div className="space-y-2 pt-3 border-t">
                <p className="text-xs font-semibold">Cách chuẩn bị</p>
                <RadioGroup
                  value={mode}
                  onValueChange={(value) => {
                    setMode(value as PreparationMode);
                    setIdempotencyKey(generateIdempotencyKey());
                  }}
                  className="space-y-2.5"
                >
                  <div className="flex items-start gap-2.5">
                    <RadioGroupItem
                      id="prep-mode-source"
                      value="source"
                      className="mt-0.5"
                    />
                    <div className="space-y-0.5">
                      <Label
                        htmlFor="prep-mode-source"
                        className="text-xs font-medium"
                      >
                        Giữ nguyên nguồn
                      </Label>
                      <p className="text-xs text-muted-foreground">
                        Dựng cấu trúc và bảng từ văn bản đã đọc, không gọi AI.
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <RadioGroupItem
                      id="prep-mode-ai"
                      value="ai"
                      className="mt-0.5"
                    />
                    <div className="space-y-0.5">
                      <Label
                        htmlFor="prep-mode-ai"
                        className="text-xs font-medium"
                      >
                        Bổ sung bằng AI
                      </Label>
                      <p className="text-xs text-muted-foreground">
                        AI gợi ý cấu trúc và metadata có dẫn chứng. Dùng
                        ModelOps và quota; nội dung nguồn vẫn được giữ.
                      </p>
                    </div>
                  </div>
                </RadioGroup>
              </div>

              {mode === "ai" ? (
                <div className="space-y-2 pl-6">
                  <div className="space-y-1">
                    <Label
                      htmlFor="prep-provider"
                      className="text-[11px] text-muted-foreground"
                    >
                      Model (chat)
                    </Label>
                    <Select
                      value={providerId}
                      onValueChange={(value) => {
                        setProviderId(value);
                        setIdempotencyKey(generateIdempotencyKey());
                      }}
                    >
                      <SelectTrigger id="prep-provider" className="h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="default" className="text-xs">
                          Theo mặc định workspace
                        </SelectItem>
                        {chatProviders.map((provider) => (
                          <SelectItem
                            key={provider.id}
                            value={provider.id}
                            className="text-xs"
                          >
                            {provider.name} ({provider.model_name})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <ConsumerModelBudgetNotice
                      model={chatProviders.find((p) => p.id === providerId)}
                      defaultModel={defaultChatProvider}
                      isDefaultSelection={providerId === "default"}
                      capability="chat"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label
                      htmlFor="prep-max-tokens"
                      className="text-[11px] text-muted-foreground"
                    >
                      Giới hạn output tokens (tùy chọn)
                    </Label>
                    <Input
                      id="prep-max-tokens"
                      type="number"
                      min={1}
                      className="h-8 text-xs font-mono"
                      placeholder="Mặc định theo model"
                      value={maxOutputTokens}
                      onChange={(event) => {
                        setMaxOutputTokens(event.target.value);
                        setIdempotencyKey(generateIdempotencyKey());
                      }}
                    />
                  </div>
                  {aiUnavailable ? (
                    <p className="text-xs text-destructive">
                      Chưa có model chat được cấp cho workspace. Hãy cấu hình
                      trong ModelOps trước khi dùng chế độ này.
                    </p>
                  ) : null}
                </div>
              ) : null}

              <div className="space-y-1 pt-3 border-t text-xs text-muted-foreground">
                <p className="font-semibold text-foreground">Khi xác nhận</p>
                <ul className="list-disc space-y-0.5 pl-4">
                  <li>
                    Hệ thống dùng đúng tệp v{revisionNo} và bản văn bản đã lưu.
                  </li>
                  <li>Tạo bản nháp có dẫn chứng rồi dừng lại để bạn xem.</li>
                  <li>Không tự đăng ký hay xuất bản.</li>
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
                disabled={createMutation.isPending || aiUnavailable}
              >
                {createMutation.isPending ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" />
                    <span>Đang gửi...</span>
                  </>
                ) : (
                  <>
                    <ClipboardList className="size-3.5" />
                    <span>Bắt đầu chuẩn bị</span>
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

function PreparationStatusView({ intent }: { intent: PreparationIntent }) {
  const isActive = isPreparationActive(intent);
  const isReady = intent.status === "ready";
  const isFailed = intent.status === "failed" || intent.status === "uncertain";

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

      {isReady ? (
        <Alert variant="success" className="py-2.5">
          <CheckCircle2 className="size-4" />
          <AlertTitle className="text-xs">Bản nháp đã sẵn sàng</AlertTitle>
          <AlertDescription className="text-xs">
            Xem và quyết định đăng ký ở bước tiếp theo. Hệ thống không tự đăng
            ký hay xuất bản.
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

      <dl className="space-y-1 text-xs">
        <div className="flex justify-between gap-3">
          <dt className="text-muted-foreground">Chế độ</dt>
          <dd>
            {intent.mode === "ai" ? "Bổ sung bằng AI" : "Giữ nguyên nguồn"}
          </dd>
        </div>
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
      </dl>

      {isActive ? (
        <p className="text-[11px] text-muted-foreground">
          Hủy chỉ ngăn bước kế tiếp; tác vụ đã gửi tới nhà cung cấp có thể vẫn
          hoàn tất. Bạn có thể đóng hộp thoại, yêu cầu vẫn chạy ở nền.
        </p>
      ) : null}
    </div>
  );
}
