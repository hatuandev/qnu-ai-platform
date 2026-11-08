import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Loader2 } from "lucide-react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { getDocumentIndexReadiness } from "./index-requests";
import type { VersionResponse } from "./publication-types";

type SearchSync = {
  status:
    | "not_requested"
    | "pending"
    | "building"
    | "ready"
    | "failed"
    | "uncertain";
  revision: number;
  error_code: string | null;
};

export function useSearchAvailability(
  workspaceId: string,
  collectionId: string,
  documentId: string,
  version:
    | Pick<VersionResponse, "id" | "status" | "state_version" | "bundle_sha256">
    | undefined,
) {
  const { sessionId } = useV1Auth();
  const client = useQueryClient();
  const path = `/workspaces/${encodeURIComponent(workspaceId)}/collections/${encodeURIComponent(collectionId)}/search-readiness`;
  const key = ["search-availability", sessionId, workspaceId, collectionId];
  const sync = useQuery({
    queryKey: [...key, version?.id, version?.state_version],
    queryFn: ({ signal }) => v1Client.get<SearchSync>(path, { signal }),
    enabled: Boolean(version?.status === "published"),
    retry: false,
    refetchInterval: (query) =>
      query.state.data?.status === "pending" ||
      query.state.data?.status === "building"
        ? 3000
        : false,
  });
  const isUpdating =
    sync.data?.status === "pending" || sync.data?.status === "building";
  const readiness = useQuery({
    queryKey: [
      ...key,
      "document",
      documentId,
      version?.id,
      version?.state_version,
      sync.data?.revision,
      sync.data?.status,
    ],
    queryFn: ({ signal }) =>
      getDocumentIndexReadiness(
        v1Client,
        workspaceId,
        collectionId,
        documentId,
        { signal },
      ),
    enabled: Boolean(version?.status === "published"),
    retry: false,
    refetchInterval: isUpdating ? 3000 : false,
  });
  const retry = useMutation({
    mutationFn: (idempotencyKey: string) =>
      v1Client.post<SearchSync>(`${path}/retry`, {}, { idempotencyKey }),
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
  const isReady =
    !readiness.isError &&
    readiness.data?.status === "ready" &&
    readiness.data.version_id === version?.id &&
    readiness.data.version_state === version?.state_version &&
    readiness.data.bundle_sha256 === version?.bundle_sha256;
  return { sync, readiness, retry, isReady, isUpdating };
}

export function SearchAvailability({
  state,
  canRetry,
}: {
  state: ReturnType<typeof useSearchAvailability>;
  canRetry: boolean;
}) {
  const { sync, readiness, retry, isReady, isUpdating } = state;
  if (isReady)
    return (
      <p role="status" className="text-sm text-success">
        Sẵn sàng tra cứu cho trợ lý AI.
      </p>
    );
  if (
    !(sync.isError || readiness.isError) &&
    (sync.isPending || readiness.isPending || isUpdating)
  ) {
    return (
      <p
        role="status"
        className="flex items-center gap-2 text-sm text-muted-foreground"
      >
        <Loader2 className="size-4 animate-spin" />
        Đang cập nhật cho trợ lý AI… Bạn có thể rời trang.
      </p>
    );
  }
  const hasFailed =
    sync.data?.status === "failed" || sync.data?.status === "uncertain";
  return (
    <Alert variant="destructive">
      <AlertCircle className="size-4" />
      <AlertDescription>
        <p>
          {sync.isError || readiness.isError
            ? "Chưa xác minh được trạng thái phục vụ trợ lý."
            : hasFailed
              ? "Tài liệu đã xuất bản, nhưng cập nhật tìm kiếm chưa hoàn tất."
              : "Tài liệu chưa được cập nhật cho trợ lý AI."}
        </p>
        {(sync.isError || readiness.isError) && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              void sync.refetch();
              void readiness.refetch();
            }}
          >
            Kiểm tra lại
          </Button>
        )}
        {sync.data?.status === "uncertain" && (
          <p>
            Yêu cầu trước chưa xác định kết quả. Chạy lại sẽ tạo tác vụ mới.
          </p>
        )}
        {retry.isError && (
          <p>
            Không gửi được yêu cầu cập nhật. Hãy kiểm tra kết nối và thử lại.
          </p>
        )}
        {canRetry && (hasFailed || sync.data?.status === "not_requested") && (
          <Button
            variant="outline"
            size="sm"
            disabled={retry.isPending}
            onClick={() => retry.mutate(crypto.randomUUID())}
          >
            Thử cập nhật
          </Button>
        )}
        {canRetry && sync.data?.error_code && (
          <details className="mt-2">
            <summary>Chi tiết kỹ thuật</summary>
            <code>{sync.data.error_code}</code>
          </details>
        )}
      </AlertDescription>
    </Alert>
  );
}
