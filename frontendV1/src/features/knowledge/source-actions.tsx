import { useNavigate } from "@tanstack/react-router";
import {
  Archive,
  Download,
  FileText,
  FolderTree,
  MoreVertical,
  Pencil,
  ScanLine,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { v1Client } from "@/app/api/v1";
import type { CallerWorkspaceRole } from "@/app/auth/v1/permissions";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LifecycleActionDialog } from "@/features/lifecycle/action-dialog";
import { canLifecycleAction } from "@/features/lifecycle/permissions";
import type { LifecycleOperation } from "@/features/lifecycle/types";
import { downloadRevisionContent, listRevisions } from "./requests";
import type { KBSource } from "./types";

export function SourceActions({
  workspaceId,
  collectionId,
  source,
  role,
  canManage,
  onRename,
  onMove,
  onOcr,
  onLifecycle,
}: {
  workspaceId: string;
  collectionId: string;
  source: KBSource;
  role?: CallerWorkspaceRole;
  canManage: boolean;
  onRename: () => void;
  onMove: () => void;
  onOcr: () => void;
  onLifecycle?: (operation: LifecycleOperation, source: KBSource) => void;
}) {
  const navigate = useNavigate();
  const [operation, setOperation] = useState<LifecycleOperation | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      const revisions = await listRevisions(
        v1Client,
        workspaceId,
        collectionId,
        source.id,
      );
      const revision = revisions.find(
        (item) => item.revision_no === source.current_revision_no,
      );
      if (!revision)
        throw new Error("Không tìm thấy phiên bản tệp. Hãy tải lại danh sách.");
      const response = await downloadRevisionContent(
        v1Client,
        workspaceId,
        collectionId,
        source.id,
        revision.id,
      );
      const url = URL.createObjectURL(response.blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = revision.file_name;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Không tải được tệp.",
      );
    } finally {
      setIsDownloading(false);
    }
  };
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={`Thao tác: ${source.title}`}
            onClick={(event) => event.stopPropagation()}
          >
            <MoreVertical className="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="end"
          onClick={(event) => event.stopPropagation()}
        >
          <DropdownMenuItem
            onSelect={() =>
              void navigate({
                to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
                params: { workspaceId, collectionId, sourceId: source.id },
              })
            }
          >
            <FileText />
            Xem chi tiết
          </DropdownMenuItem>
          <DropdownMenuItem
            disabled={isDownloading}
            onSelect={() => void handleDownload()}
          >
            <Download />
            {isDownloading ? "Đang tải…" : "Tải xuống"}
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={onOcr}>
            <ScanLine />
            OCR & hiệu đính
          </DropdownMenuItem>
          {canManage && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={onRename}>
                <Pencil />
                Đổi tên
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={onMove}>
                <FolderTree />
                Di chuyển thư mục
              </DropdownMenuItem>
            </>
          )}
          {canLifecycleAction(role, "source", "archive") && (
            <DropdownMenuItem
              onSelect={() =>
                onLifecycle
                  ? onLifecycle("archive", source)
                  : setOperation("archive")
              }
            >
              <Archive />
              Lưu trữ
            </DropdownMenuItem>
          )}
          {canLifecycleAction(role, "source", "delete") && (
            <DropdownMenuItem
              className="text-destructive"
              onSelect={() =>
                onLifecycle
                  ? onLifecycle("delete", source)
                  : setOperation("delete")
              }
            >
              <Trash2 />
              Xóa vĩnh viễn
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
      {operation && (
        <LifecycleActionDialog
          workspaceId={workspaceId}
          target={{ kind: "source", resource_id: source.id, action: operation }}
          label={source.title}
          onClose={() => setOperation(null)}
          onCompleted={() => {
            setOperation(null);
            toast.success(
              operation === "delete"
                ? "Đã xóa vĩnh viễn tài liệu."
                : "Đã lưu trữ tài liệu.",
            );
          }}
        />
      )}
    </>
  );
}
