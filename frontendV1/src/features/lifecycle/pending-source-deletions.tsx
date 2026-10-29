import { useQuery } from "@tanstack/react-query";
import { MoreHorizontal } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LifecycleActionDialog } from "./action-dialog";
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
  const [selected, setSelected] = useState<LifecycleAction | null>(null);
  const query = useQuery({
    queryKey: ["v1", sessionId, "source-deletions", workspaceId, collectionId],
    queryFn: ({ signal }) =>
      v1Client.get<LifecycleAction[]>(
        `/workspaces/${encodeURIComponent(workspaceId)}/lifecycle/source-deletions`,
        { searchParams: { collection_id: collectionId }, signal },
      ),
    enabled,
    retry: false,
    refetchInterval: 5000,
  });
  if (!enabled) return null;
  const label = (action: LifecycleAction) =>
    String(action.impact.resource_label ?? "Tài liệu");
  return (
    <>
      {query.isError ? (
        <p role="alert" className="text-sm text-destructive">
          Không đọc được trạng thái xóa tài liệu. Hãy tải lại trang.
        </p>
      ) : null}
      {query.data?.map((action) => (
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
              <DropdownMenuItem onSelect={() => setSelected(action)}>
                Theo dõi / tiếp tục xóa
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ))}
      {selected ? (
        <LifecycleActionDialog
          workspaceId={workspaceId}
          target={{
            kind: "source",
            resource_id: selected.resource_id,
            action: "delete",
          }}
          label={label(selected)}
          initialAction={selected}
          onClose={() => setSelected(null)}
          onCompleted={() => {
            setSelected(null);
            toast.success("Đã xóa vĩnh viễn tài liệu.");
            void query.refetch();
          }}
        />
      ) : null}
    </>
  );
}
