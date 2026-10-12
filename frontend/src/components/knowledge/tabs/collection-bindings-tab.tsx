import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import {
  FileText,
  Layers,
  RefreshCw,
  RotateCcw,
  Scan,
  Settings2,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { DeleteSourceButton } from "@/features/knowledge/components/delete-source-button";
import { PauseSourceButton } from "@/features/knowledge/components/pause-source-button";
import { useVectorWorkflow } from "@/features/knowledge/components/use-vector-workflow";
import { VectorLoadControls } from "@/features/knowledge/components/vector-load-controls";
import { getSourceVectorState } from "@/features/knowledge/utils/vector-workflow";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";
import type { KnowledgeCollection } from "@/types/knowledge";

export function CollectionBindingsTab({
  collection,
}: {
  collection: KnowledgeCollection;
}) {
  const navigate = useNavigate();
  const client = useQueryClient();
  const { sources, generations, state } = useVectorWorkflow(collection.id);
  const [selectedGenerationId, setSelectedGenerationId] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [isAdvanced, setIsAdvanced] = useState(false);
  const [isRollbackOpen, setIsRollbackOpen] = useState(false);
  const effectiveId =
    selectedGenerationId ||
    generations.data?.find((generation) => generation.status === "active")
      ?.id ||
    generations.data?.[0]?.id ||
    "";
  const selected = generations.data?.find(
    (generation) => generation.id === effectiveId,
  );
  const visible = (sources.data || []).filter((source) =>
    (source.document_title || source.id)
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  const selectable = visible.filter(
    (source) =>
      source.status === "active" &&
      source.source_status === "ready" &&
      !!source.active_source_revision_id,
  );
  const targets = (sources.data || [])
    .filter(
      (source) =>
        selectedIds.includes(source.id) &&
        source.status === "active" &&
        source.source_status === "ready" &&
        !!source.active_source_revision_id,
    )
    .map((source) => ({
      binding_id: source.id,
      source_revision_id: source.active_source_revision_id || "",
    }));
  const refresh = () => {
    for (const key of [
      "knowledge-bindings",
      "knowledge-vector-generations",
      "knowledge-vector-load",
      "knowledge-collection",
      "collection-summary-metrics",
    ])
      client.invalidateQueries({ queryKey: [key, collection.id] });
  };
  const rollback = useMutation({
    mutationFn: () =>
      knowledgeApi.rollbackVectorGeneration(collection.id, effectiveId),
    onSuccess: () => {
      toast.success("Đã khôi phục chỉ mục.");
      setIsRollbackOpen(false);
      refresh();
    },
    onError: (error) =>
      toast.error(extractErrorMessage(error, "Khôi phục thất bại.")),
  });
  return (
    <div className="space-y-5">
      <section className="space-y-3 rounded-lg border border-border p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 font-semibold">
            <Layers className="size-4" />
            Markdown → Vector → Chatbot
          </h2>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setIsAdvanced(!isAdvanced)}
            aria-expanded={isAdvanced}
          >
            <Settings2 className="size-3.5" />
            Nâng cao
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          Mở Studio để kiểm tra Markdown sạch, chọn nguồn rồi nạp vector. Xuất
          bản sau khi nạp hoàn tất để chatbot sử dụng.
        </p>
        {isAdvanced && (
          <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">
            <Select value={effectiveId} onValueChange={setSelectedGenerationId}>
              <SelectTrigger
                className="w-full sm:w-80"
                aria-label="Chỉ mục vector"
              >
                <SelectValue placeholder="Chưa có chỉ mục vector" />
              </SelectTrigger>
              <SelectContent>
                {generations.data?.map((generation) => (
                  <SelectItem key={generation.id} value={generation.id}>
                    {generation.embedding_model} ·{" "}
                    {generation.embedding_dimension}d · Bản{" "}
                    {generation.generation_epoch} · {generation.status}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              disabled={rollback.isPending || selected?.status !== "retired"}
              onClick={() => setIsRollbackOpen(true)}
            >
              <RotateCcw className="size-3.5" />
              Khôi phục
            </Button>
          </div>
        )}
        {generations.isError && (
          <p role="alert" className="text-sm text-destructive">
            Không tải được cấu hình vector.
          </p>
        )}
      </section>
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <Input
          className="sm:w-80"
          aria-label="Tìm nguồn"
          placeholder="Tìm nguồn..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-muted-foreground">
            Đã chọn {targets.length}
          </span>
          <Button variant="outline" size="sm" onClick={refresh}>
            <RefreshCw className="size-3.5" />
            Làm mới
          </Button>
          <VectorLoadControls
            collectionId={collection.id}
            targets={targets}
            initialGenerationId={effectiveId}
          />
        </div>
      </div>
      {sources.isPending || state.isPending ? (
        <p className="text-sm text-muted-foreground">
          Đang tải nguồn và trạng thái vector…
        </p>
      ) : sources.isError || state.isError ? (
        <p role="alert" className="text-destructive">
          {extractErrorMessage(
            sources.error || state.error,
            "Không tải được nguồn hoặc trạng thái vector.",
          )}
          <Button variant="outline" onClick={refresh}>
            Thử lại
          </Button>
        </p>
      ) : sources.isLoading ? (
        <p className="text-muted-foreground">Đang tải nguồn...</p>
      ) : (
        <div className="w-full overflow-x-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>
                  <Checkbox
                    aria-label="Chọn các nguồn sẵn sàng"
                    disabled={!selectable.length}
                    checked={
                      selectable.length > 0 &&
                      selectable.every((source) =>
                        selectedIds.includes(source.id),
                      )
                    }
                    onCheckedChange={(checked) =>
                      setSelectedIds(
                        checked
                          ? [
                              ...new Set([
                                ...selectedIds,
                                ...selectable.map((source) => source.id),
                              ]),
                            ]
                          : selectedIds.filter(
                              (id) =>
                                !selectable.some((source) => source.id === id),
                            ),
                      )
                    }
                  />
                </TableHead>
                <TableHead>Nguồn tài liệu</TableHead>
                <TableHead>Markdown sạch</TableHead>
                <TableHead>
                  Vector{selected ? ` · ${selected.embedding_model}` : ""}
                </TableHead>
                <TableHead className="text-right">Thao tác</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((source) => {
                const vector = getSourceVectorState(
                  source,
                  effectiveId,
                  state.data,
                );
                const canLoad =
                  source.status === "active" &&
                  source.source_status === "ready" &&
                  !!source.active_source_revision_id;
                return (
                  <TableRow key={source.id}>
                    <TableCell>
                      <Checkbox
                        aria-label={`Chọn ${source.document_title || source.id}`}
                        checked={selectedIds.includes(source.id)}
                        disabled={!canLoad}
                        onCheckedChange={(checked) =>
                          setSelectedIds(
                            checked
                              ? [...selectedIds, source.id]
                              : selectedIds.filter((id) => id !== source.id),
                          )
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <span className="font-medium">
                        {source.document_title || source.id}
                      </span>
                      <p className="text-xs text-muted-foreground">
                        {source.file_name}
                      </p>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={
                          source.source_status === "ready"
                            ? "border-success/30 bg-success/10 text-success"
                            : "border-warning/30 bg-warning/10 text-warning"
                        }
                      >
                        {source.source_status === "ready"
                          ? "MD sẵn sàng"
                          : "Chờ xử lý / duyệt"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={
                          vector.isReady
                            ? "border-success/30 bg-success/10 text-success"
                            : "text-muted-foreground"
                        }
                      >
                        {vector.label}
                      </Badge>
                      {vector.error && (
                        <p className="mt-1 max-w-xs text-xs text-destructive">
                          {vector.error}
                        </p>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1.5">
                        <VectorLoadControls
                          compact
                          collectionId={collection.id}
                          initialGenerationId={effectiveId}
                          targets={
                            canLoad
                              ? [
                                  {
                                    binding_id: source.id,
                                    source_revision_id:
                                      source.active_source_revision_id || "",
                                  },
                                ]
                              : []
                          }
                          disabledReason={
                            canLoad
                              ? undefined
                              : "Hãy bóc tách và duyệt Markdown trước."
                          }
                        />
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            navigate({
                              to: "/knowledge/$collectionId/sources/$sourceId",
                              search: { view: "studio", revision: undefined },
                              params: {
                                collectionId: collection.id,
                                sourceId: source.id,
                              },
                            })
                          }
                        >
                          <Scan className="size-3.5" />
                          Studio OCR
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            navigate({
                              to: "/knowledge/$collectionId/sources/$sourceId",
                              search: { view: undefined, revision: undefined },
                              params: {
                                collectionId: collection.id,
                                sourceId: source.id,
                              },
                            })
                          }
                        >
                          <FileText className="size-3.5" />
                          Chi tiết
                        </Button>
                        <PauseSourceButton
                          sourceId={source.id}
                          title={source.document_title || source.id}
                          status={source.status}
                        />
                        <DeleteSourceButton
                          sourceId={source.id}
                          status={source.status}
                          title={source.document_title || source.id}
                          onDeleted={refresh}
                        />
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
              {!visible.length && (
                <TableRow>
                  <TableCell
                    colSpan={5}
                    className="text-center text-muted-foreground"
                  >
                    {search
                      ? "Không có nguồn phù hợp bộ lọc."
                      : "Chưa có nguồn. Chọn Thêm nguồn để lấy tài liệu từ kho lưu trữ."}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      )}
      <ConfirmDialog
        open={isRollbackOpen}
        onOpenChange={setIsRollbackOpen}
        title="Khôi phục chỉ mục?"
        description="Chỉ mục đã lưu trữ sẽ được đối soát và đưa trở lại phục vụ chatbot."
        variant="default"
        confirmText="Khôi phục"
        isPending={rollback.isPending}
        onConfirm={() => rollback.mutate()}
      />
    </div>
  );
}
