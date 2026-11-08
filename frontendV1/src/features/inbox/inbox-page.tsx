import { Link } from "@tanstack/react-router";
import { ArrowRight, Inbox as InboxIcon, RefreshCw } from "lucide-react";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCollectionsQuery } from "@/features/knowledge/queries";
import { formatDateTimeValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { useInboxQuery } from "./inbox-queries";
import {
  formatAllowedRoles,
  INBOX_KIND_LABELS,
  INBOX_KINDS,
  inboxKindVariant,
  inboxTarget,
} from "./inbox-schemas";
import type { InboxItem, InboxKind } from "./inbox-types";

const ALL = "all";

function InboxOpenLink({
  workspaceId,
  item,
}: {
  workspaceId: string;
  item: InboxItem;
}) {
  const target = inboxTarget(workspaceId, item);
  const className =
    "inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline";

  if (
    target.to ===
    "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
  ) {
    return (
      <Link to={target.to} params={target.params} className={className}>
        <span>Mở</span>
        <ArrowRight className="size-3.5" />
      </Link>
    );
  }

  if (
    target.to ===
    "/workspaces/$workspaceId/collections/$collectionId/documents/$documentId/versions/$versionId"
  ) {
    return (
      <Link to={target.to} params={target.params} className={className}>
        <span>Mở</span>
        <ArrowRight className="size-3.5" />
      </Link>
    );
  }

  return (
    <Link
      to={target.to}
      params={target.params}
      search={target.search}
      className={className}
    >
      <span>Mở</span>
      <ArrowRight className="size-3.5" />
    </Link>
  );
}

export function InboxPage({
  workspaceId,
  page,
  pageSize,
  kind,
  collectionId,
  onKindChange,
  onCollectionChange,
  onPageChange,
  onPageSizeChange,
  onResetFilters,
}: {
  workspaceId: string;
  page: number;
  pageSize: number;
  kind?: InboxKind;
  collectionId?: string;
  onKindChange: (kind: InboxKind | undefined) => void;
  onCollectionChange: (collectionId: string | undefined) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onResetFilters: () => void;
}) {
  const query = useInboxQuery(workspaceId, {
    kind,
    collectionId,
    page,
    pageSize,
  });
  const collectionsQuery = useCollectionsQuery(workspaceId, {
    page: 1,
    pageSize: 100,
  });

  const items = query.data?.items ?? [];
  const total = query.data?.meta.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const hasFilters = Boolean(kind || collectionId);

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Điều phối"
        title="Cần xử lý"
        description="Việc đang chờ xử lý được tổng hợp từ trạng thái thật của tài liệu, yêu cầu duyệt và chỉ mục. Dòng tự rời danh sách khi nguồn được giải quyết; không có thao tác ẩn thủ công."
        actions={
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs"
            disabled={query.isFetching}
            onClick={() => void query.refetch()}
          >
            <RefreshCw
              className={cn("size-3.5", query.isFetching && "animate-spin")}
            />
            <span>Làm mới</span>
          </Button>
        }
      />

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
        <div className="grid grid-cols-2 gap-2 sm:flex sm:items-center">
          <Select
            value={kind ?? ALL}
            onValueChange={(value) =>
              onKindChange(value === ALL ? undefined : (value as InboxKind))
            }
          >
            <SelectTrigger
              aria-label="Lọc theo loại việc"
              className="h-8 w-full text-xs sm:w-[180px]"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>Tất cả loại việc</SelectItem>
              {INBOX_KINDS.map((option) => (
                <SelectItem key={option} value={option}>
                  {INBOX_KIND_LABELS[option]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={collectionId ?? ALL}
            onValueChange={(value) =>
              onCollectionChange(value === ALL ? undefined : value)
            }
          >
            <SelectTrigger
              aria-label="Lọc theo kho tri thức"
              className="h-8 w-full text-xs sm:w-[220px]"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>Tất cả kho tri thức</SelectItem>
              {(collectionsQuery.data?.items ?? []).map((collection) => (
                <SelectItem key={collection.id} value={collection.id}>
                  {collection.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {hasFilters ? (
            <Button
              variant="ghost"
              size="sm"
              className="col-span-2 h-8 text-xs sm:col-span-1"
              onClick={onResetFilters}
            >
              Đặt lại
            </Button>
          ) : null}
        </div>
      </div>

      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <Card className="overflow-hidden rounded-xl shadow-2xs">
          {query.isLoading ? (
            <div className="grid gap-2 p-4">
              {[0, 1, 2].map((row) => (
                <Skeleton key={row} className="h-14 w-full" />
              ))}
            </div>
          ) : items.length === 0 ? (
            <EmptyState
              icon={InboxIcon}
              title={
                hasFilters
                  ? "Không có việc phù hợp bộ lọc"
                  : "Không có việc cần xử lý"
              }
              description={
                hasFilters
                  ? "Thử bỏ bộ lọc để xem toàn bộ việc trong workspace."
                  : "Khi có phiên bản chờ duyệt, yêu cầu sửa, đồng bộ lỗi hoặc chuẩn bị thất bại, việc sẽ xuất hiện ở đây."
              }
              action={
                hasFilters
                  ? { label: "Bỏ bộ lọc", onClick: onResetFilters }
                  : undefined
              }
            />
          ) : (
            <div className="w-full overflow-x-auto">
              <Table className="min-w-[860px]">
                <TableHeader>
                  <TableRow>
                    <TableHead className="min-w-[260px]">Vấn đề</TableHead>
                    <TableHead className="min-w-[190px]">Tài liệu</TableHead>
                    <TableHead className="w-[140px]">Thời điểm</TableHead>
                    <TableHead className="w-[170px]">
                      Nhóm được phép xử lý
                    </TableHead>
                    <TableHead className="w-[80px] text-right">
                      <span className="sr-only">Liên kết</span>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="align-top">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant={inboxKindVariant(item.kind)}>
                            {INBOX_KIND_LABELS[item.kind]}
                          </Badge>
                          <span className="text-sm font-medium text-foreground">
                            {item.problem}
                          </span>
                        </div>
                        {item.detail ? (
                          <p className="mt-1 text-xs text-muted-foreground">
                            {item.detail}
                          </p>
                        ) : null}
                      </TableCell>
                      <TableCell className="align-top">
                        <div className="text-sm font-medium text-foreground">
                          {item.title}
                        </div>
                        {item.collection_name !== item.title ? (
                          <div className="text-xs text-muted-foreground">
                            {item.collection_name}
                          </div>
                        ) : null}
                      </TableCell>
                      <TableCell className="align-top text-xs text-muted-foreground whitespace-nowrap">
                        {formatDateTimeValue(item.occurred_at)}
                      </TableCell>
                      <TableCell className="align-top text-xs text-foreground">
                        {formatAllowedRoles(item.allowed_roles)}
                      </TableCell>
                      <TableCell className="align-top text-right">
                        <InboxOpenLink workspaceId={workspaceId} item={item} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          {items.length > 0 ? (
            <div className="border-t px-3">
              <DataTablePagination
                page={page}
                pageSize={pageSize}
                pageCount={pageCount}
                total={total}
                onPageChange={onPageChange}
                onPageSizeChange={onPageSizeChange}
              />
            </div>
          ) : null}
        </Card>
      )}
    </div>
  );
}
