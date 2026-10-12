import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Layers, Loader2, Upload } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";
import { apiClient } from "@/services/modelops-api";
import type { VectorLoadItem } from "@/types/knowledge";
import {
  getGenerationLabel,
  getProviderOrigin,
} from "../utils/vector-generation-label";
import {
  canPublishSources,
  getSourceVectorState,
} from "../utils/vector-workflow";
import { CandidateRagPreview } from "./candidate-rag-preview";
import { useVectorWorkflow } from "./use-vector-workflow";

export function VectorLoadControls({
  collectionId,
  targets,
  disabledReason,
  compact = false,
  initialGenerationId,
  actionLabel = "Nạp vector",
  preferNewGeneration = false,
}: {
  collectionId: string;
  targets: VectorLoadItem[];
  disabledReason?: string;
  compact?: boolean;
  initialGenerationId?: string;
  actionLabel?: string;
  preferNewGeneration?: boolean;
}) {
  const client = useQueryClient();
  const { sources, generations, state } = useVectorWorkflow(collectionId);
  const [isOpen, setIsOpen] = useState(false);
  const [isPublishOpen, setIsPublishOpen] = useState(false);
  const [selection, setSelection] = useState("");
  const [loadedGenerationId, setLoadedGenerationId] = useState("");
  const models = useQuery({
    queryKey: ["system-model-defaults"],
    queryFn: () => apiClient.getSystemModelDefaults(),
    enabled: isOpen,
  });
  const options = models.data?.available_embeddings || [];
  const collection = useQuery({
    queryKey: ["knowledge-collection", collectionId],
    queryFn: () => knowledgeApi.getCollection(collectionId),
    enabled: isOpen,
  });
  const providers = useQuery({
    queryKey: ["modelops-providers"],
    queryFn: () => apiClient.getModelProviders(),
    enabled: isOpen,
    staleTime: 60000,
  });
  const active = generations.data?.find(
    (generation) => generation.status === "active",
  );
  const defaultModel = options.find(
    (model) =>
      model.provider_id ===
        (collection.data?.data_processing?.embedding_provider_id ||
          models.data?.defaults.default_embedding_provider_id) &&
      model.model_name ===
        (collection.data?.data_processing?.embedding_model ||
          models.data?.defaults.default_embedding_model),
  );
  const effectiveSelection =
    selection ||
    (initialGenerationId &&
    generations.data?.some(
      (item) => item.id === initialGenerationId && item.status !== "retired",
    )
      ? `gen:${initialGenerationId}`
      : active && !preferNewGeneration
        ? `gen:${active.id}`
        : defaultModel
          ? `model:${defaultModel.provider_id}:${defaultModel.model_name}`
          : "");
  const publishId =
    loadedGenerationId ||
    (effectiveSelection.startsWith("gen:") ? effectiveSelection.slice(4) : "");
  const selectedProviderId = effectiveSelection.startsWith("gen:")
    ? generations.data?.find((item) => `gen:${item.id}` === effectiveSelection)
        ?.provider_id
    : options.find(
        (item) =>
          `model:${item.provider_id}:${item.model_name}` === effectiveSelection,
      )?.provider_id;
  const selectedProvider = providers.data?.find(
    (item) => item.id === selectedProviderId,
  );
  const invalidate = () => {
    for (const key of [
      "knowledge-vector-load",
      "knowledge-bindings",
      "knowledge-vector-generations",
      "knowledge-collection",
      "collection-summary-metrics",
      "knowledge-source",
      "knowledge-source-chunk-sets",
    ])
      client.invalidateQueries({ queryKey: [key, collectionId] });
  };
  const load = useMutation({
    mutationFn: async () => {
      if (collection.isPending || collection.isError || !collection.data)
        throw new Error("Chưa tải được cấu hình Embedding của kho.");
      if (!targets.length || disabledReason)
        throw new Error(
          disabledReason || "Hãy chọn nguồn có Markdown sẵn sàng.",
        );
      let generationId = effectiveSelection.startsWith("gen:")
        ? effectiveSelection.slice(4)
        : "";
      if (!generationId) {
        const model = options.find(
          (option) =>
            `model:${option.provider_id}:${option.model_name}` ===
            effectiveSelection,
        );
        if (!model)
          throw new Error("Hãy chọn mô hình embedding trong ModelOps.");
        const generation = await knowledgeApi.createVectorGeneration(
          collectionId,
          {
            embedding_model: model.model_name,
            provider_id: model.provider_id,
            embedding_dimension: model.dimension || undefined,
          },
        );
        generationId = generation.id;
        setSelection(`gen:${generationId}`);
      }
      setLoadedGenerationId(generationId);
      return knowledgeApi.loadSourceVectors(
        collectionId,
        generationId,
        targets,
      );
    },
    onSuccess: () => {
      toast.success("Đã xếp hàng nạp Markdown vào vector. Chưa xuất bản.");
      invalidate();
    },
    onError: (error) => {
      toast.error(extractErrorMessage(error, "Nạp vector thất bại."));
      invalidate();
    },
  });
  const publish = useMutation({
    mutationFn: () =>
      knowledgeApi.activateVectorGeneration(collectionId, publishId),
    onSuccess: () => {
      toast.success("Đã xuất bản chỉ mục cho chatbot.");
      setIsPublishOpen(false);
      invalidate();
    },
    onError: (error) => {
      toast.error(extractErrorMessage(error, "Xuất bản thất bại."));
      invalidate();
    },
  });
  const targetStates = targets.map((target) => {
    const source = sources.data?.find((item) => item.id === target.binding_id);
    return {
      target,
      source,
      status: source
        ? getSourceVectorState(source, publishId, state.data)
        : undefined,
    };
  });
  const isBusy =
    load.isPending || targetStates.some((item) => item.status?.isPending);
  const canPublish =
    !disabledReason &&
    !state.isError &&
    !sources.isError &&
    !generations.isError &&
    targetStates.every(
      ({ source, target }) =>
        source?.active_source_revision_id === target.source_revision_id,
    ) &&
    canPublishSources(sources.data || [], publishId, state.data);
  return (
    <>
      <Button
        size="sm"
        variant={compact ? "outline" : "default"}
        disabled={!!disabledReason || !targets.length}
        title={
          disabledReason ||
          (preferNewGeneration
            ? "Tạo chỉ mục mới từ Markdown sạch; chỉ đổi chatbot sau khi xuất bản"
            : "Nạp Markdown đã lưu vào Qdrant")
        }
        onClick={() => {
          setSelection("");
          setLoadedGenerationId("");
          setIsOpen(true);
        }}
      >
        <Upload className="size-3.5" />
        {actionLabel}
      </Button>
      <Dialog
        open={isOpen}
        onOpenChange={(value) => {
          if (!load.isPending && !publish.isPending) setIsOpen(value);
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>
              {preferNewGeneration
                ? "Đổi model · Chỉ mục mới"
                : "Nạp Markdown vào vector"}
            </DialogTitle>
            <DialogDescription>
              Dùng {targets.length} bản Markdown đã lưu và đủ điều kiện. Không
              bóc tách/OCR lại; chỉ mục đang phục vụ được giữ nguyên đến khi
              xuất bản.
            </DialogDescription>
          </DialogHeader>
          <Select
            value={effectiveSelection}
            onValueChange={(value) => {
              setSelection(value);
              setLoadedGenerationId("");
            }}
            disabled={isBusy}
          >
            <SelectTrigger
              aria-label="Mô hình embedding"
              className="h-auto min-h-9 min-w-0 [&>span]:whitespace-normal [&>span]:text-left"
            >
              <SelectValue placeholder="Chọn mô hình từ ModelOps" />
            </SelectTrigger>
            <SelectContent className="max-w-[calc(100vw-2rem)]">
              {generations.data
                ?.filter((generation) => generation.status !== "retired")
                .map((generation) => (
                  <SelectItem
                    key={generation.id}
                    value={`gen:${generation.id}`}
                    className="whitespace-normal break-words"
                  >
                    {getGenerationLabel(generation, providers.data)}
                  </SelectItem>
                ))}
              {options.map((model) => (
                <SelectItem
                  key={`${model.provider_id}:${model.model_name}`}
                  value={`model:${model.provider_id}:${model.model_name}`}
                  className="whitespace-normal break-words"
                >
                  {model.model_name} · {model.provider_name} (Chỉ mục mới)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground break-words">
            Máy chủ embedding:{" "}
            {providers.isPending
              ? "Đang tải…"
              : providers.isError
                ? "Không tải được thông tin provider"
                : getProviderOrigin(selectedProvider)}
            . “Bản” là phiên bản chỉ mục, không phải nơi chạy model.
          </p>
          {models.isSuccess && !options.length && !generations.data?.length && (
            <p className="text-sm text-muted-foreground">
              Chưa có mô hình embedding. Hãy cấu hình tại Mô hình &amp;
              Provider.
            </p>
          )}
          {(models.isError ||
            generations.isError ||
            sources.isError ||
            state.isError) && (
            <p role="alert" className="text-sm text-destructive">
              {extractErrorMessage(
                models.error ||
                  generations.error ||
                  sources.error ||
                  state.error,
                "Không tải được cấu hình/trạng thái vector.",
              )}
            </p>
          )}
          <div className="space-y-2 text-sm">
            {targetStates.map(({ target, source, status }) => (
              <div
                key={target.binding_id}
                className="rounded-md border border-border p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="break-words">
                    {source?.document_title || target.binding_id}
                  </span>
                  <span className="shrink-0 text-muted-foreground">
                    {status?.label || "Chưa nạp vector"}
                  </span>
                </div>
                {status?.error && (
                  <p role="alert" className="mt-1 text-xs text-destructive">
                    {status.error}
                  </p>
                )}
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Xuất bản áp dụng cho toàn chỉ mục của kho. Mọi nguồn đang hoạt động
            phải được nạp bản Markdown hiện hành trước khi xuất bản.
          </p>
          {publishId && (
            <CandidateRagPreview
              key={publishId}
              collectionId={collectionId}
              generationId={publishId}
            />
          )}
          <DialogFooter className="flex-wrap gap-2">
            <Button
              variant="outline"
              disabled={load.isPending || publish.isPending}
              onClick={() => setIsOpen(false)}
            >
              Đóng
            </Button>
            <Button
              variant="outline"
              disabled={!canPublish || isBusy || publish.isPending}
              onClick={() => setIsPublishOpen(true)}
            >
              <Layers className="size-3.5" />
              Xuất bản
            </Button>
            <Button
              disabled={
                !effectiveSelection ||
                isBusy ||
                !!disabledReason ||
                models.isError ||
                collection.isPending ||
                collection.isError ||
                state.isError ||
                sources.isError ||
                generations.isError
              }
              onClick={() => load.mutate()}
            >
              {isBusy ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Upload className="size-3.5" />
              )}
              {isBusy ? "Đang nạp" : "Nạp vector"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <ConfirmDialog
        open={isPublishOpen}
        onOpenChange={setIsPublishOpen}
        title="Xuất bản chỉ mục?"
        description="Chatbot sẽ sử dụng chỉ mục này cho toàn bộ kho. Backend sẽ đối soát và chỉ chuyển sang chỉ mục mới khi mọi nguồn hợp lệ."
        confirmText="Xuất bản"
        variant="default"
        isPending={publish.isPending}
        onConfirm={() => publish.mutate()}
      />
    </>
  );
}
