import { useQuery } from "@tanstack/react-query";
import { getCompilationProgressSummary } from "../compilation/requests";
import { getProcessingProgress } from "../ocr/requests";
import { preparationKeys } from "./queries";
import type { PreparationIntent } from "./types";

export type PreparationProgressData = {
  intentId: string;
  status: string;
  ocrProgress?: {
    pages_done: number;
    pages_total: number | null;
    pagination?: "page" | "document";
  } | null;
  compilationProgress?: {
    completed: number;
    total: number;
    segmented?: boolean;
    elapsedSeconds?: number | null;
  } | null;
};

/**
 * Queries durable progress for only the exact child runs pinned by this intent.
 * Strict invariants:
 * 1. Only reads ocr_run_id or compilation_run_id pinned to this intent; no inference.
 * 2. Does not poll when intent is terminal (ready, failed, cancelled, uncertain).
 */
export function usePreparationProgressQuery(intent?: PreparationIntent) {
  const reading =
    intent?.status === "waiting_ocr" && Boolean(intent.ocr_run_id);
  const compiling =
    intent?.status === "compiling" && Boolean(intent.compilation_run_id);

  return useQuery({
    queryKey: [
      ...preparationKeys.all,
      "progress",
      intent?.workspace_id,
      intent?.collection_id,
      intent?.id,
      intent?.status,
      intent?.ocr_run_id,
      intent?.compilation_run_id,
    ],
    enabled: Boolean(intent && (reading || compiling)),
    queryFn: async ({ signal }): Promise<PreparationProgressData> => {
      if (!intent) throw new Error("Preparation intent is required");

      let ocrProgress = null;
      let compilationProgress = null;

      if (reading && intent.ocr_run_id) {
        const run = await getProcessingProgress(
          intent.workspace_id,
          intent.collection_id,
          intent.source_id,
          intent.revision_id,
          intent.ocr_run_id,
          { signal },
        );
        ocrProgress = {
          pages_done: run.pages_done,
          pages_total: run.pages_total,
          pagination: run.pagination,
        };
      } else if (compiling && intent.compilation_run_id) {
        const run = await getCompilationProgressSummary(
          intent.workspace_id,
          intent.collection_id,
          intent.compilation_run_id,
          { signal },
        );
        compilationProgress = {
          completed: run.completed,
          total: run.total,
          segmented: run.total > 1,
          elapsedSeconds: run.elapsed_seconds,
        };
      }

      return {
        intentId: intent.id,
        status: intent.status,
        ocrProgress,
        compilationProgress,
      };
    },
    refetchInterval: (query) =>
      Math.min(15000, 2500 * 2 ** Math.min(query.state.fetchFailureCount, 3)),
    retry: false,
  });
}
