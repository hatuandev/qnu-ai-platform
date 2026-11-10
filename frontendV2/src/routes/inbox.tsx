import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  Clock,
  ExternalLink,
  FolderOpen,
  Inbox,
  Loader2,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useInboxQuery } from "@/api/inbox/queries";
import type { InboxItem, InboxKind } from "@/api/inbox/types";
import { EmptyState } from "@/components/admin/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useUiStore } from "@/lib/ui-store";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/inbox")({
  component: InboxPage,
});

const KIND_LABELS: Record<
  InboxKind,
  {
    label: string;
    variant: "default" | "secondary" | "destructive" | "outline";
  }
> = {
  review_pending: { label: "Chờ duyệt", variant: "default" },
  changes_requested: { label: "Yêu cầu sửa", variant: "outline" },
  awaiting_publish: { label: "Chờ phát hành", variant: "secondary" },
  sync_incomplete: { label: "Đang đồng bộ", variant: "secondary" },
  preparation_failed: { label: "Lỗi chuẩn bị", variant: "destructive" },
};

function formatOccurredTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return isoString;
    return date.toLocaleString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return isoString;
  }
}

function InboxPage() {
  const navigate = useNavigate();
  const activeWorkspaceId = useUiStore((s) => s.activeWorkspaceId);

  const [selectedKind, setSelectedKind] = useState<InboxKind | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);

  const queryParams = useMemo(() => {
    return selectedKind === "all" ? undefined : { kind: selectedKind };
  }, [selectedKind]);

  const {
    data: inboxData,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useInboxQuery(activeWorkspaceId, queryParams);

  const items = inboxData?.items ?? [];
  const counts = inboxData?.counts ?? {};
  const totalCount = inboxData?.meta?.total ?? items.length;

  // Filter items by client search
  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return items;
    const q = searchQuery.toLowerCase();
    return items.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.problem.toLowerCase().includes(q) ||
        item.collection_name.toLowerCase().includes(q),
    );
  }, [items, searchQuery]);

  // Selected item
  const selectedItem: InboxItem | undefined = useMemo(() => {
    if (!filteredItems.length) return undefined;
    if (selectedItemId) {
      const found = filteredItems.find((i) => i.id === selectedItemId);
      if (found) return found;
    }
    return filteredItems[0];
  }, [filteredItems, selectedItemId]);

  const handleOpenSource = (item: InboxItem) => {
    if (item.deep_path) {
      window.location.href = item.deep_path;
      return;
    }
    if (item.source_id) {
      void navigate({
        to: "/knowledge/$sourceId",
        params: { sourceId: item.source_id },
        search: { collectionId: item.collection_id },
      });
      return;
    }
    if (item.collection_id) {
      void navigate({
        to: "/knowledge",
        search: { collectionId: item.collection_id },
      });
    }
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col bg-background select-none overflow-x-hidden">
      {/* 1. Header */}
      <header className="flex h-14 items-center justify-between border-b border-border/60 bg-card px-4 gap-4 shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="size-8 p-0 text-muted-foreground hover:text-foreground shrink-0"
          >
            <Link to="/knowledge" aria-label="Quay lại kho tri thức">
              <ArrowLeft className="size-4" />
            </Link>
          </Button>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-semibold text-foreground tracking-tight">
                Hộp thư Duyệt & Xử lý
              </h1>
              {totalCount > 0 && (
                <Badge
                  variant="secondary"
                  className="text-[10px] h-4 px-1.5 font-medium"
                >
                  {totalCount} việc cần xử lý
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground truncate">
              Xem xét các bản nháp chờ duyệt, phiên bản chờ phát hành và thông
              báo từ hệ thống tri thức.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void refetch()}
            disabled={isFetching}
            className="h-8 text-xs gap-1.5"
            title="Làm mới danh sách"
          >
            <RefreshCw
              className={cn(
                "size-3.5",
                isFetching && "animate-spin text-primary",
              )}
            />
            <span>Làm mới</span>
          </Button>
        </div>
      </header>

      {/* 2. Main Master-Detail Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Master List */}
        <div className="w-full md:w-[420px] lg:w-[460px] border-r border-border/60 bg-card/40 flex flex-col shrink-0 overflow-hidden">
          {/* Filter Tabs & Search */}
          <div className="p-3 border-b border-border/60 space-y-2 bg-card">
            <div className="relative">
              <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Tìm tiêu đề, kho, nội dung..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full h-8 pl-8 pr-3 text-xs rounded-md border border-border/70 bg-background focus:outline-hidden focus:ring-1 focus:ring-primary"
              />
            </div>

            <Tabs
              value={selectedKind}
              onValueChange={(val) => {
                setSelectedKind(val as typeof selectedKind);
                setSelectedItemId(null);
              }}
              className="w-full"
            >
              <TabsList className="h-7 w-full justify-start overflow-x-auto p-0.5 bg-muted/50 text-[11px]">
                <TabsTrigger value="all" className="h-6 px-2 text-[11px]">
                  Tất cả (
                  {counts.review_pending ??
                    0 +
                      (counts.awaiting_publish ?? 0) +
                      (counts.changes_requested ?? 0)}
                  )
                </TabsTrigger>
                <TabsTrigger
                  value="review_pending"
                  className="h-6 px-2 text-[11px]"
                >
                  Chờ duyệt{" "}
                  {counts.review_pending ? `(${counts.review_pending})` : ""}
                </TabsTrigger>
                <TabsTrigger
                  value="awaiting_publish"
                  className="h-6 px-2 text-[11px]"
                >
                  Chờ phát hành{" "}
                  {counts.awaiting_publish
                    ? `(${counts.awaiting_publish})`
                    : ""}
                </TabsTrigger>
                <TabsTrigger
                  value="changes_requested"
                  className="h-6 px-2 text-[11px]"
                >
                  Yêu cầu sửa{" "}
                  {counts.changes_requested
                    ? `(${counts.changes_requested})`
                    : ""}
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {/* List items */}
          <div className="flex-1 overflow-y-auto divide-y divide-border/50">
            {isLoading ? (
              <div className="py-20 flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="size-5 animate-spin text-primary" />
                <span>Đang tải danh sách hộp thư...</span>
              </div>
            ) : isError ? (
              <div className="p-6">
                <EmptyState
                  title="Không thể tải hộp thư"
                  description={
                    error instanceof Error
                      ? error.message
                      : "Đã có lỗi xảy ra khi truy vấn dữ liệu hộp thư."
                  }
                  action={{
                    label: "Thử lại",
                    onClick: () => void refetch(),
                  }}
                />
              </div>
            ) : filteredItems.length === 0 ? (
              <div className="p-6">
                <EmptyState
                  title="Hộp thư trống"
                  description={
                    searchQuery
                      ? "Không tìm thấy nội dung phù hợp với từ khóa."
                      : "Hiện tại không có mục nào đang chờ duyệt hoặc cần xử lý trong đơn vị này."
                  }
                />
              </div>
            ) : (
              filteredItems.map((item) => {
                const isSelected = selectedItem?.id === item.id;
                const kindMeta = KIND_LABELS[item.kind] || {
                  label: item.kind,
                  variant: "secondary" as const,
                };

                return (
                  <button
                    type="button"
                    key={item.id}
                    onClick={() => setSelectedItemId(item.id)}
                    className={cn(
                      "w-full p-3.5 cursor-pointer transition-colors text-left space-y-1.5 block",
                      isSelected
                        ? "bg-primary/10 border-l-2 border-primary"
                        : "hover:bg-muted/40",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <Badge
                        variant={kindMeta.variant}
                        className="text-[10px] h-4 px-1.5 font-medium"
                      >
                        {kindMeta.label}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <Clock className="size-2.5" />
                        <span>{formatOccurredTime(item.occurred_at)}</span>
                      </span>
                    </div>

                    <h3 className="text-xs font-medium text-foreground line-clamp-1">
                      {item.title}
                    </h3>

                    <p className="text-[11px] text-muted-foreground line-clamp-2">
                      {item.problem}
                    </p>

                    <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground pt-0.5">
                      <FolderOpen className="size-3 text-primary/70 shrink-0" />
                      <span className="truncate">{item.collection_name}</span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right: Detail View */}
        <div className="flex-1 bg-background flex flex-col overflow-hidden">
          {selectedItem ? (
            <div className="flex-1 flex flex-col overflow-y-auto p-6 space-y-6 max-w-4xl">
              {/* Item Top Banner */}
              <div className="space-y-2 border-b border-border/60 pb-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        KIND_LABELS[selectedItem.kind]?.variant ?? "secondary"
                      }
                      className="text-xs h-5 px-2"
                    >
                      {KIND_LABELS[selectedItem.kind]?.label ??
                        selectedItem.kind}
                    </Badge>
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="size-3" />
                      <span>
                        {formatOccurredTime(selectedItem.occurred_at)}
                      </span>
                    </span>
                  </div>

                  <Button
                    size="sm"
                    onClick={() => handleOpenSource(selectedItem)}
                    className="h-8 gap-1.5 text-xs shadow-2xs"
                  >
                    <span>Mở tài liệu xử lý</span>
                    <ExternalLink className="size-3.5" />
                  </Button>
                </div>

                <h2 className="text-lg font-semibold text-foreground tracking-tight">
                  {selectedItem.title}
                </h2>

                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">
                    Kho tri thức:
                  </span>
                  <span>{selectedItem.collection_name}</span>
                  {selectedItem.document_id && (
                    <>
                      <span>•</span>
                      <span>Mã tài liệu: {selectedItem.document_id}</span>
                    </>
                  )}
                </div>
              </div>

              {/* Problem Card */}
              <Card className="border-border/70 shadow-2xs">
                <CardHeader className="p-4 pb-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                    <AlertCircle className="size-4 text-primary" />
                    <span>Nội dung thẩm định & Tình trạng</span>
                  </div>
                </CardHeader>
                <CardContent className="p-4 pt-1 text-xs text-foreground/90 leading-relaxed space-y-3">
                  <p className="font-medium bg-muted/40 p-3 rounded-md border border-border/50">
                    {selectedItem.problem}
                  </p>

                  {selectedItem.detail && (
                    <div className="text-muted-foreground whitespace-pre-wrap text-[11px] bg-card p-3 rounded-md border border-border/40">
                      {selectedItem.detail}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Action Prompt */}
              <div className="p-4 rounded-lg border border-primary/20 bg-primary/5 flex items-start gap-3">
                <ShieldCheck className="size-5 text-primary shrink-0 mt-0.5" />
                <div className="space-y-1 text-xs flex-1">
                  <span className="font-semibold text-foreground block">
                    Hướng dẫn xử lý tiếp theo
                  </span>
                  <p className="text-muted-foreground">
                    Nhấn vào nút <strong>"Mở tài liệu xử lý"</strong> ở trên để
                    vào giao diện Chi tiết tài liệu, kiểm tra đối chiếu tệp gốc,
                    chỉnh sửa nội dung văn bản nếu cần hoặc tiến hành Duyệt &
                    Phát hành tài liệu.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center p-6 text-muted-foreground text-xs">
              <div className="text-center space-y-2">
                <Inbox className="size-10 text-muted-foreground/40 mx-auto" />
                <p>Chọn một mục từ danh sách bên trái để xem chi tiết.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
