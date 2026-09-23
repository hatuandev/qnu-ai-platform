import type { IngestionTask } from "@/types/knowledge";
import { BASE_URL } from "./http-client";

const JOB_TYPE_LABEL: Record<
  string,
  { task_name: string; category: IngestionTask["category"] }
> = {
  ingestion: { task_name: "Nạp & bóc tách tài liệu", category: "ingestion" },
  reindex: { task_name: "Nạp lại vector collection", category: "reindex" },
  export: { task_name: "Xuất tài liệu", category: "ingestion" },
};

export function mapJobToIngestionTask(
  j: Record<string, unknown>,
): IngestionTask {
  const jobType = (j.job_type as string) || "ingestion";
  const status = (j.status as string) || "queued";
  const meta = JOB_TYPE_LABEL[jobType] || JOB_TYPE_LABEL.ingestion;
  const created = (j.created_at as string) || "";
  const updated = (j.updated_at as string) || created;
  const payload = (j.payload as Record<string, unknown>) || {};
  const result = (j.result as Record<string, unknown>) || {};
  const durationSeconds = Math.max(
    0,
    Math.round((Date.parse(updated) - Date.parse(created)) / 1000) || 0,
  );
  return {
    id: (j.id as string) || `job_${Date.now()}`,
    task_name: meta.task_name,
    collection_id: (j.collection_id as string) || "",
    collection_code: (j.collection_id as string) || "",
    source_file:
      (payload.filename as string) || (payload.source_file as string) || "",
    file_size_mb:
      typeof payload.file_size_mb === "number" ? payload.file_size_mb : 0,
    worker_name: "arq-worker",
    duration_seconds: durationSeconds,
    category: meta.category,
    progress_percent:
      typeof j.progress === "number" ? Math.round(j.progress as number) : 0,
    status:
      status === "completed"
        ? "completed"
        : status === "failed"
          ? "failed"
          : status === "cancelled"
            ? "cancelled"
            : "processing",
    created_at: created,
    log_output:
      (j.error as string) ||
      (typeof result.points_reindexed === "number"
        ? `Indexed ${result.points_reindexed}/${result.total_chunks || "?"} chunks`
        : undefined),
  };
}

export const jobsApi = {
  async retryJob(jobId: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/jobs/${jobId}/retry`, {
      method: "POST",
    });
    if (!res.ok) {
      throw new Error(`Chạy lại job thất bại (HTTP ${res.status}).`);
    }
  },

  async cancelJob(jobId: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/jobs/${jobId}/cancel`, {
      method: "POST",
    });
    if (!res.ok) {
      throw new Error(`Hủy job thất bại (HTTP ${res.status}).`);
    }
  },

  async deleteJob(jobId: string): Promise<void> {
    let res: Response;
    try {
      res = await fetch(`${BASE_URL}/jobs/${jobId}`, {
        method: "DELETE",
      });
    } catch {
      throw new Error(
        "Không kết nối được máy chủ Backend (kiểm tra service port 8001).",
      );
    }
    if (res.status === 404) {
      return;
    }
    if (!res.ok) {
      throw new Error(`Xóa tác vụ thất bại (HTTP ${res.status}).`);
    }
  },

  async cleanupJobs(collectionId?: string): Promise<{ deleted_count: number }> {
    let res: Response;
    try {
      const url = collectionId
        ? `${BASE_URL}/jobs/cleanup?collection_id=${encodeURIComponent(collectionId)}`
        : `${BASE_URL}/jobs/cleanup`;
      res = await fetch(url, {
        method: "DELETE",
      });
    } catch {
      throw new Error(
        "Không kết nối được máy chủ Backend (kiểm tra service port 8001).",
      );
    }
    if (!res.ok) {
      throw new Error(`Dọn dẹp tác vụ thất bại (HTTP ${res.status}).`);
    }
    return (await res.json()) as { deleted_count: number };
  },

  async getIngestionTasks(collectionId?: string): Promise<IngestionTask[]> {
    try {
      const res = await fetch(`${BASE_URL}/jobs?limit=50`);
      if (res.ok) {
        const data = (await res.json()) as Record<string, unknown>[];
        if (Array.isArray(data)) {
          return data
            .filter(
              (j) =>
                !collectionId || (j.collection_id as string) === collectionId,
            )
            .map((j) => mapJobToIngestionTask(j));
        }
      }
    } catch {
      // Offline / network failure
    }
    return [];
  },
};
