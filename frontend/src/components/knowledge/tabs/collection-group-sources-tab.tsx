import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Eye,
  FileCheck2,
  FolderGit2,
  RefreshCw,
  Search,
  Sparkles,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "@/components/admin/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";
import type {
  KnowledgeCollection,
  KnowledgeGroupSource,
} from "@/types/knowledge";

interface CollectionGroupSourcesTabProps {
  collection: KnowledgeCollection;
  onAddSource: () => void;
}

export const CollectionGroupSourcesTab: React.FC<
  CollectionGroupSourcesTabProps
> = ({ collection, onAddSource }) => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [syncingSourceId, setSyncingSourceId] = useState<string | null>(null);

  // 1. Fetch Group Sources
  const {
    data: sources = [],
    isLoading,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey: ["knowledge-group-sources", collection.id],
    queryFn: () => knowledgeApi.getGroupSources(collection.id),
  });

  // 2. Mutation Sync Group Source
  const syncMutation = useMutation({
    mutationFn: (sourceId: string) => {
      setSyncingSourceId(sourceId);
      return knowledgeApi.syncGroupSource(collection.id, sourceId, {
        confirm_detach_removed: false,
      });
    },
    onSuccess: (data) => {
      if (data.failed_count > 0 || data.status === "failed") {
        toast.error(data.message || `Đồng bộ nguồn nhóm có ${data.failed_count} lỗi.`);
      } else if (data.status === "review_required") {
        toast.info(data.message || "Đã lập chỉ mục staging, chờ xuất bản.");
      } else {
        toast.success(data.message || "Đồng bộ nguồn nhóm tài liệu thành công.");
      }

      queryClient.invalidateQueries({
        queryKey: ["knowledge-group-sources", collection.id],
      });
      queryClient.invalidateQueries({
        queryKey: ["preview-source-sync", collection.id],
      });
      queryClient.invalidateQueries({
        queryKey: ["collection-summary-metrics", collection.id],
      });
      queryClient.invalidateQueries({
        queryKey: ["knowledge-collection", collection.id],
      });
    },
    onError: (err: unknown) => {
      toast.error(extractErrorMessage(err, "Đồng bộ thất bại."));
    },
    onSettled: () => {
      setSyncingSourceId(null);
    },
  });

  // Filter sources by search query
  const filteredSources = sources.filter((s) =>
    s.group_name.toLowerCase().includes(search.toLowerCase()),
  );

  const getStatusBadge = (status: KnowledgeGroupSource["status"]) => {
    switch (status) {
      case "ready":
        return (
          <Badge
            variant="outline"
            className="bg-success/10 text-success border-success/30 gap-1 text-[11px]"
          >
            <CheckCircle2 className="size-3" />
            Sẵn sàng
          </Badge>
        );
      case "updates_available":
        return (
          <Badge
            variant="outline"
            className="bg-warning/10 text-warning border-warning/30 gap-1 text-[11px]"
          >
            <Sparkles className="size-3" />
            Có cập nhật
          </Badge>
        );
      case "up_to_date":
        return (
          <Badge
            variant="outline"
            className="bg-success/10 text-success border-success/30 gap-1 text-[11px]"
          >
            <CheckCircle2 className="size-3" />
            Đã đồng bộ
          </Badge>
        );
      case "pending":
        return (
          <Badge
            variant="outline"
            className="bg-muted text-muted-foreground border-border gap-1 text-[11px]"
          >
            <Clock className="size-3" />
            Chờ xử lý
          </Badge>
        );
      case "review_required":
        return (
          <Badge
            variant="outline"
            className="bg-primary/10 text-primary border-primary/30 gap-1 text-[11px]"
          >
            <FileCheck2 className="size-3" />
            Chờ xuất bản
          </Badge>
        );
      case "syncing":
        return (
          <Badge
            variant="outline"
            className="bg-primary/10 text-primary border-primary/30 gap-1 text-[11px]"
          >
            <RefreshCw className="size-3 animate-spin" />
            Đang đồng bộ
          </Badge>
        );
      case "failed":
        return (
          <Badge
            variant="outline"
            className="bg-destructive/10 text-destructive border-destructive/30 gap-1 text-[11px]"
          >
            <AlertCircle className="size-3" />
            Có lỗi
          </Badge>
        );
      case "empty":
        return (
          <Badge
            variant="outline"
            className="bg-muted text-muted-foreground border-border text-[11px]"
          >
            Chưa có tài liệu
          </Badge>
        );
      case "detached":
        return (
          <Badge
            variant="outline"
            className="bg-muted text-muted-foreground border-border text-[11px]"
          >
            Đã gỡ
          </Badge>
        );
      default:
        return (
          <Badge
            variant="outline"
            className="text-muted-foreground text-[11px]"
          >
            {status}
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-4">
      {/* Action and Filter Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
          <Input
            placeholder="Tìm kiếm nhóm nguồn tài liệu..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 h-9 text-xs"
          />
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isRefetching}
            className="h-9 px-3 text-xs gap-1.5"
            title="Làm mới danh sách nguồn"
          >
            <RefreshCw
              className={`size-3.5 ${isRefetching ? "animate-spin" : ""}`}
            />
            <span>Làm mới</span>
          </Button>
        </div>
      </div>

      {/* Sources Content */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-muted-foreground">
          Đang tải danh sách nguồn tài liệu...
        </div>
      ) : sources.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="pt-6">
            <EmptyState
              icon={FolderGit2}
              title="Kho tri thức chưa có nguồn tài liệu"
              description="Hãy liên kết một Nhóm tài liệu từ Kho tài liệu để bắt đầu lập chỉ mục và cung cấp dữ liệu cho Trợ lý AI."
              action={{
                label: "Thêm nguồn",
                onClick: onAddSource,
              }}
            />
          </CardContent>
        </Card>
      ) : filteredSources.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="pt-6">
            <EmptyState
              icon={Search}
              title="Không tìm thấy nhóm nguồn phù hợp"
              description={`Không có nhóm tài liệu nào khớp với từ khóa "${search}".`}
              action={{
                label: "Xóa bộ lọc",
                onClick: () => setSearch(""),
              }}
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSources.map((src) => {
            const hasUpdates =
              src.has_updates ||
              src.status === "updates_available" ||
              (src.needs_build_count ?? 0) > 0;
            const isSyncing =
              syncingSourceId === src.id || src.status === "syncing";
            const isFailed = src.status === "failed" || (src.failed_count ?? 0) > 0;
            const isReviewRequired =
              src.status === "review_required" ||
              (src.publishable_count ?? 0) > 0 ||
              (src.awaiting_publish_count ?? 0) > 0;

            return (
              <Card
                key={src.id}
                className="flex flex-col border border-border shadow-2xs hover:border-primary/40 transition-colors"
              >
                <CardHeader className="p-4 pb-2 space-y-1.5">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-sm font-semibold text-foreground line-clamp-1">
                      {src.group_name}
                    </CardTitle>
                    {getStatusBadge(src.status)}
                  </div>
                  <CardDescription className="text-xs line-clamp-2 min-h-[2rem]">
                    {src.group_description ||
                      "Nguồn tài liệu liên kết lâu dài từ Kho tài liệu."}
                  </CardDescription>
                </CardHeader>

                <CardContent className="p-4 pt-2 flex-1 space-y-3 text-xs">
                  {/* Metrics grid */}
                  <div className="grid grid-cols-2 gap-2 p-2.5 rounded-md bg-muted/40 border border-border/50 text-[11px]">
                    <div>
                      <span className="text-muted-foreground">
                        Tổng tài liệu:
                      </span>
                      <span className="ml-1.5 font-semibold text-foreground">
                        {src.total_documents}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">
                        Đã xuất bản:
                      </span>
                      <span className="ml-1.5 font-semibold text-success">
                        {src.published_count}
                      </span>
                    </div>
                    {src.new_revision_count > 0 && (
                      <div className="text-warning">
                        <span>Revision mới:</span>
                        <span className="ml-1.5 font-semibold">
                          +{src.new_revision_count}
                        </span>
                      </div>
                    )}
                    {src.new_document_count > 0 && (
                      <div className="text-primary">
                        <span>Tài liệu mới:</span>
                        <span className="ml-1.5 font-semibold">
                          +{src.new_document_count}
                        </span>
                      </div>
                    )}
                    {src.not_ready_count > 0 && (
                      <div className="text-muted-foreground">
                        <span>Chưa sẵn sàng:</span>
                        <span className="ml-1.5 font-semibold">
                          {src.not_ready_count}
                        </span>
                      </div>
                    )}
                    {src.failed_count > 0 && (
                      <div className="text-destructive">
                        <span>Lỗi:</span>
                        <span className="ml-1.5 font-semibold">
                          {src.failed_count}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Sync status info */}
                  <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1">
                    <span className="flex items-center gap-1">
                      <Clock className="size-3" />
                      Đồng bộ lần cuối:
                    </span>
                    <span>
                      {src.last_synced_at
                        ? new Date(src.last_synced_at).toLocaleDateString(
                            "vi-VN",
                          )
                        : "Chưa đồng bộ"}
                    </span>
                  </div>
                </CardContent>

                <CardFooter className="p-4 pt-0 border-t border-border/50 flex items-center justify-between gap-2 mt-auto">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs gap-1.5"
                    onClick={() =>
                      navigate({
                        to: `/knowledge/${collection.id}/sources/${src.id}`,
                      })
                    }
                  >
                    <Eye className="size-3.5" />
                    <span>Xem chi tiết</span>
                  </Button>

                  {isReviewRequired ? (
                    <Button
                      size="sm"
                      className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 font-medium shadow-xs"
                      onClick={() =>
                        navigate({
                          to: `/knowledge/${collection.id}/sources/${src.id}`,
                        })
                      }
                    >
                      <FileCheck2 className="size-3.5" />
                      <span>Xuất bản</span>
                    </Button>
                  ) : isFailed ? (
                    <Button
                      size="sm"
                      className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 font-medium shadow-xs"
                      disabled={isSyncing}
                      onClick={() => syncMutation.mutate(src.id)}
                    >
                      <RefreshCw
                        className={`size-3.5 ${isSyncing ? "animate-spin" : ""}`}
                      />
                      <span>Thử lại</span>
                    </Button>
                  ) : hasUpdates ? (
                    <Button
                      size="sm"
                      className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 font-medium shadow-xs"
                      disabled={isSyncing}
                      onClick={() => syncMutation.mutate(src.id)}
                    >
                      <RefreshCw
                        className={`size-3.5 ${isSyncing ? "animate-spin" : ""}`}
                      />
                      <span>Đồng bộ</span>
                    </Button>
                  ) : null}
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};
