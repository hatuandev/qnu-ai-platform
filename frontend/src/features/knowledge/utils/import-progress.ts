import type { KnowledgeImportItemResponse } from "@/types/knowledge";

type ProgressItem = Pick<KnowledgeImportItemResponse, "status" | "progress">;

export function getItemProgress(item: ProgressItem): number {
  if (item.status === "succeeded") return 100;
  if (item.status === "queued") return 0;
  const value = item.progress || 0;
  return Number.isFinite(value) ? Math.max(0, Math.min(99, value)) : 0;
}

export function getBatchProgress(items: ProgressItem[]): number {
  return items.length
    ? Math.round(
        items.reduce((sum, item) => sum + getItemProgress(item), 0) /
          items.length,
      )
    : 0;
}
