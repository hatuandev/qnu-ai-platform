import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Button } from "@/components/ui/button";
import {
  getIndexRun,
  listIndexRuns,
} from "@/features/knowledge/index-requests";
import type { IndexRun } from "@/features/knowledge/index-types";
import { canManageKnowledge } from "@/features/knowledge/permissions";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { EvaluationForm } from "./evaluation-form";
import { getEvaluationManifest } from "./requests";

type Props = {
  workspaceId: string;
  collectionId: string;
  page: number;
  runId?: string;
  onSearch: (patch: { page?: number; runId?: string }) => void;
};
export function EvaluationPage(props: Props) {
  const { sessionId } = useV1Auth();
  const { role, isPending } = useCallerWorkspaceRole(props.workspaceId);
  if (isPending) return <p role="status">Đang kiểm tra quyền đánh giá…</p>;
  if (!canManageKnowledge(role))
    return (
      <p role="alert">Cần quyền quản trị hoặc biên tập để chạy đánh giá.</p>
    );
  return (
    <EvaluationSession
      key={`${sessionId}:${props.workspaceId}:${props.collectionId}`}
      {...props}
    />
  );
}
function EvaluationSession({
  workspaceId,
  collectionId,
  page,
  runId,
  onSearch,
}: Props) {
  const { sessionId } = useV1Auth();
  const runs = useQuery({
    queryKey: [
      "v1",
      sessionId,
      "evaluation-runs",
      workspaceId,
      collectionId,
      page,
    ],
    queryFn: ({ signal }) =>
      listIndexRuns(
        v1Client,
        workspaceId,
        collectionId,
        { limit: 21, offset: (page - 1) * 20 },
        { signal },
      ),
    retry: false,
  });
  return (
    <div className="space-y-5">
      <Button variant="ghost" size="sm" asChild>
        <Link
          to="/workspaces/$workspaceId/collections/$collectionId"
          params={{ workspaceId, collectionId }}
          search={{ page: 1, pageSize: 20, tab: "index" }}
        >
          Về bộ sưu tập
        </Link>
      </Button>
      <div>
        <h1 className="type-page-title">Đánh giá truy xuất RAG</h1>
        <p className="text-sm text-muted-foreground">
          So sánh tìm vector, kết hợp từ khóa và xếp hạng lại trên cùng snapshot
          đang phục vụ.
        </p>
      </div>
      {runs.isPending ? (
        <p role="status">Đang đọc các đợt chỉ mục…</p>
      ) : runs.isError ? (
        <ErrorState error={runs.error} onRetry={() => void runs.refetch()} />
      ) : (
        <section className="rounded-lg border p-4 space-y-3">
          <h2 className="font-semibold text-sm">Chọn snapshot</h2>
          <ul className="space-y-2">
            {runs.data.slice(0, 20).map((run) => (
              <li
                key={run.id}
                className="flex flex-wrap items-center justify-between gap-2 text-sm"
              >
                <span>
                  Chỉ mục #{run.generation} · {run.chunks_total} đoạn ·{" "}
                  {run.is_active ? "Đang phục vụ" : "Không phục vụ"}
                </span>
                <Button
                  variant={runId === run.id ? "secondary" : "outline"}
                  size="sm"
                  disabled={
                    !run.is_active ||
                    run.status !== "completed" ||
                    !run.manifest_sha256
                  }
                  onClick={() => onSearch({ runId: run.id })}
                >
                  Chọn snapshot
                </Button>
              </li>
            ))}
          </ul>
          {runs.data.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Chưa có chỉ mục trên trang này.
            </p>
          ) : null}
          <div className="flex justify-end gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={page <= 1}
              onClick={() => onSearch({ page: page - 1 })}
            >
              Trang trước
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={runs.data.length <= 20}
              onClick={() => onSearch({ page: page + 1 })}
            >
              Trang sau
            </Button>
          </div>
        </section>
      )}
      {runId ? (
        <EvaluationSnapshot
          key={runId}
          workspaceId={workspaceId}
          collectionId={collectionId}
          runId={runId}
        />
      ) : (
        <p className="text-sm text-muted-foreground">
          Chọn snapshot để soạn bộ câu hỏi và gán nhãn.
        </p>
      )}
    </div>
  );
}
function EvaluationSnapshot({
  workspaceId,
  collectionId,
  runId,
}: {
  workspaceId: string;
  collectionId: string;
  runId: string;
}) {
  const { sessionId } = useV1Auth();
  const query = useQuery({
    queryKey: [
      "v1",
      sessionId,
      "evaluation-run",
      workspaceId,
      collectionId,
      runId,
    ],
    queryFn: ({ signal }) =>
      getIndexRun(v1Client, workspaceId, collectionId, runId, { signal }),
    retry: false,
    refetchInterval: 5000,
  });
  if (query.isPending) return <p role="status">Đang kiểm tra snapshot…</p>;
  if (query.isError)
    return (
      <ErrorState error={query.error} onRetry={() => void query.refetch()} />
    );
  if (
    !query.data.is_active ||
    query.data.status !== "completed" ||
    !query.data.manifest_sha256
  )
    return (
      <p role="alert" className="text-sm text-warning">
        Snapshot không còn đang phục vụ hoặc chưa hoàn tất. Chọn lại snapshot
        hiện hành.
      </p>
    );
  return (
    <ManifestForm
      key={`${runId}:${query.data.manifest_sha256}`}
      workspaceId={workspaceId}
      collectionId={collectionId}
      run={query.data}
    />
  );
}
function ManifestForm({
  workspaceId,
  collectionId,
  run,
}: {
  workspaceId: string;
  collectionId: string;
  run: IndexRun;
}) {
  const { sessionId } = useV1Auth();
  const query = useQuery({
    queryKey: [
      "v1",
      sessionId,
      "evaluation-manifest",
      workspaceId,
      collectionId,
      run.id,
      run.manifest_sha256,
    ],
    queryFn: ({ signal }) =>
      getEvaluationManifest(
        v1Client,
        workspaceId,
        collectionId,
        run.id,
        signal,
      ),
    retry: false,
  });
  if (query.isPending) return <p role="status">Đang đọc bản kê chỉ mục…</p>;
  if (query.isError)
    return (
      <ErrorState error={query.error} onRetry={() => void query.refetch()} />
    );
  if (query.data.run_id !== run.id || query.data.generation !== run.generation)
    return (
      <p role="alert">Bản kê không khớp snapshot. Tải lại trang để kiểm tra.</p>
    );
  return (
    <>
      <p className="text-xs text-muted-foreground break-all">
        Đang ghim chỉ mục #{run.generation} · SHA-256: {run.manifest_sha256}
      </p>
      <EvaluationForm
        workspaceId={workspaceId}
        collectionId={collectionId}
        run={run}
        manifest={query.data}
      />
    </>
  );
}
