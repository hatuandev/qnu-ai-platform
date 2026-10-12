import type { KnowledgeBinding, VectorLoadState } from "@/types/knowledge";

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
      label: job.status === "queued" ? "Chờ worker" : "Đang nạp",
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
        getSourceVectorState(source, generationId, state).isReady,
    )
  );
}
