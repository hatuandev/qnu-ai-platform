import type {
  KnowledgeBinding,
  PublishVectorItem,
  VectorLoadItem,
  VectorLoadState,
} from "@/types/knowledge";

export function getSelectedPublishItems(
  sources: KnowledgeBinding[],
  targets: VectorLoadItem[],
  generationId: string,
  state?: VectorLoadState,
): PublishVectorItem[] {
  return targets.flatMap((target) => {
    const source = sources.find((item) => item.id === target.binding_id);
    const index = state?.indexes.find(
      (item) =>
        item.binding_id === target.binding_id &&
        item.source_revision_v2_id === target.source_revision_id &&
        item.vector_generation_id === generationId &&
        ["ready", "active"].includes(item.status),
    );
    if (
      source?.status !== "active" ||
      source.source_status !== "ready" ||
      source.requires_structured_review ||
      source.active_source_revision_id !== target.source_revision_id ||
      !index ||
      !getSourceVectorState(source, generationId, state).isReady
    )
      return [];
    return [{ ...target, index_revision_id: index.id }];
  });
}

export function canPublishSelectedSources(
  sources: KnowledgeBinding[],
  targets: VectorLoadItem[],
  generationId: string,
  activeGenerationId: string | undefined,
  state?: VectorLoadState,
) {
  const selected = new Set(targets.map((item) => item.binding_id));
  return (
    !!generationId &&
    targets.length > 0 &&
    selected.size === targets.length &&
    getSelectedPublishItems(sources, targets, generationId, state).length ===
      targets.length &&
    (activeGenerationId === generationId ||
      sources.every(
        (source) =>
          source.status !== "active" ||
          !source.active_index_revision_id ||
          selected.has(source.id),
      ))
  );
}

export function getSelectedReviewBlockers(
  sources: KnowledgeBinding[],
  selectedBindingIds: string[],
) {
  const selectedIds = new Set(selectedBindingIds);
  return sources.filter(
    (source) =>
      selectedIds.has(source.id) &&
      source.status !== "paused" &&
      source.requires_structured_review &&
      source.active_source_revision_id,
  );
}

export function getSourceVectorState(
  source: KnowledgeBinding,
  generationId: string,
  state?: VectorLoadState,
) {
  if (source.status === "paused")
    return { label: "Đã ngừng dùng", isPending: false, isReady: false };
  const job = state?.jobs.find(
    (item) =>
      item.payload.binding_id === source.id &&
      item.payload.generation_id === generationId &&
      item.payload.source_revision_id === source.active_source_revision_id,
  );
  const index = state?.indexes.find(
    (item) =>
      item.binding_id === source.id &&
      item.vector_generation_id === generationId &&
      item.source_revision_v2_id === source.active_source_revision_id,
  );
  if (job && ["queued", "running"].includes(job.status))
    return {
      label:
        job.status === "queued"
          ? "Chờ worker"
          : job.phase === "waiting_embedding"
            ? "Chờ embedding"
            : "Đang nạp",
      isPending: true,
      isReady: false,
      error: job.error,
    };
  if (index && ["ready", "active"].includes(index.status))
    return {
      label:
        source.active_index_revision_id === index.id
          ? "Đang phục vụ chatbot"
          : "Đã nạp · Chờ xuất bản",
      isPending: false,
      isReady: true,
    };
  if (index?.status === "failed" || job?.status === "failed")
    return {
      label: "Nạp lỗi",
      isPending: false,
      isReady: false,
      error: index?.failure_detail || job?.error,
    };
  return { label: "Chưa nạp vector", isPending: false, isReady: false };
}

export function canPublishSources(
  sources: KnowledgeBinding[],
  generationId: string,
  state?: VectorLoadState,
) {
  const activeSources = sources.filter((source) => source.status !== "paused");
  return (
    activeSources.length > 0 &&
    !!generationId &&
    activeSources.every(
      (source) =>
        source.source_status === "ready" &&
        !source.requires_structured_review &&
        getSourceVectorState(source, generationId, state).isReady,
    )
  );
}
