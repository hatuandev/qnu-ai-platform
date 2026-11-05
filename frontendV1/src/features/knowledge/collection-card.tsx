import { Link, useNavigate } from "@tanstack/react-router";
import {
  Archive,
  ChevronRight,
  Eye,
  FileText,
  FolderOpen,
  MoreHorizontal,
  Pencil,
  Trash2,
} from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import type { KBCollection } from "@/features/knowledge/types";
import { cn } from "@/lib/utils";

export type CollectionCardProps = {
  collection: KBCollection;
  workspaceId: string;
  canManage?: boolean;
  canArchive?: boolean;
  canDelete?: boolean;
  onEdit?: (collection: KBCollection) => void;
  onArchive?: (collection: KBCollection) => void;
  onDelete?: (collection: KBCollection) => void;
  customActions?: ReactNode;
  className?: string;
};

export function CollectionCard({
  collection,
  workspaceId,
  canManage = false,
  canArchive = false,
  canDelete = false,
  onEdit,
  onArchive,
  onDelete,
  customActions,
  className,
}: CollectionCardProps) {
  const navigate = useNavigate();

  return (
    <Card
      className={cn(
        "group relative rounded-xl border border-border/70 bg-card transition-all duration-200 hover:border-primary/50 hover:shadow-xs flex flex-col justify-between overflow-hidden",
        className,
      )}
    >
      <CardContent className="p-4 flex flex-col justify-between h-full">
        <div>
          {/* Header row: Icon, Tên kho tri thức & Menu thao tác */}
          <div className="flex items-start justify-between gap-2 mb-2.5">
            <Link
              to="/workspaces/$workspaceId/knowledge/$knowledgeId"
              params={{ workspaceId, knowledgeId: collection.id }}
              search={{ page: 1, pageSize: 20 }}
              className="flex items-center gap-2.5 min-w-0 flex-1 hover:text-primary transition-colors"
            >
              <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                <FolderOpen className="size-4" />
              </span>
              <span className="font-semibold text-sm truncate text-foreground group-hover:text-primary transition-colors">
                {collection.name}
              </span>
            </Link>

            {customActions ?? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="size-7 p-0 text-muted-foreground hover:text-foreground shrink-0 focus-visible:ring-1"
                    aria-label={`Thao tác với ${collection.name}`}
                  >
                    <MoreHorizontal className="size-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48 text-xs">
                  <DropdownMenuItem
                    onClick={() =>
                      void navigate({
                        to: "/workspaces/$workspaceId/knowledge/$knowledgeId",
                        params: { workspaceId, knowledgeId: collection.id },
                        search: { page: 1, pageSize: 20 },
                      })
                    }
                  >
                    <Eye className="size-3.5 mr-2 text-muted-foreground" />
                    <span>Mở kho tri thức</span>
                  </DropdownMenuItem>

                  {canManage && onEdit ? (
                    <DropdownMenuItem onClick={() => onEdit(collection)}>
                      <Pencil className="size-3.5 mr-2 text-muted-foreground" />
                      <span>Sửa thông tin kho</span>
                    </DropdownMenuItem>
                  ) : null}

                  {(canArchive && onArchive) || (canDelete && onDelete) ? (
                    <DropdownMenuSeparator />
                  ) : null}

                  {canArchive && onArchive ? (
                    <DropdownMenuItem onClick={() => onArchive(collection)}>
                      <Archive className="size-3.5 mr-2 text-muted-foreground" />
                      <span>Lưu trữ kho</span>
                    </DropdownMenuItem>
                  ) : null}

                  {canDelete && onDelete ? (
                    <DropdownMenuItem
                      className="text-destructive focus:text-destructive"
                      onClick={() => onDelete(collection)}
                    >
                      <Trash2 className="size-3.5 mr-2" />
                      <span>Xóa kho tri thức</span>
                    </DropdownMenuItem>
                  ) : null}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>

          {/* Mô tả chi tiết */}
          <p className="text-xs text-muted-foreground line-clamp-2 min-h-8 mb-3 leading-relaxed">
            {collection.description ? (
              collection.description
            ) : (
              <span className="italic text-muted-foreground/60">
                Chưa có mô tả chi tiết.
              </span>
            )}
          </p>
        </div>

        {/* Footer: Số lượng tài liệu & Nút Mở kho */}
        <div className="flex items-center justify-between pt-3 border-t border-border/50 text-[11px] text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <FileText className="size-3.5 text-primary/70 shrink-0" />
            <span>
              <strong className="text-foreground font-semibold">
                {collection.source_count}
              </strong>{" "}
              tài liệu
            </span>
          </div>

          <Link
            to="/workspaces/$workspaceId/knowledge/$knowledgeId"
            params={{ workspaceId, knowledgeId: collection.id }}
            search={{ page: 1, pageSize: 20 }}
            className="flex items-center gap-1 text-primary font-medium hover:underline text-xs group-hover:translate-x-0.5 transition-transform"
          >
            <span>Mở kho</span>
            <ChevronRight className="size-3" />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

export function CollectionCardSkeleton({ className }: { className?: string }) {
  return (
    <Card
      className={cn(
        "rounded-xl border border-border/70 p-4 h-[148px] flex flex-col justify-between",
        className,
      )}
    >
      <div>
        <div className="flex items-center justify-between gap-2 mb-2.5">
          <div className="flex items-center gap-2.5 flex-1">
            <Skeleton className="size-8 rounded-lg shrink-0" />
            <Skeleton className="h-4 w-32" />
          </div>
          <Skeleton className="size-7 rounded-md shrink-0" />
        </div>
        <Skeleton className="h-3 w-4/5 mb-2" />
        <Skeleton className="h-3 w-3/5" />
      </div>
      <div className="flex items-center justify-between pt-3 border-t border-border/50">
        <Skeleton className="h-3.5 w-16" />
        <Skeleton className="h-3.5 w-14" />
      </div>
    </Card>
  );
}

