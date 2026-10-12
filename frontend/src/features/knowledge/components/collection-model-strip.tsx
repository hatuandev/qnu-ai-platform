import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cpu, Pencil } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";
import { apiClient } from "@/services/modelops-api";
import type { KnowledgeCollection } from "@/types/knowledge";
import {
  getGenerationLabel,
  getProviderOrigin,
} from "../utils/vector-generation-label";
import {
  EmbeddingModelSelect,
  getEmbeddingConfig,
  getEmbeddingKey,
  useEmbeddingModels,
} from "./embedding-model-select";
import { useVectorWorkflow } from "./use-vector-workflow";
import { VectorLoadControls } from "./vector-load-controls";

export function CollectionModelStrip({
  collection,
}: {
  collection: KnowledgeCollection;
}) {
  const { sources, generations, state } = useVectorWorkflow(collection.id);
  const models = useEmbeddingModels();
  const providers = useQuery({
    queryKey: ["modelops-providers"],
    queryFn: () => apiClient.getModelProviders(),
    staleTime: 60000,
  });
  const [isOpen, setIsOpen] = useState(false);
  const [selection, setSelection] = useState("");
  const client = useQueryClient();
  const active = generations.data?.find((item) => item.status === "active");
  const configured = collection.data_processing;
  const provider = providers.data?.find(
    (item) =>
      item.id === (active?.provider_id || configured?.embedding_provider_id),
  );
  const options = models.data?.available_embeddings || [];
  const selectedKey =
    selection ||
    (configured?.embedding_provider_id && configured.embedding_model
      ? `${configured.embedding_provider_id}:${configured.embedding_model}`
      : "");
  const selected = options.find(
    (item) => getEmbeddingKey(item) === selectedKey,
  );
  const targets = (sources.data || [])
    .filter(
      (item) =>
        item.status === "active" &&
        item.source_status === "ready" &&
        item.active_source_revision_id,
    )
    .map((item) => ({
      binding_id: item.id,
      source_revision_id: item.active_source_revision_id || "",
    }));
  const hasGeneration = !!generations.data?.length;
  const save = useMutation({
    mutationFn: async () => {
      if (!selected) throw new Error("Hãy chọn model Embedding hợp lệ.");
      const latest = await knowledgeApi.listVectorGenerations(collection.id);
      if (latest.length)
        throw new Error(
          "Kho đã có chỉ mục. Hãy làm mới trang và tạo chỉ mục mới qua Đổi model.",
        );
      return knowledgeApi.updateCollection(collection.id, {
        data_processing: { ...configured, ...getEmbeddingConfig(selected) },
      });
    },
    onSuccess: () => {
      client.invalidateQueries({
        queryKey: ["knowledge-collection", collection.id],
      });
      client.invalidateQueries({ queryKey: ["collections"] });
      toast.success("Đã chọn Embedding cho lần nạp vector đầu tiên.");
      setIsOpen(false);
    },
    onError: (error) => {
      toast.error(extractErrorMessage(error, "Không đổi được model."));
      client.invalidateQueries({
        queryKey: ["knowledge-vector-generations", collection.id],
      });
    },
  });
  const ocr = models.data?.available_ocrs.find(
    (item) =>
      item.provider_id === models.data?.defaults.default_ocr_provider_id &&
      item.model_name === models.data?.defaults.default_ocr_model,
  );
  const hasError = generations.isError || providers.isError || models.isError;
  return (
    <div className="space-y-2 border-t border-border/50 pt-3">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="min-w-0 space-y-1 text-sm">
          <p className="flex items-start gap-2">
            <Cpu className="size-4 mt-0.5 shrink-0 text-muted-foreground" />
            <span className="break-words">
              <span className="text-muted-foreground">Embedding: </span>
              {generations.isError
                ? "Không tải được chỉ mục"
                : generations.isPending
                  ? "Đang tải…"
                  : active
                    ? getGenerationLabel(active, providers.data)
                    : configured?.embedding_model
                      ? `${configured.embedding_model} · ${provider?.name || configured.embedding_provider_id || "Chưa chọn provider"} (Cấu hình cho chỉ mục mới)`
                      : "Chưa chọn model"}
            </span>
          </p>
          {generations.isSuccess && !active && (
            <p className="text-xs text-muted-foreground">
              Chưa xuất bản chỉ mục cho chatbot.
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            Bóc tách: Tự động ·{" "}
            {models.isPending
              ? "Đang tải OCR…"
              : ocr
                ? `${ocr.model_name} cho trang scan`
                : "OCR theo ModelOps"}
          </p>
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer">Máy chủ &amp; xử lý</summary>
            <p className="mt-1 break-words">
              Embedding:{" "}
              {providers.isPending ? "Đang tải…" : getProviderOrigin(provider)}.
              DOCX qua Docling; PDF có chữ dùng native parser; trang scan chuyển
              OCR. Tùy chọn nâng cao nằm ở Nạp tài liệu/Studio.
            </p>
          </details>
          {hasError && (
            <p role="alert" className="text-xs text-destructive">
              Không tải đủ thông tin model/chỉ mục. Hãy làm mới trang.
            </p>
          )}
        </div>
        {hasGeneration ? (
          <VectorLoadControls
            collectionId={collection.id}
            targets={targets}
            compact
            actionLabel="Đổi model"
            preferNewGeneration
            disabledReason={
              sources.isError || state.isError
                ? "Chưa tải đủ dữ liệu nguồn."
                : !targets.length
                  ? "Cần có nguồn Markdown sẵn sàng để tạo chỉ mục mới."
                  : undefined
            }
          />
        ) : (
          <Button
            size="sm"
            variant="outline"
            disabled={generations.isPending || hasError}
            onClick={() => {
              setSelection("");
              setIsOpen(true);
            }}
          >
            <Pencil className="size-3.5" />
            Đổi model
          </Button>
        )}
      </div>
      <Dialog
        open={isOpen}
        onOpenChange={(open) => {
          if (!save.isPending) setIsOpen(open);
        }}
      >
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Chọn Embedding</DialogTitle>
            <DialogDescription>
              Kho chưa có chỉ mục. Lựa chọn này dùng cho lần Nạp vector đầu
              tiên; không chạy OCR hoặc nạp dữ liệu ngay.
            </DialogDescription>
          </DialogHeader>
          <EmbeddingModelSelect
            models={options}
            value={selectedKey}
            onChange={setSelection}
            disabled={save.isPending}
          />
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsOpen(false)}
              disabled={save.isPending}
            >
              Hủy
            </Button>
            <Button
              disabled={!selected || save.isPending}
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Đang lưu…" : "Lưu"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
