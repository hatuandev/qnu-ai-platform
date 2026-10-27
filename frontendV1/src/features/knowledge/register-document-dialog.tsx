import {
  AlertCircle,
  BookPlus,
  Check,
  FilePlus2,
  Layers,
  Loader2,
  Tags,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
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
import {
  type AnnotationDraft,
  annotationDraftIssues,
  draftsToAnnotations,
  RetrievalMetadataEditor,
} from "./retrieval-metadata-editor";

export function RegisterDocumentDialog({
  workspaceId,
  collectionId,
  compilationRunId,
  defaultTitle = "",
  isOpen,
  onClose,
  onSuccess,
}: {
  workspaceId: string;
  collectionId: string;
  compilationRunId: string;
  defaultTitle?: string;
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

  // Optional retrieval metadata declared for the version being registered.
  const [metadataOpen, setMetadataOpen] = useState(false);
  const [annotationDrafts, setAnnotationDrafts] = useState<AnnotationDraft[]>(
    [],
  );
  const annotationIssues = annotationDraftIssues(annotationDrafts);
  const hasAnnotationIssues = annotationIssues.size > 0;

  // Load existing compiled documents for option "existing"
  const documentsQuery = useCompiledDocumentsQuery(
    workspaceId,
    collectionId,
    100,
    0,
    { enabled: isOpen },
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
      setIdempotencyKey(generatePublicationIdempotencyKey());
      setErrorBanner(null);
      setMode("new");
      setSelectedDocumentId("");
      setAnnotationDrafts([]);
      setMetadataOpen(false);
    }
  }, [isOpen, defaultTitle]);

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
    setErrorBanner(null);

    if (hasAnnotationIssues) {
      setMetadataOpen(true);
      setErrorBanner(
        "Metadata truy xuất còn lỗi. Sửa hoặc xoá các mục được đánh dấu trước khi đăng ký.",
      );
      return;
    }

    const retrievalMetadata = draftsToAnnotations(annotationDrafts);

    if (mode === "new") {
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
            retrieval_metadata: retrievalMetadata,
          },
          idempotencyKey,
        });

        toast.success(
          result.created
            ? "Tạo tài liệu và phiên bản mới thành công"
            : "Tài liệu đã tồn tại (Replay)",
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
      if (!selectedDocumentId) {
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
            retrieval_metadata: retrievalMetadata,
          },
          idempotencyKey,
        });

        toast.success(
          result.created
            ? `Thêm phiên bản v${result.version.version_no} thành công`
            : "Phiên bản đã được đăng ký trước đó (Replay)",
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

  const existingDocs = documentsQuery.data ?? [];

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
                Đăng ký tài liệu biên soạn
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Lưu kết quả biên soạn đã hoàn tất thành một tài liệu hoặc phiên
                bản mới trong kho tri thức.
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
          <div className="space-y-2">
            <Label className="text-xs font-semibold text-foreground">
              Hình thức đăng ký
            </Label>
            <RadioGroup
              value={mode}
              onValueChange={(val) => {
                setMode(val as "new" | "existing");
                setErrorBanner(null);
              }}
              className="grid grid-cols-1 sm:grid-cols-2 gap-2"
            >
              <label
                htmlFor="mode-new"
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  mode === "new"
                    ? "border-primary bg-primary/5 text-foreground"
                    : "border-border hover:bg-muted/40 text-muted-foreground"
                }`}
              >
                <RadioGroupItem value="new" id="mode-new" className="mt-0.5" />
                <div className="space-y-0.5 min-w-0">
                  <div className="flex items-center gap-1.5 font-medium text-xs text-foreground">
                    <FilePlus2 className="size-3.5 text-primary" />
                    Tạo tài liệu mới
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    Khởi tạo danh tính tài liệu độc lập với key và tiêu đề riêng
                  </p>
                </div>
              </label>

              <label
                htmlFor="mode-existing"
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  mode === "existing"
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
                    Nâng cấp nội dung cho một tài liệu biên soạn đã có sẵn
                  </p>
                </div>
              </label>
            </RadioGroup>
          </div>

          {mode === "new" ? (
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
                    Document Key <span className="text-destructive">*</span>
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
                  Định danh cố định trong URL/hệ thống. Chỉ gồm chữ thường không
                  dấu, số, dấu gạch nối, gạch dưới.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3 p-3.5 rounded-lg border bg-card/60">
              <div className="space-y-1.5">
                <Label htmlFor="select-doc" className="text-xs font-medium">
                  Chọn tài liệu đích <span className="text-destructive">*</span>
                </Label>
                {documentsQuery.isLoading ? (
                  <div className="h-9 rounded-md border flex items-center px-3 text-xs text-muted-foreground">
                    <Loader2 className="size-3.5 animate-spin mr-2" />
                    Đang tải danh sách tài liệu...
                  </div>
                ) : existingDocs.length === 0 ? (
                  <div className="p-3 rounded-md bg-muted/40 border text-xs text-muted-foreground">
                    Chưa có tài liệu biên soạn nào trong kho tri thức này. Vui
                    lòng chọn &quot;Tạo tài liệu mới&quot;.
                  </div>
                ) : (
                  <Select
                    value={selectedDocumentId}
                    onValueChange={(val) => {
                      setSelectedDocumentId(val);
                      setErrorBanner(null);
                    }}
                    disabled={isPending}
                  >
                    <SelectTrigger id="select-doc" className="text-xs h-9">
                      <SelectValue placeholder="Chọn một tài liệu biên soạn..." />
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
                )}
                <p className="text-[11px] text-muted-foreground">
                  Phiên bản mới sẽ được gán số thứ tự tiếp theo của tài liệu này
                  (bắt đầu ở trạng thái nháp).
                </p>
              </div>
            </div>
          )}

          <Collapsible open={metadataOpen} onOpenChange={setMetadataOpen}>
            <CollapsibleTrigger asChild>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-full h-8 justify-between text-xs"
                aria-expanded={metadataOpen}
              >
                <span className="flex items-center gap-1.5">
                  <Tags className="size-3.5 text-primary" />
                  Metadata truy xuất
                  {annotationDrafts.length > 0 ? (
                    <span className="text-[11px] text-muted-foreground">
                      ({annotationDrafts.length} mục)
                    </span>
                  ) : (
                    <span className="text-[11px] text-muted-foreground">
                      (tuỳ chọn)
                    </span>
                  )}
                </span>
                {hasAnnotationIssues ? (
                  <span className="text-[11px] text-destructive font-medium">
                    Cần sửa
                  </span>
                ) : null}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="mt-2 rounded-lg border bg-muted/10 p-3">
                <RetrievalMetadataEditor
                  drafts={annotationDrafts}
                  onChange={setAnnotationDrafts}
                  disabled={isPending}
                />
              </div>
            </CollapsibleContent>
          </Collapsible>

          <div className="text-[11px] text-muted-foreground/80 flex items-center justify-between border-t pt-2">
            <span>
              Compiler Run:{" "}
              <span className="font-mono">{compilationRunId}</span>
            </span>
            <span className="font-mono">
              Key: {idempotencyKey.slice(0, 16)}...
            </span>
          </div>

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
                hasAnnotationIssues ||
                (mode === "new" && (!title.trim() || !documentKey.trim())) ||
                (mode === "existing" &&
                  (!selectedDocumentId || existingDocs.length === 0))
              }
              className="text-xs gap-1.5"
            >
              {isPending ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang xử lý...</span>
                </>
              ) : mode === "new" ? (
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
