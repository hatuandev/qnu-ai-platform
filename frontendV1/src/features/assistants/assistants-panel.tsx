import { Link } from "@tanstack/react-router";
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  ChevronRight,
  Database,
  ExternalLink,
  MessageSquare,
  Pencil,
  Plus,
  Search,
} from "lucide-react";
import { useMemo, useState } from "react";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AssistantFormDialog } from "@/features/assistants/assistant-form-dialog";
import { canManageAssistants } from "@/features/assistants/permissions";
import { useAssistantsQuery } from "@/features/assistants/queries";
import type { Assistant } from "@/features/assistants/types";
import { ConversationCreateDialog } from "@/features/conversations/conversation-create-dialog";
import { useCollectionsQuery } from "@/features/knowledge/queries";
import { LifecycleActions } from "@/features/lifecycle/lifecycle-actions";
import { useCatalogQuery } from "@/features/modelops/queries";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { DEFAULT_PAGE_SEARCH } from "@/features/workspaces/search";
import { formatDateTimeValue } from "@/lib/date-utils";

export function AssistantsPanel({
  workspaceId,
  limit,
  offset,
  onOffsetChange,
}: {
  workspaceId: string;
  limit: number;
  offset: number;
  onOffsetChange: (offset: number) => void;
}) {
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const assistantsQuery = useAssistantsQuery(workspaceId, { limit, offset });

  // Collections and catalog for human-readable labels
  const collectionsQuery = useCollectionsQuery(workspaceId, {
    page: 1,
    pageSize: 100,
  });
  const catalogQuery = useCatalogQuery(workspaceId);

  const [searchQuery, setSearchQuery] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [editingAssistant, setEditingAssistant] = useState<Assistant | null>(
    null,
  );
  const [chatAssistant, setChatAssistant] = useState<Assistant | null>(null);

  const canManage = !rolePending && canManageAssistants(role);

  const rawItems = assistantsQuery.data ?? [];

  // Client-side quick filter on currently loaded batch (honest about scope)
  const filteredItems = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return rawItems;
    return rawItems.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q) ||
        item.collection_id.toLowerCase().includes(q),
    );
  }, [rawItems, searchQuery]);

  // Lookup maps for collections & models
  const collectionMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const col of collectionsQuery.data?.items ?? []) {
      map.set(col.id, col.name);
    }
    return map;
  }, [collectionsQuery.data?.items]);

  const catalogMap = useMemo(() => {
    const map = new Map<string, { name: string; model_name: string }>();
    for (const item of catalogQuery.data ?? []) {
      map.set(item.id, { name: item.name, model_name: item.model_name });
    }
    return map;
  }, [catalogQuery.data]);

  const hasPrevious = offset > 0;
  const hasNext = rawItems.length === limit;

  return (
    <div className="space-y-6">
      {/* Header & Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-foreground flex items-center gap-2">
            <Bot className="size-5 text-primary" />
            Trợ lý AI
          </h2>
          <p className="type-supporting text-muted-foreground">
            Quản lý các trợ lý AI gắn với kho tri thức và model chat được cấp
            phép cho workspace.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {canManage && (
            <Button
              size="sm"
              onClick={() => setCreateOpen(true)}
              className="gap-2 shrink-0"
            >
              <Plus className="size-4" />
              Tạo trợ lý
            </Button>
          )}
        </div>
      </div>

      {/* Toolbar / Search Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
          <Input
            placeholder="Tìm theo tên hoặc mô tả trợ lý..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 text-xs"
          />
        </div>

        {searchQuery.trim() && (
          <span className="text-xs text-muted-foreground italic">
            Đang lọc trên {filteredItems.length}/{rawItems.length} trợ lý trong
            phạm vi tải
          </span>
        )}
      </div>

      {/* Main Content Area */}
      {assistantsQuery.isPending ? (
        <Card>
          <CardContent className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-8 w-24" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          </CardContent>
        </Card>
      ) : assistantsQuery.isError ? (
        <ErrorState
          error={assistantsQuery.error}
          onRetry={() => void assistantsQuery.refetch()}
          title="Không thể tải danh sách trợ lý"
          description="Đã xảy ra lỗi khi kết nối tới máy chủ. Vui lòng kiểm tra quyền truy cập workspace hoặc thử lại."
        />
      ) : rawItems.length === 0 ? (
        <Card>
          <CardContent className="p-6">
            <EmptyState
              icon={Bot}
              title="Chưa có trợ lý AI nào"
              description="Workspace chưa có trợ lý AI nào được tạo. Tạo trợ lý để kết nối kho tri thức đã biên soạn với model chat phục vụ người dùng."
              action={
                canManage
                  ? {
                      label: "Tạo trợ lý đầu tiên",
                      onClick: () => setCreateOpen(true),
                    }
                  : undefined
              }
            />
          </CardContent>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40">
                <TableHead className="w-[28%] font-semibold">
                  Tên trợ lý
                </TableHead>
                <TableHead className="w-[22%] font-semibold">
                  Kho tri thức
                </TableHead>
                <TableHead className="w-[20%] font-semibold">
                  Model chat
                </TableHead>
                <TableHead className="w-[12%] font-semibold">
                  Trạng thái
                </TableHead>
                <TableHead className="w-[10%] font-semibold text-center">
                  Bản sửa
                </TableHead>
                <TableHead className="w-[8%] text-right font-semibold">
                  Thao tác
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredItems.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="h-32 text-center text-muted-foreground text-xs"
                  >
                    Không tìm thấy trợ lý phù hợp với từ khóa &ldquo;
                    {searchQuery}&rdquo;.
                  </TableCell>
                </TableRow>
              ) : (
                filteredItems.map((item) => {
                  const collectionName =
                    collectionMap.get(item.collection_id) ?? item.collection_id;
                  const modelInfo = item.chat_provider_id
                    ? catalogMap.get(item.chat_provider_id)
                    : null;

                  return (
                    <TableRow key={item.id} className="hover:bg-muted/30">
                      {/* Name & Description */}
                      <TableCell className="align-top py-3.5">
                        <div className="space-y-1">
                          <Link
                            to="/workspaces/$workspaceId/assistants/$assistantId"
                            params={{
                              workspaceId,
                              assistantId: item.id,
                            }}
                            className="font-medium text-foreground hover:text-primary transition-colors flex items-center gap-1.5 group"
                          >
                            <span>{item.name}</span>
                            <ChevronRight className="size-3 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
                          </Link>
                          {item.description ? (
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {item.description}
                            </p>
                          ) : (
                            <span className="text-[11px] text-muted-foreground italic">
                              Chưa có mô tả
                            </span>
                          )}
                        </div>
                      </TableCell>

                      {/* Collection */}
                      <TableCell className="align-top py-3.5">
                        <div className="space-y-1">
                          <Link
                            to="/workspaces/$workspaceId/collections/$collectionId"
                            params={{
                              workspaceId,
                              collectionId: item.collection_id,
                            }}
                            search={DEFAULT_PAGE_SEARCH}
                            className="text-xs font-medium text-foreground hover:text-primary transition-colors inline-flex items-center gap-1"
                          >
                            <Database className="size-3 text-muted-foreground" />
                            <span className="line-clamp-1">
                              {collectionName}
                            </span>
                            <ExternalLink className="size-2.5 text-muted-foreground" />
                          </Link>
                          <div className="text-[10px] font-mono text-muted-foreground">
                            ID: {item.collection_id.slice(0, 12)}...
                          </div>
                        </div>
                      </TableCell>

                      {/* Model Chat */}
                      <TableCell className="align-top py-3.5">
                        {item.chat_provider_id === null ? (
                          <div className="space-y-0.5">
                            <Badge
                              variant="outline"
                              className="bg-primary/5 text-primary border-primary/20 text-[11px]"
                            >
                              Mặc định workspace
                            </Badge>
                            <p className="text-[10px] text-muted-foreground">
                              Giải quyết qua ModelOps
                            </p>
                          </div>
                        ) : modelInfo ? (
                          <div className="space-y-0.5">
                            <span className="text-xs font-medium text-foreground block">
                              {modelInfo.name}
                            </span>
                            <span className="text-[10px] font-mono text-muted-foreground block">
                              [{modelInfo.model_name}]
                            </span>
                          </div>
                        ) : (
                          <div className="space-y-0.5">
                            <span className="text-xs font-mono text-amber-600 dark:text-amber-400">
                              {item.chat_provider_id.slice(0, 14)}...
                            </span>
                            <Badge
                              variant="outline"
                              className="text-[10px] border-amber-500/30 text-amber-700 dark:text-amber-300"
                            >
                              Ngoài Catalog
                            </Badge>
                          </div>
                        )}
                      </TableCell>

                      {/* Active Status & Toggle */}
                      <TableCell className="align-top py-3.5">
                        <div className="flex items-center gap-2">
                          <LifecycleActions
                            workspaceId={workspaceId}
                            kind="assistant"
                            resourceId={item.id}
                            label={item.name}
                            role={role}
                            isActive={item.is_active}
                          />
                          <Badge
                            variant={item.is_active ? "default" : "secondary"}
                            className="text-[11px]"
                          >
                            {item.is_active ? "Bật" : "Tắt"}
                          </Badge>
                        </div>
                      </TableCell>

                      {/* Revision & Updated */}
                      <TableCell className="align-top py-3.5 text-center">
                        <div className="space-y-1">
                          <Badge
                            variant="outline"
                            className="text-[10px] font-mono"
                          >
                            v{item.revision}
                          </Badge>
                          <div className="text-[10px] text-muted-foreground">
                            {formatDateTimeValue(item.updated_at)}
                          </div>
                        </div>
                      </TableCell>

                      {/* Actions */}
                      <TableCell className="align-top py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-8 gap-1.5 text-xs"
                            disabled={!item.is_active}
                            onClick={() => setChatAssistant(item)}
                            title={
                              item.is_active
                                ? "Mở hội thoại thử với trợ lý này"
                                : "Cần bật trợ lý trước khi chat thử"
                            }
                          >
                            <MessageSquare className="size-3.5 text-primary" />
                            <span>Chat thử</span>
                          </Button>
                          <Link
                            to="/workspaces/$workspaceId/assistants/$assistantId"
                            params={{
                              workspaceId,
                              assistantId: item.id,
                            }}
                            className="inline-flex size-8 items-center justify-center rounded-md border text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                            title="Xem chi tiết"
                          >
                            <Bot className="size-3.5" />
                          </Link>
                          {canManage && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-8 text-muted-foreground hover:text-foreground"
                              onClick={() => setEditingAssistant(item)}
                              title="Sửa cấu hình"
                            >
                              <Pencil className="size-3.5" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>

          {/* Honest Pagination Footer */}
          <div className="flex items-center justify-between border-t bg-muted/20 px-4 py-3 sm:px-6">
            <span className="text-xs text-muted-foreground">
              Đang hiển thị {rawItems.length} trợ lý (
              {rawItems.length === 0
                ? "0"
                : `${offset + 1}–${offset + rawItems.length}`}
              )
            </span>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-1 text-xs"
                disabled={!hasPrevious || assistantsQuery.isPending}
                onClick={() => onOffsetChange(Math.max(0, offset - limit))}
              >
                <ArrowLeft className="size-3" />
                Trước
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-1 text-xs"
                disabled={!hasNext || assistantsQuery.isPending}
                onClick={() => onOffsetChange(offset + limit)}
              >
                Sau
                <ArrowRight className="size-3" />
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Create Dialog */}
      <AssistantFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        workspaceId={workspaceId}
      />

      {/* Edit Dialog */}
      {editingAssistant && (
        <AssistantFormDialog
          open={Boolean(editingAssistant)}
          onOpenChange={(open) => {
            if (!open) setEditingAssistant(null);
          }}
          workspaceId={workspaceId}
          assistant={editingAssistant}
          onSuccess={() => setEditingAssistant(null)}
        />
      )}

      {/* Chat thử Dialog */}
      <ConversationCreateDialog
        workspaceId={workspaceId}
        open={Boolean(chatAssistant)}
        onOpenChange={(open) => {
          if (!open) setChatAssistant(null);
        }}
        preselectedAssistant={chatAssistant ?? undefined}
      />
    </div>
  );
}
