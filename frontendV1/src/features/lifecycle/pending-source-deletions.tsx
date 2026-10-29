import { useQuery } from "@tanstack/react-query";
import { MoreHorizontal } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiProblemError, v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LifecycleActionDialog } from "./action-dialog";
import {
  listLegacyDeletedSources,
  listPendingSourceDeletions,
} from "./requests";
import type { LifecycleAction } from "./types";

type Props = {
  workspaceId: string;
  collectionId: string;
  enabled: boolean;
};

export function PendingSourceDeletions(props: Props) {
  const { sessionId } = useV1Auth();
  return (
    <PendingSourceDeletionsForm
      key={`${sessionId}:${props.workspaceId}:${props.collectionId}`}
      {...props}
    />
  );
}

function PendingSourceDeletionsForm({
  workspaceId,
  collectionId,
  enabled,
}: Props) {
  const { sessionId } = useV1Auth();
  const [selected, setSelected] = useState<{
    resource_id: string;
    title: string;
    initialAction?: LifecycleAction;
  } | null>(null);
  const [offset, setOffset] = useState(0);
  const query = useQuery({
    queryKey: [
      "v1",
      sessionId,
      "source-deletions",
      workspaceId,
      collectionId,
      offset,
    ],
    queryFn: async ({ signal }) => {
      const [pending, legacy] = await Promise.all([
        listPendingSourceDeletions(v1Client, workspaceId, collectionId, signal),
        listLegacyDeletedSources(
          v1Client,
          workspaceId,
          collectionId,
          offset,
          signal,
        ),
      ]);
      return { pending, legacy };
    },
    enabled,
    retry: false,
    refetchInterval: (q) => (q.state.error ? false : 5000),
  });
  if (!enabled) return null;
  const label = (action: LifecycleAction) =>
    String(action.impact.resource_label ?? "Tài liệu");
  return (
    <>
      {query.isError ? (
        <div className="space-y-2 text-sm">
          <p role="alert" className="text-destructive">
            {query.error instanceof ApiProblemError &&
            query.error.code === "http_404"
              ? "Máy chủ chưa nạp chức năng xóa mới. Cần khởi động lại API và worker V1 trước khi tiếp tục."
              : "Không đọc được trạng thái xóa tài liệu. Chưa thể xác nhận việc xóa đã hoàn tất."}
          </p>
          <Button
            size="sm"
            variant="outline"
            disabled={query.isFetching}
            onClick={() => void query.refetch()}
          >
            Tải lại trạng thái
          </Button>
        </div>
      ) : null}
      {query.data?.pending.map((action) => (
        <div
          key={action.id}
          className="flex items-center justify-between gap-3 py-2 text-sm"
        >
          <p>
            {label(action)} —{" "}
            {action.error_code
              ? "Xóa chưa hoàn tất, có thể tiếp tục."
              : "Đang xóa vĩnh viễn…"}
          </p>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="size-7 p-0"
                aria-label="Thao tác xóa"
              >
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem
                onSelect={() =>
                  setSelected({
                    resource_id: action.resource_id,
                    title: label(action),
                    initialAction: action,
                  })
                }
              >
                Theo dõi / tiếp tục xóa
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ))}
      {query.data?.legacy.total ? (
        <section
          className="space-y-2 py-2 text-sm"
          aria-label="Tài liệu đã xóa còn giữ tệp"
        >
          <p className="font-medium">Tài liệu đã xóa còn giữ tệp</p>
          <p className="text-muted-foreground">
            Các tài liệu này đã bị ẩn theo cơ chế cũ. Hoàn tất xóa vĩnh viễn nếu
            muốn tải lại cùng nội dung.
          </p>
          {query.data.legacy.items.map((source) => (
            <div
              key={source.source_id}
              className="flex items-center justify-between gap-3 py-1"
            >
              <span>{source.title}</span>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="size-7 p-0"
                    aria-label={`Thao tác với ${source.title}`}
                  >
                    <MoreHorizontal className="size-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem
                    className="text-destructive"
                    onSelect={() =>
                      setSelected({
                        resource_id: source.source_id,
                        title: source.title,
                      })
                    }
                  >
                    Hoàn tất xóa
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          ))}
          {query.data.legacy.total > 20 || offset > 0 ? (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - 20))}
              >
                Trang trước
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={offset + 20 >= query.data.legacy.total}
                onClick={() => setOffset(offset + 20)}
              >
                Trang sau
              </Button>
            </div>
          ) : null}
        </section>
      ) : null}
      {selected ? (
        <LifecycleActionDialog
          workspaceId={workspaceId}
          target={{
            kind: "source",
            resource_id: selected.resource_id,
            action: "delete",
          }}
          label={selected.title}
          initialAction={selected.initialAction}
          onClose={() => setSelected(null)}
          onCompleted={() => {
            setSelected(null);
            setOffset(0);
            toast.success("Đã xóa vĩnh viễn tài liệu.");
            void query.refetch();
          }}
        />
      ) : null}
    </>
  );
}
