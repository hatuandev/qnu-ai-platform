import {
  AlertCircle,
  BookPlus,
  Check,
  FilePlus2,
  Layers,
  Loader2,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
import {
  useAutomaticMetadataQuery,
  useCompiledDocumentsQuery,
  useCreateCompiledDocumentMutation,
  useCreateCompiledVersionMutation,
} from "./publication-queries";
import {
  createDocumentSchema,
  formatPublicationError,
  generatePublicationIdempotencyKey,
  registerVersionSchema,
  slugifyKey,
} from "./publication-schemas";

export function RegisterDocumentDialog({
  workspaceId,
  collectionId,
  compilationRunId,
  defaultTitle = "",
  draftState = "ready",
  isOpen,
  onClose,
  onSuccess,
}: {
  workspaceId: string;
  collectionId: string;
  compilationRunId: string;
  defaultTitle?: string;
  draftState?: "ready" | "loading" | "error";
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (documentId: string, versionId: string) => void;
}) {
  const [mode, setMode] = useState<"new" | "existing">("new");
  const [title, setTitle] = useState(defaultTitle);
  const [documentKey, setDocumentKey] = useState("");
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState(() =>
    generatePublicationIdempotencyKey(),
  );
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const information = useAutomaticMetadataQuery(
    workspaceId,
    collectionId,
    compilationRunId,
    { enabled: isOpen && draftState === "ready" },
  );
  const informationReady =
    Boolean(information.data) &&
    !information.isError &&
    !information.isFetching;

  // Load existing compiled documents for option "existing"
  const documentsQuery = useCompiledDocumentsQuery(
    workspaceId,
    collectionId,
    100,
    0,
    { enabled: isOpen },
  );
  const existingDocs = documentsQuery.data ?? [];
  const hasExistingDocuments =
    documentsQuery.isSuccess && existingDocs.length > 0;
  const registrationMode = hasExistingDocuments ? mode : "new";
  const hasSelectedDocument = existingDocs.some(
    (doc) => doc.id === selectedDocumentId,
  );

  const createDocMutation = useCreateCompiledDocumentMutation(
    workspaceId,
    collectionId,
  );
  const createVerMutation = useCreateCompiledVersionMutation(
    workspaceId,
    collectionId,
    selectedDocumentId,
  );

  const isPending = createDocMutation.isPending || createVerMutation.isPending;

  // Initialize/reset form state when dialog opens
  useEffect(() => {
    if (isOpen) {
      setTitle(defaultTitle);
      const suggestedKey = slugifyKey(defaultTitle);
      setDocumentKey(suggestedKey);
      setIdempotencyKey(
        generatePublicationIdempotencyKey(`pub_${compilationRunId}`),
      );
      setErrorBanner(null);
      setMode("new");
      setSelectedDocumentId("");
    }
  }, [isOpen, defaultTitle, compilationRunId]);

  const handleTitleChange = (val: string) => {
    setTitle(val);
    // If key hasn't been manually diverged or is empty, suggest slug
    if (!documentKey || documentKey === slugifyKey(title)) {
      setDocumentKey(slugifyKey(val));
    }
  };

  const handleAutoSlug = () => {
    if (title.trim()) {
      setDocumentKey(slugifyKey(title));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      draftState !== "ready" ||
      !informationReady ||
      isPending ||
      !information.data
    )
      return;
    setErrorBanner(null);

    const automaticInput = {
      automatic_metadata_sha256: information.data.sha256,
    };

    if (registrationMode === "new") {
      const parsed = createDocumentSchema.safeParse({
        document_key: documentKey,
        title,
        compilation_run_id: compilationRunId,
      });

      if (!parsed.success) {
        setErrorBanner(
          parsed.error.issues[0]?.message ?? "Dữ liệu không hợp lệ",
        );
        return;
      }

      try {
        const result = await createDocMutation.mutateAsync({
          input: {
            document_key: documentKey.trim(),
            title: title.trim(),
            compilation_run_id: compilationRunId,
            ...automaticInput,
          },
          idempotencyKey,
        });

        toast.success(
          result.created
            ? "Tạo tài liệu và phiên bản mới thành công"
            : "Tài liệu đã tồn tại, không tạo trùng",
        );
        onSuccess?.(result.document.id, result.version.id);
        onClose();
      } catch (err: unknown) {
        if (err instanceof ApiProblemError) {
          setErrorBanner(formatPublicationError(err.code, err.message));
        } else {
          setErrorBanner("Không thể đăng ký tài liệu. Vui lòng thử lại.");
        }
      }
    } else {
      if (!hasSelectedDocument) {
        setErrorBanner("Vui lòng chọn tài liệu cần thêm phiên bản");
        return;
      }

      const parsed = registerVersionSchema.safeParse({
        compilation_run_id: compilationRunId,
      });

      if (!parsed.success) {
        setErrorBanner(
          parsed.error.issues[0]?.message ?? "Dữ liệu không hợp lệ",
        );
        return;
      }

      try {
        const result = await createVerMutation.mutateAsync({
          input: {
            compilation_run_id: compilationRunId,
            ...automaticInput,
          },
          idempotencyKey,
        });

        toast.success(
          result.created
            ? `Thêm phiên bản v${result.version.version_no} thành công`
            : "Phiên bản đã được đăng ký trước đó",
        );
        onSuccess?.(result.document.id, result.version.id);
        onClose();
      } catch (err: unknown) {
        if (err instanceof ApiProblemError) {
          setErrorBanner(formatPublicationError(err.code, err.message));
        } else {
          setErrorBanner("Không thể thêm phiên bản. Vui lòng thử lại.");
        }
      }
    }
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => !isPending && !open && onClose()}
    >
      <DialogContent className="sm:max-w-xl max-h-[min(820px,calc(100vh-2rem))] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <BookPlus className="size-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-semibold">
                Đăng ký xuất bản
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Đưa nội dung đã chuẩn bị vào danh sách tài liệu để duyệt và xuất
                bản.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          {errorBanner && (
            <Alert variant="destructive" className="py-2.5">
              <AlertCircle className="size-4" />
              <AlertDescription className="text-xs">
                {errorBanner}
              </AlertDescription>
            </Alert>
          )}

          {/* Mode Selector */}
          {hasExistingDocuments && (
            <div className="space-y-2">
              <Label className="text-xs font-semibold text-foreground">
                Hình thức đăng ký
              </Label>
              <RadioGroup
                value={registrationMode}
                disabled={isPending}
                onValueChange={(val) => {
                  setMode(val as "new" | "existing");
                  setErrorBanner(null);
                }}
                className="grid grid-cols-1 sm:grid-cols-2 gap-2"
              >
                <label
                  htmlFor="mode-new"
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    registrationMode === "new"
                      ? "border-primary bg-primary/5 text-foreground"
                      : "border-border hover:bg-muted/40 text-muted-foreground"
                  }`}
                >
                  <RadioGroupItem
                    value="new"
                    id="mode-new"
                    className="mt-0.5"
                  />
                  <div className="space-y-0.5 min-w-0">
                    <div className="flex items-center gap-1.5 font-medium text-xs text-foreground">
                      <FilePlus2 className="size-3.5 text-primary" />
                      Tạo tài liệu mới
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      Tạo tài liệu mới với mã và tiêu đề riêng
                    </p>
                  </div>
                </label>

                <label
                  htmlFor="mode-existing"
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    registrationMode === "existing"
                      ? "border-primary bg-primary/5 text-foreground"
                      : "border-border hover:bg-muted/40 text-muted-foreground"
                  }`}
                >
                  <RadioGroupItem
                    value="existing"
                    id="mode-existing"
                    className="mt-0.5"
                  />
                  <div className="space-y-0.5 min-w-0">
                    <div className="flex items-center gap-1.5 font-medium text-xs text-foreground">
                      <Layers className="size-3.5 text-info" />
                      Thêm phiên bản mới
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      Thêm nội dung đã chuẩn bị làm phiên bản mới của một tài
                      liệu đã có
                    </p>
                  </div>
                </label>
              </RadioGroup>
            </div>
          )}

          {registrationMode === "new" ? (
            <div className="space-y-3 p-3.5 rounded-lg border bg-card/60">
              <div className="space-y-1.5">
                <Label htmlFor="doc-title" className="text-xs font-medium">
                  Tiêu đề tài liệu <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="doc-title"
                  value={title}
                  onChange={(e) => handleTitleChange(e.target.value)}
                  placeholder="Ví dụ: Chỉ tiêu tuyển sinh Đại học 2026"
                  maxLength={255}
                  className="text-xs h-9"
                  disabled={isPending}
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="doc-key" className="text-xs font-medium">
                    Mã tài liệu <span className="text-destructive">*</span>
                  </Label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-6 px-1.5 text-[11px] text-primary hover:text-primary/80"
                    onClick={handleAutoSlug}
                    disabled={isPending || !title.trim()}
                  >
                    Gợi ý từ tiêu đề
                  </Button>
                </div>
                <Input
                  id="doc-key"
                  value={documentKey}
                  onChange={(e) => setDocumentKey(e.target.value)}
                  placeholder="vi-du: chi-tieu-tuyen-sinh-2026"
                  maxLength={120}
                  className="text-xs h-9 font-mono"
                  disabled={isPending}
                />
                <p className="text-[11px] text-muted-foreground">
                  Mã cố định dùng trong đường dẫn. Chỉ gồm chữ thường không dấu,
                  số, dấu gạch nối hoặc gạch dưới.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3 p-3.5 rounded-lg border bg-card/60">
              <div className="space-y-1.5">
                <Label htmlFor="select-doc" className="text-xs font-medium">
                  Chọn tài liệu đích <span className="text-destructive">*</span>
                </Label>
                <Select
                  value={selectedDocumentId}
                  onValueChange={(val) => {
                    setSelectedDocumentId(val);
                    setErrorBanner(null);
                  }}
                  disabled={isPending}
                >
                  <SelectTrigger id="select-doc" className="text-xs h-9">
                    <SelectValue placeholder="Chọn một tài liệu..." />
                  </SelectTrigger>
                  <SelectContent>
                    {existingDocs.map((doc) => (
                      <SelectItem
                        key={doc.id}
                        value={doc.id}
                        className="text-xs"
                      >
                        <span className="font-medium">{doc.title}</span>{" "}
                        <span className="font-mono text-[11px] text-muted-foreground">
                          ({doc.document_key})
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-[11px] text-muted-foreground">
                  Phiên bản mới sẽ được gán số thứ tự tiếp theo của tài liệu này
                  (bắt đầu ở trạng thái nháp).
                </p>
              </div>
            </div>
          )}

          {documentsQuery.isError && (
            <p role="status" className="text-xs text-muted-foreground">
              Chưa tải được danh sách tài liệu để thêm phiên bản.{" "}
              <Button
                type="button"
                variant="link"
                size="sm"
                disabled={documentsQuery.isFetching || isPending}
                onClick={() => void documentsQuery.refetch()}
              >
                Tải lại danh sách
              </Button>
            </p>
          )}

          {draftState === "ready" && information.isError && (
            <Alert variant="destructive" className="py-2.5">
              <AlertCircle className="size-4" />
              <AlertDescription className="text-xs">
                Chưa chuẩn bị được tài liệu.{" "}
                <Button
                  type="button"
                  variant="link"
                  size="sm"
                  disabled={information.isFetching || isPending}
                  onClick={() => void information.refetch()}
                >
                  Tải lại
                </Button>
              </AlertDescription>
            </Alert>
          )}
          {draftState === "ready" &&
            !information.isError &&
            !informationReady && (
              <p role="status" className="text-xs text-muted-foreground">
                Đang chuẩn bị tài liệu…
              </p>
            )}

          {draftState !== "ready" && (
            <p role="status" className="text-xs text-muted-foreground">
              {draftState === "error"
                ? "Chưa tải được bản đã chuẩn bị. Hãy đóng cửa sổ rồi mở lại."
                : "Đang tải bản đã chuẩn bị…"}
            </p>
          )}

          <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={isPending}
              className="text-xs"
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={
                isPending ||
                draftState !== "ready" ||
                !informationReady ||
                (registrationMode === "new" &&
                  (!title.trim() || !documentKey.trim())) ||
                (registrationMode === "existing" && !hasSelectedDocument)
              }
              className="text-xs gap-1.5"
            >
              {isPending ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang xử lý...</span>
                </>
              ) : registrationMode === "new" ? (
                <>
                  <FilePlus2 className="size-3.5" />
                  <span>Tạo tài liệu</span>
                </>
              ) : (
                <>
                  <Check className="size-3.5" />
                  <span>Thêm phiên bản</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
