import { useQuery } from "@tanstack/react-query";
import { createApiClient } from "@/app/api/client";
import { BASE_URL, getAuthHeaders } from "@/services/http-client";

export interface BackupRecord {
  id: string;
  created_at: string;
  updated_at: string;
  status: "queued" | "running" | "completed" | "failed" | "unverified";
  operation: "create" | "verify" | "drill" | "import" | "copy";
  stage: string;
  progress: number;
  size_bytes: number;
  sha256: string | null;
  verified_at: string | null;
  drill_at: string | null;
  error: string | null;
  pinned: boolean;
  remote_status:
    | "not_configured"
    | "pending"
    | "copying"
    | "verified"
    | "failed";
  remote_error: string | null;
  stage_started_at: string | null;
  processed_bytes: number;
  total_bytes: number;
  components: Record<string, unknown>;
  history: {
    timestamp: string;
    operation: BackupRecord["operation"];
    status: BackupRecord["status"];
    error: string | null;
  }[];
}

interface Catalogue {
  items: BackupRecord[];
  directory: string;
  scope: string;
  drill_enabled: boolean;
}

const client = createApiClient(BASE_URL);
export const backupKeys = ["system", "backups"] as const;
export type BackupAction = "create" | "verify" | "drill";

export function useBackups() {
  return useQuery({
    queryKey: backupKeys,
    queryFn: () =>
      client.get<Catalogue>("/backups", { headers: getAuthHeaders() }),
    refetchInterval: (query) =>
      query.state.data?.items.some(
        (item) => item.status === "running" || item.status === "queued",
      )
        ? 2000
        : 15000,
  });
}

export function runBackup(
  action: BackupAction,
  passphrase: string,
  backupId?: string,
) {
  const confirmation =
    action === "create"
      ? "BACKUP ALL"
      : action === "verify"
        ? "VERIFY"
        : "ISOLATED DRILL";
  const path =
    action === "create" ? "/backups" : `/backups/${backupId}/${action}`;
  return client.post<BackupRecord>(
    path,
    { passphrase, confirmation },
    { headers: getAuthHeaders() },
  );
}

export async function downloadBackup(backupId: string) {
  // A short-lived HttpOnly scoped cookie lets the browser stream large archives
  // directly to disk, without buffering gigabytes in a JS Blob or leaking tokens in URLs.
  const result = await client.post<{ url: string }>(
    `/backups/${backupId}/download-ticket`,
    undefined,
    { headers: getAuthHeaders() },
  );
  const anchor = document.createElement("a");
  anchor.href = result.url;
  anchor.download = `${backupId}.qnubak`;
  anchor.rel = "noreferrer";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

export const isBackupBusy = (item: BackupRecord) =>
  item.status === "queued" || item.status === "running";
export const statusLabels: Record<BackupRecord["status"], string> = {
  queued: "Đang chờ",
  running: "Đang xử lý",
  completed: "Hoàn tất",
  failed: "Thất bại",
  unverified: "Chưa kiểm chứng",
};

export interface BackupPolicy {
  schedule_enabled: boolean;
  frequency: "daily" | "weekly";
  weekday: number;
  hour: number;
  minute: number;
  utc_offset_minutes: number;
  next_run_at: string | null;
  last_backup_id: string | null;
  notice: string | null;
  remote_enabled: boolean;
  endpoint: string;
  bucket: string;
  prefix: string;
  region: string;
  retention_enabled: boolean;
  keep_daily: number;
  keep_weekly: number;
  keep_monthly: number;
}

export function useBackupPolicy() {
  return useQuery({
    queryKey: [...backupKeys, "policy"],
    queryFn: () =>
      client.get<BackupPolicy>("/backups/policy", {
        headers: getAuthHeaders(),
      }),
    refetchInterval: 15000,
  });
}
export const saveBackupPolicy = (policy: BackupPolicy) =>
  client.put<BackupPolicy>("/backups/policy", policy, {
    headers: getAuthHeaders(),
  });
export const removeBackup = (id: string) =>
  client.delete(`/backups/${id}`, { headers: getAuthHeaders() });
export const pinBackup = (id: string, pinned: boolean) =>
  client.put<BackupRecord>(
    `/backups/${id}/pin`,
    { pinned },
    { headers: getAuthHeaders() },
  );
export const copyBackup = (id: string) =>
  client.post<BackupRecord>(`/backups/${id}/copy`, undefined, {
    headers: getAuthHeaders(),
  });

export function useBackupRecord(id: string) {
  return useQuery({
    queryKey: [...backupKeys, "record", id],
    queryFn: () =>
      client.get<BackupRecord>(`/backups/${id}`, { headers: getAuthHeaders() }),
    refetchInterval: 2000,
  });
}

export function importBackup(
  file: File,
  onProgress: (value: number) => void,
): Promise<BackupRecord> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${BASE_URL}/backups/import`);
    request.withCredentials = true;
    getAuthHeaders().forEach((value, key) => {
      request.setRequestHeader(key, value);
    });
    request.setRequestHeader("Content-Type", "application/octet-stream");
    request.upload.onprogress = (event) => {
      if (event.lengthComputable)
        onProgress((100 * event.loaded) / event.total);
    };
    request.onerror = () =>
      reject(new Error("Kết nối bị gián đoạn; file chưa được kiểm chứng."));
    request.onload = () => {
      try {
        const response = JSON.parse(request.responseText) as BackupRecord & {
          detail?: string;
        };
        if (request.status >= 200 && request.status < 300) resolve(response);
        else reject(new Error(response.detail ?? "Nhập bản sao lưu thất bại."));
      } catch {
        reject(new Error("Máy chủ trả kết quả không hợp lệ."));
      }
    };
    request.send(file);
  });
}
