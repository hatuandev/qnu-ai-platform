import { FileUp, FolderPlus, HardDrive, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/admin/field";
import { FileUpload } from "@/components/admin/file-upload";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CollectionFormDialog } from "@/features/knowledge/collection-form-dialog";
import {
  useCollectionQuery,
  useCollectionsQuery,
  useFolderQuery,
  useUploadSource,
} from "@/features/knowledge/queries";
import {
  ACCEPT_UPLOAD,
  generateIdempotencyKey,
  MAX_UPLOAD_BYTES,
  validateUploadFile,
} from "@/features/knowledge/schemas";
import type { KBCollection } from "@/features/knowledge/types";

export function SourceUploadDialog({
  open,
  onOpenChange,
  workspaceId,
  collectionId,
  folderId,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collectionId?: string;
  folderId?: string | null;
  onSuccess?: (sourceId: string) => void;
}) {
  const [selectedCollectionId, setSelectedCollectionId] = useState<string>(
    collectionId ?? "",
  );
  const [createCollectionOpen, setCreateCollectionOpen] = useState(false);

  const effectiveCollectionId = collectionId || selectedCollectionId;
  const uploadMutation = useUploadSource(workspaceId, effectiveCollectionId);

  const collectionsQuery = useCollectionsQuery(
    workspaceId,
    { pageSize: 100 },
  );
  const activeCollectionQuery = useCollectionQuery(
    workspaceId,
    effectiveCollectionId,
  );
  const activeFolderQuery = useFolderQuery(
    workspaceId,
    effectiveCollectionId,
    folderId ?? "",
  );

  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [fileError, setFileError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  // Maintain idempotency key across retries of the SAME operation
  const idempotencyKeyRef = useRef<string>(generateIdempotencyKey());

  useEffect(() => {
    if (open) {
      if (collectionId) {
        setSelectedCollectionId(collectionId);
      } else if (collectionsQuery.data?.items[0] && !selectedCollectionId) {
        setSelectedCollectionId(collectionsQuery.data.items[0].id);
      }
      setFile(null);
      setTitle("");
      setFileError(null);
      setServerError(null);
      idempotencyKeyRef.current = generateIdempotencyKey();
    }
  }, [open, collectionId, collectionsQuery.data?.items, selectedCollectionId]);

  const handleFileChange = (files: File[]) => {
    const selected = files[0] ?? null;
    setFile(selected);
    setServerError(null);
    if (selected) {
      const err = validateUploadFile(selected);
      setFileError(err);
      if (!title) {
        setTitle(selected.name.replace(/\.[^/.]+$/, ""));
      }
      idempotencyKeyRef.current = generateIdempotencyKey();
    } else {
      setFileError(null);
    }
  };

  const handleTitleChange = (nextTitle: string) => {
    setTitle(nextTitle);
    setServerError(null);
    idempotencyKeyRef.current = generateIdempotencyKey();
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setServerError(null);

    if (!effectiveCollectionId) {
      setServerError("Vui lòng chọn kho tri thức đích.");
      return;
    }

    const validationErr = validateUploadFile(file);
    if (validationErr) {
      setFileError(validationErr);
      return;
    }
    if (!file) return;

    try {
      const result = await uploadMutation.mutateAsync({
        file,
        title: title.trim() || undefined,
        idempotencyKey: idempotencyKeyRef.current,
        folder_id: folderId ?? null,
      });

      toast.success("Đã tải lên và lưu tệp thành công.");
      onOpenChange(false);
      onSuccess?.(result.source.id);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setServerError(error.message);
      } else {
        setServerError(
          "Không tải lên được tệp. Vui lòng kiểm tra lại kết nối.",
        );
      }
    }
  };

  const isSubmitting = uploadMutation.isPending;
  const collections = collectionsQuery.data?.items ?? [];

  return (
    <>
      <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
        <ResponsiveDialogContent className="max-h-[min(820px,calc(100vh-2rem))] max-w-lg p-0 gap-0 flex flex-col">
          <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4 sm:px-6">
            <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base font-semibold">
              <span className="flex size-8 items-center justify-center rounded-lg bg-muted text-primary">
                <FileUp className="size-4" />
              </span>
              Tải tài liệu lên kho
            </ResponsiveDialogTitle>
            <ResponsiveDialogDescription className="text-xs">
              Thêm tài liệu vào kho tri thức. Hỗ trợ tệp định dạng PDF (.pdf) hoặc
              Word (.docx), dung lượng tối đa 60 MB.
            </ResponsiveDialogDescription>
          </ResponsiveDialogHeader>

          <form
            id="source-upload-form"
            className="min-h-0 flex-1 overflow-y-auto"
            onSubmit={handleSubmit}
          >
            <div className="grid gap-4 px-4 py-4 sm:px-6">
              {serverError ? (
                <p
                  role="alert"
                  className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
                >
                  {serverError}
                </p>
              ) : null}

              {/* Destination Location Info / Picker */}
              {!collectionId ? (
                <Field>
                  <div className="flex items-center justify-between">
                    <FieldLabel htmlFor="target-collection">
                      Kho tri thức đích <span className="text-destructive">*</span>
                    </FieldLabel>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-6 px-1.5 text-xs text-primary gap-1"
                      onClick={() => setCreateCollectionOpen(true)}
                    >
                      <FolderPlus className="size-3" />
                      <span>Tạo kho mới</span>
                    </Button>
                  </div>
                  <Select
                    value={selectedCollectionId}
                    onValueChange={setSelectedCollectionId}
                    disabled={isSubmitting || collections.length === 0}
                  >
                    <SelectTrigger id="target-collection" className="text-xs h-9">
                      <SelectValue placeholder="Chọn kho tri thức..." />
                    </SelectTrigger>
                    <SelectContent>
                      {collections.map((c: KBCollection) => (
                        <SelectItem key={c.id} value={c.id} className="text-xs">
                          {c.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {collections.length === 0 ? (
                    <FieldError>
                      Chưa có kho tri thức nào. Bấm "Tạo kho mới" ở trên để bắt đầu.
                    </FieldError>
                  ) : null}
                </Field>
              ) : (
                <div className="rounded-md border border-border/60 bg-muted/20 px-3 py-2 text-xs flex items-center justify-between">
                  <div className="flex items-center gap-2 text-muted-foreground truncate">
                    <HardDrive className="size-3.5 text-primary shrink-0" />
                    <span>Nơi lưu:</span>
                    <strong className="text-foreground truncate">
                      {activeCollectionQuery.data?.name ?? "Đang tải..."}
                    </strong>
                    {folderId && activeFolderQuery.data ? (
                      <>
                        <span>/</span>
                        <span className="text-foreground font-medium truncate">
                          {activeFolderQuery.data.name}
                        </span>
                      </>
                    ) : (
                      <span className="text-muted-foreground">(Thư mục gốc)</span>
                    )}
                  </div>
                </div>
              )}

              <Field>
                <FieldLabel htmlFor="source-file">
                  Tệp tài liệu <span className="text-destructive">*</span>
                </FieldLabel>
                <FileUpload
                  accept={ACCEPT_UPLOAD}
                  multiple={false}
                  maxSize={MAX_UPLOAD_BYTES}
                  disabled={isSubmitting}
                  value={file ? [file] : []}
                  onFilesChange={handleFileChange}
                />
                {fileError ? (
                  <FieldError>{fileError}</FieldError>
                ) : (
                  <FieldDescription>
                    Chỉ chọn 1 tệp mỗi lần. Tệp được lưu nguyên vẹn bytes vào kho
                    lưu trữ an toàn.
                  </FieldDescription>
                )}
              </Field>

              <Field>
                <FieldLabel htmlFor="source-title">Tiêu đề hiển thị</FieldLabel>
                <Input
                  id="source-title"
                  className="text-xs h-9"
                  placeholder="Ví dụ: Hướng dẫn tuyển sinh và học phí năm 2026"
                  value={title}
                  disabled={isSubmitting}
                  maxLength={255}
                  onChange={(event) => handleTitleChange(event.target.value)}
                />
                <FieldDescription>
                  Tùy chọn. Nếu để trống, hệ thống sẽ sử dụng tên tệp làm tiêu đề.
                </FieldDescription>
              </Field>

              {isSubmitting ? (
                <div className="rounded-md border border-info/30 bg-info/5 p-3 text-xs text-info flex items-center gap-2">
                  <Loader2 className="size-4 animate-spin shrink-0" />
                  <span>
                    Đang tải lên tệp ({file?.name}). Vui lòng không đóng trình
                    duyệt...
                  </span>
                </div>
              ) : null}
            </div>

            <ResponsiveDialogFooter className="border-t bg-card px-4 py-3 sm:px-6">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={isSubmitting}
                onClick={() => onOpenChange(false)}
              >
                Hủy
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={
                  isSubmitting ||
                  !file ||
                  Boolean(fileError) ||
                  !effectiveCollectionId
                }
                className="gap-1.5"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" />
                    <span>Đang tải lên...</span>
                  </>
                ) : (
                  <>
                    <FileUp className="size-3.5" />
                    <span>Tải tài liệu</span>
                  </>
                )}
              </Button>
            </ResponsiveDialogFooter>
          </form>
        </ResponsiveDialogContent>
      </ResponsiveDialog>

      {/* Inline Create Collection Dialog if needed */}
      <CollectionFormDialog
        open={createCollectionOpen}
        onOpenChange={setCreateCollectionOpen}
        workspaceId={workspaceId}
        onSuccess={(created) => {
          setSelectedCollectionId(created.id);
          toast.success(`Đã tạo kho "${created.name}". Bạn có thể tiếp tục tải tài liệu.`);
        }}
      />
    </>
  );
}
