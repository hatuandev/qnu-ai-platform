import { FileUp, FolderPlus, HardDrive, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import {
  Field,
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

  const [files, setFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{
    current: number;
    total: number;
    currentFileName: string;
    progressPercent: number;
  } | null>(null);

  useEffect(() => {
    if (open) {
      if (collectionId) {
        setSelectedCollectionId(collectionId);
      } else if (collectionsQuery.data?.items[0] && !selectedCollectionId) {
        setSelectedCollectionId(collectionsQuery.data.items[0].id);
      }
      setFiles([]);
      setFileError(null);
      setServerError(null);
      setIsSubmitting(false);
      setUploadProgress(null);
    }
  }, [open, collectionId, collectionsQuery.data?.items, selectedCollectionId]);

  const handleFilesChange = (nextFiles: File[]) => {
    setFiles(nextFiles);
    setServerError(null);
    if (nextFiles.length > 0) {
      for (const f of nextFiles) {
        const err = validateUploadFile(f);
        if (err) {
          setFileError(`${f.name}: ${err}`);
          return;
        }
      }
      setFileError(null);
    } else {
      setFileError(null);
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setServerError(null);

    if (!effectiveCollectionId) {
      setServerError("Vui lòng chọn kho tri thức đích.");
      return;
    }

    if (files.length === 0) {
      setFileError("Vui lòng chọn ít nhất 1 tệp tài liệu.");
      return;
    }

    for (const f of files) {
      const validationErr = validateUploadFile(f);
      if (validationErr) {
        setFileError(`${f.name}: ${validationErr}`);
        return;
      }
    }

    setIsSubmitting(true);
    let successCount = 0;
    let lastSourceId = "";

    try {
      for (let i = 0; i < files.length; i++) {
        const currentFile = files[i];
        const progressPercent = Math.round((i / files.length) * 100);
        setUploadProgress({
          current: i + 1,
          total: files.length,
          currentFileName: currentFile.name,
          progressPercent,
        });

        const title =
          currentFile.name.replace(/\.[^/.]+$/, "").trim() || undefined;

        const result = await uploadMutation.mutateAsync({
          file: currentFile,
          title,
          idempotencyKey: generateIdempotencyKey(),
          folder_id: folderId ?? null,
        });

        lastSourceId = result.source.id;
        successCount++;
      }

      toast.success(
        files.length === 1
          ? "Đã tải lên tệp thành công."
          : `Đã tải lên thành công ${successCount}/${files.length} tệp tài liệu.`,
      );
      onOpenChange(false);
      if (lastSourceId) {
        onSuccess?.(lastSourceId);
      }
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setServerError(error.message);
      } else {
        setServerError(
          "Không tải lên được tệp. Vui lòng kiểm tra lại kết nối.",
        );
      }
    } finally {
      setIsSubmitting(false);
      setUploadProgress(null);
    }
  };

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
              Hỗ trợ tệp định dạng PDF hoặc Word (.docx), tối đa 60 MB mỗi tệp.
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

              {/* File Upload Area */}
              <Field>
                <FieldLabel htmlFor="source-files">
                  Tệp tài liệu <span className="text-destructive">*</span>
                </FieldLabel>

                <FileUpload
                  id="source-files"
                  accept={ACCEPT_UPLOAD}
                  acceptLabel="PDF, DOCX"
                  multiple={true}
                  maxFiles={20}
                  maxSize={MAX_UPLOAD_BYTES}
                  disabled={isSubmitting}
                  value={files}
                  onFilesChange={handleFilesChange}
                  progress={
                    isSubmitting && uploadProgress
                      ? uploadProgress.progressPercent
                      : undefined
                  }
                  progressLabel={
                    uploadProgress
                      ? `Đang tải lên (${uploadProgress.current}/${uploadProgress.total}): ${uploadProgress.currentFileName}`
                      : undefined
                  }
                />
                {fileError ? <FieldError>{fileError}</FieldError> : null}
              </Field>
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
                  files.length === 0 ||
                  Boolean(fileError) ||
                  !effectiveCollectionId
                }
                className="gap-1.5"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" />
                    <span>
                      {uploadProgress
                        ? `Đang tải (${uploadProgress.current}/${uploadProgress.total})...`
                        : "Đang tải lên..."}
                    </span>
                  </>
                ) : (
                  <>
                    <FileUp className="size-3.5" />
                    <span>
                      Tải lên {files.length > 0 ? `(${files.length} tệp)` : ""}
                    </span>
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
