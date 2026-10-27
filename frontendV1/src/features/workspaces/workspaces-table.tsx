import { ChevronRight, PauseCircle, PlayCircle, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Workspace } from "@/features/workspaces/types";
import { formatDateTimeValue } from "@/lib/date-utils";

function WorkspaceStatusBadge({ status }: { status: Workspace["status"] }) {
  return status === "active" ? (
    <Badge variant="success">Đang hoạt động</Badge>
  ) : (
    <Badge variant="destructive">Tạm dừng</Badge>
  );
}

export function WorkspacesTable({
  workspaces,
  isLoading,
  onOpen,
}: {
  workspaces: Workspace[];
  isLoading: boolean;
  onOpen: (workspace: Workspace) => void;
}) {
  if (isLoading) {
    return (
      <div className="grid gap-2 p-4">
        {[0, 1, 2, 3].map((row) => (
          <Skeleton key={row} className="h-11 w-full" />
        ))}
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-[160px]">Mã</TableHead>
          <TableHead>Tên workspace</TableHead>
          <TableHead className="w-[150px]">Trạng thái</TableHead>
          <TableHead className="w-[120px]">Thành viên</TableHead>
          <TableHead className="hidden w-[170px] lg:table-cell">
            Cập nhật
          </TableHead>
          <TableHead className="w-[60px] text-right">
            <span className="sr-only">Mở</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {workspaces.map((workspace) => (
          <TableRow key={workspace.id}>
            <TableCell className="font-mono text-xs">
              {workspace.code}
            </TableCell>
            <TableCell>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{workspace.name}</p>
                {workspace.description ? (
                  <p className="truncate text-xs text-muted-foreground">
                    {workspace.description}
                  </p>
                ) : null}
              </div>
            </TableCell>
            <TableCell>
              <WorkspaceStatusBadge status={workspace.status} />
            </TableCell>
            <TableCell className="text-sm">
              <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                <Users className="size-3.5" />
                {workspace.member_count}
              </span>
            </TableCell>
            <TableCell className="hidden text-xs text-muted-foreground lg:table-cell">
              {formatDateTimeValue(workspace.updated_at)}
            </TableCell>
            <TableCell className="text-right">
              <Button
                size="sm"
                variant="ghost"
                className="gap-1 text-xs"
                onClick={() => onOpen(workspace)}
                aria-label={`Mở workspace ${workspace.name}`}
              >
                <span className="hidden sm:inline">Mở</span>
                <ChevronRight className="size-3.5" />
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function WorkspaceStatusHint({
  status,
}: {
  status: Workspace["status"];
}) {
  if (status === "active") {
    return (
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <PlayCircle className="size-3.5 text-success" />
        Thành viên truy cập được nội dung workspace.
      </p>
    );
  }
  return (
    <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <PauseCircle className="size-3.5 text-destructive" />
      Workspace tạm dừng: backendV1 trả 403 <code>workspace_suspended</code> cho
      thành viên không phải quản trị nền tảng.
    </p>
  );
}
